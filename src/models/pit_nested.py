"""Expanding annual outer folds with purged chronological inner selection."""
from src.evaluation.pit_nested_common import *
from research_completion import VARIANTS, PAIRS, features, model_fit, model_predict, losses, metric
from threadpoolctl import threadpool_limits
from statsmodels.stats.multitest import multipletests
from collections import OrderedDict
import hashlib, itertools, warnings, joblib

def verify_inputs():
    lock=json.loads((OUT/'prepared_input_lock.json').read_text(encoding='utf-8'))
    assert all((ROOT/n).exists() and sha(ROOT/n)==h for n,h in lock['files'].items()), 'Prepared input changed'

def model_key(kind,params,x,y,target):
    h=hashlib.sha256()
    h.update(json.dumps([kind,params,target,list(x.columns)],sort_keys=True).encode())
    h.update(x.index.to_numpy(dtype='datetime64[ns]').tobytes())
    h.update(np.ascontiguousarray(x.to_numpy(dtype='float64')).tobytes())
    h.update(np.ascontiguousarray(y.to_numpy(dtype='float64')).tobytes())
    return h.hexdigest()

def train():
    init();verify_inputs();check_protected();cfg=config()
    assert not (MODELS/'freeze.json').exists(), 'Frozen; use validate, never refit this namespace'
    codefiles=[CONFIG,ROOT/'research_completion.py',ROOT/'src/models/pit_nested.py',ROOT/'src/evaluation/pit_nested_common.py']
    lockpath=OUT/'fit_code_lock.json';lock=dict(files={p.relative_to(ROOT).as_posix():sha(p) for p in codefiles})
    if lockpath.exists():assert json.loads(lockpath.read_text(encoding='utf-8'))==lock
    else:save_json(lockpath,lock)
    cache=OrderedDict();fitcount=0;cachehits=0;warningrows=[]
    def fit(kind,params,x,y,target):
        nonlocal fitcount,cachehits
        key=model_key(kind,params,x,y,target)
        if key in cache:
            cache.move_to_end(key);cachehits+=1
            return cache[key],key
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');result=model_fit(kind,params,x,y,target)
        warningrows.extend(dict(fit_key=key,category=w.category.__name__,message=str(w.message)) for w in caught)
        fitcount+=1;cache[key]=result
        if len(cache)>64:cache.popitem(last=False)
        return result,key
    with threadpool_limits(limits=2):
        for asset,variant,target,year in itertools.product(['btc','eth'],VARIANTS,['return','squared_return'],cfg['outer_years']):
            for scenario in cfg['scenarios']:
                stem=f'{asset}_{variant}_{target}_{year}_{scenario}'
                done=OUT/'folds'/f'{stem}.json'
                if done.exists():
                    record=json.loads(done.read_text(encoding='utf-8'))
                    assert all(sha(ROOT/n)==h for n,h in record['files'].items()), 'Incomplete resumed fold'
                    continue
                g=read_panel(asset,variant,scenario);cols=features(asset,variant);ycol='actual_'+target
                start=pd.Timestamp(year,1,1);end=pd.Timestamp(year+1,1,1)
                tr=training(g,start);te=g[(g.index>=start)&(g.index<end)]
                assert len(tr)>=cfg['min_train'] and len(te)>=cfg['min_validation']
                inners=inner_splits(g,year);predrows=[];search=[];selected=[];inventory=[];timing=[]
                common=dict(asset=asset,variant=variant,target=target,outer_year=year,scenario=scenario)
                timing.append(dict(**common,stage='outer',fold_start=start,fit_cutoff=fit_cutoff(start),n_fit=len(tr),n_evaluate=len(te),
                    last_fit_origin=tr.index.max(),last_fit_label_available=tr.label_assumed_available_utc.max(),first_evaluate_origin=te.index.min(),
                    last_tuning_label_available=max(va.label_assumed_available_utc.max() for _,_,va in inners)))
                for vstart,itr,iva in inners:
                    timing.append(dict(**common,stage='inner',fold_start=vstart,fit_cutoff=fit_cutoff(vstart),n_fit=len(itr),n_evaluate=len(iva),
                        last_fit_origin=itr.index.max(),last_fit_label_available=itr.label_assumed_available_utc.max(),first_evaluate_origin=iva.index.min(),last_tuning_label_available=iva.label_assumed_available_utc.max()))
                for kind in cfg['models']:
                    best=None
                    for rank,params in enumerate(cfg['grids'][kind]):
                        totals=0.;n=0;innerstats=[]
                        for vstart,itr,iva in inners:
                            fitted,key=fit(kind,params,itr[cols],itr[ycol],target)
                            vp=model_predict(fitted,iva[cols],kind,target)
                            vals=losses(iva[ycol],vp,target);totals+=float(vals.sum());n+=len(vals)
                            innerstats.append(dict(start=str(vstart.date()),n=len(vals),sum_loss=float(vals.sum()),fit_key=key))
                        objective=totals/n
                        search.append(dict(**common,model=kind,grid_rank=rank,parameters=json.dumps(params,sort_keys=True),validation_n=n,validation_loss=objective,inner_folds=json.dumps(innerstats)))
                        tolerance=64*np.finfo(float).eps*max(1,abs(best[0]) if best else 1)
                        if best is None or objective<best[0]-tolerance:best=(objective,params,rank)
                    objective,params,rank=best
                    fitted,key=fit(kind,params,tr[cols],tr[ycol],target)
                    pred=model_predict(fitted,te[cols],kind,target)
                    path=MODELS/f'{stem}_{kind}.joblib'
                    joblib.dump(dict(fitted=fitted,features=cols,parameters=params,fit_key=key,**common,kind=kind,
                        simulated_fit_cutoff_utc=str(fit_cutoff(start)),last_fit_label_available=str(tr.label_assumed_available_utc.max()),
                        created_utc=pd.Timestamp.now(tz='UTC').isoformat(),interpretation=cfg['interpretation'],config_sha256=sha(CONFIG)),path)
                    inventory.append(dict(**common,model=kind,file=path.relative_to(ROOT).as_posix(),sha256=sha(path),n_fit=len(tr),fit_key=key))
                    selected.append(dict(**common,model=kind,parameters=json.dumps(params,sort_keys=True),grid_rank=rank,validation_loss=objective,n_fit=len(tr),n_outer=len(te)))
                    predrows.extend(dict(**common,origin_utc=str(d.date()),model=kind,actual=float(y),predicted=float(p)) for d,y,p in zip(te.index,te[ycol],pred))
                for kind in cfg['benchmarks']:
                    if kind=='historical_mean':pred=np.repeat(float(tr[ycol].mean()),len(te))
                    elif target=='return':pred=np.zeros(len(te))
                    else:pred=te[asset+'_vol30_annualized'].to_numpy()**2/365
                    assert np.isfinite(pred).all() and (target!='squared_return' or (pred>0).all())
                    predrows.extend(dict(**common,origin_utc=str(d.date()),model=kind,actual=float(y),predicted=float(p)) for d,y,p in zip(te.index,te[ycol],pred))
                csv(pd.DataFrame(predrows),f'folds/{stem}_predictions.csv')
                paths=[OUT/'folds'/f'{stem}_predictions.csv']+[ROOT/r['file'] for r in inventory]
                record=dict(**common,search=search,selected=selected,inventory=inventory,timing=timing,
                    files={p.relative_to(ROOT).as_posix():sha(p) for p in paths},completed_utc=pd.Timestamp.now(tz='UTC').isoformat())
                save_json(done,record)
            save_json(OUT/'fit_progress.json',dict(last_completed=[asset,variant,target,year],new_fits=fitcount,cache_hits=cachehits,utc=pd.Timestamp.now(tz='UTC').isoformat()))
            print('Nested:',asset,variant,target,year,'fits',fitcount,'cache',cachehits,flush=True)
    records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT/'folds').glob('*.json'))]
    assert len(records)==2*5*2*4*4
    for field,name in [('search','inner_search.csv'),('selected','selected_parameters.csv'),('inventory','model_inventory.csv'),('timing','fold_timing.csv')]:
        csv(pd.DataFrame([r for rec in records for r in rec[field]]),name)
    preds=pd.concat([pd.read_csv(OUT/'folds'/f'{r["asset"]}_{r["variant"]}_{r["target"]}_{r["outer_year"]}_{r["scenario"]}_predictions.csv',float_precision='round_trip') for r in records],ignore_index=True)
    csv(preds,'outer_predictions.csv')
    save_json(OUT/'fit_warnings.json',warningrows)
    save_json(MODELS/'freeze.json',dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),config_sha256=sha(CONFIG),inventory_sha256=sha(OUT/'model_inventory.csv'),
        predictions_sha256=sha(OUT/'outer_predictions.csv'),artifacts=sum(len(r['inventory']) for r in records),fold_groups=len(records),new_fits_this_process=fitcount,cache_hits=cachehits,
        interpretation=cfg['interpretation']))
    print('Nested artifacts frozen:',sum(len(r['inventory']) for r in records),flush=True)

