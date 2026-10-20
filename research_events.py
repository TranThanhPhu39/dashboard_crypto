"""FOMC statement event regressions with HC3 uncertainty and pre/post differences."""
from research_common import *
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

def main():
 e=pd.read_csv(ROOT/'data/processed/fomc_crypto_statement_windows.csv')
 e['date']=pd.to_datetime(e.event_time_utc,utc=True).dt.tz_convert('America/New_York').dt.tz_localize(None).dt.normalize()
 m=pd.read_csv(ROOT/'data/processed/fomc_policy_surprises.csv',parse_dates=['Date'])
 e=e.merge(m[['Date','STMT']],left_on='date',right_on='Date',how='left',validate='many_to_one')
 e['return_pct']=100*e.log_return; e['MP1_10bps']=e.MP1_bps/10; e['MP2_10bps']=e.MP2_bps/10
 e['STMT_10bps']=100*e.STMT/10
 rows=[]; counts=[]
 for asset in ['BTC','ETH']:
  for coverage in ['complete','include_endpoints']:
   g=e[(e.asset==asset)&e.status.isin(['complete'] if coverage=='complete' else ['complete','endpoints_only'])]
   for regime,sub in [('full',g),('pre2020',g[g.post2020==0]),('post2020',g[g.post2020==1])]:
    counts.append(dict(asset=asset,coverage=coverage,regime=regime,n_events=len(sub),first_date=str(sub.date.min().date()),last_date=str(sub.date.max().date())))
    for spec,features in [('target_nextmeeting',['MP1_10bps','MP2_10bps']),('sf_fed_stmt',['STMT_10bps'])]:
     f=sub[features+['return_pct']].dropna()
     fit=sm.OLS(f.return_pct,sm.add_constant(f[features])).fit(cov_type='HC3')
     for c in features:
      ci=fit.conf_int().loc[c]
      rows.append(dict(asset=asset,coverage=coverage,regime=regime,specification=spec,term=c,beta_return_pct=fit.params[c],se=fit.bse[c],lower95=ci.iloc[0],upper95=ci.iloc[1],pvalue=fit.pvalues[c],nobs=int(fit.nobs),r_squared=fit.rsquared))
   if coverage=='complete':
    xx=g[['MP1_10bps','MP2_10bps','post2020']].copy()
    for c in ['MP1_10bps','MP2_10bps']: xx[c+'_post2020']=xx[c]*xx.post2020
    f=xx.assign(return_pct=g.return_pct).dropna(); fit=sm.OLS(f.return_pct,sm.add_constant(f.drop(columns='return_pct'))).fit(cov_type='HC3')
    for c in ['MP1_10bps_post2020','MP2_10bps_post2020']:
     ci=fit.conf_int().loc[c]; rows.append(dict(asset=asset,coverage=coverage,regime='post_minus_pre',specification='pooled_interaction',term=c,beta_return_pct=fit.params[c],se=fit.bse[c],lower95=ci.iloc[0],upper95=ci.iloc[1],pvalue=fit.pvalues[c],nobs=int(fit.nobs),r_squared=fit.rsquared))
 result=pd.DataFrame(rows); result['qvalue_bh']=multipletests(result.pvalue,method='fdr_bh')[1]
 table(result,'fomc_regressions'); table(pd.DataFrame(counts),'fomc_sample_counts'); table(e,'fomc_analysis_observations')
 fig,axes=plt.subplots(1,2,figsize=(12,4.5))
 for ax,asset in zip(axes,['BTC','ETH']):
  g=e[(e.asset==asset)&(e.status=='complete')]
  for post,label in [(0,'Pre-2020'),(1,'2020 onward')]:
   q=g[g.post2020==post]; ax.scatter(q.MP1_bps,q.return_pct,label=label,alpha=.7,s=26)
  ax.axhline(0,color='#888',linewidth=.7); ax.axvline(0,color='#888',linewidth=.7); ax.set_title(asset+' | statement [-10,+20] minutes'); ax.set_xlabel('MP1 surprise (bps)'); ax.set_ylabel('Crypto window log return (%)'); ax.legend()
 fig.tight_layout(); figure(fig,'fomc_scatter')
 js({'window':'Statement [-10,+20] minutes; UTC derived from actual Eastern timestamps including DST.','baseline':'Complete minute windows; separate asset regressions, HC3 covariance. MP1 and MP2 jointly included.','robustness':'Add endpoint-only observations; alternative SF Fed STMT surprise.','interpretation':'Intraday event association. Policy information effects and simultaneous news can remain; no claim of pure exogenous policy shock.','small_sample':'Pre-2020 ETH event sample is short; interaction significance is assessed directly, not via overlap of separate CIs.'},'fomc_method')
 print(pd.DataFrame(counts).to_string(index=False),flush=True)
if __name__=='__main__': main()
