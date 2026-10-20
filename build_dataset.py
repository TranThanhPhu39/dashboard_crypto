"""Build research panels from saved raw data; no network access."""
from pathlib import Path
import io,json,zipfile
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data/raw'; OUT=ROOT/'data/processed'; OUT.mkdir(parents=True,exist_ok=True)
CAL=pd.date_range('2013-12-01','2026-10-15',name='date_utc')
df=pd.DataFrame(index=CAL)
definitions=[]
def define(c,desc,unit,source,rule):
 definitions.append(dict(variable=c,description=desc,unit=unit,source=source,timing_or_formula=rule))
def write(d,name):
 d.to_csv(OUT/name,index=True,encoding='utf-8-sig',float_format='%.12g')
def add_series(c,s,source,desc,unit,kind='log'):
 s=s.sort_index(); assert not s.index.duplicated().any()
 df[c]=s.reindex(CAL)
 define(c,desc,unit,source,'Observation-date level; latest downloaded vintage')
 valid=s.dropna()
 if kind=='log':
  # Do not jump across a non-positive observation, notably WTI in April 2020.
  t=np.log(valid.where(valid>0)).diff()
  col=c+'_log_return'; df[col]=t.reindex(CAL)
  define(col,desc+' log return','decimal',source,'ln(P_t/P_previous_observation); no weekend fill')
 elif kind in ['bps','diff']:
  col=c+('_change_bps' if kind=='bps' else '_change')
  df[col]=(valid.diff()*(100 if kind=='bps' else 1)).reindex(CAL)
  define(col,desc+' change','bps' if kind=='bps' else unit,source,'Difference from previous nonmissing observation; percent-point yields x100')
 return valid

for a in ['btc','eth']:
 raw=json.loads((RAW/f'{a}_coinmetrics.json').read_bytes())
 assert not raw.get('next_page_url'),'Pagination required'
 d=pd.DataFrame(raw['data'])
 d['date']=pd.to_datetime(d['time'],utc=True).dt.tz_localize(None).dt.normalize()
 s=pd.Series(pd.to_numeric(d['PriceUSD'],errors='coerce').values,index=d['date'])
 assert (s.dropna()>0).all()
 add_series(a+'_usd',s,'Coin Metrics PriceUSD',a.upper()+'/USD UTC close','USD')
 # Recompute on calendar grid to avoid bridging missing crypto days.
 r=a+'_usd_log_return'; df[r]=np.log(df[a+'_usd']).diff()
 sq=a+'_squared_return'; df[sq]=df[r]**2
 define(sq,a.upper()+' squared daily return','decimal squared','Derived Coin Metrics','r_t^2; daily volatility proxy, not intraday realized variance')
 v=a+'_vol30_annualized'; df[v]=np.sqrt(365*df[sq].rolling(30,min_periods=30).mean())
 define(v,a.upper()+' trailing 30-day RMS volatility','decimal annualized','Derived Coin Metrics','sqrt(365 * mean(last 30 daily squared log returns)); backward looking')

mapping={'VIXCLS':('vix','VIX','index','diff'),'DTWEXBGS':('broad_usd','Nominal broad USD, goods and services','index','log'),
 'DGS2':('us2y','US 2-year constant maturity yield','percent','bps'),'DGS10':('us10y','US 10-year constant maturity yield','percent','bps'),
 'DFF':('fed_funds','Effective federal funds rate','percent','bps'),
 'DFEDTARL':('fed_target_lower','Federal funds target lower bound','percent','bps'),
 'DFEDTARU':('fed_target_upper','Federal funds target upper bound','percent','bps'),
 'DCOILWTICO':('oil_wti','WTI spot Cushing (not futures)','USD/barrel','log'),
 'NFCI':('nfci','Chicago Fed NFCI, weekly','index','diff')}
for sid,(c,desc,unit,kind) in mapping.items():
 d=pd.read_csv(RAW/f'{sid}_fred.csv',parse_dates=['observation_date'])
 s=d.set_index('observation_date')[sid].apply(pd.to_numeric,errors='coerce')
 add_series(c,s,'FRED '+sid,desc,unit,kind)
