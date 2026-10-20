"""Build auditable feature envelopes; log only genuinely ex-ante eligible forecasts."""
from src.evaluation.latency_common import *
from src.data.latency_snapshots import PIT_SERIES,alfred_frame
from src.models.latency import MACRO,USD,VARIANTS,features,model_predict
from threadpoolctl import threadpool_limits
import joblib,os

def clock(origin,receipt,current):
    origin=pd.Timestamp(origin);receipt=pd.Timestamp(receipt);current=pd.Timestamp(current)
    assert all(t.tzinfo is not None for t in [origin,receipt,current]),'UTC-aware timestamps required'
    origin=origin.tz_convert('UTC')
    assert origin==origin.normalize(),'Origin must be UTC midnight'
    assert current<origin<=current+pd.Timedelta(days=1),'Must log before origin, within next24h'
    assert receipt<=origin-pd.Timedelta(hours=24),'Actual source receipt exceeds cutoff24h'

def records():
    out=[]
    for path in sorted((RAW/'live').glob('*/manifest.json')):
        obj=json.loads(path.read_text(encoding='utf-8'))
        for r in obj['sources']:
            if r['status']!='ok':continue
            p=(ROOT/r['file']).resolve();assert p.is_relative_to(ROOT.resolve()) and sha(p)==r['sha256']
            if r.get('request_file'):assert sha(ROOT/r['request_file'])==r['request_sha256']
            out.append(dict(r,manifest=path.relative_to(ROOT).as_posix(),manifest_sha256=sha(path)))
    return out

def choose(rows,predicate,info,cutoff):
    candidates=[r for r in rows if predicate(r) and pd.Timestamp(r['available_at_utc'])>=info+pd.Timedelta(days=1)
                and pd.Timestamp(r['available_at_utc'])<=cutoff]
    assert candidates,'No matching snapshot received after information-day close and by cutoff24h'
    return min(candidates,key=lambda r:pd.Timestamp(r['available_at_utc']))

def prices(record,asset):
    f=pd.DataFrame(json.loads((ROOT/record['file']).read_bytes())['data'])
    d=pd.to_datetime(f.time,utc=True).dt.tz_localize(None).dt.normalize()
    s=pd.Series(pd.to_numeric(f.PriceUSD,errors='coerce').to_numpy(),index=d)
    assert s.index.is_unique and (s.dropna()>0).all();return s.sort_index()

def market_series(record):
    path=ROOT/record['file']
    if path.suffix=='.csv':
        f=pd.read_csv(path);s=pd.Series(pd.to_numeric(f.iloc[:,1],errors='coerce').to_numpy(),index=pd.to_datetime(f.iloc[:,0]))
    else:
        f=json.loads(path.read_bytes())['chart']['result'][0]
        dates=pd.to_datetime(f['timestamp'],unit='s',utc=True).tz_convert(f['meta']['exchangeTimezoneName']).tz_localize(None).normalize()
        s=pd.Series(f['indicators']['quote'][0]['close'],index=dates,dtype=float)
        s=s.loc[~s.index.duplicated(keep='last')]
    return s.dropna().sort_index()

