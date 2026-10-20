"""Package the approved extension, preserving all older delivery ZIPs and manifests."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'topic09_completion_20261017.zip'
def digest(blob):return hashlib.sha256(blob).hexdigest()
def main():
    files={p for p in ROOT.iterdir() if p.is_file() and (p.suffix in {'.py','.cjs','.html'} or p.name in {'README.md','requirements.txt','requirements-research.txt'})}
    for folder in ['data','outputs/research','notebooks']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('_alfred_form.html','_alfred_error.html','_request.txt')):files.add(p)
    manifest={}
    for p in sorted(files):
        blob=p.read_bytes();manifest[p.relative_to(ROOT).as_posix()]=dict(bytes=len(blob),sha256=digest(blob))
    mp=ROOT/'manifest_completion.json';mp.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    with zipfile.ZipFile(OUTPUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,p.relative_to(ROOT).as_posix())
        z.write(mp,mp.name)
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        for name,r in manifest.items():
            blob=z.read(name);assert len(blob)==r['bytes'] and digest(blob)==r['sha256'],name
        for name in ['report.html','dashboard.html','design.json','independent_validation.json','browser_validation.json','availability_register.csv','ablation_tests.csv','state_covariance.csv','historical_analogues.csv']:
            assert 'outputs/research/completion/'+name in z.namelist()
        assert json.loads(z.read('outputs/research/completion/independent_validation.json'))['passed']==26
        assert len([n for n in z.namelist() if n.startswith('data/raw/usd_missing_verification/') and n.endswith('.html')])==6
    result=dict(zip=OUTPUT.name,bytes=OUTPUT.stat().st_size,files=len(manifest)+1,sha256=digest(OUTPUT.read_bytes()),all_CRC_and_manifest_hashes_verified=True)
    (ROOT/'package_completion_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
