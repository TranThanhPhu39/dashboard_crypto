# Timing/PIT và untouched OOS: bằng chứng phương pháp và hướng xử lý cho Chủ đề 9

Ngày rà soát: **19/10/2026**. Phạm vi: đọc nghiên cứu và tài liệu gốc, đối chiếu với cấu hình đã lưu, đề xuất cách khắc phục. **Chưa thay dữ liệu, mô hình, cutoff, loss, mẫu hoặc protocol prospective.** Các phương án triển khai bên dưới là đề xuất của nhóm nghiên cứu từ tài liệu, không phải kết quả thực nghiệm mới.

## 1. Kết luận có thể áp dụng

Có cách cải thiện cả hai vấn đề. Với PIT, cần tái dựng bộ thông tin theo phiên bản dữ liệu và thời điểm khả dụng, đồng thời công khai giả định cho những nguồn thiếu lịch sử chỉnh sửa. Với OOS, cần tách phát triển mô hình khỏi đánh giá; có thể bổ sung kiểm định lịch sử bằng nested rolling-origin và một kỳ prospective độc lập ngắn hơn một năm.

Không cần đặt tiêu chuẩn bất khả thi rằng phải chứng minh tuyệt đối mọi tick chưa từng bị sửa. Cần bằng chứng phù hợp với tần suất nghiên cứu, kiểm tra kỹ thuật, giả định có căn cứ và giới hạn diễn giải. Ngược lại, thêm lag, đổi cách chia mẫu hoặc chạy thêm bootstrap không tự loại bỏ revision bias hay xóa việc lựa chọn thiết kế sau khi xem test.

