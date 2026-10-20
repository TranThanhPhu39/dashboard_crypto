"""Exact-event source comparisons, falsification windows and direct regime contrasts."""
from src.evaluation.evidence_common import *
from research_fomc_comparison import candles,extract
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from datetime import datetime

CONTROLS=['prior_return','prior_vol30','prior_vix']

def bs_frame():
    f=pd.read_excel(RAW/'bauer_swanson.xlsx',sheet_name='FOMC (update 2023)')
    local=[pd.Timestamp(d).normalize()+pd.Timedelta(hours=datetime.strptime(str(t).strip().lower(),'%I:%M%p').hour,minutes=datetime.strptime(str(t).strip().lower(),'%I:%M%p').minute) for d,t in zip(f.Date,f.Time)]
    f['event_time_utc']=pd.DatetimeIndex(local).tz_localize('America/New_York',ambiguous='raise',nonexistent='raise').tz_convert('UTC').astype(str)
    assert f.event_time_utc.is_unique
    for c in ['MPS','MPS_ORTH']:f[c]=pd.to_numeric(f[c],errors='coerce')
    return f.rename(columns={'MPS':'bs_raw','MPS_ORTH':'bs_orth'})

def prepare():
    init();bs=bs_frame();csv(bs,'bauer_swanson_normalized.csv')
    events=pd.read_csv(OLD/'event_audit.csv',float_precision='round_trip');events=events[events.primary_joint].copy()
    events['event_time_utc']=pd.to_datetime(events.event_time_utc,utc=True).astype(str)
    events=events.merge(bs[['event_time_utc','bs_raw','bs_orth']],on='event_time_utc',how='left',validate='many_to_one')
    excluded_days=set()
    for sheet in ['Statements','Press Conferences','Minutes','Monetary Events']:
        s=pd.read_excel(ROOT/'data/raw/USMPD.xlsx',sheet_name=sheet)
        if 'Date' in s:excluded_days.update(pd.to_datetime(s.Date).dt.strftime('%Y-%m-%d').dropna())
    manifest=json.loads((OUT/'minute_source_manifest.json').read_text(encoding='utf-8'))
    lookup={(r['asset'],r['date'],r['kind']):r for r in manifest};rows=[];audit=[]
    for r in events.itertuples():
        main=lookup[(r.asset,r.date,'actual')];placebo=lookup[(r.asset,r.date,'placebo')]
        for md in [main,placebo]:assert sha(ROOT/md['file'])==md['sha256']
        c=candles(ROOT/main['file']);p=candles(ROOT/placebo['file']);t=pd.Timestamp(r.event_time_utc)
        old=candles(ROOT/r.minute_file);inter=old.index.intersection(c.index)
        changes=int((old.loc[inter,'close']!=c.loc[inter,'close']).sum());assert changes==0,'New snapshot differs on frozen minute overlap; inspect before fitting'
        pdtime=pd.Timestamp(placebo['window_time_utc']);conflict=str(pdtime.tz_convert('America/New_York').date()) in excluded_days
        values={name:extract(c,t,*bounds) for name,bounds in config()['causal']['minute_windows'].items()}
        values['placebo']=extract(p,pdtime,-10,20)
        complete=all(v['complete'] for v in values.values()) and not conflict
        audit.append(dict(asset=r.asset,date=r.date,event_time_utc=t.isoformat(),placebo_time_utc=pdtime.isoformat(),placebo_usmpd_conflict=conflict,all_windows_complete=complete,overlap_candles=len(inter),changed_old_close=changes,bs_raw_available=pd.notna(r.bs_raw),bs_orth_available=pd.notna(r.bs_orth),**{name+'_candles':v['observed_required_candles'] for name,v in values.items()}))
        for name,v in values.items():
            rows.append(dict(asset=r.asset,date=r.date,event_time_utc=t.isoformat(),outcome=name,actual_pct=v['return_pct'] if v['complete'] else np.nan,
                policy=r.author_policy,information=r.author_information,bs_raw=r.bs_raw,bs_orth=r.bs_orth,
                prior_return=r.prior_return,prior_vol30=r.prior_vol30,prior_vix=r.prior_vix,post2020=r.post2020,stress=int(r.prior_vix>=25),asset_complete=complete))
    a=pd.DataFrame(audit);ok=a.groupby('date').all_windows_complete.agg(['all','count']);dates=ok.index[ok['all']&(ok['count']==2)]
    f=pd.DataFrame(rows);f['primary_joint']=f.date.isin(dates)
    f['source_joint']=f.primary_joint & f[['bs_raw','bs_orth']].notna().all(axis=1)
    a['primary_joint']=a.date.isin(dates)
    csv(a,'falsification_audit.csv');f.to_csv(PANELS/'causal_panel.csv',index=False,encoding='utf-8-sig',float_format='%.17g')
    summary=dict(old_joint_events=75,falsification_joint_events=len(dates),source_joint_events=int(f[f.asset.eq('BTC')&f.outcome.eq('announcement')].source_joint.sum()),
        bs_first=str(bs.Date.min()),bs_last=str(bs.Date.max()),bs_rows=len(bs),bs_orth_missing=int(bs.bs_orth.isna().sum()),bs_covid_missing_rule='Publisher leaves March-December2020 orthogonalized surprises missing; no substitution',
        bs_units='Workbook rate changes in percentage points, MPS scaled to unit ED4 impact. Regress on component*10 for +10bps. Chart download uses bps, distinct from workbook',
        window_caveat='Nominal 30m alignment only: author shock uses quote medians, crypto uses exact minute closes. BS workbook is not claimed to reproduce identical ticks. Placebo screens USMPD communication dates only, not all other macro/crypto news')
    save_json(OUT/'causal_audit_summary.json',summary)
    lock_inputs('causal_analysis_lock.json',[PANELS/'causal_panel.csv',OUT/'falsification_audit.csv',RAW/'bauer_swanson.xlsx',OUT/'minute_source_manifest.json'])
    print(json.dumps(summary,indent=2),flush=True)

