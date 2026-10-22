# Orbit 3 — Mã nguồn đầy đủ

Đọc thiết kế và cách tích hợp trước; các file bên dưới là bản đầy đủ để đối chiếu. Gói ZIP đã đặt các file đúng đường dẫn. HTML tự chứa đã gồm dữ liệu nghiên cứu, không cần tự chép payload.

# Orbit 3 — Thiết kế, tích hợp và kiểm chứng

## 1. Chẩn đoán và hướng thiết kế

Bản trước dành nhiều chỗ cho hero và thẻ giới thiệu; người đọc phải đi qua nhiều câu giải thích mới tới kết quả. Các ghi chú kỹ thuật có giá trị nhưng xuất hiện cùng lúc nên khó xác định điều cần nhìn trước. Biểu đồ thiếu phản hồi trực tiếp khi khám phá từng ngày.

Ba thay đổi chính: đưa kết quả lên ngay sau bộ lọc; biến biểu đồ thành công cụ đối chiếu BTC/ETH; mở dần các bảng và ghi chú khi cần. Giữ nền xanh mực, lime tiết chế và tính trung thực của một workspace nghiên cứu.

## 2. Design system

### Palette và ý nghĩa

| Token / vai trò | Dark | Light | Cách nhận biết bổ sung |
|---|---|---|---|
| Background | `#0c1013` | `#f4f6f3` | Nền workspace |
| Sidebar | `#0e1418` | `#f9fbf7` | Tách bằng viền |
| Surface | `#12191d` | `#ffffff` | Panel chính |
| Surface soft | `#10171b` | `#f7f9f5` | Vùng biểu đồ / input |
| Surface raised | `#192329` | `#edf2eb` | Dialog / tooltip |
| Border | `#2b383f` | `#ccd8cd` | Viền 1 px |
| Text | `#edf3f0` | `#172821` | Nội dung chính |
| Muted | `#a6b4b8` | `#52655b` | Nội dung phụ |
| Subtle | `#96a7ac` | `#5d7066` | Metadata nhỏ |
| Accent | `#bef478` | `#40751e` | Lựa chọn / CTA |
| BTC / Calm / dương | `#8cddc4` | `#176f58` | BTC nét liền + tròn; giá trị có dấu + và nhãn |
| ETH | `#b9adf0` | `#7154ac` | Nét đứt + vuông |
| Stress / âm / analogue | `#f0bd95` | `#985027` | Nhãn Stress, dấu −; analogue nét chấm |
| Warning | `#f0ca87` | `#83540d` | Luôn kèm chữ, không chỉ màu |
| CI | Màu của tài sản chọn | Màu của tài sản chọn | Dải gradient 18% → 2,5%, nhãn CI 95% |

Các cặp chữ chính/phụ/subtle trên các surface, chữ CTA và active state có độ tương phản tối thiểu **6,41:1 ở dark** và **4,65:1 ở light** theo phép tính WCAG. Hai đường BTC/ETH có độ tương phản trên nền biểu đồ lần lượt **11,42 / 8,87** ở dark và **5,74 / 5,56** ở light. Viền trang trí và dải CI mờ không được coi là chữ hoặc đường dữ liệu chính.

### Typography

Inter có fallback `Segoe UI`, `system-ui`, `-apple-system`, `sans-serif`; không tải font từ CDN. Các số dùng `font-variant-numeric: tabular-nums`. Không cần tải font để mở offline.

| Vai trò | Desktop | Mobile | Mục đích |
|---|---|---|---|
| Hero ngắn | 32 px / 1,25 | 29 px / 1,25 | Nhận diện workspace |
| Heading panel | 24 px | 23 px | Phân cấp |
| Insight | 20 px | 19 px | Câu trả lời chính |
| Số ước lượng | 48 px | 48 px | Tiêu điểm |
| UI nền | 15 px | 15 px | Nhãn thao tác |
| Diễn giải | 13–14 px | 12–13 px | Một đến hai câu |
| Metadata | 10–12 px | 10–12 px | Đơn vị / timing / nguồn |

Spacing dùng nhịp 4/8: `4, 8, 12, 16, 24, 32`. Radius `8 / 12 / 16`. Sidebar 232 px, icon rail 80 px; topbar 77 px, mobile 64 px. Elevation dùng viền cho panel và shadow cho tooltip/dialog. Z-index: sticky 10, nav 20, tooltip 30, toast 70; dialog dùng top layer của trình duyệt.

Motion: 120 ms cho phản hồi ngắn; 200 ms cho controls/workspace; 320 ms cho count-up và indicator; 400 ms cho morph dữ liệu; 480 ms cho nét vào đầu tiên. Easing `cubic-bezier(.2,.8,.2,1)`; thumb dùng `cubic-bezier(.2,.9,.3,1.15)`. `prefers-reduced-motion` tắt các chuyển động trong CSS và JS. Skeleton chỉ chạy ba lượt.

### Component library

| Component | Cách dùng / hành vi |
|---|---|
| Button | Primary lime, secondary surface, text button; press `.98`, focus ring 2 px |
| Segmented | BTC/ETH và trạng thái; thumb trượt, `aria-pressed`, giữ select gốc |
| Chip / slider | 1/7/14/30; slider 1–30, datalist mốc đúng vị trí |
| Select | Native để hỗ trợ offline, bàn phím và mobile |
| Tooltip / popover | Crosshair bám ngày, BTC/ETH và CI thật; click để ghim |
| Command palette | Native dialog; tìm không dấu; nhóm đi đến / thao tác / thuật ngữ; ↑↓ Enter Esc |
| Tab / nav | 6 workspace, indicator trượt, có icon rail và drawer |
| Card / stat | Một giá trị chính; ghi rõ đơn vị, cỡ mẫu, BH q |
| Badge | CI chứa 0, historical pseudo-OOS, worker cũ, prospective gate |
| Skeleton / error | Lazy replay, trạng thái chờ và retry |
| Empty state | Khoảng ngày không có dữ liệu, ngày đảo thứ tự, query không khớp |
| Toast | CSV, reset, zoom, các thao tác cần phản hồi ngắn |
| Accordion | Timing, bảng dữ liệu, kiểm định, hash và phương pháp giữ nguyên nội dung |

## 3. Wireframe và thứ tự đọc

| Workspace | Desktop | Mobile |
|---|---|---|
| Truyền dẫn | Hero ngắn → control strip → insight → biểu đồ lớn bên trái / chi tiết ngày bên phải → thao tác / ghi chú → rolling và analogues cạnh nhau | Topbar → insight và nút Điều chỉnh → bộ lọc bottom sheet → biểu đồ có viewBox riêng → số kết quả → các panel xếp dọc; bottom navigation |
| Dự báo rủi ro | Bộ chọn → kết luận một câu → badge historical pseudo-OOS → ngày và metric → replay / legend bật tắt → cumulative loss → kiểm tra một ngày → kiểm định và timing mở theo nhu cầu | Cùng thứ tự; metric 2 cột, controls và bảng tự cuộn trong khung |
| FOMC | Tài sản / cửa sổ → hai card policy và information → miền xoay và bảng nhóm trong accordion | Hai card xếp dọc, đầy đủ nhãn đơn vị và giới hạn |
| Phân vị & VAR | Panel phân vị → panel VAR; mỗi panel có controls, chart, bảng/chẩn đoán | Mỗi công cụ một khối, bảng cuộn nội bộ |
| Phương pháp & nguồn | Nguồn → metadata PIT → ghi chú và tài liệu | Accordion và liên kết dạng hàng |
| Dữ liệu & OOS | Badge worker / nút cập nhật → fixed evaluation gate → 4 thẻ trạng thái → capture → ba hoạt động riêng | Các thẻ một cột, cảnh báo và kỳ đánh giá dễ thấy |

Analogue dùng chuỗi lợi suất thực tế theo horizon đã có trong `DATA.analogues`. Rê hoặc chọn thẻ vẽ một đường nét chấm riêng trên response chart, với nhãn ngày quan sát; vùng sự kiện được đánh dấu trên trục ngày của rolling. Không bịa đường giá hoặc coi return thực tế là tác động nhân quả của riêng cú sốc.

Rolling: kéo chọn một vùng để zoom; nhấp đúp hoặc “Toàn kỳ” để đặt lại. Bộ chọn khoảng ngày cung cấp cách thao tác tương đương bằng bàn phím. Khi chọn STMT ở công cụ chính, nhãn rolling ghi rõ đây vẫn là phân tích daily với cú sốc riêng, không ngầm đổi VIX thành STMT.

## 4. Dữ liệu, thống kê và giới hạn

- Các payload `DATA`, `HISTORICAL`, `LATEST` giữ nguyên giá trị so với bản trước.
- Đường nối cubic monotone đi qua đúng các ước lượng từng ngày; đó là cách nối thị giác, không tạo ước lượng cho thời hạn mới.
- CI của tài sản đang chọn là pointwise 95%, không phải simultaneous band. Tooltip cho giá trị gốc tại ngày đang chọn, không đọc giá trị đang tween làm kết quả thống kê.
- BTC/ETH daily USD và RV Binance USDT giữ nguồn/đơn vị riêng. STMT không đồng nhất với policy/information components. VAR innovation không gọi là pure policy shock.
- Bản này sửa cách hiển thị cận FOMC không bị chặn: cận dưới `−∞`, cận trên `+∞`. Không đổi các giá trị nguồn `null` hoặc bounds của nghiên cứu.
- Replay vẫn là historical pseudo-OOS / exploratory. Bật/tắt đường chỉ đổi lớp hiển thị, không đổi loss, p/q hay CSV.
- Prospective giữ `PENDING_FIXED_EVALUATION_WINDOW` và kỳ đánh giá **20/10/2027 UTC**. Worker cũ hơn 150 phút có badge cảnh báo. Không bổ sung giá trực tiếp hoặc dựng bù dự báo.
- Permutation importance trong mục thiết kế cũ vẫn là mô tả, không phải causal importance.

## 5. Tích hợp vào dự án

1. Giải nén gói `orbit_dashboard_v3.zip`.
2. Chép toàn bộ nội dung bên trong vào thư mục gốc `dashboard_crypto`, cùng cấp với `README.md` và `run_release.py`. Gộp các thư mục và thay các file code/giao diện trùng tên.
3. Mở `MO_DASHBOARD.cmd` hoặc `dashboard/index.html`. Bản này đã nhúng CSS/JS/data, không cần cài thư viện hay chạy build để xem.
4. Nếu bạn sửa source CSS/JS/HTML về sau, mở terminal tại gốc repo và chạy:

```powershell
py tools/refresh_dashboard_design.py
```

Lệnh chỉ làm mới phần trình bày từ payload đã nhúng. Không chạy train/fit/collector.

Muốn dùng localhost để kiểm tra:

```powershell
py -m http.server 8000 --bind 127.0.0.1
```

Mở `http://localhost:8000/dashboard/`. Trong Chrome/Edge: F12 → Ctrl+Shift+M → chọn Responsive → nhập width `375`, sau đó `1440`. Ctrl+F5 để bỏ cache bản cũ.

### Những file cần đi cùng nhau

| File | Vai trò |
|---|---|
| `dashboard/design.css` | Toàn bộ design tokens / layout / components / responsive / print |
| `dashboard/design.js` | Charts, compare, pin, slider, brush, analogues, URL, nav, theme, shortcuts, CSV |
| `dashboard/experience.css` | Boot, skeleton, retry, workspace transition |
| `dashboard/experience.js` | Giải nghĩa, command palette, insight ngắn, trạng thái worker |
| `dashboard/transmission.html` | HTML đầy đủ cho màn hình chính, giữ scientific IDs |
| `dashboard/rolling.html` | Rolling chart và bộ chọn ngày |
| `dashboard/analogues.html` | Các giai đoạn tương tự |
| `dashboard/workspace.js` | Nhóm 6 workspace và lazy replay |
| `dashboard/release_functions.js` | Nhãn dễ đọc và dấu vô cực FOMC |
| `src/dashboard_design.py` | Gọi các lớp trình bày theo thứ tự |
| `src/dashboard_studio.py` | Ghép markup mới, có thể refresh lặp lại |
| `dashboard/index.html` | Kết quả HTML tự chứa, mở trực tiếp được |

Các file của Orbit 2 và bản đọc báo cáo đã sửa hình cũng có trong gói đầy đủ. Cần commit các file code mới và merge vào `main` để GitHub Pages/worker dùng bản này. Giao diện mở trên máy không tự thay website công khai. Không đưa data/models/secrets vào Git.

## 6. Kiểm tra

```powershell
node tests/validate_studio.cjs
node tests/validate_experience.cjs
node tests/validate_release_dashboard.cjs
python -m unittest discover -s tests -p test_dashboard_experience.py
python tools/export_public_dashboard.py --dashboard-only
python tools/check_public_dashboard.py --dashboard-only
```

| Mục | Bằng chứng |
|---|---|
| Số liệu không đổi | So sánh JSON cả ba payload với bản V2 |
| Chart mới | 1.800 điểm/CI projection được đối chiếu cho desktop và mobile; route có allowlist; test cận FOMC thực tế |
| Chức năng nghiên cứu | 900 góc nhìn response/CSV, 640 cấu hình forecast/replay, 24 quantile, 108 VAR, 64 FOMC, 8 RV, 8 rolling |
| Lazy replay | Cold boot chưa giải nén; failure/retry và prediction integrity được kiểm tra |
| Refresh | Idempotent, không nhân đôi ID / UI |
| Bàn phím | Chart mũi tên / Enter; Ctrl K; ↑↓ Enter; shortcuts; native dialog; bảng dữ liệu thay thế |
| Mobile | Khung 375 px: filter sheet, đổi ETH/USD/30 ngày, không tràn ngang; bộ lọc/CTA có vùng chạm rộng |
| Desktop | Khung 1440 px: menu, controls, chart và bento không tràn ngang |
| Replay layers | Tắt Thực tế làm ẩn đường; loss không đổi; không thay dữ liệu tính toán |
| Rolling | Kéo zoom từ 139 xuống 65 ước lượng; double-click trở lại 139 |
| CSV | Đã kích hoạt download thực trong Chrome |
| Sáng/tối | Thử trực tiếp và kiểm tra contrast token AA |
| Reduced motion | Guard JS cho morph/count-up/entrance, media rule tắt transition/animation; chưa đổi tùy chọn hệ điều hành trong phiên QA |
| Bản in | Có stylesheet riêng, màu nền trắng, ẩn chrome và controls không cần thiết; chưa in thử trên máy in vật lý |

Thời gian dựng lại response quan sát trong môi trường QA nằm quanh 13–17 ms ở các thao tác đã thử. Đây là số đo tại môi trường kiểm tra, không phải bảo đảm 60 fps trên mọi máy. Nguồn dữ liệu thật và kết nối mạng có thể ảnh hưởng thời gian đọc metadata; phân tích nhúng vẫn mở offline.

# Phụ lục: toàn bộ file trình bày

## dashboard/design.css

