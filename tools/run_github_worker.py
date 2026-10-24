"""Linux Actions adapter around the frozen research engine, without refitting."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.github_worker_store import (GitHub, REPOSITORY, atomic, encoded, file_sha,
                                       persist, restore, state_key)


def command(*args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True,
                   env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'})


def prepare_host():
    """Frozen source calls curl.exe. Resolve that name to Linux's actual curl."""
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('This adapter runs only in the authorized repository on GitHub Actions')
    curl = shutil.which('curl.exe') or shutil.which('curl')
    if not curl:
        raise RuntimeError('curl unavailable')
    if os.name == 'posix':
        shim = ROOT / '.worker-bin'
        shim.mkdir(exist_ok=True)
        link = shim / 'curl.exe'
        if not link.exists():
            link.symlink_to(curl)
        os.environ['PATH'] = str(shim) + os.pathsep + os.environ['PATH']
    from src.automation_runtime import OUT, atomic_json, now_utc
    old = json.loads((OUT/'installation.json').read_text(encoding='utf-8-sig'))
    installed = old.get('github_installed_at_utc') or now_utc().isoformat()
    atomic_json(OUT/'installation.json', dict(registered=True, provider='github-actions',
        installed_at_utc=installed, github_installed_at_utc=installed, python_executable=sys.executable,
        desktop_notifications=False, password_stored=False, repository=REPOSITORY,
        workflow='worker.yml', run_id=os.environ['GITHUB_RUN_ID']))


def model_smoke():
    """Compare every frozen deployment model to its own archived predictions."""
    from src.evaluation.release_preservation import install
    install()
    from src.evaluation.prospective_operations import initialize
    initialize()
    from src.evaluation import latency_live as legacy
    from src.models.latency import features, model_predict
    from research_common import pd, np
    import joblib
    from threadpoolctl import threadpool_limits
    inventory, _ = legacy.frozen()
    reference = pd.read_csv(ROOT/'outputs/research/latency_20261019/test_predictions.csv', float_precision='round_trip')
    count = 0
    with threadpool_limits(limits=2):
        for row in inventory.itertuples(index=False):
            q = reference[(reference.asset == row.asset) & (reference.variant == row.variant) &
                          (reference.target == row.target) & (reference.model == row.model)]
            sample = q.iloc[-1]
            # The frozen model's own feature panel is used solely for migration
            # equivalence, never for selecting/tuning or a new performance score.
            panel = pd.read_csv(ROOT/'data/processed/latency_20261019'/f'{row.asset}_{row.variant}.csv', float_precision='round_trip')
            selected = panel[panel.date_utc == sample.date_utc]
            if len(selected) != 1:
                raise ValueError('Historical equivalence row not found')
            values = selected[features(row.asset, row.variant)]
            model = joblib.load(ROOT/row.file)
            if model['features'] != features(row.asset, row.variant):
                raise ValueError('Frozen model feature schema mismatch')
            actual = float(model_predict(model['fitted'], values, row.model, row.target)[0])
            if not np.isclose(actual, sample.predicted, rtol=1e-9, atol=1e-11):
                raise ValueError('Cross-platform model prediction mismatch')
            count += 1
    return count


def preflight():
    from src.evaluation.release_preservation import install
    install()
    from src.evaluation import prospective_operations as op
    from src import automation_runtime as auto
    models = model_smoke()
    # A separate namespace tests the SAME collector without changing the
    # official receipt ledger or creating a forecast during the handoff test.
    test_root = ROOT/'.worker-work/preflight'
    with op.bound():
        old_raw, old_out = op.snapshots.RAW, op.snapshots.OUT
        try:
            op.snapshots.RAW = test_root/'raw'
            op.snapshots.OUT = test_root/'out'
            op.snapshots.OUT.mkdir(parents=True, exist_ok=True)
            manifest = op.snapshots.collect()
        finally:
            op.snapshots.RAW, op.snapshots.OUT = old_raw, old_out
    capture = json.loads(manifest.read_text(encoding='utf-8'))
    sources = capture['sources']
    comparisons=[]
    if os.environ.get('TOPIC09_FRED_TRANSPORT') == 'official-api' and all(r['status']=='ok' for r in sources):
        from src.data.github_fred_api import compare_archived
        with op.bound():
            history=op.legacy.records()
        comparisons=compare_archived(sources,history,ROOT)
    result = dict(checked_at_utc=auto.now_utc().isoformat(), mode='preflight',
                  frozen_models_verified=models, sources_ok=sum(r['status']=='ok' for r in sources),
                  sources_total=len(sources), forecasts_created=0, models_refit=0,
                  api_website_comparisons=comparisons,
                  failures=[{'source': r.get('series_id') or Path(r.get('file','unknown')).name,
                             'error': r.get('error')} for r in sources if r['status']!='ok'])
    print(json.dumps(result), flush=True)
    atomic(ROOT/'.worker-work/preflight_result.json', encoded(result))
    if result['sources_ok'] != result['sources_total'] or result['sources_total'] != 17:
        raise RuntimeError('Live source preflight incomplete; keep the Windows worker running')
    command('run_release.py', 'build')
    command('run_release.py', 'validate')


