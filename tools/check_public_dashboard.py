"""Check publication boundaries, exact snapshot bytes and dashboard navigation."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from export_public_dashboard import FILES, PUBLIC, PUBLIC_PAGES, ROOT, RUNTIME_FILES, dashboard_only_bytes


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == 'id':
                self.ids.append(value)
            if value and (name == 'src' or (tag in ('a', 'link') and name == 'href')):
                self.links.append(value)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dashboard-only', action='store_true')
    args = parser.parse_args()
    public = PUBLIC_PAGES if args.dashboard_only else PUBLIC
    files = ('dashboard/index.html',) if args.dashboard_only else FILES
    metadata = json.loads((public/'build_info.json').read_text(encoding='utf-8'))
    require(metadata['publication_mode'] == ('dashboard_only' if args.dashboard_only else 'research_snapshot'),
            'Wrong publication scope')
    expected = set(files) | {'index.html', 'build_info.json', 'dashboard/status.json'}
    actual = set()
    for path in public.rglob('*'):
        require(not path.is_symlink(), 'Symlink in public output')
        require(path.resolve().is_relative_to(public.resolve()), 'Path outside public output')
        if path.is_file():
            require(path.stat().st_nlink == 1, 'Hard link in public output')
            actual.add(path.relative_to(public).as_posix())
    require(actual == expected, 'Missing or unexpected public files')
    require(set(metadata['files_sha256']) == set(files), 'Manifest differs from file allowlist')
    status_bytes = (public/'dashboard/status.json').read_bytes()
    require(metadata.get('derived_files_sha256') == {'dashboard/status.json': hashlib.sha256(status_bytes).hexdigest()}, 'Public status hash mismatch')
    import sys
    sys.path.insert(0, str(ROOT))
    from src.dashboard_experience import public_status, capture_status
    status = json.loads(status_bytes)
    wanted_status = public_status((ROOT/'dashboard/index.html').read_text(encoding='utf-8'))
    wanted_status.update(published_at_utc=metadata['exported_at_utc'], source_commit=metadata['source_commit'])
    wanted_status['capture'] = capture_status(ROOT)
    require(status == wanted_status, 'Public status differs from snapshot')
    for relative, digest in metadata['files_sha256'].items():
        require(Path(relative).parts[0] not in {'data', 'models', '.git', 'src', 'config', 'tools', 'tests'},
                'Non-public directory in artifact')
        data = (public/relative).read_bytes()
        require(hashlib.sha256(data).hexdigest() == digest, 'Public hash mismatch: '+relative)
        source = (ROOT/relative).read_bytes()
        require(hashlib.sha256(source).hexdigest() == metadata['source_files_sha256'][relative], 'Source hash mismatch')
        wanted = dashboard_only_bytes(source) if args.dashboard_only else source
        require(data == wanted, 'Snapshot source mismatch: '+relative)
        if args.dashboard_only:
            for tag in (b'script', b'style'):
                pattern = b'<'+tag+rb'\b[^>]*>(.*?)</'+tag+rb'\s*>'
                require(re.findall(pattern, data, re.IGNORECASE | re.DOTALL) ==
                        re.findall(pattern, source, re.IGNORECASE | re.DOTALL), 'Dashboard code/data changed')
    if os.environ.get('GITHUB_SHA'):
        require(metadata['source_commit'] == os.environ['GITHUB_SHA'], 'Wrong source commit')
        if metadata.get('worker'):
            receipt = json.loads((ROOT/'.worker-work/persisted.json').read_text())
            require(metadata['worker']['state_commit'] == receipt['state_commit'] and
                    metadata['worker']['catalog_sha256'] == receipt['catalog_sha256'] and
                    metadata['worker']['generation'] == receipt['generation'], 'Runtime commit receipt mismatch')
            require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Runtime publication outside Actions')
            from export_public_dashboard import git_value
            changed = git_value('diff', '--name-only', 'HEAD').splitlines()
            require(set(changed).issubset(RUNTIME_FILES), 'Tracked source changed outside runtime allowlist')
            require(changed == metadata['worker']['runtime_modified_paths'], 'Runtime paths changed after export')
        else:
            require(metadata['tracked_worktree_changes'] is False, 'CI source worktree is dirty')
    linked_files = 0
    for relative in ('index.html', 'dashboard/index.html'):
        parser = Links()
        parser.feed((public/relative).read_text(encoding='utf-8'))
        if args.dashboard_only and relative == 'dashboard/index.html':
            source_parser = Links()
            source_parser.feed((ROOT/relative).read_text(encoding='utf-8'))
            require(parser.ids == source_parser.ids, 'Dashboard DOM IDs changed during export')
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            require(not url.path.startswith('/'), 'Absolute path breaks GitHub project URL: '+link)
            target = ((public/relative).parent/unquote(url.path)).resolve()
            require(target.is_relative_to(public.resolve()), 'Dashboard link escapes public output')
            if target.is_dir():
                target = target/'index.html'
            require(target.is_file(), 'Missing dashboard navigation target: '+link)
            linked_files += 1
    print(json.dumps({'public_files': len(actual), 'source_hashes_verified': len(files),
                      'dashboard_navigation_targets': linked_files,
                      'dashboard_only': args.dashboard_only}))


if __name__ == '__main__':
    main()