```css
/* Orbit 3 · a quiet research instrument. No remote fonts or assets. */
:root{color-scheme:dark;--bg:#0c1013;--sidebar:#0e1418;--surface:#12191d;--surface-raised:#192329;--surface-soft:#10171b;--border:#2b383f;--border-soft:#222e34;--text:#edf3f0;--muted:#a6b4b8;--subtle:#96a7ac;--accent:#bef478;--accent-text:#d0f4ad;--accent-wash:#24301f;--mint:#8cddc4;--lavender:#b9adf0;--peach:#f0bd95;--btc:#8cddc4;--eth:#b9adf0;--positive:#8cddc4;--negative:#f0bd95;--calm:#8cddc4;--stress:#f0bd95;--warning:#f0ca87;--ci:#8cddc4;--result-bg:#141e1a;--result-border:#354735;--font-ui:Inter,"Segoe UI",system-ui,-apple-system,sans-serif;--font-numbers:Inter,"Segoe UI",system-ui,sans-serif;--type-xs:13px;--type-sm:15px;--type-md:18px;--type-title:28px;--type-number:48px;--space-1:4px;--space-2:8px;--space-3:12px;--space-4:16px;--space-6:24px;--space-8:32px;--radius-sm:8px;--radius:12px;--radius-lg:16px;--shadow:0 12px 40px #00000020;--shadow-overlay:0 24px 80px #00000065;--sidebar-width:232px;--header-height:77px;--z-sticky:10;--z-nav:20;--z-tooltip:30;--z-toast:70;--motion-fast:120ms;--motion-ui:200ms;--motion-panel:320ms;--motion-chart:480ms;--ease:cubic-bezier(.2,.8,.2,1);--spring:cubic-bezier(.2,.9,.3,1.15)}
:root[data-theme=light]{color-scheme:light;--bg:#f4f6f3;--sidebar:#f9fbf7;--surface:#fff;--surface-raised:#edf2eb;--surface-soft:#f7f9f5;--border:#ccd8cd;--border-soft:#dee6dc;--text:#172821;--muted:#52655b;--subtle:#5d7066;--accent:#40751e;--accent-text:#365f20;--accent-wash:#e7f0df;--mint:#176f58;--lavender:#7154ac;--peach:#985027;--btc:#176f58;--eth:#7154ac;--positive:#176f58;--negative:#985027;--calm:#176f58;--stress:#985027;--warning:#83540d;--ci:#176f58;--result-bg:#f3f7ed;--result-border:#d1dfc2;--shadow:0 12px 40px #17282108;--shadow-overlay:0 24px 80px #17282128}
@media(prefers-color-scheme:light){:root:not([data-theme]){color-scheme:light}}
*{box-sizing:border-box}html{scroll-behavior:auto;scroll-padding-top:100px}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.65 var(--font-ui);-webkit-font-smoothing:antialiased}body,button,input,select{font-family:var(--font-ui)}button,input,select{font-size:15px}button,a,select,input,summary{touch-action:manipulation;-webkit-tap-highlight-color:transparent}button{cursor:pointer;color:inherit}button:disabled{cursor:default;opacity:.5}a{color:var(--mint);text-underline-offset:4px}button,select,input,summary,a{transition:background-color var(--motion-fast),color var(--motion-fast),border-color var(--motion-fast),box-shadow var(--motion-fast)}button:active:not(:disabled){transform:scale(.98)}:focus-visible{outline:2px solid var(--accent);outline-offset:4px}[hidden]{display:none!important}.sr-only{position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;padding:0!important;margin:-1px!important;border:0!important}.ui-icon{display:inline-block;width:20px;height:20px;flex:0 0 20px;vertical-align:middle}.skip-link{position:fixed;top:-90px;left:250px;z-index:100;background:var(--accent);color:var(--bg);padding:12px 20px;border-radius:8px}.skip-link:focus{top:16px}.status-dot{width:6px;height:6px;background:var(--accent);display:inline-block;border-radius:50%;flex-shrink:0}kbd{font:11px/1.4 var(--font-ui);border:1px solid var(--border);border-radius:4px;color:var(--muted);padding:2px 5px;font-variant-numeric:tabular-nums}mark{background:color-mix(in srgb,var(--accent) 20%,transparent);color:var(--text);border-radius:2px}
/* Navigation */
.workspace-nav{position:fixed;inset:0 auto 0 0;width:var(--sidebar-width);height:100dvh;z-index:var(--z-nav);display:flex;flex-direction:column;align-items:stretch;gap:0;padding:30px 16px 20px;background:var(--sidebar);border:0;border-right:1px solid var(--border-soft);overflow:auto}.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--text);margin:0 0 35px;padding:0 12px;line-height:1}.brand-symbol{color:var(--accent);width:34px;height:34px;flex-basis:34px;stroke-width:1.2}.brand>span{font-size:34px;font-weight:700;letter-spacing:-1.8px}.brand-dot{color:var(--accent)}.brand small{display:block;font-size:8px;letter-spacing:2px;color:var(--muted);margin:9px 0 0 2px;font-weight:500}.nav-items{display:flex;flex-direction:column;position:relative;gap:4px}.nav-label{margin:23px 12px 6px;color:var(--subtle);font-size:11px;text-transform:uppercase;letter-spacing:1.4px;font-weight:600}.nav-label:first-of-type{margin-top:0}.workspace-tab{position:relative;z-index:1;display:flex;gap:10px;align-items:center;width:100%;min-height:46px;border:1px solid transparent;border-radius:9px;background:transparent;padding:11px 12px;text-align:left;white-space:nowrap;color:var(--muted);font:500 13px/1.4 var(--font-ui)}.workspace-tab>span{flex:1}.workspace-tab kbd{opacity:.55;font-size:10px;border:0;padding:0}.workspace-tab .ui-icon{width:18px;height:18px;flex-basis:18px}.workspace-tab:hover{background:color-mix(in srgb,var(--surface-raised) 80%,transparent);color:var(--text)}.workspace-tab[aria-pressed=true]{background:transparent;color:var(--accent-text);border-color:transparent}.workspace-tab[aria-pressed=true] .ui-icon{color:var(--accent)}#navActive{position:absolute;left:0;right:0;top:0;height:46px;background:var(--accent-wash);border:1px solid color-mix(in srgb,var(--accent) 14%,transparent);border-radius:9px;pointer-events:none;transition:transform var(--motion-panel) var(--ease),height var(--motion-panel) var(--ease)}.sidebar-bottom{margin-top:auto;padding:40px 10px 0}.sidebar-caption{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--muted);margin:20px 0}.sidebar-method,.sidebar-collapse{display:flex;align-items:center;gap:8px;width:100%;background:none;border:0;font-size:12px;padding:10px 0;color:var(--muted);text-align:left}.sidebar-method .ui-icon{width:14px;height:14px;margin-left:auto}.sidebar-collapse{border-top:1px solid var(--border-soft);margin-top:16px;padding-top:16px}.lab-signature{display:block;font-size:9px;letter-spacing:1.2px;color:var(--subtle);margin-top:20px}.mobile-workspace-picker,.bottom-nav{display:none}
:root[data-nav-collapsed=true]{--sidebar-width:80px}:root[data-nav-collapsed=true] .workspace-nav{padding-inline:12px}:root[data-nav-collapsed=true] .brand{padding:0 10px}:root[data-nav-collapsed=true] .brand>span,:root[data-nav-collapsed=true] .workspace-tab>span,:root[data-nav-collapsed=true] .workspace-tab kbd,:root[data-nav-collapsed=true] .nav-label,:root[data-nav-collapsed=true] .sidebar-caption,:root[data-nav-collapsed=true] .sidebar-method,:root[data-nav-collapsed=true] .sidebar-collapse>span,:root[data-nav-collapsed=true] .lab-signature{display:none}:root[data-nav-collapsed=true] .workspace-tab{justify-content:center;padding:12px}:root[data-nav-collapsed=true] .nav-items{gap:8px}:root[data-nav-collapsed=true] .sidebar-bottom{padding:20px 10px}:root[data-nav-collapsed=true] .brand-symbol{width:28px;flex-basis:28px}:root[data-nav-collapsed=true] .brand{margin-bottom:40px}
/* Chrome and restrained editorial hierarchy */
.app-header{position:sticky;top:0;z-index:var(--z-sticky);height:var(--header-height);margin-left:var(--sidebar-width);padding:0 32px;display:flex;align-items:center;justify-content:space-between;gap:20px;background:color-mix(in srgb,var(--bg) 95%,transparent);backdrop-filter:blur(14px);border-bottom:1px solid var(--border-soft)}.topbar-path,.topbar-actions{display:flex;align-items:center;gap:12px;min-width:0}.topbar-path{font-size:12px;white-space:nowrap}.topbar-label,.path-divider{color:var(--subtle)}.topbar-path strong{font-weight:500}.topbar-date{font-size:11px;color:var(--muted);white-space:nowrap;border:1px solid var(--border-soft);border-radius:6px;padding:5px 9px}.icon-button{width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--muted)}#openNavigation{display:none}#themeToggle .ui-icon{transition:transform var(--motion-panel) var(--ease),opacity var(--motion-panel)}[data-theme=light] #themeToggle .ui-icon{transform:rotate(85deg)}.glossary-trigger{display:flex;align-items:center;gap:10px;min-height:36px;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:5px 10px;color:var(--muted);font-size:12px}.glossary-trigger>span:first-child{font-size:23px;line-height:1}.top-export{display:flex;align-items:center;gap:7px;border:0;background:var(--accent);color:var(--bg);border-radius:8px;padding:9px 12px;font-size:12px;font-weight:650}.top-export .ui-icon{width:15px;height:15px;flex-basis:15px}main{margin-left:var(--sidebar-width);max-width:none;padding:28px 32px 24px;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:24px;min-width:0}main>*{min-width:0}.workspace-hero{grid-column:1/-1;position:relative;min-height:0;padding:0 0 2px;display:block}.hero-eyebrow{font-size:10px;font-weight:500;letter-spacing:1.8px;color:var(--subtle);margin-bottom:9px}.workspace-hero h1{font-size:32px;font-weight:600;line-height:1.25;letter-spacing:-1.1px;margin:0 0 8px}.workspace-hero h1>span{color:var(--accent)}.workspace-hero p{font-size:14px;color:var(--muted);margin:0;max-width:720px;line-height:1.6}.panel{grid-column:1/-1;min-width:0;margin:0;padding:26px;border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface);box-shadow:none}.panel.bento-panel{grid-column:auto;transition:transform var(--motion-ui) var(--ease),border-color var(--motion-ui)}@media(hover:hover){.bento-panel:hover{transform:translateY(-2px);border-color:color-mix(in srgb,var(--muted) 50%,var(--border))}}.panel h2{font-size:24px;font-weight:550;letter-spacing:-.6px;line-height:1.4;margin:0 0 8px}.panel h3{font-size:18px;font-weight:550;letter-spacing:-.2px;line-height:1.4}.panel h4{font-size:15px;font-weight:600;margin-top:24px}.section-intro{font-size:14px;line-height:1.7;color:var(--muted);max-width:750px;margin:0 0 24px}.section-kicker{display:block;font-size:10px;letter-spacing:1.5px;color:var(--subtle);margin-bottom:8px}.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.bento-panel h2{font-size:22px}.panel-heading .text-button{font-size:12px;white-space:nowrap}footer{grid-column:1/-1;order:999;display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:11px;color:var(--subtle);padding:12px 2px 0;border:0;margin:0}.footer-dot{color:var(--accent)}.footer-separator{color:var(--border);padding:0 8px}
/* Controls and reusable primitives */
.controls{display:flex;align-items:end;flex-wrap:wrap;gap:16px;margin:20px 0}.controls label{position:relative;display:flex;flex-direction:column;gap:8px;color:var(--muted);font-size:12px;min-width:0;flex:1 1 150px}.controls input,.controls select,select,input[type=date]{min-height:42px;background:var(--surface-soft);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:9px 32px 9px 12px;font-size:13px;max-width:100%;min-width:0;width:100%}select{appearance:auto;background-image:none}select:hover,input[type=date]:hover{border-color:var(--subtle)}.controls button{align-self:center}.control-strip{position:relative;display:grid;grid-template-columns:minmax(140px,.8fr) minmax(180px,1.2fr) minmax(190px,1.1fr) minmax(150px,.9fr);align-items:center;gap:22px;margin:0;padding:0 0 23px;border-bottom:1px solid var(--border-soft)}#controlHome{position:sticky;top:var(--header-height);z-index:9;background:var(--surface);padding-top:0}.control-group{min-width:0}.control-label{display:flex;gap:6px;align-items:center;font-size:11px;color:var(--muted);margin-bottom:8px;line-height:1}.control-label label{display:inline;font-size:11px;color:var(--muted)}.control-label output{font-variant-numeric:tabular-nums;color:var(--text);font-weight:600}.shock-control{flex:initial!important}.term-help{display:inline-flex;align-items:center;justify-content:center;width:19px;height:19px;min-height:19px;border:1px solid var(--border);border-radius:50%;background:transparent;color:var(--muted);font-size:11px;line-height:1;padding:0;flex:0 0 19px}.controls label>.term-help{position:absolute;top:0;right:2px}.segmented{position:relative;display:flex;border:1px solid var(--border);background:var(--surface-soft);border-radius:8px;padding:3px;isolation:isolate}.segmented button{position:relative;z-index:1;flex:1;min-width:0;min-height:34px;border:0;border-radius:5px;background:transparent;font-size:12px;font-weight:550;color:var(--muted);padding:5px 8px;white-space:nowrap}.segmented button[aria-pressed=true]{color:var(--text)}.segment-thumb{position:absolute;top:3px;bottom:3px;left:3px;width:calc((100% - 6px)/2);border:1px solid var(--border);background:var(--surface-raised);box-shadow:0 1px 3px #00000010;border-radius:5px;transition:transform var(--motion-ui) var(--spring);z-index:0}.regime-segment .segment-thumb{width:calc((100% - 6px)/3)}.asset-mark{font-size:15px;color:var(--btc);margin-right:3px}[data-asset=eth] .asset-mark{color:var(--eth)}.horizon-control input[type=range]{appearance:none;display:block;padding:0;min-height:22px;height:22px;min-width:0;width:100%;background:transparent;border:0;cursor:ew-resize;accent-color:var(--accent)}input[type=range]::-webkit-slider-runnable-track{height:3px;background:var(--border);border-radius:3px}input[type=range]::-webkit-slider-thumb{appearance:none;width:13px;height:13px;background:var(--accent);border:3px solid var(--surface);box-shadow:0 0 0 1px var(--accent);border-radius:50%;margin-top:-5px}input[type=range]::-moz-range-track{height:3px;background:var(--border)}input[type=range]::-moz-range-thumb{height:9px;width:9px;background:var(--accent);border:2px solid var(--surface);border-radius:50%}.range-marks{display:flex;justify-content:space-between;font-size:9px;color:var(--subtle);margin-top:0}.text-button{border:0;background:transparent;color:var(--muted);font-size:13px;padding:4px 0;min-height:28px;text-decoration:none}.text-button:hover{color:var(--accent)}.workspace-actions{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin:20px 0 14px}.action-primary,.action-secondary{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:1px solid var(--border);border-radius:8px;min-height:38px;padding:8px 13px;font-size:12px;font-weight:550}.action-primary{background:var(--accent);border-color:var(--accent);color:var(--bg);position:relative}.action-primary:hover{box-shadow:0 0 0 4px color-mix(in srgb,var(--accent) 8%,transparent)}.action-secondary{background:var(--surface-soft);color:var(--text)}.workspace-actions .selection-label{font-size:11px;color:var(--subtle);margin-left:3px}.workspace-actions>#printDashboard{margin-left:auto}.badge,.research-badge,.certainty-badge,.state-pill{display:inline-flex;align-items:center;gap:6px;border-radius:6px;border:1px solid var(--border);padding:5px 8px;font-size:11px;font-weight:500;line-height:1.4;color:var(--muted);white-space:normal}.research-badge{color:var(--warning);background:color-mix(in srgb,var(--warning) 6%,transparent);border-color:color-mix(in srgb,var(--warning) 24%,var(--border))}.certainty-badge[data-state=unclear]{color:var(--muted)}.certainty-badge[data-state=clear]{color:var(--mint)}.state-pill[data-state=warning]{color:var(--warning);border-color:color-mix(in srgb,var(--warning) 36%,var(--border))}.state-pill[data-state=good]{color:var(--mint)}
/* First answer, then a chart to explore it. */
.response-workspace{padding:24px}.insight-strip{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:24px 0 26px;border:0;background:none}.reading-eyebrow{display:block;font-size:9px;letter-spacing:1.5px;color:var(--subtle);margin-bottom:8px}.insight-strip strong{display:block;font-size:20px;font-weight:500;line-height:1.55;letter-spacing:-.45px;color:var(--text)}.insight-strip p{margin:4px 0 0;font-size:13px;color:var(--muted);max-width:720px}.insight-strip .certainty-badge{flex-shrink:0;max-width:180px}.response-grid{display:grid;grid-template-columns:minmax(0,1fr) 250px;gap:22px;align-items:stretch}.response-plot{min-width:0;border:1px solid var(--border-soft);border-radius:12px;background:var(--surface-soft);padding:18px 16px 12px;position:relative}.chart-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.chart-toolbar>div>strong{font-size:13px;display:block;font-weight:550}.chart-toolbar>div>span{font-size:10px;color:var(--subtle);display:block;margin-top:2px}.horizon-presets{display:flex;gap:3px;padding:3px;border:1px solid var(--border);border-radius:7px;flex-shrink:0}.horizon-presets button{border:0;border-radius:4px;min-height:26px;padding:4px 7px;font-size:10px;font-variant-numeric:tabular-nums;color:var(--muted);background:transparent}.horizon-presets button[aria-pressed=true]{background:var(--accent-wash);color:var(--accent-text)}.interactive-chart{position:relative}.interactive-chart svg{touch-action:pan-y;cursor:crosshair;max-width:100%;overflow:visible}svg:not(.ui-icon){display:block;width:100%;height:auto}svg text{fill:var(--muted);font:12px var(--font-numbers);font-variant-numeric:tabular-nums}svg .plot-grid{stroke:var(--border-soft);stroke-width:1}svg .plot-zero{stroke:var(--subtle);stroke-width:1;stroke-dasharray:4 6}svg .curve-btc{stroke:var(--btc)}svg .curve-eth{stroke:var(--eth);stroke-dasharray:6 5}svg .curve-line{fill:none;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}svg .curve-analogue{fill:none;stroke:var(--peach);stroke-width:1.8;stroke-dasharray:2 5}svg .chart-pin{stroke:var(--accent);stroke-dasharray:3 5;stroke-width:1}svg .crosshair{stroke:var(--muted);stroke-width:1;stroke-dasharray:3 4}svg .point-btc{fill:var(--btc);stroke:var(--surface-soft);stroke-width:2}svg .point-eth{fill:var(--eth);stroke:var(--surface-soft);stroke-width:2}svg .brush-region{fill:var(--accent);opacity:.12;stroke:var(--accent);stroke-width:1}svg .selected-date{fill:var(--peach);opacity:.14}.chart-legend{display:flex;align-items:center;flex-wrap:wrap;gap:12px;font-size:10px;color:var(--muted);padding-top:7px}.chart-legend>span,.chart-legend>label{display:inline-flex;align-items:center;gap:5px}.chart-legend i{width:13px;height:2px;background:var(--btc);display:inline-block}.chart-legend .eth-key i{height:0;background:none;border-top:2px dashed var(--eth)}.chart-legend .band{height:7px;background:color-mix(in srgb,var(--ci) 18%,transparent);border:1px solid color-mix(in srgb,var(--ci) 40%,transparent);border-radius:2px}.compare-toggle{margin-left:auto;font-size:10px;cursor:pointer}.compare-toggle input{accent-color:var(--accent);width:12px;height:12px;margin:0}.chart-caption{font-size:10px;color:var(--subtle);display:flex;gap:10px;justify-content:space-between;margin-top:10px;min-height:16px}#analogueOverlayLabel{color:var(--peach)}.chart-tooltip{position:absolute;z-index:var(--z-tooltip);pointer-events:none;background:var(--surface-raised);border:1px solid var(--border);border-radius:9px;box-shadow:var(--shadow);padding:12px 14px;font-size:12px;width:260px;max-width:calc(100vw - 60px)}.chart-tooltip strong{display:block;font-weight:600;margin-bottom:7px;color:var(--text)}.tooltip-row{display:grid;grid-template-columns:36px 1fr;gap:4px 10px;align-items:baseline;margin:6px 0}.tooltip-row>b{font-size:11px}.tooltip-row span{font-variant-numeric:tabular-nums;text-align:right;font-size:12px}.tooltip-row small{grid-column:2;color:var(--muted);font-size:10px;white-space:nowrap}.tooltip-row.btc>b{color:var(--btc)}.tooltip-row.eth>b{color:var(--eth)}.result{background:var(--result-bg);border:1px solid var(--result-border);border-radius:12px;padding:22px 20px;min-width:0;display:block}.result-kicker{display:flex;align-items:center;gap:6px;font-size:8px;letter-spacing:1.1px;color:var(--muted);margin-bottom:22px}.result-kicker>button{margin-left:auto;font-size:9px;letter-spacing:0;white-space:nowrap;color:var(--accent);background:none;border:0;padding:0}#responseMetricLabel{font-size:12px;color:var(--muted)}.result .big{font-family:var(--font-numbers);font-variant-numeric:tabular-nums;font-size:44px;letter-spacing:-2.2px;font-weight:500;line-height:1.2;margin:8px 0 12px;color:var(--text)}.result p{font-size:11px;line-height:1.65;margin:8px 0;color:var(--muted)}#responseCI{font-variant-numeric:tabular-nums;color:var(--text);font-size:11px;overflow-wrap:anywhere}.interval-meter{margin:15px 0;display:flex;align-items:center;gap:8px;font-size:9px;color:var(--subtle)}.interval-meter>div{position:relative;flex:1;height:15px}.interval-meter>div:before{content:'';position:absolute;left:0;right:0;top:7px;height:1px;background:var(--border)}#intervalBand{position:absolute;top:4px;height:7px;background:color-mix(in srgb,var(--mint) 25%,transparent);border:1px solid var(--mint);border-radius:3px}#intervalPoint{position:absolute;width:7px;height:7px;top:4px;margin-left:-3px;background:var(--mint);border-radius:50%}#intervalZero{position:absolute;width:1px;height:15px;background:var(--subtle)}.result .verdict{font-size:12px;color:var(--text);line-height:1.7;margin:13px 0 18px}.result-divider{height:1px;background:var(--result-border);margin:16px 0}.result-footnote{font-size:9px;color:var(--subtle);margin-top:16px;padding-top:12px;border-top:1px solid var(--result-border)}.chart-caveat{font-size:11px;line-height:1.75;color:var(--muted);margin:12px 0}.chart-caveat .text-button{font-size:11px;margin-left:3px}.compact-meta{font-size:12px;line-height:1.8;color:var(--muted);overflow-wrap:anywhere}.context-details,.research-details,.method-details,.quick-guide{border:0;border-top:1px solid var(--border-soft);border-radius:0;background:none;margin:0;padding:12px 0}.context-details summary,.research-details summary,.method-details summary,.quick-guide summary,details>summary{font-size:12px;line-height:1.6;color:var(--muted);font-weight:500;cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;min-height:24px}.context-details summary:before,.research-details summary:before,.method-details summary:before,.quick-guide summary:before,details>summary:before{content:'+';font-weight:400;color:var(--subtle);font-size:15px}.context-details[open]>summary:before,.research-details[open]>summary:before,.method-details[open]>summary:before,.quick-guide[open]>summary:before,details[open]>summary:before{content:'−'}details>summary::-webkit-details-marker{display:none}.context-details p,.research-details p,.method-details p{font-size:13px;line-height:1.8;color:var(--muted)}.guide-examples{display:flex;gap:8px;flex-wrap:wrap;padding-top:12px}.guide-examples button{border:1px solid var(--border);background:var(--surface-soft);color:var(--text);padding:8px 10px;border-radius:7px;font-size:12px}.table-wrap{width:100%;overflow:auto;max-width:100%;margin-top:14px}table{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}th,td{text-align:left;white-space:nowrap;border:0;border-bottom:1px solid var(--border-soft);padding:11px 12px;color:var(--muted)}th{font-size:11px;font-weight:550;background:var(--surface-soft);color:var(--text)}td{background:transparent}tr:hover td{background:var(--surface-soft)}
/* Secondary exploration */
.rolling-controls{margin:16px 0 18px;gap:10px}.rolling-controls label{font-size:10px}.rolling-controls select{font-size:11px;min-height:36px}#rollingChart{cursor:crosshair;touch-action:pan-y}#rollingRangeLabel{font-size:10px}#rolling .controls input{font-size:11px}#applyRollingRange{font-size:12px;background:var(--accent-wash);color:var(--accent-text);border:1px solid var(--border);border-radius:7px;padding:10px}.analogue-cards{display:grid;gap:7px;margin-top:18px}.analogue-card{display:grid;grid-template-columns:minmax(0,1fr) 78px 70px;align-items:center;gap:12px;width:100%;text-align:left;min-height:63px;border:1px solid var(--border-soft);border-radius:9px;padding:11px 12px;background:var(--surface-soft)}.analogue-card:hover,.analogue-card:focus-visible,.analogue-card[aria-pressed=true]{border-color:var(--peach);background:color-mix(in srgb,var(--peach) 4%,var(--surface))}.analogue-card strong{font-weight:500;font-size:12px;display:block}.analogue-card small{display:block;font-size:9px;color:var(--subtle);margin-top:3px}.analogue-card>span:last-child{text-align:right;font-variant-numeric:tabular-nums;color:var(--text);font-size:14px}.analogue-card svg{height:28px;width:78px}.analogue-card polyline{stroke:var(--peach);stroke-width:1.6;fill:none}.analogue-card line{stroke:var(--border)}.analogue-card circle{fill:var(--peach)}
/* Shared data visualization in secondary workspaces */
svg line[stroke="#e1ebf1"],svg line[stroke="#dce7eb"]{stroke:var(--border-soft)}svg line[stroke="#819ca9"],svg line[stroke="#8ca5b3"]{stroke:var(--subtle);stroke-dasharray:4 6}svg polygon[fill="#0c789b"]{fill:var(--mint);opacity:.1}svg polyline[stroke="#087196"]{stroke:var(--mint)}svg polyline[stroke="#64748b"]{stroke:var(--muted);stroke-dasharray:2 2}svg polyline[stroke="#ad5f2c"]{stroke:var(--peach);stroke-dasharray:7 4}svg polyline[stroke="#7e67a6"]{stroke:var(--lavender);stroke-dasharray:3 4}svg circle[fill="#cc862e"]{fill:var(--accent)}#quantileChart,#varChart{margin:20px 0 10px}.historical-oos{border-top:1px solid var(--border);margin-top:24px;padding-top:24px}.history-heading{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}.history-heading>.research-badge{width:max-content}.history-heading>div{flex-basis:100%}.history-heading h3{font-size:22px;margin:7px 0}.history-heading .eyebrow{font-size:9px;color:var(--subtle);letter-spacing:1.5px}.history-badge{font-size:11px;color:var(--mint)}.history-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;border:1px solid var(--border);border-radius:10px;overflow:hidden;margin:22px 0;background:var(--border)}.history-metrics>div{background:var(--surface-soft);padding:16px}.history-metrics span{display:block;font-size:10px;color:var(--muted)}.history-metrics strong{display:block;font-weight:500;font-size:22px;font-variant-numeric:tabular-nums;margin-top:7px;overflow-wrap:anywhere}.history-legend{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:12px 0 22px}.history-legend button{display:inline-flex;align-items:center;gap:7px;background:none;border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:11px;padding:7px 10px}.history-legend button[aria-pressed=false]{opacity:.5;text-decoration:line-through}.history-legend i{height:2px;width:14px;background:var(--muted)}.history-legend [data-curve="1"] i{background:var(--peach)}.history-legend [data-curve="2"] i{background:var(--mint)}.history-legend [data-curve="3"] i{background:var(--lavender)}.history-hashes{font:11px/1.8 var(--font-ui);overflow-wrap:anywhere}.fomc-summary{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:22px 0}.fomc-card{padding:24px;background:var(--surface-soft);border:1px solid var(--border);border-radius:12px}.fomc-card>span{font-size:12px;color:var(--muted)}.fomc-card strong{font-variant-numeric:tabular-nums;display:block;font-size:30px;font-weight:500;letter-spacing:-1px;margin:10px 0}.fomc-card p{font-size:13px;color:var(--muted);margin:0}.fomc-card small{display:block;font-size:10px;color:var(--subtle);margin-top:12px}.resource-links{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}.resource-links a{border:1px solid var(--border);border-radius:8px;font-size:13px;padding:10px 13px;text-decoration:none}.status-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:24px 0}.status-grid>article,.status-grid>div{border:1px solid var(--border);background:var(--surface-soft);border-radius:12px;padding:22px;min-width:0}.status-grid span{font-size:12px;color:var(--muted)}.status-grid strong{display:block;font-size:25px;font-weight:500;font-variant-numeric:tabular-nums;margin:12px 0 9px;overflow-wrap:anywhere}.status-grid p{font-size:12px;color:var(--muted);line-height:1.7;margin:0}.operations-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.operations-toolbar button{min-height:38px;border:1px solid var(--border);border-radius:7px;background:var(--surface-soft);padding:8px 12px;font-size:12px}.operations-toolbar a{font-size:12px;margin-left:auto}.evaluation-banner{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:22px 0;padding:18px;border:1px solid color-mix(in srgb,var(--warning) 30%,var(--border));border-radius:10px;background:color-mix(in srgb,var(--warning) 4%,var(--surface))}.evaluation-banner strong{font:11px/1.6 var(--font-ui);color:var(--warning);overflow-wrap:anywhere}.evaluation-banner>span:last-child{font-size:12px;color:var(--muted)}.explain-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.explain-grid>div{padding:20px;background:var(--surface-soft);border-radius:10px}.explain-grid h3{font-size:16px;margin-top:0}.explain-grid p{font-size:13px;color:var(--muted)}
/* Native dialogs keep focus and escape behavior consistent offline. */
dialog{color:var(--text);background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:24px;box-shadow:var(--shadow-overlay);max-height:calc(100dvh - 48px);overflow:auto}dialog::backdrop{background:#03070bb3;backdrop-filter:blur(5px)}dialog[open]{animation:dialog-in var(--motion-ui) var(--ease)}@keyframes dialog-in{from{opacity:0;transform:translateY(8px) scale(.985)}to{opacity:1;transform:none}}.dialog-heading,.glossary-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:20px}.dialog-heading h2,.glossary-heading h2{font-size:22px;font-weight:550;margin:0;letter-spacing:-.5px}.dialog-heading>button,.glossary-heading>button{width:32px;height:32px;border:1px solid var(--border);background:var(--surface-soft);color:var(--muted);border-radius:7px;font-size:21px}.glossary-dialog{width:min(780px,calc(100vw - 40px));padding:24px}.glossary-heading .eyebrow{display:none}.glossary-dialog>label{font-size:12px;color:var(--muted);display:block;margin-bottom:8px}.glossary-dialog>input{font-size:17px;width:100%;padding:14px 15px;border:1px solid var(--border);background:var(--surface-soft);border-radius:9px;color:var(--text)}.glossary-layout{display:grid;grid-template-columns:270px minmax(0,1fr);gap:24px;margin-top:20px}.glossary-results{display:flex;flex-direction:column;gap:3px;max-height:350px;overflow:auto;border-right:1px solid var(--border-soft);padding-right:12px}.command-group{font-size:9px;text-transform:uppercase;letter-spacing:1.4px;color:var(--subtle);margin:13px 9px 6px}.command-group:first-child{margin-top:0}.glossary-results button{border:1px solid transparent;background:transparent;color:var(--muted);font-size:12px;padding:10px;text-align:left;border-radius:7px;min-height:39px}.glossary-results button[aria-pressed=true]{background:var(--accent-wash);color:var(--text);border-color:color-mix(in srgb,var(--accent) 20%,var(--border))}.glossary-results button:hover{background:var(--surface-raised);color:var(--text)}.glossary-detail{min-width:0}.glossary-detail h3{font-size:22px;line-height:1.5;font-weight:500;letter-spacing:-.4px;margin:0 0 12px}.glossary-detail p{font-size:14px;line-height:1.8;color:var(--muted)}.term-example{background:var(--surface-soft);border:1px solid var(--border-soft);border-radius:9px;padding:14px 16px;margin:18px 0}.term-example>strong{font-size:11px;color:var(--mint);font-weight:500}.term-example>p{font-size:12px;margin:7px 0 0}.glossary-detail a{font-size:12px}.glossary-footnote{font-size:10px;color:var(--subtle);margin:20px 0 0;border-top:1px solid var(--border-soft);padding-top:14px}.shortcut-dialog{width:min(450px,calc(100vw - 32px))}.shortcut-dialog dl{display:grid;grid-template-columns:90px 1fr;gap:18px;font-size:13px}.shortcut-dialog dd{margin:0;color:var(--muted)}.filter-sheet{width:min(550px,100vw)}.filter-sheet>.action-primary{width:100%;margin-top:24px}.nav-drawer{width:min(400px,calc(100vw - 24px))}.nav-drawer>[data-goto]{display:flex;gap:12px;align-items:center;border:0;border-bottom:1px solid var(--border-soft);width:100%;padding:16px 8px;background:none;color:var(--text);font-size:14px}.toast{position:fixed;z-index:var(--z-toast);bottom:24px;left:calc(50% + var(--sidebar-width)/2);transform:translateX(-50%);padding:12px 18px;border:1px solid var(--border);border-radius:10px;background:var(--surface-raised);color:var(--text);font-size:12px;box-shadow:var(--shadow);max-width:calc(100vw - 40px);width:max-content}.mobile-filter-bar{display:none}
@media(min-width:1600px){main{padding-left:48px;padding-right:48px}.response-grid{grid-template-columns:minmax(0,1fr) 290px}.result .big{font-size:52px}.insight-strip strong{font-size:23px}.control-strip{gap:32px}}
@media(max-width:1190px) and (min-width:761px){:root{--sidebar-width:80px}.workspace-nav{padding-inline:12px}.brand{padding:0 10px}.brand>span,.workspace-tab>span,.workspace-tab kbd,.nav-label,.sidebar-caption,.sidebar-method,.sidebar-collapse>span,.lab-signature{display:none}.workspace-tab{justify-content:center;padding:12px}.nav-items{gap:8px}.sidebar-bottom{padding:20px 10px}.brand-symbol{width:28px;flex-basis:28px}.brand{margin-bottom:40px}.topbar-label,.path-divider{display:none}.app-header{padding:0 24px}.control-strip{gap:14px;grid-template-columns:140px minmax(170px,1fr) minmax(170px,1fr)}.horizon-control{grid-column:1/-1;display:grid;grid-template-columns:100px 1fr;gap:12px;align-items:center}.horizon-control .range-marks{display:none}.control-label{margin-bottom:0}.response-grid{grid-template-columns:minmax(0,1fr) 240px}.insight-strip strong{font-size:18px}}
@media(max-width:980px){main{padding:24px;gap:20px}.panel{padding:22px}.response-grid{grid-template-columns:1fr}.result{display:grid;grid-template-columns:1fr 1fr;column-gap:24px;padding:20px}.result-kicker{grid-column:1/-1;margin-bottom:12px}.result .big{grid-column:1;grid-row:3;margin:5px 0 10px}.interval-meter{grid-column:2;grid-row:3}.result .verdict{grid-column:2;grid-row:4;align-self:center;margin:0}.result-divider{display:none}.result-footnote{grid-column:1/-1;margin-top:12px}#responseCI{grid-column:1;grid-row:4}#responseSample,#responseInference{margin:5px 0}.insight-strip{align-items:flex-start}.topbar-date{display:none}.bento-panel .analogue-card{grid-template-columns:minmax(0,1fr) 60px}.analogue-card svg{display:none}}
@media(max-width:760px){:root,:root[data-nav-collapsed=true]{--sidebar-width:0px;--header-height:64px}.workspace-nav{display:none}.app-header{height:64px;margin:0;padding:0 16px;gap:8px}.topbar-label,.path-divider,.topbar-date{display:none}.topbar-path{font-size:13px;gap:8px}.topbar-actions{gap:6px}#openNavigation{display:inline-flex;background:none;border:0;width:32px}.glossary-trigger{min-height:40px;width:40px;padding:5px;justify-content:center}.glossary-trigger>span:nth-child(2),.glossary-trigger kbd,.top-export span{display:none}.icon-button,.top-export{width:40px;min-height:40px;justify-content:center}.top-export{padding:8px}.top-export .ui-icon{width:18px;height:18px}main{margin:0;padding:22px 16px 100px;gap:18px;display:block}.workspace-hero{margin-bottom:24px}.hero-eyebrow{font-size:9px;letter-spacing:1.2px}.workspace-hero h1{font-size:29px;letter-spacing:-.9px}.workspace-hero p{font-size:13px;line-height:1.8}.panel{padding:20px 16px;margin-bottom:18px;border-radius:13px}.panel h2{font-size:23px}.section-intro{font-size:13px}.response-workspace{padding:16px}#controlHome{display:none}#responseControls{position:static;display:flex;flex-direction:column;align-items:stretch;border:0;padding:0;gap:24px}.control-group,.shock-control{width:100%}.control-label{margin-bottom:10px;font-size:12px}.control-label label{font-size:12px}.controls label{flex:initial;font-size:12px}.controls select,.controls input[type=date]{font-size:14px;min-height:44px}.segmented button{min-height:40px;font-size:13px}.horizon-control input[type=range]{min-height:38px}.range-marks{font-size:11px}.term-help{width:26px;height:26px;flex-basis:26px;min-height:26px}.mobile-filter-bar{display:block}.mobile-filter-bar button{width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;background:var(--surface-soft);border:1px solid var(--border);border-radius:9px;padding:12px;min-height:46px;text-align:left;font-size:12px}.mobile-filter-bar button>span:last-child{color:var(--accent);font-size:11px;white-space:nowrap}.insight-strip{padding:20px 0;display:block}.insight-strip strong{font-size:19px;line-height:1.6}.insight-strip p{font-size:12px;line-height:1.8;margin-top:7px}.insight-strip .certainty-badge{margin-top:12px;font-size:10px}.reading-eyebrow{font-size:9px}.response-grid{gap:14px}.response-plot{padding:14px 8px 10px;border-radius:9px}.chart-toolbar{gap:5px;margin-bottom:10px;padding:0 4px;flex-wrap:wrap}.chart-toolbar>div>strong{font-size:12px}.chart-toolbar>div>span{font-size:9px}.horizon-presets{gap:1px;border:0;padding:0}.horizon-presets button{font-size:10px;min-height:44px;min-width:31px;padding:5px}.chart-legend{font-size:9px;gap:9px;padding:0 4px}.compare-toggle{margin-left:0;min-height:36px}.compare-toggle input{width:16px;height:16px}.chart-caption{font-size:9px;flex-direction:column;gap:0;padding:0 4px}.interactive-chart svg{min-height:195px}svg text{font-size:16px}.result{display:block;padding:20px}.result .big{font-size:48px;letter-spacing:-2px}.result p,#responseCI{font-size:12px}.result-kicker{font-size:9px}.result-kicker>button{font-size:11px;min-height:28px}.result-footnote{font-size:10px}.result-divider{display:block;margin:14px 0}.interval-meter{font-size:10px}.result .verdict{font-size:13px;margin:12px 0}.workspace-actions{gap:8px;margin:16px 0}.workspace-actions .selection-label{width:100%;order:3;margin:3px 0;font-size:10px}.action-primary,.action-secondary{min-height:44px;font-size:12px}.workspace-actions>#printDashboard{font-size:11px}.chart-caveat{font-size:10px}.chart-caveat .text-button{font-size:10px;min-height:28px}.context-details summary,.research-details summary,.method-details summary,.quick-guide summary,details>summary{min-height:32px;font-size:12px}.guide-examples button{min-height:44px;font-size:12px;width:100%;text-align:left}.bottom-nav{display:grid;grid-template-columns:repeat(3,1fr);position:fixed;left:0;right:0;bottom:0;z-index:var(--z-nav);padding:8px 12px calc(8px + env(safe-area-inset-bottom));background:color-mix(in srgb,var(--sidebar) 97%,transparent);backdrop-filter:blur(14px);border-top:1px solid var(--border)}.bottom-nav button{display:flex;align-items:center;justify-content:center;gap:7px;min-height:44px;background:none;border:0;border-radius:8px;color:var(--muted);font-size:11px}.bottom-nav button[aria-current=page]{background:var(--accent-wash);color:var(--accent-text)}.bottom-nav .ui-icon{width:17px;height:17px;flex-basis:17px}.filter-sheet{margin:auto 0 0;max-width:none;width:100vw;border-radius:18px 18px 0 0;max-height:92dvh;padding:24px}.filter-sheet .controls label{flex:initial}.filter-sheet .control-strip{gap:24px}.filter-sheet .action-primary{min-height:46px}.filter-sheet .dialog-heading>button,.nav-drawer .dialog-heading>button,.shortcut-dialog .dialog-heading>button,.glossary-heading>button{min-width:44px;min-height:44px}.dialog-heading h2{font-size:21px}.glossary-dialog{padding:18px;width:calc(100vw - 16px);max-height:calc(100dvh - 24px);border-radius:13px}.glossary-heading{margin-bottom:14px}.glossary-heading h2{font-size:21px}.glossary-dialog>label{font-size:11px}.glossary-dialog>input{font-size:15px;padding:12px}.glossary-layout{grid-template-columns:1fr;gap:18px;margin-top:15px}.glossary-results{max-height:220px;border:0;border-bottom:1px solid var(--border-soft);padding:0 0 12px;gap:3px}.glossary-results button{font-size:13px;min-height:44px}.glossary-detail h3{font-size:21px}.glossary-detail p{font-size:13px}.glossary-footnote{font-size:10px}.toast{bottom:82px;left:50%;font-size:12px}.history-heading h3{font-size:20px}.history-metrics{grid-template-columns:1fr 1fr}.history-metrics strong{font-size:20px}.history-metrics span{font-size:10px}.history-metrics>div{padding:13px}.history-legend{gap:6px}.history-legend button{min-height:44px;font-size:11px}.historical-oos .controls{gap:12px}.historical-oos .controls label{width:100%}.history-heading{display:block}.history-heading>.research-badge{margin-bottom:10px}.history-badge{display:block;margin:10px 0}.fomc-summary,.status-grid,.explain-grid{grid-template-columns:1fr}.fomc-card{padding:20px}.fomc-card strong{font-size:28px}.evaluation-banner{padding:14px}.evaluation-banner strong{font-size:10px;word-break:break-all}.status-grid strong{font-size:24px}.operations-toolbar{gap:10px}.operations-toolbar a{margin-left:0;min-height:44px;display:flex;align-items:center}.operations-toolbar button{min-height:44px}.research-badge{font-size:10px}.resource-links{flex-direction:column}.resource-links a{font-size:12px;min-height:44px}.analogue-card{grid-template-columns:minmax(0,1fr) 78px 70px}.analogue-card svg{display:block}.analogue-card strong{font-size:12px}.analogue-card small{font-size:10px}.rolling-controls{display:grid;grid-template-columns:1fr 1fr}.rolling-controls label{font-size:10px}.rolling-controls select{font-size:12px}.panel-heading{align-items:flex-start}.panel-heading h2{font-size:22px}.panel-heading .text-button{min-height:44px}.chart-tooltip{padding:10px;width:240px}.chart-tooltip strong{font-size:12px}.tooltip-row small{font-size:10px}footer{font-size:9px;display:block;margin-top:24px}footer>span{display:block}.skip-link{left:16px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}.bento-panel:hover{transform:none}dialog[open]{animation:none}}
@media print{:root{--sidebar-width:0;--bg:#fff;--surface:#fff;--surface-soft:#fff;--text:#111;--muted:#444;--subtle:#555;--border:#bbb;--border-soft:#ddd;--mint:#176f58;--btc:#176f58;--eth:#7154ac;--ci:#176f58;--peach:#985027;--result-bg:#f7f9f4;--result-border:#aaa;color-scheme:light}.workspace-nav,.app-header,.bottom-nav,.workspace-actions,.horizon-presets,.compare-toggle,.mobile-filter-bar,.toast,.chart-tooltip,.skip-link,.quick-guide,dialog,.term-help,.operations-toolbar button{display:none!important}main{display:block;padding:0;margin:0}.panel{margin:0 0 20px;padding:16px;border:1px solid #ccc;box-shadow:none;break-inside:avoid}.panel[hidden]{display:none!important}.workspace-hero{margin:0 0 20px}.response-grid{grid-template-columns:1fr 230px}.result{display:block}.response-plot{padding:10px}.interactive-chart svg{min-height:0}.result .big{font-size:38px}.chart-legend,.chart-caveat{font-size:9px}.control-strip{display:flex;flex-wrap:wrap;position:static}#controlHome{display:block;position:static}.controls select,.controls input{border:0;padding:3px;background:none}.controls{gap:8px}.segment-thumb{display:none}.segmented button[aria-pressed=false]{display:none}.segmented{border:0}.insight-strip{padding:10px 0}.certainty-badge{border-color:#888}.panel.bento-panel{transform:none}footer{font-size:9px}}
/* Reset legacy snapshot text colours and keep the rail free of overflow. */
h1,h2,h3,h4,strong{color:var(--text)}.topbar-path strong{color:var(--text)}.workspace-nav{overflow-x:hidden}
.reading-card:not(.insight-strip){background:var(--surface-soft);border:1px solid var(--border);border-left:2px solid var(--mint);border-radius:10px;margin:20px 0;padding:20px 22px}.reading-card:not(.insight-strip)>strong{font-size:20px;font-weight:500;letter-spacing:-.35px;display:block}.reading-card:not(.insight-strip)>p{font-size:13px;color:var(--muted);margin:7px 0 0}.capture-strip{display:flex;flex-direction:column;gap:8px;padding:20px 22px;border:1px solid var(--border);background:var(--surface-soft);border-radius:10px;margin:20px 0}.capture-strip>span{font-size:12px;color:var(--muted)}.capture-strip>strong{font-size:18px;font-weight:500}.glossary-detail a{display:inline-flex;align-items:center;min-height:36px}
@media(max-width:760px){.icon-button,.top-export,.glossary-trigger{min-width:44px;min-height:44px}.topbar-actions{gap:4px}#openNavigation{width:32px;min-width:32px}.term-help{position:relative;width:44px;height:44px;flex-basis:44px;min-height:44px;border:0}.term-help:before{content:'';position:absolute;inset:11px;border:1px solid var(--border);border-radius:50%;pointer-events:none}.controls label>.term-help{top:-16px;right:0}.control-label{margin-bottom:4px;min-height:44px}.panel-heading>.term-help{margin-top:-8px}.text-button{min-height:44px}.glossary-detail a{min-height:44px}.reading-card:not(.insight-strip){padding:18px}.reading-card:not(.insight-strip)>strong{font-size:18px}.capture-strip{padding:18px}}
@media(max-width:760px){#responseChart text{font-size:14px}#rollingChart text,#quantileChart text,#varChart text{font-size:24px}.horizon-presets button{min-width:44px}.chart-toolbar{row-gap:8px}.chart-toolbar .horizon-presets{margin-left:auto}#openNavigation{min-width:44px;width:44px}}
.glossary-results button[aria-selected=true]{background:var(--accent-wash);color:var(--text);border-color:color-mix(in srgb,var(--accent) 20%,var(--border))}
@media(max-width:760px){.compare-toggle{min-height:44px}}
.result .big{font-size:var(--type-number)}
@media print{.result .big{font-size:38px}}
.range-marks{position:relative;height:12px;display:block}.range-marks>span{position:absolute;top:0;transform:translateX(-50%)}.range-marks>span:nth-child(1){left:0;transform:none}.range-marks>span:nth-child(2){left:20.689655%}.range-marks>span:nth-child(3){left:44.827586%}.range-marks>span:nth-child(4){left:100%;transform:translateX(-100%)}
@media(max-width:760px){.segmented button,.chart-caveat .text-button,.result-kicker>button,#applyRollingRange{min-height:44px}.horizon-control input[type=range]{min-height:44px}button[data-term]:not(.term-help){min-height:44px}}
@media(max-width:760px){.context-details>summary,.research-details>summary,.method-details>summary,.quick-guide>summary,details>summary{min-height:44px}}
.range-marks>span{white-space:nowrap}
```

