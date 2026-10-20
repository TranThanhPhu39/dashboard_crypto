"""Operational fixes around a frozen experiment, with no model/design changes."""
from contextlib import contextmanager
from html import escape
from pathlib import Path
import json
import zipfile

import joblib
from threadpoolctl import threadpool_limits
from src.evaluation.evidence_common import ROOT, OUT, RAW, LIVE, RESULTS, sha, save_json, pd, np, check_protected
from src.evaluation import latency_live as legacy
from src.data import latency_snapshots as snapshots
from src.models.latency import features, VARIANTS, model_predict, MACRO, USD, own

OPS = OUT / 'prospective_operations'
OPERATIONAL = OUT / 'prospective'
CONFIG = ROOT / 'config/prospective_operations_20261019.json'
SELECTION = []


def initialize():
    OPS.mkdir(parents=True, exist_ok=True)
    source = Path(__file__)
    archived_source = OPS/'code_snapshots'/(sha(source)+'.py')
    archived_source.parent.mkdir(exist_ok=True)
    if not archived_source.exists():
        with archived_source.open('xb') as stream:
            stream.write(source.read_bytes())
    assert sha(archived_source) == sha(source)
    lock = OPS / 'preservation_lock.json'
    if not lock.exists():
        # Existing research artifacts are immutable. Operational status/ledgers are
        # deliberately outside this lock because this task continues their use.
        files = []
        for folder in [ROOT/'models/latency_20261019', ROOT/'models/evidence_20261019']:
            files += [p for p in folder.rglob('*') if p.is_file()]
        files += [OUT/n for n in ['report.html', 'report.md', 'dashboard.html', 'source_snapshot.json']]
        files += [ROOT/n for n in ['topic09_evidence_20261019_supplement.zip',
            'config/latency_20261019.json', 'config/evidence_20261019.json',
            'data/prospective/latency_20261019/protocol.json',
            'data/prospective/evidence_20261019/protocol.json',
            'src/evaluation/latency_live.py', 'src/data/latency_snapshots.py',
            'src/evaluation/evidence_live.py', 'src/models/latency.py']]
        save_json(lock, dict(created_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
            config_sha256=sha(CONFIG), files={p.relative_to(ROOT).as_posix():sha(p) for p in files}))
    verify_preserved()


def verify_preserved():
    lock = json.loads((OPS/'preservation_lock.json').read_text(encoding='utf-8'))
    assert sha(CONFIG) == lock['config_sha256'], 'Operational configuration changed after lock'
    bad = [name for name, digest in lock['files'].items() if sha(ROOT/name) != digest]
    assert not bad, bad
    return len(lock['files'])


def candidate_check(record, info):
    """Check content, not just HTTP success, before choosing a receipt."""
    day = info.tz_localize(None)
    name = Path(record['file']).name
    if name in ['btc_coinmetrics.json', 'eth_coinmetrics.json']:
        asset = name.split('_')[0]
        series = legacy.prices(record, asset).reindex(pd.date_range(day-pd.Timedelta(days=30), day))
        assert series.notna().all() and (series > 0).all(), 'Required complete 31-day crypto grid missing'
    elif name in ['VIXCLS_fred.csv', 'sp500_yahoo.json', 'gold_yahoo.json']:
        series = legacy.market_series(record)
        change = series.diff() if name == 'VIXCLS_fred.csv' else np.log(series.where(series > 0)).diff()
        market_day = day-pd.Timedelta(days=1)
        assert market_day in change.index and pd.notna(change.loc[market_day]), 'Exact market return day missing; no carry'
    elif record.get('series_id'):
        sid = record['series_id']
        assert record.get('requested_vintage_date') == str(day.date()), 'Wrong requested vintage'
        frame = snapshots.alfred_frame(ROOT/record['file'], sid, str(day.date()))
        assert len(frame) >= 2, 'Too few observations in requested vintage'
        _, transformation = snapshots.PIT_SERIES[sid]
        if transformation == 'log':
            assert (frame[sid].iloc[-2:] > 0).all(), 'Nonpositive log input'
    else:
        raise AssertionError('Unrecognized prospective input type')


