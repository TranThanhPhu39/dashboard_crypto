# PIT theo feature, sensitivity và nested backtest — 20/10/2026

Đã thực hiện trong namespace riêng `pit_nested_20261020` trên snapshot đến **15/10/2026**. Bảo toàn **3088 tệp cũ** bằng SHA-256. Đây là đánh giá lịch sử **exploratory**: các outcomes đã được xem trước khi thiết kế này, kể cả nested outer 2023–2026. Chưa có confirmed future skill hoặc nhận dạng nhân quả mới.

## Kết quả audit

**353/353 kiểm tra reconstruction/timing đạt**, 15 định nghĩa feature, 28026 dòng lineage macro. Không phát hiện vi phạm ngày observation/vintage so với information date trong dữ liệu đã audit. Điều này không chứng nhận mọi feature là PIT hoàn chỉnh: ALFRED có vintage theo ngày; crypto, VIX, S&P và gold vẫn dùng snapshot lịch sử, chưa có receipt/revision archive theo từng ngày quá khứ.

| feature | source | verification | remaining_assumption |
| --- | --- | --- | --- |
| broad_usd_pit_change | ALFRED DTWEXBGS | verified_date_level_asof | Exact historical provider intraday publication/receipt not observed; +24h delivery assumption |
| us2y_pit_change | ALFRED DGS2 | verified_date_level_asof | Exact historical provider intraday publication/receipt not observed; +24h delivery assumption |
| us10y_pit_change | ALFRED DGS10 | verified_date_level_asof | Exact historical provider intraday publication/receipt not observed; +24h delivery assumption |
| fed_funds_pit_change | ALFRED DFF | verified_date_level_asof | Exact historical provider intraday publication/receipt not observed; +24h delivery assumption |
| oil_wti_pit_change | ALFRED DCOILWTICO | verified_date_level_asof | Exact historical provider intraday publication/receipt not observed; +24h delivery assumption |
| nfci_pit | ALFRED NFCI | verified_date_level_asof | Exact historical provider intraday publication/receipt not observed; +24h delivery assumption |
| btc_usd_log_return | Coin Metrics PriceUSD | assumed_historical_delivery_and_revision_stability | Retrospective snapshot; historical revisions and actual release times not archived |
| btc_squared_return | Coin Metrics PriceUSD | assumed_historical_delivery_and_revision_stability | Retrospective snapshot; historical revisions and actual release times not archived |
| btc_vol30_annualized | Coin Metrics PriceUSD | assumed_historical_delivery_and_revision_stability | Retrospective snapshot; historical revisions and actual release times not archived |
| eth_usd_log_return | Coin Metrics PriceUSD | assumed_historical_delivery_and_revision_stability | Retrospective snapshot; historical revisions and actual release times not archived |
| eth_squared_return | Coin Metrics PriceUSD | assumed_historical_delivery_and_revision_stability | Retrospective snapshot; historical revisions and actual release times not archived |
| eth_vol30_annualized | Coin Metrics PriceUSD | assumed_historical_delivery_and_revision_stability | Retrospective snapshot; historical revisions and actual release times not archived |
| vix_change_lag1_proxy | FRED VIXCLS | assumed_historical_delivery_and_revision_stability | Historical feed revisions/actual receipt not archived; fixed buffer is an assumption |
| sp500_log_return_lag1_proxy | Yahoo daily unadjusted close | assumed_historical_delivery_and_revision_stability | Historical feed revisions/actual receipt not archived; fixed buffer is an assumption |
| gold_futures_log_return_lag1_proxy | Yahoo daily unadjusted close | assumed_historical_delivery_and_revision_stability | Historical feed revisions/actual receipt not archived; fixed buffer is an assumption |

Tách ba mốc: ngày quan sát; ngày vintage/công bố có bằng chứng; lúc thực nhận ở máy. `selected_record_revision_date` khác `source_last_update_date` khi nguồn sửa một quan sát khác. Retrieval 16/10/2026 là sự kiện tải snapshot, không chứng minh dữ liệu đã được nhận trong năm 2014. Gold là GC=F continuous futures, có ảnh hưởng roll; Fed Funds effective change không phải policy surprise. Broad USD không phải DXY và không nối vintage trước 2019.

