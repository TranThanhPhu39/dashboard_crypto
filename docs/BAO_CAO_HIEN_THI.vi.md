# Sửa lỗi hình bị thiếu trong báo cáo

Ảnh chụp là báo cáo `outputs/research/evidence_20261019/report.html`.
Ba đường dẫn PNG trong báo cáo không có tệp tương ứng trong bản GitHub:

- `figures/falsification_windows.png`
- `figures/rotation_and_sampling.png`
- `figures/rv_forecasting.png`

Đổi trình duyệt hoặc nhấn F5 không khôi phục được các tệp chưa có. Muốn xem
đúng ba hình gốc, cần bộ artifact nghiên cứu đầy đủ và giữ cấu trúc thư mục.
Không chạy lại train/fit để sửa lỗi hiển thị.

## Mở bản đọc đã sửa

Giải nén gói sửa vào thư mục gốc `dashboard_crypto`, cùng cấp với `README.md`
và `MO_DASHBOARD.cmd`. Nhấp đúp **`MO_BAO_CAO.cmd`**, hoặc mở trực tiếp
`outputs/research/evidence_20261019/report_view.html`.

Bản HTML độc lập `bao_cao_hien_thi.html` có thể tải và mở ngay bằng Chrome/Edge,
không cần chép vào dự án. Các biểu đồ nhúng không cần mạng hoặc thư mục ảnh.
Liên kết dashboard trong bản độc lập mở website công khai; website đó chỉ có
giao diện mới sau khi code được đẩy và triển khai.

## Các biểu đồ thay thế thể hiện gì?

- Cửa sổ sự kiện: vẽ 16 hệ số từ bảng. Không vẽ CI 95% vì bảng không có sai số chuẩn.
- Rotation: vẽ bốn ước lượng và percentile 95% tại median rotation (`w=0,5`),
  không giả lập hai trọng số còn lại của hình gốc.
- RV: vẽ số so sánh tốt hơn/kém hơn sau BH từ bảng benchmark. Đây là biểu đồ
  tổng hợp, không phải đường QLIKE tích lũy đang thiếu chuỗi nguồn.

Mỗi hình ghi rõ phạm vi đó ngay dưới biểu đồ. Giá trị dùng đúng các chữ số
đã công bố trong bảng; nội dung và bảng số liệu gốc giữ nguyên. Các liên kết
đến artifact không có trong checkout được ghi “cần bộ đầy đủ”.

Báo cáo gốc giữ nguyên bytes; `report_view.html` là bản trình bày riêng.
Không bổ sung dữ liệu giả, không sửa model hoặc giao thức OOS.

Tạo lại bản đọc bằng Python chuẩn, không cần cài thư viện nghiên cứu:

```powershell
py tools/build_readable_evidence_report.py
py tools/build_readable_evidence_report.py --standalone bao_cao_hien_thi.html
```
