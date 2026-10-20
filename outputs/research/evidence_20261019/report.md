**Chủ đề 9 — Kiểm tra nhận dạng nhân quả và dự báo realized variance**

Phiên bản riêng ngày19/10/2026, triển khai sau rà soát nghiên cứu và sự đồng ý của người dùng. Đã bảo toàn 1202 tệp dữ liệu, mô hình, kết quả và archive cũ. Không thêm MOVE, không đổi Broad USD thành DXY, không nối USDT vào baseline USD. [Dashboard tương tác](dashboard.html).

**Kết quả chính và cách diễn giải**

Policy coefficient trong cửa sổ phút vẫn âm trên toàn miền xoay tại calibration đã ước lượng cho BTC/ETH. Kiểm tra trước thông báo và tuần trước có 0 hệ số đạt BH; các chênh lệch policy thông báo-trước/tuần trước có 6/6 đạt BH. Đây là kiểm tra chống một số giải thích thay thế, chưa chứng minh exclusion hay nhận dạng nhân quả vô điều kiện. Regime interactions có20/256 đạtBH vớiHAC nhưng0/256 vớiHC3: kết luận khác biệt chế độ chưa vững theo lựa chọn suy luận.

HAR/HAR-X có 51/120 so sánh thuận lợi với benchmark đạt BH, nhưng macro ablation có **0/32 cải thiện đạt BH**. Các so sánh có tương quan với nhau, không phải51 phát hiện độc lập. Kết quả mới gợi ý cấu trúc bộ nhớ của RV hữu ích hơn một số benchmark ở mẫu này; chưa xác nhận giá trị gia tăng của macro hay khả năng dự báo tương lai. Target, nguồn giá và mô hình khác latency nên không so trực tiếp hai bảng loss để quy toàn bộ thay đổi cho RV.

**Sự kiện và đối chiếu nguồn**

Giữ75 sự kiện chung của FOMC study làm khung. Yêu cầu đủ bốn cửa sổ cho cả BTC/ETH còn72; ba sự kiện2016-09-21,2017-03-15,2019-10-30 mất do ETH thiếu cửa sổ bổ sung, không do hệ số/p-value. Trên giao nhau có đủ JK và hai BS series còn45 sự kiện. Không so nguồn trên các mẫu khác nhau rồi kết luận shock nào đúng hơn.

Workbook [Bauer–Swanson tại SF Fed](https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/) thực tế kết thúc13/12/2023. MPS_ORTH thiếu March–December2020 theo quy tắc của tác giả; giữ thiếu, không thế bằng MPS. Workbook có rate units theo percentage points, MPS chuẩn hóa unit ED4 impact; regression nhân biến shock10 tương ứng hệ số per+10bps. Chart CSV của SF Fed dùng bps, không trộn quy ước đó với workbook. BS và JK là những nhân tố có định nghĩa/chuẩn hóa khác nhau; thêm cột per+1 sampleSD để đối chiếu, không gọi chúng là cùng một shock.

| asset | shock | beta | beta_pct_per1sd | qvalue_bh | qvalue_hc3_bh | nobs |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | policy | -1.21877 | -0.538286 | 0.0472271 | 0.00289597 | 45 |
| BTC | information | 1.03736 | 0.195741 | 0.120736 | 0.331893 | 45 |
| BTC | bs_raw | -0.971907 | -0.461786 | 0.0841987 | 0.0583458 | 45 |
| BTC | bs_orth | -0.929167 | -0.399923 | 0.115247 | 0.134671 | 45 |
| ETH | policy | -1.63359 | -0.721498 | 0.0264082 | 0.0022726 | 45 |
| ETH | information | 2.43422 | 0.459317 | 0.0472271 | 0.174969 | 45 |
| ETH | bs_raw | -1.12831 | -0.536097 | 0.115247 | 0.155555 | 45 |
| ETH | bs_orth | -1.09969 | -0.473317 | 0.156324 | 0.186374 | 45 |

Cả BS raw và orthogonalized có dấu âm quanh công bố nhưng 0 hệ số BS announcement đạt BH32. Vì vậy kiểm tra chéo nguồn chưa xác nhận kết luận mạnh về significance. Không lấy việc JK có p nhỏ hơn làm bằng chứng JK nhận dạng đúng hơn.

**Falsification và direct contrasts**

