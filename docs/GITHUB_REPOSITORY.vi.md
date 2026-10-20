**Phạm vi repository GitHub**

Repository: https://github.com/TranThanhPhu39/dashboard_crypto

Repository này chứa mã nguồn, cấu hình công khai, tests, notebooks, tài liệu, dashboard có dữ liệu hiển thị nhúng sẵn và một số báo cáo kết xuất. Các trang HTML là snapshot ở thời điểm commit; lần push không cài lịch hoặc vận hành pipeline trên GitHub.

Mở `dashboard/index.html` sau khi clone để xem bản dashboard đi kèm. Các liên kết đến bộ bằng chứng chi tiết trong README/báo cáo có thể yêu cầu khôi phục artifact đầy đủ.

**Tái lập nghiên cứu và vận hành**

Clone GitHub chưa phải bản nghiên cứu độc lập hoàn chỉnh. Raw data, models, receipts, ledger OOS, các ZIP nghiên cứu và outputs đầy đủ được giữ ngoài lịch sử Git thông thường. Cần chuyển bộ artifact đầy đủ, manifests và dependencies vào đúng vị trí trước khi chạy các lệnh build/validate/operate yêu cầu bằng chứng. Các gói `supplement` bổ sung cho bản gốc, không thay thế toàn bộ bộ nghiên cứu.

Giữ nguyên bytes của các artifacts đã khóa SHA-256, đặc biệt source/protocol/model inventories và receipts. `.gitattributes` giữ nguyên xuống dòng của các file hiện có. Không tái tạo dữ liệu quá khứ hoặc đổi timestamp tiếp nhận thành thời điểm deploy.

Không chép `.research_deps` từ Windows sang Linux; cài môi trường cho hệ điều hành đích và kiểm tra tương thích models. Adapter hiện tại dùng Windows Task Scheduler/PowerShell; bản Linux cần hoàn thiện adapter và kiểm thử trước khi tiếp quản worker.

**Làm việc nhóm**

Thành viên sửa trên nhánh riêng, tạo pull request, kiểm tra rồi merge `main`. Server chỉ tự cập nhật khi đã cài workflow CI/CD. Mỗi bản clone cá nhân vẫn cần fetch/pull để nhận thay đổi. Server cần giữ một worker ghi ledger chính thức; dữ liệu thu mới không tự được commit về GitHub.

Hướng dẫn: [GitHub và server](DEPLOYMENT_GITHUB_SERVER.vi.md).

Bản web có `compose.yaml`, cấu hình Nginx và exporter danh sách file công khai. Làm theo [VPS Linux/Docker](VPS_LINUX_DOCKER.vi.md) để chạy dashboard snapshot; worker Python và CI/CD cần cấu hình/kiểm thử riêng.

**Các thành phần được giữ riêng**

- `data/`, `models/`: dữ liệu và mô hình nghiên cứu/vận hành.
- Phần lớn `outputs/`: artifacts số liệu, archive bằng chứng, logs, trạng thái máy.
- Các ZIP tại thư mục gốc: các gói nghiên cứu/bổ sung có dung lượng lớn.
- `.research_deps/`, virtualenv, cache, preview: thành phần cục bộ.
- `.env`, private keys: credentials, không đưa lên repository.

Các manifests JSON được đưa lên Git để mô tả bộ artifacts đã có. Việc một file được bỏ khỏi Git không thay đổi yêu cầu xác minh hoặc hash kỳ vọng của nghiên cứu.
