"""Audit-led report and offline dashboard for the FOMC identification extension."""
from src.evaluation.fomc_identification_common import *
from src.robustness_product import md,render_markdown
import zipfile,hashlib

def read(name):return pd.read_csv(OUT/name)

def findings():
    e=read('timing_estimates.csv');full=e[e.regime=='full'];d=read('timing_difference_tests.csv');r=read('rotation_sensitivity.csv')
    pivot=r.pivot(index=['asset','outcome','shock'],columns='weight',values='beta_pct_per10bps')
    a=read('event_audit.csv');primary=a[(a.asset=='BTC')&a.primary_joint]
    return dict(audit=json.loads((OUT/'audit_summary.json').read_text()),primary_BH128_significant=int((full.qvalue_bh<.05).sum()),period_BH256_significant=int((e[e.regime!='full'].qvalue_bh<.05).sum()),
                timing_difference_BH8_significant=int((d.qvalue_bh8<.05).sum()),rotation_sign_changes_of128=int(((pivot.min(axis=1)*pivot.max(axis=1))<0).sum()),
                primary_first_date=str(primary.date.min()),primary_last_date=str(primary.date.max()),
                causal_scope='High-frequency sign-restricted policy/information shock application; conditional on assumptions, not unconditional proof or replication of monthly JK Bayesian VAR',
                forecasting='Historical event study only; latency models/prospective protocol unchanged')

