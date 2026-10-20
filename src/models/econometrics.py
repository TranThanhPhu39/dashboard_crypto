from src.utils.project import *
from src.features.design import LP_frame
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from statsmodels.stats.multitest import multipletests

def local_projections():
    p=panel('calendar_information.csv');rows=[];inter=[];covrows=[]
    for asset in ['btc','eth']:
        for regime,g in [('full',p),('pre2020',p.loc[:'2019-12-31']),('post2020',p.loc['2020-01-01':])]:
            for h in range(1,31):
                f=LP_frame(g,asset,h);fit=sm.OLS(f.outcome,sm.add_constant(f.drop(columns='outcome'))).fit(cov_type='HAC',cov_kwds={'maxlags':max(5,h+1),'use_correction':True})
                for shock,scale in SHOCKS.items():
                    b=float(fit.params[shock]*scale);se=float(fit.bse[shock]*scale)
                    rows.append(dict(asset=asset,regime=regime,shock=shock,horizon_days=h,beta_pct=b,se=se,lower95=b-1.95996398454*se,upper95=b+1.95996398454*se,pvalue=float(fit.pvalues[shock]),nobs=int(fit.nobs),n_state=None))
        for h in range(1,31):
            f=LP_frame(p,asset,h,True);fit=sm.OLS(f.outcome,sm.add_constant(f.drop(columns='outcome'))).fit(cov_type='HAC',cov_kwds={'maxlags':max(5,h+1),'use_correction':True});v=fit.cov_params()
            for shock,scale in SHOCKS.items():
                term=shock+'_stress';b=float(fit.params[shock]*scale);d=float(fit.params[term]*scale);vb=float(v.loc[shock,shock]*scale**2);vd=float(v.loc[term,term]*scale**2);cross=float(v.loc[shock,term]*scale**2)
                covrows.append(dict(asset=asset,shock=shock,horizon_days=h,calm=b,difference=d,var_calm=vb,var_difference=vd,cov_calm_difference=cross))
                inter.append(dict(asset=asset,shock=shock,horizon_days=h,difference_pct=d,se=float(np.sqrt(vd)),pvalue=float(fit.pvalues[term]),nobs=int(fit.nobs)))
                for regime in ['calm','stress']:
                    beta=b+(d if regime=='stress' else 0);se=float(np.sqrt(vb+(vd+2*cross if regime=='stress' else 0)))
                    rows.append(dict(asset=asset,regime=regime,shock=shock,horizon_days=h,beta_pct=beta,se=se,lower95=beta-1.95996398454*se,upper95=beta+1.95996398454*se,pvalue=None,nobs=int(fit.nobs),n_state=int((f.stress==(regime=='stress')).sum())))
        print('Calendar LP completed:',asset,'all 30 horizons / 5 regimes',flush=True)
    rows=pd.DataFrame(rows);mask=rows.regime.isin(['full','pre2020','post2020']);rows['qvalue_bh']=np.nan;rows.loc[mask,'qvalue_bh']=multipletests(rows.loc[mask,'pvalue'],method='fdr_bh')[1]
    inter=pd.DataFrame(inter);inter['qvalue_bh']=multipletests(inter.pvalue,method='fdr_bh')[1]
    csv(rows,'calendar_LP.csv');csv(inter,'calendar_stress_differences.csv');csv(pd.DataFrame(covrows),'calendar_state_covariance.csv')

