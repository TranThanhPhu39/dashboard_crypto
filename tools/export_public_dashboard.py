"""Export an allowlisted web snapshot; never publish the repository root."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
PUBLIC_PAGES = ROOT / 'public-pages'
FILES = (
    'dashboard/index.html',
    'outputs/research/release_20261025/report.html',
    'outputs/research/release_20261025/report.md',
    'outputs/research/release_20261025/oos_followup.html',
    'outputs/research/release_20261025/oos_followup.md',
    'outputs/research/release_20261025/source_catalog.csv',
    'outputs/research/evidence_20261019/report.html',
    'outputs/research/evidence_20261019/report.md',
    'outputs/research/pit_nested_20261020/report.html',
    'outputs/research/pit_nested_20261020/report.md',
    'outputs/automation_20261020/health.html',
)


def dashboard_only_bytes(data):
    """Keep analysis/scripts; omit links to unpublished research/health pages."""
    text = data.decode('utf-8')
    pattern = r'''<a\b[^>]*\bhref=(["'])(\.\./outputs/[^"']+)\1[^>]*>(.*?)</a\s*>'''
    text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<p\b[^>]*>\s*(?:[\u00b7|]\s*)*</p\s*>', '', text, flags=re.IGNORECASE)
    return text.encode('utf-8')


def write_public(relative, content, public=PUBLIC):
    destination = (public / relative).resolve()
    if not destination.is_relative_to(public.resolve()):
        raise ValueError('Export destination escapes public directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    parent = destination.parent
    while True:
        parent.chmod(0o755)
        if parent == public.resolve():
            break
        parent = parent.parent
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def git_value(*arguments):
    try:
        result = subprocess.run(['git', '-C', str(ROOT), *arguments],
                                capture_output=True, text=True, timeout=15, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dashboard-only', action='store_true', help='Export only the dashboard to public-pages')
    args = parser.parse_args()
    public = PUBLIC_PAGES if args.dashboard_only else PUBLIC
    files = ('dashboard/index.html',) if args.dashboard_only else FILES
    if public.is_symlink() or not public.resolve().is_relative_to(ROOT):
        raise ValueError('Public directory must be a real directory within this repository')
    allowed = set(files) | {'index.html', 'build_info.json'}
    if public.exists():
        for path in public.rglob('*'):
            if path.is_symlink() or not path.resolve().is_relative_to(public.resolve()):
                raise ValueError('Unexpected symlink in public directory')
            if path.is_file() and path.relative_to(public).as_posix() not in allowed:
                raise ValueError('Unknown file in public directory; inspect it before publishing')
    contents = {}
    source_hashes = {}
    for relative in files:
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT) or not source.is_file():
            raise ValueError('Missing or invalid public snapshot: ' + relative)
        raw = source.read_bytes()
        source_hashes[relative] = hashlib.sha256(raw).hexdigest()
        contents[relative] = dashboard_only_bytes(raw) if args.dashboard_only else raw
    state = git_value('status', '--porcelain', '--untracked-files=no')
    metadata = {
        'exported_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': git_value('rev-parse', 'HEAD'),
        'tracked_worktree_changes': bool(state) if state is not None else None,
        'publication_mode': 'dashboard_only' if args.dashboard_only else 'research_snapshot',
        'scope': 'Rendered snapshot; exporting does not collect data or run a forecast worker',
        'source_files_sha256': source_hashes,
        'files_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    # Publish the self-contained dashboard last; other files are optional detail pages.
    for relative, data in contents.items():
        if relative != 'dashboard/index.html':
            write_public(relative, data, public)
    write_public('build_info.json', (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode(), public)
    write_public('index.html', b'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=dashboard/"><a href="dashboard/">Dashboard</a>', public)
    write_public('dashboard/index.html', contents['dashboard/index.html'], public)
    print(json.dumps({'exported_files': len(files), 'directory': str(public),
                      'source_commit': metadata['source_commit'], 'snapshot_only': True}))


if __name__ == '__main__':
    main()
