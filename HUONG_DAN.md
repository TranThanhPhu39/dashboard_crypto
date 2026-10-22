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
