"""Prepare the agreed no-MOVE research design from the frozen source snapshot."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'data/processed'
COMMON_FEATURES=[
 'vix_change_lag1_proxy','us2y_pit_change','us10y_pit_change',
 'fed_funds_pit_change','sp500_log_return_lag1_proxy',
 'gold_futures_log_return_lag1_proxy','oil_wti_pit_change','nfci_pit',
]
USD_FEATURES=['broad_usd_pit_change']

def prepare():
 f=pd.read_csv(OUT/'forecast_origins_vintage_macro.csv',parse_dates=['date_utc','close_timestamp_utc']).set_index('date_utc')
 assert f.index.is_unique and f.index.is_monotonic_increasing
 config={
  'baseline_excludes':['MOVE'],
  'source_snapshot_end':'2026-10-15',
  'historical_panel':'daily_research_latest.csv',
  'historical_rule':'Retain full available 2014-2026 calendar; no vintage-2019 truncation; pre/post cutoff 2020-01-01.',
  'usd_eligibility_start':'2019-02-04',
  'common_macro_features':COMMON_FEATURES,
  'additional_usd_features':USD_FEATURES,
  'targets':['next_return','next_squared_return'],
  'origin_rule':'Row t is information at 00:00 UTC t+1; targets cover UTC day t+1.',
  'split_rule':{'basis':'target_date_utc','train':'before 2023-01-01','validation':'2023-01-01 through 2024-12-31','test':'2025-01-01 onward'},
  'comparison_rule':'Incremental USD effect: use common_no_usd vs common_with_usd, identical dates, training windows, target, model and tuning protocol. Long no-USD run is a separate historical benchmark.',
  'missing_rule':'Complete-case per asset on the declared features and both targets; no imputation, no zero filling, no market-return carrying.',
  'assets':{},
 }
 stats=[]; checks={}
 for asset in ['btc','eth']:
  own=[asset+'_usd_log_return',asset+'_squared_return',asset+'_vol30_annualized']
  base=own+COMMON_FEATURES
  targets=[asset+'_target_next_return',asset+'_target_next_squared_return']
  clean=f.replace([np.inf,-np.inf],np.nan)
  eligible=clean[base+targets].notna().all(axis=1)
  usd_ok=clean[USD_FEATURES+['broad_usd_pit']].notna().all(axis=1)
  common=eligible & usd_ok & (f.index>=pd.Timestamp('2019-02-04'))
  variants=[('no_usd_long',eligible,base),('common_no_usd',common,base),('common_with_usd',common,base+USD_FEATURES)]
  frames={}
  for name,mask,features in variants:
   panel=f.loc[mask,['close_timestamp_utc','post2020']+features+targets].copy()
   panel.insert(1,'target_date_utc',panel.index+pd.Timedelta(days=1))
   td=panel.target_date_utc
   panel.insert(2,'split',np.where(td<'2023-01-01','train',np.where(td<'2025-01-01','validation','test')))
   filename=f'forecast_{asset}_{name}.csv'
   panel.to_csv(OUT/filename,encoding='utf-8-sig',float_format='%.12g')
   frames[name]=panel
   row={'asset':asset,'configuration':name,'file':filename,'first_origin_date':str(panel.index.min().date()),'last_origin_date':str(panel.index.max().date()),'n_rows':len(panel),'n_features':len(features),'pre2020_rows':int((panel.post2020==0).sum()),'post2020_rows':int((panel.post2020==1).sum())}
   row.update({s+'_rows':int((panel.split==s).sum()) for s in ['train','validation','test']})
   stats.append(row)
   checks[asset+'_'+name+'_finite_complete']=bool(np.isfinite(panel[features+targets].to_numpy()).all())
   checks[asset+'_'+name+'_no_move']=not any('move' in c.lower() for c in panel.columns)
   if name!='common_with_usd': checks[asset+'_'+name+'_no_dollar_features']=not any('broad_usd' in c for c in panel.columns)
  left,right=frames['common_no_usd'],frames['common_with_usd']
  checks[asset+'_paired_dates_equal']=left.index.equals(right.index)
  checks[asset+'_paired_shared_values_equal']=left.equals(right[left.columns])
  checks[asset+'_common_subset_long']=bool(left.index.isin(frames['no_usd_long'].index).all())
  checks[asset+'_paired_split_dates_equal']=left['split'].equals(right['split'])
  config['assets'][asset]={'base_features':base,'with_usd_features':base+USD_FEATURES,'target_columns':targets,'metadata_not_features':['date_utc','close_timestamp_utc','target_date_utc','split','post2020']}
 history=pd.read_csv(OUT/'daily_research_latest.csv',usecols=['date_utc'])
 checks['historical_full_sample_retained']=bool(history.date_utc.min()=='2014-01-01' and history.date_utc.max()=='2026-10-15' and len(history)==4671)
 assert all(checks.values()),checks
 (OUT/'research_design.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
 pd.DataFrame(stats).to_csv(OUT/'forecast_sample_summary.csv',index=False,encoding='utf-8-sig')
 (OUT/'forecast_design_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
 print(pd.DataFrame(stats).to_string(index=False))
 return stats

if __name__=='__main__': prepare()
