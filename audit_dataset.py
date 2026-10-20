"""Independent numeric checks against raw prices and public ALFRED snapshots."""
from pathlib import Path
import pandas as pd,numpy as np,requests,io,json
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'data/processed'; RAW=ROOT/'data/raw'
def run():
 d=pd.read_csv(OUT/'daily_research_latest.csv',parse_dates=['date_utc']).set_index('date_utc')
 f=pd.read_csv(OUT/'forecast_origins_vintage_macro.csv',parse_dates=['date_utc']).set_index('date_utc')
 checks={}
 for a in ['btc','eth']:
  # First day uses warmup data outside delivered research panel.
  checks[a+'_returns_raw_formula']=bool(np.allclose(d[a+'_usd_log_return'].iloc[1:],np.log(d[a+'_usd']).diff().iloc[1:],equal_nan=True))
  checks[a+'_squared_returns']=bool(np.allclose(d[a+'_squared_return'],d[a+'_usd_log_return']**2,equal_nan=True))
  checks[a+'_next_target']=bool(np.allclose(f[a+'_target_next_return'],d[a+'_usd_log_return'].shift(-1),equal_nan=True))
 checks['broad_usd_pit_missing_before_first_vintage']=bool(f.loc[:'2019-02-03','broad_usd_pit'].isna().all())
 checks['nfci_pit_available_in_2014']=bool(f.loc['2014','nfci_pit'].notna().all())
 fred=pd.read_csv(RAW/'SP500_fred.csv',parse_dates=['observation_date']).set_index('observation_date')['SP500']
 comp=pd.concat([d.sp500.rename('yahoo'),fred.rename('fred')],axis=1).dropna()
 discrepancy=(comp.yahoo-comp.fred).abs()
 comparison=comp.assign(difference_yahoo_minus_fred=comp.yahoo-comp.fred)
 differences=comparison.loc[discrepancy>=0.02]
 differences.index.name='date_utc'
 differences.to_csv(OUT/'sp500_source_discrepancies.csv',encoding='utf-8-sig')
 results=[]
 for sid,c,t in [('NFCI','nfci','2014-02-01'),('NFCI','nfci','2020-03-20'),('DTWEXBGS','broad_usd','2019-08-16'),('DGS2','us2y','2020-03-20')]:
  url=f'https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={sid}&cosd=2013-12-01&coed={t}&vintage_date={t}'
  p=RAW/f'audit_{sid}_{t}.csv'
  try:
   if not p.exists():
    r=requests.get(url,timeout=30); r.raise_for_status(); p.write_bytes(r.content)
   x=pd.read_csv(p,parse_dates=['observation_date']).set_index('observation_date').iloc[:,0].dropna()
   x=pd.to_numeric(x,errors='coerce').dropna(); x=x.loc[:t]
   expected=float(x.iloc[-1]); actual=float(f.loc[t,c+'_pit'])
   match=bool(np.isclose(expected,actual,rtol=0,atol=1e-8))
   checks[f'{sid}_{t}_independent_vintage']=match
   results.append({'series':sid,'as_of_date':t,'expected_latest_obs':str(x.index[-1].date()),'expected':expected,'actual':actual,'match':match,'url':url})
  except Exception as ex: results.append({'series':sid,'as_of_date':t,'error':str(ex),'url':url})
 report={'checks':checks,'sp500_common_observations':len(comp),'sp500_max_absolute_difference':float(discrepancy.max()),'source_warnings':{'sp500_discrepant_dates_at_0_02_points':len(differences),'action':'Keep one Yahoo series without manual replacement; review discrepancies and next-session returns in robustness analysis.'},'snapshot_checks':results}
 (OUT/'independent_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report,indent=2)); assert all(checks.values()),checks
if __name__=='__main__': run()
