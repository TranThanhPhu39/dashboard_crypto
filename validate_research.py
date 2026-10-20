"""Integrity checks on generated results, distinct from model adequacy diagnostics."""
from research_common import *
import hashlib,zipfile

def main():
 d=data('daily_research_latest.csv'); checks={}; notes=[]
 for asset in ['btc','eth']:
  p=data(asset+'_econometric_sessions.csv')
  expected=100*np.log(d[asset+'_usd'].reindex(p.index)).diff().iloc[1:]
  checks[asset+'_session_return_includes_all_intervening_days']=bool(np.allclose(expected,p.crypto_return_pct.iloc[1:],atol=1e-7))
  for raw,trans,scale in [('vix','vix_change',1),('broad_usd','usd_return_pct',100),('us2y','us2y_change_bps',100),('us10y','us10y_change_bps',100)]:
   s=d[raw].reindex(p.index); diff=(np.log(s).diff() if raw=='broad_usd' else s.diff())*scale
   checks[asset+'_'+trans+'_aligned_interval']=bool(np.allclose(diff.iloc[1:],p[trans].iloc[1:],atol=1e-7))
  a=data(f'forecast_{asset}_common_no_usd.csv'); b=data(f'forecast_{asset}_common_with_usd.csv')
  checks[asset+'_paired_origins_equal']=a.index.equals(b.index)
 pred=pd.read_csv(TABLES/'forecast_test_predictions.csv')
 checks['all_forecast_values_finite']=bool(np.isfinite(pred[['actual','predicted']].to_numpy()).all())
 checks['variance_forecasts_positive']=bool((pred.loc[pred.target=='squared_return','predicted']>0).all())
 checks['all_tests_in_2025plus_targets']=bool(((pd.to_datetime(pred.date_utc)+pd.Timedelta(days=1))>='2025-01-01').all())
 # Independently reconstruct test RMSE from the saved per-origin forecasts.
 reported=pd.read_csv(TABLES/'forecast_test_metrics.csv')
 for keys,g in pred.groupby(['asset','variant','target','model']):
  q=reported
  for c,val in zip(['asset','variant','target','model'],keys): q=q[q[c]==val]
  checks['rmse_'+'_'.join(keys)]=bool(np.isclose(np.sqrt(np.mean((g.actual-g.predicted)**2)),q.rmse.iloc[0],rtol=1e-7,atol=1e-12))
 lp=pd.read_csv(TABLES/'local_projections.csv'); checks['lp_ci_order']=bool(((lp.lower95<=lp.beta_pct)&(lp.beta_pct<=lp.upper95)).all())
 ev=pd.read_csv(TABLES/'fomc_analysis_observations.csv'); baseline=ev[ev.status=='complete']; checks['fomc_baseline_95_btc_83_eth']=bool((baseline.asset=='BTC').sum()==95 and (baseline.asset=='ETH').sum()==83)
 timing=pd.read_csv(TABLES/'forecast_label_availability_checks.csv')
 checks['train_labels_available_before_validation']=bool((pd.to_datetime(timing.training_last_label_close_utc)<=pd.to_datetime(timing.validation_first_origin_utc)).all())
 checks['development_labels_available_before_test']=bool((pd.to_datetime(timing.development_last_label_close_utc)<=pd.to_datetime(timing.test_first_origin_utc)).all())
 for name in ['eda_history','eda_returns_volatility','eda_correlations','lp_responses','rolling_sensitivity','fomc_scatter','forecast_usd_comparison']:
  checks['figure_'+name]=(FIGURES/(name+'.png')).stat().st_size>10000
 checks['report_and_dashboard_exist']=(RESULTS/'report.html').exists() and (RESULTS/'dashboard/index.html').exists()
 diag=pd.read_csv(TABLES/'var_diagnostics.csv'); floors=pd.read_csv(TABLES/'forecast_variance_floor_diagnostics.csv')
 notes.append(f'VAR adequacy limitation: {int((diag.whiteness_p<.05).sum())}/{len(diag)} baseline residual-whiteness tests reject; these are reported failures, not implementation checks to suppress.')
 notes.append(f'Variance limitation: {int(floors.floor_hits.sum())} predictions across model/config runs touch the fixed floor; QLIKE is sensitive.')
 sourcefiles=[ROOT/'data/processed/daily_research_latest.csv',ROOT/'data/processed/research_design.json']
 source_hash={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sourcefiles}
 original=ROOT/'topic09_research_dataset_20261017_design.zip'
 if original.exists():
  with zipfile.ZipFile(original) as z: previous=json.loads(z.read('manifest.json'))
  for p in sourcefiles:
   rel=p.relative_to(ROOT).as_posix()
   checks['unchanged_from_approved_snapshot_'+p.stem]=hashlib.sha256(p.read_bytes()).hexdigest()==previous[rel]['sha256']
 result={'passed_integrity_checks':sum(checks.values()),'n_integrity_checks':len(checks),'checks':checks,'model_adequacy_notes':notes,'source_snapshot_sha256':source_hash,'browser_visual_check':'Unavailable: CUA missing kernel asset path. Static figures visually inspected; dashboard logic separately exercised with Node.'}
 js(result,'validation_report'); assert all(checks.values()),checks
 print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2),flush=True)
if __name__=='__main__': main()
