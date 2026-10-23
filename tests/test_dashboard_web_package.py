"""Web transport round-trip, boundaries and corruption guards."""
from pathlib import Path
import unittest
from tools.dashboard_web_package import package_dashboard,unpack_program,SCRIPT

ROOT=Path(__file__).resolve().parents[1]


class WebPackageTests(unittest.TestCase):
    def test_exact_program_and_predictions_round_trip(self):
        source=(ROOT/'dashboard/index.html').read_bytes()
        package=package_dashboard(source)
        self.assertEqual(unpack_program(package['dashboard/index.html'],package),SCRIPT.search(source.decode('utf-8'))[1])
        self.assertEqual(len(package),2)
        self.assertLess(len(package['dashboard/index.html']),len(source)//4)
        self.assertTrue(all(name.startswith('dashboard/') for name in package))

    def test_corrupt_lazy_payload_cannot_recover_original(self):
        source=(ROOT/'dashboard/index.html').read_bytes()
        package=package_dashboard(source)
        name=next(name for name in package if name.endswith('.bin'))
        package[name]=b'corrupted'
        self.assertNotEqual(unpack_program(package['dashboard/index.html'],package),SCRIPT.search(source.decode('utf-8'))[1])

    def test_duplicate_program_is_rejected(self):
        with self.assertRaises(ValueError):
            package_dashboard(b'<script>one</script><script>two</script>')


if __name__=='__main__':
    unittest.main()
