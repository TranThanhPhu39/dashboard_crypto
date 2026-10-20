"""Independent sample, covariance, identification and provenance checks."""
from src.utils.project import *
from scipy import sparse
from scipy.optimize import linprog
from statsmodels.stats.multitest import multipletests
from threadpoolctl import threadpool_limits
import joblib,re

def matrix_HAC(y,X,L):
    b=np.linalg.lstsq(X,y,rcond=None)[0];res=y-X@b;score=X*res[:,None];meat=score.T@score
    for lag in range(1,L+1):
        cross=score[lag:].T@score[:-lag];meat+=(1-lag/(L+1))*(cross+cross.T)
    bread=np.linalg.inv(X.T@X);V=bread@meat@bread*len(y)/(len(y)-X.shape[1]);return b,V

def run():
    init();checks={};snap=json.loads((OUT/'source_snapshot.json').read_text());p=panel('calendar_information.csv')
    checks['all_previous_data_results_and_ZIPs_unchanged']=all(sha(ROOT/name)==v for name,v in snap['protected_sha256'].items())
    checks['design_locked_config_unchanged']=sha(CONFIG)==snap['config_sha256']
    f=pd.read_csv(ROOT/'data/processed/forecast_origins_vintage_macro.csv',parse_dates=['date_utc']).set_index('date_utc');d=pd.read_csv(ROOT/'data/processed/daily_research_latest.csv',parse_dates=['date_utc']).set_index('date_utc')
    checks['calendar_regular_UTC_days']=p.index.equals(pd.date_range(p.index.min(),p.index.max(),name='date_utc'))
    levels_ok=[];changes_ok=[];vintage_ok=[]
    for source,change,kind in [('broad_usd','usd_return_pct','log'),('us2y','us2y_change_bps','bps'),('us10y','us10y_change_bps','bps'),('fed_funds','fed_funds_change_bps','bps'),('nfci','nfci_change','diff')]:
        levels_ok.append(np.allclose(p[source+'_available'],f[source+'_pit'].shift(2).ffill(),equal_nan=True,rtol=1e-12))
        level=p[source+'_available'];diff=100*np.log(level).diff() if kind=='log' else level.diff()*(100 if kind=='bps' else 1)
        changes_ok.append(np.allclose(p[change],diff,equal_nan=True,rtol=1e-10,atol=1e-12))
        v=pd.to_datetime(p[source+'_pit_vintage_date']);vintage_ok.append((v.dropna()<=p.index[v.notna()]-pd.Timedelta(days=2)).all())
    checks['carry_only_last_admitted_levels_no_backfill']=all(levels_ok)
    checks['daily_changes_from_adjacent_levels_no_carrying_nonzero_shock']=all(changes_ok)
    checks['all_macro_vintage_dates_before_information_cutoff']=all(vintage_ok)
    checks['VIX_proxy_delayed_three_calendar_days']=np.allclose(p.vix_available_proxy,d.vix.shift(3).ffill(),equal_nan=True,rtol=1e-12)
    checks['no_PIT_USD_backcast_before_2019']=p.loc[:'2019-02-05','broad_usd_available'].isna().all()
    checks['crypto_returns_unchanged_not_forward_filled']=all(np.allclose(p[a+'_return_pct'],100*d[a+'_usd_log_return'],equal_nan=True,rtol=1e-12) for a in ['btc','eth'])
    daily=load('calendar_LP.csv');diff=load('calendar_stress_differences.csv');cov=load('calendar_state_covariance.csv');monetary=load('monetary_LP.csv');mdiff=load('monetary_stress_differences.csv')
    checks['daily_complete_1200_coefficients_every_horizon_1_to_30']=len(daily)==1200 and set(daily.horizon_days)==set(range(1,31)) and not daily.duplicated(['asset','regime','shock','horizon_days']).any()
    checks['monetary_complete_180_coefficients_every_horizon_1_to_30']=len(monetary)==180 and set(monetary.horizon_days)==set(range(1,31))
    for name,frame,mask,count in [('daily',daily,daily.regime.isin(['full','pre2020','post2020']),720),('monetary',monetary,monetary.regime=='full',60)]:
        q=frame[mask];checks[name+'_BH_family_recomputed']=len(q)==count and np.allclose(q.qvalue_bh,multipletests(q.pvalue,method='fdr_bh')[1],rtol=1e-10)
        checks[name+'_CI_arithmetic']=np.allclose(frame.lower95,frame.beta_pct-1.95996398454*frame.se,rtol=1e-10,atol=1e-10) and np.allclose(frame.upper95,frame.beta_pct+1.95996398454*frame.se,rtol=1e-10,atol=1e-10)
    checks['stress_difference_BH_240_and_60']=len(diff)==240 and len(mdiff)==60 and all(np.allclose(q.qvalue_bh,multipletests(q.pvalue,method='fdr_bh')[1],rtol=1e-10) for q in [diff,mdiff])
    # Independently build all calendar outcomes and regressions; verify samples and representative HAC matrices.
    sample_ok=[];numerical_ok=[];state_ok=[];buffer_ok=[]
    for asset in ['btc','eth']:
        for regime,g in [('full',p),('pre2020',p.loc[:'2019-12-31']),('post2020',p.loc['2020-01-01':])]:
            x=g[list(SHOCKS)].copy()
            for k in range(1,6):
                for c in list(SHOCKS)+[asset+'_return_pct']:x[f'L{k}_{c}']=g[c].shift(k+1 if c==asset+'_return_pct' else k)
            buffer_ok.append(np.allclose(x['L1_'+asset+'_return_pct'],g[asset+'_return_pct'].shift(2),equal_nan=True))
            for h in range(1,31):
                y=sum(g[asset+'_return_pct'].shift(-k) for k in range(h));frame=x.assign(outcome=y).dropna();rows=daily[(daily.asset==asset)&(daily.regime==regime)&(daily.horizon_days==h)]
                sample_ok.append(rows.nobs.eq(len(frame)).all())
                if h in [1,7,30]:
                    X=np.column_stack([np.ones(len(frame)),frame.drop(columns='outcome')]);b,V=matrix_HAC(frame.outcome.to_numpy(),X,max(5,h+1))
                    for j,(shock,scale) in enumerate(SHOCKS.items(),1):
                        r=rows[rows.shock==shock].iloc[0];numerical_ok.append(np.allclose([r.beta_pct,r.se],[b[j]*scale,np.sqrt(V[j,j])*scale],rtol=1e-7,atol=1e-7))
        for r in cov[cov.asset==asset].itertuples():
            for regime in ['calm','stress']:
                q=daily[(daily.asset==asset)&(daily.shock==r.shock)&(daily.regime==regime)&(daily.horizon_days==r.horizon_days)].iloc[0]
                beta=r.calm+(r.difference if regime=='stress' else 0);se=np.sqrt(r.var_calm+(r.var_difference+2*r.cov_calm_difference if regime=='stress' else 0))
                state_ok.append(np.allclose([q.beta_pct,q.se],[beta,se],rtol=1e-10,atol=1e-10))
    checks['all_daily_horizon_sample_counts_reconcile']=all(sample_ok)
    checks['all_own_lag_controls_start_Dminus2_buffered']=all(buffer_ok)
    checks['72_representative_daily_slopes_and_HAC_SE_recomputed']=all(numerical_ok)
    checks['all_480_Calm_Stress_slopes_include_cross_covariance']=all(state_ok)
    samples=load('monetary_LP_samples.csv');event_ok=[];scale_ok=[]
    events=pd.read_csv(ROOT/'data/processed/fomc_events_utc.csv');events=events[events.event_type=='statement'];source_mps=pd.read_csv(ROOT/'data/processed/fomc_policy_surprises.csv',parse_dates=['Date']).set_index('Date')
    for asset in ['btc','eth']:
        for h in range(1,31):
            s=samples[(samples.asset==asset)&(samples.horizon_days==h)];r=monetary[(monetary.asset==asset)&(monetary.regime=='full')&(monetary.horizon_days==h)].iloc[0]
            event_ok.append(len(s)==r.nobs)
            for row in s.itertuples():
                date=pd.Timestamp(row.date_utc);actual=100*d.loc[date+pd.Timedelta(days=1):date+pd.Timedelta(days=h),asset+'_usd_log_return'].sum()
                event_ok.append(np.isclose(actual,row.actual_cumulative_pct,atol=1e-10) and pd.Timestamp(row.outcome_start)==date+pd.Timedelta(days=1) and pd.Timestamp(row.outcome_end)==date+pd.Timedelta(days=h))
                scale_ok.append(np.isclose(row.STMT_10bps,source_mps.loc[date,'STMT']*10,atol=1e-12))
    checks['all_monetary_outcomes_exclude_event_day_and_match_daily_data']=all(event_ok)
    checks['monetary_STMT_units_correct_per10bps']=all(scale_ok)
    restrictions=load('recursive_SVAR_matrices.csv');matrix_ok=[];mat_keys=['yield_variable','regime','ordering']
    for key,g in restrictions.groupby(mat_keys):
        names=g.row.drop_duplicates().tolist();P=g.pivot(index='row',columns='column',values='P').loc[names,names].to_numpy();A=g.pivot(index='row',columns='column',values='A0').loc[names,names].to_numpy();S=g.pivot(index='row',columns='column',values='sigma').loc[names,names].to_numpy()
        matrix_ok.append(np.allclose(P@P.T,S,atol=1e-10) and np.allclose(A@S@A.T,np.eye(5),atol=1e-10) and np.allclose(np.triu(P,1),0,atol=1e-12))
    checks['all_18_recursive_SVAR_P_A0_covariance_identities']=len(matrix_ok)==18 and all(matrix_ok)
    search=load('joint_VAR_lag_search.csv');vard=load('joint_VAR_diagnostics.csv');lag_ok=[]
    for (yield_name,regime),g in search.groupby(['yield_variable','regime']):
        r=vard[(vard.yield_variable==yield_name)&(vard.regime==regime)].iloc[0];lag_ok.append(g.nobs.nunique()==1 and r.lag==g.loc[g.bic.idxmin(),'lag'])
    checks['all_joint_VAR_lags_selected_on_common_dates']=all(lag_ok)
    irf=load('joint_VAR_IRF.csv');checks['joint_IRF_complete_three_orders_two_assets_yields_periods']=len(irf)==3348 and np.isfinite(irf[['response_pct','se','lower95','upper95']]).all().all()
    checks['crypto_first_restriction_imposes_zero_macro_impact_on_crypto']=irf[(irf.ordering=='crypto_first')&(irf.horizon_sessions==0)].response_pct.abs().le(1e-12).all()
    q=load('quantile_effects.csv');draws=load('quantile_bootstrap_draws.csv');qchecks=[]
    for r in q.itertuples():
        v=draws[(draws.asset==r.asset)&(draws.regime==r.regime)&(draws.tau==r.tau)&(draws.shock==r.shock)].beta_pct
        qchecks.append(len(v)==r.successful_bootstraps and r.successful_bootstraps>=80 and np.allclose(np.quantile(v,[.025,.975]),[r.lower95,r.upper95],rtol=1e-10))
    checks['all_72_quantile_bootstrap_intervals_reconcile']=len(q)==72 and all(qchecks)
    warnings=json.loads((OUT/'quantile_warnings.json').read_text());checks['main_quantile_fits_converged_and_failed_bootstraps_disclosed']=not any(r['replicate']=='main' for r in warnings) and len(warnings)==1782-len(draws)//4
    # An exact LP solver independently checks the quantile objective on two representative fits.
    objectives=[]
    for asset,tau in [('btc',.05),('eth',.95)]:
        x=p[list(SHOCKS)].copy();x['prior_crypto']=p[asset+'_return_pct'].shift(2);g=x.assign(y=p[asset+'_return_pct']).dropna();raw=g.drop(columns='y');X=np.column_stack([np.ones(len(g)),((raw-raw.mean())/raw.std(ddof=0))]);y=g.y.to_numpy();n=len(y);k=X.shape[1]
        result=linprog(np.r_[np.zeros(k),np.repeat(tau,n),np.repeat(1-tau,n)],A_eq=sparse.hstack([sparse.csr_matrix(X),sparse.eye(n),-sparse.eye(n)],format='csr'),b_eq=y,bounds=[(None,None)]*k+[(0,None)]*(2*n),method='highs');assert result.success
        # QuantReg IRLS is also reproduced to compare pinball objective (slopes alone omit intercept/lag).
        from statsmodels.regression.quantile_regression import QuantReg
        with threadpool_limits(limits=2):fit=QuantReg(y,X).fit(q=tau,max_iter=5000,p_tol=1e-7)
        residual=y-X@fit.params;loss=np.where(residual>=0,tau*residual,(tau-1)*residual).sum();objectives.append(loss-result.fun<.001)
    checks['quantile_IRLS_objectives_match_independent_linear_program']=all(objectives)
    inventory=load('model_inventory.csv');artifact_ok=[]
    prior=pd.read_csv(RESULTS/'completion/test_predictions.csv',float_precision='round_trip')
    from research_completion import read_panel,split_panel,model_predict
    with threadpool_limits(limits=2):
        for r in inventory.itertuples():
            path=ROOT/r.file;assert sha(path)==r.sha256;model=joblib.load(path);_,_,_,te=split_panel(read_panel(r.asset,r.variant));pred=model_predict(model['fitted'],te[model['features']],r.model,r.target);ref=prior[(prior.asset==r.asset)&(prior.variant==r.variant)&(prior.target==r.target)&(prior.model==r.model)]
            artifact_ok.append(np.allclose(pred,ref.predicted,atol=1e-12,rtol=1e-9))
    checks['all_40_saved_model_hashes_and_predictions_reproduced']=len(inventory)==40 and all(artifact_ok)
    importance=load('validation_group_importance.csv');checks['importance_uses_validation_repeats_not_test']=set(importance.repeat)==set(range(10)) and importance.circular_shift.between(30,471).all() and np.isfinite(importance.loss_increase).all()
    binance=[]
    for symbol in ['BTCUSDT','ETHUSDT']:
        frame=pd.read_csv(PANELS/f'{symbol}_daily.csv',parse_dates=['date_utc']);complete=frame.close_time_ms-frame.open_time_ms==86399999
        expected=np.log(frame.close.where(complete)).diff()
        binance.append(frame.date_utc.is_unique and frame.date_utc.min()==pd.Timestamp('2017-08-17') and frame.date_utc.max()==pd.Timestamp('2026-10-15') and frame.full_utc_bar.eq(complete).all() and np.allclose(frame.log_return,expected,equal_nan=True,atol=1e-12))
    checks['Binance_partial_bars_flagged_and_not_used_as_UTC_returns']=all(binance)
    logs=json.loads((OUT/'binance_source_log.json').read_text());checks['Binance_successful_raw_payload_hashes_present']=len(logs)>=2 and all(r.get('status')=='ok' for r in logs)
    # Each metadata file names the exact cached request payload.
    checks['every_Binance_cache_matches_provenance_SHA256']=all(sha(path.with_name(path.name.removesuffix('.meta.json')+'.json'))==json.loads(path.read_text())['sha256'] for path in (RAW/'binance').glob('*.meta.json'))
    protocol=json.loads((OUT/'prospective_protocol.json').read_text());checks['new_untouched_test_not_fabricated']=protocol['status'].startswith('NOT RUN') and protocol['inventory_sha256']==sha(OUT/'model_inventory.csv')
    # Validate links only after the product stage; output has no implicit dependencies on internet.
    links=[]
    for path in [OUT/'report.html',ROOT/'dashboard/index.html']:
        for href in re.findall(r'(?:href|src)="([^"]+)"',path.read_text(encoding='utf-8')):
            if href.startswith(('http','#','data:')):continue
            target=(path.parent/href).resolve();links.append(target.exists() or target==(OUT/'independent_validation.json').resolve())
    checks['all_report_dashboard_local_links_and_images_exist']=all(links)
    source=(ROOT/'dashboard/index.html').read_text(encoding='utf-8');checks['dashboard_offline_payload_complete']='__PAYLOAD__' not in source and 'fetch(' not in source and '<script src=' not in source
    result=dict(checks={k:bool(v) for k,v in checks.items()},n_checks=len(checks),passed=int(sum(checks.values())),note='Computational/provenance checks, not proof of causal identification, fully archived PIT or a new untouched test.')
    save_json(OUT/'independent_validation.json',result);print(json.dumps(result,indent=2));assert all(checks.values()),[k for k,v in checks.items() if not v]
