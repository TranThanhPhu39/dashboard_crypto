# Orbit 2 — Hướng dẫn sử dụng và kiểm tra vận hành

## Áp dụng bản mới

Giải nén gói vào thư mục gốc `dashboard_crypto`, gộp thư mục và thay thế những file giao diện/code trùng tên. Gói gồm cả giao diện Orbit ban đầu và các sửa đổi trải nghiệm lần này.

Trên Windows, nhấp đúp `MO_DASHBOARD.cmd`. Script mở đúng `dashboard/index.html` và tạo các đường dẫn chuyển tiếp đang thiếu ở báo cáo cũ, không cần Python. Các file dashboard lịch sử đã tồn tại không bị ghi đè. Có thể mở `START_DASHBOARD.html` hoặc `dashboard/index.html` trực tiếp bằng Chrome/Edge phiên bản mới.

Nếu muốn chạy localhost:

```powershell
py tools/repair_dashboard_entrypoints.py
py -m http.server 8000 --bind 127.0.0.1
```

Mở `http://localhost:8000/dashboard/`. Nhấn Ctrl + F5 nếu trình duyệt còn giữ bản cũ. File HTML xem thử độc lập không cần cài thư viện; mục phát lại dùng API giải nén tích hợp của Chrome/Edge mới.

## Thao tác và đọc hiểu

- **Tác động vĩ mô:** chọn tài sản, thay đổi kinh tế và thời hạn. Xem số ước lượng, khoảng tin cậy, rồi đọc đoạn giải thích ngay dưới biểu đồ. Có ba ví dụ mẫu trong khung hướng dẫn.
- **Kiểm tra dự báo:** dữ liệu lớn chỉ được giải nén khi mở mục này lần đầu, có trạng thái chờ và nút thử lại nếu lỗi. Các lần sau dùng dữ liệu đã nạp. Khoảng ngày tùy chọn thay đổi biểu đồ/CSV phát lại; không thay kỳ kiểm định đã chốt.
- **Tra thuật ngữ:** bấm khung tìm kiếm hoặc Ctrl + K. Tìm bằng tiếng Việt có/không dấu hoặc tên viết tắt. Mỗi mục có ví dụ và liên kết Google. Các nút `?` cạnh bộ lọc mở đúng phần giải nghĩa.
- **Dữ liệu & OOS:** xem riêng thời điểm chốt mẫu nghiên cứu, thời điểm worker thành công, dự báo/nhãn đã ghi và thời điểm đánh giá cố định. Nút kiểm tra chỉ đọc metadata công khai, không chạy collector hoặc model.

## Lỗi mở dashboard trong ảnh

Báo cáo `outputs/research/evidence_20261019/report.html` liên kết đến `dashboard.html` trong cùng thư mục. Bản clone công khai không chứa dashboard lịch sử đầy đủ ở vị trí đó, nên Chrome báo `ERR_FILE_NOT_FOUND`. Dashboard chính nằm tại `dashboard/index.html` ở gốc repo. Công cụ `repair_dashboard_entrypoints.py` tạo file chuyển tiếp nếu đường dẫn cũ đang thiếu, giữ nguyên những file lịch sử đã có và các hash nghiên cứu.

## Kết quả kiểm tra tự động hóa và OOS

Đã kiểm tra cấu hình nguồn, API công khai của GitHub Actions và bản Pages công khai trong phiên làm việc ngày 22/10/2026 (giờ Việt Nam):

- Workflow `worker.yml` đang `active`. Lịch cấu hình: pipeline phút 15, giám sát phút 45 mỗi giờ; lịch GitHub có thể trễ. Capture được làm mới sau 4 giờ hoặc khi nguồn lỗi, không phải tải toàn bộ dữ liệu mới mỗi lần người dùng mở trang.
- [Lượt chạy lịch 39614236105](https://github.com/TranThanhPhu39/dashboard_crypto/actions/runs/39614236105) hoàn tất thành công lúc **14:10:45 UTC ngày 21/10/2026** (21:10:45 cùng ngày tại Việt Nam). Các bước khôi phục runtime, replay historical OOS, vận hành, kiểm tra dashboard, lưu checkpoint và triển khai Pages đều thành công. Lượt trước [39611461460](https://github.com/TranThanhPhu39/dashboard_crypto/actions/runs/39611461460) cũng thành công.
- Bản Pages đọc được tạo lúc **14:09:55 UTC ngày 21/10/2026**; ghi lần pipeline thành công gần nhất **13:52:00 UTC**. Đây là bằng chứng tại các mốc đó, không phải xác nhận hệ thống đang khỏe ở mọi thời điểm về sau. UI mới cảnh báo nếu trạng thái quá 150 phút.
- Bản công khai đó có **0 tệp dự báo mới, 0 dòng dự báo và 0 tệp nhãn**; trạng thái `PENDING_FIXED_EVALUATION_WINDOW`. Chưa có kết quả kiểm chứng OOS tương lai. Mốc đánh giá theo giao thức là **20/10/2027 UTC**, không tự chuyển thành ngày nộp bài hoặc mở chấm sớm.
- Mẫu nghiên cứu/biểu đồ giữ mốc **15/10/2026**. Thu dữ liệu mới không tự huấn luyện lại mô hình, thay mẫu nghiên cứu đã khóa hoặc tạo dự báo hồi tố.
- Chưa đọc được các raw receipts/model riêng từ checkpoint mã hóa trong bản clone này. Vì vậy số nguồn thực sự nhận được của lần capture gần nhất không được suy đoán từ job thành công. Sau khi code mới được triển khai, exporter cung cấp `dashboard/status.json` với thời điểm capture và số nguồn từ manifest đã kiểm tra hash; chỉ công bố metadata an toàn.

## Phạm vi thay đổi và kiểm tra

Tăng cỡ chữ, thêm hướng dẫn/giải nghĩa, sửa điều hướng và đường mở, tách nạp dữ liệu dự báo lớn khỏi lần khởi động, tránh dựng lại rolling chart chỉ vì đổi horizon. Dữ liệu ước lượng, dự báo đã lưu, mô hình, feature, receipt cutoff và giao thức OOS không đổi. Metadata trạng thái là thông tin vận hành, không phải điểm đánh giá năng lực dự báo.

Các kiểm tra có thể chạy tại gốc repo:

```powershell
python -m unittest discover -s tests -p test_dashboard_experience.py
node tests/validate_experience.cjs
node tests/validate_release_dashboard.cjs
python tools/export_public_dashboard.py --dashboard-only
python tools/check_public_dashboard.py --dashboard-only
```

Các test vận hành dùng dữ liệu giả trong thư mục tạm, không chạy collector hoặc ghi ledger thật:

```powershell
python -m unittest discover -s tests -p test_github_worker.py
python -m unittest discover -s tests -p test_automation.py
```

Các thay đổi chưa được đẩy lên GitHub. Để website và worker dùng bản này, cần commit toàn bộ các file thay đổi trong gói, bao gồm `dashboard`, các module `src/dashboard_*.py`, các công cụ export/check/repair, tests và hai workflow `.github/workflows/pages.yml`, `.github/workflows/worker.yml`, rồi merge vào `main`. Không đưa `data`, `models`, secrets hoặc các file chuyển tiếp lịch sử do script tạo vào Git.
