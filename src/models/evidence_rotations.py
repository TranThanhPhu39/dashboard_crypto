"""Analytic identified-set limits and joint first/second-stage sampling diagnostics."""
from src.evaluation.evidence_common import *
from scipy.linalg import cholesky

def geometry(M,counts=None):
    good=np.isfinite(M).all(axis=1);w=np.ones(len(M)) if counts is None else np.asarray(counts)
    A=M[good]*np.sqrt(w[good,None]);R=cholesky(A.T@A,lower=False)
    a,b=R[0,1]/R[0,0],R[1,1]/R[0,0]
    lo=float(np.arctan(a/b)) if a>0 else 0.
    hi=np.pi/2 if a>=0 else float(np.arctan(-b/a))
    return R,lo,hi

def impact(R,theta):
    a,b=R[0,1]/R[0,0],R[1,1]/R[0,0]
    return np.array([[1,a-b*np.tan(theta)],[1,a+b/np.tan(theta)]])

def pca_project(raw,indices=None):
    """Fit every generated-shock step on resampled full author rows, project original rows."""
    cols=['MP1','FF4','ED2','ED3','ED4'];X=raw[cols].to_numpy(float);missing=np.isnan(X).all(axis=1);X0=np.nan_to_num(X,nan=0.)
    ix=np.arange(len(raw)) if indices is None else indices;sample=X0[ix];sd=sample.std(axis=0,ddof=1)
    assert (sd>0).all();Z=sample/sd;_,sing,V=np.linalg.svd(Z,full_matrices=False);v=V[0]
    if v[np.argmax(abs(v))]<0:v=-v
    score=Z@v;score[missing[ix]]=np.nan
    scale=np.nanstd(raw.ED4.to_numpy()[ix],ddof=1)/np.nanstd(score,ddof=1)
    pc=np.round((X0/sd)@v*scale,8);pc[missing]=np.nan
    return np.column_stack([pc,raw.SP500.to_numpy(float)]),float(sing[0]/sing[1])

def block_indices(rng,n,block):
    starts=rng.integers(0,n,size=int(np.ceil(n/block)))
    return ((starts[:,None]+np.arange(block))%n).ravel()[:n]

def extrema_trig(A,B,lo,hi):
    candidates=[lo,hi];theta=np.arctan2(B,A)
    candidates.extend(theta+k*np.pi for k in range(-2,3) if lo<=theta+k*np.pi<=hi)
    v=[A*np.cos(t)+B*np.sin(t) for t in candidates];return float(min(v)),float(max(v))

def scaled_limit(rate,stock,c):
    if abs(stock)<1e-14:return float(rate/10)
    return float((rate+c*stock)/10)

def endpoint_ranges(R,lo,hi,beta,ncal):
    a,b=R[0,1]/R[0,0],R[1,1]/R[0,0]
    p_lo=a-b*np.tan(lo);p_hi=-np.inf if hi==np.pi/2 else a-b*np.tan(hi)
    i_lo=np.inf if lo==0 else a+b/np.tan(lo);i_hi=a if hi==np.pi/2 else a+b/np.tan(hi)
    rows=[]
    for k,(shock,c0,c1) in enumerate([('policy',p_lo,p_hi),('information',i_lo,i_hi)]):
        v=[scaled_limit(*beta,c0),scaled_limit(*beta,c1)]
        A=(R[0,0]*beta[0]+R[0,1]*beta[1])/np.sqrt(ncal);B=R[1,1]*beta[1]/np.sqrt(ncal)
        rms=extrema_trig(A,-B,lo,hi) if k==0 else extrema_trig(B,A,lo,hi)
        rows.append(dict(shock=shock,lower_per10bps=min(v),upper_per10bps=max(v),lower_per1calibration_rms=rms[0],upper_per1calibration_rms=rms[1],unbounded=bool(not np.isfinite(v).all())))
    return rows

