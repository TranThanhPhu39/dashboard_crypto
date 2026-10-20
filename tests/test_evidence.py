"""Edge guards for UTC boundaries, nominal candles, lagged evaluation and variance states."""
import unittest,tempfile,zipfile
from pathlib import Path
from research_common import np,pd
from src.models.evidence_rv import daily_from_candles,garch_filter,read_archive,qlike,monthly
from src.models.evidence_rotations import geometry,impact,endpoint_ranges

class EvidenceGuards(unittest.TestCase):
    def test_midnight_return_included(self):
        #289 consecutive closes: first is the preceding day's final close.
        t=np.arange(-300,86400,300)+int(pd.Timestamp('2024-01-02').timestamp())
        f=pd.DataFrame({'second':t,'close':100*np.exp(np.arange(289)*.001)})
        d=daily_from_candles(f).loc['2024-01-02'];self.assertTrue(d.complete)
        self.assertAlmostEqual(d.rv5,288*.001**2,places=14);self.assertAlmostEqual(d.rv15,96*.003**2,places=14)
        self.assertAlmostEqual(d.return_daily,.288,places=13)

    def test_missing_interior_is_not_bridged(self):
        t=np.arange(-300,86400,300)+int(pd.Timestamp('2024-01-02').timestamp());f=pd.DataFrame({'second':t,'close':100*np.exp(np.arange(289)*.001)}).drop(70)
        d=daily_from_candles(f).loc['2024-01-02'];self.assertFalse(d.complete);self.assertTrue(pd.isna(d.rv5));self.assertTrue(pd.isna(d.rv15))

    def test_microsecond_and_invalid_close_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'x.zip';start=1735689600000000
            rows=[[start,1,1,1,10,1,start+300000000-1],[start+300000000,1,1,1,11,1,start+600000000-2000]]
            with zipfile.ZipFile(p,'w') as z:z.writestr('x.csv','\n'.join(','.join(map(str,r)) for r in rows))
            f,unit,bad=read_archive(p);self.assertEqual(unit,'microseconds');self.assertEqual(len(f),1);self.assertEqual(len(bad),1);self.assertEqual(f.second.iloc[0],1735689600)

    def test_missing_garch_return_is_latent_expectation(self):
        r=np.array([1.,np.nan,2.,-.5]);omega,alpha,beta=.1,.2,.6;expected=[.8]
        for x in r[:-1]:expected.append(omega+alpha*(x*x if np.isfinite(x) else expected[-1])+beta*expected[-1])
        np.testing.assert_allclose(garch_filter(r,omega,alpha,beta,.8),expected)

    def test_rotation_bounds_can_be_unbounded(self):
        M=np.array([[1.,-2.],[2.,-1.],[1.,1.],[-1.,1.]])
        R,lo,hi=geometry(M);bounds=endpoint_ranges(R,lo,hi,np.array([.2,.5]),len(M))
        self.assertTrue(any(r['unbounded'] for r in bounds))
        for t in np.linspace(lo+1e-5,hi-1e-5,200):
            val=impact(R,t)@np.array([.2,.5])/10
            for r,v in zip(bounds,val):self.assertLessEqual(r['lower_per10bps']-1e-10,v);self.assertGreaterEqual(r['upper_per10bps']+1e-10,v)

    def test_nonpositive_variance_not_floored(self):
        with self.assertRaises(AssertionError):qlike([1.],[0.])

    def test_validation_label_after_first_test_is_purged(self):
        dates=pd.date_range('2021-01-01','2025-01-05');f=pd.DataFrame(index=dates)
        for c in ['rv_lag','rv7','rv30']:f[c]=np.exp(.1*np.sin(np.arange(len(f))/11))
        f['actual']=np.exp(.2*np.cos(np.arange(len(f))/13));f['label_available']=dates+pd.Timedelta(days=8)
        f['split']=np.where(dates<'2023-01-01','train',np.where(dates<'2025-01-01','validation','test'))
        g=monthly(f,'long_own',0,'validation');self.assertLessEqual(g.origin_utc.max()+pd.Timedelta(days=8),pd.Timestamp('2024-12-31'))

if __name__=='__main__':unittest.main()