## dashboard/design.js

```javascript
/* Orbit 3 presentation. Scientific functions, payload values and units stay intact. */
const ORBIT_VIEWS=['transmission','forecast','fomc','advanced','methods','operations'];
const ORBIT_SHOCKS=['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps','monetary'];
function orbitParseRoute(hash){
 const [path,query='']=String(hash||'').replace(/^#/,'').split('?');
 const aliases={responses:'transmission',rolling:'transmission',quantile:'advanced',joint:'advanced',rv:'forecast',pit:'methods',overview:'methods'};
 const p=new URLSearchParams(query),view=ORBIT_VIEWS.includes(path)?path:aliases[path]||'transmission';
 const asset=['btc','eth'].includes(p.get('asset'))?p.get('asset'):'btc',shock=ORBIT_SHOCKS.includes(p.get('shock'))?p.get('shock'):'vix_change',regime=['full','calm','stress'].includes(p.get('regime'))?p.get('regime'):'full';
 const h=Number(p.get('h')||1),horizon=Number.isInteger(h)&&h>=1&&h<=30?String(h):'1';
 return {view,asset,shock,regime,horizon,compare:p.get('compare')!=='0'};
}
function orbitCurveRows(asset,shock,regime){return (shock==='monetary'?DATA.monetary:DATA.daily).filter(r=>r.asset===asset&&r.shock===shock&&r.regime===regime).sort((a,b)=>a.horizon_days-b.horizon_days);}
function orbitLine(points){
 if(!points.length)return '';if(points.length<3)return points.map((p,i)=>(i?'L':'M')+p.map(v=>v.toFixed(2)).join(',')).join(' ');
 // Monotone cubic joins pass through every observed horizon without overshoot.
 const slopes=points.slice(1).map((p,i)=>(p[1]-points[i][1])/(p[0]-points[i][0]||1));
 const tangents=points.map((_,i)=>{if(!i)return slopes[0];if(i===points.length-1)return slopes.at(-1);const a=slopes[i-1],b=slopes[i];return a*b<=0?0:Math.sign(a)*Math.min(Math.abs((a+b)/2),3*Math.min(Math.abs(a),Math.abs(b)));});
 let path='M'+points[0].map(v=>v.toFixed(2)).join(',');
 for(let i=1;i<points.length;i++){const a=points[i-1],b=points[i],dx=(b[0]-a[0])/3;path+=` C${(a[0]+dx).toFixed(2)},${(a[1]+tangents[i-1]*dx).toFixed(2)} ${(b[0]-dx).toFixed(2)},${(b[1]-tangents[i]*dx).toFixed(2)} ${b[0].toFixed(2)},${b[1].toFixed(2)}`;}
 return path;
}
function orbitResponseScene(selected,other=[],analogue=[],size={width:720,height:330}){
 const values=selected.flatMap(r=>[r.lower95,r.upper95]).concat(other.map(r=>r.beta_pct),analogue.map(r=>r.observed_cumulative_pct));
 const low=Math.min(0,...values),high=Math.max(0,...values),pad=(high-low||1)*.11,min=low-pad,max=high+pad;
 const geometry={left:size.width<500?44:62,right:size.width-24,top:30,bottom:size.height-60,...size};
 const X=h=>geometry.left+(h-1)/29*(geometry.right-geometry.left),Y=v=>geometry.bottom-(v-min)/(max-min)*(geometry.bottom-geometry.top);
 const point=r=>[X(r.horizon_days),Y(r.beta_pct)];
 return {min,max,geometry,zero:Y(0),selected:selected.map(point),other:other.map(point),lower:selected.map(r=>[X(r.horizon_days),Y(r.lower95)]),upper:selected.map(r=>[X(r.horizon_days),Y(r.upper95)]),analogue:analogue.map(r=>[X(r.horizon_days),Y(r.observed_cumulative_pct)]),ticks:Array.from({length:5},(_,i)=>{const value=min+(max-min)*i/4;return {value,y:Y(value)};})};
}
function orbitStartStudio(){
 if(typeof window==='undefined'||!document.documentElement)return;
 const $=id=>document.getElementById(id),root=document.documentElement,reduce=matchMedia('(prefers-reduced-motion: reduce)');
 const number=(v,d=3)=>Number(v).toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d});
 const signed=(v,d=3)=>(v>0?'+':'')+number(v,d),percent=v=>signed(v)+'%';
 const date=s=>new Date(s+'T00:00:00Z').toLocaleDateString('vi-VN',{timeZone:'UTC'});
 const titles={transmission:['Từ vĩ mô đến crypto.','Một thay đổi kinh tế. Hai tài sản. 30 ngày phản ứng.'],forecast:['Dự báo phải được kiểm chứng.','Đối chiếu với kết quả đã xảy ra, rồi mới đọc các kiểm định.'],fomc:['Tách hai loại thông tin từ Fed.','Chính sách và triển vọng kinh tế có thể tạo ra những phản ứng khác nhau.'],advanced:['Nhìn sâu hơn vào phản ứng.','Phân vị và VAR trả lời hai câu hỏi khác nhau.'],methods:['Biết nguồn. Hiểu giới hạn.','Phương pháp, thời điểm thông tin khả dụng và phạm vi kết luận.'],operations:['Dữ liệu mới đến đâu?','Theo dõi vận hành và dự báo mới theo kỳ đánh giá đã chốt.']};
 let toastTimer,view=root.dataset.workspace||'transmission',pinned=false,displayedPoint=null,animationFrame=null,liveScene=null,hoverDay=null,activeAnalogue=null,lockedAnalogue=null,rollingRange=null,rollingSelection='',brush=null,lastAdvanced='quantile';
 const chart=$('responseChart');
 for(const id of ['asset','regime','horizon','mobileWorkspace']){$(id).setAttribute('tabindex','-1');$(id).setAttribute('aria-hidden','true');}
 const scientificTable=table;
 const localCell=value=>{if(typeof value==='number')return value.toLocaleString('vi-VN',{maximumSignificantDigits:8});if(typeof value!=='string')return value;if(/^[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(value))return Number(value).toLocaleString('vi-VN',{maximumSignificantDigits:8});if(value.startsWith('[')&&value.endsWith(']'))return value.replace(/[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi,n=>Number(n).toLocaleString('vi-VN',{maximumSignificantDigits:8}));return value;};
 table=function(headers,rows){return scientificTable(headers,rows.map(row=>row.map(localCell)));};
 const analogueIndex=new Map(),analogueSeries=new Map();
 for(const row of DATA.analogues){const prefix=[row.asset,row.shock,row.regime].join('|'),key=prefix+'|'+row.horizon_days,seriesKey=prefix+'|'+row.date_utc;if(!analogueIndex.has(key))analogueIndex.set(key,[]);analogueIndex.get(key).push(row);if(!analogueSeries.has(seriesKey))analogueSeries.set(seriesKey,[]);analogueSeries.get(seriesKey).push(row);}
 for(const series of analogueSeries.values())series.sort((a,b)=>a.horizon_days-b.horizon_days);
 const seriesFor=row=>analogueSeries.get([row.asset,row.shock,row.regime,row.date_utc].join('|'))||[];
 function toast(message){clearTimeout(toastTimer);$('orbitToast').textContent=message;$('orbitToast').hidden=false;toastTimer=setTimeout(()=>$('orbitToast').hidden=true,2800);}
 window.orbitToast=toast;
 function setTheme(theme){root.dataset.theme=theme;$('themeToggle').setAttribute('aria-pressed',String(theme==='light'));$('themeToggle').setAttribute('aria-label',theme==='dark'?'Chuyển sang giao diện sáng':'Chuyển sang giao diện tối');try{localStorage.setItem('orbit-theme',theme);}catch(_){}}
 let savedTheme=null;try{savedTheme=localStorage.getItem('orbit-theme');if(localStorage.getItem('orbit-nav-collapsed')==='true')root.dataset.navCollapsed='true';}catch(_){}
 setTheme(savedTheme==='light'||savedTheme==='dark'?savedTheme:matchMedia('(prefers-color-scheme:light)').matches?'light':'dark');
 window.orbitToggleTheme=()=>{setTheme(root.dataset.theme==='dark'?'light':'dark');};
 $('themeToggle').addEventListener('click',window.orbitToggleTheme);
 function navIndicator(){const b=$('tab-'+view),r=b.getBoundingClientRect(),parent=b.parentElement.getBoundingClientRect();$('navActive').style.transform=`translateY(${r.top-parent.top}px)`;$('navActive').style.height=r.height+'px';}
 function syncUrl(){try{const p=new URLSearchParams({asset:$('asset').value,shock:$('shock').value,regime:$('regime').value,h:$('horizon').value,compare:$('compareAssets').checked?'1':'0'});history.replaceState(null,'','#'+view+'?'+p.toString());}catch(_){}}
 const previousWorkspace=showWorkspace;
 showWorkspace=function(next){
  if(!ORBIT_VIEWS.includes(next))next='transmission';
  const changed=view!==next;view=next;previousWorkspace(next);root.dataset.workspace=next;
  $('designBreadcrumb').textContent=WORKSPACE_NAMES[next];$('designTitle').textContent=titles[next][0];$('designDescription').textContent=titles[next][1];$('designEyebrow').textContent='MACRO × CRYPTO / '+String(ORBIT_VIEWS.indexOf(next)+1).padStart(2,'0');
  for(const key of ORBIT_VIEWS){const b=$('tab-'+key);if(key===next)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
  for(const b of document.querySelectorAll('.bottom-nav [data-goto]')){if(b.dataset.goto===next)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
  $('bottomMore').setAttribute('aria-current',['fomc','advanced','methods','operations'].includes(next)?'page':'false');
  $('topExport').setAttribute('aria-label','Tải CSV · '+WORKSPACE_NAMES[next]);
  if(changed&&!reduce.matches)for(const id of WORKSPACE_GROUPS[next]){const panel=$(id);panel.classList.remove('workspace-enter');requestAnimationFrame(()=>panel.classList.add('workspace-enter'));}
  if(next==='fomc')fomcSummary();if(next==='advanced')varData();
  navIndicator();syncUrl();
 };
 function go(next){showWorkspace(next);window.scrollTo({top:0,behavior:'instant'});for(const id of ['navDrawer','glossaryDialog'])if($(id).open)$(id).close();}
 for(const b of document.querySelectorAll('[data-goto]'))b.addEventListener('click',()=>go(b.dataset.goto));
 $('openNavigation').addEventListener('click',()=>{if(matchMedia('(max-width:760px)').matches)$('navDrawer').showModal();else $('collapseSidebar').click();});
 $('bottomMore').addEventListener('click',()=>$('navDrawer').showModal());
 $('collapseSidebar').addEventListener('click',()=>{const collapsed=root.dataset.navCollapsed!=='true';root.dataset.navCollapsed=String(collapsed);$('collapseSidebar').setAttribute('aria-expanded',String(!collapsed));$('collapseSidebar').setAttribute('aria-label',collapsed?'Mở rộng menu':'Thu gọn menu');try{localStorage.setItem('orbit-nav-collapsed',String(collapsed));}catch(_){}requestAnimationFrame(navIndicator);});
 $('learnMethods').addEventListener('click',()=>go('methods'));
 document.querySelector('.brand').addEventListener('click',e=>{e.preventDefault();go('transmission');});
 document.querySelector('.skip-link').addEventListener('click',e=>{e.preventDefault();$('mainContent').setAttribute('tabindex','-1');$('mainContent').focus();$('mainContent').scrollIntoView({block:'start',behavior:'instant'});});
 for(const b of document.querySelectorAll('[data-close]'))b.addEventListener('click',()=>$(b.dataset.close).close());
 const sheet=$('filterSheet'),controls=$('responseControls');
 $('openFilters').addEventListener('click',()=>{$('sheetControls').append(controls);sheet.showModal();});
 const restoreControls=()=>{$('controlHome').append(controls);};sheet.addEventListener('close',restoreControls);
 $('applyMobileFilters').addEventListener('click',()=>sheet.close());
 window.addEventListener('resize',()=>{if(sheet.open&&innerWidth>760)sheet.close();requestAnimationFrame(()=>{navIndicator();drawResponse(false);});});
 // Segmented controls retain native select IDs for research functions and tests.
 function syncControls(){
  const asset=$('asset').value,regime=$('regime').value,h=$('horizon').value;
  $('assetHelp').dataset.term=asset;
  for(const kind of ['asset','regime']){const value=$(kind).value,buttons=[...document.querySelectorAll('[data-'+kind+']')];buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset[kind]===value)));const thumb=document.querySelector('.'+kind+'-segment .segment-thumb');thumb.style.transform=`translateX(${buttons.findIndex(b=>b.dataset[kind]===value)*100}%)`;}
  $('horizonSlider').value=h;$('horizonOutput').textContent=h;
  for(const b of document.querySelectorAll('[data-horizon]'))b.setAttribute('aria-pressed',String(b.dataset.horizon===h));
  const name=$('shock').selectedOptions[0].textContent;$('mobileFilterLabel').textContent=`${asset.toUpperCase()} · ${name} · ${h} ngày`;
  $('designSampleMeta').textContent=asset.toUpperCase()+' · '+regime;syncUrl();
 }
 for(const key of ['asset','regime'])for(const b of document.querySelectorAll('[data-'+key+']'))b.addEventListener('click',()=>{$(key).value=b.dataset[key];lockedAnalogue=null;renderResponse();});
 function chooseDay(h,pin=false){$('horizon').value=String(Math.max(1,Math.min(30,h)));if(pin)pinned=true;renderResponse();}
 for(const b of document.querySelectorAll('[data-horizon]'))b.addEventListener('click',()=>chooseDay(Number(b.dataset.horizon)));
 let sliderFrame=null;$('horizonSlider').addEventListener('input',()=>{const value=Number($('horizonSlider').value);$('horizonOutput').textContent=String(value);if(sliderFrame)cancelAnimationFrame(sliderFrame);sliderFrame=requestAnimationFrame(()=>{sliderFrame=null;chooseDay(value);});});
 $('compareAssets').addEventListener('change',()=>{drawResponse(false);syncUrl();});
 $('unpinResponse').addEventListener('click',()=>{pinned=false;drawResponse(false);$('pinState').textContent='NGÀY ĐANG CHỌN';$('unpinResponse').hidden=true;});
 function countPoint(value){const element=$('responsePoint'),from=displayedPoint===null?value:displayedPoint;element.dataset.finalValue=percent(value);const token=String(performance.now());element.dataset.animation=token;if(reduce.matches||from===value){displayedPoint=value;element.textContent=percent(value);element.dataset.animating='false';return;}element.dataset.animating='true';element.textContent=percent(from);const start=performance.now();function frame(now){if(element.dataset.animation!==token)return;const t=Math.min(1,(now-start)/320),e=1-(1-t)**3;displayedPoint=from+(value-from)*e;element.textContent=percent(displayedPoint);if(t<1)requestAnimationFrame(frame);else element.dataset.animating='false';}requestAnimationFrame(frame);}
 function responseDetail(){
  const rows=responseRows(),row=rows.find(r=>r.horizon_days===Number($('horizon').value));if(!row)return;
  const crosses=row.lower95<=0&&row.upper95>=0;
  $('responseMetricLabel').textContent=`${row.asset.toUpperCase()} · sau ${row.horizon_days} ngày`;countPoint(row.beta_pct);
  $('responseCI').textContent=`CI 95%: ${number(row.lower95)}% đến ${number(row.upper95)}%`;
  $('responseVerdict').textContent=crosses?'Chưa rõ chiều phản ứng: khoảng tin cậy chứa 0.':'Khoảng tin cậy nằm về một phía của 0. Cần đọc cùng BH q.';
  $('responseSample').textContent=number(row.nobs,0)+' quan sát'+(row.n_state===null?'':' · nhóm '+number(row.n_state,0));
  $('responseInference').textContent=row.qvalue_bh===null?'CI chế độ có tính covariance.':'BH q = '+number(row.qvalue_bh);
  $('certaintyBadge').textContent=crosses?'Chưa rõ chiều phản ứng':'CI không chứa 0';$('certaintyBadge').dataset.state=crosses?'unclear':'clear';
  $('pinState').textContent=pinned?'ĐÃ GHIM NGÀY '+row.horizon_days:'NGÀY ĐANG CHỌN';$('unpinResponse').hidden=!pinned;
  $('designSample').textContent=number(row.nobs,0)+' quan sát';
  const lo=Math.min(0,row.lower95),hi=Math.max(0,row.upper95),pad=(hi-lo||1)*.15,min=lo-pad,max=hi+pad,x=v=>(v-min)/(max-min)*100;
  $('intervalBand').style.left=x(row.lower95)+'%';$('intervalBand').style.width=(x(row.upper95)-x(row.lower95))+'%';$('intervalPoint').style.left=x(row.beta_pct)+'%';$('intervalZero').style.left=x(0)+'%';
  $('responseDataTable').innerHTML=table(['Ngày','Tài sản','Ước lượng (%)','CI thấp','CI cao','n','BH q'],rows.map(r=>[r.horizon_days,r.asset.toUpperCase(),number(r.beta_pct),number(r.lower95),number(r.upper95),number(r.nobs,0),r.qvalue_bh===null?'—':number(r.qvalue_bh)]));
 }
 function currentAnalogueRows(){return activeAnalogue?seriesFor(activeAnalogue):[];}
 function drawResponse(animate=true){
  if(animationFrame)cancelAnimationFrame(animationFrame);
  const selected=responseRows(),asset=$('asset').value,other=$('compareAssets').checked?orbitCurveRows(asset==='btc'?'eth':'btc',$('shock').value,$('regime').value):[],actual=currentAnalogueRows(),mobile=matchMedia('(max-width:760px)').matches,next=orbitResponseScene(selected,other,actual,mobile?{width:360,height:300}:{width:720,height:330}),g=next.geometry;
  chart.setAttribute('viewBox',`0 0 ${g.width} ${g.height}`);
  const otherClass=asset==='btc'?'eth':'btc';
  chart.innerHTML=`<title>Phản ứng ${asset.toUpperCase()} từ 1 đến 30 ngày</title><desc>Ước lượng lợi suất log cộng dồn, CI pointwise 95%. Mũi tên chọn ngày; Enter để ghim. Bảng dữ liệu nằm ngay dưới biểu đồ.</desc><defs><linearGradient id="responseBandGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--${asset})" stop-opacity=".18"/><stop offset="1" stop-color="var(--${asset})" stop-opacity=".025"/></linearGradient><clipPath id="responseClip"><rect x="${g.left-1}" y="${g.top}" width="${g.right-g.left+2}" height="${g.bottom-g.top+4}"/></clipPath></defs>`+
   next.ticks.map(t=>`<line class="plot-grid" x1="${g.left}" x2="${g.right}" y1="${t.y}" y2="${t.y}"/><text x="${g.left-12}" y="${t.y+4}" text-anchor="end">${number(t.value,2)}</text>`).join('')+
   `<line class="plot-zero" x1="${g.left}" x2="${g.right}" y1="${next.zero}" y2="${next.zero}"/>`+[1,7,14,21,30].map(h=>`<text x="${g.left+(h-1)/29*(g.right-g.left)}" y="${g.height-30}" text-anchor="middle">${h}</text>`).join('')+
   `<g clip-path="url(#responseClip)"><path id="responseBand" fill="url(#responseBandGradient)"/><path id="primaryCurve" class="curve-line curve-${asset}"/><path id="comparisonCurve" class="curve-line curve-${otherClass}"/><path id="analogueCurve" class="curve-analogue"/><line id="responsePin" class="chart-pin" y1="${g.top}" y2="${g.bottom+4}"/><line id="responseCrosshair" class="crosshair" y1="${g.top}" y2="${g.bottom+4}" hidden/><${asset==='btc'?'circle':'rect'} id="responseSelectedPoint" class="point-${asset}" ${asset==='btc'?'r="4.5"':'width="9" height="9"'}/>${other.length?`<${otherClass==='btc'?'circle':'rect'} id="responseOtherPoint" class="point-${otherClass}" ${otherClass==='btc'?'r="3.5"':'width="7" height="7"'}/>`:''}</g>`;
  const primary=$('primaryCurve'),comparison=$('comparisonCurve'),band=$('responseBand'),analogue=$('analogueCurve'),point=$('responseSelectedPoint'),otherPoint=$('responseOtherPoint'),h=Number($('horizon').value),i=h-1;
  $('responsePin').setAttribute('x1',next.selected[i][0]);$('responsePin').setAttribute('x2',next.selected[i][0]);$('responsePin').style.opacity=pinned?'1':'.45';
  function paint(scene){primary.setAttribute('d',orbitLine(scene.selected));comparison.setAttribute('d',orbitLine(scene.other));band.setAttribute('d',orbitLine(scene.upper)+' '+orbitLine(scene.lower.slice().reverse()).replace(/^M/,'L')+' Z');analogue.setAttribute('d',orbitLine(scene.analogue));if(asset==='btc'){point.setAttribute('cx',scene.selected[i][0]);point.setAttribute('cy',scene.selected[i][1]);}else{point.setAttribute('x',scene.selected[i][0]-4.5);point.setAttribute('y',scene.selected[i][1]-4.5);}if(otherPoint&&scene.other[i]){if(otherClass==='btc'){otherPoint.setAttribute('cx',scene.other[i][0]);otherPoint.setAttribute('cy',scene.other[i][1]);}else{otherPoint.setAttribute('x',scene.other[i][0]-3.5);otherPoint.setAttribute('y',scene.other[i][1]-3.5);}}liveScene=scene;}
  const previous=liveScene;
  if(animate&&!reduce.matches&&previous&&previous.selected.length===next.selected.length){const start=performance.now();function frame(now){const t=Math.min(1,(now-start)/400),ease=1-(1-t)**3,scene={...next};for(const key of ['selected','other','lower','upper','analogue'])scene[key]=next[key].map((p,j)=>p.map((v,k)=>previous[key]?.[j]?previous[key][j][k]+(v-previous[key][j][k])*ease:v));paint(scene);if(t<1)animationFrame=requestAnimationFrame(frame);else animationFrame=null;}animationFrame=requestAnimationFrame(frame);}else paint(next);
  chart.setAttribute('aria-label',`${asset.toUpperCase()}, ${$('shock').selectedOptions[0].textContent}, ngày ${h}: ${percent(selected[i].beta_pct)}. CI ${number(selected[i].lower95)} đến ${number(selected[i].upper95)}%. Dùng mũi tên chọn ngày; Enter ghim.`);
  $('analogueOverlayLabel').hidden=!activeAnalogue;$('analogueOverlayLabel').textContent=activeAnalogue?'Nét chấm: thực tế '+date(activeAnalogue.date_utc):'';
  document.querySelector('.btc-key').hidden=asset!=='btc'&&!other.length;document.querySelector('.eth-key').hidden=asset!=='eth'&&!other.length;
  if(hoverDay)showTooltip(hoverDay);
 }
 function showTooltip(h){
  if(!liveScene)return;hoverDay=h;
  const asset=$('asset').value,rows=responseRows(),r=rows[h-1],other=orbitCurveRows(asset==='btc'?'eth':'btc',$('shock').value,$('regime').value)[h-1];
  const values=$('compareAssets').checked?[r,other]:[r];
  $('responseTooltip').innerHTML=`<strong>Sau ${h} ngày ${pinned&&h===Number($('horizon').value)?'· đã ghim':''}</strong>`+values.map(v=>`<div class="tooltip-row ${v.asset}"><b>${v.asset.toUpperCase()}</b><span>${percent(v.beta_pct)}</span><small>CI ${number(v.lower95)}% → ${number(v.upper95)}%</small></div>`).join('');
  const line=$('responseCrosshair'),x=liveScene.geometry.left+(h-1)/29*(liveScene.geometry.right-liveScene.geometry.left);line.hidden=false;line.removeAttribute('hidden');line.setAttribute('x1',x);line.setAttribute('x2',x);
  const box=chart.getBoundingClientRect(),left=Math.min(Math.max(8,x/liveScene.geometry.width*box.width-130),Math.max(8,box.width-268));$('responseTooltip').style.left=left+'px';$('responseTooltip').style.top='8px';$('responseTooltip').hidden=false;
 }
 let pointerFrame=null;chart.addEventListener('pointermove',e=>{const box=chart.getBoundingClientRect(),g=liveScene.geometry,x=(e.clientX-box.left)/box.width*g.width;if(x<g.left||x>g.right)return;const h=Math.max(1,Math.min(30,Math.round(1+(x-g.left)/(g.right-g.left)*29)));if(pointerFrame)cancelAnimationFrame(pointerFrame);pointerFrame=requestAnimationFrame(()=>showTooltip(h));});
 chart.addEventListener('pointerleave',()=>{if(pointerFrame)cancelAnimationFrame(pointerFrame);hoverDay=null;$('responseTooltip').hidden=true;const line=$('responseCrosshair');if(line)line.setAttribute('hidden','');});
 chart.addEventListener('click',e=>{const box=chart.getBoundingClientRect(),g=liveScene.geometry,x=(e.clientX-box.left)/box.width*g.width;if(x>=g.left&&x<=g.right){chooseDay(Math.round(1+(x-g.left)/(g.right-g.left)*29),true);toast('Đã ghim ngày '+$('horizon').value);}});
 chart.addEventListener('keydown',e=>{const h=Number($('horizon').value);if(['ArrowLeft','ArrowRight','Home','End','Enter','Escape'].includes(e.key))e.preventDefault();if(e.key==='ArrowLeft')chooseDay(h-1,true);if(e.key==='ArrowRight')chooseDay(h+1,true);if(e.key==='Home')chooseDay(1,true);if(e.key==='End')chooseDay(30,true);if(e.key==='Enter'){pinned=!pinned;responseDetail();drawResponse(false);}if(e.key==='Escape'){$('unpinResponse').click();$('responseTooltip').hidden=true;}if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key))showTooltip(Number($('horizon').value));});
 function analogues(){
  const h=Number($('horizon').value),rows=analogueIndex.get([$('asset').value,$('shock').value,$('regime').value,h].join('|'))||[],container=$('analogueCards');container.replaceChildren();
  activeAnalogue=lockedAnalogue&&rows.find(r=>r.date_utc===lockedAnalogue)||null;
  for(const row of rows){const b=document.createElement('button');b.type='button';b.className='analogue-card';b.dataset.date=row.date_utc;b.setAttribute('aria-pressed',String(lockedAnalogue===row.date_utc));
   const series=seriesFor(row),lo=Math.min(0,...series.map(r=>r.observed_cumulative_pct)),hi=Math.max(0,...series.map(r=>r.observed_cumulative_pct)),y=v=>27-(v-lo)/(hi-lo||1)*25,points=series.map(r=>`${(r.horizon_days-1)/29*78},${y(r.observed_cumulative_pct)}`).join(' ');
   b.innerHTML=`<span><strong>${date(row.date_utc)}</strong><small>${number(row.shock_observed,2)} · ${h} ngày quan sát</small></span><svg viewBox="0 0 80 30" aria-hidden="true"><line x1="0" x2="80" y1="${y(0)}" y2="${y(0)}"/><polyline points="${points}"/></svg><span>${percent(row.observed_cumulative_pct)}</span>`;
   const preview=()=>{activeAnalogue=row;drawResponse(false);highlightRolling(row);};const leave=()=>{activeAnalogue=lockedAnalogue?rows.find(r=>r.date_utc===lockedAnalogue)||null:null;drawResponse(false);highlightRolling(activeAnalogue);};
   b.addEventListener('pointerenter',preview);b.addEventListener('pointerleave',leave);b.addEventListener('focus',preview);b.addEventListener('blur',leave);b.addEventListener('click',()=>{lockedAnalogue=lockedAnalogue===row.date_utc?null:row.date_utc;activeAnalogue=lockedAnalogue?row:null;for(const card of container.children)card.setAttribute('aria-pressed',String(card.dataset.date===lockedAnalogue));drawResponse(false);highlightRolling(activeAnalogue);});container.append(b);
  }
 }
 const beforeResponse=renderResponse;renderResponse=function(){const started=performance.now();beforeResponse();syncControls();responseDetail();analogues();drawResponse();root.dataset.responseRenderMs=(performance.now()-started).toFixed(1);};
 $('resetResponse').removeEventListener('click',resetResponse);$('resetResponse').addEventListener('click',()=>{pinned=false;lockedAnalogue=null;activeAnalogue=null;resetResponse();toast('Đã trở về BTC · VIX +5 · 1 ngày.');});
 $('exportResponse').addEventListener('click',()=>toast('Đã chuẩn bị CSV gồm 30 thời hạn và CI.'));
 // Rolling brushing uses the actual rolling dates, never the response-day axis.
 let rollingRows=[],rollingBounds=null;
 function allRolling(){return DATA.rolling.filter(r=>r.asset===$('rollAsset').value&&r.shock===$('rollShock').value).sort((a,b)=>a.date_utc.localeCompare(b.date_utc));}
 const previousRolling=renderRolling;
 renderRolling=function(){
  const selection=$('rollAsset').value+'|'+$('rollShock').value;if(selection!==rollingSelection){rollingRange=null;rollingSelection=selection;}
  const all=allRolling();rollingRows=all.filter(r=>!rollingRange||(r.date_utc>=rollingRange[0]&&r.date_utc<=rollingRange[1]));if(rollingRows.length<2){rollingRows=all;rollingRange=null;}
  $('rollingStart').min=$('rollingEnd').min=all[0].date_utc;$('rollingStart').max=$('rollingEnd').max=all.at(-1).date_utc;
  $('rollingStart').value=rollingRows[0].date_utc;$('rollingEnd').value=rollingRows.at(-1).date_utc;
  const rows=rollingRows.map(r=>({x:Date.parse(r.date_utc+'T00:00:00Z'),y:r.beta_pct,lo:r.beta_pct-1.96*r.se,hi:r.beta_pct+1.96*r.se}));
  $('rollingChart').innerHTML=chartLegacy(rows,rows.length-1,'Ngày kết thúc cửa sổ · UTC')+'<g id="rollingHighlight"></g><rect id="rollingBrush" class="brush-region" y="35" height="235" width="0"/>';
  const first=rows[0].x,last=rows.at(-1).x;rollingBounds={first,last};
  $('rollingRangeLabel').textContent=`${date(rollingRows[0].date_utc)} — ${date(rollingRows.at(-1).date_utc)} · kéo để zoom, nhấp đúp đặt lại`+($('shock').value==='monetary'?' · Rolling daily '+$('rollShock').selectedOptions[0].textContent+', tách riêng STMT.':'');
  $('rollingDataTable').innerHTML=table(['Ngày UTC','Beta (%)','CI thấp','CI cao'],rollingRows.map(r=>[date(r.date_utc),number(r.beta_pct),number(r.beta_pct-1.96*r.se),number(r.beta_pct+1.96*r.se)]));highlightRolling(activeAnalogue);
 };
 const chartLegacy=chartLegacyAlias;
 function highlightRolling(row){const g=$('rollingHighlight');if(!g||!rollingBounds)return;g.replaceChildren();if(!row)return;const x=d=>70+(Date.parse(d+'T00:00:00Z')-rollingBounds.first)/(rollingBounds.last-rollingBounds.first)*615,start=Math.max(70,x(row.date_utc)),end=Math.min(685,x(row.end_date_utc));if(end<70||start>685)return;g.innerHTML=`<rect x="${start}" y="35" width="${Math.max(3,end-start)}" height="235" class="selected-date"><title>Sự kiện ${row.date_utc}</title></rect>`;}
 for(const id of ['rollAsset','rollShock']){$(id).removeEventListener('change',previousRolling);$(id).addEventListener('change',renderRolling);}
 const roll=$('rollingChart'),rollX=e=>Math.max(70,Math.min(685,(e.clientX-roll.getBoundingClientRect().left)/roll.getBoundingClientRect().width*720));
 roll.addEventListener('pointerdown',e=>{if(e.button!==0)return;brush={start:rollX(e),id:e.pointerId};roll.setPointerCapture(e.pointerId);});
 roll.addEventListener('pointermove',e=>{if(!brush)return;const x=rollX(e);$('rollingBrush').setAttribute('x',Math.min(x,brush.start));$('rollingBrush').setAttribute('width',Math.abs(x-brush.start));});
 function endBrush(e){if(!brush)return;const end=rollX(e),start=brush.start;brush=null;if(Math.abs(end-start)<8)return;const toDate=x=>new Date(rollingBounds.first+(x-70)/615*(rollingBounds.last-rollingBounds.first)).toISOString().slice(0,10);rollingRange=[toDate(Math.min(start,end)),toDate(Math.max(start,end))];renderRolling();toast('Đã phóng to khoảng thời gian. Nhấp đúp để xem toàn kỳ.');}
 roll.addEventListener('pointerup',endBrush);roll.addEventListener('pointercancel',()=>{brush=null;const b=$('rollingBrush');if(b)b.setAttribute('width','0');});
 function resetRolling(){rollingRange=null;renderRolling();}roll.addEventListener('dblclick',resetRolling);$('resetRolling').addEventListener('click',resetRolling);roll.addEventListener('keydown',e=>{if(e.key==='Escape'||e.key==='Home'){e.preventDefault();resetRolling();}});
 $('applyRollingRange').addEventListener('click',()=>{const a=$('rollingStart').value,b=$('rollingEnd').value;if(!a||!b||a>b){toast('Chọn ngày bắt đầu trước ngày kết thúc.');return;}if(allRolling().filter(r=>r.date_utc>=a&&r.date_utc<=b).length<2){toast('Khoảng này cần ít nhất hai ước lượng rolling.');return;}rollingRange=[a,b];renderRolling();});
 // Forecast layers are display-only; losses and CSV always use the complete data.
 const visibleCurves=[true,true,true,true];
 function replayEnhance(){if(!HISTORICAL.series)return;const rows=historicalRows();for(const id of ['historyBaseLoss','historyAddedLoss','historyBenchmarkDelta'])$(id).textContent=localCell($(id).textContent);$('replayCompact').textContent=rows.length?`${rows.length.toLocaleString('vi-VN')} ngày · ${date(rows[0].date)} — ${date(rows.at(-1).date)} · dữ liệu lịch sử`: 'Không có ngày phù hợp. Chọn lại khoảng ngày.';const lines=$('historyPredictionChart').querySelectorAll('polyline');lines.forEach((line,i)=>{line.dataset.curve=String(i);line.style.display=visibleCurves[i]?'':'none';});
  const loss=$('historyLossChart').querySelector('svg'),line=loss?.querySelector('polyline');if(line){const pts=line.getAttribute('points').trim().split(/\s+/).map(p=>p.split(',').map(Number)),zero=loss.querySelector('line[stroke="#8ca5b3"]'),y=zero?Number(zero.getAttribute('y1')):null;if(pts.length&&Number.isFinite(y)&&!loss.querySelector('.loss-area')){const ns='http://www.w3.org/2000/svg',area=document.createElementNS(ns,'path');area.setAttribute('d',`M${pts[0][0]},${y} `+pts.map(p=>'L'+p.join(',')).join(' ')+` L${pts.at(-1)[0]},${y} Z`);area.setAttribute('fill','var(--mint)');area.setAttribute('opacity','.10');area.setAttribute('class','loss-area');loss.insertBefore(area,line);}}
 }
 window.orbitEnhanceReplay=replayEnhance;
 for(const b of $('replayLegend').querySelectorAll('button'))b.addEventListener('click',()=>{const i=Number(b.dataset.curve);if(visibleCurves[i]&&visibleCurves.filter(Boolean).length===1){toast('Giữ ít nhất một đường để đối chiếu.');return;}visibleCurves[i]=!visibleCurves[i];b.setAttribute('aria-pressed',String(visibleCurves[i]));replayEnhance();});
 const observer=new MutationObserver(()=>replayEnhance());observer.observe($('historyPointTable'),{childList:true});
 function fomcSummary(){const rows=LATEST.fomc.filter(r=>r.asset===$('eAsset').value&&r.outcome===$('eOutcome').value);$('fomcSummary').innerHTML=rows.map(r=>`<article class="fomc-card"><span>${r.shock==='policy'?'Thành phần chính sách':'Thông tin kinh tế'} · ${r.asset}</span><strong>${r.lower_per10bps===null?(r.unbounded?'−∞':'—'):number(r.lower_per10bps)} → ${r.upper_per10bps===null?(r.unbounded?'+∞':'—'):number(r.upper_per10bps)}%</strong><p>${r.unbounded?'Miền ước lượng không bị chặn phía trên.':r.upper_per10bps<0?'Ước lượng âm trên toàn miền xoay.':'Đọc cả miền ước lượng trước khi kết luận chiều tác động.'}</p><small>Miền point estimates / +10 bps component PC1 · không phải CI</small></article>`).join('');}
 function modelHelp(){const help=$('forecastModel').closest('label').querySelector('[data-term]');if(help)help.dataset.term=$('forecastModel').value==='gradient_boosting'?'boosting':'elastic';}
 $('forecastModel').addEventListener('change',modelHelp);modelHelp();
 const oldFomc=renderFOMC;renderFOMC=function(){oldFomc();fomcSummary();};for(const id of ['eAsset','eOutcome']){$(id).removeEventListener('change',oldFomc);$(id).addEventListener('change',renderFOMC);}
 function varData(){const yieldName=$('varYield').value,shock=$('varShock').value==='yield'?yieldName+'_change_bps':$('varShock').value;const rows=DATA.var_irf.filter(r=>r.asset===$('varAsset').value&&r.yield_variable===yieldName&&r.regime===$('varRegime').value&&r.ordering===$('varOrder').value&&r.shock===shock);$('varDataTable').innerHTML=table(['Phiên','Phản ứng (%)','CI thấp','CI cao'],rows.map(r=>[r.horizon_sessions,number(r.response_pct),number(r.lower95),number(r.upper95)]));}
 for(const id of ['varAsset','varYield','varShock','varOrder','varRegime'])$(id).addEventListener('change',()=>{lastAdvanced='var';varData();});for(const id of ['qAsset','qRegime','qShock'])$(id).addEventListener('change',()=>lastAdvanced='quantile');
 function csvDownload(rows,name){if(!rows.length){toast('Chưa có dữ liệu phù hợp để tải.');return;}const columns=Object.keys(rows[0]),q=v=>'"'+String(v??'').replace(/"/g,'""')+'"',csv='\ufeff'+[columns,...rows.map(r=>columns.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n'),url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Đã chuẩn bị '+name);}
 function exportCurrent(){if(view==='transmission'){$('exportResponse').click();return;}if(view==='forecast'){if(!HISTORICAL.series){toast('Dữ liệu phát lại đang được chuẩn bị. Hãy thử lại sau.');return;}if($('exportHistoricalOos').disabled){toast('Chọn khoảng có dữ liệu trước khi tải CSV.');return;}$('exportHistoricalOos').click();toast('Đã chuẩn bị CSV dự báo và timing.');return;}if(view==='fomc'){csvDownload(LATEST.fomc.filter(r=>r.asset===$('eAsset').value&&r.outcome===$('eOutcome').value),'fomc_rotation_ranges.csv');return;}if(view==='methods'){csvDownload(LATEST.pit,'feature_sources.csv');return;}if(view==='operations'){csvDownload([{research_cutoff:(window.orbitStatus||ORBIT_STATUS).research_cutoff,last_success_utc:(window.orbitStatus||ORBIT_STATUS).worker?.last_success_utc,performance:(window.orbitStatus||ORBIT_STATUS).prospective?.performance,prediction_rows:(window.orbitStatus||ORBIT_STATUS).prospective?.prediction_rows,fixed_end:(window.orbitStatus||ORBIT_STATUS).prospective?.fixed_end}],'operations_snapshot.csv');return;}if(lastAdvanced==='quantile')csvDownload(DATA.quantile.filter(r=>r.asset===$('qAsset').value&&r.regime===$('qRegime').value&&r.shock===$('qShock').value),'quantile_effects.csv');else{const shock=$('varShock').value==='yield'?$('varYield').value+'_change_bps':$('varShock').value;csvDownload(DATA.var_irf.filter(r=>r.asset===$('varAsset').value&&r.yield_variable===$('varYield').value&&r.regime===$('varRegime').value&&r.ordering===$('varOrder').value&&r.shock===shock),'var_irf.csv');}}
 window.orbitExportCurrent=exportCurrent;$('topExport').addEventListener('click',exportCurrent);$('printDashboard').addEventListener('click',()=>window.print());
 document.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey||e.target.closest('input,select,textarea,[contenteditable=true]')||document.querySelector('dialog[open]'))return;if(/^[1-6]$/.test(e.key)){e.preventDefault();go(ORBIT_VIEWS[Number(e.key)-1]);}if(e.key==='['||e.key===']'){e.preventDefault();chooseDay(Number($('horizon').value)+(e.key===']'?1:-1));}if(e.key.toLowerCase()==='t'){e.preventDefault();window.orbitToggleTheme();}if(e.key==='?'){e.preventDefault();$('shortcutDialog').showModal();}});
 function applyRoute(){const route=orbitParseRoute(location.hash);for(const id of ['asset','shock','regime','horizon'])$(id).value=route[id];$('compareAssets').checked=route.compare;showWorkspace(route.view);renderResponse();}
 window.addEventListener('hashchange',applyRoute);
 const chartTitles=['quantileChart','varChart'];for(const id of chartTitles){$(id).setAttribute('tabindex','0');$(id).setAttribute('aria-describedby',id==='quantileChart'?'quantileTable':'varDataTable');}
 applyRoute();renderRolling();if(HISTORICAL.series)replayEnhance();
 // One restrained entrance stroke. No repeated chart animation or forced layout.
 if(!reduce.matches){const path=$('primaryCurve');if(path&&typeof path.getTotalLength==='function'){const length=path.getTotalLength();path.style.strokeDasharray=String(length);const animation=path.animate([{strokeDashoffset:length},{strokeDashoffset:0}],{duration:480,easing:'cubic-bezier(.2,.8,.2,1)'});animation.onfinish=()=>path.style.removeProperty('stroke-dasharray');}}
 root.dataset.orbitStudioReady='true';
}
// Retain the original generic plotter for rolling, quantile and VAR validation.
const chartLegacyAlias=chart;
```

