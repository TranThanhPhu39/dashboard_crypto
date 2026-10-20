"""Versioned delivery with all code, raw evidence, frozen artifacts and audit results."""
from src.utils.project import *
import zipfile

def run():
    check=json.loads((OUT/'independent_validation.json').read_text());assert check['passed']==check['n_checks']
    browser=json.loads((OUT/'browser_validation.json').read_text());assert browser['uncaught_errors']==0
    output=ROOT/f'topic09_{VERSION}.zip';mp=ROOT/f'manifest_{VERSION}.json'
    selected={p for p in ROOT.iterdir() if p.is_file() and (p.suffix in {'.py','.cjs','.html'} or p.name=='README.md' or p.name.startswith('requirements'))}
    # Older source snapshots hash earlier deliveries and all auxiliary public raw
    # payloads. Include these too so validation works in a fully extracted copy.
    selected.update(p for p in ROOT.glob('topic09*.zip') if p!=output)
    selected.update(p for p in ROOT.glob('manifest*.json') if p!=mp)
    selected.update(p for p in ROOT.glob('package_*_validation.json') if p.name!=f'package_{VERSION}_validation.json')
    for folder in ['src','config','models','dashboard','tests','paper','data','notebooks','outputs/research']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:selected.add(p)
    manifest={}
    for p in sorted(selected):
        blob=p.read_bytes();manifest[p.relative_to(ROOT).as_posix()]=dict(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())
    save_json(mp,manifest)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(selected):z.write(p,p.relative_to(ROOT).as_posix())
        z.write(mp,mp.name)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        for name,r in manifest.items():
            blob=z.read(name);assert len(blob)==r['bytes'] and hashlib.sha256(blob).hexdigest()==r['sha256'],name
        assert len([name for name in z.namelist() if name.startswith('models/'+VERSION) and name.endswith('.joblib')])==40
        snapshot=json.loads(z.read('outputs/research/'+VERSION+'/source_snapshot.json'))
        assert all(name in z.namelist() and hashlib.sha256(z.read(name)).hexdigest()==value for name,value in snapshot['protected_sha256'].items()), 'Extracted package must contain every protected prerequisite.'
        for name in ['dashboard/index.html','run_project.py','src/models/quantile.py','src/models/econometrics.py','tests/test_prospective.py','outputs/research/'+VERSION+'/report.html']:assert name in z.namelist()
    result=dict(zip=output.name,bytes=output.stat().st_size,files=len(manifest)+1,sha256=sha(output),CRC_and_all_manifest_hashes_verified=True)
    save_json(ROOT/f'package_{VERSION}_validation.json',result);print(json.dumps(result,indent=2))
