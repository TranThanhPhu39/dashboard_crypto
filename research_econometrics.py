"""Session-aligned VAR, HAC local projections and pre-specified regime checks."""
from research_common import *
import warnings
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller,kpss
from statsmodels.stats.multitest import multipletests

NAMES=['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps','crypto_return_pct']
SHOCKS={'vix_change':5.,'usd_return_pct':1.,'us2y_change_bps':10.,'us10y_change_bps':10.}

def session_panel(d,asset):
 cols=['vix','broad_usd','us2y','us10y',asset+'_usd']
 levels=d[cols].dropna()
 p=pd.DataFrame(index=levels.index)
 p['vix_change']=levels.vix.diff()
 p['usd_return_pct']=100*np.log(levels.broad_usd).diff()
 p['us2y_change_bps']=100*levels.us2y.diff(); p['us10y_change_bps']=100*levels.us10y.diff()
 p['crypto_return_pct']=100*np.log(levels[asset+'_usd']).diff()
 p['elapsed_calendar_days']=levels.index.to_series().diff().dt.days
 p['stress_lag']=(levels.vix.shift(1)>30).astype(int)
 p['post2020']=(levels.index>='2020-01-01').astype(int)
 return p.dropna()

def main():
 d=data('daily_research_latest.csv'); var_rows=[]; diagnostics=[]; robust_diag=[]; stationarity=[]; lps=[]; interactions=[]; rolling=[]
 for asset in ['btc','eth']:
  p=session_panel(d,asset); p.to_csv(ROOT/'data/processed'/f'{asset}_econometric_sessions.csv',encoding='utf-8-sig')
  # Telescoping check against full calendar returns prevents silently dropping weekends.
  actual=100*np.log(d[asset+'_usd'].dropna()).diff()
  for i in range(1,min(len(p),20)):
   expected=actual.loc[(actual.index>p.index[i-1])&(actual.index<=p.index[i])].sum()
   assert np.isclose(expected,p.crypto_return_pct.iloc[i],atol=1e-8)
  for regime,g in [('full',p),('pre2020',p.loc[:'2019-12-31']),('post2020',p.loc['2020-01-01':])]:
   y=g[NAMES].reset_index(drop=True)
   for c in NAMES:
    with warnings.catch_warnings():
     warnings.simplefilter('ignore'); a=adfuller(y[c],maxlag=20,autolag='BIC'); k=kpss(y[c],regression='c',nlags='auto')
    stationarity.append(dict(asset=asset,regime=regime,variable=c,n=len(y),adf_stat=a[0],adf_p=a[1],adf_lags=a[2],kpss_stat=k[0],kpss_p_bound=k[1],kpss_lags=k[2]))
   selected=VAR(y).select_order(10); lag=max(1,int(selected.selected_orders['bic']))
   res=VAR(y).fit(lag); irf=res.irf(30)
   sigma=np.asarray(res.sigma_u); chol=np.linalg.cholesky(sigma)
   se=irf.stderr(orth=True)
   white=res.test_whiteness(nlags=max(20,lag+5),adjusted=True)
   diagnostics.append(dict(asset=asset,regime=regime,nobs=res.nobs,bic_lag=lag,aic_lag=int(selected.selected_orders['aic']),stable=bool(res.is_stable()),whiteness_p=float(white.pvalue),max_companion_eigenvalue=float(np.max(np.abs(np.linalg.eigvals(res.coefs.reshape(lag,5,5)[0])))) if lag==1 else float(np.max(1/np.abs(res.roots))),stress_sessions=int(g.stress_lag.sum()),median_elapsed_days=float(g.elapsed_calendar_days.median())))
   for shock,scale in SHOCKS.items():
    j=NAMES.index(shock); factor=scale/chol[j,j]
    for h in range(31):
     b=irf.orth_irfs[h,4,j]*factor; s=se[h,4,j]*abs(factor)
     var_rows.append(dict(asset=asset,regime=regime,shock=shock,horizon_sessions=h,response_pct=b,se=s,lower95=b-1.96*s,upper95=b+1.96*s,shock_size=scale,lag=lag))
   # Prespecified VAR robustness: AIC lag and reverse macro ordering.
   robust_specs=[('aic_lag',NAMES,max(1,int(selected.selected_orders['aic']))),('reverse_macro_order',NAMES[:4][::-1]+NAMES[4:],lag)]
   for label,order,rlag in robust_specs:
    rr=VAR(g[order].reset_index(drop=True)).fit(rlag); ri=rr.irf(30); pp=np.linalg.cholesky(np.asarray(rr.sigma_u))
    rw=rr.test_whiteness(nlags=max(20,rlag+5),adjusted=True)
    robust_diag.append(dict(asset=asset,regime=regime,specification=label,lag=rlag,nobs=rr.nobs,stable=bool(rr.is_stable()),whiteness_p=float(rw.pvalue)))
    for shock,scale in SHOCKS.items():
     j=order.index(shock); target=order.index('crypto_return_pct')
     for h in [0,1,5,10,20,30]:
      var_rows.append(dict(asset=asset,regime=regime,shock=shock,horizon_sessions=h,response_pct=ri.orth_irfs[h,target,j]*scale/pp[j,j],specification=label,lag=rlag))
   # LP controls: all contemporaneous macro changes plus five lags of the whole system.
   x=g[NAMES[:4]].copy()
   for k in range(1,6):
    for c in NAMES: x[f'L{k}_{c}']=g[c].shift(k)
   for h in [0,1,2,5,10,20,30]:
    outcome=sum(g.crypto_return_pct.shift(-k) for k in range(h+1))
    frame=x.assign(outcome=outcome).dropna()
    fit=sm.OLS(frame.outcome,sm.add_constant(frame.drop(columns='outcome'))).fit(cov_type='HAC',cov_kwds={'maxlags':max(5,h+1),'use_correction':True})
    for shock,scale in SHOCKS.items():
     ci=fit.conf_int().loc[shock]*scale
     lps.append(dict(asset=asset,regime=regime,shock=shock,horizon_sessions=h,beta_pct=fit.params[shock]*scale,se=fit.bse[shock]*scale,lower95=ci.iloc[0],upper95=ci.iloc[1],pvalue=fit.pvalues[shock],nobs=int(fit.nobs),outcome='cumulative t through t+h; conditional association'))
  # Difference tests use one pooled interaction regression rather than CI overlap.
  x=p[NAMES[:4]].copy()
  for k in range(1,6):
   for c in NAMES: x[f'L{k}_{c}']=p[c].shift(k)
  for kind,z in [('post2020',p.post2020),('stress_lag_vix_gt30',p.stress_lag)]:
   xx=x.copy(); xx['regime']=z
   for c in NAMES[:4]: xx[c+'_interaction']=p[c]*z
   for h in [0,1,5,10,20]:
    yy=sum(p.crypto_return_pct.shift(-k) for k in range(h+1))
    frame=xx.assign(outcome=yy).dropna()
    # Remove outcomes spanning the pre/post break so pre-regime horizons stay inside that regime.
    if kind=='post2020':
     same=p.post2020==p.post2020.shift(-h)
     frame=frame.loc[same.reindex(frame.index).fillna(False)]
    fit=sm.OLS(frame.outcome,sm.add_constant(frame.drop(columns='outcome'))).fit(cov_type='HAC',cov_kwds={'maxlags':max(5,h+1),'use_correction':True})
    for c,scale in SHOCKS.items():
     term=c+'_interaction'; ci=fit.conf_int().loc[term]*scale
     interactions.append(dict(asset=asset,interaction=kind,shock=c,horizon_sessions=h,difference_pct=fit.params[term]*scale,se=fit.bse[term]*scale,lower95=ci.iloc[0],upper95=ci.iloc[1],pvalue=fit.pvalues[term],nobs=int(fit.nobs)))
  # Rolling contemporaneous associations, 252 eligible sessions, five lag controls.
  xx=x.assign(outcome=p.crypto_return_pct).dropna()
  for end in range(252,len(xx)+1,21):
   w=xx.iloc[end-252:end]; fit=sm.OLS(w.outcome,sm.add_constant(w.drop(columns='outcome'))).fit(cov_type='HAC',cov_kwds={'maxlags':5})
   for c,scale in SHOCKS.items(): rolling.append(dict(asset=asset,date_utc=str(w.index[-1].date()),shock=c,beta_pct=fit.params[c]*scale,se=fit.bse[c]*scale))
  print('Econometrics completed:',asset,flush=True)
 var=pd.DataFrame(var_rows); var['specification']=var['specification'].fillna('bic_baseline')
 lp=pd.DataFrame(lps); inter=pd.DataFrame(interactions)
 # BH correction across each displayed family; report raw and adjusted inference.
 lp['qvalue_bh']=multipletests(lp.pvalue,method='fdr_bh')[1]
 inter['qvalue_bh']=multipletests(inter.pvalue,method='fdr_bh')[1]
 for frame,name in [(var,'var_impulse_responses'),(pd.DataFrame(diagnostics),'var_diagnostics'),(pd.DataFrame(robust_diag),'var_robustness_diagnostics'),(pd.DataFrame(stationarity),'stationarity_tests'),(lp,'local_projections'),(inter,'regime_interactions'),(pd.DataFrame(rolling),'rolling_sensitivity')]: table(frame,name)
 fig,axes=plt.subplots(2,4,figsize=(15,7),sharex=True)
 for i,asset in enumerate(['btc','eth']):
  for j,shock in enumerate(SHOCKS):
   ax=axes[i,j]; q=lp[(lp.asset==asset)&(lp.shock==shock)&(lp.regime=='full')]
   ax.plot(q.horizon_sessions,q.beta_pct,marker='o',markersize=3); ax.fill_between(q.horizon_sessions,q.lower95,q.upper95,alpha=.18); ax.axhline(0,color='#777',linewidth=.8)
   ax.set_title(asset.upper()+' | '+shock); ax.set_xlabel('Eligible US sessions'); ax.set_ylabel('Cumulative log return (%)')
 fig.suptitle('Local projections | conditional associations, pointwise HAC 95% intervals',y=1.01); fig.tight_layout(); figure(fig,'lp_responses')
 fig,axes=plt.subplots(2,2,figsize=(12,7),sharex=True)
 roll=pd.DataFrame(rolling)
 for ax,shock in zip(axes.flat,SHOCKS):
  for asset in ['btc','eth']:
   q=roll[(roll.asset==asset)&(roll.shock==shock)]; ax.plot(pd.to_datetime(q.date_utc),q.beta_pct,label=asset.upper(),linewidth=.9)
  ax.axhline(0,color='#777',linewidth=.8); ax.set_title(shock); ax.legend()
 fig.suptitle('Rolling 252-session sensitivity | conditional contemporaneous association'); fig.tight_layout(); figure(fig,'rolling_sensitivity')
 js({'ordering':NAMES,'shock_sizes':SHOCKS,'var_identification':'Recursive Cholesky; macro-first restriction is an assumption, not causal identification by itself. Alternative order exported.','lp_horizon':'Eligible observation sessions, cumulative t..t+h; same-day macro changes can overlap crypto response.','stress_rule':'Previous eligible session VIX >30; fixed threshold.','full_sample_data':'Current-vintage historical panel; not a real-time forecast backtest.'},'econometric_method')
if __name__=='__main__': main()
