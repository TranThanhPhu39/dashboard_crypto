"""Operational edge cases; synthetic inputs stay in temporary test directories."""
from contextlib import contextmanager, ExitStack, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import json
import tempfile
import unittest

from src.evaluation import prospective_operations as op
from src.evaluation.latency_common import pd, np, ROOT


class ProspectiveOperationGuards(unittest.TestCase):
    def setUp(self):
        self.info = pd.Timestamp('2026-10-18', tz='UTC')
        self.cutoff = pd.Timestamp('2026-10-20', tz='UTC')
        self.early = dict(file='btc_coinmetrics.json', available_at_utc='2026-10-19T08:00:00Z')
        self.later = dict(file='btc_coinmetrics.json', available_at_utc='2026-10-19T10:00:00Z', complete=True)

    def test_reproduces_earliest_partial_snapshot_fault(self):
        with patch.object(op.legacy, 'prices', side_effect=lambda row, _: pd.Series(
            100., index=pd.date_range('2026-09-18', '2026-10-18' if row.get('complete') else '2026-10-17'))):
            selected = op.legacy.choose([self.early, self.later], lambda r: True, self.info, self.cutoff)
            self.assertIs(selected, self.early)
            with self.assertRaises(AssertionError):
                op.candidate_check(selected, self.info)
            self.assertIs(op.choose_complete([self.early, self.later], lambda r: True, self.info, self.cutoff), self.later)

    def test_later_complete_after_cutoff_still_rejected(self):
        late = dict(self.later, available_at_utc='2026-10-20T00:00:01Z')
        with patch.object(op, 'candidate_check', side_effect=AssertionError('Partial')):
            with self.assertRaises(AssertionError):
                op.choose_complete([self.early, late], lambda r: True, self.info, self.cutoff)

    def test_snapshot_before_information_close_is_rejected(self):
        record = dict(self.later, available_at_utc='2026-10-18T23:59:59Z')
        with self.assertRaises(AssertionError):
            op.choose_complete([record], lambda r: True, self.info, self.cutoff)

    def test_receipt_exactly_at_cutoff_allowed(self):
        record = dict(self.later, available_at_utc=self.cutoff.isoformat())
        with patch.object(op, 'candidate_check'):
            self.assertIs(op.choose_complete([record], lambda r: True, self.info, self.cutoff), record)

    def test_wrong_requested_vintage_is_rejected(self):
        record = dict(file='fake.zip', series_id='DGS2', requested_vintage_date='2026-10-17')
        with self.assertRaisesRegex(AssertionError, 'Wrong requested vintage'):
            op.candidate_check(record, self.info)

    def test_weekend_market_return_still_not_carried(self):
        with patch.object(op.legacy, 'market_series', return_value=pd.Series([100., 101.], index=pd.to_datetime(['2026-10-15', '2026-10-16']))):
            with self.assertRaisesRegex(AssertionError, 'Exact market return day missing'):
                op.candidate_check(dict(file='sp500_yahoo.json'), self.info)

    def test_missing_interior_crypto_day_is_rejected(self):
        series = pd.Series(100., index=pd.date_range('2026-09-18', '2026-10-18')).drop(pd.Timestamp('2026-10-01'))
        with patch.object(op.legacy, 'prices', return_value=series):
            with self.assertRaises(AssertionError):
                op.candidate_check(self.early, self.info)

    @contextmanager
    def synthetic_runtime(self):
        op.OPS.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='synthetic_guard_', dir=op.OPS) as folder:
            directory = Path(folder)
            live = directory/'live'
            operational = directory/'operational'
            operational.mkdir()
            pd.DataFrame({'synthetic_test_only': []}).to_csv(operational/'benchmark_states.csv', index=False)
            origin = pd.Timestamp.now(tz='UTC').normalize()+pd.Timedelta(days=1)
            protocol = dict(start_utc=origin.isoformat(), end_utc_exclusive=(origin+pd.Timedelta(days=2)).isoformat())
            live.mkdir()
            (live/'protocol.json').write_text(json.dumps(protocol), encoding='utf-8')
            with ExitStack() as stack:
                stack.enter_context(patch.object(op, 'LIVE', live))
                stack.enter_context(patch.object(op, 'OPERATIONAL', operational))
                stack.enter_context(op.bound())
                stack.enter_context(patch.object(op.legacy, 'protocol', return_value=protocol))
                stack.enter_context(patch.object(op.legacy, 'records', return_value=[]))
                stack.enter_context(patch.object(op.legacy, 'frozen', return_value=(pd.DataFrame(), {})))
                stack.enter_context(patch.object(op.legacy, 'envelope', side_effect=lambda d,a,r: dict(
                    synthetic_test_only=True, asset=a, origin_utc=d.isoformat(), features={}, lineage={},
                    long_eligible=True, common_eligible=False, missing={})))
                stack.enter_context(patch.object(op, 'read_committed', side_effect=lambda p,*a: json.loads(p.read_text())))
                yield live, origin

    def test_retry_reuses_commits_without_overwrite(self):
        prediction = dict(variant='synthetic_only', target='return', model='synthetic_only', predicted=0.)
        with self.synthetic_runtime() as (live, origin), patch.object(op, 'emit_asset', return_value=[prediction]) as emit:
            first = op.forecast(origin)
            hashes = {p.name:op.sha(p) for p in (live/'predictions').glob('*.json')}
            second = op.forecast(origin)
            self.assertEqual(first['total_predictions'], 2)
            self.assertEqual(second['total_predictions'], 0)
            self.assertEqual(second['existing_predictions'], 2)
            self.assertEqual(emit.call_count, 2)
            self.assertEqual(hashes, {p.name:op.sha(p) for p in (live/'predictions').glob('*.json')})

    def test_partial_asset_failure_resumes_other_asset(self):
        prediction = dict(variant='synthetic_only', target='return', model='synthetic_only', predicted=0.)
        with self.synthetic_runtime() as (live, origin), patch.object(op, 'emit_asset', side_effect=[[prediction], RuntimeError('synthetic interruption'), [prediction]]) as emit:
            with self.assertRaisesRegex(RuntimeError, 'synthetic interruption'):
                op.forecast(origin)
            bitcoin = live/'predictions'/f'{origin.date()}_btc.json'
            digest = op.sha(bitcoin)
            result = op.forecast(origin)
            self.assertEqual(result['existing_predictions'], 1)
            self.assertEqual(result['total_predictions'], 1)
            self.assertEqual(op.sha(bitcoin), digest)
            self.assertEqual(emit.call_count, 3)

    def test_no_backdated_forecast_even_with_adapter(self):
        with self.synthetic_runtime(), self.assertRaises(AssertionError):
            op.forecast(pd.Timestamp.now(tz='UTC').normalize())

    def test_existing_commit_with_wrong_protocol_rejected(self):
        with self.synthetic_runtime() as (live, origin):
            path = live/'forged_synthetic.json'
            path.write_text(json.dumps(dict(asset='btc', origin_utc=origin.isoformat(),
                target_end_utc=(origin+pd.Timedelta(days=1)).isoformat(),
                logged_at_utc=(origin-pd.Timedelta(hours=1)).isoformat(), protocol_sha256='wrong')), encoding='utf-8')
            # synthetic_runtime mocks the retry loader; call original class-level function saved below.
            with self.assertRaises(AssertionError):
                READ_COMMITTED(path, 'btc', origin, pd.DataFrame())

    def test_failed_capture_can_be_retried_same_day(self):
        with self.synthetic_runtime() as (_, origin):
            folder = op.OPERATIONAL
            manifest = folder/'manifest.json'
            manifest.write_text(json.dumps(dict(capture_started_utc=pd.Timestamp.now(tz='UTC').isoformat(),
                sources=[dict(status='failed')]+[dict(status='ok') for _ in range(16)])), encoding='utf-8')
            (folder/'latest_capture.json').write_text(json.dumps(dict(manifest=manifest.relative_to(ROOT).as_posix(), sha256=op.sha(manifest))), encoding='utf-8')
            self.assertTrue(op.capture_needed())
            manifest.write_text(json.dumps(dict(capture_started_utc=pd.Timestamp.now(tz='UTC').isoformat(),
                sources=[dict(status='ok') for _ in range(17)])), encoding='utf-8')
            (folder/'latest_capture.json').write_text(json.dumps(dict(manifest=manifest.relative_to(ROOT).as_posix(), sha256=op.sha(manifest))), encoding='utf-8')
            self.assertFalse(op.capture_needed())
            self.assertTrue(op.capture_needed(refresh=True))

    def test_evaluation_does_not_score_before_fixed_end(self):
        with self.synthetic_runtime(), patch('research_completion.paired_stat', side_effect=AssertionError('Must not score early')):
            with redirect_stdout(StringIO()):
                op.legacy.evaluate()
            status = json.loads((op.OPERATIONAL/'prospective_evaluation.json').read_text())
            self.assertEqual(status['status'], 'PENDING_FIXED_EVALUATION_WINDOW')
            self.assertFalse(status['performance_claim'])
            self.assertFalse((op.OPERATIONAL/'prospective_benchmark_tests.csv').exists())

    def test_empty_final_window_is_reported_without_inventing_results(self):
        # Exercise the terminal evaluation path with a synthetic expired protocol
        # in a disposable directory; no production clock or protocol is changed.
        with self.synthetic_runtime(), patch.object(op.legacy, 'protocol', return_value=dict(end_utc_exclusive='2020-01-01T00:00:00Z')):
            with redirect_stdout(StringIO()):
                op.legacy.evaluate()
            status = json.loads((op.OPERATIONAL/'prospective_evaluation.json').read_text())
            self.assertEqual(status['observed_prediction_rows'], 0)
            frame = pd.read_csv(op.OPERATIONAL/'prospective_benchmark_tests.csv')
            self.assertTrue(frame.n_pairs.eq(0).all())
            self.assertTrue(frame.pvalue.isna().all())

    def test_adapter_predictions_match_frozen_historical_outputs(self):
        # Replay a previously seen historical row; no live ledger or future score.
        saved = pd.read_csv(op.RESULTS/'latency_20261019/test_predictions.csv', float_precision='round_trip')
        inventory = pd.read_csv(op.RESULTS/'latency_20261019/model_inventory.csv')
        states = pd.read_csv(op.RESULTS/'latency_20261019/benchmark_states.csv')
        for asset in ['btc', 'eth']:
            panel = pd.read_csv(ROOT/f'data/processed/latency_20261019/{asset}_common_usd.csv', float_precision='round_trip')
            row = panel[panel.split.eq('test')].iloc[0]
            origin = pd.Timestamp(row.origin_utc).tz_localize('UTC')
            columns = op.features(asset, 'common_usd')
            envelope = dict(features={c:row[c] for c in columns}, lineage={c:dict(available_at_utc=(origin-pd.Timedelta(days=1)).isoformat()) for c in columns}, long_eligible=True, common_eligible=True)
            with patch.object(op.legacy, 'clock'):
                replay = pd.DataFrame(op.emit_asset(asset, origin, envelope, inventory, states))
            reference = saved[(saved.asset==asset)&saved.date_utc.eq(str(pd.Timestamp(row.date_utc).date()))]
            joined = replay.merge(reference, on=['variant', 'target', 'model'], suffixes=('_replay','_saved'))
            self.assertEqual(len(joined), 40)
            np.testing.assert_allclose(joined.predicted_replay, joined.predicted_saved, rtol=1e-12, atol=1e-15)


READ_COMMITTED = op.read_committed

if __name__ == '__main__':
    unittest.main()
