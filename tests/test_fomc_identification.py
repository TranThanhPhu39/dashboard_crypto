"""Numerical guards for generated shocks and exact minute-window extraction."""
import unittest
from src.models.fomc_identification import median_rotation
from research_fomc_comparison import extract
from research_common import np,pd

class IdentificationGuards(unittest.TestCase):
    def test_rotation_reconstructs_inputs_and_restrictions(self):
        M=np.random.default_rng(2026).normal(size=(80,2));M[:,1]+=M[:,0]*.6
        for w in [.1,.5,.9]:
            U,C,_=median_rotation(M,w)
            self.assertTrue(np.allclose(U@C,M));self.assertTrue(np.allclose(U.sum(axis=1),M[:,0]))
            self.assertLess(C[0,1],0);self.assertGreater(C[1,1],0)
            self.assertLess(abs((U.T@U)[0,1]),1e-10)
    def test_missing_input_not_imputed_as_zero_shock(self):
        M=np.random.default_rng(7).normal(size=(30,2));M[3,1]=np.nan
        U,_,_=median_rotation(M);self.assertTrue(np.isnan(U[3]).all())
    def test_rank_deficiency_rejected(self):
        with self.assertRaises(AssertionError):median_rotation(np.ones((20,2)))
    def test_exact_boundary_and_missing_interior_candle(self):
        t=pd.Timestamp('2024-06-12T18:00:00Z');first=int(t.timestamp())-11*60
        idx=list(range(first,first+31*60,60));c=pd.DataFrame({'close':np.arange(31)+100.},index=idx)
        result=extract(c,t,-10,20);self.assertTrue(result['complete']);self.assertAlmostEqual(result['return_pct'],100*np.log(130/100))
        result=extract(c.drop(index=idx[12]),t,-10,20);self.assertFalse(result['complete']);self.assertTrue(result['endpoints'])
    def test_eastern_dst_conversion(self):
        winter=pd.Timestamp('2024-01-31 14:00').tz_localize('America/New_York').tz_convert('UTC')
        summer=pd.Timestamp('2024-06-12 14:00').tz_localize('America/New_York').tz_convert('UTC')
        self.assertEqual(winter.hour,19);self.assertEqual(summer.hour,18)

if __name__=='__main__':unittest.main()