df['vix_log_change']=np.log(df['vix'].dropna()).diff().reindex(CAL)
define('vix_log_change','VIX log change','decimal','FRED VIXCLS','ln(VIX_t/VIX_previous_session)')
df['oil_wti_change_usd']=df['oil_wti'].dropna().diff().reindex(CAL)
define('oil_wti_change_usd','WTI price difference, valid through negative prices','USD/barrel','FRED DCOILWTICO','P_t - P_previous_observation; use for full-sample robustness')
df['oil_wti_asinh_change']=np.arcsinh(df['oil_wti'].dropna()).diff().reindex(CAL)
define('oil_wti_asinh_change','WTI inverse hyperbolic sine change','transformed USD/barrel','FRED DCOILWTICO','asinh(P_t / 1 USD per barrel) - asinh(P_previous / 1 USD per barrel)')
df['nfci_expost_carried']=df['nfci'].ffill()
define('nfci_expost_carried','Latest-vintage weekly NFCI carried by observation date','index','FRED NFCI','EX POST ONLY: observation date is Friday; published later, revisions remain')

for filename,c,desc in [('sp500_yahoo.json','sp500','S&P 500 price index, no dividends'),('gold_yahoo.json','gold_futures','Gold continuous front futures GC=F, roll-affected')]:
 d=json.loads((RAW/filename).read_bytes())['chart']['result'][0]
 idx=pd.to_datetime(d['timestamp'],unit='s',utc=True).tz_convert(d['meta']['exchangeTimezoneName']).tz_localize(None).normalize()
 s=pd.Series(d['indicators']['quote'][0]['close'],index=idx)
 s=s.loc[~s.index.duplicated(keep='last')]
 add_series(c,s,'Yahoo Finance '+d['meta']['symbol'],desc,'index' if c=='sp500' else 'USD/troy ounce')
 # Retain source session timestamps for audit; daily bars keep local session date.
 pd.DataFrame({'session_date_local':idx,'bar_timestamp_utc':pd.to_datetime(d['timestamp'],unit='s',utc=True),'close':s.reindex(idx).values}).to_csv(OUT/(c+'_session_audit.csv'),index=False)

df['is_us_equity_session']=df['sp500'].notna().astype(int)
df['post2020']=(df.index>=pd.Timestamp('2020-01-01')).astype(int)
df['close_timestamp_utc']=df.index+pd.Timedelta(days=1)
define('post2020','Subsample indicator','0/1','Design','1 from 2020-01-01 inclusive')
define('is_us_equity_session','Observed S&P 500 closing price on session date','0/1','Yahoo Finance','Not a general US release calendar')
define('close_timestamp_utc','UTC close of crypto daily bar','UTC timestamp','Coin Metrics convention','date_utc + 1 calendar day at 00:00 UTC')
daily=df.loc['2014-01-01':].copy()
write(daily,'daily_research_latest.csv')
core=['btc_usd_log_return','vix_change','broad_usd_log_return','us2y_change_bps','us10y_change_bps']
btc=daily.dropna(subset=core)
eth=daily.dropna(subset=core+['eth_usd_log_return'])
write(btc,'btc_core_complete_sessions.csv'); write(eth,'btc_eth_core_complete_sessions.csv')
for label,part in [('pre2020',btc[btc.post2020==0]),('post2020',btc[btc.post2020==1])]: write(part,f'btc_core_{label}.csv')

