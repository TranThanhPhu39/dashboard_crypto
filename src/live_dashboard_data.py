"""Read-only public observations and frozen forecasts; never fit or score."""
import csv
from datetime import datetime,timezone,timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

SERIES={'DTWEXBGS':('Broad USD','index'),'DGS2':('Treasury 2Y','%'),'DGS10':('Treasury 10Y','%'),'DFF':('Fed funds','%'),'DCOILWTICO':('WTI','USD/barrel'),'NFCI':('NFCI','index')}


def verified(root,name,digest):
    root=Path(root).resolve();path=(root/name).resolve()
    if not path.is_relative_to(root):raise ValueError('Source outside workspace')
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Source checksum mismatch')
    return data


def number(value):
    value=float(value)
    if not math.isfinite(value):raise ValueError('Nonfinite observation')
    return value


def observations(root,sources):
    """Latest observation per series in this capture, keeping vintage dates."""
    result={}
    for row in sources:
        if row.get('status')!='ok' or not row.get('file'):continue
        name=Path(row['file']).name;sid=row.get('series_id');vintage=row.get('requested_vintage_date','')
        key=sid if sid in SERIES else name
        if key in result and vintage<=result[key].get('vintage_date',''):continue
        if not (sid in SERIES or name in ['btc_coinmetrics.json','eth_coinmetrics.json','VIXCLS_fred.csv','sp500_yahoo.json','gold_yahoo.json']):continue
        raw=verified(root,row['file'],row['sha256'])
        points=[]
        if name.endswith('_coinmetrics.json'):
            label=name[:3].upper()+'/USD';unit='USD';source='Coin Metrics PriceUSD'
            for point in json.loads(raw)['data']:
                try:points.append((point['time'][:10],number(point['PriceUSD'])))
                except (ValueError,TypeError,KeyError):continue
        elif sid in SERIES:
            label,unit=SERIES[sid];source='ALFRED '+sid
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                member=next(n for n in archive.namelist() if n.endswith('obs._by_real-time_period.csv'))
                records=csv.DictReader(io.StringIO(archive.read(member).decode('utf-8-sig')))
                for point in records:
                    if point['period_start_date']>vintage or point['realtime_start_date']>vintage or (point.get('realtime_end_date') and point['realtime_end_date']<vintage):continue
                    try:points.append((point['period_start_date'],number(point[sid])))
                    except (ValueError,TypeError):continue
        elif name=='VIXCLS_fred.csv':
            label='VIX';unit='index';source='FRED VIXCLS'
            for point in csv.reader(io.StringIO(raw.decode('utf-8-sig'))):
                try:points.append((point[0],number(point[1])))
                except (ValueError,TypeError,IndexError):continue
        else:
            quote=json.loads(raw)['chart']['result'][0];label='S&P 500' if name.startswith('sp500') else 'Gold futures';unit='index' if name.startswith('sp500') else 'USD/oz';source='Yahoo daily close'
            offset=timedelta(seconds=quote['meta'].get('gmtoffset',0))
            for stamp,value in zip(quote['timestamp'],quote['indicators']['quote'][0]['close']):
                try:points.append(((datetime.fromtimestamp(stamp,timezone.utc)+offset).date().isoformat(),number(value)))
                except (ValueError,TypeError):continue
        if not points:continue
        day,value=max(points,key=lambda p:p[0])
        result[key]=dict(label=label,value=value,unit=unit,observation_date=day,vintage_date=vintage or None,received_at_utc=row.get('available_at_utc'),source=source)
    return sorted(result.values(),key=lambda r:r['label'])


def latest_forecasts(root):
    folder=Path(root)/'data/prospective/evidence_20261019'
    files=list((folder/'predictions').glob('*.json'))
    if not files:return []
    protocol=hashlib.sha256((folder/'protocol.json').read_bytes()).hexdigest()
    latest={}
    for path in files:
        data=path.read_bytes();record=json.loads(data)
        if record['asset'] not in ['btc','eth']:raise ValueError('Unexpected forecast asset')
        if record['protocol_sha256']!=protocol:raise ValueError('Forecast protocol mismatch')
        if record['asset'] not in latest or record['origin_utc']>latest[record['asset']][0]['origin_utc']:
            latest[record['asset']]=(record,hashlib.sha256(data).hexdigest())
    rows=[]
    for record,digest in latest.values():
        env=json.loads(verified(root,record['envelope'],record['envelope_sha256']))
        for prediction in record['predictions']:
            if prediction['target']!='squared_return' or prediction['model'] not in ['elastic_net','gradient_boosting']:continue
            value=number(prediction['predicted'])
            if value<=0:raise ValueError('Nonpositive risk forecast')
            rows.append(dict(asset=record['asset'].upper(),origin_utc=record['origin_utc'],target_end_utc=record['target_end_utc'],logged_at_utc=record['logged_at_utc'],information_day=env['information_day'],model=prediction['model'],variant=prediction['variant'],predicted_squared_return=value,model_sha256=prediction['model_sha256'],forecast_sha256=digest))
    return rows