def envelope(origin,asset,rows):
    origin=pd.Timestamp(origin).tz_convert('UTC');info=origin-pd.Timedelta(days=3);cutoff=origin-pd.Timedelta(days=1)
    day=info.tz_localize(None);market_day=day-pd.Timedelta(days=1)
    values={};lineage={};missing={}
    def set_value(name,value,r,**meta):
        assert np.isfinite(value),f'Nonfinite {name}'
        values[name]=float(value);lineage[name]=dict(source_file=r['file'],source_sha256=r['sha256'],available_at_utc=r['available_at_utc'],manifest=r['manifest'],manifest_sha256=r['manifest_sha256'],information_day=str(day.date()),**meta)
    try:
        r=choose(rows,lambda q:Path(q['file']).name==asset+'_coinmetrics.json',info,cutoff)
        s=prices(r,asset).reindex(pd.date_range(day-pd.Timedelta(days=30),day));assert s.notna().all(),'Missing crypto day; do not bridge/fill'
        returns=np.log(s).diff().iloc[1:];value=float(returns.iloc[-1])
        for name,value2 in [(asset+'_usd_log_return',value),(asset+'_squared_return',value**2),(asset+'_vol30_annualized',np.sqrt(365*np.mean(returns.to_numpy()**2)))]:
            set_value(name,value2,r,observation_day=str(day.date()),window_start=str(s.index[0].date()),window_end=str(day.date()),declared_close_utc=(info+pd.Timedelta(days=1)).isoformat())
    except (AssertionError,KeyError,ValueError) as exc:missing['own_crypto']=str(exc)
    for name,filename,trans in [('vix_change_lag1_proxy','VIXCLS_fred.csv','diff'),('sp500_log_return_lag1_proxy','sp500_yahoo.json','log'),('gold_futures_log_return_lag1_proxy','gold_yahoo.json','log')]:
        try:
            r=choose(rows,lambda q:Path(q['file']).name==filename,info,cutoff);s=market_series(r)
            change=s.diff() if trans=='diff' else np.log(s.where(s>0)).diff()
            assert market_day in change.index and pd.notna(change.loc[market_day]),'Exact market observation day missing; no return carry'
            set_value(name,change.loc[market_day],r,observation_day=str(market_day.date()),transformation=trans)
        except (AssertionError,KeyError,ValueError) as exc:missing[name]=str(exc)
    for sid,(name,trans) in PIT_SERIES.items():
        feature=name+'_pit' if name=='nfci' else name+'_pit_change'
        try:
            r=choose(rows,lambda q:q.get('series_id')==sid and q.get('requested_vintage_date')==str(day.date()),info,cutoff)
            f=alfred_frame(ROOT/r['file'],sid,str(day.date()));assert len(f)>=2
            a,b=f[sid].iloc[-2:].to_numpy()
            value=b if name=='nfci' else np.log(b/a) if trans=='log' and a>0 and b>0 else (b-a)*100 if trans=='bps' else b-a if trans=='diff' else np.nan
            set_value(feature,value,r,requested_vintage_date=str(day.date()),observation_day=str(f.period_start_date.iloc[-1].date()),previous_observation_day=str(f.period_start_date.iloc[-2].date()),transformation='level' if name=='nfci' else trans)
        except (AssertionError,KeyError,ValueError,StopIteration) as exc:missing[feature]=str(exc)
    base=features(asset,'long_macro');common=features(asset,'common_usd')
    return dict(asset=asset,origin_utc=origin.isoformat(),information_cutoff_utc=cutoff.isoformat(),information_day=str(day.date()),feature_shift_calendar_days=2,
                features=values,lineage=lineage,missing=missing,long_eligible=all(c in values for c in base),common_eligible=all(c in values for c in common),
                provenance='Local actual-receipt evidence; source publication time is not independently certified')

def frozen():
    f=json.loads((MODELS/'freeze.json').read_text(encoding='utf-8'))
    assert f['config_sha256']==sha(CONFIG) and f['inventory_sha256']==sha(OUT/'model_inventory.csv') and f['benchmark_states_sha256']==sha(OUT/'benchmark_states.csv')
    inventory=pd.read_csv(OUT/'model_inventory.csv')
    assert len(inventory)==40 and all(sha(ROOT/r.file)==r.sha256 for r in inventory.itertuples())
    return inventory,f

def immutable(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        f.write(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False));f.flush();os.fsync(f.fileno())

def protocol():
    inventory,freeze=frozen();p=LIVE/'protocol.json'
    obj=dict(version=VERSION,config_sha256=sha(CONFIG),inventory_sha256=freeze['inventory_sha256'],benchmark_states_sha256=freeze['benchmark_states_sha256'],
             **config()['prospective'],historical_interpretation='Previously inspected test remains exploratory; extra lag does not establish causality or whole-feed historical PIT')
    if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==obj,'Protocol cannot change after freezing'
    else:immutable(p,obj)
    return obj

