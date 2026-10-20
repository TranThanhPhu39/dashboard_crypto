**Tạo server Oracle Always Free để chuẩn bị chuyển worker Topic 9**

Hướng dẫn kiểm tra ngày 20/10/2026. Dashboard đang ở GitHub Pages. Worker Windows tiếp tục chạy cho đến khi máy Oracle vượt qua kiểm tra và được bàn giao; tạo được máy Oracle chưa đồng nghĩa pipeline Python đã được chuyển.

**1. Đăng ký tài khoản**

Vào https://www.oracle.com/cloud/free/ và chọn đăng ký Free Tier. Điền thông tin và thực hiện xác minh theo giao diện; Oracle có thể yêu cầu thẻ tín dụng/ghi nợ để xác minh. Giữ thông tin thanh toán và khóa riêng tại tài khoản/máy của bạn. [Hướng dẫn đăng ký của Oracle](https://docs.oracle.com/en-us/iaas/Content/GSG/Tasks/signingup_topic-Sign_Up_for_Free_Oracle_Cloud_Promotion.htm).

Chọn home region sẽ dùng cho máy miễn phí. Singapore là một lựa chọn gần Việt Nam nếu có trong danh sách cho tài khoản; việc có region không bảo đảm còn suất A1. Home region không đổi được sau khi tạo tenancy, và compute Always Free phải nằm trong home region. [Free Tier FAQ](https://www.oracle.com/cloud/free/faq/), [tài nguyên Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

**2. Chuẩn bị SSH key trên Windows**

Mở PowerShell trên máy cá nhân. Các lệnh này tạo khóa riêng có tên dành cho project; nếu khóa đã tồn tại thì dùng lại, tránh ghi đè:

```powershell
$topic09Key = Join-Path $env:USERPROFILE '.ssh\topic09_oracle'
New-Item -ItemType Directory -Force (Split-Path $topic09Key) | Out-Null
if (-not (Test-Path -LiteralPath $topic09Key)) {
    ssh-keygen -t ed25519 -f $topic09Key -C 'topic09-oracle'
}
Get-Content -LiteralPath "$topic09Key.pub"
```

Đặt passphrase khi tạo khóa. Sao chép toàn bộ dòng public key bắt đầu bằng `ssh-ed25519` để dán lên Oracle. File không có đuôi `.pub` là private key, giữ tại máy cá nhân.

**3. Tạo instance**

Trong Oracle Console, chọn `Compute -> Instances -> Create instance`. Đặt tên `topic09-worker`. Chọn image và shape tương thích với nhau:

| Trường | Cấu hình đề xuất |
| --- | --- |
| Image | Ubuntu 24.04 LTS chính thức, bản ARM64/aarch64 tương thích A1 |
| Shape | `VM.Standard.A1.Flex` |
| OCPU | 2 |
| RAM | 12 GB |
| Boot volume | 50 GB, cấu hình hiệu năng mặc định được miễn phí |
| Số máy | 1 |
| SSH key | Dán public key ở bước 2 |

Tài liệu hiện tại nêu tổng định mức A1 cho tenancy Always Free tương đương 2 OCPU và RAM 12 GB; storage miễn phí tổng cộng 200 GB cho boot/block volumes trong home region. Đối chiếu quota của tài khoản và phần tính phí/nhãn miễn phí trong Console trước khi tạo. Các tài nguyên bổ sung hoặc cấu hình vượt quota có cách tính phí riêng. [Định mức Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

Đây là máy ARM64. Các dependencies và mô hình nghiên cứu sẽ được kiểm tra trên kiến trúc này trước khi bàn giao; thư mục `.research_deps` của Windows được giữ tại máy Windows.

**4. Cấu hình mạng**

Chọn VCN và public subnet có kết nối Internet; nếu chưa có mạng, dùng hướng dẫn tạo VCN có Internet của Oracle. Bật public IPv4 cho instance. Thêm ingress TCP cổng 22 từ IP công khai của máy bạn, ví dụ `YOUR_PUBLIC_IP/32`; giữ outbound cho tải packages và truy cập các nguồn dữ liệu.

Dashboard tiếp tục được phục vụ bởi GitHub Pages. Bước tạo worker hiện tại chỉ cần kết nối SSH tới máy Oracle. [Tạo instance](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm), [kết nối Linux](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm).

Kiểm tra cấu hình và định mức miễn phí rồi chọn `Create`. Sau khi trạng thái thành `Running`, ghi lại Public IPv4.

Nếu gặp `Out of host capacity`, có thể thử Availability Domain khác trong cùng home region hoặc chờ có capacity. Hết capacity là tình trạng tài nguyên của nhà cung cấp; không phải lỗi repository. [Oracle giải thích capacity](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

**5. Kết nối và lấy thông tin máy**

Tại PowerShell Windows, thay `YOUR_SERVER_IP` bằng địa chỉ vừa nhận:

```powershell
ssh -i "$env:USERPROFILE\.ssh\topic09_oracle" ubuntu@YOUR_SERVER_IP
```

Tài khoản mặc định của image Ubuntu là `ubuntu`. Đối chiếu fingerprint của máy đích trước khi chấp nhận kết nối lần đầu. [SSH trên Oracle](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm).

Sau khi vào terminal Linux, chạy:

```bash
uname -m
cat /etc/os-release
free -h
df -h
```

Với A1, `uname -m` dự kiến trả `aarch64`. Thông tin cần cung cấp để tiếp tục là IP, hệ điều hành, kiến trúc, RAM và kết quả SSH thành công. Không cần gửi mật khẩu, passphrase hoặc private key.

**6. Các bước bàn giao sau khi máy tồn tại**

1. Chuẩn bị adapter/worker Docker Linux và cài dependencies cho ARM64.
2. Chuyển bộ artifacts đầy đủ qua kênh riêng, đối chiếu manifests và giữ timestamps gốc của receipts/ledger.
3. Kiểm tra mô hình đã lưu và đầu vào đối chiếu; kiểm tra 17 nguồn từ mạng server.
4. Kiểm tra lịch, retry, khóa tiến trình, backup và cập nhật dashboard. Giữ nguyên protocol, cutoff và cổng chấm OOS.
5. Đến thời điểm bàn giao, dừng lịch Windows, chờ tác vụ hiện tại kết thúc và đồng bộ phần dữ liệu cuối.
6. Bật duy nhất worker chính thức trên server, theo dõi các chu kỳ thực tế, rồi xác nhận có thể tắt máy cá nhân.

Bộ `compose.yaml` hiện có chạy web snapshot; adapter worker Linux chưa được triển khai/kiểm thử trên máy thật. Lệnh chạy Docker web không thay thế bước bàn giao worker.

**7. Lưu dữ liệu lâu dài**

Oracle có thể thu hồi Always Free instances được đánh giá nhàn rỗi. Vì vậy receipts, dự báo và nhãn cần bản sao lưu ngoài máy worker, kèm kiểm tra khôi phục. [Chính sách idle instances](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).
