"""Product presentation only: frozen chart data and estimates are unchanged."""
import re
from research_common import ROOT

def workspace(html):
    # Main workflow starts with the estimator. Methodological discussions remain
    # in the report and opt-in details, rather than blocking routine use.
    html=re.sub(r'<header>.*?</header>', '''<header class="app-header"><div class="eyebrow">CRYPTO FINANCE LAB / MACRO &amp; CRYPTO</div><h1>Macro–Crypto Shock Transmission</h1><p>Khám phá phản ứng của Bitcoin và Ethereum trước biến động vĩ mô.</p><div class="dataset-badges"><span>Dữ liệu đến 15/10/2026</span><span>BTC / ETH</span><span>Horizon 1–30 ngày</span><span>UTC</span></div></header>''',html,count=1,flags=re.S)
    tabs=[('transmission','Truyền dẫn','responses rolling'),('forecast','Dự báo rủi ro','forecast rv'),('fomc','FOMC','fomc'),('advanced','Phân vị & VAR','quantile joint'),('methods','Phương pháp & nguồn','overview pit methods')]
    nav='<nav class="workspace-nav" aria-label="Các công cụ phân tích">'+''.join(f'<button type="button" id="tab-{key}" class="workspace-tab" aria-controls="{panels}" aria-pressed="{str(key=="transmission").lower()}">{label}</button>' for key,label,panels in tabs)+'<a class="report-link" href="../outputs/research/release_20261025/report.html">Báo cáo ↗</a></nav>'
    html=re.sub(r'<nav>.*?</nav>',nav,html,count=1,flags=re.S)
    pieces=re.findall(r'<section\b.*?</section>',html,re.S);panels={}
    for piece in pieces:
        match=re.search(r'\bid="([^\"]+)"',piece.split('>',1)[0]);key=match.group(1) if match else 'methods'
        if key=='responses':
            piece=re.sub(r'(<h2>).*?(</h2>)',r'\1Ước lượng phản ứng theo shock\2',piece,count=1,flags=re.S)
            piece=re.sub(r'</h2><p>.*?</p>', '</h2><p class="section-intro">Chọn tài sản, loại shock, chế độ thị trường và horizon để xem phản ứng cùng khoảng tin cậy 95%.</p>',piece,count=1,flags=re.S)
            piece=piece.replace('Monetary STMT +10 bps','Tiền tệ STMT +10 bps').replace('>Full</option>','>Toàn mẫu</option>').replace('>Calm</option>','>Bình thường</option>').replace('>Stress</option>','>Căng thẳng</option>')
            piece=piece.replace('<div class="grid">','<div class="workspace-actions"><button type="button" id="exportResponse" class="action-primary">Tải CSV đường phản ứng</button><button type="button" id="resetResponse" class="action-secondary">Đặt lại bộ lọc</button><span id="selectionLabel" class="selection-label"></span></div><div class="grid">',1)
            piece=piece.replace('<span>Log return cộng dồn</span>','<span id="responseMetricLabel">Phản ứng tại horizon đang chọn</span>')
            piece=piece.replace('<p id="responseTiming" class="note"></p>','<p id="responseTiming" class="compact-meta"></p>')
            piece=piece.replace('<details><summary>Sự kiện lịch sử có shock gần quy mô đang chọn</summary>','<details open class="episode-details"><summary>Các giai đoạn lịch sử có shock tương tự</summary>')
            piece=re.sub(r'<p class="muted">Return quan sát,.*?</p>','<p class="muted">Tối đa 5 giai đoạn không chồng lấp, gồm quy mô shock và lợi suất thực tế.</p>',piece,count=1,flags=re.S)
        elif key=='rolling':
            piece=re.sub(r'</h2><p>.*?</p>','</h2><p class="section-intro">Theo dõi hệ số nhạy cảm theo thời gian, cửa sổ 252 phiên và cập nhật mỗi 21 phiên.</p>',piece,count=1,flags=re.S)
            piece=re.sub(r'<p class="note">.*?</p>','<p class="compact-meta">Dải màu: khoảng tin cậy 95% tại từng thời điểm.</p>',piece,count=1,flags=re.S)
        elif key=='forecast':
            piece=re.sub(r'</h2><p>.*?</p>','</h2><p class="section-intro">So sánh mô hình có và không có thông tin vĩ mô theo tài sản, target, mẫu và kỳ đánh giá.</p>',piece,count=1,flags=re.S)
            piece=piece.replace('<p id="forecastContext" class="note"></p>','<p id="forecastContext" class="compact-meta"></p>')
            history=(ROOT/'dashboard/historical_oos.html').read_text(encoding='utf-8')
            piece=piece.replace('<div id="forecastTable"',history+'<h3>Kiểm định theo kỳ đánh giá đã khóa</h3><p class="compact-meta">Các bảng dưới dùng kỳ/năm ở bộ chọn phía trên; khoảng ngày replay chỉ áp dụng cho biểu đồ và CSV.</p><div id="forecastTable"',1)
        elif key=='fomc':
            piece=re.sub(r'</h2><p>.*?</p>','</h2><p class="section-intro">Tra cứu phản ứng quanh FOMC và khác biệt trước/sau 2020 hoặc giữa các chế độ thị trường.</p>',piece,count=1,flags=re.S)
            piece=re.sub(r'<p>HAC và HC3.*?</p>','<p class="compact-meta">Đơn vị: điểm phần trăm return / +10 bps component PC1. Hai cột BH tương ứng HAC và HC3.</p>',piece,count=1,flags=re.S)
        elif key=='rv':
            piece=re.sub(r'</h2><p>.*?</p>','</h2><p class="section-intro">Đánh giá HAR/HAR-X trên realized variance từ nến Binance USDT, sampling 5 hoặc 15 phút và horizon 1 hoặc 7 ngày.</p>',piece,count=1,flags=re.S)
        elif key=='quantile':
            piece=re.sub(r'</h2><p>.*?</p>','</h2><p class="section-intro">So sánh độ nhạy của return 1 ngày tại các phân vị 5%, 50% và 95%.</p>',piece,count=1,flags=re.S)
        elif key=='joint':
            piece=re.sub(r'</h2><p>.*?</p>','</h2><p class="section-intro">Xem IRF của hệ BTC–ETH khi thay đổi shock, kỳ mẫu, lợi suất Treasury và ordering. Horizon của VAR tính theo phiên.</p>',piece,count=1,flags=re.S)
            piece=piece.replace('<p id="varDiagnostics" class="note limit"></p>','<details class="method-details"><summary>Chẩn đoán mô hình</summary><p id="varDiagnostics"></p></details>')
            piece=re.sub(r'<p>CI tiệm cận pointwise.*?</p>','',piece,count=1,flags=re.S)
        elif key=='overview':
            piece='<section class="panel" id="overview"><h2>Phương pháp và tài liệu</h2><p>Mỗi công cụ giữ rõ nguồn, đơn vị, mẫu ước lượng và cách tính khoảng tin cậy. Báo cáo trình bày thiết kế nghiên cứu, kiểm định và phạm vi diễn giải.</p><div class="resource-links"><a href="../outputs/research/release_20261025/report.html">Mở báo cáo nghiên cứu ↗</a><a href="../outputs/research/release_20261025/source_catalog.csv">Danh mục nguồn dữ liệu ↗</a></div><details class="method-details"><summary>Kết quả tổng hợp của nghiên cứu</summary><p id="releaseSummary"></p></details></section>'
        elif key=='pit':
            piece='<section class="panel" id="pit"><h2>Nguồn và kiểm tra dữ liệu</h2><p>Snapshot kết thúc 15/10/2026. Crypto daily theo UTC; Broad USD là chỉ số DTWEXBGS của FRED. Sampling và source của từng phần được ghi trong báo cáo.</p><details class="method-details"><summary>Định nghĩa và metadata PIT từng feature</summary><div id="pitTable" class="table-wrap"></div></details><details class="method-details"><summary>Trạng thái pipeline</summary><p id="liveStatus"></p><p><a href="../outputs/automation_20261020/health.html">Giám sát tự động, cảnh báo và log</a></p></details></section>'
        elif key=='methods':
            piece='<section class="panel" id="methods"><h2>Ghi chú nghiên cứu</h2><details class="method-details"><summary>Thiết kế và kiểm định theo phiên bản</summary><ul id="findings"></ul></details><p><a href="../outputs/research/release_20261025/report.html">Xem đầy đủ phương pháp và phạm vi kết luận trong báo cáo ↗</a> · <a href="../outputs/research/release_20261025/oos_followup.html">Kế hoạch và trạng thái OOS</a></p></section>'
        # Long methodological notes are opt-in. Keep actual CI/sample labels.
        piece=re.sub(r'<p class="note(?: limit)?">(.*?)</p>',r'<details class="method-details"><summary>Cách đọc kết quả</summary><p>\1</p></details>',piece,flags=re.S)
        group='transmission' if key in ['responses','rolling'] else 'forecast' if key in ['forecast','rv'] else 'fomc' if key=='fomc' else 'advanced' if key in ['quantile','joint'] else 'methods'
        marker=f' data-workspace="{group}"'+(' hidden' if group!='transmission' else '')
        piece=piece.replace('<section ', '<section'+marker+' ',1)
        panels[key]=piece
    assert len(panels)==10, list(panels)
    ordered=''.join(panels[key] for key in ['responses','rolling','forecast','rv','fomc','quantile','joint','overview','pit','methods'])
    html=re.sub(r'<main>.*?</main>', '<main><span id="workspaceTitle" class="sr-only">Truyền dẫn</span>'+ordered+'<footer>Dữ liệu UTC đến 15/10/2026 · Macro–Crypto Finance Lab · <a href="../outputs/research/release_20261025/report.html">Phương pháp và báo cáo</a></footer></main>',html,count=1,flags=re.S)
    html=html.replace('</style>',(ROOT/'dashboard/workspace.css').read_text(encoding='utf-8')+'\n</style>',1)
    html=html.replace('</script>',(ROOT/'dashboard/workspace.js').read_text(encoding='utf-8')+'\n</script>',1)
    from src.dashboard_design import redesign
    return redesign(html)