Cửa sổ trước sớm[-70,-40], trước muộn[-40,-10], thông báo[-10,+20] phút; placebo đúng7 ngày trước, cùng local Eastern clock rồi chuyển UTC bằng America/New_York. Yêu cầu đủ31 endpoint-inclusive candles cho từng cửa sổ; so overlap mới/cũ không có close thay đổi. Loại ngày placebo có Statements/Press Conferences/Minutes/Monetary Events trong frozen USMPD. Chưa loại hết tin vĩ mô/crypto khác, nên không gọi đây là randomized experiment.

| asset | outcome | shock | beta | qvalue_bh | qvalue_hc3_bh | nobs |
| --- | --- | --- | --- | --- | --- | --- |
| BTC | announcement | policy | -1.18743 | 0.000179355 | 2.8351e-07 | 72 |
| BTC | announcement | information | 0.917484 | 0.0246738 | 0.222223 | 72 |
| BTC | placebo | policy | -0.319543 | 0.123291 | 0.317515 | 72 |
| BTC | placebo | information | 0.180627 | 0.609272 | 0.719655 | 72 |
| BTC | pre_early | policy | 0.0955994 | 0.538895 | 0.684668 | 72 |
| BTC | pre_early | information | -0.0408922 | 0.882041 | 0.884555 | 72 |
| BTC | pre_late | policy | 0.176642 | 0.535888 | 0.684668 | 72 |
| BTC | pre_late | information | -0.432601 | 0.538895 | 0.684668 | 72 |
| ETH | announcement | policy | -1.46715 | 0.000179355 | 4.50384e-06 | 72 |
| ETH | announcement | information | 1.47673 | 0.0806894 | 0.203559 | 72 |
| ETH | placebo | policy | -0.178617 | 0.538895 | 0.609112 | 72 |
| ETH | placebo | information | 0.0976264 | 0.788986 | 0.884555 | 72 |
| ETH | pre_early | policy | 0.171908 | 0.535888 | 0.609112 | 72 |
| ETH | pre_early | information | 0.0435355 | 0.882041 | 0.884555 | 72 |
| ETH | pre_late | policy | 0.333681 | 0.168086 | 0.609112 | 72 |
| ETH | pre_late | information | -0.490155 | 0.538895 | 0.684668 | 72 |

![Falsification windows and conditional95percent intervals](figures/falsification_windows.png)

HAC5 và HC3 là suy luận có điều kiện trên shock cố định; BH16 cho hệ số cửa sổ, BH32 cho nguồn và BH12 cho direct contrasts. Direct contrasts hồi quy chênh lệch outcome trên cùng X, giữ covariance. Không suy từ một p-value có ý nghĩa và p-value khác không có ý nghĩa sang khác hệ số. Không bác bỏ pre-event/placebo không chứng minh exogeneity.

**Toàn miền xoay và generated-shock uncertainty**

Thay ba điểm xoay bằng giới hạn giải tích trên toàn khoảng góc hợp lệ của normalized QR. Với a=R12/R11,b=R22/R11: stock impact policy=a−b tan(theta), information=a+b cot(theta); outcome coefficient là(rate slope+stock slope×stock impact)/10. Endpoint limits có thể vô hạn khi component variance tiến về0. Dải sau là infimum/supremum của point estimates, không phải confidence set.

| asset | shock | lower_per10bps | upper_per10bps | lower_per1calibration_rms | upper_per1calibration_rms |
| --- | --- | --- | --- | --- | --- |
| BTC | policy | -1.95619 | -0.711312 | -0.736185 | -0.468365 |
| BTC | information | -0.1136 | ∞ | -0.0614823 | 0.567981 |
| ETH | policy | -2.52303 | -0.794652 | -0.946189 | -0.523241 |
| ETH | information | 0.0352048 | ∞ | 0.0190535 | 0.788579 |

Đặc biệt policy BTC có miền khoảng[−1,956;−0,711], ETH[−2,523;−0,795] điểm phần trăm/+10bps. Information BTC có thể đổi dấu và unbounded phía trên; ETH information cũng unbounded theo chuẩn hóa này. +1 calibration RMS cho một cách chuẩn hóa hữu hạn khác, không phải SD trong75 sự kiện crypto và không phải giả định nhận dạng mới.

999 circular block bootstrap draws, block8 author events: resample toàn334 author rows, fit lại PCA năm rate derivatives, scaling theo ED4, QR covariance và outcome regressions theo matched event multiplicities. Không chỉ bootstrap phần dư hồi quy cuối. Khoảng dưới là percentile95% tại **median rotation**, pointwise, chưa điều chỉnh multiplicity và không bao phủ toàn structural identified set.