def redact(value):
    text = str(value)
    for name in ('FRED_API_KEY', 'GH_TOKEN', 'TOPIC09_STATE_KEY'):
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, '[redacted]')
    return re.sub(r'(?i)(api_key=)[^&\s\"\']+', r'\1[redacted]', text)


def monitor_with_recovery(auto):
    """Recover an overdue successful pipeline before judging hosted health."""
    auto.refresh_scheduler_status()
    health = auto.monitor(refresh=False)
    state = auto.read_json(auto.OUT/'state.json', {})
    keys = {row['key'] for row in health.get('issues', [])}
    # A late schedule can leave a previously healthy pipeline overdue. Other
    # faults retain their existing failure path; never clear a running worker.
    recover = (state.get('status') == 'succeeded' and 'missed_runs' in keys and
               all(key == 'missed_runs' or key.startswith(('receipt_risk_', 'receipt_missed_'))
                   for key in keys))
    if not recover:
        return 0, None
    record = dict(started_at_utc=auto.now_utc().isoformat(),
        run_id=os.environ.get('GITHUB_RUN_ID'), trigger='missed_runs',
        previous_last_success_utc=state.get('last_success_utc'),
        previous_health_issues=sorted(keys), status='running',
        scope='Current-time pipeline recovery; original receipt cutoffs and frozen models apply.')
    path = auto.OUT/'monitor_recovery.json'
    auto.atomic_json(path, record)
    print('::notice title=Topic09 schedule recovery::Pipeline heartbeat is overdue; '
          'running the normal locked pipeline before rechecking health.', flush=True)
    result = auto.run_pipeline()
    health = auto.monitor(refresh=False)
    after = auto.read_json(auto.OUT/'state.json', {})
    record.update(finished_at_utc=auto.now_utc().isoformat(), exit_code=result,
        status=after.get('status'), last_success_utc=after.get('last_success_utc'),
        remaining_health_issues=[row['key'] for row in health.get('issues', [])])
    auto.atomic_json(path, record)
    print(json.dumps({'schedule_recovery': record}), flush=True)
    return result, record