def choose_complete(rows, predicate, info, cutoff):
    eligible = sorted([r for r in rows if predicate(r)
        and info+pd.Timedelta(days=1) <= pd.Timestamp(r['available_at_utc']) <= cutoff],
        key=lambda r: (pd.Timestamp(r['available_at_utc']), r['file']))
    rejected = []
    for record in eligible:
        try:
            candidate_check(record, info)
        except (AssertionError, KeyError, ValueError, TypeError, StopIteration, IndexError) as exc:
            rejected.append(dict(file=record['file'], reason=str(exc)))
            continue
        if rejected:
            SELECTION.append(dict(information_day=str(info.date()), selected=record['file'], rejected=rejected))
        return record
    if eligible:
        SELECTION.append(dict(information_day=str(info.date()), selected=None, rejected=rejected))
        raise AssertionError('No complete eligible snapshot: '+'; '.join(r['reason'] for r in rejected))
    raise AssertionError('No matching snapshot received after information-day close and by cutoff24h')


@contextmanager
def bound():
    """Patch operational destinations only for the duration of a command."""
    saved = []
    def assign(module, name, value):
        saved.append((module, name, getattr(module, name)))
        setattr(module, name, value)
    def init_live():
        for path in [OPERATIONAL, RAW/'live', LIVE]:
            path.mkdir(parents=True, exist_ok=True)
    for module in [legacy, snapshots]:
        assign(module, 'RAW', RAW)
        assign(module, 'OUT', OPERATIONAL)
        assign(module, 'init', init_live)
    assign(legacy, 'LIVE', LIVE)
    assign(legacy, 'choose', choose_complete)
    assign(legacy, 'csv', lambda frame, name: frame.to_csv(OPERATIONAL/name, index=False, encoding='utf-8-sig', float_format='%.17g'))
    init_live()
    try:
        yield
    finally:
        for module, name, value in reversed(saved):
            setattr(module, name, value)


def read_committed(path, asset, origin, inventory):
    obj = json.loads(path.read_text(encoding='utf-8'))
    assert obj['asset'] == asset and pd.Timestamp(obj['origin_utc']) == origin
    logged = pd.Timestamp(obj['logged_at_utc'])
    assert logged < origin <= logged+pd.Timedelta(days=1)
    assert pd.Timestamp(obj['target_end_utc']) == origin+pd.Timedelta(days=1)
    assert obj['protocol_sha256'] == sha(LIVE/'protocol.json')
    if obj.get('operational_adapter_sha256'):
        digest = obj['operational_adapter_sha256']
        assert len(digest) == 64 and all(c in '0123456789abcdef' for c in digest)
        assert sha(OPS/'code_snapshots'/(digest+'.py')) == digest
    envelope_path = ROOT/obj['envelope']
    assert envelope_path.resolve().is_relative_to(ROOT.resolve())
    assert sha(envelope_path) == obj['envelope_sha256']
    env = json.loads(envelope_path.read_text(encoding='utf-8'))
    assert env['asset'] == asset and pd.Timestamp(env['origin_utc']) == origin
    for line in env['lineage'].values():
        assert pd.Timestamp(line['available_at_utc']) <= origin-pd.Timedelta(days=1)
        assert sha(ROOT/line['source_file']) == line['source_sha256']
        assert sha(ROOT/line['manifest']) == line['manifest_sha256']
    expected = {(variant, target, kind) for variant in VARIANTS
        if env['long_eligible'] and (variant.startswith('long') or env['common_eligible'])
        for target in ['return', 'squared_return']
        for kind in ['historical_mean', 'natural_benchmark', 'elastic_net', 'gradient_boosting']}
    found = [(r['variant'], r['target'], r['model']) for r in obj['predictions']]
    assert len(found) == len(set(found)) and set(found) == expected and expected
    lookup = inventory.set_index(['asset', 'variant', 'target', 'model'])
    for record in obj['predictions']:
        assert np.isfinite(record['predicted'])
        assert record['target'] != 'squared_return' or record['predicted'] > 0
        if record['model'] in ['elastic_net', 'gradient_boosting']:
            row = lookup.loc[(asset, record['variant'], record['target'], record['model'])]
            assert record['model_sha256'] == row.sha256 == sha(ROOT/row.file)
    return obj


