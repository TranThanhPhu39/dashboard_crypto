"""Operate the frozen latency experiment without modifying its archived report files."""
from src.evaluation.evidence_common import *
import shutil

def run():
    init();folder=OUT/'prospective';folder.mkdir(exist_ok=True)
    original=ROOT/'data/prospective/latency_20261019/protocol.json'
    protocol=LIVE/'protocol.json'
    if not protocol.exists():shutil.copyfile(original,protocol)
    assert sha(protocol)==sha(original)
    for name in ['model_inventory.csv','benchmark_states.csv']:
        source=RESULTS/'latency_20261019'/name;target=folder/name
        if not target.exists():shutil.copyfile(source,target)
        assert sha(target)==sha(source)
    from src.data import latency_snapshots as snapshots
    from src.evaluation import latency_live as live
    # Only operational destinations change. Source configuration, frozen models,
    # evaluation dates and clock checks retain the old experiment's definitions.
    snapshots.RAW=RAW;snapshots.OUT=folder;snapshots.init=init
    live.RAW=RAW;live.OUT=folder;live.LIVE=LIVE;live.init=init
    def operational_csv(frame,name):frame.to_csv(folder/name,index=False,encoding='utf-8-sig',float_format='%.17g')
    live.csv=operational_csv
    latest=folder/'latest_capture.json'
    capture_today=False
    if latest.exists():
        manifest=json.loads((ROOT/json.loads(latest.read_text(encoding='utf-8'))['manifest']).read_text(encoding='utf-8'))
        capture_today=pd.Timestamp(manifest['capture_started_utc']).date()==pd.Timestamp.now(tz='UTC').date()
    if not capture_today:snapshots.collect()
    live.forecast();live.labels();live.evaluate()
    save_json(folder/'namespace_audit.json',dict(original_protocol_sha256=sha(original),operational_protocol_sha256=sha(protocol),
        model_inventory_sha256=sha(RESULTS/'latency_20261019/model_inventory.csv'),model_configuration_sha256=sha(ROOT/'config/latency_20261019.json'),
        scope='Operational logs for existing frozen latency40models, same protocol and evaluation window. No new RV model deployment, no scheduler, no mutation of archived latency outputs.',
        predictions_logged=json.loads((folder/'prospective_status.json').read_text(encoding='utf-8'))['total_predictions']))
    assert sha(protocol)==sha(original);check_protected()
