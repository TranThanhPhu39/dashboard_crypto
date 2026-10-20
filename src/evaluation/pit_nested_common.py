"""Isolated, preregistered historical PIT and nested-backtest extension."""
from research_common import ROOT, np, pd, json
from src.utils.project import sha, save_json

VERSION = 'pit_nested_20261020'
OUT = ROOT/'outputs/research'/VERSION
PANELS = ROOT/'data/processed'/VERSION
MODELS = ROOT/'models'/VERSION
CONFIG = ROOT/'config'/f'{VERSION}.json'

def config():
    return json.loads(CONFIG.read_text(encoding='utf-8'))

def csv(frame, name):
    p = OUT/name
    p.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(p, index=False, encoding='utf-8-sig', float_format='%.17g')

def init():
    for p in (OUT, PANELS, MODELS, OUT/'figures', OUT/'folds'):
        p.mkdir(parents=True, exist_ok=True)
    path = OUT/'source_snapshot.json'
    if path.exists():
        s = json.loads(path.read_text(encoding='utf-8'))
        assert s['config_sha256'] == sha(CONFIG), 'Design changed after lock'
        return s
    excluded = [OUT, PANELS, MODELS]
    # Preserve all existing empirical inputs, artifacts and reports; live logs are
    # included too, so a separate live run must not occur during this study.
    paths = []
    for folder in ['data', 'outputs/research', 'models', 'config', 'dashboard']:
        paths.extend((ROOT/folder).rglob('*'))
    paths.extend(ROOT.glob('topic09*.zip'))
    paths.extend((ROOT/'paper').glob('*'))
    protected = {p.relative_to(ROOT).as_posix():sha(p) for p in paths
                 if p.is_file() and p != CONFIG and not any(d in p.parents for d in excluded)}
    s = dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(), config_sha256=sha(CONFIG), protected_sha256=protected)
    save_json(path, s)
    return s

def check_protected():
    s = init()
    bad = [n for n,h in s['protected_sha256'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
    assert not bad, bad[:10]
    return len(s['protected_sha256'])

def read_panel(asset, variant, scenario):
    return pd.read_csv(PANELS/f'{asset}_{variant}_{scenario}.csv',
        parse_dates=['origin_utc','information_date','information_close_utc','assumed_available_utc',
                     'label_close_utc','label_assumed_available_utc'], float_precision='round_trip').set_index('origin_utc')

def fit_cutoff(start):
    return pd.Timestamp(start)-pd.Timedelta(hours=config()['fit_information_buffer_hours'])

def training(frame, start):
    return frame[(frame.index < pd.Timestamp(start)) &
                 (frame.label_assumed_available_utc <= fit_cutoff(start))]

def inner_splits(frame, year):
    """Two predeclared semesters; tuning outcomes must exist by outer cutoff."""
    outer_cut = fit_cutoff(f'{year}-01-01')
    boundaries = [pd.Timestamp(year-1,1,1), pd.Timestamp(year-1,7,1), pd.Timestamp(year,1,1)]
    out = []
    for start,end in zip(boundaries[:-1],boundaries[1:]):
        tr = training(frame,start)
        va = frame[(frame.index>=start)&(frame.index<end)&(frame.label_assumed_available_utc<=outer_cut)]
        assert len(tr)>=config()['min_train'] and len(va)>=config()['min_validation'], (year,start,len(tr),len(va))
        assert tr.label_assumed_available_utc.max()<=fit_cutoff(start)
        assert va.label_assumed_available_utc.max()<=outer_cut
        out.append((start,tr,va))
    return out