def emit_asset(asset, origin, env, inventory, states):
    predictions = []
    with threadpool_limits(limits=2):
        for variant in VARIANTS:
            if not env['long_eligible'] or (not variant.startswith('long') and not env['common_eligible']):
                continue
            columns = features(asset, variant)
            x = pd.DataFrame([[env['features'][c] for c in columns]], columns=columns)
            for c in columns:
                legacy.clock(origin, pd.Timestamp(env['lineage'][c]['available_at_utc']), pd.Timestamp.now(tz='UTC'))
            for target in ['return', 'squared_return']:
                state = states[(states.asset==asset)&(states.variant==variant)&(states.target==target)].iloc[0]
                assert pd.Timestamp(state.last_fit_label_available).tz_localize('UTC') <= origin-pd.Timedelta(days=1)
                for kind in ['historical_mean', 'natural_benchmark', 'elastic_net', 'gradient_boosting']:
                    digest = None
                    if kind in ['elastic_net', 'gradient_boosting']:
                        row = inventory[(inventory.asset==asset)&(inventory.variant==variant)&(inventory.target==target)&(inventory.model==kind)].iloc[0]
                        payload = joblib.load(ROOT/row.file)
                        assert payload['features'] == columns and payload['config_sha256'] == sha(legacy.CONFIG)
                        value = float(model_predict(payload['fitted'], x, kind, target)[0])
                        digest = row.sha256
                    else:
                        value = float(state.historical_mean) if kind == 'historical_mean' else 0. if target == 'return' else env['features'][asset+'_vol30_annualized']**2/365
                    assert np.isfinite(value) and (target != 'squared_return' or value > 0)
                    predictions.append(dict(variant=variant, target=target, model=kind, predicted=value, model_sha256=digest))
    return predictions


def forecast(origin=None):
    current = pd.Timestamp.now(tz='UTC')
    origin = pd.Timestamp(origin) if origin is not None else current.normalize()+pd.Timedelta(days=1)
    assert origin.tzinfo is not None
    origin = origin.tz_convert('UTC')
    protocol = legacy.protocol()
    legacy.clock(origin, origin-pd.Timedelta(days=1), current)
    assert pd.Timestamp(protocol['start_utc']) <= origin < pd.Timestamp(protocol['end_utc_exclusive'])
    inventory, _ = legacy.frozen()
    rows = legacy.records()
    states = pd.read_csv(OPERATIONAL/'benchmark_states.csv')
    attempts = []
    for asset in ['btc', 'eth']:
        path = LIVE/'predictions'/f'{origin.date()}_{asset}.json'
        if path.exists():
            obj = read_committed(path, asset, origin, inventory)
            env = json.loads((ROOT/obj['envelope']).read_text(encoding='utf-8'))
            attempts.append(dict(asset=asset, origin_utc=origin.isoformat(), status='ALREADY_COMMITTED',
                long_eligible=env['long_eligible'], common_eligible=env['common_eligible'],
                predictions_logged=0, predictions_existing=len(obj['predictions']), missing=env['missing'], envelope=obj['envelope']))
            continue
        env = legacy.envelope(origin, asset, rows)
        stamp = pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%S%fZ')
        envpath = LIVE/'envelopes'/f'{origin.date()}_{asset}_{stamp}.json'
        env['operational_adapter_sha256'] = sha(Path(__file__))
        legacy.immutable(envpath, env)
        predictions = emit_asset(asset, origin, env, inventory, states)
        if predictions:
            logged = pd.Timestamp.now(tz='UTC')
            legacy.clock(origin, origin-pd.Timedelta(days=1), logged)
            legacy.immutable(path, dict(asset=asset, origin_utc=origin.isoformat(),
                target_end_utc=(origin+pd.Timedelta(days=1)).isoformat(), logged_at_utc=logged.isoformat(),
                envelope=envpath.relative_to(ROOT).as_posix(), envelope_sha256=sha(envpath),
                protocol_sha256=sha(LIVE/'protocol.json'), operational_adapter_sha256=sha(Path(__file__)), predictions=predictions))
        attempts.append(dict(asset=asset, origin_utc=origin.isoformat(),
            status='COMMITTED' if predictions else 'INELIGIBLE_INPUTS', long_eligible=env['long_eligible'],
            common_eligible=env['common_eligible'], predictions_logged=len(predictions), predictions_existing=0,
            missing=env['missing'], envelope=envpath.relative_to(ROOT).as_posix()))
    obj = dict(attempted_at_utc=pd.Timestamp.now(tz='UTC').isoformat(), origin_utc=origin.isoformat(), attempts=attempts,
        total_predictions=sum(r['predictions_logged'] for r in attempts),
        existing_predictions=sum(r['predictions_existing'] for r in attempts),
        performance='Not evaluated; no future labels or confirmed predictive skill claimed')
    legacy.immutable(LIVE/'attempts'/f'{current.strftime("%Y%m%dT%H%M%S%fZ")}.json', obj)
    save_json(OPERATIONAL/'prospective_status.json', obj)
    return obj


