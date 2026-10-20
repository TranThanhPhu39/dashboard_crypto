"""Evidence-led supplement; frozen baseline report and dashboard stay intact."""
from src.evaluation.robustness_common import *
import html, zipfile, re

def read(name):return pd.read_csv(OUT/name)

def md(frame):
    def value(v):return 'N/A' if pd.isna(v) else f'{v:.6g}' if isinstance(v,(float,np.floating)) else str(v)
    return '| '+' | '.join(frame.columns)+' |\n| '+' | '.join(['---']*len(frame.columns))+' |\n'+'\n'.join('| '+' | '.join(value(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None))

def inline(text):
    s=html.escape(text)
    s=re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'`(.*?)`',r'<code>\1</code>',s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    return s

def render_markdown(text):
    blocks=[]
    for block in text.split('\n\n'):
        if block.startswith('!['):
            label=block.split(']')[0][2:];url=block.split('(')[1].split(')')[0]
            blocks.append(f'<figure><img alt="{html.escape(label)}" src="{html.escape(url)}"></figure>')
        elif block.startswith('```'):
            blocks.append('<pre>'+html.escape('\n'.join(block.splitlines()[1:-1]))+'</pre>')
        elif block.startswith('| '):
            lines=block.splitlines();cells=lambda row:[v.strip() for v in row.strip('|').split('|')]
            blocks.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(v)+'</th>' for v in cells(lines[0]))+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(v)+'</td>' for v in cells(line))+'</tr>' for line in lines[2:])+'</tbody></table></div>')
        elif block.startswith('#'):
            level=len(block)-len(block.lstrip('#'));blocks.append(f'<h{level}>'+inline(block[level:].strip())+f'</h{level}>')
        else:blocks.append('<p>'+inline(block)+'</p>')
    return '\n'.join(blocks)

def findings():
    a=read('monetary_sensitivity.csv');arch=read('joint_VAR_ARCH.csv');w=read('joint_VAR_whiteness.csv')
    counts={s:int((g.qvalue_bh_scenario<.05).sum()) for s,g in a.groupby('scenario')}
    loo=a[a.scenario.str.startswith('omit_202')]
    capture=json.loads((OUT/'prospective_capture_status.json').read_text(encoding='utf-8'))
    return dict(monetary_BH_counts_per_60=counts,loo_sign_change_rows=int(loo.sign_change.sum()),
                loo_sign_change_pairs=int(loo.loc[loo.sign_change,['asset','horizon_days']].drop_duplicates().shape[0]),
                ARCH_significant_of_60=int((arch.qvalue_bh_60<.05).sum()),
                whiteness_raw_p20_reject_of_6=int(((w.test_lags==20)&(w.pvalue<.05)).sum()),
                whiteness_BH18_q20_reject_of_6=int(((w.test_lags==20)&(w.qvalue_bh_18<.05)).sum()),
                capture=capture)

def build_figures(a,c):
    fig,axes=plt.subplots(1,2,figsize=(12,4.3))
    for asset,ax in zip(['btc','eth'],axes):
        g=a[a.asset==asset];b=g[g.scenario=='baseline'];loo=g[g.scenario.str.startswith('omit_202')]
        lo=loo.groupby('horizon_days').difference_pct.min();hi=loo.groupby('horizon_days').difference_pct.max()
        ax.fill_between(lo.index,lo.values,hi.values,color='#a4c8d2',alpha=.65,label='Range over 9 single-event deletions (not CI)')
        ax.plot(b.horizon_days,b.difference_pct,label='Frozen baseline',color='#096b93')
        covid=g[g.scenario=='omit_COVID_Mar_Apr_2020']
        ax.plot(covid.horizon_days,covid.difference_pct,'--',label='Omit Mar-Apr 2020: only 3 stress events',color='#b45c77')
        ax.axhline(0,color='#888',lw=.7);ax.set_title(asset.upper()+' stress minus calm')
        ax.set_xlabel('Calendar days after announcement day');ax.set_ylabel('Cumulative return percentage points / +10bp')
    axes[0].legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'figures/monetary_sensitivity.png');plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,6),sharex=True)
    for i,y in enumerate(['us2y','us10y']):
        for j,regime in enumerate(['full','pre2020','post2020']):
            ax=axes[i,j];g=c[(c.yield_variable==y)&(c.regime==regime)&(c.current_equation=='btc_return_pct')&(c.past_equation=='btc_return_pct')]
            ax.plot(g.lag,g.correlation,label='BTC residual autocorrelation')
            ax.plot(g.lag,g.squared_correlation,label='Squared residual autocorrelation')
            ax.axhline(0,color='#888',lw=.7);ax.set_title(y.upper()+' / '+regime);ax.set_xlabel('Session lag')
    axes[0,0].legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'figures/joint_residual_acf.png');plt.close(fig)

