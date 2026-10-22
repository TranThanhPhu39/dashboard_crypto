"""Report OOS evidence and operations without fitting or inspecting new losses."""
from src.evaluation.release_preservation import ROOT, OUT, sha, save_json
from research_common import pd, json
from src.automation_runtime import automation_summary


REVIEW = 'paper/untouched_oos_followup_20261020.md'
PROTOCOL = 'data/prospective/evidence_20261019/protocol.json'
READINESS = 'outputs/research/evidence_20261019/prospective_operations/readiness_calendar.csv'


def operation_windows(now, label_delay_days):
    """Convert the audited windows to local time; never emit forecasts."""
    rows = pd.read_csv(ROOT/READINESS)
    plan = []
    for row in rows.to_dict('records'):
        origin = pd.Timestamp(row['origin_utc'])
        if origin <= now:
            continue
        cutoff = pd.Timestamp(row['receipt_cutoff_utc'])
        weekend = bool(row['market_day_is_weekend'])
        record = {key:row[key] for key in ['origin_utc', 'information_day', 'market_observation_day',
                    'capture_window_start_utc', 'receipt_cutoff_utc', 'earliest_logging_utc', 'latest_logging_exclusive_utc']}
        for key in ['origin_utc', 'capture_window_start_utc', 'receipt_cutoff_utc', 'earliest_logging_utc', 'latest_logging_exclusive_utc']:
            record[key.removesuffix('_utc')+'_local'] = pd.Timestamp(row[key]).tz_convert('Asia/Ho_Chi_Minh').isoformat()
        record.update(market_day_is_weekend=weekend,
                      currently_ready_long=bool(row['long_features_ready_from_archived_receipts']),
                      currently_ready_common=bool(row['common_features_ready_from_archived_receipts']),
                      assumed_label_available_local=(origin+pd.Timedelta(days=label_delay_days)).tz_convert('Asia/Ho_Chi_Minh').isoformat(),
                      planning_status='weekend_market_day' if weekend else 'receipt_window_closed' if cutoff < now else 'conditional_candidate',
                      role='OPERATIONAL PLAN ONLY; no forecast or future label generated; actual complete receipts required')
        plan.append(record)
    columns = ['origin_utc', 'information_day', 'market_observation_day', 'capture_window_start_utc',
               'receipt_cutoff_utc', 'earliest_logging_utc', 'latest_logging_exclusive_utc',
               'origin_local', 'capture_window_start_local', 'receipt_cutoff_local', 'earliest_logging_local',
               'latest_logging_exclusive_local', 'market_day_is_weekend', 'currently_ready_long',
               'currently_ready_common', 'assumed_label_available_local', 'planning_status', 'role']
    pd.DataFrame(plan, columns=columns).to_csv(OUT/'next_operations.csv', index=False, encoding='utf-8-sig')
    candidates = [row for row in plan if row['planning_status']=='conditional_candidate']
    return dict(source=READINESS, source_sha256=sha(ROOT/READINESS), timezone='Asia/Ho_Chi_Minh',
                next_conditional_origin=candidates[0] if candidates else None, rows=len(plan),
                scheduler_installed=automation_summary()['installed'], forecasts_created=0)