## Revision và timing trên cùng mẫu

Các số `n_asof/n_paired/n_materially_revised` đếm information dates trên lịch ngày, gồm những ngày giữ nguyên một quan sát cũ; không phải số lần công bố hay số sự kiện revision độc lập. Độ lớn revision giữ đúng đơn vị feature: log change, bps hoặc NFCI index level.

| feature | series | n_asof | n_paired | n_materially_revised | mean_absolute_revision | max_absolute_revision | first_archived_vintage | first_feature_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| broad_usd_pit_change | DTWEXBGS | 2811 | 2811 | 2555 | 0.000101027 | 0.0107629 | 2019-02-04 | 2019-02-04 |
| us2y_pit_change | DGS2 | 4671 | 4671 | 0 | 0 | 0 | 2013-12-03 | 2014-01-01 |
| us10y_pit_change | DGS10 | 4671 | 4671 | 4 | 0.00299722 | 11 | 2013-12-03 | 2014-01-01 |
| fed_funds_pit_change | DFF | 4671 | 4671 | 8 | 0.0017127 | 1 | 2013-12-03 | 2014-01-01 |
| oil_wti_pit_change | DCOILWTICO | 4664 | 4519 | 14 | 0.000715277 | 0.433433 | 2013-12-04 | 2014-01-01 |
| nfci_pit | NFCI | 4671 | 4671 | 4670 | 0.159403 | 0.536 | 2013-12-11 | 2014-01-01 |

`matched_latest_d3` là counterfactual **EX POST ORACLE**: đổi sang giá trị cuối trong archive đã khóa cho đúng hai observation dates lịch sử; giữ nguyên eligibility/observation selection. Không lấy quan sát mới hơn và không coi đó là feature dự báo hợp lệ. Oracle chỉ kiểm tra revision ALFRED; không tái tạo được revisions lịch sử của crypto/Yahoo/VIX.

Riêng WTI có 145 information dates mà change as-of có giá trị nhưng counterfactual không còn đủ cặp giá trị hợp lệ, gồm các observation dates bị thay bằng missing trong archive cuối. Các ngày này được loại đối xứng khỏi cả ba scenario matched; không lấy một quan sát cũ khác thay thế cho cặp đã khóa. Bảng revision chỉ tính độ lớn trên cặp cùng có giá trị, vì vậy phải đọc cùng `n_asof/n_paired` và bảng coverage.

Với target UTC day D, baseline dùng information I=D−3, own crypto close I+1, assumed available I+2, market proxy tại D−4. D4 sensitivity dùng I=D−4 và market D−5. Không forward-fill market returns. Macro dùng thay đổi giữa hai quan sát mới nhất trong cùng vintage, giữ change đó cho đến thông tin mới theo thiết kế cũ; không gán nhầm thành một shock mới mỗi cuối tuần.

Ba scenario matched dùng giao origin **ở cả training, inner validation và outer test**. Native D3 giữ riêng để thấy ảnh hưởng đổi mẫu. BTC: 949 → 728 outer origins (76.7% còn lại); ETH: 949 → 728 outer origins (76.7% còn lại). Thay đổi native→matched phản ánh đổi mẫu huấn luyện trên cùng test dates, không phải tác động thuần của timing.

