# Global Financial Conditions → Bitcoin và Ethereum

**Bản tổng hợp nộp ngày 25/10/2026.** Dữ liệu lịch sử đến 15/10/2026; sản phẩm cập nhật 2026-10-21T19:39:27.592454+07:00. [Dashboard tương tác](../../../dashboard/index.html). Các estimates dưới đây được lấy từ những phiên bản đã khóa, không huấn luyện lại hoặc đổi specification trong bước hợp nhất này.

## 1. Câu hỏi nghiên cứu và kết luận

Nghiên cứu kiểm tra quy mô, độ trễ và sự thay đổi transmission của monetary, dollar và risk/volatility news sang BTC/ETH; so sánh pre/post 2020 và stress/calm, đồng thời đánh giá incremental predictive content của macro so với own-history và benchmarks.

FOMC: thành phần chính sách gắn với phản ứng intraday âm, dưới các giả định nhận dạng. Khác biệt chế độ có 20/256 kiểm định đạt BH với HAC, 0/256 với HC3. Dự báo daily: macro cải thiện 3/32 so sánh ở mẫu D3 gốc; ba mẫu matched đều 0/32. Mỗi scenario gộp có 0/40 mô hình vượt benchmark sau BH. RV thắng benchmark ở 51/120 so sánh, nhưng macro chỉ cải thiện 0/32. Chưa xác nhận quan hệ nhân quả vô điều kiện hoặc khả năng dự báo tương lai.

RQ1: phản ứng intraday với policy component có dấu âm trong miền xoay admissible, nhưng diễn giải nhân quả cần giả định nhận dạng. RQ2: đã ước lượng đường horizon 1–30 cho VIX/USD/yield; chưa có một thời gian truyền dẫn ổn định, vững để tuyên bố cho mọi chế độ. RQ3–4: có khác biệt theo mẫu/cách suy luận, chưa xác nhận sự tăng sensitivity sau 2020 hoặc stress một cách vững. RQ5: chưa có bằng chứng vững rằng macro cải thiện dự báo vượt benchmark trên các thiết kế đã kiểm tra; chưa có xác nhận trên future untouched OOS.

## 2. Dữ liệu và định nghĩa

Giữ BTC/USD mẫu dài từ 2014, ETH ngắn hơn; full historical sample, chia pre/post 2020. Broad USD (DTWEXBGS) không phải ICE DXY; USD vintage chỉ từ 2019, không splice trước đó. Baseline không MOVE theo phạm vi đã thống nhất. Không nối Binance USDT vào chuỗi USD.

| feature | source | transformation | verification |
| --- | --- | --- | --- |
| broad_usd_pit_change | ALFRED DTWEXBGS | log(current/previous), both >0 | verified_date_level_asof |
| us2y_pit_change | ALFRED DGS2 | 100*(current-previous) bps | verified_date_level_asof |
| us10y_pit_change | ALFRED DGS10 | 100*(current-previous) bps | verified_date_level_asof |
| fed_funds_pit_change | ALFRED DFF | 100*(current-previous) bps | verified_date_level_asof |
| oil_wti_pit_change | ALFRED DCOILWTICO | log(current/previous), both >0 | verified_date_level_asof |
| nfci_pit | ALFRED NFCI | level | verified_date_level_asof |
| btc_usd_log_return | Coin Metrics PriceUSD | log(P_I/P_(I-1)) | assumed_historical_delivery_and_revision_stability |
| btc_squared_return | Coin Metrics PriceUSD | r_I squared | assumed_historical_delivery_and_revision_stability |
| btc_vol30_annualized | Coin Metrics PriceUSD | sqrt(365*mean(last 30 squared daily returns)) | assumed_historical_delivery_and_revision_stability |
| eth_usd_log_return | Coin Metrics PriceUSD | log(P_I/P_(I-1)) | assumed_historical_delivery_and_revision_stability |
| eth_squared_return | Coin Metrics PriceUSD | r_I squared | assumed_historical_delivery_and_revision_stability |
| eth_vol30_annualized | Coin Metrics PriceUSD | sqrt(365*mean(last 30 squared daily returns)) | assumed_historical_delivery_and_revision_stability |
| vix_change_lag1_proxy | FRED VIXCLS | session difference | assumed_historical_delivery_and_revision_stability |
| sp500_log_return_lag1_proxy | Yahoo daily unadjusted close | log return between nonmissing local sessions | assumed_historical_delivery_and_revision_stability |
| gold_futures_log_return_lag1_proxy | Yahoo daily unadjusted close | log return between nonmissing local sessions | assumed_historical_delivery_and_revision_stability |

