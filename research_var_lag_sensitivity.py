"""Finite, approved VAR lag sensitivity: weekday+gap, domain 0..15, no data edits."""
import os
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ.setdefault(key, '2')
from research_common import *
import hashlib, datetime, html
from statsmodels.tsa.api import VAR

OUT = RESULTS / 'var_lag_sensitivity'
NAMES = ['vix_change', 'usd_return_pct', 'us2y_change_bps', 'us10y_change_bps', 'crypto_return_pct']
SHOCKS = {'vix_change': 5., 'usd_return_pct': 1., 'us2y_change_bps': 10., 'us10y_change_bps': 10.}
CUT = 15
STAGES = ['historical_lag_common_dates', 'search10_common_dates', 'search15_common_dates']


def save(frame, name):
    frame.to_csv(OUT / (name + '.csv'), index=False, encoding='utf-8-sig', float_format='%.14g')


def controls(panel):
    x = pd.DataFrame(index=panel.index)
    for weekday, label in [(1, 'tuesday'), (2, 'wednesday'), (3, 'thursday'), (4, 'friday')]:
        x[label] = (panel.index.dayofweek == weekday).astype(float)
    x['extra_calendar_days'] = panel.elapsed_calendar_days - 1.
    return x


def protected_hashes():
    files = list((ROOT / 'data').rglob('*')) + list(RESULTS.rglob('*')) + list((ROOT / 'notebooks').rglob('*'))
    files += [ROOT / x for x in ['research_econometrics.py', 'research_var_calendar.py', 'research_forecasting.py', 'research_events.py']]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file() and OUT not in p.parents}


