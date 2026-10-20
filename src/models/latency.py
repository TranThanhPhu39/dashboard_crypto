"""Shift before selection, train on past labels, retain both benchmarks and artifacts."""
from src.evaluation.latency_common import *
from research_completion import (MACRO,USD,PIT,VARIANTS,PAIRS,KINDS,GRIDS,features,own,
    split_panel,model_fit,model_predict,losses,metric,benchmark,paired_stat)
from statsmodels.stats.multitest import multipletests
from threadpoolctl import threadpool_limits
import itertools,warnings,joblib

DATES=['date_utc','origin_utc','target_date_utc','information_row_date','information_reference_close_utc','label_close_utc','label_assumed_available_utc']

def panel(asset,variant):
    return pd.read_csv(PANELS/f'{asset}_{variant}.csv',parse_dates=DATES,float_precision='round_trip').set_index('date_utc')

def prepare():
    init();assert not (MODELS/'freeze.json').exists(),'Artifacts already frozen; use a new version.'
    f=pd.read_csv(ROOT/config()['historical_source'],parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc')
    assert f.index.equals(pd.date_range(f.index.min(),f.index.max(),name='date_utc'))
    lag=f.shift(config()['original_feature_shift_calendar_days']);summary=[];timing=[]
    for asset in ['btc','eth']:
        b=lag[own(asset)+MACRO+USD].copy()
        b['origin_utc']=b.index+pd.Timedelta(days=1)
        b['target_date_utc']=b.origin_utc
        b['information_row_date']=b.index-pd.Timedelta(days=2)
        b['information_reference_close_utc']=b.index-pd.Timedelta(days=1)
        b['label_close_utc']=b.index+pd.Timedelta(days=2)
        b['label_assumed_available_utc']=b.index+pd.Timedelta(days=3)
        for c in PIT:
            for suffix in ['_pit_obs_date','_pit_vintage_date']:b[c+suffix]=lag[c+suffix]
        for target in ['return','squared_return']:b['actual_'+target]=f[asset+'_target_next_'+target]
        b['split']=np.where(b.target_date_utc<'2023-01-01','train',np.where(b.target_date_utc<'2025-01-01','validation','test'))
        b=b.replace([np.inf,-np.inf],np.nan)
        long=b[own(asset)+MACRO+['actual_return','actual_squared_return']].notna().all(axis=1)
        common=long & b[USD].notna().all(axis=1) & (pd.to_datetime(b.broad_usd_pit_vintage_date)>='2019-02-04')
        for variant in VARIANTS:
            g=b.loc[long if variant.startswith('long') else common].copy()
            meta=[c for c in g if c not in own(asset)+MACRO+USD];g=g[features(asset,variant)+meta]
            g.to_csv(PANELS/f'{asset}_{variant}.csv',encoding='utf-8-sig',float_format='%.17g')
            tr,va,dev,te=split_panel(g)
            summary.append(dict(asset=asset,variant=variant,n_rows=len(g),n_features=len(features(asset,variant)),train=len(tr),validation=len(va),development=len(dev),test=len(te),first_origin=str(g.origin_utc.min()),last_origin=str(g.origin_utc.max())))
            timing.append(dict(asset=asset,variant=variant,last_train_label_available=str(tr.label_assumed_available_utc.max()),first_validation_origin=str(va.origin_utc.min()),last_development_label_available=str(dev.label_assumed_available_utc.max()),first_test_origin=str(te.origin_utc.min())))
    csv(pd.DataFrame(summary),'sample_summary.csv');csv(pd.DataFrame(timing),'label_timing.csv')
    print(pd.DataFrame(summary).to_string(index=False),flush=True)

def train():
    init();check_protected();assert not (MODELS/'freeze.json').exists(),'Frozen models cannot be overwritten.'
    scores=[];search=[];parameters=[];predictions=[];selected=[];inventory=[];benchstates=[];warning_rows=[]
    with threadpool_limits(limits=2):
        for asset,variant,target in itertools.product(['btc','eth'],VARIANTS,['return','squared_return']):
            f=panel(asset,variant);tr,va,dev,te=split_panel(f);cols=features(asset,variant);col='actual_'+target;group=[]
            benchstates.append(dict(asset=asset,variant=variant,target=target,historical_mean=float(dev[col].mean()),n_fit=len(dev),last_fit_label_available=str(dev.label_assumed_available_utc.max())))
            for kind in KINDS:
                settings={};fit=None
                if kind in GRIDS:
                    best=None
                    for params in GRIDS[kind]:
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter('always');vfit=model_fit(kind,params,tr[cols],tr[col],target)
                        warning_rows.extend(dict(asset=asset,variant=variant,target=target,model=kind,stage='validation',message=str(w.message)) for w in caught)
                        vp=model_predict(vfit,va[cols],kind,target);objective=float(losses(va[col],vp,target).mean())
                        search.append(dict(asset=asset,variant=variant,target=target,model=kind,parameters=json.dumps(params,sort_keys=True),validation_loss=objective))
                        if best is None or objective<best[0]:best=(objective,params)
                    objective,settings=best
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always');fit=model_fit(kind,settings,dev[cols],dev[col],target)
                    warning_rows.extend(dict(asset=asset,variant=variant,target=target,model=kind,stage='refit',message=str(w.message)) for w in caught)
                    pred=model_predict(fit,te[cols],kind,target)
                    file=MODELS/f'{asset}_{variant}_{target}_{kind}.joblib'
                    payload=dict(fitted=fit,features=cols,asset=asset,variant=variant,target=target,kind=kind,parameters=settings,last_fit_label_available=str(dev.label_assumed_available_utc.max()),config_sha256=sha(CONFIG),feature_shift_calendar_days=2,sklearn_version=__import__('sklearn').__version__)
                    joblib.dump(payload,file)
                    inventory.append(dict(file=file.relative_to(ROOT).as_posix(),sha256=sha(file),asset=asset,variant=variant,target=target,model=kind,n_fit=len(dev)))
                else:
                    vp=benchmark(kind,tr,va,asset,target);objective=float(losses(va[col],vp,target).mean());pred=benchmark(kind,dev,te,asset,target)
                out=dict(asset=asset,variant=variant,target=target,model=kind,n_test=len(te),validation_loss=objective,**metric(te[col],pred,target))
                scores.append(out);group.append(out)
                parameters.append(dict(asset=asset,variant=variant,target=target,model=kind,parameters=json.dumps(settings,sort_keys=True),n_fit=len(dev)))
                predictions.extend(dict(date_utc=str(date.date()),origin_utc=str(date+pd.Timedelta(days=1)),asset=asset,variant=variant,target=target,model=kind,actual=float(y),predicted=float(p)) for date,y,p in zip(te.index,te[col],pred))
            selected.append(min(group,key=lambda r:r['validation_loss']))
            print('New latency models:',asset,variant,target,flush=True)
    for frame,name in [(pd.DataFrame(scores),'forecast_metrics.csv'),(pd.DataFrame(search),'validation_search.csv'),(pd.DataFrame(parameters),'selected_parameters.csv'),(pd.DataFrame(predictions),'test_predictions.csv'),(pd.DataFrame(selected),'validation_selected_models.csv'),(pd.DataFrame(inventory),'model_inventory.csv'),(pd.DataFrame(benchstates),'benchmark_states.csv')]:csv(frame,name)
    save_json(OUT/'fit_warnings.json',warning_rows)
    save_json(MODELS/'freeze.json',dict(frozen_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),inventory_sha256=sha(OUT/'model_inventory.csv'),benchmark_states_sha256=sha(OUT/'benchmark_states.csv'),config_sha256=sha(CONFIG),artifacts=40,interpretation='Old test was viewed; all historical results exploratory. No future OOS claim.'))
    comparisons()