Daily return `rD=log(PD/P(D−1))`; daily variance proxy `rD²`; trailing volatility `sqrt(365×mean(last30 r²))`. RV là tổng intraday squared log returns trên ngày UTC hoàn chỉnh. Δyield/ΔDFF có đơn vị bps, DFF change không phải monetary policy surprise. Gold là continuous GC=F, có roll effects. [Dictionary gốc](../../../data/processed/data_dictionary.csv), [source receipts và hashes](../../../data/source_log.json).

| Thiết kế | Nguồn / convention | Timing / đơn vị |
| --- | --- | --- |
| Daily USD | Coin Metrics PriceUSD | UTC day D đóng D+1; snapshot 16/10, nhãn availability D+2 là giả định |
| Nested / daily risk | Information I=D−3; marketD−4 | D4 sensitivity dùng I=D−4; ghép cả train/inner/test trên cùng origins |
| Calendar LP / quantile | Blueprint available-information | Thiết kế riêng với f information D−2, VIX observation D−3; outcomeD…D+h−1 |
| Monetary STMT daily | USMPD baseline | Outcome D+1…D+h; khác intraday policy/information component |
| FOMC intraday | Coinbase USD, author shock files | Eastern có DST→UTC; crypto −10/+20 phút; quote sampling khác author median |
| RV extension | Binance USDT 5m/15m | Tổng squared intraday log returns; h1/7, không dùng squared tổng 7-day return |

Các thiết kế có timing khác nhau và được giữ nhãn riêng. Không so trực tiếp daily STMT, intraday component, session IRF hoặc các loss ở khác nguồn/target như cùng một đại lượng.

## 3. Phương pháp và nhận dạng

VAR chung BTC/ETH với VIX, broad USD, yield; BIC và ordering sensitivity đã khóa. Recursive restrictions tạo một structural representation dưới giả định ordering, không tự chứng minh pure exogenous policy shock. LP hồi quy cumulative return lên information update/shock, controls/lags và interactions; h1–30 calendar days. Quantile τ=.05/.50/.95 và rolling252 sessions mô tả tail/time variation; pointwise CI không phải simultaneous bands.

FOMC dùng policy/information decomposition của tác giả, matched windows, source comparison, placebo/pre-announcement và generated-shock bootstrap. Không bác bỏ placebo không chứng minh exogeneity. Ước lượng shock/scaling có uncertainty; median-rotation intervals chưa bao phủ toàn identified set.

ML dùng Elastic Net và histogram gradient boosting; latter không phải XGBoost/LightGBM. Return dùng MSE; variance dùng QLIKE=`log(pred)+actual/pred`. Standardization, variance scale và smearing chỉ dùng training. Native/macro and USD comparisons ghép origins; nested outer refit theo năm 2023/24/25/26, inner hai học kỳ năm trước, purge bằng label availability≤fold_start−24h. Các outcomes lịch sử đã được xem, nên nesting cải thiện quy trình đánh giá nhưng không biến test thành untouched.

## 4. Dynamic responses, pre/post 2020 và VAR diagnostics

Daily LP full có 0/240 hệ số đạt BH trong family 720; stress contrasts0/240 trong family riêng. Các estimates chọn h1/7/30 bên dưới có đơn vị cumulative log return%, đọc cùng CI/n và không diễn giải riêng p-values thành causal effects.

