"""Independent checks of author replication, sample alignment and conditional inference."""
from src.evaluation.fomc_identification_common import *
from src.models.fomc_identification import design
from scipy.stats import norm
import unittest

def bh(p):
    p=np.asarray(p);order=np.argsort(p);n=len(p);q=np.minimum.accumulate((p[order]*n/np.arange(1,n+1))[::-1])[::-1];out=np.empty(n);out[order]=np.minimum(q,1);return out

def sandwich(X,y):
    beta=np.linalg.lstsq(X,y,rcond=None)[0];e=y-X@beta;score=X*e[:,None];meat=score.T@score
    for L in range(1,6):
        gamma=score[L:].T@score[:-L];meat+=(1-L/6)*(gamma+gamma.T)
    n,k=X.shape;bread=np.linalg.inv(X.T@X);cov=bread@meat@bread*n/(n-k)
    return beta,cov

def run():
    init();checks={};manifest=json.loads((RAW/'author/manifest.json').read_text())
    checks['pinned_author_source_hashes']=all(sha(ROOT/r['file'])==r['sha256'] and manifest['commit'] in r['url'] for r in manifest['sources'])
    lock=json.loads((OUT/'analysis_lock.json').read_text());checks['pre_fit_design_membership_lock']=lock['config_sha256']==sha(CONFIG) and lock['panel_sha256']==sha(PANELS/'analysis_panel.csv') and lock['event_audit_sha256']==sha(OUT/'event_audit.csv')
    f=pd.read_csv(PANELS/'analysis_panel.csv',float_precision='round_trip');a=pd.read_csv(OUT/'event_audit.csv');est=pd.read_csv(OUT/'timing_estimates.csv');rot=pd.read_csv(OUT/'author_rotation_shocks.csv')
    author=pd.read_csv(RAW/'author/shocks_fed_jk_t.csv',float_precision='round_trip');M=author[['pc1','SP500']].to_numpy();valid=np.isfinite(M).all(axis=1);A=M[valid]
    # Cholesky of uncentered Gram matrix provides an independent route to the QR factor.
    R=np.linalg.cholesky(A.T@A).T;Q=A@np.linalg.inv(R);orth_error=0.;replay_error=0.
    impacts=pd.read_csv(OUT/'author_rotation_impacts.csv')
    for w in [.1,.5,.9]:
        C=impacts[impacts.weight==w].iloc[0];angle=C.angle;c,s=np.cos(angle),np.sin(angle)
        D=np.diag([R[0,0]*c,R[0,0]*s]);U=Q@np.array([[c,s],[-s,c]])@D
        recorded=rot[rot.weight==w].loc[valid,['policy_component','information_component']].to_numpy()
        orth_error=max(orth_error,float(abs((U.T@U)[0,1])));replay_error=max(replay_error,float(np.max(abs(U-recorded))))
        assert C.policy_to_stock<0<C.information_to_stock
        assert np.allclose(U.sum(axis=1),A[:,0],atol=1e-12)
    checks['independent_Cholesky_rotation_and_sign_restrictions']=replay_error<1e-10 and orth_error<1e-10
    good=rot[(rot.weight==.5)&rot.input_complete]
    checks['published_median_shocks_reproduced']=bool(np.max(abs(good[['policy_component','information_component']].to_numpy()-good[['published_policy','published_information']].to_numpy()))<2e-8)
    # PCA independently via the eigenvector of the uncentered standardized Gram matrix.
    source=pd.read_csv(RAW/'author/source_data/fomc_surprises_jk.csv',float_precision='round_trip');source=source[pd.to_datetime(source.start).dt.year>1989]
    X=source[['MP1','FF4','ED2','ED3','ED4']].to_numpy();missing=np.isnan(X).all(axis=1);X=np.nan_to_num(X,nan=0.);X=X/X.std(axis=0,ddof=1)
    vals,vectors=np.linalg.eigh(X.T@X);v=vectors[:,np.argmax(vals)]
    if v[np.argmax(abs(v))]<0:v=-v
    score=X@v;score[missing]=np.nan;pc=np.round(score/np.nanstd(score,ddof=1)*source.ED4.std(),8)
    checks['PCA_independent_eigendecomposition']=bool(np.nanmax(abs(pc-author.pc1.to_numpy()))<2e-8)
    checks['missing_author_stock_inputs_not_zero_imputed']=bool(rot.loc[~rot.input_complete,['policy_component','information_component']].isna().all().all() and a.loc[a.shock_input_complete,'author_stock_log_pct'].notna().all())
    membership={}
    for asset in ['BTC','ETH']:
        g=f[(f.asset==asset)&f.primary_joint];membership[asset]=set(g.date)
        assert len(g)==len(membership[asset])*32
        assert (g.groupby('outcome').date.apply(set).apply(lambda s:s==membership[asset])).all()
    checks['identical_events_both_assets_all32_outcomes']=membership['BTC']==membership['ETH'] and len(membership['BTC'])>0
    checks['scheduled_exact_timestamp_shocks_only']=bool(a[a.primary_joint].scheduled.all() and a[a.primary_joint].author_exact_match.all() and a[a.primary_joint].shock_input_complete.all())
    times=pd.to_datetime(a.event_time_et,utc=True);utc=pd.to_datetime(a.event_time_utc,utc=True)
    checks['ET_UTC_timestamp_alignment']=bool((times==utc).all())
    minute_errors=[]
    for row in a[a.primary_joint].itertuples():
        assert sha(ROOT/row.minute_file)==row.minute_sha256
        values=json.loads((ROOT/row.minute_file).read_bytes());lookup={int(v[0]):float(v[4]) for v in values};t=int(pd.Timestamp(row.event_time_utc).timestamp())
        needed=list(range(t-11*60,t+20*60,60));assert all(n in lookup for n in needed) and len(needed)==31
        y=100*np.log(lookup[t+19*60]/lookup[t-11*60]);ref=f[(f.asset==row.asset)&(f.date==row.date)&(f.outcome=='intraday')].actual_pct.iloc[0]
        minute_errors.append(abs(y-ref))
    checks['all_primary_minute_boundaries_and31_candles']=max(minute_errors)<1e-10
    daily_error=control_error=0.
    for asset in ['BTC','ETH']:
        raw=pd.read_csv(PANELS/f'{asset}_Coinbase_daily.csv',parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc')
        closes=raw.close
        for row in f[(f.asset==asset)&f.primary_joint].itertuples():
            day=pd.Timestamp(row.date)
            if row.outcome=='intraday':continue
            if row.outcome=='event_day':expected=100*np.log(closes.loc[day]/closes.loc[day-pd.Timedelta(days=1)])
            else:
                h=int(row.outcome.split('_')[1]);expected=100*np.log(closes.loc[day+pd.Timedelta(days=h)]/closes.loc[day])
                assert closes.reindex(pd.date_range(day,day+pd.Timedelta(days=h))).notna().all()
            daily_error=max(daily_error,abs(expected-row.actual_pct))
        for row in a[(a.asset==asset)&a.primary_joint].itertuples():
            day=pd.Timestamp(row.date)-pd.Timedelta(days=2);prices=closes.reindex(pd.date_range(day-pd.Timedelta(days=30),day))
            returns=np.log(prices.to_numpy()[1:]/prices.to_numpy()[:-1]);control_error=max(control_error,abs(100*returns[-1]-row.prior_return),abs(np.sqrt(365*np.mean(returns**2))-row.prior_vol30))
    checks['daily_and_post_outcomes_same_venue_exact_UTC_days']=daily_error<1e-10
    checks['prior_controls_are_backward_only']=control_error<1e-10
    max_beta=max_se=max_p=0.
    for key,g in est.groupby(['asset','outcome','regime']):
        asset,outcome,regime=key;d=f[(f.asset==asset)&f.primary_joint&(f.outcome==outcome)].sort_values('date').reset_index(drop=True)
        if regime!='full':d=d[d.post2020==(regime=='post2020')]
        X=design(d,.5,rot).to_numpy();y=d.actual_pct.to_numpy();beta,cov=sandwich(X,y)
        for row in g.itertuples():
            i=1 if row.shock=='policy' else 2;se=np.sqrt(cov[i,i]);p=2*norm.sf(abs(beta[i]/se))
            max_beta=max(max_beta,abs(beta[i]-row.beta_pct_per10bps));max_se=max(max_se,abs(se-row.se));max_p=max(max_p,abs(p-row.pvalue))
    checks['all384_coefficients_manual_OLS_HAC5']=max_beta<1e-8 and max_se<1e-8 and max_p<1e-8
    checks['BH128_full_and256_periods']=bool(np.allclose(bh(est.loc[est.regime=='full','pvalue']),est.loc[est.regime=='full','qvalue_bh'],atol=1e-12) and np.allclose(bh(est.loc[est.regime!='full','pvalue']),est.loc[est.regime!='full','qvalue_bh'],atol=1e-12))
    diff=pd.read_csv(OUT/'timing_difference_tests.csv');diff_error=0.
    for row in diff.itertuples():
        outcome=row.comparison.replace('_minus_intraday','');d=f[(f.asset==row.asset)&f.primary_joint]
        wide=d.pivot(index='date',columns='outcome',values='actual_pct');g=d[d.outcome=='intraday'].sort_values('date').reset_index(drop=True)
        X=design(g,.5,rot).to_numpy();y=(wide[outcome]-wide.intraday).reindex(g.date).to_numpy();b,v=sandwich(X,y);i=1 if row.shock=='policy' else 2
        diff_error=max(diff_error,abs(b[i]-row.difference_pct_per10bps),abs(np.sqrt(v[i,i])-row.se))
    checks['direct_timing_differences_include_cross_covariance']=diff_error<1e-8 and np.allclose(bh(diff.pvalue),diff.qvalue_bh8,atol=1e-12)
    loo=pd.read_csv(OUT/'leave_one_event_out.csv');loo_error=0.
    for asset in ['BTC','ETH']:
        d=f[(f.asset==asset)&f.primary_joint];g=d[d.outcome=='intraday'].sort_values('date').reset_index(drop=True);X=design(g,.5,rot).to_numpy()
        Y=d.pivot(index='date',columns='outcome',values='actual_pct').reindex(g.date)
        for i,day in enumerate(g.date):
            keep=np.arange(len(X))!=i;B=np.linalg.lstsq(X[keep],Y.to_numpy()[keep],rcond=None)[0]
            recorded=loo[(loo.asset==asset)&(loo.omitted_date==day)].pivot(index='outcome',columns='shock',values='beta_pct_per10bps').reindex(Y.columns)
            loo_error=max(loo_error,float(np.max(abs(recorded.policy.to_numpy()-B[1]))),float(np.max(abs(recorded.information.to_numpy()-B[2]))))
    checks['all9600_case_deletion_coefficients_independently_refit']=loo_error<1e-8 and len(loo)==len(membership['BTC'])*128
    spec=json.loads((OUT/'influence_diagnostic_spec.json').read_text());checks['posthoc_influence_disclosed']=spec['status'].startswith('Post-hoc')
    source_log=json.loads((OUT/'daily_source_log.json').read_text());checks['all_Coinbase_daily_source_hashes']=all(sha(ROOT/r['file'])==r['sha256'] for r in source_log)
    from tests.test_fomc_identification import IdentificationGuards
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IdentificationGuards);result=unittest.TextTestRunner(verbosity=1).run(suite)
    checks['five_identification_and_boundary_guards']=result.wasSuccessful() and result.testsRun==5
    count=check_protected();checks['all_previous_outputs_models_protocols_and_ZIPs_unchanged']=True
    checks={k:bool(v) for k,v in checks.items()}
    report=dict(passed=sum(checks.values()),total=len(checks),checks=checks,protected_files=count,unit_tests=result.testsRun,
                maximum_errors=dict(median_rotation=replay_error,coefficients=max_beta,HAC_se=max_se,timing_difference=diff_error,leave_one_out=loo_error),
                interpretation='Numerical/alignment checks; no validation of exclusion/sign assumptions or full generated-shock uncertainty.')
    save_json(OUT/'independent_validation.json',report);print(json.dumps(report,indent=2));assert all(checks.values())
