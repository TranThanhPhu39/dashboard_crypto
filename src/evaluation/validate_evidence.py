"""Independent numerical, chronology and source checks for the evidence supplement."""
from src.evaluation.evidence_common import *
from scipy.stats import norm
import zipfile,itertools,subprocess,sys

def bh(p):
    p=np.asarray(p);order=np.argsort(p);q=np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1];out=np.empty(len(p));out[order]=np.minimum(q,1.);return out

def ols(X,y):
    X=np.asarray(X,float);y=np.asarray(y,float);B=np.linalg.lstsq(X,y,rcond=None)[0];e=y-X@B;n,k=X.shape;bread=np.linalg.inv(X.T@X);s=X*e[:,None];meat=s.T@s
    for lag in range(1,6):
        cross=s[lag:].T@s[:-lag];meat+=(1-lag/6)*(cross+cross.T)
    hac=bread@meat@bread*n/(n-k);hat=np.sum((X@bread)*X,axis=1);u=s/(1-hat)[:,None];hc=bread@(u.T@u)@bread
    return B,np.sqrt(np.diag(hac)),np.sqrt(np.diag(hc))

def run():
    init();checks=[];details={}
    def ok(name,value=True):assert bool(value),name;checks.append(dict(check=name,status='PASS'))
    ok('All old protected data/models/results/archives unchanged',check_protected()>0)
    for name in ['causal_analysis_lock.json','rotation_analysis_lock.json','rv_analysis_lock.json']:verify_lock(name)
    ok('Config and all pre-fit input locks match')
    for file in ['minute_source_manifest.json','rv_source_manifest.json']:
        for r in json.loads((OUT/file).read_text(encoding='utf-8')):
            assert sha(ROOT/r['file'])==r['sha256']
            if 'publisher_checksum' in r:
                assert r['publisher_checksum']==r['sha256']==(ROOT/r['checksum_file']).read_text().split()[0]
                assert sha(ROOT/r['checksum_file'])==r['checksum_sha256']
                with zipfile.ZipFile(ROOT/r['file']) as z:assert z.testzip() is None
    ok('300 minute payload hashes and250 publisher archive checksums/CRC')
    f=pd.read_csv(PANELS/'causal_panel.csv',float_precision='round_trip');a=pd.read_csv(OUT/'falsification_audit.csv')
    assert f[f.primary_joint].groupby(['asset','outcome']).size().eq(72).all();assert f[f.source_joint].groupby(['asset','outcome']).size().eq(45).all()
    assert not a.changed_old_close.any()
    for r in a.itertuples():
        t=pd.Timestamp(r.event_time_utc);p=pd.Timestamp(r.placebo_time_utc)
        assert t.tz_convert('America/New_York').tz_localize(None)-p.tz_convert('America/New_York').tz_localize(None)==pd.Timedelta(days=7)
    ok('Joint windows/sources use72/45 exact events, DST and frozen price overlap')
    # Independently recover every required endpoint and interior candle from raw JSON.
    manifests=json.loads((OUT/'minute_source_manifest.json').read_text());lookup={(r['asset'],r['date'],r['kind']):r for r in manifests}
    for r in f.itertuples():
        kind='placebo' if r.outcome=='placebo' else 'actual';m=lookup[(r.asset,r.date,kind)];c={int(row[0]):float(row[4]) for row in json.loads((ROOT/m['file']).read_bytes())};t=pd.Timestamp(m['window_time_utc']);lo,hi=(-10,20) if kind=='placebo' else config()['causal']['minute_windows'][r.outcome]
        times=np.arange(int((t+pd.Timedelta(minutes=lo)).timestamp())-60,int((t+pd.Timedelta(minutes=hi)).timestamp()),60)
        complete=all(int(v) in c for v in times)
        if complete:assert np.isclose(100*(np.log(c[int(times[-1])])-np.log(c[int(times[0])])),r.actual_pct,atol=2e-12)
        else:assert pd.isna(r.actual_pct)
    ok('All pre-event/announcement/placebo returns independently recovered, no missing bridge')
    maximum=0.
    for file in ['falsification_estimates.csv','source_comparison.csv','falsification_contrasts.csv']:
        result=pd.read_csv(OUT/file,float_precision='round_trip')
        for r in result.itertuples():
            g=f[f.asset.eq(r.asset)&(f.source_joint if file=='source_comparison.csv' else f.primary_joint)]
            if file=='falsification_contrasts.csv':
                wide=g.pivot(index='date',columns='outcome',values='actual_pct');g=g[g.outcome.eq('announcement')].sort_values('date');outcome=r.comparison.replace('announcement_minus_','');y=(wide.announcement-wide[outcome]).reindex(g.date)
            else:g=g[g.outcome.eq(r.outcome)].sort_values('date');y=g.actual_pct
            terms=[r.shock] if file=='source_comparison.csv' and r.specification!='jk' else ['policy','information']
            X=np.column_stack([np.ones(len(g))]+[g[c]*10 for c in terms]+[g[c] for c in ['prior_return','prior_vol30','prior_vix']]);B,se,hc=ols(X,y);col=1+terms.index(r.shock)
            maximum=max(maximum,abs(B[col]-r.beta),abs(se[col]-r.se_hac5),abs(hc[col]-r.se_hc3));assert np.isclose(2*norm.sf(abs(B[col]/se[col])),r.pvalue,atol=1e-10)
        assert np.allclose(bh(result.pvalue),result.qvalue_bh,atol=1e-10) and np.allclose(bh(result.pvalue_hc3),result.qvalue_hc3_bh,atol=1e-10)
    ok('Every falsification/source/direct-contrast slope, HAC5, HC3 and BH independently recomputed',maximum<1e-8);details['causal_max_error']=maximum
    old=pd.read_csv(ROOT/'data/processed/fomc_identification_20261019/analysis_panel.csv',float_precision='round_trip');inter=pd.read_csv(OUT/'regime_interaction_tests.csv',float_precision='round_trip')
    for r in inter.itertuples():
        g=old[old.asset.eq(r.asset)&old.primary_joint&old.outcome.eq(r.outcome)].sort_values('date');z=g.post2020 if r.contrast=='post2020' else (g.prior_vix>=25).astype(int);p=g.author_policy*10;i=g.author_information*10
        X=np.column_stack([np.ones(len(g)),p,i,z,p*z,i*z,g.prior_return,g.prior_vol30,g.prior_vix]);B,se,hc=ols(X,g.actual_pct);col=4 if r.shock=='policy' else 5
        assert np.allclose([B[col],se[col],hc[col]],[r.beta,r.se_hac5,r.se_hc3],atol=1e-8)
    ok('256 pooled interaction contrasts and both shock interactions independently checked',np.allclose(bh(inter.pvalue),inter.qvalue_bh))
    ranges=pd.read_csv(OUT/'full_rotation_ranges.csv',float_precision='round_trip');grid=pd.read_csv(OUT/'full_rotation_grid.csv',float_precision='round_trip')
    for r in ranges.itertuples():
        v=grid[grid.asset.eq(r.asset)&grid.shock.eq(r.shock)&grid.outcome.eq(r.outcome)].beta
        assert v.min()>=r.lower_per10bps-1e-7 and v.max()<=r.upper_per10bps+1e-7
        assert r.unbounded==(not np.isfinite([r.lower_per10bps,r.upper_per10bps]).all())
    original=pd.read_csv(OLD/'timing_estimates.csv',float_precision='round_trip').query("regime=='full'");ref=pd.read_csv(OUT/'rotation_reference_coefficients.csv',float_precision='round_trip').query('weight==.5')
    joined=ref.merge(original,on=['asset','outcome','shock']);details['unrounded_vs_published_round8_max_beta_difference']=float(np.max(abs(joined.beta-joined.beta_pct_per10bps)))
    published=pd.read_csv(ROOT/'data/raw/fomc_identification_20261019/author/shocks_fed_jk_t.csv',parse_dates=['start'],float_precision='round_trip');mat=published[['pc1','SP500']].to_numpy();good=np.isfinite(mat).all(axis=1);Q,R=np.linalg.qr(mat[good]);S=np.diag(np.where(np.diag(R)>=0,1.,-1.));Q=Q@S;R=S@R
    lo=np.arctan(R[0,1]/R[1,1]) if R[0,1]>0 else 0.;hi=np.pi/2 if R[0,1]>=0 else np.arctan(-R[1,1]/R[0,1]);t=(lo+hi)/2;P=np.array([[np.cos(t),np.sin(t)],[-np.sin(t),np.cos(t)]]);U=np.full_like(mat,np.nan);U[good]=Q@P@np.diag([R[0,0]*np.cos(t),R[0,0]*np.sin(t)])
    assert np.allclose(np.round(U[good],8),published.loc[good,['MP_median','CBI_median']],atol=1e-12,rtol=0)
    for asset in ['BTC','ETH']:
        g=old[old.asset.eq(asset)&old.primary_joint&old.outcome.eq('intraday')].sort_values('date');local=pd.to_datetime(g.event_time_utc,utc=True).dt.tz_convert('America/New_York').dt.tz_localize(None);ix=pd.Index(published.start).get_indexer(local);Y=old[old.asset.eq(asset)&old.primary_joint].pivot(index='date',columns='outcome',values='actual_pct').reindex(g.date)
        X=np.column_stack([np.ones(len(g)),U[ix]*10,g[['prior_return','prior_vol30','prior_vix']]]);B=np.linalg.lstsq(X,Y,rcond=None)[0]
        Xrounded=np.column_stack([np.ones(len(g)),np.round(U[ix],8)*10,g[['prior_return','prior_vol30','prior_vix']]]);Br=np.linalg.lstsq(Xrounded,Y,rcond=None)[0]
        for r in joined[joined.asset.eq(asset)].itertuples():
            col=1 if r.shock=='policy' else 2;oi=list(Y.columns).index(r.outcome)
            assert np.isclose(B[col,oi],r.beta,atol=1e-9) and np.isclose(Br[col,oi],r.beta_pct_per10bps,atol=1e-9)
    ok('All128 median slopes independently match before/after published8decimal rounding; analytic limits contain grid')
    array=np.load(OUT/'joint_generated_shock_bootstrap.npz');interval=pd.read_csv(OUT/'generated_shock_intervals.csv',float_precision='round_trip');weights=array['weights'];outcomes=list(array['outcomes'])
    for r in interval.itertuples():
        v=array['draws'][:,['BTC','ETH'].index(r.asset),list(weights).index(r.weight),['policy','information'].index(r.shock),outcomes.index(r.outcome)]
        assert np.allclose(np.quantile(v,[.025,.975]),[r.lower95_percentile,r.upper95_percentile],atol=1e-10)
    ok('All384 fixed-rotation sampling intervals agree with999 saved full-stage draws')
    # Reconstruct first-stage bootstrap draws using eigenvectors and weighted QR, independently of SVD/Cholesky.
    raw=pd.read_csv(ROOT/'data/raw/fomc_identification_20261019/author/source_data/fomc_surprises_jk.csv',parse_dates=['start'],float_precision='round_trip');raw=raw[raw.start.dt.year>1989].reset_index(drop=True);Xraw=raw[['MP1','FF4','ED2','ED3','ED4']].to_numpy();missing=np.isnan(Xraw).all(axis=1);Xzero=np.nan_to_num(Xraw,nan=0.);rng=np.random.default_rng(9019)
    for boot in range(5):
        starts=rng.integers(0,len(raw),size=int(np.ceil(len(raw)/8)));ix=((starts[:,None]+np.arange(8))%len(raw)).ravel()[:len(raw)];count=np.bincount(ix,minlength=len(raw));sd=Xzero[ix].std(axis=0,ddof=1);Z=Xzero[ix]/sd;vals,vectors=np.linalg.eigh(Z.T@Z);v=vectors[:,-1]
        if v[np.argmax(abs(v))]<0:v=-v
        scores=Z@v;scores[missing[ix]]=np.nan;pc=np.round((Xzero/sd)@v/np.nanstd(scores,ddof=1)*raw.ED4.iloc[ix].std(ddof=1),8);pc[missing]=np.nan;M=np.column_stack([pc,raw.SP500]);good=np.isfinite(M).all(axis=1);Q,R=np.linalg.qr(M[good]*np.sqrt(count[good,None]));S=np.diag(np.where(np.diag(R)>=0,1.,-1.));R=S@R
        lo=np.arctan(R[0,1]/R[1,1]) if R[0,1]>0 else 0.;hi=np.pi/2 if R[0,1]>=0 else np.arctan(-R[1,1]/R[0,1])
        for ai,asset in enumerate(['BTC','ETH']):
            g=old[old.asset.eq(asset)&old.primary_joint&old.outcome.eq('intraday')].sort_values('date');local=pd.to_datetime(g.event_time_utc,utc=True).dt.tz_convert('America/New_York').dt.tz_localize(None);ids=pd.Index(raw.start).get_indexer(local);Y=old[old.asset.eq(asset)&old.primary_joint].pivot(index='date',columns='outcome',values='actual_pct').reindex(g.date)[outcomes].to_numpy();design=np.column_stack([np.ones(len(g)),M[ids],g[['prior_return','prior_vol30','prior_vix']]]);sw=np.sqrt(count[ids]);B=np.linalg.lstsq(design*sw[:,None],Y*sw[:,None],rcond=None)[0]
            for wi,w in enumerate(weights):
                t=lo+w*(hi-lo);P=np.array([[np.cos(t),np.sin(t)],[-np.sin(t),np.cos(t)]]);D=np.diag([R[0,0]*np.cos(t),R[0,0]*np.sin(t)]);C=np.linalg.solve(D,P.T@R)
                assert np.allclose(C@B[1:3]/10,array['draws'][boot,ai,wi],atol=2e-6)
    ok('First5 bootstrap draws independently reproduce PCA, weighted QR and all outcome coefficients')
    # All-day RV reconstruction uses indexed boundary prices and right-closed bins.
    manifest=json.loads((OUT/'rv_source_manifest.json').read_text());max_rv=0.
    for asset in ['BTC','ETH']:
        parts=[];ninvalid=0
        for md in manifest:
            if f'/{asset}/' not in md['file']:continue
            path=ROOT/md['file'];unit='us' if int(path.name.split('-')[2])>=2025 else 'ms';scale=1_000_000 if unit=='us' else 1000
            with zipfile.ZipFile(path) as z:fraw=pd.read_csv(z.open(z.namelist()[0]),header=None,usecols=[0,4,6],names=['opening','price','ending'])
            mask=(fraw.opening%(300*scale)==0)&(fraw.ending-fraw.opening==300*scale-1);ninvalid+=int((~mask).sum());valid=fraw[mask];time=pd.to_datetime(valid.opening,unit=unit)+pd.Timedelta(minutes=5);parts.append(pd.Series(valid.price.to_numpy(),index=time))
        prices=pd.concat(parts).sort_index();assert prices.index.is_unique;prices=prices.reindex(pd.date_range(prices.index.min(),prices.index.max(),freq='5min'));r5=np.log(prices).diff();r15=np.log(prices[prices.index.minute%15==0]).diff();rv5=r5.pow(2).resample('1D',closed='right',label='left').sum(min_count=288);rv15=r15.pow(2).resample('1D',closed='right',label='left').sum(min_count=96);daily_return=r5.resample('1D',closed='right',label='left').sum(min_count=288)
        d=pd.read_csv(PANELS/f'{asset}_daily_rv.csv',parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc');ind=pd.DataFrame({'rv5':rv5,'rv15':rv15,'return_daily':daily_return}).reindex(d.index);ind.loc[ind.rv5.isna(),:]=np.nan
        assert d[['rv5','rv15']].isna().equals(ind[['rv5','rv15']].isna())
        max_rv=max(max_rv,float(np.nanmax(abs(d[['rv5','rv15','return_daily']].to_numpy()-ind.to_numpy()))));assert ninvalid==257
    ok('All daily5/15minute RVs and returns independently rebuilt, midnight included,257 invalid candles per asset audited',max_rv<1e-10);details['rv_max_error']=max_rv
    macro=pd.read_csv(ROOT/'data/processed/forecast_origins_vintage_macro.csv',parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc');frames={}
    for asset,freq,h,variant in itertools.product(['BTC','ETH'],[5,15],[1,7],['long_own','long_macro','common_own','common_macro','common_usd']):
        g=pd.read_csv(PANELS/f'{asset}_{freq}_{h}_{variant}.csv',parse_dates=['origin_utc','information_day','information_close','information_cutoff','label_close','label_available'],float_precision='round_trip').set_index('origin_utc');frames[(asset,freq,h,variant)]=g
        d=pd.read_csv(PANELS/f'{asset}_daily_rv.csv',parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc');rv=d[f'rv{freq}'];assert (g.information_day==g.index-pd.Timedelta(days=3)).all() and (g.information_close<=g.information_cutoff-pd.Timedelta(days=1)).all();assert (g.label_available==g.index+pd.Timedelta(days=h+1)).all()
        for col,v in [('rv_lag',rv),('rv7',rv.rolling(7,min_periods=7).mean()),('rv30',rv.rolling(30,min_periods=30).mean())]:assert np.allclose(g[col],v.reindex(g.information_day),atol=1e-14)
        target=rv.rolling(h,min_periods=h).sum().shift(1-h).reindex(g.index);assert np.allclose(target,g.actual,atol=1e-14)
        for c in ['vix_change_lag1_proxy','us2y_pit_change','us10y_pit_change','fed_funds_pit_change','sp500_log_return_lag1_proxy','gold_futures_log_return_lag1_proxy','oil_wti_pit_change','nfci_pit']:assert np.allclose(g[c],macro[c].reindex(g.information_day),atol=1e-13)
        for c in ['broad_usd','us2y','us10y','fed_funds','oil_wti','nfci']:
            dates=pd.to_datetime(g[c+'_pit_obs_date']);vintage=pd.to_datetime(g[c+'_pit_vintage_date']);assert (dates.dropna()<=g.information_day.loc[dates.notna()]).all() and (vintage.dropna()<=g.information_day.loc[vintage.notna()]).all()
    for asset,freq,h in itertools.product(['BTC','ETH'],[5,15],[1,7]):
        assert frames[asset,freq,h,'long_own'].index.equals(frames[asset,freq,h,'long_macro'].index)
        assert frames[asset,freq,h,'common_own'].index.equals(frames[asset,freq,h,'common_macro'].index) and frames[asset,freq,h,'common_own'].index.equals(frames[asset,freq,h,'common_usd'].index)
    ok('All40 panels: exact calendar lags, complete targets, label dates, macro vintages and matched samples')
    freeze=json.loads((MODELS/'rv_freeze.json').read_text());assert freeze['config_sha256']==sha(CONFIG) and freeze['har_models_sha256']==sha(MODELS/'har_monthly_models.json') and freeze['garch_models_sha256']==sha(MODELS/'garch_monthly_models.json') and freeze['test_predictions_sha256']==sha(OUT/'rv_test_predictions.csv')
    models=json.loads((MODELS/'har_monthly_models.json').read_text());pred=pd.read_csv(OUT/'rv_test_predictions.csv',parse_dates=['origin_utc'],float_precision='round_trip');max_har=0.
    for m in models:
        g=frames[m['asset'],m['sampling_minutes'],m['horizon_days'],m['variant']];origin=pd.Timestamp(m['refit_origin']);train=g[g.label_available<=origin-pd.Timedelta(days=1)]
        if m['window_calendar_days']:train=train[train.index>=origin-pd.Timedelta(days=m['window_calendar_days'])]
        assert len(train)==m['nobs'] and str(train.label_available.max())==m['last_label_available'];X=train[m['columns']].to_numpy().copy();X[:,:3]=np.log(X[:,:3]);mu=X.mean(0);sd=X.std(0);sd[sd==0]=1;Z=np.column_stack([np.ones(len(X)),(X-mu)/sd]);q,r=np.linalg.qr(Z);B=np.linalg.solve(r,q.T@np.log(train.actual));smear=float(np.mean(np.exp(np.log(train.actual)-Z@B)))
        assert np.allclose(B,m['coefficients'],atol=1e-8) and np.isclose(smear,m['smearing'],rtol=1e-10)
        test=g[(g.index.to_period('M')==origin.to_period('M'))&g.split.eq('test')];tx=test[m['columns']].to_numpy().copy();tx[:,:3]=np.log(tx[:,:3]);p=smear*np.exp(np.column_stack([np.ones(len(tx)),(tx-mu)/sd])@B);saved=pred[pred.asset.eq(m['asset'])&pred.sampling_minutes.eq(m['sampling_minutes'])&pred.horizon_days.eq(m['horizon_days'])&pred.variant.eq(m['variant'])&pred.model.isin(['har','har_x'])].set_index('origin_utc').reindex(test.index);max_har=max(max_har,float(np.max(abs(p-saved.predicted))));assert np.array_equal(saved.actual.to_numpy(),test.actual.to_numpy())
    ok('All monthly HAR artifacts, training-only preprocessing, smearing and forecasts independently reconstructed',max_har<1e-8);details['har_max_error']=max_har
    search=pd.read_csv(OUT/'rv_validation_search.csv');selected=pd.read_csv(OUT/'rv_selected_windows.csv');
    for r in selected.itertuples():
        s=search[search.asset.eq(r.asset)&search.sampling_minutes.eq(r.sampling_minutes)&search.horizon_days.eq(r.horizon_days)&search.variant.eq(r.variant)];assert r.validation_qlike==s.validation_qlike.min()
        g=frames[r.asset,r.sampling_minutes,r.horizon_days,r.variant];cap=g.index[g.split.eq('test')].min()-pd.Timedelta(days=1);val=g[g.split.eq('validation')&(g.label_available<=cap)];assert len(val)==int(s.n_validation.iloc[0]);assert val.label_available.max()<=cap
    ok('Validation window selection uses only labels available before first test minus24h')
    gmodels=json.loads((MODELS/'garch_monthly_models.json').read_text());gerror=0.
    for m in gmodels:
        assert m['optimizer_success'] and m['omega']>0 and m['alpha']>0 and m['beta']>0 and m['alpha']+m['beta']<1
        d=pd.read_csv(PANELS/f"{m['asset']}_daily_rv.csv",parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc');returns=d.return_daily*100;origin=pd.Timestamp(m['refit_origin']);assert pd.Timestamp(m['last_return_day'])<=origin-pd.Timedelta(days=3)
        # Scalar recursion, independent of production lfilter/segment implementation.
        state=[];v=m['initial_variance']
        for x in returns:
            state.append(v);v=m['omega']+m['alpha']*(x*x if pd.notna(x) else v)+m['beta']*v
        states=pd.Series(state,index=returns.index)
        saved=pred[pred.asset.eq(m['asset'])&pred.model.eq('garch11')&(pred.origin_utc.dt.to_period('M')==origin.to_period('M'))].drop_duplicates(['origin_utc','horizon_days'])
        for r in saved.itertuples():
            info=r.origin_utc-pd.Timedelta(days=3);v=m['omega']+m['alpha']*returns.loc[info]**2+m['beta']*states.loc[info];future=[v]
            for k in range(r.horizon_days+1):future.append(m['omega']+(m['alpha']+m['beta'])*future[-1])
            gerror=max(gerror,abs(sum(future[2:r.horizon_days+2])/10000-r.predicted))
    ok('Every GARCH test forecast: positive stationary parameters, scalar states and delayed steps3..h+2',gerror<1e-10);details['garch_max_error']=gerror
    metrics=pd.read_csv(OUT/'rv_forecast_metrics.csv')
    for r in metrics.itertuples():
        g=pred[pred.asset.eq(r.asset)&pred.sampling_minutes.eq(r.sampling_minutes)&pred.horizon_days.eq(r.horizon_days)&pred.variant.eq(r.variant)&pred.model.eq(r.model)];assert len(g)==r.n_test;assert np.isclose(np.mean(np.log(g.predicted)+g.actual/g.predicted),r.qlike,atol=1e-10) and np.isclose(np.mean((g.actual-g.predicted)**2),r.mse,atol=1e-15)
    ok('All160 paired forecast metrics use positive predictions and same actual labels')
    weight_cache={}
    def boot_means(frame):
        full=frame.reindex(pd.date_range(frame.index.min(),frame.index.max()));n=len(full)
        if n not in weight_cache:
            rng=np.random.default_rng(9020);weights=[]
            for draw in range(999):
                positions=[]
                for start in rng.integers(0,n,size=int(np.ceil(n/30))):positions.extend((int(start)+np.arange(30))%n)
                weights.append(np.bincount(np.array(positions[:n],int),minlength=n))
            weight_cache[n]=np.asarray(weights,dtype=float)
        W=weight_cache[n];A=full.to_numpy(float);mask=np.isfinite(A).astype(float)
        return (W@np.nan_to_num(A,nan=0.))/(W@mask)
    bootstrap_max=0.
    for name in ['rv_ablation_tests.csv','rv_benchmark_tests.csv']:
        result=pd.read_csv(OUT/name);assert np.allclose(bh(result.pvalue),result.qvalue_bh)
        for r in result.itertuples():
            g=pred[pred.asset.eq(r.asset)&pred.sampling_minutes.eq(r.sampling_minutes)&pred.horizon_days.eq(r.horizon_days)];learned=g[g.model.isin(['har','har_x'])]
            if name=='rv_ablation_tests.csv':a=learned[learned.variant.eq(r.base)].set_index('origin_utc');b=learned[learned.variant.eq(r.added)].set_index('origin_utc')
            else:a=g[g.variant.eq(r.variant)&g.model.eq(r.benchmark)].set_index('origin_utc');b=learned[learned.variant.eq(r.variant)].set_index('origin_utc')
            a=a.sort_index();b=b.sort_index();assert a.index.equals(b.index);delta=(np.log(b.predicted)+b.actual/b.predicted)-(np.log(a.predicted)+a.actual/a.predicted);assert np.isclose(delta.mean(),r.mean_loss_added_minus_base,atol=1e-10)
            means=boot_means(delta.to_frame('difference'))[:,0];lo,hi=np.quantile(means,[.025,.975]);p=float((1+(abs(means-delta.mean())>=abs(delta.mean())).sum())/1000)
            bootstrap_max=max(bootstrap_max,abs(lo-r.lower95),abs(hi-r.upper95));assert abs(p-r.pvalue)<5e-13,(name,p,r.pvalue)
    ok('32 macro ablations and120 benchmark comparisons: direction, paired dates and BH')
    ok('All152 calendar-block bootstrap intervals and p-values independently reproduced using resampling counts',bootstrap_max<1e-10);details['forecast_bootstrap_max_error']=bootstrap_max
    members=pd.read_csv(OUT/'rv_model_confidence_sets.csv');steps=pd.read_csv(OUT/'rv_mcs_steps.csv')
    for key,g in pred.groupby(['asset','sampling_minutes','horizon_days']):
        names=['long_own','long_macro','common_own','common_macro','common_usd','trailing30','ewma','garch11'];series=[]
        for name in names:
            s=g[(g.variant.eq(name)&g.model.isin(['har','har_x'])) if name in names[:5] else (g.variant.eq('long_own')&g.model.eq(name))].set_index('origin_utc');series.append(pd.Series(np.log(s.predicted)+s.actual/s.predicted,index=s.index,name=name))
        losses=pd.concat(series,axis=1).dropna();bs=boot_means(losses);avg=losses.mean().to_numpy();active=list(range(8));history=steps[(steps.asset==key[0])&(steps.sampling_minutes==key[1])&(steps.horizon_days==key[2])].sort_values('step')
        for saved in history.itertuples():
            d=avg[active,None]-avg[None,active];db=bs[:,active,None]-bs[:,None,active];se=db.std(0,ddof=1);np.fill_diagonal(se,np.inf)
            assert not np.any((se==0)&(abs(d)>1e-12));se[se==0]=np.inf;stat=np.max(abs(d/se));sims=np.max(abs((db-d)/se),axis=(1,2));p=float((1+(sims>=stat).sum())/1000);assert abs(p-saved.pvalue)<5e-13,(key,p,saved.pvalue)
            worst=int(np.argmax(np.max(d/se,axis=1)))
            if p<.1:assert saved.removed==names[active[worst]];active.pop(worst)
            else:assert pd.isna(saved.removed);break
        own=members[(members.asset==key[0])&(members.sampling_minutes==key[1])&(members.horizon_days==key[2])]
        assert set(own[own.retained90].model)=={names[i] for i in active}
    ok('Eight90percent MCS families independently replayed with joint common-date losses')
    protocol=LIVE/'protocol.json';assert sha(protocol)==sha(ROOT/'data/prospective/latency_20261019/protocol.json');status=json.loads((OUT/'prospective/prospective_status.json').read_text());evaluation=json.loads((OUT/'prospective/prospective_evaluation.json').read_text())
    if pd.Timestamp.now(tz='UTC')<pd.Timestamp('2027-10-21',tz='UTC'):assert evaluation['status']=='PENDING_FIXED_EVALUATION_WINDOW' and not evaluation['performance_claim']
    assert status['total_predictions']==sum(a['predictions_logged'] for a in status['attempts'])
    for file in (LIVE/'predictions').glob('*.json'):
        forecast=json.loads(file.read_text(encoding='utf-8'));origin=pd.Timestamp(forecast['origin_utc']);logged=pd.Timestamp(forecast['logged_at_utc']);assert logged<origin<=logged+pd.Timedelta(days=1) and forecast['protocol_sha256']==sha(protocol)
        envelope=ROOT/forecast['envelope'];assert sha(envelope)==forecast['envelope_sha256'];env=json.loads(envelope.read_text(encoding='utf-8'))
        for line in env['lineage'].values():assert pd.Timestamp(line['available_at_utc'])<=origin-pd.Timedelta(days=1) and sha(ROOT/line['source_file'])==line['source_sha256']
    successful_receipts=0
    for file in (RAW/'live').glob('*/manifest.json'):
        capture=json.loads(file.read_text());assert len(capture['sources'])==17
        for r in capture['sources']:
            if r['status']!='ok':assert r.get('error');continue
            successful_receipts+=1
            assert sha(ROOT/r['file'])==r['sha256']
            if r.get('request_file'):assert sha(ROOT/r['request_file'])==r['request_sha256']
    details['successful_actual_receipts']=successful_receipts
    ok('Prospective protocol unchanged, actual response provenance, no backdated forecasts or premature score')
    unit=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_evidence.py'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');assert unit.returncode==0,unit.stdout+unit.stderr
    ok('Seven edge guards passed');details['unit_stdout']=unit.stdout;details['unit_stderr']=unit.stderr
    save_json(OUT/'independent_validation.json',dict(status='PASS',checks=checks,passed=len(checks),details=details,scope='Independent numerical/provenance/chronology checks; not proof of identification assumptions, general bootstrap coverage, or future forecast skill.'))
    print('Independent evidence checks:',len(checks),'/',len(checks),flush=True)
