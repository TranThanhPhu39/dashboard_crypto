"""Coinbase minute data for statement windows; separate from Coin Metrics daily prices."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import pandas as pd,numpy as np,requests,time,json,hashlib,datetime
ROOT=Path(__file__).resolve().parent; RAW=ROOT/'data/raw/fomc_coinbase'; RAW.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'data/processed'
e=pd.read_excel(ROOT/'data/raw/USMPD.xlsx',sheet_name='Statements')
e=e[(pd.to_datetime(e.Date)>='2014-01-01')&(pd.to_datetime(e.Date)<='2026-10-15')]
def fetch(row,asset):
 dt=pd.Timestamp(row['date_time']).tz_localize('America/New_York').tz_convert('UTC')
 start=dt-pd.Timedelta(minutes=10); end=dt+pd.Timedelta(minutes=20)
 name=f'{asset}_{dt.strftime("%Y%m%dT%H%M%S")}.json'; p=RAW/name
 url=f'https://api.exchange.coinbase.com/products/{asset}-USD/candles'
 params={'granularity':60,'start':(start-pd.Timedelta(minutes=1)).isoformat(),'end':end.isoformat()}
 rec={'asset':asset,'event_time_utc':dt.isoformat(),'window_start_utc':start.isoformat(),'window_end_utc':end.isoformat(),'MP1_bps':row['MP1']*100,'MP2_bps':row['MP2']*100,'post2020':int(dt.year>=2020),'source':'Coinbase Exchange '+asset+'-USD','source_file':name,'url':requests.Request('GET',url,params=params).prepare().url,'log_return':np.nan,'window_realized_variance':np.nan}
 for attempt in range(2):
  try:
   if p.exists(): data=json.loads(p.read_bytes())
   else:
    r=requests.get(url,params=params,timeout=(10,20),headers={'User-Agent':'Academic research'}); r.raise_for_status(); data=r.json()
    assert isinstance(data,list),str(data)
    p.write_bytes(r.content); rec['retrieved_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
   rec['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
   if not data: rec['status']='no_history'; return rec
   c=pd.DataFrame(data,columns=['time','low','high','open','close','volume']).drop_duplicates('time').set_index('time').sort_index()
   first=int(start.timestamp())-60; last=int(end.timestamp())-60
   rec['n_candles']=len(c)
   if start.second or end.second or first not in c.index or last not in c.index:
    rec['status']='missing_exact_boundary'; return rec
   rec['log_return']=float(np.log(c.loc[last,'close']/c.loc[first,'close']))
   expected=pd.Index(range(first,last+1,60))
   if expected.isin(c.index).all():
    rec['window_realized_variance']=float(np.square(np.log(c.loc[expected,'close']).diff().dropna()).sum())
    rec['status']='complete'
   else: rec['status']='endpoints_only'
   return rec
  except Exception as ex:
   rec['status']='download_failed'; rec['error']=str(ex); time.sleep(1+attempt)
 return rec
if __name__=='__main__':
 rows=[]
 with ThreadPoolExecutor(max_workers=3) as pool:
  fs=[pool.submit(fetch,r,a) for _,r in e.iterrows() for a in ['BTC','ETH']]
  for i,f in enumerate(as_completed(fs),1):
   rows.append(f.result())
   if i%25==0: print('Event downloads',i,'/',len(fs),flush=True)
 d=pd.DataFrame(rows).sort_values(['event_time_utc','asset'])
 OUT.mkdir(exist_ok=True,parents=True)
 d.to_csv(OUT/'fomc_crypto_statement_windows.csv',index=False,encoding='utf-8-sig')
 print(d.groupby(['asset','status']).size().to_string(),flush=True)
