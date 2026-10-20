"""Report the approved lag change, fair comparisons and genuine prospective status."""
from src.evaluation.latency_common import *
from src.robustness_product import md,render_markdown
import zipfile,hashlib

def read(name):return pd.read_csv(OUT/name)

def findings():
    a=read('ablation_tests.csv');b=read('benchmark_tests.csv');c=read('timing_comparison_common_dates.csv')
    return dict(ablation_q05=int((a.qvalue_bh<.05).sum()),ablation_improved_q05=int(((a.qvalue_bh<.05)&(a.mean_loss_added_minus_base<0)).sum()),
                benchmark_improved_q05=int(((b.qvalue_bh<.05)&(b.mean_loss_added_minus_base<0)).sum()),benchmark_worse_q05=int(((b.qvalue_bh<.05)&(b.mean_loss_added_minus_base>0)).sum()),
                test_origins=int(read('sample_summary.csv').test.min()),common_old_new_origins=int(c.n_common.min()),
                fit_warnings=len(json.loads((OUT/'fit_warnings.json').read_text(encoding='utf-8'))),artifacts=len(read('model_inventory.csv')),
                prospective=json.loads((OUT/'prospective_status.json').read_text(encoding='utf-8')),
                capture=json.loads((OUT/'latest_capture.json').read_text(encoding='utf-8')),
                interpretation='Exploratory on previously inspected test; no causal or confirmed future forecasting claim')

def figures():
    p=read('test_predictions.csv');fig,axes=plt.subplots(2,2,figsize=(12,7))
    for i,asset in enumerate(['btc','eth']):
        for j,kind in enumerate(['elastic_net','gradient_boosting']):
            a=p[(p.asset==asset)&(p.target=='squared_return')&(p.model==kind)&(p.variant=='long_own')].sort_values('date_utc')
            b=p[(p.asset==asset)&(p.target=='squared_return')&(p.model==kind)&(p.variant=='long_macro')].sort_values('date_utc')
            assert a.date_utc.tolist()==b.date_utc.tolist()
            loss=lambda g:np.log(g.predicted.to_numpy())+g.actual.to_numpy()/g.predicted.to_numpy()
            d=loss(b)-loss(a);ax=axes[i,j];ax.plot(pd.to_datetime(a.date_utc)+pd.Timedelta(days=1),np.cumsum(d))
            ax.axhline(0,color='#888',lw=.7);ax.set_title(asset.upper()+' / '+kind);ax.set_ylabel('Cumulative QLIKE: macro minus own');ax.tick_params(axis='x',rotation=20)
    fig.suptitle('New timing / long no-USD sample | negative favors macro, historical exploratory test');fig.tight_layout();fig.savefig(OUT/'figures/cumulative_variance_loss.png');plt.close(fig)
    c=read('timing_comparison_common_dates.csv');q=c[(c.target=='squared_return')&(c.model.isin(['elastic_net','gradient_boosting']))&(c.variant.isin(['long_macro','common_usd']))]
    labels=q.asset.str.upper()+' / '+q.model.str.replace('gradient_boosting','GB').str.replace('elastic_net','EN')+' / '+q.variant
    fig,ax=plt.subplots(figsize=(11,5));ax.barh(labels,q.mean_loss_new_minus_old,color=['#096b93' if x<0 else '#b45c77' for x in q.mean_loss_new_minus_old]);ax.axvline(0,color='#777',lw=.8)
    ax.set_title('Extra feature-day delay: mean QLIKE change on 347 common origins');ax.set_xlabel('New timing minus old timing; negative favors new, descriptive');fig.tight_layout();fig.savefig(OUT/'figures/timing_common_dates.png');plt.close(fig)

