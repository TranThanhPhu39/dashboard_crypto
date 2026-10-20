"""Deadline-specific addendum; no collection, training or prospective scoring."""
from src.evaluation.release_preservation import install,verify_mapping,historical_path,initialize
install()
from src.evaluation.pit_nested_common import ROOT, np, pd, json, sha, save_json, check_protected
from src.robustness_product import md, render_markdown
import zipfile,hashlib

VERSION='submission_20261025'
OUT=ROOT/'outputs/research'/VERSION
CONFIG=ROOT/'config'/f'{VERSION}.json'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'));tz=cfg['timezone']
    oldfiles=check_protected()
    # The empirical supplement stays byte-for-byte intact. README may acquire
    # a new navigation entry, but its archived version remains in the old ZIP.
    empirical=json.loads((ROOT/'manifest_pit_nested_20261020.json').read_text(encoding='utf-8'))['files']
    empirical={n:h for n,h in empirical.items() if n!='README.md'}
    protocol=ROOT/cfg['existing_protocol']
    paths=[protocol,ROOT/'data/prospective/evidence_20261019/protocol.json',
           ROOT/'topic09_pit_nested_20261020_supplement.zip',ROOT/'manifest_pit_nested_20261020.json']
    empirical.update({p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    lockfile=OUT/'prerequisite_lock.json'
    lock=dict(config_sha256=sha(CONFIG),files=empirical)
    if lockfile.exists():assert json.loads(lockfile.read_text(encoding='utf-8'))==lock
    else:save_json(lockfile,lock)
    verify_mapping(empirical)
    protocol_data=json.loads(protocol.read_text(encoding='utf-8'))
    readiness_path=ROOT/'outputs/research/evidence_20261019/prospective_operations/readiness_calendar.csv'
    historical_readiness=historical_path(readiness_path.relative_to(ROOT).as_posix(),initialize()['paths'][readiness_path.relative_to(ROOT).as_posix()]['original_sha256'])
    readiness=pd.read_csv(historical_readiness)
    origins=pd.date_range(cfg['operational_origin_window_start_utc'],cfg['operational_origin_window_end_exclusive_utc'],inclusive='left')
    freeze=pd.Timestamp(cfg['internal_report_freeze_local'])
    # End-of-day bound is deliberately generous; actual submission hour unknown.
    latest_deadline=pd.Timestamp(cfg['submission_date_local'],tz=tz)+pd.Timedelta(days=1)
    now=pd.Timestamp.now(tz='UTC');rows=[]
    for origin in origins:
        info=origin-pd.Timedelta(days=cfg['information_lag_days'])
        market=origin-pd.Timedelta(days=cfg['market_lag_days'])
        label=origin+pd.Timedelta(days=cfg['label_assumed_delay_days'])
        status='conditional_future_capture_and_completeness_required'
        eligible=True
        if market.dayofweek>=5:
            eligible=False;status='ineligible_exact_market_return_day_is_weekend'
        if origin==origins[0]:
            # Existing attempt explicitly missed the 24h receipt cutoff. This
            # is read from the frozen readiness audit, not newly simulated.
            r=readiness[pd.to_datetime(readiness.origin_utc,utc=True)==origin]
            assert len(r)==1 and not bool(r.iloc[0].long_features_ready_from_archived_receipts)
            assert 'No matching snapshot' in r.iloc[0]['missing']
            eligible=False;status='missed_required_receipt_cutoff_in_existing_audit'
        before_freeze=eligible and label<=freeze
        before_deadline=eligible and label<latest_deadline
        rows.append(dict(origin_utc=origin.isoformat(),origin_local=origin.tz_convert(tz).isoformat(),
            information_day=info.date().isoformat(),market_observation_day=market.date().isoformat(),
            receipt_cutoff_utc=(origin-pd.Timedelta(hours=24)).isoformat(),
            label_assumed_available_utc=label.isoformat(),label_assumed_available_local=label.tz_convert(tz).isoformat(),
            potentially_eligible=bool(eligible),status=status,potential_mature_by_internal_freeze=bool(before_freeze),
            potential_mature_before_end_of_submission_date=bool(before_deadline),
            role='READINESS UPPER BOUND ONLY; no forecast or label generated'))
    table=pd.DataFrame(rows);table.to_csv(OUT/'deadline_readiness.csv',index=False,encoding='utf-8-sig')
    upper_freeze=int(table.potential_mature_by_internal_freeze.sum());upper_deadline=int(table.potential_mature_before_end_of_submission_date.sum())
    earliest=table[table.potentially_eligible].iloc[0]
    checks={
        'zero_potential_mature_origins_at_internal_freeze':upper_freeze==0,
        'at_most_one_potential_mature_origin_before_end_of_deadline_date':upper_deadline==1,
        'earliest_conditional_origin_23_october':earliest.origin_utc=='2026-10-23T00:00:00+00:00',
        'first_label_25_october_0700_vietnam':earliest.label_assumed_available_local=='2026-10-25T07:00:00+07:00',
        'report_freeze_precedes_any_possible_25_october_submission_hour':freeze<pd.Timestamp(cfg['submission_date_local'],tz=tz),
        'one_year_protocol_end_unchanged':protocol_data['end_utc_exclusive']=='2027-10-20T00:00:00Z',
        'all_empirical_artifacts_and_protocol_hashes_unchanged':verify_mapping(empirical)==len(empirical),
        'no_new_forecast_or_label_files':not (OUT/'forecasts').exists() and not (OUT/'labels').exists(),
    }
    assert all(checks.values()),checks
    decision=dict(version=VERSION,created_utc=now.isoformat(),user_deadline_local=cfg['submission_date_local'],timezone=tz,
        internal_report_freeze_local=freeze.isoformat(),decision=cfg['decision'],
        statistical_oos_window_for_submission=None,untouched_oos_requirement='not_met_for_final_design; explicitly disclosed',
        readiness_only_window=dict(start_utc=origins[0].isoformat(),end_exclusive_utc=cfg['operational_origin_window_end_exclusive_utc']),
        possible_mature_daily_origins_at_internal_freeze_upper_bound=upper_freeze,
        possible_mature_daily_origins_before_end_of_submission_date_upper_bound=upper_deadline,
        bounds_are_not_actual_forecasts=True,early_scoring_authorized=False,original_protocol_sha256=sha(protocol),
        operational_snapshot=historical_readiness.relative_to(ROOT).as_posix(),operational_snapshot_sha256=sha(historical_readiness),
        scheduler_installed=False)
    save_json(OUT/'decision.json',decision)
    schedule=pd.DataFrame([
        ['20/10','Đã hoàn tất','Audit PIT, revision/timing sensitivity, nested backtest và kiểm chứng; khóa phạm vi kết luận.'],
        ['21–23/10','Kế hoạch','Rà soát liên kết/bảng, đối chiếu kết luận với literature và viết phần phương pháp/hạn chế. Nếu tiếp tục prospective: chạy collector thủ công hằng ngày; chỉ báo coverage/execution theo protocol cũ.'],
        ['24/10, 18:00 VN','Mốc nội bộ đề xuất','Chốt bản báo cáo để nộp; kiểm tra package và trích dẫn. Không dùng nhãn 23/10 vì sớm nhất 25/10 mới khả dụng.'],
        ['25/10','Hạn nộp do người dùng cung cấp','Nộp kết quả lịch sử và trạng thái prospective. Chưa biết giờ nộp; không phụ thuộc vào dữ liệu chỉ đến sau 07:00 cùng ngày.'],
    ],columns=['Thời gian','Trạng thái','Nội dung'])
    schedule.to_csv(OUT/'submission_schedule.csv',index=False,encoding='utf-8-sig')
    short=table[['origin_local','market_observation_day','status','label_assumed_available_local']]
    note=f'''# Phương án nộp chủ đề 9 — hạn 25/10/2026

Đã nhận hạn nộp **25/10/2026**, múi giờ Việt Nam. Quyết định cập nhật ngày 20/10: dùng kết quả lịch sử đã khóa và công bố giới hạn; **không mở kỳ OOS mới để kiểm định skill trước hạn này**. Protocol một năm đến 20/10/2027 giữ nguyên, không chấm sớm qua namespace khác. Addendum này thay phần đề xuất đang chờ deadline, không sửa dữ liệu, mô hình hoặc các report cũ.

## Vì sao không thể chốt OOS xác nhận trước hạn

Với timing hiện tại, target UTC day D dùng information D−3, market return D−4; snapshot phải được nhận trước origin ít nhất 24h. Nhãn có mốc khả dụng giả định D+2. Origin 20/10 đã lỡ receipt cutoff; 21–22/10 cần market returns cuối tuần nên không đủ điều kiện. Origin **23/10 07:00 VN** mới có thể đủ điều kiện nếu capture/log đúng hạn và nguồn đầy đủ. Nhãn của origin này chỉ khả dụng sớm nhất **25/10 07:00 VN**, còn phụ thuộc actual source delivery.

{md(short)}

Chọn mốc nội bộ **24/10 lúc 18:00 VN** để khóa báo cáo trước mọi giờ nộp có thể trong 25/10. Đây là lựa chọn lập kế hoạch, không phải giờ nộp do người dùng cung cấp. Tại mốc này có **0 ngày dự báo mới có thể đủ nhãn**. Ngay cả nếu đợi đến hết 25/10 cũng có tối đa **1 origin có thể đủ nhãn**, không phải một forecast đã được log. BTC/ETH và nhiều mô hình trên cùng ngày không biến thành nhiều ngày độc lập. Lượng dữ liệu đó không đủ để kiểm định ổn định khả năng dự báo, CI theo thời gian hay cải thiện ngoài mẫu đáng tin cậy.

Không phải có quy định bắt buộc phải đánh giá một năm: trở ngại ở đây là độ trễ nhãn và chỉ 0–1 ngày có thể đánh giá. Không rút ngắn buffer, tái định nghĩa nhãn hoặc dùng outcomes đã xem chỉ để kịp tạo kết luận xác nhận.

## Phạm vi kết quả cho bài nộp

Dùng [audit và nested backtest](../pit_nested_20261020/report.html) làm bằng chứng lịch sử exploratory: 353/353 reconstruction/timing checks, 640 artifacts, 21/21 independent checks và 6 guards. Kết quả gộp có 3/32 macro ablations tốt hơn sau BH ở native D3; ba scenario matched đều 0/32, mỗi scenario 0/40 learned thắng benchmark sau BH. Kết quả có ý nghĩa riêng theo năm được báo đầy đủ trong report, không dùng để thay kết luận gộp.

Giữ nguyên baseline không MOVE; lịch sử dùng mẫu đầy đủ; forecasting có mẫu dài không USD và cấu hình có USD vintage từ 2019, so trên cùng sample. Broad USD không gọi là DXY. Hạn chế PIT của crypto/market proxies và vintage nhãn được trình bày riêng. Phần FOMC/nhân quả tiếp tục giữ các assumptions và giới hạn nhận dạng đã ghi trong [báo cáo evidence](../evidence_20261019/report.html); nested backtest không nâng cấp bằng chứng nhân quả.

Trong bài có thể ghi: **“Nghiên cứu đánh giá dự báo lịch sử bằng nested chronological backtest có kiểm soát ngày thông tin và nhãn, đồng thời thực hiện sensitivity về vintage/timing. Do các outcomes đã được xem trong quá trình phát triển và kỳ prospective chưa tích lũy đủ quan sát trước hạn nộp, nghiên cứu chưa có kiểm định untouched OOS cho thiết kế cuối và không tuyên bố khả năng dự báo tương lai đã được xác nhận.”**

Yêu cầu untouched OOS cho thiết kế cuối được ghi nhận là **chưa đạt**, không chuyển thành đã đạt chỉ bằng một đoạn hạn chế. Đây là giới hạn thực tế của bài nộp; không cần cố tạo kết quả dương để đề tài có kết quả nghiên cứu.

## Lịch hoàn thiện

{md(schedule)}

Cửa sổ theo dõi vận hành **20–24/10 UTC** chỉ phục vụ capture, receipt cutoff, feature completeness và forecast logging theo protocol cũ; không phải kỳ đánh giá performance mới. Không giả định đã cài scheduler và không hứa hệ thống tự chạy các ngày tới. Khi có người chủ động vận hành:

```powershell
py -3.11 run_prospective.py run
py -3.11 run_prospective.py validate
```

Không chạy future clock, không backfill dự báo đã lỡ cutoff và không dùng namespace mới để vượt gate chấm điểm của protocol hiện có. Nếu sau nộp cần thay kỳ/mô hình, phải đăng ký thay đổi trước outcomes liên quan; không chuyển dữ liệu đã xem thành holdout mới.

## Kiểm chứng addendum

{len(checks)}/{len(checks)} kiểm tra về timezone, nhãn, upper bound số origin, deadline và bảo toàn artifact đạt. [Quyết định máy đọc](decision.json), [lịch readiness](deadline_readiness.csv), [kiểm chứng](validation.json), [cấu hình](../../../config/submission_20261025.json). Không huấn luyện lại, không tạo forecasts/labels và không sửa các statistical results. Các mốc 0/1 là upper bounds theo quy tắc, không phải future scores.
'''
    (OUT/'report.md').write_text(note,encoding='utf-8')
    style='body{font:16px/1.6 system-ui,sans-serif;color:#153248;background:#f2f6f8;margin:0}main{max-width:1080px;margin:28px auto;background:white;padding:28px;border-radius:12px}h1{font-size:29px;line-height:1.25}h2{font-size:22px;margin-top:30px;color:#075873}a{color:#07688c}p{overflow-wrap:anywhere}.table-wrap{overflow-x:auto}table{border-collapse:collapse;min-width:650px;width:100%;font-size:13px}td,th{padding:10px;border-bottom:1px solid #dce5eb;text-align:left;vertical-align:top}th{background:#e9f1f5}pre{overflow-x:auto;background:#edf2f6;padding:16px}@media(max-width:700px){main{margin:0;padding:18px;border-radius:0}body{font-size:15px}h1{font-size:25px}}'
    (OUT/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kế hoạch nộp 25/10/2026</title><style>'+style+'</style><main>'+render_markdown(note)+'</main></html>',encoding='utf-8')
    save_json(OUT/'validation.json',dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),checks={k:bool(v) for k,v in checks.items()},passed=len(checks),total=len(checks),
        preserved_pre_pit_files=oldfiles,preserved_empirical_supplement_entries=len(empirical),models_retrained=0,new_forecasts=0,new_labels=0,
        original_protocol_unchanged=True,assumptions=['Submission hour not given; internal freeze chosen before start of submission date','Readiness bound conditional on real captures, source delivery and completeness']))
    verify_mapping(empirical)
    print(json.dumps(dict(report=str(OUT/'report.html'),checks=len(checks),mature_origins_at_freeze_upper_bound=upper_freeze,mature_origins_by_deadline_day_end_upper_bound=upper_deadline,old_files_preserved=check_protected()),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