| asset | regime | shock | horizon_days | beta_pct | lower95 | upper95 | qvalue_bh | nobs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| btc | full | vix_change | 1 | -0.234024 | -1.25054 | 0.782495 | 0.995787 | 2803 |
| btc | full | usd_return_pct | 1 | 0.103549 | -0.311883 | 0.518982 | 0.995787 | 2803 |
| btc | full | vix_change | 7 | -0.713285 | -2.15654 | 0.729975 | 0.995787 | 2797 |
| btc | full | usd_return_pct | 7 | 0.172299 | -1.00548 | 1.35008 | 0.995787 | 2797 |
| btc | full | vix_change | 30 | -0.429669 | -2.18724 | 1.32791 | 0.995787 | 2774 |
| btc | full | usd_return_pct | 30 | -0.0370389 | -2.51788 | 2.44381 | 0.996198 | 2774 |
| btc | pre2020 | vix_change | 1 | -0.028914 | -2.06019 | 2.00236 | 0.996198 | 323 |
| btc | pre2020 | usd_return_pct | 1 | -0.475229 | -2.84681 | 1.89635 | 0.995787 | 323 |
| btc | pre2020 | vix_change | 7 | -2.62512 | -9.26173 | 4.01149 | 0.995787 | 317 |
| btc | pre2020 | usd_return_pct | 7 | -2.20423 | -7.76051 | 3.35204 | 0.995787 | 317 |
| btc | pre2020 | vix_change | 30 | 3.32725 | -7.65988 | 14.3144 | 0.995787 | 294 |
| btc | pre2020 | usd_return_pct | 30 | -5.96158 | -16.8732 | 4.95009 | 0.995787 | 294 |
| btc | post2020 | vix_change | 1 | -0.286732 | -1.36958 | 0.796113 | 0.995787 | 2474 |
| btc | post2020 | usd_return_pct | 1 | 0.175742 | -0.243067 | 0.594552 | 0.995787 | 2474 |
| btc | post2020 | vix_change | 7 | -0.638784 | -2.14348 | 0.865908 | 0.995787 | 2468 |
| btc | post2020 | usd_return_pct | 7 | 0.301114 | -0.899269 | 1.5015 | 0.995787 | 2468 |
| btc | post2020 | vix_change | 30 | -0.388658 | -2.22153 | 1.44422 | 0.995787 | 2445 |
| btc | post2020 | usd_return_pct | 30 | 0.158984 | -2.3804 | 2.69837 | 0.995787 | 2445 |
| eth | full | vix_change | 1 | -0.610419 | -1.91069 | 0.689848 | 0.995787 | 2803 |
| eth | full | usd_return_pct | 1 | -0.0679114 | -0.596976 | 0.461153 | 0.995787 | 2803 |
| eth | full | vix_change | 7 | -1.51718 | -3.24491 | 0.210558 | 0.995787 | 2797 |
| eth | full | usd_return_pct | 7 | 0.374869 | -1.09146 | 1.8412 | 0.995787 | 2797 |
| eth | full | vix_change | 30 | -2.35123 | -5.06988 | 0.367432 | 0.995787 | 2774 |
| eth | full | usd_return_pct | 30 | -0.0273691 | -3.30708 | 3.25235 | 0.997658 | 2774 |
| eth | pre2020 | vix_change | 1 | -1.03541 | -3.17486 | 1.10405 | 0.995787 | 323 |
| eth | pre2020 | usd_return_pct | 1 | -0.806673 | -3.08053 | 1.46719 | 0.995787 | 323 |
| eth | pre2020 | vix_change | 7 | 0.0260512 | -9.10459 | 9.15669 | 0.997658 | 317 |
| eth | pre2020 | usd_return_pct | 7 | -3.05609 | -9.33413 | 3.22195 | 0.995787 | 317 |
| eth | pre2020 | vix_change | 30 | 2.85243 | -15.049 | 20.7539 | 0.995787 | 294 |
| eth | pre2020 | usd_return_pct | 30 | -7.18826 | -16.5234 | 2.14692 | 0.995787 | 294 |
| eth | post2020 | vix_change | 1 | -0.67059 | -2.04918 | 0.708003 | 0.995787 | 2474 |
| eth | post2020 | usd_return_pct | 1 | 0.0334175 | -0.513696 | 0.580531 | 0.995787 | 2474 |
| eth | post2020 | vix_change | 7 | -1.56719 | -3.34482 | 0.210446 | 0.995787 | 2468 |
| eth | post2020 | usd_return_pct | 7 | 0.542657 | -0.978961 | 2.06427 | 0.995787 | 2468 |
| eth | post2020 | vix_change | 30 | -2.40583 | -5.2684 | 0.456731 | 0.995787 | 2445 |
| eth | post2020 | usd_return_pct | 30 | 0.530926 | -2.85842 | 3.92028 | 0.995787 | 2445 |

