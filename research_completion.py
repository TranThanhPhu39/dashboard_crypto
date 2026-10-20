"""Approved timing, macro ablation and positive-variance extension; frozen prior work."""
from research_common import *
import argparse
import datetime
import hashlib
import itertools
import warnings
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import ElasticNet
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

OUT = RESULTS/'completion'
MACRO = ['vix_change_lag1_proxy','us2y_pit_change','us10y_pit_change',
         'fed_funds_pit_change','sp500_log_return_lag1_proxy',
         'gold_futures_log_return_lag1_proxy','oil_wti_pit_change','nfci_pit']
USD = ['broad_usd_pit_change']
PIT = ['broad_usd','us2y','us10y','fed_funds','oil_wti','nfci']
VARIANTS = ['long_own','long_macro','common_own','common_macro','common_usd']
PAIRS = [('long_own','long_macro'),('common_own','common_macro'),
         ('common_macro','common_usd'),('common_own','common_usd')]
KINDS = ['historical_mean','natural_benchmark','elastic_net','gradient_boosting']
GRIDS = {
    'elastic_net':[dict(alpha=a,l1_ratio=l) for a,l in itertools.product([.001,.01,.1],[.1,.9])],
    'gradient_boosting':[dict(max_leaf_nodes=l,l2_regularization=r) for l,r in itertools.product([7,15],[1.,10.])],
}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(name, obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str,allow_nan=False),encoding='utf-8')
def csv(frame, name): frame.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.17g')
def protected():
    files = list((ROOT/'data').rglob('*'))+list(RESULTS.rglob('*'))+list((ROOT/'notebooks').rglob('*'))+list(ROOT.glob('topic09*.zip'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file() and OUT not in p.parents}
def own(asset): return [asset+'_usd_log_return',asset+'_squared_return',asset+'_vol30_annualized']
def features(asset,variant):
    return own(asset)+([] if variant.endswith('_own') else MACRO)+(USD if variant=='common_usd' else [])


def prepare():
    OUT.mkdir(exist_ok=True); (OUT/'panels').mkdir(exist_ok=True); (OUT/'figures').mkdir(exist_ok=True)
    design = dict(
        version='timing-macro-positive-variance-v1',locked_before_fits=True,
        interpretation='Exploratory extension: the 2025+ test has previously been inspected. No new untouched test is claimed.',
        snapshot_end='2026-10-15',origin='row t: 00:00 UTC t+1',
        target='UTC day t+1, [00:00 t+1,00:00 t+2); return and squared return',
        timing='Shift ALL original feature and PIT metadata columns by one CALENDAR day before complete-case selection. At row t use original information row t-1, whose reference close is 00:00 t, giving a 24-hour buffer. Existing market lag1 proxies become two-calendar-day proxies.',
        labels='Training/development labels require label close +24 hours <= first validation/test origin; purge boundary labels otherwise.',
        availability_limit='The 24h buffer is a conservative assumption, not observed publication timestamps. Retrospective PriceUSD and revised market proxies remain; no fully real-time certification.',
        samples='long: own and macro WITHOUT USD on identical complete cases. common 2019+: own, macro WITHOUT USD, macro WITH USD on identical complete cases. No imputation/carrying market returns.',
        features={a:{v:features(a,v) for v in VARIANTS} for a in ['btc','eth']},
        split=dict(train='target date before 2023',validation='target date 2023-2024',test='target date 2025 onward; exploratory'),
        grids=GRIDS,model_order=KINDS,selection='Minimum validation MSE for return, QLIKE for squared return; first listed wins ties. Refit once on available train+validation; no test tuning.',
        fixed_boosting=dict(max_iter=200,learning_rate=.05,min_samples_leaf=30,early_stopping=False,random_state=9),
        positive_variance=dict(gradient_boosting='Poisson quasi-deviance with log link, y scaled by fitting-sample mean; no prediction floor.',
            elastic_net='Fit standardized log(y / fitting_mean + 1e-12); retransformation exp(prediction) times fitting-residual smearing mean times fitting_mean. No prediction floor; global smearing is approximate under heteroskedasticity.',
            epsilon=1e-12,mean_scale='Recomputed using fit labels only at each training/refit stage; never validation/test labels.'),
        paired_tests='Two-sided intercept HAC lag5 finite-sample correction on eligible origins; MSE return, QLIKE variance. BH across 32 learned-model ablation comparisons; benchmark comparisons separately BH across 40. Approximate diagnostics, nested forecasts and irregular origins, not causal or confirmatory tests.',
        stress='Reproduce saved pooled stress-interaction model at h=0,1,5,10,20. Calm=beta; stress=beta+delta, variance=Vbeta+Vdelta+2Cov. Same previous eligible VIX>30 rule, controls and HAC. Pointwise CI only.',
        analogues='Descriptive top-5 nearest observed shock magnitudes within selected calm/stress state, scaled by fixed reporting shock size; exclude overlapping t..t+h session windows. Uses historical full sample; no prediction/causal claim.',
        references=[
            'https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html',
            'https://fred.stlouisfed.org/docs/api/fred/realtime_period.html',
            'https://fred.stlouisfed.org/docs/api/fred/release_dates.html'],
    )
    if (OUT/'design.json').exists():
        assert json.loads((OUT/'design.json').read_text(encoding='utf-8'))==design, 'Design already locked: use a new version for changes.'
    else:
        write_json('design.json',design)
        write_json('source_snapshot.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),protected_sha256=protected(),design_sha256=sha(OUT/'design.json')))
    f=pd.read_csv(ROOT/'data/processed/forecast_origins_vintage_macro.csv',parse_dates=['date_utc']).set_index('date_utc')
    assert f.index.equals(pd.date_range(f.index.min(),f.index.max(),freq='D',name='date_utc'))
    lag=f.shift(1)  # calendar grid verified above; NEVER shift after dropping dates
    timing=[]; summary=[]
    for asset in ['btc','eth']:
        base=pd.DataFrame(index=f.index)
        for c in own(asset)+MACRO+USD: base[c]=lag[c]
        base['origin_utc']=f.index+pd.Timedelta(days=1)
        base['information_row_date']=f.index-pd.Timedelta(days=1)
        base['information_reference_close_utc']=f.index
        base['target_date_utc']=f.index+pd.Timedelta(days=1)
        base['label_close_utc']=f.index+pd.Timedelta(days=2)
        base['label_assumed_available_utc']=f.index+pd.Timedelta(days=3)
        for c in PIT:
            for suffix in ['_pit_obs_date','_pit_vintage_date']:
                base[c+suffix]=lag[c+suffix]
        for target in ['return','squared_return']: base['actual_'+target]=f[asset+'_target_next_'+target]
        td=base.target_date_utc
        base['split']=np.where(td<'2023-01-01','train',np.where(td<'2025-01-01','validation','test'))
        base=base.replace([np.inf,-np.inf],np.nan)
        long_ok=base[own(asset)+MACRO+['actual_return','actual_squared_return']].notna().all(axis=1)
        common_ok=long_ok & base[USD].notna().all(axis=1) & (pd.to_datetime(base.broad_usd_pit_vintage_date)>='2019-02-04')
        for variant in VARIANTS:
            panel=base.loc[long_ok if variant.startswith('long') else common_ok].copy()
            # Keep only declared features, plus audit metadata; ablations cannot accidentally ingest macro.
            meta=[c for c in panel if c not in own(asset)+MACRO+USD]
            panel=panel[features(asset,variant)+meta]
            csv(panel.reset_index(),f'panels/{asset}_{variant}.csv')
            tr,va,dev,te=split_panel(panel)
            summary.append(dict(asset=asset,variant=variant,n_features=len(features(asset,variant)),first_date=str(panel.index.min().date()),last_date=str(panel.index.max().date()),n_rows=len(panel),train=len(tr),validation=len(va),development=len(dev),test=len(te),train_boundary_purged=int((panel.split=='train').sum()-len(tr)),development_boundary_purged=int((panel.split!='test').sum()-len(dev))))
            timing.append(dict(asset=asset,variant=variant,last_training_label_available=str(tr.label_assumed_available_utc.max()),first_validation_origin=str(va.origin_utc.min()),last_development_label_available=str(dev.label_assumed_available_utc.max()),first_test_origin=str(te.origin_utc.min())))
    csv(pd.DataFrame(summary),'sample_summary.csv');csv(pd.DataFrame(timing),'label_timing_checks.csv')
    availability=[]
    for name,group,rule,status in [
        ('BTC/ETH own features','Coin Metrics PriceUSD','close at 00:00 UTC, use preceding information row with 24h buffer','Retrospective snapshot; publication latency assumed <=24h, not certified'),
        ('VIX, S&P 500, gold','historical market feeds','existing lag1 + extra 1 calendar day; effective daily observation <=t-2','Lagged proxies; revisions/adjustments not archived'),
        ('2Y, 10Y, Fed Funds, WTI, NFCI','ALFRED','vintage <= information row t-1; admit original date-level information then extra 24h','Date-level vintage, not exact provider delivery timestamp'),
        ('Broad USD','ALFRED','same rule; first vintage 2019-02-04, no legacy splice','Common-sample feature only'),
        ('Training labels','Coin Metrics snapshot','label close +24h <= model fitting origin','Conservative assumed availability; labels remain retrospective')]:
        availability.append(dict(variable_group=name,source=group,admission_rule=rule,remaining_limit=status))
    csv(pd.DataFrame(availability),'availability_register.csv')
    print(pd.DataFrame(summary).to_string(index=False),flush=True)


def read_panel(asset,variant):
    f=pd.read_csv(OUT/f'panels/{asset}_{variant}.csv',parse_dates=['date_utc','origin_utc','target_date_utc','label_close_utc','label_assumed_available_utc','information_row_date','information_reference_close_utc']).set_index('date_utc')
    return f


def split_panel(panel):
    va=panel[panel.split=='validation'];te=panel[panel.split=='test']
    tr=panel[(panel.split=='train')&(panel.label_assumed_available_utc<=va.origin_utc.min())]
    dev=panel[(panel.split!='test')&(panel.label_assumed_available_utc<=te.origin_utc.min())]
    return tr,va,dev,te


def model_fit(kind,params,x,y,target):
    scale=float(np.mean(y)) if target=='squared_return' else 1.
    if target=='squared_return': assert scale>0
    if kind=='elastic_net':
        model=TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(),ElasticNet(max_iter=20000,tol=1e-6,**params)),transformer=StandardScaler())
        z=np.log(np.asarray(y)/scale+1e-12) if target=='squared_return' else np.asarray(y)
        model.fit(x,z)
        smear=float(np.mean(np.exp(z-model.predict(x)))) if target=='squared_return' else 1.
    else:
        model=HistGradientBoostingRegressor(loss='poisson' if target=='squared_return' else 'squared_error',max_iter=200,learning_rate=.05,min_samples_leaf=30,early_stopping=False,random_state=9,**params)
        model.fit(x,np.asarray(y)/scale);smear=1.
    return model,scale,smear


