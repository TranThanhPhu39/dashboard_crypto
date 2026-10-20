"""Replay frozen monetary LP and diagnose sparse stress-event influence."""
from src.evaluation.robustness_common import *
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from itertools import combinations

def frames():
    p = pd.read_csv(PANELS / 'calendar_information.csv', parse_dates=['date_utc']).set_index('date_utc')
    d = pd.read_csv(ROOT / 'data/processed/daily_research_latest.csv', parse_dates=['date_utc']).set_index('date_utc')
    e = pd.read_csv(ROOT / 'data/processed/fomc_events_utc.csv')
    e = e[e.event_type == 'statement'].copy()
    e['date_utc'] = pd.to_datetime(e.event_time_utc, utc=True).dt.tz_localize(None).dt.normalize()
    surprises = pd.read_csv(ROOT / 'data/processed/fomc_policy_surprises.csv', parse_dates=['Date']).set_index('Date')
    e = e.set_index('date_utc').join(surprises[['STMT']])
    for asset in ['btc', 'eth']:
        x = pd.DataFrame(index=e.index)
        x['monetary'] = e.STMT * 10
        x['prior_return'] = p[asset + '_prior_return_pct'].reindex(x.index)
        x['prior_vol30'] = p[asset + '_prior_vol30'].reindex(x.index)
        x['prior_vix'] = p.vix_available_proxy.reindex(x.index)
        x['stress'] = p.stress.reindex(x.index)
        x['monetary_stress'] = x.monetary * x.stress
        for h in range(1, 31):
            returns = 100 * d[asset + '_usd_log_return']
            y = sum(returns.shift(-k) for k in range(1, h + 1)).reindex(x.index)
            yield asset, h, x.assign(outcome=y).dropna()

def fit(frame):
    return sm.OLS(frame.outcome, sm.add_constant(frame.drop(columns='outcome'))).fit(
        cov_type='HAC', cov_kwds={'maxlags': 5, 'use_correction': True})

def run():
    init()
    rows, influence, overlaps, support, residuals = [], [], [], [], []
    old = pd.read_csv(BASE / 'monetary_stress_differences.csv')
    replay_error = 0.
    for asset, h, f in frames():
        r = fit(f)
        ref = old[(old.asset == asset) & (old.horizon_days == h)].iloc[0]
        replay_error = max(replay_error, abs(r.params.monetary_stress - ref.difference_pct),
                           abs(r.bse.monetary_stress - ref.se))
        stress_dates = f.index[f.stress == 1]
        scenarios = [('baseline', None, f)]
        scenarios += [('omit_' + date.strftime('%Y-%m-%d'), str(date.date()), f.drop(index=date)) for date in stress_dates]
        scenarios += [('omit_COVID_Mar_Apr_2020', None, f.loc[~((f.index >= '2020-03-01') & (f.index <= '2020-04-30'))])]
        for scenario, omitted, g in scenarios:
            rr = r if scenario == 'baseline' else fit(g)
            v = rr.cov_params()
            delta, calm = float(rr.params.monetary_stress), float(rr.params.monetary)
            rows.append(dict(asset=asset, horizon_days=h, scenario=scenario, omitted_event=omitted,
                             difference_pct=delta, se=float(rr.bse.monetary_stress), pvalue=float(rr.pvalues.monetary_stress),
                             lower95=delta-1.95996398454*rr.bse.monetary_stress, upper95=delta+1.95996398454*rr.bse.monetary_stress,
                             calm_pct=calm, stress_pct=calm+delta,
                             stress_se=float(np.sqrt(v.loc['monetary','monetary']+v.loc['monetary_stress','monetary_stress']+2*v.loc['monetary','monetary_stress'])),
                             nobs=len(g), n_stress=int(g.stress.sum()), rank=int(np.linalg.matrix_rank(rr.model.exog)),
                             condition_number=float(rr.condition_number), sparse_stress=bool(g.stress.sum()<10),
                             change_from_baseline=delta-float(r.params.monetary_stress),
                             sign_change=bool(delta*r.params.monetary_stress<0)))
        # Conventional OLS influence quantities describe sensitivity; their distributional
        # cutoffs are not used as deletion rules under heteroskedasticity/dependence.
        infl = r.get_influence()
        X = pd.DataFrame(r.model.exog, index=f.index, columns=r.model.exog_names)
        z = X.monetary_stress - sm.OLS(X.monetary_stress, X.drop(columns='monetary_stress')).fit().fittedvalues
        shares = z**2 / np.sum(z**2)
        for i, date in enumerate(f.index):
            influence.append(dict(asset=asset, horizon_days=h, date_utc=str(date.date()), stress=int(f.loc[date,'stress']),
                                  monetary_10bps=float(f.loc[date,'monetary']), leverage=float(infl.hat_matrix_diag[i]),
                                  cooks_distance=float(infl.cooks_distance[0][i]),
                                  residual_standardized_internal=float(infl.resid_studentized_internal[i]),
                                  interaction_information_share=float(shares.loc[date])))
            residuals.append(dict(asset=asset,horizon_days=h,date_utc=str(date.date()),actual_pct=float(f.outcome.iloc[i]),
                                  fitted_pct=float(r.fittedvalues.iloc[i]),residual_pct=float(r.resid.iloc[i])))
        pairs = list(combinations(f.index, 2))
        for a,b in pairs:
            shared = max(0,h-int((b-a).days))
            if shared:
                overlaps.append(dict(asset=asset,horizon_days=h,event_a=str(a.date()),event_b=str(b.date()),shared_outcome_days=shared,
                                     both_stress=bool(f.loc[a,'stress']==1 and f.loc[b,'stress']==1)))
        for label, dates in [('all',f.index),('stress',stress_dates)]:
            dates=dates.sort_values()
            # Adjacent intervals share an outcome day iff gap<h. Components are
            # a geometric overlap description, never an estimate of independent n.
            components=0 if len(dates)==0 else 1+int((dates.to_series().diff().dt.days.dropna()>=h).sum())
            n_pairs=sum(max(0,h-int((b-a).days))>0 for a,b in combinations(dates,2))
            support.append(dict(asset=asset,horizon_days=h,subset=label,n_events=len(dates),
                                overlap_pairs=n_pairs,overlap_components=components,
                                max_positive_surprise_bps=float(f.loc[dates,'monetary'].max()*10),
                                min_surprise_bps=float(f.loc[dates,'monetary'].min()*10)))
    result=pd.DataFrame(rows)
    result['qvalue_bh_scenario']=result.groupby('scenario').pvalue.transform(lambda p:multipletests(p,method='fdr_bh')[1])
    write_csv(result,'monetary_sensitivity.csv')
    write_csv(pd.DataFrame(influence),'monetary_event_influence.csv')
    write_csv(pd.DataFrame(overlaps),'monetary_outcome_overlap.csv')
    write_csv(pd.DataFrame(support),'monetary_support.csv')
    write_csv(pd.DataFrame(residuals),'monetary_baseline_residuals.csv')
    assert replay_error<1e-9, replay_error
    save_json(OUT/'monetary_replay.json',dict(max_coefficient_or_se_error=replay_error,baseline_unchanged=True,
               caution='Deletion scenarios are post-hoc diagnostics; event-row HAC adjacency changes after deletion; sparse-state inference and horizon overlap remain.'))
    print('Monetary: frozen baseline replayed; LOO, episode omission, influence and overlap saved.',flush=True)
