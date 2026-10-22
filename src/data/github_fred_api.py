"""Official FRED/ALFRED API transport for hosted workers.

Raw HTTP JSON is retained unchanged. CSV/ZIP inputs are explicitly labelled
derived views, not website responses. Frozen feature and clock code is reused.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import io
import json
import os
from pathlib import Path
import re
import zipfile

ENDPOINT = 'https://api.stlouisfed.org/fred/series/observations'
VERSION = 'official_fred_api_v1'
_installed = False


class ProviderMaintenance(RuntimeError):
    """An explicit St. Louis Fed maintenance page, including HTTP 200 pages."""


def maintenance_response(body):
    text = body[:16384].lower()
    return (b'site maintenance' in text and b'st. louis fed' in text and
            (b'proactive maintenance' in text or b'undergoing maintenance' in text))


def public_parameters(sid, start, end, asof=None):
    result = dict(series_id=sid, file_type='json', observation_start=start,
                  observation_end=end, sort_order='asc', units='lin', output_type=1, limit=100000)
    if asof is not None:
        result.update(realtime_start=asof, realtime_end=asof)
    return result


def normalize(payload, params, asof=None):
    """Use exact provider value strings; never carry returns or invent vintages."""
    sid = params['series_id']
    rows = payload.get('observations', [])
    if payload.get('units') != 'lin' or int(payload.get('output_type', -1)) != 1:
        raise ValueError('Provider units or output type differs from the frozen input definition')
    if not rows or int(payload.get('offset', -1)) != 0 or int(payload.get('count', -1)) != len(rows):
        raise ValueError('Incomplete API response or unhandled pagination')
    if asof is not None and (payload.get('realtime_start') != asof or payload.get('realtime_end') != asof):
        raise ValueError('Provider returned a different realtime period')
    seen = set()
    for row in rows:
        day = row['date']
        if not params['observation_start'] <= day <= params['observation_end'] or day in seen:
            raise ValueError('Observation outside requested range or duplicate day')
        seen.add(day)
        if asof is not None and not row['realtime_start'] <= asof <= row['realtime_end']:
            raise ValueError('Observation realtime spell excludes requested vintage')
        if row['value'] != '.':
            value = float(row['value'])
            import math
            if not math.isfinite(value):
                raise ValueError('Nonfinite provider value')
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['period_start_date', 'realtime_start_date', 'realtime_end_date', sid]
                    if asof else ['observation_date', sid])
    for row in sorted(rows, key=lambda r: r['date']):
        writer.writerow([row['date'], row['realtime_start'], row['realtime_end'], row['value']]
                        if asof else [row['date'], row['value']])
    return stream.getvalue().encode('utf-8')


def api_one(folder, sid, start, end, asof=None, root=None, key=None):
    import requests
    from src.automation_runtime import now_utc, digest
    if root is None:
        from research_common import ROOT
        root = ROOT
    key = key if key is not None else os.environ.get('FRED_API_KEY', '').strip()
    if not re.fullmatch(r'[a-z0-9]{32}', key):
        raise ValueError('A valid FRED_API_KEY secret is required; do not put the key in source or logs')
    params = public_parameters(sid, start, end, asof)
    stem = sid + ('_vintage_' + asof if asof else '')
    raw = folder/(stem + '_api_response.json')
    view = folder/'normalized'/(stem + '.zip' if asof else sid + '_fred.csv')
    record = dict(source='alfred_official_api' if asof else 'fred_official_api', series_id=sid,
        url=ENDPOINT, request_parameters=params, request_started_utc=now_utc().isoformat(),
        file=view.relative_to(root).as_posix(), file_role='derived_view_of_archived_raw_api_json',
        transport_version=VERSION, normalizer_sha256=digest(Path(__file__)),
        normalizer_code_snapshot='outputs/research/evidence_20261019/prospective_operations/code_snapshots/' + digest(Path(__file__)) + '.py')
    if asof:
        record['requested_vintage_date'] = asof
    try:
        response = requests.get(ENDPOINT, params={**params, 'api_key': key}, timeout=(12, 35),
                                headers={'User-Agent': 'Topic09 academic macro-crypto research'})
        received = now_utc()
        body = response.content
        if key.encode() in body:
            raise ValueError('Credential echoed by provider; response intentionally not retained')
        with raw.open('xb') as stream:
            stream.write(body)
        record.update(raw_file=raw.relative_to(root).as_posix(), raw_sha256=digest(raw), raw_bytes=len(body),
            raw_received_at_utc=received.isoformat(), http_status=response.status_code,
            http_date=response.headers.get('Date'), last_modified=response.headers.get('Last-Modified'),
            response_content_type=response.headers.get('Content-Type'))
        if response.status_code in (200, 503) and maintenance_response(body):
            raise ProviderMaintenance()
        if response.status_code != 200:
            raise RuntimeError('API HTTP ' + str(response.status_code))
        payload = json.loads(body)
        content = normalize(payload, params, asof)
        view.parent.mkdir(exist_ok=True)
        if asof:
            with zipfile.ZipFile(view, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
                member = zipfile.ZipInfo(sid + '.obs._by_real-time_period.csv', (1980, 1, 1, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(member, content)
        else:
            with view.open('xb') as stream:
                stream.write(content)
        ready = now_utc()
        numeric = [r for r in payload['observations'] if r['value'] != '.']
        if len(numeric) < 2:
            raise ValueError('Fewer than two numeric observations')
        record.update(status='ok', sha256=digest(view), bytes=view.stat().st_size,
            available_at_utc=ready.isoformat(), retrieved_at_utc=received.isoformat(),
            normalized_at_utc=ready.isoformat(), numeric_observations=len(numeric),
            latest_observation_date=max(r['date'] for r in numeric))
    except Exception as error:
        # requests exceptions contain the prepared URL, including api_key.
        # Never serialize their message, traceback or response URL.
        record.update(status='failed', error_code='PROVIDER_MAINTENANCE' if isinstance(error, ProviderMaintenance) else type(error).__name__,
            error=('St. Louis Fed returned an explicit maintenance page; raw response retained; retry next scheduled capture'
                   if isinstance(error, ProviderMaintenance) else
                   type(error).__name__ + '; API transport failed; inspect archived HTTP status and response format'),
            finished_utc=now_utc().isoformat())
    return record


def verify_record(record, root):
    if record.get('transport_version') != VERSION:
        return
    from src.automation_runtime import digest, timestamp
    root = Path(root).resolve()
    def checked(name, expected):
        path = (root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path) != expected:
            raise ValueError('API raw/view/code integrity failure')
        return path
    raw = checked(record['raw_file'], record['raw_sha256'])
    view = checked(record['file'], record['sha256'])
    checked(record['normalizer_code_snapshot'], record['normalizer_sha256'])
    expected = normalize(json.loads(raw.read_bytes()), record['request_parameters'], record.get('requested_vintage_date'))
    if record.get('requested_vintage_date'):
        with zipfile.ZipFile(view) as archive:
            names = archive.namelist()
            if names != [record['series_id'] + '.obs._by_real-time_period.csv']:
                raise ValueError('Unexpected normalized API ZIP content')
            actual = archive.read(names[0])
    else:
        actual = view.read_bytes()
    if actual != expected:
        raise ValueError('Normalized view does not match the actual raw API response')
    if not timestamp(record['raw_received_at_utc']) <= timestamp(record['available_at_utc']):
        raise ValueError('Derived view predates actual source receipt')


def collect():
    from src.data import latency_snapshots as snapshots
    from research_common import ROOT, pd
    from src.automation_runtime import digest
    snapshots.init()
    started = snapshots.now()
    folder = snapshots.RAW/'live'/started.strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True, exist_ok=False)
    origin = started.normalize() + pd.Timedelta(days=1)
    info_dates = [str((origin-pd.Timedelta(days=k)).date()) for k in [3, 2]]
    start = str((started.normalize()-pd.Timedelta(days=180)).date())
    end = str((started.normalize()-pd.Timedelta(days=1)).date())
    p1 = int((started.normalize()-pd.Timedelta(days=180)).timestamp())
    p2 = int(started.normalize().timestamp())
    public = {f'{a}_coinmetrics.json': f'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={a}&metrics=PriceUSD&frequency=1d&start_time={start}&end_time={end}&page_size=10000' for a in ['btc', 'eth']}
    for name, symbol in [('gold', 'GC%3DF'), ('sp500', '%5EGSPC')]:
        public[name+'_yahoo.json'] = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={p1}&period2={p2}&interval=1d'
    rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [pool.submit(snapshots.fetch_one, folder, name, url) for name, url in public.items()]
        tasks.append(pool.submit(api_one, folder, 'VIXCLS', start, end))
        tasks.extend(pool.submit(api_one, folder, sid,
            str((pd.Timestamp(day)-pd.Timedelta(days=180)).date()), day, day)
            for day in info_dates for sid in snapshots.PIT_SERIES)
        for future in as_completed(tasks):
            row = future.result()
            rows.append(row)
            print(row.get('series_id') or Path(row['file']).name, row['status'],
                  row.get('latest_observation_date', row.get('error', '')), flush=True)
    manifest = dict(capture_started_utc=started.isoformat(), capture_finished_utc=snapshots.now().isoformat(),
        method='Official FRED/ALFRED API; raw JSON retained verbatim. CSV/ZIP inputs are verified derived views. Requested realtime_start=realtime_end for each information-day vintage; actual receipt and original clock rules.',
        transport_version=VERSION, normalizer_sha256=digest(Path(__file__)),
        information_dates=info_dates, sources=sorted(rows, key=lambda r: r['file']))
    snapshots.save_json(folder/'manifest.json', manifest)
    snapshots.save_json(snapshots.OUT/'latest_capture.json', dict(manifest=(folder/'manifest.json').relative_to(ROOT).as_posix(),
        sha256=digest(folder/'manifest.json'), sources_ok=sum(r['status']=='ok' for r in rows), sources_total=len(rows)))
    return folder/'manifest.json'


def compare_archived(records, history, root):
    """Migration check against saved website vintages; no forecast loss is read."""
    from src.data.latency_snapshots import alfred_frame
    from src.evaluation.latency_live import market_series
    import numpy as np
    results = []
    for record in records:
        if record.get('transport_version') != VERSION or record['status'] != 'ok':
            continue
        verify_record(record, root)
        sid = record['series_id']
        asof = record.get('requested_vintage_date')
        matches = [r for r in history if r.get('transport_version') != VERSION and
            (r.get('series_id') == sid and r.get('requested_vintage_date') == asof if asof else
             Path(r['file']).name == 'VIXCLS_fred.csv')]
        if not matches:
            continue
        previous = max(matches, key=lambda r: r['available_at_utc'])
        if asof:
            before = alfred_frame(root/previous['file'], sid, asof).set_index('period_start_date')[sid]
            after = alfred_frame(root/record['file'], sid, asof).set_index('period_start_date')[sid]
            if not before.index.equals(after.index):
                raise ValueError('API and saved website vintage observation dates differ: ' + sid)
        else:
            before, after = market_series(previous), market_series(record)
        common = before.index.intersection(after.index)
        if not len(common) or not np.allclose(before.loc[common], after.loc[common], rtol=1e-12, atol=1e-12):
            raise ValueError('API and saved website observations differ: ' + sid)
        results.append(dict(series_id=sid, requested_vintage_date=asof, matched_observations=len(common)))
    return results


def install():
    """Operational transport only. Do not edit the frozen collector/parser files."""
    global _installed
    if _installed:
        return
    if not re.fullmatch(r'[a-z0-9]{32}', os.environ.get('FRED_API_KEY', '').strip()):
        raise RuntimeError('FRED_API_KEY repository secret is missing or malformed')
    from src.evaluation import prospective_operations as op
    from src.data import latency_snapshots as snapshots
    from research_common import ROOT
    from src.automation_runtime import digest
    source = Path(__file__)
    archived = op.OPS/'code_snapshots'/(digest(source) + '.py')
    archived.parent.mkdir(parents=True, exist_ok=True)
    if not archived.exists():
        with archived.open('xb') as stream:
            stream.write(source.read_bytes())
    if digest(archived) != digest(source):
        raise ValueError('API transport code snapshot differs from its digest')
    original = op.legacy.records
    def verified_records():
        rows = original()
        for row in rows:
            verify_record(row, ROOT)
        return rows
    op.legacy.records = verified_records
    snapshots.collect = collect
    _installed = True