def capture_needed(refresh=False):
    if refresh:
        return True
    latest = OPERATIONAL/'latest_capture.json'
    if not latest.exists():
        return True
    obj = json.loads(latest.read_text(encoding='utf-8'))
    path = ROOT/obj['manifest']
    assert sha(path) == obj['sha256']
    manifest = json.loads(path.read_text(encoding='utf-8'))
    return (pd.Timestamp(manifest['capture_started_utc']).date() != pd.Timestamp.now(tz='UTC').date()
        or len(manifest['sources']) != 17
        or any(r['status'] != 'ok' for r in manifest['sources']))


def run(refresh_capture=False):
    SELECTION.clear()
    with bound():
        if capture_needed(refresh_capture):
            snapshots.collect()
        result = forecast()
        legacy.labels()
        legacy.evaluate()
    save_json(OPERATIONAL/'namespace_audit.json', dict(
        original_protocol_sha256=sha(ROOT/'data/prospective/latency_20261019/protocol.json'),
        operational_protocol_sha256=sha(LIVE/'protocol.json'),
        model_inventory_sha256=sha(RESULTS/'latency_20261019/model_inventory.csv'),
        model_configuration_sha256=sha(ROOT/'config/latency_20261019.json'),
        operational_adapter_sha256=sha(Path(__file__)),
        predictions_logged=result['total_predictions'], existing_predictions=result['existing_predictions'],
        scope='Existing frozen latency40 models, same protocol and fixed window. Operational complete-input selection and idempotent per-asset commits; no RV deployment or scheduler.'))
    save_json(OPS/'last_run.json', dict(at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
        adapter_sha256=sha(Path(__file__)), result=result, candidate_fallbacks=SELECTION))
    audit()
    verify_preserved()
    check_protected()
    print(json.dumps(dict(new_predictions=result['total_predictions'], existing=result['existing_predictions'],
        status='PROSPECTIVE_OPERATED_WITH_UNCHANGED_PROTOCOL'), ensure_ascii=False))


