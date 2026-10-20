"""Apply both supplements to a separate base checkout and validate without network."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    allowed = (root/'.verification').resolve()
    destination = (allowed/'prospective_operations_20261019').resolve()
    assert destination.is_relative_to(allowed) and destination != allowed
    destination.mkdir(parents=True, exist_ok=False)
    base = root/'topic09_evidence_20261019_supplement.zip'
    supplement = root/'topic09_prospective_operations_20261019_supplement.zip'
    with zipfile.ZipFile(base) as first, zipfile.ZipFile(supplement) as second:
        manifest = json.loads(first.read('manifest_evidence_20261019.json'))
        supplemental = json.loads(second.read('manifest_prospective_operations_20261019.json'))
        for name, value in supplemental['files'].items():
            assert hashlib.sha256(second.read(name)).hexdigest() == value
        dependencies = dict(manifest['external_frozen_prerequisites'])
        dependencies.update(manifest['base_code_dependencies'])
        dependencies[base.name] = digest(base)
        names = set(first.namelist()) | set(second.namelist())
        linked = 0
        for name, value in dependencies.items():
            source = (root/name).resolve()
            target = (destination/name).resolve()
            assert source.is_relative_to(root) and target.is_relative_to(destination)
            assert digest(source) == value
            if name not in names:
                target.parent.mkdir(parents=True, exist_ok=True)
                os.link(source, target)
                linked += 1
        for archive in [first, second]:
            assert archive.testzip() is None
            assert all((destination/name).resolve().is_relative_to(destination) for name in archive.namelist())
            archive.extractall(destination)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root/'.research_deps')
    unit = subprocess.run([sys.executable, 'run_prospective.py', 'validate'], cwd=destination,
        env=env, capture_output=True, text=True, encoding='utf-8')
    dashboard = subprocess.run(['node', 'tests/validate_evidence_dashboard.cjs'], cwd=destination,
        env=env, capture_output=True, text=True, encoding='utf-8')
    result = dict(supplement_sha256=digest(supplement), base_supplement_sha256=digest(base),
        external_files_linked_read_only_use=linked, operational_validation_exit=unit.returncode,
        dashboard_validation_exit=dashboard.returncode, operational_stdout=unit.stdout,
        operational_stderr=unit.stderr, dashboard_stdout=dashboard.stdout, dashboard_stderr=dashboard.stderr,
        mode='Separate workspace directory; frozen prerequisites hardlinked for read-only use; no network or live forecast')
    target = root/'bundle_reproduction_prospective_operations_20261019.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(operational_exit=unit.returncode, dashboard_exit=dashboard.returncode,
        audit=target.name)))
    assert unit.returncode == dashboard.returncode == 0, unit.stderr+dashboard.stderr


if __name__ == '__main__':
    main()
