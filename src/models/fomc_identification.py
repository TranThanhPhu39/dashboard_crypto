"""Audit first, reproduce published shock construction, then matched timing regressions."""
from src.evaluation.fomc_identification_common import *
from research_fomc_comparison import candles,extract
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

def median_rotation(M,w=.5):
    """Independent NumPy implementation of the author's normalized QR rotation."""
    M=np.asarray(M,dtype=float);valid=np.isfinite(M).all(axis=1);A=M[valid]
    assert len(A)>2 and np.linalg.matrix_rank(A)==2 and 0<w<1
    Q,R=np.linalg.qr(A,mode='reduced');S=np.diag(np.where(np.diag(R)>=0,1.,-1.));Q=Q@S;R=S@R
    low=np.arctan(R[0,1]/R[1,1]) if R[0,1]>0 else 0.
    high=np.pi/2 if R[0,1]>=0 else np.arctan(-R[1,1]/R[0,1])
    angle=(1-w)*low+w*high;c,s=np.cos(angle),np.sin(angle)
    P=np.array([[c,s],[-s,c]]);D=np.diag([R[0,0]*c,R[0,0]*s])
    shocks=np.full_like(M,np.nan);shocks[valid]=Q@P@D
    impact=np.linalg.solve(D,P.T@R)
    return shocks,impact,dict(angle=float(angle),lower_angle=float(low),upper_angle=float(high),weight=w)

def decompose():
    folder=RAW/'author';j=pd.read_csv(folder/'shocks_fed_jk_t.csv',parse_dates=['start'],float_precision='round_trip')
    source=pd.read_csv(folder/'source_data/fomc_surprises_jk.csv',parse_dates=['start'],float_precision='round_trip')
    source=source[source.start.dt.year>1989].copy();assert source.start.tolist()==j.start.tolist()
    X=source[['MP1','FF4','ED2','ED3','ED4']].to_numpy();all_missing=np.isnan(X).all(axis=1)
    X=np.nan_to_num(X,nan=0.);sd=X.std(axis=0,ddof=1);assert (sd>0).all();X=X/sd
    _,_,V=np.linalg.svd(X,full_matrices=False);v=V[0]
    if v[np.argmax(abs(v))]<0:v=-v
    score=X@v;score[all_missing]=np.nan
    pc=score/np.nanstd(score,ddof=1)*source.ED4.std(ddof=1)
    # MATLAB rounds at 8 decimals before the sign rotation.
    pc=np.round(pc,8);pca_error=float(np.nanmax(abs(pc-j.pc1.to_numpy())))
    assert pca_error<2e-8,('PCA does not reproduce the pinned author series',pca_error)
    M=j[['pc1','SP500']].to_numpy();rows=[];impacts=[];error=0.
    for w in [.1,.5,.9]:
        U,C,details=median_rotation(M,w)
        assert C[0,1]<0<C[1,1] and np.allclose(C[:,0],1)
        if w==.5:
            good=np.isfinite(M).all(axis=1)
            error=float(np.max(abs(U[good]-j.loc[good,['MP_median','CBI_median']].to_numpy())))
            assert error<2e-8,('Published median shocks not reproduced',error)
        for i,row in j.iterrows():
            rows.append(dict(start=row.start,weight=w,pc1=float(row.pc1),stock_surprise_log_pct=row.SP500,
                             policy_component=U[i,0],information_component=U[i,1],
                             input_complete=bool(np.isfinite(M[i]).all()),published_policy=row.MP_median,published_information=row.CBI_median))
        impacts.append(dict(weight=w,policy_to_rate=float(C[0,0]),information_to_rate=float(C[1,0]),policy_to_stock=float(C[0,1]),information_to_stock=float(C[1,1]),
                            shock_uncentered_crossproduct=float((U[np.isfinite(U).all(axis=1)].T@U[np.isfinite(U).all(axis=1)])[0,1]),**{k:v for k,v in details.items() if k!='weight'}))
    csv(pd.DataFrame(rows),'author_rotation_shocks.csv');csv(pd.DataFrame(impacts),'author_rotation_impacts.csv')
    save_json(OUT/'decomposition_replay.json',dict(author_rows=len(j),complete_input_rows=int(np.isfinite(M).all(axis=1).sum()),pca_max_error=pca_error,median_component_max_error=error,
              missing_policy='Published missing-input zero placeholders excluded from crypto identification; no imputation',
              caveat='Normalized component shocks are orthogonal in uncentered second moments, following author zero-population-mean assumption. Not a posterior or full identified-set uncertainty calculation.'))
    return j,pd.DataFrame(rows)