| asset | variant | scenario | n | outer_n | first_origin | last_origin |
| --- | --- | --- | --- | --- | --- | --- |
| btc | long_macro | native_asof_d3 | 3204 | 949 | 2014-01-06 00:00:00 | 2026-10-13 00:00:00 |
| btc | long_macro | matched_asof_d3 | 2435 | 728 | 2014-01-11 00:00:00 | 2026-10-13 00:00:00 |
| btc | long_macro | matched_latest_d3 | 2435 | 728 | 2014-01-11 00:00:00 | 2026-10-13 00:00:00 |
| btc | long_macro | matched_asof_d4 | 2435 | 728 | 2014-01-11 00:00:00 | 2026-10-13 00:00:00 |
| btc | common_usd | native_asof_d3 | 1927 | 949 | 2019-02-08 00:00:00 | 2026-10-13 00:00:00 |
| btc | common_usd | matched_asof_d3 | 1480 | 728 | 2019-02-09 00:00:00 | 2026-10-13 00:00:00 |
| btc | common_usd | matched_latest_d3 | 1480 | 728 | 2019-02-09 00:00:00 | 2026-10-13 00:00:00 |
| btc | common_usd | matched_asof_d4 | 1480 | 728 | 2019-02-09 00:00:00 | 2026-10-13 00:00:00 |
| eth | long_macro | native_asof_d3 | 2781 | 949 | 2015-09-12 00:00:00 | 2026-10-13 00:00:00 |
| eth | long_macro | matched_asof_d3 | 2136 | 728 | 2015-09-13 00:00:00 | 2026-10-13 00:00:00 |
| eth | long_macro | matched_latest_d3 | 2136 | 728 | 2015-09-13 00:00:00 | 2026-10-13 00:00:00 |
| eth | long_macro | matched_asof_d4 | 2136 | 728 | 2015-09-13 00:00:00 | 2026-10-13 00:00:00 |
| eth | common_usd | native_asof_d3 | 1927 | 949 | 2019-02-08 00:00:00 | 2026-10-13 00:00:00 |
| eth | common_usd | matched_asof_d3 | 1480 | 728 | 2019-02-09 00:00:00 | 2026-10-13 00:00:00 |
| eth | common_usd | matched_latest_d3 | 1480 | 728 | 2019-02-09 00:00:00 | 2026-10-13 00:00:00 |
| eth | common_usd | matched_asof_d4 | 1480 | 728 | 2019-02-09 00:00:00 | 2026-10-13 00:00:00 |

![Số origins](figures/sample_coverage.png)

## Nested chronological evaluation

640 learned artifacts, 320 outer fit groups. Outer refit đầu mỗi năm 2023/24/25/26, training expanding; inner chọn tham số bằng H1/H2 của năm trước. Không random K-fold. Tất cả preprocessing/scale/smearing fit bằng nhãn training. Ở mỗi fold, nhãn cần `label_available <= fold_start −24h`; nhãn của validation cuối năm cũng phải khả dụng trước cutoff chọn tham số outer. So với latency cũ, fit cutoff thêm 24h là lựa chọn bảo thủ đã khóa, không phải kết luận cutoff cũ rò rỉ.

| outer_year | scenario | n_groups | min_train | min_test | max_test |
| --- | --- | --- | --- | --- | --- |
| 2023 | matched_asof_d3 | 20 | 752 | 194 | 194 |
| 2023 | matched_asof_d4 | 20 | 752 | 194 | 194 |
| 2023 | matched_latest_d3 | 20 | 752 | 194 | 194 |
| 2023 | native_asof_d3 | 20 | 977 | 251 | 251 |
| 2024 | matched_asof_d3 | 20 | 945 | 190 | 190 |
| 2024 | matched_asof_d4 | 20 | 945 | 190 | 190 |
| 2024 | matched_latest_d3 | 20 | 945 | 190 | 190 |
| 2024 | native_asof_d3 | 20 | 1227 | 252 | 252 |
| 2025 | matched_asof_d3 | 20 | 1135 | 189 | 189 |
| 2025 | matched_asof_d4 | 20 | 1135 | 189 | 189 |
| 2025 | matched_latest_d3 | 20 | 1135 | 189 | 189 |
| 2025 | native_asof_d3 | 20 | 1479 | 249 | 249 |
| 2026 | matched_asof_d3 | 20 | 1325 | 155 | 155 |
| 2026 | matched_asof_d4 | 20 | 1325 | 155 | 155 |
| 2026 | matched_latest_d3 | 20 | 1325 | 155 | 155 |
| 2026 | native_asof_d3 | 20 | 1729 | 197 | 197 |

Giữ nguyên grids và hai learners. Aggregate MSE cho return, QLIKE cho variance; chọn trong inner, refit và đánh giá outer mà không dùng outer scores chọn mô hình. Targets là daily return/squared return, không trộn với Binance intraday RV đã có ở nghiên cứu khác. Số cảnh báo fit ghi nhận: **0**; xem `fit_warnings.json`.

