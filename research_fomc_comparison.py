"""Approved FOMC comparison: 2017-2022, scheduled meetings, two 30m windows.

No Target/Path/LSAP reconstruction or changes to existing model outputs.
Run with --download once; subsequent runs use the separately frozen raw cache.
"""
from research_common import *
import argparse, hashlib, datetime, time, html
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

OUT = RESULTS / 'fomc_comparison'
RAW = ROOT / 'data/raw/fomc_comparison'
WINDOWS = {'baseline_m10_p20': (-10, 20), 'nyfed_m5_p25': (-5, 25)}
SPECS = {'mp1_mp2': ['MP1_10bps', 'MP2_10bps'], 'sf_stmt': ['STMT_10bps']}
NYFED = 'https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1052.pdf'
SF = 'https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf'


def save(frame, name):
    frame.to_csv(OUT / (name + '.csv'), index=False, encoding='utf-8-sig', float_format='%.14g')


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def protected_hashes():
    files = list((ROOT / 'data').rglob('*')) + list(RESULTS.rglob('*'))
    files += list((ROOT / 'notebooks').rglob('*'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file() and OUT not in p.parents and RAW not in p.parents}


def candles(path):
    values = json.loads(path.read_bytes())
    assert isinstance(values, list)
    c = pd.DataFrame(values, columns=['time', 'low', 'high', 'open', 'close', 'volume'])
    assert not c.time.duplicated().any(), path
    if len(c):
        assert (c.close > 0).all() and (c.time % 60 == 0).all(), path
    return c.set_index('time').sort_index()


def extract(c, event, before, after):
    first = int((event + pd.Timedelta(minutes=before)).timestamp()) - 60
    last = int((event + pd.Timedelta(minutes=after)).timestamp()) - 60
    expected = list(range(first, last + 1, 60))
    complete = all(t in c.index for t in expected)
    endpoints = first in c.index and last in c.index
    return dict(first_candle_utc=pd.Timestamp(first, unit='s', tz='UTC').isoformat(),
                last_candle_utc=pd.Timestamp(last, unit='s', tz='UTC').isoformat(),
                expected_candles=len(expected), observed_required_candles=sum(t in c.index for t in expected),
                complete=complete, endpoints=endpoints,
                return_pct=float(100 * np.log(c.loc[last, 'close'] / c.loc[first, 'close'])) if endpoints else np.nan)


def fetch(row, asset, allow_download):
    dt = pd.Timestamp(row.date_time).tz_localize('America/New_York').tz_convert('UTC')
    p = RAW / f'{asset}_{dt.strftime("%Y%m%dT%H%M%S")}.json'
    meta = p.with_suffix('.meta.json')
    params = dict(granularity=60, start=(dt - pd.Timedelta(minutes=11)).isoformat(),
                  end=(dt + pd.Timedelta(minutes=25)).isoformat())
    url = f'https://api.exchange.coinbase.com/products/{asset}-USD/candles'
    request_url = requests.Request('GET', url, params=params).prepare().url
    if not p.exists():
        if not allow_download:
            raise RuntimeError('Missing cache; run with --download: ' + p.name)
        for attempt in range(3):
            try:
                r = requests.get(url, params=params, timeout=(10, 25), headers={'User-Agent': 'Academic research'})
                r.raise_for_status()
                assert isinstance(r.json(), list)
                p.write_bytes(r.content)
                meta.write_text(json.dumps(dict(url=request_url, retrieved_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                               sha256=hashlib.sha256(r.content).hexdigest()), indent=2), encoding='utf-8')
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
    md = json.loads(meta.read_text(encoding='utf-8'))
    assert md['sha256'] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert md['url'] == request_url
    c = candles(p)
    old_path = ROOT / 'data/raw/fomc_coinbase' / p.name
    old = candles(old_path)
    overlap = c.index.intersection(old.index)
    differences = int((c.loc[overlap, 'close'] != old.loc[overlap, 'close']).sum())
    records = []
    for name, (start, end) in WINDOWS.items():
        rec = dict(asset=asset, date=row.Date.date().isoformat(), event_time_et=pd.Timestamp(row.date_time).tz_localize('America/New_York').isoformat(),
                   event_time_utc=dt.isoformat(), unscheduled=int(row.Unscheduled), window=name,
                   MP1_10bps=float(row.MP1 * 10), MP2_10bps=float(row.MP2 * 10),
                   source_file=p.name, sha256=md['sha256'], **extract(c, dt, start, end))
        records.append(rec)
    audit = dict(asset=asset, date=row.Date.date().isoformat(), **md, source_file=p.name,
                 n_overlap_candles=len(overlap), n_changed_close= differences)
    return records, audit


def fit_block(g, asset, stage, window, family, estimates, influences, loo):
    # Both specifications use the same retained events, not spec-specific missingness.
    g = g.dropna(subset=['return_pct', 'MP1_10bps', 'MP2_10bps', 'STMT_10bps']).reset_index(drop=True)
    for spec, features in SPECS.items():
        x = sm.add_constant(g[features], has_constant='add')
        assert np.linalg.matrix_rank(x) == x.shape[1] and len(g) > x.shape[1] + 2
        model = sm.OLS(g.return_pct, x)
        ordinary = model.fit()
        fit = model.fit(cov_type='HC3')
        for term in features:
            ci = fit.conf_int().loc[term]
            estimates.append(dict(asset=asset, stage=stage, window=window, family=family, specification=spec, term=term,
                                  beta_return_pct_per10bps=fit.params[term], se_hc3=fit.bse[term], lower95=ci.iloc[0], upper95=ci.iloc[1],
                                  pvalue=fit.pvalues[term], nobs=int(fit.nobs), r_squared=fit.rsquared,
                                  design_condition_number=float(np.linalg.cond(x))))
        if family == 'primary_matched':
            influence = ordinary.get_influence()
            for i, row in g.iterrows():
                influences.append(dict(asset=asset, window=window, specification=spec, date=row.date,
                                       cooks_distance=influence.cooks_distance[0][i], leverage=influence.hat_matrix_diag[i],
                                       cooks_above_4_over_n=bool(influence.cooks_distance[0][i] > 4 / len(g))))
                keep = np.arange(len(g)) != i
                xx = x.loc[keep]
                assert np.linalg.matrix_rank(xx) == xx.shape[1]
                f = sm.OLS(g.loc[keep, 'return_pct'], xx).fit(cov_type='HC3')
                for term in features:
                    loo.append(dict(asset=asset, window=window, specification=spec, term=term, omitted_date=row.date,
                                    beta_return_pct_per10bps=f.params[term], pvalue=f.pvalues[term],
                                    change_from_full_beta=f.params[term] - fit.params[term]))
    return len(g)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    before = protected_hashes()
    design_path = OUT / 'design.json'
    design = dict(sample=['2017-01-01', '2022-12-31'], primary_meetings='USMPD Statements Unscheduled == 0',
                  assets=['BTC', 'ETH'], windows=WINDOWS, specifications=SPECS,
                  dependent_variable='100 * log(close_end / close_start), same as baseline',
                  boundaries='Candle timestamp is minute start. Price at boundary = close of minute immediately before boundary; no interpolation.',
                  complete='All 31 required endpoint-inclusive minute candles present per 30m window.',
                  primary_sample='Per asset intersection of both complete windows and nonmissing MP1/MP2/STMT; identical dates across windows and specs.',
                  covariance='HC3, normal-reference 95% CIs as baseline; not exact White implementation replication.',
                  multiple_testing='BH across 12 primary matched coefficient tests; bridge coefficients corrected as a separate descriptive family.',
                  bridge='Original frozen all events -> original scheduled -> refreshed scheduled, all 2017-2022, original window.',
                  influence='Cook distance and leave-one-event-out on every primary regression; no deletion or model selection.',
                  not_replication='Published shock vector and shock windows not reproduced; NY Fed simple percent return also differs from log return.',
                  nyfed_pdf=NYFED, usmpd_pdf=SF,
                  created_before_new_downloads_and_fits_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if not design_path.exists():
        write_json('design.json', design)
    else:
        prior = json.loads(design_path.read_text(encoding='utf-8'))
        assert all(prior[k] == json.loads(json.dumps(v)) for k, v in design.items() if k != 'created_before_new_downloads_and_fits_utc')
    sheet = pd.read_excel(ROOT / 'data/raw/USMPD.xlsx', sheet_name='Statements')
    sheet = sheet[sheet.Date.between('2017-01-01', '2022-12-31')].copy()
    assert not sheet.Date.duplicated().any()
    save(sheet, 'event_universe')
    scheduled = sheet[sheet.Unscheduled == 0]
    records, audits, errors = [], [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {pool.submit(fetch, row, asset, args.download): (str(row.Date.date()), asset)
                for _, row in scheduled.iterrows() for asset in ['BTC', 'ETH']}
        for i, future in enumerate(as_completed(jobs), 1):
            try:
                recs, audit = future.result()
                records.extend(recs)
                audits.append(audit)
            except Exception as exc:
                errors.append(dict(date=jobs[future][0], asset=jobs[future][1], error=str(exc)))
            if i % 20 == 0:
                print('FOMC comparison cache', i, '/', len(jobs), flush=True)
    write_json('download_errors.json', errors)
    if errors:
        raise RuntimeError('Download/cache errors saved; no regression run.')
    observations = pd.DataFrame(records).sort_values(['asset', 'date', 'window'])
    surprises = pd.read_csv(ROOT / 'data/processed/fomc_policy_surprises.csv')
    surprises['date'] = pd.to_datetime(surprises.Date).dt.strftime('%Y-%m-%d')
    observations = observations.merge(surprises[['date', 'STMT']], on='date', how='left', validate='many_to_one')
    observations['STMT_10bps'] = observations.STMT * 10
    save(observations, 'observations')
    save(pd.DataFrame(audits).sort_values(['asset', 'date']), 'source_log')
    original = pd.read_csv(ROOT / 'data/processed/fomc_crypto_statement_windows.csv')
    original['date'] = pd.to_datetime(original.event_time_utc, utc=True).dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
    original = original.merge(sheet[['Date', 'Unscheduled']].assign(date=sheet.Date.dt.strftime('%Y-%m-%d')).drop(columns='Date'),
                              on='date', how='inner', validate='many_to_one')
    original = original.merge(surprises[['date', 'STMT']], on='date', how='left', validate='many_to_one')
    original['return_pct'] = original.log_return * 100
    original['MP1_10bps'] = original.MP1_bps / 10
    original['MP2_10bps'] = original.MP2_bps / 10
    original['STMT_10bps'] = original.STMT * 10
    save(original, 'original_observations')
    rows, influence, loo, counts, membership = [], [], [], [], []
    for asset in ['BTC', 'ETH']:
        old = original[(original.asset == asset) & (original.status == 'complete')]
        refreshed = observations[(observations.asset == asset) & (observations.window == 'baseline_m10_p20') & observations.complete]
        for stage, g in [('original_all_events', old), ('original_scheduled', old[old.Unscheduled == 0]), ('refreshed_scheduled', refreshed)]:
            n = fit_block(g, asset, stage, 'baseline_m10_p20', 'bridge_descriptive', rows, influence, loo)
            counts.append(dict(asset=asset, stage=stage, window='baseline_m10_p20', nobs=n))
        full = observations[observations.asset == asset].copy()
        good = full.complete & full[['MP1_10bps', 'MP2_10bps', 'STMT_10bps', 'return_pct']].notna().all(axis=1)
        eligible = full.assign(eligible=good).groupby('date').eligible.agg(['all', 'count'])
        dates = eligible.index[eligible['all'] & (eligible['count'] == len(WINDOWS))]
        for day in full.date.unique():
            membership.append(dict(asset=asset, date=day, included=bool(day in dates)))
        for window in WINDOWS:
            g = full[(full.window == window) & full.date.isin(dates)]
            n = fit_block(g, asset, 'matched_scheduled', window, 'primary_matched', rows, influence, loo)
            counts.append(dict(asset=asset, stage='matched_scheduled', window=window, nobs=n))
    estimates = pd.DataFrame(rows)
    for family, group in estimates.groupby('family'):
        estimates.loc[group.index, 'qvalue_bh'] = multipletests(group.pvalue, method='fdr_bh')[1]
    save(estimates, 'regressions')
    save(pd.DataFrame(counts), 'sample_counts')
    save(pd.DataFrame(membership), 'matched_membership')
    save(pd.DataFrame(influence), 'influence')
    loo = pd.DataFrame(loo)
    save(loo, 'leave_one_out')
    ranges = loo.groupby(['asset', 'window', 'specification', 'term']).agg(
        min_beta=('beta_return_pct_per10bps', 'min'), max_beta=('beta_return_pct_per10bps', 'max'),
        min_raw_p=('pvalue', 'min'), max_raw_p=('pvalue', 'max'),
        max_absolute_beta_change=('change_from_full_beta', lambda x: x.abs().max())).reset_index()
    save(ranges, 'influence_ranges')
    # Compare the original and refreshed baseline window without silently overwriting old prices.
    revision = original[original.Unscheduled == 0][['asset', 'date', 'return_pct', 'status']].merge(
        observations[observations.window == 'baseline_m10_p20'][['asset', 'date', 'return_pct', 'complete']],
        on=['asset', 'date'], suffixes=('_original', '_refreshed'), validate='one_to_one')
    revision['return_change_pp'] = revision.return_pct_refreshed - revision.return_pct_original
    save(revision, 'snapshot_comparison')
    after = protected_hashes()
    assert before == after, 'Protected baseline/source file changed'
    write_json('validation.json', dict(protected_files_unchanged=True, protected_sha256=before,
               n_scheduled=len(scheduled), n_unscheduled=len(sheet) - len(scheduled), n_raw=len(audits),
               n_primary_tests=int((estimates.family == 'primary_matched').sum()),
               n_primary_raw_p_lt_05=int(((estimates.family == 'primary_matched') & (estimates.pvalue < .05)).sum()),
               n_primary_bh_q_lt_05=int(((estimates.family == 'primary_matched') & (estimates.qvalue_bh < .05)).sum()),
               n_changed_overlap_closes=int(sum(a['n_changed_close'] for a in audits)),
               design_sha256=hashlib.sha256(design_path.read_bytes()).hexdigest()))
    report(estimates, pd.DataFrame(counts), ranges, revision, scheduled, sheet)
    print(estimates[estimates.family == 'primary_matched'].to_string(index=False), flush=True)


def report(estimates, counts, ranges, revision, scheduled, universe):
    primary = estimates[estimates.family == 'primary_matched']
    audit = json.loads((OUT / 'validation.json').read_text(encoding='utf-8'))
    membership = pd.read_csv(OUT / 'matched_membership.csv')
    observations = pd.read_csv(OUT / 'observations.csv')
    descriptions, conclusions = [], []
    for asset in ['BTC', 'ETH']:
        days = membership[(membership.asset == asset) & membership.included].date
        g = observations[(observations.asset == asset) & (observations.window == 'nyfed_m5_p25') & observations.date.isin(days)]
        s = g.STMT_10bps * 10
        r = primary[(primary.asset == asset) & (primary.window == 'nyfed_m5_p25') & (primary.term == 'STMT_10bps')].iloc[0]
        descriptions.append(dict(asset=asset, nobs=len(g), stmt_min_bps=s.min(), stmt_max_bps=s.max(), stmt_sd_bps=s.std(ddof=1),
                                 fitted_return_pct_per_1sd_stmt=r.beta_return_pct_per10bps * s.std(ddof=1) / 10))
        conclusions.append(f'- {asset}, STMT, −5/+25: hệ số {r.beta_return_pct_per10bps:.3f}% log return / +10 bps; '
                           f'CI 95% [{r.lower95:.3f}; {r.upper95:.3f}], p={r.pvalue:.5f}, q={r.qvalue_bh:.5f}, n={int(r.nobs)}.')
    descriptions = pd.DataFrame(descriptions)
    save(descriptions, 'shock_scale_summary')
    key_findings = '\n'.join(conclusions)
    columns = ['asset', 'window', 'term', 'beta_return_pct_per10bps', 'lower95', 'upper95', 'pvalue', 'qvalue_bh', 'nobs']
    def markdown(frame):
        # No optional tabulate dependency.
        f = frame.copy()
        for c in f.select_dtypes(include='number'):
            f[c] = f[c].map(lambda x: f'{x:.6g}')
        return '| ' + ' | '.join(f.columns) + ' |\n| ' + ' | '.join(['---'] * len(f.columns)) + ' |\n' + '\n'.join('| ' + ' | '.join(map(str, row)) + ' |' for row in f.itertuples(index=False, name=None))
    narrative = f'''# Đối chiếu FOMC với New York Fed — 17/10/2026

Đây là đối chiếu cửa sổ/mẫu bằng surprise hiện có, **chưa phải replication đầy đủ**. Không thay baseline, VAR, LP hoặc forecasting.

## Thiết kế và phạm vi

- Khoảng ngày 2017–2022: {len(universe)} sự kiện trong USMPD, {len(scheduled)} định kỳ và {len(universe)-len(scheduled)} bất thường. Chọn định kỳ bằng cờ nguồn, không theo return hay p-value.
- Dùng cả BTC và ETH; bài gốc chỉ nghiên cứu Bitcoin. Cùng sự kiện trong từng tài sản cho cả hai cửa sổ và hai đặc tả surprise.
- Dữ liệu Coinbase tải thêm được lưu riêng; {audit['n_raw']} payload, {audit['n_changed_overlap_closes']} giá đóng phút khác snapshot cũ trên phần giao nhau. Chênh lệch return baseline lớn nhất: {revision.return_change_pp.abs().max():.6g} điểm phần trăm.
- Giá tại mốc phút lấy close của phút ngay trước mốc. Mỗi cửa sổ 30 phút yêu cầu 31 close liên tiếp, không nội suy. ET→UTC dùng America/New_York, xử lý DST.
- Giữ return log (%), OLS HC3, MP1+MP2 cùng hồi quy hoặc STMT riêng; hệ số theo surprise +10 bps. Không đổi thước đo return để tìm ý nghĩa.
- BH cho toàn bộ 12 kiểm định hệ số chính; bridge là nhóm mô tả riêng. CI là pointwise 95%, không phải CI đồng thời điều chỉnh BH. Đây là phân tích bổ sung sau khi đã xem baseline.

## Kết quả chính

Có {audit['n_primary_raw_p_lt_05']}/12 hệ số p<0,05 trước điều chỉnh và {audit['n_primary_bh_q_lt_05']}/12 hệ số q<0,05 sau BH. Cần đọc cả độ lớn và CI; không có ý nghĩa không chứng minh tác động bằng 0.

{key_findings}

Hai hệ số còn ý nghĩa sau BH đều thuộc STMT ở cửa sổ −5/+25. MP1/MP2 chưa có ý nghĩa trong cả hai cửa sổ; STMT ở −10/+20 có raw p<0,05 nhưng không còn q<0,05 trong nhóm chính. Vì vậy, dữ liệu cho thấy kết luận phụ thuộc thước đo surprise và cửa sổ, chưa hỗ trợ kết luận chung rằng crypto không phản ứng với FOMC.

{markdown(descriptions)}

Quy mô +10 bps là đơn vị trình bày hệ số tuyến tính, không phải một shock điển hình hay dự báo chắc chắn. Đọc cùng min/max và độ lệch chuẩn shock phía trên; hiệu ứng 1 SD cũng là fitted association. STMT là chuỗi công bố hiện tại, PCA/chuẩn hóa theo thiết kế nguồn có thể dùng thông tin ngoài 2017–2022; dùng cho phân tích ex post, không tuyên bố là surprise factor point-in-time tại năm 2022.

{markdown(primary[columns])}

## Số quan sát và bridge

{markdown(counts)}

`regressions.csv` giữ cả bridge: snapshot cũ tất cả sự kiện → snapshot cũ định kỳ → snapshot mới định kỳ. Bridge không phải ước lượng thuần hiệu ứng bất thường: số sự kiện và phân phối shock cũng đổi. So hai cửa sổ chính dùng đúng mẫu giao nhau, không trộn ảnh hưởng thay mẫu.

## Ảnh hưởng từng sự kiện

{markdown(ranges)}

`influence.csv` chứa leverage/Cook distance; ngưỡng 4/n chỉ là cờ rà soát. `leave_one_out.csv` bỏ lần lượt TẤT CẢ sự kiện để đo độ nhạy, không chọn bản bỏ quan sát nào làm kết quả chính. Min/max p trong bảng không được dùng như bằng chứng có ý nghĩa sau tìm kiếm. Mẫu nhỏ và shock ít biến thiên có thể làm CI rộng.

Với STMT ở −5/+25, tất cả hệ số leave-one-out vẫn âm và raw p<0,05 cho cả hai tài sản. Đây là độ bền với một sự kiện đơn lẻ, không chứng minh độ bền với mọi đặc tả, nhóm outlier hoặc điều chỉnh nhiều kiểm định của toàn bộ các lượt nghiên cứu. BH ở trên chỉ bao phủ 12 kiểm định trong lượt đối chiếu này.

Các ngày không vào mẫu matched: BTC 01/02/2017; ETH 01/02/2017 và 20/03/2019, do thiếu ít nhất một nến yêu cầu. Không coi các phút thiếu là return 0. Không có khác biệt giá close trên phần snapshot giao nhau; bridge snapshot cũ/mới vì thế trùng hệ số ở cửa sổ baseline.

## Bản đồ khác biệt với bài gốc

| Thành phần | New York Fed | Đối chiếu hiện tại |
| --- | --- | --- |
| Mẫu | BTC 2017–2022, định kỳ | Định kỳ 2017–2022; BTC và ETH riêng; số ngày bằng nhau không đảm bảo cùng vector shock |
| Cửa sổ return | −5/+25 phút | Cửa sổ đó và −10/+20 trên cùng ngày |
| Return | Percentage price change | Log return ×100 như baseline |
| Shock | Target, Path, LSAP | MP1, MP2; hoặc STMT, không thể đổi tên để coi là tương đương |
| Target/MP1 | Nhân tố target | MP1: surprise kỳ họp hiện tại; có liên hệ khái niệm nhưng không đồng nhất nhân tố |
| Path/MP2 | News đường đi chính sách ngoài target | MP2: thay đổi kỳ vọng kỳ họp kế tiếp, chưa trực giao với MP1 và không bao quát cả đường đi |
| STMT | Không thay thế bộ ba shock | PCA một chiều, chuẩn hóa theo lợi suất 1Y; gộp thông tin, không tách policy/information |
| LSAP | Shock dài hạn xây từ forward Treasury rate | Chưa có đúng chuỗi và phép dựng; UST10Y đơn lẻ không thay thế |
| Timing shock | Xây theo thiết kế bài | USMPD Statements đo −10/+20; khi chuyển return sang −5/+25, shock vẫn ở cửa sổ gốc. Chỉ là sensitivity của return |
| Sai số chuẩn | OLS heteroskedasticity-consistent | HC3; không khẳng định giống chính xác cách tính White trong bài |

Do khác shock và timing shock, phần này chỉ xác định mức nhạy với lựa chọn mẫu/cửa sổ. Không thể quy mọi khác biệt với bài gốc cho thời gian hay kết luận đã xác nhận/bác bỏ bài. Không tự tạo Target/Path/LSAP, mở press conference, thêm cửa sổ 1 giờ hoặc đổi mô hình.

## File và khả năng tái lập

Thiết kế lưu trước download/fit trong `design.json`; URL/thời gian tải/hash trong `source_log.csv`, raw cache trong `data/raw/fomc_comparison/`. `validation.json` lưu SHA-256 của {len(audit['protected_sha256'])} file nguồn/kết quả cũ, tất cả giữ nguyên.

```powershell
py -3.11 research_fomc_comparison.py --download
py -3.11 validate_fomc_comparison.py
```

Đã có cache thì bỏ `--download`; code không tự tải mới đè snapshot. Dữ liệu bổ sung này chỉ phục vụ event study, không dùng làm dữ liệu intraday cả ngày cho volatility.

Nguồn: [Benigno & Rosa, NY Fed Staff Report 1052]({NYFED}), phương trình (5), Bảng 4; [Acosta và cộng sự, bản sửa 2026]({SF}), mục 2.2–3.1. Diễn giải và đánh giá thiết kế trong báo cáo này là của dự án.
'''
    (OUT / 'report.md').write_text(narrative, encoding='utf-8')
    # Simple offline HTML; tables below contain all primary coefficients and bridge fits.
    intro = narrative.split('## Kết quả chính')[0]
    body = '<pre>' + html.escape(intro) + '</pre>'
    body += '<h2>Kết quả chính</h2><pre>' + html.escape(key_findings) + '</pre>'
    body += '<p>MP1/MP2 chưa có ý nghĩa ở cả hai cửa sổ. Hai hệ số STMT âm ở −5/+25 còn ý nghĩa sau BH cho 12 kiểm định của lượt này; ở −10/+20 thì không. Đây là kết quả bổ sung phụ thuộc đặc tả, không chứng minh causal effect hay replication đầy đủ.</p>'
    body += descriptions.to_html(index=False, float_format=lambda x: f'{x:.6g}')
    body += '<h2>Regressions: primary and descriptive bridge</h2>' + estimates.to_html(index=False, float_format=lambda x: f'{x:.6g}')
    body += '<h2>Sample counts</h2>' + counts.to_html(index=False)
    body += '<h2>Leave-one-out ranges (diagnostic only)</h2>' + ranges.to_html(index=False, float_format=lambda x: f'{x:.6g}')
    body += '<p>Not a full replication: shocks remain USMPD [-10,+20], no Target/Path/LSAP reconstruction. See the complete Vietnamese method and interpretation in <a href="report.md">report.md</a>.</p>'
    links = ['design.json', 'regressions.csv', 'observations.csv', 'sample_counts.csv', 'influence.csv', 'leave_one_out.csv', 'snapshot_comparison.csv', 'source_log.csv', 'validation.json']
    body += '<p>' + ' | '.join(f'<a href="{x}">{x}</a>' for x in links) + '</p>'
    (OUT / 'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>FOMC comparison</title><style>body{font:15px system-ui;margin:30px;color:#183344}pre{white-space:pre-wrap;font:inherit}table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccd;padding:6px}th{background:#e7f0f5}</style>' + body + '</html>', encoding='utf-8')


if __name__ == '__main__':
    main()
