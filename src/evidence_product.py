"""Scientific figures, offline evidence dashboard, report and reproducible supplement."""
from src.evaluation.evidence_common import *
from src.robustness_product import md,render_markdown
import html,zipfile

def read(name):return pd.read_csv(OUT/name,float_precision='round_trip')

def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
    if isinstance(v,(float,np.floating)):return '∞' if np.isposinf(v) else '−∞' if np.isneginf(v) else None if np.isnan(v) else float(v)
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.bool_,)):return bool(v)
    return v

def findings():
    a=read('rv_ablation_tests.csv');b=read('rv_benchmark_tests.csv');f=read('falsification_estimates.csv');c=read('falsification_contrasts.csv');i=read('regime_interaction_tests.csv');s=read('source_comparison.csv')
    return dict(macro_ablation_wins=int(((a.qvalue_bh<.05)&(a.mean_loss_added_minus_base<0)).sum()),macro_ablation_tests=len(a),har_benchmark_wins=int(((b.qvalue_bh<.05)&(b.mean_loss_added_minus_base<0)).sum()),har_benchmark_tests=len(b),
        falsification_pre_placebo_BH=int(((f.qvalue_bh<.05)&f.outcome.ne('announcement')).sum()),announcement_BH=int(((f.qvalue_bh<.05)&f.outcome.eq('announcement')).sum()),direct_policy_falsification_BH=int(((c.qvalue_bh<.05)&c.shock.eq('policy')).sum()),
        bs_announcement_BH=int(((s.qvalue_bh<.05)&s.shock.str.startswith('bs_')&s.outcome.eq('announcement')).sum()),interaction_BH=int((i.qvalue_bh<.05).sum()),interaction_HC3_BH=int((i.qvalue_hc3_bh<.05).sum()),interaction_tests=len(i),
        interaction_post2020_BH=int(((i.qvalue_bh<.05)&i.contrast.eq('post2020')).sum()),interaction_stress_BH=int(((i.qvalue_bh<.05)&i.contrast.eq('stress')).sum()),old_protected_files=check_protected())

def figures():
    f=read('falsification_estimates.csv');fig,axes=plt.subplots(1,2,figsize=(12,4.4),sharey=True)
    order=['pre_early','pre_late','announcement','placebo'];labels=['Pre −70/−40','Pre −40/−10','FOMC −10/+20','Previous week']
    for asset,ax in zip(['BTC','ETH'],axes):
        for offset,shock,color in [(-.1,'policy','#147a7f'),(.1,'information','#b9783f')]:
            g=f[f.asset.eq(asset)&f.shock.eq(shock)].set_index('outcome').reindex(order);x=np.arange(4)+offset;ax.errorbar(x,g.beta,yerr=1.95996398454*g.se_hac5,fmt='o',capsize=3,color=color,label=shock)
        ax.axhline(0,color='gray',ls='--',lw=.8);ax.set_xticks(range(4),labels,rotation=15);ax.set_title(asset+' · same72 events');ax.set_ylabel('Return percentage points /10bps component');ax.legend()
    fig.tight_layout();fig.savefig(OUT/'figures/falsification_windows.png');plt.close(fig)
    r=read('full_rotation_ranges.csv');g=read('generated_shock_intervals.csv');fig,axes=plt.subplots(1,2,figsize=(12,4.3))
    for asset,ax in zip(['BTC','ETH'],axes):
        for w,color in [(.1,'#e0a258'),(.5,'#147a7f'),(.9,'#7e74ae')]:
            z=g[g.asset.eq(asset)&g.shock.eq('policy')&g.outcome.eq('intraday')&g.weight.eq(w)].iloc[0];ax.errorbar(w,z.beta,yerr=[[z.beta-z.lower95_percentile],[z.upper95_percentile-z.beta]],fmt='o',color=color,capsize=4)
        bound=r[r.asset.eq(asset)&r.shock.eq('policy')&r.outcome.eq('intraday')].iloc[0];ax.axhspan(bound.lower_per10bps,bound.upper_per10bps,color='#b2cec3',alpha=.35,label='Full rotation point range (not CI)');ax.axhline(0,color='gray',ls='--',lw=.8);ax.set_xticks([.1,.5,.9]);ax.set_xlabel('Interior rotation weight');ax.set_ylabel('Return percentage points /10bps');ax.set_title(asset+' ·75 events,999 bootstrap draws');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(OUT/'figures/rotation_and_sampling.png');plt.close(fig)
    p=read('rv_test_predictions.csv');fig,axes=plt.subplots(1,2,figsize=(12,4.3))
    for asset,ax in zip(['BTC','ETH'],axes):
        sub=p[p.asset.eq(asset)&p.sampling_minutes.eq(5)&p.horizon_days.eq(1)&p.variant.eq('long_own')].copy();wide=sub.pivot(index='origin_utc',columns='model',values='predicted').sort_index();actual=sub.groupby('origin_utc').actual.first().reindex(wide.index);baseline=np.log(wide.trailing30)+actual/wide.trailing30
        for name,color in [('har','#147a7f'),('garch11','#b9783f'),('ewma','#7e74ae')]:
            diff=(np.log(wide[name])+actual/wide[name]-baseline).cumsum();ax.plot(pd.to_datetime(wide.index),diff,label=name,color=color)
        ax.axhline(0,color='gray',ls='--',lw=.8);ax.set_title(asset+' · RV5m, horizon1, long own');ax.set_ylabel('Cumulative QLIKE minus trailing30');ax.tick_params(axis='x',rotation=20);ax.legend()
    fig.tight_layout();fig.savefig(OUT/'figures/rv_forecasting.png');plt.close(fig)