def build():
    init();f=findings();save_json(OUT/'headline_findings.json',f);figures()
    a=read('ablation_tests.csv');b=read('benchmark_tests.csv');sig=a[a.qvalue_bh<.05]
    inventory=read('model_inventory.csv');cap=f['capture'];status=f['prospective'];cm=read('timing_comparison_common_dates.csv')
    warnings=json.loads((OUT/'fit_warnings.json').read_text(encoding='utf-8'))
    text=f'''# Chủ đề 9 — Features trễ thêm một ngày, phiên bản riêng 19/10/2026

Đã thực hiện theo đồng ý của người dùng sau khi giải thích bước đệm không xác nhận nhân quả hay forecasting skill. Baseline, econometrics, monetary robustness, dữ liệu nguồn và ZIP cũ giữ nguyên hash. Phần mới chỉ thay timing của predictive features, tái huấn luyện riêng và bổ sung actual-receipt workflow; không fit lại VAR/LP để tìm p-value.

## Kết quả hiện tại

Đã lưu và khóa **{f['artifacts']} learned artifacts**, không có cảnh báo fit. Mỗi cấu hình có **{f['test_origins']} test origins**. **{f['ablation_improved_q05']}/32 macro ablations** cải thiện loss với BH q<0,05, đều là squared-return forecasting trên mẫu dài không USD. Trên mẫu chung2019+ chưa có macro/USD ablation đạt BH. So benchmark: **{f['benchmark_improved_q05']}/40 learned tốt hơn, {f['benchmark_worse_q05']}/40 kém hơn** đạt BH.

Ba tín hiệu macro có điều kiện không chứng minh mô hình đã vượt benchmark. Không suy từ cải thiện so crypto-only sang predictive skill đã được xác nhận; test2025+ đã xem nên mọi kết quả lịch sử mới vẫn exploratory. Extra lag không bảo đảm cải thiện accuracy và không thiết lập causal transmission.

{md(sig[['asset','target','model','base','added','n_pairs','mean_loss_added_minus_base','qvalue_bh']])}

![Cumulative variance loss](figures/cumulative_variance_loss.png)

## Timing và mẫu đã khóa

Original panel row t dự báo UTC day D=t+1. Completion cũ lấy features ở row t−1; phiên bản này lấy **row t−2=D−3**, dịch trên calendar đầy đủ trước khi drop missing. Own crypto return/squared return/trailing30 RMS tại D−3; theo quy ước date labeling của baseline, reference close là D−2 00:00 UTC. Market features vốn lag1 dùng return đúng ngày D−4. Macro dùng last two known observation dates trong cùng ALFRED vintage tại D−3; NFCI dùng level. Không biến nó thành chênh lệch giữa hai ngày capture. Giữ nguyên nguồn USD và đơn vị; không thêm MOVE, không đổi Broad USD thành DXY, không nối USDT vào USD.

Không carry market returns trên ngày nghỉ, không fill hoặc bridge missing crypto days. Các mức macro đã biết có thể tiếp tục là thông tin mới nhất; changes trong model này là thay đổi giữa hai observation trong cùng vintage, đúng định nghĩa training cũ, không phải pure policy surprise.

Own vs macro không USD dùng cùng eligible dates trên mẫu dài. Các cấu hình common_own/common_macro/common_usd dùng cùng dates và USD vintage>=2019-02-04. Thiếu macro prerequisite thì không ghi own-only forecast để rồi đem so sánh trên mẫu khác.

{md(read('sample_summary.csv'))}

Train: target trước2023; validation2023–2024; test2025+ đã xem. Label close+24h phải không muộn hơn first validation/test origin; purge boundary labels. Targets giữ nguyên, chỉ features/vintage metadata dịch thêm một ngày. Preprocessing fit trên train; giữ grid EN/GB, minimum validation MSE cho return và QLIKE cho squared return, refit train+validation có nhãn khả dụng. Historical mean và natural benchmark (zero return hoặc trailing30 mean squared return) giữ nguyên định nghĩa.

Không retune theo test hay prospective outcomes. EN variance dùng log-target + smearing; histogram boosting dùng Poisson log link, variance dương và không đặt prediction floor. Squared daily return là noisy variance proxy, không phải intraday realized volatility. Test coefficient comparisons dùng HAC5 trên chuỗi eligible origins và BH32/BH40 riêng: xấp xỉ dưới dependence, không phải confirmatory inference.

## So timing cũ và mới trên đúng cùng ngày

Old test có447 origins, new có446; giao nhau **{f['common_old_new_origins']} origins**. Không so trực tiếp hai metric tính trên ngày khác nhau để kết luận lag mới tốt hơn. Xuất80 comparisons của mọi asset/variant/target/model trên giao nhau; đây là đối chiếu mô tả, không bổ sung family significance để chọn thiết kế.

Đọc CSV bằng round-trip ở phiên bản mới gây chênh lệch target với lượt parse cũ tối đa **{cm.target_roundtrip_max_difference.max():.3g}**, thuộc sai số floating-point. Ghép dates trước, kiểm tra tolerance64eps theo scale target và dùng cùng target mới cho cả hai losses; không thay ngày, không sửa source. Mọi dự báo/metrics lịch sử của bản cũ giữ nguyên.

![Timing comparison on common dates](figures/timing_common_dates.png)

## Prospective đã triển khai đến đâu?

Đã tạo collector và tải lần mới nhất **{cap['sources_ok']}/{cap['sources_total']} response hợp lệ**, gồm crypto, VIX, Yahoo S&P500/gold và 6 ALFRED series ×2 requested information dates. Lần requests POST trước đó bị remote disconnect/timeout; log failures giữ nguyên. Tải lại thành công bằng curl form-download như downloader ALFRED gốc; không thay định nghĩa dữ liệu. Lưu raw ZIP/JSON/CSV, request/form/header và manifest với actual UTC receipt/SHA256. Đây là local receipt evidence, không phải provider-certified publication timestamps.

Feature envelope kiểm tra exact information day, within-vintage macro, đủ31 crypto prices cho30 returns, market observation date, source hashes và actual receipt≤origin−24h. Không lấy current-vintage FRED để thay cho ALFRED vintage đã yêu cầu. Forecasts chỉ ghi strictly trước origin và trong next24h; kiểm tra clock lần cuối sau model inference. Predictions lưu file exclusive theo asset/origin, không overwrite; model inventory và protocol đã khóa. Benchmarks được ghi cùng learned models để paired evaluation thật.

Lần thử hiện tại: origin **{status['origin_utc']}**, **{status['total_predictions']} prediction**. Các snapshot đầu tiên nhận sau cutoff của origin này, nên pipeline từ chối. Không backdate và không log forecast cho origin quá xa chỉ để có kết quả. Input readiness example của21/10 chỉ là kiểm tra features, không phải forecast; own/macro có thể đủ receipt buffer nhưng market return cuối tuần vẫn thiếu, đúng complete-case rule.

Protocol bắt đầu20/10/2026, kết thúc trước20/10/2027; chờ đủ close+24h cho label cuối trước full review. Không tính skill trước fixed window, không interim tuning. Stage labels chỉ lưu nhãn có snapshot thật sau label close+24h; evaluation chỉ ghép những dates cả hai forecast đã thực sự được log và có outcome thật. Phải công bố missing days và coverage. Hiện **chưa có prospective score**; không thể làm sẵn kết quả của dữ liệu tương lai.

## Chạy lại và vận hành

Trên fresh source checkout chưa có artifacts khóa: `prepare`, rồi `train` một lần. ZIP bàn giao có sẵn40 artifacts nên lệnh train/prepare sẽ từ chối ghi đè. Có thể chạy compare/product/validate từ outputs đã lưu; muốn fit lại dùng bản sao hoặc thư mục phiên bản riêng không chứa generated outputs của phiên bản này, không xóa freeze trong bản đang vận hành.

```powershell
py -3.11 run_latency.py validate
py -3.11 run_latency.py compare
py -3.11 run_latency.py product
node tests/validate_latency_dashboard.cjs
node tests/preview_latency.cjs
```

Vận hành hàng ngày (không có scheduler tự cài):

```powershell
py -3.11 run_latency.py collect
py -3.11 run_latency.py forecast
py -3.11 run_latency.py labels
py -3.11 run_latency.py evaluate
py -3.11 run_latency.py product
```

Collector lấy vintage cho origin gần nhất và origin kế tiếp để có thể lưu receipt trước cutoff cho lần chạy ngày sau. Chạy collect hôm nay không làm nó khả dụng trong hôm qua. Nếu nguồn thất bại hoặc ngày cần market return không có, giữ missing attempt, không bù dữ liệu bằng timestamp giả. Evaluate trước hạn trả PENDING, không công bố provisional performance. `all` là luồng fresh fit một lần; không dùng để chạy hàng ngày sau khi models đã khóa.

## Bằng chứng và giới hạn

[Dashboard timing](dashboard.html) · [20 kiểm tra độc lập và 11 unit guards](independent_validation.json) · [model inventory](model_inventory.csv) · [ablation32](ablation_tests.csv) · [benchmark40](benchmark_tests.csv) · [common-date timing80](timing_comparison_common_dates.csv) · [prospective attempt](prospective_status.json) · [latest capture](latest_capture.json) · [protocol](../../../data/prospective/latency_20261019/protocol.json) · [thiết kế khóa](../../../config/latency_20261019.json) · [monetary/VAR robustness giữ nguyên](../robustness_20261019/report.html).

20 checks kiểm alignment, unchanged target, purge, matched samples, manual loss/HAC/BH,80 metrics,40 serialized predictions, requests/vintage provenance và11 deployment guards; không chứng nhận mô hình kinh tế đúng. Historical crypto/market feeds vẫn retrospective snapshots, macro vintage ở date resolution, chưa whole-feed historical PIT. Monetary influence/VAR ARCH-whiteness limitations của bản trước không được giải quyết bởi thêm lag. Không có causal identification hoặc confirmed future skill mới. Không dùng kết quả cho khuyến nghị đầu tư.
'''
    (OUT/'report.md').write_text(text,encoding='utf-8')
    css='body{font:16px/1.65 system-ui;color:#193849;margin:30px auto;padding:0 20px;max-width:1120px}h1{line-height:1.25}h2{margin-top:30px;color:#096b93}img{max-width:100%;height:auto}.table-wrap{overflow:auto;max-width:100%}table{border-collapse:collapse;font-size:13px}th,td{padding:8px;border-bottom:1px solid #dce6ed;white-space:nowrap}a{color:#096b93}pre{white-space:pre-wrap;overflow-wrap:anywhere}code{overflow-wrap:anywhere}'
    (OUT/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Topic09 — Extra feature-day delay</title><style>'+css+'</style><body><p><a href="dashboard.html">Mở dashboard timing</a></p>'+render_markdown(text)+'</body></html>',encoding='utf-8')
    frames={name:json.loads(read(name+'.csv').to_json(orient='records',double_precision=15)) for name in ['forecast_metrics','test_predictions','ablation_tests','benchmark_tests','timing_comparison_common_dates','validation_selected_models']}
    payload=dict(**frames,findings=f)
    template=(ROOT/'dashboard/latency_template.html').read_text(encoding='utf-8')
    (OUT/'dashboard.html').write_text(template.replace('__PAYLOAD__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/')),encoding='utf-8')
    print('New latency report, figures and dashboard built.',flush=True)

