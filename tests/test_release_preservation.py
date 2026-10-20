"""Exact operational exemptions never weaken empirical artifact checks."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from src.evaluation.release_preservation import sha,verify_mapping,historical_path,install,ROOT,validate_policy

class PreservationTests(unittest.TestCase):
    def fixture(self,root):
        (root/'live').mkdir();(root/'archive').mkdir();(root/'models').mkdir()
        live=root/'live/status.json';old=root/'archive/status.json';model=root/'models/fit.bin'
        live.write_bytes(b'original');old.write_bytes(b'original');model.write_bytes(b'frozen model')
        mapping={'paths':{'live/status.json':{'original_sha256':sha(old),'archive':'archive/status.json'}}}
        expected={'live/status.json':sha(old),'models/fit.bin':sha(model)}
        return mapping,expected

    def test_realistic_status_update_accepted_and_original_bytes_resolved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);migration,expected=self.fixture(root)
            (root/'live/status.json').write_bytes(b'updated receipt and attempts')
            self.assertEqual(verify_mapping(expected,root,migration),2)
            self.assertEqual(historical_path('live/status.json',expected['live/status.json'],root,migration).read_bytes(),b'original')

    def test_model_change_still_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);migration,expected=self.fixture(root)
            (root/'models/fit.bin').write_bytes(b'changed')
            with self.assertRaisesRegex(AssertionError,'Immutable file changed'):verify_mapping(expected,root,migration)

    def test_archive_tampering_rejected_even_if_live_matches_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);migration,expected=self.fixture(root)
            (root/'archive/status.json').write_bytes(b'changed')
            with self.assertRaisesRegex(AssertionError,'archive damaged'):verify_mapping(expected,root,migration)

    def test_missing_live_status_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);migration,expected=self.fixture(root)
            (root/'live/status.json').unlink()
            with self.assertRaisesRegex(AssertionError,'live file missing'):verify_mapping(expected,root,migration)

    def test_expected_old_hash_cannot_be_rebased(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);migration,expected=self.fixture(root)
            expected['live/status.json']='0'*64
            with self.assertRaisesRegex(AssertionError,'differs from expected lock'):verify_mapping(expected,root,migration)

    def test_outside_repository_path_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(AssertionError,'outside repository'):historical_path('../escape','0'*64,Path(folder),{})

    def test_adapter_preserves_modeling_functions_and_is_idempotent(self):
        from src.evaluation import pit_nested_common as common
        before={n:getattr(common,n) for n in ['fit_cutoff','training','inner_splits','read_panel']}
        install();checker=common.check_protected;install()
        self.assertIs(common.check_protected,checker)
        for n,obj in before.items():self.assertIs(getattr(common,n),obj)

    def test_editing_migration_cannot_exempt_an_unlisted_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cfg={'mutable_operational_paths':['live/status.json'],'maintained_paths':[]}
            obj={'paths':{'models/fit.bin':{}},'archive_sha256':{}}
            with self.assertRaisesRegex(AssertionError,'expand exact allowlist'):validate_policy(obj,cfg,root,root/'release')

if __name__=='__main__':unittest.main()
