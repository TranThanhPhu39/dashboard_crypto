"""Read-only model audit: summarize frozen diagnostics and verify every session interval.

No estimation, lag search, hypothesis test or data download is performed.
CSV summaries and a reviewable proposal are saved outside existing output folders.
"""
from pathlib import Path
import sys, json, hashlib, html
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.research_deps'))
import pandas as pd
import numpy as np

SOURCE = ROOT / 'outputs/research/var_calendar_extension'
OUT = ROOT / 'outputs/research/var_diagnostic_audit'
NAMES = ['vix_change', 'usd_return_pct', 'us2y_change_bps', 'us10y_change_bps', 'crypto_return_pct']
KEYS = ['asset', 'regime', 'specification', 'criterion']


def hashes():
    paths = list((ROOT / 'data').rglob('*')) + list((ROOT / 'outputs/research').rglob('*'))
    paths += list((ROOT / 'notebooks').rglob('*'))
    paths += [ROOT / 'research_econometrics.py', ROOT / 'research_var_calendar.py']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file() and OUT not in p.parents}


def save(frame, name):
    frame.to_csv(OUT / (name + '.csv'), index=False, encoding='utf-8-sig', float_format='%.12g')


def md(frame):
    f = frame.copy()
    for c in f.select_dtypes(include='number'):
        f[c] = f[c].map(lambda x: f'{x:.6g}')
    return '| ' + ' | '.join(f.columns) + ' |\n| ' + ' | '.join(['---'] * len(f.columns)) + ' |\n' + '\n'.join('| ' + ' | '.join(map(str, r)) + ' |' for r in f.itertuples(index=False, name=None))


