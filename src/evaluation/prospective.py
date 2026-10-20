"""Append predictions before their target starts; never fabricate a new untouched test."""
from src.utils.project import *
from research_completion import model_predict
import joblib

def validate_clock(origin,cutoff,now):
    assert origin.tzinfo is not None and cutoff.tzinfo is not None and now.tzinfo is not None
    origin=origin.tz_convert('UTC')
    assert origin==origin.normalize() and origin>=pd.Timestamp('2026-10-20',tz='UTC')
    assert now<origin<=now+pd.Timedelta(days=1), 'Log before target starts; origin must be within the next24h.'
    assert cutoff<=origin-pd.Timedelta(hours=24) and cutoff<=now

def predict(envelope_path,asset,variant,target,kind):
    envelope=json.loads(Path(envelope_path).read_text(encoding='utf-8'));origin=pd.Timestamp(envelope['origin_utc'])
    assert origin.tzinfo is not None;origin=origin.tz_convert('UTC');now=pd.Timestamp.now(tz='UTC')
    cutoff=pd.Timestamp(envelope['information_cutoff_utc']);assert cutoff.tzinfo is not None
    validate_clock(origin,cutoff,now)
    assert envelope['source_evidence'], 'Actual input evidence is required; no placeholder forecast.'
    for record in envelope['source_evidence']:
        t=pd.Timestamp(record['available_at_utc']);assert t.tzinfo is not None and t<=cutoff
        p=ROOT/record['local_file'];assert sha(p)==record['sha256']
    inventory=load('model_inventory.csv');name=f'{asset}_{variant}_{target}_{kind}.joblib';path=MODELS/name
    expected=inventory[inventory.file==path.relative_to(ROOT).as_posix()].iloc[0];assert sha(path)==expected.sha256
    frozen=joblib.load(path);assert pd.Timestamp(frozen['last_fit_label_available']).tz_localize('UTC')<=cutoff
    cols=frozen['features'];assert set(envelope['features'])==set(cols)
    x=pd.DataFrame([[envelope['features'][c] for c in cols]],columns=cols);assert np.isfinite(x.to_numpy()).all()
    value=float(model_predict(frozen['fitted'],x,kind,target)[0])
    log=OUT/'prospective_predictions.jsonl';key=f'{origin.isoformat()}|{asset}|{variant}|{target}|{kind}'
    prior=[json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
    assert not any(r['key']==key for r in prior), 'A forecast already exists; do not overwrite it.'
    row=dict(key=key,origin_utc=origin.isoformat(),target_end_utc=(origin+pd.Timedelta(days=1)).isoformat(),logged_at_utc=now.isoformat(),asset=asset,variant=variant,target=target,model=kind,predicted=value,information_cutoff_utc=cutoff.isoformat(),envelope_sha256=sha(Path(envelope_path)),model_sha256=sha(path),availability='user-supplied evidence; timestamps are not independently provider-certified')
    with log.open('a',encoding='utf-8') as stream:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(json.dumps(row,indent=2,ensure_ascii=False))

def protocol():
    inventory=OUT/'model_inventory.csv'
    save_json(OUT/'prospective_protocol.json',dict(status='NOT RUN: no future observations or performance claims',earliest_target_start_utc='2026-10-20T00:00:00Z',fixed_evaluation_end_utc='2027-10-20T00:00:00Z',target='next full UTC day return or squared return',freeze='All40 learned artifacts frozen; no tuning on logged outcomes; no interim model selection',inventory_sha256=sha(inventory),logging='Write strictly before origin; future origin <=24h away; own/macro information cutoff at least24h before origin; append-only duplicate protection; input and model hashes',score='After fixed evaluation window, use paired dates and declared MSE/QLIKE/HAC5/BH families32and40; do not call old2025+ test untouched; disclose missing forecast days',limit='Requires actual collection of future input/label snapshots. A protocol is not a completed new OOS experiment.'))
