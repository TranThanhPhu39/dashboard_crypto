"""Reconstruct date-level ALFRED information directly from archived spells.

Never imports build_dataset.py (which has mutating module-level code).
The oracle changes values, not which observations were historically known.
"""
from src.evaluation.pit_nested_common import *
from research_completion import MACRO, USD, PIT, VARIANTS, features, own
import io, zipfile

SERIES = {'DTWEXBGS':('broad_usd','log'), 'DGS2':('us2y','bps'),
          'DGS10':('us10y','bps'), 'DFF':('fed_funds','bps'),
          'DCOILWTICO':('oil_wti','log'), 'NFCI':('nfci','level')}

def delta(a,b,kind):
    if not np.isfinite(a) or not np.isfinite(b):return np.nan
    if kind=='log':return np.log(b/a) if a>0 and b>0 else np.nan
    return (b-a)*(100 if kind=='bps' else 1)

def spell_at(raw, sid, date):
    """Independent interval query; retain NaN withdrawals before selection."""
    g=raw[(raw.realtime_start_date<=date)&
          (raw.realtime_end_date.isna() | (raw.realtime_end_date>=date))&
          (raw.period_start_date<=date)]
    assert not g.period_start_date.duplicated().any(), ('Overlapping spells',sid,date)
    return g.dropna(subset=[sid]).sort_values('period_start_date').tail(2)

def latest_values(raw,sid):
    # Keep latest missing records as missing, never resurrect a withdrawn value.
    return raw[raw.realtime_start_date<=pd.Timestamp(config()['snapshot_end'])].sort_values(
        ['period_start_date','realtime_start_date']).drop_duplicates('period_start_date',keep='last').set_index('period_start_date')[sid]