def build_followup(live, now):
    protocol = json.loads((ROOT/PROTOCOL).read_text(encoding='utf-8'))
    cfg = json.loads((ROOT/'config/submission_20261025.json').read_text(encoding='utf-8'))
    capture = json.loads((ROOT/'outputs/research/evidence_20261019/prospective/latest_capture.json').read_text(encoding='utf-8'))
    manifest_path = ROOT/capture['manifest']
    assert sha(manifest_path) == capture['sha256'], 'Capture manifest changed'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    nested_path = ROOT/'outputs/research/pit_nested_20261020/model_inventory.csv'
    latency_path = ROOT/'outputs/research/latency_20261019/model_inventory.csv'
    attempt = json.loads((ROOT/'outputs/research/evidence_20261019/prospective/prospective_status.json').read_text(encoding='utf-8'))
    attempts = [dict(asset=row['asset'], origin_utc=row['origin_utc'], status=row['status'],
                     long_eligible=row['long_eligible'], common_eligible=row['common_eligible'], missing=row['missing'])
                for row in attempt['attempts']]
    plan = operation_windows(now, cfg['label_assumed_delay_days'])
    obj = dict(
        version='oos_followup_20261020', generated_utc=now.isoformat(),
        submission=dict(date_local=cfg['submission_date_local'], timezone=cfg['timezone'],
                        internal_freeze_local=cfg['internal_report_freeze_local'],
                        role='Writing/package milestone, not a statistical validity threshold or evaluation endpoint'),
        evaluation=dict(protocol=PROTOCOL, protocol_sha256=sha(ROOT/PROTOCOL),
                        start_utc=protocol['start_utc'], end_exclusive_utc=protocol['end_utc_exclusive'],
                        changed=False, new_pilot_activated=False, early_scoring=False,
                        minimum_one_year_is_universal_requirement=False),
        historical=dict(nested_artifacts=len(pd.read_csv(nested_path)),
                        interpretation='Exploratory historical nested backtest; final design used previously inspected outcomes',
                        unused_historical_holdout='Not established for this final design', new_fits=0),
        prospective=dict(frozen_latency_artifacts=len(pd.read_csv(latency_path)), live=live, latest_attempts=attempts,
                         latest_capture=dict(manifest=capture['manifest'], sha256=capture['sha256'],
                                             capture_started_utc=manifest['capture_started_utc'],
                                             sources_ok=sum(row['status']=='ok' for row in manifest['sources']),
                                             sources_total=len(manifest['sources'])),
                         operational_success_is_predictive_skill=False),
        operations_plan=plan,
        methodology=dict(review=REVIEW, review_sha256=sha(ROOT/REVIEW),
                         spa_status='Not added: original fixed/rolling assumptions do not directly cover annual expanding nested design',
                         requirement_status='Untouched OOS for final design not yet completed'),
        input_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/PROTOCOL, nested_path, latency_path]},
        estimates_changed=False, performance_claim=False)
    save_json(OUT/'oos_followup.json', obj)
    capture_state = obj['prospective']['latest_capture']
    from src.automation_runtime import automation_description
    automation_note=automation_description(live['automation'])
    attempt_text = '; '.join(f"{row['asset'].upper()}: {row['status']}" for row in attempts)
    next_origin = plan['next_conditional_origin']
    next_note = 'Chưa có candidate trong khoảng lịch hiện được audit; cần chạy operate để làm mới readiness.'
    if next_origin:
        clock = lambda value: pd.Timestamp(value).tz_convert('Asia/Ho_Chi_Minh').strftime('%H:%M ngày %d/%m/%Y')
        next_note = f'''Candidate kế tiếp có origin **{clock(next_origin['origin_local'])}**, information day **{next_origin['information_day']}** và market observation day **{next_origin['market_observation_day']}**. Đây là lịch có điều kiện, chưa phải forecast đã tồn tại.

| Việc cần làm | Khoảng giờ Việt Nam |
| --- | --- |
| Thu thập inputs cho candidate này | Từ {clock(next_origin['capture_window_start_local'])} đến {clock(next_origin['receipt_cutoff_local'])}; mọi nguồn cần có receipt hợp lệ trước hoặc đúng cutoff |
| Chạy lệnh để ghi forecast trước origin | Từ {clock(next_origin['earliest_logging_local'])} đến trước {clock(next_origin['latest_logging_exclusive_local'])} |
| Nhãn có thể bắt đầu khả dụng theo giả định hiện tại | {clock(next_origin['assumed_label_available_local'])}; chưa phải label đã nhận hoặc thời điểm được chấm performance |
'''
    note = f'''# OOS: bằng chứng đã có và vận hành tiếp theo

Cập nhật {now.tz_convert('Asia/Ho_Chi_Minh').isoformat()}. [Báo cáo chính](report.html) · [Review tài liệu](../../../{REVIEW}) · [Audit có provenance](oos_followup.json).

## Hai mốc thời gian khác nhau

Hạn **{cfg['submission_date_local']}** dùng để chốt nội dung nộp. Mốc nội bộ **{cfg['internal_report_freeze_local']}** là lựa chọn lập kế hoạch, không phải điều kiện thống kê. Bài có thể báo cáo nested backtest lịch sử tại thời điểm nộp; đánh giá độc lập tiếp tục sau đó.

Protocol hiện tại chạy từ **{protocol['start_utc']}** tới trước **{protocol['end_utc_exclusive']}**. Đây là thời lượng đã chọn, không phải quy định chung rằng OOS phải đủ một năm. Trong lần cập nhật này, endpoint, receipt buffer, feature timing, mô hình và chính sách chấm được giữ nguyên. Chưa kích hoạt pilot khác.

## Những việc đã thực hiện

- Đối chiếu tài liệu với nested chronological backtest hiện có: **{obj['historical']['nested_artifacts']} artifacts**; giữ nguyên kết quả benchmark, macro ablation và sensitivity trên cùng mẫu. Không fit lại trong bước báo cáo.
- Phân biệt test lịch sử đã tham gia phát triển với holdout chưa sử dụng. Chưa có bằng chứng xác lập một holdout lịch sử độc lập cho thiết kế cuối.
- Liên kết phương pháp với [Gillet/Chicago Fed (2024)](https://www.chicagofed.org/publications/economic-perspectives/2024/7), [Cawley–Talbot (2010)](https://www.jmlr.org/papers/v11/cawley10a.html), [White (2000)](https://users.ssc.wisc.edu/~behansen/718/White2000.pdf) và [Hansen (2005)](https://doi.org/10.1198/073500105000000063). Nested evaluation và data-snooping inference giải quyết những phần khác nhau của rủi ro đánh giá; không biến test đã xem thành holdout độc lập.
- Giữ SPA ở trạng thái chưa triển khai: cần suy luận tương thích expanding estimation và universe đã tìm kiếm. Không thêm một p-value không đáp ứng assumptions.
- Tiếp tục collector thực tế: lần capture bắt đầu **{capture_state['capture_started_utc']}**, **{capture_state['sources_ok']}/{capture_state['sources_total']} nguồn** trả thành công. Thành công của nguồn không tự có nghĩa forecast đủ điều kiện.

## Trạng thái thực tế

Lần thử gần nhất: {attempt_text}. Ledger có **{live['prediction_files']} tệp dự báo, {live['prediction_rows']} dòng dự báo mô hình/benchmark và {live['label_files']} tệp nhãn** trên **{live['origin_count']} origin khác nhau**. Số dòng không phải số ngày kiểm định độc lập. Dùng **{obj['prospective']['frozen_latency_artifacts']} latency artifacts đã khóa**; không triển khai 640 nested artifacts thay thế. Chưa chấm performance trước fixed endpoint, không suy ra skill từ tình trạng collector.

Lịch eligibility/receipt/logging nằm trong [readiness calendar](../evidence_20261019/prospective_operations/readiness_calendar.csv); đây là điều kiện vận hành, không phải dự báo đã tồn tại. Nhật ký ghi cả lần thiếu inputs; không backdate hoặc bù dự báo sau outcome. {automation_note} [Giám sát, cảnh báo và log](../../automation_20261020/health.html).

## Việc cần chạy tiếp theo

{next_note}

[Lịch đầy đủ theo UTC và giờ Việt Nam](next_operations.csv). Ngày nghỉ theo weekend mới chỉ là một điều kiện; ngày thường vẫn cần holiday/source/completeness checks thực tế.

```powershell
py -3.11 run_release.py operate
```

Lệnh trên dành cho host đang giữ quyền ghi ledger; bản sao trong máy được chặn chạy worker khi GitHub giữ quyền ghi. {automation_note} Capture mới được yêu cầu sau4 giờ hoặc khi nguồn lỗi, giữ riêng bytes từng lần để có thể phục hồi từ snapshot thiếu nội dung. Sau origin cuối chỉ nhận nhãn và giữ evaluation gate cũ. Chỉ cần chạy `build` nếu muốn làm mới giao diện từ artifacts có sẵn mà không vận hành collector.

Nếu cần đổi thời hạn đánh giá, phải thống nhất protocol mới trước outcomes liên quan và ghi rõ ảnh hưởng tới protocol cũ. Vài ngày tới hạn nộp có thể kiểm tra vận hành, nhưng chưa đủ cơ sở hứa xác nhận lợi ích dự báo. Việc nộp báo cáo và việc tích lũy bằng chứng OOS độc lập là hai công việc có thể kết thúc ở hai thời điểm khác nhau.
'''
    (OUT/'oos_followup.md').write_text(note, encoding='utf-8')
    return obj