def figures():
    estimates=read('timing_estimates.csv');full=estimates[estimates.regime=='full'];rot=read('rotation_sensitivity.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,shock in zip(axes,['policy','information']):
        for i,asset in enumerate(['BTC','ETH']):
            q=full[(full.asset==asset)&(full.shock==shock)&(full.outcome=='intraday')].iloc[0]
            ax.errorbar(i,q.beta_pct_per10bps,yerr=1.95996398454*q.se,fmt='o',capsize=5,label=asset)
            s=rot[(rot.asset==asset)&(rot.shock==shock)&(rot.outcome=='intraday')]
            ax.plot([i+.16,i+.16],[s.beta_pct_per10bps.min(),s.beta_pct_per10bps.max()],color='#a4567d',ls='--',alpha=.8,label='3-rotation range (not CI)' if i==0 else None)
        ax.set_xticks([0,1],['BTC','ETH']);ax.axhline(0,color='#888',lw=.7);ax.set_title(shock+' component, [-10,+20] minutes');ax.set_ylabel('Crypto log return (%) / +10bp pc1 contribution');ax.legend(fontsize=7)
    fig.suptitle('75 identical scheduled events | median rotation; conditional pointwise HAC 95% CI');fig.tight_layout();fig.savefig(OUT/'figures/intraday_components.png');plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for i,asset in enumerate(['BTC','ETH']):
        for j,shock in enumerate(['policy','information']):
            ax=axes[i,j];g=full[(full.asset==asset)&(full.shock==shock)&full.outcome.str.startswith('post_')].copy();g['h']=g.outcome.str.split('_').str[-1].astype(int);g=g.sort_values('h')
            ax.plot(g.h,g.beta_pct_per10bps);ax.fill_between(g.h,g.lower95,g.upper95,alpha=.15);ax.axhline(0,color='#888',lw=.7)
            ax.set_title(asset+' / '+shock);ax.set_xlabel('Calendar days D+1 through D+h; event day excluded');ax.set_ylabel('Cumulative log return (%) / +10bp component')
    fig.suptitle('Post-event outcome | same75 events; conditional HAC CI excludes shock-estimation uncertainty');fig.tight_layout();fig.savefig(OUT/'figures/post_event_components.png');plt.close(fig)

def build():
    init();headline=findings();save_json(OUT/'headline_findings.json',headline);figures()
    save_json(OUT/'measurement_window_audit.json',dict(status='NOMINAL_WINDOW_ALIGNMENT_ONLY',author_pre_price='Median in (t-15min,t-5min], representing t-10min',author_post_price='Median in [t+15min,t+25min), representing t+20min',author_thin_quote_rule='Authors may extend quote windows when fewer than3 observations; event-specific extension flags are not supplied in published shock file',crypto_price='Exact close of minute immediately preceding t-10min/t+20min; all31 required closes',identical_tick_sampling=False,interpretation='Same nominal announcement window and timestamp, different price sampling. Published shocks used unchanged. Not an exact tick/window-construction replication; underlying market tick coverage cannot be certified from published shock series.',source='Pinned author README.md, Computation of the surprises'))
    estimates=read('timing_estimates.csv');full=estimates[estimates.regime=='full'];intraday=full[full.outcome=='intraday'];sig=full[full.qvalue_bh<.05]
    audit=read('event_audit.csv');g=audit[(audit.asset=='BTC')&audit.primary_joint]
    scale=pd.DataFrame([dict(shock=name,min_bps=g[col].min()*100,max_bps=g[col].max()*100,std_bps=g[col].std()*100,positive10bps_within_observed_range=bool(g[col].max()>=.1)) for name,col in [('policy','author_policy'),('information','author_information')]])
    csv(scale,'shock_scale.csv')
    loo=read('influence_ranges.csv');r=read('rotation_sensitivity.csv');a=headline['audit'];replay=json.loads((OUT/'decomposition_replay.json').read_text())
    text=f'''# Chủ đề 9 — FOMC identification và so sánh timing, 19/10/2026

Đã hoàn thành audit trước fit, khóa thiết kế và cùng một membership cho toàn bộ cửa sổ. Phiên bản mới giữ nguyên {check_protected()} file dữ liệu/kết quả/models/protocol/ZIP trước đó. Đây là nghiên cứu lịch sử về shock FOMC; không đổi mô hình forecasting, VIX/USD identification hoặc stress threshold.

## Kết quả có thể sử dụng

Trên **{a['primary_joint_events']} sự kiện định kỳ chung** ({a['primary_pre2020']} trước2020, {a['primary_post2020']} từ2020), median policy component gắn với phản ứng30phút khoảng **−1,163% BTC và −1,422% ETH trên mỗi +10bps đóng góp vào policy indicator**. Cả hai đạt BH trong family128. Crypto không được áp đặt dấu khi xây shock; dấu âm này là kết quả ước lượng có điều kiện.

Có **{headline['primary_BH128_significant']}/128 hệ số full đạt BH**: hai intraday policy effects và BTC post1 information effect. Không suy từ một horizon đạt BH thành một chuỗi tác động kéo dài. Information intraday có CI pointwise không chứa0 nhưng chưa đạt BH128. Có **{headline['timing_difference_BH8_significant']}/8 chênh lệch slope giữa cửa sổ** đạt BH, nên chưa đủ cơ sở khẳng định slope phút khác slope event-day/post7 chỉ vì p-values khác nhau.

{md(intraday[['asset','shock','beta_pct_per10bps','lower95','upper95','qvalue_bh','nobs']])}

![Intraday policy and information components](figures/intraday_components.png)

CI ở đây là HAC pointwise95% **có điều kiện trên chuỗi shock công bố và rotation median đã chọn**. Không bao gồm uncertainty của PCA, covariance nhận diện hoặc toàn bộ tập rotation; không phải simultaneous bands. Các đường tím đứt chỉ gợi phạm vi hệ số ở3 rotations, không phải CI.

Các hệ số full đạt BH:

{md(sig[['asset','outcome','shock','beta_pct_per10bps','lower95','upper95','qvalue_bh']])}

## Dữ liệu, đơn vị và coverage

Universe frozen USMPD có {a['total_statements']} Statements từ2014 đến15/10/2026; {a['scheduled']} định kỳ. Exact announcement timestamp khớp tác giả ở {a['author_exact_matches']} events. Hai unmatched events là thông báo bất thường; không dùng nearest-date matching để ép ghép.

USMPD futures/OIS/yields là chênh lệch implied rate theo percentage points: ×100 thànhbps. USMPD SP500 là simple percent return; tác giả JK SP500 là100×log change, có quy trình giá median riêng. Hai nguồn không được coi là những quote giống hệt nhau. Thống kê FF3/OIS/UST2Y được audit nhưng **shock chính lấy từ chuỗi công bố của tác giả**, không đổi tên STMT hay FF3 thành policy shock.

**Cửa sổ chỉ đồng bộ ở mức danh nghĩa, chưa phải cùng quote sampling.** Tác giả dùng median trong(t−15,t−5] để đại diện mốc−10 và[t+15,t+25) để đại diện mốc+20; có thể mở rộng nếu thiếu3 observations. Crypto dùng exact minute closes tại mốc−10/+20. Published shock file không có tick-level coverage hoặc event-specific extension flags để kiểm tra lại toàn bộ quy tắc này. Vì thế không gọi đây là replication đồng bộ tick/window construction, và diễn giải intraday còn phụ thuộc khác biệt measurement. [Audit cách lấy giá](measurement_window_audit.json).

Coinbase BTC/USD daily có từ20/07/2015 và ETH/USD từ18/05/2016 trong cache mới. Dùng cùng venue/USD với minute returns để giảm khác biệt nguồn khi so timing. Nến ngày có timestamp UTC-day start; close là close của ngày đó. Không nối vào Coin Metrics hoặc Binance USDT. Cache phút frozen được kiểm lại SHA và31 endpoint-inclusive minute closes; boundary price là close của phút ngay trước boundary, không nội suy/forward-fill. ET→UTC dùng America/New_York có DST.

{md(read('coverage_summary.csv'))}

Primary intersection là cùng75 events cho BTC/ETH, intraday, event-day và post1…post30; actual range **{headline['primary_first_date']} đến {headline['primary_last_date']}**. Đây là yêu cầu công bằng về membership, không phải nói mẫu crypto lịch sử chỉ bắt đầu2016. Loại sự kiện cuối sample nếu chưa đủ30 ngày outcome; báo mọi exclusion trongCSV. Daily-only sensitivity giữ mọi per-asset event đủ daily/control/shock nhưng không cần minute coverage; dùng để xem tác động chọn mẫu, không chọn kết quả đẹp hơn làm baseline.

## Phép tách shock đã kiểm tra

Dùng repository do Jarocinski và Karadi duy trì, pinned commit **{a['author_commit']}**, shock theo announcement đến **{a['author_last_event']}**. Chuỗi policy indicator làPC1 củaMP1/FF4/ED2/ED3/ED4, chuẩn hóa theo độ lệch chuẩn ED4. Không dùng crypto để chọn factor, sign hoặc rotation. Local replay khớp PCA với sai số tối đa {replay['pca_max_error']:.3g}; median components khớp chuỗi công bố trong sai số làm tròn tối đa {replay['median_component_max_error']:.3g}.

Theo mã tác giả, PCA không center và xử lý missing theo quy tắc của họ; normalized QR rotation tách policy component có rate loading+ và stock loading−, information component có rate loading+ và stock loading+. Cả hai có thể cùng xuất hiện trong một announcement, tổng bằngpc1. Orthogonality là **uncentered second moment** theo giả định population mean0, không khẳng định sample covariance sau demean bằng0. Các row thiếu inputSP500 mà tác giả xuất shock0 được loại khỏi identification, không coi là event không có shock.

Hệ số báo theo+10bps **đóng góp vào pc1**, không phải thay đổi Fed target thực tế, không phải STMT/FF3+10bps. Chuẩn hóa và calibration dùng toàn bộ mẫu tác giả, mang tính retrospective; không dùng làm PIT forecasting feature. Support trong75 events:

{md(scale)}

Policy +10bps nằm trong khoảng positive component quan sát; information +10bps vượt positive support (~5,551bps), nên dùng như reporting unit và xem thêm1SD, không ngoại suy thành sự kiện điển hình.

Đây là ứng dụng chuỗi shock high-frequency sign-restricted vào crypto; **không tái lập monthly Bayesian VAR của JK2020**, và không có đầy đủ posterior uncertainty của bài gốc. Thiết kế mở rộng có lợi về nhận diện so với chỉ dùng Δyield/VIX, nhưng diễn giải causal còn phụ thuộc no-confounding-news trong window, sign restrictions, cấu trúc hai shocks và external validity. Những giả định đó không được xác nhận chỉ bằng phép replay số học.

## So ba loại timing trên cùng X và cùng events

Outcome là (i)100log return[-10,+20] phút quanhstatement; (ii)full event UTC-day return; (iii)tổng daily log returns D+1…D+h, h1…30. Event-day chứa phần trước thông báo, press conference và tin khác trong ngày; post outcomes loại ngày thông báo. Các outcome này là interval khác nhau, không gọi chúng là một IRF có cùng đơn vị thời gian. Shock vẫn từ statement window, không tách tác động press conference chỉ bằng daily regression.

Mọi fit có intercept, cả policy và information components, prior crypto returnD−2, prior trailing30 RMSD−2 và frozen available VIX proxy. Controls và events giữ nguyên qua outcomes. OLS/HAC5 finite correction theo thứ tự event; event spacing/overlap và small sample khiến uncertainty chỉ xấp xỉ. Full family128=2assets×32outcomes×2shocks; pre/post family256 riêng. CI không simultaneous; không so overlap CI/p của hai mẫu để kết luận khác slope.

![Post-event components](figures/post_event_components.png)

Direct timing difference là hồi quy (event-day−intraday) hoặc (post7−intraday) lên cùng X, nên covariance giữa hai outcome được tính trong SE. Family8 riêng:

{md(read('timing_difference_tests.csv'))}

Pre/post có23/52 events; số q nhỏ trong subgroup không làm giả định xấp xỉ trở nên đúng. Không coi BH correction là finite-sample repair. Chưa chạy pooled pre/post slope-difference test ở phiên bản này, nên không khẳng định thay đổi sensitivity có ý nghĩa chỉ từ hai đường fit riêng.

## Độ nhạy nhận diện và ảnh hưởng sự kiện

Giữ cùng calibration sample và membership, tính lại components theo w=.1,.5,.9 trong khoảng rotation thỏa sign restrictions. **{headline['rotation_sign_changes_of128']}/128 hệ số full đổi dấu** giữa3 rotations. Đây là3 lựa chọn để chẩn đoán, không phải toàn bộ identified-set bounds hoặc posterior credible interval. Intraday policy giữ dấu âm ở cả3 rotations; information magnitude thay đổi mạnh:

{md(r[r.outcome=='intraday'][['asset','weight','shock','beta_pct_per10bps']])}

Sau khi xem hệ số chính, bổ sung **post-hoc** chẩn đoán case-deletion cho toàn bộ128 hệ số, không chọn riêng kết quả significant. Giữ cố định shock construction/controls, bỏ từng event row;9600 point estimates lưu riêng, không chọn mẫu hay báo q sau deletion. Intraday policy cũng giữ dấu âm trong75 lần xóa từng sự kiện:

{md(loo[loo.outcome=='intraday'])}

Dải deletion/rotation **không phải CI**. Giữ dấu ở những đối chiếu này không chứng minh mọi loại độ vững hoặc exclusion restriction. Monetary stress9-event result và joint VAR diagnostics của bản trước giữ nguyên; kết quả FOMC mới không tự xử lý chúng.

## Chạy lại và gói bổ sung

```powershell
py -3.11 run_fomc_identification.py audit
py -3.11 run_fomc_identification.py fit
py -3.11 run_fomc_identification.py influence
py -3.11 run_fomc_identification.py validate
py -3.11 run_fomc_identification.py product
node tests/validate_fomc_identification_dashboard.cjs
node tests/preview_fomc_identification.cjs
```

Stage sources dùng cache nếu có; tải public sources chỉ khi thiếu. Audit khóa config, author snapshot và panel hash trước fit. Influence có spec ghi rõ hậu nghiệm. Mọi dữ liệu/kết quả mới nằm riêng;40 latency artifacts và prospective protocol không thay đổi.

ZIP phiên bản này là **gói bổ sung cho repository hiện có**, không chứa lặp các ZIP/model bundles cũ. Giải nén vào bản sao repo hiện tại, giữ nguyên prerequisites; validation vẫn kiểm mọi1077 hash đã khóa. Manifest phân biệt files trong gói và external frozen prerequisites. Không gọi đây là standalone bundle hoặc giả định có thể chạy từ một thư mục trống.

## Bằng chứng và nguồn

[Dashboard](dashboard.html) · [audit](event_audit.csv) · [coverage](coverage_summary.csv) · [price-window audit](measurement_window_audit.json) · [exclusions](exclusions.csv) · [replay](decomposition_replay.json) · [estimates](timing_estimates.csv) · [rotations](rotation_sensitivity.csv) · [influence](leave_one_event_out.csv) · [independent validation](independent_validation.json) · [thiết kế khóa](../../../config/fomc_identification_20261019.json) · [forecasting riêng giữ nguyên](../latency_20261019/report.html).

Nguồn phương pháp: [Jarocinski–Karadi2020](https://www.aeaweb.org/articles?id=10.1257/mac.20180090), [maintained author code/data](https://github.com/marekjarocinski/jkshocks_update_fed), [SF Fed USMPD](https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/). Author data CC BY4.0, code BSD3-Clause theo repository README; attribution và nguồn pinned giữ trong raw manifest. Nguồn được dùng để xác định phương pháp/đơn vị, không coi việc khớp code là bằng chứng giả định kinh tế đúng.

Chưa có kết quả dự báo tương lai mới từ nghiên cứu này. Các kết luận là conditional/exploratory historical research, không phải khuyến nghị đầu tư.
'''
    (OUT/'report.md').write_text(text,encoding='utf-8')
    css='body{font:16px/1.65 system-ui;color:#193849;max-width:1120px;margin:30px auto;padding:0 20px}h1{line-height:1.25}h2{color:#096b93;margin-top:30px}img{max-width:100%;height:auto}.table-wrap{overflow:auto;max-width:100%}table{border-collapse:collapse;font-size:13px}td,th{padding:8px;border-bottom:1px solid #dbe4eb;white-space:nowrap}a{color:#096b93}pre{white-space:pre-wrap;overflow-wrap:anywhere}code{overflow-wrap:anywhere}'
    (OUT/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FOMC identification & timing</title><style>'+css+'</style><body><p><a href="dashboard.html">Mở dashboard FOMC</a></p>'+render_markdown(text)+'</body></html>',encoding='utf-8')
    payload={name:json.loads(read(name+'.csv').to_json(orient='records',double_precision=15)) for name in ['timing_estimates','timing_difference_tests','rotation_sensitivity','influence_ranges','coverage_summary','shock_scale']}
    payload['findings']=headline
    template=(ROOT/'dashboard/fomc_identification_template.html').read_text(encoding='utf-8')
    (OUT/'dashboard.html').write_text(template.replace('__PAYLOAD__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/')),encoding='utf-8')
    print('FOMC report, figures and dashboard generated.',flush=True)

def package():
    check_protected();report=json.loads((OUT/'independent_validation.json').read_text());assert report['passed']==report['total']
    assert json.loads((OUT/'browser_validation.json').read_text())['uncaught_errors']==0
    path=ROOT/f'topic09_{VERSION}_supplement.zip';mp=ROOT/f'manifest_{VERSION}.json';assert not path.exists()
    files=set()
    for folder in [OUT,RAW,PANELS]:files.update(p for p in folder.rglob('*') if p.is_file())
    for folder in ['src','tests']:
        files.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and 'fomc_identification' in p.name and '__pycache__' not in p.parts)
    files.update([CONFIG,ROOT/'README.md',ROOT/'run_fomc_identification.py',ROOT/'dashboard/fomc_identification_template.html',ROOT/'paper/fomc_identification_20261019.md'])
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}
    dependencies=['research_common.py','research_fomc_comparison.py','preview_completion.cjs','src/utils/project.py','src/robustness_product.py','src/evaluation/robustness_common.py','requirements-project.txt','requirements-research.txt','requirements.txt']
    base_code={name:sha(ROOT/name) for name in dependencies}
    save_json(mp,dict(version=VERSION,type='Supplement for existing repository; not standalone',files=hashes,external_frozen_prerequisites=init()['protected_sha256'],base_code_dependencies=base_code,instructions='Extract into a copy of the existing topic09 repository. Previous ZIPs/models are referenced, not nested. Install requirements-project.txt from base repo.'))
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,p.relative_to(ROOT).as_posix())
        z.write(mp,mp.name)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    obj=dict(file=path.name,bytes=path.stat().st_size,files=len(hashes)+1,sha256=sha(path),CRC_and_all_SHA256_verified=True,type='Supplement; existing base repository required')
    save_json(ROOT/f'package_{VERSION}.json',obj);print(json.dumps(obj,indent=2))
