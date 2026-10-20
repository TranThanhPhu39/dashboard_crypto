**Hướng dẫn GitHub và server cho Topic 9**

Ngày kiểm tra: 20/10/2026. Đây là hướng dẫn triển khai dự kiến, chưa phải biên bản xác nhận hệ thống Linux đã triển khai. Tác vụ Windows hiện tại tiếp tục là nơi vận hành chính cho đến khi hoàn tất chuyển giao.

**1. Người khác sửa trên GitHub thì có tự cập nhật không?**

Có thể cấu hình như vậy. Một thay đổi phải được đưa vào đúng repository và nhánh triển khai, vượt qua kiểm tra, rồi workflow deploy chạy thành công thì server mới dùng phiên bản mới. Chỉ push code lên GitHub chưa tự tạo cơ chế này.

| Hành động | Ảnh hưởng đến server theo thiết kế đề xuất |
| --- | --- |
| Người lạ xem repo public | Không thay đổi code |
| Người khác sửa fork của họ | Không thay đổi server của bạn |
| Thành viên push nhánh làm việc, mở pull request (PR) | Chạy kiểm tra; chờ merge |
| PR được merge vào `main` | Tự cập nhật dashboard và phần vận hành được phép, nếu deploy thành công |
| Thay đổi mô hình, features hoặc giao thức OOS | Đăng ký phiên bản nghiên cứu mới trước khi triển khai worker tương ứng |
| Server thu được dữ liệu mới theo lịch | Cập nhật kết quả và trang công khai, không cần commit Git |
| Bạn mở lại IDE sau khi người khác merge | Máy bạn cần fetch/pull để nhận code mới |

Repo public không đồng nghĩa mọi người được quyền push. Với repo cá nhân, có thể mời collaborator; người được cấp quyền mới có thể push vào repo. Người ngoài có thể đóng góp qua fork và PR. [Quyền repository cá nhân](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository), [mời collaborator](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository).

**2. Hiểu hai luồng tự động riêng nhau**

Luồng cập nhật code:

```text
Thành viên sửa code -> push nhánh riêng -> PR -> kiểm tra
-> merge main -> build bản phát hành -> deploy -> kiểm tra sức khỏe
```

Luồng vận hành dữ liệu:

```text
Lịch server -> tải và lưu phản hồi nguồn -> kiểm tra PIT/timing
-> tạo dự báo đủ điều kiện -> cập nhật nhãn đến hạn
-> dựng lại report/dashboard -> công bố bản cập nhật
```

