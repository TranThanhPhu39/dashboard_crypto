"""Download public research sources; retain bytes, URLs, UTC fetch times and hashes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, hashlib, json, datetime, time, argparse

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data'/'raw'
RAW.mkdir(parents=True,exist_ok=True)
START='2013-12-01'
END='2026-10-15'  # Last complete UTC day at the user's 2026-10-16 cutoff.
SOURCES={
 **{f'{a}_coinmetrics.json':f'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={a}&metrics=PriceUSD&frequency=1d&start_time={START}&end_time={END}&page_size=10000' for a in ['btc','eth']},
 **{f'{s}_fred.csv':f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}&cosd={START}&coed={END}' for s in ['VIXCLS','DTWEXBGS','DGS2','DGS10','DFF','DFEDTARL','DFEDTARU','SP500','DCOILWTICO','NFCI']},
 'sp500_yahoo.json':'https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=1385856000&period2=1792108800&interval=1d',
 'gold_yahoo.json':'https://query2.finance.yahoo.com/v8/finance/chart/GC%3DF?period1=1385856000&period2=1792108800&interval=1d',
 'gold_spot_stooq.csv':'https://stooq.pl/q/d/l/?s=xauusd&i=d&d1=20131201&d2=20261015',
 'USMPD.xlsx':'https://www.frbsf.org/wp-content/uploads/USMPD.xlsx',
 'monetary-policy-surprises.zip':'https://www.frbsf.org/wp-content/uploads/monetary-policy-surprises.zip',
}
def fetch(item):
 name,url=item; p=RAW/name
 if p.exists():
  return {'file':name,'url':url,'status':'cached','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 for attempt in range(3):
  try:
   r=requests.get(url,timeout=(15,45),headers={'User-Agent':'Mozilla/5.0 (academic research data download)'})
   r.raise_for_status(); b=r.content
   if name.endswith('.csv'):
    assert b',' in b[:300] and b'<' not in b[:50], 'Not CSV'
   if name.endswith('.json'): json.loads(b)
   if name.endswith(('.xlsx','.zip')): assert b[:2]==b'PK','Not ZIP/XLSX'
   p.write_bytes(b)
   return {'file':name,'url':url,'status':'ok','retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
  except Exception as e:
   err=str(e); time.sleep(attempt+1)
 return {'file':name,'url':url,'status':'failed','error':err}
if __name__=='__main__':
 records=[]
 with ThreadPoolExecutor(max_workers=5) as pool:
  for f in as_completed([pool.submit(fetch,i) for i in SOURCES.items()]):
   x=f.result(); records.append(x); print(x['file'],x['status'],x.get('bytes',x.get('error','')),flush=True)
 old_path=ROOT/'data'/'source_log.json'
 old={x['file']:x for x in json.loads(old_path.read_text())} if old_path.exists() else {}
 for x in records:
  if x['status']!='cached' or x['file'] not in old: old[x['file']]=x
 old_path.write_text(json.dumps(list(old.values()),indent=2),encoding='utf-8')
