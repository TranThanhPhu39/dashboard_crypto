"""Accessible product UI, lazy historical replay and safe public status metadata."""
from pathlib import Path
import base64
import gzip
import json
import re
import hashlib

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'orbit-2'


def historical_payload(html):
    match = re.search(r'const HISTORICAL=(.*?);\s*(?:const HISTORY_ARCHIVE_GZIP_B64="([A-Za-z0-9+/=]+)";\s*)?const LATEST=', html, re.S)
    if not match:
        raise ValueError('Missing historical research payload')
    return json.loads(gzip.decompress(base64.b64decode(match[2]))) if match[2] else json.loads(match[1])


def public_status(html):
    from src.live_dashboard_data import latest_forecasts
    latest = json.loads(re.search(r'const LATEST=(.*?);\s*const el=', html, re.S)[1])
    live = latest['live']
    auto = live.get('automation', {})
    return {
        'schema_version': 1,
        'research_cutoff': '2026-10-15',
        'generated_at_utc': latest['generatedUtc'],
        'worker': {key: auto.get(key) for key in ['installed', 'provider', 'last_success_utc', 'health_status', 'latest_status', 'health_checked_at_utc', 'active_alerts']},
        'schedule': {'pipeline_minute_utc': 15, 'monitor_minute_utc': 45, 'capture_refresh_hours': 4, 'stale_after_minutes': 150},
        'prospective': {key: live.get(key) for key in ['prediction_files', 'prediction_rows', 'label_files', 'origin_count', 'first_origin_utc', 'last_origin_utc', 'fixed_end', 'performance', 'performance_claim']},
        'latest_forecasts': latest_forecasts(ROOT),
        'repository': 'TranThanhPhu39/dashboard_crypto',
        'workflow_url': 'https://github.com/TranThanhPhu39/dashboard_crypto/actions/workflows/worker.yml',
    }


def capture_status(root=ROOT):
    """Read an integrity-checked capture without exposing URLs or raw records."""
    pointer = root / 'outputs/research/evidence_20261019/prospective/latest_capture.json'
    if not pointer.is_file():
        return {'status': 'not_in_checkout', 'sources_ok': None, 'sources_total': None}
    try:
        record = json.loads(pointer.read_text(encoding='utf-8-sig'))
        path = (root / record['manifest']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Invalid capture path')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Capture integrity mismatch')
        manifest = json.loads(raw)
        sources = manifest['sources']
        from src.live_dashboard_data import observations
        return {'status': 'verified', 'started_at_utc': manifest['capture_started_utc'], 'finished_at_utc': manifest['capture_finished_utc'], 'sources_ok': sum(r['status']=='ok' for r in sources), 'sources_total': len(sources), 'observations': observations(root,sources)}
    except (ValueError, KeyError, OSError, TypeError):
        return {'status': 'unverified', 'sources_ok': None, 'sources_total': None}


