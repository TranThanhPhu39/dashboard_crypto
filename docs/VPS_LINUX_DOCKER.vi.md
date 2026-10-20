**Đưa dashboard_crypto lên VPS Linux bằng Docker**

Bộ Compose trong repo chạy dashboard và các báo cáo snapshot qua Nginx. Worker Python thu thập dữ liệu/dự báo đang dùng Windows; bản web này chưa thay thế worker đó. Khi web chạy được, giữ lịch Windows hiện tại cho đến khi adapter Linux và chuyển giao receipts/ledger được kiểm chứng.

**1. Chọn VPS và đăng nhập**

Dùng Linux x86-64, ví dụ Ubuntu 24.04 LTS. Bản web tĩnh cần ít tài nguyên hơn worker Python; cấu hình worker sẽ đo bằng workload và artifacts thực tế. Chuẩn bị IP, tài khoản SSH, quyền sudo và SSH key. Có thể dùng IP trước, thêm tên miền/HTTPS sau.

Từ PowerShell trên máy cá nhân:

```powershell
ssh YOUR_USER@SERVER_IP
```

Thay hai giá trị bằng thông tin VPS. Các lệnh từ bước 2 trở đi chạy trong terminal Linux sau khi SSH thành công.

**2. Cài Docker Engine và Compose**

