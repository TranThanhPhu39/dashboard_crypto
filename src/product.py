"""Current report and offline dashboard, built from explicit versioned results."""
from src.utils.project import *
import html
import re

def records(f):return json.loads(f.to_json(orient='records',double_precision=15))
def ht(f):return '<div class="table-wrap">'+f.to_html(index=False,border=0,float_format=lambda x:f'{x:.6g}',na_rep='N/A')+'</div>'
def md(f):
    def value(x):return 'N/A' if pd.isna(x) else f'{x:.6g}' if isinstance(x,(float,np.floating)) else str(x)
    return '| '+' | '.join(f.columns)+' |\n| '+' | '.join(['---']*len(f.columns))+' |\n'+'\n'.join('| '+' | '.join(value(x) for x in r)+' |' for r in f.itertuples(index=False,name=None))

def analogues(daily,monetary):
    p=panel('calendar_information.csv');samples=load('monetary_LP_samples.csv');rows=[]
    for asset in ['btc','eth']:
        for shock,scale in list(SHOCKS.items())+[('monetary',1.)]:
            for h in range(1,31):
                if shock=='monetary':
                    pool=samples[(samples.asset==asset)&(samples.horizon_days==h)].copy().rename(columns={'STMT_10bps':'shock_observed','actual_cumulative_pct':'observed_cumulative_pct','outcome_end':'end_date_utc'})
                    pool['outcome_start_utc']=pd.to_datetime(pool.outcome_start);pool['outcome_end_utc']=pd.to_datetime(pool.end_date_utc)
                else:
                    y=sum(p[asset+'_return_pct'].shift(-k) for k in range(h));pool=p[[shock,'stress']].assign(observed_cumulative_pct=y).dropna().rename(columns={shock:'shock_observed'}).reset_index();pool['end_date_utc']=pool.date_utc+pd.Timedelta(days=h-1);pool['outcome_start_utc']=pool.date_utc;pool['outcome_end_utc']=pool.end_date_utc
                for regime in ['full','calm','stress']:
                    q=pool if regime=='full' else pool[pool.stress==(regime=='stress')]
                    q=q.assign(distance=abs(q.shock_observed-scale)/scale).sort_values(['distance','date_utc'],kind='stable');used=[];rank=0
                    for _,r in q.iterrows():
                        start=pd.Timestamp(r.outcome_start_utc);end=pd.Timestamp(r.outcome_end_utc)
                        if any(not(end<a or start>b) for a,b in used):continue
                        used.append((start,end));rank+=1
                        rows.append(dict(asset=asset,shock=shock,regime=regime,horizon_days=h,rank=rank,date_utc=str(pd.Timestamp(r.date_utc).date()),end_date_utc=str(end.date()),shock_observed=float(r.shock_observed),distance_scaled=float(r.distance),observed_cumulative_pct=float(r.observed_cumulative_pct)))
                        if rank==5:break
    f=pd.DataFrame(rows);csv(f,'calendar_analogues.csv');return f

