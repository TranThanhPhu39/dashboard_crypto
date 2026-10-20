"""Verify classical ARCH arithmetic and conditional case deletion independently."""
import os
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ.setdefault(key, '2')
from pathlib import Path
import sys, json, hashlib, re
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.research_deps'))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import OLSInfluence
from statsmodels.tsa.vector_ar.var_model import ma_rep
from scipy.stats import chi2

OUT = ROOT / 'outputs/research/var_residual_diagnostics'
SOURCE = ROOT / 'outputs/research/var_lag_sensitivity'
NAMES = ['vix_change', 'usd_return_pct', 'us2y_change_bps', 'us10y_change_bps', 'crypto_return_pct']


def main():
    audit = json.loads((OUT / 'validation.json').read_text())
    checks = dict(all_protected_files_unchanged=all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == v for p, v in audit['protected_sha256'].items()),
                  design_hash_unchanged=hashlib.sha256((OUT / 'design.json').read_bytes()).hexdigest() == audit['design_sha256'])
    inventory = pd.read_csv(SOURCE / 'fit_inventory.csv')
    residuals = pd.read_csv(SOURCE / 'residuals_by_date.csv')
    arch = pd.read_csv(OUT / 'arch_tests.csv')
    screens = pd.read_csv(OUT / 'all_observation_screens.csv')
    top = pd.read_csv(OUT / 'top_observations.csv')
    target = pd.read_csv(OUT / 'january2016_gap_screen.csv')
    cases = pd.read_csv(OUT / 'conditional_case_deletion.csv')
    coefficients = pd.read_csv(OUT / 'case_deletion_coefficients.csv')
    responses = pd.read_csv(OUT / 'case_deletion_irfs.csv')
    originals = pd.read_csv(SOURCE / 'impulse_responses.csv')
    arch_ok, cook_ok, student_ok, leverage_ok, selection_ok, woodbury_ok, irf_ok, case_dates_ok, summary_ok = [], [], [], [], [], [], [], [], []
    for _, item in inventory.iterrows():
        p = int(item.lag)
        panel = pd.read_csv(ROOT / f'data/processed/{item.asset}_econometric_sessions.csv', parse_dates=['date_utc']).set_index('date_utc')
        g = panel if item.regime == 'full' else panel.loc[:'2019-12-31'] if item.regime == 'pre2020' else panel.loc['2020-01-01':]
        yy = g[NAMES].to_numpy(); y = yy[15:]; n = len(y)
        x = np.column_stack([np.ones(n)] + [(g.index[15:].dayofweek == day).astype(float) for day in [1, 2, 3, 4]] + [g.elapsed_calendar_days.iloc[15:].to_numpy()-1] + [yy[15-j:len(yy)-j] for j in range(1, p+1)])
        k = x.shape[1]; dates = g.index[15:].strftime('%Y-%m-%d').tolist()
        u = residuals[residuals.fit_id == item.fit_id][NAMES].to_numpy()
        beta = np.linalg.lstsq(x, y, rcond=1e-15)[0]
        s = screens[screens.fit_id == item.fit_id].reset_index(drop=True)
        assert s.date_utc.tolist() == dates
        bread = np.linalg.inv(x.T @ x)
        cooks = []
        for j, eq in enumerate(NAMES):
            fit = sm.OLS(y[:, j], x).fit()
            influence = OLSInfluence(fit)
            expected = influence.cooks_distance[0]
            cooks.append(expected)
            cook_ok.append(np.allclose(expected, s['cook_'+eq], atol=1e-10, rtol=1e-8))
            if j == 4:
                student_ok.append(np.allclose(influence.resid_studentized_internal, s.crypto_internal_studentized, atol=1e-10, rtol=1e-8))
                leverage_ok.append(np.allclose(influence.hat_matrix_diag, s.leverage, atol=1e-10, rtol=1e-8))
            squared = u[:, j]**2
            for lag in [5, 10]:
                z = np.column_stack([np.ones(n-lag)] + [squared[lag-l:n-l] for l in range(1, lag+1)])
                outcome = squared[lag:]
                aux_beta = np.linalg.lstsq(z, outcome, rcond=None)[0]
                error = outcome-z@aux_beta
                r2 = 1 - error@error / np.sum((outcome-outcome.mean())**2)
                lm = (n-lag-k)*r2
                r = arch[(arch.fit_id == item.fit_id) & (arch.equation == eq) & (arch.arch_lags == lag)].iloc[0]
                arch_ok.append(np.isclose(lm, r.lm_stat, atol=1e-8, rtol=1e-8) and np.isclose(chi2.sf(lm, lag), r.pvalue, atol=1e-12, rtol=1e-6) and r.ddof == k and r.auxiliary_nobs == n-lag)
        cooks = np.array(cooks).T
        cook_ok.append(np.allclose(s.max_cook, cooks.max(axis=1), atol=1e-10))
        cook_ok.append(np.array_equal(s.crypto_cook_rank, pd.Series(cooks[:, 4]).rank(method='min', ascending=False).astype(int)))
        chosen = s.sort_values(['max_cook', 'date_utc'], ascending=[False, True]).head(3).date_utc.tolist()
        if '2016-01-27' in dates and '2016-01-27' not in chosen: chosen.append('2016-01-27')
        c = cases[cases.fit_id == item.fit_id]
        selection_ok.append(set(c.selected_date) == set(chosen) and len(c) == 2*len(chosen))
        terms = ['const', 'tuesday', 'wednesday', 'thursday', 'friday', 'extra_calendar_days'] + [f'L{j}.{eq}' for j in range(1, p+1) for eq in NAMES]
        for _, r in c.iterrows():
            i = dates.index(r.selected_date)
            stop = min(n, i+(1 if r['mode'] == 'single_response_row' else p+1))
            block = np.arange(i, stop); keep = np.ones(n, dtype=bool); keep[block] = False
            case_dates_ok.append(r.n_removed == len(block) and r.nobs == n-len(block) and r.removed_first_date == dates[i] and r.removed_last_date == dates[stop-1])
            # Block-deletion identity, independent of the explicit refits used in producer.
            xb = x[block]; ub = y[block]-xb@beta
            new_beta = beta-bread@xb.T@np.linalg.solve(np.eye(len(block))-xb@bread@xb.T, ub)
            co = coefficients[coefficients.case_id == r.case_id].pivot(index='term', columns='equation', values='sensitivity_beta').loc[terms, NAMES].to_numpy()
            woodbury_ok.append(np.allclose(new_beta, co, atol=1e-9, rtol=1e-8))
            new_u = y[keep]-x[keep]@new_beta
            sigma = new_u.T@new_u / (keep.sum()-k)
            chol = np.linalg.cholesky(sigma)
            a = np.array([new_beta[6+5*j:6+5*(j+1)].T for j in range(p)])
            phis = ma_rep(a, maxn=30)
            exported = responses[responses.case_id == r.case_id]
            for j, shock in enumerate(NAMES[:4]):
                scale = [5, 1, 10, 10][j] / chol[j, j]
                expected = np.array([(phi@chol)[4, j]*scale for phi in phis])
                saved = exported[exported.shock == shock].sort_values('horizon_sessions')
                original = originals[(originals.fit_id == item.fit_id) & (originals.shock == shock)].sort_values('horizon_sessions')
                irf_ok.append(len(saved) == 31 and np.allclose(expected, saved.sensitivity_response_pct, atol=1e-8, rtol=1e-7) and np.allclose(saved.baseline_response_pct, original.response_pct, atol=1e-10))
            summary_ok.append(np.isclose(r.max_abs_irf_change_pp, exported.difference_pp.abs().max(), atol=1e-10))
    order = np.argsort(arch.pvalue.to_numpy())
    corrected = np.minimum(1, np.minimum.accumulate((arch.pvalue.to_numpy()[order]*len(arch)/np.arange(1, len(arch)+1))[::-1])[::-1])
    checks.update(dict(
        hundred_ARCH_tests_on_unique_fits=len(arch) == 100 and not arch.duplicated(['fit_id', 'equation', 'arch_lags']).any(),
        all_ARCH_LM_statistics_pvalues_and_ddof_recomputed=all(arch_ok),
        one_BH_family_recomputed=np.allclose(corrected, arch.qvalue_bh.to_numpy()[order], atol=1e-12),
        all_Cook_values_and_crypto_ranks_match_library=all(cook_ok),
        internal_studentization_matches_library=all(student_ok),
        leverage_matches_library=all(leverage_ok),
        selected_cases_follow_frozen_screen_rule=all(selection_ok),
        all_case_blocks_preserve_original_dates_and_lags=all(case_dates_ok),
        all_case_coefficients_match_block_deletion_identity=all(woodbury_ok),
        all_case_IRFs_match_library_MA_representation=all(irf_ok),
        all_max_IRF_change_summaries_reconcile=all(summary_ok),
        all_IRF_differences_reconcile=np.allclose(responses.difference_pp, responses.sensitivity_response_pct-responses.baseline_response_pct, atol=1e-11),
        six_2016_gap_screens_present=len(target) == 6 and target.date_utc.eq('2016-01-27').all() and target.elapsed_calendar_days.eq(6).all(),
        hundred_top10_screen_rows=len(top) == 100,
        screen_rows_unique=not screens.duplicated(['fit_id', 'date_utc']).any(),
        all_case_outputs_complete=len(responses) == len(cases)*124 and not responses.duplicated(['case_id', 'shock', 'horizon_sessions']).any(),
        all_local_report_links_exist=all((OUT/link).exists() for link in re.findall(r'href="([^"]+)"', (OUT/'report.html').read_text(encoding='utf-8')) if not link.startswith('http')),
    ))
    result = dict(checks={k: bool(v) for k, v in checks.items()}, n_checks=len(checks), passed=int(sum(checks.values())),
                  note='Verifies arithmetic/screens/sensitivity; not a validation of classical test assumptions or causal interpretation.')
    (OUT/'independent_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)
    assert all(checks.values()), checks


if __name__ == '__main__': main()
