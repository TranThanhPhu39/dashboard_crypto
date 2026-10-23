"""Public live readings preserve receipt integrity and never expose labels/keys."""
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile
from src.live_dashboard_data import observations,latest_forecasts,verified


class LiveDataTests(unittest.TestCase):
    def put(self,root,name,data):
        raw=data if isinstance(data,bytes) else json.dumps(data).encode()
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_latest_crypto_observation_without_private_fields(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);name='data/raw/btc_coinmetrics.json'
            digest=self.put(root,name,dict(data=[dict(time='2026-10-21T00:00:00Z',PriceUSD='1.25'),dict(time='2026-10-22T00:00:00Z',PriceUSD='1.5')],api_key='DO_NOT_PUBLISH'))
            row=dict(file=name,sha256=digest,status='ok',available_at_utc='2026-10-23T01:00:00Z',url='private provider URL')
            result=observations(root,[row]);self.assertEqual(result[0]['observation_date'],'2026-10-22');self.assertEqual(result[0]['value'],1.5)
            self.assertNotIn('DO_NOT_PUBLISH',json.dumps(result));self.assertNotIn('private',json.dumps(result))
            (root/name).write_bytes(b'changed')
            with self.assertRaises(ValueError):observations(root,[row])

    def test_vintage_date_and_observation_date_are_separate(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);records=[]
            for vintage,value in [('2026-10-21',110),('2026-10-22',112)]:
                stream=io.BytesIO()
                with zipfile.ZipFile(stream,'w') as archive:
                    archive.writestr('DTWEXBGS_obs._by_real-time_period.csv','period_start_date,realtime_start_date,realtime_end_date,DTWEXBGS\n2026-10-20,2026-10-21,9999-12-31,'+str(value)+'\n2026-10-23,2026-10-23,9999-12-31,999\n')
                name='data/raw/usd_'+vintage+'.zip';digest=self.put(root,name,stream.getvalue())
                records.append(dict(file=name,sha256=digest,status='ok',series_id='DTWEXBGS',requested_vintage_date=vintage))
            row=observations(root,records)[0]
            self.assertEqual((row['observation_date'],row['vintage_date'],row['value']),('2026-10-20','2026-10-22',112))

    def test_latest_frozen_risk_forecast_does_not_publish_outcomes(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);base='data/prospective/evidence_20261019/'
            protocol=self.put(root,base+'protocol.json',{})
            env=self.put(root,base+'envelopes/sample.json',dict(information_day='2026-10-21',private='DO_NOT_PUBLISH'))
            for day,value in [(23,.001),(24,.002)]:
                record=dict(asset='btc',origin_utc=f'2026-10-{day}T00:00:00Z',target_end_utc=f'2026-10-{day+1}T00:00:00Z',logged_at_utc='2026-10-22T01:00:00Z',protocol_sha256=protocol,envelope=base+'envelopes/sample.json',envelope_sha256=env,actual_return='DO_NOT_PUBLISH',predictions=[dict(target='squared_return',model='elastic_net',variant='long_macro',predicted=value,model_sha256='f'*64)])
                self.put(root,base+f'predictions/{day}_btc.json',record)
            rows=latest_forecasts(root);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['predicted_squared_return'],.002)
            self.assertNotIn('DO_NOT_PUBLISH',json.dumps(rows));self.assertNotIn('actual_return',json.dumps(rows))

    def test_path_outside_workspace_is_rejected(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):verified(Path(folder),'../outside','0'*64)


if __name__=='__main__':unittest.main()