def run():
    init();oldpanel=ROOT/'data/processed/fomc_identification_20261019/analysis_panel.csv'
    rawpath=ROOT/'data/raw/fomc_identification_20261019/author/source_data/fomc_surprises_jk.csv'
    lock_inputs('rotation_analysis_lock.json',[oldpanel,rawpath,ROOT/'data/raw/fomc_identification_20261019/author/shocks_fed_jk_t.csv'])
    raw=pd.read_csv(rawpath,parse_dates=['start'],float_precision='round_trip');raw=raw[raw.start.dt.year>1989].reset_index(drop=True)
    M,gap=pca_project(raw);R,lo,hi=geometry(M);f=pd.read_csv(oldpanel,float_precision='round_trip');outcomes=['intraday','event_day']+[f'post_{h}' for h in range(1,31)]
    groups={};base=[];ranges=[];grids=[];weights=config()['causal']['bootstrap']['rotation_weights'];point=np.zeros((2,len(weights),2,32))
    for ai,asset in enumerate(['BTC','ETH']):
        g=f[f.asset.eq(asset)&f.primary_joint&f.outcome.eq('intraday')].sort_values('date')
        starts=pd.to_datetime(g.event_time_utc,utc=True).dt.tz_convert('America/New_York').dt.tz_localize(None)
        ix=pd.Index(raw.start).get_indexer(starts);assert (ix>=0).all()
        controls=g[['prior_return','prior_vol30','prior_vix']].to_numpy()
        Y=f[f.asset.eq(asset)&f.primary_joint].pivot(index='date',columns='outcome',values='actual_pct').reindex(g.date)[outcomes].to_numpy()
        X=np.column_stack([np.ones(len(g)),M[ix],controls]);B=np.linalg.lstsq(X,Y,rcond=None)[0]
        groups[asset]=(ix,controls,Y)
        for wi,w in enumerate(weights):point[ai,wi]=impact(R,lo+w*(hi-lo))@B[1:3]/10
        for oi,name in enumerate(outcomes):
            ranges.extend(dict(asset=asset,outcome=name,**row) for row in endpoint_ranges(R,lo,hi,B[1:3,oi],int(np.isfinite(M).all(axis=1).sum())))
            for w in np.linspace(.001,.999,501):
                values=impact(R,lo+w*(hi-lo))@B[1:3,oi]/10
                for si,shock in enumerate(['policy','information']):grids.append(dict(asset=asset,outcome=name,weight=w,shock=shock,beta=values[si]))
        for wi,w in enumerate(weights):
            for si,shock in enumerate(['policy','information']):
                for oi,name in enumerate(outcomes):base.append(dict(asset=asset,weight=w,shock=shock,outcome=name,beta=point[ai,wi,si,oi]))
    csv(pd.DataFrame(ranges),'full_rotation_ranges.csv');csv(pd.DataFrame(grids),'full_rotation_grid.csv');csv(pd.DataFrame(base),'rotation_reference_coefficients.csv')
    cfg=config()['causal']['bootstrap'];rng=np.random.default_rng(cfg['seed']);draws=[];log=[]
    for bi in range(cfg['draws']):
        ixboot=block_indices(rng,len(raw),cfg['block_events']);counts=np.bincount(ixboot,minlength=len(raw))
        try:
            Mb,gb=pca_project(raw,ixboot);Rb,lb,hb=geometry(Mb,counts);result=np.zeros_like(point)
            for ai,asset in enumerate(['BTC','ETH']):
                ix,c,Y=groups[asset];w=counts[ix];X=np.column_stack([np.ones(len(ix)),Mb[ix],c]);sw=np.sqrt(w)
                assert (w>0).sum()>X.shape[1]+3 and np.linalg.matrix_rank(X*sw[:,None])==X.shape[1]
                B=np.linalg.lstsq(X*sw[:,None],Y*sw[:,None],rcond=None)[0]
                for wi,weight in enumerate(weights):result[ai,wi]=impact(Rb,lb+weight*(hb-lb))@B[1:3]/10
            assert np.isfinite(result).all();draws.append(result);log.append(dict(draw=bi,status='ok',outcome_event_rows=int(counts[groups['BTC'][0]].sum()),unique_outcome_events=int((counts[groups['BTC'][0]]>0).sum()),pca_singular_ratio=gb))
        except (AssertionError,np.linalg.LinAlgError) as exc:log.append(dict(draw=bi,status='failed',reason=str(exc)))
        if (bi+1)%200==0:print('Joint generated-shock bootstrap:',bi+1,'/',cfg['draws'],flush=True)
    array=np.asarray(draws);assert len(array)>=.95*cfg['draws'];np.savez_compressed(OUT/'joint_generated_shock_bootstrap.npz',draws=array,point=point,weights=weights,outcomes=outcomes)
    rows=[]
    for ai,asset in enumerate(['BTC','ETH']):
        for wi,w in enumerate(weights):
            for si,shock in enumerate(['policy','information']):
                for oi,name in enumerate(outcomes):
                    v=array[:,ai,wi,si,oi];lower,upper=np.quantile(v,[.025,.975]);rows.append(dict(asset=asset,weight=w,shock=shock,outcome=name,beta=point[ai,wi,si,oi],lower95_percentile=lower,upper95_percentile=upper,bootstrap_sd=float(v.std(ddof=1)),successful_draws=len(v)))
    csv(pd.DataFrame(rows),'generated_shock_intervals.csv');csv(pd.DataFrame(log),'generated_shock_draw_log.csv')
    save_json(OUT/'rotation_method.json',dict(lower_angle=lo,upper_angle=hi,calibration_events=int(np.isfinite(M).all(axis=1).sum()),pca_singular_ratio=gap,draws_requested=cfg['draws'],draws_successful=len(array),
        analytic='Coefficient = (rate coefficient + stock coefficient * stock impact)/10. Stock impact policy=a-b*tan(theta), information=a+b*cot(theta). Evaluate exact endpoint limits, including infinity. Bounds are infimum/supremum over open sign interval, not a95% CI.',
        calibration_rms='Structural shock measured at one full-author-calibration root-mean-square unit, using zero-population-mean normalization; not the standard deviation in the75-event crypto sample.',
        bootstrap='Resample all334 author events in circular8-event blocks; re-estimate PCA scaling, QR covariance and outcome regressions with matched event multiplicities. Intervals are approximate sampling intervals for fixed interior rotation functionals, not robust credible regions or confidence sets covering the entire identified set. No correction makes exclusion assumptions testable.'))
    simulation()