## dashboard/experience.css

```css
/* Runtime states shared by Orbit 3. Never hide scientific caveats. */
.boot-screen{position:fixed;inset:0;z-index:90;display:grid;place-items:center;background:var(--bg);color:var(--text)}.boot-screen>div{text-align:center}.boot-screen strong{font-size:44px;letter-spacing:-2px}.boot-screen strong>span{color:var(--accent)}.boot-screen p{font-size:15px;margin:20px 0 5px;color:var(--muted)}.boot-screen small{font-size:12px;color:var(--subtle)}.app-feedback{grid-column:1/-1;border:1px solid var(--warning);padding:16px;background:var(--surface);border-radius:10px;color:var(--warning);font-size:13px}.loading-card,.error-card{border:1px solid var(--border);padding:20px;border-radius:10px;background:var(--surface-soft);margin:20px 0;font-size:13px;color:var(--muted)}.error-card{border-color:var(--warning)}.error-card strong{color:var(--text);font-size:15px}.error-card p{font-size:13px}.error-card button{border:1px solid var(--border);background:var(--accent);color:var(--bg);border-radius:7px;padding:10px 16px;font-size:13px;min-height:44px}.skeleton-line{display:block;height:13px;background:var(--border);border-radius:4px;width:70%;margin:0 0 14px;position:relative;overflow:hidden}.skeleton-line:nth-child(2){width:43%;margin-bottom:20px}.skeleton-line:after{content:'';position:absolute;inset:0;transform:translateX(-100%);background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--muted) 12%,transparent),transparent);animation:skeleton-pass 1400ms ease 3}@keyframes skeleton-pass{to{transform:translateX(100%)}}.workspace-enter{animation:workspace-enter 200ms var(--ease)}@keyframes workspace-enter{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}@media(prefers-reduced-motion:reduce){.skeleton-line:after,.workspace-enter{animation:none}}@media print{.boot-screen,.loading-card,.error-card,.app-feedback{display:none}}
```

