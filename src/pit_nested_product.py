"""Render empirical audit, matched sensitivities and nested evaluation."""
from src.evaluation.pit_nested_common import *
from src.robustness_product import md, render_markdown
from research_common import plt
import html

def build():
    init();check_protected()
    audit=json.loads((OUT/'audit_summary.json').read_text(encoding='utf-8'))
    validation=json.loads((OUT/'independent_validation.json').read_text(encoding='utf-8'))
    evidence=pd.read_csv(OUT/'feature_evidence.csv');revision=pd.read_csv(OUT/'revision_magnitude.csv')
    sample=pd.read_csv(OUT/'sample_summary.csv');metrics=pd.read_csv(OUT/'forecast_metrics.csv')
    abl=pd.read_csv(OUT/'ablation_tests.csv');bench=pd.read_csv(OUT/'benchmark_tests.csv');sens=pd.read_csv(OUT/'sensitivity_tests.csv')
    timing=pd.read_csv(OUT/'fold_timing.csv');warnings=json.loads((OUT/'fit_warnings.json').read_text(encoding='utf-8'))
    pooled=abl[abl.scope.astype(str)=='pooled'].copy();bp=bench[bench.scope.astype(str)=='pooled'].copy();sp=sens[sens.scope.astype(str)=='pooled'].copy()
    count=[]
    for scenario,q in pooled.groupby('scenario',sort=False):
        b=bp[bp.scenario==scenario]
        count.append(dict(scenario=scenario,macro_comparisons=len(q),macro_better_BH=int(((q.mean_loss_new_minus_base<0)&(q.qvalue_bh<.05)).sum()),macro_worse_BH=int(((q.mean_loss_new_minus_base>0)&(q.qvalue_bh<.05)).sum()),
            learned_vs_benchmark=len(b),learned_better_BH=int(((b.mean_loss_new_minus_base<0)&(b.qvalue_bh<.05)).sum()),learned_worse_BH=int(((b.mean_loss_new_minus_base>0)&(b.qvalue_bh<.05)).sum())))
    counts=pd.DataFrame(count);csv(counts,'pooled_summary.csv')
    full_benchmark_wins=int(((bench.mean_loss_new_minus_base<0)&(bench.qvalue_bh<.05)).sum())
    sc=[]
    for label,q in sp.groupby('comparison',sort=False):
        sc.append(dict(comparison=label,n_comparisons=len(q),changed_better_BH=int(((q.mean_loss_new_minus_base<0)&(q.qvalue_bh<.05)).sum()),changed_worse_BH=int(((q.mean_loss_new_minus_base>0)&(q.qvalue_bh<.05)).sum()),
            changed_raw_p_lt05=int((q.pvalue<.05).sum())))
    sensitivity_summary=pd.DataFrame(sc);csv(sensitivity_summary,'sensitivity_summary.csv')
    # Scientific figures: paired loss units must never mix MSE and QLIKE axes.
    fig,axes=plt.subplots(1,2,figsize=(12,5.4))
    from matplotlib.ticker import MaxNLocator
    for ax,target in zip(axes,['return','squared_return']):
        q=sp[(sp.target==target)&(sp.comparison=='extra_calendar_day')].reset_index(drop=True)
        labels=q.asset.str.upper()+' / '+q.model.str.replace('gradient_boosting','GB').str.replace('elastic_net','EN')+' / '+q.variant
        for i,r in q.iterrows():
            ax.plot([r.ci_low,r.ci_high],[i,i],color='#216b8e',alpha=.75);ax.plot(r.mean_loss_new_minus_base,i,'o',color='#216b8e',ms=4)
        ax.axvline(0,color='#444',lw=1);ax.set_yticks(range(len(q)),labels,fontsize=7)
        ax.set_xlabel('MSE D4 - D3' if target=='return' else 'QLIKE D4 - D3');ax.set_title('Return' if target=='return' else 'Squared return');ax.invert_yaxis()
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
        if target=='return':ax.ticklabel_format(axis='x',style='sci',scilimits=(-3,3),useOffset=False)
    fig.suptitle('Extra calendar-day delay on matched origins (95% descriptive CI)')
    fig.tight_layout();fig.savefig(OUT/'figures/timing_sensitivity.png',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,asset in zip(axes,['btc','eth']):
        q=sample[(sample.asset==asset)&(sample.variant=='common_usd')]
        ax.barh(q.scenario,q.outer_n,color=['#126b92','#478f9b','#dbab58','#777eae']);ax.set_title(asset.upper()+' common USD');ax.set_xlabel('Outer origins 2023-2026 YTD')
    fig.tight_layout();fig.savefig(OUT/'figures/sample_coverage.png',bbox_inches='tight');plt.close(fig)
    features_short=evidence[['feature','source','verification','remaining_assumption']]
    sample_short=sample[sample.variant.isin(['long_macro','common_usd'])][['asset','variant','scenario','n','outer_n','first_origin','last_origin']]
    timing_summary=timing[timing.stage=='outer'].groupby(['outer_year','scenario']).agg(n_groups=('asset','size'),min_train=('n_fit','min'),min_test=('n_evaluate','min'),max_test=('n_evaluate','max')).reset_index()
    native=sample[sample.variant=='long_macro'].set_index(['asset','scenario'])
    retention=[]
    for asset in ['btc','eth']:
        a=int(native.loc[(asset,'native_asof_d3'),'outer_n']);b=int(native.loc[(asset,'matched_asof_d3'),'outer_n'])
        retention.append(f'{asset.upper()}: {a} → {b} outer origins ({100*b/a:.1f}% còn lại)')
    draft={
        'status':'DRAFT_NOT_ACTIVATED_AWAITING_SUBMISSION_DEADLINE',
        'created_utc':pd.Timestamp.now(tz='UTC').isoformat(),
        'existing_protocol':'data/prospective/latency_20261019/protocol.json; unchanged, no early score',
        'candidate_models':'Existing frozen 40 latency artifacts, not the 640 historical nested artifacts; confirm final choice in prospective protocol before outcomes',
        'primary_comparisons':'BTC/ETH squared return: own vs macro long without USD, macro without vs with USD common; Elastic Net and GB = 8 declared tests',
        'primary_metric':'QLIKE; paired dates, BH8 at fixed final endpoint; CI and sample counts. No guarantee of sufficient power.',
        'secondary':'Return MSE, benchmarks, annual historical nested folds; separate exploratory reporting',
        'start_rule':'After final protocol freeze; each snapshot received <= origin-24h. No backfilling missed forecasts. Start >= actual freeze +24h and all source/eligibility rules.',
        'end_rule':'Fixed date from submission deadline minus time for labels, validation and writing; calendar endpoint not performance trigger',
        'label_rule':'Target closes D+1; assumed usable D+2. End scoring only after last label available.',
        'independence':'No performance peeking/tuning during window; updates are execution/coverage only. Model changes terminate and register a new later experiment.',
        'short_window':'If deadline gives insufficient origins, report prospective process and descriptive errors; do not claim confirmed skill or create fake untouched historical test.',
        'decision_needed':'Submission date DD/MM/YYYY; approved window/model/protocol must be locked before affected outcomes.'}
    save_json(OUT/'oos_protocol_draft.json',draft)
    proposal='''# Phương án OOS độc lập — chưa kích hoạt

Hạn nộp chưa được cung cấp. Protocol một năm đang khóa được giữ nguyên; không chấm sớm các forecasts của protocol đó bằng một namespace khác.

Sau khi biết hạn nộp, chốt ngày kết thúc trước hạn ít nhất 5 ngày lịch để nhận nhãn cuối, kiểm chứng và viết bài; nếu lịch nghỉ/nguồn chậm cần dư thêm. Chọn ngày bắt đầu sau lúc khóa protocol và bảo đảm snapshot đã nhận trước origin ít nhất 24h. Mốc cụ thể phải ghi trước outcomes, không tính từ ngày lịch sử đã có kết quả.

Nếu có khoảng 8–12 tuần: có thể đăng ký pilot prospective cố định, vẫn phải báo số origins thực tế và độ bất định. Khoảng 2–4 tuần: chủ yếu kiểm chứng vận hành và kết quả mô tả; số ít quan sát không đủ tự bảo đảm power. Nếu hạn quá gần: dùng nested backtest như bằng chứng lịch sử exploratory, ghi rõ chưa có kiểm định tương lai độc lập. Các độ dài này là lựa chọn thực tế, không phải ngưỡng học thuật bảo đảm xác nhận skill.

Đề xuất reviewable: giữ 40 latency artifacts đã đóng băng, không triển khai 640 artifacts của nested lịch sử. So sánh chính QLIKE squared return: BTC/ETH × Elastic Net/GB × (thêm macro mẫu dài không USD; thêm USD trên common sample) = 8 tests, BH8 ở endpoint cố định. Return MSE và benchmarks là phân tích phụ. Ngày/nhãn ghép giữa mô hình, không chọn ngày có lợi. Không thay mô hình theo kết quả đang tích lũy.

Việc thống nhất kỳ mới cần hạn nộp và một protocol/amendment minh bạch trước outcomes; bản đề xuất này chưa bật thu thập/chấm điểm mới, chưa sửa gate một năm. Log vận hành và lịch sử sensitivity không phải bằng chứng dự báo tương lai đã xác nhận.
'''
    (OUT/'oos_proposal.md').write_text(proposal,encoding='utf-8')
    strongest=sp.sort_values('qvalue_bh').head(12)[['asset','target','model','variant','comparison','n','mean_loss_new_minus_base','ci_low','ci_high','pvalue','qvalue_bh']]
    note=f'''# PIT theo feature, sensitivity và nested backtest — 20/10/2026

Đã thực hiện trong namespace riêng `{VERSION}` trên snapshot đến **15/10/2026**. Bảo toàn **{validation['protected_files']} tệp cũ** bằng SHA-256. Đây là đánh giá lịch sử **exploratory**: các outcomes đã được xem trước khi thiết kế này, kể cả nested outer 2023–2026. Chưa có confirmed future skill hoặc nhận dạng nhân quả mới.

## Kết quả audit

**{audit['passed']}/{audit['checks']} kiểm tra reconstruction/timing đạt**, {audit['feature_definitions']} định nghĩa feature, {audit['lineage_rows']} dòng lineage macro. Không phát hiện vi phạm ngày observation/vintage so với information date trong dữ liệu đã audit. Điều này không chứng nhận mọi feature là PIT hoàn chỉnh: ALFRED có vintage theo ngày; crypto, VIX, S&P và gold vẫn dùng snapshot lịch sử, chưa có receipt/revision archive theo từng ngày quá khứ.

{md(features_short)}

Tách ba mốc: ngày quan sát; ngày vintage/công bố có bằng chứng; lúc thực nhận ở máy. `selected_record_revision_date` khác `source_last_update_date` khi nguồn sửa một quan sát khác. Retrieval 16/10/2026 là sự kiện tải snapshot, không chứng minh dữ liệu đã được nhận trong năm 2014. Gold là GC=F continuous futures, có ảnh hưởng roll; Fed Funds effective change không phải policy surprise. Broad USD không phải DXY và không nối vintage trước 2019.

## Revision và timing trên cùng mẫu

Các số `n_asof/n_paired/n_materially_revised` đếm information dates trên lịch ngày, gồm những ngày giữ nguyên một quan sát cũ; không phải số lần công bố hay số sự kiện revision độc lập. Độ lớn revision giữ đúng đơn vị feature: log change, bps hoặc NFCI index level.

{md(revision)}

`matched_latest_d3` là counterfactual **EX POST ORACLE**: đổi sang giá trị cuối trong archive đã khóa cho đúng hai observation dates lịch sử; giữ nguyên eligibility/observation selection. Không lấy quan sát mới hơn và không coi đó là feature dự báo hợp lệ. Oracle chỉ kiểm tra revision ALFRED; không tái tạo được revisions lịch sử của crypto/Yahoo/VIX.

Riêng WTI có 145 information dates mà change as-of có giá trị nhưng counterfactual không còn đủ cặp giá trị hợp lệ, gồm các observation dates bị thay bằng missing trong archive cuối. Các ngày này được loại đối xứng khỏi cả ba scenario matched; không lấy một quan sát cũ khác thay thế cho cặp đã khóa. Bảng revision chỉ tính độ lớn trên cặp cùng có giá trị, vì vậy phải đọc cùng `n_asof/n_paired` và bảng coverage.

Với target UTC day D, baseline dùng information I=D−3, own crypto close I+1, assumed available I+2, market proxy tại D−4. D4 sensitivity dùng I=D−4 và market D−5. Không forward-fill market returns. Macro dùng thay đổi giữa hai quan sát mới nhất trong cùng vintage, giữ change đó cho đến thông tin mới theo thiết kế cũ; không gán nhầm thành một shock mới mỗi cuối tuần.

Ba scenario matched dùng giao origin **ở cả training, inner validation và outer test**. Native D3 giữ riêng để thấy ảnh hưởng đổi mẫu. {'; '.join(retention)}. Thay đổi native→matched phản ánh đổi mẫu huấn luyện trên cùng test dates, không phải tác động thuần của timing.

{md(sample_short)}

![Số origins](figures/sample_coverage.png)

## Nested chronological evaluation

640 learned artifacts, 320 outer fit groups. Outer refit đầu mỗi năm 2023/24/25/26, training expanding; inner chọn tham số bằng H1/H2 của năm trước. Không random K-fold. Tất cả preprocessing/scale/smearing fit bằng nhãn training. Ở mỗi fold, nhãn cần `label_available <= fold_start −24h`; nhãn của validation cuối năm cũng phải khả dụng trước cutoff chọn tham số outer. So với latency cũ, fit cutoff thêm 24h là lựa chọn bảo thủ đã khóa, không phải kết luận cutoff cũ rò rỉ.

{md(timing_summary)}

Giữ nguyên grids và hai learners. Aggregate MSE cho return, QLIKE cho variance; chọn trong inner, refit và đánh giá outer mà không dùng outer scores chọn mô hình. Targets là daily return/squared return, không trộn với Binance intraday RV đã có ở nghiên cứu khác. Số cảnh báo fit ghi nhận: **{len(warnings)}**; xem `fit_warnings.json`.

Nhãn cũng được dựng từ snapshot Coin Metrics tải 16/10/2026. Mốc `D+2` là giả định khả dụng đã công bố, không phải log thực nhận nhãn ở từng ngày lịch sử. Nếu có historical PriceUSD revisions sau cutoff fit, snapshot này chưa đủ loại trừ ảnh hưởng đó. Nested/purge xử lý việc dùng nhãn quá sớm theo quy ước đã khóa, không tự chứng nhận vintage của nhãn hoặc sửa được lịch sử nhà cung cấp chưa lưu.

{md(counts)}

Ở kết quả gộp, native D3 có 3/32 macro ablations tốt hơn sau BH; ba scenario matched đều 0/32. Các cấu hình learned đều 0/40 vượt benchmark sau BH ở từng scenario gộp. Đây là tín hiệu lợi ích macro không ổn định theo thiết kế/mẫu, chưa phải chứng minh hệ số hay hiệu quả giữa các thiết kế khác nhau: chênh lệch significance tự nó không phải kiểm định chênh lệch effects. Dùng các paired sensitivity bên dưới để đánh giá thay đổi trực tiếp. Trong toàn bộ các scope, bao gồm từng năm, vẫn có **{full_benchmark_wins}** so sánh learned thắng benchmark sau BH; không lấy các năm riêng thắng để thay kết luận gộp.

Các số trên là các so sánh liên quan nhau, không phải số phát hiện độc lập. BH điều chỉnh trong toàn family đã khóa, gồm 4 scenarios và pooled/4 annual scopes: 640 ablation, 800 benchmark, 600 sensitivity. Negative mean loss = cấu hình mới tốt hơn. Không so trực tiếp số BH với report cũ để kết luận phương pháp mới tốt/xấu, vì kỳ đánh giá, mẫu và family kiểm định khác nhau.

## Sensitivity kết quả

{md(sensitivity_summary)}

Thêm ngày đệm có 1/40 cấu hình tốt hơn và 1/40 kém hơn sau BH trên kết quả gộp; không có cải thiện đồng loạt. Counterfactual latest vintage có 0/40 tốt hơn, 2/40 kém hơn sau BH, nên không thể mặc định revisions làm kết quả dự báo đẹp hơn trong dữ liệu này. Những kết quả đó chỉ nói về các learners, targets, cặp quan sát và sample đã khóa; không kết luận mọi revision vô hại hoặc việc bỏ kiểm soát PIT là chấp nhận được.

![Sensitivity timing](figures/timing_sensitivity.png)

{md(strongest)}

CI/p-values dùng 999 resamples của calendar clusters 30 ngày; paired loss MSE/QLIKE, BH trong từng family. CI mô tả pointwise, p hai phía centered bootstrap; không phải bootstrap toàn bộ thuật toán nested, không chứng minh causal effect và không xóa selection từ việc đã xem dữ liệu. Ít calendar clusters theo năm làm suy luận kém chính xác. Giữ toàn bộ kết quả, không chọn scenario thắng làm kết luận xác nhận.

## OOS độc lập và hạn nộp

**Chưa chốt được kỳ OOS vì chưa có hạn nộp.** [Phương án cụ thể](oos_proposal.md), [draft máy đọc được](oos_protocol_draft.json). Protocol một năm giữ nguyên. Không có future score mới, không backdate forecasts và không đặt lại tên test đã xem thành untouched. Có thể dùng một pilot ngắn hơn khi khóa minh bạch trước outcomes; độ dài do hạn nộp và số origins thực có quyết định, không có yêu cầu chung bắt buộc một năm.

## Kiểm chứng và chạy lại

{validation['passed']}/{validation['total']} kiểm tra độc lập và {len(validation['guards'])} edge guards đạt. Replay toàn bộ 640 artifacts/{validation['forecast_values_replayed']} prediction values, fit lại 8 mô hình đại diện và kiểm tra scaler của toàn bộ Elastic Net chỉ từ training. [Chi tiết kiểm chứng](independent_validation.json), [lineage macro](macro_row_lineage.csv), [forecast metrics](forecast_metrics.csv), [sensitivity đầy đủ](sensitivity_tests.csv), [ablation](ablation_tests.csv), [benchmark](benchmark_tests.csv), [fold timing](fold_timing.csv), [inner search](inner_search.csv).

```powershell
py -3.11 run_pit_nested.py validate
py -3.11 run_pit_nested.py compare
py -3.11 run_pit_nested.py product
```

Artifacts đã freeze: không chạy `audit/fit/all` đè lên bản này. Trên bản sao repo trước khi freeze, `audit → fit → compare → validate → product` tái tạo toàn bộ; cần Python dependencies hiện có. [Thiết kế khóa](../../../config/pit_nested_20261020.json), [khóa code fit](fit_code_lock.json), [khóa input](prepared_input_lock.json).

Phương pháp tham khảo: [ALFRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [Cawley–Talbot về nested evaluation](https://www.jmlr.org/papers/v11/cawley10a.html), [TimeSeriesSplit: gap theo số hàng](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html). [Rà soát tài liệu trước triển khai](../pit_oos_review_20261019/report.html).
'''
    (OUT/'report.md').write_text(note,encoding='utf-8')
    style='''body{font:16px/1.6 system-ui,sans-serif;color:#153248;background:#f2f6f8;margin:0}main{max-width:1180px;margin:28px auto;background:white;padding:32px;border-radius:12px}h1{font-size:30px;line-height:1.2}h2{font-size:23px;margin-top:36px;color:#075873}a{color:#07688c}p{overflow-wrap:anywhere}.table-wrap{overflow-x:auto;margin:20px 0}table{border-collapse:collapse;font-size:13px;min-width:650px;width:100%}th,td{border-bottom:1px solid #dce5eb;padding:8px;text-align:left;vertical-align:top}th{background:#e9f1f5}code,pre{background:#edf2f6}pre{overflow-x:auto;padding:16px}figure{margin:25px 0}img{max-width:100%;height:auto}@media(max-width:700px){main{margin:0;padding:18px;border-radius:0}h1{font-size:25px}body{font-size:15px}}'''
    (OUT/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PIT audit và nested backtest</title><style>'+style+'</style><main>'+render_markdown(note)+'</main></html>',encoding='utf-8')
    # Keep proposal rendering separate for easy review without empirical tables.
    (OUT/'oos_proposal.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OOS proposal</title><style>'+style+'</style><main>'+render_markdown(proposal)+'</main></html>',encoding='utf-8')
    print('Report:',OUT/'report.html',flush=True)