def main():
    OUT.mkdir(exist_ok=True)
    before = hashes()
    diag = pd.read_csv(SOURCE / 'diagnostics.csv')
    corr = pd.read_csv(SOURCE / 'residual_cross_correlations.csv')
    own = pd.read_csv(SOURCE / 'residual_own_serial_tests.csv')
    selections = pd.read_csv(SOURCE / 'lag_selection.csv')
    stationarity = pd.read_csv(ROOT / 'outputs/research/tables/stationarity_tests.csv')
    checks = {}
    checks['cross_correlation_grid_complete_unique'] = len(corr) == 24 * 20 * 25 and not corr.duplicated(KEYS + ['lag_sessions', 'current_equation', 'lagged_equation']).any()
    checks['correlations_finite_within_bounds'] = np.isfinite(corr.residual_correlation).all() and corr.residual_correlation.abs().le(1).all()
    checks['own_serial_grid_complete_unique'] = len(own) == 24 * 5 and not own.duplicated(KEYS + ['equation']).any()
    corr['abs_correlation'] = corr.residual_correlation.abs()
    corr['own_or_cross'] = np.where(corr.current_equation == corr.lagged_equation, 'own', 'cross')
    # Rank by descriptive Pearson magnitude only, NOT contribution to Portmanteau.
    top = corr.sort_values('abs_correlation', ascending=False).groupby(KEYS, sort=False).head(10).sort_values(KEYS + ['abs_correlation'], ascending=[True] * 4 + [False])
    save(top, 'top_residual_correlations')
    lag_summary = corr.groupby(KEYS + ['lag_sessions', 'own_or_cross']).agg(
        max_abs_pearson=('abs_correlation', 'max'), mean_abs_pearson=('abs_correlation', 'mean')).reset_index()
    save(lag_summary, 'lag_magnitude_summary')
    by_variable = corr.groupby(KEYS + ['current_equation', 'own_or_cross']).agg(
        max_abs_pearson=('abs_correlation', 'max'), mean_abs_pearson=('abs_correlation', 'mean')).reset_index()
    save(by_variable, 'equation_magnitude_summary')
    save(own, 'own_serial_tests_existing')
    combined = diag[diag.specification == 'weekday_gap'].copy()
    save(combined, 'combined_diagnostics_existing')
    full_p = own[(own.specification == 'weekday_gap') & (own.regime == 'full')].pivot(index=['asset', 'criterion'], columns='equation', values='own_autocorr_ljungbox_p20').reset_index()
    save(full_p, 'full_sample_own_serial_existing')
    ic = selections.groupby(KEYS, as_index=False).agg(min_candidate_lag=('candidate_lag', 'min'), max_candidate_lag=('candidate_lag', 'max'),
                                                      raw_selected_lag=('raw_selected_lag', 'first'), fitted_lag=('fitted_lag', 'first'))
    ic['selected_at_upper_boundary'] = ic.raw_selected_lag == ic.max_candidate_lag
    save(ic, 'lag_search_existing')
    checks['lag_domain_remains_zero_to_ten'] = (ic.min_candidate_lag == 0).all() and (ic.max_candidate_lag == 10).all()
    checks['combined_12_stable_reject_whiteness20'] = len(combined) == 12 and combined.stable.all() and (combined.whiteness_p20 < .05).all()
    checks['stationarity_existing_table_complete_valid'] = len(stationarity) == 30 and not stationarity.duplicated(['asset', 'regime', 'variable']).any() and np.isfinite(stationarity[['adf_p', 'kpss_p_bound']]).all().all()
    # Rejection is an empirical finding, not a failed integrity assertion.
    conflicts = stationarity[(stationarity.adf_p < .05) & (stationarity.kpss_p_bound < .05)]
    save(conflicts, 'stationarity_conflicts_existing')
    save(stationarity, 'stationarity_existing')
    daily = pd.read_csv(ROOT / 'data/processed/daily_research_latest.csv', parse_dates=['date_utc']).set_index('date_utc')
    usd_missing = daily[(daily.index.dayofweek < 5) & daily[['vix', 'us2y', 'us10y']].notna().all(axis=1) & daily.broad_usd.isna()]
    save(usd_missing[['vix', 'broad_usd', 'us2y', 'us10y', 'btc_usd', 'eth_usd']].reset_index(), 'usd_missing_other_US_core_observed')
    raw_usd = pd.read_csv(ROOT / 'data/raw/DTWEXBGS_fred.csv', index_col=0)
    target_days = ['2016-01-22', '2016-01-25', '2016-01-26']
    checks['three_2016_USD_missing_values_confirmed_in_raw'] = raw_usd.reindex(target_days).isna().all().all() and set(target_days).issubset(set(raw_usd.index))
    intervals, comparisons = [], []
    for asset in ['btc', 'eth']:
        panel = pd.read_csv(ROOT / f'data/processed/{asset}_econometric_sessions.csv', parse_dates=['date_utc']).set_index('date_utc')
        levels = daily[['vix', 'broad_usd', 'us2y', 'us10y', asset + '_usd']].dropna()
        expected = pd.DataFrame(index=levels.index)
        expected['vix_change'] = levels.vix.diff()
        expected['usd_return_pct'] = 100 * np.log(levels.broad_usd).diff()
        expected['us2y_change_bps'] = 100 * levels.us2y.diff()
        expected['us10y_change_bps'] = 100 * levels.us10y.diff()
        expected['crypto_return_pct'] = 100 * np.log(levels[asset + '_usd']).diff()
        expected['elapsed_calendar_days'] = levels.index.to_series().diff().dt.days
        expected = expected.dropna()
        checks[asset + '_session_dates_exactly_match_common_observed_levels'] = panel.index.equals(expected.index)
        checks[asset + '_all_five_changes_reconcile'] = np.allclose(panel[NAMES], expected[NAMES], atol=1e-10, rtol=1e-10)
        checks[asset + '_elapsed_days_reconcile'] = np.array_equal(panel.elapsed_calendar_days, expected.elapsed_calendar_days)
        checks[asset + '_no_weekend_rows_created_for_US_market'] = set(panel.index.dayofweek).issubset(set(range(5)))
        controls = pd.read_csv(SOURCE / f'{asset}_calendar_controls.csv', parse_dates=['date_utc']).set_index('date_utc')
        checks[asset + '_calendar_controls_exactly_match_dates'] = controls.index.equals(panel.index) and np.array_equal(controls.extra_calendar_days, panel.elapsed_calendar_days - 1)
        returns = 100 * np.log(daily[asset + '_usd']).diff()
        previous = pd.Series(levels.index, index=levels.index).shift(1)
        for end in panel.index:
            start = previous.loc[end]
            dates = pd.date_range(start + pd.Timedelta(days=1), end, freq='D')
            rv = returns.reindex(dates)
            weekend = dates.dayofweek >= 5
            summed = rv.sum(min_count=len(dates))
            intervals.append(dict(asset=asset, previous_session=start.date().isoformat(), session=end.date().isoformat(),
                                  elapsed_calendar_days=len(dates), n_daily_returns_present=int(rv.notna().sum()),
                                  n_weekend_days=int(weekend.sum()), n_weekend_returns_present=int(rv[weekend].notna().sum()),
                                  session_return_pct=panel.loc[end, 'crypto_return_pct'], sum_daily_return_pct=summed,
                                  weekend_return_pct=rv[weekend].sum(min_count=int(weekend.sum())) if weekend.any() else 0.,
                                  end_weekday=end.day_name()))
        for c in NAMES:
            comparisons.append(dict(asset=asset, variable=c, n_intervals=len(panel),
                                    max_abs_difference=float(np.abs(panel[c] - expected[c]).max())))
    intervals = pd.DataFrame(intervals)
    intervals['telescoping_difference_pp'] = intervals.session_return_pct - intervals.sum_daily_return_pct
    checks['all_intervals_include_every_daily_crypto_return'] = intervals.n_daily_returns_present.eq(intervals.elapsed_calendar_days).all()
    checks['all_weekend_daily_returns_included'] = intervals.n_weekend_days.eq(intervals.n_weekend_returns_present).all()
    checks['all_interval_returns_telescope'] = np.isfinite(intervals.telescoping_difference_pp).all() and intervals.telescoping_difference_pp.abs().max() < 1e-9
    save(intervals, 'all_session_interval_checks')
    save(pd.DataFrame(comparisons), 'all_change_reconciliation')
    gaps = intervals.groupby(['asset', 'elapsed_calendar_days'], as_index=False).agg(
        n_intervals=('session', 'size'), n_intervals_with_weekend=('n_weekend_days', lambda x: int((x > 0).sum())),
        mean_return_pct=('session_return_pct', 'mean'), sd_return_pct=('session_return_pct', 'std'),
        max_abs_telescoping_difference_pp=('telescoping_difference_pp', lambda x: x.abs().max()))
    save(gaps, 'interval_length_summary')
    full_top = top[(top.specification == 'weekday_gap') & (top.regime == 'full')].groupby(['asset', 'criterion']).head(5)
    save(full_top, 'full_sample_top_correlations')
    after = hashes()
    checks['all_existing_data_and_results_unchanged'] = before == after
    validation = dict(checks={k: bool(v) for k, v in checks.items()}, n_checks=len(checks), passed=int(sum(checks.values())),
                      protected_sha256=before, no_model_estimation=True, no_new_hypothesis_tests=True,
                      n_intervals_audited=len(intervals), n_intervals_with_weekend=int((intervals.n_weekend_days > 0).sum()),
                      max_abs_interval_difference_pp=float(intervals.telescoping_difference_pp.abs().max()))
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2, ensure_ascii=False), encoding='utf-8')
    assert all(checks.values()), checks
    render_report(full_p, full_top, combined, gaps, ic, validation)
    print(json.dumps({k: v for k, v in validation.items() if k != 'protected_sha256'}, indent=2), flush=True)