## dashboard/experience.js

```javascript
/* User education and status reading; never changes scientific data or gates. */
const ORBIT_TERMS = [
 ['oos','OOS · Kiểm tra ngoài mẫu','out of sample oss ngoài mẫu dự báo tương lai','Kiểm tra dự báo trên dữ liệu không dùng để huấn luyện mô hình. Với nhánh theo dõi thật, dự báo phải được ghi trước khi kết quả xảy ra.','Một mô hình được chốt hôm nay, ghi dự báo cho ngày mai, rồi đợi giá thực tế để đối chiếu.'],
 ['pseudo-oos','OOS lịch sử · Historical pseudo-OOS','historical backtest replay phát lại kiểm thử quá khứ','Mô phỏng các lần dự báo trong quá khứ, mỗi lần chỉ huấn luyện bằng giai đoạn trước đó. Khi dữ liệu lịch sử đã được xem trong quá trình phát triển, kết quả này chưa phải bằng chứng độc lập về tương lai.','Mô hình dùng dữ liệu trước 2024 để kiểm tra dự báo trong năm 2024; dashboard phát lại các dự báo đã lưu.'],
 ['shock','Cú sốc · Shock','shock cú shock cú sốc biến động vĩ mô thay đổi kinh tế','Một thay đổi kinh tế có quy mô xác định để xem crypto thường phản ứng thế nào trong mẫu nghiên cứu. Không phải mọi shock trong dashboard đều là tác động nhân quả đã được nhận dạng.','Chọn VIX +5 điểm: đọc phản ứng ước lượng khi thước đo lo ngại của thị trường tăng 5 điểm.'],
 ['vix','VIX · Chỉ số biến động kỳ vọng','vix sợ hãi lo ngại chứng khoán','Thước đo biến động kỳ vọng của chỉ số S&P 500 được suy ra từ giá quyền chọn. VIX cao thường gắn với mức bất định thị trường cao hơn.','VIX từ 15 lên 20 là tăng 5 điểm, khác với tăng 5%.'],
 ['fomc','FOMC · Ủy ban chính sách tiền tệ Mỹ','fomc họp fed tiền tệ','Ủy ban của Fed đưa ra các quyết định chính sách tiền tệ Mỹ. Thông báo và họp báo có thể mang cả tin về chính sách lẫn triển vọng kinh tế.','Một tin lãi suất đi kèm đánh giá kinh tế có thể chứa hai loại thông tin khác nhau.'],
 ['fed','Fed · Ngân hàng trung ương Mỹ','fed federal reserve dự trữ liên bang','Hệ thống Dự trữ Liên bang Mỹ, thực hiện chính sách tiền tệ và nhiều chức năng ngân hàng trung ương.','Trong mục FOMC, bạn xem phản ứng giá quanh thông tin chính sách từ Fed.'],
 ['btc','BTC · Bitcoin','btc bitcoin tiền mã hóa','Ký hiệu của Bitcoin. Trong nhánh nghiên cứu daily, giá được đo bằng USD từ nguồn tổng hợp; không đồng nhất với giá BTC/USDT tại một sàn.','Chọn Bitcoin để các kết quả bên dưới dùng mẫu của BTC.'],
 ['eth','ETH · Ethereum','eth ethereum ether','Ký hiệu của Ether, tài sản gốc của mạng Ethereum. Mẫu lịch sử có thể khác Bitcoin do thời điểm bắt đầu dữ liệu.','Đổi BTC sang ETH để so sánh phản ứng của hai tài sản với cùng một thay đổi kinh tế.'],
 ['horizon','Thời hạn phản ứng · Horizon','horizon thời hạn bao lâu số ngày ngày lịch phiên','Số ngày hoặc số phiên theo dõi sau một thay đổi. Local Projections dùng ngày lịch; VAR trong dashboard dùng phiên đủ điều kiện của thị trường Mỹ.','7 ngày lịch bao gồm cuối tuần; 7 phiên không có cùng độ dài thời gian.'],
 ['regime','Trạng thái thị trường · Regime','regime calm stress full bình thường căng thẳng toàn mẫu','Cách phân loại quan sát để so sánh phản ứng trong các trạng thái như bình thường hoặc căng thẳng, theo quy tắc nghiên cứu đã định.','Mẫu căng thẳng ít quan sát hơn có thể cho khoảng tin cậy rộng hơn.'],
 ['ci','Khoảng tin cậy 95% · CI','ci confidence interval khoảng tin cậy dải màu sai số độ chắc chắn','Khoảng ước lượng thể hiện mức bất định theo phương pháp thống kê đã dùng. Nếu khoảng chứa 0, riêng khoảng này chưa cho thấy phản ứng khác 0 rõ ràng ở mức tương ứng.','Ước lượng −0,2% nhưng khoảng từ −1,2% đến +0,8%: cả tăng và giảm vẫn nằm trong khoảng. Không đọc −0,2% như dự báo chắc chắn.'],
 ['bps','Điểm cơ bản · bps','bps basis point điểm cơ bản lãi suất','Đơn vị đo chênh lệch lãi suất: 100 bps bằng 1 điểm phần trăm; 10 bps bằng 0,1 điểm phần trăm.','Lợi suất từ 4,0% lên 4,1% là tăng 10 bps.'],
 ['return','Lợi suất · Return','return lợi suất tăng giảm giá lợi nhuận log return','Mức thay đổi của giá theo thời gian. Nghiên cứu dùng log return; phần đường phản ứng hiển thị theo phần trăm và giữ đúng cách tính đã chốt.','Số âm cho biết phản ứng giảm trong mẫu; không tự bao gồm phí giao dịch hoặc cổ tức.'],
 ['lp','Local Projections · Ước lượng theo từng thời hạn','lp local projections phản ứng ước lượng','Phương pháp ước lượng phản ứng tại từng thời hạn riêng. Đường 1–30 ngày kết nối các ước lượng đó, cùng khoảng tin cậy tại mỗi điểm.','Điểm tại ngày 7 là ước lượng cho thời hạn 7 ngày, không phải giá Bitcoin dự báo ngày thứ 7.'],
 ['rolling','Rolling beta · Độ nhạy theo cửa sổ trượt','rolling beta 252 cửa sổ trượt độ nhạy','Ước lượng lặp trên các đoạn dữ liệu chuyển dần theo thời gian để xem độ nhạy thay đổi thế nào. Dashboard dùng cửa sổ 252 phiên và bước 21 phiên.','Đường beta khác nhau giữa các năm cho thấy mối liên hệ trong mẫu thay đổi theo thời gian.'],
 ['var','VAR · Mô hình tự hồi quy vector','var vector autoregression tự hồi quy vector','Mô hình mô tả nhiều chuỗi thời gian cùng lúc bằng các giá trị trễ của chúng. Phản ứng phụ thuộc cách đặt mô hình và thứ tự nhận dạng.','Mục phân tích sâu dùng hệ chung BTC–ETH; đây không phải VaR (Value at Risk).'],
 ['irf','IRF · Hàm phản ứng xung','irf impulse response phản ứng xung','Đường mô tả phản ứng theo thời gian sau một cú sốc trong mô hình VAR, dưới các giả định nhận dạng đã chọn.','Đổi thứ tự các biến có thể làm thay đổi đường IRF; nên xem cùng chẩn đoán mô hình.'],
 ['quantile','Phân vị · Quantile','quantile phân vị 5 50 95 phần trăm','Vị trí trong phân phối dữ liệu. Phân vị 5% tập trung vào vùng thấp, 50% ở giữa và 95% ở vùng cao của phân phối có điều kiện.','Phản ứng ở phân vị 5% có thể khác phản ứng tại trung vị 50%.'],
 ['rv','Realized variance · Phương sai từ giá trong ngày','rv realized variance har har-x biến động trong ngày','Thước đo được xây từ các biến động giá ở tần suất cao trong ngày. Nhánh RV dùng dữ liệu Binance USDT riêng, khác nhánh daily USD.','Lấy nến 5 phút hoặc 15 phút để dựng thước đo biến động; không ghép ngầm hai nguồn giá.'],
 ['benchmark','Benchmark · Mốc so sánh','benchmark mốc đối chứng mô hình cơ sở','Một cách dự báo làm mốc để đánh giá liệu mô hình phức tạp hơn có hữu ích hơn hay không.','Mô hình dùng thêm nhiều biến cần được so với mốc đơn giản trên cùng các ngày.'],
 ['ablation','Ablation · Kiểm tra đóng góp của nhóm biến','ablation thêm bỏ biến macro đóng góp','So sánh hai cấu hình có và không có một nhóm thông tin, giữ cách so sánh nhất quán để xem nhóm đó có cải thiện kết quả hay không.','So mô hình chỉ dùng crypto với mô hình có thêm dữ liệu kinh tế.'],
 ['mse','MSE · Sai số bình phương trung bình','mse mean squared error sai số loss','Bình quân bình phương chênh lệch giữa dự báo và kết quả thực tế. Với cùng mục tiêu và cùng mẫu, giá trị thấp hơn là sai số nhỏ hơn.','Không so MSE của lợi suất trực tiếp với QLIKE của phương sai vì hai thước đo khác nhau.'],
 ['qlike','QLIKE · Thước đo sai số dự báo biến động','qlike loss phương sai','Hàm mất mát dùng để đánh giá dự báo phương sai. So trên cùng dữ liệu, thấp hơn là tốt hơn; giá trị có thể âm.','QLIKE −6,5 có thể tốt hơn −6,4. Số âm ở đây không có nghĩa là lỗ tiền.'],
 ['pvalue','p-value · Mức bằng chứng thống kê','p p-value ý nghĩa thống kê kiểm định','Thước đo mức tương thích của dữ liệu với giả thuyết kiểm định và các giả định của mô hình. Không phải xác suất mô hình đúng hoặc dự báo sẽ thắng.','Khi kiểm tra nhiều giả thuyết, cần xem thêm hiệu chỉnh nhiều kiểm định, không chỉ p < 0,05.'],
 ['bh','BH q · Hiệu chỉnh nhiều kiểm định','bh q q-value benjamini hochberg nhiều kiểm định','Giá trị p đã được điều chỉnh theo phương pháp Benjamini–Hochberg trong từng nhóm kiểm định quy định trước, nhằm kiểm soát tỷ lệ phát hiện sai kỳ vọng.','Một kết quả có p nhỏ nhưng q lớn có thể không còn đạt ngưỡng sau hiệu chỉnh.'],
 ['pit','PIT · Thông tin đúng thời điểm','pit point in time rò rỉ dữ liệu leakage','Chỉ dùng thông tin thực sự được coi là khả dụng tại lúc dự báo. Ngày quan sát của một số liệu có thể sớm hơn ngày công bố hoặc ngày nhận được.','GDP quý trước được công bố hôm nay không thể dùng như thông tin đã biết từ đầu quý trước.'],
 ['vintage','Vintage · Phiên bản dữ liệu','vintage sửa đổi revision alfred phiên bản dữ liệu','Bản dữ liệu mà nguồn cung cấp tại một thời điểm. Một số chỉ tiêu kinh tế có thể được sửa lại sau công bố ban đầu.','Dữ liệu mới nhất tải hôm nay có thể khác dữ liệu mà người dự báo đã nhìn thấy năm trước.'],
 ['cutoff','Cutoff · Hạn chốt thông tin','cutoff receipt thời điểm nhận hạn chót buffer','Mốc muộn nhất mà thông tin được phép đi vào một dự báo. Receipt ghi thời điểm thực sự nhận dữ liệu; tải muộn không được đổi thành nhận sớm.','Nguồn về sau hạn chốt khiến ngày đó không đủ điều kiện; hệ thống không dựng bù dự báo cũ.'],
 ['target','Mục tiêu dự báo · Target','target label nhãn mục tiêu','Đại lượng mà mô hình cần dự báo; nhãn là kết quả thực tế để đối chiếu sau đó.','Chọn lợi suất mỗi ngày hoặc mức biến động giá; hai mục tiêu dùng cách đánh giá khác nhau.'],
 ['elastic','Elastic Net','elastic net hồi quy regularization thuật toán','Mô hình hồi quy có cơ chế điều chuẩn để hạn chế hệ số quá lớn và xử lý nhiều biến giải thích. Tên thuật toán không tự nói lên chất lượng dự báo.','So sánh kết quả ngoài mẫu với mô hình làm mốc thay vì chỉ nhìn độ khớp trên mẫu huấn luyện.'],
 ['boosting','Gradient boosting','boosting histogram cây mô hình machine learning','Phương pháp học máy kết hợp nhiều mô hình cây theo từng bước để cải thiện mục tiêu tối ưu. Vẫn cần kiểm tra ngoài mẫu và giới hạn thông tin đúng thời điểm.','Mô hình phức tạp hơn có thể khớp dữ liệu cũ tốt nhưng không nhất thiết dự báo tương lai tốt hơn.'],
];
function orbitNormalize(s){return String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/[^a-z0-9]+/g,' ').trim();}
function orbitSearchTerms(query){
 const words=orbitNormalize(query).split(/\s+/).filter(Boolean);
 return ORBIT_TERMS.map(t=>({term:t,text:orbitNormalize(t.slice(0,4).join(' '))})).filter(t=>words.every(w=>w.length<=3?t.text.split(/[^a-z0-9]+/).includes(w):t.text.includes(w))).sort((a,b)=>Number(orbitNormalize(b.term[1]).startsWith(orbitNormalize(query)))-Number(orbitNormalize(a.term[1]).startsWith(orbitNormalize(query)))).map(r=>r.term);
}
(() => {
 if(typeof window==='undefined'||!document.documentElement)return;
 const $=id=>document.getElementById(id), root=document.documentElement;
 const text=(id,value)=>{const e=$(id);if(e)e.textContent=value;};
 const workspaceRenderer=showWorkspace;
 showWorkspace=function(view){workspaceRenderer(view);$('mobileWorkspace').value=root.dataset.workspace||view;};
 $('mobileWorkspace').value=root.dataset.workspace||initialWorkspace;
 $('mobileWorkspace').addEventListener('change',e=>{showWorkspace(e.target.value);window.scrollTo({top:0,behavior:'instant'});});
 window.addEventListener('hashchange',()=>{$('mobileWorkspace').value=root.dataset.workspace;});
 const date=value=>{const d=new Date(value);return !value||Number.isNaN(d.getTime())?'Chưa có thông tin':d.toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});};
 let lastFocus=null, selectedTerm=null, commandRows=[], commandIndex=0;
 const commandActions=()=>[
  ...Object.entries(WORKSPACE_NAMES).map(([key,label])=>({key:'go-'+key,title:'Mở '+label,aliases:key+' workspace chuyển trang',group:'Đi đến',run:()=>{showWorkspace(key);window.scrollTo({top:0,behavior:'instant'});}})),
  {key:'theme',title:'Đổi giao diện sáng / tối',aliases:'theme dark light giao dien',group:'Thao tác',run:()=>window.orbitToggleTheme()},
  {key:'csv',title:'Tải CSV của workspace',aliases:'export download tai xuat du lieu',group:'Thao tác',run:()=>window.orbitExportCurrent()},
  {key:'print',title:'In workspace đang xem',aliases:'print ban in pdf',group:'Thao tác',run:()=>window.print()},
  {key:'keys',title:'Xem phím tắt',aliases:'shortcut keyboard ban phim',group:'Thao tác',run:()=>$('shortcutDialog').showModal()},
 ];
 function highlight(label,query){
  const span=document.createElement('span'),normal=orbitNormalize(label),word=orbitNormalize(query).split(' ').find(w=>w&&normal.includes(w));
  if(!word){span.textContent=label;return span;}
  // Vietnamese precomposed characters map one-to-one after removing accents.
  const start=normal.indexOf(word),before=document.createTextNode(label.slice(0,start)),mark=document.createElement('mark');mark.textContent=label.slice(start,start+word.length);span.append(before,mark,document.createTextNode(label.slice(start+word.length)));return span;
 }
 function selectTerm(term){
  selectedTerm=term[0];const box=$('glossaryDetail');box.replaceChildren();
  const title=document.createElement('h3');title.textContent=term[1];
  const body=document.createElement('p');body.textContent=term[3];
  const example=document.createElement('div');example.className='term-example';
  const label=document.createElement('strong');label.textContent='Ví dụ';
  const para=document.createElement('p');para.textContent=term[4];example.append(label,para);
  const link=document.createElement('a');link.href='https://www.google.com/search?q='+encodeURIComponent(term[1]+' finance giải thích');link.target='_blank';link.rel='noopener noreferrer';link.textContent='Tìm hiểu thêm trên Google ↗';
  box.append(title,body,example,link);
 }
 function focusCommand(index){
  commandIndex=Math.max(0,Math.min(commandRows.length-1,index));
  const row=commandRows[commandIndex];if(!row)return;
  const buttons=[...$('glossaryResults').querySelectorAll('button')];buttons.forEach((b,i)=>b.setAttribute('aria-selected',String(i===commandIndex)));
  if(buttons[commandIndex]){buttons[commandIndex].scrollIntoView({block:'nearest'});$('glossarySearch').setAttribute('aria-activedescendant',buttons[commandIndex].id);}
  if(row.term)selectTerm(row.term);else{const box=$('glossaryDetail');box.replaceChildren();const h=document.createElement('h3');h.textContent=row.title;const p=document.createElement('p');p.textContent='Nhấn Enter hoặc chọn kết quả để thực hiện.';box.append(h,p);}
 }
 function activateCommand(index){const row=commandRows[index];if(!row)return;if(row.term){focusCommand(index);return;}$('glossaryDialog').close();row.run();}
 function searchTerms(){
  const query=$('glossarySearch').value,words=orbitNormalize(query).split(' ').filter(Boolean),list=$('glossaryResults');list.replaceChildren();
  const actions=commandActions().filter(a=>words.every(w=>orbitNormalize(a.title+' '+a.aliases).includes(w)));
  const terms=orbitSearchTerms(query).slice(0,query?16:6).map(term=>({key:term[0],title:term[1],group:'Thuật ngữ',term}));
  commandRows=[...actions,...terms];commandIndex=0;
  if(!commandRows.length){const p=document.createElement('p');p.textContent='Chưa có kết quả. Thử từ ngắn hơn.';list.append(p);const link=document.createElement('a');link.href='https://www.google.com/search?q='+encodeURIComponent(query+' tài chính crypto');link.target='_blank';link.rel='noopener noreferrer';link.textContent='Tìm trên Google ↗';list.append(link);$('glossaryDetail').replaceChildren();return;}
  let group='';commandRows.forEach((row,i)=>{if(row.group!==group){group=row.group;const label=document.createElement('div');label.className='command-group';label.textContent=group;list.append(label);}const b=document.createElement('button');b.type='button';b.id='command-result-'+i;b.dataset.key=row.key;b.append(highlight(row.title,query));b.setAttribute('role','option');b.setAttribute('aria-selected','false');b.addEventListener('click',()=>activateCommand(i));b.addEventListener('pointerenter',()=>focusCommand(i));list.append(b);});
  const remembered=commandRows.findIndex(r=>r.term&&r.term[0]===selectedTerm);focusCommand(query&&remembered>=0?remembered:0);
 }
 function openGlossary(key){
  lastFocus=document.activeElement;const term=ORBIT_TERMS.find(t=>t[0]===key);if(term)selectedTerm=term[0];else selectedTerm=null;
  $('glossarySearch').value=term?term[1].split(' · ')[0]:'';if(!$('glossaryDialog').open)$('glossaryDialog').showModal();$('glossarySearch').setAttribute('aria-expanded','true');searchTerms();$('glossarySearch').focus();$('glossarySearch').select();
 }
 window.orbitOpenCommand=openGlossary;
 $('openGlossary').addEventListener('click',()=>openGlossary());$('closeGlossary').addEventListener('click',()=>$('glossaryDialog').close());
 $('glossaryDialog').addEventListener('close',()=>{$('glossarySearch').setAttribute('aria-expanded','false');if(lastFocus&&lastFocus.isConnected)lastFocus.focus();});
 $('glossaryDialog').addEventListener('click',e=>{const r=e.currentTarget.getBoundingClientRect();if(e.target===e.currentTarget&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))e.currentTarget.close();});
 $('glossarySearch').addEventListener('input',searchTerms);
 $('glossarySearch').addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();focusCommand(commandIndex+1);}if(e.key==='ArrowUp'){e.preventDefault();focusCommand(commandIndex-1);}if(e.key==='Enter'){e.preventDefault();activateCommand(commandIndex);}});
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openGlossary();}});
 document.addEventListener('click',e=>{const b=e.target.closest('[data-term]');if(b)openGlossary(b.dataset.term);});
 function updateResponseReading(){
  const row=responseRows().find(r=>r.horizon_days===Number($('horizon').value));if(!row)return;
  const n=v=>Number(v).toLocaleString('vi-VN',{minimumFractionDigits:3,maximumFractionDigits:3}),shock=$('shock').selectedOptions[0].textContent;
  text('responseReadingTitle',`${shock} → ${row.asset.toUpperCase()} ước lượng ${row.beta_pct>0?'+':''}${n(row.beta_pct)}% sau ${row.horizon_days} ngày.`);
  text('responseReadingBody',`CI 95%: ${n(row.lower95)}% đến ${n(row.upper95)}%. Kết quả ước lượng từ lịch sử.`);
 }
 const responseRenderer=renderResponse;
 renderResponse=function(){const start=performance.now();responseRenderer();updateResponseReading();root.dataset.responseRenderMs=(performance.now()-start).toFixed(1);};
 let responseFrame=null;
 const queuedResponse=()=>{if(responseFrame!==null)cancelAnimationFrame(responseFrame);responseFrame=requestAnimationFrame(()=>{responseFrame=null;renderResponse();});};
 for(const id of ['asset','shock','regime','horizon']){$(id).removeEventListener('change',responseRenderer);$(id).addEventListener('change',queuedResponse);}
 function updateForecastReading(){
  const s=selectedForecast(),pair=historyPairs[Number($('forecastPair').value||0)],row=LATEST.ablation.find(r=>matches(r,s)&&r.base===pair[0]&&r.added===pair[1]);if(!row)return;
  const better=row.mean_loss_new_minus_base<0,significant=row.qvalue_bh!==null&&row.qvalue_bh<.05;
  text('forecastReadingTitle',`Thêm dữ liệu: sai số ${better?'thấp hơn':'cao hơn'} trong kỳ đang chọn.`);
  text('forecastReadingBody',`${significant?'Đạt':'Chưa đạt'} BH q < 0,05 · ${row.n.toLocaleString('vi-VN')} ngày ghép cặp. Historical pseudo-OOS / exploratory.${s.scenario==='matched_latest_d3'?' Dữ liệu sửa sau: chỉ để đối chiếu.':''}`);
 }
 window.orbitUpdateForecast=updateForecastReading;
 const forecastRenderer=renderForecast;
 renderForecast=function(){forecastRenderer();updateForecastReading();};
 for(const id of ['target','forecastModel','forecastPair','fAsset','fScenario']){$(id).removeEventListener('change',forecastRenderer);$(id).addEventListener('change',renderForecast);}
 $('retryHistory').addEventListener('click',()=>loadForecastWorkspace());
 for(const b of document.querySelectorAll('[data-example]'))b.addEventListener('click',()=>{
  const examples={vix:{asset:'btc',shock:'vix_change',horizon:'7'},usd:{asset:'eth',shock:'usd_return_pct',horizon:'7'},fomc:{asset:'btc',shock:'monetary',horizon:'3'}};
  for(const [key,value]of Object.entries(examples[b.dataset.example]))$(key).value=value;
  $('regime').value='full';showWorkspace('transmission');renderResponse();$('responses').scrollIntoView({block:'start',behavior:'smooth'});
 });
 // Reports may contain machine vocabulary; explain it beside the results.
 const terms={asset:'btc',shock:'shock',regime:'regime',horizon:'horizon',target:'target',forecastModel:'elastic',fScenario:'pit',forecastPair:'ablation',varOrder:'irf',rvSampling:'rv',eOutcome:'fomc'};
 for(const [id,key] of Object.entries(terms)){const select=$(id),label=select&&select.closest('label');if(!label||label.querySelector('[data-term]'))continue;const h=document.createElement('button');h.type='button';h.className='term-help';h.dataset.term=key;h.setAttribute('aria-label','Giải thích '+label.childNodes[0].textContent.trim());h.textContent='?';label.append(h);}
 for(const option of $('horizon').options)option.textContent=option.value+' ngày';
 const cutoff=document.querySelector('.topbar-date');if(cutoff)cutoff.title='Ngày cuối của mẫu nghiên cứu lịch sử';
 let status=ORBIT_STATUS;
 function showStatus(data,source){
  status=data;window.orbitStatus=data;const worker=data.worker||{},p=data.prospective||{},last=Date.parse(worker.last_success_utc),age=Number.isFinite(last)?Date.now()-last:Infinity,stale=age>(data.schedule?.stale_after_minutes||150)*60000;
  const enabled=worker.installed===true,health=worker.health_status==='healthy';
  text('statusBadge',!enabled?'Chưa xác minh lịch chạy':stale?'Trạng thái quá 150 phút':health?'Worker hoạt động tại lần kiểm tra':'Cần kiểm tra worker');
  $('statusBadge').dataset.state=enabled&&health&&!stale?'good':'warning';
  text('statusLastRun',date(worker.last_success_utc));
  text('statusWorkerDetail',`${worker.provider==='github-actions'?'GitHub Actions.':'Nơi chạy: '+(worker.provider||'chưa xác minh')+'.'} ${stale?'Thông tin đã cũ; đối chiếu lịch sử chạy.':'Thời điểm theo metadata công khai.'}`);
  text('statusPredictions',`${p.prediction_files??0} lượt · ${p.prediction_rows??0} dự báo`);
  text('statusPredictionDetail',`${p.label_files??0} tệp nhãn thực tế. ${p.prediction_rows?'Đợi đủ nhãn và đến kỳ đánh giá.':'Bản này chưa ghi dự báo mới đủ điều kiện.'}`);
  text('statusEvaluation',p.fixed_end?new Date(p.fixed_end).toLocaleDateString('vi-VN',{timeZone:'UTC'})+' · UTC':'Chưa có thông tin');
  text('statusEvaluationDetail',p.performance==='PENDING_FIXED_EVALUATION_WINDOW'?'Chưa đến kỳ đánh giá cố định. Dashboard chưa xác nhận năng lực dự báo tương lai.':'Trạng thái đánh giá: '+(p.performance||'chưa có thông tin')+'.');
  const capture=data.capture||{};
  text('statusCaptureTime',capture.status==='verified'?date(capture.finished_at_utc):'Chưa có biên bản thu trong bản này');
  text('statusCaptureSources',capture.status==='verified'?`${capture.sources_ok}/${capture.sources_total} nguồn thành công; đã đối chiếu hash biên bản thu.`:'Bản này chưa có biên bản thu dữ liệu đã xác minh.');
  text('statusMessage',`${source} · ${date(data.generated_at_utc)} giờ Việt Nam. Chỉ đọc metadata.`);
 }
 let checking=false;
 async function checkStatus(){
  if(checking)return;checking=true;$('refreshStatus').disabled=true;text('statusMessage','Đang đọc metadata công khai của website…');
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),6000);
  try{
   const url=location.protocol==='file:'?'https://tranthanhphu39.github.io/dashboard_crypto/dashboard/status.json':new URL('status.json',location.href).href;
   const response=await fetch(url,{cache:'no-store',signal:controller.signal});if(!response.ok)throw new Error('Trạng thái chưa được xuất bản (HTTP '+response.status+').');
   const next=await response.json();if(next.schema_version!==1||next.repository!=='TranThanhPhu39/dashboard_crypto')throw new Error('Định dạng trạng thái không phù hợp.');
   showStatus(next,'Đã kiểm tra website');
   if(next.generated_at_utc!==ORBIT_STATUS.generated_at_utc){const a=document.createElement('a');a.href='https://tranthanhphu39.github.io/dashboard_crypto/dashboard/';a.target='_blank';a.rel='noopener noreferrer';a.textContent='Mở bản online mới nhất ↗';$('statusMessage').append(' ',a);}
  }catch(error){showStatus(status,'Đang dùng trạng thái nhúng trong file');text('statusMessage',$('statusMessage').textContent+' Chưa kiểm tra được website: '+(error.name==='AbortError'?'kết nối quá thời gian chờ.':error.message)+' Có thể dùng bản nhúng và đối chiếu GitHub.');}
  finally{clearTimeout(timeout);checking=false;$('refreshStatus').disabled=false;}
 }
 $('refreshStatus').addEventListener('click',checkStatus);showStatus(status,location.protocol==='file:'?'Bản HTML mở trên máy':'Trạng thái đi kèm bản website này');
 if(location.protocol==='https:'||location.protocol==='http:'){checkStatus();setInterval(()=>{if(!document.hidden)checkStatus();},300000);}
 // Restore readable labels after each render, without replacing numeric values.
 const labels={transmission:'Truyền dẫn',forecast:'Dự báo rủi ro',fomc:'FOMC',advanced:'Phân vị & VAR'};
 for(const [key,label]of Object.entries(labels)){const span=$('tab-'+key).querySelector('span');if(span)span.textContent=label;}
 updateResponseReading();
 orbitStartStudio();
 for(const node of document.querySelectorAll('[data-orbit-inert]'))node.removeAttribute('inert');
 $('bootStatus').hidden=true;
 root.dataset.orbitReady='true';
})();
```

