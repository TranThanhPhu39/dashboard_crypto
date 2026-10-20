"""Versioned maintenance adapter; frozen empirical source files stay unchanged.

An old snapshot is verified against live immutable files and byte-identical
archived copies of a small explicit set of operational/presentation files.
This is NOT permission to ignore arbitrary changed files or refresh a lock.
"""
from pathlib import Path
import importlib,json,hashlib,shutil,sys
from research_common import ROOT, pd
from src.utils.project import sha,save_json

VERSION='release_20261025'
OUT=ROOT/'outputs/research'/VERSION
CONFIG=ROOT/'config'/f'{VERSION}.json'
MIGRATION=OUT/'preservation_migration.json'

def config():return json.loads(CONFIG.read_text(encoding='utf-8'))

def safe_path(root,name):
    p=(root/name).resolve()
    if not p.is_relative_to(root.resolve()):raise AssertionError('Path outside repository: '+name)
    return p

def validate_policy(obj,cfg,root=ROOT,out=OUT):
    allowed=set(cfg['mutable_operational_paths']+cfg['maintained_paths'])
    assert set(obj['paths']).issubset(allowed),'Migration attempts to expand exact allowlist'
    expected={}
    for name,record in obj['paths'].items():
        assert record['archive']==(out/'originals'/name).relative_to(root).as_posix(),'Unexpected archive location'
        role='operational_status' if name in cfg['mutable_operational_paths'] else 'maintained_navigation_or_entrypoint'
        assert record['role']==role,'Wrong migration role'
        digest=record['original_sha256']
        assert len(digest)==64 and all(c in '0123456789abcdef' for c in digest),'Invalid archive hash'
        expected[record['archive']]=digest
    assert obj['archive_sha256']==expected,'Archive inventory differs from exact allowlist records'

def initialize():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=config()
    if MIGRATION.exists():
        obj=json.loads(MIGRATION.read_text(encoding='utf-8'))
        assert obj['config_sha256']==sha(CONFIG),'Migration policy changed; register a new version'
        validate_policy(obj,cfg)
        verify_mapping(obj['archive_sha256'],root=ROOT,migration={})
        return obj
    allowed=cfg['mutable_operational_paths']+cfg['maintained_paths']
    assert len(allowed)==len(set(allowed))
    mapping={};archives={}
    for name in allowed:
        p=safe_path(ROOT,name)
        if not p.exists():continue
        digest=sha(p);archive=OUT/'originals'/name
        archive.parent.mkdir(parents=True,exist_ok=True)
        if archive.exists():assert sha(archive)==digest
        else:shutil.copyfile(p,archive)
        assert sha(archive)==digest
        key=archive.relative_to(ROOT).as_posix()
        mapping[name]=dict(original_sha256=digest,archive=key,role='operational_status' if name in cfg['mutable_operational_paths'] else 'maintained_navigation_or_entrypoint')
        archives[key]=digest
    obj=dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),config_sha256=sha(CONFIG),paths=mapping,archive_sha256=archives,
        scope='Original snapshots remain immutable; only exact enumerated mutable paths resolve to their archived historical bytes.')
    validate_policy(obj,cfg)
    save_json(MIGRATION,obj)
    return obj

def historical_path(name,digest,root=ROOT,migration=None):
    """Resolve expected OLD bytes. Unknown changes fail closed."""
    root=Path(root);live=safe_path(root,name)
    obj=initialize() if migration is None else migration
    records=obj.get('paths',{})
    record=records.get(name)
    if record is not None:
        assert record['original_sha256']==digest, 'Archived version differs from expected lock: '+name
        archive=safe_path(root,record['archive'])
        assert archive.is_file() and sha(archive)==digest,'Historical archive damaged: '+name
        assert live.is_file(),'Maintained live file missing: '+name
        return archive
    assert live.is_file() and sha(live)==digest,'Immutable file changed: '+name
    return live

def verify_mapping(files,root=ROOT,migration=None):
    obj=initialize() if migration is None else migration
    for name,digest in files.items():historical_path(name,digest,root,obj)
    return len(files)

def check_snapshot(module):
    obj=module.init()
    return verify_mapping(obj['protected_sha256'])

def install():
    """Patch verification only, never fit_cutoff/features/learners/forecasts."""
    initialize();replacements={}
    for name in ['pit_nested_common','evidence_common','latency_common','robustness_common','fomc_identification_common']:
        module=importlib.import_module('src.evaluation.'+name)
        original=module.check_protected
        if getattr(original,'_release_adapter',False):continue
        def checker(m=module):return check_snapshot(m)
        checker._release_adapter=True
        module.check_protected=checker;replacements[original]=checker
    # Handle already-imported from-* bindings (CLI imports and test runners).
    for name,module in list(sys.modules.items()):
        if module is None or not (name.startswith('src.') or name in ['run_pit_nested','run_evidence','run_prospective','plan_submission']):continue
        value=getattr(module,'check_protected',None)
        if value in replacements:setattr(module,'check_protected',replacements[value])

def validate():
    obj=initialize();checks={}
    checks['original_archive_hashes']=bool(verify_mapping(obj['archive_sha256'],migration={}))
    snap=ROOT/'outputs/research/pit_nested_20261020/source_snapshot.json'
    old=json.loads(snap.read_text(encoding='utf-8'))
    checks['3088_old_entries_verifiable']=verify_mapping(old['protected_sha256'])==3088
    # These locks remain byte-identical; they are checked against live code/data.
    for name in ['prepared_input_lock.json','fit_code_lock.json']:
        lock=json.loads((snap.parent/name).read_text(encoding='utf-8'))
        checks[name]=all(sha(ROOT/n)==h for n,h in lock['files'].items())
    prior=ROOT/'outputs/research/submission_20261025/prerequisite_lock.json'
    checks['submission_prerequisites']=bool(verify_mapping(json.loads(prior.read_text(encoding='utf-8'))['files']))
    checks['allowlist_excludes_data_models_protocols']=all(not (n.startswith(('data/','models/')) or n.endswith('protocol.json')) for n in obj['paths'])
    raw_live_mismatches=[n for n,h in old['protected_sha256'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
    checks['every_live_difference_is_explicitly_migrated']=all(n in obj['paths'] for n in raw_live_mismatches)
    assert all(checks.values()),checks
    save_json(OUT/'preservation_validation.json',dict(checked_utc=pd.Timestamp.now(tz='UTC').isoformat(),checks=checks,passed=len(checks),total=len(checks),
        historical_entries=len(old['protected_sha256']),archived_paths=len(obj['paths']),permitted_live_differences=raw_live_mismatches,interpretation='Historical bytes verified, permitted current status may evolve; not a performance or PIT certification.'))
    return checks