def audit():
    historical = pd.read_csv(ROOT/'data/processed/forecast_origins_vintage_macro.csv', parse_dates=['date_utc'])
    historical = historical.set_index('date_utc').replace([np.inf, -np.inf], np.nan)
    summaries = []
    market = ['vix_change_lag1_proxy', 'sp500_log_return_lag1_proxy', 'gold_futures_log_return_lag1_proxy']
    for asset in ['btc', 'eth']:
        own_ok = historical[own(asset)].notna().all(axis=1)
        market_ok = historical[market].notna().all(axis=1)
        macro_ok = historical[MACRO].notna().all(axis=1)
        usd_ok = historical[USD].notna().all(axis=1)
        # Information-day row I gives origin I+3 and proxy observation I-1.
        # Counts are feature coverage only, without inspecting targets/losses.
        weekend = (historical.index-pd.Timedelta(days=1)).dayofweek >= 5
        summaries.append(dict(asset=asset, information_rows=len(historical), own_feature_rows=int(own_ok.sum()),
            long_matched_feature_rows=int((own_ok&macro_ok).sum()),
            common_usd_feature_rows=int((own_ok&macro_ok&usd_ok).sum()),
            own_rows_rejected_by_matched_macro=int((own_ok&~macro_ok).sum()),
            own_rows_with_missing_market=int((own_ok&~market_ok).sum()),
            own_rows_with_market_weekend=int((own_ok&weekend).sum()),
            own_rows_with_missing_market_on_weekday=int((own_ok&~market_ok&~weekend).sum()),
            note='Feature-only counts on original information rows; no prospective predictions or target-based sample selection'))
    pd.DataFrame(summaries).to_csv(OPS/'historical_feature_coverage.csv', index=False, encoding='utf-8-sig')
    multiplicity = []
    for filename in ['rv_ablation_tests.csv', 'regime_interaction_tests.csv']:
        frame = pd.read_csv(OUT/filename)
        multiplicity.append(dict(file=filename, tests=len(frame),
            raw_p_below005=int((frame.pvalue<.05).sum()), adjusted_q_below005=int((frame.qvalue_bh<.05).sum())))
    readiness = []
    current = pd.Timestamp.now(tz='UTC')
    with bound():
        records = legacy.records()
        for origin in pd.date_range(current.normalize()+pd.Timedelta(days=1), periods=14, tz='UTC'):
            info = origin-pd.Timedelta(days=3)
            env = legacy.envelope(origin, 'btc', records)
            readiness.append(dict(origin_utc=origin.isoformat(), information_day=str(info.date()),
                market_observation_day=str((info-pd.Timedelta(days=1)).date()),
                market_day_is_weekend=(info-pd.Timedelta(days=1)).dayofweek>=5,
                capture_window_start_utc=(origin-pd.Timedelta(days=2)).isoformat(),
                receipt_cutoff_utc=(origin-pd.Timedelta(days=1)).isoformat(),
                earliest_logging_utc=(origin-pd.Timedelta(days=1)).isoformat(),
                latest_logging_exclusive_utc=origin.isoformat(),
                long_features_ready_from_archived_receipts=env['long_eligible'],
                common_features_ready_from_archived_receipts=env['common_eligible'],
                missing=json.dumps(env['missing'], ensure_ascii=False),
                role='READINESS ONLY; no synthetic forecast; weekday is not a verified exchange holiday calendar'))
    pd.DataFrame(readiness).to_csv(OPS/'readiness_calendar.csv', index=False, encoding='utf-8-sig')
    files = list((LIVE/'predictions').glob('*.json'))
    labels = list((LIVE/'labels').glob('*.json'))
    prediction_rows = sum(len(json.loads(p.read_text(encoding='utf-8'))['predictions']) for p in files)
    evaluation = json.loads((OPERATIONAL/'prospective_evaluation.json').read_text(encoding='utf-8'))
    capture = json.loads((OPERATIONAL/'latest_capture.json').read_text(encoding='utf-8'))
    rule_rows = [
        dict(rule='24h receipt cutoff + D-3 features', classification='Conservative locked design', consequence='New capture cannot be used for the immediate next origin; warm-up is expected', action='Keep; changing buffer requires a separate design'),
        dict(rule='Matched own/macro origins + exact D-4 market return', classification='Locked comparison sample', consequence='Missing weekend/holiday market day also suppresses own-only forecasts; not a claim of 24/7 coverage', action='Keep; report coverage and missing days'),
        dict(rule='Earliest timestamp without checking complete content', classification='Operational fault reproduced with synthetic input', consequence='Earlier partial response can hide a later complete response within cutoff', action='Fixed in adapter: earliest COMPLETE eligible candidate; original clock retained'),
        dict(rule='Immutable forecast path on every rerun', classification='Operational fault reproduced with retry test', consequence='Second run can raise FileExistsError; partial per-asset completion can block recovery', action='Fixed in adapter: validate and reuse existing commit; resume missing asset'),
        dict(rule='One capture per UTC day even after source failure', classification='Operational retry limitation', consequence='Transient failures cannot recover through the old wrapper on the same day', action='Retry failed captures; explicit refresh archives new bytes without replacing old ones'),
        dict(rule='Fixed evaluation end 2027-10-20; labels close+24h', classification='Precommitted evaluation policy', consequence='No performance score now; operational coverage and label readiness are still visible', action='Keep; not a mathematical requirement to wait a year, but no interim tuning or protocol changes'),
        dict(rule='BH correction and HAC/HC3 comparisons', classification='Statistical inference choices', consequence='Multiplicity/inference sensitivity can reduce significant findings; not a computational failure', action='Keep original families; expose raw and adjusted counts without selecting favorable inference'),
        dict(rule='Complete 288-return UTC RV day', classification='Measurement quality design', consequence='Partial and malformed days are excluded; sample shorter than daily baseline', action='Keep audit/exclusions; no interpolation or unapproved partial-day scaling'),
        dict(rule='Sign restrictions and admissible rotation set', classification='Economic identification assumptions', consequence='Information-component bounds can be unbounded; intervals for one rotation are not full identified-set confidence sets', action='Disclose assumptions and partial identification; do not narrow the set to manufacture significance'),
        dict(rule='VAR residual whiteness and ARCH diagnostics', classification='Model adequacy limitations', consequence='Remaining serial dependence/heteroskedasticity affects inference; stable roots or relaxed thresholds do not fix this', action='Keep VAR as a diagnostic comparison; do not remove observations or change thresholds to pass'),
    ]
    save_json(OPS/'rule_audit.json', dict(audited_at_utc=current.isoformat(), rules=rule_rows,
        historical_coverage=summaries, multiplicity=multiplicity,
        ledger=dict(asset_day_files=len(files), prediction_rows=prediction_rows, label_files=len(labels),
            attempt_files=len(list((LIVE/'attempts').glob('*.json'))),
            missing_label_files=len([p for p in files if not (LIVE/'labels'/p.name).exists()])),
        latest_capture=capture, evaluation=evaluation, preserved_files=verify_preserved(),
        performance_claim=False, protocol_sha256=sha(LIVE/'protocol.json'),
        sources=[dict(url='https://github.com/coinmetrics/docs-website/blob/master/asset-metrics/market/priceusd.md',
            finding='PriceUSD daily value is end-of-day UTC; kept original day+1 close convention'),
            dict(url='https://fred.stlouisfed.org/docs/api/fred/realtime_period.html',
            finding='ALFRED real-time periods identify historical information dates; date-level vintage is not an intraday receipt certificate')]))
    return readiness


