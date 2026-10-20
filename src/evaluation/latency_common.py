"""Paths and frozen provenance for the separately approved latency extension."""
from research_common import *
from src.utils.project import sha, save_json
import datetime

VERSION='latency_20261019'
OUT=RESULTS/VERSION
PANELS=ROOT/'data/processed'/VERSION
MODELS=ROOT/'models'/VERSION
RAW=ROOT/'data/raw'/VERSION
LIVE=ROOT/'data/prospective'/VERSION
CONFIG=ROOT/'config'/f'{VERSION}.json'

def csv(frame,name):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    frame.to_csv(path,index=False,encoding='utf-8-sig',float_format='%.17g')

def init():
    for path in [OUT,OUT/'figures',PANELS,MODELS,RAW,LIVE]:path.mkdir(parents=True,exist_ok=True)
    path=OUT/'source_snapshot.json'
    if path.exists():
        obj=json.loads(path.read_text(encoding='utf-8'));assert sha(CONFIG)==obj['config_sha256'];return obj
    files=list((ROOT/'data').rglob('*'))+list(RESULTS.rglob('*'))+list((ROOT/'models').rglob('*'))
    files+=list(ROOT.glob('topic09*.zip'))+list((ROOT/'config').glob('*.json'))+list((ROOT/'dashboard').glob('*.html'))
    excluded=[OUT,PANELS,MODELS,RAW,LIVE]
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file() and not any(d in p.parents for d in excluded) and p!=CONFIG}
    obj=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),config_sha256=sha(CONFIG),protected_sha256=protected)
    save_json(path,obj);return obj

def check_protected():
    obj=init();bad=[p for p,h in obj['protected_sha256'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not bad,bad[:10];return len(obj['protected_sha256'])

def config():return json.loads(CONFIG.read_text(encoding='utf-8'))
