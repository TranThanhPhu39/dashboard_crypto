"""Operational guards; all synthetic state stays in temporary directories."""
from contextlib import nullcontext, ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import hashlib
import json
import unittest

from src import automation_runtime as auto


class AutomationGuards(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,21,22,30,tzinfo=timezone.utc)
        self.cfg=auto.read_json(auto.CONFIG)
        self.install=dict(installed_at_utc=(self.now-timedelta(hours=1)).isoformat())
        self.scheduler=dict(verified=True,tasks=[dict(role=role,enabled=True,action_matches=True,last_task_result=0) for role in ['pipeline','monitor']])
        self.state=dict(status='succeeded',last_success_utc=self.now.isoformat(),forecasts_logged=0)

    def test_ineligible_origin_is_not_a_software_failure(self):
        row=dict(origin_utc='2026-10-22T00:00:00Z',receipt_cutoff_utc='2026-10-21T00:00:00Z',
                 market_day_is_weekend='True',long_features_ready_from_archived_receipts='False',common_features_ready_from_archived_receipts='False')
        self.assertEqual(auto.health_issues(self.now,self.cfg,self.install,self.scheduler,self.state,[row]),[])

    def test_stale_success_detects_missed_runs(self):
        self.state['last_success_utc']=(self.now-timedelta(hours=3)).isoformat()
        keys={row['key'] for row in auto.health_issues(self.now,self.cfg,self.install,self.scheduler,self.state)}
        self.assertIn('missed_runs',keys)

    def test_installation_has_a_startup_grace_period(self):
        self.assertEqual(auto.health_issues(self.now,self.cfg,self.install,self.scheduler,{}),[])

    def test_disabled_or_tampered_task_is_detected(self):
        self.scheduler['tasks'][0]['action_matches']=False
        self.assertIn('scheduler_unavailable',[r['key'] for r in auto.health_issues(self.now,self.cfg,self.install,self.scheduler,self.state)])

    def test_monitor_failure_is_visible_to_pipeline_health(self):
        self.scheduler['tasks'][1]['last_task_result']=1
        self.assertIn('monitor_task_failed',[r['key'] for r in auto.health_issues(self.now,self.cfg,self.install,self.scheduler,self.state)])

    def test_cutoff_risk_then_missed_receipt_does_not_backfill(self):
        self.install['installed_at_utc']='2026-10-20T08:00:00Z'
        row=dict(origin_utc='2026-10-23T00:00:00Z',receipt_cutoff_utc='2026-10-22T00:00:00Z',market_day_is_weekend='False',
                 long_features_ready_from_archived_receipts='False',common_features_ready_from_archived_receipts='False')
        issues=auto.health_issues(self.now,self.cfg,self.install,self.scheduler,self.state,[row])
        self.assertEqual([r['key'] for r in issues],['receipt_risk_2026-10-23'])
        later=self.now+timedelta(hours=2)
        self.state['last_success_utc']=later.isoformat()
        self.assertEqual([r['key'] for r in auto.health_issues(later,self.cfg,self.install,self.scheduler,self.state,[row])],['receipt_missed_2026-10-23'])
        row['long_features_ready_from_archived_receipts']='True';row['common_features_ready_from_archived_receipts']='True'
        self.assertEqual(auto.health_issues(later,self.cfg,self.install,self.scheduler,self.state,[row]),[])

    def test_no_retroactive_warning_for_windows_before_install(self):
        row=dict(origin_utc='2026-10-22T00:00:00Z',receipt_cutoff_utc='2026-10-21T00:00:00Z',market_day_is_weekend='False',
                 long_features_ready_from_archived_receipts='False',common_features_ready_from_archived_receipts='False')
        self.assertEqual(auto.health_issues(self.now,self.cfg,self.install,self.scheduler,self.state,[row]),[])

    def test_hung_running_process_is_detected(self):
        self.state.update(status='running',started_at_utc=(self.now-timedelta(minutes=26)).isoformat())
        self.assertIn('pipeline_hung',[r['key'] for r in auto.health_issues(self.now,self.cfg,self.install,self.scheduler,self.state)])

    def test_process_lock_rejects_overlap_and_releases_on_error(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'lock'
            with self.assertRaises(ValueError):
                with auto.process_lock(path):
                    with self.assertRaises(auto.AlreadyRunningError):
                        with auto.process_lock(path):
                            self.fail('Overlapping mutation was allowed')
                    raise ValueError('Simulated worker failure')
            with auto.process_lock(path):
                pass

    def test_model_protocol_hash_change_is_rejected(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'protocol.json';path.write_bytes(b'original')
            cfg=dict(immutable_inputs={'protocol.json':hashlib.sha256(b'original').hexdigest()})
            auto.check_immutable(cfg,Path(folder))
            path.write_bytes(b'changed')
            with self.assertRaises(AssertionError):
                auto.check_immutable(cfg,Path(folder))

    def test_capture_refresh_and_integrity_guards(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);manifest=root/'capture.json'
            payload=dict(capture_started_utc=(self.now-timedelta(hours=1)).isoformat(),sources=[dict(status='ok') for _ in range(17)])
            pointer=root/'outputs/research/evidence_20261019/prospective/latest_capture.json'
            def save():
                auto.atomic_json(manifest,payload)
                auto.atomic_json(pointer,dict(manifest='capture.json',sha256=auto.digest(manifest)))
            save();self.assertFalse(auto.needs_refresh(self.now,self.cfg,root))
            payload['capture_started_utc']=(self.now-timedelta(hours=4)).isoformat()
            save();self.assertTrue(auto.needs_refresh(self.now,self.cfg,root))
            payload['capture_started_utc']=self.now.isoformat();payload['sources'][0]['status']='failed'
            save();self.assertTrue(auto.needs_refresh(self.now,self.cfg,root))
            manifest.write_text('{}')
            with self.assertRaises(AssertionError):auto.needs_refresh(self.now,self.cfg,root)

    def test_notification_deduplication_and_recovery(self):
        with TemporaryDirectory() as folder:
            sender=Mock(return_value=dict(submitted=True))
            issues=[dict(key='missed_runs',message='Test-only synthetic missed heartbeat')]
            auto.send_health_notifications(issues,self.cfg,{},folder=folder,sender=sender,now=self.now)
            auto.send_health_notifications(issues,self.cfg,{},folder=folder,sender=sender,now=self.now+timedelta(minutes=1))
            self.assertEqual(sender.call_count,1)
            auto.send_health_notifications([],self.cfg,{},folder=folder,sender=sender,now=self.now+timedelta(minutes=2))
            self.assertEqual(sender.call_count,2)

    def test_failed_notification_submission_is_retried(self):
        with TemporaryDirectory() as folder:
            sender=Mock(return_value=dict(submitted=False))
            issue=[dict(key='pipeline_failed',message='Test-only failure')]
            for seconds in [0,60]:auto.send_health_notifications(issue,self.cfg,{},folder=folder,sender=sender,now=self.now+timedelta(seconds=seconds))
            self.assertEqual(sender.call_count,2)

    def test_installation_receipt_alone_cannot_claim_scheduler_enabled(self):
        with TemporaryDirectory() as folder:
            auto.atomic_json(Path(folder)/'installation.json',dict(registered=True))
            self.assertFalse(auto.automation_summary(folder)['installed'])
            auto.atomic_json(Path(folder)/'scheduler_status.json',self.scheduler)
            self.assertTrue(auto.automation_summary(folder)['installed'])

    def test_corrupt_json_is_not_silently_treated_as_success(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'state.json';path.write_text('{')
            with self.assertRaises(json.JSONDecodeError):auto.read_json(path,{})

    def test_last_allowed_origin_and_label_only_transition(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);protocol=dict(start_utc='2026-10-20T00:00:00Z',end_utc_exclusive='2027-10-20T00:00:00Z')
            auto.atomic_json(root/'protocol.json',protocol)
            op=Mock();op.LIVE=root;op.OPS=root/'ops';op.bound.side_effect=lambda:nullcontext();op.capture_needed.return_value=True
            original=(root/'protocol.json').read_bytes()
            auto.operate_frozen(op,at=datetime(2027,10,18,12,tzinfo=timezone.utc))
            op.run.assert_called_once()
            op.reset_mock()
            auto.operate_frozen(op,at=datetime(2027,10,19,12,tzinfo=timezone.utc))
            op.run.assert_not_called();op.legacy.labels.assert_called_once();op.legacy.evaluate.assert_called_once()
            self.assertEqual((root/'protocol.json').read_bytes(),original)
            self.assertEqual(auto.read_json(op.OPS/'last_run.json')['result']['total_predictions'],0)

    def exercise_retry(self, fail_forever=False):
        with TemporaryDirectory() as folder,ExitStack() as stack:
            root=Path(folder);out=root/'outputs/automation_20261020';config=root/'config.json'
            cfg={**self.cfg,'attempts':2,'immutable_inputs':{}}
            auto.atomic_json(config,cfg)
            auto.atomic_json(out/'state.json',dict(last_success_utc='2026-10-20T01:00:00+00:00'))
            auto.atomic_json(root/'outputs/research/evidence_20261019/prospective/prospective_status.json',dict(total_predictions=0,attempts=[dict(status='INELIGIBLE_INPUTS')]))
            for name,value in [('ROOT',root),('OUT',out),('CONFIG',config)]:stack.enter_context(patch.object(auto,name,value))
            stack.enter_context(patch.object(auto,'refresh_scheduler_status'))
            stack.enter_context(patch.object(auto,'needs_refresh',return_value=False))
            stack.enter_context(patch.object(auto,'monitor'))
            sleep=stack.enter_context(patch.object(auto.time,'sleep'))
            child=stack.enter_context(patch.object(auto,'run_child',side_effect=RuntimeError('Synthetic subprocess failure') if fail_forever else None))
            stack.enter_context(patch.object(auto,'capture_complete',side_effect=[False,True]))
            result=auto.run_pipeline();state=auto.read_json(out/'state.json')
            self.assertEqual(sleep.call_count,1)
            if fail_forever:
                self.assertEqual(result,1);self.assertEqual(state['status'],'failed')
                self.assertEqual(state['last_success_utc'],'2026-10-20T01:00:00+00:00')
            else:
                self.assertEqual(result,0);self.assertEqual(state['status'],'succeeded')
                self.assertEqual(state['forecasts_logged'],0);self.assertEqual(child.call_count,3)

    def test_partial_sources_are_retried_without_changing_protocol(self):
        self.exercise_retry()

    def test_final_failure_is_not_recorded_as_success(self):
        self.exercise_retry(fail_forever=True)


if __name__=='__main__':unittest.main()