Cài Docker Engine từ apt repository chính thức, có gói Compose plugin. Hướng dẫn chính thức: [Docker Engine trên Ubuntu](https://docs.docker.com/engine/install/ubuntu/), [Compose plugin](https://docs.docker.com/compose/install/linux/).

Trên VPS sạch, có thể thực hiện chuỗi sau; nếu máy đã cài Docker hoặc có ứng dụng khác thì dùng phần kiểm tra trước và đối chiếu hướng dẫn chính thức trước khi đổi cài đặt:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' "$(dpkg --print-architecture)" "$VERSION_CODENAME" | sudo tee /etc/apt/sources.list.d/topic09-docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
sudo docker run --rm hello-world
```

Giữ `sudo docker` trong các bước dưới; không cần đổi quyền truy cập Docker của tài khoản để làm theo hướng dẫn.

**3. Clone mã nguồn và xuất bản web**

```bash
mkdir -p ~/topic09
cd ~/topic09
git clone https://github.com/TranThanhPhu39/dashboard_crypto.git
cd dashboard_crypto
python3 tools/export_public_dashboard.py
sudo docker compose config
sudo docker compose run --rm --no-deps web nginx -t
sudo docker compose up -d
sudo docker compose ps
```

Script xuất 11 file đã chọn và metadata vào `public/`. Nó không publish `.git`, source, raw data, models hoặc credentials. Không đặt file khác vào thư mục `public`; exporter từ chối file ngoài danh sách của nó. Không cần cài pandas hoặc các thư viện nghiên cứu để chạy bước xuất dashboard.

Mặc định Compose dùng cổng 80. Nếu cổng đã có ứng dụng khác sử dụng, tạo `.env` trong repo với `WEB_PORT=8080`, rồi chạy lại Compose. `.env` không được commit. Có thể đặt `WEB_BIND_ADDRESS=127.0.0.1` khi có reverse proxy HTTPS trên cùng VPS.

Image hiện được chỉ định tag `nginx:1.30.6-alpine`, có healthcheck, tự khởi động lại, logs có giới hạn và chỉ đọc thư mục public. [Nginx official image](https://hub.docker.com/_/nginx). Khi đưa vào vận hành lâu dài, ghi image digest đã kiểm tra vào biên bản triển khai.

**4. Mở cổng và kiểm tra từ máy cá nhân**

Trên control panel của nhà cung cấp VPS, cho phép TCP cổng web đang dùng; giữ quyền truy cập SSH. Với bản này cổng mặc định là 80. Đặt quy tắc ở firewall/security group của nhà cung cấp: Docker có thể xử lý published ports khác với kỳ vọng chỉ dựa trên UFW. [Lưu ý firewall của Docker](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations).

Mở trình duyệt:

```text
http://SERVER_IP/dashboard/
http://SERVER_IP/outputs/research/release_20261025/report.html
http://SERVER_IP/build_info.json
```

Nếu đổi cổng, thêm `:8080` sau IP. Kiểm tra bộ lọc shock, BTC/ETH, horizon, chế độ và tải CSV. Dashboard nhúng dữ liệu hiển thị; các liên kết tới artifacts chi tiết không nằm trong bộ snapshot vẫn cần bộ nghiên cứu đầy đủ.

Theo dõi trên VPS:

```bash
sudo docker compose ps
sudo docker compose logs --tail=100 web
curl -I http://127.0.0.1/dashboard/
```

Nếu dùng cổng khác, sửa địa chỉ curl tương ứng. Xem `public/build_info.json` để biết commit nguồn, hash file và thời điểm xuất snapshot. Trang health được kèm từ máy nghiên cứu, không phải chứng nhận worker đang chạy trên VPS.

**5. Cập nhật khi có code mới trên GitHub**

Với bản hiện tại, cập nhật thủ công trên VPS:

```bash
cd ~/topic09/dashboard_crypto
git pull --ff-only origin main
python3 tools/export_public_dashboard.py
sudo docker compose config
sudo docker compose up -d
sudo docker compose ps
```

Nếu cấu hình Nginx thay đổi, kiểm tra trước và restart để nạp lại:

```bash
sudo docker compose run --rm --no-deps web nginx -t
sudo docker compose restart web
```

Repo chưa có workflow CI/CD để chạy chuỗi này tự động. Khi đã có VPS, thiết lập workflow chỉ deploy `main` sau kiểm tra, dùng credentials đúng phạm vi, khóa deploy để tránh hai lượt đồng thời và giữ release trước để rollback. Hướng dẫn nhóm/quyền/CI-CD: [GitHub và server](DEPLOYMENT_GITHUB_SERVER.vi.md).

**6. Tên miền và HTTPS**

Trỏ bản ghi DNS của tên miền về IP VPS. Đặt reverse proxy HTTPS phía trước web; khi proxy ở host thì bind container vào `127.0.0.1` thay vì công khai cổng nội bộ. Kiểm tra chứng chỉ, redirect HTTP sang HTTPS và địa chỉ truy cập trước khi chia sẻ link lâu dài. Cấu hình cụ thể phụ thuộc tên miền và proxy đã chọn; Compose đi kèm hiện phục vụ HTTP.

**7. Chuyển worker Python tự động sang Linux**

Phần này cần triển khai và kiểm thử riêng sau bước web:

- Cài image Python phù hợp, dependencies và bộ artifacts đầy đủ; kiểm tra models đã lưu trên đầu vào đối chiếu.
- Adapter Linux thay thao tác Task Scheduler/PowerShell và khai báo trạng thái cài đặt thật.
- Lưu `data`, `models`, receipts, ledger, outputs/logs trên ổ bền vững; giữ protocol/model hashes và timestamps gốc.
- Lập lịch pipeline phút 15, monitor phút 45, giữ gate OOS, retry và quy tắc skip inputs thiếu.
- Xuất lại public snapshot sau một lần vận hành thành công; chỉ công bố các files được phép.
- Thử backup, phục hồi và restart trước khi dừng lịch Windows. Chỉ một worker được ghi ledger chính thức.

Không dùng `docker compose up -d` của bản web làm bằng chứng phần thu thập/dự báo đã chạy tự động. Sau khi adapter và chuyển giao đạt kiểm tra, VPS mới tiếp quản hoàn toàn và máy cá nhân có thể tắt.

**8. Trạng thái kiểm thử của bộ web**

Exporter được chạy và kiểm tra manifest đối chiếu bytes nguồn trên máy phát triển. Máy hiện tại chưa có Docker để kiểm thử Nginx/Compose thực tế; vì vậy các lệnh `compose config`, `nginx -t`, healthcheck và truy cập trình duyệt trên VPS là bước xác nhận bắt buộc trước khi công bố dịch vụ.
