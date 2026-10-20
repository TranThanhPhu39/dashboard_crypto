# Timing prospective — đề xuất chưa thực hiện

Ngày 19/10/2026 đã bắt đầu lưu response thật của 11 nguồn. Manifest capture đầu tiên nằm trong `data/raw/robustness_20261019/live/20261019T064838540006Z/manifest.json`.

Origin 20/10/2026 00:00 UTC yêu cầu mọi input có bằng chứng available trước hoặc tại 19/10/2026 00:00 UTC. Capture đầu tiên diễn ra khoảng 06:48 UTC nên không đạt điều kiện. Không có prediction hoặc kết quả OOS mới.

Ngoài capture đầu tiên, có một vấn đề triển khai lặp lại: feature crypto của bản đã chốt dùng bar D−2, đóng tại D−1 00:00 UTC, đúng cutoff24h của origin D. Nếu provider công bố hoặc collector nhận giá sau fixing, actual receipt sẽ sau cutoff. Không thể chứng nhận điều kiện đó chỉ bằng tải dữ liệu nhanh hơn. HTTP Date không chứng minh giá đã được công bố ở một thời điểm lịch sử sớm hơn.

Đề xuất để người dùng xem xét: tạo **phiên bản prospective timing mới**, giữ UTC target day và buffer24h, thêm một ngày đệm cho feature crypto (bar D−3 thay cho D−2) và đưa mọi feature khác về cùng information row trước khi complete-case selection. Snapshot phải được nhận thật trước cutoff, mỗi feature có lineage và ngày tham chiếu; thiếu nguồn thì ghi missing day, không backdate hoặc lấy current vintage để lấp lịch sử. Đây là thay đổi độ trễ có thể làm thay đổi phân phối features, nên cần dựng panel và refit artifacts trong phiên bản mới thay vì áp dụng ngầm lên 40 artifacts đã đóng băng.

Nếu được đồng ý, công việc triển khai sẽ gồm:

1. Khóa timing mới trước khi fit; giữ bản cũ nguyên vẹn và ghi rõ mọi proxy availability còn lại trong training lịch sử.
2. Kiểm tra lại benchmark, mẫu dài không USD và mẫu 2019+ có/không USD trên cùng origin dates; test đã xem vẫn là exploratory.
3. Tạo feature envelopes từ snapshot có timestamp thực, kiểm tra đúng feature dates, ghi predictions append-only trước outcome và lưu hash artifacts/input.
4. Khóa lại lịch đánh giá prospective trước prediction đầu tiên; không tuyên bố kết quả trước khi có đủ nhãn tương lai. Scheduler chỉ cài nếu được yêu cầu.

Đề xuất này **chưa được thực hiện**. Không thay lag, nới buffer, refit model hoặc ghi prediction trong đợt kiểm tra độ vững hiện tại. Việc cần đồng ý đến từ yêu cầu của người dùng: báo trước khi thay đổi kế hoạch; không phải từ một hạn chế kỹ thuật buộc phải xin phép cho các kiểm tra đã được cho phép.