def product():
    if not (OPS/'rule_audit.json').exists():
        audit()
    obj = json.loads((OPS/'rule_audit.json').read_text(encoding='utf-8'))
    calendar = pd.read_csv(OPS/'readiness_calendar.csv')
    rules = pd.DataFrame([
        ['Cutoff 24 giờ; features D−3', 'Thiết kế bảo thủ', 'Snapshot mới chưa dùng cho origin ngày kế tiếp. Cần khởi động tích lũy receipts; giữ nguyên ngày đệm.'],
        ['Ghép cùng mẫu; market return đúng ngày D−4', 'Đánh đổi về độ phủ', 'Thiếu ngày nghỉ cũng chặn own-only. Kết quả chỉ đại diện các origin đủ điều kiện; mẫu 24/7 riêng sẽ là thiết kế khác.'],
        ['Chọn snapshot đầu tiên dù thiếu nội dung', 'Đã sửa lỗi vận hành', 'Thử bản đủ dữ liệu tiếp theo trong cùng cutoff/vintage; không nới thời gian nhận. Lỗi tái hiện bằng dữ liệu kiểm thử, chưa ghi nhận là nguyên nhân thực tế của lượt 0 dự báo.'],
        ['Chạy lại hoặc dở dang giữa hai tài sản', 'Đã sửa lỗi vận hành', 'Kiểm tra và tái dùng commit cũ, tiếp tục tài sản còn thiếu. Không ghi đè dự báo đã chốt.'],
        ['Chỉ tải một lần/ngày kể cả lần lỗi', 'Đã sửa hạn chế retry', 'Lần tải thất bại được thử lại. --refresh-capture lưu snapshot mới riêng, không thay bytes cũ.'],
        ['Chờ hết cửa sổ đánh giá đã khóa', 'Chính sách nghiên cứu', 'Không bắt buộc về mặt kỹ thuật phải chờ một năm; đây là cam kết tránh xem kết quả rồi điều chỉnh. Hiện vẫn theo dõi được coverage, nhãn và lỗi vận hành.'],
        ['BH, HAC/HC3, sign restrictions', 'Giới hạn suy luận', 'Không nới ngưỡng để có ý nghĩa thống kê. Miền nhận dạng rộng, mẫu stress ít và độ nhạy sai số không phải lỗi chương trình.'],
        ['RV đủ lưới; chẩn đoán VAR', 'Chất lượng đo lường/đặc tả', 'Giữ danh sách ngày/nến loại. ARCH và whiteness chưa đạt cần được công bố; không thể sửa bằng đổi ngưỡng kiểm định.'],
    ], columns=['Quy tắc', 'Phân loại', 'Ảnh hưởng và xử lý'])
    coverage = pd.DataFrame([dict(
        asset=r['asset'].upper(), own=r['own_feature_rows'], matched=r['long_matched_feature_rows'],
        reduction=round(100*r['own_rows_rejected_by_matched_macro']/r['own_feature_rows'], 2),
        weekend=r['own_rows_with_market_weekend'], weekday_missing=r['own_rows_with_missing_market_on_weekday'],
        usd=r['common_usd_feature_rows']) for r in obj['historical_coverage']]).rename(columns={
            'asset':'Tài sản', 'own':'Ngày đủ own features', 'matched':'Ngày đủ macro ghép mẫu', 'reduction':'Giảm độ phủ (%)',
            'weekend':'Market day là cuối tuần', 'weekday_missing':'Thiếu market ngày thường', 'usd':'Ngày đủ thêm USD'})
    calendar_display = calendar[['origin_utc','information_day','market_observation_day','market_day_is_weekend',
        'capture_window_start_utc','receipt_cutoff_utc','earliest_logging_utc','long_features_ready_from_archived_receipts']].rename(columns={
        'origin_utc':'Origin UTC', 'information_day':'Ngày thông tin', 'market_observation_day':'Ngày market',
        'market_day_is_weekend':'Market cuối tuần', 'capture_window_start_utc':'Bắt đầu cửa sổ nhận',
        'receipt_cutoff_utc':'Cutoff nhận UTC', 'earliest_logging_utc':'Bắt đầu được log',
        'long_features_ready_from_archived_receipts':'Đủ từ receipts đã lưu'})
    for column in ['Origin UTC', 'Bắt đầu cửa sổ nhận', 'Cutoff nhận UTC', 'Bắt đầu được log']:
        calendar_display[column] = pd.to_datetime(calendar_display[column], utc=True).dt.strftime('%d/%m %H:%M')
    calendar_display['Market cuối tuần'] = calendar_display['Market cuối tuần'].map({True:'Có', False:'Không'})
    calendar_display['Đủ từ receipts đã lưu'] = calendar_display['Đủ từ receipts đã lưu'].map({True:'Đủ', False:'Chưa'})
    multiplicity = obj['multiplicity'][0]
    body = f'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prospective operations — 19/10/2026</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1120px;margin:auto;padding:24px;color:#142c40;background:#f4f8fc}}h1{{font-size:27px}}section{{background:white;border:1px solid #d7e3ee;padding:20px;margin:20px 0;border-radius:10px}}.table{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;border-bottom:1px solid #d7e3ee;text-align:left;vertical-align:top}}a{{color:#086890}}code{{overflow-wrap:anywhere}}</style>