def main():
    OUT.mkdir(exist_ok=True)
    before = protected_hashes()
    design = dict(variables=NAMES, controls='constant, Tuesday-Friday dummies, elapsed_calendar_days-1',
                  regimes=['full', 'pre2020', 'post2020'], assets=['btc', 'eth'], candidate_lags=list(range(16)), minimum_fitted_lag=1,
                  effective_sample='Within each asset/regime, response dates are panel.index[15:] for ALL candidates and reference fits.',
                  fitting='For lag p, supply panel.iloc[15-p:] to VAR.fit(p). Lagged observations remain within regime.',
                  stages=STAGES, criteria=['bic', 'aic'], whiteness_lags=[20, 30, 40], whiteness_adjusted=True,
                  selection='Choose IC only; do not search for p-values. Domain 0..10 and 0..15 both use identical IC response sample.',
                  interpretation='Exploratory sensitivity after earlier diagnostics; finite domain, no automatic extension beyond 15.',
                  excluded='No ARCH/influence tests, outlier deletion, bootstrap, new data, imputation, weekly aggregation or forecasting changes.',
                  irf='Recursive Cholesky same order/sizes, conditional on fixed exogenous path; pointwise asymptotic CI, no post-selection correction.',
                  started_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    path = OUT / 'design.json'
    if path.exists():
        prior = json.loads(path.read_text(encoding='utf-8'))
        assert all(prior[k] == v for k, v in design.items() if k != 'started_at_utc')
    else:
        path.write_text(json.dumps(design, indent=2), encoding='utf-8')
    old = pd.read_csv(RESULTS / 'var_calendar_extension/diagnostics.csv')
    old = old[old.specification == 'weekday_gap']
    grid, diag, residual, coeff, irfs, inventory, selections = [], [], [], [], [], [], []
    checks = {}
    for asset in ['btc', 'eth']:
        panel = data(asset + '_econometric_sessions.csv')
        for regime, g in [('full', panel), ('pre2020', panel.loc[:'2019-12-31']), ('post2020', panel.loc['2020-01-01':])]:
            x = controls(g)
            fits = {}
            for p in range(16):
                start = CUT - p
                yy = g[NAMES].iloc[start:].reset_index(drop=True)
                xx = x.iloc[start:].reset_index(drop=True)
                fit = VAR(yy, exog=xx).fit(p)
                fits[p] = fit
                assert fit.nobs == len(g) - CUT
                assert fit.df_resid > 0
                grid.append(dict(asset=asset, regime=regime, candidate_lag=p, nobs=fit.nobs,
                                 response_start=g.index[CUT].date(), response_end=g.index[-1].date(),
                                 aic=fit.aic, bic=fit.bic, n_parameters=fit.params.size,
                                 logdet_sigma_mle=float(np.linalg.slogdet(fit.sigma_u_mle)[1])))
            # Cross-check candidate ICs against the library's documented order selection.
            auto = VAR(g[NAMES].reset_index(drop=True), exog=x.reset_index(drop=True)).select_order(15)
            for criterion in ['bic', 'aic']:
                checks[f'{asset}_{regime}_{criterion}_IC_matches_library'] = bool(np.allclose(
                    [getattr(fits[p], criterion) for p in range(16)], auto.ics[criterion], atol=1e-9, rtol=1e-9))
                original = old[(old.asset == asset) & (old.regime == regime) & (old.criterion == criterion)].iloc[0]
                p10_raw = min(range(11), key=lambda p: getattr(fits[p], criterion))
                p15_raw = min(range(16), key=lambda p: getattr(fits[p], criterion))
                for stage, raw_p in zip(STAGES, [int(original.lag), p10_raw, p15_raw]):
                    p = max(1, raw_p)
                    fit = fits[p]
                    fit_id = f'{asset}_{regime}_p{p}_common15'
                    selections.append(dict(asset=asset, regime=regime, stage=stage, criterion=criterion,
                                           raw_selected_lag=raw_p, fitted_lag=p, fit_id=fit_id,
                                           original_lag=int(original.lag), original_nobs=int(original.nobs),
                                           original_whiteness_p20=float(original.whiteness_p20)))
                    white = {h: fit.test_whiteness(nlags=h, adjusted=True) for h in [20, 30, 40]}
                    roots = np.linalg.eigvals(np.column_stack([np.asarray(fit.coefs).transpose(1, 0, 2).reshape(5, 5*p)]) if p == 1 else
                                             np.vstack([np.column_stack(list(fit.coefs)), np.column_stack([np.eye(5*(p-1)), np.zeros((5*(p-1), 5))])]))
                    record = dict(asset=asset, regime=regime, stage=stage, criterion=criterion, fit_id=fit_id,
                                  lag=p, nobs=int(fit.nobs), n_parameters=fit.params.size, parameters_per_equation=fit.params.shape[0],
                                  df_resid=int(fit.df_resid), stable=bool(fit.is_stable()), max_companion_eigenvalue=float(np.abs(roots).max()),
                                  response_start=g.index[CUT].date(), response_end=g.index[-1].date())
                    for h, test in white.items():
                        record.update({f'whiteness_p{h}': float(test.pvalue), f'whiteness_stat{h}': float(test.test_statistic), f'whiteness_df{h}': int(test.df)})
                    diag.append(record)
            # Store selected fits once; multiple criteria/stages can refer to one fitted system.
            selected_lags = sorted({r['lag'] for r in diag if r['asset'] == asset and r['regime'] == regime})
            for p in selected_lags:
                fit = fits[p]; fit_id = f'{asset}_{regime}_p{p}_common15'
                inventory.append(dict(fit_id=fit_id, asset=asset, regime=regime, lag=p, nobs=int(fit.nobs), response_start=g.index[CUT].date(), response_end=g.index[-1].date()))
                u = pd.DataFrame(np.asarray(fit.resid), columns=NAMES)
                u.insert(0, 'date_utc', g.index[CUT:].strftime('%Y-%m-%d'))
                u.insert(0, 'fit_id', fit_id); residual.append(u)
                for term in fit.params.index:
                    for eq in NAMES:
                        coeff.append(dict(fit_id=fit_id, term=term, equation=eq, beta=float(fit.params.loc[term, eq])))
                irf = fit.irf(30); se = irf.stderr(orth=True)
                chol = np.linalg.cholesky(np.asarray(fit.sigma_u))
                for shock, size in SHOCKS.items():
                    j = NAMES.index(shock); scale = size / chol[j, j]
                    for h in range(31):
                        b = float(irf.orth_irfs[h, 4, j] * scale); s = float(se[h, 4, j] * abs(scale))
                        irfs.append(dict(fit_id=fit_id, shock=shock, shock_size=size, horizon_sessions=h, response_pct=b, se=s, lower95=b-1.96*s, upper95=b+1.96*s))
            print('Completed finite VAR sensitivity:', asset, regime, 'selected lags', selected_lags, flush=True)
    diagnostics = pd.DataFrame(diag); selection = pd.DataFrame(selections); responses = pd.DataFrame(irfs)
    for frame, name in [(pd.DataFrame(grid), 'candidate_ic'), (diagnostics, 'diagnostics'), (selection, 'lag_selection'),
                        (pd.DataFrame(inventory), 'fit_inventory'), (pd.concat(residual, ignore_index=True), 'residuals_by_date'),
                        (pd.DataFrame(coeff), 'coefficients'), (responses, 'impulse_responses')]:
        save(frame, name)
    base = diagnostics[diagnostics.stage == STAGES[0]]
    newer = diagnostics[diagnostics.stage == STAGES[-1]]
    comparison = newer.merge(base, on=['asset', 'regime', 'criterion'], suffixes=('_new', '_reference'), validate='one_to_one')
    comparison = comparison.merge(selection[selection.stage == STAGES[-1]][['asset', 'regime', 'criterion', 'original_lag', 'original_nobs', 'original_whiteness_p20']], on=['asset', 'regime', 'criterion'], validate='one_to_one')
    comparison['same_lag_as_historical'] = comparison.lag_new == comparison.lag_reference
    comparison['identical_response_dates'] = (comparison.response_start_new == comparison.response_start_reference) & (comparison.response_end_new == comparison.response_end_reference)
    save(comparison, 'matched_comparison')
    diff = []
    for _, r in comparison.iterrows():
        a = responses[responses.fit_id == r.fit_id_new]
        b = responses[responses.fit_id == r.fit_id_reference]
        q = a.merge(b, on=['shock', 'horizon_sessions'], suffixes=('_new', '_reference'), validate='one_to_one')
        q['asset'] = r.asset; q['regime'] = r.regime; q['criterion'] = r.criterion
        q['response_difference_pp'] = q.response_pct_new - q.response_pct_reference
        diff.append(q)
    difference = pd.concat(diff, ignore_index=True); save(difference, 'irf_matched_comparison')
    checks['existing_files_unchanged'] = before == protected_hashes()
    checks['all_reported_models_have_identical_dates_within_asset_regime'] = bool(diagnostics.groupby(['asset', 'regime'])[['nobs', 'response_start', 'response_end']].nunique().eq(1).all().all())
    validation = dict(checks=checks, protected_sha256=before, n_checks=len(checks), passed=int(sum(checks.values())),
                      n_candidate_fits=len(grid), n_reported_stage_criterion_records=len(diag), n_unique_selected_fits=len(inventory),
                      n_search15_reject_at_each_horizon={str(h): int((newer[f'whiteness_p{h}'] < .05).sum()) for h in [20, 30, 40]},
                      n_search15_models=len(newer), n_search15_stable=int(newer.stable.sum()),
                      max_abs_matched_irf_difference_pp=float(difference.response_difference_pp.abs().max()),
                      design_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2), encoding='utf-8')
    assert all(checks.values()), checks
    report(diagnostics, selection, comparison, validation)
    print(newer[['asset', 'regime', 'criterion', 'lag', 'nobs', 'whiteness_p20', 'whiteness_p30', 'whiteness_p40']].to_string(index=False), flush=True)