## dashboard/transmission.html

```html
<section data-workspace="transmission" class="panel response-workspace" id="responses">
  <h2 class="sr-only">Khám phá phản ứng theo cú sốc</h2>
  <div class="mobile-filter-bar"><button type="button" id="openFilters"><span id="mobileFilterLabel">BTC · VIX +5 điểm</span><span>Điều chỉnh ↗</span></button></div>
  <div id="controlHome"><div class="controls control-strip" id="responseControls">
    <div class="control-group"><div class="control-label">Tài sản <button type="button" id="assetHelp" class="term-help" data-term="btc" aria-label="Giải thích tài sản">?</button></div><label class="sr-only" for="asset">Tài sản</label><select id="asset" class="sr-only"><option value="btc">Bitcoin</option><option value="eth">Ethereum</option></select><div class="segmented asset-segment" aria-label="Tài sản"><i class="segment-thumb" aria-hidden="true"></i><button type="button" data-asset="btc" aria-pressed="true"><span class="asset-mark">₿</span> BTC</button><button type="button" data-asset="eth" aria-pressed="false"><span class="asset-mark">Ξ</span> ETH</button></div></div>
    <label class="shock-control">Cú sốc vĩ mô<select id="shock"><option value="vix_change">VIX +5 điểm</option><option value="usd_return_pct">Broad USD +1%</option><option value="us2y_change_bps">Treasury 2Y +10 bps</option><option value="us10y_change_bps">Treasury 10Y +10 bps</option><option value="monetary">Tiền tệ STMT +10 bps</option></select></label>
    <div class="control-group"><div class="control-label">Trạng thái <button type="button" class="term-help" data-term="regime" aria-label="Giải thích trạng thái thị trường">?</button></div><label class="sr-only" for="regime">Trạng thái thị trường</label><select id="regime" class="sr-only"><option value="full">Toàn mẫu</option><option value="calm">Bình thường</option><option value="stress">Căng thẳng</option></select><div class="segmented regime-segment" aria-label="Trạng thái"><i class="segment-thumb" aria-hidden="true"></i><button type="button" data-regime="full" aria-pressed="true">Tất cả</button><button type="button" data-regime="calm" aria-pressed="false" aria-label="Bình thường · Calm" title="Bình thường · Calm">Calm</button><button type="button" data-regime="stress" aria-pressed="false" aria-label="Căng thẳng · Stress" title="Căng thẳng · Stress">Stress</button></div></div>
    <div class="control-group horizon-control"><div class="control-label"><label for="horizonSlider">Sau <output id="horizonOutput" for="horizonSlider">1</output> ngày</label><button type="button" class="term-help" data-term="horizon" aria-label="Giải thích thời hạn phản ứng">?</button></div><label class="sr-only" for="horizon">Thời hạn phản ứng</label><select id="horizon" class="sr-only"></select><input id="horizonSlider" list="horizonMarks" type="range" min="1" max="30" step="1" value="1" aria-label="Thời hạn phản ứng, từ 1 đến 30 ngày"><datalist id="horizonMarks"><option value="1"></option><option value="7"></option><option value="14"></option><option value="30"></option></datalist><div class="range-marks"><span>1</span><span>7</span><span>14</span><span>30 ngày</span></div></div>
  </div></div>
  <div class="insight-strip" id="responseReading" aria-live="polite" aria-atomic="true"><div><span class="reading-eyebrow">GÓC NHÌN ĐANG CHỌN</span><strong id="responseReadingTitle"></strong><p id="responseReadingBody"></p></div><span class="certainty-badge" id="certaintyBadge">Đang đọc kết quả</span></div>
  <div class="grid response-grid">
    <div class="response-plot"><div class="chart-toolbar"><div><strong>30 ngày sau cú sốc</strong><span>Lợi suất log cộng dồn · %</span></div><div class="horizon-presets" id="horizonPresets" aria-label="Chọn nhanh thời hạn"><button type="button" data-horizon="1" aria-label="Phản ứng sau 1 ngày" aria-pressed="true">1N</button><button type="button" data-horizon="7" aria-label="Phản ứng sau 7 ngày" aria-pressed="false">7N</button><button type="button" data-horizon="14" aria-label="Phản ứng sau 14 ngày" aria-pressed="false">14N</button><button type="button" data-horizon="30" aria-label="Phản ứng sau 30 ngày" aria-pressed="false">30N</button></div></div>
      <div class="interactive-chart" id="responseChartWrap"><svg id="responseChart" viewBox="0 0 720 330" role="img" tabindex="0" aria-label="Đường phản ứng và CI tại từng ngày. Dùng mũi tên trái phải chọn ngày; Enter để ghim."></svg><div class="chart-tooltip" id="responseTooltip" role="status" hidden></div></div>
      <div class="chart-legend"><span class="asset-key btc-key"><i></i>BTC · nét liền</span><span class="asset-key eth-key"><i></i>ETH · nét đứt</span><span><i class="band"></i>CI 95% của tài sản chọn</span><label class="compare-toggle"><input id="compareAssets" type="checkbox" checked>So sánh hai tài sản</label></div><div class="chart-caption"><span id="chartInteractionHint">Rê để xem · bấm để ghim ngày</span><span id="analogueOverlayLabel" hidden></span></div>
    </div>
    <aside class="result" aria-label="Chi tiết ngày đang chọn"><div class="result-kicker"><span class="status-dot"></span><span id="pinState">NGÀY ĐANG CHỌN</span><button type="button" id="unpinResponse" hidden>Bỏ ghim</button></div><span id="responseMetricLabel">Phản ứng sau 1 ngày</span><div class="big" id="responsePoint"></div><p id="responseCI"></p><div class="interval-meter" aria-hidden="true"><span>Giảm</span><div id="intervalTrack"><i id="intervalBand"></i><b id="intervalPoint"></b><em id="intervalZero"></em></div><span>Tăng</span></div><p id="responseVerdict" class="verdict"></p><div class="result-divider"></div><p id="responseSample"></p><p id="responseInference" class="muted"></p><div class="result-footnote">Ước lượng lịch sử · không phải dự báo giá</div></aside>
  </div>
  <div class="workspace-actions"><button type="button" id="exportResponse" class="action-primary">↓ Tải CSV</button><button type="button" id="resetResponse" class="action-secondary">↺ Đặt lại</button><span id="selectionLabel" class="selection-label"></span><button type="button" id="printDashboard" class="text-button">Bản in ↗</button></div>
  <p class="chart-caveat">CI 95% tại từng ngày (pointwise), không phải dải đồng thời. <button type="button" class="text-button" data-term="ci">Đọc CI thế nào?</button></p>
  <details class="context-details"><summary>Timing, mẫu và giới hạn diễn giải</summary><p id="responseTiming" class="compact-meta"></p><p>Mẫu nền daily UTC: 01/01/2014–15/10/2026; phạm vi thực tế tùy tài sản và biến. USD PIT bắt đầu từ 2019.</p><p>Daily USD và nhánh RV Binance USDT dùng nguồn riêng. STMT không đồng nhất với các thành phần policy / information của FOMC. Các kết quả là quan hệ ước lượng theo thiết kế nghiên cứu.</p></details>
  <details class="context-details"><summary>Bảng dữ liệu 1–30 ngày</summary><div class="table-wrap" id="responseDataTable"></div></details>
  <details class="context-details"><summary>Kiểm định Stress − Calm</summary><div id="differenceTable" class="table-wrap"></div><p>Kiểm định trực tiếp chênh lệch; không suy từ hai p-value khác nhau. BH tách family 240 daily và 60 monetary; kết quả exploratory.</p></details>
  <details class="quick-guide" id="quickGuide"><summary>Thử một câu hỏi có sẵn</summary><div class="guide-examples"><button type="button" data-example="vix">BTC khi VIX tăng · 7 ngày</button><button type="button" data-example="usd">ETH khi USD tăng · 7 ngày</button><button type="button" data-example="fomc">BTC sau thông tin Fed · 3 ngày</button></div></details>
</section>
```

