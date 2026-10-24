# Worker GitHub Actions và dashboard Pages

Dashboard: <https://tranthanhphu39.github.io/dashboard_crypto/dashboard/>.

Workflow: [Scheduled crypto worker and Pages](https://github.com/TranThanhPhu39/dashboard_crypto/actions/workflows/worker.yml).

## Bàn giao đã kiểm chứng ngày 21/10/2026

[Preflight](https://github.com/TranThanhPhu39/dashboard_crypto/actions/runs/39531412055) đạt 17 nguồn, 40 mô hình cho dự báo khớp và 820 quan sát API/web tương đương. [Lượt worker/deploy](https://github.com/TranThanhPhu39/dashboard_crypto/actions/runs/39532364758) và [monitor trên runner mới/deploy](https://github.com/TranThanhPhu39/dashboard_crypto/actions/runs/39532852477) thành công. Dashboard live đã kiểm tra desktop/mobile, bộ chọn, CSV, reset, hash artifact và metadata checkpoint; không có lỗi JavaScript. Hai task Windows đã được xác minh disabled. Có thể tắt máy cá nhân.

## Luồng chạy

`worker.yml` chạy pipeline mỗi giờ phút **15 UTC** và giám sát phút **45 UTC**. Việt Nam lệch UTC đúng 7 giờ nên phút trong giờ không đổi. `push/merge main` chạy pipeline với mã nguồn mới. Có thể dùng **Run workflow → run/monitor** để chạy thủ công. Lịch GitHub có thể trễ hoặc bỏ lượt khi tải cao; tất cả receipt, forecast và cutoff sử dụng đồng hồ thực của runner. Không tạo dự báo hồi tố.

[GitHub xác nhận lịch có thể trễ hoặc bị bỏ khi tải cao](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Trong [lượt monitor lỗi ngày 24/10/2026 lúc 21:09 giờ Việt Nam](https://github.com/TranThanhPhu39/dashboard_crypto/actions/runs/40101107753), lần pipeline thành công gần nhất đã cách hơn 150 phút, nên `missed_runs` chặn xuất bản mặc dù capture đủ 17/17 nguồn và không có lỗi pipeline. Bản sửa dưới đây thêm bước phục hồi trước khi kết luận lỗi, giữ nguyên ngưỡng giám sát.

Mỗi lượt khôi phục bootstrap và checkpoint gần nhất, xác minh hash, gọi engine đã khóa, lưu checkpoint mới rồi mới xuất bản Pages. Mô hình không được huấn luyện lại trên Actions. Capture mới theo quy tắc hiện có: sau 4 giờ hoặc khi nguồn lỗi, tối đa 3 lần thử cách nhau 60 giây. Giữ 17 nguồn, 40 deployment models, buffer, feature definitions, ngày kết thúc OOS **20/10/2027 UTC** và stop-after **23/10/2027 UTC** của thiết kế gốc.

`preflight` kiểm tra 40 mô hình bằng dự báo lịch sử đã lưu và thử collector thật ở namespace riêng. Nó không ghi forecast, không chấm skill, không nhận quyền sở hữu ledger và không deploy dashboard.

## Kết nối FRED/ALFRED chính thức

Kiểm tra thực tế ngày 21/10: đường web download cũ timeout/reset trên cả Ubuntu, Windows và macOS hosted runners, trong khi máy cá nhân truy cập được. Đường API `https://api.stlouisfed.org/fred/series/observations` truy cập được trên cả ba nền tảng. Worker dùng secret **`FRED_API_KEY`** do chủ repo tự tạo tại [FRED API keys](https://fredaccount.stlouisfed.org/apikeys) và lưu trong [Actions secrets](https://github.com/TranThanhPhu39/dashboard_crypto/settings/secrets/actions). Không đưa key vào Git hoặc chat.

Adapter `src/data/github_fred_api.py` giữ nguyên 13 lượt dữ liệu FRED/ALFRED trong tổng 17 nguồn, cùng series, cửa sổ 180 ngày, `units=lin`, và `realtime_start=realtime_end` đúng từng information-day vintage. Raw JSON nhận từ API được archive nguyên bytes, không chứa khóa. CSV/ZIP trong thư mục `normalized/` là **view đã chuẩn hóa**, được ghi rõ vai trò; không gọi chúng là response web nguyên bản. Manifest liên kết raw hash, view hash, tham số công khai, thời điểm nhận/thời điểm view sẵn sàng và code snapshot của adapter. Trước khi đọc feature, raw/view được đối chiếu nội dung, không chỉ kiểm tra hash. Nguồn fit/feature/parser đã khóa không sửa.

Monitor kiểm tra trạng thái và render artifact đã có. Từ bản sửa 24/10/2026, khi lần pipeline trước đã thành công nhưng quá ngưỡng 150 phút và chỉ còn cảnh báo `missed_runs` cùng cảnh báo receipt, monitor gọi một lượt pipeline bình thường để phục hồi rồi kiểm tra health lại. Lượt phục hồi dùng thời gian thực, transport FRED/API và cơ chế khóa/retry hiện có; chỉ thu capture mới khi quy tắc 4 giờ/nguồn lỗi yêu cầu. Nó không tạo forecast hồi tố hoặc sửa dự báo đã commit. Cảnh báo receipt/cutoff vẫn được giữ; nếu phục hồi không thành công hoặc lỗi health còn tồn tại, workflow vẫn báo lỗi. Trạng thái `running`, lỗi pipeline thực sự và lỗi scheduler không bị monitor ghi đè. Audit phục hồi nằm ở `outputs/automation_20261020/monitor_recovery.json`, operation status và Actions summary. Monitor khi pipeline chưa quá hạn vẫn chỉ đọc trạng thái.

Preflight còn đối chiếu API với các web vintage đã archive nếu có cùng ngày, và đối chiếu VIX trên phần ngày giao nhau. Đây là kiểm tra tương đương đầu vào khi chuyển host, không phải đánh giá forecast skill. Windows giữ collector cũ khi không có cờ transport GitHub; lịch sử và receipt cũ không bị chuyển đổi hoặc ghi đè.

Lượt bàn giao đầu tiên thu thêm một capture API thật nếu checkpoint vẫn trỏ tới web collector cũ. Sau đó giữ nhịp refresh 4 giờ/nguồn lỗi hiện có. Capture cũ không bị thay; selector vẫn chọn input đủ nội dung sớm nhất trong cutoff ban đầu. Preflight thành công ngày 21/10/2026: 17/17 nguồn, 40 model predictions tương đương và 820 observations đối chiếu API/web đạt (6 series vintage 19/10 và phần VIX giao nhau).

## Dữ liệu và trạng thái bền vững

- **GitHub Releases:** bootstrap và các gói thay đổi được mã hóa AES-256-GCM bằng khóa 32 byte. Mỗi phần dưới 48 MiB plaintext, có SHA-256 cho ciphertext, archive và từng file. Release trạng thái tách theo ngày để tránh giới hạn số asset trên một release.
- **Nhánh `worker-state`:** con trỏ generation/catalog mã hóa. Commit chỉ tiến lên khi API xác nhận đúng SHA trước đó; host giữ state cũ không được ghi đè host mới. Lịch sử Git lưu các con trỏ trước; không force-push hay xóa nhánh này.
- **Secret `TOPIC09_STATE_KEY`:** khóa giải mã trong Actions. Không nằm trong Git, Pages, log hoặc asset plaintext. Bản dự phòng trên máy Windows dùng DPAPI trong `.verification/actions-worker/state-key.dpapi`, gắn với tài khoản Windows hiện tại.
- **Cache Actions:** chỉ lưu ciphertext để tăng tốc. Mất cache vẫn khôi phục từ Releases và nhánh state; cache/artifact có hạn lưu không phải bản gốc của ledger.
- **Pages:** đúng năm file: `index.html`, `dashboard/index.html`, `build_info.json`, `dashboard/status.json` và `dashboard/replay-<hash>.bin`. HTML web nén chương trình/dữ liệu khởi tạo; file replay là dữ liệu hiển thị đã có trong HTML cũ, chỉ tải khi mở Dự báo. Validator giải nén và khôi phục đúng chương trình/dữ liệu gốc, kiểm tra hash và allowlist từng file. Bản `dashboard/index.html` trong repository vẫn tự chứa để mở offline. Không có raw data, model, ledger, report hoặc health chi tiết trên website.

`build_info.json` cho biết source commit, generation, state commit, catalog hash và link lần chạy. Snapshot mới chỉ được phát hành sau khi checkpoint bền vững đã commit và các kiểm tra nguồn/giao diện đạt. Khi lỗi collector không được phân loại là cảnh báo nguồn bên ngoài, các receipt thu được vẫn được lưu nếu kiểm tra tính toàn vẹn cho phép; Pages giữ bản thành công trước đó và workflow báo thất bại.

**Bảo trì nguồn dữ liệu:** FRED có thể trả HTML `Site Maintenance` với HTTP 200 thay vì JSON (đã ghi nhận trong các capture 21–22/10/2026). Transport giữ nguyên raw bytes, gắn `PROVIDER_MAINTENANCE`, không tạo feature từ HTML. Chỉ khi toàn bộ nguồn thất bại đều có phản hồi bảo trì FRED đã xác minh hash thì pipeline chuyển sang `deferred_source_maintenance`: giữ nguyên lần thu đủ dữ liệu thành công cuối, forecast đã commit và cutoff; thử lại ở lượt lịch tiếp theo. Health vẫn `attention`, số nguồn thực vẫn hiển thị (ví dụ 4/17), Actions có warning và Step Summary rõ ràng. Dashboard được cập nhật trạng thái sau kiểm chứng và lưu checkpoint, không bị kẹt ở bản cũ chỉ vì nguồn bảo trì.

Monitor phân biệt cảnh báo bảo trì/readiness với lỗi code. Lỗi scheduler, integrity, model/protocol, JSON/schema không phải bảo trì hoặc lỗi subprocess vẫn làm workflow fail. Không nới cutoff, tạo forecast hồi tố, thay dữ liệu nguồn, đổi vintage hoặc ghi đè forecast để xử lý lỗi này. `outputs/automation_20261020/operation_status.json` lưu phân loại; log Actions hiển thị summary nguồn và các dòng lỗi con sau khi loại secret.

Repo công khai nên ciphertext có thể được tải công khai. Người có quyền sửa workflow trên `main` có thể sử dụng secret; chỉ cấp quyền ghi cho người tin cậy. Pull request không chạy worker hoặc nhận state key. Workflow PR chỉ kiểm tra dashboard snapshot bằng quyền đọc.

## Bàn giao từ Windows

1. Chạy `preflight` thành công trên Ubuntu, gồm đầy đủ 17 nguồn và 40 mô hình tương đương.
2. Tạm dừng hai task Windows bằng lệnh dưới; không kết thúc cưỡng bức collector đang chạy.
3. Đợi các OS lock được nhả rồi chạy `handoff-state`: chuyển mọi receipt/attempt/forecast mới kể từ bootstrap thành checkpoint cuối của Windows.
4. Bật repository variable `TOPIC09_WORKER_ENABLED=true`, chạy `run`, kiểm tra checkpoint, Pages deploy và metadata trên website.
5. Kiểm tra thêm `monitor` từ một runner mới để xác minh khôi phục state qua lượt chạy khác.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/manage_topic09_automation.ps1 -Action Pause
py -3.11 tools/setup_github_worker.py handoff-state
py -3.11 tools/setup_github_worker.py enable
py -3.11 tools/setup_github_worker.py run
```

Các bước thiết lập dùng Git Credential Manager đã đăng nhập chủ repo; credential chỉ ở bộ nhớ. Không đưa token/mật khẩu vào lệnh hoặc file Git. Khởi tạo bootstrap và tạo secret cần sự đồng ý riêng của chủ dữ liệu; không chạy `initialize` để thay bootstrap hiện đang vận hành.

Sau bàn giao, máy cá nhân có thể tắt. Bản data/model tại máy cá nhân giữ lại làm bản dự phòng tại thời điểm bàn giao; ledger mới tích lũy trên GitHub. Không bật lại Windows để chạy từ bản cũ: phải tắt worker GitHub, đợi job đang chạy kết thúc, khôi phục checkpoint mới nhất, rồi mới `Resume` Windows. Chỉ có một host được phép ghi ledger.

Workspace hiện có thể đồng bộ checkpoint GitHub thành bản **chỉ đọc** bằng:

```powershell
py -3.11 -m pip install --target .verification/worker-deps -r requirements-worker-admin.txt
py -3.11 tools/setup_github_worker.py sync-state
py -3.11 run_release.py validate
```

`sync-state` kiểm tra hai task Windows disabled, bảo toàn mọi evidence bất biến, rồi chỉ khôi phục overlay đã commit trên GitHub. Không ghi ngược state lên server và không tải lại bootstrap hơn 1 GB khi full base cục bộ đã có. Cấu hình sở hữu Windows được giữ tại `outputs/automation_20261020/installation_windows_before_github.json`; metadata canonical phản ánh host GitHub. `Status/Pause` Windows ghi riêng `scheduler_status_windows.json`. Các entry point worker cục bộ bị chặn khi GitHub đang là chủ ledger; `build/validate` vẫn dùng được. Chuyển quyền về Windows phải là một lần bàn giao riêng từ checkpoint mới nhất, không chỉ bật lại task.

## Theo dõi và cập nhật code

Mở **Actions → Scheduled crypto worker and Pages**: kiểm tra thời gian, loại `run/monitor/preflight`, Step Summary và bước deploy. Job thành công có thể kèm warning bảo trì/readiness; chỉ trạng thái `succeeded` cùng capture 17/17 mới xác nhận lượt thu đủ nguồn. Bật thông báo Actions trong tài khoản GitHub nếu muốn nhận thông báo lỗi; hệ thống không thiết lập kênh gửi tin cho người khác.

Người có quyền ghi có thể push vào `main`; cộng tác viên dùng PR rồi merge. Không thay dữ liệu/model/protocol hoặc code khoa học đã khóa để làm workflow xanh. Thay đổi thiết kế nghiên cứu cần version/bootstrap và đánh giá riêng. Snapshot HTML ở nhánh `main` là snapshot của source checkout; Pages lấy bản runtime mới hơn, có provenance trong `build_info.json`.

Tạm dừng worker: **Settings → Secrets and variables → Actions → Variables → `TOPIC09_WORKER_ENABLED=false`**. Lượt đang chạy không bị giết; kiểm tra Actions trước khi chuyển host. Xóa secret, release asset hoặc nhánh state làm mất khả năng khôi phục; worker sẽ dừng thay vì chạy với ledger rỗng.

GitHub có thể tự tắt lịch của repo công khai sau 60 ngày không có hoạt động. Cần theo dõi workflow đang `active`; lịch chạy không có SLA. Chu kỳ heartbeat vận hành trên `main` giữ bằng chứng hoạt động định kỳ, không sửa khoa học hoặc kết quả.

Giới hạn nguồn: [schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas). Standard hosted runners cho repo công khai được miễn phí compute; cache và artifact có quota riêng. Không dùng larger runner hoặc tăng quota trả phí.

## Mã nguồn vận hành

`tools/github_worker_store.py`: mã hóa, kiểm tra đường dẫn/hash, pack, khôi phục, catalog và compare-and-swap. `tools/run_github_worker.py`: adapter Ubuntu, shim `curl.exe` trỏ tới `curl` Linux, kiểm tra mô hình và gọi engine nguyên bản. `src/github_scheduler.py`: xác minh workflow đang active để hiển thị đúng host. `requirements-worker.txt`: phiên bản inference khớp với model đã serialize. Các nguồn fit/features/collector đã khóa không sửa.
