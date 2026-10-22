"""Make a self-contained reading copy without changing the frozen report.

The public checkout omits the original figure files and their underlying series.
Charts here use only the rounded, published HTML tables. They are explicitly
labelled as alternative summaries; unavailable intervals/paths are never inferred.
"""
from pathlib import Path
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import argparse
import hashlib
import math
import re

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = Path('outputs/research/evidence_20261019/report.html')
PUBLIC = 'https://tranthanhphu39.github.io/dashboard_crypto/dashboard/#fomc'
GITHUB = 'https://github.com/TranThanhPhu39/dashboard_crypto/blob/main/'


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.rows, self.row, self.cell = [], [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.rows = []
        elif tag == 'tr':
            self.row = []
        elif tag in ('td', 'th'):
            self.cell = ''

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th'):
            self.row.append(self.cell)
            self.cell = None
        elif tag == 'tr':
            self.rows.append(self.row)
        elif tag == 'table':
            self.tables.append(self.rows)


def table(tables, required):
    matches = [rows for rows in tables if set(required).issubset(rows[0])]
    if len(matches) != 1:
        raise ValueError('Expected exactly one published table: ' + ', '.join(required))
    rows = matches[0]
    return [dict(zip(rows[0], row)) for row in rows[1:]]


def chart(title, rows, caption, unit, intervals=False, bars=False):
    """rows: (label, literal published value, literal low/high or None, colour)."""
    values = [float(v) for _, value, low, high, _ in rows
              for v in (value, low, high) if v is not None]
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError('A chart needs finite published values')
    low, high = min([0] + values), max([0] + values)
    pad = (high-low or 1) * .12
    low, high = (0 if bars else low-pad), high+pad
    left, right, top = 290, 790, 30
    step = 32 if len(rows) > 10 else 43
    height = top + step*len(rows) + 55
    x = lambda value: left+(float(value)-low)/(high-low)*(right-left)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 {height}" role="img" aria-label="{escape(title, quote=True)}">',
           f'<title>{escape(title)}</title><desc>{escape(caption)}</desc>']
    for i in range(6):
        tick = low + (high-low)*i/5
        xpos = x(tick)
        out += [f'<line x1="{xpos:.2f}" y1="10" x2="{xpos:.2f}" y2="{height-48}" stroke="#e1e9e7"/>',
                f'<text x="{xpos:.2f}" y="{height-25}" text-anchor="middle" fill="#58716c" font-size="13">{tick:.2f}</text>']
    out.append(f'<line x1="{x(0):.2f}" x2="{x(0):.2f}" y1="10" y2="{height-48}" stroke="#7f9993" stroke-dasharray="4 4"/>')
    for i, (label, value, lower, upper, colour) in enumerate(rows):
        y = top+i*step
        out.append(f'<text x="0" y="{y+5}" fill="#26463e" font-size="14">{escape(label)}</text>')
        tip = label + ': ' + value
        if intervals:
            tip += f'; percentile 95% [{lower}, {upper}]'
        out.append(f'<g data-published-value="{escape(value)}"><title>{escape(tip)}</title>')
        if bars:
            out.append(f'<rect x="{min(x(0),x(value)):.2f}" y="{y-10}" width="{abs(x(value)-x(0)):.2f}" height="20" rx="4" fill="{colour}"/>')
        else:
            if intervals:
                out.append(f'<path d="M{x(lower):.2f},{y} H{x(upper):.2f} M{x(lower):.2f},{y-6} v12 M{x(upper):.2f},{y-6} v12" stroke="{colour}" stroke-width="2"/>')
            out.append(f'<circle cx="{x(value):.2f}" cy="{y}" r="5" fill="{colour}"/>')
        out.append(f'<text x="810" y="{y+5}" fill="#26463e" font-size="14">{escape(value)}</text></g>')
    out.append('</svg>')
    return ('<figure class="reading-figure"><h3>'+escape(title)+'</h3><p class="unit">'+escape(unit)+
            '</p><div class="chart-scroll">'+''.join(out)+'</div><figcaption>'+escape(caption)+'</figcaption></figure>')


