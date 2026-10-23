"""Orbit 3 markup: focused reading order, stable scientific IDs, offline assets."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAGES = [('transmission', 'Truyền dẫn', 'wave'), ('forecast', 'Dự báo rủi ro', 'chart'),
         ('fomc', 'FOMC', 'bank'), ('advanced', 'Phân vị & VAR', 'layers'),
         ('methods', 'Phương pháp & nguồn', 'book'), ('operations', 'Dữ liệu & OOS', 'clock')]


def studio(html):
    from src.dashboard_design import icon
    html = re.sub(r'<style id="orbit-aurora">.*?</style>', '', html, flags=re.S)
    html = re.sub(r'<!-- ORBIT STUDIO [A-Z_]+ START -->.*?<!-- ORBIT STUDIO [A-Z_]+ END -->', '', html, flags=re.S)
    # Offline coastline scene and reusable crypto marks; no canvas loop or timers.
    scenery = (ROOT/'dashboard/world-network.svg').read_text(encoding='utf-8').strip()
    scenery = '<!-- ORBIT STUDIO SCENERY START --><div id="globalCryptoBackdrop" class="global-crypto-backdrop" aria-hidden="true" inert>'+scenery+'</div><!-- ORBIT STUDIO SCENERY END -->'
    html = re.sub(r'(<body\b[^>]*>)', lambda match: match[1]+scenery, html, count=1)
    def button(key, label, symbol, mobile=False):
        if mobile:
            return f'<button type="button" data-goto="{key}">{icon(symbol)}<span>{label}</span></button>'
        return f'<button type="button" id="tab-{key}" class="workspace-tab" aria-controls="{dict(transmission="responses rolling analoguePanel",forecast="forecast rv",fomc="fomc",advanced="quantile joint",methods="overview pit methods",operations="operations")[key]}" aria-pressed="{str(key=="transmission").lower()}" title="{label}">{icon(symbol)}<span>{label}</span><kbd>{[x[0] for x in PAGES].index(key)+1}</kbd></button>'
    groups = [('Phân tích', [0, 2, 3]), ('Kiểm chứng', [1, 5]), ('Tài liệu', [4])]
    nav = '<nav id="workspaceNavigation" class="workspace-nav" aria-label="Không gian nghiên cứu"><div class="sidebar-heading"><a class="brand" href="#transmission" aria-label="orbit. — Trang truyền dẫn">'+icon('orbit','brand-symbol')+'<span>orbit<span class="brand-dot">.</span><small>MACRO × CRYPTO</small></span></a><button type="button" id="collapseSidebar" class="sidebar-toggle" aria-label="Thu gọn menu" title="Thu gọn menu" aria-controls="workspaceNavigation" aria-expanded="true">'+icon('arrow')+'</button></div><div class="nav-items"><i id="navActive" aria-hidden="true"></i>'
    for label, indices in groups:
        nav += '<div class="nav-label">'+label+'</div>'+''.join(button(*PAGES[i]) for i in indices)
    nav += '</div><div class="sidebar-bottom"><div class="sidebar-caption"><span class="status-dot"></span>Nghiên cứu, từng góc nhìn.</div><button type="button" id="learnMethods" class="sidebar-method">Cách đọc kết quả '+icon('arrow')+'</button><span class="lab-signature">AURORA · GLASS / 03</span></div><div id="sidebarResizer" class="sidebar-resizer" role="separator" tabindex="0" aria-label="Độ rộng menu. Kéo hoặc dùng phím trái, phải để điều chỉnh." title="Kéo để đổi độ rộng · nhấp đúp để đặt lại" aria-orientation="vertical" aria-controls="workspaceNavigation" aria-valuemin="224" aria-valuemax="340" aria-valuenow="252"></div><select id="mobileWorkspace" class="sr-only" aria-label="Workspace">'+''.join(f'<option value="{k}">{l}</option>' for k,l,_ in PAGES)+'</select></nav>'
    html = re.sub(r'<nav\b[^>]*>.*?</nav>', nav, html, count=1, flags=re.S)
    header = '<header class="app-header"><div class="topbar-path"><button type="button" id="openNavigation" class="icon-button" aria-label="Mở menu">'+icon('layers')+'</button><span class="topbar-label">Nghiên cứu</span><span class="path-divider">/</span><strong id="designBreadcrumb">Truyền dẫn</strong></div><div class="topbar-actions"><span class="topbar-date">Dữ liệu đến 15/10/2026</span><button type="button" id="openGlossary" class="glossary-trigger" aria-label="Tìm kiếm và lệnh · Ctrl K"><span aria-hidden="true">⌕</span><span>Tìm kiếm &amp; lệnh</span><kbd>Ctrl K</kbd></button><button type="button" id="themeToggle" class="icon-button" aria-label="Đổi giao diện sáng tối">'+icon('sun')+'</button><button type="button" id="topExport" class="top-export" aria-label="Tải CSV của workspace">'+icon('download')+'<span>Tải CSV</span></button></div></header>'
    header=header.replace('<span class="topbar-date">Dữ liệu đến 15/10/2026</span>','<button type="button" class="topbar-date" data-goto="operations" aria-label="Xem ngày chốt mẫu nghiên cứu và dữ liệu mới"><span>Mẫu ước lượng: 15/10/2026</span><small id="latestDataBadge">Thu dữ liệu: đang đọc</small></button>')
    header=header.replace('id="themeToggle" class="icon-button"','id="themeToggle" class="icon-button theme-toggle"').replace(icon('sun')+'</button>',icon('sun')+'<span id="themeModeLabel">Tối</span></button>')
    html = re.sub(r'<header\b[^>]*>.*?</header>', header, html, count=1, flags=re.S)
    # Keep the sidebar before the action bar in keyboard and DOM reading order.
    html = html.replace(nav, '', 1).replace(header, nav + header, 1)
    hero = '<!-- ORBIT HERO START --><div class="workspace-hero"><div class="hero-eyebrow" id="designEyebrow">MACRO × CRYPTO / RESEARCH EXPLORER</div><h1 id="designTitle">Từ vĩ mô đến crypto<span>.</span></h1><p id="designDescription">Một thay đổi kinh tế. Hai tài sản. 30 ngày phản ứng.</p><div id="designMetrics" hidden><span id="designSample"></span><span id="designSampleMeta"></span></div></div><!-- ORBIT HERO END -->'
    html = re.sub(r'<!-- ORBIT HERO START -->.*?<!-- ORBIT HERO END -->', hero, html, flags=re.S)
    hero_map = '<div class="hero-crypto-badges" aria-hidden="true"><span class="hero-crypto-token token-bitcoin"><svg viewBox="-32 -32 64 64" fill="none" focusable="false"><use class="bitcoin-mark" href="#orbitBitcoinMark"/></svg><span><b>BTC</b><small>BITCOIN</small></span></span><span class="hero-crypto-token token-ethereum"><svg viewBox="-32 -32 64 64" fill="none" focusable="false"><use href="#orbitEthereumMark"/></svg><span><b>ETH</b><small>ETHEREUM</small></span></span></div>'
    html = html.replace('<div class="workspace-hero">', '<div class="workspace-hero">'+hero_map, 1)
    html = re.sub(r'<!-- ORBIT EXPERIENCE GUIDE START -->.*?<!-- ORBIT EXPERIENCE GUIDE END -->', '', html, flags=re.S)
    html = re.sub(r'<div id="appFeedback"[^>]*></div>', '', html)
    html = html.replace('<span id="workspaceTitle"', '<div id="appFeedback" class="app-feedback" role="status" hidden></div><span id="workspaceTitle"',1)
    for key, filename in [('responses','transmission.html'),('rolling','rolling.html'),('fomc','fomc.html')]:
        template = (ROOT/'dashboard'/filename).read_text().strip()+'\n'
        html = re.sub(r'<section\b[^>]*\bid="'+key+r'".*?</section>\s*', lambda _:template, html, count=1, flags=re.S)
    analogue = (ROOT/'dashboard/analogues.html').read_text()
    html = html.replace('<footer>', '<!-- ORBIT STUDIO ANALOGUES START -->'+analogue+'<!-- ORBIT STUDIO ANALOGUES END --><footer>',1)
    # Group lengthy tables without removing any numbers, IDs, or caveats.
    if '<summary>Xem kiểm định và các so sánh</summary>' not in html:
        html = re.sub(r'(<h3>Kết quả thống kê của kỳ đánh giá đã chốt</h3>.*?<div id="sensitivityTable"[^>]*></div>)', r'<details class="research-details"><summary>Xem kiểm định và các so sánh</summary>\1</details>', html, flags=re.S)
    if 'id="fomcSummary"' not in html:
        html = html.replace('<div id="fomcTable" class="table-wrap"></div>', '<div id="fomcSummary" class="fomc-summary"></div><details class="research-details"><summary>Bảng miền xoay và định nghĩa</summary><div id="fomcTable" class="table-wrap"></div></details>')
        html = html.replace('<div id="regimeTable" class="table-wrap"></div>', '<details class="research-details"><summary>Bảng khác biệt giữa các nhóm</summary><div id="regimeTable" class="table-wrap"></div></details>')
    if 'id="varDataTable"' not in html:
        html = html.replace('<svg id="varChart"', '<p class="chart-caveat">VAR innovation phụ thuộc mô hình và thứ tự nhận dạng; không gọi là “pure policy shock”.</p><svg id="varChart"')
        html = html.replace('<details class="method-details"><summary>Chẩn đoán mô hình</summary>', '<details><summary>Bảng dữ liệu IRF</summary><div id="varDataTable" class="table-wrap"></div></details><details class="method-details"><summary>Chẩn đoán mô hình</summary>',1)
    html = html.replace('<span class="research-badge">Historical pseudo-OOS / exploratory</span>', '')
    html = html.replace('<div class="history-heading">', '<div class="history-heading"><span class="research-badge">Historical pseudo-OOS / exploratory</span>',1)
    # Keep audit descriptions available, while the default view stays concise.
    if '<summary>Mẫu và cách so sánh</summary>' not in html:
        html = html.replace('<p id="forecastContext" class="compact-meta"></p>', '<details class="context-details"><summary>Mẫu và cách so sánh</summary><p id="forecastContext" class="compact-meta"></p></details>')
    if 'id="replayCompact"' not in html:
        html = html.replace('<p id="historyContext" class="compact-meta" role="status" aria-live="polite"></p>', '<p id="replayCompact" class="compact-meta" role="status"></p><details class="context-details"><summary>Phạm vi phát lại</summary><p id="historyContext" class="compact-meta" role="status" aria-live="polite"></p></details>')
    html = html.replace('<div id="historyPredictionChart"></div>', '<div id="historyPredictionChart" tabindex="0" aria-label="Biểu đồ dự báo lịch sử. Dùng bộ chọn ngày để xem giá trị bằng bàn phím."></div>')
    html = re.sub(r'<div class="history-legend">.*?</div>', '<div class="history-legend" id="replayLegend" aria-label="Bật tắt các đường dữ liệu">'+''.join(f'<button type="button" data-curve="{i}" aria-pressed="true"><i></i>{label}</button>' for i,label in enumerate(['Thực tế','Gốc','Bổ sung','Benchmark']))+'</div>',html,count=1,flags=re.S)
    html = html.replace('<div id="historyLossChart"></div>', '<div id="historyLossChart" tabindex="0" aria-label="Chênh lệch sai số tích lũy; giá trị âm có lợi cho mô hình bổ sung."></div>')
    for old,new in {
        '<label>Outcome<select id="eOutcome">':'<label>Cửa sổ quan sát<select id="eOutcome">',
        '<label>Sampling<select id="rvSampling">':'<label>Nến giá<select id="rvSampling">',
        '<label>Horizon<select id="rvHorizon">':'<label>Thời hạn<select id="rvHorizon">',
        '<label>Yield<select id="varYield">':'<label>Lợi suất Treasury<select id="varYield">',
        '<label>Ordering<select id="varOrder">':'<label>Thứ tự biến<select id="varOrder">',
        'Tác động phân vị — conditional quantile slopes':'Phản ứng tại các phân vị',
        'VAR chung BTC–ETH và giả định recursive SVAR':'Phản ứng trong hệ VAR BTC–ETH',
        '>Histogram gradient boosting</option>':'>Gradient boosting</option>',
    }.items():
        html=html.replace(old,new)
    # Essential labels stay visible rather than disappearing inside an accordion.
    if 'class="skeleton-line"' not in html:
        html = html.replace('<div id="historyLoading" class="loading-card" role="status" hidden>', '<div id="historyLoading" class="loading-card" role="status" hidden><span class="skeleton-line"></span><span class="skeleton-line"></span>')
    html = html.replace('<h2>Dữ liệu đang được cập nhật thế nào?</h2>', '<h2>Dữ liệu &amp; kiểm chứng</h2><div class="evaluation-banner"><span class="research-badge">Prospective OOS</span><strong>PENDING_FIXED_EVALUATION_WINDOW</strong><span>Kỳ đánh giá: 20/10/2027 UTC</span></div>')
    extra = '<!-- ORBIT STUDIO DIALOGS START --><dialog id="filterSheet" class="filter-sheet"><div class="dialog-heading"><h2>Điều chỉnh góc nhìn</h2><button type="button" data-close="filterSheet" aria-label="Đóng bộ lọc">×</button></div><div id="sheetControls"></div><button type="button" id="applyMobileFilters" class="action-primary">Xem kết quả</button></dialog><dialog id="navDrawer" class="nav-drawer"><div class="dialog-heading"><h2>Không gian nghiên cứu</h2><button type="button" data-close="navDrawer" aria-label="Đóng menu">×</button></div>'+''.join(button(k,l,s,True) for k,l,s in PAGES)+'</dialog><dialog id="shortcutDialog" class="shortcut-dialog"><div class="dialog-heading"><h2>Đi nhanh hơn</h2><button type="button" data-close="shortcutDialog" aria-label="Đóng phím tắt">×</button></div><dl><dt><kbd>Ctrl K</kbd></dt><dd>Tìm thuật ngữ và thao tác</dd><dt><kbd>1–6</kbd></dt><dd>Đổi workspace</dd><dt><kbd>[</kbd> <kbd>]</kbd></dt><dd>Lùi / tiến một ngày</dd><dt><kbd>T</kbd></dt><dd>Đổi sáng / tối</dd><dt><kbd>?</kbd></dt><dd>Phím tắt</dd></dl></dialog><div class="bottom-nav"><button type="button" data-goto="transmission">'+icon('wave')+'<span>Truyền dẫn</span></button><button type="button" data-goto="forecast">'+icon('chart')+'<span>Dự báo</span></button><button type="button" id="bottomMore">'+icon('layers')+'<span>Khám phá</span></button></div><div id="orbitToast" class="toast" role="status" aria-live="polite" hidden></div><!-- ORBIT STUDIO DIALOGS END -->'
    html = html.replace('id="glossarySearch" type="search"', 'id="glossarySearch" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="glossaryResults" type="search"')
    html = html.replace('id="glossaryResults" class="glossary-results"', 'id="glossaryResults" role="listbox" class="glossary-results"')
    html = html.replace('Đọc hiểu trước, phân tích sau.', 'Tìm kiếm &amp; lệnh')
    html = html.replace('ORBIT DICTIONARY', 'ORBIT COMMAND')
    html = html.replace('Nhập thuật ngữ hoặc điều bạn chưa hiểu', 'Thuật ngữ, workspace hoặc thao tác')
    html = html.replace('Ví dụ: OOS, cú sốc, khoảng tin cậy…', 'Thử: dự báo, OOS, đổi theme, tải CSV…')
    html = html.replace('Giải thích ngắn cho dashboard này. Liên kết Google mở ở tab mới khi bạn chọn.', '↑ ↓ chọn · Enter thực hiện · Esc đóng. Liên kết Google mở ở tab mới.')
    html = html.replace('../outputs/research/evidence_20261019/report.html', '../outputs/research/evidence_20261019/report_view.html')
    html = html.replace('<script>', extra+'<script>',1)
    for tag in ['<header class="app-header"', '<nav class="workspace-nav"']:
        html = html.replace(tag, tag.replace(' ', ' data-orbit-inert="true" inert ', 1), 1)
    from src.dashboard_fomc import enhance as enhance_fomc
    css = (ROOT/'dashboard/aurora.css').read_text(encoding='utf-8')
    html = html.replace('</head>', '<style id="orbit-aurora">'+css+'</style></head>', 1)
    return enhance_fomc(html)