def same_numeric(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    return bool(np.all(np.isclose(a,b,rtol=6e-12,atol=6e-15,equal_nan=True)))

def source_file(name):
    return ROOT/'data/raw'/name

def raw_market():
    market={}
    v=pd.read_csv(source_file('VIXCLS_fred.csv'),parse_dates=['observation_date'])
    s=pd.to_numeric(v.set_index('observation_date').VIXCLS,errors='coerce').dropna()
    market['vix_change_lag1_proxy']=s.diff()
    for filename,c in [('sp500_yahoo.json','sp500'),('gold_yahoo.json','gold_futures')]:
        d=json.loads(source_file(filename).read_text(encoding='utf-8'))['chart']['result'][0]
        idx=pd.to_datetime(d['timestamp'],unit='s',utc=True).tz_convert(d['meta']['exchangeTimezoneName']).tz_localize(None).normalize()
        s=pd.Series(d['indicators']['quote'][0]['close'],index=idx)
        s=s[~s.index.duplicated(keep='last')].dropna()
        market[c+'_log_return_lag1_proxy']=np.log(s).diff()
    return market

def prepare():
    init();check_protected()
    assert not (MODELS/'freeze.json').exists(), 'Panels frozen; validate instead of rewriting'
    f=pd.read_csv(ROOT/config()['historical_source'],parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc')
    assert f.index.equals(pd.date_range(f.index.min(),f.index.max(),name='date_utc'))
    checks=[]; details=[]; revision=[]; evidence=[]
    latest=f.copy(); reconstructed=pd.DataFrame(index=f.index)
    def check(name,ok,detail=''):
        checks.append(dict(check=name,passed=bool(ok),detail=detail))
        assert ok,(name,detail)
    # Source receipt is a snapshot fact, not evidence of historical availability.
    log=json.loads((ROOT/'data/source_log.json').read_text(encoding='utf-8'))
    logrows=log if isinstance(log,list) else log.get('sources',[])
    def receipt(name):
        matches=[r for r in logrows if str(r.get('file','')).replace('\\','/').endswith(name)]
        return matches[-1].get('retrieved_at_utc','not recorded') if matches else 'not recorded'
    for sid,(c,kind) in SERIES.items():
        path=source_file(sid+'_alfred_realtime.zip')
        with zipfile.ZipFile(path) as z:
            name=next(n for n in z.namelist() if n.endswith('.csv'))
            raw=pd.read_csv(io.BytesIO(z.read(name)),na_values=['.'])
        for col in ['period_start_date','realtime_start_date','realtime_end_date']:
            raw[col]=pd.to_datetime(raw[col])
        raw[sid]=pd.to_numeric(raw[sid],errors='coerce')
        stored=pd.read_csv(ROOT/f'data/processed/{sid}_vintage_periods.csv',float_precision='round_trip')
        check(sid+'_raw_stored_spell_values',len(stored)==len(raw) and same_numeric(stored[sid],raw[sid]))
        for col in ['period_start_date','realtime_start_date','realtime_end_date']:
            check(sid+'_raw_stored_'+col, pd.to_datetime(stored[col]).fillna(pd.Timestamp('1900-01-01')).equals(raw[col].fillna(pd.Timestamp('1900-01-01'))))
        lv=latest_values(raw,sid); starts=np.sort(raw.realtime_start_date.unique()); rows=[]; raw_sha=sha(path)
        for date in f.index:
            g=spell_at(raw,sid,date)
            obs=list(g.period_start_date); vals=g[sid].to_numpy(); last=vals[-1] if len(vals) else np.nan
            previous=vals[-2] if len(vals)==2 else np.nan
            observed=obs[-1] if obs else pd.NaT
            vintage=pd.Timestamp(starts[np.searchsorted(starts,np.datetime64(date),side='right')-1]) if np.searchsorted(starts,np.datetime64(date),side='right') else pd.NaT
            newer=[lv.get(o,np.nan) for o in obs]
            oracle= newer[-1] if newer else np.nan
            oraclechange=delta(newer[-2],newer[-1],kind) if len(newer)==2 else np.nan
            aschange=delta(previous,last,kind) if len(vals)==2 else np.nan
            rows.append([last,aschange,observed,vintage,oracle,oraclechange])
            details.append(dict(series=sid,information_date=date,previous_observation_date=obs[-2] if len(obs)==2 else pd.NaT,
                observation_date=observed,selected_record_revision_date=g.realtime_start_date.iloc[-1] if len(g) else pd.NaT,
                source_last_update_date=vintage,assumed_available_utc=date+pd.Timedelta(days=2),
                asof_value=last,asof_change=aschange,latest_same_observation_value=oracle,latest_same_observation_change=oraclechange,
                source_sha256=raw_sha))
        q=pd.DataFrame(rows,index=f.index,columns=['value','change','obs','vintage','latest_value','latest_change'])
        reconstructed[c+'_pit']=q.value;reconstructed[c+'_pit_change']=q.change
        for dest,src in [(c+'_pit','value'),(c+'_pit_change','change')]:
            check(dest+'_independent_reconstruction',same_numeric(f[dest],q[src]))
        for suffix,col in [('_pit_obs_date','obs'),('_pit_vintage_date','vintage')]:
            check(c+suffix+'_independent_reconstruction',pd.to_datetime(f[c+suffix]).fillna(pd.Timestamp('1900-01-01')).equals(q[col].fillna(pd.Timestamp('1900-01-01'))))
        used=c+'_pit' if kind=='level' else c+'_pit_change'
        oracle=q.latest_value if kind=='level' else q.latest_change
        latest[used]=oracle.map(lambda v:float(format(v,'.12g')) if np.isfinite(v) else np.nan)
        valid=f[used].notna()&latest[used].notna(); diff=latest.loc[valid,used]-f.loc[valid,used]
        material=~np.isclose(latest.loc[valid,used],f.loc[valid,used],rtol=6e-12,atol=6e-15)
        revision.append(dict(feature=used,series=sid,n_asof=int(f[used].notna().sum()),n_paired=int(valid.sum()),
            n_materially_revised=int(material.sum()),mean_absolute_revision=float(abs(diff).mean()),max_absolute_revision=float(abs(diff).max()),
            first_archived_vintage=str(raw.realtime_start_date.min().date()),first_feature_date=str(f[used].first_valid_index().date())))
        evidence.append(dict(feature=used,asset='both',source='ALFRED '+sid,raw_path=path.relative_to(ROOT).as_posix(),sha256=sha(path),
            retrieved_at_utc=receipt(path.name),observation_rule='Last two nonmissing active observation spells at information date; NFCI uses last level',
            transformation='level' if kind=='level' else '100*(current-previous) bps' if kind=='bps' else 'log(current/previous), both >0',
            availability_rule='Date-level vintage <= I; assumed usable I+2 00UTC; D3/D4 at origin',
            verification='verified_date_level_asof',remaining_assumption='Exact historical provider intraday publication/receipt not observed; +24h delivery assumption',
            special_limit='No USD before vintage 2019-02-04' if sid=='DTWEXBGS' else 'Weekly release and revisions preserved' if sid=='NFCI' else 'DFF change is not policy surprise' if sid=='DFF' else 'WTI nonpositive pairs missing' if sid=='DCOILWTICO' else 'Yield change is not identified monetary shock'))
        print('Raw PIT reconstructed:',sid,flush=True)
    # Crypto complete-grid reconstruction, independent of source feature columns.
    fullcal=pd.date_range('2013-12-01',config()['snapshot_end'])
    for asset in ['btc','eth']:
        path=source_file(asset+'_coinmetrics.json'); raw=pd.DataFrame(json.loads(path.read_text(encoding='utf-8'))['data'])
        idx=pd.to_datetime(raw.time,utc=True).dt.tz_localize(None).dt.normalize()
        check(asset+'_unique_raw_dates',not idx.duplicated().any())
        s=pd.Series(pd.to_numeric(raw.PriceUSD,errors='coerce').to_numpy(),index=idx).reindex(fullcal)
        r=np.log(s).diff(); sq=r*r; vol=np.sqrt(365*sq.rolling(30,min_periods=30).mean())
        for col,x,formula in zip(own(asset),[r,sq,vol],['log(P_I/P_(I-1))','r_I squared','sqrt(365*mean(last 30 squared daily returns))']):
            check(col+'_raw_reconstruction',same_numeric(f[col],x.reindex(f.index)))
            evidence.append(dict(feature=col,asset=asset,source='Coin Metrics PriceUSD',raw_path=path.relative_to(ROOT).as_posix(),sha256=sha(path),retrieved_at_utc=receipt(path.name),observation_rule='Daily date I denotes UTC close I+1 00UTC; no gap bridging',transformation=formula,availability_rule='Assumed I+2 00UTC; use I=D-3 or D-4',verification='assumed_historical_delivery_and_revision_stability',remaining_assumption='Retrospective snapshot; historical revisions and actual release times not archived',special_limit='Daily squared return/RMS, not intraday realized variance'))
        check(asset+'_target_raw',same_numeric(f[asset+'_target_next_return'],r.reindex(f.index).shift(-1)))
        check(asset+'_squared_target_raw',same_numeric(f[asset+'_target_next_squared_return'],sq.reindex(f.index).shift(-1)))
    market=raw_market()
    for col,s in market.items():
        # Frozen source trims to Jan 2014 before creating its market lag. The
        # first calendar row is intentionally missing, even if Dec 2013 exists.
        expected=s.reindex(f.index).shift(1)
        check(col+'_raw_reconstruction',same_numeric(f[col],expected))
        name='VIXCLS_fred.csv' if col.startswith('vix') else 'sp500_yahoo.json' if col.startswith('sp500') else 'gold_yahoo.json'
        path=source_file(name)
        evidence.append(dict(feature=col,asset='both',source='FRED VIXCLS' if col.startswith('vix') else 'Yahoo daily unadjusted close',raw_path=path.relative_to(ROOT).as_posix(),sha256=sha(path),retrieved_at_utc=receipt(name),observation_rule='Local session date I-1; timestamp is daily bar timestamp, not release/receipt time',transformation='session difference' if col.startswith('vix') else 'log return between nonmissing local sessions',availability_rule='Market day D-4 for D3; D-5 for D4. No fill of market returns.',verification='assumed_historical_delivery_and_revision_stability',remaining_assumption='Historical feed revisions/actual receipt not archived; fixed buffer is an assumption',special_limit='Continuous GC=F affected by contract rolls' if col.startswith('gold') else 'Price index, no dividends' if col.startswith('sp500') else 'Change in VIX points'))
    csv(pd.DataFrame(evidence),'feature_evidence.csv');csv(pd.DataFrame(details),'macro_row_lineage.csv')
    csv(pd.DataFrame(revision),'revision_magnitude.csv');csv(pd.DataFrame(checks),'reconstruction_checks.csv')
    pd.DataFrame(reconstructed).to_csv(PANELS/'independent_macro_reconstruction.csv',encoding='utf-8-sig',float_format='%.17g')
    counts=[];panel_audit=[]
    scenarios=config()['scenarios']
    for asset in ['btc','eth']:
        bases={}
        for scenario,source,lag in [('native_asof_d3',f,2),('matched_asof_d3',f,2),('matched_latest_d3',latest,2),('matched_asof_d4',f,3)]:
            shifted=source.shift(lag)
            b=shifted[own(asset)+MACRO+USD].copy();b.index=b.index+pd.Timedelta(days=1);b.index.name='origin_utc'
            b['information_date']=b.index-pd.Timedelta(days=lag+1)
            b['information_close_utc']=b.information_date+pd.Timedelta(days=1)
            b['assumed_available_utc']=b.information_date+pd.Timedelta(days=2)
            b['label_close_utc']=b.index+pd.Timedelta(days=1);b['label_assumed_available_utc']=b.index+pd.Timedelta(days=2)
            b['actual_return']=f[asset+'_target_next_return'].to_numpy();b['actual_squared_return']=f[asset+'_target_next_squared_return'].to_numpy()
            for c in PIT:
                for suffix in ['_pit_obs_date','_pit_vintage_date']:
                    b[c+suffix]=shifted[c+suffix].to_numpy()
            bases[scenario]=b.replace([np.inf,-np.inf],np.nan)
        masks={}
        for scenario,b in bases.items():
            ok=b[own(asset)+MACRO+['actual_return','actual_squared_return']].notna().all(axis=1)
            masks[scenario,'long']=ok
            masks[scenario,'common']=ok&b[USD].notna().all(axis=1)&(pd.to_datetime(b.broad_usd_pit_vintage_date)>='2019-02-04')
        for variant in VARIANTS:
            family='long' if variant.startswith('long') else 'common'
            shared=masks['matched_asof_d3',family]&masks['matched_latest_d3',family]&masks['matched_asof_d4',family]
            for scenario in scenarios:
                b=bases[scenario];mask=masks[scenario,family] if scenario.startswith('native') else shared
                g=b.loc[mask].copy(); cols=features(asset,variant)
                meta=[c for c in g if c not in own(asset)+MACRO+USD]
                g=g[cols+meta]
                check(asset+variant+scenario+'_available_before_origin',bool((g.assumed_available_utc<=g.index-pd.Timedelta(days=1)).all()))
                for c in PIT:
                    dates=pd.to_datetime(g[c+'_pit_vintage_date']);obs=pd.to_datetime(g[c+'_pit_obs_date'])
                    ok=dates.isna()|((dates<=g.information_date)&(obs<=g.information_date))
                    check(asset+variant+scenario+c+'_no_future_vintage_or_observation',bool(ok.all()))
                g.to_csv(PANELS/f'{asset}_{variant}_{scenario}.csv',encoding='utf-8-sig',float_format='%.17g')
                counts.append(dict(asset=asset,variant=variant,scenario=scenario,n=len(g),first_origin=str(g.index.min()),last_origin=str(g.index.max()),outer_n=int((g.index>='2023-01-01').sum()),n_features=len(cols)))
                if scenario=='native_asof_d3':
                    old=pd.read_csv(ROOT/f'data/processed/latency_20261019/{asset}_{variant}.csv',parse_dates=['origin_utc'],float_precision='round_trip').set_index('origin_utc')
                    check(asset+variant+'_matches_frozen_latency_panel',g.index.equals(old.index) and same_numeric(g[cols],old[cols]) and same_numeric(g.actual_return,old.actual_return))
                panel_audit.append(dict(asset=asset,variant=variant,scenario=scenario,minimum_buffer_hours=float(((g.index-g.assumed_available_utc).dt.total_seconds()/3600).min()),
                    macro_max_observation_age_days=max(int((g.information_date-pd.to_datetime(g[c+'_pit_obs_date'])).dt.days.max()) for c in PIT if g[c+'_pit_obs_date'].notna().any())))
    csv(pd.DataFrame(checks),'reconstruction_checks.csv');csv(pd.DataFrame(counts),'sample_summary.csv');csv(pd.DataFrame(panel_audit),'panel_timing_audit.csv')
    save_json(OUT/'audit_summary.json',dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),checks=len(checks),passed=sum(r['passed'] for r in checks),
        feature_definitions=len(evidence),lineage_rows=len(details),code_timing_violations_detected=0,
        conclusion='Date-level reconstruction passed. Historical receipt and market/crypto revision stability remain assumptions, not certified PIT.',protected_files=check_protected()))
    inputs=[CONFIG,ROOT/config()['historical_source'],ROOT/'research_completion.py',ROOT/'src/models/latency.py',ROOT/'src/evaluation/pit_feature_audit.py',ROOT/'src/evaluation/pit_nested_common.py']
    inputs+=sorted(PANELS.glob('*.csv'))
    save_json(OUT/'prepared_input_lock.json',dict(files={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}))
    print(pd.DataFrame(counts).to_string(index=False),flush=True)