def daily_panel(asset):
    f=pd.read_csv(PANELS/f'{asset}_Coinbase_daily.csv',parse_dates=['date_utc'],float_precision='round_trip').set_index('date_utc')
    calendar=pd.date_range(pd.Timestamp(config()['sample'][0])-pd.Timedelta(days=35),pd.Timestamp(config()['sample'][1]),name='date_utc')
    prices=f.close.reindex(calendar);r=100*np.log(prices).diff()
    vol=np.sqrt(365*(r/100).pow(2).rolling(30,min_periods=30).mean()).shift(2)
    return pd.DataFrame(dict(close=prices,return_pct=r,prior_return=r.shift(2),prior_vol30=vol),index=calendar)

def audit():
    init();j,rotations=decompose()
    e=pd.read_excel(ROOT/'data/raw/USMPD.xlsx',sheet_name='Statements');e=e[e.Date.between(*config()['sample'])].copy()
    e['event_time_et']=pd.to_datetime(e.date_time).dt.tz_localize('America/New_York',ambiguous='raise',nonexistent='raise')
    e['event_time_utc']=e.event_time_et.dt.tz_convert('UTC');e['date_utc']=e.event_time_utc.dt.tz_localize(None).dt.normalize()
    e['date']=e.Date.dt.strftime('%Y-%m-%d');assert not e.date_time.duplicated().any()
    author=j.rename(columns={'start':'author_time_local'});e=e.merge(author,left_on='date_time',right_on='author_time_local',how='left',validate='one_to_one',indicator='author_match')
    e['shock_input_complete']=e[['pc1','SP500_y','MP_median','CBI_median']].notna().all(axis=1)
    # Preserve distinct stock definitions; USMPD SP500 is simple percent, author is log percent.
    e=e.rename(columns={'SP500_x':'usmpd_sp500_simple_pct','SP500_y':'author_sp500_log_pct'})
    old=pd.read_csv(ROOT/'data/processed/fomc_crypto_statement_windows.csv')
    old['event_time_utc']=pd.to_datetime(old.event_time_utc,utc=True)
    vix=pd.read_csv(ROOT/'data/processed/blueprint_20261019/calendar_information.csv',parse_dates=['date_utc']).set_index('date_utc').vix_available_proxy
    records=[];source=[];outcomes=[]
    for asset in ['BTC','ETH']:
        d=daily_panel(asset)
        for event in e.itertuples():
            expected=old[(old.asset==asset)&(old.event_time_utc==event.event_time_utc)]
            minute=dict(complete=False,endpoints=False,expected_candles=31,observed_required_candles=0,return_pct=np.nan)
            file=None;digest=None;status='cache_missing'
            if len(expected):
                row=expected.iloc[0];path=ROOT/'data/raw/fomc_coinbase'/row.source_file
                if path.exists():
                    assert sha(path)==row.sha256
                    c=candles(path);minute=extract(c,event.event_time_utc,-10,20);file=path.relative_to(ROOT).as_posix();digest=sha(path)
                    status='complete' if minute['complete'] else 'no_history' if not len(c) else 'endpoints_only' if minute['endpoints'] else 'missing_boundary'
                    source.append(dict(asset=asset,date=event.date,file=file,sha256=digest,source='Frozen Coinbase minute cache',url=row.url))
            date=event.date_utc;daily={}
            daily['intraday']=minute['return_pct'] if minute['complete'] else np.nan
            daily['event_day']=d.loc[date,'return_pct'] if date in d.index else np.nan
            for h in range(1,31):
                dates=pd.date_range(date+pd.Timedelta(days=1),date+pd.Timedelta(days=h))
                values=d.return_pct.reindex(dates);daily[f'post_{h}']=float(values.sum()) if values.notna().all() else np.nan
            prior_return=d.loc[date,'prior_return'];prior_vol=d.loc[date,'prior_vol30'];prior_vix=vix.reindex([date]).iloc[0]
            controls_ok=bool(np.isfinite([prior_return,prior_vol,prior_vix]).all())
            daily_ok=all(pd.notna(value) for key,value in daily.items() if key!='intraday')
            record=dict(asset=asset,date=event.date,event_time_et=event.event_time_et.isoformat(),event_time_utc=event.event_time_utc.isoformat(),scheduled=bool(event.Unscheduled==0),
                        author_exact_match=bool(event.author_match=='both'),shock_input_complete=bool(event.shock_input_complete),
                        author_policy=event.MP_median,author_information=event.CBI_median,pc1=event.pc1,
                        usmpd_FF3_pp=event.FF3,usmpd_FF3_bps=event.FF3*100,usmpd_OIS1Y_pp=event.OIS1Y,usmpd_UST2Y_pp=event.UST2Y,
                        usmpd_stock_simple_pct=event.usmpd_sp500_simple_pct,author_stock_log_pct=event.author_sp500_log_pct,
                        minute_status=status,minute_complete=bool(minute['complete']),minute_required=31,minute_observed=int(minute['observed_required_candles']),
                        daily_all_h30_complete=bool(daily_ok),controls_complete=controls_ok,prior_return=prior_return,prior_vol30=prior_vol,prior_vix=prior_vix,
                        post2020=int(date>=pd.Timestamp('2020-01-01')),minute_file=file,minute_sha256=digest)
            record['daily_eligible']=record['scheduled'] and record['shock_input_complete'] and daily_ok and controls_ok
            record['asset_eligible']=record['daily_eligible'] and record['minute_complete']
            records.append(record)
            for name,value in daily.items():outcomes.append(dict(asset=asset,date=event.date,outcome=name,actual_pct=value))
    audit=pd.DataFrame(records);joint=audit.groupby('date').asset_eligible.agg(['all','count']);dates=joint.index[joint['all']&(joint['count']==2)]
    audit['primary_joint']=audit.date.isin(dates)
    f=pd.DataFrame(outcomes).merge(audit,on=['asset','date'],how='left',validate='many_to_one')
    f.to_csv(PANELS/'analysis_panel.csv',index=False,encoding='utf-8-sig',float_format='%.17g')
    csv(audit,'event_audit.csv');csv(pd.DataFrame(source),'minute_source_log.csv')
    cov=audit.groupby(['asset','post2020']).agg(universe=('date','size'),scheduled=('scheduled','sum'),author_exact=('author_exact_match','sum'),minute_complete=('minute_complete','sum'),daily_eligible=('daily_eligible','sum'),primary_joint=('primary_joint','sum')).reset_index()
    csv(cov,'coverage_summary.csv')
    missing=audit[~audit.primary_joint].copy();missing['reason']=missing.apply(lambda r:'; '.join(name for name,ok in [('unscheduled',r.scheduled),('author_missing_or_timestamp',r.shock_input_complete),('incomplete_minute',r.minute_complete),('daily_or_h30_missing',r.daily_all_h30_complete),('prior_controls_missing',r.controls_complete)] if not ok) or 'other_asset_not_eligible',axis=1)
    csv(missing,'exclusions.csv')
    # Timestamp mismatches are reported; no shifting/nearest-date substitution.
    e[e.author_match!='both'][['date','date_time','Unscheduled']].to_csv(OUT/'unmatched_author_events.csv',index=False,encoding='utf-8-sig')
    summary=dict(total_statements=len(e),scheduled=int((e.Unscheduled==0).sum()),author_exact_matches=int((e.author_match=='both').sum()),primary_joint_events=len(dates),
                 primary_pre2020=int(sum(d<'2020-01-01' for d in dates)),primary_post2020=int(sum(d>='2020-01-01' for d in dates)),
                 author_last_event=str(j.start.max()),author_commit=json.loads((RAW/'author/manifest.json').read_text())['commit'],
                 eligible_for_primary_fit=bool(len(dates)>=config()['minimum_fit_rows']),all_old_files_unchanged=bool(check_protected()))
    save_json(OUT/'audit_summary.json',summary)
    lock=dict(config_sha256=sha(CONFIG),panel_sha256=sha(PANELS/'analysis_panel.csv'),author_manifest_sha256=sha(RAW/'author/manifest.json'),event_audit_sha256=sha(OUT/'event_audit.csv'))
    path=OUT/'analysis_lock.json'
    if path.exists():assert json.loads(path.read_text())==lock
    else:save_json(path,lock)
    print(json.dumps(summary,indent=2),flush=True)

