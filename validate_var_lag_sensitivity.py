"""Independent OLS/IC/residual/Portmanteau/IRF verification; no model selection changes."""
import os
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ.setdefault(key, '2')
from pathlib import Path
import sys, json, hashlib, re
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.research_deps'))
import numpy as np
import pandas as pd
from scipy.stats import chi2

OUT = ROOT / 'outputs/research/var_lag_sensitivity'
NAMES = ['vix_change', 'usd_return_pct', 'us2y_change_bps', 'us10y_change_bps', 'crypto_return_pct']


def main():
    audit = json.loads((OUT / 'validation.json').read_text())
    checks = {'all_protected_files_unchanged': all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == v for p, v in audit['protected_sha256'].items()),
              'design_hash_unchanged': hashlib.sha256((OUT / 'design.json').read_bytes()).hexdigest() == audit['design_sha256']}
    grid = pd.read_csv(OUT / 'candidate_ic.csv')
    diagnostics = pd.read_csv(OUT / 'diagnostics.csv')
    selection = pd.read_csv(OUT / 'lag_selection.csv')
    inventory = pd.read_csv(OUT / 'fit_inventory.csv')
    residual = pd.read_csv(OUT / 'residuals_by_date.csv')
    coefficients = pd.read_csv(OUT / 'coefficients.csv')
    irfs = pd.read_csv(OUT / 'impulse_responses.csv')
    comparison = pd.read_csv(OUT / 'matched_comparison.csv')
    difference = pd.read_csv(OUT / 'irf_matched_comparison.csv')
    manual = {}; ic_ok = []; samples = []; eigen_ok = []; selected_ok = []; residual_ok = []; coeff_ok = []; port_ok = []; irf_ok = []
    for asset in ['btc', 'eth']:
        panel = pd.read_csv(ROOT / f'data/processed/{asset}_econometric_sessions.csv', parse_dates=['date_utc']).set_index('date_utc')
        for regime in ['full', 'pre2020', 'post2020']:
            g = panel if regime == 'full' else panel.loc[:'2019-12-31'] if regime == 'pre2020' else panel.loc['2020-01-01':]
            y = g[NAMES].to_numpy()
            n = len(g) - 15
            deterministic = np.column_stack([np.ones(n)] + [(g.index[15:].dayofweek == day).astype(float) for day in [1, 2, 3, 4]] + [g.elapsed_calendar_days.iloc[15:].to_numpy() - 1])
            for p in range(16):
                z = np.column_stack([deterministic] + [y[15-k:len(y)-k] for k in range(1, p+1)])
                beta = np.linalg.lstsq(z, y[15:], rcond=1e-15)[0]
                u = y[15:] - z @ beta
                sign, logdet = np.linalg.slogdet(u.T @ u / n)
                assert sign > 0
                free = 5 * z.shape[1]
                aic = logdet + 2 * free / n
                bic = logdet + np.log(n) * free / n
                r = grid[(grid.asset == asset) & (grid.regime == regime) & (grid.candidate_lag == p)].iloc[0]
                ic_ok.append(np.allclose([aic, bic, logdet], [r.aic, r.bic, r.logdet_sigma_mle], atol=1e-10, rtol=1e-10))
                samples.append(r.nobs == n and r.response_start == str(g.index[15].date()) and r.response_end == str(g.index[-1].date()) and r.n_parameters == free)
                manual[(asset, regime, p)] = dict(beta=beta, u=u, aic=aic, bic=bic, dates=g.index[15:].strftime('%Y-%m-%d').tolist(), z=z)
            for _, s in selection[(selection.asset == asset) & (selection.regime == regime)].iterrows():
                if s.stage.startswith('search'):
                    limit = 10 if s.stage.startswith('search10') else 15
                    raw = min(range(limit+1), key=lambda p: manual[(asset, regime, p)][s.criterion])
                    selected_ok.append(raw == s.raw_selected_lag and max(1, raw) == s.fitted_lag)
                else:
                    selected_ok.append(s.fitted_lag == s.original_lag)
    for _, item in inventory.iterrows():
        p = int(item.lag); m = manual[(item.asset, item.regime, p)]
        beta, u = m['beta'], m['u']; n = len(u)
        r = residual[residual.fit_id == item.fit_id]
        residual_ok.append(r.date_utc.tolist() == m['dates'] and np.allclose(r[NAMES], u, atol=1e-10, rtol=1e-10))
        terms = ['const', 'tuesday', 'wednesday', 'thursday', 'friday', 'extra_calendar_days'] + [f'L{k}.{name}' for k in range(1, p+1) for name in NAMES]
        saved = coefficients[coefficients.fit_id == item.fit_id].pivot(index='term', columns='equation', values='beta').loc[terms, NAMES]
        coeff_ok.append(np.allclose(beta, saved, atol=1e-10, rtol=1e-10))
        a = np.array([beta[6+5*k:6+5*(k+1)].T for k in range(p)])
        companion = np.zeros((5*p, 5*p)); companion[:5] = np.concatenate(a, axis=1)
        if p > 1: companion[5:, :-5] = np.eye(5*(p-1))
        maxeig = float(np.abs(np.linalg.eigvals(companion)).max())
        d = diagnostics[diagnostics.fit_id == item.fit_id]
        eigen_ok.append(np.allclose(d.max_companion_eigenvalue, maxeig, atol=1e-10) and (d.stable == (maxeig <= 1)).all())
        # Formula follows the documented small-sample adjusted Portmanteau.
        centered = u - u.mean(axis=0)
        inv = np.linalg.inv(centered.T @ centered / n)
        for h in [20, 30, 40]:
            q = 0.
            for k in range(1, h+1):
                cov = centered[k:].T @ centered[:-k] / n
                q += np.trace(cov.T @ inv @ cov @ inv) / (n-k)
            q *= n**2
            pvalue = chi2.sf(q, 25*(h-p))
            port_ok.append(np.allclose(d[f'whiteness_stat{h}'], q, atol=1e-8, rtol=1e-10) and np.allclose(d[f'whiteness_p{h}'], pvalue, atol=1e-12, rtol=1e-8))
        sigma = u.T @ u / (n-beta.shape[0])
        chol = np.linalg.cholesky(sigma)
        phi = [np.eye(5)]
        for h in range(1, 31):
            phi.append(sum(a[k-1] @ phi[h-k] for k in range(1, min(p, h)+1)))
        for _, r in irfs[irfs.fit_id == item.fit_id].iterrows():
            j = NAMES.index(r.shock)
            expected = (phi[int(r.horizon_sessions)] @ chol)[4, j] * r.shock_size / chol[j, j]
            irf_ok.append(np.isclose(expected, r.response_pct, atol=1e-10, rtol=1e-9))
    checks.update({
        '96_unique_candidates_complete': len(grid) == 96 and not grid.duplicated(['asset', 'regime', 'candidate_lag']).any(),
        'all_candidate_ICs_match_manual_OLS': all(ic_ok),
        'all_candidates_use_same_response_dates_and_parameter_counts': all(samples),
        'all_IC_selections_recomputed': len(selection) == 36 and all(selected_ok),
        'all_saved_residuals_match_OLS_and_dates': all(residual_ok),
        'all_coefficients_match_manual_OLS': all(coeff_ok),
        'all_stability_eigenvalues_recomputed': all(eigen_ok),
        'all_20_30_40_Portmanteau_results_recomputed': all(port_ok),
        'all_IRFs_recomputed_from_lag_matrices': all(irf_ok),
        'pointwise_CI_arithmetic_correct': np.allclose(irfs.lower95, irfs.response_pct - 1.96*irfs.se) and np.allclose(irfs.upper95, irfs.response_pct + 1.96*irfs.se),
        '12_matched_comparisons_same_dates': len(comparison) == 12 and comparison.identical_response_dates.all() and comparison.nobs_new.eq(comparison.nobs_reference).all(),
        'matched_IRF_differences_reconcile': np.allclose(difference.response_difference_pp, difference.response_pct_new-difference.response_pct_reference, atol=1e-12),
        'residuals_saved_once_per_fit_date': not residual.duplicated(['fit_id', 'date_utc']).any() and set(residual.fit_id) == set(inventory.fit_id),
        'all_model_references_have_inventory': set(diagnostics.fit_id) == set(inventory.fit_id) == set(irfs.fit_id),
        'all_report_links_exist': all((OUT / link).exists() for link in re.findall(r'href="([^"]+)"', (OUT / 'report.html').read_text(encoding='utf-8')) if not link.startswith('http')),
    })
    result = dict(checks={k: bool(v) for k, v in checks.items()}, n_checks=len(checks), passed=int(sum(checks.values())),
                  n_unique_selected_fits=len(inventory), note='Integrity and arithmetic verification, not a claim of model adequacy or causal identification.')
    (OUT / 'independent_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)
    assert all(checks.values()), checks


if __name__ == '__main__': main()
