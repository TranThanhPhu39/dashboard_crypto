"""Canonical submission report/dashboard from frozen estimates; no model fits."""
from src.evaluation.release_preservation import ROOT,OUT,CONFIG,sha,save_json,initialize,verify_mapping,historical_path
from research_common import pd,np,json
from src.robustness_product import md,render_markdown
import re,html,zipfile,hashlib

BASE=ROOT/'outputs/research'
SOURCES={}

def prose(text):
    """Space numeric phrases in human text; never alter source data or keys."""
    for word in ['ngày','đến','từ','có','gộp','đều','matched','whiteness','stress','snapshot','horizon','family','replay','lại','nộp','bộ','Origin','nhất','hết','đa','dùng','gồm','với','thêm','năm','trước','sau','Pre','HAC']:
        text=re.sub(r'(?<![\w/])('+word+r')(?=\d)',r'\1 ',text)
    for a,b in [('đạtBH','đạt BH'),('sauBH','sau BH'),('pre/post2020','pre/post 2020'),('stress9events','stress 9 events'),('bỏ03/','bỏ 03/'),('matched728','matched 728'),('native949','native 949'),('USDT5m','USDT 5m'),('tổng7-day','tổng 7-day'),('feature definitions,28','feature definitions, 28'),('rows,353','rows, 353'),(';21/21','; 21/21'),('checks,6','checks, 6'),('điểm phần trăm return/+10bps','điểm phần trăm return / +10 bps')]:text=text.replace(a,b)
    return text

def load(version,name):
    p=BASE/version/name;SOURCES[p.relative_to(ROOT).as_posix()]=sha(p)
    return pd.read_csv(p,float_precision='round_trip')

def records(frame):
    return json.loads(frame.replace([np.inf,-np.inf],np.nan).to_json(orient='records',double_precision=15))

def live_status():
    from src.automation_runtime import automation_summary
    folder=ROOT/'data/prospective/evidence_20261019'
    files=list((folder/'predictions').glob('*.json'))
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    last=BASE/'evidence_20261019/prospective_operations/last_run.json'
    stamp=json.loads(last.read_text(encoding='utf-8'))['at_utc'] if last.exists() else None
    automation=automation_summary()
    evaluation=json.loads((BASE/'evidence_20261019/prospective/prospective_evaluation.json').read_text(encoding='utf-8'))
    return dict(prediction_files=len(files),prediction_rows=sum(len(json.loads(p.read_text(encoding='utf-8'))['predictions']) for p in files),
        label_files=len(list((folder/'labels').glob('*.json'))),fixed_end=protocol['end_utc_exclusive'],
        last_run_local=pd.Timestamp(stamp).tz_convert('Asia/Ho_Chi_Minh').isoformat() if stamp else 'chưa có',
        performance=evaluation['status'],performance_claim=False,scheduler_installed=automation['installed'],automation=automation)