def build(standalone=False):
    raw = (ROOT/RELATIVE).read_bytes()
    source = raw.decode('utf-8')
    tables = Tables()
    tables.feed(source)
    falsification = table(tables.tables, ['asset', 'outcome', 'shock', 'beta', 'qvalue_hc3_bh'])
    rotation = table(tables.tables, ['asset', 'shock', 'beta', 'lower95_percentile', 'upper95_percentile'])
    benchmarks = table(tables.tables, ['benchmark', 'comparisons', 'BH_wins_HAR', 'BH_losses_HAR'])
    names = {'pre_early':'Trước 70–40 phút', 'pre_late':'Trước 40–10 phút',
             'announcement':'Quanh thông báo', 'placebo':'Cùng giờ, tuần trước',
             'policy':'Chính sách', 'information':'Thông tin'}
    colour = {'policy':'#087f71', 'information':'#b26a32'}
    order = ['pre_early', 'pre_late', 'announcement', 'placebo']
    falsification.sort(key=lambda r: (r['asset'], order.index(r['outcome']), r['shock']=='information'))
    figures = {
        'falsification_windows.png': chart('Hệ số theo cửa sổ sự kiện',
            [(f"{r['asset']} · {names[r['outcome']]} · {names[r['shock']]}",r['beta'],None,None,colour[r['shock']]) for r in falsification],
            'Biểu đồ thay thế từ bảng ngay phía trên, dùng các giá trị đã làm tròn trong báo cáo. Chỉ có ước lượng điểm: bảng không chứa sai số chuẩn nên không vẽ khoảng tin cậy 95% của hình gốc.',
            'Điểm phần trăm lợi suất trên +10 bps thành phần · 72 sự kiện'),
        'rotation_and_sampling.png': chart('Ước lượng và khoảng bootstrap tại median rotation',
            [(f"{r['asset']} · {names[r['shock']]}",r['beta'],r['lower95_percentile'],r['upper95_percentile'],colour[r['shock']]) for r in rotation],
            'Biểu đồ thay thế từ bảng median rotation (w = 0,5), với percentile 95% và 999 lượt bootstrap. Không có các điểm w = 0,1 và 0,9 của hình gốc. Khoảng này không bao phủ toàn miền nhận dạng; miền xoay được giữ trong bảng riêng phía trên.',
            'Điểm phần trăm lợi suất trên +10 bps · ước lượng điểm và percentile 95%', intervals=True),
        'rv_forecasting.png': chart('Số so sánh HAR/HAR-X đạt BH theo mốc dự báo',
            [(f"{r['benchmark']} · {'Tốt hơn' if key=='BH_wins_HAR' else 'Kém hơn'} / {r['comparisons']}",r[key],None,None,'#087f71' if key=='BH_wins_HAR' else '#b26a32')
             for r in benchmarks for key in ('BH_wins_HAR','BH_losses_HAR')],
            'Biểu đồ tổng hợp thay thế từ bảng benchmark: mỗi mốc có 40 so sánh. Không phải đường QLIKE tích lũy của hình gốc vì bản GitHub không chứa chuỗi dự báo RV cần thiết. Các so sánh có tương quan và không chứng minh khả năng dự báo tương lai.',
            'Số so sánh có ý nghĩa sau điều chỉnh BH · số lớn hơn không phải tỷ lệ thắng giao dịch', bars=True),
    }
    body = re.search(r'<body>(.*?)</body>', source, re.S)[1]
    count = 0

    def replace_figure(match):
        nonlocal count
        src = re.search(r'src="([^"]+)"', match[0])[1]
        result = figures.get(Path(src).name)
        if result is None:
            raise ValueError('Unrecognised report image: ' + src)
        count += 1
        return result

    body = re.sub(r'<figure>\s*<img\b[^>]*>\s*</figure>', replace_figure, body)
    if count != 3:
        raise ValueError('Expected all three missing report figures')

    def links(match):
        href, label = unescape(match[1]), match[2]
        if href == 'dashboard.html':
            href = PUBLIC if standalone else '../../../dashboard/index.html#fomc'
        elif not urlsplit(href).scheme and not href.startswith('#'):
            target = ((ROOT/RELATIVE).parent/href).resolve()
            if not target.is_relative_to(ROOT) or not target.is_file():
                return '<span class="unavailable" title="Tệp này cần bộ nghiên cứu đầy đủ">'+label+' (cần bộ đầy đủ)</span>'
            if standalone:
                href = GITHUB + target.relative_to(ROOT).as_posix()
        return '<a href="'+escape(href, quote=True)+'">'+label+'</a>'

    body = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', links, body, flags=re.S)
    css = '''*{box-sizing:border-box}body{font:17px/1.85 "Segoe UI",system-ui,sans-serif;margin:0;background:#f5f8f6;color:#244139}main{max-width:1160px;margin:30px auto;padding:35px 42px;background:white;border:1px solid #dbe7e1;border-radius:20px}a{color:#06796d;text-underline-offset:4px}p{margin:20px 0}p>strong:only-child{display:block;font-size:23px;color:#125b4c;margin-top:38px;line-height:1.5}.notice{background:#eaf5ef;padding:20px 24px;border-radius:12px;border-left:4px solid #118574;font-size:16px}.notice strong{display:block;font-size:20px}table{border-collapse:collapse;font-size:14px;white-space:nowrap;width:100%}th,td{padding:10px 14px;border-bottom:1px solid #dae6e0;text-align:left}th{background:#edf5f0}.table-wrap{overflow:auto;max-width:100%;margin:22px 0}figure{margin:28px 0;padding:24px;border:1px solid #d8e5de;border-radius:14px;background:#fbfdfb}h3{font-size:21px;line-height:1.5;margin:0 0 7px}.unit{font-size:14px;color:#5c7269;margin:0 0 18px}.chart-scroll{overflow-x:auto}.chart-scroll svg{display:block;width:100%;min-width:790px;height:auto}figcaption{font-size:14px;line-height:1.8;color:#586f65;border-top:1px solid #dce7e0;margin-top:16px;padding-top:14px}code{font-size:.88em;overflow-wrap:anywhere;background:#edf5ef;padding:3px 5px}.unavailable{color:#64746a;font-size:.93em}footer{font-size:12px;overflow-wrap:anywhere;border-top:1px solid #dce7e0;margin-top:30px;padding-top:20px;color:#66796e}@media(max-width:680px){body{font-size:16px}main{padding:22px 16px;margin:0;border:0;border-radius:0}figure{padding:16px 12px}.notice{padding:16px}h3{font-size:19px}}'''
    note = '<aside class="notice"><strong>Bản đọc có biểu đồ nhúng</strong>Các ảnh gốc không có trong bản GitHub. Ba biểu đồ dưới đây được dựng từ các bảng đã công bố và ghi rõ phạm vi thay thế. Nội dung, số liệu và các giới hạn nghiên cứu của báo cáo gốc được giữ lại.</aside>'
    digest = hashlib.sha256(raw).hexdigest()
    return ('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Báo cáo nghiên cứu · Bản đọc có biểu đồ</title><style>'+css+'</style><body><main>'+note+body+
            '<footer>Bản trình bày riêng từ evidence_20261019/report.html. SHA-256 của báo cáo nguồn: '+digest+'. Biểu đồ dùng độ chính xác của số liệu đã công bố trong bảng; không chạy lại mô hình.</footer></main></body></html>')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--standalone', type=Path, help='Write a portable HTML with online navigation links')
    args = parser.parse_args()
    output = args.standalone or ROOT/RELATIVE.with_name('report_view.html')
    if output.resolve() == (ROOT/RELATIVE).resolve():
        raise ValueError('Never overwrite the frozen source report')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build(standalone=bool(args.standalone)), encoding='utf-8')
    print('Created:', output)
