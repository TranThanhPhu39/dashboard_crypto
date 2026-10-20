"""Public Binance UTC daily klines; keep provenance and quote-currency distinction."""
from src.utils.project import *
import requests,time

def download(network=False):
    init();folder=RAW/'binance';folder.mkdir(exist_ok=True);logs=[];summary=[]
    cutoff=pd.Timestamp(config()['snapshot_end'])+pd.Timedelta(days=1)
    for symbol in ['BTCUSDT','ETHUSDT']:
        start=int(pd.Timestamp('2014-01-01',tz='UTC').timestamp()*1000);end=int(cutoff.tz_localize('UTC').timestamp()*1000)-1;allrows=[];page=0
        while start<=end:
            path=folder/f'{symbol}_{page:02d}.json';meta=path.with_suffix('.meta.json')
            if path.exists():
                rows=json.loads(path.read_bytes());record=json.loads(meta.read_text())
            elif not network:
                logs.append(dict(symbol=symbol,status='cache_missing',page=page));break
            else:
                url='https://data-api.binance.vision/api/v3/klines'
                params=dict(symbol=symbol,interval='1d',timeZone='0',startTime=start,endTime=end,limit=1000)
                try:
                    r=requests.get(url,params=params,timeout=(10,20));r.raise_for_status();rows=r.json()
                    assert isinstance(rows,list) and all(len(row)>=7 for row in rows)
                    path.write_bytes(r.content);record=dict(symbol=symbol,url=r.url,retrieved_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=sha(path),n_rows=len(rows),quote='USDT',timezone='UTC',status='ok')
                    save_json(meta,record)
                except Exception as e:
                    logs.append(dict(symbol=symbol,status='download_failed',error=str(e),page=page));break
            assert sha(path)==record['sha256'];logs.append(record)
            if not rows:break
            allrows.extend(rows);next_start=int(rows[-1][0])+86400000
            assert next_start>start;start=next_start;page+=1
            if len(rows)<1000:break
        if allrows:
            f=pd.DataFrame(dict(open_time_ms=[int(r[0]) for r in allrows],close=[float(r[4]) for r in allrows],close_time_ms=[int(r[6]) for r in allrows]))
            f['date_utc']=pd.to_datetime(f.open_time_ms,unit='ms',utc=True).dt.tz_localize(None).dt.normalize()
            f=f.sort_values('date_utc').drop_duplicates('date_utc');assert f.close.gt(0).all() and (f.close_time_ms<end+1).all()
            f['full_utc_bar']=f.close_time_ms.eq(f.open_time_ms+86399999)
            # Preserve raw closes but do not treat partial candles as UTC daily closes.
            f['log_return']=np.log(f.close.where(f.full_utc_bar)).diff();f['symbol']=symbol
            f.to_csv(PANELS/f'{symbol}_daily.csv',index=False,encoding='utf-8-sig',float_format='%.17g')
            daily=pd.read_csv(ROOT/'data/processed/daily_research_latest.csv',parse_dates=['date_utc']).set_index('date_utc')
            a=symbol[:3].lower();pair=f.set_index('date_utc')[['log_return']].join(daily[[a+'_usd_log_return']],how='inner').dropna()
            summary.append(dict(symbol=symbol,n_rows=len(f),first_date=str(f.date_utc.min().date()),last_date=str(f.date_utc.max().date()),partial_UTC_bars=int((~f.full_utc_bar).sum()),n_matched=len(pair),return_correlation=float(pair.corr().iloc[0,1]),rmse_return_difference=float(np.sqrt(np.mean((pair.iloc[:,0]-pair.iloc[:,1])**2))),complete_to_cutoff=bool(f.date_utc.max()==cutoff-pd.Timedelta(days=1))))
            csv(f.loc[~f.full_utc_bar,['symbol','date_utc','open_time_ms','close_time_ms','close']],f'{symbol}_partial_UTC_bars.csv')
    save_json(OUT/'binance_source_log.json',logs);csv(pd.DataFrame(summary),'binance_comparison.csv')
    print('Binance source comparison:',summary,flush=True)
