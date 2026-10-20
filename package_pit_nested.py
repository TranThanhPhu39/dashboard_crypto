"""Package only this extension; requires the preserved full base repository."""
from src.evaluation.pit_nested_common import *
import zipfile,hashlib

def main():
    check_protected()
    validation=json.loads((OUT/'independent_validation.json').read_text(encoding='utf-8'))
    assert validation['passed']==validation['total']
    paths=[]
    for directory in [OUT,PANELS,MODELS]:paths.extend(p for p in directory.rglob('*') if p.is_file())
    paths += [CONFIG,ROOT/'run_pit_nested.py',ROOT/'package_pit_nested.py',ROOT/'src/evaluation/pit_nested_common.py',
              ROOT/'src/evaluation/pit_feature_audit.py',ROOT/'src/evaluation/validate_pit_nested.py',ROOT/'src/models/pit_nested.py',
              ROOT/'src/pit_nested_product.py',ROOT/'tests/preview_pit_nested.cjs',ROOT/'README.md']
    files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
    manifest=dict(version=VERSION,created_utc=pd.Timestamp.now(tz='UTC').isoformat(),files=files,
                  prerequisites='Full preserved base repo with raw archives, research_common.py, research_completion.py and Python dependencies. Supplement is not standalone.',
                  freeze_sha256=sha(MODELS/'freeze.json'))
    manifestpath=ROOT/f'manifest_{VERSION}.json';save_json(manifestpath,manifest)
    archive=ROOT/f'topic09_{VERSION}_supplement.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n in files:z.write(ROOT/n,n)
        z.write(manifestpath,manifestpath.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for n,h in files.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
        assert json.loads(z.read(manifestpath.name))==manifest
    save_json(ROOT/f'package_{VERSION}.json',dict(archive=archive.name,sha256=sha(archive),files_verified=len(files),zip_crc_passed=True,
        bytes=archive.stat().st_size,protected_files=check_protected()))
    print('Verified supplement:',archive.name,len(files),'files',flush=True)

if __name__=='__main__':main()