def comparisons():
    pred=pd.read_csv(OUT/'test_predictions.csv',float_precision='round_trip');ablation=[];bench=[]
    for asset,target,kind in itertools.product(['btc','eth'],['return','squared_return'],['elastic_net','gradient_boosting']):
        q=pred[(pred.asset==asset)&(pred.target==target)&(pred.model==kind)]
        for left,right in PAIRS:
            a=q[q.variant==left].sort_values('date_utc');b=q[q.variant==right].sort_values('date_utc')
            ablation.append(dict(asset=asset,target=target,model=kind,base=left,added=right,**paired_stat(a,b,target)))
        for variant in VARIANTS:
            ref='historical_mean' if target=='return' else 'natural_benchmark'
            a=pred[(pred.asset==asset)&(pred.target==target)&(pred.variant==variant)&(pred.model==ref)].sort_values('date_utc')
            b=q[q.variant==variant].sort_values('date_utc')
            bench.append(dict(asset=asset,target=target,model=kind,variant=variant,benchmark=ref,**paired_stat(a,b,target)))
    for rows,name in [(ablation,'ablation_tests.csv'),(bench,'benchmark_tests.csv')]:
        frame=pd.DataFrame(rows);frame['qvalue_bh']=multipletests(frame.pvalue,method='fdr_bh')[1];csv(frame,name)
    old=pd.read_csv(RESULTS/'completion/test_predictions.csv',float_precision='round_trip');rows=[]
    for key,b in pred.groupby(['asset','variant','target','model']):
        asset,variant,target,kind=key
        a=old[(old.asset==asset)&(old.variant==variant)&(old.target==target)&(old.model==kind)]
        pairs=a.merge(b,on='date_utc',suffixes=('_old','_new'))
        error=float(abs(pairs.actual_old-pairs.actual_new).max())
        tolerance=64*np.finfo(float).eps*max(float(abs(pairs.actual_new).max()),np.finfo(float).tiny)
        assert len(pairs)>0 and error<=tolerance,'Target mismatch beyond CSV floating-point rounding'
        ma=metric(pairs.actual_new,pairs.predicted_old,target);mb=metric(pairs.actual_new,pairs.predicted_new,target)
        rows.append(dict(asset=asset,variant=variant,target=target,model=kind,n_old=len(a),n_new=len(b),n_common=len(pairs),target_roundtrip_max_difference=error,old_rmse=ma['rmse'],new_rmse=mb['rmse'],old_qlike=ma['qlike'],new_qlike=mb['qlike'],mean_loss_new_minus_old=float(np.mean(losses(pairs.actual_new,pairs.predicted_new,target)-losses(pairs.actual_new,pairs.predicted_old,target)))))
    csv(pd.DataFrame(rows),'timing_comparison_common_dates.csv')
    print('New timing: BH32/BH40 and old/new timing on common dates saved.',flush=True)