def build():
    init();f=findings();save_json(OUT/'headline_findings.json',f)
    a=read('monetary_sensitivity.csv');c=read('joint_VAR_residual_correlations.csv')
    build_figures(a,c)
    counts=pd.DataFrame([dict(scenario=k,BH_below_005_of_60=v) for k,v in f['monetary_BH_counts_per_60'].items()])
    support=read('monetary_support.csv');s30=support[(support.horizon_days==30)&(support.subset=='stress')]
    top=read('monetary_event_influence.csv');top=top[(top.horizon_days==1)&(top.stress==1)].sort_values(['asset','interaction_information_share'],ascending=[True,False]).groupby('asset').head(3)
    white=read('joint_VAR_whiteness.csv');white=white[white.test_lags==20]
    cap=f['capture']
    text=f'''# Chủ đề 9 — Kiểm tra độ vững và phần dư, 19/10/2026

Đây là phân tích bổ sung hậu nghiệm. Giữ nguyên baseline, dữ liệu, 40 model artifacts, báo cáo/dashboard và ZIP cũ. Không chọn lại lag, không thay shock, không fit thêm GARCH/TVP, không dùng kết quả này để chọn mô hình theo p-value.

## Kết luận có thể sử dụng

**Monetary stress phụ thuộc đáng kể vào sự kiện.** Baseline có {f['monetary_BH_counts_per_60']['baseline']}/60 stress−calm differences đạt BH q<0,05; bỏ riêng 03/03/2020 chỉ còn {f['monetary_BH_counts_per_60']['omit_2020-03-03']}/60. Trong 9 phép bỏ từng sự kiện có {f['loo_sign_change_pairs']}/60 cặp asset–horizon đổi dấu ít nhất một lần. Đây là bằng chứng độ nhạy với quan sát, không phải lý do loại sự kiện khỏi baseline.

**Bỏ COVID không xác nhận độ vững.** Loại mọi event date trong 01/03–30/04/2020 để lại 3 stress events. Dù số hệ số đạt BH có thể tăng (bản này {f['monetary_BH_counts_per_60']['omit_COVID_Mar_Apr_2020']}/60), mẫu quá mỏng, leverage và sai số chuẩn tiệm cận có thể gây ấn tượng sai về độ chắc chắn. Không gọi đây là 50 phát hiện độc lập; các horizon dùng phần lớn cùng sự kiện và outcome chồng lấn.

**Joint VAR có cả vấn đề ở mean và variance.** {f['whiteness_raw_p20_reject_of_6']}/6 hệ bác bỏ whiteness lag20 ở p<0,05; {f['whiteness_BH18_q20_reject_of_6']}/6 sau BH family18. {f['ARCH_significant_of_60']}/60 ARCH LM tests đạt BH family60. Không bác bỏ whiteness pre2020 không chứng minh phần dư độc lập. ARCH phụ thuộc mean đã fit, và cũng có thể phản ánh sai đặc tả/breaks/outliers. Chẩn đoán này chưa xác nhận GARCH hay một cơ chế biến động cụ thể. VAR/recursive IRF tiếp tục là đối chiếu; LP/FOMC/rolling vẫn là trọng tâm, với các giới hạn suy luận đã nêu.

## Thiết kế monetary và cách đọc

Tái lập nguyên mô hình pooled interaction của baseline ở 2 tài sản × horizon 1–30: outcome là tổng log return (%) D+1…D+h, loại ngày thông báo; controls prior return, prior volatility và prior VIX; giữ stress rule và shock STMT. Full-sample monetary null cũ không đổi. Shock dương +10bps là đơn vị chuẩn hóa, vượt positive surprise lớn nhất quan sát (~6,094bps); không coi hệ số như forecast cho một sự kiện nằm trong hỗ trợ dữ liệu.

Sau đó bỏ từng trong 9 stress event dates; và một scenario bỏ toàn bộ event dates tháng 3–4/2020. Không sửa returns/controls hay loại outcome của các event khác. HAC5 finite correction trên chuỗi event còn lại; xóa một row thay đổi event-row adjacency, nên các p/q của deletion chỉ mang tính chẩn đoán. BH riêng mỗi scenario60, không bảo vệ toàn bộ các scenario đã xem; không có finite-sample certification. Ngưỡng ít hơn10 stress events chỉ là cờ hỗ trợ thưa, không phải định lý hiệu lực. Không thay baseline bằng scenario đẹp nhất.

![Monetary sensitivity](figures/monetary_sensitivity.png)

Dải tô là min–max của 9 ước lượng sau bỏ từng sự kiện, **không phải confidence interval**. CI trong bảng/dashboard là HAC pointwise xấp xỉ, không simultaneous và không khắc phục sparse-state inference.

{md(counts)}

Partialled-interaction information share đo tỷ trọng z²/sum(z²), z là monetary×stress sau khi chiếu lên mọi regressor còn lại. Leverage, Cook và residual chuẩn hóa là mô tả, không dùng ngưỡng để tự động bỏ quan sát. Ba stress events có information share cao nhất mỗi tài sản ở h=1:

{md(top[['asset','date_utc','monetary_10bps','leverage','interaction_information_share','cooks_distance']])}

Outcome overlap tại h=30:

{md(s30)}

Overlap components là số nhóm interval giao nhau, **không phải số quan sát độc lập/effective n**. Chín stress events có 11 cặp outcome giao nhau và 4 nhóm interval ở h30; 60 horizon coefficients không phải 60 replication độc lập.

## Đúng sáu reduced-form joint VAR

Khôi phục đúng response dates, lag, thứ tự crypto_first, hệ số và covariance của từng fit frozen. Không chạy lại lag search và không gộp chẩn đoán cũ của 10 VAR đơn tài sản. Lưu residual theo session date, fitted/observed values, Pearson own/cross-equation correlations và squared correlations lag1–40, adjusted system whiteness lag20/30/40, ARCH LM5/10 với ddof bằng số regressor mỗi phương trình (gồm intercept). Correlation graphs là mô tả, không có 40×25 kiểm định điểm lẻ. BH60 ARCH và BH18 whiteness tách family.

{md(white[['yield_variable','regime','pvalue','qvalue_bh_18']])}

![Joint residual ACF](figures/joint_residual_acf.png)

Heteroskedasticity có thể làm CI Gaussian/homoskedastic IRF thiếu tin cậy; serial correlation còn lại đặt vấn đề với mean specification. HAC/variance modeling không tự sửa mean. Một số cross-lag correlation nhỏ vẫn có thể tạo system rejection khi mẫu lớn. Không diễn giải ARCH rejection như lỗi tải data. Không dùng asymptotic p-value nhỏ để khẳng định causal identification.

## Snapshot thật và giới hạn triển khai prospective

Đã capture {cap['sources_ok']}/{cap['sources_total']} nguồn thành công. Lưu nguyên response bytes, URL, request/retrieval UTC thực tế, HTTP Date/Last-Modified nếu có và SHA256 tại `{cap['capture_manifest']}`. Public FRED hiện tại là current vintage được lưu từ bây giờ, **không phải ALFRED historical PIT**. Latest observation date khác nhau do lịch công bố, không tự động là lỗi.

Forecast origin gần nhất: `{cap['next_origin_utc']}`; cutoff24h yêu cầu `{cap['required_information_cutoff_utc']}`. Capture hôm nay xảy ra sau cutoff nên không đủ điều kiện. Riêng điều kiện capture+24h sớm nhất đạt tại `{cap['earliest_origin_using_this_capture_24h']}`; **mốc này chưa bảo đảm đủ feature dates theo convention đã chốt**. Snapshot cũ hơn có thể làm own-feature thêm trễ. Việc yêu cầu actual receipt≤cutoff và đúng freshest lag ở cutoff UTC midnight có thể không tương thích với latency công bố sau fixing. Không backdate, không tự thay lag hoặc nới buffer. Chưa log prediction; chưa có điểm OOS mới.

Phần còn cần quyết định trước triển khai dự báo thật: protocol phiên bản mới dành cho publication latency, với feature age rõ ràng và kiểm tra lại so sánh cùng mẫu. Đây là thay đổi timing so với bản đã chốt nên chỉ thực hiện sau khi người dùng đồng ý. Chưa cài scheduler. Dùng `collect` để lưu snapshot thêm; giữ cả failures/missing days. Logger envelope cũ vẫn giữ nguyên, không dùng nó để ghi giả prediction từ snapshot này.

## Tái lập và bằng chứng

```powershell
py -3.11 run_robustness.py diagnostics
py -3.11 run_robustness.py collect
py -3.11 run_robustness.py product
py -3.11 run_robustness.py validate
node tests/validate_robustness_dashboard.cjs
node tests/preview_robustness.cjs
py -3.11 run_robustness.py package
```

`collect` tạo capture mới theo thời điểm chạy, nên raw bytes/timestamps và trạng thái prospective có thể thay đổi; `diagnostics` tái lập từ frozen inputs. Không dùng `all` để giả lập dữ liệu tương lai. Bundle bổ sung có manifest riêng; cần giải nén giữ cấu trúc thư mục. [Dashboard chẩn đoán](dashboard.html), [bản chính giữ nguyên](../blueprint_20261019/report.html), [đối chiếu nghiên cứu và tài liệu gốc](../issue_literature_review_20261019.md), [validation](independent_validation.json), [thiết kế khóa](../../../config/robustness_20261019.json).

Kết quả vẫn là nghiên cứu mô phỏng học thuật; không phải khuyến nghị đầu tư, chưa nhận diện pure monetary policy, chưa chứng nhận whole-feed PIT hoặc một untouched OOS mới.
'''
    (OUT/'report.md').write_text(text,encoding='utf-8')
    body=render_markdown(text)
    css='body{font:16px/1.6 system-ui,sans-serif;margin:30px auto;padding:0 20px;max-width:1100px;color:#173344}img{width:100%;height:auto}table{display:block;overflow-x:auto;border-collapse:collapse;max-width:100%;font-size:13px}td,th{padding:7px;border-bottom:1px solid #cad6dc}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#096b93}code{overflow-wrap:anywhere}'
    (OUT/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Topic09 — Robustness</title><style>'+css+'</style><body><p><a href="dashboard.html">Mở dashboard chẩn đoán</a></p>'+body+'</body></html>',encoding='utf-8')
    payload=dict(monetary=a.to_dict('records'),correlations=c.to_dict('records'),arch=read('joint_VAR_ARCH.csv').to_dict('records'),whiteness=read('joint_VAR_whiteness.csv').to_dict('records'),findings=f)
    # Nulls (omitted_event for non-LOO rows) are legitimate; never embed NaN JS tokens.
    clean=json.loads(pd.Series([payload]).to_json(orient='values',double_precision=15))[0]
    template=(ROOT/'dashboard/robustness_template.html').read_text(encoding='utf-8')
    (OUT/'dashboard.html').write_text(template.replace('__PAYLOAD__',json.dumps(clean,ensure_ascii=False,allow_nan=False)),encoding='utf-8')
    print('Supplement report, figures, dashboard and headline findings generated.',flush=True)

def package():
    """Supplement with all frozen dependencies; old bundles are never overwritten."""
    check_protected()
    path=ROOT/'topic09_robustness_20261019.zip'
    assert not path.exists(),'Bundle exists; choose a new version instead of overwriting it.'
    snap=json.loads((OUT/'source_snapshot.json').read_text(encoding='utf-8'))
    files={ROOT/p for p in snap['protected_sha256']}
    files.update(p for p in OUT.rglob('*') if p.is_file())
    files.update(p for p in RAW.rglob('*') if p.is_file())
    files.update(p for p in (ROOT/'src').rglob('*.py'))
    files.update(p for p in (ROOT/'tests').glob('*') if p.is_file())
    files.update(p for pattern in ['*.py','*.cjs','requirements*.txt','manifest*.json'] for p in ROOT.glob(pattern) if p.is_file())
    files.update(p for p in (ROOT/'paper').glob('*.md'))
    files.update([ROOT/'README.md',ROOT/'run_robustness.py',CONFIG,ROOT/'dashboard/robustness_template.html',ROOT/'research_common.py',ROOT/'research_completion.py',ROOT/'requirements-project.txt',ROOT/'requirements-research.txt'])
    paths=sorted(files)
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    manifest=ROOT/'manifest_robustness_20261019.json'
    save_json(manifest,dict(version=VERSION,files=hashes,scope='Supplement and its frozen inputs; dependencies .research_deps excluded, install requirements. Old ZIPs retained as protected artifacts.'))
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
        z.write(manifest,manifest.name)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name,digest in hashes.items():
            import hashlib
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    save_json(ROOT/'package_robustness_20261019.json',dict(file=path.name,bytes=path.stat().st_size,sha256=sha(path),files=len(hashes)+1,CRC_and_all_SHA256_verified=True))
    print('Supplement bundle verified:',path.name,path.stat().st_size,flush=True)