def joint_VAR():
    daily=pd.read_csv(ROOT/'data/processed/daily_research_latest.csv',parse_dates=['date_utc']).set_index('date_utc')
    diagnostics=[];responses=[];selection=[];coeff=[];restrictions=[]
    for yield_name in ['us2y','us10y']:
        levels=daily[['btc_usd','eth_usd','vix','broad_usd',yield_name]].dropna()
        p=pd.DataFrame(index=levels.index)
        for a in ['btc','eth']:p[a+'_return_pct']=100*np.log(levels[a+'_usd']).diff()
        p['vix_change']=levels.vix.diff();p['usd_return_pct']=100*np.log(levels.broad_usd).diff();p[yield_name+'_change_bps']=100*levels[yield_name].diff();p=p.dropna()
        p.to_csv(PANELS/f'joint_VAR_{yield_name}_sessions.csv',encoding='utf-8-sig',float_format='%.17g')
        for regime,g in [('full',p),('pre2020',p.loc[:'2019-12-31']),('post2020',p.loc['2020-01-01':])]:
            candidates=[]
            for lag in range(1,11):
                fit=VAR(g.iloc[10-lag:].reset_index(drop=True)).fit(lag);candidates.append((fit.bic,lag))
                selection.append(dict(yield_variable=yield_name,regime=regime,lag=lag,nobs=int(fit.nobs),bic=float(fit.bic),aic=float(fit.aic)))
            lag=min(candidates)[1]
            orders={'crypto_first':list(p.columns),'macro_first':['vix_change','usd_return_pct',yield_name+'_change_bps','btc_return_pct','eth_return_pct'],'reverse_macro':[yield_name+'_change_bps','usd_return_pct','vix_change','btc_return_pct','eth_return_pct']}
            for order_name,order in orders.items():
                r=VAR(g[order].iloc[10-lag:].reset_index(drop=True)).fit(lag);irf=r.irf(30);se=irf.stderr(orth=True);P=np.linalg.cholesky(np.asarray(r.sigma_u));A=np.linalg.inv(P)
                if order_name=='crypto_first':
                    white=r.test_whiteness(nlags=20,adjusted=True)
                    diagnostics.append(dict(yield_variable=yield_name,regime=regime,lag=lag,nobs=int(r.nobs),stable=bool(r.is_stable()),whiteness_p20=float(white.pvalue),start_date=str(g.index[10].date()),end_date=str(g.index[-1].date())))
                    for term in r.params.index:
                        for equation in order:coeff.append(dict(yield_variable=yield_name,regime=regime,term=term,equation=equation,coefficient=float(r.params.loc[term,equation])))
                for i,c1 in enumerate(order):
                    for j,c2 in enumerate(order):restrictions.append(dict(yield_variable=yield_name,regime=regime,ordering=order_name,row=c1,column=c2,P=float(P[i,j]),A0=float(A[i,j]),sigma=float(r.sigma_u.iloc[i,j])))
                for shock,scale in [('vix_change',5.),('usd_return_pct',1.),(yield_name+'_change_bps',10.)]:
                    j=order.index(shock);factor=scale/P[j,j]
                    for asset in ['btc','eth']:
                        target=order.index(asset+'_return_pct')
                        for h in range(31):
                            b=float(irf.orth_irfs[h,target,j]*factor);s=float(se[h,target,j]*abs(factor))
                            responses.append(dict(asset=asset,yield_variable=yield_name,regime=regime,ordering=order_name,shock=shock,horizon_sessions=h,response_pct=b,se=s,lower95=b-1.95996398454*s,upper95=b+1.95996398454*s,lag=lag))
            print('Joint BTC-ETH VAR / recursive restrictions:',yield_name,regime,'lag',lag,flush=True)
    for f,name in [(pd.DataFrame(diagnostics),'joint_VAR_diagnostics.csv'),(pd.DataFrame(responses),'joint_VAR_IRF.csv'),(pd.DataFrame(selection),'joint_VAR_lag_search.csv'),(pd.DataFrame(coeff),'joint_VAR_coefficients.csv'),(pd.DataFrame(restrictions),'recursive_SVAR_matrices.csv')]:csv(f,name)