# ALFRED: reconstruct the complete information set at the end of each UTC day.
# Date-only vintages are admitted at next-day 00:00 UTC, with no claimed intraday precision.
pit=pd.DataFrame(index=CAL)
for sid,(c,desc,unit,kind) in mapping.items():
 p=RAW/f'{sid}_alfred_realtime.zip'
 if not p.exists() or p.read_bytes()[:2]!=b'PK': continue
 z=zipfile.ZipFile(p); names=[n for n in z.namelist() if n.endswith('.csv')]
 v=pd.read_csv(io.BytesIO(z.read(names[0])),na_values=['.'])
 v['period_start_date']=pd.to_datetime(v['period_start_date'])
 v['realtime_start_date']=pd.to_datetime(v['realtime_start_date'])
 v['realtime_end_date']=pd.to_datetime(v['realtime_end_date'])
 v[sid]=pd.to_numeric(v[sid],errors='coerce')
 write(v.set_index('period_start_date'),sid+'_vintage_periods.csv')
 starts={k:g for k,g in v.groupby('realtime_start_date')}
 state={}; rows=[]; latest_release=pd.NaT
 for date in CAL:
  # State updates may include replacement with missing values; preserve those withdrawals.
  if date in starts:
   latest_release=date
   for _,r in starts[date].iterrows(): state[r['period_start_date']]=(r[sid],date,r['realtime_end_date'])
  # Initialize for earlier releases only on the first iteration.
  if date==CAL[0]:
   prev=v[v.realtime_start_date<date].sort_values('realtime_start_date')
   for _,r in prev.iterrows(): state[r['period_start_date']]=(r[sid],r['realtime_start_date'],r['realtime_end_date'])
   if len(prev): latest_release=prev.realtime_start_date.max()
  valid=[(obs,val,rev) for obs,(val,rev,end) in state.items() if obs<=date and pd.notna(val) and (pd.isna(end) or date<=end)]
  valid.sort(key=lambda t:t[0]); vals=valid[-2:]
  row={c+'_pit':np.nan,c+'_pit_change':np.nan,c+'_pit_obs_date':pd.NaT,c+'_pit_vintage_date':pd.NaT}
  if vals:
   row[c+'_pit']=vals[-1][1]; row[c+'_pit_obs_date']=vals[-1][0]; row[c+'_pit_vintage_date']=latest_release
   if len(vals)==2:
    a,b=vals[-2][1],vals[-1][1]
    row[c+'_pit_change']=(np.log(b/a) if a>0 and b>0 else np.nan) if kind=='log' else (b-a)*(100 if kind=='bps' else 1)
  rows.append(row)
 pit=pit.join(pd.DataFrame(rows,index=CAL))
 define(c+'_pit',desc+' latest known observation',''+unit,'ALFRED '+sid,'Only vintages with realtime_start_date <= date_utc; available at date_utc+1 00:00 UTC')
 define(c+'_pit_change',desc+' latest known observation change','decimal' if kind=='log' else 'bps' if kind=='bps' else unit,'ALFRED '+sid,'Change between last two nonmissing observation dates WITHIN SAME vintage; carried until new information')
 define(c+'_pit_obs_date','Observation date of latest known '+c,'date','ALFRED '+sid,'Observation date is distinct from publication/vintage date')
 define(c+'_pit_vintage_date','Latest admitted ALFRED update for '+c,'date','ALFRED '+sid,'Date-level archival availability; conservative UTC end-of-day rule')
pit=pit.loc['2014-01-01':]
forecast=daily[['close_timestamp_utc','post2020','btc_usd_log_return','eth_usd_log_return','btc_squared_return','eth_squared_return','btc_vol30_annualized','eth_vol30_annualized']].join(pit)
for c in ['vix_change','vix_log_change','sp500_log_return','gold_futures_log_return']:
 # Extra full-calendar day of delay, explicit proxy label: historical feed availability is not archived.
 forecast[c+'_lag1_proxy']=daily[c].shift(1)
 define(c+'_lag1_proxy','One-calendar-day delayed market feature','same as parent','Latest historical market feed','Lagged proxy; not a provider-timestamped historical vintage')
for a in ['btc','eth']:
 forecast[a+'_target_next_return']=daily[a+'_usd_log_return'].shift(-1)
 forecast[a+'_target_next_squared_return']=daily[a+'_squared_return'].shift(-1)
 define(a+'_target_next_return','Next UTC-day log return TARGET','decimal','Derived crypto','r_(t+1); never use as a feature')
 define(a+'_target_next_squared_return','Next UTC-day squared return TARGET','decimal squared','Derived crypto','r_(t+1)^2; never use as a feature')
write(forecast,'forecast_origins_vintage_macro.csv')

