# Untouched OOS sau khi đã xem test: tài liệu bổ sung và phương án cho Chủ đề 9

Ngày rà soát: **20/10/2026**. Hạn nộp: **25/10/2026**. Đây là bản nghiên cứu phương pháp bổ sung cho [review ngày 19/10](pit_oos_remedies_review_20261019.md), đã đối chiếu với artifacts hiện tại. Không chạy lại mô hình, thay protocol, chấm prospective sớm hoặc sửa kết quả/dashboard trong lần rà soát này.

## 1. Kết luận để ra quyết định

**Có hướng xử lý, với hai mục tiêu khác nhau:** nâng chất lượng suy luận từ backtest lịch sử, hoặc tạo một đánh giá độc lập mới. Nested backtest và điều chỉnh data snooping phục vụ mục tiêu thứ nhất. Một holdout thật sự chưa tham gia phát triển, hoặc forecasts được ghi trước outcomes tương lai, phục vụ mục tiêu thứ hai.

Thiếu đánh giá độc lập mới không làm mọi kết quả lịch sử vô giá trị. Tuy nhiên, chạy lại trên cùng dữ liệu không tự phục hồi tính độc lập. Đề gốc có checklist “Có untouched out-of-sample test” tại dòng 280 của `09_global_financial_conditions_crypto.md`; không được đánh dấu hoàn thành mục đó chỉ vì đã có robustness hay đã mô tả hạn chế.

Đọc test một lần để báo cáo theo một quy trình đã chốt là bình thường. Rủi ro xuất hiện khi outcomes/điểm test ảnh hưởng tới lựa chọn features, timing, mô hình, loss, kỳ đánh giá hoặc kết luận được chọn báo cáo. “Untouched” nói về lịch sử sử dụng thông tin, không đơn thuần về tên thư mục hay ngày cắt mẫu.

## 2. Nghiên cứu và tài liệu gốc được đối chiếu

Đã đọc các phần phương pháp/kết quả liên quan được ghi dưới đây; không thực hiện replication các bài. Năm của working paper và bản xuất bản được phân biệt khi cần.

