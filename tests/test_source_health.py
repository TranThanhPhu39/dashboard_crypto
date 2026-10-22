"""Regression for the archived HTTP-200 FRED maintenance incident."""
from contextlib import ExitStack, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src import automation_runtime as auto
from src.source_health import capture_status, assess, INCOMPLETE_CAPTURE
from src.data.github_fred_api import ENDPOINT
from tools.run_github_worker import report_operation

MAINTENANCE = b'<html><title>Site Maintenance | St. Louis Fed</title>undergoing proactive maintenance</html>'


def fixture(root):
    folder=root/'data/raw/evidence_20261019/live/test'
    folder.mkdir(parents=True)
    rows=[]
    for i in range(13):
        raw=folder/f'source_{i}.json';raw.write_bytes(MAINTENANCE)
        rows.append(dict(status='failed',series_id=f'test_{i}',url=ENDPOINT,http_status=200,
            raw_file=raw.relative_to(root).as_posix(),raw_sha256=auto.digest(raw),raw_bytes=len(MAINTENANCE),
            error='JSONDecodeError; previous archived transport message'))
    rows.extend(dict(status='ok',file=f'public_{i}.json') for i in range(4))
    manifest=folder/'manifest.json'
    def save():
        auto.atomic_json(manifest,dict(capture_started_utc='2026-10-22T01:36:33+00:00',sources=rows))
        auto.atomic_json(root/'outputs/research/evidence_20261019/prospective/latest_capture.json',
            dict(manifest=manifest.relative_to(root).as_posix(),sha256=auto.digest(manifest)))
    save()
    return rows,save


