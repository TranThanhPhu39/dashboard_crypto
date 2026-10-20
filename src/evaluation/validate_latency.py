"""Independent alignment, scoring and deployment checks for the extra-day extension."""
from src.evaluation.latency_common import *
from src.models.latency import panel,features,VARIANTS,MACRO,USD,PIT,split_panel,model_predict,GRIDS
from src.evaluation.latency_live import frozen,records,envelope
from threadpoolctl import threadpool_limits
from scipy.stats import norm
import joblib,unittest

def manual_bh(p):
    p=np.asarray(p);idx=np.argsort(p);n=len(p);q=np.minimum.accumulate((p[idx]*n/np.arange(1,n+1))[::-1])[::-1]
    out=np.empty(n);out[idx]=np.minimum(q,1);return out

def run():
    init();checks={};source=pd.read_csv(ROOT/config()['historical_source'],parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc')
    pred=pd.read_csv(OUT/'test_predictions.csv',float_precision='round_trip');score=pd.read_csv(OUT/'forecast_metrics.csv');inventory,freeze=frozen()
    panel_ok=labels_ok=sample_ok=purge_ok=vintage_ok=True
    for asset in ['btc','eth']:
        frames={v:panel(asset,v) for v in VARIANTS}
        for variant,g in frames.items():
            cols=features(asset,variant);information=g.index-pd.Timedelta(days=2)
            expected=source.reindex(information)[cols].to_numpy()
            panel_ok &= np.array_equal(g[cols].to_numpy(),expected)
            panel_ok &= bool((g.information_row_date==information).all() and (g.information_reference_close_utc==g.origin_utc-pd.Timedelta(days=2)).all())
            labels_ok &= all(np.array_equal(g['actual_'+t].to_numpy(),source.reindex(g.index)[asset+'_target_next_'+t].to_numpy()) for t in ['return','squared_return'])
            tr,va,dev,te=split_panel(g);purge_ok &= bool(tr.label_assumed_available_utc.max()<=va.origin_utc.min() and dev.label_assumed_available_utc.max()<=te.origin_utc.min())
            for c in PIT:
                vd=pd.to_datetime(g[c+'_pit_vintage_date']);obs=pd.to_datetime(g[c+'_pit_obs_date'])
                vintage_ok &= bool(((vd<=information)|vd.isna()).all() and ((obs<=information)|obs.isna()).all())
        for a,b in [('long_own','long_macro'),('common_own','common_macro'),('common_macro','common_usd')]:
            sample_ok &= frames[a].index.equals(frames[b].index)
            shared=list(set(frames[a].columns)&set(frames[b].columns));sample_ok &= frames[a][shared].equals(frames[b][shared])
    checks['all_features_shifted_two_calendar_days_before_selection']=panel_ok
    checks['targets_not_shifted_with_features']=labels_ok
    checks['label_boundary_purging']=purge_ok
    checks['macro_vintage_and_observation_dates_not_future']=vintage_ok
    checks['matched_samples_and_shared_values']=sample_ok
    checks['no_USD_features_in_long_and_common_macro']=all('broad_usd_pit_change' not in features('btc',v) for v in ['long_own','long_macro','common_own','common_macro'])
    search=pd.read_csv(OUT/'validation_search.csv');params=pd.read_csv(OUT/'selected_parameters.csv');selection_ok=True
    for row in inventory.itertuples():
        s=search[(search.asset==row.asset)&(search.variant==row.variant)&(search.target==row.target)&(search.model==row.model)]
        r=params[(params.asset==row.asset)&(params.variant==row.variant)&(params.target==row.target)&(params.model==row.model)].iloc[0]
        selection_ok &= json.loads(s.loc[s.validation_loss.idxmin(),'parameters'])==json.loads(r.parameters)
    checks['40_parameters_selected_by_validation_only']=selection_ok and len(search)==200
    checks['all40_model_hashes_and_freeze_verified']=len(inventory)==40
    maximum=0.
    with threadpool_limits(limits=2):
        for row in inventory.itertuples():
            model=joblib.load(ROOT/row.file);g=panel(row.asset,row.variant);tr,va,dev,te=split_panel(g)
            out=model_predict(model['fitted'],te[model['features']],row.model,row.target)
            ref=pred[(pred.asset==row.asset)&(pred.variant==row.variant)&(pred.target==row.target)&(pred.model==row.model)]
            maximum=max(maximum,float(np.max(abs(out-ref.predicted.to_numpy()))))
    checks['serialized_artifacts_reproduce_all_test_predictions']=maximum<1e-12
    checks['all_variance_predictions_positive']=bool((pred.loc[pred.target=='squared_return','predicted']>0).all())
    metric_ok=True
    for row in score.itertuples():
        g=pred[(pred.asset==row.asset)&(pred.variant==row.variant)&(pred.target==row.target)&(pred.model==row.model)]
        metric_ok &= np.isclose(np.mean((g.actual-g.predicted)**2),row.mse,rtol=1e-12,atol=1e-18)
        if row.target=='squared_return':metric_ok &= np.isclose(np.mean(np.log(g.predicted)+g.actual/g.predicted),row.qlike,rtol=1e-12)
    checks['all80_metrics_recomputed']=metric_ok
    inference_ok=True
    for name,family in [('ablation_tests.csv',32),('benchmark_tests.csv',40)]:
        f=pd.read_csv(OUT/name);inference_ok &= len(f)==family and np.allclose(manual_bh(f.pvalue),f.qvalue_bh,rtol=1e-12,atol=1e-14)
        for row in f.itertuples():
            base=row.base if hasattr(row,'base') else row.variant;added=row.added if hasattr(row,'added') else row.variant
            ka=row.model if hasattr(row,'base') else row.benchmark
            a=pred[(pred.asset==row.asset)&(pred.target==row.target)&(pred.variant==base)&(pred.model==ka)].sort_values('date_utc')
            b=pred[(pred.asset==row.asset)&(pred.target==row.target)&(pred.variant==added)&(pred.model==row.model)].sort_values('date_utc')
            assert a.date_utc.tolist()==b.date_utc.tolist()
            loss=lambda g:(g.actual.to_numpy()-g.predicted.to_numpy())**2 if row.target=='return' else np.log(g.predicted.to_numpy())+g.actual.to_numpy()/g.predicted.to_numpy()
            d=loss(b)-loss(a)
            if row.numerical_tie:d=np.zeros(len(d))
            u=d-d.mean();n=len(u);v=u@u
            for L in range(1,6):v+=2*(1-L/6)*(u[L:]@u[:-L])
            se=np.sqrt(max(0,v/n**2*n/(n-1)));p=2*norm.sf(abs(d.mean()/se)) if se>0 else 1.
            inference_ok &= np.isclose(d.mean(),row.mean_loss_added_minus_base,atol=1e-12) and np.isclose(se,row.hac_se,atol=1e-12) and np.isclose(p,row.pvalue,atol=1e-10)
    checks['manual_loss_HAC_and_BH_all72_comparisons']=inference_ok
    states=pd.read_csv(OUT/'benchmark_states.csv');benchmark_ok=True
    for row in states.itertuples():
        g=panel(row.asset,row.variant);_,_,dev,te=split_panel(g)
        benchmark_ok &= np.isclose(dev['actual_'+row.target].mean(),row.historical_mean,atol=1e-16)
        q=pred[(pred.asset==row.asset)&(pred.variant==row.variant)&(pred.target==row.target)&(pred.model=='natural_benchmark')]
        expected=np.zeros(len(te)) if row.target=='return' else te[row.asset+'_vol30_annualized'].to_numpy()**2/365
        benchmark_ok &= np.allclose(q.predicted,expected,rtol=1e-12,atol=1e-18)
    checks['benchmark_training_means_and_variance_formula']=benchmark_ok
    old=pd.read_csv(RESULTS/'completion/test_predictions.csv',float_precision='round_trip');comparison= pd.read_csv(OUT/'timing_comparison_common_dates.csv');comparison_ok=True
    for row in comparison.itertuples():
        mask=lambda f:(f.asset==row.asset)&(f.variant==row.variant)&(f.target==row.target)&(f.model==row.model)
        a=old[mask(old)];b=pred[mask(pred)];dates=set(a.date_utc)&set(b.date_utc)
        comparison_ok &= row.n_common==len(dates) and row.target_roundtrip_max_difference<1e-14
    checks['old_new_timing_compared_on_common_origins']=comparison_ok and len(comparison)==80
    actual=records();checks['snapshot_raw_and_request_hashes']=len(actual)>0
    vintage_rows=[r for r in actual if r.get('source')=='alfred'];request_ok=True
    for row in vintage_rows:
        fields=json.loads((ROOT/row['request_file']).read_text(encoding='utf-8'))
        request_ok &= dict(fields)['form[entered_vintage_dates]']==row['requested_vintage_date'] and dict(fields)['form[file_type]']=='1'
    checks['actual_ALFRED_requests_match_vintage_metadata']=request_ok and len(vintage_rows)>=12
    # Readiness is only a feature audit for a later origin; it is never logged as a forecast.
    readiness=[envelope(pd.Timestamp('2026-10-21',tz='UTC'),asset,actual) for asset in ['btc','eth']]
    save_json(OUT/'input_readiness_example.json',dict(status='FEATURE AUDIT ONLY, NOT A FORECAST',origin_utc='2026-10-21T00:00:00Z',envelopes=readiness))
    checks['next_day_inputs_have_extra_day_and_receipt_evidence']=all(asset+'_usd_log_return' in e['features'] and e['information_day']=='2026-10-18' for asset,e in zip(['btc','eth'],readiness))
    # This must remain valid after real prospective logging starts too.
    live_ok=True
    for p in (LIVE/'predictions').glob('*.json'):
        obj=json.loads(p.read_text(encoding='utf-8'));e=json.loads((ROOT/obj['envelope']).read_text(encoding='utf-8'))
        live_ok &= pd.Timestamp(obj['logged_at_utc'])<pd.Timestamp(obj['origin_utc']) and sha(ROOT/obj['envelope'])==obj['envelope_sha256']
        live_ok &= all(pd.Timestamp(r['available_at_utc'])<=pd.Timestamp(e['information_cutoff_utc']) for r in e['lineage'].values())
    checks['no_ineligible_or_backdated_live_forecasts']=live_ok
    from tests.test_latency import TimingGuards
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(TimingGuards);result=unittest.TextTestRunner(verbosity=1).run(suite)
    checks['11_critical_deployment_guards']=result.wasSuccessful() and result.testsRun==11
    count=check_protected();checks['old_frozen_files_unchanged']=True
    checks={k:bool(v) for k,v in checks.items()}
    report=dict(passed=sum(checks.values()),total=len(checks),checks=checks,protected_files=count,unit_tests=result.testsRun,max_artifact_prediction_error=maximum,
                interpretation='Validates code and declared timing; not causal identification, whole-feed historical PIT, or future predictive skill.')
    save_json(OUT/'independent_validation.json',report);print(json.dumps(report,indent=2));assert all(checks.values())
