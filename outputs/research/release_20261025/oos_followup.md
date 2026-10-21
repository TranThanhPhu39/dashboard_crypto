# OOS: bằng chứng đã có và vận hành tiếp theo

Cập nhật 2026-10-21T19:39:27.592454+07:00. [Báo cáo chính](report.html) · [Review tài liệu](../../../paper/untouched_oos_followup_20261020.md) · [Audit có provenance](oos_followup.json).

## Hai mốc thời gian khác nhau

Hạn **2026-10-25** dùng để chốt nội dung nộp. Mốc nội bộ **2026-10-24T18:00:00+07:00** là lựa chọn lập kế hoạch, không phải điều kiện thống kê. Bài có thể báo cáo nested backtest lịch sử tại thời điểm nộp; đánh giá độc lập tiếp tục sau đó.

Protocol hiện tại chạy từ **2026-10-20T00:00:00Z** tới trước **2027-10-20T00:00:00Z**. Đây là thời lượng đã chọn, không phải quy định chung rằng OOS phải đủ một năm. Trong lần cập nhật này, endpoint, receipt buffer, feature timing, mô hình và chính sách chấm được giữ nguyên. Chưa kích hoạt pilot khác.

## Những việc đã thực hiện

- Đối chiếu tài liệu với nested chronological backtest hiện có: **640 artifacts**; giữ nguyên kết quả benchmark, macro ablation và sensitivity trên cùng mẫu. Không fit lại trong bước báo cáo.
- Phân biệt test lịch sử đã tham gia phát triển với holdout chưa sử dụng. Chưa có bằng chứng xác lập một holdout lịch sử độc lập cho thiết kế cuối.
- Liên kết phương pháp với [Gillet/Chicago Fed (2024)](https://www.chicagofed.org/publications/economic-perspectives/2024/7), [Cawley–Talbot (2010)](https://www.jmlr.org/papers/v11/cawley10a.html), [White (2000)](https://users.ssc.wisc.edu/~behansen/718/White2000.pdf) và [Hansen (2005)](https://doi.org/10.1198/073500105000000063). Nested evaluation và data-snooping inference giải quyết những phần khác nhau của rủi ro đánh giá; không biến test đã xem thành holdout độc lập.
- Giữ SPA ở trạng thái chưa triển khai: cần suy luận tương thích expanding estimation và universe đã tìm kiếm. Không thêm một p-value không đáp ứng assumptions.
- Tiếp tục collector thực tế: lần capture bắt đầu **2026-10-21T02:16:29.919173+00:00**, **17/17 nguồn** trả thành công. Thành công của nguồn không tự có nghĩa forecast đủ điều kiện.

## Trạng thái thực tế

Lần thử gần nhất: BTC: INELIGIBLE_INPUTS; ETH: INELIGIBLE_INPUTS. Ledger có **0 forecast commits, 0 dự báo mô hình và 0 label files**. Dùng **40 latency artifacts đã khóa**; không triển khai 640 nested artifacts thay thế. Chưa chấm performance trước fixed endpoint, không suy ra skill từ tình trạng collector.

Lịch eligibility/receipt/logging nằm trong [readiness calendar](../evidence_20261019/prospective_operations/readiness_calendar.csv); đây là điều kiện vận hành, không phải dự báo đã tồn tại. Nhật ký ghi cả lần thiếu inputs; không backdate hoặc bù dự báo sau outcome. Tự động trên GitHub Actions: pipeline mỗi giờ phút 15, giám sát phút 45; không cần bật máy cá nhân. Lịch có thể trễ; cutoff và thời điểm nhận dữ liệu giữ nguyên. [Giám sát, cảnh báo và log](../../automation_20261020/health.html).

## Việc cần chạy tiếp theo

Candidate kế tiếp có origin **07:00 ngày 23/10/2026**, information day **2026-10-20** và market observation day **2026-10-19**. Đây là lịch có điều kiện, chưa phải forecast đã tồn tại.

| Việc cần làm | Khoảng giờ Việt Nam |
| --- | --- |
| Thu thập inputs cho candidate này | Từ 07:00 ngày 21/10/2026 đến 07:00 ngày 22/10/2026; mọi nguồn cần có receipt hợp lệ trước hoặc đúng cutoff |
| Chạy lệnh để ghi forecast trước origin | Từ 07:00 ngày 22/10/2026 đến trước 07:00 ngày 23/10/2026 |
| Nhãn có thể bắt đầu khả dụng theo giả định hiện tại | 07:00 ngày 25/10/2026; chưa phải label đã nhận hoặc thời điểm được chấm performance |


[Lịch đầy đủ theo UTC và giờ Việt Nam](next_operations.csv). Ngày nghỉ theo weekend mới chỉ là một điều kiện; ngày thường vẫn cần holiday/source/completeness checks thực tế.

```powershell
py -3.11 run_release.py operate
```

Lệnh trên chạy thủ công một lần; lịch Windows gọi `run_automation.py run` để có log/retry/health và làm mới báo cáo/dashboard. Capture mới được yêu cầu sau4 giờ hoặc khi nguồn lỗi, giữ riêng bytes từng lần để có thể phục hồi từ snapshot thiếu nội dung. Sau origin cuối chỉ nhận nhãn và giữ evaluation gate cũ. Chỉ cần chạy `build` nếu muốn làm mới giao diện từ artifacts có sẵn mà không vận hành collector.

Nếu cần đổi thời hạn đánh giá, phải thống nhất protocol mới trước outcomes liên quan và ghi rõ ảnh hưởng tới protocol cũ. Vài ngày tới hạn nộp có thể kiểm tra vận hành, nhưng chưa đủ cơ sở hứa xác nhận lợi ích dự báo. Việc nộp báo cáo và việc tích lũy bằng chứng OOS độc lập là hai công việc có thể kết thúc ở hai thời điểm khác nhau.