![Calendar LP và regimes](../blueprint_20261019/figures/calendar_LP.png)

| yield_variable | regime | lag | nobs | stable | whiteness_p20 | start_date | end_date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| us2y | full | 1 | 2764 | True | 3.27258e-08 | 2015-08-25 | 2026-10-09 |
| us2y | pre2020 | 1 | 1077 | True | 0.148851 | 2015-08-25 | 2019-12-31 |
| us2y | post2020 | 1 | 1677 | True | 1.02523e-09 | 2020-01-16 | 2026-10-09 |
| us10y | full | 1 | 2764 | True | 3.80105e-08 | 2015-08-25 | 2026-10-09 |
| us10y | pre2020 | 1 | 1077 | True | 0.117379 | 2015-08-25 | 2019-12-31 |
| us10y | post2020 | 1 | 1677 | True | 3.51434e-11 | 2020-01-16 | 2026-10-09 |

4/6 VAR systems bác bỏ whiteness 20; 60/60 ARCH tests đạt BH. Mô hình mean/variance chưa adequate đầy đủ; không dùng IRF CI tiệm cận làm bằng chứng causal vững. LP/robust inference và sensitivity là các phân tích bổ sung, không tự sửa mọi misspecification của VAR.

![Quantile effects](../blueprint_20261019/figures/quantile_effects.png)

Quantile CI dùng 99 block bootstrap draws, có 5/1782 bootstrap fits không hội tụ đã loại và ghi log. Chưa có paired quantile-gap test; đường khác nhau chưa chứng minh khác slope. Rolling và full h1–30 được giữ trên dashboard cùng source/version labels.

## 5. FOMC và khác biệt chế độ

75 common scheduled events;72 đủ tất cả falsification windows;45 có đủ JK/BS sources. Không thay missing orthogonalized surprise bằng raw. Intraday policy point ranges trên toàn miền xoay:

| asset | lower_per10bps | upper_per10bps | unbounded |
| --- | --- | --- | --- |
| BTC | -1.95619 | -0.711312 | False |
| ETH | -2.52303 | -0.794652 | False |

Đơn vị điểm phần trăm return / +10 bps component PC1. Đây là infimum/supremum point estimates, **không phải confidence set**. Information component có thể unbounded theo chuẩn hóa này. 999 bootstrap draws lặp PCA/scaling/QR/outcome fit cho uncertainty tại median rotation; không phải toàn structural identified set.

| contrast | tests | BH_HAC | BH_HC3 | n0 | n1 |
| --- | --- | --- | --- | --- | --- |
| post2020 | 128 | 17 | 0 | 23 | 52 |
| stress | 128 | 3 | 0 | 63 | 12 |

HAC 20/256 so HC3 0/256: bằng chứng regime sensitivity chưa vững theo cách suy luận. Pre 2020 có 23 events; stress 12 events. STMT post-event baseline stress 9events từng cho nhiều hệ số có ý nghĩa, nhưng bỏ 03/03/2020 làm BH contrasts giảm36/60→3/60; không dùng riêng baseline để khẳng định stress transmission. [Evidence đầy đủ](../evidence_20261019/report.html), [influence diagnostics](../robustness_20261019/report.html), [FOMC timing study](../fomc_identification_20261019/report.html).

![Rotation và sampling uncertainty](../evidence_20261019/figures/rotation_and_sampling.png)

## 6. Nested risk forecasting và sensitivity

640 artifacts, 320 outer groups, replay 125.320 learned predictions và fit lại 8 representatives; 21/21 independent checks, 6 guards. Các số dưới là kết quả gộp 2023–2026; BH bao gồm pooled và annual scopes trong family đã khóa. Không gọi các so sánh liên quan nhau là các phát hiện độc lập.

