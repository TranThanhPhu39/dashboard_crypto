"""Read-only consistency checks for the LP/FOMC/rolling synthesis."""
from research_common import *
import hashlib, re
from urllib.parse import unquote
from statsmodels.stats.multitest import multipletests

OUT=RESULTS/'synthesis'

def main():
    audit=json.loads((OUT/'validation.json').read_text())
    checks={'all_protected_files_unchanged':all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in audit['protected_sha256'].items()),
            'method_unchanged':hashlib.sha256((OUT/'method.json').read_bytes()).hexdigest()==audit['method_sha256']}
    html=(OUT/'dashboard.html').read_text(encoding='utf-8')
    payload=json.loads(re.search(r'const DATA=(.*?);\nconst el=',html,re.S).group(1))
    lp=pd.read_csv(TABLES/'local_projections.csv'); inter=pd.read_csv(TABLES/'regime_interactions.csv')
    events=pd.read_csv(RESULTS/'fomc_comparison/regressions.csv'); events=events[events.family=='primary_matched']
    for key,frame in [('lp',lp),('interactions',inter),('rolling',pd.read_csv(TABLES/'rolling_sensitivity.csv')),('events',events)]:
        saved=pd.DataFrame(payload[key]); cols=list(frame.columns)
        checks[key+'_payload_same_order_and_labels']=len(saved)==len(frame) and all(saved[c].tolist()==frame[c].tolist() for c in frame.select_dtypes(exclude='number').columns)
        checks[key+'_payload_numeric_matches']=all(np.allclose(saved[c],frame[c],atol=1e-12,rtol=1e-10,equal_nan=True) for c in frame.select_dtypes(include='number').columns)
    checks['LP_grid_complete']=len(lp)==168 and not lp.duplicated(['asset','regime','shock','horizon_sessions']).any() and set(lp.horizon_sessions)=={0,1,2,5,10,20,30}
    checks['LP_BH_168_recomputed']=np.allclose(lp.qvalue_bh,multipletests(lp.pvalue,method='fdr_bh')[1],atol=1e-8,rtol=1e-7)
    checks['LP_pointwise_CI_arithmetic']=np.allclose(lp.lower95,lp.beta_pct-1.959963984540054*lp.se,atol=1e-7,rtol=1e-7) and np.allclose(lp.upper95,lp.beta_pct+1.959963984540054*lp.se,atol=1e-7,rtol=1e-7)
    checks['interaction_BH_80_recomputed']=len(inter)==80 and np.allclose(inter.qvalue_bh,multipletests(inter.pvalue,method='fdr_bh')[1],atol=1e-8,rtol=1e-7)
    checks['event_BH_12_recomputed']=len(events)==12 and np.allclose(events.qvalue_bh,multipletests(events.pvalue,method='fdr_bh')[1],atol=1e-12,rtol=1e-9)
    # Verify all LP and interaction effective outcome counts without re-fitting.
    sample_checks=[]; rolling_checks=[]
    for asset in ['btc','eth']:
        panel=data(asset+'_econometric_sessions.csv')
        cols=['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps','crypto_return_pct']
        for regime,g in [('full',panel),('pre2020',panel.loc[:'2019-12-31']),('post2020',panel.loc['2020-01-01':])]:
            x=g[cols[:4]].copy()
            for k in range(1,6):
                for c in cols: x[f'L{k}_{c}']=g[c].shift(k)
            for h in [0,1,2,5,10,20,30]:
                yy=sum(g.crypto_return_pct.shift(-j) for j in range(h+1))
                expected=len(x.assign(outcome=yy).dropna())
                rows=lp[(lp.asset==asset)&(lp.regime==regime)&(lp.horizon_sessions==h)]
                sample_checks.append(len(rows)==4 and rows.nobs.eq(expected).all())
        rolling=pd.read_csv(TABLES/'rolling_sensitivity.csv')
        xx=panel[cols[:4]].copy()
        for k in range(1,6):
            for c in cols: xx[f'L{k}_{c}']=panel[c].shift(k)
        xx=xx.assign(outcome=panel.crypto_return_pct).dropna()
        ends=[xx.index[end-1].strftime('%Y-%m-%d') for end in range(252,len(xx)+1,21)]
        for c in cols[:4]:
            rows=rolling[(rolling.asset==asset)&(rolling.shock==c)]
            rolling_checks.append(rows.date_utc.tolist()==ends and np.isfinite(rows[['beta_pct','se']]).all().all() and rows.se.gt(0).all())
    checks['all_LP_horizons_and_nobs_reconcile']=all(sample_checks)
    checks['all_rolling_252_step21_window_dates_reconcile']=all(rolling_checks)
    checks['six_baseline_event_coefficients_retained']=len(payload['baseline_events'])==6 and {r['asset'] for r in payload['baseline_events']}=={'BTC','ETH'}
    checks['primary_order_and_VAR_supplementary']=payload['protocol']['primary'][0].startswith('LP/HAC') and 'VAR exploratory IRF/diagnostics' in payload['protocol']['supplementary'] and 'id="method"' not in html
    checks['all_rendered_figures_exist']=all((OUT/name).stat().st_size>10000 for name in ['figures/rolling_vix.png','figures/fomc_windows.png'])
    link_checks=[]
    for name in ['report.html','dashboard.html']:
        source=(OUT/name).read_text(encoding='utf-8')
        for link in re.findall(r'(?:href|src)="([^"]+)"',source):
            if link.startswith(('http','#','data:')): continue
            link_checks.append((OUT/unquote(link.split('#')[0])).exists())
    checks['all_local_HTML_links_and_images_exist']=all(link_checks)
    checks['dashboard_is_offline_self_contained']='fetch(' not in html and '<script src=' not in html and '__PAYLOAD__' not in html
    checks['current_result_counts_consistent']=int(((lp.regime=='full')&(lp.qvalue_bh<.05)).sum())==15 and int((inter.qvalue_bh<.05).sum())==0 and int((events.qvalue_bh<.05).sum())==2
    checks['no_new_model_fitting_declared']=audit['no_new_model_fits'] and audit['no_new_statistical_tests']
    result=dict(checks={k:bool(v) for k,v in checks.items()},n_checks=len(checks),passed=int(sum(checks.values())),
                note='Consistency checks for frozen results, sample definitions and presentation; not a new test of model adequacy.')
    (OUT/'independent_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
    assert all(checks.values()),checks

if __name__=='__main__': main()
