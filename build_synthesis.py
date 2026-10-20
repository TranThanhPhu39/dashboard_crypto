"""Assemble LP/HAC, FOMC and rolling results; do not estimate or alter models."""
from research_common import *
import hashlib, html, datetime

OUT = RESULTS / 'synthesis'
SHOCKS = {'vix_change': 'VIX +5 điểm', 'usd_return_pct': 'Broad USD +1% log return',
          'us2y_change_bps': 'US 2Y +10 bps', 'us10y_change_bps': 'US 10Y +10 bps'}


def protected_hashes():
    files = list((ROOT/'data').rglob('*')) + list(RESULTS.rglob('*')) + list((ROOT/'notebooks').rglob('*'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file() and OUT not in p.parents}


def load(name): return pd.read_csv(TABLES/(name+'.csv'))
def records(df): return json.loads(df.to_json(orient='records', double_precision=15))
def ht(df): return '<div class="table-wrap">'+df.to_html(index=False, border=0, float_format=lambda x: f'{x:.5g}')+'</div>'
def md(df):
    q = df.copy()
    for c in q.select_dtypes(include='number'): q[c] = q[c].map(lambda x: f'{x:.6g}')
    return '| '+' | '.join(q.columns)+' |\n| '+' | '.join(['---']*len(q.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in q.itertuples(index=False,name=None))


def make_figures(rolling, events):
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.6), sharex=True)
    for ax, asset in zip(axes, ['btc','eth']):
        q = rolling[(rolling.asset == asset) & (rolling.shock == 'vix_change')].sort_values('date_utc')
        dates = pd.to_datetime(q.date_utc)
        ax.fill_between(dates, q.beta_pct-1.96*q.se, q.beta_pct+1.96*q.se, alpha=.16)
        ax.plot(dates, q.beta_pct, linewidth=1.2, label='252-session rolling association')
        ax.axhline(0, color='#777', linewidth=.8)
        ax.axvline(pd.Timestamp('2020-01-01'), color='#ab7459', linestyle='--', linewidth=.8)
        ax.set_title(asset.upper()+' | VIX +5 points'); ax.set_ylabel('Log return (%)')
    axes[-1].set_xlabel('Window end date | updated every 21 eligible sessions')
    fig.suptitle('Rolling VIX sensitivity | pointwise HAC 95% CI, no break test', y=1.01)
    fig.tight_layout(); fig.savefig(OUT/'figures/rolling_vix.png', bbox_inches='tight'); plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(10,4.4),sharey=True)
    for ax, asset in zip(axes,['BTC','ETH']):
        q = events[(events.asset == asset) & (events.term == 'STMT_10bps')].set_index('window').loc[['baseline_m10_p20','nyfed_m5_p25']]
        for i, (_,r) in enumerate(q.iterrows()):
            ax.errorbar(i,r.beta_return_pct_per10bps,yerr=[[r.beta_return_pct_per10bps-r.lower95],[r.upper95-r.beta_return_pct_per10bps]],fmt='o',capsize=5,color=['#096b93','#b45c77'][i])
            ax.annotate('BH q='+f'{r.qvalue_bh:.3f}',(i,r.beta_return_pct_per10bps),xytext=(8,0),textcoords='offset points',fontsize=9)
        ax.axhline(0,color='#777',linewidth=.8); ax.set_xlim(-.6,1.8)
        ax.set_xticks([0,1],['[-10,+20] min','[-5,+25] min']); ax.set_title(asset+' | matched scheduled events')
    axes[0].set_ylabel('Log return (%) per STMT +10 bps')
    fig.suptitle('FOMC sensitivity | pointwise HC3 95% CI, shock window stays [-10,+20]')
    fig.tight_layout(); fig.savefig(OUT/'figures/fomc_windows.png',bbox_inches='tight'); plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True); (OUT/'figures').mkdir(exist_ok=True); (OUT/'tables').mkdir(exist_ok=True)
    before = protected_hashes()
    lp=load('local_projections'); inter=load('regime_interactions'); rolling=load('rolling_sensitivity')
    baseline_events=load('fomc_regressions'); counts=load('fomc_sample_counts')
    event_all=pd.read_csv(RESULTS/'fomc_comparison/regressions.csv')
    events=event_all[event_all.family=='primary_matched'].copy()
    event_scale=pd.read_csv(RESULTS/'fomc_comparison/shock_scale_summary.csv')
    metrics=load('forecast_test_metrics'); usd=load('forecast_usd_paired_tests')
    selected=load('forecast_validation_selected_models')
    floor=load('forecast_variance_floor_diagnostics')
    var=pd.read_csv(RESULTS/'var_lag_sensitivity/diagnostics.csv')
    var=var[var.stage=='search15_common_dates']
    diagnostics=json.loads((RESULTS/'var_residual_diagnostics/headline_findings.json').read_text())
    desc=load('descriptive_statistics')
    ds=desc[(desc.regime=='full') & desc.variable.isin(['btc_usd_log_return','eth_usd_log_return'])][['variable','n','std','excess_kurtosis']].copy()
    ds['std_pct']=ds.pop('std')*100
    roll_summary=rolling.groupby(['asset','shock'],as_index=False).agg(n_windows=('date_utc','size'),first_window_end=('date_utc','min'),last_window_end=('date_utc','max'))
    h0=lp[(lp.regime=='full') & (lp.shock=='vix_change') & (lp.horizon_sessions==0)].set_index('asset')
    full=lp[lp.regime=='full']
    findings=[
        f'LP/HAC cùng phiên, VIX +5 điểm: BTC {h0.loc["btc","beta_pct"]:.2f}%, ETH {h0.loc["eth","beta_pct"]:.2f}% log return; quan hệ có điều kiện, chưa xác lập nhân quả.',
        f'{int((full.qvalue_bh<.05).sum())}/{len(full)} hệ số LP full sample có q<0,05; BH tính trên cả {len(lp)} hệ số full/pre/post. CI là pointwise, không phải simultaneous bands.',
        f'{int((inter.qvalue_bh<.05).sum())}/{len(inter)} interaction pre/post hoặc stress có q<0,05; chưa có bằng chứng vững về khác biệt, không chứng minh hiệu ứng không đổi.',
        'FOMC baseline MP1/MP2 chưa có ý nghĩa; đối chiếu 2017–2022 cho STMT âm ở [-5,+25] còn ý nghĩa sau BH trong lượt bổ sung. Shock vẫn đo [-10,+20].',
        'Rolling 252 phiên mô tả sensitivity thay đổi theo thời gian; không dùng nhìn đồ thị để xác nhận structural break hoặc chọn tham số dự báo.',
        'VAR là đối chiếu thăm dò: ổn định nhưng whiteness vẫn bị bác bỏ; ARCH và ảnh hưởng quan sát là các giới hạn chưa được khắc phục.',
        'Forecasting chưa cho thấy USD gia tăng cải thiện bền trong các cấu hình đã xét. Chưa tách riêng đóng góp của toàn bộ nhóm macro; variance boosting còn nhạy với floor.'
    ]
    protocol=dict(version='lp-fomc-rolling synthesis',built_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  primary=['LP/HAC conditional cumulative associations','FOMC event associations','rolling historical sensitivity'],
                  supplementary=['VAR exploratory IRF/diagnostics','USD incremental forecasting'],
                  no_new_fits=True,no_new_hypothesis_tests=True,lp_horizons=[0,1,2,5,10,20,30],lp_BH_family=168,
                  lp_outcome='sum of crypto log returns t through t+h on eligible US sessions',lp_covariance='HAC maxlags=max(5,h+1), finite-sample correction, pointwise 95%',
                  interactions_BH_family=80,rolling_window=252,rolling_step=21,rolling_CI='pointwise normal-reference HAC, not simultaneous or break inference',
                  fomc_BH_family=12,fomc_primary_scope='scheduled 2017-2022, matched dates within each asset; exploratory extension',
                  fomc_baseline_BH_family=len(baseline_events),var_role='supplementary; do not use stable roots as adequacy or causal proof',
                  forecasting_scope='incremental USD within declared feature set; no all-macro ablation',
                  timing_limit='Macro date-level vintages plus market proxies; fixing time does not certify delivery at 00:00 UTC.')
    for frame,name in [(full,'lp_full'),(inter,'regime_interactions'),(events,'fomc_matched'),(roll_summary,'rolling_coverage'),(selected,'forecast_validation_selected')]:
        frame.to_csv(OUT/'tables'/f'{name}.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
    (OUT/'method.json').write_text(json.dumps(protocol,indent=2,ensure_ascii=False),encoding='utf-8')
    make_figures(rolling,events)
    baseline=baseline_events[(baseline_events.coverage=='complete') & (baseline_events.regime=='full') & baseline_events.specification.isin(['target_nextmeeting','sf_fed_stmt'])]
    sections=[]
    def section(title,text,table=None,picture=None): sections.append(dict(title=title,text=text,table=table,picture=picture))
    section('Tóm tắt', '\n'.join('- '+x for x in findings))
    section('1. Câu hỏi và cách đọc nghiên cứu', '''Nghiên cứu đánh giá mối liên hệ giữa điều kiện tài chính và BTC/ETH, độ lớn và diễn biến theo horizon, khác biệt pre/post-2020 hoặc stress, phản ứng quanh FOMC và giá trị dự báo USD gia tăng. Baseline không MOVE; không nối chỉ số USD cũ. Dữ liệu daily giữ snapshot 16/10/2026, từ 2014 đến 15/10/2026; ETH ngắn hơn, mỗi mô hình dùng số quan sát khả dụng riêng.

LP/HAC, event study và rolling sensitivity là trục trình bày chính theo các mục 2.5–2.7 của blueprint. VAR được giữ làm đối chiếu thăm dò, không xóa khỏi lịch sử nghiên cứu. Thay đổi vai trò trình bày không có nghĩa LP đã khắc phục mọi vấn đề thống kê hoặc FOMC đã nhận diện chính sách thuần túy. Báo cáo này không fit hoặc chọn mô hình mới.''')
    section('2. Dữ liệu, timing và đơn vị', '''BTC/ETH là Coin Metrics PriceUSD end-of-day UTC; date t đóng tại 00:00 UTC t+1. FOMC dùng Coinbase minute candles, một nguồn/sàn khác. Biến Mỹ theo ngày quan sát/phiên nguồn, không phải giá đồng bộ tại UTC midnight. Không gọi DXY intraday trong USMPD là broad USD daily.

Với LP/VAR, trước hết lấy common observed levels rồi tính thay đổi giữa các mốc; return crypto gồm đủ ngày cuối tuần/lễ ở giữa. Audit 5.942 khoảng xác nhận không bỏ weekend returns. Vì thế h là eligible US sessions, không phải ngày lịch. Khoảng 21–27/01/2016 dài 6 ngày được giữ: broad USD thiếu đã xác nhận trên nguồn Fed, không điền bằng chỉ số cũ.

Macro forecasting dùng ALFRED ngày vintage; VIX/S&P/gold là lagged historical proxies. Giá fixing và giờ công bố không đồng nhất; chưa chứng nhận toàn feed sẵn có đúng origin 00:00. Squared return và trailing RMS là volatility proxies, không phải realized variance intraday cả ngày. Gold là GC=F có roll; WTI spot có giá âm, log change tương ứng để thiếu.''',ds)
    lp_view=full[['asset','shock','horizon_sessions','beta_pct','lower95','upper95','qvalue_bh','nobs']]
    section('3. LP/HAC: kết quả chính theo horizon', '''Với mỗi h=0,1,2,5,10,20,30 phiên, outcome là tổng crypto log return từ t đến t+h. Các biến macro cùng phiên được đưa vào đồng thời, cùng 5 lags của toàn hệ; quy mô +5 điểm VIX, +1% USD log return, +10 bps yield. HAC maxlags=max(5,h+1), CI pointwise 95%; không phải simultaneous confidence band. BH áp dụng trên 168 hệ số full/pre/post, không chỉ 56 hệ số full dưới đây.

VIX +5 điểm đi kèm BTC −2,687% (CI [−3,604; −1,769]) và ETH −3,879% (CI [−5,068; −2,690]) tại h=0. Liên hệ VIX cumulative còn âm/có ý nghĩa tại một số horizon dài. Điều này không có nghĩa crypto tiếp tục giảm mỗi ngày, hay mất đúng 20 ngày lịch để phản ứng: outcome đã cộng cả phiên t và các phiên sau. Không kết luận ETH nhạy hơn BTC có ý nghĩa thống kê nếu chưa kiểm định trực tiếp chênh lệch giữa tài sản.

Một số hệ số 2Y ở BTC tại h=20/30 còn ý nghĩa sau BH, nhưng thay đổi yield không phải monetary surprise đã nhận diện. Không diễn giải dấu hệ số thành kênh chính sách duy nhất. LP không phải causal response chỉ vì dùng HAC; controls/lag specification, đồng thời, nonlinearities và timing vẫn là các giới hạn. Không loại USD/10Y hoặc horizon không có ý nghĩa khỏi bảng.''',lp_view,'../figures/lp_responses.png')
    section('4. Pre/post-2020 và stress', '''Pooled interactions kiểm định trực tiếp chênh lệch slope; không so hai p-value hoặc CI overlap để suy ra khác biệt. Mốc 01/01/2020 đã chốt trước; stress là VIX của phiên đủ dữ liệu trước >30. Với pre/post, outcome đi qua điểm chia được loại khỏi phép kiểm định interaction.

Không có hệ số nào trong 80 interaction có q<0,05 sau BH. Có thể viết “chưa tìm thấy khác biệt bền theo thiết kế này”, không viết “institutionalization không có tác động” hoặc “hiệu ứng hai giai đoạn bằng nhau”. Stress phân bố không cân bằng: core pre chỉ có 9 stress sessions, post có 148. Không đổi điểm chia/threshold để tìm ý nghĩa. Mọi khác biệt theo thời gian quan sát trên rolling chỉ bổ trợ mô tả, không thay kiểm định interaction.''',inter[['asset','interaction','shock','horizon_sessions','difference_pct','lower95','upper95','qvalue_bh','nobs']])
    section('5. FOMC: baseline và đối chiếu phải trình bày cùng nhau', '''Baseline sử dụng statement [-10,+20] phút, actual Eastern timestamps đổi UTC có DST; chỉ lấy cửa sổ đủ minute candles, robustness endpoint-only đã lưu. Có 95 BTC và 83 ETH complete windows, MP1/MP2 cùng hồi quy; alternative là SF Fed STMT, HC3. Bảng dưới giữ cả hai đặc tả ở full sample, không bỏ baseline kết quả yếu để chỉ trình bày extension có ý nghĩa.

Đối chiếu bổ sung dùng cuộc họp định kỳ 2017–2022 và matched complete dates trong từng tài sản: 46 BTC, 45 ETH. Hai cửa sổ return [-10,+20] và [-5,+25] dùng cùng ngày và cùng surprise. Các yếu tố mẫu/scheduled/window khác baseline được ghi riêng, chưa phải replication bộ Target/Path/LSAP của New York Fed.''',baseline[['asset','specification','term','beta_return_pct','lower95','upper95','qvalue_bh','nobs']])
    section('5a. FOMC matched: bằng chứng và giới hạn', '''STMT ở [-5,+25] có hệ số BTC −2,721% và ETH −3,557% / +10 bps, q≈0,0296 và 0,0230 trong nhóm 12 hệ số của lượt bổ sung. 1 SD STMT chỉ khoảng 2,03 bps, tương ứng fitted association −0,55% và −0,72%; +10 bps là đơn vị báo cáo, vượt khoảng shock dương quan sát trong mẫu, không coi là một sự kiện điển hình.

STMT ở [-10,+20] không còn ý nghĩa sau BH; MP1/MP2 chưa có ý nghĩa ở cả hai cửa sổ. Leave-one-event-out của STMT ở [-5,+25] giữ dấu âm và raw p<0,05, nhưng đó không phải BH cho toàn chuỗi nghiên cứu hay mọi đặc tả. Có ý nghĩa ở một cửa sổ và không ở cửa sổ khác chưa chứng minh hai slope khác nhau.

Đây là association với policy news: surprise vẫn đo [-10,+20], chưa tách policy/information shocks; STMT là PCA/normalization công bố hồi cứu, không dùng như forecast feature PIT. CI HC3 pointwise, không đồng thời. Không dùng kết quả này để khẳng định Fed tăng rate gây giảm crypto một lượng xác định.''',events[['asset','window','specification','term','beta_return_pct_per10bps','lower95','upper95','qvalue_bh','nobs']],'figures/fomc_windows.png')
    section('6. Rolling sensitivity: độ nhạy thay đổi theo thời gian', '''Rolling regressions dùng 252 eligible sessions, cập nhật mỗi 21 sessions, cùng hệ macro contemporaneous và 5 lags; HAC lag 5. Hệ số biểu thị quan hệ cùng phiên trong cửa sổ, không phải cumulative h=20 hoặc IRF identified.

Hình dưới thêm CI pointwise từ beta/se đã lưu, không fit lại regression. Các cửa sổ chồng lấp nên phụ thuộc mạnh; dải tại từng ngày không phải simultaneous band. Đường đổi dấu hoặc hai CI thay đổi không tự chứng minh structural break. Không dùng rolling chọn mốc 2020, threshold stress, mô hình hoặc tuning forecasting sau khi nhìn kết quả. Dashboard cho phép xem cả 4 biến, không chỉ VIX.''',roll_summary,'figures/rolling_vix.png')
    section('7. VAR và chẩn đoán: đối chiếu bổ sung', '''Miền search hữu hạn 0–15 với weekday+gap vẫn chọn BIC=1; AIC full=4, pre=1, post=2. Cả 12 lựa chọn ổn định nhưng bác bỏ Portmanteau adjusted ở 20/30/40. IRF trùng tham chiếu khi cùng mẫu/cùng lag không phải bằng chứng mô hình đã đạt.

10 unique fitted systems có 100/100 ARCH-LM q<0,05 trong family đã khai báo. Đây là kiểm định cổ điển có thể chịu ảnh hưởng mean misspecification và đuôi dày; không tự xác nhận GARCH. Case sensitivity nổi bật: ETH pre-2020, VIX +5, h=0, bỏ block quanh 05/02/2018 làm IRF −1,783% thành −0,641%. Khoảng USD thiếu 01/2016 cũng ảnh hưởng ETH. Không xóa các quan sát khỏi mô hình chính hoặc kiểm định whiteness trên mẫu đã nén.

CI Cholesky/tiệm cận của VAR chưa được xác nhận phù hợp với các hạn chế trên. Đưa VAR vào phụ lục/đối chiếu với nhãn thăm dò; không tiếp tục tăng lag hoặc bootstrap để ép kiểm định đạt. LP cumulative và VAR point-horizon là hai outcome khác nhau, không so ngang trực tiếp.''',var[['asset','regime','criterion','lag','nobs','whiteness_p20','whiteness_p30','whiteness_p40']])
    section('8. Forecasting USD: phạm vi giữ nguyên', '''Giữ cấu hình không USD mẫu dài, và cặp không/có USD vintage từ 2019 trên cùng origins/targets/lịch train-validation-test. Train trước 2023; validation 2023–2024; test từ 2025. Tuning chỉ bằng validation, refit train+validation một lần; test đã được xem, mọi sửa đổi theo test sau này phải là exploratory hoặc đánh giá mới.

Validation chọn historical mean cho return ở các cấu hình common, trailing30 cho variance; không chọn lại theo test. 0/12 dòng paired tests có q<0,05; trong đó 8 có loss difference chính xác bằng 0 (historical mean và Elastic Net), không coi là 12 thí nghiệm độc lập. Có 44 floor hits ở boosting variance cộng trên các cấu hình; QLIKE nhạy mạnh nên không dùng cải thiện đó làm bằng chứng chắc chắn về USD.

Chưa có own-only vs own+macro ablation, nên phạm vi trực tiếp là USD gia tăng, không phải “mọi biến macro không dự báo được crypto”. Có thể hoàn thành nghiên cứu bằng cách giới hạn câu hỏi, không bắt buộc thêm model. Squared daily return vẫn là variance proxy; metric hướng cho zero-return được hiển thị N/A trong bản tổng hợp vì benchmark không dự báo hướng, không sửa CSV gốc.''',selected[['asset','variant','target','model','n_test','rmse','mae','qlike']])
    section('9. Đặt kết quả trong tài liệu và kết luận', '''Tài liệu không thống nhất một dấu/độ lớn cho mọi mẫu và shock. Benigno & Rosa (2023, New York Fed) là đối chiếu cho phản ứng macro/FOMC yếu; Karau (2023) và Köse và cộng sự (2026) gợi ý quan hệ thay đổi theo giai đoạn; Pietrzak (2023) cho thấy ý nghĩa của tách policy/information shocks. Khác sample, frequency, target và identification phải được giữ trong diễn giải, không chọn mô hình chỉ để giống một bài.

Đóng góp hiện tại: dữ liệu có convention/vintage minh bạch; đường conditional cumulative association và uncertainty theo horizon; kiểm định regime trực tiếp; FOMC baseline đi cùng sensitivity và influence; báo cáo cả kết quả null, model inadequacy và hạn chế forecast. Không chứng minh một cơ chế causal monetary transmission hoặc một hệ dự báo thắng benchmark bền.

Nếu tiếp tục phương pháp mới như quantile/TVP/weekly/robust inference, cần câu hỏi và thiết kế riêng được thống nhất. Không tự fit thêm trong bản tổng hợp này. Việc ưu tiên LP/FOMC/rolling là lựa chọn trình bày dựa trên phạm vi bằng chứng, không tuyên bố mọi vấn đề nghiên cứu đã được giải quyết.''')
    # Markdown is the complete narrative; tables and figures are also linked for portability.
    text='# Chủ đề 9 — LP/HAC, FOMC và rolling sensitivity\n\nBản tổng hợp kết quả đã lưu · 17/10/2026 · Baseline không MOVE.\n\n'
    for s in sections:
        text+='## '+s['title']+'\n\n'+s['text']+'\n\n'
        if s['table'] is not None: text+=md(s['table'])+'\n\n'
        if s['picture']: text+='!['+s['title']+']('+s['picture']+')\n\n'
    text+='## Nguồn, phụ lục và tái lập\n\n'+'''- [Literature review](../literature_review.md), [review tổng hợp](../current_results_review.md).
- [Baseline đầy đủ](../report.html), [FOMC comparison](../fomc_comparison/report.md), [VAR calendar](../var_calendar_extension/report.md), [VAR lag sensitivity](../var_lag_sensitivity/report.md), [ARCH/influence](../var_residual_diagnostics/report.md), [USD source verification](../usd_missing_verification/report.md).
- [Dashboard hiện tại](dashboard.html), [phương pháp](method.json), [validation](validation.json). Code chỉ đọc số liệu cũ: `py -3.11 build_synthesis.py`; kiểm tra `py -3.11 validate_synthesis.py` và `node validate_synthesis_dashboard.cjs`.
- Nguồn dữ liệu: [Coin Metrics](https://gitbook-docs.coinmetrics.io/network-data/network-data-overview/market/price), [FRED/ALFRED](https://alfred.stlouisfed.org/), [SF Fed USMPD](https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/), Coinbase, Yahoo Finance. Raw payloads và source logs đi kèm repository.
- Tài liệu: [Jordà (2005)](https://www.aeaweb.org/articles?id=10.1257/0002828053828518), [Benigno & Rosa (2023)](https://www.newyorkfed.org/research/staff_reports/sr1052.html), [Karau (2023), trang tác giả/abstract](https://soeren-karau.de/), [Pietrzak (2023)](https://link.springer.com/article/10.1007/s10436-023-00432-3), [Köse và cộng sự (2026)](https://link.springer.com/article/10.1007/s00181-026-02897-3). Không coi việc trích dẫn là replication toàn văn.
'''
    (OUT/'report.md').write_text(text,encoding='utf-8')
    css='body{font:16px/1.65 system-ui;color:#19354a;background:#eef3f6;margin:0}main{max-width:1200px;margin:auto;padding:40px;background:#fff}h1{line-height:1.2;font-size:34px}h2{color:#086887;margin-top:38px}nav{padding:18px;background:#eaf3f6}.table-wrap{overflow-x:auto}table{border-collapse:collapse;font-size:12px;white-space:nowrap}th,td{padding:8px;border-bottom:1px solid #dce6ec;text-align:right}th{background:#eaf2f7}img{max-width:100%;height:auto}a{color:#096b93}.lead{padding:18px;background:#eaf3f6;border-left:4px solid #08789e}@media(max-width:700px){main{padding:18px}h1{font-size:26px}}@media print{main{padding:0}img{break-inside:avoid}}'
    body='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chủ đề 9 — LP/HAC, FOMC, rolling</title><style>'+css+'</style><main><p>CRYPTO FINANCE LAB · RESEARCH 09</p><h1>Điều kiện tài chính toàn cầu và BTC/ETH</h1><p class="lead">LP/HAC · FOMC · Rolling sensitivity<br>Kết quả có điều kiện; VAR là đối chiếu thăm dò. Snapshot daily đến 15/10/2026.</p><nav><a href="dashboard.html">Dashboard tương tác</a> · <a href="report.md">Markdown</a> · <a href="../current_results_review.md">Review</a> · <a href="../literature_review.md">Tài liệu</a></nav>'
    for s in sections:
        body+='<section><h2>'+html.escape(s['title'])+'</h2>'
        if s['text'].startswith('- '): body+='<ul>'+''.join('<li>'+html.escape(x[2:])+'</li>' for x in s['text'].splitlines())+'</ul>'
        else: body+=''.join('<p>'+html.escape(x)+'</p>' for x in s['text'].split('\n\n'))
        if s['picture']: body+='<img src="'+s['picture']+'" alt="'+html.escape(s['title'])+'">'
        if s['table'] is not None: body+=ht(s['table'])
        body+='</section>'
    body+='<section><h2>Nguồn và tái lập</h2><p><a href="report.md">Bản Markdown có danh mục nguồn và lệnh tái lập</a> · <a href="../report.html">Baseline giữ nguyên</a> · <a href="../fomc_comparison/report.html">FOMC đối chiếu</a> · <a href="../var_residual_diagnostics/report.html">VAR diagnostics</a> · <a href="method.json">Phương pháp</a> · <a href="validation.json">Kiểm tra</a></p></section></main></html>'
    (OUT/'report.html').write_text(body,encoding='utf-8')
    payload=dict(lp=records(lp),interactions=records(inter),rolling=records(rolling),events=records(events),event_scale=records(event_scale),
                 baseline_events=records(baseline),counts=records(counts[counts.coverage=='complete']),usd=records(usd),selected=records(selected),
                 var_diagnostics=records(var),residual_findings=diagnostics,findings=findings,protocol=protocol,shock_labels=SHOCKS)
    template=(ROOT/'synthesis_dashboard_template.html').read_text(encoding='utf-8')
    (OUT/'dashboard.html').write_text(template.replace('__PAYLOAD__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/')),encoding='utf-8')
    checks={'all_existing_sources_and_results_unchanged':before==protected_hashes(),
            'LP_168_rows_and_56_full':len(lp)==168 and len(full)==56,'interactions_80':len(inter)==80,
            'FOMC_matched_12':len(events)==12,'baseline_FOMC_retained':len(baseline)==6,
            'no_payload_placeholder': '__PAYLOAD__' not in (OUT/'dashboard.html').read_text(encoding='utf-8')}
    result=dict(checks=checks,n_checks=len(checks),passed=int(sum(checks.values())),protected_sha256=before,
                no_new_model_fits=True,no_new_statistical_tests=True,method_sha256=hashlib.sha256((OUT/'method.json').read_bytes()).hexdigest())
    (OUT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert all(checks.values()),checks
    print('\n'.join(findings),flush=True)


if __name__=='__main__': main()