GitHub Actions phục vụ kiểm tra và triển khai. Lịch thu thập chính chạy trên server để không phụ thuộc vào một lần push. GitHub Pages có thể phục vụ dashboard tĩnh, nhưng không cung cấp tiến trình Python chạy thường trực. [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

**3. Chuẩn bị repository trước khi push**

Tạo repository trên GitHub, ví dụ `macro-crypto-topic09`. Private phù hợp khi nhóm đang chuẩn bị bài; public phù hợp khi đã xác định những mã nguồn, tài liệu và dữ liệu được chia sẻ.

Tách mã nguồn khỏi bộ dữ liệu vận hành:

| Nội dung | Cách quản lý đề xuất |
| --- | --- |
| `src`, entry points, `tools`, `tests`, cấu hình công khai, mã dashboard, README | Git |
| Mô hình và bằng chứng lịch sử cố định | Archive có manifest SHA-256, lưu ngoài lịch sử Git thông thường |
| Raw receipts, dự báo và nhãn thu mới, logs | Ổ bền vững trên server, có backup |
| API keys, SSH private keys, mật khẩu | Secrets trên GitHub/server |
| `.research_deps`, virtualenv, cache, bản preview tạm | Cài lại theo môi trường đích |

Chuẩn bị `.gitignore` cho `.env`, private keys, cache, dependency cục bộ và dữ liệu lớn trước khi stage. Có thể dùng LFS hoặc kho artifact cho file lớn; GitHub chặn file thông thường lớn hơn 100 MiB. [Giới hạn file GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

Không áp dụng chuẩn hóa xuống dòng hàng loạt lên bằng chứng đã khóa. Repo đang kiểm tra SHA-256 theo bytes; đổi CRLF/LF cũng làm hash thay đổi. Giữ nguyên bytes của files đã bảo vệ, kiểm tra lại sau clone và giải nén. Quy tắc LF cho scripts Linux mới có thể khai báo riêng. [Git và line endings](https://docs.github.com/en/get-started/git-basics/configuring-git-to-handle-line-endings).

Nếu dùng CLI để xuất bản lần đầu, thực hiện trong một bản sao dành cho xuất bản đã chuẩn bị ignore và kiểm tra dữ liệu chia sẻ. Các lệnh sau dành cho bản sao chưa có Git; nếu đã có repository thì dùng nhánh và remote hiện có:

```powershell
git init
git config core.autocrlf false
git add .
git status --short
```

Đọc danh sách stage, xác nhận secrets và dữ liệu lớn không nằm trong đó, rồi tiếp tục:

```powershell
git commit -m "Publish Topic 9 source and deployment documentation"
git branch -M main
git remote add origin https://github.com/OWNER/macro-crypto-topic09.git
git push -u origin main
```

Thay `OWNER` bằng tài khoản hoặc tổ chức thực tế. Commit mã nguồn không thay thế việc chuyển bộ bằng chứng đầy đủ sang server. Các ZIP có chữ `supplement` trong workspace là gói bổ sung, không phải bản cài độc lập.

**4. Thiết lập cách làm việc cho nhóm**

Trong repository, mở `Settings` và mục quản lý collaborators/access, mời tài khoản GitHub của thành viên. Tại phần bảo vệ nhánh/rules, cấu hình `main` yêu cầu PR và kiểm tra thành công trước khi merge. Nếu có người review, đặt ít nhất một approval và áp dụng quy tắc cho cả người có quyền bypass khi phù hợp. Khả năng bảo vệ nhánh private phụ thuộc gói GitHub; repo public trên GitHub Free có hỗ trợ protected branches. [Bảo vệ nhánh](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

Ví dụ một thành viên sửa dashboard:

```bash
git clone https://github.com/OWNER/macro-crypto-topic09.git
cd macro-crypto-topic09
git switch -c fix/dashboard-labels
# Sua file, chay kiem tra, sau do:
git add dashboard/
git commit -m "Improve dashboard labels"
git push -u origin fix/dashboard-labels
```

Sau đó mở PR trên GitHub, kiểm tra và merge. Thành viên đã clone trước đó có thể cập nhật `main` bằng `git pull --ff-only` sau khi xử lý các thay đổi cục bộ của mình. Bản clone trên máy cá nhân không tự đồng bộ chỉ vì server đã deploy.

**5. Chuẩn bị VPS**

Chọn Linux x86-64, ví dụ Ubuntu 24.04 LTS, có ổ bền vững và snapshot/backup. Đây là lựa chọn môi trường triển khai; dung lượng RAM, CPU và đĩa cần xác định bằng lần chạy thử với bộ artifact thực tế. Trước mắt đo workload vận hành thu thập/suy luận/dựng trang; một lần tái huấn luyện toàn bộ có nhu cầu khác.

Chuẩn bị IP, SSH key, tài khoản triển khai, và tên miền nếu cần đường dẫn dễ chia sẻ. Kết nối từ PowerShell:

```powershell
ssh YOUR_USER@SERVER_IP
```

Trên VPS, cài Docker Engine và Compose theo hướng dẫn chính thức cho Ubuntu. Docker giúp đóng gói môi trường Python đã kiểm thử; không mang `.research_deps` của Windows sang Linux. [Cài Docker trên Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

Tổ chức lưu trữ đề xuất:

```text
/srv/topic09/
  releases/<commit-sha>/    Ma/anh chuong trinh theo tung lan deploy
  shared/                  Data, models, receipts, forecasts, labels, logs
  public/                  Chi cac tep dashboard/report duoc cong bo
  backups/                 Ban sao cuc bo; can them ban sao ngoai VPS
```

Phần tích hợp phải ánh xạ `shared` vào đúng các đường dẫn tương đối mà pipeline đang sử dụng. Bản repo hiện tại chưa có lớp ánh xạ này. Cài hệ điều hành/môi trường riêng, giữ đồng hồ đồng bộ, ghi timestamps nghiên cứu theo UTC. Web server chỉ phục vụ `public`, không phục vụ nguyên thư mục dự án chứa raw responses, models và secrets.

**6. Hoàn thiện lớp Linux trước lần deploy đầu**

Repo đã có `compose.yaml` cho web, cấu hình Nginx và script xuất dashboard theo danh sách file công khai; xem [hướng dẫn VPS/Docker](VPS_LINUX_DOCKER.vi.md). Repo chưa có image/adapter worker Linux hoặc workflow GitHub Actions để deploy. `src/automation_runtime.py` đã có khóa tiến trình POSIX, nhưng vẫn gọi PowerShell để kiểm tra scheduler và gửi thông báo. Vì vậy chưa thể chỉ clone rồi chạy `run_automation.py run` trên Linux như bản Windows.

Những thành phần cần bổ sung và kiểm thử:

| Thành phần dự kiến | Nhiệm vụ |
| --- | --- |
| Dockerfile + lock dependencies cho Linux | Python 3.11, nạp models hiện có, kiểm tra tương thích dự đoán |
| Adapter chạy/giám sát Linux | Thay phần Task Scheduler/PowerShell; giữ nguyên engine nghiên cứu |
| Hai `systemd service/timer` | Pipeline phút 15 và monitor phút 45 mỗi giờ |
| Cơ chế lưu trữ dùng chung | Giữ dữ liệu và ledger qua mọi lần cập nhật code |
| Bộ xuất trang công khai | Sao chép đúng tài nguyên, kiểm tra liên kết, công bố nguyên một bản hoàn chỉnh |
| Script deploy/rollback | Chọn commit, kiểm tra, chuyển phiên bản, lưu biên bản |
| Workflow CI/deploy | Kết nối GitHub với quy trình trên server |

Tên file cụ thể của adapter và deploy scripts sẽ được chốt khi triển khai; bảng này không khẳng định chúng đã tồn tại.

Môi trường hiện ghi nhận Python 3.11.9 và các phiên bản nghiên cứu trong `requirements-research.txt`, `outputs/research/evidence_20261019/environment.json`. Cài dependencies Linux vào image mới, ghi lại phiên bản thực tế và kiểm tra mô hình đã lưu. Không tự nâng phiên bản thư viện khi rebuild nếu chưa đánh giá ảnh hưởng.

Các lệnh kiểm tra sẵn có, chạy trong bản sao/môi trường thử có đủ bộ artifact:

```bash
python tests/validate_automation.py
python run_release.py validate
node tests/validate_release_dashboard.cjs
```

Một số kiểm tra hiện dành riêng Windows, đặc biệt kiểm tra cài Task Scheduler. Bản server cần kiểm tra cài đặt systemd tương ứng; không sử dụng biên bản Windows làm bằng chứng server đã đạt. CI clone mã nguồn đơn thuần cũng chưa đủ cho các kiểm tra đòi bộ bằng chứng đầy đủ.

Systemd hỗ trợ lịch `OnCalendar` và `Persistent=true` để kích hoạt tác vụ bị lỡ sau khi timer hoạt động trở lại. Trong adapter, dự báo quá hạn vẫn phải bị từ chối; chạy bù tác vụ không được tạo dự báo quá khứ. Cần giữ cả giới hạn thời gian kết thúc của giao thức và lịch vận hành hiện có. [Systemd timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).

**7. Kết nối GitHub với server để tự cập nhật**

Tạo workflow kiểm tra PR và workflow deploy nhánh `main` dưới `.github/workflows/`. Quy trình dự kiến:

```text
PR -> kiem tra trong moi truong tach biet
Merge main -> lay dung commit SHA -> build artifact/image
-> xac minh hash va kha nang tuong thich
-> lay khoa deploy, cho worker dang chay ket thuc
-> chuyen phien ban -> smoke test -> ghi release SHA va thoi gian
```

Tại `Settings -> Environments`, tạo môi trường `production`, giới hạn nhánh triển khai. Tại secrets của môi trường, đặt các thông tin kết nối như host, user, deploy key và host key đã xác minh. API keys phục vụ pipeline đặt trên server hoặc secrets đúng phạm vi. GitHub hỗ trợ environment để giới hạn nhánh và quyền truy cập secrets. [Deployment environments](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments), [GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

Workflow cần tuần tự hóa deploy để hai lần merge không chuyển phiên bản đồng thời. PR không được cấp credentials production. Deploy key trên server cần đúng quyền phục vụ triển khai. Phần nạp bộ artifact dùng để test cũng phải được giới hạn theo độ tin cậy của PR.

Sau một lần deploy thành công, các lần merge đủ điều kiện tiếp theo tự đi qua quy trình này. Nếu build/kiểm tra thất bại, server tiếp tục phiên bản đang chạy. Nếu lỗi sau khi chuyển phiên bản, rollback code bằng release đã lưu; giữ nguyên receipts và ledger đã thu, không phục hồi cả thư mục dữ liệu về quá khứ.

**8. Cập nhật code mà vẫn giữ đúng thí nghiệm OOS**

| Thay đổi | Cách triển khai |
| --- | --- |
| Nhãn UI, bố cục, biểu đồ | Tự deploy sau kiểm tra dashboard |
| Retry, logs, giám sát, hạ tầng | Kiểm tra không đổi inputs/dự báo/gate, ghi phiên bản rồi deploy |
| Cách thu nguồn hoặc định nghĩa availability | Đánh giá tác động PIT, lưu snapshot và phiên bản adapter |
| Features, lag, xử lý vintage, mô hình, tuning, cửa sổ đánh giá | Tạo giao thức/phiên bản thí nghiệm mới; giữ nguyên kết quả và ledger cũ |

Dashboard có thể theo `main`, còn worker phải dùng đúng phiên bản đã đăng ký cho thí nghiệm. Sửa lỗi vận hành vẫn thực hiện được khi có kiểm tra phù hợp; không cần khóa mọi phát triển cho tới khi OOS kết thúc. Điều quan trọng là ghi nhận chính xác phiên bản và không trộn dự báo của các thiết kế khác nhau thành một thí nghiệm cố định.

Biên bản deploy tối thiểu ghi commit SHA, image digest nếu có, hash mô hình/giao thức, thời gian UTC, kết quả kiểm tra và thời điểm tiếp quản worker. Deploy không tự mở sớm cổng chấm OOS.

**9. Chuyển giao từ máy Windows sang server**

Thực hiện trước một cửa sổ thu thập quan trọng, có thời gian xử lý sự cố:

1. Chạy thử trên bản sao cách ly, dùng fixtures hoặc dữ liệu lịch sử; không cho bản thử ghi ledger production.
2. Xác nhận đủ bộ bằng chứng lịch sử, hashes khớp, mô hình nạp được, và dự đoán trên cùng đầu vào tương đương trong sai số cho phép đã xác định.
3. Kiểm tra 17 nguồn từ mạng/IP server. HTTP thành công chưa đủ; nội dung phải vượt qua kiểm tra độ đầy đủ/timing.
4. Kiểm tra lịch, log, retry, khóa tiến trình, cảnh báo, backup, restart và giao diện web.
5. Đến thời điểm bàn giao, dừng lịch worker Windows, chờ tác vụ đang chạy kết thúc, rồi chép phần dữ liệu mới cuối cùng. Giữ nguyên bytes, tên file và timestamps receipts gốc; ghi riêng thời gian chuyển.
6. Xác minh manifest/ledger trên server, bật duy nhất worker production ở server. Khóa file cục bộ không ngăn được hai máy cùng ghi; cần chuyển quyền vận hành rõ ràng.
7. Theo dõi ít nhất hai chu kỳ scheduler và một lượt thu mới. Nếu nguồn/đầu vào chưa đủ điều kiện thì ghi skip đúng quy tắc, không tính đó là dự báo thành công.
8. Xác nhận rollback và backup. Nếu quay lại Windows, dừng worker server trước và đồng bộ toàn bộ ledger mới về; giữ nguyên records đã ghi.

Máy cá nhân sau đó có thể tắt. Server tiếp tục chạy và cập nhật dashboard theo lịch, miễn dịch vụ và mạng server hoạt động.

**10. Kiểm tra sau mỗi lần cập nhật**

- Trang hiển thị đúng commit/release và thời gian cập nhật dữ liệu.
- Pipeline và monitor có lần chạy mới, giờ thành công gần nhất đúng thực tế.
- Các sources và inputs được đánh giá riêng; không ép phải có dự báo mỗi ngày nghỉ thị trường.
- Protocol/model hashes đúng phiên bản thí nghiệm; không có ghi đè dự báo/receipts cũ.
- Chỉ một worker ghi ledger; deploy không làm mất data/models/logs.
- Bộ lọc, biểu đồ, khoảng tin cậy, CSV export và liên kết report hoạt động.
- Bản công khai không chứa secrets hoặc toàn bộ thư mục raw/models.
- Có thể khôi phục bản code trước mà giữ nguyên dữ liệu đã thu.

Thông tin cần chốt để triển khai thật: URL repository, VPS/IP và tài khoản SSH được cấp quyền, môi trường/tài khoản cung cấp server, tên miền nếu dùng, nơi backup và kênh nhận cảnh báo. Không gửi private key hoặc mật khẩu qua nội dung repo/chat.