def model_predict(fitted,x,kind,target):
    model,scale,smear=fitted;p=model.predict(x)
    if kind=='elastic_net' and target=='squared_return': p=np.exp(p)*smear
    p=p*scale
    assert np.isfinite(p).all() and (target!='squared_return' or (p>0).all()), 'Invalid prediction; stop instead of adjusting floor.'
    return p


def losses(y,p,target):
    y=np.asarray(y);p=np.asarray(p)
    return (y-p)**2 if target=='return' else np.log(p)+y/p


def metric(y,p,target):
    y=np.asarray(y);p=np.asarray(p);e=y-p
    result=dict(mse=float(np.mean(e**2)),rmse=float(np.sqrt(np.mean(e**2))),mae=float(np.mean(abs(e))),qlike=None,direction_accuracy=None)
    if target=='squared_return': result['qlike']=float(np.mean(losses(y,p,target)))
    elif np.any(p!=0): result['direction_accuracy']=float(np.mean(np.sign(y)==np.sign(p)))
    return result


def benchmark(kind,fit,eval_frame,asset,target):
    if kind=='historical_mean': return np.repeat(fit['actual_'+target].mean(),len(eval_frame))
    if target=='return': return np.zeros(len(eval_frame))
    return eval_frame[asset+'_vol30_annualized'].to_numpy()**2/365