| asset | shock | beta | lower95_percentile | upper95_percentile | successful_draws |
| --- | --- | --- | --- | --- | --- |
| BTC | policy | -1.16305 | -1.73997 | -0.332839 | 999 |
| BTC | information | 0.935847 | 0.129605 | 1.70217 | 999 |
| ETH | policy | -1.42184 | -2.16339 | -0.565567 | 999 |
| ETH | information | 1.49225 | 0.144233 | 2.84799 | 999 |

![Rotation range versus sampling uncertainty](figures/rotation_and_sampling.png)

Mô phỏng kiểm tra riêng100 mẫu trong Gaussian two-variable calibration cho empirical coverage policy=91%, information=93% ở nominal95%, Monte Carlo SE tối đa0,05. Nó không xác nhận coverage của full five-derivative pipeline, fat tails, nonstationarity hay identified set. Không gọi percentile intervals này là robust credible regions của Giacomini–Kitagawa. Sai khác slope tối đa1,75e−6 so nghiên cứu cũ được giải thích và kiểm tra bằng công bố shock làm tròn8 chữ số; bản cũ không đổi.

Phân rã MP/CBI/FRN theo nghiên cứu2026 chưa triển khai vì chưa xác minh được author shock file trực tiếp. Không invent FRN hay ép mô hình ba thành phần trên mẫu con yếu. Daily VIX/USD models vẫn là quan hệ có điều kiện nếu chưa có nhận dạng ngoại sinh riêng. LP hoặc heteroskedasticity-robust SE không tự tạo identification.

**Khác biệt pre/post và stress**

Pooled regression gồm cả hai shocks, regime indicator, cả hai shock×regime interactions và prior controls. Giữ75 sự kiện, stress định trước bằng VIX khả dụng trước sự kiện≥25. Direct differences được xét chung BH256:

| contrast | tests | BH_HAC | BH_HC3 | n0 | n1 |
| --- | --- | --- | --- | --- | --- |
| post2020 | 128 | 17 | 0 | 23 | 52 |
| stress | 128 | 3 | 0 | 63 | 12 |

**Không có hệ số regime interaction nào đạtBH vớiHC3**, dù20/256 đạtBH vớiHAC. Trước2020 chỉ23events, stress12events. Chưa có full-stage bootstrap cho interaction specification. Vì vậy không kết luận chế độ làm tác động mạnh hơn một cách vững, không gọi đây là thay đổi cơ chế nhân quả đã xác nhận. Không thay các kết quả subgroup cũ bằng bảng này.

**Realized variance: dữ liệu và timing**

Tải250 archive Binance spot5m BTCUSDT/ETHUSDT từ2017-08 đến2026-09 và daily October đến15/10/2026; tổng ZIP raw khoảng98MB. Xác minh publisher CHECKSUM và ZIP CRC. Nguồn chuyển ms→microseconds từ2025 được parse riêng. Có257 nến/asset lệch opening grid hoặc non-nominal close time; lưu nguyên raw và danh sách loại, không làm tròn timestamp. Một số ngày khác thiếu grid; chỉ dùng ngày đủ288 r5 và96 r15 gồm midnight boundary. RV15 lấy từ cùng lưới5m, không suy RV từ cửa sổ phút FOMC. Mẫu forecast đầu09/10/2017, ngắn hơn lịch sử baseline2014–2026.

Target là tổng variance D…D+h−1 với h=1/7, đơn vị decimal log return squared, khác bình phương tổng return7 ngày. HAR regressors RV tại D−3 và trung bình7/30 ngày kết thúc D−3; macro/vintage dùng frozen information row D−3, market proxies quan sát D−4. Không carry market returns trên ngày nghỉ; no crypto bridge/fill. Cấu hình long own/macro cùng origins; ba common variants cùng origins và USD vintage từ2019.

Tại refit đầu tháng, chỉ dùng label available≤origin−24h; label availability=D+h+1. Validation2023–2024 cũng purge các nhãn chưa khả dụng trước first test minus24h. Chọn cửa sổ730/1460/expanding bằng validation QLIKE, không dùng test. Log HAR/HAR-X OLS có training-only scaling và residual smearing; lưu880 monthly test artifacts. Không refit40 latency models cũ, không thêm learner phi tuyến trong nhánh này.