## dashboard/rolling.html

```html
<section data-workspace="transmission" class="panel bento-panel" id="rolling"><div class="panel-heading"><div><span class="section-kicker">THAY ĐỔI THEO THỜI GIAN</span><h2>Độ nhạy có ổn định?</h2></div><button type="button" id="resetRolling" class="text-button">Toàn kỳ ↗</button></div><p class="section-intro">Cửa sổ 252 phiên · dịch mỗi 21 phiên</p><div class="controls rolling-controls"><label>Tài sản<select id="rollAsset"><option value="btc">Bitcoin</option><option value="eth">Ethereum</option></select></label><label>Cú sốc<select id="rollShock"><option value="vix_change">VIX +5 điểm</option><option value="usd_return_pct">USD +1%</option><option value="us2y_change_bps">2Y +10 bps</option><option value="us10y_change_bps">10Y +10 bps</option></select></label></div><svg id="rollingChart" viewBox="0 0 720 330" role="img" tabindex="0" aria-label="Rolling beta. Kéo để phóng to một khoảng; nhấp đúp để đặt lại. Dùng bộ chọn ngày bên dưới để zoom bằng bàn phím."></svg><p class="compact-meta" id="rollingRangeLabel">Kéo một khoảng để zoom · nhấp đúp để đặt lại</p><details class="context-details"><summary>Chọn khoảng ngày hoặc đọc bảng</summary><div class="controls"><label>Từ ngày<input type="date" id="rollingStart"></label><label>Đến ngày<input type="date" id="rollingEnd"></label><button type="button" id="applyRollingRange">Xem khoảng</button></div><div id="rollingDataTable" class="table-wrap"></div></details></section>
```