def regress(g,X,y):
    keep=np.isfinite(y)&np.isfinite(X).all(axis=1);X=X.loc[keep];y=y.loc[keep]
    assert len(X)>=config()['minimum_fit_rows'] and np.linalg.matrix_rank(X)==X.shape[1]
    return sm.OLS(y,X).fit(cov_type='HAC',cov_kwds={'maxlags':5,'use_correction':True})

def design(g,weight,rotations):
    x=pd.DataFrame(index=g.index)
    if weight==.5:
        x['policy']=g.author_policy*10;x['information']=g.author_information*10
    else:
        rotation=rotations[rotations.weight==weight].copy();rotation['event_time_utc']=pd.to_datetime(rotation.start).dt.tz_localize('America/New_York').dt.tz_convert('UTC').astype(str)
        bytime=rotation.set_index('event_time_utc');keys=pd.to_datetime(g.event_time_utc,utc=True).astype(str)
        x['policy']=bytime.policy_component.reindex(keys).to_numpy()*10;x['information']=bytime.information_component.reindex(keys).to_numpy()*10
    for c in ['prior_return','prior_vol30','prior_vix']:x[c]=g[c]
    return sm.add_constant(x,has_constant='add')

def fit():
    init();lock=json.loads((OUT/'analysis_lock.json').read_text());assert lock['config_sha256']==sha(CONFIG) and lock['panel_sha256']==sha(PANELS/'analysis_panel.csv')
    f=pd.read_csv(PANELS/'analysis_panel.csv',float_precision='round_trip');rotations=pd.read_csv(OUT/'author_rotation_shocks.csv')
    rows=[];coefs=[];residuals=[];sensitivity=[];differences=[];counts=[]
    for asset in ['BTC','ETH']:
        for outcome in ['intraday','event_day']+[f'post_{h}' for h in range(1,31)]:
            primary=f[(f.asset==asset)&f.primary_joint&(f.outcome==outcome)].sort_values('date').reset_index(drop=True)
            for regime in ['full','pre2020','post2020']:
                g=primary if regime=='full' else primary[primary.post2020==(regime=='post2020')]
                counts.append(dict(asset=asset,outcome=outcome,regime=regime,nobs=len(g)))
                if len(g)<config()['minimum_fit_rows']:continue
                X=design(g,.5,rotations);r=regress(g,X,g.actual_pct)
                for term in ['policy','information']:
                    b=float(r.params[term]);se=float(r.bse[term]);rows.append(dict(asset=asset,outcome=outcome,regime=regime,shock=term,beta_pct_per10bps=b,se=se,lower95=b-1.95996398454*se,upper95=b+1.95996398454*se,pvalue=float(r.pvalues[term]),nobs=int(r.nobs)))
                for term in X.columns:coefs.append(dict(asset=asset,outcome=outcome,regime=regime,term=term,coefficient=float(r.params[term])))
                if regime=='full':
                    for i,record in enumerate(g.itertuples()):residuals.append(dict(asset=asset,outcome=outcome,date=record.date,actual_pct=float(record.actual_pct),fitted_pct=float(r.fittedvalues.iloc[i]),residual_pct=float(r.resid.iloc[i])))
            for weight in [.1,.5,.9]:
                X=design(primary,weight,rotations);r=regress(primary,X,primary.actual_pct)
                for term in ['policy','information']:sensitivity.append(dict(asset=asset,outcome=outcome,weight=weight,shock=term,beta_pct_per10bps=float(r.params[term]),nobs=int(r.nobs)))
        # Direct timing differences: same regressors/rows, not p-value comparisons.
        wide=f[(f.asset==asset)&f.primary_joint].pivot(index='date',columns='outcome',values='actual_pct')
        g=f[(f.asset==asset)&f.primary_joint&(f.outcome=='intraday')].sort_values('date').reset_index(drop=True)
        X=design(g,.5,rotations)
        for name in ['event_day','post_7']:
            y=pd.Series((wide[name]-wide.intraday).reindex(g.date).to_numpy(),index=g.index);r=regress(g,X,y)
            for term in ['policy','information']:
                b=float(r.params[term]);se=float(r.bse[term]);differences.append(dict(asset=asset,comparison=name+'_minus_intraday',shock=term,difference_pct_per10bps=b,se=se,lower95=b-1.95996398454*se,upper95=b+1.95996398454*se,pvalue=float(r.pvalues[term]),nobs=int(r.nobs)))
    result=pd.DataFrame(rows);result['qvalue_bh']=np.nan
    for label,family in [('full',128),('periods',256)]:
        mask=result.regime.eq('full') if label=='full' else result.regime.ne('full');idx=result.index[mask]
        p=np.r_[result.loc[idx,'pvalue'],np.ones(family-len(idx))];result.loc[idx,'qvalue_bh']=multipletests(p,method='fdr_bh')[1][:len(idx)]
    diff=pd.DataFrame(differences);diff['qvalue_bh8']=multipletests(diff.pvalue,method='fdr_bh')[1]
    daily=[]
    for (asset,outcome),g in f[f.daily_eligible&f.outcome.ne('intraday')].groupby(['asset','outcome']):
        g=g.sort_values('date').reset_index(drop=True)
        if len(g)<config()['minimum_fit_rows']:continue
        X=design(g,.5,rotations);r=regress(g,X,g.actual_pct)
        for term in ['policy','information']:daily.append(dict(asset=asset,outcome=outcome,shock=term,beta_pct_per10bps=float(r.params[term]),nobs=int(r.nobs)))
    for frame,name in [(result,'timing_estimates.csv'),(pd.DataFrame(coefs),'timing_coefficients.csv'),(pd.DataFrame(residuals),'primary_residuals.csv'),(pd.DataFrame(sensitivity),'rotation_sensitivity.csv'),(diff,'timing_difference_tests.csv'),(pd.DataFrame(counts),'fit_sample_counts.csv'),(pd.DataFrame(daily),'daily_coverage_sensitivity.csv')]:csv(frame,name)
    print('FOMC matched timing regressions, direct differences and rotation sensitivity saved.',flush=True)

