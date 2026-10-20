"""Reproduce operational guards; no fitting or invented live forecasts."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import research_common
from src.evaluation.release_preservation import install
from src.automation_runtime import atomic_json, now_utc, OUT, CONFIG, read_json, check_immutable

install()
loader=unittest.TestLoader()
suite=unittest.TestSuite([loader.discover(str(ROOT/'tests'),pattern=name) for name in
    ['test_automation.py','test_prospective_operations.py','test_prospective.py','test_release_preservation.py']])
result=unittest.TextTestRunner(verbosity=1).run(suite)
check_immutable(read_json(CONFIG))
atomic_json(OUT/'guard_validation.json',dict(checked_at_utc=now_utc().isoformat(),tests=result.testsRun,
    failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
    immutable_protocol_and_inventory_hashes_verified=True,scope='Temporary fixtures, clock/receipt/lock/retry/preservation guards; not predictive performance'))
raise SystemExit(not result.wasSuccessful())