Nhãn cũng được dựng từ snapshot Coin Metrics tải 16/10/2026. Mốc `D+2` là giả định khả dụng đã công bố, không phải log thực nhận nhãn ở từng ngày lịch sử. Nếu có historical PriceUSD revisions sau cutoff fit, snapshot này chưa đủ loại trừ ảnh hưởng đó. Nested/purge xử lý việc dùng nhãn quá sớm theo quy ước đã khóa, không tự chứng nhận vintage của nhãn hoặc sửa được lịch sử nhà cung cấp chưa lưu.

| scenario | macro_comparisons | macro_better_BH | macro_worse_BH | learned_vs_benchmark | learned_better_BH | learned_worse_BH |
| --- | --- | --- | --- | --- | --- | --- |
| native_asof_d3 | 32 | 3 | 1 | 40 | 0 | 12 |
| matched_asof_d3 | 32 | 0 | 1 | 40 | 0 | 10 |
| matched_latest_d3 | 32 | 0 | 5 | 40 | 0 | 11 |
| matched_asof_d4 | 32 | 0 | 1 | 40 | 0 | 11 |

Ở kết quả gộp, native D3 có 3/32 macro ablations tốt hơn sau BH; ba scenario matched đều 0/32. Các cấu hình learned đều 0/40 vượt benchmark sau BH ở từng scenario gộp. Đây là tín hiệu lợi ích macro không ổn định theo thiết kế/mẫu, chưa phải chứng minh hệ số hay hiệu quả giữa các thiết kế khác nhau: chênh lệch significance tự nó không phải kiểm định chênh lệch effects. Dùng các paired sensitivity bên dưới để đánh giá thay đổi trực tiếp. Trong toàn bộ các scope, bao gồm từng năm, vẫn có **2** so sánh learned thắng benchmark sau BH; không lấy các năm riêng thắng để thay kết luận gộp.

Các số trên là các so sánh liên quan nhau, không phải số phát hiện độc lập. BH điều chỉnh trong toàn family đã khóa, gồm 4 scenarios và pooled/4 annual scopes: 640 ablation, 800 benchmark, 600 sensitivity. Negative mean loss = cấu hình mới tốt hơn. Không so trực tiếp số BH với report cũ để kết luận phương pháp mới tốt/xấu, vì kỳ đánh giá, mẫu và family kiểm định khác nhau.

## Sensitivity kết quả

| comparison | n_comparisons | changed_better_BH | changed_worse_BH | changed_raw_p_lt05 |
| --- | --- | --- | --- | --- |
| sample_refit_effect_on_common_test | 40 | 3 | 2 | 5 |
| vintage_same_observations | 40 | 0 | 2 | 4 |
| extra_calendar_day | 40 | 1 | 1 | 7 |

Thêm ngày đệm có 1/40 cấu hình tốt hơn và 1/40 kém hơn sau BH trên kết quả gộp; không có cải thiện đồng loạt. Counterfactual latest vintage có 0/40 tốt hơn, 2/40 kém hơn sau BH, nên không thể mặc định revisions làm kết quả dự báo đẹp hơn trong dữ liệu này. Những kết quả đó chỉ nói về các learners, targets, cặp quan sát và sample đã khóa; không kết luận mọi revision vô hại hoặc việc bỏ kiểm soát PIT là chấp nhận được.

![Sensitivity timing](figures/timing_sensitivity.png)