def paired_stat(a,b,target):
    # b minus a: negative is improvement. Match keys before calling.
    assert a.date_utc.tolist()==b.date_utc.tolist() and np.array_equal(a.actual.to_numpy(),b.actual.to_numpy())
    d=losses(b.actual,b.predicted,target)-losses(a.actual,a.predicted,target)
    # Intercept-only Elastic Net can equal the mean up to floating-point rounding.
    # Testing machine noise creates spurious p-values; record these as numerical ties.
    pa=a.predicted.to_numpy();pb=b.predicted.to_numpy()
    tolerance=64*np.finfo(float).eps*max(float(np.max(abs(pa))),float(np.max(abs(pb))),np.finfo(float).tiny)
    tied=bool(np.max(abs(pa-pb))<=tolerance)
    if tied:d=np.zeros_like(d)
    if np.max(abs(d))==0: se=0.;pval=1.
    else:
        fit=sm.OLS(d,np.ones((len(d),1))).fit(cov_type='HAC',cov_kwds={'maxlags':5,'use_correction':True})
        se=float(fit.bse[0]);pval=float(fit.pvalues[0]) if se>0 else 1.
    ma=metric(a.actual,a.predicted,target);mb=metric(b.actual,b.predicted,target)
    return dict(n_pairs=len(d),numerical_tie=tied,mean_loss_added_minus_base=float(d.mean()),hac_se=se,pvalue=pval,
                rmse_base=ma['rmse'],rmse_added=mb['rmse'],rmse_improvement_pct=100*(ma['rmse']-mb['rmse'])/ma['rmse'],
                qlike_base=ma['qlike'],qlike_added=mb['qlike'])