def render_report(full_p, full_top, combined, gaps, ic, validation):
    cols = ['asset', 'criterion', 'lag_sessions', 'current_equation', 'lagged_equation', 'residual_correlation']
    conflicts = pd.read_csv(OUT / 'stationarity_conflicts_existing.csv')
    text = f'''# Rà soát chẩn đoán VAR — 17/10/2026

Phạm vi được đồng ý: đọc chẩn đoán đã lưu, kiểm tra cách dựng dữ liệu, đề xuất bước sửa để duyệt. Không fit VAR/LP/forecasting, không chọn lại lag, không kiểm định giả thuyết mới, không tải nguồn mới.

## Kết luận dựa trên kết quả đã có

1. Cả 12 hệ weekday+gap ổn định nhưng vẫn bác bỏ adjusted Portmanteau tại 20 lags. Ổn định không đồng nghĩa phần dư trắng.
2. Chỉ báo riêng từng biến tập trung đáng chú ý ở VIX, USD và 2Y. BTC không bác bỏ ở ngưỡng 5% trong các hệ weekday+gap đã lưu; ETH full có p khoảng 0,043–0,046, post-2020 BIC khoảng 0,046 nhưng AIC khoảng 0,214. Không kết luận toàn bộ vấn đề nằm ở crypto hoặc crypto hoàn toàn sạch.
3. Không thấy lỗi bỏ cuối tuần trong phép dựng session return: đã kiểm tra {validation['n_intervals_audited']} khoảng, trong đó {validation['n_intervals_with_weekend']} khoảng chứa ngày cuối tuần. Tất cả daily returns cần thiết có mặt và cộng đúng return giữa hai mốc; sai số lớn nhất {validation['max_abs_interval_difference_pp']:.3g} điểm phần trăm.
4. ADF đã lưu bác bỏ unit root cho toàn bộ biến/mẫu, nhưng KPSS bác bỏ level stationarity của ETH return ở full/pre-2020. Đây là tín hiệu mâu thuẫn cần xem xét về mean/breaks và độ nhạy, chưa đủ để tự động differencing thêm return. KPSS trong thư viện dùng bảng nội suy và chặn ngoài miền, không phải p giải tích chính xác. Không kiểm định lại trong lượt này.

{md(conflicts[['asset', 'regime', 'variable', 'adf_p', 'kpss_p_bound']])}

## Chỉ báo riêng từng phương trình — full sample, weekday+gap

Các p-value sau được chép từ kết quả cũ, không phải kiểm định mới và chưa điều chỉnh multiple testing.

{md(full_p)}

Ljung–Box cũ dùng `model_df = số lag VAR`. Đây là chỉ báo phụ theo từng chuỗi phần dư, không phải phép phân rã chính xác kiểm định hệ VAR hay suy luận phương trình đã hiệu chỉnh đầy đủ cấu trúc đa biến. Không diễn giải p≥0,05 thành bằng chứng chắc chắn không có tự tương quan.

## Các tương quan phần dư lớn nhất — full sample, weekday+gap

`current_equation` là phần dư hiện tại, `lagged_equation` là phần dư lùi `lag_sessions` phiên. Xếp theo độ lớn Pearson trên từng đoạn giao nhau ở mỗi lag; chưa kiểm định riêng từng ô.

{md(full_top[cols])}

Ở BIC, VIX own-lag 4 nổi bật (BTC khoảng −0,091; ETH −0,085). Ở AIC, VIX own-lag 8 vẫn khoảng −0,064 và −0,070. 2Y còn các tương quan own-lag 11/14; USD cũng còn tín hiệu, cùng các tương quan chéo. Các giá trị này nhỏ về độ lớn tuyệt đối nhưng kiểm định hệ có thể tích lũy tín hiệu từ nhiều cặp và lag.

**Giới hạn:** Pearson đã lưu dùng centering/normalization trên từng cặp đoạn lag, không phải đúng ma trận autocovariance của Portmanteau. Không gán phần trăm đóng góp hay tuyên bố VIX là nguyên nhân duy nhất làm kiểm định thất bại. Có 500 ô tương quan mỗi hệ; ô lớn nhất là mô tả sau khi xem toàn bảng, không có ý nghĩa riêng chỉ vì đứng đầu.

## Kiểm định hệ đã lưu

{md(combined[['asset', 'regime', 'criterion', 'lag', 'nobs', 'whiteness_p20', 'whiteness_p30']])}

## Miền lag và việc thêm calendar controls

Tất cả lag search hiện có là 0–10, lag fit tối thiểu 1; BIC/AIC của các hệ kết hợp không chọn ở biên trên. Full: BIC 1/AIC 4; pre: 1/1; post: 1/2. Do đó, chưa có bằng chứng đơn giản rằng optimizer bị chặn ở lag 10. Tương quan ở 11/14 là lý do cân nhắc một sensitivity dài hơn, không chứng minh VAR(14/15) sẽ tốt hơn.

Weekday và gap đã được đưa vào phần **mean**, nhưng kiểm định hệ vẫn bác bỏ. Chúng không tự xử lý thay đổi variance theo độ dài khoảng, volatility clustering hoặc thay đổi cấu trúc. Không đủ dữ liệu chẩn đoán đã lưu để phân biệt các nguyên nhân này; không coi một kiểm định whiteness là chứng minh duy nhất của lỗi conditional mean.

## Rà soát cuối tuần và ghép phiên

{md(gaps)}

Mỗi khoảng đi từ mốc common observed levels trước đó đến mốc hiện tại; có thể dài 3–5 ngày quanh cuối tuần/lễ. Không điền 0 cho ngày thị trường Mỹ nghỉ, không xóa crypto weekend return. Dòng đầu mỗi panel cũng được đối chiếu với common level trước đó, không bỏ qua khỏi audit.

**Khoảng dài 6 ngày cần chú ý:** từ 21/01 đến 27/01/2016. Broad USD trống ngày 22, 25, 26/01 trong chính file raw `DTWEXBGS_fred.csv`, trong khi VIX, 2Y, 10Y có giá. Điều kiện common levels vì thế gom các ngày này vào một khoảng; ETH return khoảng +47,33%, BTC khoảng −3,65%. Không phải lỗi cộng return, nhưng độ dài bất thường và quan sát lớn cần xác minh nguồn/ảnh hưởng trước khi kết luận chỉ thiếu lag. Chưa kiểm tra lại nguồn online, chưa biết lý do nguồn trống và chưa biết mức ảnh hưởng lên fitted model.

`usd_missing_other_US_core_observed.csv` liệt kê các ngày USD trống mà ba biến Mỹ còn lại có giá; không tự gán tất cả cho ngày lễ hoặc lỗi nguồn. Chênh lệch std theo độ dài khoảng chỉ mang tính mô tả, với vài nhóm rất ít quan sát; chưa phải kiểm định variance hay ARCH.

Đây là căn chỉnh **khoảng ngày quan sát**, chưa phải căn chỉnh đúng cùng thời điểm intraday: crypto là UTC close, còn VIX/USD/yields là quan sát theo ngày của từng nguồn. Không có giá Mỹ đồng bộ tại UTC close trong audit này. Không suy ra kiểm tra telescoping đạt đã loại bỏ timing mismatch hay xác nhận causal ordering.

## Những gì chưa thể xác định trong phạm vi này

- Các chuỗi phần dư theo ngày và fitted model objects chưa được lưu riêng; chỉ có bảng tương quan/tổng kiểm định. Chưa đo được ARCH, ảnh hưởng từng ngày cực đoan, độ bền heteroskedasticity của kiểm định hay phân rã thống kê hệ.
- Phương sai thay đổi có thể ảnh hưởng suy luận theo các giả định của kiểm định; chưa kiểm tra thực nghiệm, không dùng khả năng này để bỏ qua việc bác bỏ hiện có.
- Calendar aggregation, asynchronous closes, long memory, breaks và sai đặc tả có thể cùng hiện diện. Audit không nhận diện duy nhất nguyên nhân.

## Đề xuất cụ thể để người dùng duyệt — CHƯA CHẠY

**Ưu tiên xác minh ba quan sát USD thiếu 01/2016 trên nguồn chính thức trước.** Chỉ đối chiếu và lưu nguồn riêng; nếu có thể khôi phục, trình bày lựa chọn có/không khôi phục và ảnh hưởng cách dựng khoảng để duyệt trước khi sửa panel. Không nội suy hoặc điền 0. Điểm này mới được phát hiện từ audit, chưa thực hiện xác minh online hay sửa dữ liệu.

**Sau khi chốt vấn đề nguồn, đề xuất một lượt sensitivity hữu hạn cho conditional mean, đồng thời lưu residual:**

1. Giữ đúng 5 biến, biến đổi, thứ tự, full/pre/post và weekday+gap hiện tại. Mở miền lag search duy nhất từ 0–10 lên **0–15**; giữ min fitted lag 1 và cả AIC/BIC. Đây là sensitivity do đã quan sát chẩn đoán, không phải mô hình được xác nhận trước mẫu.
2. Dùng cùng khoảng quan sát hữu hiệu cho các ứng viên trong việc chọn lag. Khi so IRF trước/sau, kiểm soát khác biệt mẫu bằng một bản tham chiếu fit trên cùng ngày; ghi rõ số quan sát/parameter, không quy tất cả thay đổi cho lag.
3. Đánh giá ổn định và Portmanteau tại **20/30/40 lags** cho tất cả mô hình đã chốt, không chọn horizon có p cao nhất. Lưu residual theo ngày; bổ sung chẩn đoán biến động và ảnh hưởng quan sát cần được quy định trước khi chạy lượt này. Không loại outlier tự động.
4. Không tăng tiếp lag hoặc đổi biến nếu vẫn bác bỏ. Khi đó báo giới hạn VAR, cân nhắc thiết kế khác như tần suất tuần hoặc inference thích hợp với volatility sau một đề xuất riêng. Bootstrap không tự sửa sai conditional mean.

Lượt sensitivity này chưa giải quyết nhận diện shock chính sách hay đồng bộ giá intraday; dù whiteness không bác bỏ cũng không đủ cho kết luận causal. LP/HAC có thể trình bày như conditional association hiện có, không tự động biến thành bằng chứng nhân quả hoặc được xác nhận bởi audit.

**Đề nghị phê duyệt bước ngay sau audit:** xác minh riêng ba ngày USD thiếu trên nguồn chính thức, giữ nguyên panel. Chưa xin chạy trọn lượt lag sensitivity: sau khi rõ nguồn và cách dựng mẫu, cần chốt danh sách chẩn đoán volatility/influence và cách suy luận trước khi fit. Chưa chạy bất cứ phần mở rộng nào trong lượt audit.

## Tái lập và nguồn

Chạy `py -3.11 audit_var_diagnostics.py`. Bảng đọc từ `outputs/research/var_calendar_extension/`, stationarity từ baseline, giá từ snapshot hiện có. `validation.json` lưu {validation['n_checks']} kiểm tra đối chiếu và hash của {len(validation['protected_sha256'])} file cũ; tất cả giữ nguyên.

Tham chiếu phương pháp: [statsmodels Portmanteau](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.var_model.VARResults.test_whiteness.html), [Ljung–Box và model_df](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html), [KPSS và p-value nội suy](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html). Xếp hạng, nhận định và đề xuất điều chỉnh ở đây là đánh giá của dự án, không phải khuyến nghị đặc tả từ tài liệu thư viện.
'''
    (OUT / 'report.md').write_text(text, encoding='utf-8')
    body = '<!doctype html><html lang="vi"><meta charset="utf-8"><title>VAR diagnostic audit</title><style>body{font:16px system-ui;margin:28px;color:#19374a}pre{white-space:pre-wrap;font:inherit}table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccd;padding:6px}th{background:#e5f0f4}</style><h1>Rà soát chẩn đoán VAR</h1><p>Chỉ đọc kết quả có sẵn; chưa fit lại mô hình. <a href="report.md">Đọc báo cáo và đề xuất đầy đủ</a>.</p>'
    body += '<h2>Chỉ báo riêng: full sample</h2>' + full_p.to_html(index=False)
    body += '<h2>Tương quan phần dư lớn: mô tả, chưa kiểm định từng ô</h2>' + full_top[cols].to_html(index=False)
    body += '<h2>Khoảng phiên và cuối tuần</h2>' + gaps.to_html(index=False)
    body += '<h2>Báo cáo đầy đủ</h2><pre>' + html.escape(text) + '</pre></html>'
    (OUT / 'report.html').write_text(body, encoding='utf-8')


if __name__ == '__main__':
    main()
