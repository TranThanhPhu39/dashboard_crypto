"""Independent checks for the approved VAR extension; do not rerun forecasting."""
from research_common import *
import hashlib,re

def main():
 out=RESULTS/'var_calendar_extension'
 report=json.loads((out/'validation.json').read_text())
 checks={}
 checks['all_protected_source_and_baseline_files_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in report['input_baseline_sha256'].items())
 diag=pd.read_csv(out/'diagnostics.csv'); comparison=pd.read_csv(out/'baseline_comparison.csv'); irf=pd.read_csv(out/'impulse_responses.csv'); diffs=pd.read_csv(out/'irf_comparison.csv')
 old=pd.read_csv(TABLES/'var_impulse_responses.csv')
 checks['48_models_fitted']=len(diag)==48
 checks['12_combined_models_reported']=len(comparison)==12
 checks['lag_search_not_expanded']=diag.lag.between(1,10).all()
 checks['combined_same_lag_and_sample']=bool(comparison.same_lag_as_baseline.all() and (comparison.nobs==comparison.baseline_nobs).all())
 checks['irf_differences_reconcile']=bool(np.allclose(diffs.response_difference_pp,diffs.response_pct-diffs.baseline_response_pct,atol=1e-10))
 for criterion,label in [('bic','bic_baseline'),('aic','aic_lag')]:
  a=irf[(irf.specification=='baseline')&(irf.criterion==criterion)]
  b=old[old.specification==label]
  q=a.merge(b,on=['asset','regime','shock','horizon_sessions'],suffixes=('_new','_old'),validate='one_to_one')
  checks[criterion+'_baseline_irf_reproduced']=bool(len(q)==len(b) and np.allclose(q.response_pct_new,q.response_pct_old,atol=1e-7,rtol=1e-6))
 for asset in ['btc','eth']:
  x=pd.read_csv(out/(asset+'_calendar_controls.csv'),parse_dates=['date_utc'])
  checks[asset+'_weekday_dummies_correct']=all(np.array_equal(x[label],(x.date_utc.dt.dayofweek==day).astype(float)) for day,label in [(1,'tuesday'),(2,'wednesday'),(3,'thursday'),(4,'friday')])
  checks[asset+'_gap_correct']=bool(np.array_equal(x.extra_calendar_days,x.elapsed_calendar_days-1))
 ranks=pd.read_csv(out/'control_rank_checks.csv')
 checks['all_deterministic_designs_full_rank']=bool((ranks['rank']==ranks.n_deterministic_columns).all())
 h=(out/'report.html').read_text(encoding='utf-8')
 checks['all_local_report_links_exist']=all((out/p).exists() for p in re.findall(r'href="([^"]+)"',h) if not p.startswith('http'))
 checks['both_irf_figures_exist']=all((out/f'irf_comparison_{c}.png').stat().st_size>10000 for c in ['bic','aic'])
 result={'checks':{k:bool(v) for k,v in checks.items()},'n_checks':len(checks),'passed':int(sum(checks.values())),'max_absolute_irf_change_pp':float(diffs.response_difference_pp.abs().max()),'max_absolute_full_sample_irf_change_pp':float(diffs.loc[diffs.regime=='full','response_difference_pp'].abs().max()),'all_12_combined_models_reject_whiteness_5pct':bool((comparison.whiteness_p20<.05).all()),'note':'Integrity checks passing do not mean the residual-whiteness adequacy test passed.'}
 (out/'independent_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 assert all(checks.values()),checks
 print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__': main()
