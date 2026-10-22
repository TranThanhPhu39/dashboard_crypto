# orbit. — Giao diện Macro × Crypto

Giao diện mới dùng nền xanh mực, điểm nhấn lime/mint, menu bên trái và bố cục tự điều chỉnh cho điện thoại. Có giao diện sáng, chọn nhanh phản ứng 1/7/14/30 ngày và chọn ngày bằng cách chạm đường phản ứng. Các chức năng phân tích, phát lại dự báo, CSV, dữ liệu và mô hình nghiên cứu được giữ nguyên.

## Áp dụng vào bản clone trong VS Code

Giải nén gói giao diện, chép các thư mục `dashboard`, `src`, `tools`, `docs` vào thư mục gốc `dashboard_crypto` đang có. Chọn thay thế đúng các file trùng tên; không xóa những file khác trong dự án. Gói chỉ chứa các file giao diện đã sửa hoặc thêm.

Mở `dashboard/index.html` bằng trình duyệt, hoặc mở terminal ở thư mục gốc và chạy:

```powershell
py -m http.server 8000 --bind 127.0.0.1
```

Truy cập `http://localhost:8000/dashboard/`. Nếu đang mở bản cũ, nhấn Ctrl + F5 để tải lại.

## Chỉnh tiếp giao diện

| File | Vai trò |
| --- | --- |
| `dashboard/design.css` | Màu sắc, bố cục, giao diện sáng/tối, màn hình nhỏ và bản in |
| `dashboard/design.js` | Chuyển giao diện, điều hướng, chọn nhanh horizon và đồng bộ thẻ số liệu |
| `src/dashboard_design.py` | Dựng phần giao diện từ snapshot hiện có, giữ nguyên payload và code tính toán |
| `src/dashboard_workspace.py` | Tự áp dụng thiết kế mới khi pipeline dựng dashboard |
| `tools/refresh_dashboard_design.py` | Làm mới giao diện mà không cần tải dữ liệu hoặc huấn luyện mô hình |

Sau khi sửa CSS/JS, chạy:

```powershell
py tools/refresh_dashboard_design.py
```

Script chỉ cần Python chuẩn, không cần cài thư viện nghiên cứu. Có thể chạy nhiều lần, không nhân đôi thành phần giao diện. Trang HTML kết quả đã nhúng CSS/JS nên mở được offline.

## Kiểm chứng

- `node tests/validate_release_dashboard.cjs`: đạt 900 tổ hợp phản ứng/CSV, 640 cấu hình dự báo/replay, 108 VAR, 64 FOMC, 24 phân vị, 8 RV, 40 importance và 8 rolling.
- `python tools/export_public_dashboard.py --dashboard-only` và `python tools/check_public_dashboard.py --dashboard-only`: đạt.
- Đối chiếu payload `DATA`, `HISTORICAL`, `LATEST` và chương trình tính toán gốc: không đổi.
- Kiểm tra trình duyệt: bộ lọc tài sản, horizon, menu, chế độ sáng/tối; bản điện thoại 375px không tràn ngang.

Snapshot và mốc dữ liệu được ghi đúng trạng thái lịch sử. Giao diện không giả lập giá hay dữ liệu thị trường trực tiếp. Các liên kết báo cáo chi tiết trong bản repo phụ thuộc các file đi kèm; bản HTML xem thử độc lập bỏ các liên kết báo cáo ngoài trang.

Những thay đổi này được chuẩn bị trên nhánh cục bộ `design/orbit-dashboard`, chưa đẩy lên GitHub.
