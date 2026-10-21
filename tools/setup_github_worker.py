"""Owner-side bootstrap/handoff administration; credentials never leave memory."""
import argparse
import base64
from contextlib import ExitStack
import ctypes
import ctypes.wintypes
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'.verification/worker-deps'))
from tools.github_worker_store import (GitHub, REPOSITORY, FORMAT, atomic, encoded, inventory,
    persist, read_descriptor, upload_blob, make_pack, upload_archive, utc)


def credential():
    result = subprocess.run(['git', '-c', 'credential.interactive=false', 'credential', 'fill'],
        input='protocol=https\nhost=github.com\npath=' + REPOSITORY + '.git\n\n',
        text=True, capture_output=True, timeout=30, check=True,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'never'})
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)['password']


class Blob(ctypes.Structure):
    _fields_ = [('size', ctypes.wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_char))]


def dpapi(data, protect):
    """Backup the key under the current Windows user's DPAPI identity."""
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    target = Blob()
    function = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if not function(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(target.data)


def local_key():
    path = ROOT/'.verification/actions-worker/state-key.dpapi'
    if path.exists():
        return dpapi(path.read_bytes(), False)
    key = os.urandom(32)
    atomic(path, dpapi(key, True))
    return key


def variable(api, value):
    name = 'TOPIC09_WORKER_ENABLED'
    exists = api.json('/actions/variables/' + name)
    if exists is None:
        api.json('/actions/variables', 'POST', json={'name': name, 'value': value})
    else:
        api.json('/actions/variables/' + name, 'PATCH', json={'name': name, 'value': value})


def create_bootstrap(api, key):
    from src.automation_runtime import process_lock, OUT
    # Wait by retrying this command if an actual worker owns a lock. Never kill
    # an active collector or capture a half-written forecast.
    with ExitStack() as stack:
        for name in ('worker.lock', 'monitor.lock', 'operate.lock'):
            stack.enter_context(process_lock(OUT/name))
        files = inventory(ROOT)
        package = make_pack(files, ROOT, ROOT/'.worker-work')
    pack = upload_archive(api, key, package, 'worker-bootstrap-v1')
    descriptor = {'format': FORMAT, 'created_at_utc': utc(), 'files': files, 'pack': pack}
    asset = upload_blob(api, key, encoded(descriptor), 'worker-bootstrap-v1', 'bootstrap-catalog')
    config = {'version': 1, 'repository': REPOSITORY, 'bootstrap': asset,
              'storage_branch': 'worker-state', 'pipeline_cron': '15 * * * *', 'monitor_cron': '45 * * * *'}
    atomic(ROOT/'config/github_worker.json', json.dumps(config, indent=2).encode())
    catalog = {'format': FORMAT, 'generation': 0, 'bootstrap_sha256': asset['sha256'],
               'files': {}, 'packs': {}, 'created_at_utc': utc(), 'parent_catalog_sha256': None}
    catalog_asset = upload_blob(api, key, encoded(catalog), 'worker-bootstrap-v1', 'state-catalog-0')
    pointer = {'format': FORMAT, 'generation': 0, 'bootstrap_sha256': asset['sha256'],
               'catalog': catalog_asset, 'owner': 'windows-preflight', 'committed_at_utc': utc()}
    commit = api.commit_pointer(pointer, None)
    print(json.dumps({'bootstrap_files': len(files), 'plaintext_bytes': pack['bytes'],
                      'encrypted_parts': len(pack['parts']), 'state_commit': commit}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['initialize', 'handoff-state', 'enable', 'disable', 'preflight', 'run', 'monitor', 'probe', 'status', 'actions'])
    parser.add_argument('--runner', choices=['ubuntu-24.04', 'windows-2025', 'macos-15'])
    parser.add_argument('--api-only', action='store_true')
    args = parser.parse_args()
    api = GitHub(credential())
    if args.stage == 'initialize':
        if (ROOT/'config/github_worker.json').exists() or api.pointer()[0] is not None:
            raise ValueError('Bootstrap already configured; refusing to replace it or pause the existing worker')
        variable(api, 'false')
        key = local_key()
        from nacl.public import PublicKey, SealedBox
        public = api.json('/actions/secrets/public-key')
        secret = SealedBox(PublicKey(base64.b64decode(public['key']))).encrypt(base64.b64encode(key))
        api.json('/actions/secrets/TOPIC09_STATE_KEY', 'PUT', json={
            'key_id': public['key_id'], 'encrypted_value': base64.b64encode(secret).decode()})
        create_bootstrap(api, key)
    elif args.stage == 'handoff-state':
        key = local_key()
        config = json.loads((ROOT/'config/github_worker.json').read_text())
        pointer, blob = api.pointer()
        if pointer['owner'] != 'windows-preflight':
            raise ValueError('GitHub already owns the ledger; do not import a divergent local copy')
        base = read_descriptor(api, key, config['bootstrap'])
        catalog = read_descriptor(api, key, pointer['catalog'])
        from src.automation_runtime import process_lock, OUT
        with ExitStack() as stack:
            for name in ('worker.lock', 'monitor.lock', 'operate.lock'):
                stack.enter_context(process_lock(OUT/name))
            persist(api, key, config, {'pointer': pointer, 'pointer_blob': blob,
                'baseline': base['files'], 'catalog': catalog}, ROOT, owner='github-actions-handoff')
    elif args.stage in ('enable', 'disable'):
        variable(api, 'true' if args.stage=='enable' else 'false')
        print('Worker enabled' if args.stage=='enable' else 'Worker paused on GitHub')
    elif args.stage == 'probe':
        api.json('/actions/workflows/network-probe.yml/dispatches', 'POST', json={'ref': 'main',
            'inputs': {'api_only': str(args.api_only).lower()}})
        print('Dispatched network probe')
    elif args.stage in ('preflight', 'run', 'monitor'):
        inputs = {'mode': args.stage}
        if args.runner:
            inputs['runner'] = args.runner
        api.json('/actions/workflows/worker.yml/dispatches', 'POST', json={'ref': 'main', 'inputs': inputs})
        print('Dispatched ' + args.stage)
    elif args.stage == 'actions':
        for name, tag in [('cache', 'v5'), ('cache', 'v4')]:
            result = api.json('https://api.github.com/repos/actions/'+name+'/git/ref/tags/'+tag)
            print(json.dumps({'action': name, 'tag': tag, 'object': result.get('object') if result else None}))
    else:
        pointer, _ = api.pointer()
        print(json.dumps({'pointer': pointer, 'enabled': api.json('/actions/variables/TOPIC09_WORKER_ENABLED')}))
        runs = api.json('/actions/workflows/worker.yml/runs', params={'per_page': 5})
        print(json.dumps({'runs': [{k: row.get(k) for k in ('id', 'status', 'conclusion', 'html_url', 'head_sha', 'event')}
                                   for row in (runs or {}).get('workflow_runs', [])]}))


if __name__ == '__main__':
    main()
