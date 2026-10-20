"""Complete UTC-day realized variance, lagged HAR-X, and paired volatility forecasts."""
from src.evaluation.evidence_common import *
from research_completion import MACRO,USD,PIT,PAIRS,VARIANTS
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import expit
from statsmodels.stats.multitest import multipletests
from threadpoolctl import threadpool_limits
import zipfile,itertools

OWN=['rv_lag','rv7','rv30']

def features(variant):return OWN+([] if variant.endswith('_own') else MACRO)+(USD if variant=='common_usd' else [])

def read_archive(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None;name=z.namelist()[0]
        with z.open(name) as stream:f=pd.read_csv(stream,header=None,usecols=[0,4,6],names=['open_time','close','close_time'])
    for c in f:f[c]=pd.to_numeric(f[c],errors='raise')
    scale=1_000_000 if f.open_time.min()>100_000_000_000_000 else 1000
    assert (f.close>0).all()
    valid=(f.open_time%(300*scale)==0)&((f.close_time-f.open_time)==300*scale-1)
    bad=f.loc[~valid].copy();bad['reason']='Off-grid opening time or close time differs from nominal5minute end; excluded, not repaired'
    f=f.loc[valid].copy();f['second']=(f.open_time//scale).astype('int64');assert (f.second%300==0).all()
    return f[['second','close']],('microseconds' if scale==1_000_000 else 'milliseconds'),bad

def daily_from_candles(f):
    f=f.sort_values('second').copy();assert not f.second.duplicated().any()
    t=f.second.to_numpy();close=f.close.to_numpy();r=np.r_[np.nan,np.diff(np.log(close))]
    gap=np.r_[True,np.diff(t)!=300];r[gap]=np.nan
    f['date_utc']=pd.to_datetime(t,unit='s').normalize();f['r5']=r
    take=(t%900)==600;t15=t[take];r15=np.r_[np.nan,np.diff(np.log(close[take]))];r15[np.r_[True,np.diff(t15)!=900]]=np.nan
    f['r15']=np.nan;f.loc[take,'r15']=r15
    groups=f.groupby('date_utc');rows=[]
    for day,g in groups:
        full=len(g)==288 and g.r5.notna().sum()==288 and g.r15.notna().sum()==96
        rows.append(dict(date_utc=day,n_candles=len(g),n_returns5=int(g.r5.notna().sum()),n_returns15=int(g.r15.notna().sum()),complete=full,
            rv5=float(np.sum(g.r5.to_numpy()**2)) if full else np.nan,rv15=float(np.nansum(g.r15.to_numpy()**2)) if full else np.nan,
            return_daily=float(g.r5.sum()) if full else np.nan,close=float(g.close.iloc[-1]),
            boundary_start_second=int(g.second.iloc[0])-300,boundary_end_second=int(g.second.iloc[-1])))
    out=pd.DataFrame(rows).set_index('date_utc');return out.reindex(pd.date_range(out.index.min(),out.index.max(),name='date_utc'))

def prepare():
    init();assert not (MODELS/'rv_freeze.json').exists(),'Models frozen; use new version.'
    manifest=json.loads((OUT/'rv_source_manifest.json').read_text(encoding='utf-8'));audit=[];invalid=[]
    immutable_json(OUT/'rv_quality_rule.json',dict(stage='Before RV model fitting, after source timestamp audit',rule='Reject off-grid candle opening or non-nominal close time. Preserve source bytes. Do not round timestamps or impute prices. Require complete daily5m grid and previous close for both5m and15m analysis.'))
    for asset in ['BTC','ETH']:
        frames=[]
        for md in manifest:
            if f'/{asset}/' not in md['file']:continue
            path=ROOT/md['file'];assert sha(path)==md['sha256']==md['publisher_checksum'] and sha(ROOT/md['checksum_file'])==md['checksum_sha256']
            f,unit,bad=read_archive(path);frames.append(f)
            if len(bad):invalid.append(bad.assign(file=md['file'],asset=asset))
            audit.append(dict(file=md['file'],asset=asset,rows=len(f),invalid_candles=len(bad),unit=unit,first_second=int(f.second.min()),last_second=int(f.second.max()),sha256=md['sha256']))
        d=daily_from_candles(pd.concat(frames,ignore_index=True));d.to_csv(PANELS/f'{asset}_daily_rv.csv',encoding='utf-8-sig',float_format='%.17g')
    csv(pd.DataFrame(audit),'archive_parsing_audit.csv')
    csv(pd.concat(invalid,ignore_index=True) if invalid else pd.DataFrame(columns=['open_time','close','close_time','reason','file','asset']),'invalid_source_candles.csv')
    macro=pd.read_csv(ROOT/'data/processed/forecast_origins_vintage_macro.csv',parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc')
    summary=[]
    for asset,frequency,horizon in itertools.product(['BTC','ETH'],[5,15],[1,7]):
        d=pd.read_csv(PANELS/f'{asset}_daily_rv.csv',parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc');rv=d[f'rv{frequency}'];dates=d.index
        g=pd.DataFrame(index=dates);g.index.name='origin_utc'
        g['rv_lag']=rv.shift(3);g['rv7']=rv.rolling(7,min_periods=7).mean().shift(3);g['rv30']=rv.rolling(30,min_periods=30).mean().shift(3)
        for c in MACRO+USD:g[c]=macro[c].reindex(dates-pd.Timedelta(days=3)).to_numpy()
        for c in PIT:
            for suffix in ['_pit_obs_date','_pit_vintage_date']:g[c+suffix]=macro[c+suffix].reindex(dates-pd.Timedelta(days=3)).to_numpy()
        g['actual']=rv.rolling(horizon,min_periods=horizon).sum().shift(-(horizon-1))
        g['information_day']=dates-pd.Timedelta(days=3);g['information_close']=dates-pd.Timedelta(days=2)
        g['information_cutoff']=dates-pd.Timedelta(days=1);g['label_close']=dates+pd.Timedelta(days=horizon);g['label_available']=dates+pd.Timedelta(days=horizon+1)
        g['split']=np.where(dates<'2023-01-01','train',np.where(dates<'2025-01-01','validation','test'))
        g=g.replace([np.inf,-np.inf],np.nan)
        good=g[OWN+MACRO+['actual']].notna().all(axis=1)&(g.actual>0)&(g[OWN]>0).all(axis=1)
        common=good & g[USD].notna().all(axis=1)&(pd.to_datetime(g.broad_usd_pit_vintage_date)>='2019-02-04')
        for variant in VARIANTS:
            b=g.loc[common if variant.startswith('common') else good].copy()
            b.to_csv(PANELS/f'{asset}_{frequency}_{horizon}_{variant}.csv',encoding='utf-8-sig',float_format='%.17g')
            summary.append(dict(asset=asset,sampling_minutes=frequency,horizon_days=horizon,variant=variant,n_rows=len(b),first_origin=str(b.index.min()),last_origin=str(b.index.max()),train=int((b.split=='train').sum()),validation=int((b.split=='validation').sum()),test=int((b.split=='test').sum()),n_features=len(features(variant))))
    csv(pd.DataFrame(summary),'rv_sample_summary.csv')
    lock_inputs('rv_analysis_lock.json',[OUT/'rv_source_manifest.json',OUT/'archive_parsing_audit.csv',ROOT/'data/processed/forecast_origins_vintage_macro.csv']+list(PANELS.glob('*_daily_rv.csv'))+list(PANELS.glob('*_own.csv'))+list(PANELS.glob('*_macro.csv'))+list(PANELS.glob('*_usd.csv')))
    print(pd.DataFrame(summary).to_string(index=False),flush=True)

def panel(asset,freq,horizon,variant):
    return pd.read_csv(PANELS/f'{asset}_{freq}_{horizon}_{variant}.csv',parse_dates=['origin_utc','information_day','information_close','information_cutoff','label_close','label_available'],float_precision='round_trip').set_index('origin_utc')

def qlike(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float);assert np.isfinite(p).all() and (p>0).all()
    return np.log(p)+y/p

def har_fit(train,columns):
    X=train[columns].to_numpy().copy();X[:,:3]=np.log(X[:,:3]);mu=X.mean(axis=0);sd=X.std(axis=0,ddof=0);sd[sd==0]=1
    Z=np.column_stack([np.ones(len(X)),(X-mu)/sd]);y=np.log(train.actual.to_numpy());b,_,rank,_=np.linalg.lstsq(Z,y,rcond=None);res=y-Z@b;smear=float(np.exp(res).mean())
    return dict(columns=columns,mean=mu.tolist(),scale=sd.tolist(),coefficients=b.tolist(),smearing=smear,rank=int(rank),nobs=len(train),last_label_available=str(train.label_available.max()),first_training_origin=str(train.index.min()),last_training_origin=str(train.index.max()))

def har_predict(model,frame):
    X=frame[model['columns']].to_numpy().copy();X[:,:3]=np.log(X[:,:3]);X=(X-np.array(model['mean']))/np.array(model['scale'])
    p=np.exp(np.column_stack([np.ones(len(X)),X])@np.array(model['coefficients']))*model['smearing'];assert np.isfinite(p).all() and (p>0).all();return p

def monthly(frame,variant,window,split,store=None):
    selected=frame[frame.split.eq(split)];rows=[]
    if split=='validation':
        first_test=frame.index[frame.split.eq('test')].min()
        selected=selected[selected.label_available<=first_test-pd.Timedelta(days=1)]
    for month,test in selected.groupby(selected.index.to_period('M')):
        origin=test.index.min();train=frame[frame.label_available<=origin-pd.Timedelta(days=1)]
        if window:train=train[train.index>=origin-pd.Timedelta(days=window)]
        assert len(train)>=100,'Insufficient past labels; no fallback to future labels'
        model=har_fit(train,features(variant));model.update(refit_origin=str(origin),window_calendar_days=window,split=split,variant=variant)
        assert pd.Timestamp(model['last_label_available'])<=origin-pd.Timedelta(days=1)
        pred=har_predict(model,test)
        if store is not None:store.append(model)
        rows.extend(dict(origin_utc=date,actual=float(y),predicted=float(p),last_label_available=model['last_label_available'],refit_origin=str(origin)) for date,y,p in zip(test.index,test.actual,pred))
    return pd.DataFrame(rows)

def garch_filter(r,omega,alpha,beta,initial):
    r=np.asarray(r,float);h=np.empty(len(r));h[0]=initial;pos=1
    bad=np.flatnonzero(~np.isfinite(r[:-1]))+1
    for end in np.r_[bad,len(r)]:
        if end>pos:
            inp=omega+alpha*r[pos-1:end-1]**2
            h[pos:end]=lfilter([1.],[1.,-beta],inp,zi=[beta*h[pos-1]])[0]
        if end<len(r):h[end]=omega+(alpha+beta)*h[end-1]
        pos=end+1
    assert np.isfinite(h).all() and (h>0).all();return h

def garch_fit(returns):
    r=returns.to_numpy()*100;initial=float(np.nanmean(r[:100]**2));assert initial>0
    def transform(theta):
        pers=.999*expit(theta[1]);share=expit(theta[2]);return np.exp(theta[0]),pers*share,pers*(1-share)
    def objective(theta):
        o,a,b=transform(theta);h=garch_filter(r,o,a,b,initial);good=np.isfinite(r);return .5*float(np.sum(np.log(h[good])+r[good]**2/h[good]))
    fits=[]
    for alpha,beta in [(.05,.9),(.1,.8)]:
        pers=(alpha+beta)/.999;share=alpha/(alpha+beta);start=[np.log(initial*(1-alpha-beta)),np.log(pers/(1-pers)),np.log(share/(1-share))]
        opt=minimize(objective,start,method='L-BFGS-B',bounds=[(-20,15),(-8,8),(-8,8)],options={'maxiter':300,'ftol':1e-10})
        if opt.success and np.isfinite(opt.fun):fits.append(opt)
    assert fits,'No converged GARCH optimizer; no silent forecast replacement'
    best=min(fits,key=lambda x:x.fun);o,a,b=transform(best.x)
    return dict(omega=float(o),alpha=float(a),beta=float(b),initial_variance=initial,negative_log_likelihood=float(best.fun),optimizer_success=True,n_observed=int(np.isfinite(r).sum()),last_return_day=str(returns.index.max()))

def garch_predict(model,returns,origin,horizon):
    known=returns.loc[:origin-pd.Timedelta(days=3)];r=known.to_numpy()*100;m=model;h=garch_filter(r,m['omega'],m['alpha'],m['beta'],m['initial_variance'])
    future=m['omega']+m['alpha']*r[-1]**2+m['beta']*h[-1];values=[future]
    for step in range(1,horizon+2):values.append(m['omega']+(m['alpha']+m['beta'])*values[-1])
    return float(np.sum(values[2:horizon+2])/10000)

def benchmarks(asset):
    daily=pd.read_csv(PANELS/f'{asset}_daily_rv.csv',parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc');returns=daily.return_daily
    # Parameters only use available returns by the first eligible forecast of each month.
    dates=sorted(set().union(*(set(panel(asset,f,h,v).query("split != 'train'").index) for f,h,v in itertools.product([5,15],[1,7],VARIANTS))))
    dates=pd.DatetimeIndex(dates);rows=[];models=[];ewma={};state=float(returns.dropna().iloc[:100].pow(2).mean())
    for day,value in returns.items():
        if pd.notna(value):state=.94*state+.06*value**2
        ewma[day]=state
    for month,origin_group in pd.Series(dates,index=dates).groupby(dates.to_period('M')):
        origin=origin_group.min();known=returns.loc[:origin-pd.Timedelta(days=3)];model=garch_fit(known);model.update(asset=asset,refit_origin=str(origin));models.append(model)
        for day in origin_group:
            for freq,h in itertools.product([5,15],[1,7]):
                info=day-pd.Timedelta(days=3);rv=daily[f'rv{freq}'].reindex(pd.date_range(info-pd.Timedelta(days=29),info))
                if not rv.notna().all() or info not in ewma or pd.isna(returns.loc[info]):continue
                for name,value in [('trailing30',h*float(rv.mean())),('ewma',h*ewma[info]),('garch11',garch_predict(model,returns,day,h))]:rows.append(dict(asset=asset,sampling_minutes=freq,horizon_days=h,origin_utc=day,model=name,predicted=value,information_day=info))
        if len(models)%12==0:print('GARCH benchmark refits:',asset,len(models),flush=True)
    return pd.DataFrame(rows),models

def fit():
    init();verify_lock('rv_analysis_lock.json');assert not (MODELS/'rv_freeze.json').exists(),'RV fits already frozen'
    predictions=[];selected=[];search=[];models=[];benchmodels=[]
    with threadpool_limits(limits=2):
        for asset in ['BTC','ETH']:
            bench,bmodels=benchmarks(asset);benchmodels.extend(bmodels)
            for freq,h,variant in itertools.product([5,15],[1,7],VARIANTS):
                frame=panel(asset,freq,h,variant);choices=[]
                for window in config()['rv']['windows_calendar_days']:
                    val=monthly(frame,variant,window,'validation');score=float(qlike(val.actual,val.predicted).mean());choices.append((score,window));search.append(dict(asset=asset,sampling_minutes=freq,horizon_days=h,variant=variant,window=window,validation_qlike=score,n_validation=len(val)))
                score,window=min(choices,key=lambda x:x[0]);selected.append(dict(asset=asset,sampling_minutes=freq,horizon_days=h,variant=variant,window=window,validation_qlike=score))
                stored=[];test=monthly(frame,variant,window,'test',stored)
                for m in stored:m.update(asset=asset,sampling_minutes=freq,horizon_days=h)
                models.extend(stored)
                test=test.assign(asset=asset,sampling_minutes=freq,horizon_days=h,variant=variant,model='har_x' if not variant.endswith('_own') else 'har')
                predictions.append(test)
                for name,g in bench[(bench.sampling_minutes==freq)&(bench.horizon_days==h)].groupby('model'):
                    b=test[['asset','sampling_minutes','horizon_days','variant','origin_utc','actual']].merge(g[['origin_utc','predicted']],on='origin_utc',how='left',validate='one_to_one');assert b.predicted.notna().all()
                    b['model']=name;predictions.append(b)
                print('RV monthly forecasts:',asset,freq,h,variant,'window',window,flush=True)
    pred=pd.concat(predictions,ignore_index=True);assert (pred.predicted>0).all() and np.isfinite(pred.predicted).all()
    csv(pred,'rv_test_predictions.csv');csv(pd.DataFrame(search),'rv_validation_search.csv');csv(pd.DataFrame(selected),'rv_selected_windows.csv')
    save_json(MODELS/'har_monthly_models.json',models);save_json(MODELS/'garch_monthly_models.json',benchmodels)
    metrics=[]
    for key,g in pred.groupby(['asset','sampling_minutes','horizon_days','variant','model']):metrics.append(dict(zip(['asset','sampling_minutes','horizon_days','variant','model'],key),n_test=len(g),qlike=float(qlike(g.actual,g.predicted).mean()),mse=float(np.mean((g.actual-g.predicted)**2))))
    csv(pd.DataFrame(metrics),'rv_forecast_metrics.csv')
    comparisons(pred)
    save_json(MODELS/'rv_freeze.json',dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),config_sha256=sha(CONFIG),analysis_lock_sha256=sha(OUT/'rv_analysis_lock.json'),har_models_sha256=sha(MODELS/'har_monthly_models.json'),garch_models_sha256=sha(MODELS/'garch_monthly_models.json'),test_predictions_sha256=sha(OUT/'rv_test_predictions.csv'),historical_status='Exploratory; test previously viewed; not future predictive confirmation'))

def calendar_bootstrap_means(frame,draws=999,seed=9020):
    frame=frame.reindex(pd.date_range(frame.index.min(),frame.index.max(),name='origin_utc'));values=frame.to_numpy(float);mask=np.isfinite(values);safe=np.nan_to_num(values,nan=0.);rng=np.random.default_rng(seed);n=len(frame);out=[]
    for b in range(draws):
        starts=rng.integers(0,n,size=int(np.ceil(n/30)));ix=((starts[:,None]+np.arange(30))%n).ravel()[:n];count=mask[ix].sum(axis=0);assert (count>0).all();out.append(safe[ix].sum(axis=0)/count)
    return np.array(out)

def comparison_row(a,b,**meta):
    z=a[['origin_utc','actual','predicted']].merge(b[['origin_utc','actual','predicted']],on='origin_utc',suffixes=('_base','_added'),validate='one_to_one').sort_values('origin_utc')
    assert len(z)==len(a)==len(b) and np.array_equal(z.actual_base.to_numpy(),z.actual_added.to_numpy())
    d=qlike(z.actual_added,z.predicted_added)-qlike(z.actual_base,z.predicted_base);g=pd.DataFrame({'difference':d},index=pd.DatetimeIndex(z.origin_utc));boot=calendar_bootstrap_means(g)[:,0];mean=float(np.mean(d));centered=boot-mean
    p=(1+np.sum(abs(centered)>=abs(mean)))/(1+len(boot));lo,hi=np.quantile(boot,[.025,.975])
    return dict(meta,n_pairs=len(z),mean_loss_added_minus_base=mean,lower95=lo,upper95=hi,pvalue=float(p),bootstrap_calendar_block=30)

def comparisons(pred):
    if 'origin_utc' in pred:pred=pred.copy();pred['origin_utc']=pd.to_datetime(pred.origin_utc)
    ablation=[];bench=[];mcs=[];mcslog=[]
    for key,g in pred.groupby(['asset','sampling_minutes','horizon_days']):
        meta=dict(zip(['asset','sampling_minutes','horizon_days'],key));learned=g[g.model.isin(['har','har_x'])]
        for left,right in PAIRS:
            ablation.append(comparison_row(learned[learned.variant==left],learned[learned.variant==right],**meta,base=left,added=right))
        for variant in VARIANTS:
            for name in ['trailing30','ewma','garch11']:bench.append(comparison_row(g[(g.variant==variant)&g.model.eq(name)],learned[learned.variant==variant],**meta,variant=variant,benchmark=name))
        # MCS uses the exact common origin intersection for all five learned and3 benchmark forecasts.
        parts=[]
        for v in VARIANTS:
            s=learned[learned.variant==v].set_index('origin_utc');parts.append(pd.Series(qlike(s.actual,s.predicted),index=s.index,name=v))
        for name in ['trailing30','ewma','garch11']:
            s=g[g.variant.eq('long_own')&g.model.eq(name)].set_index('origin_utc');parts.append(pd.Series(qlike(s.actual,s.predicted),index=s.index,name=name))
        loss=pd.concat(parts,axis=1).dropna();bm=calendar_bootstrap_means(loss);mean=loss.mean().to_numpy();active=list(range(len(loss.columns)));steps=[]
        while len(active)>1:
            delta=mean[active,None]-mean[None,active];bs=bm[:,active,None]-bm[:,None,active];se=bs.std(axis=0,ddof=1);np.fill_diagonal(se,np.inf)
            se=np.where(se==0,np.inf,se);observed=float(np.max(abs(delta/se)));sim=np.max(abs((bs-delta)/se),axis=(1,2));p=float((1+(sim>=observed).sum())/(1+len(sim)))
            worst=int(np.argmax(np.max(delta/se,axis=1)));removed=loss.columns[active[worst]] if p<.1 else ''
            mcslog.append(dict(meta,step=len(steps),pvalue=p,removed=removed,n_active=len(active)));steps.append(p)
            if p>=.1:break
            active.pop(worst)
        for i,name in enumerate(loss.columns):mcs.append(dict(meta,model=name,retained90=i in active,n_common=len(loss),interpretation='MCS membership is not proof of superiority to a retained benchmark'))
    for rows,name in [(ablation,'rv_ablation_tests.csv'),(bench,'rv_benchmark_tests.csv')]:
        f=pd.DataFrame(rows);f['qvalue_bh']=multipletests(f.pvalue,method='fdr_bh')[1];csv(f,name)
    csv(pd.DataFrame(mcs),'rv_model_confidence_sets.csv');csv(pd.DataFrame(mcslog),'rv_mcs_steps.csv')
    save_json(OUT/'rv_inference_method.json',dict(ablation_family=len(ablation),benchmark_family=len(bench),mcs_families=8,bootstrap_draws=999,calendar_block_days=30,seed=9020,
        loss='QLIKE=log(predicted variance)+actual/predicted, common-date paired comparisons; mean added-minus-base<0 is favorable. Percentile intervals and centered two-sided bootstrap p-values are approximate under weak dependence/stability.',
        mcs='90% MCS range statistic, sequentially removes the largest standardized relative loss; joint resampling of common-date losses. A retained macro model with retained benchmark does not establish a win.',
        limitations='Historical market/crypto files retrospective; macro date-level vintages and24h buffer do not certify whole-feed PIT. No Clark-West adjustment for QLIKE. All forecasts exploratory; no selected test winner deployed.'))