## dashboard/analogues.html

```html
<section data-workspace="transmission" class="panel bento-panel" id="analoguePanel"><div class="panel-heading"><div><span class="section-kicker">ĐỐI CHIẾU LỊCH SỬ</span><h2>Những lần tương tự</h2></div><button type="button" class="term-help" data-term="shock" aria-label="Giải thích sự kiện tương tự">?</button></div><p class="section-intro">Tối đa 5 giai đoạn không chồng lấp. Rê hoặc chọn thẻ để đối chiếu diễn biến thực tế.</p><div id="analogueCards" class="analogue-cards"></div><p class="chart-caveat">Lợi suất thực tế là quan sát lịch sử; không phải tác động nhân quả của riêng cú sốc.</p><details class="context-details"><summary>Số liệu và quy mô cú sốc</summary><div id="analogueTable" class="table-wrap"></div></details></section>
```

## src/dashboard_design.py

```python
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
```

## src/dashboard_studio.py

```python
"""Orbit 3 markup: focused reading order, stable scientific IDs, offline assets."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAGES = [('transmission', 'Truyền dẫn', 'wave'), ('forecast', 'Dự báo rủi ro', 'chart'),
         ('fomc', 'FOMC', 'bank'), ('advanced', 'Phân vị & VAR', 'layers'),
         ('methods', 'Phương pháp & nguồn', 'book'), ('operations', 'Dữ liệu & OOS', 'clock')]


def studio(html):
    from src.dashboard_design import icon
    html = re.sub(r'<!-- ORBIT STUDIO [A-Z_]+ START -->.*?<!-- ORBIT STUDIO [A-Z_]+ END -->', '', html, flags=re.S)
    def button(key, label, symbol, mobile=False):
        if mobile:
            return f'<button type="button" data-goto="{key}">{icon(symbol)}<span>{label}</span></button>'
        return f'<button type="button" id="tab-{key}" class="workspace-tab" aria-controls="{dict(transmission="responses rolling analoguePanel",forecast="forecast rv",fomc="fomc",advanced="quantile joint",methods="overview pit methods",operations="operations")[key]}" aria-pressed="{str(key=="transmission").lower()}" title="{label}">{icon(symbol)}<span>{label}</span><kbd>{[x[0] for x in PAGES].index(key)+1}</kbd></button>'
    groups = [('Phân tích', [0, 2, 3]), ('Kiểm chứng', [1, 5]), ('Tài liệu', [4])]
    nav = '<nav class="workspace-nav" aria-label="Không gian nghiên cứu"><a class="brand" href="#transmission" aria-label="orbit. — Trang truyền dẫn">'+icon('orbit','brand-symbol')+'<span>orbit<span class="brand-dot">.</span><small>MACRO × CRYPTO</small></span></a><div class="nav-items"><i id="navActive" aria-hidden="true"></i>'
    for label, indices in groups:
        nav += '<div class="nav-label">'+label+'</div>'+''.join(button(*PAGES[i]) for i in indices)
    nav += '</div><div class="sidebar-bottom"><div class="sidebar-caption"><span class="status-dot"></span>Nghiên cứu, từng góc nhìn.</div><button type="button" id="learnMethods" class="sidebar-method">Cách đọc kết quả '+icon('arrow')+'</button><button type="button" id="collapseSidebar" class="sidebar-collapse" aria-label="Thu gọn menu" aria-expanded="true">'+icon('layers')+'<span>Thu gọn menu</span></button><span class="lab-signature">ORBIT RESEARCH / 03</span></div><select id="mobileWorkspace" class="sr-only" aria-label="Workspace">'+''.join(f'<option value="{k}">{l}</option>' for k,l,_ in PAGES)+'</select></nav>'
    html = re.sub(r'<nav\b[^>]*>.*?</nav>', nav, html, count=1, flags=re.S)
    header = '<header class="app-header"><div class="topbar-path"><button type="button" id="openNavigation" class="icon-button" aria-label="Mở menu">'+icon('layers')+'</button><span class="topbar-label">Nghiên cứu</span><span class="path-divider">/</span><strong id="designBreadcrumb">Truyền dẫn</strong></div><div class="topbar-actions"><span class="topbar-date">Dữ liệu đến 15/10/2026</span><button type="button" id="openGlossary" class="glossary-trigger" aria-label="Tìm kiếm và lệnh · Ctrl K"><span aria-hidden="true">⌕</span><span>Tìm kiếm &amp; lệnh</span><kbd>Ctrl K</kbd></button><button type="button" id="themeToggle" class="icon-button" aria-label="Đổi giao diện sáng tối">'+icon('sun')+'</button><button type="button" id="topExport" class="top-export" aria-label="Tải CSV của workspace">'+icon('download')+'<span>Tải CSV</span></button></div></header>'
    html = re.sub(r'<header\b[^>]*>.*?</header>', header, html, count=1, flags=re.S)
    hero = '<!-- ORBIT HERO START --><div class="workspace-hero"><div class="hero-eyebrow" id="designEyebrow">MACRO × CRYPTO / RESEARCH EXPLORER</div><h1 id="designTitle">Từ vĩ mô đến crypto<span>.</span></h1><p id="designDescription">Một thay đổi kinh tế. Hai tài sản. 30 ngày phản ứng.</p><div id="designMetrics" hidden><span id="designSample"></span><span id="designSampleMeta"></span></div></div><!-- ORBIT HERO END -->'
    html = re.sub(r'<!-- ORBIT HERO START -->.*?<!-- ORBIT HERO END -->', hero, html, flags=re.S)
    html = re.sub(r'<!-- ORBIT EXPERIENCE GUIDE START -->.*?<!-- ORBIT EXPERIENCE GUIDE END -->', '', html, flags=re.S)
    html = re.sub(r'<div id="appFeedback"[^>]*></div>', '', html)
    html = html.replace('<span id="workspaceTitle"', '<div id="appFeedback" class="app-feedback" role="status" hidden></div><span id="workspaceTitle"',1)
    for key, filename in [('responses','transmission.html'),('rolling','rolling.html')]:
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
    return html
```
