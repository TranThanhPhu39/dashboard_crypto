"""Migration failure cases: persistence, tampering, missing state, competing hosts."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import github_worker_store as store


class MemoryGitHub:
    def __init__(self):
        self.assets = {}
        self.current = None
        self.blob = None

    def put_asset(self, tag, name, data):
        identity = len(self.assets) + 1
        self.assets[identity] = data
        return dict(id=identity, tag=tag, name=name, sha256=store.digest(data), bytes=len(data))

    def get_asset(self, record, cache=None):
        data = self.assets[record['id']]
        if store.digest(data) != record['sha256']:
            raise ValueError('Encrypted object corrupted')
        return data

    def pointer(self):
        return copy.deepcopy(self.current), self.blob

    def commit_pointer(self, pointer, expected_blob):
        if self.blob != expected_blob:
            raise ValueError('Concurrent pointer change')
        self.current = copy.deepcopy(pointer)
        self.blob = store.digest(store.encoded(pointer))
        return self.blob[:40]


class DurableWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)/'runtime'
        self.root.mkdir()
        self.key = bytes(range(32))
        self.api = MemoryGitHub()
        for name, content in {'data/processed/frozen.csv': b'date,value\n2026-10-15,1\n',
            'models/frozen.joblib': b'frozen model bytes', 'dashboard/index.html': b'<p>old</p>',
            'paper/README.md': b'old report', store.AUTO+'state.json': b'{"status":"old"}'}.items():
            store.atomic(store.safe_path(self.root, name), content)
        files = store.inventory(self.root)
        pack = store.upload_pack(self.api, self.key, files, self.root, 'test', self.root/'.worker-work')
        asset = store.upload_blob(self.api, self.key, store.encoded({'format': store.FORMAT,
            'files': files, 'pack': pack}), 'test', 'base')
        self.config = {'bootstrap': asset}
        catalog = {'format': store.FORMAT, 'generation': 0, 'bootstrap_sha256': asset['sha256'],
                   'files': {}, 'packs': {}}
        catalog_asset = store.upload_blob(self.api, self.key, store.encoded(catalog), 'test', 'catalog')
        self.api.commit_pointer({'generation': 0, 'bootstrap_sha256': asset['sha256'],
                                 'catalog': catalog_asset, 'owner': 'test'}, None)

    def restore(self, target=None):
        return store.restore(self.api, self.key, self.config, target or self.root)

    def test_clean_runner_recovers_receipts_forecast_and_last_status(self):
        context = self.restore()
        for name, data in {store.RAW+'capture/source.csv': b'actual receipt',
                           store.LIVE+'predictions/2026-10-23_btc.json': b'ex ante forecast',
                           store.AUTO+'state.json': b'{"status":"succeeded"}',
                           'dashboard/index.html': b'<p>new</p>'}.items():
            store.atomic(store.safe_path(self.root, name), data)
        result = store.persist(self.api, self.key, self.config, context, self.root)
        fresh = Path(self.temporary.name)/'fresh-runner'
        restored = self.restore(fresh)
        self.assertEqual(result['generation'], 1)
        self.assertEqual(restored['pointer']['generation'], 1)
        self.assertEqual((fresh/'dashboard/index.html').read_bytes(), b'<p>new</p>')
        self.assertEqual((fresh/(store.LIVE+'predictions/2026-10-23_btc.json')).read_bytes(), b'ex ante forecast')
        self.assertEqual((fresh/(store.RAW+'capture/source.csv')).read_bytes(), b'actual receipt')
        context = restored
        store.atomic(fresh/(store.AUTO+'state.json'), b'{"status":"next-run"}')
        store.persist(self.api, self.key, self.config, context, fresh)
        final = Path(self.temporary.name)/'third-runner'
        self.restore(final)
        self.assertEqual((final/(store.AUTO+'state.json')).read_bytes(), b'{"status":"next-run"}')
        self.assertEqual((final/(store.LIVE+'predictions/2026-10-23_btc.json')).read_bytes(), b'ex ante forecast')

    def test_model_edits_cannot_be_committed(self):
        context = self.restore()
        (self.root/'models/frozen.joblib').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            store.persist(self.api, self.key, self.config, context, self.root)
        self.assertEqual(self.api.current['generation'], 0)

    def test_report_reader_stays_in_git_while_runtime_receipts_are_persisted(self):
        context = self.restore()
        reader = 'outputs/research/evidence_20261019/report_view.html'
        store.atomic(self.root/reader, b'<p>Versioned presentation, not worker state</p>')
        receipt = store.RAW+'capture/source.csv'
        forecast = store.LIVE+'predictions/2026-10-23_btc.json'
        store.atomic(self.root/receipt, b'original receipt')
        store.atomic(self.root/forecast, b'ex ante forecast')
        result = store.persist(self.api, self.key, self.config, context, self.root)
        self.assertEqual(result['generation'], 1)
        self.assertNotIn(reader, store.inventory(self.root))
        self.assertEqual((self.root/reader).read_bytes(), b'<p>Versioned presentation, not worker state</p>')
        fresh = Path(self.temporary.name)/'runner-with-reader-fix'
        restored = self.restore(fresh)
        self.assertNotIn(reader, restored['catalog']['files'])
        self.assertFalse((fresh/reader).exists())
        self.assertEqual((fresh/receipt).read_bytes(), b'original receipt')
        self.assertEqual((fresh/forecast).read_bytes(), b'ex ante forecast')

    def test_unexpected_report_beside_reader_is_still_rejected(self):
        context = self.restore()
        name = 'outputs/research/evidence_20261019/unexpected_report.html'
        store.atomic(self.root/name, b'not allowlisted')
        with self.assertRaisesRegex(ValueError, 'Unexpected new runtime file'):
            store.persist(self.api, self.key, self.config, context, self.root)
        self.assertEqual(self.api.current['generation'], 0)

    def test_loss_of_existing_files_cannot_reset_ledger(self):
        context = self.restore()
        (self.root/'models/frozen.joblib').unlink()
        with self.assertRaisesRegex(ValueError, 'lost'):
            store.persist(self.api, self.key, self.config, context, self.root)

    def test_raw_receipt_cannot_be_edited_on_next_run(self):
        context = self.restore()
        path = self.root/(store.RAW+'real/source.csv')
        store.atomic(path, b'original')
        store.persist(self.api, self.key, self.config, context, self.root)
        context = self.restore()
        path.write_bytes(b'revised')
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            store.persist(self.api, self.key, self.config, context, self.root)

    def test_forecast_cannot_be_replaced_after_commit(self):
        before = {store.LIVE+'predictions/a.json': 'a'*64}
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            store.changes(before, {}, {next(iter(before)): 'b'*64})

    def test_two_hosts_cannot_overwrite_each_other(self):
        context = self.restore()
        self.api.commit_pointer({**self.api.current, 'generation': 10}, self.api.blob)
        with self.assertRaisesRegex(ValueError, 'another host'):
            store.persist(self.api, self.key, self.config, context, self.root)

    def test_missing_pointer_never_falls_back_to_bootstrap(self):
        self.api.current, self.api.blob = None, None
        with self.assertRaisesRegex(ValueError, 'Missing'):
            self.restore()

    def test_tampered_ciphertext_rejected(self):
        cipher = store.encrypt(b'receipts', self.key)
        self.assertEqual(store.decrypt(cipher, self.key), b'receipts')
        from cryptography.exceptions import InvalidTag
        with self.assertRaises(InvalidTag):
            store.decrypt(cipher[:-1] + bytes([cipher[-1] ^ 1]), self.key)
        with self.assertRaises(InvalidTag):
            store.decrypt(cipher, bytes([1])*32)

    def test_pack_checksum_rejected_before_writes(self):
        base = store.read_descriptor(self.api, self.key, self.config['bootstrap'])
        base['pack']['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'checksum'):
            store.restore_pack(self.api, self.key, base['pack'], self.root, base['files'], self.root/'.worker-work')

    def test_traversal_and_code_overwrite_disallowed(self):
        for name in ['../secret', '/etc/passwd', 'data/../../.git/config', 'data\\..\\secret',
                     'C:/Users/Admin/key', 'src/models/latency.py', '.env', 'data/./secret']:
            self.assertFalse(store.runtime_name(name), name)

    def test_hosted_status_does_not_require_the_personal_computer(self):
        from src import automation_runtime as auto
        folder = self.root/store.AUTO
        auto.atomic_json(folder/'installation.json', {'registered': True, 'provider': 'github-actions'})
        auto.atomic_json(folder/'scheduler_status.json', {'provider': 'github-actions', 'verified': True,
            'tasks': [{'role': role, 'enabled': True, 'action_matches': True} for role in ['pipeline', 'monitor']]})
        summary = auto.automation_summary(folder)
        self.assertTrue(summary['installed'])
        self.assertIn('không cần bật máy cá nhân', auto.automation_description(summary))
        auto.write_health_page({'checked_at_utc': '2026-10-21T01:00:00+00:00', 'status': 'healthy', 'issues': []},
                               {'status': 'succeeded'}, folder)
        page = (folder/'health.html').read_text(encoding='utf-8')
        self.assertIn('không cần bật máy cá nhân', page)
        self.assertNotIn('Máy cần bật', page)
        auto.atomic_json(folder/'scheduler_status.json', {'provider': 'github-actions', 'verified': False, 'tasks': []})
        self.assertFalse(auto.automation_summary(folder)['installed'])

    def test_original_stop_timestamp_ends_installation_claim(self):
        from src import automation_runtime as auto
        folder = self.root/store.AUTO
        auto.atomic_json(folder/'installation.json', {'registered': True})
        auto.atomic_json(folder/'scheduler_status.json', {'provider': 'github-actions', 'verified': True,
            'tasks': [{'role': role, 'enabled': True, 'action_matches': True} for role in ['pipeline', 'monitor']]})
        auto.atomic_json(folder/'state.json', {'status': 'finished_schedule'})
        summary = auto.automation_summary(folder)
        self.assertFalse(summary['installed'])
        self.assertIn('kết thúc', auto.automation_description(summary))

    def test_local_mirror_cannot_start_a_second_writer(self):
        from src import automation_runtime as auto
        folder=self.root/store.AUTO
        auto.atomic_json(folder/'installation.json', {'provider':'github-actions'})
        before=(folder/'state.json').read_bytes()
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}), patch.object(auto,'OUT',folder):
            with self.assertRaises(auto.HostedAuthorityError):
                auto.run_pipeline()
        self.assertEqual((folder/'state.json').read_bytes(),before)
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}):
            auto.assert_writer_allowed(folder)


if __name__ == '__main__':
    unittest.main()
