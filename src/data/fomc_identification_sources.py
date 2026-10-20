"""Frozen public author snapshot and Coinbase daily candles; never overwrite old caches."""
from src.evaluation.fomc_identification_common import *
import requests,hashlib
from concurrent.futures import ThreadPoolExecutor,as_completed

AUTHOR='https://api.github.com/repos/marekjarocinski/jkshocks_update_fed/commits/main'
AUTHOR_FILES=['README.md','code/main.m','code/signrestr_median.m','code/mypc.m','source_data/fomc_surprises_jk.csv','shocks_fed_jk_t.csv']

def author():
    init();folder=RAW/'author';folder.mkdir(exist_ok=True);manifest=folder/'manifest.json'
    if manifest.exists():
        obj=json.loads(manifest.read_text(encoding='utf-8'))
        assert all(sha(ROOT/r['file'])==r['sha256'] for r in obj['sources']);return obj
    response=requests.get(AUTHOR,timeout=(12,35),headers={'User-Agent':'Academic crypto research'});response.raise_for_status()
    revision=response.json()['sha'];(folder/'commit.json').write_bytes(response.content);rows=[]
    for name in AUTHOR_FILES:
        url=f'https://raw.githubusercontent.com/marekjarocinski/jkshocks_update_fed/{revision}/{name}'
        r=requests.get(url,timeout=(12,35));r.raise_for_status();path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(r.content)
        rows.append(dict(file=path.relative_to(ROOT).as_posix(),url=url,sha256=sha(path),retrieved_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),bytes=len(r.content)))
    obj=dict(repository='marekjarocinski/jkshocks_update_fed',commit=revision,captured_utc=pd.Timestamp.now(tz='UTC').isoformat(),sources=rows,
             attribution='Jarocinski and Karadi (2020), DOI10.1257/mac.20180090; maintained update by the authors. Source/final data CC BY4.0; code BSD3-Clause per repository README. Raw code retained for provenance; local implementation independently written.')
    save_json(manifest,obj);print('Author snapshot pinned:',revision,flush=True);return obj

def daily_asset(asset):
    folder=RAW/'coinbase_daily'/asset;folder.mkdir(parents=True,exist_ok=True)
    start=pd.Timestamp(config()['sample'][0],tz='UTC')-pd.Timedelta(days=35)
    end=pd.Timestamp(config()['sample'][1],tz='UTC')+pd.Timedelta(days=1)
    logs=[];frames=[]
    while start<end:
        stop=min(start+pd.Timedelta(days=290),end)
        path=folder/f'{start.strftime("%Y%m%d")}_{stop.strftime("%Y%m%d")}.json';meta=path.with_suffix('.meta.json')
        params=dict(granularity=86400,start=start.isoformat(),end=stop.isoformat())
        url=requests.Request('GET',f'https://api.exchange.coinbase.com/products/{asset}-USD/candles',params=params).prepare().url
        if not path.exists():
            r=requests.get(url,timeout=(12,35),headers={'User-Agent':'Academic crypto event study'});r.raise_for_status();obj=r.json();assert isinstance(obj,list)
            path.write_bytes(r.content);save_json(meta,dict(file=path.relative_to(ROOT).as_posix(),url=url,retrieved_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),sha256=sha(path),granularity=86400))
        record=json.loads(meta.read_text(encoding='utf-8'));assert sha(path)==record['sha256'] and record['url']==url;logs.append(record)
        values=json.loads(path.read_bytes());assert isinstance(values,list)
        f=pd.DataFrame(values,columns=['time','low','high','open','close','volume'])
        if len(f):
            assert not f.time.duplicated().any() and (f.time%86400==0).all() and (f.close>0).all()
            f=f[(f.time>=start.timestamp())&(f.time<stop.timestamp())];frames.append(f)
        start=stop
    g=pd.concat(frames,ignore_index=True).sort_values('time') if frames else pd.DataFrame(columns=['time','low','high','open','close','volume'])
    assert not g.time.duplicated().any()
    g['date_utc']=pd.to_datetime(g.time,unit='s',utc=True).dt.tz_localize(None)
    g.to_csv(PANELS/f'{asset}_Coinbase_daily.csv',index=False,encoding='utf-8-sig',float_format='%.17g')
    print(asset,'Coinbase UTC daily candles:',len(g),str(g.date_utc.min()),str(g.date_utc.max()),flush=True)
    return logs

def collect():
    init();author();logs=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(daily_asset,a) for a in ['BTC','ETH']]):logs.extend(future.result())
    save_json(OUT/'daily_source_log.json',logs)
