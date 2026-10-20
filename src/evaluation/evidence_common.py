"""Isolated paths, immutable inputs and preservation checks for the evidence extension."""
from research_common import *
from src.utils.project import sha, save_json

VERSION='evidence_20261019'
OUT=RESULTS/VERSION
RAW=ROOT/'data/raw'/VERSION
PANELS=ROOT/'data/processed'/VERSION
MODELS=ROOT/'models'/VERSION
LIVE=ROOT/'data/prospective'/VERSION
CONFIG=ROOT/'config'/f'{VERSION}.json'
OLD=RESULTS/'fomc_identification_20261019'

def config():return json.loads(CONFIG.read_text(encoding='utf-8'))

def csv(frame,name):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    frame.to_csv(p,index=False,encoding='utf-8-sig',float_format='%.17g')

def immutable_json(path,obj):
    if path.exists():assert json.loads(path.read_text(encoding='utf-8'))==obj,str(path)
    else:save_json(path,obj)

def init():
    for p in [OUT,RAW,PANELS,MODELS,LIVE,OUT/'figures']:p.mkdir(parents=True,exist_ok=True)
    path=OUT/'source_snapshot.json'
    if path.exists():
        s=json.loads(path.read_text(encoding='utf-8'));assert s['config_sha256']==sha(CONFIG);return s
    files=[]
    for d in ['data','outputs/research','models','config','dashboard']:
        files.extend((ROOT/d).rglob('*'))
    files.extend(ROOT.glob('topic09*.zip'))
    excluded=[OUT,RAW,PANELS,MODELS,LIVE]
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file() and p!=CONFIG and not any(d in p.parents for d in excluded)}
    s=dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),config_sha256=sha(CONFIG),protected_sha256=protected)
    save_json(path,s);return s

def check_protected():
    s=init();bad=[n for n,h in s['protected_sha256'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
    assert not bad,bad[:10];return len(s['protected_sha256'])

def lock_inputs(name,paths):
    obj=dict(config_sha256=sha(CONFIG),inputs={p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    immutable_json(OUT/name,obj);return obj

def verify_lock(name):
    obj=json.loads((OUT/name).read_text(encoding='utf-8'));assert obj['config_sha256']==sha(CONFIG)
    assert all(sha(ROOT/n)==h for n,h in obj['inputs'].items());return obj