**Benchmark và đánh giá**

Trailing30, EWMA0,94 và zero-mean Gaussian-QMLE GARCH(1,1) cùng source/cutoff. GARCH expanding parameters refit monthly, filter đến D−3; tổng forecast steps3…h+2 mới trùng target khi có buffer.92 parameter fits gồm validation/test. Missing daily return là trạng thái unobserved, GARCH cập nhật conditional expectation; không điền giá hay coi đó là observed zero return. Mọi variance prediction dương, không prediction floor.

QLIKE chính=log(pred)+actual/pred; MSE phụ. Paired losses trên cùng origins, calendar block30 ngày,999 draws, giữ missing-origin mask. Two-sided centered bootstrap p và percentile intervals là xấp xỉ dưới điều kiện dependence/stability, không uniform inference qua mọi regime. BH32 ablations và BH120 learned-vs-benchmark riêng; MCS90% cho8 series trên cùng origins của mỗi asset/sampling/horizon. Không áp Clark–West cho QLIKE.

| benchmark | comparisons | BH_wins_HAR | BH_losses_HAR |
| --- | --- | --- | --- |
| ewma | 40 | 7 | 0 |
| garch11 | 40 | 35 | 0 |
| trailing30 | 40 | 9 | 0 |

![Historical cumulative QLIKE benchmark comparisons](figures/rv_forecasting.png)

0/32 macro ablations đạt BH. GARCH không được giữ trong8 MCS; các HAR-X macro series đều được giữ, nhưng nhiều own-only forecasts cũng được giữ. MCS membership không chứng minh incremental macro skill. Thắng một benchmark khác với xác nhận giá trị của thông tin toàn cầu. Test2025+ đã xem, mọi kết quả là historical/exploratory. Không bảo đảm kết quả sẽ lặp lại trên giá USD, sampling khác hoặc nguồn real-time.

**Prospective và mức hoàn thành**

Đã capture 17/17 responses thật, giữ request, raw bytes, URL, receipt UTC và SHA256. Namespace vận hành riêng dùng protocol nguyên hash và40 latency models nguyên hash. Origin 20/10/2026 ghi 0 predictions do snapshot không đạt timing/receipt requirements; giữ missing attempts, không backdate. Evaluation vẫn theo fixed window/label timing; chưa có future score trong lần nghiên cứu này. Không deploy RV models, không tự cài scheduler.

Chạy hàng ngày khi vận hành: `py -3.11 run_evidence.py prospective`. Đây là thao tác thực tại thời điểm chạy, không cách tái tạo receipt trong quá khứ. Chưa có whole-feed historical PIT: market/crypto retrospective snapshots, macro date-level vintages và conservative buffer chỉ giảm một số rủi ro timing.

21/21 kiểm tra độc lập và7 edge guards đạt, gồm all-day RV rebuild, toàn bộ HAR/GARCH forecast replay, bootstrap/MCS replay, pooled contrasts và first-stage bootstrap checks. Các kiểm tra tính toán không xác nhận causal assumptions hay future skill.

Trên artifact checkout đã freeze: `py -3.11 run_evidence.py validate`, rồi `product`; dashboard QA bằng Node. `rv_prepare/rv_fit/all` chỉ cho phiên bản fresh chưa freeze, không ghi đè model đang lưu. Muốn thay thiết kế phải dùng version riêng và thông báo trước.

[Validation](independent_validation.json) · [thiết kế khóa](../../../config/evidence_20261019.json) · [nguồn](rv_source_manifest.json) · [audit timestamps](archive_parsing_audit.csv) · [nến loại](invalid_source_candles.csv) · [event exclusions](falsification_audit.csv) · [source comparisons](source_comparison.csv) · [direct contrasts](falsification_contrasts.csv) · [rotation bounds](full_rotation_ranges.csv) · [bootstrap draws](joint_generated_shock_bootstrap.npz) · [interaction tests](regime_interaction_tests.csv) · [sample summary](rv_sample_summary.csv) · [monthly windows](rv_selected_windows.csv) · [test predictions](rv_test_predictions.csv) · [macro ablations](rv_ablation_tests.csv) · [benchmark tests](rv_benchmark_tests.csv) · [MCS](rv_model_confidence_sets.csv) · [prospective](prospective/namespace_audit.json) · [literature review](../../../paper/causality_forecast_literature_review_20261019.md).