def paired(a,b,target,seed):
    q=a[['origin_utc','actual','predicted']].merge(b[['origin_utc','actual','predicted']],on='origin_utc',suffixes=('_base','_new'),validate='one_to_one')
    assert len(q)>0 and np.array_equal(q.actual_base.to_numpy(),q.actual_new.to_numpy())
    d=losses(q.actual_base,q.predicted_new,target)-losses(q.actual_base,q.predicted_base,target)
    days=pd.to_datetime(q.origin_utc).to_numpy(dtype='datetime64[D]').astype('int64')
    blocks=days//config()['inference']['calendar_block_days'];unique,idx=np.unique(blocks,return_inverse=True)
    sums=np.bincount(idx,weights=d);counts=np.bincount(idx);mean=float(d.mean())
    rng=np.random.default_rng(seed);draw=rng.integers(0,len(unique),(config()['inference']['bootstrap_draws'],len(unique)))
    boot=sums[draw].sum(axis=1)/counts[draw].sum(axis=1)
    lo,hi=np.quantile(boot,[.025,.975]);tol=64*np.finfo(float).eps*max(1,float(abs(d).max()))
    p=1. if np.max(abs(d))<=tol else (1+int((abs(boot-mean)>=abs(mean)).sum()))/(len(boot)+1)
    return dict(n=len(q),calendar_clusters=len(unique),mean_loss_new_minus_base=mean,ci_low=float(lo),ci_high=float(hi),pvalue=p,
                first_origin=str(q.origin_utc.min()),last_origin=str(q.origin_utc.max()))