def forecast(origin=None):
    init();current=pd.Timestamp.now(tz='UTC');origin=pd.Timestamp(origin) if origin else current.normalize()+pd.Timedelta(days=1)
    assert origin.tzinfo is not None;origin=origin.tz_convert('UTC')
    prot=protocol();clock(origin,origin-pd.Timedelta(days=1),current)
    assert pd.Timestamp(prot['start_utc'])<=origin<pd.Timestamp(prot['end_utc_exclusive'])
    rows=records();inventory,_=frozen();states=pd.read_csv(OUT/'benchmark_states.csv');attempt=[]
    for asset in ['btc','eth']:
        env=envelope(origin,asset,rows);stamp=pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%S%fZ')
        envpath=LIVE/'envelopes'/f'{origin.date()}_{asset}_{stamp}.json';immutable(envpath,env)
        predictions=[]
        with threadpool_limits(limits=2):
            for variant in VARIANTS:
                if not env['long_eligible'] or (not variant.startswith('long') and not env['common_eligible']):continue
                cols=features(asset,variant);x=pd.DataFrame([[env['features'][c] for c in cols]],columns=cols)
                for c in cols:clock(origin,pd.Timestamp(env['lineage'][c]['available_at_utc']),pd.Timestamp.now(tz='UTC'))
                for target in ['return','squared_return']:
                    state=states[(states.asset==asset)&(states.variant==variant)&(states.target==target)].iloc[0]
                    assert pd.Timestamp(state.last_fit_label_available).tz_localize('UTC')<=origin-pd.Timedelta(days=1)
                    for kind in ['historical_mean','natural_benchmark','elastic_net','gradient_boosting']:
                        digest=None
                        if kind in ['elastic_net','gradient_boosting']:
                            r=inventory[(inventory.asset==asset)&(inventory.variant==variant)&(inventory.target==target)&(inventory.model==kind)].iloc[0]
                            payload=joblib.load(ROOT/r.file);assert payload['features']==cols and payload['config_sha256']==sha(CONFIG)
                            value=float(model_predict(payload['fitted'],x,kind,target)[0]);digest=r.sha256
                        else:value=float(state.historical_mean) if kind=='historical_mean' else 0. if target=='return' else env['features'][asset+'_vol30_annualized']**2/365
                        assert np.isfinite(value) and (target!='squared_return' or value>0)
                        predictions.append(dict(variant=variant,target=target,model=kind,predicted=value,model_sha256=digest))
        if predictions:
            # Check the wall clock again after all model computations, before commit.
            logged=pd.Timestamp.now(tz='UTC');clock(origin,origin-pd.Timedelta(days=1),logged)
            path=LIVE/'predictions'/f'{origin.date()}_{asset}.json'
            immutable(path,dict(asset=asset,origin_utc=origin.isoformat(),target_end_utc=(origin+pd.Timedelta(days=1)).isoformat(),logged_at_utc=logged.isoformat(),envelope=envpath.relative_to(ROOT).as_posix(),envelope_sha256=sha(envpath),protocol_sha256=sha(LIVE/'protocol.json'),predictions=predictions))
        attempt.append(dict(asset=asset,origin_utc=origin.isoformat(),long_eligible=env['long_eligible'],common_eligible=env['common_eligible'],predictions_logged=len(predictions),missing=env['missing'],envelope=envpath.relative_to(ROOT).as_posix()))
    obj=dict(attempted_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),origin_utc=origin.isoformat(),attempts=attempt,total_predictions=sum(r['predictions_logged'] for r in attempt),performance='Not evaluated; no future labels or confirmed predictive skill claimed')
    immutable(LIVE/'attempts'/f'{current.strftime("%Y%m%dT%H%M%S%fZ")}.json',obj);save_json(OUT/'prospective_status.json',obj)
    print(json.dumps(obj,ensure_ascii=False,indent=2));return obj

def labels():
    init();current=pd.Timestamp.now(tz='UTC');rows=records();saved=0;pending=[]
    for file in sorted((LIVE/'predictions').glob('*.json')):
        obj=json.loads(file.read_text(encoding='utf-8'));origin=pd.Timestamp(obj['origin_utc']);asset=obj['asset'];dest=LIVE/'labels'/file.name
        if dest.exists():continue
        earliest=origin+pd.Timedelta(days=2)
        try:
            assert current>=earliest,'Label close+24h has not elapsed'
            choices=[r for r in rows if Path(r['file']).name==asset+'_coinmetrics.json' and pd.Timestamp(r['available_at_utc'])>=earliest and pd.Timestamp(r['available_at_utc'])<=current]
            assert choices,'No actual label snapshot after close+24h'
            day=origin.tz_localize(None);r=None;s=None
            for candidate in sorted(choices,key=lambda q:pd.Timestamp(q['available_at_utc'])):
                candidate_prices=prices(candidate,asset)
                if day in candidate_prices.index and day-pd.Timedelta(days=1) in candidate_prices.index and pd.notna(candidate_prices.loc[day]) and pd.notna(candidate_prices.loc[day-pd.Timedelta(days=1)]):
                    r=candidate;s=candidate_prices;break
            assert r is not None,'No label snapshot contains both required crypto dates'
            value=float(np.log(s.loc[day])-np.log(s.loc[day-pd.Timedelta(days=1)]))
            immutable(dest,dict(asset=asset,origin_utc=origin.isoformat(),actual_return=value,actual_squared_return=value**2,captured_at_utc=r['available_at_utc'],source_file=r['file'],source_sha256=r['sha256'],prediction_sha256=sha(file)))
            saved+=1
        except (AssertionError,KeyError) as exc:pending.append(dict(file=file.name,reason=str(exc)))
    save_json(OUT/'label_status.json',dict(labels_saved=saved,pending=pending));print('Actual labels saved:',saved,'pending:',len(pending))