def simulation():
    rng=np.random.default_rng(9021);n=334;idx=np.arange(n-75,n);truthM=np.array([[2.,.2],[.2,1.3]])
    popR=cholesky(truthM,lower=False);_,lo,hi=geometry(cholesky(truthM,lower=False)*np.sqrt(2))
    # Geometry above must use population Gram, not rows of its upper factor.
    a,b=popR[0,1]/popR[0,0],popR[1,1]/popR[0,0];lo=np.arctan(a/b) if a>0 else 0.;hi=np.pi/2 if a>=0 else np.arctan(-b/a)
    slope=np.array([.2,.5]);truth=impact(popR,(lo+hi)/2)@slope/10;records=[]
    for sim in range(100):
        M=rng.multivariate_normal(np.zeros(2),truthM,n);y=M[idx]@slope+rng.normal(size=len(idx));est=[]
        for boot in range(199):
            ix=block_indices(rng,n,8);w=np.bincount(ix,minlength=n);R,l,h=geometry(M,w);X=np.column_stack([np.ones(len(idx)),M[idx]]);sw=np.sqrt(w[idx]);B=np.linalg.lstsq(X*sw[:,None],y*sw,rcond=None)[0]
            est.append(impact(R,(l+h)/2)@B[1:]/10)
        q=np.quantile(est,[.025,.975],axis=0)
        records.append(dict(simulation=sim,policy_covered=bool(q[0,0]<=truth[0]<=q[1,0]),information_covered=bool(q[0,1]<=truth[1]<=q[1,1])))
    g=pd.DataFrame(records);csv(g,'bootstrap_coverage_simulation.csv')
    save_json(OUT/'bootstrap_coverage_summary.json',dict(simulations=100,bootstrap_draws_per_simulation=199,seed=9021,policy_coverage=float(g.policy_covered.mean()),information_coverage=float(g.information_covered.mean()),max_monte_carlo_se=.05,
        dgp='IID Gaussian two-variable surprises, covariance[[2,.2],[.2,1.3]], last75 paired outcomes y=.2rate+.5stock+N(0,1). First-stage covariance/rotation and outcome slope re-estimated. This is a restricted calibration example, NOT coverage validation of the full five-derivative PCA pipeline, fat tails, nonstationarity, or set identification.'))
    print('Analytic full rotation limits, first-stage bootstrap and restricted coverage diagnostic saved.',flush=True)