def make_figures(daily,monetary,quantile,importance):
    fig,axes=plt.subplots(2,2,figsize=(12,7),sharex=True)
    for i,asset in enumerate(['btc','eth']):
        for j,shock in enumerate(['vix_change','monetary']):
            ax=axes[i,j];base=monetary if shock=='monetary' else daily
            for regime,color in [('full','#096b93'),('calm','#5f8d59'),('stress','#b45c77')]:
                q=base[(base.asset==asset)&(base.shock==shock)&(base.regime==regime)].sort_values('horizon_days')
                ax.plot(q.horizon_days,q.beta_pct,color=color,label=regime);ax.fill_between(q.horizon_days,q.lower95,q.upper95,color=color,alpha=.08)
            ax.axhline(0,color='#888',linewidth=.8);ax.set_title(asset.upper()+' / '+('STMT +10bps, post-event days' if shock=='monetary' else 'VIX +5, information update'));ax.set_xlabel('Calendar days');ax.set_ylabel('Cumulative log return (%)');ax.legend(fontsize=8)
    fig.suptitle('Calendar LP | pointwise HAC 95% CI, conditional associations, different timing by shock');fig.tight_layout();fig.savefig(OUT/'figures/calendar_LP.png',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(14,7))
    for i,asset in enumerate(['btc','eth']):
        for j,shock in enumerate(SHOCKS):
            ax=axes[i,j];q=quantile[(quantile.asset==asset)&(quantile.shock==shock)&(quantile.regime=='full')].sort_values('tau')
            ax.plot(q.tau,q.beta_pct,marker='o');ax.fill_between(q.tau,q.lower95,q.upper95,alpha=.15);ax.axhline(0,color='#888',linewidth=.8);ax.set_title(asset.upper()+' / '+shock,fontsize=10);ax.set_xticks([.05,.5,.95]);ax.set_xlabel('Conditional quantile');ax.set_ylabel('Log return (%)')
    fig.suptitle('Quantile effects | 99 moving-block resamples, approximate percentile pointwise CI');fig.tight_layout();fig.savefig(OUT/'figures/quantile_effects.png',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,asset in zip(axes,['btc','eth']):
        q=importance[(importance.asset==asset)&(importance.variant=='common_usd')&(importance.target=='squared_return')]
        labels=q.model.str.replace('gradient_boosting','Boost').str.replace('elastic_net','EN')+' / '+q.feature_group
        ax.barh(labels,q.mean_loss_increase,color='#096b93');ax.axvline(0,color='#888',linewidth=.8);ax.set_title(asset.upper());ax.set_xlabel('Validation QLIKE increase on group permutation')
    fig.suptitle('Validation-only grouped importance | descriptive, correlated features, not causal');fig.tight_layout();fig.savefig(OUT/'figures/forecast_importance.png',bbox_inches='tight');plt.close(fig)

def build():
    init();daily=load('calendar_LP.csv');monetary=load('monetary_LP.csv');quantile=load('quantile_effects.csv');vard=load('joint_VAR_diagnostics.csv');irf=load('joint_VAR_IRF.csv')
    importance=load('validation_group_importance.csv').groupby(['asset','variant','target','model','feature_group'],as_index=False).agg(mean_loss_increase=('loss_increase','mean'),min_loss_increase=('loss_increase','min'),max_loss_increase=('loss_increase','max'),n=('loss_increase','size'))
    csv(importance,'validation_importance_summary.csv');analog=analogues(daily,monetary);make_figures(daily,monetary,quantile,importance)
    full=daily[daily.regime=='full'];delta=load('calendar_stress_differences.csv');mdelta=load('monetary_stress_differences.csv');mf=monetary[monetary.regime=='full']
    bootstrap=load('quantile_bootstrap_draws.csv');n_rejected=18*99-len(bootstrap)//4
    findings=[
        'Bản yêu cầu phù hợp với blueprint sau khi phân biệt gợi ý mở rộng với yêu cầu tối thiểu; Broad USD được cho phép, không gắn nhãn DXY.',
        f'Calendar LP có đủ 1–30 ngày: {int((full.qvalue_bh<.05).sum())}/{len(full)} hệ số full có BH q<0,05 trong family720; outcome D…D+h−1 sau information cutoff bảo thủ.',
        f'Monetary post-event LP: {int((mf.qvalue_bh<.05).sum())}/{len(mf)} hệ số full đạt BH trong family60; outcome D+1…D+h khác cửa sổ phút, STMT gồm policy/information news.',
        f'Stress−Calm: daily {int((delta.qvalue_bh<.05).sum())}/240, monetary {int((mdelta.qvalue_bh<.05).sum())}/60 đạt BH theo family riêng; monetary stress chỉ9 sự kiện, không coi là bằng chứng regime causal vững.',
        f'Joint BTC–ETH VAR: {int(vard.stable.sum())}/6 hệ ổn định, {int((vard.whiteness_p20<.05).sum())}/6 bác bỏ whiteness20. Recursive restrictions là giả định, CI IRF còn hạn chế.',
        f'Quantile 5%/50%/95% cho full/pre/post; {n_rejected}/1782 bootstrap fits không hội tụ đã loại và lưu log. CI pointwise xấp xỉ, không tự khẳng định chênh lệch slope giữa phân vị.',
        'Giữ 0/32 macro ablation đạt BH từ completion, thêm validation-only feature importance và 40 artifacts tái lập dự báo cũ; không thêm thuật toán chỉ để tìm kết quả có ý nghĩa.',
        'PIT chỉ theo ngày archive và buffer; còn market/crypto historical proxies. Test cũ là exploratory; quy trình log trước outcome cho test tương lai đã có nhưng chưa có kết quả untouched mới.',
    ];save_json(OUT/'headline_findings.json',dict(findings=findings,calendar_full_significant=int((full.qvalue_bh<.05).sum()),monetary_full_significant=int((mf.qvalue_bh<.05).sum()),quantile_failed_bootstraps=n_rejected))
    # A reviewable mapping distinguishes delivered functionality from research limitations.
    compliance=[
        ('Nguồn crypto và macro','Đã có','Coin Metrics USD mẫu dài, Coinbase phút, connector/cache Binance USDT đối chiếu; FRED/ALFRED. Không splice quotes.'),
        ('Calendar/forward-fill','Đã có','Carry last admitted LEVELS; changes từ adjacent levels; no bfill/no crypto filling. EXPOST panel tách riêng.'),
        ('PIT tuyệt đối mọi feed','Chưa thể chứng nhận','Macro date-vintage + buffer; thiếu archive delivery/corrections của mọi nguồn. Không được đánh dấu hết leakage.'),
        ('VAR chung và recursive structural restrictions','Đã có, có giới hạn','BTC và ETH cùng hệ; 2Y/10Y sensitivity, ordering sensitivity, P/A0, diagnostics. Chưa pure monetary identification.'),
        ('LP/regime/pre-post/rolling','Đã có','Daily h1–30 Full/Calm/Stress; pre/post tables. Historical full-sample session models/rolling giữ nguyên.'),
        ('Quantile và hình tác động phân vị','Đã có','3 phân vị ×2 assets ×3 periods, block-bootstrap CI xấp xỉ; mô tả slope, chưa kiểm định paired quantile gaps.'),
        ('ML risk forecast và macro ablation','Đã có','Elastic Net đáp ứng chữ hoặc; histogram boosting bổ sung. Squared return proxy, variance dương, matched ablations, benchmark.'),
        ('Untouched test mới sau sửa thiết kế','Chưa có kết quả','Không gọi lại test2025+ là untouched. Có protocol và lệnh predict append trước outcome, cần dữ liệu tương lai thật.'),
        ('Dashboard đủ widgets và estimated response/CI','Đã có','5 shocks gồm Monetary;2 assets;h1–30 calendar;Full/Calm/Stress;quantile/IRF/rolling/analogue/importance.'),
        ('Repo và pipeline','Đã có','src/data,features,models,evaluation,utils;config;models artifacts;dashboard;tests;paper;run_project.py;README;versioned outputs.'),
        ('Kết luận causal transmission','Chưa xác lập','Daily information updates và STMT event associations không chứng minh pure exogenous policy shocks.'),
    ];cf=pd.DataFrame(compliance,columns=['Yêu cầu','Trạng thái','Phạm vi/giới hạn']);csv(cf,'compliance.csv')
    (OUT/'compliance.md').write_text('# Đối chiếu yêu cầu với blueprint và bản triển khai\n\n'+md(cf)+'\n\nSVAR/TVP/Markov/quantile và XGBoost/LightGBM là các lựa chọn gợi ý trong đề. Đã triển khai recursive restrictions và quantile; không cần chạy mọi thuật toán. Không đổi giả định để ép kết quả đạt kiểm định.\n',encoding='utf-8')
    sections=[]
    def section(title,text,frame=None,figure=None):sections.append((title,text,frame,figure))
    section('Tóm tắt','\n'.join('- '+f for f in findings))
    section('1. Đối chiếu yêu cầu và phạm vi',
        'Yêu cầu mô tả đúng hướng Research + Code + Financial Product. Blueprint cho phép broad dollar index; không bắt buộc ICE DXY hoặc mọi mô hình nâng cao. Bản này giữ baseline không MOVE và historical sample đầy đủ đã thống nhất; bổ sung chức năng thiếu, không đổi kết quả cũ.\n\nCác câu hỏi: quy mô và diễn biến liên hệ có điều kiện theo horizon, khác biệt pre/post và stress, tail/quantile slopes, và predictive content ngoài mẫu. Null results vẫn là kết quả nghiên cứu. Không thiết kế để ép kết quả giống một bài hoặc đạt p<0,05.',cf)
    section('2. Dữ liệu, source comparison và timing',
        'Daily USD là Coin Metrics PriceUSD; UTC bar ngày D đóng tại 00:00 UTC D+1. Binance BTCUSDT/ETHUSDT là nguồn đối chiếu riêng, có lịch sử từ17/08/2017, không thay hoặc nối vào USD từ2014. Nến Binance 08/02/2018 của cả hai tài sản có close timestamp sớm: giữ raw/giá, gắn full_utc_bar=false, để thiếu return ngày đó và ngày kế tiếp trong so sánh UTC. Chưa xác minh nguyên nhân từ nguồn chính thức. FOMC intraday cũ dùng Coinbase, SF Fed USMPD và ET→UTC có DST. Broad USD là FRED DTWEXBGS, không phải DXY trong event database.\n\nCalendar information panel: tại start D dùng f row D−2 với reference close D−1, tạo buffer24h; VIX proxy observation D−3 hoặc cũ hơn. Carry latest admitted levels trên ngày nghỉ, không bfill hoặc fill crypto. Δlevels là cập nhật bộ thông tin, có thể bao gồm revisions/đổi latest observation; không phải pure market surprise. Các crypto lag controls bắt đầu rD−2, không dùng giá vừa fixing tại origin.\n\nUSD vintage chỉ từ2019 nên calendar information LP/quantile có mẫu ngắn hơn historical session analyses. Panel historical levels carried EXPOST tách riêng và không dùng forecast. Dataset daily gốc đầy đủ2014–2026, pre/post và rolling cũ vẫn trong gói. ALFRED không chứng nhận exact provider delivery; buffer không xóa mọi revision/latency issue của market/crypto proxies.',load('binance_comparison.csv'))
    section('3. Calendar LP và regime interactions',
        'Outcome h là tổng log return D…D+h−1, h=1…30 calendar days; không nội suy đường cũ theo phiên. Đồng thời4 macro information changes,5 lags của macro và5 admissible crypto returns. Full/pre/post fit riêng; post bắt đầu2020, outcome pre không đi qua ranh giới. HAC max(5,h+1) finite-sample correction, CI pointwise95%.\n\nBH family720 gồm2assets×3periods×4shocks×30h. Stress pooling gồm regime dummy và4 shock×stress; stress là VIX available proxy>30 tại cutoff. State beta stress=beta+delta, variance có2Cov; BH differences riêng family240. State CIs không phải simultaneous bands. Không so p-values hai mẫu để kết luận đổi sensitivity. Dù timing bảo thủ, missing controls/omitted variables và archived proxy revisions vẫn ngăn diễn giải nhân quả.',full[full.horizon_days.isin([1,7,30])][['asset','shock','horizon_days','beta_pct','lower95','upper95','qvalue_bh','nobs']], 'figures/calendar_LP.png')
    section('4. Monetary response theo ngày sau FOMC',
        'SF Fed STMT dùng retrospective PCA/normalization, đơn vị percentage point; STMT×10 là shock per10bps. Fit STMT cùng own return/RMS từD−2 và VIX proxy đã khả dụng trước event. Dùng toàn bộ statements có surprise và daily data, không chọn mẫu theo Coinbase-minute coverage.\n\nOutcome D+1…D+h, loại toàn bộ event-day return nên không lẫn pre-announcement return; cũng bỏ mất phản ứng phút/ngày công bố. Vì vậy phải xem cùng event study intraday cũ, không gọi đây là tổng tác động bao gồm announcement. Event order HAC lag5 chỉ là approximation cho event spacing/overlapping outcomes; BH full60 và interaction60 riêng. State stress chỉ9 sự kiện ở h1, uncertainty lớn. +10bps là đơn vị hệ số; bảng shock scale nêu khoảng quan sát, không coi đơn vị đó là một sự kiện điển hình.\n\nKhông gọi STMT pure policy shock: có information effects và chuẩn hóa hồi cứu. Chưa nhận diện policy/information components như một structural experiment.',mf[mf.horizon_days.isin([1,7,30])][['asset','horizon_days','beta_pct','lower95','upper95','qvalue_bh','nobs']])
    samples=load('monetary_LP_samples.csv');scale=samples[samples.horizon_days==1].groupby('asset').STMT_10bps.agg(['min','max','std']).reset_index();csv(scale,'monetary_shock_scale.csv')
    section('4a. Quy mô STMT quan sát','Giá trị dưới đây theo đơn vị10bps. Khi đọc fitted response, phải phân biệt reporting unit với khoảng shock quan sát. Không ngoại suy thành khuyến nghị giao dịch.',scale)
    section('4b. Monetary Stress−Calm: tín hiệu và giới hạn mẫu nhỏ',
        f'{int((mdelta.qvalue_bh<.05).sum())}/60 chênh lệch slope monetary đạt BH trong family60, trong khi daily information-update differences là{int((delta.qvalue_bh<.05).sum())}/240. Đây là kết quả cần công bố, không bỏ vì khác câu chuyện kỳ vọng. Tuy nhiên stress chỉ9events mỗiasset ởh1, các horizon cộng dồn phụ thuộc mạnh; HAC trên eventorder và normal-reference CI có thể không đủ trong subgroup nhỏ. Chưa có leave-one-stress-event-out hoặc một finite-sample inference xác nhận độ vững của tín hiệu mới.\n\nKhông kết luận “stress làm Fed tightening gây giảm mạnh hơn”: dấu delta phải đọc từ bảng, STMT gồm policy/informationnews, +10bps vượt khoảng shock dương quan sát, và outcomes đã loại ngày công bố. Kết quả này là exploratory conditional regime association.',mdelta[mdelta.horizon_days.isin([1,7,30])][['asset','horizon_days','difference_pct','se','pvalue','qvalue_bh','nobs']])
    section('5. Joint VAR và recursive SVAR',
        'Reduced form vector [rBTC,rETH,ΔVIX,ΔBroadUSD,Δ2Y]; thay2Y bằng10Y là sensitivity. Common observed levels rồi tính chênh lệch: crypto gồm mọi ngày cuối tuần/lễ ở giữa. Đây là historical analysis với current vintage, không phải PIT forecast. BIC search1…10 dùng cùng response dates sau10 lags, không soIC trên mẫu thay đổi.\n\nCrypto-first là vector tham chiếu; macro-first [VIX,USD,yield,BTC,ETH] giả định macro không phản ứng đồng thời với crypto trong innovation, BTC đi trướcETH. Reverse macro order làm sensitivity. Với u=Pε, P Cholesky và A0=P−1, A0ΣA0′=I. Đã xuất P,A0 và coefficients để review. Những restrictions này là giả định recursive structural model, không chứng minh ngoại sinh hay pure policy.\n\nIRF là response riêng tại h phiên; không so ngang với cumulative calendar LP. Cả6 hệ stable nhưng4/6 bác bỏ Portmanteau20; pre samples không bác bỏ cũng không chứng minh mô hình đúng. CI tiệm cận chỉ để đối chiếu, chưa xác nhận adequate dưới heteroskedasticity/serial misspecification. Giữ residual limitations cũ, không tăng lag tùy tiện hoặc xóa outliers.',vard)
    section('6. Quantile effects và phi tuyến',
        'Quantile regression τ=.05,.50,.95 của1-day return trên4 information changes và crypto return đủ bufferD−2, full/pre/post. Chuẩn hóa X để cải thiện điều kiện số; scale slopes về shock reporting units. Mẫu phù hợp calendar thông tin USD vintage2019+, không thay historical full-sample findings.\n\nCircular moving-block pairs bootstrap: block20rows,99draws,seed9, giữ X/Y cùng dòng trong block. Percentile95% là CI pointwise xấp xỉ, có Monte Carlo error và giả định phù hợp block bootstrap. Mỗi fit tối đa5000iterations; bootstrap bị warning loại, exportlog và số draws thành công (98–99/99). Main estimates hội tụ. Chưa có kiểm định paired gap giữa phân vị hoặc simultaneous correction; đường khác nhau chỉ là mô tả conditional tail sensitivity, không chứng minh causal nonlinearity.',quantile[['asset','regime','tau','shock','beta_pct','lower95','upper95','nobs','successful_bootstraps']], 'figures/quantile_effects.png')
    section('7. ML, benchmark và forecast importance',
        'Elastic Net đáp ứng lựa chọn thuật toán trong đề; histogram gradient boosting là bổ sung, không gọi thành XGBoost/LightGBM. Target squared daily return là proxy variance, chưa phải intraday realized variance. Giữ các ablation matched và positive-variance design của completion, không retune khi thêm sản phẩm. Test2025+ đã được xem, toàn bộ extension vẫn exploratory.\n\nĐã tái dựng40 learned artifacts từ parameters khóa, tái lập dự báo test cũ, lưu joblib vàSHA256. Không dùng test làm feature importance. Importance fittrain và evaluatevalidation: circular group permutation own/macro/USD10repeats; loss increase mean/min/max mô tả predictive reliance. Correlated features, chọn hyperparameters trên cùngvalidation và circular shifts hạn chế cách diễn giải; không có causal importance.\n\n0/32 ablation đạtBH; benchmark family40 có0learned tốt hơn và5 kém hơn cóý nghĩa. Variancepositive không đủ đảm bảo chất lượng. Mọi winner vẫn chọn theovalidation. Chưa có một future untouched evaluation mới.',pd.read_csv(RESULTS/'completion/validation_selected_models.csv')[['asset','variant','target','model','rmse','qlike']], 'figures/forecast_importance.png')
    section('8. Tái lập, ứng dụng và kiểm tra',
        'Repository có src/data,features,models,evaluation,utils,config,models,notebooks,dashboard,tests,paper. run_project.py all chạy từ snapshot đã bàn giao, dùng cacheBinance nếu không truyền--download; không ghi đè oldoutputs. bootstrap chỉ dành freshcopy để lấy prerequisites từ publicproviders, có thể khác snapshot do revisions/availability; ZIPraw+hash là căn cứ tái lập đúng snapshot.\n\nDashboard có5shocks,2assets,h1–30calendar,Full/Calm/Stress,pointwiseCI,quantile,jointIRF,rolling và analogues. Analogues trả observedcumulative return và shock thực tế, không scale hay giữ các shock khác cố định. Monetary và daily có timingkhác nhau, luôn ghi trênUI.\n\nProtocolprospective từ20/10/2026: modelsfrozen,logpredictiontrướctargetstart,buffer24h và input/modelhash,append-only keys. Không tự tạo futureprices hoặc gọi protocol là đã có newOOSresults. Publication metadata thiếu vẫn là giới hạn phải công bố.')
    links='<p><a href="../../../dashboard/index.html">Dashboard hiện tại</a> · <a href="compliance.md">Đối chiếu yêu cầu</a> · <a href="calendar_LP.csv">Toàn bộ LP</a> · <a href="monetary_LP.csv">Monetary LP</a> · <a href="quantile_effects.csv">Quantile</a> · <a href="joint_VAR_IRF.csv">Joint IRF</a> · <a href="recursive_SVAR_matrices.csv">P/A0 restrictions</a> · <a href="prospective_protocol.json">Prospective protocol</a> · <a href="independent_validation.json">Validation</a></p>'
    for name,label in [('completion/report.html','Báo cáo completion trước'),('synthesis/report.html','LP/FOMC/rolling historical snapshot'),('report.html','Baseline đầy đủ'),('literature_review.md','Literature review')]:
        if (RESULTS/name).exists():links+=f'<p><a href="../{name}">{label}</a></p>'
    links+='<p>Nguồn chính: <a href="https://developers.binance.com/en/docs/products/spot/rest-api">Binance market-data API</a> · <a href="https://fred.stlouisfed.org/docs/api/fred/realtime_period.html">ALFRED real-time periods</a> · <a href="https://www.statsmodels.org/stable/_modules/statsmodels/regression/quantile_regression.html">statsmodels quantile regression</a>. Data dictionary vàsource log gốc đi kèm thư mụcdata.</p>'
    css='body{font:16px/1.65 system-ui;color:#193849;background:#edf3f6;margin:0}main{background:white;max-width:1240px;margin:auto;padding:36px}h1{line-height:1.25}h2{color:#096d90;margin-top:36px}.lead{background:#edf5f8;padding:18px;border-left:4px solid #0b7698}.table-wrap{overflow:auto}table{border-collapse:collapse;white-space:nowrap;font-size:12px}td,th{padding:8px;border-bottom:1px solid #dce6ed;text-align:right}th{background:#edf4f7}img{max-width:100%;height:auto}a{color:#096b93}@media(max-width:700px){main{padding:18px}h1{font-size:26px}}'
    body='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Topic09 — Blueprint implementation</title><style>'+css+'</style><main><p>CRYPTO FINANCE LAB / 19.10.2026</p><h1>Global Financial Conditions → BTC/ETH</h1><p class="lead">Calendar LP · Joint VAR / recursive restrictions · Quantile effects · ML risk forecasts<br>Conditional associations, transparent timing and model limitations.</p>'+links
    text='# Topic09 — Blueprint implementation\n\nBản19/10/2026. Giữ snapshot daily đến15/10/2026 và baselinekhôngMOVE.\n\n'
    for title,paragraphs,frame,figure in sections:
        body+='<section><h2>'+html.escape(title)+'</h2>';body+=('<ul>'+''.join('<li>'+html.escape(p[2:])+'</li>' for p in paragraphs.splitlines())+'</ul>') if paragraphs.startswith('- ') else ''.join('<p>'+html.escape(p)+'</p>' for p in paragraphs.split('\n\n'))
        text+='## '+title+'\n\n'+paragraphs+'\n\n'
        if frame is not None:body+=ht(frame);text+=md(frame)+'\n\n'
        if figure:body+='<img src="'+figure+'" alt="'+html.escape(title)+'">';text+='!['+title+']('+figure+')\n\n'
        body+='</section>'
    body+='<h2>Nguồn và phụ lục</h2>'+links+'</main></html>';text+='## Nguồn và phụ lục\n\n'+links
    (OUT/'report.html').write_text(body,encoding='utf-8');(OUT/'report.md').write_text(text,encoding='utf-8')
    (ROOT/'paper').mkdir(exist_ok=True);(ROOT/'paper/README.md').write_text('# Báo cáo hiện tại\n\n[Báo cáoHTML](../outputs/research/blueprint_20261019/report.html) · [Markdown](../outputs/research/blueprint_20261019/report.md) · [Đối chiếu yêu cầu](../outputs/research/blueprint_20261019/compliance.md).\n\nCác báo cáo trước là snapshot nghiên cứu theo phiên bản; không ghi đè.\n',encoding='utf-8')
    payload=dict(daily=records(daily),monetary=records(monetary),quantile=records(quantile),var_diagnostics=records(vard),var_irf=records(irf),daily_difference=records(delta),monetary_difference=records(mdelta),analogues=records(analog),importance=records(importance),ablation=records(pd.read_csv(RESULTS/'completion/ablation_tests.csv')),rolling=records(pd.read_csv(TABLES/'rolling_sensitivity.csv')),findings=findings)
    template=(ROOT/'dashboard/template.html').read_text(encoding='utf-8');(ROOT/'dashboard/index.html').write_text(template.replace('__PAYLOAD__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/')),encoding='utf-8')
    print('\n'.join(findings),flush=True)