def fit_forecasts():
    snap=json.loads((OUT/'source_snapshot.json').read_text())
    assert sha(OUT/'design.json')==snap['design_sha256']
    assert all(sha(ROOT/p)==v for p,v in snap['protected_sha256'].items())
    scores=[];tuning=[];predictions=[];parameters=[];chosen=[];warning_rows=[]
    with threadpool_limits(limits=2):
        for asset,variant,target in itertools.product(['btc','eth'],VARIANTS,['return','squared_return']):
            f=read_panel(asset,variant);tr,va,dev,te=split_panel(f);feat=features(asset,variant);col='actual_'+target
            group=[]
            for kind in KINDS:
                fitted=None;best_params={}
                if kind in GRIDS:
                    best=None
                    for params in GRIDS[kind]:
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter('always');fit=model_fit(kind,params,tr[feat],tr[col],target)
                        warning_rows.extend(dict(asset=asset,variant=variant,target=target,model=kind,message=str(w.message)) for w in caught)
                        vp=model_predict(fit,va[feat],kind,target);objective=float(losses(va[col],vp,target).mean())
                        tuning.append(dict(asset=asset,variant=variant,target=target,model=kind,parameters=json.dumps(params,sort_keys=True),validation_objective=objective))
                        if best is None or objective<best[0]: best=(objective,params)
                    valobj,best_params=best
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always');fitted=model_fit(kind,best_params,dev[feat],dev[col],target)
                    warning_rows.extend(dict(asset=asset,variant=variant,target=target,model=kind,message=str(w.message)) for w in caught)
                    pred=model_predict(fitted,te[feat],kind,target)
                else:
                    vp=benchmark(kind,tr,va,asset,target);valobj=float(losses(va[col],vp,target).mean())
                    pred=benchmark(kind,dev,te,asset,target)
                out=dict(asset=asset,variant=variant,target=target,model=kind,n_test=len(te),validation_objective=valobj,**metric(te[col],pred,target))
                scores.append(out);group.append(out)
                parameters.append(dict(asset=asset,variant=variant,target=target,model=kind,parameters=json.dumps(best_params,sort_keys=True),fit_target_scale=fitted[1] if fitted else None,fit_smearing=fitted[2] if fitted else None,train_n=len(tr),refit_n=len(dev),n_features=len(feat)))
                predictions.extend(dict(date_utc=str(date.date()),asset=asset,variant=variant,target=target,model=kind,actual=float(y),predicted=float(p)) for date,y,p in zip(te.index,te[col],pred))
            chosen.append(min(group,key=lambda r:r['validation_objective']))
            print('Completed exploratory forecasts:',asset,variant,target,flush=True)
    scores=pd.DataFrame(scores);pred=pd.DataFrame(predictions);tests=[];bench_tests=[]
    for asset,target,kind in itertools.product(['btc','eth'],['return','squared_return'],['elastic_net','gradient_boosting']):
        q=pred[(pred.asset==asset)&(pred.target==target)&(pred.model==kind)]
        for left,right in PAIRS:
            a=q[q.variant==left].sort_values('date_utc');b=q[q.variant==right].sort_values('date_utc')
            tests.append(dict(asset=asset,target=target,model=kind,base=left,added=right,**paired_stat(a,b,target)))
        for variant in VARIANTS:
            ref='historical_mean' if target=='return' else 'natural_benchmark'
            a=pred[(pred.asset==asset)&(pred.target==target)&(pred.variant==variant)&(pred.model==ref)].sort_values('date_utc')
            b=q[q.variant==variant].sort_values('date_utc')
            bench_tests.append(dict(asset=asset,target=target,model=kind,variant=variant,benchmark=ref,**paired_stat(a,b,target)))
    for rows,name in [(tests,'ablation_tests.csv'),(bench_tests,'benchmark_tests.csv')]:
        frame=pd.DataFrame(rows);frame['qvalue_bh']=multipletests(frame.pvalue,method='fdr_bh')[1];csv(frame,name)
    for frame,name in [(scores,'forecast_metrics.csv'),(pd.DataFrame(tuning),'validation_search.csv'),(pd.DataFrame(parameters),'selected_parameters.csv'),(pred,'test_predictions.csv'),(pd.DataFrame(chosen),'validation_selected_models.csv')]: csv(frame,name)
    v=pred[pred.target=='squared_return'].groupby(['asset','variant','model']).agg(n=('predicted','size'),minimum=('predicted','min'),maximum=('predicted','max'),count_le_1e12=('predicted',lambda s:int((s<=1e-12).sum()))).reset_index()
    csv(v,'variance_diagnostics.csv');write_json('fit_warnings.json',warning_rows)
    write_json('run_audit.json',dict(design_sha256=sha(OUT/'design.json'),protected_files_unchanged=all(sha(ROOT/p)==v for p,v in snap['protected_sha256'].items()),n_metric_rows=len(scores),n_ablation_tests=len(tests),n_benchmark_tests=len(bench_tests),n_fit_warnings=len(warning_rows),interpretation='exploratory; previously inspected test'))


