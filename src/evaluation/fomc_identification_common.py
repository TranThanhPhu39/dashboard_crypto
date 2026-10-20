"""Separate provenance for the authorized FOMC identification and timing study."""
from research_common import *
from src.utils.project import sha,save_json

VERSION='fomc_identification_20261019'
OUT=RESULTS/VERSION
RAW=ROOT/'data/raw'/VERSION
PANELS=ROOT/'data/processed'/VERSION
CONFIG=ROOT/'config'/f'{VERSION}.json'

def csv(frame,name):
    frame.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.17g')

def config():return json.loads(CONFIG.read_text(encoding='utf-8'))

def init():
    for p in [OUT,OUT/'figures',RAW,PANELS]:p.mkdir(parents=True,exist_ok=True)
    path=OUT/'source_snapshot.json'
    if path.exists():
        obj=json.loads(path.read_text(encoding='utf-8'));assert obj['config_sha256']==sha(CONFIG);return obj
    files=list((ROOT/'data').rglob('*'))+list(RESULTS.rglob('*'))+list((ROOT/'models').rglob('*'))
    files+=list(ROOT.glob('topic09*.zip'))+list((ROOT/'config').glob('*.json'))+list((ROOT/'dashboard').glob('*.html'))
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file() and not any(d in p.parents for d in [OUT,RAW,PANELS]) and p!=CONFIG}
    obj=dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),config_sha256=sha(CONFIG),protected_sha256=protected)
    save_json(path,obj);return obj

def check_protected():
    obj=init();bad=[p for p,h in obj['protected_sha256'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not bad,bad[:10];return len(obj['protected_sha256'])
