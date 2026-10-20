"""Quantile slopes with exploratory circular moving-block pairs bootstrap."""
from src.utils.project import *
import warnings,time
from statsmodels.regression.quantile_regression import QuantReg
from threadpoolctl import threadpool_limits

def run():
    cfg=config()['quantile'];p=panel('calendar_information.csv');rows=[];bootrows=[];issues=[];rng=np.random.default_rng(9)
    with threadpool_limits(limits=2):
        for asset in ['btc','eth']:
            x=p[list(SHOCKS)].copy();x['prior_crypto']=p[asset+'_return_pct'].shift(2)
            f=x.assign(outcome=p[asset+'_return_pct']).dropna()
            for regime,g in [('full',f),('pre2020',f.loc[:'2019-12-31']),('post2020',f.loc['2020-01-01':])]:
                raw=g.drop(columns='outcome');mu=raw.mean();sd=raw.std(ddof=0);X=np.column_stack([np.ones(len(g)),((raw-mu)/sd).to_numpy()]);y=g.outcome.to_numpy();n=len(y)
                for tau in cfg['taus']:
                    started=time.time()
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always');fit=QuantReg(y,X).fit(q=tau,max_iter=cfg['max_iter'],p_tol=1e-7)
                    if caught:issues.extend(dict(asset=asset,regime=regime,tau=tau,replicate='main',message=str(w.message)) for w in caught)
                    main_warning_count=len(caught)
                    draws=[]
                    for rep in range(99):
                        starts=rng.integers(0,n,size=int(np.ceil(n/20)));idx=np.concatenate([(start+np.arange(20))%n for start in starts])[:n]
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter('always');r=QuantReg(y[idx],X[idx]).fit(q=tau,max_iter=cfg['max_iter'],p_tol=1e-6)
                        if caught:
                            issues.extend(dict(asset=asset,regime=regime,tau=tau,replicate=rep,message=str(w.message)) for w in caught)
                            continue
                        draws.append(r.params)
                        for j,(shock,scale) in enumerate(SHOCKS.items(),1):bootrows.append(dict(asset=asset,regime=regime,tau=tau,replicate=rep,shock=shock,beta_pct=float(r.params[j]/sd[shock]*scale)))
                    draws=np.asarray(draws);assert len(draws)>=80, 'Too few converged block-bootstrap fits; do not report unreliable CI.'
                    for j,(shock,scale) in enumerate(SHOCKS.items(),1):
                        values=draws[:,j]/sd[shock]*scale;lo,hi=np.quantile(values,[.025,.975]);rows.append(dict(asset=asset,regime=regime,tau=tau,shock=shock,beta_pct=float(fit.params[j]/sd[shock]*scale),lower95=float(lo),upper95=float(hi),nobs=n,successful_bootstraps=len(draws),planned_bootstraps=99,main_iterations=int(fit.iterations),main_warnings=main_warning_count))
                    print('Quantile/block bootstrap:',asset,regime,tau,'successful',len(draws),'seconds',round(time.time()-started,1),flush=True)
    csv(pd.DataFrame(rows),'quantile_effects.csv');csv(pd.DataFrame(bootrows),'quantile_bootstrap_draws.csv');save_json(OUT/'quantile_warnings.json',issues)