| scenario | macro_comparisons | macro_better_BH | macro_worse_BH | benchmark_comparisons | learned_better_BH | learned_worse_BH |
| --- | --- | --- | --- | --- | --- | --- |
| native_asof_d3 | 32 | 3 | 1 | 40 | 0 | 12 |
| matched_asof_d3 | 32 | 0 | 1 | 40 | 0 | 10 |
| matched_latest_d3 | 32 | 0 | 5 | 40 | 0 | 11 |
| matched_asof_d4 | 32 | 0 | 1 | 40 | 0 | 11 |

Native có 949 origins và matched 728 mỗi tài sản. Khác significance giữa native và matched không tự là test khác effects; xem paired sensitivity. Thêm ngày buffer có 1/40 tốt hơn và1/40 kém hơn sau BH ở kết quả gộp. Latest-vintage counterfactual có 0/40 tốt hơn,2/40 kém hơn; revisions không mặc định làm kết quả đẹp hơn. Tuy vậy đây không phải lý do được bỏ PIT. [Toàn bộ nested/sensitivity](../pit_nested_20261020/report.html).

![Timing sensitivity trên cùng origins](../pit_nested_20261020/figures/timing_sensitivity.png)

## 7. Intraday realized variance extension

250 Binance archives có checksums/CRC;257 invalid candles mỗi asset được giữ raw và loại có audit, không sửa timestamp/nội suy. Chỉ dùng ngày hoàn chỉnh gồm midnight boundary. HAR/HAR-X h1/7 với 5m/15m sampling,880 monthly artifacts; benchmarks trailing30/EWMA/GARCH cùng cutoff. Nhánh này khác daily USD squared return.

51/120 HAR/HAR-X-vs-benchmark comparisons thắng sau BH; 0/32 incremental macro comparisons cải thiện sau BH. Model confidence set membership không chứng minh macro skill. Kết quả này ủng hộ một số cấu trúc lịch sử RV trong sample hơn một số benchmark, chưa xác nhận macro hoặc future predictive ability. [Nguồn, sample và loss đầy đủ](../evidence_20261019/report.html).

![RV forecast comparisons](../evidence_20261019/figures/rv_forecasting.png)

## 7b. Kiểm thử OOS trên dữ liệu quá khứ theo khoảng ngày

Dashboard → **Dự báo rủi ro → Phát lại dự báo trên dữ liệu quá khứ** cho phép chọn khoảng ngày UTC trong 01/01/2023–13/10/2026, tài sản, target, model, scenario và cặp so sánh. Hiển thị thực tế/base/added/benchmark, loss cộng dồn, timing và model SHA-256 của từng origin; CSV giữ nguyên dự báo và các mốc thời gian. Chỉ các origins đã đủ điều kiện trong thiết kế gốc được dùng, không tạo forecast cho ngày thiếu.

Đã replay **640 artifacts**, đối chiếu **125320 learned predictions** và **125320 benchmark predictions** với CSV đã khóa; kiểm tra chronology, label availability và train-only scaling. Không refit, không thay ước lượng hoặc ghi dự báo lịch sử vào ledger prospective. Chạy lại bằng `py -3.11 run_release.py validate-history`; dữ liệu hiển thị và bằng chứng checksum ở `dashboard/historical_oos_data.json` và `dashboard/historical_oos_audit.json`.

Đây là **historical pseudo-OOS** kiểm chứng quy trình tính toán, khác với tính độc lập của toàn bộ thiết kế cuối với outcomes đã xem. Scenario latest-vintage giữ nhãn **EX POST ORACLE**. Khoảng ngày người dùng chọn chỉ tính thống kê mô tả; các bảng CI/BH vẫn dùng kỳ/năm đánh giá đã khóa, không suy luận significance cho đoạn được chọn sau khi xem biểu đồ.

## 8. PIT, OOS độc lập và hạn nộp

15 feature definitions, 28.026 macro-lineage rows, 353/353 checks đối chiếu raw ALFRED spells và calendar transforms đạt. Không phát hiện vi phạm observation/vintage date trong phạm vi metadata được audit; không chứng nhận mọi feed có đầy đủ historical receipt/revision evidence. Targets/nhãn cũng là retrospective Coin Metrics snapshot; D+2 là giả định availability. D4 delay không sửa được unknown revisions hoặc biến kết quả thành causal identification.

