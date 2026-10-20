"""Independent price-boundary, sample, coefficient and HC3 checks for FOMC comparison."""
from research_common import *
import hashlib, math, re

OUT = RESULTS / 'fomc_comparison'
RAW = ROOT / 'data/raw/fomc_comparison'


def manual_fit(g, terms):
    x = np.column_stack([np.ones(len(g)), g[terms].to_numpy(dtype=float)])
    y = g.return_pct.to_numpy(dtype=float)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    bread = np.linalg.inv(x.T @ x)
    h = np.einsum('ij,jk,ik->i', x, bread, x)
    residual = y - x @ beta
    meat = x.T @ (x * ((residual / (1 - h)) ** 2)[:, None])
    se = np.sqrt(np.diag(bread @ meat @ bread))
    p = np.array([math.erfc(abs(b / s) / np.sqrt(2)) for b, s in zip(beta, se)])
    return beta[1:], se[1:], p[1:]


def main():
    checks = {}
    audit = json.loads((OUT / 'validation.json').read_text(encoding='utf-8'))
    design = json.loads((OUT / 'design.json').read_text(encoding='utf-8'))
    checks['protected_files_unchanged'] = all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == value for p, value in audit['protected_sha256'].items())
    checks['frozen_design_unchanged'] = hashlib.sha256((OUT / 'design.json').read_bytes()).hexdigest() == audit['design_sha256']
    events = pd.read_csv(OUT / 'event_universe.csv')
    checks['universe_has_47_scheduled_7_unscheduled'] = len(events) == 54 and (events.Unscheduled == 0).sum() == 47 and (events.Unscheduled == 1).sum() == 7
    obs = pd.read_csv(OUT / 'observations.csv')
    source = pd.read_csv(OUT / 'source_log.csv')
    checks['all_94_raw_payloads_documented'] = len(source) == 94 and not source[['asset', 'date']].duplicated().any()
    checks['design_written_before_new_downloads'] = bool((pd.to_datetime(source.retrieved_at_utc, utc=True) >= pd.Timestamp(design['created_before_new_downloads_and_fits_utc'])).all())
    checks['raw_hashes_valid'] = all(hashlib.sha256((RAW / r.source_file).read_bytes()).hexdigest() == r.sha256 for _, r in source.iterrows())
    price_ok, timing_ok, coverage_ok, surprise_ok = [], [], [], []
    sheet = pd.read_excel(ROOT / 'data/raw/USMPD.xlsx', sheet_name='Statements')
    sheet['date'] = sheet.Date.dt.strftime('%Y-%m-%d')
    stmt = pd.read_csv(ROOT / 'data/processed/fomc_policy_surprises.csv').set_index('Date')
    for _, row in obs.iterrows():
        original_event = sheet[sheet.date == row.date].iloc[0]
        event = pd.Timestamp(original_event.date_time).tz_localize('America/New_York').tz_convert('UTC')
        a, b = (-10, 20) if row.window == 'baseline_m10_p20' else (-5, 25)
        first = int(event.timestamp()) + a * 60 - 60
        last = int(event.timestamp()) + b * 60 - 60
        timing_ok.append(pd.Timestamp(row.event_time_utc) == event and pd.Timestamp(row.event_time_et).tz_convert('UTC') == event
                         and pd.Timestamp(row.first_candle_utc).timestamp() == first and pd.Timestamp(row.last_candle_utc).timestamp() == last)
        values = json.loads((RAW / row.source_file).read_bytes())
        closes = {v[0]: v[4] for v in values}
        present = sum(t in closes for t in range(first, last + 1, 60))
        coverage_ok.append(present == row.observed_required_candles and row.expected_candles == 31 and bool(row.complete) == (present == 31))
        if first in closes and last in closes:
            exact = 100 * math.log(closes[last] / closes[first])
            price_ok.append(np.isclose(exact, row.return_pct, atol=1e-11, rtol=1e-10))
        else:
            price_ok.append(pd.isna(row.return_pct))
        surprise_ok.append(np.isclose(row.MP1_10bps, original_event.MP1 * 10) and np.isclose(row.MP2_10bps, original_event.MP2 * 10)
                           and np.isclose(row.STMT_10bps, stmt.loc[row.date, 'STMT'] * 10, equal_nan=True))
    checks['all_188_price_returns_recomputed'] = len(obs) == 188 and all(price_ok)
    checks['all_ET_UTC_DST_and_boundary_rules_correct'] = all(timing_ok)
    checks['complete_requires_all_31_close_observations'] = all(coverage_ok)
    checks['shock_scaling_and_joins_correct'] = all(surprise_ok)
    estimates = pd.read_csv(OUT / 'regressions.csv')
    old = pd.read_csv(OUT / 'original_observations.csv')
    membership = pd.read_csv(OUT / 'matched_membership.csv')
    primary = estimates[estimates.family == 'primary_matched']
    checks['12_primary_tests_same_specs'] = len(primary) == 12 and set(primary.term) == {'MP1_10bps', 'MP2_10bps', 'STMT_10bps'}
    sample_ok, beta_ok, se_ok, p_ok, ci_ok = [], [], [], [], []
    selected = {}
    for _, row in estimates.drop_duplicates(['asset', 'stage', 'window', 'specification']).iterrows():
        if row.family == 'primary_matched':
            a = obs[obs.asset == row.asset]
            valid = a.complete & a[['return_pct', 'MP1_10bps', 'MP2_10bps', 'STMT_10bps']].notna().all(axis=1)
            days = a.assign(good=valid).groupby('date').good.agg(['all', 'count'])
            days = set(days.index[days['all'] & (days['count'] == 2)])
            saved_days = set(membership[(membership.asset == row.asset) & membership.included].date)
            sample_ok.append(days == saved_days)
            g = a[(a.window == row.window) & a.date.isin(days)]
        elif row.stage == 'refreshed_scheduled':
            g = obs[(obs.asset == row.asset) & (obs.window == row.window) & obs.complete]
        else:
            g = old[(old.asset == row.asset) & (old.status == 'complete')]
            if row.stage == 'original_scheduled':
                g = g[g.Unscheduled == 0]
        g = g.dropna(subset=['return_pct', 'MP1_10bps', 'MP2_10bps', 'STMT_10bps']).reset_index(drop=True)
        sample_ok.append(len(g) == row.nobs)
        terms = ['MP1_10bps', 'MP2_10bps'] if row.specification == 'mp1_mp2' else ['STMT_10bps']
        beta, se, p = manual_fit(g, terms)
        r = estimates[(estimates.asset == row.asset) & (estimates.stage == row.stage) & (estimates.window == row.window) & (estimates.specification == row.specification)].set_index('term').loc[terms]
        beta_ok.append(np.allclose(beta, r.beta_return_pct_per10bps, atol=1e-10, rtol=1e-9))
        se_ok.append(np.allclose(se, r.se_hc3, atol=1e-10, rtol=1e-9))
        p_ok.append(np.allclose(p, r.pvalue, atol=1e-10, rtol=1e-9))
        ci_ok.append(np.allclose(beta - 1.959963984540054 * se, r.lower95, atol=1e-10) and np.allclose(beta + 1.959963984540054 * se, r.upper95, atol=1e-10))
        if row.family == 'primary_matched':
            selected[(row.asset, row.window, row.specification)] = (g, terms)
    checks['identical_complete_case_dates_and_sample_sizes'] = all(sample_ok)
    checks['all_coefficients_match_independent_linear_algebra'] = all(beta_ok)
    checks['all_HC3_SE_match_manual_sandwich'] = all(se_ok)
    checks['all_pvalues_match_normal_reference'] = all(p_ok)
    checks['all_pointwise_CIs_correct'] = all(ci_ok)
    q_ok = []
    for family, group in estimates.groupby('family'):
        order = np.argsort(group.pvalue.to_numpy())
        raw = group.pvalue.to_numpy()[order] * len(group) / np.arange(1, len(group) + 1)
        corrected = np.minimum(1, np.minimum.accumulate(raw[::-1])[::-1])
        q_ok.append(np.allclose(corrected, group.qvalue_bh.to_numpy()[order], atol=1e-12))
    checks['BH_recomputed_with_declared_families'] = all(q_ok)
    loo = pd.read_csv(OUT / 'leave_one_out.csv')
    sensitivity_ok = []
    for key, (g, terms) in selected.items():
        for i, event in g.iterrows():
            beta, _, p = manual_fit(g.drop(index=i), terms)
            saved = loo[(loo.asset == key[0]) & (loo.window == key[1]) & (loo.specification == key[2]) & (loo.omitted_date == event.date)].set_index('term').loc[terms]
            sensitivity_ok.append(np.allclose(beta, saved.beta_return_pct_per10bps, atol=1e-10) and np.allclose(p, saved.pvalue, atol=1e-10))
    checks['all_leave_one_event_out_fits_recomputed'] = all(sensitivity_ok) and len(sensitivity_ok) > 0
    h = (OUT / 'report.html').read_text(encoding='utf-8')
    checks['all_local_report_links_exist'] = all((OUT / link).exists() for link in re.findall(r'href="([^"]+)"', h) if not link.startswith('http'))
    result = dict(checks={k: bool(v) for k, v in checks.items()}, n_checks=len(checks), passed=int(sum(checks.values())),
                  note='Checks verify prices and computation; do not establish pure policy identification or full replication.')
    (OUT / 'independent_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)
    assert all(checks.values()), result


if __name__ == '__main__':
    main()