def runtime(html):
    history = historical_payload(html)
    encoded = base64.b64encode(gzip.compress(json.dumps(history, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode(), compresslevel=9, mtime=0)).decode()
    metadata = {k: v for k, v in history.items() if k not in ['series', 'folds']}
    metadata.update(series=None, folds=None)
    html = re.sub(r'const HISTORICAL=.*?;\s*(?:const HISTORY_ARCHIVE_GZIP_B64="[A-Za-z0-9+/=]+";\s*)?const LATEST=', lambda _: 'const HISTORICAL=' + json.dumps(metadata, ensure_ascii=False, separators=(',', ':')) + ';\nconst HISTORY_ARCHIVE_GZIP_B64="' + encoded + '";\nconst LATEST=', html, count=1, flags=re.S)
    # Replace presentation renderers from their maintained sources, once only.
    for start, end, filename in [
        ('const historyPairs=', 'const scenarioNames=', 'historical_oos.js'),
        ('const scenarioNames=', 'initializeRelease();', 'release_functions.js'),
        ('const WORKSPACE_GROUPS=', 'showWorkspace(initialWorkspace);renderResponse();', 'workspace.js'),
    ]:
        first = html.index(start)
        if filename == 'historical_oos.js' and 'let historyLoadPromise = null;' in html[:first]:
            first = html.index('let historyLoadPromise = null;')
        last = html.index(end, first)
        if filename != 'historical_oos.js':
            last += len(end)
        while last < len(html) and html[last] in '\r\n':
            last += 1
        html = html[:first] + (ROOT / 'dashboard' / filename).read_text().rstrip() + '\n' + html[last:]
    # Hidden workspaces do not build SVGs, large date selectors or replay data.
    # Once Studio owns the chart, the legacy renderer still updates its exact
    # numbers/tables but must not overwrite the SVG immediately before Studio.
    guard="if(typeof window==='undefined'||!window.orbitOwnsResponseChart)"
    legacy_plot="el('responseChart').innerHTML=chart(rows.map(q=>({x:q.horizon_days,y:q.beta_pct,lo:q.lower95,hi:q.upper95})),i,'Horizon: calendar days');"
    if guard+legacy_plot not in html:
        html=html.replace(legacy_plot,guard+legacy_plot,1)
    html = html.replace('renderResponse();renderQuantile();renderVAR();renderForecast();renderRolling();', "renderResponse();if(typeof window==='undefined'){renderQuantile();renderVAR();renderForecast();renderRolling();}")
    return html


def enhance(html):
    html = re.sub(r'<!-- ORBIT EXPERIENCE [A-Z_]+ START -->.*?<!-- ORBIT EXPERIENCE [A-Z_]+ END -->', '', html, flags=re.S)
    html = re.sub(r'<style id="orbit-experience">.*?</style>', '', html, flags=re.S)
    html = re.sub(r'<script data-orbit-guard>.*?</script>', '', html, flags=re.S)
    html = re.sub(r'<noscript id="orbitNoScript">.*?</noscript>', '', html, flags=re.S)
    html = html.replace(' data-orbit-inert="true" inert', '')
    html = re.sub(r'\n?/\* ORBIT EXPERIENCE START \*/.*?/\* ORBIT EXPERIENCE END \*/\n?', '', html, flags=re.S)
    html = runtime(html)
    search = '''<!-- ORBIT EXPERIENCE SEARCH START --><button class="glossary-trigger" type="button" id="openGlossary"><span aria-hidden="true">⌕</span><span>Tra thuật ngữ: OOS, VIX…</span><kbd>Ctrl K</kbd></button><!-- ORBIT EXPERIENCE SEARCH END -->'''
    html = html.replace('<div class="topbar-actions">', search + '<div class="topbar-actions">', 1)
    nav = '''<!-- ORBIT EXPERIENCE NAV START --><button type="button" id="tab-operations" class="workspace-tab" aria-controls="operations" aria-pressed="false" title="Dữ liệu & OOS"><svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M3 12h4l3-7 4 14 3-7h4M4 4h3m10 16h3"/></svg><span>Dữ liệu &amp; OOS</span><i class="nav-indicator"></i></button><!-- ORBIT EXPERIENCE NAV END -->'''
    html = html.replace('<div class="sidebar-bottom">', nav + '<div class="sidebar-bottom">', 1)
    picker = '''<!-- ORBIT EXPERIENCE PICKER START --><div class="mobile-workspace-picker"><label for="mobileWorkspace">Bạn muốn tìm hiểu gì?</label><select id="mobileWorkspace"><option value="transmission">Tác động vĩ mô đến crypto</option><option value="forecast">Kiểm tra dự báo</option><option value="fomc">Thông tin từ Fed</option><option value="advanced">Phân tích sâu</option><option value="methods">Phương pháp và nguồn</option><option value="operations">Dữ liệu và OOS</option></select></div><!-- ORBIT EXPERIENCE PICKER END -->'''
    html = html.replace('<div class="sidebar-bottom">', picker + '<div class="sidebar-bottom">', 1)
    guide = '''<!-- ORBIT EXPERIENCE GUIDE START -->
    <details class="quick-guide" id="quickGuide"><summary>Bạn mới bắt đầu? Xem cách đọc dashboard <span>3 bước đơn giản</span></summary><div class="guide-steps"><div><b>01</b><strong>Chọn điều muốn tìm hiểu</strong><p>Ví dụ: Bitcoin thường phản ứng thế nào khi mức lo ngại của thị trường tăng?</p></div><div><b>02</b><strong>Chọn tài sản và số ngày</strong><p>Thay đổi bộ lọc bên dưới. Toàn bộ biểu đồ là kết quả nghiên cứu trên dữ liệu lịch sử.</p></div><div><b>03</b><strong>Đọc số và mức bất định</strong><p>Số âm là phản ứng giảm. Nếu khoảng tin cậy chứa 0, kết quả còn chưa rõ ràng.</p></div></div><div class="guide-examples"><span>Thử một câu hỏi:</span><button type="button" data-example="vix">BTC khi VIX tăng · 7 ngày</button><button type="button" data-example="usd">ETH khi USD tăng · 7 ngày</button><button type="button" data-example="fomc">BTC sau tin Fed · 3 ngày</button></div></details>
    <div class="app-feedback" id="appFeedback" role="status" aria-live="polite" hidden></div>
    <!-- ORBIT EXPERIENCE GUIDE END -->'''
    html = html.replace('<span id="workspaceTitle"', guide + '<span id="workspaceTitle"', 1)
    insight = '''<!-- ORBIT EXPERIENCE INSIGHT START --><div class="reading-card" id="responseReading" aria-live="polite"><span class="reading-eyebrow">ĐỌC KẾT QUẢ TRONG 20 GIÂY</span><strong id="responseReadingTitle"></strong><p id="responseReadingBody"></p><button type="button" data-term="ci">Khoảng tin cậy là gì? ↗</button></div><!-- ORBIT EXPERIENCE INSIGHT END -->'''
    html = html.replace('<p id="responseTiming"', insight + '<p id="responseTiming"', 1)
    forecast = '''<!-- ORBIT EXPERIENCE FORECAST START --><div class="reading-card" id="forecastReading" aria-live="polite"><span class="reading-eyebrow">KẾT QUẢ NÀY CÓ Ý NGHĨA GÌ?</span><strong id="forecastReadingTitle"></strong><p id="forecastReadingBody"></p></div><div id="historyLoading" class="loading-card" role="status" hidden>Đang chuẩn bị dữ liệu dự báo… Chỉ cần tải lần đầu khi mở mục này.</div><div id="historyError" class="error-card" role="alert" hidden><strong>Chưa mở được dữ liệu phát lại</strong><p id="historyErrorText"></p><button type="button" id="retryHistory">Thử lại</button></div><!-- ORBIT EXPERIENCE FORECAST END -->'''
    html = html.replace('<div class="historical-oos"', forecast + '<div class="historical-oos"', 1)
    ops = '''<!-- ORBIT EXPERIENCE OPERATIONS START --><section data-workspace="operations" hidden class="panel" id="operations"><div class="section-kicker">06 / DATA &amp; OUT-OF-SAMPLE</div><h2>Dữ liệu đang được cập nhật thế nào?</h2><p class="section-intro">Tách rõ mẫu nghiên cứu đã chốt, công việc thu dữ liệu tự động và việc kiểm chứng dự báo mới.</p>
    <div class="operations-toolbar"><span class="state-pill" id="statusBadge">Đang đọc trạng thái bản này</span><button class="action-secondary" type="button" id="refreshStatus">Kiểm tra bản cập nhật</button><a href="https://github.com/TranThanhPhu39/dashboard_crypto/actions/workflows/worker.yml" target="_blank" rel="noopener noreferrer">Xem lịch sử chạy GitHub ↗</a></div><p id="statusMessage" class="compact-meta" role="status"></p>
    <div class="status-grid"><article><span>Mẫu dùng cho biểu đồ nghiên cứu</span><strong>15/10/2026</strong><p>Mốc dữ liệu lịch sử đã chốt; worker thu dữ liệu mới không tự kéo dài các mô hình và biểu đồ đã khóa.</p></article><article><span>Lần vận hành thành công gần nhất</span><strong id="statusLastRun">—</strong><p id="statusWorkerDetail"></p></article><article><span>Dự báo mới ghi trước khi biết kết quả</span><strong id="statusPredictions">—</strong><p id="statusPredictionDetail"></p></article><article><span>Thời điểm cho phép đánh giá OOS</span><strong id="statusEvaluation">—</strong><p id="statusEvaluationDetail"></p></article></div>
    <div class="capture-strip"><span>Lần nhận dữ liệu nguồn gần nhất</span><strong id="statusCaptureTime">Chưa có biên bản thu trong bản này</strong><span id="statusCaptureSources"></span></div>
    <h3>Ba việc khác nhau, ba cách kiểm tra</h3><div class="explain-grid"><div><b>Thu dữ liệu</b><p>Pipeline chạy theo lịch phút 15 mỗi giờ; bộ giám sát chạy phút 45. Capture được làm mới sau 4 giờ hoặc khi nguồn lỗi, theo quy tắc đã khóa.</p></div><div><b>Phát lại lịch sử</b><p>Dùng mô hình đã lưu để kiểm tra dự báo trên các năm 2023–2026. Đây là <button type="button" data-term="pseudo-oos">OOS lịch sử</button>; chưa phải bằng chứng dự báo tốt trong tương lai.</p></div><div><b>Theo dõi dự báo thật</b><p>Chỉ ghi dự báo khi dữ liệu đến đúng hạn và đủ điều kiện. Ngày không có dự báo được ghi rõ; không dựng bù dự báo sau khi biết kết quả.</p></div></div><details><summary>Cách đọc trạng thái và giới hạn của bản mở trên máy</summary><p>Bản HTML tải về là ảnh chụp trạng thái lúc tạo file. Nút kiểm tra chỉ đọc metadata công khai từ website; không khởi chạy worker và không huấn luyện lại mô hình. Nếu website có phiên bản mới, bạn có thể mở bản mới. Màu cảnh báo có thể xuất hiện khi trạng thái đã quá 150 phút; hãy đối chiếu lịch sử GitHub.</p></details></section><!-- ORBIT EXPERIENCE OPERATIONS END -->'''
    ops=ops.replace('</section><!-- ORBIT EXPERIENCE OPERATIONS END -->',(ROOT/'dashboard/live_operations.html').read_text(encoding='utf-8')+'</section><!-- ORBIT EXPERIENCE OPERATIONS END -->')
    html = html.replace('<footer>', ops + '<footer>', 1)
    dialog = '''<!-- ORBIT EXPERIENCE DIALOG START --><dialog id="glossaryDialog" class="glossary-dialog" aria-labelledby="glossaryTitle"><div class="glossary-heading"><div><span class="section-kicker">ORBIT DICTIONARY</span><h2 id="glossaryTitle">Đọc hiểu trước, phân tích sau.</h2></div><button type="button" id="closeGlossary" class="icon-button" aria-label="Đóng tra cứu">✕</button></div><label class="glossary-search-label" for="glossarySearch">Nhập thuật ngữ hoặc điều bạn chưa hiểu</label><input id="glossarySearch" type="search" autocomplete="off" placeholder="Ví dụ: OOS, cú sốc, khoảng tin cậy…"><div class="glossary-layout"><div id="glossaryResults" class="glossary-results" aria-label="Thuật ngữ tìm được"></div><article id="glossaryDetail" class="glossary-detail" aria-live="polite"></article></div><p class="glossary-footnote">Giải thích ngắn cho dashboard này. Liên kết Google mở ở tab mới khi bạn chọn.</p></dialog><!-- ORBIT EXPERIENCE DIALOG END -->'''
    # The dialog must exist before the application binds its event handlers.
    html = html.replace('<script>', dialog + '<script>', 1)
    for old, new in {
        'Một cú shock. Crypto phản ứng ra sao?': 'Crypto phản ứng thế nào khi kinh tế thay đổi?',
        'Cú shock vĩ mô': 'Biến động kinh tế',
        'Chọn tài sản, loại shock, chế độ thị trường và horizon để xem phản ứng cùng khoảng tin cậy 95%.': 'Chọn Bitcoin hoặc Ethereum, một thay đổi kinh tế và số ngày muốn theo dõi. Biểu đồ cho thấy phản ứng ước lượng từ dữ liệu lịch sử.',
        'Macro có cải thiện dự báo rủi ro?': 'Thêm dữ liệu kinh tế có giúp dự báo tốt hơn?',
        'Phát lại dự báo trên dữ liệu quá khứ': 'Đối chiếu dự báo với kết quả đã xảy ra',
        'Loss mô hình gốc': 'Sai số mô hình gốc',
        'Loss mô hình bổ sung': 'Sai số khi thêm dữ liệu',
        'Bổ sung − benchmark': 'Chênh lệch với mốc so sánh',
        'Loss added − base cộng dồn': 'Chênh lệch sai số cộng dồn: mô hình mới − gốc',
        '<label>Target<select': '<label>Điều muốn dự báo<select',
        '<label>Model<select': '<label>Thuật toán<select',
        '<label>Scenario<select': '<label>Cách dùng dữ liệu<select',
        'Daily squared return · QLIKE': 'Mức biến động giá · QLIKE',
        'Daily return · MSE': 'Lợi suất mỗi ngày · MSE',
        'Native as-of D3</option>': 'Dữ liệu đúng thời điểm · mẫu gốc</option>',
        'Matched as-of D3</option>': 'Cùng mẫu · độ trễ 3 ngày</option>',
        'Latest vintage · EX POST ORACLE': 'Đối chiếu bằng dữ liệu sửa sau',
        'Matched as-of D4</option>': 'Cùng mẫu · độ trễ 4 ngày</option>',
        'Kiểm định theo kỳ đánh giá đã khóa': 'Kết quả thống kê của kỳ đánh giá đã chốt',
        'So với benchmark': 'So với cách dự báo làm mốc',
        'Vintage / timing trên cùng origins': 'So sánh thời điểm và phiên bản dữ liệu',
        'FOMC: policy / information components': 'Sau thông tin từ Fed: giá phản ứng thế nào?',
        'Realized variance: HAR / HAR-X': 'Đo biến động từ dữ liệu giá trong ngày',
        'Chạm biểu đồ để chọn ngày': 'Bấm biểu đồ để chọn số ngày',
    }.items():
        # Wording changes are restricted to markup, not embedded scientific data.
        parts = re.split(r'(<script\b.*?</script>)', html, flags=re.S)
        html = ''.join(p if p.startswith('<script') else p.replace(old, new) for p in parts)
    css = (ROOT / 'dashboard/experience.css').read_text()
    js = (ROOT / 'dashboard/experience.js').read_text()
    status_data = public_status(html)
    status_data['capture'] = capture_status(ROOT)
    status = json.dumps(status_data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = html.replace('</head>', '<style id="orbit-experience">' + css + '</style></head>', 1)
    # A separate guard still works if the application script fails to parse.
    guard = '''<script data-orbit-guard>window.addEventListener('error',function(e){if(e.filename&&e.filename.indexOf('chrome-extension:')===0)return;var boot=document.getElementById('bootStatus');if(boot)boot.hidden=true;document.querySelectorAll('[data-orbit-inert]').forEach(function(n){n.removeAttribute('inert');});var b=document.getElementById('appFeedback');if(b){b.hidden=false;b.textContent='Một thành phần chưa mở được. Hãy tải lại trang; nếu vẫn lỗi, dùng Chrome/Edge mới và mở START_DASHBOARD.html.';b.setAttribute('role','alert');}});</script>'''
    boot = '''<!-- ORBIT EXPERIENCE BOOT START --><div id="bootStatus" class="boot-screen" role="status" aria-live="polite"><div><strong>orbit<span>.</span></strong><p>Đang mở không gian phân tích…</p><small>Chuẩn bị bộ lọc và dữ liệu lịch sử</small></div></div><!-- ORBIT EXPERIENCE BOOT END -->'''
    for tag in ['<header class="app-header"', '<nav class="workspace-nav"', '<main id="mainContent"']:
        html = html.replace(tag, tag.replace(' ', ' data-orbit-inert="true" inert ', 1), 1)
    html = html.replace('<body>', '<body>' + boot + guard + '<noscript id="orbitNoScript"><style>.boot-screen{display:none}</style>Dashboard cần bật JavaScript để hiển thị biểu đồ và bộ lọc.</noscript>', 1)
    script_end = html.index('</script>', html.index('<script>'))
    html = html[:script_end] + '\n/* ORBIT EXPERIENCE START */\nconst ORBIT_STATUS=' + status + ';\n' + js + '\n/* ORBIT EXPERIENCE END */\n' + html[script_end:]
    return html
