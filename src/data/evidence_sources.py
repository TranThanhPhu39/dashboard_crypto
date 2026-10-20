"""Immutable public downloads with timestamp/unit audit and published archive checksums."""
from src.evaluation.evidence_common import *
import requests,time,hashlib,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed

BS_URL='https://www.frbsf.org/wp-content/uploads/monetary-policy-surprises-data.xlsx?2026-10-16='

def fetch(path,url):
    meta=Path(str(path)+'.meta.json');path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        m=json.loads(meta.read_text(encoding='utf-8'));assert sha(path)==m['sha256'] and m['url']==url;return m
    for attempt in range(4):
        try:
            r=requests.get(url,timeout=(15,50),headers={'User-Agent':'Mozilla/5.0 academic research'});r.raise_for_status()
            m=dict(file=path.relative_to(ROOT).as_posix(),url=url,retrieved_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),http_status=r.status_code,http_date=r.headers.get('Date'),last_modified=r.headers.get('Last-Modified'),sha256=hashlib.sha256(r.content).hexdigest(),bytes=len(r.content))
            with path.open('xb') as f:f.write(r.content)
            save_json(meta,m);return m
        except Exception:
            if attempt==3:raise
            time.sleep(1+attempt)

def preflight():
    init();m=fetch(RAW/'bauer_swanson.xlsx',BS_URL)
    book=pd.ExcelFile(ROOT/m['file']);summary={}
    for sheet in book.sheet_names:
        g=pd.read_excel(book,sheet_name=sheet,header=None);summary[sheet]=dict(shape=list(g.shape),first_rows=[[str(v) if pd.notna(v) else '' for v in row] for row in g.head(12).to_numpy()])
    save_json(OUT/'bs_workbook_audit.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    for asset,stamp in [('BTC','2017-08'),('BTC','2025-01'),('ETH','2026-09')]:archive(asset,stamp,monthly=True)

def archive(asset,stamp,monthly=True):
    period='monthly' if monthly else 'daily';name=f'{asset}USDT-5m-{stamp}.zip'
    url=f'https://data.binance.vision/data/spot/{period}/klines/{asset}USDT/5m/{name}'
    path=RAW/'binance_5m'/asset/name;m=fetch(path,url);cm=fetch(Path(str(path)+'.CHECKSUM'),url+'.CHECKSUM')
    expected=Path(str(path)+'.CHECKSUM').read_text(encoding='ascii').split()[0]
    assert len(expected)==64 and sha(path)==expected,'Publisher checksum mismatch'
    with zipfile.ZipFile(path) as z:assert z.testzip() is None and len(z.namelist())==1
    return dict(m,publisher_checksum=expected,checksum_file=cm['file'],checksum_sha256=cm['sha256'])

def rv_archives():
    init();jobs=[(a,d.strftime('%Y-%m'),True) for a in ['BTC','ETH'] for d in pd.date_range('2017-08-01','2026-09-01',freq='MS')]
    jobs.extend((a,d.strftime('%Y-%m-%d'),False) for a in ['BTC','ETH'] for d in pd.date_range('2026-10-01','2026-10-15'))
    rows=[];errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks={pool.submit(archive,a,s,monthly=m):(a,s) for a,s,m in jobs}
        for i,f in enumerate(as_completed(tasks),1):
            try:rows.append(f.result())
            except Exception as exc:errors.append(dict(asset=tasks[f][0],period=tasks[f][1],error=str(exc)))
            if i%25==0:print('Binance source archives:',i,'/',len(jobs),flush=True)
    save_json(OUT/'rv_download_errors.json',errors);assert not errors,'Source errors saved; no fitting'
    save_json(OUT/'rv_source_manifest.json',sorted(rows,key=lambda r:r['file']));print('Archive checksums verified:',len(rows),flush=True)

def minute_one(asset,date,event,kind):
    if kind=='placebo':
        local=event.tz_convert('America/New_York').tz_localize(None)-pd.Timedelta(days=7)
        at=local.tz_localize('America/New_York').tz_convert('UTC');before,after=-10,20
    else:at=event;before,after=-70,20
    params=dict(granularity=60,start=(at+pd.Timedelta(minutes=before-1)).isoformat(),end=(at+pd.Timedelta(minutes=after)).isoformat())
    url=requests.Request('GET',f'https://api.exchange.coinbase.com/products/{asset}-USD/candles',params=params).prepare().url
    path=RAW/'coinbase_minutes'/f'{asset}_{date}_{kind}.json';m=fetch(path,url)
    return dict(m,asset=asset,date=date,kind=kind,window_time_utc=at.isoformat())

def minutes():
    init();g=pd.read_csv(OLD/'event_audit.csv');g=g[g.primary_joint].copy();logs=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(minute_one,r.asset,r.date,pd.Timestamp(r.event_time_utc),kind) for r in g.itertuples() for kind in ['actual','placebo']]
        for i,f in enumerate(as_completed(tasks),1):
            logs.append(f.result())
            if i%25==0:print('Coinbase event/placebo snapshots:',i,'/',len(tasks),flush=True)
    save_json(OUT/'minute_source_manifest.json',sorted(logs,key=lambda r:(r['asset'],r['date'],r['kind'])))
