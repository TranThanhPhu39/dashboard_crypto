"""Source-to-product and preservation checks, without fitting or early scoring."""
from src.evaluation.release_preservation import ROOT,OUT,sha,save_json,validate as validate_preservation
from research_common import pd,np,json
import re

def validate():
    validate_preservation();checks={}
    lock=json.loads((OUT/'scientific_input_lock.json').read_text(encoding='utf-8'))
    checks['all_scientific_inputs_unchanged']=all(sha(ROOT/n)==h for n,h in lock['files'].items())
    p=json.loads((OUT/'dashboard_payload.json').read_text(encoding='utf-8'));latest=p['latest'];base=p['base']
    text=(ROOT/'dashboard/index.html').read_text(encoding='utf-8')
    # JSON is generated once for UI and report; compare every displayed latest
    # row with its frozen CSV independently of aggregation/rendering code.
    sources={
        'ablation':('pit_nested_20261020','ablation_tests.csv'),
        'benchmarks':('pit_nested_20261020','benchmark_tests.csv'),
        'sensitivity':('pit_nested_20261020','sensitivity_tests.csv'),
        'metrics':('pit_nested_20261020','forecast_metrics.csv'),
        'samples':('pit_nested_20261020','sample_summary.csv'),
        'fomc':('evidence_20261019','full_rotation_ranges.csv'),
        'regimes':('evidence_20261019','regime_interaction_tests.csv'),
        'rvAblation':('evidence_20261019','rv_ablation_tests.csv'),
        'rvBenchmarks':('evidence_20261019','rv_benchmark_tests.csv'),
        'pit':('pit_nested_20261020','feature_evidence.csv')}
    rowchecks=[]
    for key,(version,name) in sources.items():
        f=pd.read_csv(ROOT/'outputs/research'/version/name,float_precision='round_trip').replace([np.inf,-np.inf],np.nan)
        q=pd.DataFrame(latest[key]);ok=list(f.columns)==list(q.columns) and len(f)==len(q)
        for c in f:
            if pd.api.types.is_numeric_dtype(f[c]) and not pd.api.types.is_bool_dtype(f[c]):
                ok &= bool(np.allclose(f[c].to_numpy(dtype=float),pd.to_numeric(q[c],errors='coerce').to_numpy(dtype=float),rtol=2e-12,atol=2e-14,equal_nan=True))
            else:ok &= f[c].fillna('__MISSING__').astype(str).tolist()==q[c].fillna('__MISSING__').astype(str).tolist()
        rowchecks.append(dict(key=key,rows=len(f),passed=bool(ok)))
    checks['every_latest_display_row_matches_frozen_csv']=all(r['passed'] for r in rowchecks)
    # Legacy charts retain the same source numbers rather than transformed IRFs.
    for key,name in [('daily','calendar_LP.csv'),('monetary','monetary_LP.csv'),('var_irf','joint_VAR_IRF.csv'),('quantile','quantile_effects.csv')]:
        f=pd.read_csv(ROOT/'outputs/research/blueprint_20261019'/name,float_precision='round_trip');q=pd.DataFrame(base[key])
        cols=[c for c in ['beta_pct','response_pct','lower95','upper95','nobs'] if c in f]
        checks[key+'_legacy_estimates_unchanged']=len(q)==len(f) and bool(np.allclose(f[cols].to_numpy(),q[cols].to_numpy(),rtol=2e-12,atol=2e-14,equal_nan=True))
    summary=pd.DataFrame(latest['pooled'])
    # groupby ordering can vary; validate by key rather than only list position.
    expected={'native_asof_d3':3,'matched_asof_d3':0,'matched_latest_d3':0,'matched_asof_d4':0}
    checks['pooled_summary_matches_declared_results']=all(int(summary.set_index('scenario').loc[k,'macro_better_BH'])==v for k,v in expected.items()) and bool(summary.learned_better_BH.eq(0).all())
    from src.release_product import live_status
    checks['live_counts_match_committed_files']=latest['live']==live_status()
    checks['no_early_performance_claim']=(latest['live']['performance_claim'] is False
        and (pd.Timestamp.now(tz='UTC')>=pd.Timestamp(latest['live']['fixed_end'])+pd.Timedelta(days=1)
             or latest['live']['performance']=='PENDING_FIXED_EVALUATION_WINDOW'))
    followup=json.loads((OUT/'oos_followup.json').read_text(encoding='utf-8'))
    checks['oos_followup_uses_current_ledger_and_unchanged_inputs']=(followup['prospective']['live']==live_status()
        and all(sha(ROOT/n)==h for n,h in followup['input_hashes'].items())
        and sha(ROOT/followup['methodology']['review'])==followup['methodology']['review_sha256'])
    checks['submission_milestone_does_not_change_evaluation_protocol']=(followup['evaluation']['end_exclusive_utc']==latest['live']['fixed_end']
        and followup['evaluation']['changed'] is False and followup['evaluation']['early_scoring'] is False
        and followup['evaluation']['new_pilot_activated'] is False and followup['historical']['new_fits']==0
        and followup['performance_claim'] is False and followup['estimates_changed'] is False)
    capture=followup['prospective']['latest_capture']
    capture_manifest=json.loads((ROOT/capture['manifest']).read_text(encoding='utf-8'))
    pointer=json.loads((ROOT/'outputs/research/evidence_20261019/prospective/latest_capture.json').read_text(encoding='utf-8'))
    checks['oos_capture_summary_matches_archived_receipts']=(sha(ROOT/capture['manifest'])==capture['sha256']==pointer['sha256']
        and capture['manifest']==pointer['manifest'] and capture['capture_started_utc']==capture_manifest['capture_started_utc']
        and capture['sources_ok']==sum(row['status']=='ok' for row in capture_manifest['sources'])
        and capture['sources_total']==len(capture_manifest['sources']))
    plan=followup['operations_plan']; calendar=pd.read_csv(OUT/'next_operations.csv')
    audited=pd.read_csv(ROOT/plan['source']).set_index('origin_utc')
    planning_ok=(sha(ROOT/plan['source'])==plan['source_sha256'] and len(calendar)==plan['rows']
                 and plan['forecasts_created']==0 and plan['scheduler_installed']==latest['live']['scheduler_installed'])
    for row in calendar.to_dict('records'):
        reference=audited.loc[row['origin_utc']];origin=pd.Timestamp(row['origin_utc'])
        planning_ok &= (origin>pd.Timestamp(followup['generated_utc'])
                        and pd.Timestamp(row['information_day'])==origin.tz_localize(None)-pd.Timedelta(days=3)
                        and pd.Timestamp(row['market_observation_day'])==origin.tz_localize(None)-pd.Timedelta(days=4)
                        and pd.Timestamp(row['assumed_label_available_local'])==origin+pd.Timedelta(days=2))
        for key in ['origin', 'capture_window_start', 'receipt_cutoff', 'earliest_logging', 'latest_logging_exclusive']:
            planning_ok &= (pd.Timestamp(row[key+'_utc'])==pd.Timestamp(row[key+'_local'])
                            and pd.Timestamp(row[key+'_local']).utcoffset().total_seconds()==7*3600)
            if key!='origin':planning_ok &= row[key+'_utc']==reference[key+'_utc']
        planning_ok &= bool(row['market_day_is_weekend'])==bool(reference['market_day_is_weekend'])
    candidate=plan['next_conditional_origin']
    if candidate:
        planning_ok &= (not candidate['market_day_is_weekend'] and candidate['planning_status']=='conditional_candidate'
                        and pd.Timestamp(candidate['receipt_cutoff_utc'])>=pd.Timestamp(followup['generated_utc'])
                        and candidate['origin_utc'] in calendar.origin_utc.tolist())
    checks['next_operations_are_advisory_and_match_audited_clock_rules']=bool(planning_ok)
    from src.automation_runtime import automation_summary
    checks['scheduler_display_matches_last_verified_windows_tasks']=latest['live']['automation']==automation_summary()
    checks['canonical_modules_and_provenance_present']=all(x in text for x in ['id="responses"','id="forecast"','id="fScenario"','id="fomc"','id="pitTable"','const LATEST=','EX POST ORACLE'])
    links=[]
    for path in [ROOT/'dashboard/index.html',OUT/'report.html',OUT/'oos_followup.html']:
        content=path.read_text(encoding='utf-8')
        for url in re.findall(r'(?:href|src)="([^\"]+)"',content):
            if url.startswith(('http:','https:','data:','#')):continue
            links.append((path,url));assert (path.parent/url).exists(),(path,url)
    checks['all_local_report_dashboard_links_exist']=True
    checks['frozen_old_reports_preserved']=True # Full digests verified by validate_preservation above.
    assert all(checks.values()),checks
    save_json(OUT/'product_validation.json',dict(checked_utc=pd.Timestamp.now(tz='UTC').isoformat(),checks={k:bool(v) for k,v in checks.items()},
        passed=len(checks),total=len(checks),row_checks=rowchecks,local_links_verified=len(links),models_refit=0,performance_claim=False))
    print('Release checks:',len(checks),'frozen displayed rows:',sum(r['rows'] for r in rowchecks),'links:',len(links),flush=True)
    return checks
