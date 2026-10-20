"""Separate output and provenance for the explicitly authorized diagnostics."""
from research_common import *
from src.utils.project import sha, save_json
import datetime

VERSION = 'robustness_20261019'
OUT = RESULTS / VERSION
BASE = RESULTS / 'blueprint_20261019'
PANELS = ROOT / 'data/processed/blueprint_20261019'
RAW = ROOT / 'data/raw' / VERSION
CONFIG = ROOT / 'config' / (VERSION + '.json')

def write_csv(frame, name):
    frame.to_csv(OUT / name, index=False, encoding='utf-8-sig', float_format='%.17g')

def init():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'figures').mkdir(exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    path = OUT / 'source_snapshot.json'
    if path.exists():
        obj = json.loads(path.read_text(encoding='utf-8'))
        assert obj['config_sha256'] == sha(CONFIG), 'Design changed after locking'
        return obj
    # Hash all frozen baseline outputs, inputs, model artifacts, old ZIPs and configs.
    files = list((ROOT / 'data').rglob('*')) + list(RESULTS.rglob('*'))
    files += list((ROOT / 'models').rglob('*')) + list(ROOT.glob('topic09*.zip'))
    files += list((ROOT / 'config').glob('*.json')) + list((ROOT / 'dashboard').glob('*.html'))
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in files
                 if p.is_file() and OUT not in p.parents and RAW not in p.parents and p != CONFIG}
    obj = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               config_sha256=sha(CONFIG), protected_sha256=protected)
    save_json(path, obj)
    return obj

def check_protected():
    snap = init()
    failures = [p for p, digest in snap['protected_sha256'].items()
                if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert not failures, f'Frozen files changed: {failures[:10]}'
    return len(snap['protected_sha256'])
