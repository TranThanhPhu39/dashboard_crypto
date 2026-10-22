"""Create missing local report entrypoints; never overwrite historical files."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
LEGACY = {
    'outputs/research/evidence_20261019/dashboard.html': 'fomc',
    'outputs/research/pit_nested_20261020/dashboard.html': 'forecast',
    'outputs/research/release_20261025/dashboard.html': 'transmission',
}


def repair(root=ROOT):
    created = []
    for relative, view in LEGACY.items():
        path = root / relative
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        target = os.path.relpath(root/'dashboard/index.html', path.parent).replace(os.sep, '/') + '#' + view
        content = f'<!doctype html><html lang="vi"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={target}"><title>Mở dashboard chính</title><p>Dashboard chính đã được hợp nhất.</p><a href="{target}">Mở Orbit dashboard</a></html>'
        with path.open('x', encoding='utf-8') as stream:
            stream.write(content)
        created.append(relative)
    return created


if __name__ == '__main__':
    for name in repair():
        print('Added missing local entrypoint:', name)
