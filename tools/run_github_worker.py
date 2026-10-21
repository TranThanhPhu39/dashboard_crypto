"""Linux Actions adapter around the frozen research engine, without refitting."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
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
        if result or auto.read_json(auto.OUT/'state.json')['status'] != 'finished_schedule':
            raise SystemExit(result)
    auto.refresh_scheduler_status()
    health = auto.monitor(refresh=False)
    command('run_release.py', 'build')
    command('run_release.py', 'validate')
    if health['status'] != 'healthy':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