def report(diagnostics, selection, comparison, validation):
    newer = diagnostics[diagnostics.stage == STAGES[-1]]
    cols = ['asset', 'regime', 'criterion', 'lag', 'nobs', 'stable', 'whiteness_p20', 'whiteness_p30', 'whiteness_p40']
    def md(frame):
        f = frame.copy()
        for c in f.select_dtypes(include='number'):
            f[c] = f[c].map(lambda x: f'{x:.6g}')
        return '| ' + ' | '.join(f.columns) + ' |\n| ' + ' | '.join(['---'] * len(f.columns)) + ' |\n' + '\n'.join('| ' + ' | '.join(map(str, r)) + ' |' for r in f.itertuples(index=False, name=None))
    n = len(newer)
    results = '; '.join(f"{h} lags: {validation['n_search15_reject_at_each_horizon'][str(h)]}/{n} bác bỏ" for h in [20, 30, 40])
    note = f'''# VAR sensitivity miền lag 0–15 — 17/10/2026

Đã thực hiện lượt hữu hạn theo yêu cầu tiếp tục VAR. Giữ nguyên panel, 5 biến và thứ tự VIX/USD/2Y/10Y/crypto; constant, weekday Tuesday–Friday (Monday reference), elapsed_calendar_days−1. Không khôi phục USD 01/2016, không loại outlier, không đổi forecasting/FOMC/LP. Đây là sensitivity sau khi đã xem chẩn đoán cũ, không phải thiết kế xác nhận trước mẫu.

## Kết quả miền 0–15

{validation['n_search15_stable']}/{n} hệ ổn định. Portmanteau adjusted: {results}. Các kiểm định cùng dữ liệu và nhiều horizon không phải các bằng chứng độc lập. Không chọn mô hình/horizon theo p-value.

{md(newer[cols])}

## Tách ảnh hưởng đổi miền lag và đổi mẫu

Mỗi asset/regime dùng cùng **response dates từ quan sát thứ 16 trở đi** cho toàn bộ 16 ứng viên p=0…15, với các lags lấy từ 15 quan sát đầu cùng regime. AIC/BIC so trên cùng nobs, gồm chi phí của cả constant và 5 exogenous controls. Nếu IC chọn 0, fitted lag tối thiểu 1 theo convention cũ; raw/fitted lag đều được lưu.

Ba bước cùng response dates: (1) lag lịch sử 0–10 đã chọn trước đây, refit trên mẫu common15; (2) chọn lại 0–10 trên common15; (3) chọn 0–15 trên common15. Nhờ đó, (2)→(3) tách mở miền search khỏi thay đổi sample; (1)→(3) so IRF trên cùng ngày. Kết quả cũ vốn fit trên n−p được giữ nguyên, chỉ trích tham chiếu trong bảng mới; không gán thay đổi p-value do cắt đầu mẫu thành tác dụng của tăng lag.

{md(selection[['asset', 'regime', 'criterion', 'stage', 'raw_selected_lag', 'fitted_lag']])}

So 0–15 với lag lịch sử trên common15: {int(comparison.same_lag_as_historical.sum())}/{len(comparison)} lựa chọn giữ cùng lag. Chênh lệch IRF tuyệt đối lớn nhất trên cả 4 shocks, 0–30 phiên, 2 criteria và 3 regimes: {validation['max_abs_matched_irf_difference_pp']:.6g} điểm phần trăm. Nếu cùng fit_id, các đường trùng nhau chính xác; không xem chúng là nhiều ước lượng độc lập.

## Diễn giải và giới hạn

- Whiteness không bác bỏ, nếu có, cũng không chứng minh phần dư trắng hay tác động nhân quả. Bác bỏ cần được giữ trong kết luận, không tự tăng tiếp lag vượt 15 để tìm p-value đạt.
- IRF là phản ứng Cholesky có điều kiện, giữ exogenous path cố định. CI pointwise dùng tiệm cận như các lượt trước, chưa hiệu chỉnh lag selection, heteroskedasticity hay kiểm định nhiều horizon. Không coi CI là suy luận đã được xác nhận khi phần dư còn hạn chế.
- Việc căn khoảng ngày và cộng cuối tuần không đồng bộ chính xác market closes Mỹ với crypto UTC. Khoảng 6 ngày 01/2016 vẫn được giữ; ETH ADF/KPSS mâu thuẫn đã được ghi trong audit trước. Lượt này không giải quyết những giới hạn đó.
- Chưa thêm ARCH/influence/robust bootstrap hoặc mô hình tuần. Các phần đó cần chốt thiết kế trước; không tự triển khai chỉ vì kết quả whiteness.

## Tệp tái lập và đối chiếu

- `design.json`: thiết kế ghi trước fitting.
- `candidate_ic.csv`: 96 candidate fits (6 asset/regime × 16 p), không phải 96 mô hình được chọn.
- `diagnostics.csv`, `lag_selection.csv`: 36 dòng tham chiếu stage/criterion; chỉ {validation['n_unique_selected_fits']} fitted systems khác nhau, tra `fit_inventory.csv`.
- `residuals_by_date.csv`: phần dư 5 phương trình theo ngày/fit_id, lưu một lần mỗi hệ; `coefficients.csv` cho phép replay fitted values.
- `matched_comparison.csv`, `irf_matched_comparison.csv`, `impulse_responses.csv`: so sánh trên cùng response dates.
- `validation.json`: kiểm tra nội bộ và SHA-256 của {len(validation['protected_sha256'])} file dữ liệu/kết quả cũ; tất cả giữ nguyên. Đạt kiểm tra tính toán không đồng nghĩa mô hình đạt adequacy.

```powershell
py -3.11 research_var_lag_sensitivity.py
py -3.11 validate_var_lag_sensitivity.py
```

Phương pháp thư viện: [chọn lag](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.var_model.VAR.select_order.html), [Portmanteau và adjusted](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.var_model.VARResults.test_whiteness.html). Việc chốt miền 0–15 và cách đánh giá là thiết kế của dự án.
'''
    (OUT / 'report.md').write_text(note, encoding='utf-8')
    h = '<!doctype html><html lang="vi"><meta charset="utf-8"><title>VAR lag sensitivity</title><style>body{font:15px system-ui;margin:28px;color:#1b3445}table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccd;padding:7px}th{background:#e5f0f5}pre{white-space:pre-wrap;font:inherit}</style><h1>VAR: miền lag 0–15</h1>'
    h += '<p>' + html.escape(results) + '</p>' + newer[cols].to_html(index=False, float_format=lambda x: f'{x:.5g}')
    h += '<p><a href="report.md">Báo cáo đầy đủ</a> | <a href="diagnostics.csv">Diagnostics</a> | <a href="residuals_by_date.csv">Residuals</a> | <a href="validation.json">Kiểm tra</a></p><pre>' + html.escape(note) + '</pre></html>'
    (OUT / 'report.html').write_text(h, encoding='utf-8')


if __name__ == '__main__': main()
