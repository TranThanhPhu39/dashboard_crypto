"""Audit timing, paired samples, metrics, positive predictions and full state covariance."""
from research_common import *
from research_completion import OUT, VARIANTS, MACRO, USD, PIT, own, read_panel, split_panel, features, sha, model_fit, model_predict
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests
from threadpoolctl import threadpool_limits
import re


def main():
    checks={};snap=json.loads((OUT/'source_snapshot.json').read_text())
    checks['old_data_results_notebooks_and_delivery_ZIPs_unchanged']=all(sha(ROOT/p)==v for p,v in snap['protected_sha256'].items())
    checks['locked_design_unchanged']=sha(OUT/'design.json')==snap['design_sha256']
    source=pd.read_csv(ROOT/'data/processed/forecast_origins_vintage_macro.csv',parse_dates=['date_utc']).set_index('date_utc')
    checks['source_is_daily_calendar_before_lagging']=source.index.equals(pd.date_range(source.index.min(),source.index.max(),name='date_utc'))
    feature_ok=[];target_ok=[];vintage_ok=[];timing_ok=[];columns_ok=[];pair_ok=[];samples_ok=[]
    summary=pd.read_csv(OUT/'sample_summary.csv')
    for asset in ['btc','eth']:
        panels={v:read_panel(asset,v) for v in VARIANTS}
        for variant,f in panels.items():
            cols=features(asset,variant)
            # Re-index prior CALENDAR dates; do not call the production shift logic.
            reference=source.reindex(f.index-pd.Timedelta(days=1))
            feature_ok.append(np.allclose(f[cols],reference[cols],atol=1e-14,rtol=1e-12))
            target_ok.extend(np.allclose(f['actual_'+t],source.loc[f.index,asset+'_target_next_'+t],atol=1e-14,rtol=1e-12) for t in ['return','squared_return'])
            target_ok.append((f.target_date_utc==f.index+pd.Timedelta(days=1)).all() and (f.label_close_utc==f.index+pd.Timedelta(days=2)).all())
            timing_ok.append(((f.origin_utc-f.information_reference_close_utc)==pd.Timedelta(hours=24)).all())
            tr,va,dev,te=split_panel(f)
            timing_ok.append((tr.label_assumed_available_utc<=va.origin_utc.min()).all() and (dev.label_assumed_available_utc<=te.origin_utc.min()).all())
            timing_ok.append(tr.target_date_utc.lt('2023-01-01').all() and va.target_date_utc.between('2023-01-01','2024-12-31').all() and te.target_date_utc.ge('2025-01-01').all())
            for c in PIT:
                vint=pd.to_datetime(f[c+'_pit_vintage_date']);obs=pd.to_datetime(f[c+'_pit_obs_date'])
                vintage_ok.append((vint.dropna()<=f.information_row_date[vint.notna()]).all() and (obs.dropna()<=f.information_row_date[obs.notna()]).all())
            used=[c for c in f if c in own(asset)+MACRO+USD]
            columns_ok.append(used==cols and (variant=='common_usd' or not any(c in used for c in USD)))
            row=summary[(summary.asset==asset)&(summary.variant==variant)].iloc[0]
            samples_ok.append(row.n_rows==len(f) and row.test==len(te) and row.train==len(tr) and row.validation==len(va) and row.development==len(dev))
        for a,b in [('long_own','long_macro'),('common_own','common_macro'),('common_macro','common_usd')]:
            left,right=panels[a],panels[b]
            pair_ok.append(left.index.equals(right.index) and left[['actual_return','actual_squared_return','split']].equals(right[['actual_return','actual_squared_return','split']]))
    for name,values in [('features_are_exact_prior_calendar_information',feature_ok),('targets_still_next_UTC_day',target_ok),('vintages_and_observations_precede_information_cutoff',vintage_ok),('features_and_fitting_labels_obey_buffer',timing_ok),('only_declared_3_11_12_features_no_USD_leakage',columns_ok),('paired_own_macro_USD_samples_targets_splits_equal',pair_ok),('all_sample_counts_reconcile',samples_ok)]:checks[name]=all(values)
    pred=pd.read_csv(OUT/'test_predictions.csv',float_precision='round_trip');scores=pd.read_csv(OUT/'forecast_metrics.csv');search=pd.read_csv(OUT/'validation_search.csv');params=pd.read_csv(OUT/'selected_parameters.csv');selected=pd.read_csv(OUT/'validation_selected_models.csv')
    checks['prediction_keys_unique_and_expected_count']=not pred.duplicated(['asset','variant','target','model','date_utc']).any() and len(pred)==80*447 and len(scores)==80
    checks['all_predictions_finite_and_variance_strictly_positive']=np.isfinite(pred[['actual','predicted']]).all().all() and pred.loc[pred.target=='squared_return','predicted'].gt(0).all()
    checks['no_variance_prediction_near_old_floor']=pred.loc[pred.target=='squared_return','predicted'].gt(1e-12).all()
    metric_ok=[];actual_ok=[];bench_ok=[];refit_ok=[]
    for r in scores.itertuples():
        q=pred[(pred.asset==r.asset)&(pred.variant==r.variant)&(pred.target==r.target)&(pred.model==r.model)]
        e=q.actual-q.predicted
        metric_ok.append(np.isclose(r.rmse,np.sqrt(np.mean(e**2)),rtol=1e-10) and np.isclose(r.mae,np.mean(abs(e)),rtol=1e-10))
        if r.target=='squared_return':metric_ok.append(np.isclose(r.qlike,np.mean(np.log(q.predicted)+q.actual/q.predicted),rtol=1e-10))
        f=read_panel(r.asset,r.variant);tr,va,dev,te=split_panel(f)
        actual_ok.append(q.date_utc.tolist()==te.index.strftime('%Y-%m-%d').tolist() and np.allclose(q.actual,te['actual_'+r.target],atol=1e-14))
        if r.model=='historical_mean':bench_ok.append(np.allclose(q.predicted,dev['actual_'+r.target].mean(),atol=1e-14))
        if r.model=='natural_benchmark':bench_ok.append(np.allclose(q.predicted,0 if r.target=='return' else te[r.asset+'_vol30_annualized']**2/365,atol=1e-14))
        if r.model in ['elastic_net','gradient_boosting']:
            pr=params[(params.asset==r.asset)&(params.variant==r.variant)&(params.target==r.target)&(params.model==r.model)].iloc[0]
            tuning=search[(search.asset==r.asset)&(search.variant==r.variant)&(search.target==r.target)&(search.model==r.model)]
            best=tuning.loc[tuning.validation_objective.idxmin()]
            refit_ok.append(json.loads(pr.parameters)==json.loads(best.parameters) and np.isclose(r.validation_objective,best.validation_objective,rtol=1e-10) and pr.refit_n==len(dev))
            if r.target=='squared_return':refit_ok.append(np.isclose(pr.fit_target_scale,dev.actual_squared_return.mean(),rtol=1e-12))
    checks['all_80_metrics_recomputed']=all(metric_ok)
    checks['every_actual_and_test_date_matches_panel']=all(actual_ok)
    checks['benchmarks_use_only_available_labels_or_lagged_RMS']=all(bench_ok)
    checks['all_learned_parameters_selected_by_validation_only']=all(refit_ok) and len(search)==200
    selection_ok=[]
    for r in selected.itertuples():
        g=scores[(scores.asset==r.asset)&(scores.variant==r.variant)&(scores.target==r.target)]
        selection_ok.append(g.loc[g.validation_objective.idxmin(),'model']==r.model)
    checks['validation_winners_preserved_regardless_of_test']=all(selection_ok) and len(selected)==20
    tests_ok=[];bh_ok=[];test_errors=[]
    for filename in ['ablation_tests.csv','benchmark_tests.csv']:
        tests=pd.read_csv(OUT/filename)
        bh_ok.append(np.allclose(tests.qvalue_bh,multipletests(tests.pvalue,method='fdr_bh')[1],rtol=1e-10))
        for r in tests.itertuples():
            q=pred[(pred.asset==r.asset)&(pred.target==r.target)]
            if filename.startswith('ablation'):
                a=q[(q.variant==r.base)&(q.model==r.model)];b=q[(q.variant==r.added)&(q.model==r.model)]
            else:
                a=q[(q.variant==r.variant)&(q.model==r.benchmark)];b=q[(q.variant==r.variant)&(q.model==r.model)]
            a=a.sort_values('date_utc');b=b.sort_values('date_utc')
            if r.target=='return':d=(b.actual.to_numpy()-b.predicted.to_numpy())**2-(a.actual.to_numpy()-a.predicted.to_numpy())**2
            else:d=np.log(b.predicted.to_numpy()/a.predicted.to_numpy())+a.actual.to_numpy()*(1/b.predicted.to_numpy()-1/a.predicted.to_numpy())
            pa=a.predicted.to_numpy();pb=b.predicted.to_numpy()
            tied=np.max(abs(pa-pb))<=64*np.finfo(float).eps*max(np.max(abs(pa)),np.max(abs(pb)),np.finfo(float).tiny)
            if tied:d=np.zeros_like(d)
            n=len(d);res=d-d.mean();meat=res@res
            for lag in range(1,6):meat+=2*(1-lag/6)*(res[lag:]@res[:-lag])
            se=np.sqrt(max(0,meat*n/(n-1)))/n
            p=2*norm.sf(abs(d.mean()/se)) if se>0 else 1.
            ok=np.isclose(d.mean(),r.mean_loss_added_minus_base,atol=1e-12,rtol=1e-9) and np.isclose(se,r.hac_se,atol=1e-12,rtol=1e-8) and np.isclose(p,r.pvalue,atol=1e-8)
            tests_ok.append(ok)
            if not ok:test_errors.append(dict(file=filename,asset=r.asset,target=r.target,model=r.model,mean_recomputed=float(d.mean()),mean_saved=r.mean_loss_added_minus_base,se_recomputed=float(se),se_saved=r.hac_se,p_recomputed=float(p),p_saved=r.pvalue))
    checks['all_72_paired_HAC_tests_recomputed_manually']=all(tests_ok)
    checks['BH_families_32_and_40_recomputed']=all(bh_ok)
    # Representative deterministic re-fits verify the saved pipeline/transform results.
    reproduced=[]
    with threadpool_limits(limits=2):
        for asset,variant,target,kind in [('btc','common_own','return','elastic_net'),('btc','long_macro','squared_return','elastic_net'),('eth','common_usd','squared_return','gradient_boosting')]:
            f=read_panel(asset,variant);_,_,dev,te=split_panel(f);cols=features(asset,variant)
            pr=params[(params.asset==asset)&(params.variant==variant)&(params.target==target)&(params.model==kind)].iloc[0]
            fit=model_fit(kind,json.loads(pr.parameters),dev[cols],dev['actual_'+target],target);p=model_predict(fit,te[cols],kind,target)
            q=pred[(pred.asset==asset)&(pred.variant==variant)&(pred.target==target)&(pred.model==kind)]
            reproduced.append(np.allclose(p,q.predicted,rtol=1e-9,atol=1e-12))
    checks['three_representative_return_and_positive_variance_fits_reproduced']=all(reproduced)
    state=pd.read_csv(OUT/'state_responses.csv');cov=pd.read_csv(OUT/'state_covariance.csv');z=norm.ppf(.975)
    state_ok=[];manual_ok=[];old_ok=[]
    old=pd.read_csv(TABLES/'regime_interactions.csv');old=old[old.interaction=='stress_lag_vix_gt30']
    for asset in ['btc','eth']:
        panel=pd.read_csv(ROOT/f'data/processed/{asset}_econometric_sessions.csv',index_col=0)
        names=['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps','crypto_return_pct'];x=panel[names[:4]].copy()
        for lag in range(1,6):
            for c in names:x[f'L{lag}_{c}']=panel[c].shift(lag)
        x['regime']=panel.stress_lag
        for c in names[:4]:x[c+'_interaction']=panel[c]*panel.stress_lag
        for h in [0,1,5,10,20]:
            f=x.assign(outcome=sum(panel.crypto_return_pct.shift(-k) for k in range(h+1))).dropna()
            X=np.column_stack([np.ones(len(f)),f.drop(columns='outcome')]);y=f.outcome.to_numpy();beta=np.linalg.lstsq(X,y,rcond=None)[0]
            score=X*(y-X@beta)[:,None];meat=score.T@score;L=max(5,h+1)
            for lag in range(1,L+1):
                cross=score[lag:].T@score[:-lag];meat+=(1-lag/(L+1))*(cross+cross.T)
            bread=np.linalg.inv(X.T@X);V=bread@meat@bread*len(f)/(len(f)-X.shape[1]);columns=['const']+list(f.drop(columns='outcome'))
            for c,scale in zip(names[:4],[5.,1.,10.,10.]):
                r=cov[(cov.asset==asset)&(cov.shock==c)&(cov.horizon_sessions==h)].iloc[0];i=columns.index(c);j=columns.index(c+'_interaction')
                manual_ok.append(np.allclose([r.calm,r.difference,r.var_calm,r.var_difference,r.cov_calm_difference],[beta[i]*scale,beta[j]*scale,V[i,i]*scale**2,V[j,j]*scale**2,V[i,j]*scale**2],atol=1e-7,rtol=1e-7))
                prior=old[(old.asset==asset)&(old.shock==c)&(old.horizon_sessions==h)].iloc[0]
                old_ok.append(np.isclose(r.difference,prior.difference_pct,atol=1e-7))
                for regime in ['calm','stress']:
                    q=state[(state.asset==asset)&(state.shock==c)&(state.horizon_sessions==h)&(state.regime==regime)].iloc[0]
                    b=r.calm+(r.difference if regime=='stress' else 0);se=np.sqrt(r.var_calm+(r.var_difference+2*r.cov_calm_difference if regime=='stress' else 0))
                    state_ok.append(np.allclose([q.beta_pct,q.se,q.lower95,q.upper95],[b,se,b-z*se,b+z*se],atol=1e-10))
    checks['all_40_state_covariances_recomputed_by_matrix_HAC']=all(manual_ok)
    checks['all_80_Calm_Stress_CIs_include_covariance']=len(state)==80 and all(state_ok)
    checks['saved_stress_interaction_results_reproduced']=all(old_ok)
    episodes=pd.read_csv(OUT/'historical_analogues.csv');episode_ok=[]
    for (asset,shock,regime,h),g in episodes.groupby(['asset','shock','regime','horizon_sessions']):
        p=pd.read_csv(ROOT/f'data/processed/{asset}_econometric_sessions.csv',index_col=0);intervals=[]
        for r in g.sort_values('rank').itertuples():
            pos=p.index.get_loc(r.date_utc);intervals.append((pos,pos+h))
            episode_ok.append(p.index[pos+h]==r.end_date_utc and p.stress_lag.iloc[pos]==(regime=='stress') and np.isclose(p[shock].iloc[pos],r.shock_observed) and np.isclose(p.crypto_return_pct.iloc[pos:pos+h+1].sum(),r.observed_cumulative_pct,atol=1e-10))
        episode_ok.append(len(g)==5 and all(b<c or d<a for i,(a,b) in enumerate(intervals) for c,d in intervals[i+1:]))
    checks['all_400_analogues_actual_returns_states_and_nonoverlap_verified']=len(episodes)==400 and all(episode_ok)
    checks['no_optimizer_warnings']=json.loads((OUT/'fit_warnings.json').read_text())==[]
    result=dict(checks={k:bool(v) for k,v in checks.items()},n_checks=len(checks),passed=int(sum(checks.values())),note='Computational/design validation. No claim of fully timestamped PIT, causal identification or new untouched test.')
    write=OUT/'independent_validation.json';write.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));print(json.dumps(test_errors,indent=2));assert all(checks.values()),[k for k,v in checks.items() if not v]


if __name__=='__main__':main()
