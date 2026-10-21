"""No-secret connectivity diagnostic; responses never enter the research ledger."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    now = datetime.now(timezone.utc)
    end = (now-timedelta(days=1)).date().isoformat()
    start = (now-timedelta(days=14)).date().isoformat()
    urls = [('fred', f'https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS&cosd={start}&coed={end}'),
            ('alfred', 'https://alfred.stlouisfed.org/series/downloaddata?seid=DGS2')]
    rows = []
    folder = ROOT/'.worker-work/network-probe'
    folder.mkdir(parents=True, exist_ok=True)
    for name, url in urls:
        started = time.monotonic()
        row = {'source': name, 'url': url}
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (academic prospective research)'})
            with urllib.request.urlopen(request, timeout=35) as response:
                data = response.read()
                row.update(status=response.status, bytes=len(data), ok=response.status==200)
        except Exception as error:
            row.update(ok=False, error=str(error))
        row['seconds'] = round(time.monotonic()-started, 2)
        rows.append(row)
        print(json.dumps(row), flush=True)
        started = time.monotonic()
        curl = shutil.which('curl.exe') or shutil.which('curl')
        result = subprocess.run([curl, '-4', '-f', '-sS', '-L', '--max-time', '35', '--connect-timeout', '12',
            '--user-agent', 'Mozilla/5.0 (academic prospective research)', '-o', str(folder/(name+'.response')),
            '--write-out', '%{http_code}', url], capture_output=True, text=True, timeout=40)
        row = {'source': name, 'transport': 'curl_ipv4', 'returncode': result.returncode,
               'http_status': result.stdout, 'error': result.stderr[-300:],
               'seconds': round(time.monotonic()-started, 2), 'ok': result.returncode==0}
        rows.append(row)
        print(json.dumps(row), flush=True)
    record = {'checked_at_utc': now.isoformat(), 'platform': platform.platform(), 'checks': rows,
              'used_for_forecasts': False}
    (folder/'result.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    return 0 if all(row['ok'] for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
