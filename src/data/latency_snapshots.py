"""Actual-receipt snapshots, including requested ALFRED information-day vintages."""
from src.evaluation.latency_common import *
from src.data.prospective_snapshots import fetch_one
from concurrent.futures import ThreadPoolExecutor,as_completed
from io import BytesIO
import requests,re,zipfile,subprocess,urllib.parse
from email.parser import Parser

PIT_SERIES={'DTWEXBGS':('broad_usd','log'),'DGS2':('us2y','bps'),'DGS10':('us10y','bps'),
            'DFF':('fed_funds','bps'),'DCOILWTICO':('oil_wti','log'),'NFCI':('nfci','diff')}

def now():return pd.Timestamp.now(tz='UTC')

def alfred_frame(path,sid,asof):
    """Same within-vintage observation definition as the historical feature panel."""
    with zipfile.ZipFile(path) as z:
        name=next(n for n in z.namelist() if n.endswith('obs._by_real-time_period.csv'))
        f=pd.read_csv(BytesIO(z.read(name)),na_values=['.'])
    for c in ['period_start_date','realtime_start_date','realtime_end_date']:
        f[c]=pd.to_datetime(f[c],errors='coerce')
    f[sid]=pd.to_numeric(f[sid],errors='coerce');d=pd.Timestamp(asof)
    f=f[(f.period_start_date<=d)&(f.realtime_start_date<=d)&(f.realtime_end_date.isna()|(f.realtime_end_date>=d))]
    f=f.sort_values(['period_start_date','realtime_start_date']).drop_duplicates('period_start_date',keep='last')
    return f.dropna(subset=[sid])

def alfred_one(folder,sid,asof):
    url=f'https://alfred.stlouisfed.org/series/downloaddata?seid={sid}'
    prefix=f'{sid}_vintage_{asof}';start=now()
    record=dict(source='alfred',series_id=sid,requested_vintage_date=asof,url=url,request_started_utc=start.isoformat())
    try:
        session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0 (academic prospective research)'})
        form=session.get(url,timeout=(12,30));form.raise_for_status()
        formfile=folder/(prefix+'_form.html');formfile.write_bytes(form.content)
        text=form.text;last=re.search(r'id="form_obs_end_date"[^>]*value="([^"]+)"',text).group(1)
        fields=[('form[units]','lin'),('form[obs_start_date]',str((pd.Timestamp(asof)-pd.Timedelta(days=180)).date())),
                ('form[obs_end_date]',min(last,asof)),('form[entered_vintage_dates]',asof),
                ('form[file_type]','1'),('form[file_format]','csv'),('form[download_data]','')]
        for tag in re.findall(r'<input\b[^>]*>',text):
            if 'type="hidden"' in tag:
                n=re.search(r'name="([^"]+)"',tag);v=re.search(r'value="([^"]*)"',tag)
                if n:fields.append((n.group(1),v.group(1) if v else ''))
        requestfile=folder/(prefix+'_request.json');save_json(requestfile,fields)
        # Use the same curl form-download path as the frozen ALFRED downloader;
        # requests POST is disconnected by this host/network while GET succeeds.
        bodyfile=folder/(prefix+'_body.txt');bodyfile.write_text(urllib.parse.urlencode(fields),encoding='ascii')
        headerfile=folder/(prefix+'_headers.txt');path=folder/(prefix+'.zip')
        call=subprocess.run(['curl.exe','-f','-sS','-L','--max-time','45','--dump-header',str(headerfile),'--data-binary','@'+str(bodyfile),'-o',str(path),url],capture_output=True,text=True,timeout=50)
        received=now();assert call.returncode==0,call.stderr
        headerblock=headerfile.read_text(encoding='iso-8859-1').replace('\r\n','\n').strip().split('\n\n')[-1]
        headers=Parser().parsestr('\n'.join(headerblock.splitlines()[1:]))
        record.update(file=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size,
                      available_at_utc=received.isoformat(),retrieved_at_utc=received.isoformat(),http_status=200,
                      http_date=headers.get('Date'),last_modified=headers.get('Last-Modified'),
                      request_file=requestfile.relative_to(ROOT).as_posix(),request_sha256=sha(requestfile),
                      form_file=formfile.relative_to(ROOT).as_posix(),form_sha256=sha(formfile))
        assert path.read_bytes()[:2]==b'PK','Not a ZIP response'
        f=alfred_frame(path,sid,asof);assert len(f)>=2,'Fewer than two observations in requested vintage'
        record.update(status='ok',latest_observation_date=str(f.period_start_date.max().date()),numeric_observations=len(f))
    except Exception as exc:record.update(status='failed',error=f'{type(exc).__name__}: {exc}',finished_utc=now().isoformat())
    return record

def collect():
    init();started=now();folder=RAW/'live'/started.strftime('%Y%m%dT%H%M%S%fZ');folder.mkdir(parents=True,exist_ok=False)
    origin=started.normalize()+pd.Timedelta(days=1);info_dates=[str((origin-pd.Timedelta(days=k)).date()) for k in [3,2]]
    start=str((started.normalize()-pd.Timedelta(days=180)).date());end=str((started.normalize()-pd.Timedelta(days=1)).date())
    sources={f'{s}_fred.csv':f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}&cosd={start}&coed={end}' for s in ['VIXCLS']}
    sources.update({f'{a}_coinmetrics.json':f'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={a}&metrics=PriceUSD&frequency=1d&start_time={start}&end_time={end}&page_size=10000' for a in ['btc','eth']})
    p1=int((started.normalize()-pd.Timedelta(days=180)).timestamp());p2=int(started.normalize().timestamp())
    for name,symbol in [('gold','GC%3DF'),('sp500','%5EGSPC')]:
        sources[name+'_yahoo.json']=f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={p1}&period2={p2}&interval=1d'
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks=[pool.submit(fetch_one,folder,name,url) for name,url in sources.items()]
        tasks += [pool.submit(alfred_one,folder,sid,date) for date in info_dates for sid in PIT_SERIES]
        for future in as_completed(tasks):
            row=future.result();rows.append(row);print(Path(row.get('file',row.get('series_id','unknown'))).name,row['status'],row.get('latest_observation_date',row.get('error','')),flush=True)
    manifest=dict(capture_started_utc=started.isoformat(),capture_finished_utc=now().isoformat(),
                  method='Actual public response receipt; exact requested date-level ALFRED vintages; current-vintage crypto/market snapshots archived now, no historical publication certification',
                  information_dates=info_dates,sources=sorted(rows,key=lambda r:r.get('file',r.get('series_id',''))))
    save_json(folder/'manifest.json',manifest)
    save_json(OUT/'latest_capture.json',dict(manifest=(folder/'manifest.json').relative_to(ROOT).as_posix(),sha256=sha(folder/'manifest.json'),sources_ok=sum(r['status']=='ok' for r in rows),sources_total=len(rows)))
    return folder/'manifest.json'
