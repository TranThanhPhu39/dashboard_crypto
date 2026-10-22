"""Encrypted, durable worker storage in Releases; a Git ref commits the catalog.

Actions caches are optional accelerators. They are never the source of truth.
No credentials, plaintext inputs, or models are uploaded to Pages or Releases.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'TranThanhPhu39/dashboard_crypto'
BRANCH = 'worker-state'
POINTER = 'state.json'
CHUNK = 48 * 1024 * 1024
FORMAT = 'topic09-encrypted-worker-v1'
AAD = (FORMAT + ':' + REPOSITORY).encode()
MAGIC = b'T09AESGCM1\0'
AUTO = 'outputs/automation_20261020/'
RELEASE = 'outputs/research/release_20261025/'
OPS = 'outputs/research/evidence_20261019/prospective_operations/'
LIVE_OUT = 'outputs/research/evidence_20261019/prospective/'
RAW = 'data/raw/evidence_20261019/live/'
LIVE = 'data/prospective/evidence_20261019/'
# This reader is maintained in Git, separately from the frozen source report.
# It is presentation code, not a receipt or an encrypted runtime artifact.
GIT_PRESENTATION_FILES = frozenset({
    'outputs/research/evidence_20261019/report_view.html',
})


def utc():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def runtime_name(name):
    """Reject traversal, host files, source code, links, and executable payloads."""
    parts = PurePosixPath(name).parts
    if not name or str(PurePosixPath(name)) != name or '\\' in name or ':' in name or name.startswith('/') or '..' in parts or '.' in parts:
        return False
    return (name.startswith(('data/', 'models/', 'outputs/')) or
            name in ('dashboard/index.html', 'paper/README.md') or
            bool(re.fullmatch(r'topic09_[A-Za-z0-9_]+\.zip', name)))


def safe_path(root, name):
    if not runtime_name(name):
        raise ValueError('Disallowed runtime path: ' + name)
    root = Path(root).resolve()
    path = root.joinpath(*PurePosixPath(name).parts)
    for component in [path, *path.parents]:
        if component == root:
            break
        if component.is_symlink():
            raise ValueError('Symlink in runtime path')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path outside workspace')
    return path


def mutable(name):
    if name in ('dashboard/index.html', 'paper/README.md',
                'outputs/research/pit_nested_20261020/independent_validation.json'):
        return True
    if name.startswith(AUTO):
        return True
    if name.startswith(RELEASE) and '/originals/' not in name and not name.endswith('scientific_input_lock.json') and not name.endswith('preservation_migration.json'):
        return True
    if name.startswith(LIVE_OUT):
        return True
    return name.startswith(OPS) and name.rsplit('/', 1)[-1] in {
        'last_run.json', 'readiness_calendar.csv', 'historical_feature_coverage.csv',
        'rule_audit.json', 'report.html', 'validation.json', 'browser_validation.json'}


def appendable(name):
    return mutable(name) or name.startswith((RAW, LIVE + 'envelopes/', LIVE + 'attempts/',
                                           LIVE + 'predictions/', LIVE + 'labels/', OPS + 'code_snapshots/'))


def inventory(root=ROOT):
    names = set()
    for folder in ('data', 'models', 'outputs'):
        for path in (root / folder).rglob('*'):
            if path.is_symlink():
                raise ValueError('Symlink in runtime tree')
            if path.is_file() and not path.name.endswith(('.lock', '.tmp')):
                name = path.relative_to(root).as_posix()
                if name not in GIT_PRESENTATION_FILES:
                    names.add(name)
    names.update(p.name for p in root.glob('topic09*.zip'))
    names.update(['dashboard/index.html', 'paper/README.md'])
    return {name: file_sha(safe_path(root, name)) for name in sorted(names)}


def changes(baseline, previous, current):
    """Any loss or edit of an immutable receipt/forecast/model fails closed."""
    expected = {**baseline, **{n: row['sha256'] for n, row in previous.items()}}
    missing = set(expected) - set(current)
    if missing:
        raise ValueError('Runtime files lost: ' + ', '.join(sorted(missing)[:5]))
    changed = {}
    for name, sha in current.items():
        if name in expected and sha != expected[name] and not mutable(name):
            raise ValueError('Immutable runtime file changed: ' + name)
        if name not in expected and not appendable(name):
            raise ValueError('Unexpected new runtime file: ' + name)
        if sha != expected.get(name):
            changed[name] = sha
    return changed


def encrypt(data, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, data, AAD)


def decrypt(data, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not data.startswith(MAGIC):
        raise ValueError('Unsupported encrypted object')
    offset = len(MAGIC)
    return AESGCM(key).decrypt(data[offset:offset+12], data[offset+12:], AAD)


def state_key():
    value = base64.b64decode(os.environ['TOPIC09_STATE_KEY'], validate=True)
    if len(value) != 32:
        raise ValueError('State key must contain 32 bytes')
    return value


class GitHub:
    def __init__(self, token=None):
        import requests
        self.session = requests.Session()
        self.session.headers.update({'Authorization': 'Bearer ' + (token or os.environ['GH_TOKEN']),
            'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10',
            'User-Agent': 'Topic09-Worker'})

    def request(self, path, method='GET', **kwargs):
        url = path if path.startswith('https://') else 'https://api.github.com/repos/' + REPOSITORY + path
        if not url.startswith(('https://api.github.com/', 'https://uploads.github.com/')):
            raise ValueError('Unexpected GitHub API host')
        response = self.session.request(method, url, timeout=(20, 240), **kwargs)
        # requests strips Authorization on cross-host download redirects.
        if response.status_code == 404 and method == 'GET':
            return None
        if not response.ok:
            raise RuntimeError(f'GitHub {method} HTTP {response.status_code}: {response.text[:180]}')
        return response

    def json(self, path, method='GET', **kwargs):
        response = self.request(path, method, **kwargs)
        return None if response is None else response.json() if response.content else {}

    def release(self, tag):
        result = self.json('/releases/tags/' + tag)
        if result is None:
            result = self.json('/releases', 'POST', json={'tag_name': tag, 'target_commitish': 'main',
                'name': 'Encrypted worker storage — ' + tag, 'make_latest': 'false',
                'body': 'AES-256-GCM encrypted runtime objects. No plaintext datasets/models. '
                        'Required by the scheduled worker; do not delete these assets.'})
        return result

    def put_asset(self, tag, name, data):
        release = self.release(tag)
        url = release['upload_url'].split('{')[0]
        response = self.json(url, 'POST', params={'name': name}, data=data,
                             headers={'Content-Type': 'application/octet-stream'})
        return {'id': response['id'], 'name': name, 'tag': tag, 'sha256': digest(data), 'bytes': len(data),
                'url': response['browser_download_url']}

    def get_asset(self, record, cache=None):
        path = Path(cache)/record['sha256'] if cache else None
        if path and path.exists() and file_sha(path) == record['sha256']:
            return path.read_bytes()
        if record.get('url'):
            import requests
            if not record['url'].startswith('https://github.com/' + REPOSITORY + '/releases/download/'):
                raise ValueError('Unexpected encrypted asset host')
            # Public ciphertext downloads need no credential and don't consume
            # the authenticated REST API quota, even as the receipt set grows.
            response = requests.get(record['url'], timeout=(20, 240))
            response.raise_for_status()
        else:
            response = self.request('/releases/assets/' + str(int(record['id'])),
                                    headers={'Accept': 'application/octet-stream'})
        if response is None:
            raise RuntimeError('Durable worker object missing; never start from an empty state')
        data = response.content
        if len(data) != record['bytes'] or digest(data) != record['sha256']:
            raise ValueError('Encrypted asset checksum mismatch')
        if path:
            atomic(path, data)
        return data

    def pointer(self):
        result = self.json('/contents/' + POINTER, params={'ref': BRANCH})
        if result is None:
            return None, None
        return json.loads(base64.b64decode(result['content'])), result['sha']

    def commit_pointer(self, pointer, expected_blob):
        content = encoded(pointer)
        message = 'Persist worker generation ' + str(pointer['generation'])
        if expected_blob is None:
            if self.json('/git/ref/heads/' + BRANCH) is not None:
                raise ValueError('State branch exists without a pointer; manual recovery required')
            tree = self.json('/git/trees', 'POST', json={'tree': [
                {'path': POINTER, 'mode': '100644', 'type': 'blob', 'content': content.decode()}]})
            commit = self.json('/git/commits', 'POST', json={'message': message, 'tree': tree['sha'], 'parents': []})
            self.json('/git/refs', 'POST', json={'ref': 'refs/heads/' + BRANCH, 'sha': commit['sha']})
            return commit['sha']
        result = self.json('/contents/' + POINTER, 'PUT', json={'message': message, 'branch': BRANCH,
            'sha': expected_blob, 'content': base64.b64encode(content).decode()})
        return result['commit']['sha']


def upload_blob(api, key, data, tag, prefix, cache=None):
    ciphertext = encrypt(data, key)
    record = api.put_asset(tag, prefix + '-' + uuid.uuid4().hex + '.enc', ciphertext)
    if cache:
        atomic(Path(cache)/record['sha256'], ciphertext)
    return record


def prune_cache(root, catalog, catalog_asset):
    cache = root/'.worker-cache/state'
    if not cache.exists():
        return
    if cache.is_symlink() or not cache.resolve().is_relative_to(root.resolve()):
        raise ValueError('Invalid cache directory')
    needed = {catalog_asset['sha256']}
    for pack in catalog['packs'].values():
        needed.update(part['sha256'] for part in pack['parts'])
    for path in cache.iterdir():
        if path.is_file() and re.fullmatch(r'[a-f0-9]{64}', path.name) and path.name not in needed:
            path.unlink()


def make_pack(files, root, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    package = folder / ('pack-' + uuid.uuid4().hex + '.zip')
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=4) as archive:
        archive.writestr('_manifest.json', encoded(files))
        for name, sha in files.items():
            source = safe_path(root, name)
            if file_sha(source) != sha:
                raise ValueError('Runtime changed during snapshot: ' + name)
            archive.write(source, name, compress_type=zipfile.ZIP_STORED if source.suffix == '.zip' else None)
    return package


def upload_archive(api, key, package, tag):
    """Network upload does not hold the local collector's filesystem locks."""
    try:
        parts = []
        with package.open('rb') as stream:
            while data := stream.read(CHUNK):
                parts.append(upload_blob(api, key, data, tag, 'pack-part'))
                print(json.dumps({'uploaded_encrypted_part': len(parts), 'bytes': len(data)}), flush=True)
        return {'parts': parts, 'sha256': file_sha(package), 'bytes': package.stat().st_size}
    finally:
        package.unlink(missing_ok=True)


