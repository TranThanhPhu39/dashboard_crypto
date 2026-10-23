"""FOMC display preserves sample, candle-close timing and frozen intervals."""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.dashboard_fomc import payload


class FomcDisplayTests(unittest.TestCase):
    def put(self, root, name, data):
        raw=data if isinstance(data, bytes) else json.dumps(data).encode()
        path=root/name;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def csv(self, root, name, rows):
        stream=io.StringIO();writer=csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
        return self.put(root, name, stream.getvalue().encode())

    def fixture(self, root):
        audit=[];panel=[];intervals=[];links={}
        outcomes=['intraday','event_day']+[f'post_{h}' for h in range(1,31)]
        for day, offset in [('2019-01-30','-05:00'),('2020-06-10','-04:00')]:
            local=datetime.fromisoformat(day+'T14:00:00'+offset)
            utc=datetime.fromtimestamp(local.timestamp(), timezone.utc)
            links[day]='https://www.federalreserve.gov/newsevents/pressreleases/monetary'+day.replace('-','')+'a.htm'
            for asset in ['BTC','ETH']:
                # Distinguish the OPEN timestamp from its closing time by 60s.
                candles=[[int(utc.timestamp())+minute*60-60,1,1,1,100+minute,1] for minute in range(-10,21)]
                name='data/raw/fomc_coinbase/'+asset+day+'.json';digest=self.put(root,name,candles)
                audit.append(dict(asset=asset,date=day,event_time_et=local.isoformat(),event_time_utc=utc.isoformat(),scheduled='True',primary_joint='True',author_policy=.02,author_information=-.01,pc1=.01,prior_vix=26,minute_file=name,minute_sha256=digest))
                for outcome in outcomes:panel.append(dict(asset=asset,date=day,outcome=outcome,actual_pct=100*math.log(120/90) if outcome=='intraday' else 2.5,primary_joint='True'))
        for asset in ['BTC','ETH']:
            for shock in ['policy','information']:
                for outcome in outcomes:intervals.append(dict(asset=asset,shock=shock,outcome=outcome,weight=.5,beta=-.2,lower95_percentile=-.5,upper95_percentile=.1,successful_draws=999))
        a='outputs/research/fomc_identification_20261019/event_audit.csv'
        p='data/processed/fomc_identification_20261019/analysis_panel.csv'
        i='outputs/research/evidence_20261019/generated_shock_intervals.csv'
        hashes={a:self.csv(root,a,audit),p:self.csv(root,p,panel),i:self.csv(root,i,intervals)}
        self.put(root,'dashboard/fomc_display_sources.json',dict(files=hashes))
        self.put(root,'dashboard/fomc_statements.json',dict(statements=links))
        self.put(root,'outputs/research/fomc_identification_20261019/analysis_lock.json',dict(event_audit_sha256=hashes[a],panel_sha256=hashes[p]))
        return audit

    def test_joint_sample_dst_units_and_minute_close_alignment(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);self.fixture(root);data=payload(root)
            self.assertEqual(data['sample'],dict(count=2,first_date='2019-01-30',last_date='2020-06-10',pre2020=1,post2020=1))
            self.assertEqual(len(data['intervals']),128)
            self.assertEqual([e['event_time_utc'][11:16] for e in data['events']],['19:00','18:00'])
            for e in data['events']:
                self.assertEqual((e['policy_bps'],e['information_bps']),(2,-1))
                for s in e['assets'].values():
                    self.assertEqual(len(s['minute_path']),31)
                    self.assertEqual(s['minute_path'][0],[-10,0])
                    self.assertAlmostEqual(s['minute_path'][-1][1],s['returns']['intraday'])
                    self.assertEqual(s['returns']['post_30'],2.5)
            self.assertEqual(data['intervals'][0]['lower95'],-.5)

    def test_changed_minute_bytes_are_rejected(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);audit=self.fixture(root)
            (root/audit[0]['minute_file']).write_text('[]')
            with self.assertRaisesRegex(ValueError,'checksum'):payload(root)

    def test_rewritten_input_manifest_cannot_bypass_original_lock(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);self.fixture(root)
            path=root/'dashboard/fomc_display_sources.json';data=json.loads(path.read_text())
            name='data/processed/fomc_identification_20261019/analysis_panel.csv'
            raw=(root/name).read_bytes()+b'\n';(root/name).write_bytes(raw)
            data['files'][name]=hashlib.sha256(raw).hexdigest();path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'frozen analysis'):payload(root)

    def test_statement_link_must_match_event_and_official_domain(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);self.fixture(root)
            path=root/'dashboard/fomc_statements.json';data=json.loads(path.read_text())
            data['statements']['2019-01-30']='https://example.com/fomc';path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'official FOMC'):payload(root)


if __name__=='__main__':unittest.main()
