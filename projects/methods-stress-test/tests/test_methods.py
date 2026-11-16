import sys
import unittest
from pathlib import Path
import numpy as np
from scipy import stats
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from methods import (wilson_interval,slope,calibrated_slope,mean_interval,ipw_mean,standardized_mean,
                     treatment_difference,simulate_one,summarize)

class MethodsTests(unittest.TestCase):
    def setUp(self):
        self.rng=np.random.default_rng(517)
        self.x=self.rng.normal(size=200)
        self.y=.5*self.x+self.rng.normal(size=200)

    def test_slope_matches_scipy(self):
        got=slope(self.x,self.y); expected=stats.linregress(self.x,self.y)
        self.assertAlmostEqual(got[0],expected.slope,12)
        self.assertAlmostEqual(got[1],expected.stderr,12)

    def test_slope_translation_invariance(self):
        np.testing.assert_allclose(slope(self.x,self.y),slope(self.x+12,self.y-7),atol=1e-12)

    def test_constant_predictor_rejected(self):
        with self.assertRaises(ValueError): slope(np.ones(200),self.y)

    def test_calibration_scales_all_quantities(self):
        np.testing.assert_allclose(calibrated_slope(self.x,self.y,.5),np.array(slope(self.x,self.y))*2)

    def test_invalid_reliability_rejected(self):
        for r in [0,-1,1.01]:
            with self.assertRaises(ValueError): calibrated_slope(self.x,self.y,r)

    def test_mean_interval_matches_definition(self):
        got=mean_interval(self.y)
        self.assertAlmostEqual(got[1],stats.sem(self.y))
        self.assertAlmostEqual(got[3],self.y.mean()+stats.t.ppf(.975,199)*stats.sem(self.y))

    def test_ipw_constant_probability_is_observed_mean(self):
        observed=np.arange(200)%2==0
        y=np.where(observed,self.y,0)
        self.assertAlmostEqual(ipw_mean(y,observed,np.full(200,.6))[0],self.y[observed].mean())

    def test_ipw_with_everyone_observed(self):
        np.testing.assert_allclose(ipw_mean(self.y,np.ones(200,dtype=bool),np.ones(200))[:2],mean_interval(self.y)[:2])

    def test_invalid_probabilities_rejected(self):
        with self.assertRaises(ValueError): ipw_mean(self.y,np.ones(200),np.zeros(200))

    def test_standardization_with_everyone_observed(self):
        got=standardized_mean(self.x,self.y,np.ones(200,dtype=bool))
        np.testing.assert_allclose(got[:2],mean_interval(self.y)[:2],atol=1e-12)

    def test_unobserved_outcomes_cannot_enter_standardization(self):
        observed=np.arange(200)%2==0
        changed=self.y.copy(); changed[~observed]=1e10
        np.testing.assert_allclose(standardized_mean(self.x,self.y,observed),standardized_mean(self.x,changed,observed))

    def test_treatment_difference_matches_scipy(self):
        a=np.arange(200)%2==0
        got=treatment_difference(self.y,a)
        expected=stats.ttest_ind(self.y[a],self.y[~a],equal_var=True)
        self.assertAlmostEqual(got[0]/got[1],expected.statistic)

    def test_relabel_treatment_reverses_estimate(self):
        a=np.arange(200)%2==0
        self.assertAlmostEqual(treatment_difference(self.y,a)[0],-treatment_difference(self.y,~a)[0])

    def test_stream_is_reproducible(self):
        c=dict(id=10,family="measurement",n=100,truth=.5,error_sd=1,error_correlation=0)
        self.assertEqual(simulate_one(c,4,22),simulate_one(c,4,22))
        self.assertNotEqual(simulate_one(c,4,22),simulate_one(c,5,22))

    def test_no_measurement_error_makes_methods_identical(self):
        c=dict(id=10,family="measurement",n=100,truth=.5,error_sd=0,error_correlation=0)
        got,_=simulate_one(c,4,22)
        for v in got.values(): np.testing.assert_allclose(v,got["latent_oracle"])

    def test_summary_coverage_and_mcse(self):
        a=[[0,1,-1,1],[2,1,1,3],[0,1,-1,1],[0,1,-1,1]]
        r=summarize(a,0,4)
        self.assertEqual(r["coverage"],.75)
        self.assertEqual(r["reject_zero"],.25)
        self.assertAlmostEqual(r["coverage_mcse"],np.sqrt(.75*.25/4))
        self.assertAlmostEqual(r["bias"],.5)

    def test_failed_results_are_counted(self):
        a=[[0,1,-1,1],[0,1,-1,1],[np.nan,1,-1,1]]
        r=summarize(a,0,3)
        self.assertEqual(r["failed"],1)
        self.assertEqual(r["coverage_all_attempts"],2/3)

    def test_zero_events_do_not_imply_zero_uncertainty(self):
        lower, upper = wilson_interval(0,2000)
        self.assertAlmostEqual(lower,0)
        self.assertGreater(upper,0)
        self.assertLess(upper,.003)

    def test_standardization_influence_by_case_weight_derivative(self):
        observed=np.arange(200)%3!=0
        z=np.column_stack([np.ones(200),self.x]); beta=np.linalg.lstsq(z[observed],self.y[observed],rcond=None)[0]
        a=z.mean(axis=0); inv=np.linalg.inv(z[observed].T@z[observed]/200)
        residual=np.where(observed,self.y-z@beta,0)
        influence=(z*residual[:,None])@inv@a+(z-a)@beta
        eps=1e-5
        for i in [0,1,2,3]:
            weights=np.ones(200);weights[i]+=eps
            zr=z[observed];wr=weights[observed]
            b=np.linalg.solve(zr.T@(zr*wr[:,None]),zr.T@(self.y[observed]*wr))
            mu=np.average(z,axis=0,weights=weights)@b
            self.assertAlmostEqual((mu-a@beta)/eps*200,influence[i],places=4)

if __name__=="__main__":
    unittest.main()