def estimate(X,y):
    X=np.asarray(X,float);y=np.asarray(y,float)
    assert np.isfinite(X).all() and np.isfinite(y).all() and len(y)>X.shape[1]+3 and np.linalg.matrix_rank(X)==X.shape[1]
    m=sm.OLS(y,X)
    return m.fit(cov_type='HAC',cov_kwds={'maxlags':5,'use_correction':True}),m.fit(cov_type='HC3')

def design(g,terms):
    return np.column_stack([np.ones(len(g))]+[g[t].to_numpy()*10 for t in terms]+[g[c].to_numpy() for c in CONTROLS])

def record(r,h,col,**meta):
    b=float(r.params[col]);se=float(r.bse[col]);hc=float(h.bse[col])
    return dict(meta,beta=b,se_hac5=se,lower95=b-1.95996398454*se,upper95=b+1.95996398454*se,pvalue=float(r.pvalues[col]),se_hc3=hc,pvalue_hc3=float(h.pvalues[col]),nobs=int(r.nobs))

def bh(frame):
    frame['qvalue_bh']=multipletests(frame.pvalue,method='fdr_bh')[1]
    frame['qvalue_hc3_bh']=multipletests(frame.pvalue_hc3,method='fdr_bh')[1]
    return frame

def fit():
    verify_lock('causal_analysis_lock.json');f=pd.read_csv(PANELS/'causal_panel.csv',float_precision='round_trip');rows=[];sources=[];direct=[]
    for (asset,outcome),g in f[f.primary_joint].groupby(['asset','outcome']):
        g=g.sort_values('date');X=design(g,['policy','information']);r,h=estimate(X,g.actual_pct)
        for i,t in enumerate(['policy','information'],1):rows.append(record(r,h,i,asset=asset,outcome=outcome,shock=t,scope='falsification'))
    for (asset,outcome),g in f[f.source_joint].groupby(['asset','outcome']):
        g=g.sort_values('date')
        for spec,terms in [('jk',['policy','information']),('bs_raw',['bs_raw']),('bs_orth',['bs_orth'])]:
            X=design(g,terms);r,h=estimate(X,g.actual_pct)
            for i,t in enumerate(terms,1):
                row=record(r,h,i,asset=asset,outcome=outcome,shock=t,specification=spec,scope='same_source_intersection')
                row['sample_sd_bps']=float(g[t].std(ddof=1)*100);row['beta_pct_per1sd']=row['beta']*row['sample_sd_bps']/10;sources.append(row)
    for asset in ['BTC','ETH']:
        g=f[f.primary_joint&f.asset.eq(asset)&f.outcome.eq('announcement')].sort_values('date')
        wide=f[f.primary_joint&f.asset.eq(asset)].pivot(index='date',columns='outcome',values='actual_pct').reindex(g.date)
        for outcome in ['pre_early','pre_late','placebo']:
            r,h=estimate(design(g,['policy','information']),wide.announcement-wide[outcome])
            for i,t in enumerate(['policy','information'],1):direct.append(record(r,h,i,asset=asset,comparison='announcement_minus_'+outcome,shock=t))
    for frame,name in [(bh(pd.DataFrame(rows)),'falsification_estimates.csv'),(bh(pd.DataFrame(sources)),'source_comparison.csv'),(bh(pd.DataFrame(direct)),'falsification_contrasts.csv')]:csv(frame,name)
    # Full 32-outcome, original75-event direct interactions, not separate-regression p-value comparisons.
    old=pd.read_csv(ROOT/'data/processed/fomc_identification_20261019/analysis_panel.csv',float_precision='round_trip');rows=[];counts=[]
    for (asset,outcome),g in old[old.primary_joint].groupby(['asset','outcome']):
        g=g.sort_values('date')
        for regime in ['post2020','stress']:
            z=g.post2020.to_numpy() if regime=='post2020' else (g.prior_vix>=25).astype(int).to_numpy()
            counts.append(dict(asset=asset,outcome=outcome,contrast=regime,n0=int((z==0).sum()),n1=int((z==1).sum())))
            # include both components and both interactions; all lower-order regressors present
            p=g.author_policy.to_numpy()*10;i=g.author_information.to_numpy()*10
            X=np.column_stack([np.ones(len(g)),p,i,z,p*z,i*z]+[g[c].to_numpy() for c in CONTROLS])
            r,h=estimate(X,g.actual_pct)
            for j,t in [(4,'policy'),(5,'information')]:rows.append(record(r,h,j,asset=asset,outcome=outcome,contrast=regime,shock=t,n_group1=int(z.sum()),n_group0=int((1-z).sum())))
    csv(bh(pd.DataFrame(rows)),'regime_interaction_tests.csv');csv(pd.DataFrame(counts),'interaction_sample_counts.csv')
    save_json(OUT/'causal_families.json',dict(falsification=len(pd.read_csv(OUT/'falsification_estimates.csv')),source_comparison=len(pd.read_csv(OUT/'source_comparison.csv')),direct_falsification=len(direct),regime_interactions=len(rows),interpretation='Exploratory conditional HAC5/HC3 inference, fixed shock series. Falsification non-rejection cannot establish exogeneity; no random assignment of FOMC dates. Stress small sample remains a limitation.'))
    print('Causal source/falsification and256 direct regime contrasts saved.',flush=True)