**Ngày nộp và thời hạn đánh giá OOS là hai mốc khác nhau.** Ngày25/10/2026 quyết định nội dung có thể đưa vào bản nộp; không làm một backtest trở nên hợp lệ hoặc không hợp lệ. Mốc chốt nội bộ 24/10 18:00 VN là lựa chọn lập kế hoạch. Theo timing hiện tại, origin23/10 chỉ có thể đủ nhãn sớm nhất 25/10 07:00 VN; readiness upper bound là0 origin tại mốc nội bộ và tối đa 1 origin trước hết ngày nộp, còn phụ thuộc actual receipts. Đây không phải forecasts đã được log hoặc số quan sát đủ để xác nhận skill. [Phân tích lịch trước hạn](../submission_20261025/report.html).

**Hướng xử lý đã áp dụng:** giữ historical as-of nested evaluation làm kết quả nghiên cứu lịch sử, báo toàn bộ benchmark/ablation và matched sensitivity; đánh giá độc lập tiếp tục ở nhánh prospective. [Gillet/Chicago Fed (2024)](https://www.chicagofed.org/publications/economic-perspectives/2024/7) cũng phân biệt backtest ALFRED lịch sử với true OOS; [Cawley–Talbot (2010)](https://www.jmlr.org/papers/v11/cawley10a.html) giải thích vai trò đánh giá cả bước chọn mô hình. Những phương pháp này hỗ trợ chất lượng historical evaluation, không hồi phục holdout đã tham gia phát triển thiết kế.

Reality Check/SPA xử lý một số dạng data snooping; SPA gốc có giới hạn với recursive expanding estimation nên chưa được thêm máy móc vào annual expanding backtest. Xem [White (2000)](https://users.ssc.wisc.edu/~behansen/718/White2000.pdf), [Hansen (2005)](https://doi.org/10.1198/073500105000000063) và [review áp dụng cho repo](../../../paper/untouched_oos_followup_20261020.md). Chưa xác lập được holdout lịch sử độc lập; **mục untouched OOS cho cấu hình cuối chưa hoàn thành**. Đánh giá mới cần forecasts trước outcomes hoặc một tập thực sự chưa tham gia phát triển.

Trạng thái lúc 2026-10-21T19:39:27.592454+07:00: **0 forecast commits, 0 labels**; evaluation status **PENDING_FIXED_EVALUATION_WINDOW**. Lần vận hành gần nhất 2026-10-21T09:20:31.369974+07:00; capture có 17/17 nguồn thành công. Protocol hiện có giữ nguyên đến 2027-10-20T00:00:00Z; một năm là thời lượng đã chọn, không phải yêu cầu khoa học phổ quát. Đổi lịch chấm cần một protocol được thống nhất trước outcomes liên quan. Tự động trên GitHub Actions: pipeline mỗi giờ phút 15, giám sát phút 45; không cần bật máy cá nhân. Lịch có thể trễ; cutoff và thời điểm nhận dữ liệu giữ nguyên. [Giám sát tự động](../../automation_20261020/health.html), [kế hoạch và trạng thái OOS](oos_followup.html), [lịch chạy theo giờ Việt Nam](next_operations.csv), [provenance của cập nhật](oos_followup.json).

## 9. Đối chiếu yêu cầu và giới hạn kết luận

| Yêu cầu | Trạng thái | Phạm vi |
| --- | --- | --- |
| Data / pipeline | Đã có | USD mẫu dài; Binance USDT đối chiếu/RV riêng; broad USD, baseline không MOVE. |
| VAR / recursive restrictions | Đã có, có hạn chế | BTC/ETH cùng hệ, IRF/order sensitivity; residual mean/variance diagnostics chưa đạt toàn bộ. |
| LP / rolling / quantile / regimes | Đã có | Ngày lịch1–30, pre/post 2020 và stress; CI pointwise, uncertainty và subgroup limits được công bố. |
| ML risk forecast | Đã có | Elastic Net, histogram boosting; benchmarks và matched macro ablations; HAR/RV là nhánh riêng. |
| Whole-feed PIT | Chưa chứng nhận đầy đủ | ALFRED date-level vintage; crypto/market và nhãn vẫn có giả định delivery/revision lịch sử. |
| Untouched OOS cho thiết kế cuối | Chưa hoàn thành | Lịch sử đã tham gia phát triển; ledger prospective và endpoint riêng được theo dõi, không gắn tính hợp lệ với ngày nộp. |
| Causal transmission vô điều kiện | Chưa xác lập | FOMC mạnh hơn daily association nhưng cần sign/exclusion assumptions; không thay identification bằng ML. |
| Báo cáo / dashboard / repository | Đã hợp nhất | Bản tổng hợp này và dashboard chính dùng cùng nguồn; snapshots/ZIP cũ giữ nguyên. |

Kết quả null, sự nhạy với sample/inference và VAR diagnostics không tự là lỗi code hoặc dữ liệu. Bài trả lời câu hỏi nghiên cứu với bằng chứng hiện có, không cần có hiệu ứng dương/cải thiện dự báo mới được ghi nhận. Chưa tuyên bố institutionalization là nguyên nhân của thay đổi hệ số, global shocks được nhận dạng ngoại sinh cho mọi biến, hoặc skill tương lai đã được xác nhận.

## 10. Repository, chạy lại và bảo toàn

Mỗi source/result/version có trong [source catalog](source_catalog.csv). Scientific inputs được khóa hash ở [scientific_input_lock.json](scientific_input_lock.json). Không sửa estimates/data/models/protocol; báo cáo và dashboard render cùng payload. Các snapshots cũ và ZIP cũ giữ nguyên; dashboard/paper navigation cũ và các status trước migration có byte-identical copies trong [preservation migration](preservation_migration.json).

Chỉ exact allowlist các file trạng thái/entrypoints/navigation được cập nhật. Validator nghiên cứu kiểm tra bản gốc đã archive của những file này; mọi raw response/manifest, data, fit-code/input lock, model và protocol vẫn kiểm tra live hash nghiêm ngặt. Archive hỏng hoặc model đổi vẫn bị chặn. Đây là tách mutable status khỏi historical evidence, không bỏ kiểm tra bảo toàn.

```powershell
py -3.11 run_release.py build
py -3.11 run_release.py validate
py -3.11 run_release.py validate-pit
node tests/validate_release_dashboard.cjs
node tests/preview_release.cjs
py -3.11 run_release.py package
```

`build/validate/all` không refit. `operate` chạy collector/forecast bằng actual clock theo protocol hiện có, rồi làm mới và kiểm chứng báo cáo/dashboard. Tác vụ Windows gọi operational wrapper, có khóa chống chạy trùng, retry, log và watchdog; thu thập mới tối đa sau mỗi4 giờ hoặc khi nguồn lỗi. Retry không backdate hoặc nới cutoff. Ngoài cửa sổ origin, wrapper chỉ tiếp tục nhãn và original evaluation gate. Không dùng các lệnh legacy `all/train/fit` trên artifact checkout đã freeze. Supplement cần full base repo/dependencies; snapshot raw và hash là căn cứ tái lập, fresh download có thể khác do revisions.

## 11. Tài liệu và phụ lục

[Blueprint yêu cầu đã đối chiếu](../../../paper/requirements.md), [review causality/prediction literature](../../../paper/causality_forecast_literature_review_20261019.md), [review PIT/OOS remedies](../../../paper/pit_oos_remedies_review_20261019.md), [nghiên cứu bổ sung về untouched OOS ngày 20/10](../../../paper/untouched_oos_followup_20261020.md). Các bảng và hình là kết quả của repo, chưa phải replication của một paper khác.

Nguồn phương pháp gốc: [ALFRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [Cawley–Talbot: nested evaluation](https://www.jmlr.org/papers/v11/cawley10a.html), [Bauer–Swanson data](https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/). Author data, metadata và bibliography chi tiết được giữ trong các research snapshots liên kết ở trên. Nghiên cứu học thuật, không phải khuyến nghị đầu tư.
