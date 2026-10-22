"""Classify source availability from authenticated receipts, without relaxing PIT."""
import json
from pathlib import Path

from src.data.github_fred_api import ENDPOINT, maintenance_response
from src.automation_runtime import digest


INCOMPLETE_CAPTURE = 'Not all 17 sources succeeded; retry with a new immutable capture'


def capture_status(root):
    root = Path(root).resolve()
    pointer = root/'outputs/research/evidence_20261019/prospective/latest_capture.json'
    if not pointer.exists():
        return dict(sources_ok=0, sources_total=0, maintenance_only=False, failures=[])
    link = json.loads(pointer.read_text(encoding='utf-8-sig'))
    path = (root/link['manifest']).resolve()
    if not path.is_relative_to(root) or digest(path) != link['sha256']:
        raise ValueError('Capture manifest integrity failure')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    sources = manifest['sources']
    failed = [r for r in sources if r['status'] != 'ok']
    failures = []
    for row in failed:
        maintenance = False
        if row.get('url') == ENDPOINT and row.get('raw_file') and row.get('http_status') in (200, 503):
            raw = (root/row['raw_file']).resolve()
            if not raw.is_relative_to(root) or digest(raw) != row['raw_sha256']:
                raise ValueError('Failed source raw-response integrity failure')
            maintenance = maintenance_response(raw.read_bytes())
        failures.append(dict(source=row.get('series_id') or Path(row.get('file', 'unknown')).name,
            code='PROVIDER_MAINTENANCE' if maintenance else row.get('error_code', 'CAPTURE_ERROR'),
            maintenance_confirmed=maintenance, http_status=row.get('http_status'),
            raw_bytes=row.get('raw_bytes', row.get('bytes'))))
    return dict(capture_started_utc=manifest.get('capture_started_utc'), manifest=link['manifest'],
        sources_ok=sum(r['status'] == 'ok' for r in sources), sources_total=len(sources),
        maintenance_only=bool(len(sources) == 17 and failures and all(r['maintenance_confirmed'] for r in failures)),
        failures=failures)


def assess(state, health, capture, exit_code=0):
    """Data-readiness warnings may publish status; operational faults still fail."""
    maintenance = bool(capture['maintenance_only'] and (
        state.get('status') == 'deferred_source_maintenance' or
        (state.get('status') == 'failed' and state.get('error') == INCOMPLETE_CAPTURE)))
    blockers = []
    warnings = []
    for issue in health.get('issues', []):
        name = issue['key']
        if name.startswith(('receipt_risk_', 'receipt_missed_')) or (
                maintenance and name in ('source_maintenance', 'pipeline_failed', 'missed_runs')):
            warnings.append(name)
        else:
            blockers.append(name)
    if exit_code or blockers or (state.get('status') == 'failed' and not maintenance):
        status = 'failed'
    elif maintenance or warnings:
        status = 'deferred_source_maintenance' if maintenance else 'input_readiness_warning'
    else:
        status = 'succeeded'
    return dict(status=status, exit_code=exit_code, blocking_issues=blockers, warning_issues=warnings,
                provider_maintenance=maintenance)
