"""Archive actual public responses now; never reconstruct historical availability."""
from src.evaluation.robustness_common import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import requests

SERIES = ['VIXCLS','DTWEXBGS','DGS2','DGS10','DFF','SP500','DCOILWTICO','NFCI']

def utc_now():
    return pd.Timestamp.now(tz='UTC')

def earliest_origin(captured):
    """First midnight meeting actual capture+24h, inclusive at exact midnight."""
    return (pd.Timestamp(captured)+pd.Timedelta(hours=24)).ceil('D')

def fetch_one(folder, name, url):
    began=utc_now()
    record=dict(file=(folder/name).relative_to(ROOT).as_posix(),url=url,request_started_utc=began.isoformat())
    try:
        response=requests.get(url,timeout=(12,35),headers={'User-Agent':'Mozilla/5.0 (academic prospective research)'})
        received=utc_now()
        response.raise_for_status()
        b=response.content
        path=folder/name
        # Retain even unexpected content for an auditable failed response.
        with path.open('xb') as stream:stream.write(b)
        record.update(retrieved_at_utc=received.isoformat(),available_at_utc=received.isoformat(),
                      sha256=sha(path),bytes=len(b),http_status=response.status_code,
                      http_date=response.headers.get('Date'),last_modified=response.headers.get('Last-Modified'))
        if name.endswith('.csv'):
            f=pd.read_csv(BytesIO(b));assert len(f.columns)==2 and len(f)>0,'Unexpected CSV layout'
            dates=pd.to_datetime(f.iloc[:,0],errors='raise')
            values=pd.to_numeric(f.iloc[:,1],errors='coerce')
            ok=values.notna();assert ok.any(),'No numeric observations'
            record.update(latest_observation_date=str(dates[ok].max().date()),numeric_observations=int(ok.sum()))
        else:
            obj=json.loads(b)
            if 'coinmetrics' in name:
                f=pd.DataFrame(obj['data']);values=pd.to_numeric(f.PriceUSD,errors='coerce')
                dates=pd.to_datetime(f.time,utc=True);ok=values.notna();assert ok.any()
                assert not obj.get('next_page_url'),'Pagination requires an explicit subsequent capture'
                record.update(latest_observation_date=str(dates[ok].max().date()),numeric_observations=int(ok.sum()))
            else:
                result=obj['chart']['result'][0]
                assert result['timestamp'] and result['indicators']['quote'][0]['close']
                dates=pd.to_datetime(result['timestamp'],unit='s',utc=True)
                record.update(latest_observation_date=str(dates.max().date()),numeric_observations=len(dates))
        record['status']='ok'
    except Exception as exc:
        record.update(status='failed',error=f'{type(exc).__name__}: {exc}',finished_utc=utc_now().isoformat())
    return record

def collect():
    init();started=utc_now()
    folder=RAW/'live'/started.strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    end=(started.normalize()-pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    start=(started.normalize()-pd.Timedelta(days=180)).strftime('%Y-%m-%d')
    sources={f'{s}_fred.csv':f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}&cosd={start}&coed={end}' for s in SERIES}
    sources.update({f'{a}_coinmetrics.json':f'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={a}&metrics=PriceUSD&frequency=1d&start_time={start}&end_time={end}&page_size=10000' for a in ['btc','eth']})
    p1=int((started.normalize()-pd.Timedelta(days=180)).timestamp());p2=int(started.normalize().timestamp())
    sources['gold_yahoo.json']=f'https://query2.finance.yahoo.com/v8/finance/chart/GC%3DF?period1={p1}&period2={p2}&interval=1d'
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(fetch_one,folder,name,url) for name,url in sources.items()]):
            row=future.result();rows.append(row);print(Path(row['file']).name,row['status'],row.get('latest_observation_date',row.get('error','')),flush=True)
    records=sorted(rows,key=lambda r:r['file'])
    finished=utc_now()
    # This is a local observation of availability, never an ALFRED vintage backfill.
    manifest=dict(capture_started_utc=started.isoformat(),capture_finished_utc=finished.isoformat(),
                  provenance='New current-vintage public responses archived prospectively; local retrieval timestamps are not historical publication timestamps.',
                  sources=records)
    save_json(folder/'manifest.json',manifest)
    successes=[r for r in records if r['status']=='ok']
    eligible=earliest_origin(max(pd.Timestamp(r['available_at_utc']) for r in successes)) if successes else None
    next_origin=finished.ceil('D')
    cutoff=next_origin-pd.Timedelta(hours=24)
    status=dict(capture_manifest=(folder/'manifest.json').relative_to(ROOT).as_posix(),manifest_sha256=sha(folder/'manifest.json'),
                status='CAPTURED; NO ELIGIBLE FROZEN-CONVENTION FORECAST LOGGED',
                sources_ok=len(successes),sources_total=len(records),next_origin_utc=next_origin.isoformat(),
                required_information_cutoff_utc=cutoff.isoformat(),
                earliest_origin_using_this_capture_24h=eligible.isoformat() if eligible is not None else None,
                snapshot_meets_next_origin_buffer=bool(successes and all(pd.Timestamp(r['available_at_utc'])<=cutoff for r in successes)),
                predictions_logged=0,
                reason='First actual capture is later than next-origin cutoff. An older captured snapshot at a later origin may also have stale own-feature dates: do not silently alter frozen lags. Exact prospective publication latency requires a separately approved timing protocol before deployment.',
                deployment='No scheduler installed. Capture manually each day; preserve failures and missing days. Existing envelope logger remains available for independently evidenced eligible inputs.',
                evaluation='No new OOS score: future outcomes and sufficient eligible predictions do not yet exist.')
    save_json(OUT/'prospective_capture_status.json',status)
    print(json.dumps(status,ensure_ascii=False,indent=2))
    return status