def influence():
    """Explicitly post-hoc point sensitivity, never a rule for sample deletion."""
    init();path=OUT/'influence_diagnostic_spec.json'
    spec=dict(status='Post-hoc diagnostic added after observing main coefficients',scope='All128 full-sample coefficients, all75 single-event deletions; no p-values, no sample/model selection',method='OLS case-deletion identity, unchanged prior controls and shock construction; shocks not re-estimated after deleting crypto outcome row')
    if path.exists():assert json.loads(path.read_text())==spec
    else:save_json(path,spec)
    f=pd.read_csv(PANELS/'analysis_panel.csv',float_precision='round_trip');rot=pd.read_csv(OUT/'author_rotation_shocks.csv');rows=[];eventrows=[]
    for asset in ['BTC','ETH']:
        g=f[(f.asset==asset)&f.primary_joint&(f.outcome=='intraday')].sort_values('date').reset_index(drop=True)
        X=design(g,.5,rot).to_numpy();bread=np.linalg.inv(X.T@X);hat=np.einsum('ij,jk,ik->i',X,bread,X)
        outcomes=f[(f.asset==asset)&f.primary_joint].pivot(index='date',columns='outcome',values='actual_pct').reindex(g.date)
        Y=outcomes.to_numpy();B=np.linalg.lstsq(X,Y,rcond=None)[0];E=Y-X@B;n,k=X.shape
        for j,name in enumerate(outcomes.columns):
            scale=float(np.sum(E[:,j]**2)/(n-k))
            for i,date in enumerate(g.date):
                drop=B[:,j]-(bread@X[i])*E[i,j]/(1-hat[i])
                eventrows.append(dict(asset=asset,outcome=name,date=date,leverage=float(hat[i]),cooks_distance=float(E[i,j]**2/(k*scale)*hat[i]/(1-hat[i])**2)))
                for col,term in [(1,'policy'),(2,'information')]:
                    rows.append(dict(asset=asset,outcome=name,shock=term,omitted_date=date,beta_pct_per10bps=float(drop[col]),baseline_beta=float(B[col,j]),sign_change=bool(drop[col]*B[col,j]<0)))
    f=pd.DataFrame(rows);csv(f,'leave_one_event_out.csv');csv(pd.DataFrame(eventrows),'event_influence.csv')
    ranges=f.groupby(['asset','outcome','shock']).agg(min_beta=('beta_pct_per10bps','min'),max_beta=('beta_pct_per10bps','max'),sign_changes=('sign_change','sum')).reset_index()
    csv(ranges,'influence_ranges.csv');print('Post-hoc all-event point sensitivity saved; main sample unchanged.',flush=True)