def build():
    migration=initialize();OUT.mkdir(parents=True,exist_ok=True);SOURCES.clear()
    original=migration['paths']['dashboard/index.html']
    archived=historical_path('dashboard/index.html',original['original_sha256'])
    source=archived.read_text(encoding='utf-8')
    base=json.loads(re.search(r'const DATA=(.*?);\s*const el=',source,re.S).group(1))
    SOURCES[archived.relative_to(ROOT).as_posix()]=sha(archived)
    pit='pit_nested_20261020';ev='evidence_20261019';bp='blueprint_20261019'
    ablation=load(pit,'ablation_tests.csv');bench=load(pit,'benchmark_tests.csv');sensitivity=load(pit,'sensitivity_tests.csv')
    metrics=load(pit,'forecast_metrics.csv');samples=load(pit,'sample_summary.csv');features=load(pit,'feature_evidence.csv');revision=load(pit,'revision_magnitude.csv')
    ranges=load(ev,'full_rotation_ranges.csv');regimes=load(ev,'regime_interaction_tests.csv')
    rvab=load(ev,'rv_ablation_tests.csv');rvbench=load(ev,'rv_benchmark_tests.csv');rvmetrics=load(ev,'rv_forecast_metrics.csv')
    vard=load(bp,'joint_VAR_diagnostics.csv');arch=load('robustness_20261019','joint_VAR_ARCH.csv')
    daily=load(bp,'calendar_LP.csv');daily_delta=load(bp,'calendar_stress_differences.csv');monetary=load(bp,'monetary_LP.csv')
    influence=load('robustness_20261019','monetary_sensitivity.csv')
    counts=[]
    for scenario,g in ablation[ablation.scope.astype(str)=='pooled'].groupby('scenario',sort=False):
        b=bench[(bench.scope.astype(str)=='pooled')&(bench.scenario==scenario)]
        counts.append(dict(scenario=scenario,macro_comparisons=len(g),macro_better_BH=int(((g.mean_loss_new_minus_base<0)&(g.qvalue_bh<.05)).sum()),
            macro_worse_BH=int(((g.mean_loss_new_minus_base>0)&(g.qvalue_bh<.05)).sum()),benchmark_comparisons=len(b),
            learned_better_BH=int(((b.mean_loss_new_minus_base<0)&(b.qvalue_bh<.05)).sum()),learned_worse_BH=int(((b.mean_loss_new_minus_base>0)&(b.qvalue_bh<.05)).sum())))
    counts=pd.DataFrame(counts)
    rvwins=int(((rvbench.mean_loss_added_minus_base<0)&(rvbench.qvalue_bh<.05)).sum())
    rvmacro=int(((rvab.mean_loss_added_minus_base<0)&(rvab.qvalue_bh<.05)).sum())
    regime_summary=regimes.groupby('contrast',sort=False).agg(tests=('asset','size'),BH_HAC=('qvalue_bh',lambda x:int((x<.05).sum())),BH_HC3=('qvalue_hc3_bh',lambda x:int((x<.05).sum())),n0=('n_group0','min'),n1=('n_group1','min')).reset_index()
    bounds=ranges[(ranges.outcome=='intraday')&(ranges.shock=='policy')][['asset','lower_per10bps','upper_per10bps','unbounded']]
    now=pd.Timestamp.now(tz='UTC');local=now.tz_convert('Asia/Ho_Chi_Minh').isoformat();status=live_status()
    from src.oos_followup import build_followup
    oos_followup=build_followup(status,now)
    from src.automation_runtime import automation_description
    automation_note=automation_description(status['automation'])
    summary=f'FOMC: thành phần chính sách gắn với phản ứng intraday âm, dưới các giả định nhận dạng. Khác biệt chế độ có {int((regimes.qvalue_bh<.05).sum())}/256 kiểm định đạt BH với HAC, {int((regimes.qvalue_hc3_bh<.05).sum())}/256 với HC3. Dự báo daily: macro cải thiện 3/32 so sánh ở mẫu D3 gốc; ba mẫu matched đều 0/32. Mỗi scenario gộp có 0/40 mô hình vượt benchmark sau BH. RV thắng benchmark ở {rvwins}/120 so sánh, nhưng macro chỉ cải thiện {rvmacro}/32. Chưa xác nhận quan hệ nhân quả vô điều kiện hoặc khả năng dự báo tương lai.'
    latest=dict(generatedUtc=now.isoformat(),generatedLocal=local,summary=summary,live=status,ablation=records(ablation),benchmarks=records(bench),sensitivity=records(sensitivity),
        metrics=records(metrics),samples=records(samples),fomc=records(ranges),regimes=records(regimes),rvAblation=records(rvab),rvBenchmarks=records(rvbench),rvMetrics=records(rvmetrics),pit=records(features),revision=records(revision),pooled=records(counts))
    base['findings']=[summary,
        'Calendar LP, quantile và rolling giữ estimates đã khóa, có nhãn phương pháp/phiên/ngày riêng; không nội suy hoặc gộp các nguồn giá.',
        'VAR: 4/6 hệ bác bỏ whiteness20;60/60 ARCH tests đạtBH. CI IRF là đối chiếu có điều kiện, chưa đủ dùng làm kết luận causal vững.',
        'STMT calendar LP baseline có stress subgroup nhỏ và nhạy với event03/03/2020. Đọc FOMC component/regime sensitivity mới thay vì chỉ bảng baseline.',
        'PIT được audit theo metadata/vintage có sẵn; historical crypto/market receipts và revisions của nhãn chưa thể chứng nhận toàn bộ.',
        'Hạn nộp25/10 là mốc chốt bản báo cáo; OOS độc lập là một đánh giá riêng. Kết quả lịch sử exploratory được giữ, protocol hiện có tiếp tục sau hạn nộp.']
    base['findings']=[prose(x) for x in base['findings']]
    # Reuse frozen charts and estimates, replace obsolete forecast presentation.
    template=(ROOT/'dashboard/template.html').read_text(encoding='utf-8')
    sections=prose((ROOT/'dashboard/release_sections.html').read_text(encoding='utf-8'))
    overview=re.search(r'<section.*?</section>',sections,re.S).group(0)
    more=sections[len(overview):]
    template=template.replace('/ 19.10.2026','/ BẢN NỘP 25.10.2026')
    template=template.replace('LP theo ngày lịch · Monetary news sau FOMC · Quantile effects · VAR chung BTC–ETH.','Calendar LP · FOMC identification checks · Nested forecasting · Realized variance · PIT audit.')
    template=re.sub(r'<nav>.*?</nav><main>','<nav><a href="#overview">Tổng hợp</a><a href="#responses">Transmission</a><a href="#fomc">FOMC</a><a href="#forecast">Nested forecast</a><a href="#rv">RV</a><a href="#pit">PIT / hạn nộp</a><a href="../outputs/research/release_20261025/report.html">Báo cáo tổng hợp</a></nav><main>'+overview,template,count=1,flags=re.S)
    template=re.sub(r'<section class="panel" id="forecast">.*?(?=<section class="panel" id="rolling">)',more,template,count=1,flags=re.S)
    template=template.replace('Báo cáo hiện tại','Snapshot blueprint 19/10')
    template=template.replace('Macro daily đo liên hệ với cập nhật bộ thông tin đã khả dụng;', 'Calendar LP baseline 19/10 (khác FOMC components và forecasting bên dưới). Macro daily đo liên hệ với cập nhật bộ thông tin đã khả dụng;')
    template=template.replace('function renderForecast(){'+template.split('function renderForecast(){',1)[1].split('\nfunction renderImportance',1)[0], '')
    from src.historical_oos import load as load_historical_oos
    history=load_historical_oos()
    additions=(ROOT/'dashboard/historical_oos.js').read_text(encoding='utf-8')+'\n'+(ROOT/'dashboard/release_functions.js').read_text(encoding='utf-8')
    template=template.replace('for(let h=1;h<=30;h++)',additions+'\nfor(let h=1;h<=30;h++)',1)
    template=template.replace('const DATA=__PAYLOAD__;','const DATA=__PAYLOAD__;\nconst LATEST=__LATEST__;')
    template=template.replace('__PAYLOAD__',json.dumps(base,ensure_ascii=False,allow_nan=False).replace('</','<\/')).replace('__LATEST__',json.dumps(latest,ensure_ascii=False,allow_nan=False).replace('</','<\/'))
    history_json=json.dumps(history,ensure_ascii=False,allow_nan=False,separators=(',',':'))
    template=template.replace('const LATEST=', 'const HISTORICAL='+history_json.replace('</', '<'+'\\'+'/')+';\nconst LATEST=',1)
    from src.dashboard_workspace import workspace
    template=workspace(template)
    (ROOT/'dashboard/index.html').write_text(template,encoding='utf-8')
    save_json(OUT/'dashboard_payload.json',dict(base=base,latest=latest))
    requirement=pd.DataFrame([
        ['Data / pipeline','Đã có','USD mẫu dài; Binance USDT đối chiếu/RV riêng; broad USD, baseline không MOVE.'],
        ['VAR / recursive restrictions','Đã có, có hạn chế','BTC/ETH cùng hệ, IRF/order sensitivity; residual mean/variance diagnostics chưa đạt toàn bộ.'],
        ['LP / rolling / quantile / regimes','Đã có','Ngày lịch1–30, pre/post2020 và stress; CI pointwise, uncertainty và subgroup limits được công bố.'],
        ['ML risk forecast','Đã có','Elastic Net, histogram boosting; benchmarks và matched macro ablations; HAR/RV là nhánh riêng.'],
        ['Whole-feed PIT','Chưa chứng nhận đầy đủ','ALFRED date-level vintage; crypto/market và nhãn vẫn có giả định delivery/revision lịch sử.'],
        ['Untouched OOS cho thiết kế cuối','Chưa hoàn thành','Lịch sử đã tham gia phát triển; ledger prospective và endpoint riêng được theo dõi, không gắn tính hợp lệ với ngày nộp.'],
        ['Causal transmission vô điều kiện','Chưa xác lập','FOMC mạnh hơn daily association nhưng cần sign/exclusion assumptions; không thay identification bằng ML.'],
        ['Báo cáo / dashboard / repository','Đã hợp nhất','Bản tổng hợp này và dashboard chính dùng cùng nguồn; snapshots/ZIP cũ giữ nguyên.'],
    ],columns=['Yêu cầu','Trạng thái','Phạm vi'])
    feature_table=features[['feature','source','transformation','verification']]
    timing_table=pd.DataFrame([
        ['Daily USD','Coin Metrics PriceUSD','UTC day D đóng D+1; snapshot16/10, nhãn availability D+2 là giả định'],
        ['Nested / daily risk','Information I=D−3; marketD−4','D4 sensitivity dùng I=D−4; ghép cả train/inner/test trên cùng origins'],
        ['Calendar LP / quantile','Blueprint available-information','Thiết kế riêng với f information D−2, VIX observation D−3; outcomeD…D+h−1'],
        ['Monetary STMT daily','USMPD baseline','Outcome D+1…D+h; khác intraday policy/information component'],
        ['FOMC intraday','Coinbase USD, author shock files','Eastern có DST→UTC; crypto −10/+20 phút; quote sampling khác author median'],
        ['RV extension','Binance USDT5m/15m','Tổng squared intraday log returns; h1/7, không dùng squared tổng7-day return'],
    ],columns=['Thiết kế','Nguồn / convention','Timing / đơn vị'])
    dailyshort=daily[(daily.regime.isin(['full','pre2020','post2020']))&daily.shock.isin(['vix_change','usd_return_pct'])&daily.horizon_days.isin([1,7,30])][['asset','regime','shock','horizon_days','beta_pct','lower95','upper95','qvalue_bh','nobs']]
    current=BASE/'submission_20261025/decision.json'
    deadline=json.loads(current.read_text(encoding='utf-8'))
    text=f'''# Global Financial Conditions → Bitcoin và Ethereum

**Bản tổng hợp nộp ngày25/10/2026.** Dữ liệu lịch sử đến15/10/2026; sản phẩm cập nhật {local}. [Dashboard tương tác](../../../dashboard/index.html). Các estimates dưới đây được lấy từ những phiên bản đã khóa, không huấn luyện lại hoặc đổi specification trong bước hợp nhất này.

## 1. Câu hỏi nghiên cứu và kết luận

Nghiên cứu kiểm tra quy mô, độ trễ và sự thay đổi transmission của monetary, dollar và risk/volatility news sang BTC/ETH; so sánh pre/post2020 và stress/calm, đồng thời đánh giá incremental predictive content của macro so với own-history và benchmarks.

{summary}

RQ1: phản ứng intraday với policy component có dấu âm trong miền xoay admissible, nhưng diễn giải nhân quả cần giả định nhận dạng. RQ2: đã ước lượng đường horizon1–30 cho VIX/USD/yield; chưa có một thời gian truyền dẫn ổn định, vững để tuyên bố cho mọi chế độ. RQ3–4: có khác biệt theo mẫu/cách suy luận, chưa xác nhận sự tăng sensitivity sau2020 hoặc stress một cách vững. RQ5: chưa có bằng chứng vững rằng macro cải thiện dự báo vượt benchmark trên các thiết kế đã kiểm tra; chưa có xác nhận trên future untouched OOS.

## 2. Dữ liệu và định nghĩa

Giữ BTC/USD mẫu dài từ2014, ETH ngắn hơn; full historical sample, chia pre/post2020. Broad USD (DTWEXBGS) không phải ICE DXY; USD vintage chỉ từ2019, không splice trước đó. Baseline không MOVE theo phạm vi đã thống nhất. Không nối Binance USDT vào chuỗi USD.

{md(feature_table)}

Daily return `rD=log(PD/P(D−1))`; daily variance proxy `rD²`; trailing volatility `sqrt(365×mean(last30 r²))`. RV là tổng intraday squared log returns trên ngày UTC hoàn chỉnh. Δyield/ΔDFF có đơn vị bps, DFF change không phải monetary policy surprise. Gold là continuous GC=F, có roll effects. [Dictionary gốc](../../../data/processed/data_dictionary.csv), [source receipts và hashes](../../../data/source_log.json).

{md(timing_table)}

Các thiết kế có timing khác nhau và được giữ nhãn riêng. Không so trực tiếp daily STMT, intraday component, session IRF hoặc các loss ở khác nguồn/target như cùng một đại lượng.

## 3. Phương pháp và nhận dạng

VAR chung BTC/ETH với VIX, broad USD, yield; BIC và ordering sensitivity đã khóa. Recursive restrictions tạo một structural representation dưới giả định ordering, không tự chứng minh pure exogenous policy shock. LP hồi quy cumulative return lên information update/shock, controls/lags và interactions; h1–30 calendar days. Quantile τ=.05/.50/.95 và rolling252 sessions mô tả tail/time variation; pointwise CI không phải simultaneous bands.

FOMC dùng policy/information decomposition của tác giả, matched windows, source comparison, placebo/pre-announcement và generated-shock bootstrap. Không bác bỏ placebo không chứng minh exogeneity. Ước lượng shock/scaling có uncertainty; median-rotation intervals chưa bao phủ toàn identified set.

ML dùng Elastic Net và histogram gradient boosting; latter không phải XGBoost/LightGBM. Return dùng MSE; variance dùng QLIKE=`log(pred)+actual/pred`. Standardization, variance scale và smearing chỉ dùng training. Native/macro and USD comparisons ghép origins; nested outer refit theo năm2023/24/25/26, inner hai học kỳ năm trước, purge bằng label availability≤fold_start−24h. Các outcomes lịch sử đã được xem, nên nesting cải thiện quy trình đánh giá nhưng không biến test thành untouched.

## 4. Dynamic responses, pre/post2020 và VAR diagnostics

Daily LP full có0/240 hệ số đạt BH trong family720; stress contrasts0/240 trong family riêng. Các estimates chọn h1/7/30 bên dưới có đơn vị cumulative log return%, đọc cùng CI/n và không diễn giải riêng p-values thành causal effects.

{md(dailyshort)}

![Calendar LP và regimes](../blueprint_20261019/figures/calendar_LP.png)

{md(vard)}

4/6 VAR systems bác bỏ whiteness20; {int((arch.qvalue_bh_60<.05).sum())}/60 ARCH tests đạtBH. Mô hình mean/variance chưa adequate đầy đủ; không dùng IRF CI tiệm cận làm bằng chứng causal vững. LP/robust inference và sensitivity là các phân tích bổ sung, không tự sửa mọi misspecification của VAR.

![Quantile effects](../blueprint_20261019/figures/quantile_effects.png)

Quantile CI dùng99 block bootstrap draws, có5/1782 bootstrap fits không hội tụ đã loại và ghi log. Chưa có paired quantile-gap test; đường khác nhau chưa chứng minh khác slope. Rolling và full h1–30 được giữ trên dashboard cùng source/version labels.

## 5. FOMC và khác biệt chế độ

75 common scheduled events;72 đủ tất cả falsification windows;45 có đủ JK/BS sources. Không thay missing orthogonalized surprise bằng raw. Intraday policy point ranges trên toàn miền xoay:

{md(bounds)}

Đơn vị điểm phần trăm return/+10bps component PC1. Đây là infimum/supremum point estimates, **không phải confidence set**. Information component có thể unbounded theo chuẩn hóa này. 999 bootstrap draws lặp PCA/scaling/QR/outcome fit cho uncertainty tại median rotation; không phải toàn structural identified set.

{md(regime_summary)}

HAC20/256 so HC3 0/256: bằng chứng regime sensitivity chưa vững theo cách suy luận. Pre2020 có23 events; stress12 events. STMT post-event baseline stress9events từng cho nhiều hệ số có ý nghĩa, nhưng bỏ03/03/2020 làm BH contrasts giảm36/60→3/60; không dùng riêng baseline để khẳng định stress transmission. [Evidence đầy đủ](../evidence_20261019/report.html), [influence diagnostics](../robustness_20261019/report.html), [FOMC timing study](../fomc_identification_20261019/report.html).

![Rotation và sampling uncertainty](../evidence_20261019/figures/rotation_and_sampling.png)

## 6. Nested risk forecasting và sensitivity

640 artifacts, 320 outer groups, replay125.320 learned predictions và fit lại8 representatives;21/21 independent checks,6 guards. Các số dưới là kết quả gộp2023–2026; BH bao gồm pooled và annual scopes trong family đã khóa. Không gọi các so sánh liên quan nhau là các phát hiện độc lập.

{md(counts)}

Native có949 origins và matched728 mỗi tài sản. Khác significance giữa native và matched không tự là test khác effects; xem paired sensitivity. Thêm ngày buffer có1/40 tốt hơn và1/40 kém hơn sauBH ở kết quả gộp. Latest-vintage counterfactual có0/40 tốt hơn,2/40 kém hơn; revisions không mặc định làm kết quả đẹp hơn. Tuy vậy đây không phải lý do được bỏ PIT. [Toàn bộ nested/sensitivity](../pit_nested_20261020/report.html).

![Timing sensitivity trên cùng origins](../pit_nested_20261020/figures/timing_sensitivity.png)

## 7. Intraday realized variance extension

250 Binance archives có checksums/CRC;257 invalid candles mỗi asset được giữ raw và loại có audit, không sửa timestamp/nội suy. Chỉ dùng ngày hoàn chỉnh gồm midnight boundary. HAR/HAR-X h1/7 với5m/15m sampling,880 monthly artifacts; benchmarks trailing30/EWMA/GARCH cùng cutoff. Nhánh này khác daily USD squared return.

{rvwins}/120 HAR/HAR-X-vs-benchmark comparisons thắng sauBH; {rvmacro}/32 incremental macro comparisons cải thiện sauBH. Model confidence set membership không chứng minh macro skill. Kết quả này ủng hộ một số cấu trúc lịch sử RV trong sample hơn một số benchmark, chưa xác nhận macro hoặc future predictive ability. [Nguồn, sample và loss đầy đủ](../evidence_20261019/report.html).

![RV forecast comparisons](../evidence_20261019/figures/rv_forecasting.png)

## 7b. Kiểm thử OOS trên dữ liệu quá khứ theo khoảng ngày

Dashboard → **Dự báo rủi ro → Phát lại dự báo trên dữ liệu quá khứ** cho phép chọn khoảng ngày UTC trong 01/01/2023–13/10/2026, tài sản, target, model, scenario và cặp so sánh. Hiển thị thực tế/base/added/benchmark, loss cộng dồn, timing và model SHA-256 của từng origin; CSV giữ nguyên dự báo và các mốc thời gian. Chỉ các origins đã đủ điều kiện trong thiết kế gốc được dùng, không tạo forecast cho ngày thiếu.

Đã replay **{history['audit']['artifacts_replayed']} artifacts**, đối chiếu **{history['audit']['learned_predictions_checked']} learned predictions** và **{history['audit']['benchmark_predictions_checked']} benchmark predictions** với CSV đã khóa; kiểm tra chronology, label availability và train-only scaling. Không refit, không thay ước lượng hoặc ghi dự báo lịch sử vào ledger prospective. Chạy lại bằng `py -3.11 run_release.py validate-history`; dữ liệu hiển thị và bằng chứng checksum ở `dashboard/historical_oos_data.json` và `dashboard/historical_oos_audit.json`.

Đây là **historical pseudo-OOS** kiểm chứng quy trình tính toán, khác với tính độc lập của toàn bộ thiết kế cuối với outcomes đã xem. Scenario latest-vintage giữ nhãn **EX POST ORACLE**. Khoảng ngày người dùng chọn chỉ tính thống kê mô tả; các bảng CI/BH vẫn dùng kỳ/năm đánh giá đã khóa, không suy luận significance cho đoạn được chọn sau khi xem biểu đồ.

## 8. PIT, OOS độc lập và hạn nộp

15 feature definitions,28.026 macro-lineage rows,353/353 checks đối chiếu raw ALFRED spells và calendar transforms đạt. Không phát hiện vi phạm observation/vintage date trong phạm vi metadata được audit; không chứng nhận mọi feed có đầy đủ historical receipt/revision evidence. Targets/nhãn cũng là retrospective Coin Metrics snapshot; D+2 là giả định availability. D4 delay không sửa được unknown revisions hoặc biến kết quả thành causal identification.

**Ngày nộp và thời hạn đánh giá OOS là hai mốc khác nhau.** Ngày25/10/2026 quyết định nội dung có thể đưa vào bản nộp; không làm một backtest trở nên hợp lệ hoặc không hợp lệ. Mốc chốt nội bộ24/10 18:00 VN là lựa chọn lập kế hoạch. Theo timing hiện tại, origin23/10 chỉ có thể đủ nhãn sớm nhất25/10 07:00 VN; readiness upper bound là0 origin tại mốc nội bộ và tối đa1 origin trước hết ngày nộp, còn phụ thuộc actual receipts. Đây không phải forecasts đã được log hoặc số quan sát đủ để xác nhận skill. [Phân tích lịch trước hạn](../submission_20261025/report.html).

**Hướng xử lý đã áp dụng:** giữ historical as-of nested evaluation làm kết quả nghiên cứu lịch sử, báo toàn bộ benchmark/ablation và matched sensitivity; đánh giá độc lập tiếp tục ở nhánh prospective. [Gillet/Chicago Fed (2024)](https://www.chicagofed.org/publications/economic-perspectives/2024/7) cũng phân biệt backtest ALFRED lịch sử với true OOS; [Cawley–Talbot (2010)](https://www.jmlr.org/papers/v11/cawley10a.html) giải thích vai trò đánh giá cả bước chọn mô hình. Những phương pháp này hỗ trợ chất lượng historical evaluation, không hồi phục holdout đã tham gia phát triển thiết kế.

Reality Check/SPA xử lý một số dạng data snooping; SPA gốc có giới hạn với recursive expanding estimation nên chưa được thêm máy móc vào annual expanding backtest. Xem [White (2000)](https://users.ssc.wisc.edu/~behansen/718/White2000.pdf), [Hansen (2005)](https://doi.org/10.1198/073500105000000063) và [review áp dụng cho repo](../../../paper/untouched_oos_followup_20261020.md). Chưa xác lập được holdout lịch sử độc lập; **mục untouched OOS cho cấu hình cuối chưa hoàn thành**. Đánh giá mới cần forecasts trước outcomes hoặc một tập thực sự chưa tham gia phát triển.

Trạng thái lúc {local}: **{status['prediction_files']} forecast commits, {status['label_files']} labels**; evaluation status **{status['performance']}**. Lần vận hành gần nhất {status['last_run_local']}; capture có {oos_followup['prospective']['latest_capture']['sources_ok']}/{oos_followup['prospective']['latest_capture']['sources_total']} nguồn thành công. Protocol hiện có giữ nguyên đến {status['fixed_end']}; một năm là thời lượng đã chọn, không phải yêu cầu khoa học phổ quát. Đổi lịch chấm cần một protocol được thống nhất trước outcomes liên quan. {automation_note} [Giám sát tự động](../../automation_20261020/health.html), [kế hoạch và trạng thái OOS](oos_followup.html), [lịch chạy theo giờ Việt Nam](next_operations.csv), [provenance của cập nhật](oos_followup.json).

## 9. Đối chiếu yêu cầu và giới hạn kết luận

{md(requirement)}

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

[Blueprint yêu cầu đã đối chiếu](../../../paper/requirements.md), [review causality/prediction literature](../../../paper/causality_forecast_literature_review_20261019.md), [review PIT/OOS remedies](../../../paper/pit_oos_remedies_review_20261019.md), [nghiên cứu bổ sung về untouched OOS ngày20/10](../../../paper/untouched_oos_followup_20261020.md). Các bảng và hình là kết quả của repo, chưa phải replication của một paper khác.

Nguồn phương pháp gốc: [ALFRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [Cawley–Talbot: nested evaluation](https://www.jmlr.org/papers/v11/cawley10a.html), [Bauer–Swanson data](https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/). Author data, metadata và bibliography chi tiết được giữ trong các research snapshots liên kết ở trên. Nghiên cứu học thuật, không phải khuyến nghị đầu tư.
'''
    text=prose(text)
    (OUT/'report.md').write_text(text,encoding='utf-8')
    css='body{font:16px/1.65 system-ui;color:#193849;background:#edf3f6;margin:0}main{max-width:1180px;background:white;margin:24px auto;padding:32px;border-radius:12px}h1{font-size:32px;line-height:1.2}h2{font-size:23px;color:#096d90;margin-top:36px}a{color:#08678a}p{overflow-wrap:anywhere}.table-wrap{overflow:auto;margin:20px 0}table{border-collapse:collapse;min-width:650px;font-size:12px;width:100%}td,th{padding:8px;text-align:left;border-bottom:1px solid #dce6ed;vertical-align:top}th{background:#edf4f7}pre{overflow:auto;background:#edf4f7;padding:16px}img{max-width:100%;height:auto}figure{margin:24px 0}@media(max-width:760px){main{margin:0;padding:18px;border-radius:0}h1{font-size:27px}}'
    (OUT/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chủ đề9 — Bản tổng hợp nộp25/10</title><style>'+css+'</style><main>'+render_markdown(text)+'</main></html>',encoding='utf-8')
    oos_html=render_markdown((OUT/'oos_followup.md').read_text(encoding='utf-8'))
    # The frozen renderer does not support Markdown lists. Format only the new
    # operational document here, without modifying its historical source.
    oos_html=re.sub(r'<p>- (.*?)</p>',lambda match:'<ul>'+''.join('<li>'+item+'</li>' for item in match.group(1).split('\n- '))+'</ul>',oos_html,flags=re.S)
    (OUT/'oos_followup.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kế hoạch và trạng thái OOS</title><style>'+css+'</style><main>'+oos_html+'</main></html>',encoding='utf-8')
    (ROOT/'paper/README.md').write_text('# Báo cáo nộp 25/10/2026\n\n[Báo cáo tổng hợp](../outputs/research/release_20261025/report.html) · [Markdown](../outputs/research/release_20261025/report.md) · [Dashboard](../dashboard/index.html) · [Kế hoạch và trạng thái OOS](../outputs/research/release_20261025/oos_followup.md).\n\nBản này hợp nhất kết quả lịch sử đã khóa và đối chiếu phương pháp với [review untouched OOS](untouched_oos_followup_20261020.md). Ngày nộp là mốc viết báo cáo; nhánh đánh giá OOS độc lập có endpoint riêng và tiếp tục sau hạn nộp. Các assumptions PIT/identification và phạm vi suy luận nằm trong báo cáo; không sửa estimates. Snapshots cũ giữ nguyên; navigation cũ đã archive theo hash.\n',encoding='utf-8')
    catalog=pd.DataFrame([dict(path=n,sha256=h,role='Frozen empirical source; see method/version in report') for n,h in SOURCES.items()])
    catalog.to_csv(OUT/'source_catalog.csv',index=False,encoding='utf-8-sig')
    lock=OUT/'scientific_input_lock.json';locked=dict(files=SOURCES)
    if lock.exists():assert json.loads(lock.read_text(encoding='utf-8'))==locked,'Scientific inputs changed'
    else:save_json(lock,locked)
    save_json(OUT/'release_state.json',dict(generated_utc=now.isoformat(),generated_local=local,live=status,nested_summary=records(counts),
        rv_benchmark_wins=rvwins,rv_macro_wins=rvmacro,regime_summary=records(regime_summary),models_refit=0,estimates_changed=False,
        canonical_report='outputs/research/release_20261025/report.html',canonical_dashboard='dashboard/index.html'))
    print('Built canonical report/dashboard; source tables:',len(SOURCES),flush=True)

def package():
    from src.evaluation.validate_release import validate
    validate()
    paths=[p for p in OUT.rglob('*') if p.is_file()]
    paths += [ROOT/n for n in ['run_release.py','run_pit_nested.py','run_prospective.py','run_evidence.py','plan_submission.py','README.md','paper/README.md',
        'config/release_20261025.json','src/evaluation/release_preservation.py','src/evaluation/validate_release.py','src/release_product.py','src/oos_followup.py','paper/untouched_oos_followup_20261020.md',
        'dashboard/index.html','dashboard/release_sections.html','dashboard/release_functions.js','dashboard/workspace.css','dashboard/workspace.js','src/dashboard_workspace.py','tests/test_release_preservation.py','tests/validate_release_dashboard.cjs','tests/preview_release.cjs',
        'config/automation_20261020.json','src/automation_runtime.py','run_automation.py','tools/manage_topic09_automation.ps1','tools/notify_topic09.ps1','tests/test_automation.py','tests/validate_automation.py','tests/validate_installed_automation.py']]
    auto=ROOT/'outputs/automation_20261020'
    paths += [p for p in auto.iterdir() if p.is_file() and p.suffix in ['.json','.html','.xml']]
    files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
    manifest=dict(version='release_20261025_automation_v5',created_utc=pd.Timestamp.now(tz='UTC').isoformat(),files=files,prerequisites='Full frozen base repository and empirical supplements/dependencies; no raw/model duplication. Not standalone. Reinstall scheduled tasks explicitly on a different machine; no credentials are packaged.')
    m=ROOT/'manifest_release_20261025_automation_v5.json';save_json(m,manifest)
    dest=ROOT/'topic09_release_20261025_automation_v5_supplement.zip'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n in files:z.write(ROOT/n,n)
        z.write(m,m.name)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in files.items())
    save_json(ROOT/'package_release_20261025_automation_v5.json',dict(file=dest.name,sha256=sha(dest),bytes=dest.stat().st_size,verified_files=len(files),zip_crc_passed=True))
    print('Release supplement verified:',dest.name,len(files),'files',flush=True)