def evaluate():
    init();prot=protocol();current=pd.Timestamp.now(tz='UTC')
    if current<pd.Timestamp(prot['end_utc_exclusive'])+pd.Timedelta(days=1):
        obj=dict(status='PENDING_FIXED_EVALUATION_WINDOW',fixed_end_utc=prot['end_utc_exclusive'],earliest_full_label_review_utc=(pd.Timestamp(prot['end_utc_exclusive'])+pd.Timedelta(days=1)).isoformat(),performance_claim=False)
        save_json(OUT/'prospective_evaluation.json',obj);print(json.dumps(obj));return
    from src.models.latency import comparisons
    from research_completion import PAIRS,paired_stat
    from statsmodels.stats.multitest import multipletests
    observations=[]
    for p in sorted((LIVE/'predictions').glob('*.json')):
        labelpath=LIVE/'labels'/p.name
        if not labelpath.exists():continue
        forecast=json.loads(p.read_text(encoding='utf-8'));label=json.loads(labelpath.read_text(encoding='utf-8'))
        assert label['prediction_sha256']==sha(p) and sha(ROOT/label['source_file'])==label['source_sha256']
        for r in forecast['predictions']:
            observations.append(dict(date_utc=forecast['origin_utc'],asset=forecast['asset'],actual=label['actual_'+r['target']],**r))
    f=pd.DataFrame(observations);csv(f,'prospective_observed_predictions.csv');ablation=[];bench=[]
    import itertools
    for asset,target,kind in itertools.product(['btc','eth'],['return','squared_return'],['elastic_net','gradient_boosting']):
        for left,right in PAIRS:
            # Merge keys explicitly; comparisons use only paired, actually logged dates.
            a=f[(f.asset==asset)&(f.target==target)&(f.model==kind)&(f.variant==left)] if len(f) else pd.DataFrame()
            b=f[(f.asset==asset)&(f.target==target)&(f.model==kind)&(f.variant==right)] if len(f) else pd.DataFrame()
            ablation.append(_paired_live(a,b,asset,target,kind,dict(base=left,added=right),paired_stat))
        for variant in VARIANTS:
            ref='historical_mean' if target=='return' else 'natural_benchmark'
            a=f[(f.asset==asset)&(f.target==target)&(f.model==ref)&(f.variant==variant)] if len(f) else pd.DataFrame()
            b=f[(f.asset==asset)&(f.target==target)&(f.model==kind)&(f.variant==variant)] if len(f) else pd.DataFrame()
            bench.append(_paired_live(a,b,asset,target,kind,dict(variant=variant,benchmark=ref),paired_stat))
    for records_,name in [(ablation,'prospective_ablation_tests.csv'),(bench,'prospective_benchmark_tests.csv')]:
        g=pd.DataFrame(records_);g['qvalue_bh']=multipletests(g.pvalue.fillna(1),method='fdr_bh')[1];g.loc[g.pvalue.isna(),'qvalue_bh']=np.nan;csv(g,name)
    save_json(OUT/'prospective_evaluation.json',dict(status='FIXED_WINDOW_REVIEW',observed_prediction_rows=len(f),missing_labels=len(list((LIVE/'predictions').glob('*.json')))-len(list((LIVE/'labels').glob('*.json'))),attempt_files=len(list((LIVE/'attempts').glob('*.json'))),interpretation='Report coverage and paired uncertainty; finite-sample and time-dependence limitations remain. A fixed window alone never guarantees skill.'))

def _paired_live(a,b,asset,target,kind,extra,paired_stat):
    row=dict(asset=asset,target=target,model=kind,**extra)
    if not len(a) or not len(b):return dict(row,n_pairs=0,pvalue=None,status='insufficient paired forecasts')
    dates=sorted(set(a.date_utc)&set(b.date_utc));a=a[a.date_utc.isin(dates)].sort_values('date_utc');b=b[b.date_utc.isin(dates)].sort_values('date_utc')
    if len(a)<2:return dict(row,n_pairs=len(a),pvalue=None,status='insufficient paired forecasts')
    return dict(row,status='approximate paired diagnostic',**paired_stat(a,b,target))