class SourceHealthTests(unittest.TestCase):
    def test_old_maintenance_receipts_are_recognized_without_rewriting_them(self):
        with TemporaryDirectory() as d:
            root=Path(d);fixture(root)
            before={p:auto.digest(p) for p in root.rglob('*.json')}
            state=capture_status(root)
            self.assertTrue(state['maintenance_only']);self.assertEqual(state['sources_ok'],4)
            self.assertEqual(before,{p:auto.digest(p) for p in before})

    def test_metadata_claim_alone_cannot_downgrade_an_error(self):
        with TemporaryDirectory() as d:
            root=Path(d);rows,save=fixture(root)
            raw=root/rows[0]['raw_file'];raw.write_bytes(b'{invalid JSON}')
            rows[0].update(error_code='PROVIDER_MAINTENANCE',raw_sha256=auto.digest(raw));save()
            self.assertFalse(capture_status(root)['maintenance_only'])

    def test_unrelated_source_failure_stays_a_failure(self):
        with TemporaryDirectory() as d:
            root=Path(d);rows,save=fixture(root)
            rows[-1]['status']='failed';save()
            self.assertFalse(capture_status(root)['maintenance_only'])

    def test_incomplete_manifest_cannot_claim_maintenance_only(self):
        with TemporaryDirectory() as d:
            root=Path(d);rows,save=fixture(root);rows.pop();save()
            self.assertFalse(capture_status(root)['maintenance_only'])

    def test_raw_tampering_is_not_a_provider_warning(self):
        with TemporaryDirectory() as d:
            root=Path(d);rows,_=fixture(root)
            (root/rows[0]['raw_file']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'integrity'):
                capture_status(root)

    def test_monitor_does_not_repeat_a_false_code_failure_for_known_maintenance(self):
        state=dict(status='failed',error=INCOMPLETE_CAPTURE)
        health=dict(issues=[dict(key='pipeline_failed'),dict(key='missed_runs')])
        result=assess(state,health,dict(maintenance_only=True))
        self.assertEqual(result['status'],'deferred_source_maintenance')
        self.assertEqual(state['status'],'failed')

    def test_scheduler_or_code_errors_still_fail_during_maintenance(self):
        state=dict(status='deferred_source_maintenance')
        for name in ['scheduler_unavailable','pipeline_hung','unknown_error']:
            self.assertEqual(assess(state,dict(issues=[dict(key=name)]),dict(maintenance_only=True))['status'],'failed')
        self.assertEqual(assess(dict(status='failed',error='Subprocess exit 1'),dict(issues=[]),dict(maintenance_only=True))['status'],'failed')
        self.assertEqual(assess(state,dict(issues=[]),dict(maintenance_only=True),1)['status'],'failed')

    def test_readiness_warning_does_not_claim_a_forecast_or_complete_capture(self):
        result=assess(dict(status='succeeded'),dict(issues=[dict(key='receipt_risk_2026-10-23')]),dict(maintenance_only=False))
        self.assertEqual(result['status'],'input_readiness_warning')

    def test_deferred_capture_retains_last_success_and_forecasts_then_recovers(self):
        with TemporaryDirectory() as d,ExitStack() as stack:
            root=Path(d);fixture(root);out=root/'outputs/automation_20261020'
            config=root/'config.json';cfg={**auto.read_json(auto.CONFIG),'immutable_inputs':{}}
            auto.atomic_json(config,cfg)
            auto.atomic_json(out/'state.json',dict(last_success_utc='2026-10-21T13:52:00+00:00'))
            auto.atomic_json(root/'outputs/research/evidence_20261019/prospective/prospective_status.json',
                dict(total_predictions=0,existing_predictions=80,attempts=[dict(status='ALREADY_COMMITTED')]))
            forecast=root/'data/prospective/evidence_20261019/predictions/untouched.json'
            auto.atomic_json(forecast,dict(predictions=['synthetic fixture only']))
            original=forecast.read_bytes()
            for name,value in [('ROOT',root),('OUT',out),('CONFIG',config)]:stack.enter_context(patch.object(auto,name,value))
            stack.enter_context(patch.object(auto,'refresh_scheduler_status'))
            stack.enter_context(patch.object(auto,'needs_refresh',return_value=True))
            stack.enter_context(patch.object(auto,'monitor'))
            sleep=stack.enter_context(patch.object(auto.time,'sleep'))
            child=stack.enter_context(patch.object(auto,'run_child'))
            complete=stack.enter_context(patch.object(auto,'capture_complete',return_value=False))
            self.assertEqual(auto.run_pipeline(),0)
            state=auto.read_json(out/'state.json')
            self.assertEqual(state['status'],'deferred_source_maintenance')
            self.assertEqual(state['last_success_utc'],'2026-10-21T13:52:00+00:00')
            self.assertEqual(state['sources_ok'],4);self.assertEqual(state['forecasts_existing'],80)
            sleep.assert_not_called();self.assertEqual(child.call_count,2)
            self.assertEqual(forecast.read_bytes(),original)
            complete.return_value=True
            self.assertEqual(auto.run_pipeline(),0)
            state=auto.read_json(out/'state.json')
            self.assertEqual(state['status'],'succeeded');self.assertEqual(state['sources_ok'],17)
            self.assertEqual(forecast.read_bytes(),original)

    def test_actions_diagnostic_redacts_keys_and_does_not_edit_forecasts(self):
        with TemporaryDirectory() as d:
            root=Path(d);fixture(root);folder=root/'outputs/automation_20261020';secret='c'*32
            auto.atomic_json(folder/'state.json',dict(status='failed',error='api_key='+secret))
            auto.atomic_json(folder/'health.json',dict(issues=[dict(key='pipeline_failed')]))
            log=StringIO()
            with patch.dict(os.environ,{'FRED_API_KEY':secret,'GITHUB_STEP_SUMMARY':''}),redirect_stdout(log):
                report=report_operation('run',1,root)
            self.assertNotIn(secret,log.getvalue())
            self.assertNotIn(secret,json.dumps(report))
            self.assertEqual(report['status'],'failed');self.assertFalse(report['performance_evaluated'])


if __name__=='__main__':unittest.main()