def compare():
    verify_inputs();freeze=json.loads((MODELS/'freeze.json').read_text(encoding='utf-8'))
    assert sha(OUT/'outer_predictions.csv')==freeze['predictions_sha256']
    pred=pd.read_csv(OUT/'outer_predictions.csv',float_precision='round_trip');scores=[];abl=[];bench=[];sens=[]
    for key,q in pred.groupby(['asset','variant','target','model','scenario']):
        asset,variant,target,kind,scenario=key
        for scope,g in [('pooled',q)]+[(str(year),g) for year,g in q.groupby('outer_year')]:
            scores.append(dict(asset=asset,variant=variant,target=target,model=kind,scenario=scenario,scope=scope,n=len(g),**metric(g.actual,g.predicted,target)))
    counter=0
    def test(a,b,target):
        nonlocal counter
        counter+=1;return paired(a,b,target,config()['inference']['seed']+counter)
    for asset,target,kind in itertools.product(['btc','eth'],['return','squared_return'],config()['models']):
        q=pred[(pred.asset==asset)&(pred.target==target)]
        for scope in ['pooled']+[str(y) for y in config()['outer_years']]:
            z=q if scope=='pooled' else q[q.outer_year==int(scope)]
            common=dict(asset=asset,target=target,model=kind,scope=scope)
            for scenario in config()['scenarios']:
                w=z[z.scenario==scenario];learn=w[w.model==kind]
                for left,right in PAIRS:
                    abl.append(dict(**common,scenario=scenario,base=left,added=right,**test(learn[learn.variant==left],learn[learn.variant==right],target)))
                for variant in VARIANTS:
                    ref='historical_mean' if target=='return' else 'natural_benchmark'
                    bench.append(dict(**common,scenario=scenario,variant=variant,benchmark=ref,
                        **test(w[(w.model==ref)&(w.variant==variant)],learn[learn.variant==variant],target)))
            for variant in VARIANTS:
                w=z[(z.variant==variant)&(z.model==kind)]
                for left,right,label in [('native_asof_d3','matched_asof_d3','sample_refit_effect_on_common_test'),
                                         ('matched_asof_d3','matched_latest_d3','vintage_same_observations'),
                                         ('matched_asof_d3','matched_asof_d4','extra_calendar_day')]:
                    sens.append(dict(**common,variant=variant,comparison=label,base=left,changed=right,
                        **test(w[w.scenario==left],w[w.scenario==right],target)))
    csv(pd.DataFrame(scores),'forecast_metrics.csv')
    for rows,name in [(abl,'ablation_tests.csv'),(bench,'benchmark_tests.csv'),(sens,'sensitivity_tests.csv')]:
        frame=pd.DataFrame(rows);frame['qvalue_bh']=multipletests(frame.pvalue,method='fdr_bh')[1];csv(frame,name)
    print('Paired comparisons:',len(abl),len(bench),len(sens),flush=True)
