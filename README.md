# Chủ đề 9: Global Financial Conditions và Crypto

Repository GitHub: [TranThanhPhu39/dashboard_crypto](https://github.com/TranThanhPhu39/dashboard_crypto). Bản clone chứa mã nguồn, dashboard nhúng dữ liệu hiển thị và một số báo cáo snapshot; raw data, models, ledger và bộ bằng chứng đầy đủ được chuyển riêng. Xem [phạm vi repository](docs/GITHUB_REPOSITORY.vi.md) và [hướng dẫn GitHub/server](docs/DEPLOYMENT_GITHUB_SERVER.vi.md) trước khi chạy pipeline trên máy mới. Lịch Windows trên máy nghiên cứu không được cài lại tự động khi clone.

Bộ dữ liệu nghiên cứu tải ngày **16/10/2026**, mẫu theo ngày UTC **01/01/2014–15/10/2026**. Chỉ dùng ngày đã kết thúc. Không kéo dài dữ liệu đến cuối năm 2026 khi chưa có quan sát. Mô hình và báo cáo được triển khai theo thiết kế đã thống nhất dưới đây.

## Bản tổng hợp nộp 25/10/2026 — entry point hiện tại

[Báo cáo tổng hợp](outputs/research/release_20261025/report.html) · [Markdown](outputs/research/release_20261025/report.md) · [Dashboard chính](dashboard/index.html) · [Source catalog](outputs/research/release_20261025/source_catalog.csv).

[ZIP bổ sung tự động hóa v5](topic09_release_20261025_automation_v5_supplement.zip) cần full base repo và các empirical supplements/dependencies hiện có, không standalone. [Gói vận hành v4](topic09_release_20261025_operations_v4_supplement.zip), [gói OOS v3](topic09_release_20261025_oos_v3_supplement.zip), [gói UI v2](topic09_release_20261025_ui_v2_supplement.zip) và các ZIP nghiên cứu cũ giữ nguyên. Trên máy khác phải chủ động cài lại lịch; gói không chứa mật khẩu và không tự đăng ký task khi giải nén.

Dashboard mở trực tiếp workspace **Truyền dẫn**: chọn shock, BTC/ETH, horizon 1–30 ngày và Full/Calm/Stress để xem response/CI, rolling beta và các giai đoạn lịch sử tương tự. Có nút **Tải CSV đường phản ứng** và **Đặt lại bộ lọc**. Các workspace khác gồm Dự báo rủi ro, FOMC, Phân vị & VAR, Phương pháp & nguồn. Thuyết minh học thuật nằm ở báo cáo và các mục mở khi cần; không chiếm luồng phân tích chính. Dataset đến 15/10/2026 được ghi ngay trên header.

Đã hợp nhất VAR/LP/quantile/rolling, FOMC identification checks, RV forecasting, PIT audit và nested backtest. Dashboard có đầy đủ bộ chọn shock/asset/horizon/regime, đồng thời hiển thị scenario/năm của nested, FOMC component và RV. Mỗi thiết kế giữ nhãn nguồn, timing, đơn vị và sample; không gộp USD/USDT hoặc STMT/component thành một shock.

Đã sửa xung đột preservation/status bằng adapter có allowlist exact paths. File trạng thái được cập nhật sau khi bytes gốc đã archive và khóa hash. Dữ liệu, raw response/manifest, model, protocol và fit/input locks không được miễn kiểm tra. Validator lịch sử xác minh bytes cũ từ archive đối với status/navigation; không đổi hash kỳ vọng hay bỏ qua mọi thay đổi. [Migration](outputs/research/release_20261025/preservation_migration.json), [kiểm chứng](outputs/research/release_20261025/preservation_validation.json). Code tính feature, label cutoff và fit đã khóa không sửa.

```powershell
py -3.11 run_release.py build
py -3.11 run_release.py validate
py -3.11 run_release.py validate-pit
node tests/validate_release_dashboard.cjs
node tests/preview_release.cjs
py -3.11 run_release.py package
```

`build/validate/all` chỉ render/kiểm chứng, không train. `validate-pit` replay artifacts và fit lại tám đại diện để kiểm chứng, không ghi đè model. Lịch Windows gọi `run_automation.py run`: collect/refresh capture → forecast/labels theo điều kiện thực → kiểm tra evaluation gate → làm mới và kiểm chứng báo cáo/dashboard. Có thể chạy thủ công bằng `py -3.11 run_release.py operate`. Lệnh `run_prospective.py run` cũ vẫn chỉ làm mới operational report. Actual-clock, cutoff và fixed evaluation gate giữ nguyên. Kết quả lịch sử vẫn exploratory; cài lịch không tự tạo bằng chứng untouched OOS.

Đã bổ sung tự động hóa theo yêu cầu ngày 20/10: **pipeline mỗi giờ phút 15, giám sát mỗi giờ phút 45, thêm trigger khi Admin đăng nhập**. Windows dùng tài khoản đang đăng nhập, không lưu mật khẩu; máy cần bật và có mạng. Có StartWhenAvailable/WakeToRun theo khả năng Windows, không sửa power policy. Xem trạng thái thực tế tại [health](outputs/automation_20261020/health.html), [Task Scheduler đã xác minh](outputs/automation_20261020/scheduler_status.json), [log lần chạy](outputs/automation_20261020/state.json). Nhật ký cũ ghi “chưa cài scheduler” thuộc các snapshot trước extension này.

Mỗi lần có tối đa 3 lượt thử, cách nhau 60 giây; Windows có thêm restart khi task kết thúc lỗi. Capture mới sau 4 giờ hoặc khi nguồn lỗi được lưu thành bytes/receipt mới, không ghi đè snapshot cũ. Watchdog kiểm tra heartbeat quá hạn, task sai/tắt, lần chạy treo và inputs gần/quá cutoff; cảnh báo qua Windows notification center và trang health, có chống lặp. Ngày không đủ inputs là trạng thái dữ liệu, không bị ghi thành lỗi phần mềm hoặc bù forecasts hồi tố. Sau origin cuối, chỉ tiếp tục nhận nhãn và giữ gate chấm ban đầu.

```powershell
py -3.11 run_automation.py status
py -3.11 run_automation.py run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/manage_topic09_automation.ps1 -Action Status
```

Quản lý lịch dùng `-Action Install`, `RunNow` hoặc `Uninstall` trên script trên; script chỉ thao tác đúng hai task có action trỏ về workspace này. `ExecutionPolicy Bypass` chỉ cho tiến trình đang chạy script dự án, không thay chính sách PowerShell của máy. [Cấu hình và phạm vi được cho phép](config/automation_20261020.json) tách khỏi model/protocol đã freeze.

**Ngày nộp và OOS là hai mốc riêng:** 25/10 quyết định nội dung bản nộp, không phải điều kiện thống kê của backtest hoặc ngày bắt buộc kết thúc đánh giá. Đã đối chiếu [tài liệu bổ sung](paper/untouched_oos_followup_20261020.md), giữ nested backtest/matched sensitivity làm kết quả lịch sử và tiếp tục collector theo protocol đang khóa. [Kế hoạch, trạng thái và lệnh vận hành OOS](outputs/research/release_20261025/oos_followup.html) · [lịch UTC/giờ Việt Nam](outputs/research/release_20261025/next_operations.csv) · [provenance](outputs/research/release_20261025/oos_followup.json). Một năm là thời lượng của protocol hiện tại, không phải ngưỡng phổ quát; chưa kích hoạt pilot hay chấm sớm. Không tự thêm SPA gốc vào expanding estimation khi chưa có thiết kế suy luận phù hợp.

Các mục bên dưới là **nhật ký snapshots theo phiên bản**. Những nhãn “hiện tại” và lệnh `all/train/fit/package` trong các snapshot cũ thuộc thời điểm đó; không dùng để ghi đè artifact checkout đã freeze. Dùng entry point ở trên cho bản nộp hợp nhất. Các báo cáo và ZIP cũ được giữ nguyên, dashboard/navigation cũ có bản archive theo SHA-256.

## Phương án nộp trước 25/10/2026

Đã nhận hạn nộp **25/10/2026**. [Quyết định và lịch hoàn thiện](outputs/research/submission_20261025/report.html) cập nhật phần OOS theo hạn này: dùng kết quả lịch sử nested/sensitivity đã khóa, công bố chưa có untouched OOS cho thiết kế cuối. Mốc chốt báo cáo nội bộ đề xuất **24/10, 18:00 giờ Việt Nam**; đây không phải giờ nộp do người dùng cung cấp.

Origin sớm nhất có thể hợp lệ là 23/10; nhãn sớm nhất 25/10 lúc 07:00 VN. Vì vậy tại mốc chốt 24/10 có 0 ngày dự báo mới đủ nhãn; ngay cả đợi hết 25/10 cũng tối đa 1 origin có thể đủ nhãn, chưa đủ để xác nhận future skill. Cửa sổ 20–24/10 UTC chỉ theo dõi vận hành theo protocol một năm hiện có, không chấm performance sớm hoặc tạo holdout mới. Đã thêm lịch tự động theo extension 20/10 ở trên. Dữ liệu, 640 nested artifacts, các báo cáo và ZIP cũ giữ nguyên.

```powershell
py -3.11 plan_submission.py
```

## PIT từng feature và nested backtest — 20/10/2026

Phiên bản riêng `pit_nested_20261020`: [báo cáo audit và sensitivity](outputs/research/pit_nested_20261020/report.html), [thiết kế khóa trước fit](config/pit_nested_20261020.json), [kiểm chứng độc lập](outputs/research/pit_nested_20261020/independent_validation.json). Giữ nguyên dữ liệu, mô hình, report và ZIP cũ.

- Audit trực tiếp từ raw archive: 15 định nghĩa feature, 28.026 dòng lineage macro, 353/353 kiểm tra reconstruction/timing đạt. ALFRED có vintage theo ngày; thời điểm nhận dữ liệu lịch sử và revision của crypto/market proxies vẫn là giả định được công bố.
- Bốn scenario: native as-of D3, matched as-of D3, latest-vintage trên đúng observation dates cũ, matched as-of D4. Cả training/validation/test dùng cùng tập ngày khi so vintage/timing; outer origins từ 949 xuống 728 mỗi tài sản. Latest-vintage chỉ là counterfactual ex post.
- Nested chronological outer folds 2023–2026, inner hai học kỳ năm trước; purge bằng ngày nhãn khả dụng và fit cutoff có buffer 24h. Kết quả lịch sử vẫn exploratory vì outcomes đã được xem.
- Kết quả gộp: native D3 có 3/32 macro ablations cải thiện sau BH; ba scenario matched đều 0/32. Mỗi scenario gộp có 0/40 learned vượt benchmark. Thêm ngày đệm có cả tốt hơn và kém hơn; không tự xác nhận future skill. Đã replay 640 artifacts/125.320 dự báo, fit lại 8 đại diện; 21/21 checks và 6 edge guards đạt, không có fit warnings.
- [Phương án OOS ban đầu](outputs/research/pit_nested_20261020/oos_proposal.html) được lưu trước khi biết hạn nộp; xem quyết định 25/10 ở trên để biết phạm vi nộp cuối cùng. Chưa đổi protocol một năm, chưa tạo future score hoặc triển khai các nested artifacts.

```powershell
py -3.11 run_pit_nested.py validate
py -3.11 run_pit_nested.py compare
py -3.11 run_pit_nested.py product
node tests/preview_pit_nested.cjs
py -3.11 package_pit_nested.py
```

Trên bản sao repo trước khi freeze, chạy `audit → fit → compare → validate → product`; `fit` tiếp tục các folds đã hoàn tất nếu bị gián đoạn. Sau freeze, không chạy lại `audit/fit/all` để ghi đè. Supplement mới cần full base repo và dependencies, không standalone. Preservation checks là so sánh với trạng thái trước study này; các cập nhật operational được chủ động thực hiện về sau cần ghi nhận riêng khi đối chiếu snapshot, không phải tự động là lỗi leakage.

## Research bổ sung về Timing/PIT và untouched OOS — 19/10/2026

[Rà soát tài liệu và hướng xử lý](outputs/research/pit_oos_review_20261019/report.html), [bản Markdown](paper/pit_oos_remedies_review_20261019.md): vintage/release timing theo nguồn, sensitivity về revision, nested rolling-origin, và phương án pilot prospective ngắn hạn. Có đối chiếu giới hạn của SPA, reusable holdout và anytime-valid inference. Đây là research/đề xuất; chưa đổi pipeline, mô hình hoặc protocol một năm hiện có.

## Rà soát quy tắc và vận hành prospective — 19/10/2026

Đã kiểm tra rule timing/ghép mẫu và tiếp tục thí nghiệm theo protocol đã khóa. [Báo cáo vận hành](outputs/research/evidence_20261019/prospective_operations/report.html), [audit quy tắc](outputs/research/evidence_20261019/prospective_operations/rule_audit.json), [lịch chuẩn bị 14 ngày](outputs/research/evidence_20261019/prospective_operations/readiness_calendar.csv), [kiểm chứng](outputs/research/evidence_20261019/prospective_operations/validation.json).

- Sửa trong adapter riêng: chọn snapshot **đủ nội dung** đầu tiên trong cùng cutoff/vintage; chạy lại tái dùng commit và tiếp tục tài sản còn thiếu; lần capture lỗi được retry trong ngày. Không sửa code latency cũ hoặc ghi đè dự báo đã chốt.
- Đối chiếu đúng80 giá trị dự báo lịch sử của BTC/ETH;15 kiểm thử vận hành đạt. Giữ40 mô hình, lags, buffer24h, mẫu ghép và fixed evaluation window.
- Rule ghép macro làm giảm khoảng31% số ngày có đủ own features trên lịch sử; chủ yếu là market day cuối tuần. Đây là đánh đổi độ phủ, không tự đổi thành mẫu own-only24/7. Macro RV có1/32 p<0,05 trướcBH,0/32 sauBH; không quy toàn bộ kết quả yếu cho ngưỡng kiểm định.
- Đã capture thêm17/17 responses thật ngày19/10. Origin20/10 đã lỡ cutoff;21–22/10 đòi market day cuối tuần. Origin23/10 **có thể** đủ điều kiện nếu capture21/10 UTC và log22/10 UTC; không phải forecast đã ghi. Hiện chưa có dự báo/nhãn hợp lệ hoặc future score. Chưa cài scheduler.

```powershell
py -3.11 run_prospective.py run
py -3.11 run_prospective.py run --refresh-capture
py -3.11 run_prospective.py validate
```

Khi vận hành, chạy mỗi ngày UTC, ví dụ16:00 giờ Việt Nam (09:00 UTC). Lệnh thường tái dùng capture thành công cùng ngày; `--refresh-capture` lưu một capture mới riêng. Không dùng đồng hồ giả, backdate hoặc tải sau cutoff để dựng dự báo cũ. Đọc report vận hành để biết trạng thái mới; các report nghiên cứu bên dưới vẫn là snapshot đã giữ nguyên. [ZIP vận hành bổ sung](topic09_prospective_operations_20261019_supplement.zip) cần full base repo và evidence supplement, không standalone.

## Evidence extension từ nghiên cứu tham khảo — 19/10/2026

Đã triển khai riêng sau khi được đồng ý: kiểm tra chéo Bauer–Swanson, cửa sổ trước thông báo/tuần trước, toàn miền xoay, bootstrap cả bước xây dựng shock và pooled regime interactions; thêm nghiên cứu RV5m/15m với HAR/HAR-X, GARCH/EWMA và MCS. Giữ nguyên **1.202 tệp nền** đã khóa hash, gồm các mô hình, dữ liệu, báo cáo và ZIP cũ.

- [Báo cáo mới](outputs/research/evidence_20261019/report.html), [dashboard offline](outputs/research/evidence_20261019/dashboard.html), [rà soát nghiên cứu](paper/causality_forecast_literature_review_20261019.md), [thiết kế khóa](config/evidence_20261019.json).
- FOMC: **75 sự kiện gốc →72 đủ cửa sổ →45 giao nhau đủ các nguồn**. BS workbook đến12/2023 và thiếu orthogonalized surprise trong COVID; không thay missing bằng raw. Policy intraday point range trên toàn miền xoay: BTC khoảng[−1,956;−0,711], ETH[−2,523;−0,795] điểm phần trăm/+10bps PC1 component. Đây **không phải confidence set**; information component có thể unbounded theo chuẩn hóa này.
- **999 bootstrap draws** lặp PCA/scaling/QR và outcome fit; CI chỉ cho phép xoay nội miền cố định, không bao phủ toàn structural identified set. Kiểm tra giả sự kiện và nguồn chưa loại được mọi confounding. Regime contrasts có20/256 đạtBH vớiHAC, **0/256 vớiHC3**; pre2020 chỉ23events, stress12events. Khác biệt chế độ chưa vững theo lựa chọn suy luận.
- RV riêng dùng **Binance USDT**, không nối vào USD baseline.250 archives có checksum;257 nến/asset sai timestamp bị ghi audit và loại, không sửa/nội suy. Chọn cửa sổ bằng validation đã purge; monthly refit bằng nhãn khả dụng. Có **51/120 so sánh HAR/HAR-X thắng benchmark đạtBH**, nhưng **0/32 macro ablations đạtBH**. Đây không phải51 phát hiện độc lập hoặc confirmed future skill; test2025+ đã xem.
- [21/21 kiểm tra độc lập và7 edge guards](outputs/research/evidence_20261019/independent_validation.json), [428 dashboard views](outputs/research/evidence_20261019/dashboard_validation.json). Có full-day RV reconstruction, HAR/GARCH replay và kiểm tra độc lập bootstrap/MCS.
- Prospective vận hành trong namespace mới với protocol và40 latency models nguyên hash. Capture17/17 responses; origin20/10 ghi0 predictions do nhận sau cutoff24h. Chưa có future score; không deploy RV models hoặc cài scheduler. [Operational audit](outputs/research/evidence_20261019/prospective/namespace_audit.json).

```powershell
py -3.11 run_evidence.py validate
py -3.11 run_evidence.py product
node tests/validate_evidence_dashboard.cjs
node tests/preview_evidence.cjs
```

Vận hành snapshot/forecast/labels thật hàng ngày: `py -3.11 run_evidence.py prospective`; có thể chạy `product` sau đó để cập nhật trạng thái. `rv_prepare/rv_fit/all` chỉ cho fresh version chưa freeze; không xóa freeze hoặc refit bản đang lưu. Gói `topic09_evidence_20261019_supplement.zip` cần full base repo và dependencies hiện có, không standalone.

## FOMC identification và matched timing — 19/10/2026

Đã audit và khóa thiết kế trước khi fit:75 scheduled events chung cho BTC/ETH và toàn bộ32 outcomes, gồm23 pre2020 và52 post2020. Giữ nguyên1077 file cũ đã khóa hash; không thay latency40models, prospective protocol, baseline hoặc monetary/VAR robustness.

- [Báo cáo FOMC mới](outputs/research/fomc_identification_20261019/report.html), [Markdown](outputs/research/fomc_identification_20261019/report.md), [dashboard](outputs/research/fomc_identification_20261019/dashboard.html).
- Dùng author-published policy/information median components và pinned GitHub commit. PCA tái lập đúng8decimal; components khớp trong rounding≈5e−9. Đủ input/timestamp mới ghép, không biến missing thành shock0. [Audit](outputs/research/fomc_identification_20261019/audit_summary.json), [replay](outputs/research/fomc_identification_20261019/decomposition_replay.json).
- Coinbase USD cho cả minute/day; so intraday−10/+20, event UTC-day và postD+1…D+h, h1…30 trên cùng75 events. Controls/shock giữ nguyên giữa windows. [Coverage](outputs/research/fomc_identification_20261019/coverage_summary.csv), [exclusions](outputs/research/fomc_identification_20261019/exclusions.csv).
- Median intraday policy: **−1,163%BTC, −1,422%ETH / +10bps contribution to pc1**, cùng đạtBH128. Giữ dấu âm ở3 rotations và75 single-event deletions. Có3/128 full coefficients đạtBH, **0/8 direct timing differences** đạtBH; không suy ra khác slope giữa windows chỉ từ p-values khác nhau. Đơn vị không phải Fed target/STMT/FF3+10bps; information+10bps vượt positive support quan sát.
- **CI có điều kiện**, không chứa đầy đủ uncertainty của shock construction hoặc toàn identified set. Pre2020 chỉ23events; historical/exploratory và causal interpretation còn phụ thuộc exclusion/sign assumptions. 51/128 hệ số full đổi dấu giữa3 rotations. Case deletion là chẩn đoán hậu nghiệm, không bỏ event khỏi baseline.
- Cửa sổ khớp danh nghĩa, chưa cùng quote sampling: tác giả dùng median quanh−10/+20, crypto dùng close phút tại mốc; thiếu underlying tick/extension flags để kiểm chứng đầy đủ. [Measurement audit](outputs/research/fomc_identification_20261019/measurement_window_audit.json).
- [20/20 independent checks và5 guard tests](outputs/research/fomc_identification_20261019/independent_validation.json), [384 UI views](outputs/research/fomc_identification_20261019/dashboard_validation.json), [Chrome desktop/mobile](outputs/research/fomc_identification_20261019/browser_validation.json).
- [ZIP bổ sung cho repo hiện có](topic09_fomc_identification_20261019_supplement.zip), [manifest](manifest_fomc_identification_20261019.json), [package audit](package_fomc_identification_20261019.json). Supplement không standalone: giải nén vào bản sao repo hiện tại có frozen prerequisites; các ZIP/model bundle cũ được tham chiếu SHA, không đóng lặp.

```powershell
py -3.11 run_fomc_identification.py audit
py -3.11 run_fomc_identification.py fit
py -3.11 run_fomc_identification.py influence
py -3.11 run_fomc_identification.py validate
py -3.11 run_fomc_identification.py product
node tests/validate_fomc_identification_dashboard.cjs
node tests/preview_fomc_identification.cjs
```

`sources` dùng cache tác giả/Coinbase riêng khi đã có; không làm mới source cũ tại chỗ. `all` chạy sources→audit→fit→influence→product→validate; Chrome/UI checks chạy bằng Node như trên. Không dùng kết quả event study này làm prospective score. [Ghi chú triển khai](paper/fomc_identification_20261019.md).

## Phiên bản timing mới 19/10/2026: thêm một ngày đệm và tái huấn luyện riêng

Đã thực hiện sau khi được đồng ý: shift features/vintage metadata **2 ngày trên original calendar**, thay shift1 của completion; targets giữ nguyên. Own crypto tại D−3, market proxies tại D−4; macro đúng information-day vintage. Giữ nguyên 887 file cũ được khóa hash, gồm baseline, monetary/VAR robustness, artifacts và ZIP cũ.

- [Báo cáo timing mới](outputs/research/latency_20261019/report.html), [Markdown](outputs/research/latency_20261019/report.md), [dashboard matched forecasts](outputs/research/latency_20261019/dashboard.html).
- Đã huấn luyện và freeze **40 artifacts riêng**, không cảnh báo fit. Mỗi cấu hình có446 test origins; so timing cũ/mới trên347 origin giao nhau, không so metric trên hai mẫu khác ngày.
- **3/32 macro ablations cải thiện với BH**, đều là squared return trên mẫu dài không USD. **0/40 learned vượt benchmark, 2/40 kém benchmark** đạt BH. Test2025+ đã xem nên các tín hiệu mới vẫn exploratory; không phải confirmed future skill hoặc causal identification.
- [20/20 kiểm tra độc lập và 11 deployment guards](outputs/research/latency_20261019/independent_validation.json); [UI checks](outputs/research/latency_20261019/dashboard_validation.json); [Chrome desktop/mobile](outputs/research/latency_20261019/browser_validation.json).
- Collector mới có crypto/VIX/Yahoo S&P500/gold và ALFRED exact requested vintage. Lần capture thành công17/17 responses; giữ cả lần lỗi requests trước khi chuyển sang curl form-download của pipeline gốc. [Capture audit](outputs/research/latency_20261019/latest_capture.json).
- [Protocol prospective đã khóa](data/prospective/latency_20261019/protocol.json), [attempt thực tế](outputs/research/latency_20261019/prospective_status.json): 0 prediction cho origin20/10 vì snapshot nhận sau cutoff24h. Không backdate, không tạo nhãn tương lai, chưa có OOS score mới. Không cài scheduler.
- [ZIP phiên bản mới](topic09_latency_20261019.zip), [manifest SHA256](manifest_latency_20261019.json), [kiểm tra gói](package_latency_20261019.json).

Kiểm tra bản đã bàn giao (không ghi đè models):

```powershell
py -3.11 run_latency.py validate
py -3.11 run_latency.py compare
py -3.11 run_latency.py product
node tests/validate_latency_dashboard.cjs
node tests/preview_latency.cjs
```

Vận hành hàng ngày:

```powershell
py -3.11 run_latency.py collect
py -3.11 run_latency.py forecast
py -3.11 run_latency.py labels
py -3.11 run_latency.py evaluate
py -3.11 run_latency.py product
```

`prepare`/`train`/`all` chỉ cho fresh source checkout chưa có generated artifacts của phiên bản này; bản đã freeze sẽ từ chối refit. Muốn tái huấn luyện, dùng bản sao/phiên bản riêng không chứa generated outputs mới, giữ nguyên các prerequisites cũ; không xóa freeze của bản đang dùng. `forecast --origin` chỉ nhận UTC midnight trong24h kế tiếp và kiểm tra mọi actual receipt≤origin−24h. Thiếu market return đúng ngày hoặc source receipt không đạt thì ghi missing attempt. Evaluation trước fixed end trả PENDING. [Ghi chú triển khai](paper/latency_20261019.md).

## Bổ sung 19/10/2026: monetary robustness và đúng 6 joint VAR

Đã thực hiện kiểm tra tiếp theo và lưu riêng; giữ nguyên 842 file baseline được khóa hash, gồm dữ liệu, kết quả, artifacts, dashboard và ZIP cũ.

- [Báo cáo bổ sung](outputs/research/robustness_20261019/report.html), [Markdown](outputs/research/robustness_20261019/report.md), [dashboard chẩn đoán](outputs/research/robustness_20261019/dashboard.html).
- Monetary: 9 phép bỏ từng stress event và bỏ toàn bộ event dates tháng 3–4/2020; leverage, Cook, partialled-interaction information shares và overlap. Bỏ riêng 03/03/2020 làm số stress−calm differences đạt BH giảm từ **36/60 xuống 3/60**. 13/60 cặp asset–horizon đổi dấu trong ít nhất một lần bỏ sự kiện. Bỏ COVID còn 3 stress events nên không xác nhận độ vững, dù p/q có thể nhỏ hơn. Baseline đầy đủ giữ nguyên.
- Joint VAR: tái lập đúng 6 fits và lưu residual theo ngày, own/cross-lag và squared correlations lag1–40, whiteness20/30/40, ARCH5/10. **60/60 ARCH tests đạt BH; 4/6 hệ bác bỏ whiteness20**, cả trước và sau BH18. Có vấn đề ở mean và variance; chưa thêm GARCH/TVP hoặc đổi lag.
- [18/18 kiểm tra độc lập](outputs/research/robustness_20261019/independent_validation.json); [660 lựa chọn monetary + 30 residual views](outputs/research/robustness_20261019/dashboard_validation.json); [Chrome desktop/mobile](outputs/research/robustness_20261019/browser_validation.json) không lỗi JavaScript/tràn ngang.
- Đã capture **11/11 nguồn thật** với bytes/URL/retrieval UTC/HTTP metadata/SHA256. [Capture audit](outputs/research/robustness_20261019/prospective_capture_status.json). Chưa log dự báo vì snapshot không đạt cutoff24h cho origin gần nhất; chưa có OOS mới. [Đề xuất timing prospective](paper/prospective_timing_proposal.md) đang chờ đồng ý, chưa đổi lag hoặc refit.
- [ZIP bổ sung](topic09_robustness_20261019.zip), [manifest SHA256](manifest_robustness_20261019.json), [kiểm tra gói](package_robustness_20261019.json).

```powershell
py -3.11 run_robustness.py diagnostics
py -3.11 run_robustness.py product
py -3.11 run_robustness.py validate
node tests/validate_robustness_dashboard.cjs
node tests/preview_robustness.cjs
```

`py -3.11 run_robustness.py collect` tạo snapshot mới theo thời điểm chạy; không tái tạo availability trong quá khứ. `package` tạo ZIP phiên bản mới một lần, không ghi đè bản đã phát hành. Xem báo cáo bổ sung trước khi dùng kết luận monetary stress hoặc CI VAR.

## Snapshot 19/10/2026: triển khai blueprint và pipeline có cấu trúc

Bản bổ sung giải thích các vấn đề: [phân loại lỗi/dữ liệu/phương pháp/kết quả và đối chiếu nghiên cứu](outputs/research/issue_literature_review_20261019.md). Review này không thay mô hình hoặc snapshot đã đóng gói; các hướng xử lý mới trong đó là đề xuất chưa chạy.

Bản yêu cầu chi tiết phù hợp với hướng đề. [Yêu cầu đã làm rõ theo blueprint](paper/requirements.md) phân biệt phần tối thiểu với mô hình mở rộng và các giới hạn chưa thể chứng nhận. Giữ baseline không MOVE, Broad USD thay vì đổi tên thành DXY, historical sample đầy đủ và forecasting USD vintage từ 2019.

- [Báo cáo hiện tại](outputs/research/blueprint_20261019/report.html), [Markdown](outputs/research/blueprint_20261019/report.md), [đối chiếu từng yêu cầu](outputs/research/blueprint_20261019/compliance.md).
- [Macro–Crypto Dashboard hiện tại](dashboard/index.html): VIX/Broad USD/2Y/10Y/Monetary, BTC/ETH, mọi horizon 1–30 ngày lịch, Full/Calm/Stress; CI, quantile effects, joint VAR IRF, rolling, historical analogues và validation importance.
- [ZIP phiên bản hiện tại](topic09_blueprint_20261019.zip), [manifest SHA-256](manifest_blueprint_20261019.json).
- [Thiết kế khóa](config/blueprint_20261019.json); [37 kiểm tra độc lập](outputs/research/blueprint_20261019/independent_validation.json), [kiểm tra UI](outputs/research/blueprint_20261019/dashboard_validation.json), [Chrome desktop/mobile](outputs/research/blueprint_20261019/browser_validation.json).

Đã bổ sung connector Binance BTCUSDT/ETHUSDT từ 17/08/2017 đến 15/10/2026, chỉ dùng đối chiếu nguồn. Nến 08/02/2018 của cả hai tài sản kết thúc sớm: giữ raw và gắn cờ, để thiếu hai return liên quan khi so close-to-close UTC. Không nối USDT vào chuỗi USD mẫu dài. Các payload/cache và hash lưu riêng trong `data/raw/blueprint_20261019/`.

**Thiết kế mới:** daily LP tính cập nhật của mức thông tin đã khả dụng và có buffer 24h; carry mức trên ngày nghỉ, không carry nonzero changes, không fill crypto. Các crypto lag controls cũng đủ buffer. Vì Broad USD vintage chỉ từ 2019 nên phần calendar-information LP/quantile ngắn hơn mẫu lịch sử đầy đủ. Historical session models/rolling cũ vẫn được giữ. Monetary LP đo ngày D+1…D+h sau FOMC, loại ngày công bố, khác cửa sổ phút.

**Kết quả và giới hạn:** 0/240 hệ số daily LP full đạt BH trong family 720; 0/60 monetary full đạt BH. Stress−Calm có 0/240 daily và 36/60 monetary đạt BH theo các family riêng; monetary stress chỉ có 9 sự kiện, chưa có kiểm tra influence/finite-sample inference xác nhận độ vững. Joint VAR cả BTC và ETH có 6/6 hệ stable nhưng 4/6 bác bỏ whiteness; recursive restrictions là giả định, chưa nhận diện pure monetary policy. Quantile có CI bootstrap pointwise xấp xỉ; 5/1.782 bootstrap fits không hội tụ được loại và lưu log. Không dùng khác CI để kết luận khác slope.

ML giữ các kết quả completion đã khóa (0/32 macro ablation đạt BH), thêm validation-only grouped importance và lưu 40 model artifacts với SHA-256. **Chưa chứng nhận whole-feed PIT, chưa có untouched test mới.** Protocol và lệnh log forecast trước outcome cho giai đoạn từ 20/10/2026 đã có, nhưng không được gọi là đã hoàn thành đánh giá OOS tương lai. Không dùng ML thay identification hoặc sửa mô hình để ép kết quả có ý nghĩa.

Chạy lại toàn bộ bản hiện tại từ snapshot đã bàn giao (Python 3.11, Node có WebSocket/fetch, Chrome để QA):

```powershell
py -3.11 -m pip install -r requirements-project.txt
py -3.11 run_project.py all
```

Mặc định dùng cache, không tải lại và không ghi đè kết quả cũ. `--download` cho phép tải Binance pages còn thiếu vào thư mục riêng. Có thể chạy từng stage: `prepare`, `econometrics`, `quantile`, `models`, `product`, `validate`, `package`. `validate` gồm đối chiếu độc lập, 5 prospective-timing unit tests và Chrome QA; `package` kiểm tra CRC và mọi SHA-256.

Trên **fresh copy chưa có dữ liệu**: chạy `py -3.11 run_project.py bootstrap`, sau đó `py -3.11 run_project.py all --download`. Bootstrap dùng các script nguồn gốc để dựng prerequisites, không cho chạy khi đã có frozen daily panel. Public providers có thể sửa dữ liệu/giới hạn lịch sử; ZIP raw và manifest mới bảo đảm tái lập đúng snapshot đã nộp. Không dùng bootstrap để cập nhật snapshot cũ tại chỗ.

```text
config/                    Thiết kế khóa theo phiên bản
src/data/                  Binance connector và calendar information panels
src/features/              Timing, controls và định nghĩa outcome
src/models/                LP, joint VAR/recursive restrictions, quantile, ML artifacts
src/evaluation/            Independent checks và prospective prediction logging
src/utils/                 Paths, provenance và packaging
models/blueprint_20261019/  40 artifacts, model card
dashboard/                 Offline app, template
tests/                     Unit, UI-state và real-browser checks
paper/                     Yêu cầu đã làm rõ và liên kết báo cáo
data/raw/, data/processed/  Snapshot gốc và phần mới lưu riêng
outputs/research/          Báo cáo, bảng, hình và audits theo phiên bản
```

## Snapshot 17/10: timing, macro ablation, variance dương và dashboard

Đã thực hiện phần hoàn thiện được đồng ý: buffer thông tin 24 giờ trước forecast origin, kiểm tra nhãn khi fit; so sánh crypto-only với macro trên mẫu dài và mẫu chung từ 2019; dự báo variance dương; thêm Calm/Stress và các ví dụ lịch sử. LP/HAC, FOMC và rolling vẫn là trọng tâm; VAR ở phụ lục. Dữ liệu, kết quả và ZIP cũ giữ nguyên hash.

- [Báo cáo hiện tại](outputs/research/completion/report.html), [Markdown](outputs/research/completion/report.md) và [dashboard offline](outputs/research/completion/dashboard.html).
- [ZIP hiện tại: dữ liệu, code và kết quả](topic09_completion_20261017.zip); [manifest SHA-256](manifest_completion.json).
- [Thiết kế khóa trước khi fit](outputs/research/completion/design.json), [timing register](outputs/research/completion/availability_register.csv), [32 so sánh ablation](outputs/research/completion/ablation_tests.csv), [40 so sánh benchmark](outputs/research/completion/benchmark_tests.csv).
- [26/26 kiểm tra độc lập](outputs/research/completion/independent_validation.json): timing/calendar lag, label availability, samples, metrics, HAC/BH, tái lập mô hình và CI Calm/Stress có covariance. [Kiểm tra dashboard](outputs/research/completion/dashboard_validation.json) duyệt 248 lựa chọn LP/state, 1.036 cửa sổ rolling, 80 danh sách lịch sử và 16 cấu hình forecast. [Chrome desktop/mobile](outputs/research/completion/browser_validation.json) không lỗi JavaScript hoặc tràn ngang.

**Kết quả:** 0/32 ablation đạt BH q<0,05; chưa thấy cải thiện macro/USD bền theo thiết kế này. Dự báo variance đều dương, không ép prediction floor và không còn giá trị ≤1e−12. So benchmark có 0 trường hợp learned tốt hơn và 5 kém hơn đạt BH trong family 40. Đây không phải bằng chứng mọi biến macro đều không có giá trị dự báo.

**Giới hạn còn lại:** test 2025+ đã được xem nên lượt mới là exploratory, không có untouched test mới. Buffer 24 giờ là giả định bảo thủ; publication timestamps và historical market vintages chưa đầy đủ, chưa chứng nhận toàn feed real-time hoặc không còn mọi look-ahead. VAR vẫn chưa đạt chẩn đoán; LP/FOMC chưa xác lập nhân quả. Không thay mô hình để ép kết quả có ý nghĩa.

Tái lập riêng extension, giữ các snapshot trước:

```powershell
py -3.11 research_completion.py prepare
py -3.11 research_completion.py fit
py -3.11 research_completion.py tests
py -3.11 research_completion.py stress
py -3.11 validate_completion.py
py -3.11 build_completion.py
node validate_completion_dashboard.cjs
node preview_completion.cjs
py -3.11 package_completion.py
```

Bước `tests` tái tính paired loss và xử lý dự báo hòa đến độ chính xác máy; [ghi chú](outputs/research/completion/numerical_tie_note.json) phân biệt sửa số học với thay thiết kế. Bước `stress` tái lập pooled interaction cũ để lấy covariance, không thêm mô hình regime. Không gọi `run_research.py` nếu chỉ muốn tái lập extension. Giải nén toàn bộ ZIP để giữ liên kết tới các báo cáo nguồn; preview cần Chrome và Node có WebSocket.

## Snapshot trước: LP/HAC, FOMC và rolling

Theo hướng đã thống nhất, LP/HAC, FOMC và rolling sensitivity là trọng tâm; VAR nằm ở phần đối chiếu và chẩn đoán. Bản này tổng hợp các ước lượng đã lưu, không fit thêm mô hình hoặc thay dữ liệu, lag, mẫu và kiểm định. Các snapshot trước vẫn giữ nguyên.

- [Báo cáo HTML](outputs/research/synthesis/report.html) và [Markdown](outputs/research/synthesis/report.md).
- [Dashboard tương tác offline](outputs/research/synthesis/dashboard.html): LP theo asset/shock/regime/horizon, FOMC theo cửa sổ, rolling theo ngày và forecasting theo cấu hình.
- [ZIP dữ liệu, mã nguồn và kết quả tổng hợp](topic09_lp_fomc_synthesis_20261017.zip); [manifest SHA-256](manifest_synthesis.json). Script đóng gói kiểm tra CRC và hash của toàn bộ file, lưu kết quả kiểm tra cạnh ZIP.
- [24/24 đối chiếu độc lập](outputs/research/synthesis/independent_validation.json) đạt; [kiểm tra dashboard](outputs/research/synthesis/dashboard_validation.json) duyệt 168 lựa chọn LP và 1.036 cửa sổ rolling. [Chrome thực tế](outputs/research/synthesis/browser_validation.json) không có lỗi JavaScript, không tràn ngang trên desktop/mobile, ảnh báo cáo tải đủ.

LP đo lợi suất cộng dồn theo phiên đủ dữ liệu, FOMC đo cửa sổ phút với ET → UTC/DST. HAC và các kiểm tra kỹ thuật không xác lập quan hệ nhân quả hoặc khắc phục mọi sai đặc tả. Kết quả STMT phụ thuộc cửa sổ; tương tác pre/post chưa đạt BH; hạn chế VAR và variance forecasting được công bố trong báo cáo.

Tạo lại riêng phần tổng hợp từ kết quả đã lưu, không chạy lại mô hình:

```powershell
py -3.11 build_synthesis.py
py -3.11 validate_synthesis.py
node validate_synthesis_dashboard.cjs
node preview_synthesis.cjs
py -3.11 package_synthesis.py
```

Bước preview cần Chrome hoặc Edge cài sẵn; không tải thêm thư viện. Mở `report.html` hoặc `dashboard.html` trực tiếp sau khi giải nén toàn bộ ZIP để giữ liên kết tới bảng và báo cáo nguồn.

## Review tổng hợp hiện tại — đọc trước khi dùng kết quả

[Bản review ngày 17/10/2026](outputs/research/current_results_review.md) tổng hợp baseline và toàn bộ phần bổ sung, xếp ưu tiên các giới hạn và phân biệt kết luận có thể sử dụng với câu hỏi chưa được trả lời. [Đối chiếu số liệu/hash](outputs/research/current_results_review_checks.json) không chạy thêm mô hình hoặc kiểm định.

Kết luận review: dữ liệu và các kết quả thăm dò có thể dùng để viết nghiên cứu với phạm vi rõ; VAR chưa đủ cho suy luận nhân quả, variance boosting/QLIKE còn hạn chế, forecasting hiện xét trực tiếp USD gia tăng. Có thể hoàn thiện nghiên cứu bằng cách giới hạn kết luận phù hợp; không bắt buộc tiếp tục thử VAR hoặc thêm mô hình. Báo cáo/dashboard/ZIP baseline giữ snapshot cũ; bản tổng hợp hiện tại nằm ở mục đầu README.

## Tổng quan nghiên cứu trước bước chạy tiếp

Đã tra cứu tài liệu liên quan ngày 17/10/2026: [bản đối chiếu nghiên cứu](outputs/research/literature_review.md), gồm kết quả, khác biệt dữ liệu/phương pháp, tiêu chí đánh giá và đề xuất thứ tự tiếp theo. Phân biệt tài liệu đọc toàn văn với tài liệu mới kiểm tra abstract. Lượt này chỉ bổ sung tài liệu; chưa chạy hay thay đổi mô hình.

## Đối chiếu FOMC đã được đồng ý: mẫu 2017–2022 và cửa sổ sự kiện

- Báo cáo: [outputs/research/fomc_comparison/report.md](outputs/research/fomc_comparison/report.md); [bản HTML và bảng kết quả](outputs/research/fomc_comparison/report.html).
- Chọn 47 cuộc họp định kỳ theo cờ `Unscheduled` của USMPD, tách 7 sự kiện bất thường. Mẫu đủ phút và đủ surprise giao nhau của hai cửa sổ có **46 BTC, 45 ETH**; mỗi tài sản dùng cùng ngày cho cả hai đặc tả và cửa sổ.
- Đối chiếu return `[-10,+20]` và `[-5,+25]`, giữ MP1/MP2 hoặc STMT hiện có. **MP1/MP2 chưa có ý nghĩa; STMT âm ở cửa sổ `[-5,+25]` còn ý nghĩa sau BH**: BTC q≈0,0296, ETH q≈0,0230 trong nhóm 12 kiểm định của lượt này. Hệ số tương ứng một độ lệch chuẩn STMT khoảng −0,55% và −0,72% log return. Đây là phân tích bổ sung sau baseline, chưa phải bằng chứng chính sách thuần túy hay replication đầy đủ.
- STMT ở `[-10,+20]` không còn ý nghĩa sau BH. Leave-one-event-out của STMT ở `[-5,+25]` giữ dấu âm và raw p<0,05; không diễn giải kiểm tra này như điều chỉnh nhiều kiểm định toàn dự án.
- Surprise USMPD vẫn đo trong `[-10,+20]`; chỉ đổi cửa sổ crypto return. Chưa dựng đúng Target/Path/LSAP của bài New York Fed. Thiết kế và bản đồ khác biệt được ghi trong báo cáo.
- Lưu riêng 94 payload Coinbase trong `data/raw/fomc_comparison/`; giá phút giao nhau khớp snapshot cũ. **19/19 kiểm tra độc lập đạt**, bao gồm giá, ET/UTC, mẫu, HC3 và BH; hash xác nhận dữ liệu và kết quả nghiên cứu cũ giữ nguyên. Không thay VAR/LP/forecasting hoặc mô hình volatility trong lượt này.

Chạy lại từ cache đã lưu:

```powershell
py -3.11 research_fomc_comparison.py
py -3.11 validate_fomc_comparison.py
```

`--download` chỉ cần khi chưa có cache riêng. Thiết kế đóng băng trong `outputs/research/fomc_comparison/design.json`; không tự ghi đè snapshot đã có.

## Chẩn đoán ARCH và ảnh hưởng quan sát VAR — đã hoàn tất

- Báo cáo: [outputs/research/var_residual_diagnostics/report.md](outputs/research/var_residual_diagnostics/report.md); [bản HTML](outputs/research/var_residual_diagnostics/report.html).
- Dùng 10 fitted systems khác nhau, giữ lag, controls, thứ tự và mẫu. **100/100 ARCH-LM** (5 phương trình × 10 hệ × lag 5/10) còn ý nghĩa sau BH; riêng crypto là 20/20. Đây là kiểm định cổ điển thăm dò, không xác nhận GARCH hay sửa được hạn chế whiteness/mean dynamics.
- Khoảng 6 ngày kết thúc 27/01/2016 có Cook rank của phương trình ETH: **1 ở full p=1 và pre, 2 ở full p=4**. Diagnostic sensitivity của khoảng đó làm IRF ETH đổi tối đa khoảng **0,100 điểm phần trăm ở full**, **0,389 ở pre** trong các hệ/shocks/horizons đã xét.
- Trường hợp thay đổi IRF lớn nhất là ETH pre-2020 quanh **05/02/2018**, bỏ block sự kiện và các hàng dùng nó làm lag: phản ứng tức thời với VIX +5 điểm từ **−1,783% thành −0,641%**, chênh **1,143 điểm phần trăm**. Không chọn bản bỏ block này làm kết quả chính.
- Đã rà soát tất cả dòng bằng leverage/Cook, rồi chạy 68 diagnostic fits: ba dòng max-Cook nổi bật mỗi hệ và khoảng 01/2016 nếu có, mỗi ngày gồm single-row và block sensitivity. Giữ nguyên lag matrix/lịch, không nén ngày sau khi bỏ hàng; không kiểm định whiteness trên mẫu bị nén. Tất cả diagnostic fits ổn định.
- **19/19 kiểm tra độc lập đạt**: ARCH/BH, Cook, studentization, block-deletion identity và IRF được đối chiếu. Dữ liệu và mô hình chính giữ nguyên. Chưa fit GARCH, bootstrap hoặc thay inference; tiếp tục công bố giới hạn VAR thay vì xóa quan sát để đạt kiểm định.

Chạy lại lượt chẩn đoán đã thống nhất:

```powershell
py -3.11 research_var_residual_diagnostics.py
py -3.11 validate_var_residual_diagnostics.py
```

## VAR sensitivity miền lag 0–15 — đã hoàn tất

- Báo cáo: [outputs/research/var_lag_sensitivity/report.md](outputs/research/var_lag_sensitivity/report.md); [bản HTML](outputs/research/var_lag_sensitivity/report.html).
- Giữ 5 biến, thứ tự, weekday+gap và full/pre/post. Toàn bộ ứng viên 0–15 có cùng response dates từ quan sát thứ 16 trong mỗi asset/regime. Có tham chiếu lag lịch sử và miền 0–10 trên cùng mẫu để tách thay đổi miền search khỏi thay đổi sample.
- **Lag không đổi:** BIC=1; AIC full=4, pre=1, post=2 cho cả BTC và ETH. Cả 12 lựa chọn đều ổn định nhưng **vẫn bác bỏ Portmanteau adjusted ở 20/30/40 lags**. Mở miền lag chưa giải quyết vấn đề phần dư; không tự tăng tiếp vượt 15.
- Trên cùng mẫu và cùng lag, IRF mới trùng tham chiếu, chênh lệch lớn nhất bằng 0. Điều này không khẳng định IRF so với bản cũ dùng mẫu n−p cũng trùng: khác biệt cắt đầu mẫu được ghi riêng trong bảng đối chiếu.
- Đã lưu `residuals_by_date.csv`, `coefficients.csv` và `fit_inventory.csv`: 36 dòng stage/criterion tham chiếu **10 fitted systems khác nhau**, không phải 36 ước lượng độc lập. Có 96 candidate fits trong 6 lưới chọn lag.
- **17/17 kiểm tra độc lập đạt**: OLS/IC, dates, residuals, eigenvalues, Portmanteau và IRF được tính lại. Hash xác nhận dữ liệu và kết quả cũ giữ nguyên; kiểm tra tính toán đạt không thay thế adequacy thống kê. Lượt lag sensitivity không thêm ARCH/influence/bootstrap hoặc thay forecasting; ARCH/influence được thực hiện riêng sau đó, xem mục trên.

Chạy lại riêng lượt đã thống nhất:

```powershell
py -3.11 research_var_lag_sensitivity.py
py -3.11 validate_var_lag_sensitivity.py
```

## Xác minh nguồn ba ngày USD thiếu — hoàn tất, giữ nguyên panel

- Báo cáo: [outputs/research/usd_missing_verification/report.md](outputs/research/usd_missing_verification/report.md); [bằng chứng và kiểm tra](outputs/research/usd_missing_verification/report.html).
- Bảng Fed hiện hành của broad USD và goods-only đều ghi **ND cho 22, 25, 26/01/2016**. Năm giá broad USD xung quanh khớp snapshot gốc; khoảng trống không chỉ nằm trong file đã tải.
- Bản H.10 lưu trữ 27/01 và 01/02/2016 có giá trị cho ba ngày, nhưng thuộc **broad goods-only, base Jan 1997, vintage cũ**; không điền các giá trị đó vào DTWEXBGS. Chưa xác minh được giá thay thế tương thích cùng chuỗi.
- Thông báo Fed xác nhận đóng cửa do thời tiết 25–26/01, nhưng chưa đủ để giải thích đầy đủ lịch sử ND của ba ngày; không khẳng định chắc chắn nguyên nhân.
- HTML Fed và provenance/hash lưu riêng trong `data/raw/usd_missing_verification/` và `source_log.json` của báo cáo. CSV FRED tải mới bị timeout; không diễn giải lỗi tải như bằng chứng missing. Kết luận dựa trên bảng Fed hiện hành và snapshot FRED đã có.
- **9/9 kiểm tra nguồn/đối chiếu đạt**, hash của 607 file dữ liệu/kết quả cũ giữ nguyên. Lượt xác minh nguồn không điền giá, nối chỉ số cũ, sửa panel hoặc fit mô hình. Kết quả sensitivity VAR thực hiện sau đó nằm ở mục trên.

Script xác minh: `verify_usd_missing_source.py`; tái dùng payload thành công đã lưu, ghi rõ trạng thái khi endpoint không tải được.

## Rà soát chẩn đoán VAR — chưa fit mô hình mới

- Báo cáo và đề xuất để duyệt: [outputs/research/var_diagnostic_audit/report.md](outputs/research/var_diagnostic_audit/report.md); [bản HTML](outputs/research/var_diagnostic_audit/report.html).
- Đã đối chiếu **5.942 khoảng phiên**, gồm **1.248 khoảng chứa cuối tuần**: mọi daily crypto return được cộng đủ, các biến thay đổi và khoảng ngày khớp giá gốc. Không phát hiện lỗi bỏ crypto weekend returns.
- Tương quan phần dư đáng chú ý còn ở VIX/USD/2Y, với cả own và cross correlations. Bảng Pearson xếp hạng mang tính mô tả, không phải phân rã Portmanteau hay kiểm định ý nghĩa từng ô; Ljung–Box từng phương trình chỉ là chỉ báo phụ.
- Phát hiện USD trống trong raw ở **22, 25, 26/01/2016**, dù VIX/2Y/10Y có giá, tạo khoảng common-session **21–27/01/2016 dài 6 ngày**, chứa ETH return khoảng **+47,33%**. Chưa xác minh nguồn online, chưa sửa hoặc nội suy dữ liệu.
- ADF bác bỏ unit root nhưng KPSS bác bỏ level stationarity của ETH return ở full/pre-2020. Ghi rõ kết quả mâu thuẫn; không tự differencing thêm.
- **21/21 đối chiếu dữ liệu/bảng đã đạt** và hash xác nhận file nghiên cứu cũ giữ nguyên. Đây không phải kết luận mô hình đã đạt chẩn đoán thống kê: cả 12 VAR weekday+gap vẫn bác bỏ whiteness.
- Tại thời điểm audit, đề xuất xác minh ba ngày USD rồi mới xét lag sensitivity. Hai bước đã được thực hiện sau khi thống nhất; xem các mục kết quả phía trên.

Chạy lại audit từ snapshot đã có, không fit mô hình:

```powershell
py -3.11 audit_var_diagnostics.py
```

## VAR bổ sung đã được đồng ý: weekday và khoảng cách phiên

- Báo cáo bổ sung: [outputs/research/var_calendar_extension/report.html](outputs/research/var_calendar_extension/report.html).
- Đặc tả: Tuesday–Friday dummies với Monday làm tham chiếu, và `extra_calendar_days = elapsed_calendar_days - 1`. Giữ hệ biến, thứ tự shock và miền chọn lag tối đa 10 như baseline.
- Đã chạy baseline/weekday-only/gap-only/weekday+gap, BIC và AIC riêng, cho BTC/ETH và full/pre/post-2020: **48 hệ VAR**.
- Cả **12 hệ weekday+gap** vẫn bác bỏ adjusted Portmanteau whiteness ở mức 5%. Tất cả hệ ổn định, nhưng thêm calendar controls chưa giải quyết hạn chế phần dư. Không coi p-value tăng hoặc hệ ổn định là bằng chứng mô hình đã đạt.
- Các hệ kết hợp chọn cùng lag và có cùng số quan sát với baseline tương ứng, nên so sánh IRF không bị lẫn thay đổi lag/sample. IRF là phản ứng có điều kiện giữ calendar path cố định, không mặc nhiên causal.
- Baseline, LP, event study và forecasting được giữ nguyên; mã kiểm tra đối chiếu SHA-256 của các file bảo vệ. Chưa chạy phần variance bổ sung.

Chạy lại riêng phần đã được đồng ý:

```powershell
py -3.11 research_var_calendar.py
py -3.11 validate_var_calendar.py
py -3.11 package_dataset.py --var-calendar
```

Kết quả được lưu riêng trong `outputs/research/var_calendar_extension/`; gói mới `topic09_var_calendar_extension_20261017.zip` không ghi đè ZIP baseline. Các điều chỉnh khác như bootstrap, mở rộng lag search hoặc thay loss/mô hình variance cần thống nhất trước khi chạy.

## Lượt nghiên cứu baseline ngày 17/10/2026

Theo yêu cầu bắt đầu thực hiện kế hoạch, đã chạy EDA, VAR/LP, interaction pre/post và stress, rolling sensitivity, event study FOMC, forecasting ngoài mẫu và tạo báo cáo/dashboard cục bộ.

- Báo cáo đầy đủ: [outputs/research/report.html](outputs/research/report.html).
- Tổng quan dạng Markdown: [outputs/research/report.md](outputs/research/report.md).
- Dashboard mở cục bộ: [outputs/research/dashboard/index.html](outputs/research/dashboard/index.html), tự chứa dữ liệu kết quả, không cần API.
- Notebook EDA: [notebooks/01_eda.ipynb](notebooks/01_eda.ipynb), chạy từ thư mục dự án hoặc notebooks; bản notebook để chạy lại, không giả lập cell outputs đã thực thi.
- Bảng số, forecasts từng origin, validation grid và diagnostics: `outputs/research/tables/`.
- Kiểm tra tính toàn vẹn: `outputs/research/validation_report.json`; kiểm tra logic dashboard: `outputs/research/dashboard_validation.json`.

Kết quả baseline có giới hạn cần giữ rõ: VAR ổn định nhưng residual-whiteness bị bác bỏ, kể cả đặc tả AIC; boosting variance có dự báo chạm floor làm QLIKE nhạy. Không tự thay đặc tả VAR, thêm mô hình variance hoặc thay loss sau khi thấy test. Những mở rộng ngoài bản baseline sẽ được trao đổi trước theo yêu cầu của người dùng. Kết quả hiện tại là bản nghiên cứu đầu tiên, không phải xác nhận mô hình đã đạt mọi chẩn đoán hoặc bằng chứng causal.

Biểu đồ PNG đã được kiểm tra trực quan. Dashboard đã kiểm tra 288 tổ hợp asset/method/regime/shock/horizon và liên kết tải file bằng Node; chưa kiểm tra render trực tiếp trong browser vì công cụ preview không khởi tạo được.

Chạy lại các phân tích (không tải lại nguồn):

```powershell
py -3.11 -m pip install --target .research_deps -r requirements-research.txt
py -3.11 run_research.py
node validate_dashboard.cjs
py -3.11 validate_research.py
py -3.11 package_dataset.py --research
```

Dependencies được cài riêng trong `.research_deps`, không đi kèm ZIP; phiên bản thư viện thực tế lưu trong `outputs/research/environment.json`. Gói nghiên cứu mới giữ nguyên raw snapshot và cả hai bảng forecasting đã chốt. Đặc tả chi tiết và giới hạn inference được nêu trong báo cáo; không diễn giải p-value không có ý nghĩa như bằng chứng không tồn tại tác động.

## Thiết kế đã chốt ngày 17/10/2026

**Baseline không MOVE. Phân tích lịch sử giữ toàn bộ mẫu khả dụng. Forecasting gồm cấu hình không USD trên mẫu dài và cấu hình có USD vintage từ 2019, cộng một cặp so sánh trên cùng mẫu từ 2019.** Không nối chỉ số USD cũ vào baseline. Lần cập nhật này dùng nguyên snapshot tải ngày 16/10, không tải thêm giá mới.

| Cấu hình | BTC | ETH | Phạm vi origin đủ dữ liệu |
| --- | ---: | ---: | --- |
| `no_usd_long` | 3.206 | 2.783 | BTC: 03/01/2014–14/10/2026; ETH: 09/09/2015–14/10/2026 |
| `common_no_usd` | 1.929 | 1.929 | 05/02/2019–14/10/2026 |
| `common_with_usd` | 1.929 | 1.929 | 05/02/2019–14/10/2026 |

Sáu bảng `forecast_{btc,eth}_{no_usd_long,common_no_usd,common_with_usd}.csv` là đầu vào đã lọc complete-case theo từng tài sản. `research_design.json` khai báo danh sách feature/target/metadata; `forecast_sample_summary.csv` báo cáo cỡ mẫu; `forecast_design_checks.json` kiểm tra tính đồng nhất. Kết quả fit mô hình, RMSE và kiểm định nằm riêng trong lượt nghiên cứu baseline, không nằm trong các bảng thiết kế này.

Feature cơ sở gồm: return/squared return/volatility30 hiện tại của chính tài sản; VIX change lag1 proxy; 2Y/10Y/Fed Funds latest-known changes; S&P/gold return lag1 proxies; WTI latest-known log change; NFCI vintage level. Bản `common_with_usd` chỉ thêm `broad_usd_pit_change`, từ 11 lên 12 features. Các cột ngày, `post2020`, `split` và hai targets không được tự động đưa vào feature matrix. Metadata PIT vẫn có trong panel nguồn để tra cứu vintage.

**Quy tắc so sánh:** đánh giá đóng góp của USD bằng cặp `common_no_usd` và `common_with_usd`. Hai bảng có cùng origin dates, target values, features chung và train/validation/test dates. Dùng cùng thuật toán, ngân sách tuning và quy trình đánh giá; mô hình/scaler được fit riêng trong từng cấu hình nhưng cùng lịch dữ liệu. Không lấy kết quả `no_usd_long` so trực tiếp với `common_with_usd` để kết luận hiệu ứng USD vì độ dài lịch sử training khác nhau. Mẫu dài là benchmark riêng.

Phân chia mặc định theo **ngày của target**: train trước 01/01/2023, validation từ 01/01/2023 đến 31/12/2024, test từ 01/01/2025. Mỗi bản common có 980 train, 501 validation, 448 test. Đây là quy ước tái lập mặc định, chưa sử dụng test để lựa chọn mô hình. Nếu đổi mốc, sửa thống nhất cả hai cấu hình. Khi mô phỏng retraining tại đầu ngày UTC, cần kiểm tra cả thời gian nhãn training đã khả dụng, không chỉ split theo ngày.

Không nội suy hoặc điền 0 cho market returns. Những origin thiếu bất kỳ feature đã khai báo hoặc thiếu target bị loại; vì market lag1 proxies không có mọi ngày, đây là tập origin không liên tục, **target vẫn là ngày UTC kế tiếp, không phải dòng kế tiếp**. WTI log change không xác định quanh quan sát giá âm cũng làm origin tương ứng không đủ điều kiện. Ngày common đầu tiên là 05/02/2019 sau khi đủ USD change và toàn bộ features; trước 2020 chỉ còn 229 quan sát trong common, nên phân tích forecasting pre/post có hạn chế về cỡ mẫu.

Panel lịch sử `daily_research_latest.csv` vẫn giữ **4.671 ngày 2014–2026**, không cắt theo vintage USD. Các giới hạn revision của nghiên cứu ex post và feed thị trường proxy ở phần sau vẫn áp dụng.

## File sử dụng

Tất cả bảng kết quả nằm trong `data/processed/`, CSV UTF-8 có BOM, dấu phân cách phẩy, số thập phân dấu chấm.

| File | Mục đích |
| --- | --- |
| `daily_research_latest.csv` | Panel đầy đủ 7 ngày/tuần, giá gốc, biến đổi, cờ post2020. Macro là vintage hiện tại: dùng phân tích lịch sử, không coi là forecasting point-in-time. |
| `btc_core_complete_sessions.csv` | Những ngày đủ BTC, ΔVIX, USD return, Δ2Y, Δ10Y. |
| `btc_eth_core_complete_sessions.csv` | Mẫu giao nhau có thêm ETH return. |
| `btc_core_pre2020.csv`, `btc_core_post2020.csv` | Chia tại 01/01/2020. ETH vẫn thiếu tự nhiên trước khi có giá. |
| `forecast_origins_vintage_macro.csv` | Mỗi dòng là thông tin tại UTC close ngày t, ghép vintage macro thật và target ngày t+1. Các feature thị trường bổ sung được ghi rõ là proxy. |
| `*_vintage_periods.csv` | Lịch sử revision ALFRED dạng observation date, value, realtime_start_date, realtime_end_date. |
| `fomc_events_utc.csv` | Các sự kiện statement, press conference, monetary event và minutes. Có ET, UTC, cửa sổ thời gian, MP1/MP2 và yield changes. |
| `fomc_policy_surprises.csv` | STMT/PC/ME surprises do SF Fed công bố, đơn vị percentage point. |
| `fomc_crypto_statement_windows.csv` | BTC/USD, ETH/USD Coinbase từng phút quanh statement, return [-10,+20] phút, realized variance của cửa sổ và trạng thái coverage. |
| `coverage.csv` | Ngày đầu/cuối thực sự, số quan sát có/thiếu cho từng cột. |
| `data_dictionary.csv` | Định nghĩa, đơn vị, công thức, nguồn và timing cho các cột daily/forecast. |
| `quality_report.json` | Số dòng, các mẫu phân kỳ và kết quả kiểm tra. |
| `independent_audit.json`, `sp500_source_discrepancies.csv` | Đối chiếu snapshot ALFRED độc lập và chênh lệch giữa hai nguồn S&P 500. |

`data/raw/` giữ dữ liệu nguồn. `data/source_log.json` giữ URL, thời gian tải UTC, SHA-256 và trạng thái tải các nguồn daily/macro. Các part ZIP ALFRED là bản xuất gốc; file ZIP `_realtime` là bản hợp nhất và khử trùng lặp. Bảng sự kiện crypto có URL và hash riêng theo từng cửa sổ.

## Nguồn và lựa chọn biến

| Biến | Nguồn | Biến đổi chính và lưu ý |
| --- | --- | --- |
| BTC/USD, ETH/USD | [Coin Metrics Community API](https://docs.coinmetrics.io/api/v4/) `PriceUSD` | ln(Pt/Pt−1), decimal. Giá tổng hợp USD, không phải USDT và không phải một sàn đơn lẻ. |
| BTC/ETH volatility | Tính từ từng crypto return | `*_squared_return` = r². `*_vol30_annualized` = sqrt(365 × mean(r², 30 ngày)). Đây là trailing RMS proxy, không phải realized volatility intraday theo ngày. |
| VIX | [FRED VIXCLS](https://fred.stlouisfed.org/series/VIXCLS), nguồn Cboe | ΔVIX theo điểm index và Δlog(VIX). |
| Broad USD | [FRED DTWEXBGS](https://fred.stlouisfed.org/series/DTWEXBGS), Fed H.10 | Log return. **Không phải ICE DXY**. Không ghép lẫn hai chỉ số. |
| US 2Y, 10Y | [DGS2](https://fred.stlouisfed.org/series/DGS2), [DGS10](https://fred.stlouisfed.org/series/DGS10) | Δbps = 100 × chênh lệch yield tính bằng percent. Đây là constant maturity yields, không phải bond total returns. |
| Fed Funds | [DFF](https://fred.stlouisfed.org/series/DFF) | Effective rate và Δbps; thêm target lower/upper từ DFEDTARL/U. **ΔDFF không phải policy surprise**. |
| Monetary surprise | [SF Fed USMPD](https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/) | MP1/MP2 từ futures trong cửa sổ FOMC. MPS STMT/PC/ME là PCA shock do tác giả chuẩn hóa. |
| S&P 500 | [Yahoo Finance ^GSPC](https://finance.yahoo.com/quote/%5EGSPC/history/) | Log return của price index, không gồm cổ tức. FRED SP500 chỉ có lịch sử khoảng 10 năm nên giữ riêng làm đối chiếu, không dùng để cắt mất 2014–2016. |
| Gold | [Yahoo Finance GC=F](https://finance.yahoo.com/quote/GC%3DF/history/) | Log return của **chuỗi gold futures liên tục**. Không phải vàng spot/LBMA. Contract roll có thể tạo thay đổi giá không phải biến động spot. |
| Oil | [FRED DCOILWTICO](https://fred.stlouisfed.org/series/DCOILWTICO), EIA | WTI spot Cushing. Log return bỏ trống khi giá hiện tại/trước đó không dương; thêm ΔUSD và Δasinh(price) cho robustness. |
| NFCI | [Chicago Fed](https://www.chicagofed.org/research/data/nfci/current-data), [ALFRED NFCI](https://alfred.stlouisfed.org/series?seid=NFCI) | Weekly level và weekly change. Bản daily có giá trị carried ghi rõ ex post; forecasting dùng vintage thực. |
| MOVE (optional) | Chưa cung cấp | Endpoint thử trả HTTP 429. Không thay bằng VIX/VVIX và không tạo dữ liệu giả. |

Return = log return dạng decimal: 0.01 xấp xỉ 1%, không nhân 100. Squared return dùng decimal². Yield level là percent: 4.00 → 4.10 tương ứng +10 bps.

Mẫu thực tế: **4.671 ngày** trong panel đầy đủ; BTC core đủ biến có **3.169 ngày** (1.482 trước 2020, 1.687 từ 2020); mẫu BTC+ETH core có **2.775 ngày**. Giá ETH bắt đầu 08/08/2015, return bắt đầu 09/08/2015 theo nguồn đã tải. Cửa sổ statement Coinbase có 95 BTC và 83 ETH đầy đủ minute candles; thêm 3 cửa sổ mỗi tài sản chỉ đủ endpoints.

Đối chiếu S&P có **6 ngày lệch ≥0,02 điểm trên 2.513 quan sát chung**, lớn nhất 5,28984 điểm ngày 11/08/2021. Giữ nguồn Yahoo thống nhất cho toàn chuỗi, không tự thay số chưa xác minh. Bảng chênh lệch giữ cả hai giá. Robustness nên kiểm tra cả ngày lệch và return ở phiên kế tiếp, vì thay một price level ảnh hưởng hai returns.

## Quy ước thời gian daily

1. `date_utc=t` là **ngày giao dịch UTC**, bắt đầu 00:00 UTC ngày t và đóng tại 00:00 UTC ngày t+1. `close_timestamp_utc` ghi t+1. Coin Metrics [định nghĩa PriceUSD](https://coverage.coinmetrics.io/asset-metrics/PriceUSD) là fixing close lúc 00:00 UTC ngày kế tiếp. `r_t=ln(Pclose,t/Pclose,t−1)`.
2. Biến Mỹ gắn theo **ngày phiên/ngày quan sát Mỹ t**, nằm trong ngày UTC t. S&P đóng cửa thường lúc 16:00 ET (20:00/21:00 UTC); nửa phiên đóng sớm. VIX dùng giá đóng cửa do nguồn công bố, không tự giả định là 16:00 ET. Lãi suất/commodity dùng observation date của nhà cung cấp. **Return của tài sản Mỹ là local-session close-to-close, không giả gọi là return 00:00 UTC**. Đây là quy tắc ghép với crypto UTC return, không đồng bộ giá của thị trường đã đóng cửa.
3. [H.15](https://www.federalreserve.gov/releases/h15/) công bố 16:15 ET ngày làm việc. [EFFR](https://www.newyorkfed.org/markets/reference-rates/effr) thường công bố khoảng 09:00 ET cho ngày làm việc trước đó. Broad USD có quan sát daily nhưng công bố qua H.10 theo lịch release; không dùng observation date như ngày biết dữ liệu.
4. Không nội suy giá crypto. Không forward-fill market return, không biến ngày nghỉ thành return 0. Market return lấy chênh lệch giữa hai **quan sát không thiếu liên tiếp của chính nguồn**, rồi mới ghép lịch daily. Vì vậy Monday S&P return có khoảng thời gian dài hơn một calendar day, còn BTC Monday return luôn là 24 giờ.
5. Các file `*_complete_sessions` chỉ là mẫu lọc quan sát, có khoảng trống cuối tuần/ngày lễ/ngày thiếu. Không coi bước trễ 1 dòng của các file này là trễ đúng 1 calendar day. Dùng panel đầy đủ để xây horizon theo ngày; nếu chạy VAR trên lịch phiên thì ghi rõ và xem xét gộp crypto returns theo khoảng giữa các phiên để làm robustness.

## Vintage và forecasting

`forecast_origins_vintage_macro.csv` dùng các vintage ALFRED của NFCI, USD, DGS2, DGS10, DFF, WTI. [ALFRED](https://alfred.stlouisfed.org/help) cho phép lấy các giá trị thực sự có trong cơ sở dữ liệu tại từng ngày lịch sử.

- Forecast origin cho dòng t là **00:00 UTC t+1**. Chỉ nhận record có `realtime_start_date ≤ t`, chưa hết hiệu lực và `observation_date ≤ t`. Vì archive chỉ có ngày, việc chờ đến hết ngày UTC là quy tắc bảo thủ; không khẳng định vintage có giờ công bố chính xác hay SLA khả dụng.
- `*_pit` là quan sát mới nhất có trong vintage ấy. `*_pit_obs_date` ghi observation date; `*_pit_vintage_date` ghi ngày update ALFRED gần nhất được nhận vào thông tin tại origin.
- `*_pit_change` là chênh lệch giữa hai observation gần nhất **trong cùng vintage**, không lấy diff giữa hai snapshot khác vintage. Nếu không có release mới thì feature giữ nguyên. Nó không phải daily shock hoặc revision surprise.
- NFCI công bố thường 08:30 ET thứ Tư, có ngày lùi do lễ và có revision. Không tự gán tất cả vào thứ Tư: dùng ngày vintage thực trong archive. [Chicago Fed giải thích lịch và revision](https://www.chicagofed.org/research/data/nfci/current-data).
- **DTWEXBGS chỉ có vintage từ 04/02/2019**. Giá lịch sử trước 2019 trong bản hiện tại là backcast, không phải dữ liệu từng được công bố dưới chỉ số này vào 2014. Feature USD PIT trước vintage đầu để thiếu. Không tự ghép với chỉ số broad goods cũ. Vì vậy mô hình forecasting dùng đầy đủ cùng DTWEXBGS sẽ có mẫu ngắn hơn nghiên cứu ex post.
- VIX/S&P/gold trong forecast là cột `*_lag1_proxy`: lịch sử feed hiện tại, trễ thêm 1 ngày lịch. **Không có archive thời điểm công bố/correction của chính feed**, nên toàn bộ panel này không được chứng nhận tuyệt đối không leakage. Các macro `_pit` mới được dựng từ lịch sử vintage; crypto PriceUSD cũng là lịch sử nhà cung cấp tải hiện tại, không có snapshot lịch sử riêng.
- `*_target_next_return`, `*_target_next_squared_return` là **nhãn t+1**, không phải feature. Dòng cuối để thiếu target. Chỉ fit scaler, chọn biến, siêu tham số trên training; chia theo thời gian, không random split. Tính volatility đã dùng cửa sổ lùi, không dùng centered window.
- Fed Funds target date là ngày hiệu lực, có thể khác giờ công bố FOMC; giữ trong panel nghiên cứu, không đưa target current-vintage vào feature forecasting.

Độ trễ/cột lag đơn thuần không xóa revision bias. MPS do SF Fed xây dựng bằng PCA/chuẩn hóa trên mẫu cập nhật là **thước đo shock phục vụ event study**, không tự coi là feature forecasting tính real time từ tham số đã biết trong quá khứ.

## Event study FOMC

Nguồn USMPD cập nhật ngày **17/09/2026**. Timestamp `date_time` gốc là Eastern Time. Code dùng múi giờ IANA `America/New_York`, tự xử lý DST, rồi đổi UTC. Ví dụ 14:00 ET là 18:00 UTC trong EDT hoặc 19:00 UTC trong EST. Không áp một offset cố định cho toàn bộ năm.

Cửa sổ đúng theo README của nguồn:

- Statement/minutes: từ −10 đến +20 phút quanh giờ thực tế của sự kiện.
- Press conference: từ −10 đến +60 phút quanh giờ bắt đầu thực tế.
- Monetary event: từ statement −10 phút đến press conference +60 phút; nếu không có conference thì dùng cửa sổ statement. Không cộng statement + conference + monetary event như ba shock độc lập.

Giữ đơn vị gốc: yield/futures rate changes theo **percentage point**, stock/FX returns theo **percent**. Thêm `MP1_bps`, `MP2_bps`, `UST2Y_bps`, `UST10Y_bps` = 100 × cột gốc. Không trộn DXY intraday của USMPD với broad USD daily.

`download_fomc_crypto.py` lấy minute candles trên Coinbase cho **statement windows**, gồm cả các sự kiện trước khi sàn có đủ lịch sử. Nó báo `no_history`, `missing_exact_boundary`, `endpoints_only` hoặc `download_failed` khi cần, không điền giá giả. Dữ liệu này là giá một sàn USD, khác nguồn tổng hợp Coin Metrics ở panel daily.

Return event dùng close của minute bucket kết thúc đúng boundary đầu/cuối: ln(Pclose,end−1min/Pclose,start−1min). Realized variance cửa sổ là tổng squared 1-minute log returns và chỉ tính khi có đủ minute candles. Độ phân giải một phút không thay cho tick/quote và last trade có thể cũ. Có return khi đủ hai endpoints nhưng thiếu nội bộ thì trạng thái `endpoints_only`. Timestamp có giây không tròn phút không được làm tròn ngầm. Xem [quy tắc candle và giới hạn lịch sử Coinbase](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles).

## Chạy lại

Yêu cầu Python 3.11+, có kết nối mạng cho bước download. Không yêu cầu FRED API key vì dùng public CSV và form xuất ALFRED; không hardcode secret.

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 download_data.py
py -3.11 download_vintages.py
py -3.11 build_dataset.py
py -3.11 download_fomc_crypto.py
py -3.11 audit_dataset.py
py -3.11 prepare_forecast_design.py
py -3.11 package_dataset.py
```

Downloaders dùng cache raw để tái lập bản tải này. Muốn refresh, lưu raw snapshot hiện tại sang thư mục phiên bản khác, rồi chạy downloader trong thư mục dự án bản mới với raw trống; đừng ghi đè bản nghiên cứu đã công bố. Muốn thay cutoff, cập nhật đồng nhất ngày trong scripts. Endpoint và quyền dữ liệu có thể thay đổi; nhật ký ghi rõ lỗi tải. Chưa có MOVE thì không làm hỏng những chuỗi core đã tải được.

CSV raw và script phân tích không cấp lại quyền phân phối dữ liệu của các nhà cung cấp. Khi công bố nghiên cứu, trích nguồn và giữ điều kiện sử dụng của từng nguồn. Trích USMPD: Acosta, Ajello, Bauer, Loria và Miranda-Agrippino (2025), *Financial Market Effects of FOMC Communication: Evidence from a New Event-Study Database*, SF Fed Working Paper 2025-30.
