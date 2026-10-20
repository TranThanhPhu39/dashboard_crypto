"""Build the current report/dashboard with the approved completion extension."""
from research_common import *
from research_completion import OUT
import html
import re


def read(name):return pd.read_csv(OUT/(name+'.csv'))
def records(f):return json.loads(f.to_json(orient='records',double_precision=15))
def ht(f):return '<div class="table-wrap">'+f.to_html(index=False,border=0,float_format=lambda x:f'{x:.6g}',na_rep='N/A')+'</div>'
def md(f):
    def val(x):return 'N/A' if pd.isna(x) else f'{x:.6g}' if isinstance(x,(float,np.floating)) else str(x)
    return '| '+' | '.join(f.columns)+' |\n| '+' | '.join(['---']*len(f.columns))+' |\n'+'\n'.join('| '+' | '.join(val(v) for v in row)+' |' for row in f.itertuples(index=False,name=None))


def figures(tests,state):
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    for ax,target in zip(axes,['return','squared_return']):
        q=tests[(tests.target==target)&~((tests.base=='common_own')&(tests.added=='common_usd'))].copy()
        labels=q.asset.str.upper()+' / '+q.model.str.replace('gradient_boosting','Boost').str.replace('elastic_net','EN')+' / '+q.base.str.replace('common_macro','USD').str.replace('common_own','Macro 2019+').str.replace('long_own','Macro long')
        ax.errorbar(q.mean_loss_added_minus_base,np.arange(len(q)),xerr=1.96*q.hac_se,fmt='o',capsize=3,markersize=4)
        ax.axvline(0,color='#999',linewidth=1);ax.set_yticks(np.arange(len(q)),labels,fontsize=8)
        ax.set_title('Return MSE' if target=='return' else 'Variance QLIKE');ax.set_xlabel('Added minus base loss; negative = improvement')
        ax.ticklabel_format(axis='x',style='sci',scilimits=(-3,3));ax.invert_yaxis()
    fig.suptitle('Exploratory matched ablations | HAC pointwise 95% CI, BH family = 32')
    fig.tight_layout();fig.savefig(OUT/'figures/ablation.png',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
    for ax,asset in zip(axes,['btc','eth']):
        for regime,color in [('calm','#096b93'),('stress','#b45c77')]:
            q=state[(state.asset==asset)&(state.shock=='vix_change')&(state.regime==regime)].sort_values('horizon_sessions')
            ax.plot(q.horizon_sessions,q.beta_pct,marker='o',color=color,label=regime)
            ax.fill_between(q.horizon_sessions,q.lower95,q.upper95,color=color,alpha=.12)
        ax.axhline(0,color='#888',linewidth=.8);ax.set_title(asset.upper()+' / VIX +5');ax.set_xlabel('Eligible US sessions');ax.legend()
    axes[0].set_ylabel('Cumulative log return (%)')
    fig.suptitle('Existing pooled interaction model | full covariance, pointwise HAC 95% CI')
    fig.tight_layout();fig.savefig(OUT/'figures/calm_stress.png',bbox_inches='tight');plt.close(fig)


def main():
    scores=read('forecast_metrics');tests=read('ablation_tests');bench=read('benchmark_tests');selected=read('validation_selected_models')
    samples=read('sample_summary');availability=read('availability_register');state=read('state_responses');episodes=read('historical_analogues');diag=read('variance_diagnostics')
    figures(tests,state)
    significant=bench[bench.qvalue_bh<.05];better=int((significant.mean_loss_added_minus_base<0).sum());worse=int((significant.mean_loss_added_minus_base>0).sum())
    findings=[
        'LP/HAC, FOMC và rolling giữ kết quả đã lưu: quan hệ có điều kiện, chưa xác lập nhân quả; VAR tiếp tục ở phụ lục chẩn đoán.',
        'Timing forecasting: thêm buffer 24 giờ cho toàn bộ bộ thông tin, kiểm tra khả dụng nhãn khi fit; target vẫn là ngày UTC kế tiếp. Nguồn thiếu publication timestamps vẫn là proxy.',
        'Đã so crypto-only → macro không USD trên mẫu dài; crypto-only → macro không USD → macro có USD trên mẫu chung từ 2019, giữ cùng ngày/target trong mỗi phép so.',
        f'{int((tests.qvalue_bh<.05).sum())}/{len(tests)} ablation đạt BH q<0,05. Chưa thấy cải thiện dự báo bền của macro/USD trong các cấu hình và mẫu này.',
        f'Đối chiếu benchmark riêng: {better} so sánh tốt hơn và {worse} kém hơn có q<0,05 trong family 40; không đồng nhất có ý nghĩa với tốt hơn.',
        f'Variance dùng log-link, không ép prediction floor: min={diag.minimum.min():.3g}; {(diag.count_le_1e12>0).sum()} cấu hình có dự báo ≤1e−12. Điều này xử lý vấn đề dấu/floor, không bảo đảm forecast chính xác.',
        'Test 2025+ đã từng được xem: toàn bộ kết quả mới là exploratory; chưa có một test mới thực sự chưa từng được xem.',
    ]
    sections=[]
    def section(title,text,frame=None,picture=None):sections.append((title,text,frame,picture))
    section('Tóm tắt', '\n'.join('- '+x for x in findings))
    section('1. Phạm vi và các kết quả giữ nguyên',
        'Bản hiện tại hoàn thiện timing, macro ablation, variance dương và sản phẩm theo phương án đã đồng ý. Không MOVE; không nối USD goods-only vào broad USD. Dữ liệu snapshot kết thúc 15/10/2026. Không tải thêm dữ liệu, không thay panel lịch sử hoặc các kết quả VAR/LP/FOMC/rolling cũ.\n\nLP/HAC, FOMC và rolling vẫn là trục nghiên cứu chính. LP đo tổng log return t…t+h trên eligible US sessions, không phải ngày lịch. FOMC dùng Eastern Time → UTC có DST, khác dữ liệu daily. Bản LP/FOMC trước được giữ nguyên để tra toàn bộ bảng số; các câu nói “chưa có macro ablation” trong snapshot đó là trạng thái trước lượt này.\n\nVIX +5 cùng phiên đi kèm BTC −2,687%, ETH −3,879% log return có điều kiện. 0/80 interaction pre/post hoặc stress đạt BH. FOMC STMT âm có ý nghĩa trong cửa sổ −5/+25 của extension 2017–2022; kết quả phụ thuộc cửa sổ/thước đo. Không kết luận Fed gây ra mức giảm xác định hay institutionalization không ảnh hưởng.')
    section('2. Timing: xử lý bảo thủ và giới hạn còn lại',
        'Row t dự báo tại 00:00 UTC t+1 cho return của UTC day t+1, kết thúc 00:00 UTC t+2. Feature lấy từ original information row t−1, whose reference close là 00:00 UTC t: buffer 24 giờ. Dịch trên lịch đủ 7 ngày/tuần trước khi drop missing, không dịch theo dòng đủ dữ liệu. Các market lag1 proxies cũ vì vậy trở thành lag2 theo ngày lịch.\n\nMacro chỉ nhận vintage có ngày không sau information row t−1. Các thông tin quan sát, ngày vintage và thời điểm tham chiếu được lưu cùng panel nhưng không vào feature matrix. Nhãn train/development yêu cầu label close +24h không sau origin validation/test đầu tiên; có một nhãn ở ranh giới train bị loại.\n\nBuffer 24h là giả định bảo thủ về độ trễ; không thay thế archive giờ công bố. Giá crypto hồi cứu và VIX/S&P/gold historical proxies vẫn có thể khác feed thực sự biết trong quá khứ. Vì thế không gắn nhãn whole-feed PIT hoặc khẳng định “đã loại bỏ mọi look-ahead”. ALFRED real-time periods giải quyết revisions theo ngày, không chứng nhận exact intraday provider delivery.',availability)
    section('3. Mẫu ghép cặp và câu hỏi forecasting',
        'Mỗi tài sản có long_own (3 own features) và long_macro (thêm 8 macro, không USD) trên cùng complete-case dates. Từ 2019 có common_own, common_macro và common_usd (thêm USD thứ 9). Giữ cùng origins/targets/splits trong từng phép so; own-only cũng dùng lịch đủ macro để tránh quy sample selection thành tác dụng macro. Không suy rộng kết quả sang tất cả ngày crypto.\n\nTrain theo target date trước 2023; validation 2023–2024; test 2025+ gồm 447 eligible origins. Mốc đầu common thay đổi sau buffer, không nội suy phần USD trước 2019. Mẫu dài và mẫu common khác training history nên chỉ so USD trong mẫu common. Metadata/split/target không được dùng làm predictor.',samples)
    section('4. Mô hình, lựa chọn và variance dương',
        'Giữ historical mean, zero-return (target return) hoặc trailing30 variance, Elastic Net và histogram gradient boosting. Lưới tham số và lịch chọn được khóa trong design.json trước khi fit. Chọn bằng validation MSE cho return và QLIKE cho squared return; refit train+validation một lần khi nhãn đã đủ thời gian. Không chọn lại winner theo test.\n\nVariance boosting dùng Poisson quasi-deviance với log-link trên squared return chia mean của fitting labels. Đây là loss cho conditional mean không âm, không giả định squared return có phân phối đếm Poisson. Elastic Net fit log(y/fitting_mean + 1e−12), chuyển ngược bằng exp và smearing từ fitting residuals. Smearing toàn cục là xấp xỉ khi heteroskedastic; không đảm bảo unbiased conditional variance. Không ép prediction về 1e−12. Mean scale và smearing chỉ dùng fit labels.\n\nSquared return là proxy nhiễu cho variance, không phải realized variance intraday. Các mô hình return giữ loss cũ. Việc đổi timing, purge và variance link đồng thời làm kết quả mới khác baseline; không quy toàn bộ thay đổi hiệu năng cho một yếu tố duy nhất.',diag)
    section('5. Kết quả ablation: toàn bộ macro và USD gia tăng',
        f'Có 32 so sánh learned-model: 2 tài sản × 2 targets × 2 thuật toán × 4 cặp feature sets. Mean loss added−base âm là tốt hơn; QLIKE có thể âm vì bỏ hằng số, giá trị thấp hơn tốt hơn. BH trên cả 32; {int((tests.qvalue_bh<.05).sum())} đạt q<0,05. Ví dụ BTC long Elastic Net variance có raw p≈0,0059 nhưng q≈0,189; không báo cáo nó như bằng chứng chắc chắn.\n\nHAC lag5 trên thứ tự eligible origins chỉ là diagnostic xấp xỉ: nested forecasts, ngày không đều, nhiều quyết định nghiên cứu đã diễn ra. Không coi BH trong lượt này là sửa multiple testing cho toàn bộ lịch sử dự án. Các so sánh chung dữ liệu không phải thí nghiệm độc lập.',tests[['asset','target','model','base','added','mean_loss_added_minus_base','hac_se','pvalue','qvalue_bh']], 'figures/ablation.png')
    section('6. Benchmark và lựa chọn từ validation',
        f'Benchmark tests có family riêng 40; {better} so sánh learned tốt hơn và {worse} kém hơn benchmark sau BH. Dấu loss phải được đọc cùng p/q. Dự báo hòa đến độ chính xác máy được ghi numerical_tie, loss difference=0, SE=0, p=1 thay vì kiểm định nhiễu làm tròn. Đây là sửa tính toán, không thay fit hoặc tham số.\n\nBảng dưới giữ winner validation của từng cấu hình, kể cả khi test kém. Không so hai winner dùng thuật toán khác nhau để tách riêng tác dụng macro; các bảng ablation giữ cùng thuật toán mới trả lời câu hỏi đó.',selected[['asset','variant','target','model','n_test','validation_objective','rmse','mae','qlike']])
    section('7. Calm/Stress và sự kiện lịch sử tương tự',
        'Tái lập đúng pooled stress-interaction model đã lưu ở h=0,1,5,10,20. Calm=β; stress=β+δ; Var(stress)=Var(β)+Var(δ)+2Cov(β,δ). Kiểm tra ma trận HAC độc lập xác nhận toàn bộ 40 covariance blocks. Các δ/SE khớp kết quả cũ; đây không phải model regime mới.\n\nCI là pointwise 95%, không phải simultaneous bands. Không lấy CI overlap hoặc một state có ý nghĩa để kết luận khác biệt hai state; kiểm định δ cũ 0/80 sau BH gồm cả pre/post vẫn giữ. Stress chỉ có 9 phiên trước 2020 trong core panel. Dashboard dùng 5 horizon có sẵn của interaction, không nội suy 2/30.\n\nMục lịch sử chọn 5 shock quan sát gần reporting magnitude nhất trong từng state; tránh các cửa sổ outcome chồng lấp trong mỗi danh sách. Bảng trả về return thực tế cộng dồn, không phải fitted response, không giữ cố định các shock khác và không chứng minh nhân quả. Có thể có sự kiện trước/sau ngày đang xem vì đây là công cụ tra cứu toàn mẫu lịch sử.',state[state.horizon_sessions.isin([0,20])][['asset','shock','regime','horizon_sessions','beta_pct','lower95','upper95','n_state']], 'figures/calm_stress.png')
    section('8. Phần đã xử lý và phần chưa thể xác nhận',
        'Đã bổ sung ablation trực tiếp cho RQ5, buffer/timing register và label purge, variance predictor dương không floor, Calm/Stress có đúng covariance và historical analogues. Các file dữ liệu, kết quả và ZIP trước lượt này có hash giữ nguyên.\n\nCòn lại: chưa có publication archive đầy đủ, chưa có một test mới chưa từng được xem; chưa có nhận diện cú sốc chính sách thuần túy. VAR vẫn bác bỏ whiteness và có ARCH/influence sensitivity; giữ ở phụ lục, không tiếp tục sửa để ép kiểm định đạt. LP/HAC không tự giải quyết confounding hoặc mọi sai đặc tả.\n\nKết luận phù hợp: các liên hệ lịch sử và phản ứng sự kiện có điều kiện, chưa thấy macro/USD cải thiện forecast bền theo thiết kế đã xét. Không diễn giải null như chứng minh không có tác dụng. Chưa thể đánh dấu checklist “không look-ahead tuyệt đối” hoặc “fully real-time” là đã được chứng nhận.')
    links='''<p><a href="dashboard.html">Dashboard hiện tại</a> · <a href="../synthesis/report.html">LP/FOMC/rolling đầy đủ (snapshot trước)</a> · <a href="../var_residual_diagnostics/report.html">VAR diagnostics</a> · <a href="../literature_review.md">Literature review</a> · <a href="design.json">Thiết kế khóa</a> · <a href="independent_validation.json">26 kiểm tra độc lập</a></p><p><a href="ablation_tests.csv">32 ablation tests</a> · <a href="benchmark_tests.csv">40 benchmark tests</a> · <a href="forecast_metrics.csv">Toàn bộ 80 metrics</a> · <a href="state_responses.csv">Calm/Stress</a> · <a href="historical_analogues.csv">400 ví dụ lịch sử</a> · <a href="availability_register.csv">Timing register</a> · <a href="numerical_tie_note.json">Ghi chú numerical ties</a></p><p>Nguồn phương pháp: <a href="https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html">scikit-learn: Poisson loss/log-link</a> · <a href="https://fred.stlouisfed.org/docs/api/fred/realtime_period.html">FRED real-time periods</a> · <a href="https://fred.stlouisfed.org/docs/api/fred/release_dates.html">FRED: release date khác provider availability</a>.</p>'''
    css='body{margin:0;background:#edf3f6;color:#183446;font:16px/1.65 system-ui}main{max-width:1220px;margin:auto;padding:36px;background:white}h1{line-height:1.2}h2{color:#096b8c;margin-top:36px}.table-wrap{overflow:auto}table{border-collapse:collapse;font-size:12px;white-space:nowrap}td,th{padding:8px;border-bottom:1px solid #d9e5ec;text-align:right}th{background:#edf4f7}img{width:100%;height:auto}a{color:#096b8c}.lead{padding:18px;background:#fff5e7;border-left:4px solid #bc893d}code{font-size:13px}@media(max-width:700px){main{padding:18px}h1{font-size:26px}}'
    body='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chủ đề 9 — bản hoàn thiện thực nghiệm</title><style>'+css+'</style><main><p>CRYPTO FINANCE LAB / RESEARCH 09</p><h1>Điều kiện tài chính toàn cầu và BTC/ETH</h1><p class="lead">LP/HAC · FOMC · Rolling · Macro ablation · Variance dương<br>Snapshot đến 15/10/2026. Forecasting mới là exploratory vì test cũ đã được xem.</p>'+links
    text='# Chủ đề 9 — bản hoàn thiện thực nghiệm\n\nForecasting mở rộng: exploratory, không phải test mới chưa từng được xem.\n\n'
    for title,paragraphs,frame,picture in sections:
        body+='<section><h2>'+html.escape(title)+'</h2>'
        if paragraphs.startswith('- '):body+='<ul>'+''.join('<li>'+html.escape(p[2:])+'</li>' for p in paragraphs.splitlines())+'</ul>'
        else:body+=''.join('<p>'+html.escape(p)+'</p>' for p in paragraphs.split('\n\n'))
        if frame is not None:body+=ht(frame)
        if picture:body+='<img src="'+picture+'" alt="'+html.escape(title)+'">'
        body+='</section>';text+='## '+title+'\n\n'+paragraphs+'\n\n'
        if frame is not None:text+=md(frame)+'\n\n'
        if picture:text+='!['+title+']('+picture+')\n\n'
    commands='py -3.11 research_completion.py prepare\npy -3.11 research_completion.py fit\npy -3.11 research_completion.py tests\npy -3.11 research_completion.py stress\npy -3.11 validate_completion.py\npy -3.11 build_completion.py\nnode validate_completion_dashboard.cjs\nnode preview_completion.cjs\npy -3.11 package_completion.py'
    body+='<h2>Tái lập và nguồn</h2><pre style="overflow:auto"><code>'+html.escape(commands)+'</code></pre>'+links+'</main></html>'
    text+='## Tái lập và nguồn\n\n```powershell\n'+commands+'\n```\n\n'+links+'\n'
    (OUT/'report.html').write_text(body,encoding='utf-8');(OUT/'report.md').write_text(text,encoding='utf-8')
    # Reuse the frozen primary dashboard; only this new HTML receives the extension.
    old=(RESULTS/'synthesis/dashboard.html').read_text(encoding='utf-8')
    payload=json.loads(re.search(r'const DATA=(.*?);\nconst el=',old,re.S).group(1))
    payload.update(states=records(state),analogues=records(episodes),ablation=records(tests),benchmark_tests=records(bench),selected=records(selected),variance_diagnostics=records(diag),findings=findings,completion_design=json.loads((OUT/'design.json').read_text(encoding='utf-8')))
    template=(ROOT/'synthesis_dashboard_template.html').read_text(encoding='utf-8')
    template=template.replace('<option value="post2020">Từ 2020</option></select>','<option value="post2020">Từ 2020</option><option value="calm">Calm (pooled interaction)</option><option value="stress">Stress (pooled interaction)</option></select>',1)
    template=template.replace('<b>448</b>','<b>447</b>').replace('Forecast USD','Forecast macro').replace('Chủ đề 9 · LP, FOMC và rolling','Chủ đề 9 · Macro, timing và regime')
    template=template.replace('Snapshot daily đến 15/10/2026; phần mở rộng giữ riêng và công khai giới hạn.','Snapshot đến 15/10/2026. Forecasting mới có buffer 24 giờ và là exploratory; test cũ đã được xem.')
    template=template.replace('<a href="#forecast">','<a href="#analogues">Sự kiện lịch sử</a><a href="#forecast">',1)
    template=template.replace('Controls cùng phiên và 5 lags của toàn hệ; HAC maxlags=max(5,h+1).','Controls cùng phiên và 5 lags của toàn hệ; HAC maxlags=max(5,h+1).')
    analog='''<section class="panel" id="analogues"><div class="section-id">Tra cứu lịch sử</div><h2>Các khoảng có shock quan sát tương tự</h2><p>5 shock gần quy mô đang chọn nhất, tránh outcome chồng lấp trong mỗi danh sách. Return thực tế chưa điều chỉnh các shock khác; đây là mô tả lịch sử toàn mẫu.</p><div class="controls"><label>Tài sản<select id="analogueAsset"><option value="btc">Bitcoin</option><option value="eth">Ethereum</option></select></label><label>Biến<select id="analogueShock"><option value="vix_change">VIX +5 điểm</option><option value="usd_return_pct">USD +1%</option><option value="us2y_change_bps">2Y +10 bps</option><option value="us10y_change_bps">10Y +10 bps</option></select></label><label>Trạng thái<select id="analogueState"><option value="calm">Calm</option><option value="stress">Stress, VIX trước &gt;30</option></select></label><label>Horizon<select id="analogueH"><option>0</option><option>1</option><option>5</option><option>10</option><option>20</option></select></label></div><div class="table-wrap" id="analogueTable"></div><p class="note">Khoảng t đo giữa hai common observed levels nên có thể bao gồm cuối tuần/lễ. Quy mô shock chỉ dùng để xếp độ gần; không scale return thực tế thành phản ứng giả định.</p></section>'''
    template=template.replace('<section class="panel" id="fomc">',analog+'\n<section class="panel" id="fomc">',1)
    forecast='''<section class="panel" id="forecast"><div class="section-id">04 / Forecasting mở rộng</div><h2>Crypto-only → macro → USD</h2><p>Buffer thông tin 24 giờ; train/validation/test theo target date, 447 test origins ghép cặp. Đây là phân tích exploratory trên test đã được xem.</p><div class="controls"><label>Target<select id="target"><option value="return">Next UTC-day return</option><option value="squared_return">Next UTC-day squared return</option></select></label><label>Mô hình<select id="forecastModel"><option value="elastic_net">Elastic Net</option><option value="gradient_boosting">Gradient boosting</option></select></label><label>So sánh<select id="forecastComparison"><option value="0">Mẫu dài: thêm macro không USD</option><option value="1">2019+: thêm macro không USD</option><option value="2">2019+: thêm USD vào macro</option><option value="3">2019+: thêm toàn bộ macro và USD</option></select></label></div><div id="forecastTable" class="table-wrap"></div><p id="forecastNote" class="note"></p><details><summary>Winner validation, không chọn lại theo test</summary><div id="selectedTable" class="table-wrap"></div><p>Variance dùng Poisson log-link hoặc log-target + fitting-residual smearing, không prediction floor. Own-only và macro trong mỗi cặp dùng cùng eligible dates. Bảng ablation giữ cùng thuật toán; winner validation có thể khác nhau.</p></details><p class="note limit">0/32 ablation có BH q&lt;0,05. Buffer bảo thủ chưa chứng nhận whole-feed real-time; giá hồi cứu và market proxies vẫn còn. QLIKE thấp hơn tốt hơn; q kiểm định QLIKE cho variance, MSE cho return, không phải trực tiếp RMSE.</p><p><a href="ablation_tests.csv">32 paired comparisons</a> · <a href="benchmark_tests.csv">40 benchmark comparisons</a> · <a href="availability_register.csv">Timing register</a></p></section>'''
    template=re.sub(r'<section class="panel" id="forecast">.*?(?=<section class="panel" id="supplement">)',forecast+'\n',template,flags=re.S)
    # LP state curves use the same interaction model, not separately fitted regressions.
    template=template.replace('lpRows=DATA.lp.filter(',"lpRows=(['calm','stress'].includes(el('regime').value)?DATA.states:DATA.lp).filter(",1)
    template=template.replace('xmax=dateAxis?series[series.length-1].x:30;', 'xmax=series[series.length-1].x;')
    template=template.replace(': [0,5,10,20,30]', ': [0,5,10,20,30]')
    template=template.replace(':[0,5,10,20,30];', ':[0,5,10,20,30].filter(t=>t<=xmax);')
    template=template.replace("el('horizon').value=lpRows.some(r=>r.horizon_sessions===old)?String(old):'0';", "el('horizon').value=lpRows.some(r=>r.horizon_sessions===old)?String(old):'0';")
    template=template.replace("el('lpInference').textContent=`BH q=${prob(r.qvalue_bh)} · raw p=${prob(r.pvalue)}`;", "el('lpInference').textContent=['calm','stress'].includes(r.regime)?'Pooled interaction; stress CI gồm covariance β,δ. Kiểm định khác biệt xem bảng interaction.':`BH q=${prob(r.qvalue_bh)} · raw p=${prob(r.pvalue)}`;")
    template=template.replace('Controls cùng phiên và 5 lags', 'Calm/Stress dùng pooled interaction, chỉ h=0,1,5,10,20; không phải chia mẫu fit riêng. Controls cùng phiên và 5 lags',1)
    replacement='''function renderForecasts(){
 const pairs=[['long_own','long_macro'],['common_own','common_macro'],['common_macro','common_usd'],['common_own','common_usd']];
 const pair=pairs[Number(el('forecastComparison').value||0)],target=el('target').value,model=el('forecastModel').value||'elastic_net';
 const rows=DATA.ablation.filter(r=>r.target===target&&r.model===model&&r.base===pair[0]&&r.added===pair[1]);
 const num=x=>Number(x).toPrecision(5);
 el('forecastTable').innerHTML=table(['Asset','RMSE base','RMSE added','Mean loss Δ','HAC SE','BH q','n'],rows.map(r=>[r.asset.toUpperCase(),num(r.rmse_base),num(r.rmse_added),num(r.mean_loss_added_minus_base),num(r.hac_se),prob(r.qvalue_bh),r.n_pairs]));
 el('forecastNote').textContent=(target==='return'?'Loss = MSE. ':'Loss = QLIKE, không phải RMSE. ')+ 'Added − base âm là cải thiện. CI/test xấp xỉ HAC lag5; BH family 32. Không có ablation đạt q<0,05.';
 el('selectedTable').innerHTML=table(['Asset','Variant','Validation winner','Test RMSE','Test QLIKE'],DATA.selected.filter(r=>r.target===target).map(r=>[r.asset.toUpperCase(),r.variant,r.model,num(r.rmse),r.qlike===null?'N/A':num(r.qlike)]));
}
function renderAnalogues(){const rows=DATA.analogues.filter(r=>r.asset===el('analogueAsset').value&&r.shock===el('analogueShock').value&&r.regime===el('analogueState').value&&r.horizon_sessions===Number(el('analogueH').value)).sort((a,b)=>a.rank-b.rank);el('analogueTable').innerHTML=table(['Phiên shock','Đến phiên','Shock thực tế','Độ lệch / quy mô','Return thực tế (%)','Ngày lịch'],rows.map(r=>[r.date_utc,r.end_date_utc,fmt(r.shock_observed),fmt(r.distance_scaled),fmt(r.observed_cumulative_pct),r.interval_calendar_days]));}
'''
    template=re.sub(r'function renderForecasts\(\).*?(?=function renderStatic)',replacement,template,flags=re.S)
    template=template.replace("el('target').addEventListener('change',renderForecasts);", "for(const id of ['target','forecastModel','forecastComparison'])el(id).addEventListener('change',renderForecasts);for(const id of ['analogueAsset','analogueShock','analogueState','analogueH'])el(id).addEventListener('change',renderAnalogues);")
    template=template.replace('refreshRolling();renderForecasts();','refreshRolling();renderForecasts();renderAnalogues();')
    template=template.replace('Chỉ trình bày kết quả đã lưu, không tự ước lượng lại.','Forecasting mở rộng được chạy theo thiết kế khóa; LP/FOMC/rolling và VAR giữ snapshot trước.')
    template=template.replace('Thiết kế tổng hợp','Thiết kế mở rộng').replace('href="method.json"','href="design.json"')
    # CSV links originally pointed at synthesis/tables; the current directory is its sibling.
    template=template.replace('href="tables/fomc_matched.csv"','href="../synthesis/tables/fomc_matched.csv"')
    template=template.replace('href="tables/lp_full.csv"','href="../synthesis/tables/lp_full.csv"')
    (OUT/'dashboard.html').write_text(template.replace('__PAYLOAD__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/')),encoding='utf-8')
    summary=dict(findings=findings,benchmark_significant_better=better,benchmark_significant_worse=worse,ablation_significant=int((tests.qvalue_bh<.05).sum()),variance_minimum=float(diag.minimum.min()),test_origins=447)
    (OUT/'headline_findings.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print('\n'.join(findings),flush=True)


if __name__=='__main__':main()