def report_operation(mode, exit_code=0, root=ROOT, recovery=None):
    """Make the actual source/health cause visible, including subprocess failures."""
    from src.automation_runtime import read_json, atomic_json, now_utc
    from src.source_health import capture_status, assess
    root = Path(root)
    folder = root/'outputs/automation_20261020'
    state = read_json(folder/'state.json', {})
    health = read_json(folder/'health.json', {})
    capture = capture_status(root)
    outcome = assess(state, health, capture, exit_code)
    ledger = root/'data/prospective/evidence_20261019'
    forecasts = list((ledger/'predictions').glob('*.json'))
    record = dict(checked_at_utc=now_utc().isoformat(), mode=mode, **outcome,
        pipeline_status=state.get('status'), last_success_utc=state.get('last_success_utc'),
        capture=capture, prediction_files=len(forecasts),
        prediction_rows=sum(len(read_json(p)['predictions']) for p in forecasts),
        label_files=len(list((ledger/'labels').glob('*.json'))),
        error=redact(state.get('error', '')), performance_evaluated=False,
        schedule_recovery=recovery)
    atomic_json(folder/'operation_status.json', record)
    print(json.dumps(record, ensure_ascii=False), flush=True)
    if record['status'] != 'succeeded':
        level = 'error' if record['status'] == 'failed' else 'warning'
        message = (f"{mode}: {record['status']}; sources {capture['sources_ok']}/{capture['sources_total']}; "
                   f"blocking={','.join(record['blocking_issues']) or 'none'}; "
                   f"{record['error'] or 'see archived source receipts and health issues'}")
        message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::{level} title=Topic09 operational status::{message}', flush=True)
        name = state.get('log')
        log = (root/name).resolve() if name else None
        if log and log.is_relative_to(root.resolve()) and log.is_file():
            lines = log.read_text(encoding='utf-8', errors='replace').splitlines()[-150:]
            selected = [line for line in lines if any(word in line.lower()
                        for word in ('traceback', 'error', 'failed', 'assertion', 'exception'))]
            for line in selected[-25:]:
                print('pipeline log: '+redact(line)[:600], flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(f"\n### Topic09 {mode}: {record['status']}\n\n"
                f"Pipeline state: `{record['pipeline_status']}`. "
                f"Latest archived capture: **{capture['sources_ok']}/{capture['sources_total']}** sources. "
                f"Committed forecasts: {record['prediction_files']} files / {record['prediction_rows']} rows. "
                f"Labels: {record['label_files']}. No performance scoring.\n\n")
            for row in capture['failures']:
                stream.write(f"- {row['source']}: `{row['code']}`, HTTP {row['http_status']}, {row['raw_bytes']} archived bytes.\n")
            if recovery:
                stream.write(f"\nSchedule recovery: prior success `{recovery['previous_last_success_utc']}`; "
                    f"normal pipeline exit `{recovery['exit_code']}`; "
                    f"remaining health issues: `{','.join(recovery['remaining_health_issues']) or 'none'}`.\n")
            if record['error']:
                stream.write('\n'+record['error']+'\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['restore', 'preflight', 'run', 'monitor', 'persist', 'heartbeat'])
    args = parser.parse_args()
    config = json.loads((ROOT/'config/github_worker.json').read_text())
    api = GitHub()
    if args.stage == 'restore':
        restore(api, state_key(), config)
        return
    if args.stage == 'persist':
        from src.evaluation.release_preservation import install, validate
        from src.automation_runtime import check_immutable, read_json, CONFIG
        install()
        validate()
        check_immutable(read_json(CONFIG))
        context = json.loads((ROOT/'.worker-work/context.json').read_text())
        persist(api, state_key(), config, context)
        return
    if args.stage == 'heartbeat':
        import base64
        from tools.github_worker_store import utc
        from src.automation_runtime import timestamp
        persisted = json.loads((ROOT/'.worker-work/persisted.json').read_text())
        now = datetime.now(timezone.utc)
        stop = timestamp(json.loads((ROOT/'config/automation_20261020.json').read_text())['stop_after_utc'])
        if now >= stop:
            api.json('/actions/workflows/worker.yml/disable', 'PUT')
            print('Stopped the hosted schedule at the original stop_after timestamp.', flush=True)
            return
        path = '/contents/operations/worker-heartbeat.json'
        previous = api.json(path, params={'ref': 'main'})
        if previous:
            record = json.loads(base64.b64decode(previous['content']))
            if now - timestamp(record['checked_at_utc']) < timedelta(days=28):
                return
        record = {'checked_at_utc': utc(), 'run_id': os.environ['GITHUB_RUN_ID'],
                  'state_generation': persisted['generation'], 'scope': 'Operational heartbeat; no scientific changes'}
        payload = {'message': 'Record scheduled worker heartbeat', 'branch': 'main',
                   'content': base64.b64encode(encoded(record)).decode()}
        if previous:
            payload['sha'] = previous['sha']
        api.json(path, 'PUT', json=payload)
        print('Recorded monthly operational heartbeat on main.', flush=True)
        return
    prepare_host()
    if args.stage == 'preflight':
        if os.environ.get('TOPIC09_FRED_TRANSPORT') == 'official-api':
            from src.data.github_fred_api import install as install_api_transport
            install_api_transport()
        preflight()
        return
    from src import automation_runtime as auto
    if args.stage == 'run':
        result = auto.run_pipeline()
        report = report_operation(args.stage, result)
        if result or auto.read_json(auto.OUT/'state.json')['status'] != 'finished_schedule':
            raise SystemExit(result or int(report['status'] == 'failed'))
    result, recovery = monitor_with_recovery(auto)
    command('run_release.py', 'build')
    command('run_release.py', 'validate')
    report = report_operation(args.stage, result, recovery=recovery)
    if report['status'] == 'failed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
