"""Verify three USD missing observations against official sources; never edit panels."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import sys, json, hashlib, datetime, time, io
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.research_deps'))
import pandas as pd
import numpy as np
import requests

OUT = ROOT / 'outputs/research/usd_missing_verification'
RAW = ROOT / 'data/raw/usd_missing_verification'
TARGET = ['2016-01-22', '2016-01-25', '2016-01-26']
SOURCES = {
    'fred_broad.csv': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS&cosd=2016-01-18&coed=2016-01-29',
    'fred_legacy.csv': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXB&cosd=2016-01-18&coed=2016-01-29',
    'fed_broad.html': 'https://www.federalreserve.gov/releases/h10/summary/jrxwtfb_nb.htm',
    'fed_legacy.html': 'https://www.federalreserve.gov/releases/h10/summary/v0.jrxwtfb_nb.htm',
    'fed_20160127.html': 'https://www.federalreserve.gov/releases/h10/20160127/',
    'fed_20160201.html': 'https://www.federalreserve.gov/releases/h10/20160201/',
    'fed_announcements.html': 'https://www.federalreserve.gov/feeds/h10.html',
    'fred_broad_metadata.html': 'https://fred.stlouisfed.org/series/DTWEXBGS',
    'fred_legacy_metadata.html': 'https://fred.stlouisfed.org/series/DTWEXB',
    'fed_index_definitions.html': 'https://www.federalreserve.gov/releases/h10/summary/default.htm',
}


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = []; self.row = None; self.cell = None
    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row = []
        if tag in ('td', 'th') and self.row is not None: self.cell = []
    def handle_data(self, value):
        if self.cell is not None: self.cell.append(value)
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row); self.row = None


def rows(name):
    parser = Tables(); parser.feed((RAW / name).read_text(encoding='utf-8', errors='replace'))
    return parser.rows


def hashes():
    paths = list((ROOT / 'data').rglob('*')) + list((ROOT / 'outputs/research').rglob('*'))
    paths += list((ROOT / 'notebooks').rglob('*'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file() and RAW not in p.parents and OUT not in p.parents}


def fetch(item):
    name, url = item; p = RAW / name; meta = p.with_suffix(p.suffix + '.meta.json')
    if not p.exists():
        for attempt in range(2):
            try:
                r = requests.get(url, timeout=(5, 15), headers={'User-Agent': 'Academic research source verification'})
                r.raise_for_status()
                assert len(r.content) > 50
                if name.endswith('.csv'): assert b'DTWEXB' in r.content[:250], r.content[:100]
                else: assert b'<html' in r.content.lower()[:1500]
                p.write_bytes(r.content)
                m = dict(file=name, requested_url=url, final_url=r.url, status_code=r.status_code,
                         retrieved_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         bytes=len(r.content), sha256=hashlib.sha256(r.content).hexdigest())
                meta.write_text(json.dumps(m, indent=2), encoding='utf-8')
                break
            except Exception as exc:
                print('Source attempt failed:', name, type(exc).__name__, flush=True)
                if attempt == 1:
                    return dict(file=name, requested_url=url, status='download_failed', error=str(exc), checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
                time.sleep(1 + attempt)
    m = json.loads(meta.read_text(encoding='utf-8'))
    assert m['sha256'] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert m['requested_url'] == url
    print('Verified source cache:', name, flush=True)
    return m


def main():
    OUT.mkdir(exist_ok=True); RAW.mkdir(exist_ok=True)
    before = hashes()
    # Official HTML first; CSV endpoints may time out independently.
    ordered = sorted(SOURCES.items(), key=lambda x: x[0].endswith('.csv'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        logs = list(pool.map(fetch, ordered))
    (OUT / 'source_log.json').write_text(json.dumps(logs, indent=2), encoding='utf-8')
    for required in ['fed_broad.html', 'fed_legacy.html', 'fed_20160127.html', 'fed_20160201.html', 'fed_announcements.html']:
        assert (RAW / required).exists(), 'Required official evidence unavailable: ' + required
    fresh = pd.read_csv(RAW / 'fred_broad.csv', index_col=0) if (RAW / 'fred_broad.csv').exists() else None
    legacy = pd.read_csv(RAW / 'fred_legacy.csv', index_col=0) if (RAW / 'fred_legacy.csv').exists() else None
    old = pd.read_csv(ROOT / 'data/raw/DTWEXBGS_fred.csv', index_col=0)
    daily = pd.read_csv(ROOT / 'data/processed/daily_research_latest.csv', index_col='date_utc')
    official = {}
    for name in ['fed_broad.html', 'fed_legacy.html']:
        values = {}
        for row in rows(name):
            if len(row) != 2: continue
            try: date = datetime.datetime.strptime(row[0], '%d-%b-%y').date().isoformat()
            except ValueError: continue
            assert date not in values
            values[date] = row[1]
        assert all(d in values for d in TARGET)
        official[name] = values
    historical = {}
    for name, dates in [('fed_20160127.html', pd.date_range('2016-01-18', periods=5)),
                         ('fed_20160201.html', pd.date_range('2016-01-25', periods=5))]:
        broad = [r for r in rows(name) if r and 'BROAD' in r[0].upper()]
        assert len(broad) == 1, broad
        row = broad[0]
        assert len(row) == 7 and 'JAN97' in row[1].replace(' ', '').upper(), row
        for d, value in zip(dates, row[2:]):
            historical[d.date().isoformat()] = dict(value=float(value) if value != 'ND' else np.nan,
                                                   vintage_release='2016-01-27' if name == 'fed_20160127.html' else '2016-02-01',
                                                   evidence_file=name)
    records = []
    for day in TARGET:
        h = historical[day]
        records.append(dict(date=day, original_DTWEXBGS=old.loc[day].iloc[0],
                            fresh_DTWEXBGS=fresh.loc[day].iloc[0] if fresh is not None else np.nan,
                            fresh_fred_status='downloaded' if fresh is not None else 'not_retrieved',
                            current_fed_broad_status=official['fed_broad.html'][day],
                            current_fred_DTWEXB=legacy.loc[day].iloc[0] if legacy is not None else np.nan,
                            fresh_fred_legacy_status='downloaded' if legacy is not None else 'not_retrieved',
                            current_fed_legacy_status=official['fed_legacy.html'][day],
                            historical_goods_only_broad=h['value'], historical_release=h['vintage_release'],
                            evidence_file=h['evidence_file'], baseline_compatible_fill=False))
    comparison = pd.DataFrame(records)
    comparison.to_csv(OUT / 'comparison.csv', index=False, encoding='utf-8-sig')
    context = old.loc['2016-01-18':'2016-01-29'].rename(columns={old.columns[0]: 'original_DTWEXBGS'})
    if fresh is not None:
        context = context.join(fresh.rename(columns={fresh.columns[0]: 'fresh_DTWEXBGS'}), how='left')
    context.to_csv(OUT / 'surrounding_dates.csv', encoding='utf-8-sig')
    intervals = pd.read_csv(ROOT / 'outputs/research/var_diagnostic_audit/all_session_interval_checks.csv')
    affected = intervals[(intervals.previous_session == '2016-01-21') & (intervals.session == '2016-01-27')]
    affected.to_csv(OUT / 'affected_intervals_existing.csv', index=False, encoding='utf-8-sig')
    announcement = ' '.join((RAW / 'fed_announcements.html').read_text(encoding='utf-8').split())
    checks = dict(
        all_three_original_values_missing=old.loc[TARGET].isna().all().all(),
        all_three_fed_current_broad_ND=all(official['fed_broad.html'][d] == 'ND' for d in TARGET),
        all_three_fed_current_legacy_also_ND=all(official['fed_legacy.html'][d] == 'ND' for d in TARGET),
        historical_releases_have_numeric_goods_only_values=comparison.historical_goods_only_broad.notna().all(),
        baseline_three_days_USD_missing_other_US_variables_present=daily.loc[TARGET, 'broad_usd'].isna().all() and daily.loc[TARGET, ['vix', 'us2y', 'us10y']].notna().all().all(),
        two_affected_six_day_intervals_unchanged=len(affected) == 2 and affected.elapsed_calendar_days.eq(6).all(),
        official_closure_notices_for_Jan25_Jan26='January 25, 2016' in announcement and 'January 26, 2016' in announcement and 'inclement weather' in announcement,
        fed_current_broad_matches_existing_surrounding_observations=all(np.isclose(float(official['fed_broad.html'][d]), float(old.loc[d].iloc[0])) for d in ['2016-01-20', '2016-01-21', '2016-01-27', '2016-01-28', '2016-01-29']),
        all_existing_sources_and_results_unchanged=before == hashes(),
    )
    if fresh is not None:
        checks['all_three_fresh_fred_values_missing'] = fresh.loc[TARGET].isna().all().all()
        checks['original_and_fresh_fred_match_surrounding_dates'] = np.allclose(context.original_DTWEXBGS, context.fresh_DTWEXBGS, equal_nan=True)
    if legacy is not None:
        checks['all_three_fresh_legacy_fred_values_missing'] = legacy.loc[TARGET].isna().all().all()
    result = dict(checks={k: bool(v) for k, v in checks.items()}, n_checks=len(checks), passed=int(sum(checks.values())),
                  protected_sha256=before, no_panel_edits=True, no_model_fits=True,
                  fresh_fred_downloaded=fresh is not None, fresh_fred_legacy_downloaded=legacy is not None,
                  conclusion='Missing confirmed at current official Fed source; old-vintage goods-only numbers are not direct replacements for DTWEXBGS.')
    (OUT / 'validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    assert all(checks.values()), checks
    report(comparison, result, logs)
    print(comparison.to_string(index=False), flush=True)
    print('Verification checks:', result['passed'], '/', result['n_checks'], flush=True)


def report(comparison, result, logs):
    links = {name: url for name, url in SOURCES.items()}
    fred_status = 'Đã tải lại CSV FRED, xác nhận cả ba ngày trống và các ngày xung quanh khớp snapshot.' if result['fresh_fred_downloaded'] else 'Endpoint CSV FRED tải mới không thành công trong thời gian chờ hữu hạn; không coi việc tải thất bại là bằng chứng missing. Kết luận missing dựa vào bảng Fed hiện hành tải được và snapshot FRED gốc. Cột fresh_FRED không khả dụng được ghi rõ not_retrieved, không đồng nhất với missing observation.'
    selected = comparison[['date', 'current_fed_broad_status', 'current_fed_legacy_status', 'historical_goods_only_broad', 'historical_release']]
    table = '| ' + ' | '.join(selected.columns) + ' |\n| ' + ' | '.join(['---'] * len(selected.columns)) + ' |\n' + '\n'.join('| ' + ' | '.join(map(str, r)) + ' |' for r in selected.itertuples(index=False, name=None))
    note = f'''# Xác minh nguồn cho ba ngày broad USD thiếu — 17/10/2026

**Kết luận: chưa có giá trị thay thế cùng chuỗi DTWEXBGS được xác minh; giữ nguyên missing và panel.** Không nội suy, không nối legacy index, không chạy lại mô hình.

## Bằng chứng chính thức

{table}

- [Bảng broad USD hiện hành của Fed]({links['fed_broad.html']}) ghi ND ở cả ba ngày; năm điểm quanh khoảng thiếu khớp snapshot đang dùng.
- [Bảng goods-only hiện hành]({links['fed_legacy.html']}) cũng ghi ND. Vì thế, đổi sang latest legacy không tự cung cấp ba quan sát này.
- [H.10 công bố 27/01/2016]({links['fed_20160127.html']}) và [H.10 công bố 01/02/2016]({links['fed_20160201.html']}) có các con số trong bảng, nhưng là broad index cũ, base JAN97=100, thuộc vintage công bố lúc đó.
- [FRED mô tả DTWEXB]({links['fred_legacy_metadata.html']}) là goods only, base Jan 1997; [DTWEXBGS]({links['fred_broad_metadata.html']}) dùng base Jan 2006. [Fed liệt kê hai họ chỉ số riêng]({links['fed_index_definitions.html']}). Khác biệt không chỉ là đơn vị index mà còn phạm vi/trọng số; không lấy giá trị từ họ cũ điền vào chuỗi mới bằng đổi base đơn giản.

Các trang archive cho biết ngày công bố; số liệu cũ tồn tại không có nghĩa chúng là đúng vintage hoặc đúng methodology của chuỗi mới. Không suy ra DTWEXBGS đã được biết vào năm 2016 từ các bảng archive này.

## Nguyên nhân khoảng thiếu: điều gì đã biết?

[Thông báo Fed]({links['fed_announcements.html']}) xác nhận văn phòng đóng cửa do thời tiết ngày 25–26/01/2016 và lùi lịch H.10. Thông báo đó nói về lịch phát hành, không giải thích trực tiếp vì sao lịch sử hiện hành để ND cả ngày 22/01 và hai ngày sau. Bản công bố bị lùi vẫn có số liệu cho chỉ số cũ. Do đó, **chưa xác minh được nguyên nhân đầy đủ của ba missing observations**; không gán chắc chắn cho bão tuyết hay lỗi tải dữ liệu.

## Trạng thái tải và khả năng kiểm chứng

{fred_status}

`source_log.json` lưu kết quả từng URL, thời gian, hash, số byte hoặc lỗi tải. Các HTML tải thành công được lưu nguyên trạng dưới `data/raw/usd_missing_verification/`. Tình trạng nguồn online có thể thay đổi; báo cáo này gắn với snapshot xác minh đã lưu, không khẳng định các giá trị sẽ mãi thiếu.

## Ảnh hưởng đối với thiết kế hiện tại

- Panel common-session vẫn có khoảng 21–27/01/2016 dài 6 ngày: ETH log return khoảng +47,33%, BTC khoảng −3,65%. Phép cộng return đúng; đây là khoảng dữ liệu quan sát không đều cần công bố.
- Không có căn cứ xóa riêng khoảng này hoặc khôi phục bằng giá trị khác chỉ số. Chưa đo ảnh hưởng lên phần dư/IRF nên không quy việc VAR bác bỏ whiteness cho duy nhất khoảng này.
- Baseline không MOVE, mẫu lịch sử đầy đủ, cấu hình forecasting không USD mẫu dài và USD vintage từ 2019 đều giữ nguyên. Việc xác minh năm 2016 không mở rộng vintage USD forecasting về trước 2019.

## Đề xuất bước sau — chưa chạy

Giữ missing và dữ liệu gốc. Trước khi ước lượng lại, chốt thiết kế sensitivity hữu hạn cho VAR (miền lag 0–15, AIC/BIC, weekday+gap, cùng mẫu khi so sánh; kiểm định ở 20/30/40) và cách lưu/kiểm tra residual theo ngày. Phần influence/volatility cần một đặc tả chẩn đoán cụ thể trước khi thực hiện. Không tự động loại outlier, đổi tần suất, điền giá hay thay loss forecasting.

## Kiểm tra tính toàn vẹn

{result['passed']}/{result['n_checks']} kiểm tra đối chiếu đạt; hash của {len(result['protected_sha256'])} file dữ liệu/kết quả cũ giữ nguyên. Đây là kiểm tra nguồn và tính toàn vẹn, không phải kiểm định mô hình đạt yêu cầu. Script: `py -3.11 verify_usd_missing_source.py` tái dùng các payload thành công đã lưu; nguồn tải thất bại có thể được thử lại và được ghi trạng thái riêng.
'''
    (OUT / 'report.md').write_text(note, encoding='utf-8')
    import html
    body = '<!doctype html><html lang="vi"><meta charset="utf-8"><title>USD missing source verification</title><style>body{font:16px system-ui;max-width:1200px;margin:30px;color:#193747}pre{white-space:pre-wrap;font:inherit}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:8px}</style><h1>Xác minh ba ngày USD thiếu</h1>'
    body += selected.to_html(index=False) + '<p><a href="report.md">Báo cáo đầy đủ</a> | <a href="source_log.json">Nguồn và hash</a> | <a href="validation.json">Kiểm tra</a></p><pre>' + html.escape(note) + '</pre></html>'
    (OUT / 'report.html').write_text(body, encoding='utf-8')


if __name__ == '__main__': main()