def stress_and_episodes():
    shocks={'vix_change':5.,'usd_return_pct':1.,'us2y_change_bps':10.,'us10y_change_bps':10.}
    names=list(shocks)+['crypto_return_pct'];rows=[];cov_rows=[];delta_rows=[];episodes=[]
    from scipy.stats import norm
    zcrit=norm.ppf(.975)
    for asset in ['btc','eth']:
        p=pd.read_csv(ROOT/f'data/processed/{asset}_econometric_sessions.csv',parse_dates=['date_utc']).set_index('date_utc')
        x=p[names[:4]].copy()
        for k in range(1,6):
            for c in names:x[f'L{k}_{c}']=p[c].shift(k)
        x['regime']=p.stress_lag
        for c in shocks:x[c+'_interaction']=p[c]*p.stress_lag
        for h in [0,1,5,10,20]:
            y=sum(p.crypto_return_pct.shift(-k) for k in range(h+1));f=x.assign(outcome=y).dropna()
            fit=sm.OLS(f.outcome,sm.add_constant(f.drop(columns='outcome'))).fit(cov_type='HAC',cov_kwds={'maxlags':max(5,h+1),'use_correction':True})
            cov=fit.cov_params()
            for shock,scale in shocks.items():
                term=shock+'_interaction'
                b=float(fit.params[shock]*scale);d=float(fit.params[term]*scale)
                vb=float(cov.loc[shock,shock]*scale**2);vd=float(cov.loc[term,term]*scale**2);cross=float(cov.loc[shock,term]*scale**2)
                cov_rows.append(dict(asset=asset,shock=shock,horizon_sessions=h,calm=b,difference=d,var_calm=vb,var_difference=vd,cov_calm_difference=cross))
                delta_rows.append(dict(asset=asset,shock=shock,horizon_sessions=h,difference_pct=d,se=float(np.sqrt(vd)),nobs=int(fit.nobs)))
                for state in ['calm','stress']:
                    beta=b+(d if state=='stress' else 0);se=float(np.sqrt(vb+(vd+2*cross if state=='stress' else 0)))
                    rows.append(dict(asset=asset,shock=shock,horizon_sessions=h,regime=state,beta_pct=beta,se=se,lower95=beta-zcrit*se,upper95=beta+zcrit*se,nobs=int(fit.nobs),n_state=int((f.regime==(state=='stress')).sum())))
                    # Descriptive observed cumulative return; no fitted/counterfactual response.
                    pool=p.assign(observed_cumulative_pct=y,position=np.arange(len(p)))
                    pool=pool[(pool.stress_lag==(state=='stress'))&pool.observed_cumulative_pct.notna()].copy()
                    pool['distance']=abs(pool[shock]-scale)/scale
                    pool=pool.sort_values(['distance','position'],kind='stable');used=[];rank=0
                    for date,r in pool.iterrows():
                        pos=int(r.position)
                        if any(not (pos+h<a or pos>b) for a,b in used):continue
                        used.append((pos,pos+h));rank+=1
                        episodes.append(dict(asset=asset,shock=shock,regime=state,horizon_sessions=h,rank=rank,date_utc=str(date.date()),end_date_utc=str(p.index[pos+h].date()),shock_observed=float(r[shock]),shock_reference=scale,distance_scaled=float(r.distance),observed_cumulative_pct=float(r.observed_cumulative_pct),interval_calendar_days=int(p.elapsed_calendar_days.iloc[pos:pos+h+1].sum())))
                        if rank==5:break
        print('Reproduced stress model and historical analogues:',asset,flush=True)
    for frame,name in [(pd.DataFrame(rows),'state_responses.csv'),(pd.DataFrame(cov_rows),'state_covariance.csv'),(pd.DataFrame(delta_rows),'reproduced_stress_differences.csv'),(pd.DataFrame(episodes),'historical_analogues.csv')]:csv(frame,name)
    prior=pd.read_csv(TABLES/'regime_interactions.csv');prior=prior[prior.interaction=='stress_lag_vix_gt30']
    match=prior.merge(pd.DataFrame(delta_rows),on=['asset','shock','horizon_sessions'],suffixes=('_old','_new'))
    assert len(match)==40 and np.allclose(match.difference_pct_old,match.difference_pct_new,rtol=1e-7,atol=1e-7)
    assert np.allclose(match.se_old,match.se_new,rtol=1e-7,atol=1e-7)


