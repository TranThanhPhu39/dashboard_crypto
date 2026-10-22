"""Orbit presentation layer. Does not modify payloads, estimates or model code."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def icon(name, extra=""):
    paths = {
        'orbit': '<ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(-35 12 12)"/><circle cx="12" cy="12" r="3"/><circle cx="20" cy="6.5" r="1.6" fill="currentColor" stroke="none"/>',
        'wave': '<path d="M2 12h4l3-7 5 14 3-7h5"/>',
        'chart': '<path d="M4 4v16h16M8 15l4-5 4 3 5-8"/>',
        'bank': '<path d="m3 8 9-5 9 5M4 9h16M6 10v7m6-7v7m6-7v7M3 20h18"/>',
        'layers': '<path d="m3 7 9-4 9 4-9 4-9-4Zm0 5 9 4 9-4M3 17l9 4 9-4"/>',
        'book': '<path d="M12 6c-3-2-6-2-9-1v14c3-1 6-1 9 1 3-2 6-2 9-1V5c-3-1-6-1-9 1Zm0 0v14"/>',
        'arrow': '<path d="M5 12h14m-5-5 5 5-5 5"/>',
        'download': '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
        'reset': '<path d="M4 10a8 8 0 1 1 1 8M4 4v6h6"/>',
        'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
        'calendar': '<rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4m8-4v4M4 11h16m-11 4h6"/>',
        'globe': '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
        'check': '<path d="m5 12 4 4L19 6"/>',
        'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    }
    return f'<svg class="ui-icon {extra}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>'


def redesign(html):
    """Apply/reapply the UI to a rendered snapshot, preserving embedded data."""
    html = html.replace(' data-orbit-inert="true" inert', '')
    html = re.sub(r'<style id="orbit-theme">.*?</style>', '', html, flags=re.S)
    html = re.sub(r'\n/\* ORBIT DESIGN START \*/.*?/\* ORBIT DESIGN END \*/\n', '', html, flags=re.S)
    html = re.sub(r'<!-- ORBIT HERO START -->.*?<!-- ORBIT HERO END -->', '', html, flags=re.S)
    html = re.sub(r'<a class="skip-link".*?</a>', '', html, flags=re.S)
    html = re.sub(r'<title>.*?</title>', '<title>orbit. — Macro × Crypto Research</title>', html, count=1, flags=re.S)
    header = f'''<header class="app-header">
      <div class="topbar-path"><span class="topbar-label">Không gian nghiên cứu</span><span class="path-divider">/</span><strong id="designBreadcrumb">Truyền dẫn</strong></div>
      <div class="topbar-actions"><span class="snapshot-status"><i></i>Dữ liệu lịch sử</span><span class="topbar-date">{icon('calendar')}15.10.2026 <span>UTC</span></span><button type="button" id="themeToggle" class="icon-button" aria-label="Chuyển sang giao diện sáng" title="Đổi giao diện sáng / tối">{icon('sun')}</button></div>
    </header>'''
    html = re.sub(r'<header\b[^>]*>.*?</header>', header, html, count=1, flags=re.S)
    tabs = [
        ('transmission', 'Truyền dẫn', 'wave', 'responses rolling'),
        ('forecast', 'Dự báo rủi ro', 'chart', 'forecast rv'),
        ('fomc', 'Sự kiện FOMC', 'bank', 'fomc'),
        ('advanced', 'Phân vị & VAR', 'layers', 'quantile joint'),
        ('methods', 'Phương pháp & nguồn', 'book', 'overview pit methods'),
    ]
    buttons = ''.join(f'<button type="button" id="tab-{key}" class="workspace-tab" aria-controls="{panels}" aria-pressed="{str(key == "transmission").lower()}" title="{label}">{icon(symbol)}<span>{label}</span><i class="nav-indicator"></i></button>' for key, label, symbol, panels in tabs)
    nav = f'''<nav class="workspace-nav" aria-label="Các công cụ phân tích">
      <a class="brand" href="#transmission" aria-label="orbit. — Trang truyền dẫn">{icon('orbit', 'brand-symbol')}<span>orbit<span class="brand-dot">.</span><small>MACRO × CRYPTO</small></span></a>
      <div class="nav-label">KHÁM PHÁ</div><div class="nav-items">{buttons}</div>
      <div class="sidebar-bottom"><div class="sidebar-note"><span class="note-orbit" aria-hidden="true">◌</span><strong>Zoom out.<br>See the bigger picture.</strong><p>Từ chuyển động vĩ mô đến góc nhìn về crypto.</p><button type="button" id="learnMethods">Khám phá phương pháp {icon('arrow')}</button></div>
      <a class="report-link" href="../outputs/research/release_20261025/report.html">{icon('book')}<span>Báo cáo nghiên cứu</span>{icon('arrow')}</a><div class="lab-signature"><span class="status-dot"></span> CRYPTO FINANCE LAB <span>v.01</span></div></div>
    </nav>'''
    html = re.sub(r'<nav\b[^>]*>.*?</nav>', nav, html, count=1, flags=re.S)
    hero = f'''<!-- ORBIT HERO START -->
      <div class="workspace-hero"><div class="hero-copy"><div class="hero-eyebrow"><span class="status-dot"></span><span id="designEyebrow">THE BIG PICTURE / 01</span></div>
      <h1 id="designTitle">Thị trường chuyển động.<br><span>Hiểu điều đứng sau.</span></h1><p id="designDescription">Kết nối những biến động vĩ mô với phản ứng của Bitcoin và Ethereum. Bắt đầu từ một cú shock.</p>
      <div class="hero-tags"><span>{icon('globe')} Global financial conditions</span><span>BTC &amp; ETH</span><span>Research snapshot</span></div></div>
      <div class="hero-art" aria-hidden="true"><div class="art-grid"></div><div class="art-orbit orbit-one"></div><div class="art-orbit orbit-two"></div><div class="art-orbit orbit-three"></div><div class="art-core">₿</div><span class="art-satellite satellite-eth">Ξ</span><span class="art-satellite satellite-star">✦</span><span class="art-coordinate">MACRO ↔ CRYPTO</span></div></div>
      <div class="overview-metrics" id="designMetrics">
      <div class="metric-card"><div class="metric-icon mint">{icon('layers')}</div><div><span>Tài sản nghiên cứu</span><strong>Bitcoin <em>&amp;</em> Ethereum</strong><small>USD · Hai tài sản, một góc nhìn</small></div><span class="metric-corner">02</span></div>
      <div class="metric-card"><div class="metric-icon lavender">{icon('clock')}</div><div><span>Khung phản ứng</span><strong>01 <em>—</em> 30 <em>ngày</em></strong><small>Local Projections · ngày lịch</small></div></div>
      <div class="metric-card"><div class="metric-icon peach">{icon('chart')}</div><div><span>Mẫu ước lượng đang chọn</span><strong id="designSample">—</strong><small id="designSampleMeta">BTC · Toàn mẫu</small></div></div>
      </div>
      <!-- ORBIT HERO END -->'''
    html = html.replace('<main>', '<main id="mainContent">', 1)
    html = html.replace('<main id="mainContent">', '<main id="mainContent">' + hero, 1)
    html = html.replace('<body>', '<body><a class="skip-link" href="#mainContent">Đến nội dung chính</a>', 1)
    replacements = {
        '<h2>Ước lượng phản ứng theo shock</h2>': '<div class="section-kicker">01 / SHOCK EXPLORER</div><h2>Một cú shock. Crypto phản ứng ra sao?</h2>',
        '<h2>Rolling sensitivity — 252 phiên</h2>': '<div class="section-kicker">02 / ROLLING SENSITIVITY</div><h2>Độ nhạy thay đổi theo thời gian</h2>',
        '<label>Regime<select id="regime">': '<label>Trạng thái thị trường<select id="regime">',
        '<label>Horizon (ngày lịch)<select id="horizon">': '<label>Thời hạn phản ứng<select id="horizon">',
        '<label>Shock<select id="shock">': '<label>Cú shock vĩ mô<select id="shock">',
        '>Tải CSV đường phản ứng</button>': '>' + icon('download') + 'Tải đường phản ứng</button>',
        '>Đặt lại bộ lọc</button>': '>' + icon('reset') + 'Đặt lại</button>',
    }
    for old, new in replacements.items():
        html = html.replace(old, new, 1)
    if 'class="result-kicker"' not in html:
        html = html.replace('<aside class="result">', '<aside class="result"><div class="result-kicker"><span class="status-dot"></span> KẾT QUẢ ƯỚC LƯỢNG</div>', 1)
    if 'id="horizonPresets"' not in html:
        toolbar = '''<div class="chart-toolbar"><div><strong>Đường phản ứng</strong><span>Log return cộng dồn (%)</span></div><div class="horizon-presets" id="horizonPresets" aria-label="Chọn nhanh thời hạn phản ứng">'''
        toolbar += ''.join(f'<button type="button" data-horizon="{h}" aria-pressed="{str(h == 1).lower()}" aria-label="Phản ứng sau {h} ngày">{h}N</button>' for h in [1, 7, 14, 30])
        toolbar += '</div></div>'
        html = html.replace('<div><svg id="responseChart"', '<div class="response-plot">' + toolbar + '<svg id="responseChart"', 1)
        html = html.replace('aria-label="Đường phản ứng 1–30 ngày và CI"></svg>', 'aria-label="Đường phản ứng 1–30 ngày và CI"></svg><div class="chart-legend"><span><i></i>Ước lượng phản ứng</span><span><i class="band"></i>Khoảng tin cậy 95%</span><span class="chart-hint">Chạm biểu đồ để chọn ngày</span></div>', 1)
    if 'class="result-footnote"' not in html:
        html = html.replace('<p id="responseInference" class="muted"></p></aside>', '<p id="responseInference" class="muted"></p><div class="result-footnote">' + icon('check') + '<span>Ước lượng lịch sử<br>Đọc cùng khoảng tin cậy</span></div></aside>', 1)
    html = re.sub(r'<footer>.*?</footer>', '<footer><span>orbit<span class="footer-dot">.</span> <span class="footer-separator">/</span> Macro × Crypto Research</span><span>Snapshot đến 15.10.2026 · UTC</span></footer>', html, count=1, flags=re.S)
    css = (ROOT / 'dashboard/design.css').read_text(encoding='utf-8')
    js = (ROOT / 'dashboard/design.js').read_text(encoding='utf-8')
    html = html.replace('</head>', '<style id="orbit-theme">' + css + '</style></head>', 1)
    # Keep one script so the existing validation exercises the same program.
    # A boot guard may precede the app; bind UI only after its DOM exists.
    script_end = html.index('</script>', html.index('<script>'))
    html = html[:script_end] + '\n/* ORBIT DESIGN START */\n' + js + '\n/* ORBIT DESIGN END */\n' + html[script_end:]
    from src.dashboard_experience import enhance
    from src.dashboard_studio import studio
    return studio(enhance(html))