# FOMC event calendar with actual source Eastern timestamps and matching windows.
events=[]
for sheet,typ,before,after in [('Statements','statement',10,20),('Press Conferences','press_conference',10,60),('Minutes','minutes',10,20),('Monetary Events','monetary_event',10,20)]:
 e=pd.read_excel(RAW/'USMPD.xlsx',sheet_name=sheet)
 e=e[(pd.to_datetime(e['Date'])>='2014-01-01')&(pd.to_datetime(e['Date'])<='2026-10-15')].copy()
 e['event_type']=typ
 e['event_time_et']=pd.to_datetime(e['date_time']).dt.tz_localize('America/New_York',ambiguous='raise',nonexistent='raise')
 e['event_time_utc']=e['event_time_et'].dt.tz_convert('UTC')
 e['window_start_utc']=e['event_time_utc']-pd.Timedelta(minutes=before)
 e['window_end_utc']=e['event_time_utc']+pd.Timedelta(minutes=after)
 if typ=='monetary_event':
  pcs=pd.read_excel(RAW/'USMPD.xlsx',sheet_name='Press Conferences').set_index('Date')['date_time']
  for i,r in e.iterrows():
   if r.get('PC',0)==1 and r['Date'] in pcs.index:
    pc=pd.Timestamp(pcs.loc[r['Date']]).tz_localize('America/New_York').tz_convert('UTC')
    e.loc[i,'window_end_utc']=pc+pd.Timedelta(minutes=60)
 e['post2020']=(pd.to_datetime(e['Date'])>='2020-01-01').astype(int)
 for col in ['MP1','MP2','UST2Y','UST10Y']:
  if col in e: e[col+'_bps']=e[col]*100
 events.append(e)
ev=pd.concat(events,ignore_index=True).sort_values(['event_time_utc','event_type'])
ev.to_csv(OUT/'fomc_events_utc.csv',index=False,encoding='utf-8-sig')
z=zipfile.ZipFile(RAW/'monetary-policy-surprises.zip')
for name in ['README.md','mps.csv','mps_minutes.csv','mps.R','gss.R','y1.csv']:
 (RAW/('sf_fed_'+name)).write_bytes(z.read(name))
mps=pd.read_csv(io.BytesIO(z.read('mps.csv')),parse_dates=['Date']).set_index('Date')
mps=mps.loc['2014-01-01':'2026-10-15']
write(mps,'fomc_policy_surprises.csv')

# Audit outputs: coverage and sample sizes, plus numerical/timing integrity checks.
coverage=[]
for name,panel in [('research',daily),('forecast',forecast)]:
 for c in panel:
  s=panel[c].dropna(); coverage.append(dict(panel=name,variable=c,first_date=str(s.index.min().date()) if len(s) else '',last_date=str(s.index.max().date()) if len(s) else '',n_valid=len(s),n_missing=int(panel[c].isna().sum())))
pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(definitions).drop_duplicates('variable').to_csv(OUT/'data_dictionary.csv',index=False,encoding='utf-8-sig')
summary={'calendar_days':len(daily),'btc_core_sessions':len(btc),'btc_eth_core_sessions':len(eth),'btc_pre2020':int((btc.post2020==0).sum()),'btc_post2020':int((btc.post2020==1).sum()),'fomc_event_rows':len(ev),'macro_pit_series':[c for c in pit if c.endswith('_pit')],'research_start':str(daily.index.min().date()),'research_end':str(daily.index.max().date())}
checks={'unique_daily_dates':not daily.index.duplicated().any(),'sorted_daily_dates':daily.index.is_monotonic_increasing,'no_infinite_numeric_values':not np.isinf(daily.select_dtypes('number').to_numpy()).any(),'utc_crypto_close_next_day':bool((daily.close_timestamp_utc==daily.index+pd.Timedelta(days=1)).all()),'oil_negative_values_preserved':bool((daily.oil_wti<0).any()),'oil_log_returns_missing_when_nonpositive':bool(daily.loc[daily.oil_wti<=0,'oil_wti_log_return'].isna().all()),'fomc_window_order':bool((ev.window_start_utc<ev.window_end_utc).all())}
for c in pit:
 if c.endswith('_pit_vintage_date'):
  checks[c+'_no_future']=bool((pit[c].dropna()<=pit[c].dropna().index).all())
summary['checks']=checks
(OUT/'quality_report.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
assert all(checks.values()),checks
print(json.dumps(summary,indent=2))
from prepare_forecast_design import prepare
prepare()
