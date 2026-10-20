"""Critical deployment guards; synthetic clocks never create forecast records."""
import unittest
from unittest.mock import patch
from src.evaluation.latency_live import clock,choose,envelope,records,immutable
from src.evaluation.latency_common import pd,OUT

class TimingGuards(unittest.TestCase):
    def test_valid_before_origin(self):
        clock(pd.Timestamp('2026-10-21',tz='UTC'),pd.Timestamp('2026-10-19 08:00',tz='UTC'),pd.Timestamp('2026-10-20 09:00',tz='UTC'))
    def test_reject_late_receipt(self):
        with self.assertRaises(AssertionError):clock(pd.Timestamp('2026-10-21',tz='UTC'),pd.Timestamp('2026-10-20 00:01',tz='UTC'),pd.Timestamp('2026-10-20 09:00',tz='UTC'))
    def test_reject_after_outcome_start(self):
        with self.assertRaises(AssertionError):clock(pd.Timestamp('2026-10-21',tz='UTC'),pd.Timestamp('2026-10-19',tz='UTC'),pd.Timestamp('2026-10-21 00:01',tz='UTC'))
    def test_reject_far_future_origin(self):
        with self.assertRaises(AssertionError):clock(pd.Timestamp('2026-10-22',tz='UTC'),pd.Timestamp('2026-10-19',tz='UTC'),pd.Timestamp('2026-10-20 09:00',tz='UTC'))
    def test_reject_nonmidnight(self):
        with self.assertRaises(AssertionError):clock(pd.Timestamp('2026-10-21 01:00',tz='UTC'),pd.Timestamp('2026-10-19',tz='UTC'),pd.Timestamp('2026-10-20 09:00',tz='UTC'))
    def test_reject_naive_time(self):
        with self.assertRaises(AssertionError):clock(pd.Timestamp('2026-10-21'),pd.Timestamp('2026-10-19',tz='UTC'),pd.Timestamp('2026-10-20 09:00',tz='UTC'))
    def test_reject_snapshot_before_information_day_closed(self):
        with self.assertRaises(AssertionError):choose([dict(available_at_utc='2026-10-18T12:00:00Z')],lambda r:True,pd.Timestamp('2026-10-18',tz='UTC'),pd.Timestamp('2026-10-20',tz='UTC'))
    def test_no_market_return_carry_on_weekend(self):
        e=envelope(pd.Timestamp('2026-10-21',tz='UTC'),'btc',records())
        self.assertIn('sp500_log_return_lag1_proxy',e['missing']);self.assertFalse(e['long_eligible'])
        self.assertIn('btc_usd_log_return',e['features'])
    def test_wrong_requested_vintage_is_rejected(self):
        rows=[dict(r,requested_vintage_date='2026-10-16') if r.get('series_id') else r for r in records()]
        e=envelope(pd.Timestamp('2026-10-21',tz='UTC'),'btc',rows)
        self.assertNotIn('broad_usd_pit_change',e['features']);self.assertIn('broad_usd_pit_change',e['missing'])
    def test_missing_crypto_day_never_bridged(self):
        fake=pd.Series(100.,index=pd.date_range('2026-09-18','2026-10-18'));fake.loc['2026-10-01']=float('nan')
        with patch('src.evaluation.latency_live.prices',return_value=fake):
            e=envelope(pd.Timestamp('2026-10-21',tz='UTC'),'btc',records())
        self.assertIn('own_crypto',e['missing']);self.assertNotIn('btc_usd_log_return',e['features'])
    def test_immutable_write_rejects_duplicate(self):
        path=OUT/'unit_immutable_guard.json';self.assertFalse(path.exists())
        try:
            immutable(path,dict(unit_test=True))
            with self.assertRaises(FileExistsError):immutable(path,dict(unit_test=False))
        finally:
            if path.exists():path.unlink()

if __name__=='__main__':unittest.main()
