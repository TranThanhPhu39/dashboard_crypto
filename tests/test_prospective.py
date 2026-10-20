"""Test genuine ex-ante timing guards without writing invented forecast records."""
import unittest
from src.evaluation.prospective import validate_clock
from src.utils.project import pd

class ProspectiveTiming(unittest.TestCase):
    def test_valid_future_origin_and_old_information(self):
        validate_clock(pd.Timestamp('2026-10-20',tz='UTC'),pd.Timestamp('2026-10-19',tz='UTC'),pd.Timestamp('2026-10-19 12:00',tz='UTC'))
    def test_reject_after_origin(self):
        with self.assertRaises(AssertionError):validate_clock(pd.Timestamp('2026-10-20',tz='UTC'),pd.Timestamp('2026-10-19',tz='UTC'),pd.Timestamp('2026-10-20 00:01',tz='UTC'))
    def test_reject_insufficient_buffer(self):
        with self.assertRaises(AssertionError):validate_clock(pd.Timestamp('2026-10-20',tz='UTC'),pd.Timestamp('2026-10-19 02:00',tz='UTC'),pd.Timestamp('2026-10-19 12:00',tz='UTC'))
    def test_reject_non_UTC_day_start(self):
        with self.assertRaises(AssertionError):validate_clock(pd.Timestamp('2026-10-20 01:00',tz='UTC'),pd.Timestamp('2026-10-19',tz='UTC'),pd.Timestamp('2026-10-19 12:00',tz='UTC'))
    def test_reject_unavailable_future_information(self):
        with self.assertRaises(AssertionError):validate_clock(pd.Timestamp('2026-10-21',tz='UTC'),pd.Timestamp('2026-10-20',tz='UTC'),pd.Timestamp('2026-10-19 23:59',tz='UTC'))

if __name__=='__main__':unittest.main()