def refresh_tests():
    """Recompute paired summaries only; numerical tie fix leaves all fitted models intact."""
    pred=pd.read_csv(OUT/'test_predictions.csv',float_precision='round_trip');tests=[];bench=[]
    for asset,target,kind in itertools.product(['btc','eth'],['return','squared_return'],['elastic_net','gradient_boosting']):
        q=pred[(pred.asset==asset)&(pred.target==target)&(pred.model==kind)]
        for left,right in PAIRS:
            a=q[q.variant==left].sort_values('date_utc');b=q[q.variant==right].sort_values('date_utc')
            tests.append(dict(asset=asset,target=target,model=kind,base=left,added=right,**paired_stat(a,b,target)))
        for variant in VARIANTS:
            ref='historical_mean' if target=='return' else 'natural_benchmark'
            a=pred[(pred.asset==asset)&(pred.target==target)&(pred.variant==variant)&(pred.model==ref)].sort_values('date_utc')
            b=q[q.variant==variant].sort_values('date_utc')
            bench.append(dict(asset=asset,target=target,model=kind,variant=variant,benchmark=ref,**paired_stat(a,b,target)))
    for rows,name in [(tests,'ablation_tests.csv'),(bench,'benchmark_tests.csv')]:
        frame=pd.DataFrame(rows);frame['qvalue_bh']=multipletests(frame.pvalue,method='fdr_bh')[1];csv(frame,name)
    write_json('numerical_tie_note.json',dict(reason='Computational correction: constant Elastic Net and historical mean differ only at machine precision in some comparisons. HAC on rounding noise produced spurious p-values.',rule='Treat max prediction difference <=64*machine_epsilon*max absolute prediction as a numerical tie; mean loss difference=0, SE=0, p=1; no model/parameter/sample change.',ablation_ties=sum(r['numerical_tie'] for r in tests),benchmark_ties=sum(r['numerical_tie'] for r in bench)))
    print('Paired summaries recomputed with machine-precision ties documented.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','fit','stress','tests']);args=parser.parse_args()
    {'prepare':prepare,'fit':fit_forecasts,'stress':stress_and_episodes,'tests':refresh_tests}[args.stage]()
