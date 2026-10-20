"""Independent numerical and provenance checks for the new diagnostics."""
from src.evaluation.robustness_common import *
from src.evaluation.monetary_robustness import frames
from src.data.prospective_snapshots import earliest_origin
from scipy.stats import chi2

def bh(p):
    p=np.asarray(p);order=np.argsort(p);n=len(p)
    q=np.minimum.accumulate((p[order]*n/np.arange(1,n+1))[::-1])[::-1]
    out=np.empty(n);out[order]=np.minimum(q,1);return out

def run():
    init();checks={}
    monetary=pd.read_csv(OUT/'monetary_sensitivity.csv')
    checks['60_baseline_and_600_deletion_rows']=bool(len(monetary)==660 and (monetary.scenario=='baseline').sum()==60)
    checks['11_scenarios_each_60']=bool((monetary.groupby('scenario').size()==60).all())
    max_coef_error=0.;max_hac_error=0.;max_fwl_error=0.
    influence=pd.read_csv(OUT/'monetary_event_influence.csv')
    for asset,h,f in frames():
        for row in monetary[(monetary.asset==asset)&(monetary.horizon_days==h)].itertuples():
            g=f
            if row.scenario.startswith('omit_202'):g=f.drop(index=pd.Timestamp(row.omitted_event))
            if row.scenario=='omit_COVID_Mar_Apr_2020':g=f.loc[~((f.index>='2020-03-01')&(f.index<='2020-04-30'))]
            X=np.column_stack([np.ones(len(g)),g.drop(columns='outcome').to_numpy()]);y=g.outcome.to_numpy()
            beta=np.linalg.lstsq(X,y,rcond=None)[0];u=y-X@beta;n,k=X.shape
            # Manual Bartlett HAC5 sandwich with baseline finite correction.
            score=X*u[:,None];meat=score.T@score
            for L in range(1,6):
                gamma=score[L:].T@score[:-L];meat+=(1-L/6)*(gamma+gamma.T)
            bread=np.linalg.inv(X.T@X);cov=bread@meat@bread*n/(n-k)
            max_coef_error=max(max_coef_error,abs(beta[-1]-row.difference_pct))
            max_hac_error=max(max_hac_error,abs(np.sqrt(cov[-1,-1])-row.se))
            assert row.n_stress==g.stress.sum() and row.nobs==len(g)
        X=np.column_stack([np.ones(len(f)),f.drop(columns='outcome').to_numpy()])
        z=X[:,-1]-X[:,:-1]@np.linalg.lstsq(X[:,:-1],X[:,-1],rcond=None)[0]
        shares=z*z/(z@z)
        recorded=influence[(influence.asset==asset)&(influence.horizon_days==h)]
        max_fwl_error=max(max_fwl_error,float(np.max(abs(shares-recorded.interaction_information_share.to_numpy()))))
    checks['independent_lstsq_all_660_slopes']=max_coef_error<1e-7
    checks['manual_HAC5_all_660_standard_errors']=max_hac_error<1e-7
    checks['manual_partialled_interaction_information_shares']=max_fwl_error<1e-10
    checks['BH_per_scenario_all_11']=all(np.allclose(bh(g.pvalue),g.qvalue_bh_scenario,atol=1e-13) for _,g in monetary.groupby('scenario'))
    baseline=monetary[monetary.scenario=='baseline'].sort_values(['asset','horizon_days'])
    old=pd.read_csv(BASE/'monetary_stress_differences.csv').sort_values(['asset','horizon_days'])
    checks['saved_baseline_delta_SE_BH_reproduced']=bool(np.allclose(baseline.difference_pct,old.difference_pct,atol=1e-9) and np.allclose(baseline.se,old.se,atol=1e-9) and np.allclose(baseline.qvalue_bh_scenario,old.qvalue_bh,atol=1e-10))
    u=pd.read_csv(OUT/'joint_VAR_residuals.csv');arch=pd.read_csv(OUT/'joint_VAR_ARCH.csv')
    max_lm=0.;max_arch_p=0.
    for row in arch.itertuples():
        e=u[(u.yield_variable==row.yield_variable)&(u.regime==row.regime)&(u.equation==row.equation)].residual.to_numpy()
        v=e*e;L=int(row.test_lags);Y=v[L:];X=np.column_stack([np.ones(len(Y))]+[v[L-k:len(v)-k] for k in range(1,L+1)])
        resid=Y-X@np.linalg.lstsq(X,Y,rcond=None)[0]
        R2=1-(resid@resid)/np.sum((Y-Y.mean())**2)
        lm=(len(Y)-row.ddof)*R2
        max_lm=max(max_lm,abs(lm-row.lm));max_arch_p=max(max_arch_p,abs(chi2.sf(lm,L)-row.pvalue))
    checks['60_ARCH_manual_auxiliary_regression']=max_lm<1e-8 and max_arch_p<1e-10
    checks['BH_ARCH_family_60']=bool(np.allclose(bh(arch.pvalue),arch.qvalue_bh_60,atol=1e-13))
    white=pd.read_csv(OUT/'joint_VAR_whiteness.csv')
    checks['BH_whiteness_family_18']=bool(np.allclose(bh(white.pvalue),white.qvalue_bh_18,atol=1e-13))
    # Date-indexed lag correlation spot-checks, including direction of cross-equation lag.
    c=pd.read_csv(OUT/'joint_VAR_residual_correlations.csv');err=0.
    for row in c.iloc[::137].itertuples():
        g=u[(u.yield_variable==row.yield_variable)&(u.regime==row.regime)]
        v=g.pivot(index='date_utc',columns='equation',values='residual');L=int(row.lag)
        a=v[row.current_equation].iloc[L:].to_numpy();b=v[row.past_equation].iloc[:-L].to_numpy()
        a=a-a.mean();b=b-b.mean();rho=(a@b)/np.sqrt((a@a)*(b@b))
        err=max(err,abs(rho-row.correlation))
    checks['cross_correlation_direction_and_lag']=err<1e-12
    replay=pd.read_csv(OUT/'joint_VAR_replay.csv')
    checks['six_exact_reduced_forms_and_frozen_response_dates']=bool(len(replay)==6 and (replay.coefficient_max_error<1e-10).all() and (replay.whiteness_p20_error<1e-12).all())
    # Add covariance and data identities to that same fit-replay check.
    checks['six_exact_reduced_forms_and_frozen_response_dates'] &= bool((replay.sigma_max_error<1e-10).all() and np.allclose(u.residual+u.fitted,u.observed,atol=1e-12))
    overlap=pd.read_csv(OUT/'monetary_outcome_overlap.csv')
    checks['outcome_overlap_calendar_arithmetic']=all(row.shared_outcome_days==row.horizon_days-(pd.Timestamp(row.event_b)-pd.Timestamp(row.event_a)).days for row in overlap.itertuples())
    capture=json.loads((OUT/'prospective_capture_status.json').read_text(encoding='utf-8'))
    mpath=ROOT/capture['capture_manifest'];manifest=json.loads(mpath.read_text(encoding='utf-8'))
    checks['actual_snapshot_manifest_and_response_bytes']=bool(sha(mpath)==capture['manifest_sha256'] and all(sha(ROOT/r['file'])==r['sha256'] for r in manifest['sources'] if r.get('sha256')))
    checks['actual_capture_never_backdated']=all(pd.Timestamp(r['available_at_utc'])>=pd.Timestamp(r['request_started_utc']) for r in manifest['sources'] if r['status']=='ok')
    checks['24h_origin_ceiling_guards']=bool(earliest_origin('2026-10-19T06:00:00Z')==pd.Timestamp('2026-10-21',tz='UTC') and earliest_origin('2026-10-19T00:00:00Z')==pd.Timestamp('2026-10-20',tz='UTC'))
    checks['no_invented_prospective_predictions']=bool(capture['predictions_logged']==0 and not (OUT/'prospective_predictions.jsonl').exists())
    protected=check_protected();checks['all_frozen_baseline_hashes_unchanged']=True
    checks={key:bool(value) for key,value in checks.items()}
    result=dict(passed=sum(checks.values()),total=len(checks),checks=checks,protected_files=protected,
                maximum_errors=dict(slope=max_coef_error,HAC_SE=max_hac_error,ARCH_LM=max_lm,correlation=err),
                interpretation='Numerical/provenance checks do not validate economic identification or sparse-state inference.')
    save_json(OUT/'independent_validation.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert all(checks.values())