def build():
    init();stats=findings();save_json(OUT/'findings.json',stats)
    import sys,platform,scipy,statsmodels,sklearn
    save_json(OUT/'environment.json',dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,statsmodels=statsmodels.__version__,sklearn=sklearn.__version__,recorded_utc=pd.Timestamp.now(tz='UTC').isoformat(),scope='Versions used by this local evidence extension; dependencies are external to supplement'))
    figures()
    audit=json.loads((OUT/'causal_audit_summary.json').read_text());coverage=json.loads((OUT/'bootstrap_coverage_summary.json').read_text());validation=json.loads((OUT/'independent_validation.json').read_text());live=json.loads((OUT/'prospective/prospective_status.json').read_text());capture=json.loads((OUT/'prospective/latest_capture.json').read_text());live_day=pd.Timestamp(live['origin_utc']).strftime('%d/%m/%Y');live_reason='do snapshot không đạt timing/receipt requirements; giữ missing attempts, không backdate' if live['total_predictions']==0 else 'được ghi trước origin với receipts đủ buffer, không đánh giá sớm'
    f=read('falsification_estimates.csv');r=read('full_rotation_ranges.csv');bi=read('generated_shock_intervals.csv');sources=read('source_comparison.csv');inter=read('regime_interaction_tests.csv');bench=read('rv_benchmark_tests.csv')
    limits=r[r.outcome.eq('intraday')][['asset','shock','lower_per10bps','upper_per10bps','lower_per1calibration_rms','upper_per1calibration_rms']].copy()
    limits=limits.map(lambda v:'∞' if isinstance(v,(float,np.floating)) and np.isposinf(v) else '−∞' if isinstance(v,(float,np.floating)) and np.isneginf(v) else v)
    bench_summary=bench.groupby('benchmark').apply(lambda x:pd.Series({'comparisons':len(x),'BH_wins_HAR':int(((x.qvalue_bh<.05)&(x.mean_loss_added_minus_base<0)).sum()),'BH_losses_HAR':int(((x.qvalue_bh<.05)&(x.mean_loss_added_minus_base>0)).sum())})).reset_index()
    interaction_summary=inter.groupby('contrast').agg(tests=('qvalue_bh','size'),BH_HAC=('qvalue_bh',lambda x:int((x<.05).sum())),BH_HC3=('qvalue_hc3_bh',lambda x:int((x<.05).sum())),n0=('n_group0','min'),n1=('n_group1','min')).reset_index()
    text=f'''**Chủ đề 9 — Kiểm tra nhận dạng nhân quả và dự báo realized variance**

Phiên bản riêng ngày19/10/2026, triển khai sau rà soát nghiên cứu và sự đồng ý của người dùng. Đã bảo toàn {stats['old_protected_files']} tệp dữ liệu, mô hình, kết quả và archive cũ. Không thêm MOVE, không đổi Broad USD thành DXY, không nối USDT vào baseline USD. [Dashboard tương tác](dashboard.html).

**Kết quả chính và cách diễn giải**

Policy coefficient trong cửa sổ phút vẫn âm trên toàn miền xoay tại calibration đã ước lượng cho BTC/ETH. Kiểm tra trước thông báo và tuần trước có {stats['falsification_pre_placebo_BH']} hệ số đạt BH; các chênh lệch policy thông báo-trước/tuần trước có {stats['direct_policy_falsification_BH']}/6 đạt BH. Đây là kiểm tra chống một số giải thích thay thế, chưa chứng minh exclusion hay nhận dạng nhân quả vô điều kiện. Regime interactions có20/256 đạtBH vớiHAC nhưng0/256 vớiHC3: kết luận khác biệt chế độ chưa vững theo lựa chọn suy luận.

HAR/HAR-X có {stats['har_benchmark_wins']}/{stats['har_benchmark_tests']} so sánh thuận lợi với benchmark đạt BH, nhưng macro ablation có **{stats['macro_ablation_wins']}/{stats['macro_ablation_tests']} cải thiện đạt BH**. Các so sánh có tương quan với nhau, không phải51 phát hiện độc lập. Kết quả mới gợi ý cấu trúc bộ nhớ của RV hữu ích hơn một số benchmark ở mẫu này; chưa xác nhận giá trị gia tăng của macro hay khả năng dự báo tương lai. Target, nguồn giá và mô hình khác latency nên không so trực tiếp hai bảng loss để quy toàn bộ thay đổi cho RV.

**Sự kiện và đối chiếu nguồn**

Giữ75 sự kiện chung của FOMC study làm khung. Yêu cầu đủ bốn cửa sổ cho cả BTC/ETH còn72; ba sự kiện2016-09-21,2017-03-15,2019-10-30 mất do ETH thiếu cửa sổ bổ sung, không do hệ số/p-value. Trên giao nhau có đủ JK và hai BS series còn45 sự kiện. Không so nguồn trên các mẫu khác nhau rồi kết luận shock nào đúng hơn.

Workbook [Bauer–Swanson tại SF Fed](https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/) thực tế kết thúc13/12/2023. MPS_ORTH thiếu March–December2020 theo quy tắc của tác giả; giữ thiếu, không thế bằng MPS. Workbook có rate units theo percentage points, MPS chuẩn hóa unit ED4 impact; regression nhân biến shock10 tương ứng hệ số per+10bps. Chart CSV của SF Fed dùng bps, không trộn quy ước đó với workbook. BS và JK là những nhân tố có định nghĩa/chuẩn hóa khác nhau; thêm cột per+1 sampleSD để đối chiếu, không gọi chúng là cùng một shock.

{md(sources[sources.outcome.eq('announcement')][['asset','shock','beta','beta_pct_per1sd','qvalue_bh','qvalue_hc3_bh','nobs']])}

Cả BS raw và orthogonalized có dấu âm quanh công bố nhưng {stats['bs_announcement_BH']} hệ số BS announcement đạt BH32. Vì vậy kiểm tra chéo nguồn chưa xác nhận kết luận mạnh về significance. Không lấy việc JK có p nhỏ hơn làm bằng chứng JK nhận dạng đúng hơn.

**Falsification và direct contrasts**

Cửa sổ trước sớm[-70,-40], trước muộn[-40,-10], thông báo[-10,+20] phút; placebo đúng7 ngày trước, cùng local Eastern clock rồi chuyển UTC bằng America/New_York. Yêu cầu đủ31 endpoint-inclusive candles cho từng cửa sổ; so overlap mới/cũ không có close thay đổi. Loại ngày placebo có Statements/Press Conferences/Minutes/Monetary Events trong frozen USMPD. Chưa loại hết tin vĩ mô/crypto khác, nên không gọi đây là randomized experiment.

{md(f[['asset','outcome','shock','beta','qvalue_bh','qvalue_hc3_bh','nobs']])}

![Falsification windows and conditional95percent intervals](figures/falsification_windows.png)

HAC5 và HC3 là suy luận có điều kiện trên shock cố định; BH16 cho hệ số cửa sổ, BH32 cho nguồn và BH12 cho direct contrasts. Direct contrasts hồi quy chênh lệch outcome trên cùng X, giữ covariance. Không suy từ một p-value có ý nghĩa và p-value khác không có ý nghĩa sang khác hệ số. Không bác bỏ pre-event/placebo không chứng minh exogeneity.

**Toàn miền xoay và generated-shock uncertainty**

Thay ba điểm xoay bằng giới hạn giải tích trên toàn khoảng góc hợp lệ của normalized QR. Với a=R12/R11,b=R22/R11: stock impact policy=a−b tan(theta), information=a+b cot(theta); outcome coefficient là(rate slope+stock slope×stock impact)/10. Endpoint limits có thể vô hạn khi component variance tiến về0. Dải sau là infimum/supremum của point estimates, không phải confidence set.

{md(limits)}

Đặc biệt policy BTC có miền khoảng[−1,956;−0,711], ETH[−2,523;−0,795] điểm phần trăm/+10bps. Information BTC có thể đổi dấu và unbounded phía trên; ETH information cũng unbounded theo chuẩn hóa này. +1 calibration RMS cho một cách chuẩn hóa hữu hạn khác, không phải SD trong75 sự kiện crypto và không phải giả định nhận dạng mới.

999 circular block bootstrap draws, block8 author events: resample toàn334 author rows, fit lại PCA năm rate derivatives, scaling theo ED4, QR covariance và outcome regressions theo matched event multiplicities. Không chỉ bootstrap phần dư hồi quy cuối. Khoảng dưới là percentile95% tại **median rotation**, pointwise, chưa điều chỉnh multiplicity và không bao phủ toàn structural identified set.

{md(bi[bi.outcome.eq('intraday')&bi.weight.eq(.5)][['asset','shock','beta','lower95_percentile','upper95_percentile','successful_draws']])}

![Rotation range versus sampling uncertainty](figures/rotation_and_sampling.png)

Mô phỏng kiểm tra riêng100 mẫu trong Gaussian two-variable calibration cho empirical coverage policy={coverage['policy_coverage']:.0%}, information={coverage['information_coverage']:.0%} ở nominal95%, Monte Carlo SE tối đa0,05. Nó không xác nhận coverage của full five-derivative pipeline, fat tails, nonstationarity hay identified set. Không gọi percentile intervals này là robust credible regions của Giacomini–Kitagawa. Sai khác slope tối đa1,75e−6 so nghiên cứu cũ được giải thích và kiểm tra bằng công bố shock làm tròn8 chữ số; bản cũ không đổi.

Phân rã MP/CBI/FRN theo nghiên cứu2026 chưa triển khai vì chưa xác minh được author shock file trực tiếp. Không invent FRN hay ép mô hình ba thành phần trên mẫu con yếu. Daily VIX/USD models vẫn là quan hệ có điều kiện nếu chưa có nhận dạng ngoại sinh riêng. LP hoặc heteroskedasticity-robust SE không tự tạo identification.

**Khác biệt pre/post và stress**

Pooled regression gồm cả hai shocks, regime indicator, cả hai shock×regime interactions và prior controls. Giữ75 sự kiện, stress định trước bằng VIX khả dụng trước sự kiện≥25. Direct differences được xét chung BH256:

{md(interaction_summary)}

**Không có hệ số regime interaction nào đạtBH vớiHC3**, dù20/256 đạtBH vớiHAC. Trước2020 chỉ23events, stress12events. Chưa có full-stage bootstrap cho interaction specification. Vì vậy không kết luận chế độ làm tác động mạnh hơn một cách vững, không gọi đây là thay đổi cơ chế nhân quả đã xác nhận. Không thay các kết quả subgroup cũ bằng bảng này.

**Realized variance: dữ liệu và timing**

Tải250 archive Binance spot5m BTCUSDT/ETHUSDT từ2017-08 đến2026-09 và daily October đến15/10/2026; tổng ZIP raw khoảng98MB. Xác minh publisher CHECKSUM và ZIP CRC. Nguồn chuyển ms→microseconds từ2025 được parse riêng. Có257 nến/asset lệch opening grid hoặc non-nominal close time; lưu nguyên raw và danh sách loại, không làm tròn timestamp. Một số ngày khác thiếu grid; chỉ dùng ngày đủ288 r5 và96 r15 gồm midnight boundary. RV15 lấy từ cùng lưới5m, không suy RV từ cửa sổ phút FOMC. Mẫu forecast đầu09/10/2017, ngắn hơn lịch sử baseline2014–2026.

Target là tổng variance D…D+h−1 với h=1/7, đơn vị decimal log return squared, khác bình phương tổng return7 ngày. HAR regressors RV tại D−3 và trung bình7/30 ngày kết thúc D−3; macro/vintage dùng frozen information row D−3, market proxies quan sát D−4. Không carry market returns trên ngày nghỉ; no crypto bridge/fill. Cấu hình long own/macro cùng origins; ba common variants cùng origins và USD vintage từ2019.

Tại refit đầu tháng, chỉ dùng label available≤origin−24h; label availability=D+h+1. Validation2023–2024 cũng purge các nhãn chưa khả dụng trước first test minus24h. Chọn cửa sổ730/1460/expanding bằng validation QLIKE, không dùng test. Log HAR/HAR-X OLS có training-only scaling và residual smearing; lưu880 monthly test artifacts. Không refit40 latency models cũ, không thêm learner phi tuyến trong nhánh này.

**Benchmark và đánh giá**

Trailing30, EWMA0,94 và zero-mean Gaussian-QMLE GARCH(1,1) cùng source/cutoff. GARCH expanding parameters refit monthly, filter đến D−3; tổng forecast steps3…h+2 mới trùng target khi có buffer.92 parameter fits gồm validation/test. Missing daily return là trạng thái unobserved, GARCH cập nhật conditional expectation; không điền giá hay coi đó là observed zero return. Mọi variance prediction dương, không prediction floor.

QLIKE chính=log(pred)+actual/pred; MSE phụ. Paired losses trên cùng origins, calendar block30 ngày,999 draws, giữ missing-origin mask. Two-sided centered bootstrap p và percentile intervals là xấp xỉ dưới điều kiện dependence/stability, không uniform inference qua mọi regime. BH32 ablations và BH120 learned-vs-benchmark riêng; MCS90% cho8 series trên cùng origins của mỗi asset/sampling/horizon. Không áp Clark–West cho QLIKE.

{md(bench_summary)}

![Historical cumulative QLIKE benchmark comparisons](figures/rv_forecasting.png)

0/32 macro ablations đạt BH. GARCH không được giữ trong8 MCS; các HAR-X macro series đều được giữ, nhưng nhiều own-only forecasts cũng được giữ. MCS membership không chứng minh incremental macro skill. Thắng một benchmark khác với xác nhận giá trị của thông tin toàn cầu. Test2025+ đã xem, mọi kết quả là historical/exploratory. Không bảo đảm kết quả sẽ lặp lại trên giá USD, sampling khác hoặc nguồn real-time.

**Prospective và mức hoàn thành**

Đã capture {capture['sources_ok']}/{capture['sources_total']} responses thật, giữ request, raw bytes, URL, receipt UTC và SHA256. Namespace vận hành riêng dùng protocol nguyên hash và40 latency models nguyên hash. Origin {live_day} ghi {live['total_predictions']} predictions {live_reason}. Evaluation vẫn theo fixed window/label timing; chưa có future score trong lần nghiên cứu này. Không deploy RV models, không tự cài scheduler.

Chạy hàng ngày khi vận hành: `py -3.11 run_evidence.py prospective`. Đây là thao tác thực tại thời điểm chạy, không cách tái tạo receipt trong quá khứ. Chưa có whole-feed historical PIT: market/crypto retrospective snapshots, macro date-level vintages và conservative buffer chỉ giảm một số rủi ro timing.

{validation['passed']}/{validation['passed']} kiểm tra độc lập và7 edge guards đạt, gồm all-day RV rebuild, toàn bộ HAR/GARCH forecast replay, bootstrap/MCS replay, pooled contrasts và first-stage bootstrap checks. Các kiểm tra tính toán không xác nhận causal assumptions hay future skill.

Trên artifact checkout đã freeze: `py -3.11 run_evidence.py validate`, rồi `product`; dashboard QA bằng Node. `rv_prepare/rv_fit/all` chỉ cho phiên bản fresh chưa freeze, không ghi đè model đang lưu. Muốn thay thiết kế phải dùng version riêng và thông báo trước.

[Validation](independent_validation.json) · [thiết kế khóa](../../../config/evidence_20261019.json) · [nguồn](rv_source_manifest.json) · [audit timestamps](archive_parsing_audit.csv) · [nến loại](invalid_source_candles.csv) · [event exclusions](falsification_audit.csv) · [source comparisons](source_comparison.csv) · [direct contrasts](falsification_contrasts.csv) · [rotation bounds](full_rotation_ranges.csv) · [bootstrap draws](joint_generated_shock_bootstrap.npz) · [interaction tests](regime_interaction_tests.csv) · [sample summary](rv_sample_summary.csv) · [monthly windows](rv_selected_windows.csv) · [test predictions](rv_test_predictions.csv) · [macro ablations](rv_ablation_tests.csv) · [benchmark tests](rv_benchmark_tests.csv) · [MCS](rv_model_confidence_sets.csv) · [prospective](prospective/namespace_audit.json) · [literature review](../../../paper/causality_forecast_literature_review_20261019.md).
'''
    (OUT/'report.md').write_text(text,encoding='utf-8')
    css='body{font:16px/1.75 system-ui,Segoe UI,sans-serif;max-width:1120px;margin:30px auto;padding:0 22px;color:#193b45;background:#fbfdfc}p{margin:18px 0}strong{color:#0c6f78}figure{margin:25px 0}img{max-width:100%;height:auto}.table-wrap{overflow-x:auto;max-width:100%}table{border-collapse:collapse;font-size:13px}th,td{padding:8px 12px;border-bottom:1px solid #d5e2e3;text-align:left;white-space:nowrap}th{background:#e8f2ef}a{color:#146d84}code{background:#eaf2f1;padding:3px 5px;overflow-wrap:anywhere}'
    (OUT/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Topic09 evidence extension</title><style>'+css+'</style><body><p><a href="dashboard.html">Mở dashboard</a></p>'+render_markdown(text)+'</body></html>',encoding='utf-8')
    payload={key:read(file).to_dict('records') for key,file in [('falsification','falsification_estimates.csv'),('sources','source_comparison.csv'),('contrasts','falsification_contrasts.csv'),('ranges','full_rotation_ranges.csv'),('intervals','generated_shock_intervals.csv'),('interactions','regime_interaction_tests.csv'),('metrics','rv_forecast_metrics.csv'),('samples','rv_sample_summary.csv'),('windows','rv_selected_windows.csv'),('ablations','rv_ablation_tests.csv'),('benchmarks','rv_benchmark_tests.csv'),('mcs','rv_model_confidence_sets.csv')]}
    packed={};p=read('rv_test_predictions.csv')
    for key,g in p.groupby(['asset','sampling_minutes','horizon_days','variant']):
        g=g.copy();g['series']=g.model.replace({'har':'learned','har_x':'learned'});w=g.pivot(index='origin_utc',columns='series',values='predicted').sort_index();y=g.groupby('origin_utc').actual.first().reindex(w.index)
        packed['|'.join(map(str,key))]=[[str(date)[:10],float(actual),float(row.learned),float(row.trailing30),float(row.ewma),float(row.garch11)] for (date,row),actual in zip(w.iterrows(),y)]
    payload['forecasts']=packed;payload['liveText']=f"Capture {capture['sources_ok']}/{capture['sources_total']} responses thật. Origin {live_day}: {live['total_predictions']} predictions {live_reason}. Protocol đến20/10/2027, labels cuối cần thêm24h."
    options='<option value="intraday">Cửa sổ phút</option><option value="event_day">Ngày UTC công bố</option>'+''.join(f'<option value="post_{h}">Post {h} ngày</option>' for h in range(1,31))
    template=(ROOT/'dashboard/evidence_template.html').read_text(encoding='utf-8');page=template.replace('__OUTCOME_OPTIONS__',options).replace('__DATA__',json.dumps(clean(payload),ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('</','<\\/'))
    (OUT/'dashboard.html').write_text(page,encoding='utf-8')
    (ROOT/'paper/evidence_20261019.md').write_text('**Evidence extension —19/10/2026**\n\n[Báo cáo](../outputs/research/evidence_20261019/report.html) · [Dashboard](../outputs/research/evidence_20261019/dashboard.html) · [Thiết kế](../config/evidence_20261019.json).\n\nTriển khai đề xuất đã được đồng ý; nguồn/FOMC falsification, toàn miền xoay, generated-shock sampling bootstrap, direct interactions, RV/HAR-X/GARCH và vận hành frozen prospective tách biệt. Không xác nhận nhân quả vô điều kiện hoặc future skill. Macro ablations0/32 đạtBH; HAR benchmark comparisons51/120 thuận lợi đạtBH. Giữ1202 tệp nền nguyênhash.\n',encoding='utf-8')
    print('Evidence report, scientific figures and40 RV dashboard views built.',flush=True)

def package():
    init();check_protected();target=ROOT/f'topic09_{VERSION}_supplement.zip';assert not target.exists(),'Never overwrite final archive'
    files=[]
    for folder in [OUT,RAW,PANELS,MODELS,LIVE]:files.extend(p for p in folder.rglob('*') if p.is_file())
    for folder in ['src','tests']:
        files.extend(p for p in (ROOT/folder).rglob('*evidence*') if p.is_file() and '__pycache__' not in p.parts)
    files.extend(ROOT/p for p in ['run_evidence.py','config/evidence_20261019.json','dashboard/evidence_template.html','paper/evidence_20261019.md','paper/causality_forecast_literature_review_20261019.md','README.md','requirements-project.txt','requirements-research.txt','requirements.txt'])
    deps=['research_common.py','research_completion.py','research_fomc_comparison.py','src/utils/project.py','src/evaluation/latency_common.py','src/models/latency.py','src/data/latency_snapshots.py','src/data/prospective_snapshots.py','src/evaluation/latency_live.py','src/evaluation/robustness_common.py','src/robustness_product.py','preview_completion.cjs']
    files=sorted(set(files));manifest=dict(version=VERSION,type='Supplement; existing full base repository and Python/Node dependencies required, not standalone',files={p.relative_to(ROOT).as_posix():sha(p) for p in files},external_frozen_prerequisites=init()['protected_sha256'],base_code_dependencies={n:sha(ROOT/n) for n in deps})
    mp=ROOT/f'manifest_{VERSION}.json';save_json(mp,manifest)
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[mp]:z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        import hashlib
        assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest['files'].items())
    result=dict(file=target.name,bytes=target.stat().st_size,files=len(files)+1,sha256=sha(target),all_crc_sha256_verified=True,type=manifest['type'])
    save_json(ROOT/f'package_{VERSION}.json',result);print(json.dumps(result,indent=2),flush=True)