def upload_pack(api, key, files, root, tag, folder):
    return upload_archive(api, key, make_pack(files, root, folder), tag)


def restore_pack(api, key, record, root, wanted, folder, cache=None):
    """Authenticate the complete pack before writing any selected file."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    package = folder / ('restore-' + uuid.uuid4().hex + '.zip')
    try:
        with package.open('wb') as stream:
            for part in record['parts']:
                stream.write(decrypt(api.get_asset(part, cache), key))
        if package.stat().st_size != record['bytes'] or file_sha(package) != record['sha256']:
            raise ValueError('Decrypted pack checksum mismatch')
        with zipfile.ZipFile(package) as archive:
            if len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError('Duplicate archive names')
            declared = json.loads(archive.read('_manifest.json'))
            if set(archive.namelist()) != set(declared) | {'_manifest.json'}:
                raise ValueError('Archive inventory mismatch')
            if not set(wanted).issubset(declared):
                raise ValueError('Required file absent from pack')
            # Validate ALL archive names, including entries not selected today.
            for name in declared:
                safe_path(root, name)
                info = archive.getinfo(name)
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Archive symlink rejected')
            for name, sha in wanted.items():
                if declared[name] != sha:
                    raise ValueError('Catalog disagrees with pack')
                data = archive.read(name)
                if digest(data) != sha:
                    raise ValueError('Decrypted file checksum mismatch')
                atomic(safe_path(root, name), data)
    finally:
        package.unlink(missing_ok=True)


def read_descriptor(api, key, asset, cache=None):
    result = json.loads(decrypt(api.get_asset(asset, cache), key))
    if result['format'] != FORMAT:
        raise ValueError('Unknown catalog format')
    return result


def restore(api, key, config, root=ROOT):
    cache = root / '.worker-cache/bootstrap'
    folder = root / '.worker-work'
    base = read_descriptor(api, key, config['bootstrap'], cache)
    restore_pack(api, key, base['pack'], root, base['files'], folder, cache)
    pointer, blob = api.pointer()
    if pointer is None or pointer['bootstrap_sha256'] != config['bootstrap']['sha256']:
        raise ValueError('Missing or incompatible state pointer; bootstrap is not current state')
    state_cache = root / '.worker-cache/state'
    catalog = read_descriptor(api, key, pointer['catalog'], state_cache)
    if catalog['bootstrap_sha256'] != config['bootstrap']['sha256'] or catalog['generation'] != pointer['generation']:
        raise ValueError('Catalog generation/bootstrap mismatch')
    for pack_id, pack in catalog['packs'].items():
        wanted = {name: row['sha256'] for name, row in catalog['files'].items() if row['pack'] == pack_id}
        if wanted:
            restore_pack(api, key, pack, root, wanted, folder, state_cache)
    expected = {**base['files'], **{n: r['sha256'] for n, r in catalog['files'].items()}}
    for name, sha in expected.items():
        if file_sha(safe_path(root, name)) != sha:
            raise ValueError('Restored runtime differs from committed inventory')
    context = {'pointer': pointer, 'pointer_blob': blob, 'catalog': catalog, 'baseline': base['files']}
    prune_cache(root, catalog, pointer['catalog'])
    atomic(folder / 'context.json', encoded(context))
    print(json.dumps({'restored_files': len(expected), 'generation': pointer['generation'],
                      'catalog_sha256': pointer['catalog']['sha256']}), flush=True)
    return context


def persist(api, key, config, context, root=ROOT, owner='github-actions'):
    pointer = context['pointer']
    catalog = context['catalog']
    current = inventory(root)
    changed = changes(context['baseline'], catalog['files'], current)
    latest, latest_blob = api.pointer()
    if latest_blob != context['pointer_blob']:
        raise ValueError('State changed on another host; refusing to overwrite it')
    generation = pointer['generation'] + 1
    tag = 'worker-state-' + datetime.now(timezone.utc).strftime('%Y%m%d')
    files = dict(catalog['files'])
    packs = dict(catalog['packs'])
    if changed:
        pack = upload_pack(api, key, changed, root, tag, root / '.worker-work')
        packs[pack['sha256']] = pack
        files.update({n: {'sha256': sha, 'pack': pack['sha256']} for n, sha in changed.items()})
    needed = {row['pack'] for row in files.values()}
    new_catalog = {'format': FORMAT, 'generation': generation, 'bootstrap_sha256': config['bootstrap']['sha256'],
        'files': files, 'packs': {k: v for k, v in packs.items() if k in needed},
        'parent_catalog_sha256': pointer['catalog']['sha256'], 'created_at_utc': utc()}
    asset = upload_blob(api, key, encoded(new_catalog), tag, 'catalog-' + str(generation), root/'.worker-cache/state')
    new_pointer = {'format': FORMAT, 'generation': generation, 'bootstrap_sha256': config['bootstrap']['sha256'],
        'catalog': asset, 'previous_catalog_sha256': pointer['catalog']['sha256'], 'committed_at_utc': utc(),
        'owner': owner, 'run_id': os.environ.get('GITHUB_RUN_ID'), 'source_commit': os.environ.get('GITHUB_SHA')}
    commit = api.commit_pointer(new_pointer, context['pointer_blob'])
    prune_cache(root, new_catalog, asset)
    result = {'generation': generation, 'changed_files': len(changed), 'catalog_sha256': asset['sha256'],
              'state_commit': commit, 'owner': owner}
    atomic(root / '.worker-work/persisted.json', encoded(result))
    print(json.dumps(result), flush=True)
    return result