| asset | target | model | variant | comparison | n | mean_loss_new_minus_base | ci_low | ci_high | pvalue | qvalue_bh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| btc | squared_return | elastic_net | common_own | sample_refit_effect_on_common_test | 728 | -0.0174239 | -0.0248071 | -0.00963218 | 0.001 | 0.0193548 |
| eth | squared_return | elastic_net | long_macro | sample_refit_effect_on_common_test | 728 | 0.0864705 | 0.0448519 | 0.129215 | 0.001 | 0.0193548 |
| eth | squared_return | elastic_net | long_own | sample_refit_effect_on_common_test | 728 | -0.0112352 | -0.0155508 | -0.00669435 | 0.001 | 0.0193548 |
| eth | squared_return | elastic_net | long_macro | vintage_same_observations | 728 | 0.0337969 | 0.018598 | 0.0500204 | 0.001 | 0.0193548 |
| eth | return | gradient_boosting | common_own | sample_refit_effect_on_common_test | 728 | 4.19403e-05 | 1.52647e-05 | 6.89931e-05 | 0.002 | 0.03 |
| btc | squared_return | elastic_net | common_macro | extra_calendar_day | 728 | -0.0670431 | -0.108405 | -0.0282966 | 0.002 | 0.03 |
| btc | squared_return | gradient_boosting | long_macro | vintage_same_observations | 728 | 0.110292 | 0.0369768 | 0.175576 | 0.002 | 0.03 |
| eth | squared_return | elastic_net | long_own | extra_calendar_day | 728 | 0.0213539 | 0.0110487 | 0.0316275 | 0.002 | 0.03 |
| btc | squared_return | elastic_net | long_own | sample_refit_effect_on_common_test | 728 | -0.0100373 | -0.0164344 | -0.0039564 | 0.003 | 0.0418605 |
| btc | squared_return | elastic_net | long_macro | vintage_same_observations | 728 | 0.022959 | 0.00841341 | 0.0378377 | 0.004 | 0.0521739 |
| btc | squared_return | elastic_net | common_usd | extra_calendar_day | 728 | -0.0598154 | -0.104448 | -0.0161108 | 0.008 | 0.096 |
| eth | squared_return | gradient_boosting | common_usd | vintage_same_observations | 728 | 0.113294 | 0.0302278 | 0.210286 | 0.013 | 0.139286 |

CI/p-values dùng 999 resamples của calendar clusters 30 ngày; paired loss MSE/QLIKE, BH trong từng family. CI mô tả pointwise, p hai phía centered bootstrap; không phải bootstrap toàn bộ thuật toán nested, không chứng minh causal effect và không xóa selection từ việc đã xem dữ liệu. Ít calendar clusters theo năm làm suy luận kém chính xác. Giữ toàn bộ kết quả, không chọn scenario thắng làm kết luận xác nhận.

## OOS độc lập và hạn nộp

**Chưa chốt được kỳ OOS vì chưa có hạn nộp.** [Phương án cụ thể](oos_proposal.md), [draft máy đọc được](oos_protocol_draft.json). Protocol một năm giữ nguyên. Không có future score mới, không backdate forecasts và không đặt lại tên test đã xem thành untouched. Có thể dùng một pilot ngắn hơn khi khóa minh bạch trước outcomes; độ dài do hạn nộp và số origins thực có quyết định, không có yêu cầu chung bắt buộc một năm.

## Kiểm chứng và chạy lại

21/21 kiểm tra độc lập và 6 edge guards đạt. Replay toàn bộ 640 artifacts/125320 prediction values, fit lại 8 mô hình đại diện và kiểm tra scaler của toàn bộ Elastic Net chỉ từ training. [Chi tiết kiểm chứng](independent_validation.json), [lineage macro](macro_row_lineage.csv), [forecast metrics](forecast_metrics.csv), [sensitivity đầy đủ](sensitivity_tests.csv), [ablation](ablation_tests.csv), [benchmark](benchmark_tests.csv), [fold timing](fold_timing.csv), [inner search](inner_search.csv).

```powershell
py -3.11 run_pit_nested.py validate
py -3.11 run_pit_nested.py compare
py -3.11 run_pit_nested.py product
```

Artifacts đã freeze: không chạy `audit/fit/all` đè lên bản này. Trên bản sao repo trước khi freeze, `audit → fit → compare → validate → product` tái tạo toàn bộ; cần Python dependencies hiện có. [Thiết kế khóa](../../../config/pit_nested_20261020.json), [khóa code fit](fit_code_lock.json), [khóa input](prepared_input_lock.json).

Phương pháp tham khảo: [ALFRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [Cawley–Talbot về nested evaluation](https://www.jmlr.org/papers/v11/cawley10a.html), [TimeSeriesSplit: gap theo số hàng](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html). [Rà soát tài liệu trước triển khai](../pit_oos_review_20261019/report.html).
