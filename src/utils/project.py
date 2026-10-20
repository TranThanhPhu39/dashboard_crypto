from research_common import *
import hashlib,datetime

VERSION='blueprint_20261019'
OUT=RESULTS/VERSION
PANELS=ROOT/'data/processed'/VERSION
RAW=ROOT/'data/raw'/VERSION
MODELS=ROOT/'models'/VERSION
CONFIG=ROOT/'config'/f'{VERSION}.json'
SHOCKS={'vix_change':5.,'usd_return_pct':1.,'us2y_change_bps':10.,'us10y_change_bps':10.}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str,allow_nan=False),encoding='utf-8')
def csv(f,name):f.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.17g')
def load(name):return pd.read_csv(OUT/name)
def panel(name):return pd.read_csv(PANELS/name,parse_dates=['date_utc']).set_index('date_utc')
def config():return json.loads(CONFIG.read_text(encoding='utf-8'))
def init():
    for p in [OUT,PANELS,RAW,MODELS,OUT/'figures']:p.mkdir(parents=True,exist_ok=True)
    stamp=OUT/'source_snapshot.json'
    if stamp.exists():
        snap=json.loads(stamp.read_text());assert sha(CONFIG)==snap['config_sha256'];return
    files=list((ROOT/'data').rglob('*'))+list(RESULTS.rglob('*'))+list(ROOT.glob('topic09*.zip'))
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in files if p.is_file() and OUT not in p.parents and PANELS not in p.parents and RAW not in p.parents}
    save_json(stamp,dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),config_sha256=sha(CONFIG),protected_sha256=protected))
