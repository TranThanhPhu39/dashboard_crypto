"""UI packaging invariants; no model training or production state mutations."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import sys
import unittest
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.dashboard_design import redesign
from src.dashboard_experience import capture_status, historical_payload, public_status
from tools.repair_dashboard_entrypoints import repair, LEGACY


class ExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT/'dashboard/index.html').read_text()

    def test_refresh_is_idempotent_and_preserves_predictions(self):
        rebuilt = redesign(self.source)
        self.assertEqual(rebuilt, self.source)
        source = json.loads((ROOT/'dashboard/historical_oos_data.json').read_text())
        decoded = historical_payload(rebuilt)
        self.assertEqual(decoded['series'], source['series'])
        self.assertEqual(decoded['folds'], source['folds'])
        app = re.search(r'<script>(.*?)</script>', rebuilt, re.S)[1]
        self.assertIn('/* ORBIT DESIGN START */', app)

    def test_missing_report_entrypoints_redirect_to_real_dashboard(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name in repair(root):
                content = (root/name).read_text()
                self.assertIn('../../../dashboard/index.html#', content)
            self.assertEqual(repair(root), [])

    def test_existing_historical_dashboard_is_never_overwritten(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/next(iter(LEGACY))
            path.parent.mkdir(parents=True)
            original = b'locked historical HTML\r\n'
            path.write_bytes(original)
            repair(root)
            self.assertEqual(path.read_bytes(), original)

    def test_public_status_separates_research_and_future_evaluation(self):
        state = public_status(self.source)
        self.assertEqual(state['research_cutoff'], '2026-10-15')
        self.assertFalse(state['prospective']['performance_claim'])
        self.assertEqual(state['schedule']['capture_refresh_hours'], 4)

    def test_capture_metadata_checks_hash_and_never_exposes_raw_records(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            pointer = root/'outputs/research/evidence_20261019/prospective/latest_capture.json'
            pointer.parent.mkdir(parents=True)
            raw = json.dumps({'capture_started_utc':'2026-10-21T12:00:00Z','capture_finished_utc':'2026-10-21T12:01:00Z','sources':[{'status':'ok','url':'private URL not for export'}]}).encode()
            (root/'capture.json').write_bytes(raw)
            pointer.write_text(json.dumps({'manifest':'capture.json','sha256':hashlib.sha256(raw).hexdigest()}))
            result = capture_status(root)
            self.assertEqual(result['sources_ok'], 1)
            self.assertNotIn('private',json.dumps(result))
            (root/'capture.json').write_text('{}')
            self.assertEqual(capture_status(root)['status'], 'unverified')


if __name__ == '__main__':
    unittest.main()
