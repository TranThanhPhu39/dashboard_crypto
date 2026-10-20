"""Diagnose only the exact six joint VAR fits used in the frozen blueprint."""
from src.evaluation.robustness_common import *
from statsmodels.tsa.api import VAR
from statsmodels.stats.diagnostic import het_arch
from statsmodels.stats.multitest import multipletests

def run():
    init()
    frozen=pd.read_csv(BASE/'joint_VAR_diagnostics.csv')
    coeff=pd.read_csv(BASE/'joint_VAR_coefficients.csv')
    matrices=pd.read_csv(BASE/'recursive_SVAR_matrices.csv')
    residuals=[]; correlations=[]; arch=[]; systems=[]; replay=[]
    for row in frozen.itertuples():
        p=pd.read_csv(PANELS/f'joint_VAR_{row.yield_variable}_sessions.csv',parse_dates=['date_utc']).set_index('date_utc')
        g=p if row.regime=='full' else p.loc[:'2019-12-31'] if row.regime=='pre2020' else p.loc['2020-01-01':]
        lag=int(row.lag)
        r=VAR(g.iloc[10-lag:].reset_index(drop=True)).fit(lag)
        dates=g.index[10:]
        u=np.asarray(r.resid); names=list(p.columns);k=r.params.shape[0]
        assert len(u)==len(dates)==row.nobs
        ref=coeff[(coeff.yield_variable==row.yield_variable)&(coeff.regime==row.regime)]
        maxerr=max(abs(r.params.loc[v.term,v.equation]-v.coefficient) for v in ref.itertuples())
        m=matrices[(matrices.yield_variable==row.yield_variable)&(matrices.regime==row.regime)&(matrices.ordering=='crypto_first')]
        sigmaerr=max(abs(r.sigma_u.loc[v.row,v.column]-v.sigma) for v in m.itertuples())
        white=r.test_whiteness(nlags=20,adjusted=True)
        assert maxerr<1e-10 and sigmaerr<1e-10 and abs(white.pvalue-row.whiteness_p20)<1e-12
        replay.append(dict(yield_variable=row.yield_variable,regime=row.regime,lag=lag,nobs=len(u),
                           start_date=str(dates[0].date()),end_date=str(dates[-1].date()),coefficient_max_error=float(maxerr),
                           sigma_max_error=float(sigmaerr),whiteness_p20_error=float(abs(white.pvalue-row.whiteness_p20)),stable=bool(r.is_stable())))
        for i,date in enumerate(dates):
            for j,name in enumerate(names):
                residuals.append(dict(yield_variable=row.yield_variable,regime=row.regime,date_utc=str(date.date()),
                                      equation=name,residual=float(u[i,j]),fitted=float(r.fittedvalues.iloc[i,j]),
                                      observed=float(g.loc[date,name])))
        for L in [20,30,40]:
            w=r.test_whiteness(nlags=L,adjusted=True)
            systems.append(dict(yield_variable=row.yield_variable,regime=row.regime,lag=lag,nobs=len(u),
                                test_lags=L,statistic=float(w.test_statistic),pvalue=float(w.pvalue)))
        for j,name in enumerate(names):
            for L in [5,10]:
                lm,pvalue,fstat,fp=het_arch(u[:,j],nlags=L,ddof=k)
                arch.append(dict(yield_variable=row.yield_variable,regime=row.regime,equation=name,nobs=len(u),
                                 test_lags=L,ddof=k,lm=float(lm),pvalue=float(pvalue),fstat=float(fstat),f_pvalue=float(fp)))
        for L in range(1,41):
            for j,current in enumerate(names):
                for k2,past in enumerate(names):
                    correlations.append(dict(yield_variable=row.yield_variable,regime=row.regime,lag=L,
                                             current_equation=current,past_equation=past,
                                             correlation=float(np.corrcoef(u[L:,j],u[:-L,k2])[0,1]),
                                             squared_correlation=float(np.corrcoef(u[L:,j]**2,u[:-L,k2]**2)[0,1])))
    arch=pd.DataFrame(arch);arch['qvalue_bh_60']=multipletests(arch.pvalue,method='fdr_bh')[1]
    systems=pd.DataFrame(systems);systems['qvalue_bh_18']=multipletests(systems.pvalue,method='fdr_bh')[1]
    for f,name in [(pd.DataFrame(replay),'joint_VAR_replay.csv'),(pd.DataFrame(residuals),'joint_VAR_residuals.csv'),
                   (pd.DataFrame(correlations),'joint_VAR_residual_correlations.csv'),(arch,'joint_VAR_ARCH.csv'),
                   (systems,'joint_VAR_whiteness.csv')]:write_csv(f,name)
    print('Joint VAR: exact six fits replayed; residuals, correlations, whiteness and ARCH saved.',flush=True)