def monetary_LP():
    p=panel('calendar_information.csv');d=pd.read_csv(ROOT/'data/processed/daily_research_latest.csv',parse_dates=['date_utc']).set_index('date_utc')
    events=pd.read_csv(ROOT/'data/processed/fomc_events_utc.csv');events=events[events.event_type=='statement'].copy()
    events['date_utc']=pd.to_datetime(events.event_time_utc,utc=True).dt.tz_localize(None).dt.normalize()
    surprises=pd.read_csv(ROOT/'data/processed/fomc_policy_surprises.csv',parse_dates=['Date']).set_index('Date')
    events=events.set_index('date_utc').join(surprises[['STMT']]);assert events.index.is_unique
    rows=[];differences=[];samples=[]
    for asset in ['btc','eth']:
        x=pd.DataFrame(index=events.index);x['monetary']=events.STMT*10 # STMT percentage point -> per10bps coefficient
        x['prior_return']=p[asset+'_prior_return_pct'].reindex(x.index);x['prior_vol30']=p[asset+'_prior_vol30'].reindex(x.index);x['prior_vix']=p.vix_available_proxy.reindex(x.index)
        stress=p.stress.reindex(x.index)
        for h in range(1,31):
            returns=100*d[asset+'_usd_log_return'];y=sum(returns.shift(-k) for k in range(1,h+1)).reindex(x.index)
            f=x.assign(outcome=y).dropna();full=sm.OLS(f.outcome,sm.add_constant(f.drop(columns='outcome'))).fit(cov_type='HAC',cov_kwds={'maxlags':5,'use_correction':True})
            b=float(full.params.monetary);s=float(full.bse.monetary)
            rows.append(dict(asset=asset,regime='full',shock='monetary',horizon_days=h,beta_pct=b,se=s,lower95=b-1.95996398454*s,upper95=b+1.95996398454*s,pvalue=float(full.pvalues.monetary),nobs=int(full.nobs),n_state=None))
            xx=x.copy();xx['stress']=stress;xx['monetary_stress']=x.monetary*stress;f=xx.assign(outcome=y).dropna()
            r=sm.OLS(f.outcome,sm.add_constant(f.drop(columns='outcome'))).fit(cov_type='HAC',cov_kwds={'maxlags':5,'use_correction':True});v=r.cov_params();b=float(r.params.monetary);delta=float(r.params.monetary_stress)
            differences.append(dict(asset=asset,horizon_days=h,difference_pct=delta,se=float(r.bse.monetary_stress),pvalue=float(r.pvalues.monetary_stress),nobs=int(r.nobs)))
            for regime in ['calm','stress']:
                beta=b+(delta if regime=='stress' else 0);variance=v.loc['monetary','monetary']+(v.loc['monetary_stress','monetary_stress']+2*v.loc['monetary','monetary_stress'] if regime=='stress' else 0);s=float(np.sqrt(variance))
                rows.append(dict(asset=asset,regime=regime,shock='monetary',horizon_days=h,beta_pct=beta,se=s,lower95=beta-1.95996398454*s,upper95=beta+1.95996398454*s,pvalue=None,nobs=int(r.nobs),n_state=int((f.stress==(regime=='stress')).sum())))
            for date in f.index:samples.append(dict(asset=asset,horizon_days=h,date_utc=str(date.date()),event_time_utc=events.loc[date,'event_time_utc'],STMT_10bps=float(x.loc[date,'monetary']),stress=int(stress.loc[date]),actual_cumulative_pct=float(y.loc[date]),outcome_start=str((date+pd.Timedelta(days=1)).date()),outcome_end=str((date+pd.Timedelta(days=h)).date())))
        print('Monetary post-event daily LP:',asset,'all 30 horizons',flush=True)
    f=pd.DataFrame(rows);mask=f.regime=='full';f['qvalue_bh']=np.nan;f.loc[mask,'qvalue_bh']=multipletests(f.loc[mask,'pvalue'],method='fdr_bh')[1]
    delta=pd.DataFrame(differences);delta['qvalue_bh']=multipletests(delta.pvalue,method='fdr_bh')[1]
    csv(f,'monetary_LP.csv');csv(delta,'monetary_stress_differences.csv');csv(pd.DataFrame(samples),'monetary_LP_samples.csv')

def run():local_projections();joint_VAR();monetary_LP()