<h1>Rà soát quy tắc và vận hành dự báo tương lai</h1><p>Audit UTC: {escape(obj['audited_at_utc'])}. Protocol và 40 mô hình học máy giữ nguyên. Đây là trạng thái vận hành; chưa có đánh giá hiệu quả dự báo tương lai.</p>
<section><h2>Nhật ký thực tế</h2><p>{obj['latest_capture']['sources_ok']}/{obj['latest_capture']['sources_total']} nguồn thành công trong capture mới nhất. Đã ghi {obj['ledger']['asset_day_files']} tệp tài sản-ngày / {obj['ledger']['prediction_rows']} giá trị dự báo; {obj['ledger']['label_files']} tệp nhãn. Số attempt: {obj['ledger']['attempt_files']}.</p>
<p>Evaluation: <strong>{escape(obj['evaluation']['status'])}</strong>. Fixed end: {escape(obj['evaluation'].get('fixed_end_utc','2027-10-20T00:00:00Z'))}. Không dùng đồng hồ giả hoặc snapshot tải sau cutoff để tạo dự báo quá khứ.</p></section>
<section><h2>Quy tắc nào cần giữ, điểm nào đã sửa?</h2><div class="table">{rules.to_html(index=False,escape=True,border=0)}</div></section>
<section><h2>Ảnh hưởng tới độ phủ lịch sử</h2><p>Đếm điều kiện features, không dùng nhãn hay loss để chọn mẫu. Các nhóm nguyên nhân có thể chồng lấn. Đây không phải số ngày prospective đã chạy.</p><div class="table">{coverage.to_html(index=False,escape=True,border=0)}</div>
<p>Macro RV: chỉ {multiplicity['raw_p_below005']}/{multiplicity['tests']} phép so sánh có p&lt;0,05 trước điều chỉnh; sau BH là {multiplicity['adjusted_q_below005']}/{multiplicity['tests']}. Kết quả yếu không chỉ do điều chỉnh BH.</p></section>
<section><h2>Lịch chuẩn bị 14 ngày</h2><p>Chỉ kiểm tra khả năng đáp ứng từ receipts đang lưu. Không phải dự báo hoặc cam kết ngày nào sẽ có đủ dữ liệu. Cờ cuối tuần chưa bao gồm toàn bộ ngày lễ thị trường.</p><div class="table">{calendar_display.to_html(index=False,escape=True,border=0)}</div>
<p>Với thời điểm bắt đầu lưu19/10: origin20/10 đã lỡ cutoff;21/10 và22/10 đòi market day cuối tuần. Origin23/10 có thể là mốc đầu nếu thu đủ dữ liệu trong21/10 UTC và log trong22/10 UTC. Đây là dự tính điều kiện, không phải forecast đã ghi.</p></section>
<section><h2>Cách vận hành</h2><p><code>py -3.11 run_prospective.py run</code> — thu thập nếu cần, ghi dự báo đủ điều kiện, nhận nhãn đã tới hạn và giữ evaluation gate.</p><p><code>py -3.11 run_prospective.py run --refresh-capture</code> — tải một snapshot mới, lưu riêng nguyên bytes/receipt. Chạy lại cùng kỳ tái dùng bản dự báo đã commit; không ghi đè.</p><p>Chạy một lần trong mỗi ngày UTC khi đang vận hành, ví dụ16:00 giờ Việt Nam (09:00 UTC). Với origin23/10, cần capture21/10 và log22/10. Lệnh thường ngày thực hiện cả hai nhiệm vụ tương ứng cho các origin khác nhau. Chưa cài scheduler hoặc tác vụ nền.</p></section>
<p><a href="rule_audit.json">Audit JSON</a> · <a href="readiness_calendar.csv">Lịch CSV</a> · <a href="historical_feature_coverage.csv">Coverage CSV</a> · <a href="validation.json">Kiểm chứng vận hành</a> · <a href="../report.html">Báo cáo nghiên cứu đã giữ nguyên</a></p>
<p>Định nghĩa ngày: <a href="https://github.com/coinmetrics/docs-website/blob/master/asset-metrics/market/priceusd.md">Coin Metrics PriceUSD</a>; vintage: <a href="https://fred.stlouisfed.org/docs/api/fred/realtime_period.html">FRED/ALFRED real-time periods</a>.</p></html>'''
    (OPS/'report.html').write_text(body, encoding='utf-8')
    print('Operational report:', (OPS/'report.html').relative_to(ROOT))


def validate():
    from unittest import TextTestRunner, defaultTestLoader
    suite = defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_prospective_operations.py')
    result = TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful(), 'Operational guard tests failed'
    with bound():
        inventory, _ = legacy.frozen()
        records = legacy.records()
        for file in (LIVE/'predictions').glob('*.json'):
            obj = json.loads(file.read_text(encoding='utf-8'))
            read_committed(file, obj['asset'], pd.Timestamp(obj['origin_utc']), inventory)
        protocol = legacy.protocol()
    evaluation = json.loads((OPERATIONAL/'prospective_evaluation.json').read_text(encoding='utf-8'))
    if pd.Timestamp.now(tz='UTC') < pd.Timestamp(protocol['end_utc_exclusive'])+pd.Timedelta(days=1):
        assert evaluation['status'] == 'PENDING_FIXED_EVALUATION_WINDOW' and not evaluation['performance_claim']
    protected = check_protected()
    save_json(OPS/'validation.json', dict(status='PASS', tested_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
        unit_tests=result.testsRun, actual_source_records_verified=len(records),
        preserved_files=verify_preserved(), older_protected_files=protected,
        protocol_unchanged=True, model_inventory_verified=True, future_performance_claim=False,
        scope='Operational safety, retry behavior, source/commit integrity; not evidence of predictive skill'))


def package():
    verify_preserved()
    assert json.loads((OPS/'validation.json').read_text())['status'] == 'PASS'
    destination = ROOT/'topic09_prospective_operations_20261019_supplement.zip'
    assert not destination.exists(), 'Published supplement cannot be overwritten'
    files = [ROOT/n for n in ['run_prospective.py', 'src/evaluation/prospective_operations.py',
        'tests/test_prospective_operations.py', 'tests/preview_prospective_operations.cjs',
        'tests/reproduce_prospective_bundle.py',
        'config/prospective_operations_20261019.json', 'README.md']]
    files += [p for p in OPS.rglob('*') if p.is_file()]
    files += [p for p in LIVE.rglob('*') if p.is_file()]
    files += [p for p in OPERATIONAL.rglob('*') if p.is_file()]
    files += [p for p in (RAW/'live').rglob('*') if p.is_file()]
    manifest = {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))}
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in manifest:
            archive.write(ROOT/name, name)
        archive.writestr('manifest_prospective_operations_20261019.json', json.dumps(dict(files=manifest,
            requires='Existing full base repository and evidence_20261019 supplement; external dependencies required',
            frozen_protocol_sha256=sha(LIVE/'protocol.json')), ensure_ascii=False, indent=2))
    import hashlib
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert all(hashlib.sha256(archive.read(name)).hexdigest() == digest for name,digest in manifest.items())
    save_json(ROOT/'package_prospective_operations_20261019.json', dict(file=destination.name,
        bytes=destination.stat().st_size, sha256=sha(destination), files=len(manifest)+1,
        all_crc_sha256_verified=True, standalone=False))
    print('Verified supplement:', destination.name)
