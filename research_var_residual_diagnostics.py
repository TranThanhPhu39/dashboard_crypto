"""Approved ARCH and observation-influence diagnostics on frozen VAR residuals.

Baseline lag, response dates and observations remain unchanged. Case-deletion
fits are conditional sensitivity experiments, never replacement estimates.
"""
import os
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ.setdefault(key, '2')
from research_common import *
import hashlib, datetime, html
from statsmodels.stats.diagnostic import het_arch
from statsmodels.stats.multitest import multipletests

OUT = RESULTS / 'var_residual_diagnostics'
SOURCE = RESULTS / 'var_lag_sensitivity'
NAMES = ['vix_change', 'usd_return_pct', 'us2y_change_bps', 'us10y_change_bps', 'crypto_return_pct']
SHOCKS = {'vix_change': 5., 'usd_return_pct': 1., 'us2y_change_bps': 10., 'us10y_change_bps': 10.}
TARGET = '2016-01-27'


def save(df, name):
    df.to_csv(OUT / (name + '.csv'), index=False, encoding='utf-8-sig', float_format='%.14g')


def protected_hashes():
    files = list((ROOT / 'data').rglob('*')) + list(RESULTS.rglob('*')) + list((ROOT / 'notebooks').rglob('*'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file() and OUT not in p.parents}


def rebuild(item):
    panel = data(item.asset + '_econometric_sessions.csv')
    g = panel if item.regime == 'full' else panel.loc[:'2019-12-31'] if item.regime == 'pre2020' else panel.loc['2020-01-01':]
    p = int(item.lag); yy = g[NAMES].to_numpy()
    x = np.column_stack([np.ones(len(g)-15)] + [(g.index[15:].dayofweek == k).astype(float) for k in [1, 2, 3, 4]] + [g.elapsed_calendar_days.iloc[15:].to_numpy()-1])
    x = np.column_stack([x] + [yy[15-k:len(g)-k] for k in range(1, p+1)])
    terms = ['const', 'tuesday', 'wednesday', 'thursday', 'friday', 'extra_calendar_days'] + [f'L{k}.{c}' for k in range(1, p+1) for c in NAMES]
    return g.iloc[15:], x, yy[15:], terms


def response(beta, residual, p):
    n, k = len(residual), beta.shape[0]
    a = np.array([beta[6+5*j:6+5*(j+1)].T for j in range(p)])
    companion = np.zeros((5*p, 5*p)); companion[:5] = np.concatenate(a, axis=1)
    if p > 1: companion[5:, :-5] = np.eye(5*(p-1))
    eig = float(np.abs(np.linalg.eigvals(companion)).max())
    chol = np.linalg.cholesky(residual.T @ residual / (n-k))
    phi = [np.eye(5)]
    for h in range(1, 31):
        phi.append(sum(a[j-1] @ phi[h-j] for j in range(1, min(p, h)+1)))
    result = np.zeros((31, 4))
    for h in range(31):
        for j, size in enumerate(SHOCKS.values()):
            result[h, j] = (phi[h] @ chol)[4, j] * size / chol[j, j]
    return result, eig


def main():
    OUT.mkdir(exist_ok=True)
    before = protected_hashes()
    design = dict(assets=['btc', 'eth'], source='Frozen var_lag_sensitivity 10 unique fit IDs; no duplicate tests for repeated criterion/stage labels.',
                  arch_lags=[5, 10], arch_ddof='k = parameters per equation including constant/calendar controls = 6+5p',
                  arch_family='100 classical univariate ARCH-LM p-values: 10 systems x 5 equations x 2 lags; one BH family.',
                  arch_interpretation='Exploratory squared-residual dependence; classical p-values conditional on model/test assumptions, not robust to all remaining mean misspecification/heavy tails.',
                  influence='Leverage, internally studentized residuals, equationwise Cook distance; 4/n and 2k/n are descriptive screens only.',
                  case_selection='Top 3 distinct response dates per fit by maximum Cook across 5 equations, plus 2016-01-27 if present.',
                  sensitivity='For each selected date: conditional deletion of one original design row; also block of that row and next p rows, removing uses of event endogenous levels as lags without compressing time.',
                  scope='Fixed lag/control/order. Refit all five equations jointly by OLS with original lag matrix retained. No data deletion in original panels, lag reselection, or selection by significance.',
                  irf='Same 4 recursive shocks, horizons 0..30, conditional exog path; compare point curves, not new significance tests. Re-estimate residual covariance for each diagnostic fit.',
                  excluded='No whiteness test on compressed deletion samples, no ARCH/GARCH fit, bootstrap, new source downloads or forecast changes.',
                  started_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    dp = OUT / 'design.json'
    if dp.exists():
        prior = json.loads(dp.read_text(encoding='utf-8'))
        assert all(prior[k] == v for k, v in design.items() if k != 'started_at_utc')
    else: dp.write_text(json.dumps(design, indent=2), encoding='utf-8')
    inventory = pd.read_csv(SOURCE / 'fit_inventory.csv')
    residuals = pd.read_csv(SOURCE / 'residuals_by_date.csv')
    coefficients = pd.read_csv(SOURCE / 'coefficients.csv')
    baseline_irf = pd.read_csv(SOURCE / 'impulse_responses.csv')
    arch, screens, tops, target_rows, cases, changed_coefs, changed_irfs = [], [], [], [], [], [], []
    checks = {}
    for _, item in inventory.iterrows():
        g, x, y, terms = rebuild(item)
        p = int(item.lag); n, k = x.shape
        saved = residuals[residuals.fit_id == item.fit_id]
        beta = coefficients[coefficients.fit_id == item.fit_id].pivot(index='term', columns='equation', values='beta').loc[terms, NAMES].to_numpy()
        u = saved[NAMES].to_numpy()
        checks[item.fit_id + '_saved_residuals_replayed'] = bool(saved.date_utc.tolist() == g.index.strftime('%Y-%m-%d').tolist() and np.allclose(y-x@beta, u, atol=1e-10, rtol=1e-10))
        assert n == int(item.nobs) and np.linalg.matrix_rank(x) == k
        bread = np.linalg.inv(x.T @ x)
        leverage = np.einsum('ij,jk,ik->i', x, bread, x)
        assert np.all(leverage >= 0) and np.all(leverage < 1)
        sigma2 = np.sum(u*u, axis=0) / (n-k)
        internal = u / np.sqrt((1-leverage[:, None])*sigma2[None, :])
        cook = (u*u / (k*sigma2[None, :])) * (leverage / ((1-leverage)**2))[:, None]
        # Closed-form conditional single-row deletion, scaled with full-fit classical SE.
        se = np.sqrt(np.diag(bread)[:, None] * sigma2[None, :])
        influence_direction = x @ bread
        max_scaled_change = np.zeros(n)
        for i in range(n):
            delta = -np.outer(influence_direction[i], u[i]) / (1-leverage[i])
            max_scaled_change[i] = np.max(np.abs(delta / se))
        frame = pd.DataFrame(dict(fit_id=item.fit_id, date_utc=g.index.strftime('%Y-%m-%d'), asset=item.asset, regime=item.regime,
                                  lag=p, nobs=n, parameters_per_equation=k, elapsed_calendar_days=g.elapsed_calendar_days.to_numpy(),
                                  crypto_return_pct=g.crypto_return_pct.to_numpy(), leverage=leverage,
                                  max_cook=cook.max(axis=1), crypto_cook=cook[:, 4], crypto_internal_studentized=internal[:, 4],
                                  max_abs_internal_studentized=np.abs(internal).max(axis=1),
                                  max_abs_single_row_coef_change_in_full_classical_SE=max_scaled_change))
        for j, name in enumerate(NAMES): frame['cook_' + name] = cook[:, j]
        frame['max_cook_rank'] = frame.max_cook.rank(method='min', ascending=False).astype(int)
        frame['crypto_cook_rank'] = frame.crypto_cook.rank(method='min', ascending=False).astype(int)
        frame['max_cook_above_4_over_n'] = frame.max_cook > 4/n
        frame['leverage_above_2k_over_n'] = frame.leverage > 2*k/n
        screens.append(frame)
        tops.append(frame.sort_values(['max_cook', 'date_utc'], ascending=[False, True]).head(10))
        target_rows.append(frame[frame.date_utc == TARGET])
        for j, equation in enumerate(NAMES):
            for lag in [5, 10]:
                lm, pv, _, _ = het_arch(u[:, j], nlags=lag, ddof=k, result_object=False)
                arch.append(dict(fit_id=item.fit_id, asset=item.asset, regime=item.regime, var_lag=p, equation=equation,
                                 arch_lags=lag, residual_nobs=n, auxiliary_nobs=n-lag, ddof=k, lm_stat=lm, pvalue=pv))
        baseline, eigen = response(beta, u, p)
        reference = baseline_irf[baseline_irf.fit_id == item.fit_id]
        checks[item.fit_id + '_baseline_IRFs_replayed'] = bool(all(np.allclose(reference[reference.shock == name].sort_values('horizon_sessions').response_pct, baseline[:, j], atol=1e-10, rtol=1e-9) for j, name in enumerate(SHOCKS)))
        chosen = frame.sort_values(['max_cook', 'date_utc'], ascending=[False, True]).head(3).date_utc.tolist()
        if TARGET in set(frame.date_utc) and TARGET not in chosen: chosen.append(TARGET)
        for date in chosen:
            i = int(frame.index[frame.date_utc == date][0])
            row = frame.loc[i]
            for mode, count in [('single_response_row', 1), ('event_and_following_lag_rows', p+1)]:
                dropped = np.arange(i, min(n, i+count))
                keep = np.ones(n, dtype=bool); keep[dropped] = False
                assert np.linalg.matrix_rank(x[keep]) == k
                new_beta = np.linalg.lstsq(x[keep], y[keep], rcond=1e-15)[0]
                new_u = y[keep] - x[keep] @ new_beta
                new_irf, new_eigen = response(new_beta, new_u, p)
                case_id = item.fit_id + '_' + date + '_' + mode
                cases.append(dict(case_id=case_id, fit_id=item.fit_id, asset=item.asset, regime=item.regime, lag=p,
                                  selected_date=date, mode=mode, selection_reason='preidentified_2016_gap' if date == TARGET else 'top3_max_cook',
                                  max_cook_rank=int(row.max_cook_rank), crypto_cook_rank=int(row.crypto_cook_rank),
                                  max_cook=float(row.max_cook), crypto_cook=float(row.crypto_cook),
                                  n_removed=len(dropped), removed_first_date=frame.loc[dropped[0], 'date_utc'],
                                  removed_last_date=frame.loc[dropped[-1], 'date_utc'], nobs=n-len(dropped),
                                  baseline_max_eigenvalue=eigen, sensitivity_max_eigenvalue=new_eigen,
                                  stable=bool(new_eigen < 1), max_abs_irf_change_pp=float(np.abs(new_irf-baseline).max()),
                                  max_abs_coefficient_change_in_full_classical_SE=float(np.abs((new_beta-beta)/se).max())))
                for t, term in enumerate(terms):
                    for j, eq in enumerate(NAMES):
                        changed_coefs.append(dict(case_id=case_id, term=term, equation=eq, baseline_beta=beta[t, j], sensitivity_beta=new_beta[t, j], change=new_beta[t, j]-beta[t, j]))
                for h in range(31):
                    for j, name in enumerate(SHOCKS):
                        changed_irfs.append(dict(case_id=case_id, fit_id=item.fit_id, shock=name, horizon_sessions=h,
                                                 baseline_response_pct=baseline[h, j], sensitivity_response_pct=new_irf[h, j],
                                                 difference_pp=new_irf[h, j]-baseline[h, j]))
        print('Residual diagnostics completed:', item.fit_id, flush=True)
    arch = pd.DataFrame(arch); arch['qvalue_bh'] = multipletests(arch.pvalue, method='fdr_bh')[1]
    cases = pd.DataFrame(cases)
    for df, name in [(arch, 'arch_tests'), (pd.concat(screens, ignore_index=True), 'all_observation_screens'),
                     (pd.concat(tops, ignore_index=True), 'top_observations'), (pd.concat(target_rows, ignore_index=True), 'january2016_gap_screen'),
                     (cases, 'conditional_case_deletion'), (pd.DataFrame(changed_coefs), 'case_deletion_coefficients'),
                     (pd.DataFrame(changed_irfs), 'case_deletion_irfs')]: save(df, name)
    summary = arch.groupby(['asset', 'regime', 'equation', 'arch_lags'], as_index=False).agg(n_unique_fits=('fit_id', 'size'),
        n_reject_raw_05=('pvalue', lambda s: int((s < .05).sum())), n_reject_bh_05=('qvalue_bh', lambda s: int((s < .05).sum())))
    save(summary, 'arch_summary')
    checks['protected_files_unchanged'] = before == protected_hashes()
    result = dict(checks=checks, n_checks=len(checks), passed=int(sum(checks.values())), protected_sha256=before,
                  design_sha256=hashlib.sha256(dp.read_bytes()).hexdigest(), n_arch_tests=len(arch),
                  n_arch_raw_reject_05=int((arch.pvalue < .05).sum()), n_arch_bh_reject_05=int((arch.qvalue_bh < .05).sum()),
                  n_diagnostic_case_fits=len(cases), n_unstable_diagnostic_fits=int((~cases.stable).sum()),
                  max_abs_case_IRF_change_pp=float(cases.max_abs_irf_change_pp.max()),
                  no_primary_observations_deleted=True, no_lag_reselection=True)
    (OUT / 'validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    assert all(checks.values()), checks
    report(arch, pd.concat(tops), pd.concat(target_rows), cases, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ['protected_sha256', 'checks']}, indent=2), flush=True)


def report(arch, top, target, cases, result):
    def md(frame):
        f = frame.copy()
        for c in f.select_dtypes(include='number'): f[c] = f[c].map(lambda x: f'{x:.6g}')
        return '| ' + ' | '.join(f.columns) + ' |\n| ' + ' | '.join(['---']*len(f.columns)) + ' |\n' + '\n'.join('| ' + ' | '.join(map(str, r)) + ' |' for r in f.itertuples(index=False, name=None))
    crypto = arch[arch.equation == 'crypto_return_pct']
    focus = top[top.regime == 'full'].groupby('fit_id').head(3)
    gap_cases = cases[cases.selected_date == TARGET]
    responses = pd.read_csv(OUT / 'case_deletion_irfs.csv')
    largest = responses.loc[responses.difference_pp.abs().idxmax()]
    details = cases[cases.case_id == largest.case_id].iloc[0]
    findings = dict(n_arch_bh_reject=result['n_arch_bh_reject_05'], n_arch_tests=result['n_arch_tests'],
                    n_crypto_arch_bh_reject=int((crypto.qvalue_bh < .05).sum()), n_crypto_arch_tests=len(crypto),
                    largest_case=details.case_id, largest_case_date=details.selected_date,
                    largest_case_asset=details.asset, largest_case_regime=details.regime,
                    largest_case_shock=largest.shock, largest_case_horizon=int(largest.horizon_sessions),
                    largest_case_baseline_response_pct=float(largest.baseline_response_pct),
                    largest_case_sensitivity_response_pct=float(largest.sensitivity_response_pct),
                    largest_case_difference_pp=float(largest.difference_pp),
                    january2016_max_eth_full_change_pp=float(gap_cases[(gap_cases.asset == 'eth') & (gap_cases.regime == 'full')].max_abs_irf_change_pp.max()),
                    january2016_max_eth_pre_change_pp=float(gap_cases[(gap_cases.asset == 'eth') & (gap_cases.regime == 'pre2020')].max_abs_irf_change_pp.max()))
    (OUT / 'headline_findings.json').write_text(json.dumps(findings, indent=2), encoding='utf-8')
    text = f'''# VAR: ARCH và ảnh hưởng quan sát — 17/10/2026

Chẩn đoán thăm dò từ **10 fitted systems khác nhau**, không lặp kiểm định theo các nhãn BIC/AIC/stage dùng cùng fit. Giữ nguyên dữ liệu, lag, controls, thứ tự và kết quả chính. Thiết kế được lưu trước khi chạy trong `design.json`.

## Những điều đã xác định

- Bình phương phần dư có dấu hiệu phụ thuộc theo thời gian ở toàn bộ các hệ/phương trình được kiểm tra theo ARCH-LM cổ điển. Không đủ cơ sở coi sai số có độ biến động cố định; cũng chưa thể quy toàn bộ vấn đề cho ARCH vì mean dynamics còn hạn chế.
- Khoảng 01/2016 có ảnh hưởng cao trong phương trình ETH: Cook rank 1 ở full p=1 và pre, rank 2 ở full p=4. Đây là xếp hạng theo diagnostic, không phải p-value.
- Với riêng khoảng đó, chênh lệch IRF lớn nhất ở ETH full khoảng {findings['january2016_max_eth_full_change_pp']:.3f} điểm phần trăm, ETH pre khoảng {findings['january2016_max_eth_pre_change_pp']:.3f}. Ngày này đáng công bố sensitivity nhưng không phải quan sát gây thay đổi lớn nhất trong toàn bộ các trường hợp đã kiểm tra.
- Cực đại là {details.selected_date}, {details.asset.upper()} {details.regime}, {largest.shock}, h={int(largest.horizon_sessions)}: baseline {largest.baseline_response_pct:.3f}% → diagnostic {largest.sensitivity_response_pct:.3f}%, chênh {largest.difference_pp:.3f} điểm phần trăm. Đây là refit bỏ block có điều kiện đã chọn theo Cook, không phải kết quả thay thế.

## ARCH: phụ thuộc trong bình phương phần dư

{result['n_arch_bh_reject_05']}/{result['n_arch_tests']} kiểm định có q<0,05 sau BH; trước BH là {result['n_arch_raw_reject_05']}/{result['n_arch_tests']}. Riêng phương trình crypto: {int((crypto.qvalue_bh < .05).sum())}/{len(crypto)} kiểm định còn ý nghĩa sau BH.

{md(crypto[['fit_id', 'arch_lags', 'lm_stat', 'pvalue', 'qvalue_bh']])}

ARCH-LM ở 5 và 10 phiên; auxiliary regression của u² trên constant và các lag u². `ddof=6+5p`, bằng số tham số mỗi phương trình mean kể cả controls. BH dùng chung 100 p-value LM, không phải điều chỉnh toàn bộ các lượt nghiên cứu. Các hệ full/subsample và các tài sản phụ thuộc nhau; không coi số lượt bác bỏ là các bằng chứng độc lập.

Đây là p-value tiệm cận cổ điển. Conditional mean VAR vẫn có hạn chế whiteness, dữ liệu nhiều đuôi dày/biến động; ARCH test có thể chịu ảnh hưởng misspecification còn lại. Bác bỏ gợi ý phụ thuộc của độ lớn sai số, không chứng minh mô hình ARCH/GARCH cụ thể là đúng, không xác định riêng ARCH so với breaks/calendar effects. Không bác bỏ cũng không loại trừ mọi dạng heteroskedasticity. Chưa có robust calibration/bootstrap và chưa fit variance model.

## Quan sát nổi bật theo Cook — full sample

{md(focus[['fit_id', 'date_utc', 'leverage', 'max_cook', 'crypto_cook', 'crypto_cook_rank']])}

Leverage dùng ma trận các biến giải thích đã đóng băng; Cook tính riêng từng phương trình. `max_cook` lấy lớn nhất của 5 phương trình để rà soát cả macro và crypto, không phải multi-equation Cook được hiệu chỉnh đặc biệt cho VAR. 4/n và 2k/n chỉ là cờ sàng lọc, không phải kiểm định hay lý do xóa dòng. Studentization và SE dùng scale cổ điển của fit gốc để so độ nhạy, không dùng làm kiểm định robust mới.

## Khoảng 6 ngày 01/2016

{md(target[['fit_id', 'date_utc', 'elapsed_calendar_days', 'crypto_return_pct', 'crypto_internal_studentized', 'leverage', 'max_cook_rank', 'crypto_cook_rank']])}

Ngày 27/01/2016 đại diện return từ 21/01 đến 27/01, không phải một ngày ETH tăng 47%. Phần dư lớn và ảnh hưởng hệ số là hai khái niệm khác nhau; đọc cùng leverage, rank và các phép sensitivity dưới đây.

{md(gap_cases[['fit_id', 'mode', 'n_removed', 'stable', 'max_abs_irf_change_pp', 'max_abs_coefficient_change_in_full_classical_SE']])}

## Cách kiểm tra ảnh hưởng lên hệ số và IRF

Chọn ba ngày có max Cook cao nhất mỗi fit, cộng ngày 27/01/2016 nếu có; đây là lựa chọn dựa trên chẩn đoán, không phải một kiểm định xác nhận độc lập. Có {result['n_diagnostic_case_fits']} diagnostic fits, trong đó {result['n_unstable_diagnostic_fits']} không ổn định. Chênh lệch IRF lớn nhất trong nhóm đã chọn, trên 4 shocks và 0–30 phiên: {result['max_abs_case_IRF_change_pp']:.6g} điểm phần trăm. Không gán giá trị cực đại sau sàng lọc là tác động nhân quả hay độ tin cậy xác suất.

- `single_response_row`: bỏ một hàng của bài toán OLS, giữ nguyên mọi hàng lag/design khác. Đây là ảnh hưởng có điều kiện vào X, không mô phỏng xóa hẳn sự kiện khỏi lịch sử.
- `event_and_following_lag_rows`: bỏ hàng sự kiện và tối đa p hàng sau, vì giá trị endogenous của sự kiện xuất hiện như predictor ở các hàng đó. Giữ nguyên lịch và lag matrix; không dồn các ngày còn lại thành lags mới. Cách này vẫn không loại toàn bộ tác động lan truyền của sự kiện hay calendar controls của khoảng tiếp theo.
- Giữ lag/order/controls; ước lượng lại covariance cho từng diagnostic fit nên thay đổi IRF phản ánh cả dynamics và shock orthogonalization. Không báo CI/p-value mới cho các phép xóa được chọn theo dữ liệu.
- Không kiểm định whiteness sau khi nén các mẫu có lỗ: lag của residual lúc đó có thể đổi nghĩa. Không chọn bản bỏ dòng nào làm mô hình thay thế. Kết quả whiteness gốc vẫn giữ nguyên.

Tệp `conditional_case_deletion.csv` có mọi trường hợp, `case_deletion_coefficients.csv` có hệ số trước/sau, `case_deletion_irfs.csv` có mọi horizon để kiểm tra thay vì chỉ nhìn cực đại. Các diagnostic fits không sửa panel, không loại outlier khỏi nghiên cứu chính, không chọn lại lag.

## Ý nghĩa đối với bước nghiên cứu tiếp theo

Đọc ARCH cùng influence để phân biệt dấu hiệu volatility clustering với sự phụ thuộc vào vài hàng thiết kế; hai chẩn đoán có thể cùng tồn tại. Chúng chưa sửa được whiteness và chưa xác nhận causal IRF. Việc đổi covariance/inference, fit GARCH, dùng tuần hoặc thay đặc tả cần một thiết kế tiếp theo được thống nhất; chưa thực hiện trong lượt này.

Hiện tại nên giữ VAR như phân tích bổ sung có giới hạn, báo rõ sensitivity thay vì tiếp tục tăng lag hoặc xóa ngày để đạt kiểm định. ARCH/influence cho thấy cần cân nhắc cách suy luận chịu phương sai thay đổi và độ bền với quan sát, nhưng robust SE/bootstrap không tự sửa sai mean dynamics. LP/HAC và FOMC hiện có cũng phải giữ các giới hạn nhận diện riêng; không tự nâng chúng thành bằng chứng causal vì VAR gặp vấn đề.

## Tái lập và nguồn phương pháp

```powershell
py -3.11 research_var_residual_diagnostics.py
py -3.11 validate_var_residual_diagnostics.py
```

`validation.json` đối chiếu hash của {len(result['protected_sha256'])} file nghiên cứu cũ: tất cả giữ nguyên. Đạt kiểm tra tính toán không có nghĩa các giả định thống kê đã đạt.

Tham khảo chính thức: [ARCH-LM và ddof](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.het_arch.html), [Cook's distance](https://www.statsmodels.org/stable/generated/statsmodels.stats.outliers_influence.OLSInfluence.cooks_distance.html). Thiết kế sàng lọc và các giới hạn diễn giải ở đây là đánh giá của dự án.
'''
    (OUT / 'report.md').write_text(text, encoding='utf-8')
    body = '<!doctype html><html lang="vi"><meta charset="utf-8"><title>VAR residual diagnostics</title><style>body{font:15px system-ui;margin:28px;color:#193747}pre{white-space:pre-wrap;font:inherit}table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccd;padding:7px}th{background:#e6f0f5}</style><h1>ARCH và ảnh hưởng quan sát</h1>'
    body += '<p>Chẩn đoán thăm dò; dữ liệu và mô hình chính giữ nguyên.</p>' + crypto.to_html(index=False, float_format=lambda x: f'{x:.5g}')
    body += '<p><a href="report.md">Báo cáo</a> | <a href="arch_tests.csv">ARCH tests</a> | <a href="conditional_case_deletion.csv">Sensitivity</a> | <a href="validation.json">Kiểm tra</a></p><pre>' + html.escape(text) + '</pre></html>'
    (OUT / 'report.html').write_text(body, encoding='utf-8')


if __name__ == '__main__': main()
