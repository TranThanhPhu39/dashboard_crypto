"""Read-only FOMC presentation from frozen event observations and saved fits."""
import csv
from datetime import datetime
import io
import json
import math
from pathlib import Path
import re

from src.live_dashboard_data import verified, number

ROOT = Path(__file__).resolve().parents[1]


def records(raw):
    return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))


def payload(root=ROOT):
    root = Path(root)
    manifest = json.loads((root/'dashboard/fomc_display_sources.json').read_text(encoding='utf-8'))
    sources = {name: verified(root, name, digest) for name, digest in manifest['files'].items()}
    audit_name = 'outputs/research/fomc_identification_20261019/event_audit.csv'
    panel_name = 'data/processed/fomc_identification_20261019/analysis_panel.csv'
    interval_name = 'outputs/research/evidence_20261019/generated_shock_intervals.csv'
    lock = json.loads((root/'outputs/research/fomc_identification_20261019/analysis_lock.json').read_text(encoding='utf-8'))
    if (manifest['files'][audit_name] != lock['event_audit_sha256'] or
            manifest['files'][panel_name] != lock['panel_sha256']):
        raise ValueError('FOMC display differs from frozen analysis inputs')
    statements = json.loads((root/'dashboard/fomc_statements.json').read_text(encoding='utf-8'))['statements']
    audit = [r for r in records(sources[audit_name]) if r['primary_joint'] == 'True']
    panel = {(r['asset'], r['date'], r['outcome']): number(r['actual_pct'])
             for r in records(sources[panel_name]) if r['primary_joint'] == 'True'}
    outcomes = ['intraday', 'event_day'] + [f'post_{h}' for h in range(1, 31)]
    events = {}
    for row in audit:
        day, asset = row['date'], row['asset']
        if row['scheduled'] != 'True' or asset not in ['BTC', 'ETH']:
            raise ValueError('Unexpected primary FOMC event')
        local, utc = datetime.fromisoformat(row['event_time_et']), datetime.fromisoformat(row['event_time_utc'])
        if local != utc or utc.utcoffset().total_seconds() != 0:
            raise ValueError('FOMC Eastern/UTC mismatch')
        url = statements[day]
        if not re.fullmatch(r'https://www\.federalreserve\.gov/newsevents/pressreleases/monetary' + day.replace('-', '') + r'a\.htm', url):
            raise ValueError('Unexpected official FOMC statement URL')
        event = dict(date=day, event_time_et=local.isoformat(), event_time_utc=utc.isoformat(),
                     statement_url=url, policy_bps=number(row['author_policy'])*100,
                     information_bps=number(row['author_information'])*100,
                     pc1_bps=number(row['pc1'])*100, stress=number(row['prior_vix']) >= 25)
        if day not in events:
            events[day] = dict(event, assets={})
        if any(events[day][key] != value for key, value in event.items()) or asset in events[day]['assets']:
            raise ValueError('Inconsistent or duplicate FOMC event')
        values = {name: panel[asset, day, name] for name in outcomes}
        candles = json.loads(verified(root, row['minute_file'], row['minute_sha256']))
        close = {}
        for candle in candles:
            stamp, value = int(candle[0]), number(candle[4])
            if stamp in close or value <= 0:
                raise ValueError('Duplicate or nonpositive FOMC minute close')
            close[stamp] = value
        # Coinbase timestamps mark candle OPEN; use its close at t + minute.
        first = int(utc.timestamp()) - 11*60
        path = [[minute, 100*math.log(close[int(utc.timestamp())+minute*60-60]/close[first])]
                for minute in range(-10, 21)]
        if not math.isclose(path[-1][1], values['intraday'], abs_tol=1e-10):
            raise ValueError('FOMC minute path does not reproduce frozen outcome')
        events[day]['assets'][asset] = dict(returns=values, minute_path=path)
    ordered = [events[day] for day in sorted(events)]
    if not ordered or any(set(e['assets']) != {'BTC', 'ETH'} for e in ordered):
        raise ValueError('Incomplete joint FOMC sample')
    intervals = []
    for row in records(sources[interval_name]):
        if number(row['weight']) != .5:
            continue
        intervals.append(dict(asset=row['asset'], shock=row['shock'], outcome=row['outcome'],
                              beta=number(row['beta']), lower95=number(row['lower95_percentile']),
                              upper95=number(row['upper95_percentile']), draws=int(row['successful_draws'])))
    if len(intervals) != 2*2*len(outcomes) or len({(r['asset'], r['shock'], r['outcome']) for r in intervals}) != len(intervals):
        raise ValueError('Incomplete saved FOMC interval grid')
    return dict(schema_version=1, sample=dict(count=len(ordered), first_date=ordered[0]['date'],
                last_date=ordered[-1]['date'], pre2020=sum(e['date'] < '2020-01-01' for e in ordered),
                post2020=sum(e['date'] >= '2020-01-01' for e in ordered)), events=ordered,
                intervals=intervals, source_hashes=manifest['files'])


def enhance(html):
    html = re.sub(r'\n?/\* ORBIT FOMC START \*/.*?/\* ORBIT FOMC END \*/\n?', '', html, flags=re.S)
    data = json.dumps(payload(), ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('</', '<\\/')
    script = '\n/* ORBIT FOMC START */\nconst FOMC_RESEARCH=' + data + ';\n'
    script += (ROOT/'dashboard/fomc.js').read_text(encoding='utf-8') + '\n/* ORBIT FOMC END */\n'
    end = html.index('\n/* ORBIT DESIGN START */')
    return html[:end] + script + html[end:]
