"""Independent chronology, sample, artifact and forecast checks."""
from src.evaluation.pit_nested_common import *
from research_completion import features, own, MACRO, USD, VARIANTS, model_predict, model_fit, losses
from src.evaluation.pit_feature_audit import spell_at, latest_values, same_numeric
from threadpoolctl import threadpool_limits
import joblib

def validate():
    init();checks=[];guards=[]
    def check(name,condition,detail=''):
        checks.append(dict(check=name,passed=bool(condition),detail=detail))
        assert condition,(name,detail)
    for name in ['prepared_input_lock.json','fit_code_lock.json']:
        lock=json.loads((OUT/name).read_text(encoding='utf-8'))
        check(name,all(sha(ROOT/n)==h for n,h in lock['files'].items()))
    audit=json.loads((OUT/'audit_summary.json').read_text(encoding='utf-8'))
    check('raw_reconstruction_all_checks',audit['checks']==audit['passed'] and audit['code_timing_violations_detected']==0)
    evidence=pd.read_csv(OUT/'feature_evidence.csv')
    check('every_feature_evidenced',set(evidence.feature)==set(own('btc')+own('eth')+MACRO+USD) and len(evidence)==15)
    panels={};shapeok=True;timingok=True;nativeok=True;oracleok=True
    for asset in ['btc','eth']:
        for variant in VARIANTS:
            for scenario in config()['scenarios']:
                g=read_panel(asset,variant,scenario);panels[asset,variant,scenario]=g;cols=features(asset,variant)
                nativeok &= g.index.is_unique and g.index.is_monotonic_increasing
                shapeok &= set(cols).issubset(g.columns) and not set(own(asset)+MACRO+USD).difference(cols).intersection(g.columns)
                lag=4 if scenario=='matched_asof_d4' else 3
                timingok &= bool((g.information_date==g.index-pd.Timedelta(days=lag)).all())
                timingok &= bool((g.label_assumed_available_utc==g.index+pd.Timedelta(days=2)).all())
                timingok &= bool((g.assumed_available_utc==g.information_date+pd.Timedelta(days=2)).all())
            base=panels[asset,variant,'matched_asof_d3'];oracle=panels[asset,variant,'matched_latest_d3'];delayed=panels[asset,variant,'matched_asof_d4']
            shapeok &= base.index.equals(oracle.index) and base.index.equals(delayed.index)
            unchanged=own(asset)+(['vix_change_lag1_proxy','sp500_log_return_lag1_proxy','gold_futures_log_return_lag1_proxy'] if not variant.endswith('_own') else [])
            oracleok &= np.array_equal(base[unchanged].to_numpy(),oracle[unchanged].to_numpy())
            oracleok &= np.array_equal(base.actual_return.to_numpy(),oracle.actual_return.to_numpy())
            old=pd.read_csv(ROOT/f'data/processed/latency_20261019/{asset}_{variant}.csv',parse_dates=['origin_utc'],float_precision='round_trip').set_index('origin_utc')
            native=panels[asset,variant,'native_asof_d3']
            nativeok &= native.index.equals(old.index) and np.array_equal(native[features(asset,variant)].to_numpy(),old[features(asset,variant)].to_numpy())
    check('declared_features_and_identical_matched_origin_sets',shapeok)
    check('calendar_lags_label_times_and_availability_independent',timingok)
    check('frozen_latency_panels_exactly_preserved_and_replayed',nativeok)
    check('oracle_does_not_change_own_market_or_targets',oracleok)
    inv=pd.read_csv(OUT/'model_inventory.csv');pred=pd.read_csv(OUT/'outer_predictions.csv',float_precision='round_trip');sel=pd.read_csv(OUT/'selected_parameters.csv');search=pd.read_csv(OUT/'inner_search.csv')
    check('640_artifacts_and_unique_predictions',len(inv)==640 and not pred.duplicated(['asset','variant','target','outer_year','scenario','model','origin_utc']).any())
    fitok=True;replayok=True;scalerok=True;allknown=True;replays=0;refitrows=[]
    with threadpool_limits(limits=2):
        for r in inv.to_dict('records'):
            artifact=joblib.load(ROOT/r['file']);g=panels[r['asset'],r['variant'],r['scenario']];year=int(r['outer_year']);start=pd.Timestamp(year,1,1)
            # Independent cutoff arithmetic, without training()/inner_splits().
            cutoff=start-pd.Timedelta(days=1)
            tr=g[(g.index<start)&(g.label_assumed_available_utc<=cutoff)]
            te=g[(g.index>=start)&(g.index<pd.Timestamp(year+1,1,1))];cols=features(r['asset'],r['variant']);y=tr['actual_'+r['target']]
            fitok &= sha(ROOT/r['file'])==r['sha256'] and len(tr)==r['n_fit'] and artifact['last_fit_label_available']==str(tr.label_assumed_available_utc.max())
            m=artifact['fitted'];scale=m[1]
            scalerok &= np.isclose(scale,float(y.mean()) if r['target']=='squared_return' else 1,rtol=1e-14,atol=0)
            if r['model']=='elastic_net':
                xs=m[0].regressor_.named_steps['standardscaler']
                scalerok &= np.allclose(xs.mean_,tr[cols].mean().to_numpy(),rtol=1e-12,atol=1e-12)
                expected=np.log(y.to_numpy()/scale+1e-12) if r['target']=='squared_return' else y.to_numpy()
                scalerok &= np.isclose(m[0].transformer_.mean_[0],expected.mean(),rtol=1e-12,atol=1e-12)
            q=pred[(pred.asset==r['asset'])&(pred.variant==r['variant'])&(pred.target==r['target'])&(pred.model==r['model'])&(pred.scenario==r['scenario'])&(pred.outer_year==year)].sort_values('origin_utc')
            p=model_predict(m,te[cols],r['model'],r['target']);replays+=len(p)
            replayok &= np.array_equal(pd.to_datetime(q.origin_utc).to_numpy(),te.index.to_numpy()) and np.allclose(q.predicted,p,rtol=1e-13,atol=1e-15)
            replayok &= np.array_equal(q.actual.to_numpy(),te['actual_'+r['target']].to_numpy())
            # Refit eight representative outer models (both assets/targets/learners),
            # complementing replay of all artifacts and all train-only scaler checks.
            if r['variant']=='common_usd' and r['scenario']=='matched_asof_d4' and year==2026:
                independent=model_fit(r['model'],artifact['parameters'],tr[cols],y,r['target'])
                rp=model_predict(independent,te[cols],r['model'],r['target'])
                error=float(abs(rp-p).max());refitrows.append(dict(**r,max_prediction_error=error))
                fitok &= bool(np.allclose(rp,p,rtol=1e-13,atol=1e-15))
    check('artifact_hashes_and_fit_labels_plus_eight_refits',fitok)
    check('all_640_frozen_predictions_replayed',replayok,str(replays))
    check('all_train_only_scaling_and_target_transforms',scalerok)
    print('Validated artifact replay, train-only transforms and representative refits:',replays,flush=True)
    for rec in [json.loads(p.read_text(encoding='utf-8')) for p in (OUT/'folds').glob('*.json')]:
        g=panels[rec['asset'],rec['variant'],rec['scenario']];year=rec['outer_year'];oc=pd.Timestamp(year,1,1)-pd.Timedelta(days=1)
        for t in rec['timing']:
            allknown &= pd.Timestamp(t['last_fit_label_available'])<=pd.Timestamp(t['fit_cutoff'])
            if t['stage']=='outer':allknown &= pd.Timestamp(t['last_tuning_label_available'])<=oc
        for selected in rec['selected']:
            rows=sorted([s for s in rec['search'] if s['model']==selected['model']],key=lambda r:r['grid_rank'])
            best=None
            for s in rows:
                inner=json.loads(s['inner_folds']);score=sum(t['sum_loss'] for t in inner)/sum(t['n'] for t in inner)
                allknown &= np.isclose(score,s['validation_loss'],rtol=1e-14)
                if best is None or score<best[0]-64*np.finfo(float).eps*max(1,abs(best[0])):best=(score,s['grid_rank'])
            allknown &= selected['grid_rank']==best[1]
    check('every_inner_outer_cutoff_and_parameter_selection',allknown)
    # Benchmark replay independent of learned model helper.
    bmok=True
    for key,q in pred[pred.model.isin(['historical_mean','natural_benchmark'])].groupby(['asset','variant','target','scenario','outer_year','model']):
        asset,variant,target,scenario,year,kind=key;g=panels[asset,variant,scenario];start=pd.Timestamp(year,1,1)
        tr=g[(g.index<start)&(g.label_assumed_available_utc<=start-pd.Timedelta(days=1))];q=q.sort_values('origin_utc')
        te=g.loc[pd.to_datetime(q.origin_utc)]
        expected=np.repeat(tr['actual_'+target].mean(),len(q)) if kind=='historical_mean' else np.zeros(len(q)) if target=='return' else te[asset+'_vol30_annualized'].to_numpy()**2/365
        bmok &= np.allclose(q.predicted,expected,rtol=1e-13,atol=1e-15)
    check('all_benchmarks_replayed_with_available_labels',bmok)
    lineage=pd.read_csv(OUT/'macro_row_lineage.csv',parse_dates=['information_date','previous_observation_date','observation_date','selected_record_revision_date','source_last_update_date'],float_precision='round_trip')
    q=lineage[lineage.observation_date.notna()]
    check('lineage_observation_and_revision_dates_not_future',bool(((q.observation_date<=q.information_date)&(q.selected_record_revision_date<=q.information_date)&(q.source_last_update_date<=q.information_date)).all()))
    from src.evaluation.pit_feature_audit import SERIES
    oraclevalues=True
    for sid,(name,kind) in SERIES.items():
        col=name+'_pit' if kind=='level' else name+'_pit_change'
        source='latest_same_observation_value' if kind=='level' else 'latest_same_observation_change'
        values=lineage[lineage.series==sid].set_index('information_date')[source]
        for asset in ['btc','eth']:
            g=panels[asset,'common_usd','matched_latest_d3']
            expected=values.reindex(pd.DatetimeIndex(g.information_date)).map(lambda v:float(format(v,'.12g')) if np.isfinite(v) else np.nan).to_numpy()
            oraclevalues &= np.array_equal(expected,g[col].to_numpy())
    check('oracle_values_use_exact_historical_observation_pair_lineage',oraclevalues)
    # End dates are inclusive. All latest spells used by the oracle must remain
    # active at the archive cutoff; an expired spell must not be resurrected.
    import io,zipfile
    from src.evaluation.pit_feature_audit import source_file
    spellchecks=[]
    for sid in SERIES:
        with zipfile.ZipFile(source_file(sid+'_alfred_realtime.zip')) as z:
            raw=pd.read_csv(io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith('.csv')))),na_values=['.'])
        raw['realtime_start_date']=pd.to_datetime(raw.realtime_start_date);raw['realtime_end_date']=pd.to_datetime(raw.realtime_end_date)
        current=raw[raw.realtime_start_date<=pd.Timestamp(config()['snapshot_end'])].sort_values(['period_start_date','realtime_start_date']).drop_duplicates('period_start_date',keep='last')
        expired=current.realtime_end_date.notna()&(current.realtime_end_date<pd.Timestamp(config()['snapshot_end']))
        spellchecks.append(dict(series=sid,latest_records=len(current),latest_expired_records=int(expired.sum())))
    csv(pd.DataFrame(spellchecks),'latest_archive_spell_check.csv')
    check('oracle_last_spells_active_at_frozen_archive_cutoff',all(r['latest_expired_records']==0 for r in spellchecks))
    print('Validated oracle observation pairs, withdrawals and active final spells.',flush=True)
    # Verify paired losses and BH implementation without the comparison helper.
    from statsmodels.stats.multitest import multipletests
    inferenceok=True
    for file in ['ablation_tests.csv','benchmark_tests.csv','sensitivity_tests.csv']:
        tests=pd.read_csv(OUT/file,float_precision='round_trip')
        p=tests.pvalue.to_numpy();order=np.argsort(p);raw=p[order]*len(p)/np.arange(1,len(p)+1)
        adjusted=np.minimum(1,np.minimum.accumulate(raw[::-1])[::-1]);manual=np.empty_like(p);manual[order]=adjusted
        inferenceok &= np.allclose(manual,tests.qvalue_bh,rtol=1e-13,atol=1e-15)
        for r in tests[tests.scope.astype(str)=='pooled'].to_dict('records'):
            z=pred[(pred.asset==r['asset'])&(pred.target==r['target'])]
            if file=='sensitivity_tests.csv':
                z=z[(z.model==r['model'])&(z.variant==r['variant'])]
                a=z[z.scenario==r['base']];b=z[z.scenario==r['changed']]
            elif file=='ablation_tests.csv':
                z=z[(z.model==r['model'])&(z.scenario==r['scenario'])]
                a=z[z.variant==r['base']];b=z[z.variant==r['added']]
            else:
                z=z[(z.variant==r['variant'])&(z.scenario==r['scenario'])]
                a=z[z.model==r['benchmark']];b=z[z.model==r['model']]
            joined=a[['origin_utc','actual','predicted']].merge(b[['origin_utc','predicted']],on='origin_utc',suffixes=('_a','_b'),validate='one_to_one')
            if r['target']=='return':d=(joined.actual-joined.predicted_b)**2-(joined.actual-joined.predicted_a)**2
            else:d=np.log(joined.predicted_b)+joined.actual/joined.predicted_b-np.log(joined.predicted_a)-joined.actual/joined.predicted_a
            inferenceok &= len(joined)==r['n'] and np.isclose(d.mean(),r['mean_loss_new_minus_base'],rtol=1e-11,atol=1e-14)
            inferenceok &= 0<=r['pvalue']<=1 and r['ci_low']<=r['ci_high']
    check('independent_paired_losses_and_manual_BH_all_families',inferenceok)
    # Reproduce first comparison's clustered bootstrap using explicit block lists
    # and scalar resampling, independently of bincount/vectorized ratio code.
    first=pd.read_csv(OUT/'ablation_tests.csv',float_precision='round_trip').iloc[0]
    z=pred[(pred.asset==first.asset)&(pred.target==first.target)&(pred.model==first.model)&(pred.scenario==first.scenario)]
    joined=z[z.variant==first['base']][['origin_utc','actual','predicted']].merge(z[z.variant==first.added][['origin_utc','predicted']],on='origin_utc',suffixes=('_a','_b'))
    d=((joined.actual-joined.predicted_b)**2-(joined.actual-joined.predicted_a)**2).to_numpy()
    blockids=pd.to_datetime(joined.origin_utc).to_numpy(dtype='datetime64[D]').astype('int64')//30
    blocks=[d[blockids==key] for key in sorted(set(blockids))];rng=np.random.default_rng(config()['inference']['seed']+1);resampled=[]
    for _ in range(999):
        draw=rng.integers(0,len(blocks),len(blocks));resampled.append(sum(blocks[i].sum() for i in draw)/sum(len(blocks[i]) for i in draw))
    resampled=np.asarray(resampled);ci=np.quantile(resampled,[.025,.975]);tol=64*np.finfo(float).eps*max(1,float(abs(d).max()))
    pvalue=1. if np.max(abs(d))<=tol else (1+int((abs(resampled-d.mean())>=abs(d.mean())).sum()))/1000
    check('independent_scalar_calendar_cluster_bootstrap',np.allclose(ci,[first.ci_low,first.ci_high],rtol=1e-11,atol=1e-15) and pvalue==first.pvalue)
    # Direct edge guards, using small counterexamples with known answers.
    raw=pd.DataFrame(dict(period_start_date=pd.to_datetime(['2020-01-01']*2+['2020-01-02']),realtime_start_date=pd.to_datetime(['2020-01-02','2020-01-04','2020-01-06']),realtime_end_date=pd.to_datetime(['2020-01-03',None,None]),X=[2.,np.nan,7.]))
    guards.append(dict(guard='withdrawn_value_not_resurrected',passed=len(spell_at(raw,'X',pd.Timestamp('2020-01-05')))==0))
    guards.append(dict(guard='unreleased_new_observation_not_admitted',passed=len(spell_at(raw,'X',pd.Timestamp('2020-01-03')))==1))
    latest=latest_values(raw,'X');guards.append(dict(guard='latest_missing_remains_missing',passed=pd.isna(latest.loc[pd.Timestamp('2020-01-01')])))
    fake=pd.DataFrame({'label_assumed_available_utc':pd.to_datetime(['2020-01-01','2020-01-02'])},index=pd.to_datetime(['2019-12-29','2019-12-30']))
    guards.append(dict(guard='fit_cutoff_has_additional_24h_buffer',passed=len(training(fake,'2020-01-02'))==1))
    dates=pd.date_range('2020-01-01','2022-12-31');fake=pd.DataFrame({'label_assumed_available_utc':dates+pd.Timedelta(days=2)},index=dates)
    inner=inner_splits(fake,2023)
    guards.append(dict(guard='last_inner_validation_labels_purged_before_outer_selection',passed=inner[-1][2].index.max()==pd.Timestamp('2022-12-29')))
    weekdays=pd.Series([10.,20.,30.],index=pd.to_datetime(['2020-01-03','2020-01-06','2020-01-07']));calendar=weekdays.reindex(pd.date_range('2020-01-03','2020-01-07'))
    guards.append(dict(guard='calendar_lag_does_not_mean_previous_available_row',passed=pd.isna(calendar.shift(1).loc['2020-01-06']) and weekdays.shift(1).loc['2020-01-06']==10))
    for guard in guards:guard['passed']=bool(guard['passed'])
    check('six_edge_guards',all(r['passed'] for r in guards))
    preserved=check_protected();check('all_preexisting_files_unchanged',preserved>1202,str(preserved))
    csv(pd.DataFrame(refitrows),'independent_refits.csv')
    save_json(OUT/'independent_validation.json',dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),checks=checks,guards=guards,passed=sum(r['passed'] for r in checks),total=len(checks),protected_files=preserved,forecast_values_replayed=replays,independent_refits=len(refitrows)))
    print('Independent checks:',len(checks),'guards:',len(guards),flush=True)