def package():
    check_protected();assert read('model_inventory.csv').shape[0]==40
    check=json.loads((OUT/'independent_validation.json').read_text());assert check['passed']==check['total']
    browser=json.loads((OUT/'browser_validation.json').read_text());assert browser['uncaught_errors']==0
    path=ROOT/f'topic09_{VERSION}.zip';mp=ROOT/f'manifest_{VERSION}.json';assert not path.exists(),'Use a new version; do not overwrite a delivered ZIP.'
    snapshot=init();files={ROOT/p for p in snapshot['protected_sha256']}
    for folder in [OUT,PANELS,MODELS,RAW,LIVE,ROOT/'src',ROOT/'tests',ROOT/'paper']:
        files.update(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for pattern in ['*.py','*.cjs','requirements*.txt','manifest*.json']:
        files.update(p for p in ROOT.glob(pattern) if p.is_file() and p!=mp)
    files.update([ROOT/'README.md',CONFIG,ROOT/'dashboard/latency_template.html'])
    paths=sorted(files);hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    save_json(mp,dict(version=VERSION,files=hashes,dependencies='Install requirements-project.txt; frozen prior ZIPs retained because provenance verification hashes them'))
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
        z.write(mp,mp.name)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    obj=dict(file=path.name,bytes=path.stat().st_size,files=len(hashes)+1,sha256=sha(path),CRC_and_all_SHA256_verified=True)
    save_json(ROOT/f'package_{VERSION}.json',obj);print(json.dumps(obj,indent=2))
