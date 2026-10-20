"""Render the standalone literature review without mutating research outputs."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import os
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.robustness_product import render_markdown

SOURCE = ROOT/'paper/pit_oos_remedies_review_20261019.md'
OUT = ROOT/'outputs/research/pit_oos_review_20261019'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    content = render_markdown(SOURCE.read_text(encoding='utf-8'))
    def relocate(match):
        href = match.group(1)
        if urlsplit(href).scheme or href.startswith('#'):
            return match.group(0)
        target = (SOURCE.parent/unquote(href)).resolve()
        assert target.is_relative_to(ROOT) and target.exists(), str(target)
        return 'href="'+Path(os.path.relpath(target, OUT)).as_posix()+'"'
    content = re.sub(r'href="([^"]+)"', relocate, content)
    css = 'body{font:16px/1.65 system-ui,sans-serif;color:#17324a;background:#f7fafc;max-width:1120px;margin:auto;padding:24px}h1{font-size:28px;line-height:1.3}h2{font-size:23px;margin-top:36px}h3{font-size:19px;margin-top:24px}p{overflow-wrap:anywhere}a{color:#075e83}code{font-size:.9em;overflow-wrap:anywhere}.table-wrap{overflow:auto;background:#fff;border:1px solid #d6e1eb;border-radius:8px}table{border-collapse:collapse;width:100%;min-width:760px;font-size:14px}td,th{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #d6e1eb}thead{background:#eaf2f8}pre{overflow:auto;background:#edf3f8;padding:16px}'
    page = '<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Timing/PIT và untouched OOS — rà soát phương pháp</title><style>'+css+'</style><body>'+content+'</body></html>'
    target = OUT/'report.html'
    target.write_text(page, encoding='utf-8')
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.links = []; self.tables = 0
        def handle_starttag(self, tag, attributes):
            if tag == 'a': self.links.append(dict(attributes)['href'])
            if tag == 'table': self.tables += 1
    parser = Links(); parser.feed(page)
    local = [href for href in parser.links if not urlsplit(href).scheme and not href.startswith('#')]
    assert all((OUT/unquote(href)).resolve().exists() for href in local)
    assert parser.tables == 3
    assert not any(marker in page for marker in ['turn100view', 'turn111view', '\ufffd'])
    audit = dict(status='PASS', scope='Literature/document rendering and local links only; no new empirical results',
        markdown_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), html_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        tables=parser.tables, local_links_verified=len(local), external_links=len(parser.links)-len(local),
        design_changes_implemented=False)
    (OUT/'document_validation.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