**Untouched là thuộc tính của quy trình sử dụng dữ liệu.** Xem điểm test một lần để báo cáo theo thiết kế đã khóa là bình thường. Dùng điểm đó để sửa thiết kế rồi báo lại trên cùng test mới tạo rủi ro lựa chọn thích nghi. Tập lịch sử giữ kín thực sự từ đầu có thể là test độc lập; không nhất thiết mọi nghiên cứu phải đợi dữ liệu chưa xảy ra. Trường hợp repo này chưa xác lập được tập lịch sử như vậy cho cấu hình cuối. [Cawley–Talbot (2010)](https://www.jmlr.org/papers/v11/cawley10a.html).

## 2. Nghiên cứu gốc: họ xử lý thế nào và kết quả ra sao?

Các bản toàn văn được đọc tập trung vào thiết kế dữ liệu, thuật toán đánh giá, giả định và phần kết quả liên quan; không phải replication. Những mục chỉ tiếp cận abstract/summary được ghi riêng.

| Tài liệu | Phương pháp hoặc kết quả liên quan | Ý nghĩa đối với repo; giới hạn |
| --- | --- | --- |
| **Croushore–Stark (2001), Journal of Econometrics**; đọc WP 99-4, mục II và VII–VIII. [Bài](https://www.sciencedirect.com/science/article/pii/S0304407601000720), [WP toàn văn](https://www.philadelphiafed.org/-/media/FRBP/Assets/working-papers/1999/wp99-4.pdf) | Lưu các vintage theo thời điểm. Trong minh họa AR/BAR, forecast có thể khác giữa real-time và bản sửa cuối, nhưng RMSE không nhất thiết khác nhiều; một số kết luận khác nhạy với vintage. | Phải đo ảnh hưởng của revision trên cùng mẫu, không mặc định sửa PIT luôn làm điểm số xấu đi. Bộ dữ liệu vĩ mô trong bài không thay thế dữ liệu crypto/ngày của repo. |
| **Amburgey–McCracken (2023), Journal of Applied Econometrics**; đọc WP 2022-003B, mục 1–2 và kết luận phương pháp. [Bài](https://onlinelibrary.wiley.com/doi/abs/10.1002/jae.2943), [WP toàn văn](https://s3.amazonaws.com/real.stlouisfed.org/wp/2022/2022-003.pdf) | Tái dựng vintage NFCI trước thời kỳ archive chính thức, dùng lịch phát hành và GDP vintage. Mục 2.1 giả định revisions của một số chuỗi tài chính/survey là nhỏ. Real-time NFCI có ích cho dự báo GDP ở đuôi, nhất là trước suy thoái. | Có tiền lệ dùng giả định rõ ràng cho dữ liệu khó khôi phục; không phải bảo đảm mọi financial series không sửa. Kết quả GDP không chứng minh macro sẽ dự báo crypto tốt. Tự tái dựng NFCI không cần thiết khi repo đã có ALFRED cho mẫu sử dụng. |
| **Gillet–Brave (2024), Chicago Fed Insights**, bài phân tích của nhà cung cấp NFCI. [Toàn văn](https://www.chicagofed.org/publications/chicago-fed-insights/2024/nfci-future-economic-growth) | Chỉ ra revision làm thời điểm NFCI vượt ngưỡng stress khác đi; dùng as-released NFCI và điều chỉnh release lag. Quan hệ dẫn dắt FCI-G vẫn còn nhưng yếu hơn; mẫu cũng thay đổi nên không quy toàn bộ chênh lệch cho revisions. | Đối chiếu đúng biến NFCI của đề. Dùng giá trị tuần được biết tại ngày phát hành; không gán ngược mức tuần mới cho những ngày trước công bố. |
| **Tashman (2000), International Journal of Forecasting**; đọc abstract và summary của nhà xuất bản. [Nguồn](https://www.sciencedirect.com/science/article/pii/S0169207000000650) | Phân biệt fixed/rolling origin, fixed/rolling window, cập nhật tham số và nhiều test periods. Đề xuất rolling-origin để giảm phụ thuộc vào một mốc chia mẫu. | Cơ sở cho backtest lịch sử nhiều giai đoạn. Tự thực hiện rolling-origin trên dữ liệu đã xem không làm chúng thành blind test mới. |
| **Cawley–Talbot (2010), JMLR**, đọc toàn văn các mục 1 và 5.1. [Bài và PDF](https://www.jmlr.org/papers/v11/cawley10a.html) | Lựa chọn siêu tham số cũng có thể overfit. Đánh giá phải bao gồm cả bước chọn mô hình, bằng một vòng đánh giá ngoài độc lập với vòng chọn bên trong. | Nested validation cần đánh giá cả thuật toán và quy trình chọn. Cách áp dụng cho chuỗi thời gian phải giữ trật tự thời gian; bài gốc không tự xác nhận một splitter cụ thể cho crypto. |
| **Bergmeir–Hyndman–Koo (2018), CSDA**, đọc mục điều kiện lý thuyết và kết quả mô phỏng. [Trang tác giả](https://robjhyndman.com/publications/cv-time-series/), [PDF](https://robjhyndman.com/papers/cv-wp.pdf) | K-fold có thể hợp lệ trong mô hình autoregressive với điều kiện về sai số không tương quan; không có kết luận mọi time series đều được chia ngẫu nhiên. | Không dùng bài này để hợp thức hóa random split cho bộ macro–crypto đang có phụ thuộc thời gian và thay đổi chế độ chưa kiểm soát đầy đủ. |
| **White (2000), Econometrica**, đọc abstract nhà xuất bản. [Nguồn](https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152) | Reality Check kiểm tra mô hình tốt nhất trong tập đã tìm kiếm có vượt benchmark hay không, thay cho chỉ kiểm định bản thắng như thể chưa từng thử mô hình khác. | Cần khai báo tập ứng viên và điều kiện bootstrap. Không sửa dữ liệu bị nhìn trước hay tạo lại untouched sample. |
| **Hansen (2005), JBES**, đọc mục 1–2 và mô tả bootstrap. [DOI](https://doi.org/10.1198/073500105000000063), [toàn văn lưu tại trang Kevin Sheppard](https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Hansen.pdf) | SPA cải thiện power so với Reality Check trong thiết kế của bài. Trang 366 nêu hạn chế: không bao quát ước lượng tham số theo recursive scheme; cho phép fixed hoặc rolling theo điều kiện tương ứng. | Không áp SPA gốc máy móc cho tất cả HAR/GARCH có expanding refit trong repo. Nếu nghiên cứu thêm, nhánh latency frozen gần với fixed scheme hơn; vẫn phải xét dependence/stability và mẫu loss chung. |
| **Dwork và cộng sự (2015), NeurIPS**, đọc phần reusable holdout và Thresholdout. [Toàn văn](https://proceedings.neurips.cc/paper_files/paper/2015/file/bad5f33780c42f2588878a9d07405083-Paper.pdf), [bản mở rộng](https://arxiv.org/abs/1506.02629) | Holdout được truy cập qua cơ chế kiểm soát thông tin, có bảo đảm dưới các điều kiện của phương pháp, gồm thiết lập i.i.d. cho Thresholdout. | Không áp sau khi toàn bộ điểm test đã công khai để tuyên bố test được phục hồi. Chuỗi crypto phụ thuộc và loss không chặn cũng cần lý thuyết riêng; không phải lựa chọn triển khai ưu tiên. |
| **Choe–Ramdas (2024), Operations Research**, đọc bản v6, mục 4 và 6. [Toàn văn](https://arxiv.org/html/2110.00115v6), [DOI](https://doi.org/10.1287/opre.2021.0792) | Confidence sequences/e-processes cho phép giám sát tuần tự theo điều kiện phương pháp. Kết quả chính dùng bounded scores; mở rộng loss unbounded cần thêm điều kiện. Tác giả phân biệt thắng trong giai đoạn đã quan sát với thắng tương lai. | Có hướng xem giữa kỳ hợp lệ, nhưng không cắm trực tiếp QLIKE thô vào định lý bounded-score. Delayed labels/horizon nhiều ngày cần xử lý riêng. Không bảo đảm có power trên mẫu ngắn. |

## 3. Hướng xử lý PIT: thay tuyên bố tuyệt đối bằng bằng chứng kiểm tra được

### 3.1. Tách ba mốc thời gian và lịch sử phiên bản

Mỗi giá trị cần phân biệt: **observation time** là thời kỳ được đo; **public availability/vintage** là lúc phiên bản đó được công bố; **local receipt** là lúc hệ thống thật sự nhận bytes. Chúng không thay thế nhau. FRED cảnh báo release date của nhà cung cấp không nhất thiết là ngày dữ liệu đã xuất hiện trên FRED/ALFRED. [FRED release dates](https://fred.stlouisfed.org/docs/api/fred/releases_dates.html).

Đề xuất bảng bằng chứng ở cấp feature: `series_id`, `observation_time`, `vintage_date`, `source_release_time`, `release_time_evidence`, `received_at_utc`, `source_sha256`, `feature_cutoff`, `feature_age`, `assumption`. Nếu chỉ biết ngày vintage, ghi độ phân giải là ngày; không chế tạo một giờ công bố chính xác. Với nhánh historical thiếu receipt, để receipt thiếu và ghi giả định. Với prospective, dùng receipt thật; không backdate.

Quy tắc join phải chọn phiên bản và quan sát đáp ứng cutoff đã khai báo. Dữ liệu thuộc cùng ngày quan sát nhưng phát hành sau cutoff không được dùng. Giá trị sửa sau cutoff cũng không được dùng làm historical feature. Cần giữ một lịch sử giá trị đã biết, không chỉ một bảng current vintage có thêm cột lag. [ALFRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [các dạng dữ liệu vintage](https://alfred.stlouisfed.org/help/downloaddata).

### 3.2. Đối chiếu từng nhóm đang có

| Nhóm | Cách xử lý phù hợp | Tồn tại cần ghi rõ |
| --- | --- | --- |
| NFCI, Fed Funds, 2Y/10Y, WTI | Giữ ALFRED vintage thực đã có; audit ngày quan sát, ngày vintage, cutoff và unit. Với NFCI, phân biệt tuần được đo với ngày phát hành. | Vintage theo ngày không tự cung cấp intraday delivery time. Không xem việc thêm một ngày đệm là thay thế vintage. |
| Broad USD | Giữ forecasting có USD từ vintage 2019; đối chiếu với mô hình không USD trên đúng giao mẫu. | Không lấp trước 2019 bằng backcast rồi gọi PIT. Một chỉ số USD khác trước 2019 là biến khác, chỉ có thể là robustness riêng nếu được chấp thuận. |
| VIX, S&P 500, gold proxies | Audit fixing/close và timezone theo nguồn; giữ độ trễ đã chốt trong baseline. Có thể so nguồn độc lập và kiểm tra phần giá trị giao nhau. | Không mặc định mọi U.S. variable đóng cửa cùng một giờ. Lịch sử trả hôm nay chưa phải archive mọi phiên bản đã được cung cấp trong quá khứ. |
| Coin Metrics USD | Kiểm tra date label và thời điểm close theo định nghĩa PriceUSD; giữ raw snapshots và receipt cho prospective. | Tài liệu định nghĩa timestamp không phải chứng nhận không có chỉnh sửa. Nguồn thứ hai là kiểm tra measurement, chưa phải vintage thay thế. [Định nghĩa PriceUSD](https://github.com/coinmetrics/docs-website/blob/master/asset-metrics/market/priceusd.md). |
| Binance USDT RV | Giữ checksum, unit parsing, raw và cờ chất lượng đã có; nghiên cứu nguồn và ngày archive bị thay thế khi cần. | Binance công bố rằng archive có thể được sửa và có changelog checksum cũ/mới. Checksum xác nhận bytes tải được, không xác nhận chúng đã tồn tại như thế ở một origin lịch sử. [Tài liệu chính thức](https://github.com/binance/binance-public-data#updates). |

NFCI là ví dụ cụ thể: nhà cung cấp ghi lịch thường vào thứ Tư 08:30 ET, đo tới thứ Sáu trước đó; lịch có thể chuyển vì ngày lễ. Điều kiện đúng là lịch/vintage thực của từng release, không phải gắn một giờ cố định cho mọi tuần. [Chicago Fed FAQ](https://www.chicagofed.org/~/media/publications/nfci/nfci-faqs-pdf.pdf).

### 3.3. Sensitivity có thể làm trong phiên bản nghiên cứu riêng

**So vintages trên cùng mẫu:** đối chiếu as-of với latest-vintage tại cùng origins, cùng thuật toán và target. Tách thay đổi do revision khỏi thay đổi do mất quan sát. Chênh lệch đo được mới cho biết ảnh hưởng của giả định; không dự đoán trước chiều thay đổi metric.

**So quy tắc timing:** so baseline D−3 với một quy tắc dựa trên release/receipt được chứng minh hoặc thêm độ trễ bảo thủ; công bố mức giảm độ phủ và tuổi thông tin. Không chạy nhiều lag rồi chọn lag có test đẹp nhất. Nếu thay feature definition hoặc timing, đó là phiên bản mới cần được thống nhất trước.

**Ablation về bằng chứng dữ liệu:** loại riêng những feed có giả định revision yếu nhất để xem kết luận còn giữ được không, ghép đúng ngày giữa các mô hình. Đây là kiểm tra độ phụ thuộc vào giả định, không phải xác nhận toàn bộ dữ liệu đã đạt PIT. Dữ liệu không có archive quá khứ không thể phục hồi chỉ bằng mã; cần archive ngoài, tái dựng có căn cứ, hoặc giới hạn tuyên bố.

## 4. Hướng xử lý OOS và điều gì không thể “sửa hồi tố”

### 4.1. Nested rolling-origin: tăng chất lượng backtest lịch sử

Đề xuất áp dụng cho một tập thuật toán và grid đã khai báo trước. Tại mỗi outer origin, inner rolling validation chỉ dùng quá khứ để chọn tham số; scaler, imputer, lựa chọn features và smearing cũng chỉ fit trên training. Sau đó refit theo quy tắc cố định và phát forecast cho outer period. Lặp qua nhiều giai đoạn, báo toàn bộ outer losses. Đây là thiết kế kết hợp tư tưởng nested evaluation và rolling-origin, không phải sao chép một định lý duy nhất cho mọi macro–crypto process.

Purge phải dựa trên `label_available_at <= fit_cutoff`, cùng cutoff của từng feature. Với target tổng RV bảy ngày và nhãn trễ, chỉ xóa bảy hàng trước test có thể sai trên tập origin không liên tục. `TimeSeriesSplit.gap` đếm số mẫu, không đếm ngày lịch hoặc chứng minh nhãn đã khả dụng. [Tài liệu TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

Vì thiết kế nghiên cứu đã chịu ảnh hưởng của việc xem test cũ, outer backtest mới trên lịch sử đó vẫn nên ghi **historical OOS, exploratory**. Nó giảm lỗi tuning ở cấp fold nhưng không xóa lựa chọn thích nghi ở cấp toàn dự án.

### 4.2. Holdout mới: có thể ngắn hơn một năm

Muốn có đánh giá độc lập cho cấu hình cuối, có thể đề xuất một **protocol pilot ngắn hạn** và khóa trước outcomes của pilot. Protocol một năm hiện tại vẫn giữ nguyên trong lần research này. Nếu chuyển sang lịch chấm khác, phải lưu phiên bản mới và công khai thay đổi; không ghi đè bản cũ hoặc đọc score sớm rồi tuyên bố vẫn tuân thủ nguyên protocol cũ.

Ví dụ thảo luận, **chưa chốt và chưa chạy**: một pilot tám tuần bắt đầu sau khi điều kiện thu thập sẵn sàng; ghi trước start/end, mô hình, target, loss, primary comparison và cách xử lý missing. Không kéo dài/rút ngắn theo p-value. Nếu pilot dùng cùng forecasts/outcomes với thí nghiệm một năm thì chấm sớm thực chất thay đổi chính sách evaluation gate; chỉ đổi namespace không giải quyết xung đột này. Cần được thống nhất và khóa chính sách mới trước outcomes sẽ được đánh giá; nếu vẫn giữ nguyên cổng cũ thì chưa chấm hiệu quả những forecasts đó trước hạn. Không coi hai bảng dùng cùng quan sát là hai replication độc lập.

Để khả thi cho bài môn học, có thể chọn trước một primary macro-vs-own comparison và một target; BTC là primary, ETH là secondary nếu mục tiêu đã được thống nhất. Không chọn primary bằng cách nhìn xem mô hình nào thắng trên test đã xem. Chọn mô hình mới, refit hoặc triển khai nhánh RV đều cần thiết kế riêng.

**Độc lập về quy trình không đồng nghĩa đủ power.** Tám tuần lịch không phải tám tuần đủ origins; market-day rule, ngày nghỉ, missing feeds và dependence làm số thông tin ít hơn. Báo số forecasts hợp lệ, losses/CI và thiếu dữ liệu; nếu chưa đủ thông tin thì kết luận chưa rõ. Không có quy tắc trong các tài liệu đã đọc rằng phải đủ một năm hoặc một ngưỡng số ngày phổ quát mới được gọi là OOS.

### 4.3. Điều chỉnh data snooping và kiểm tra giữa kỳ: lựa chọn phụ

Repo đã có BH và MCS cho các family đã khai báo. SPA/Reality Check có thể bổ sung một câu hỏi khác: có ứng viên nào trong tập so sánh vượt benchmark không? Phải giữ tập ứng viên, lịch loss ghép và giả định suy luận phù hợp. Không thay kiểm định hiện tại sau khi thấy p-value chỉ để đạt significance; không xem family của bản cuối là toàn bộ lịch sử nghiên cứu nếu đã thử nhiều thiết kế khác.

Reusable holdout không phải công cụ tẩy việc đã xem toàn bộ test. Anytime-valid inference có thể là hướng cho một nghiên cứu giám sát tương lai, nhưng cần loss và cơ chế nhãn phù hợp; không đưa QLIKE không chặn hoặc nhãn trễ vào một định lý bounded-score rồi tuyên bố có bảo đảm. Cả hai không phải bước triển khai ưu tiên cho repo hiện tại.

## 5. Phương án ưu tiên cho repo

Đây là đề xuất triển khai, **chưa được thực hiện trong lần research này**.

| Ưu tiên | Công việc | Sản phẩm kiểm chứng | Nó giải quyết đến đâu? |
| --- | --- | --- | --- |
| 1 | Audit provenance/timing từng feature; giữ nguồn và định nghĩa hiện tại | Bảng bằng chứng: vintage, release/receipt, cutoff, age, assumption; danh sách vi phạm nếu có | Chuyển nhận định PIT chung chung thành bằng chứng hoặc vấn đề cụ thể. Phát hiện leakage thật phải sửa phần bị ảnh hưởng. |
| 2 | Khóa sensitivity về vintage/nguồn/timing và chạy nested chronological backtest trong namespace riêng | Outer-fold forecasts, manifest fit/tuning, purge audit và matched loss comparisons | Cải thiện chất lượng historical OOS; chưa biến lịch sử đã xem thành untouched. |
| 3 | Nếu cần kết quả độc lập trước khi nộp môn, thống nhất protocol ngắn hạn mới trước outcomes; công khai nếu thay lịch chấm của cùng forecasts | Protocol/version chốt trước outcomes, ledger, coverage và đánh giá tại end đã chốt | Có thêm OOS độc lập nếu thực sự ghi trước outcome; có thể cho kết quả không rõ hoặc không thắng benchmark. Không vượt cổng cũ bằng đổi tên folder. |
| 4 | Nếu chưa đổi thiết kế, tiếp tục prospective một năm đang có | Actual receipts, frozen model hashes, immutable forecasts và labels khi tới hạn | Bằng chứng vận hành dài hơn; không cần đổi để trình bày kết quả lịch sử hợp lệ. |
| Tùy chọn sau | SPA hoặc phương pháp sequential với giả định đã kiểm chứng | Phân tích method/coverage riêng; giữ nguyên bảng BH/MCS cũ | Kiểm soát những dạng reuse/monitoring cụ thể; không thay thế PIT và một thiết kế đánh giá trung thực. |

Nếu không còn thời gian thu thập pilot trước hạn nộp, có thể hoàn thiện phần historical với nested backtest, sensitivity và giới hạn rõ ràng. Khi đó phải giữ trạng thái chưa có untouched evaluation cho cấu hình cuối; ghi hạn chế không tự hoàn thành mục checklist này.

## 6. Đối chiếu phần đã có và phần còn mới

**Đã có:** ALFRED cho macro, USD vintage từ 2019, lag/calendar alignment, purge theo nhãn, training-only preprocessing, snapshot bytes/receipt/SHA, frozen 40 latency models, các so sánh cùng mẫu, BH/MCS, immutable logger và sửa retry/chọn snapshot đủ dữ liệu. Lần vận hành gần nhất vẫn chưa có forecasts hợp lệ; đây không phải kết quả skill.

**Chưa có trong repo như một nghiên cứu hoàn chỉnh:** bảng tổng hợp mức bằng chứng PIT cho từng feature, sensitivity vintage/source theo một thiết kế thống nhất, nested outer-fold evaluation cho quy trình chọn mô hình cuối, và pilot độc lập ngắn hạn. Không cần thêm mô hình phức tạp chỉ để giải quyết các thiếu sót này.

[Thiết kế latency](../config/latency_20261019.json) · [Protocol đang khóa](../data/prospective/evidence_20261019/protocol.json) · [Báo cáo vận hành](../outputs/research/evidence_20261019/prospective_operations/report.html) · [Báo cáo evidence giữ nguyên](../outputs/research/evidence_20261019/report.html) · [Yêu cầu đã đối chiếu](requirements.md).

## 7. Cách diễn đạt kết quả sau khi áp dụng

Nếu audit và sensitivity hỗ trợ: “Nghiên cứu sử dụng historical as-of macro vintages, quy tắc khả dụng khai báo theo nguồn và các kiểm tra độ nhạy. Một số market/crypto feeds được xử lý theo giả định về lịch sử chỉnh sửa, được liệt kê riêng.” Không dùng câu khẳng định tuyệt đối nếu dữ liệu không cho phép kiểm chứng.

Nếu chỉ có backtest lịch sử: “Forecasts được xây theo trật tự thời gian, tuning nằm trong từng training window và nhãn được purge theo availability. Do quy trình phát triển đã sử dụng test trước đây, kết quả được xem là exploratory historical OOS.”

Nếu hoàn thành pilot mới: nêu đúng thời gian, số forecasts hợp lệ, số ngày thiếu, loss difference và uncertainty. Có thể gọi là prospective OOS theo thiết kế đã chốt; không chuyển tự động thành khẳng định sẽ tiếp tục thắng trong tương lai hoặc bằng chứng nhân quả.

Lần rà soát này đưa ra hướng xử lý có thể triển khai và căn cứ phương pháp. Không tạo forecast, không chạy mô hình mới và không thay bất kỳ protocol đã khóa nào.