| Tài liệu; phần tiếp cận | Họ làm gì, kết quả liên quan | Áp dụng cho trường hợp hiện tại |
| --- | --- | --- |
| **Gillet (2024), Chicago Fed, Nowcasting Median Household Income with Mixed-Frequency Models**. Đọc mục Backtesting và kết quả. [Toàn văn](https://www.chicagofed.org/publications/economic-perspectives/2024/7). | Dùng ALFRED tái dựng thông tin, refit từng năm trong 2012–2022; gọi rõ là pseudo-OOS. Một số chuỗi thiếu vintage trước 2016 được lag theo lịch công bố và công khai thiếu kiểm soát revision. | Tiền lệ thực tế cho backtest lịch sử có ích dù không phải thử nghiệm prospective. Không biến giả định dữ liệu thành chứng nhận PIT. |
| **Cawley–Talbot (2010), JMLR**. Đọc mục 5–5.1 và minh họa selection bias. [PDF](https://www.jmlr.org/papers/volume11/cawley10a/cawley10a.pdf). | Tuning cũng có thể overfit; đưa cả training lẫn chọn mô hình vào vòng đánh giá. Bias có thể lớn hơn khác biệt giữa thuật toán. | Nested evaluation của repo là hướng xử lý đúng ở cấp fold. Việc thiết kế toàn dự án sau khi xem kết quả là cấp thích nghi khác. |
| **Cerqueira–Torgo–Mozetič (2020), Machine Learning**; preprint 2019. Đọc thiết kế và kết luận so sánh. [PDF](https://arxiv.org/pdf/1905.11744), [DOI](https://doi.org/10.1007/s10994-020-05910-7). | Thử trên 62 chuỗi thực và ba chuỗi mô phỏng. Với dữ liệu thực có nonstationarity, các phương pháp OOS giữ thứ tự thời gian cho ước lượng lỗi tốt hơn trong thí nghiệm của bài. | Giữ chronological outer/inner folds; không chuyển sang random split để tăng số điểm kiểm tra. Kết quả không bảo đảm mọi splitter đều hợp lệ với crypto. |
| **White (2000), Econometrica, A Reality Check for Data Snooping**. Đọc introduction và framework. [PDF](https://users.ssc.wisc.edu/~behansen/718/White2000.pdf). | Kiểm định liệu mô hình tốt nhất trong tập đã tìm kiếm có vượt benchmark sau khi tính việc thử nhiều mô hình. Thừa nhận time series thường chỉ có một lịch sử. | Có công cụ suy luận hồi cứu, không bắt buộc bỏ toàn bộ dữ liệu cũ. Cần phạm vi tìm kiếm đủ rõ và điều kiện phụ thuộc/ước lượng phù hợp. |
| **Hansen (2005), JBES, A Test for Superior Predictive Ability**. Đọc mục 1–2 và empirical application. [PDF](https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Hansen.pdf), [DOI](https://doi.org/10.1198/073500105000000063). | SPA studentize để giảm ảnh hưởng của ứng viên kém/biến động cao. Minh họa so 3.303 mô hình dự báo lạm phát bằng rolling window. Bài gốc không bao quát recursive expanding estimation. | Không cắm SPA gốc trực tiếp vào toàn bộ annual expanding nested forecasts. Cần thiết kế suy luận thích hợp; chưa triển khai trong review này. |
| **Rossi–Inoue (2012), JBES**. Đọc introduction và framework. [Bản tác giả](https://crei.cat/wp-content/uploads/users/working-papers/rossi_outofsample.pdf), [DOI](https://doi.org/10.1080/07350015.2012.693850). | Kiểm định độ vững với kích thước cửa sổ, xử lý rủi ro thử nhiều windows rồi chỉ báo kỳ có kết quả đẹp. Có xét fixed, rolling và recursive schemes theo điều kiện của bài. | Nếu nghiên cứu tiếp độ nhạy theo windows, phải tính cả việc tìm kiếm. Báo từng năm hữu ích nhưng chưa tương đương kiểm định chuyên biệt này. |
| **Bauer–Hamilton (2018), Review of Financial Studies**; đọc WP tháng 5/2017, mục 2.7 và kết luận. [WP chính thức](https://www.frbsf.org/wp-content/uploads/wp2015-15.pdf), [bản xuất bản trên trang tác giả](https://econweb.ucsd.edu/~jhamilto/pub_finance). | Tái xét sáu nghiên cứu bond risk premia bằng suy luận vững hơn và dữ liệu đến sau nghiên cứu gốc. Các predictors bổ sung hiếm khi hữu ích trên dữ liệu mới. | Một mở rộng không thắng benchmark vẫn là kết quả nghiên cứu có giá trị. Dữ liệu mới kiểm tra được tuyên bố cũ; không bảo đảm sẽ xác nhận nó. |
| **Dwork và cộng sự (2015), Generalization in Adaptive Data Analysis and Holdout Reuse**. Đọc mục 4.1. [Toàn văn](https://arxiv.org/html/1506.02629). | Thresholdout giới hạn thông tin trả về từ holdout, dùng ngưỡng, noise và query budget; không phải cung cấp toàn bộ test scores cho người phát triển. | Cơ chế cần được áp dụng khi truy cập holdout. Không có bảo đảm hồi tố cho test đã được xem ngoài cơ chế; thiết lập i.i.d./bounded queries không tự áp cho QLIKE crypto. |
| **Blum–Hardt (2015), ICML, The Ladder**. Đọc mô tả phương pháp trong trang proceedings. [Nguồn](https://proceedings.mlr.press/v37/blum15.html). | Leaderboard chỉ tiết lộ tiến bộ đủ lớn, giảm overfit do gửi mô hình nhiều lần. | Hướng thiết kế cho đánh giá tương lai có kiểm soát; không khôi phục test đã công khai. |
| **Choe–Ramdas (2024), Operations Research**. Đọc introduction, bounded-score framework và các phần mở rộng được nêu. [Toàn văn](https://arxiv.org/html/2110.00115), [DOI](https://doi.org/10.1287/opre.2021.0792). | Confidence sequences/e-processes cho phép theo dõi khác biệt score qua thời gian với kiểm soát sai số. Kết quả chính dùng bounded scores; có mở rộng cần điều kiện riêng. | Có thể thiết kế xem giữa kỳ hợp lệ. Không tự hợp thức hóa việc xem p-value thông thường nhiều lần hoặc áp định lý bounded-score cho QLIKE thô. |

**Lưu ý thuật ngữ:** các bài dùng “pseudo-OOS”, “real-time OOS” và “true OOS” theo những nghĩa chưa hoàn toàn thống nhất. Ví dụ [Bokun và cộng sự, FRED-SD, WP 2020-031](https://s3.amazonaws.com/real.stlouisfed.org/wp/2020/2020-031.pdf), mục 3.2, phân biệt real-time với pseudo-OOS dựa vào vintage. Bài đó không đủ để kết luận dữ liệu đã được giữ kín khỏi mọi quyết định của người nghiên cứu. Trong repo nên khai báo riêng **thông tin khả dụng tại origin** và **test có tham gia phát triển thiết kế hay không**.

## 3. Tình trạng repo sau khi đối chiếu

Đây là kiểm tra artifacts đã lưu, không phải một lần huấn luyện hay đánh giá mới:

- [Nested backtest](../outputs/research/pit_nested_20261020/report.html): outer folds 2023–2026, tuning theo thời gian ở vòng trong; purge theo label availability, preprocessing trong training. Có 640 model artifacts; validator đã replay 125.320 predictions và kiểm tra các cutoff.
- [Kết quả tổng hợp](../outputs/research/release_20261025/release_state.json): `native_asof_d3` có 3/32 so sánh macro cải thiện sau BH, nhưng mỗi cấu hình matched có 0/32. Không cấu hình nào có pooled learned-model benchmark wins sau BH. Không được bỏ qua các kết quả theo năm khi diễn giải tổng hợp.
- [Kiểm tra timing/vintage](../outputs/research/pit_nested_20261020/report.html): có matched as-of D3, latest-vintage D3 và as-of D4. Latest-vintage là đối chiếu ex post, không phải cấu hình forecast khả thi tại origin lịch sử.
- [Protocol prospective đang khóa](../data/prospective/evidence_20261019/protocol.json): từ 20/10/2026 tới trước 20/10/2027 UTC; 40 latency artifacts khác với 640 nested artifacts. Trạng thái release hiện ghi 0 forecasts và 0 labels được commit.

**Diễn giải từ lần rà soát này:** phần historical đã có các biện pháp quan trọng mà tài liệu đề xuất. Hạn chế còn lại nằm ở tính độc lập của thiết kế cuối với outcomes đã xem, không phải chỉ thiếu một lời gọi `train_test_split`. Kết quả hiện hỗ trợ câu “chưa có bằng chứng lợi ích dự báo gia tăng của macro ổn định qua các cấu hình”, không hỗ trợ câu “macro chắc chắn không có giá trị dự báo”.

## 4. Các phương án có thể áp dụng

| Phương án | Giải quyết được gì? | Điều kiện và giới hạn trong repo |
| --- | --- | --- |
| Chốt historical nested backtest, báo đầy đủ matched results, benchmark và sensitivity | Tạo kết quả thực nghiệm lịch sử minh bạch, tái lập; không cần chờ một năm để có một bài nghiên cứu lịch sử. | Đã có phần lớn. Kết luận trong phạm vi dữ liệu/thiết kế được đánh giá; checklist untouched vẫn chưa hoàn thành. |
| Holdout lịch sử thật sự chưa sử dụng, do cơ chế giữ kín kiểm soát | Có thể có đánh giá độc lập mà không phải chờ outcomes chưa xảy ra. | Phải chứng minh outcomes/metrics chưa ảnh hưởng tới thiết kế, chọn kỳ trước khi mở, và giữ cả kết quả không thuận lợi. Repo hiện chưa xác lập được tập như vậy. Không lấy đoạn đã xem rồi đổi tên thành holdout. |
| Dữ liệu mới sau khi khóa thiết kế; forecasts ghi trước outcome | Tạo prospective OOS mới; là cách trực tiếp nhất cho phần còn thiếu. | Khóa model/procedure, target, metric, benchmark, missing-data rule và lịch đánh giá trước dữ liệu liên quan. Có thể refit theo lịch đã khóa nếu protocol cho phép; protocol hiện tại dùng artifacts frozen. Cần đủ thông tin để kết luận, không chỉ có vài forecasts. |
| Reality Check/SPA hoặc kiểm định robustness với windows phù hợp | Giảm một số sai lệch do thử nhiều mô hình/cửa sổ trên lịch sử. | Cần xác định universe đã tìm kiếm và assumptions. Family BH hiện tại không tự bao trùm mọi thử nghiệm trong quá trình phát triển. Không tạo untouched data và không tự sửa leakage. |
| Reusable holdout/Ladder/sequential inference cho vòng nghiên cứu mới | Quản lý việc truy cập/giám sát kết quả về sau. | Phải chọn cơ chế và kiểm chứng điều kiện trước khi áp dụng. Không phải bước cần thêm chỉ để hoàn thiện dashboard hiện tại. |

Đổi nguồn BTC/USD sang một sàn khác trên cùng ngày có ích để kiểm tra measurement, nhưng không tự tạo độc lập với kết quả BTC của ngày đã xem. Tương tự, BTC/ETH có phụ thuộc chung; không coi hai tài sản là hai replication hoàn toàn độc lập. Thêm số bars intraday không tự cung cấp thêm cùng số quan sát độc lập cho câu hỏi dự báo daily đã chốt. Đây là suy luận thiết kế cho repo, không phải một kết quả empirical mới.

## 5. Hạn nộp 25/10 và các quy tắc có thể đang bị hiểu quá cứng

**Một năm không phải ngưỡng khoa học phổ quát của untouched OOS.** Đề gốc không quy định thời lượng đó; protocol hiện tại của dự án có quy định. Thời lượng phù hợp phụ thuộc horizon, mức cải thiện có ý nghĩa, độ biến động của loss differences, serial dependence, missing origins và số phép so sánh. Kỳ ngắn vẫn có thể độc lập về quy trình nhưng thiếu power.

Tương tự, buffer receipt 24 giờ là quy tắc bảo thủ đang dùng, không phải định nghĩa chung của OOS. Một thiết kế khác có thể dựa trên khả dụng thực trước forecast origin với bằng chứng phù hợp. Thay đổi nó phải xem lại feature definitions, train/deployment consistency và ngày bắt đầu đánh giá; không sửa hồi tố để nhận những forecasts đã bỏ lỡ.

Nếu muốn một pilot ngắn, có thể đề xuất một **phiên bản protocol mới cho dữ liệu tương lai**, khai báo trước những gì sẽ chấm. Nếu pilot dùng cùng forecasts/outcomes với protocol năm đang khóa, việc mở score sớm là sửa chính sách đánh giá: phải ghi nhận rõ, không lách bằng namespace khác. Không chọn ngày dừng sau khi thấy kết quả đẹp. Review này chưa kích hoạt hay sửa protocol nào.

Từ 20/10 tới hạn nộp chỉ có vài ngày lịch; còn latency, eligibility và label maturity. Với thiết kế hiện tại, không có cơ sở hứa sẽ thu đủ bằng chứng về skill trước hạn. Một pilot vận hành, nếu có dữ liệu hợp lệ, có thể báo coverage, receipt và forecast ledger; không mặc định đủ để xác nhận mức cải thiện dự báo. Không có cơ sở đặt một ngưỡng tùy ý như 30 ngày hay một năm rồi coi đó là bảo đảm power.

## 6. Khuyến nghị cho bài hiện tại

1. **Giữ kết quả historical làm kết quả chính**, gồm cả các mô hình không thắng benchmark. Không tiếp tục đổi model/timing/test period để tìm significance.
2. **Dùng mô tả chính xác:** “historical as-of nested backtest; kết quả khám phá sau quá trình phát triển” và tách rõ nhánh latest-vintage ex post. Việc đặt nhãn này không phủ nhận công việc đã hoàn thành.
3. **Không triển khai SPA máy móc.** Nếu bổ sung suy luận data snooping, cần một thiết kế riêng tương thích expanding estimation và toàn bộ universe có thể kiểm kê; báo song song kết quả cũ.
4. **Giữ prospective là bước xác nhận tiếp theo.** Chỉ đổi lịch/model nếu đã thống nhất phiên bản mới trước outcomes liên quan. Phần dashboard phân tích lịch sử vẫn sử dụng được trong lúc đánh giá này chưa hoàn thành.

Câu có thể dùng trong bài:

> Nghiên cứu đánh giá sức mạnh dự báo gia tăng của các biến toàn cầu bằng nested backtest theo thời gian, sử dụng macro vintages theo thông tin khả dụng và các đối chiếu cùng mẫu. Kết quả chưa cho thấy cải thiện ổn định qua các thiết kế. Do dữ liệu kiểm tra lịch sử đã tham gia quá trình phát triển, đây là bằng chứng thực nghiệm hồi cứu; đánh giá độc lập cho cấu hình cuối cần một holdout chưa sử dụng hoặc một kỳ prospective mới.

**Kết luận áp dụng:** có thể bảo vệ tính hợp lý của nghiên cứu lịch sử bằng phương pháp và bằng chứng hiện có. Không có thao tác kỹ thuật đơn lẻ biến test đã tham gia phát triển thành untouched. Nếu checklist của đề được yêu cầu đúng nghĩa độc lập, phải có đánh giá mới để hoàn thành mục đó; tài liệu hóa hạn chế không thay thế kết quả đánh giá.
