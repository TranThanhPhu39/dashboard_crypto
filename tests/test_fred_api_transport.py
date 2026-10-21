"""Raw API lineage, exact vintage/units, normalization and credential guards."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from src.data import github_fred_api as api
from src.automation_runtime import digest


class APITransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder = self.root/'data/raw/evidence_20261019/live/test'
        self.folder.mkdir(parents=True)
        self.payload = dict(realtime_start='2026-10-20', realtime_end='2026-10-20',
            count=3, offset=0, units='lin', output_type=1, observations=[
                dict(date='2026-10-16', realtime_start='2026-10-20', realtime_end='2026-10-20', value='3.95'),
                dict(date='2026-10-19', realtime_start='2026-10-20', realtime_end='2026-10-20', value='4.12'),
                dict(date='2026-10-20', realtime_start='2026-10-20', realtime_end='2026-10-20', value='.')])
        self.params = api.public_parameters('DGS2', '2026-10-01', '2026-10-20', '2026-10-20')
        self.key = 'a'*32

    def capture(self, sid='DGS2', asof='2026-10-20'):
        response = Mock(status_code=200, content=json.dumps(self.payload).encode(), headers={'Date': 'test'})
        with patch('requests.get', return_value=response) as get:
            record = api.api_one(self.folder, sid, '2026-10-01', '2026-10-20', asof,
                                 root=self.root, key=self.key)
        self.assertEqual(get.call_args.kwargs['params']['api_key'], self.key)
        archive = self.root/record['normalizer_code_snapshot']
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(Path(api.__file__).read_bytes())
        return record

    def test_original_raw_bytes_and_derived_view_have_a_verifiable_chain(self):
        record = self.capture()
        self.assertEqual(record['status'], 'ok')
        self.assertEqual((self.root/record['raw_file']).read_bytes(), json.dumps(self.payload).encode())
        self.assertEqual(record['file_role'], 'derived_view_of_archived_raw_api_json')
        self.assertNotIn(self.key, json.dumps(record))
        self.assertNotIn('api_key', record['request_parameters'])
        api.verify_record(record, self.root)
        from src.data.latency_snapshots import alfred_frame
        frame = alfred_frame(self.root/record['file'], 'DGS2', '2026-10-20')
        self.assertEqual(frame.DGS2.tolist(), [3.95, 4.12])
        self.assertAlmostEqual((frame.DGS2.iloc[-1]-frame.DGS2.iloc[-2])*100, 17)

    def test_vix_csv_is_identical_to_raw_api_observations(self):
        record = self.capture(sid='VIXCLS', asof=None)
        api.verify_record(record, self.root)
        self.assertEqual((self.root/record['file']).name, 'VIXCLS_fred.csv')
        self.assertIn(b'2026-10-19,4.12', (self.root/record['file']).read_bytes())

    def test_future_observation_or_wrong_vintage_rejected(self):
        for changed in ['future', 'vintage', 'units', 'pagination']:
            payload = copy.deepcopy(self.payload)
            if changed == 'future':
                payload['observations'][0]['date'] = '2026-10-21'
            elif changed == 'vintage':
                payload['realtime_start'] = '2026-10-21'
            elif changed == 'units':
                payload['units'] = 'pch'
            else:
                payload['count'] = 999
            with self.assertRaises(ValueError, msg=changed):
                api.normalize(payload, self.params, '2026-10-20')

    def test_raw_changes_detected_even_when_view_is_unchanged(self):
        record = self.capture()
        (self.root/record['raw_file']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            api.verify_record(record, self.root)

    def test_rehashed_forged_normalized_view_still_rejected(self):
        record = self.capture(sid='VIXCLS', asof=None)
        (self.root/record['file']).write_bytes(b'observation_date,VIXCLS\n2026-10-19,999\n')
        record['sha256'] = digest(self.root/record['file'])
        with self.assertRaisesRegex(ValueError, 'does not match'):
            api.verify_record(record, self.root)

    def test_transport_error_message_never_persists_the_secret_url(self):
        import requests
        with patch('requests.get', side_effect=requests.Timeout('api_key=' + self.key)):
            record = api.api_one(self.folder, 'DGS2', '2026-10-01', '2026-10-20', '2026-10-20',
                                 root=self.root, key=self.key)
        self.assertEqual(record['status'], 'failed')
        self.assertNotIn(self.key, json.dumps(record))

    def test_provider_echoing_key_is_not_archived(self):
        response = Mock(status_code=400, content=('key=' + self.key).encode(), headers={})
        with patch('requests.get', return_value=response):
            record = api.api_one(self.folder, 'DGS2', '2026-10-01', '2026-10-20', '2026-10-20',
                                 root=self.root, key=self.key)
        self.assertEqual(record['status'], 'failed')
        self.assertNotIn('raw_file', record)
        self.assertFalse(list(self.folder.glob('*_api_response.json')))

    def test_normalized_feature_availability_cannot_precede_receipt(self):
        record = self.capture()
        record['available_at_utc'] = '2000-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError, 'predates'):
            api.verify_record(record, self.root)


if __name__ == '__main__':
    unittest.main()
