const scenarioNames={native_asof_d3:'Dữ liệu đúng thời điểm · mẫu gốc',matched_asof_d3:'Cùng mẫu · trễ 3 ngày',matched_latest_d3:'Đối chiếu dùng dữ liệu sửa sau',matched_asof_d4:'Cùng mẫu · trễ 4 ngày'};
const variantLabels={long_own:'Chỉ crypto · mẫu dài',long_macro:'Crypto + vĩ mô · mẫu dài',common_own:'Chỉ crypto · từ 2019',common_macro:'Crypto + vĩ mô · từ 2019',common_usd:'Crypto + vĩ mô + USD · từ 2019',historical_mean:'Bình quân lịch sử',zero:'Lợi suất bằng 0'};
const humanVariant=x=>variantLabels[x]||String(x).replace(/_/g,' ');
const latestNumber=x=>x===null||x===undefined?'N/A':Number(x).toPrecision(5);
const interval=(a,b)=>`[${latestNumber(a)}; ${latestNumber(b)}]`;
const selectedForecast=()=>({asset:el('fAsset').value,target:el('target').value,model:el('forecastModel').value,scenario:el('fScenario').value,scope:el('fScope').value});
const matches=(r,s)=>Object.entries(s).every(([key,value])=>String(r[key])===String(value));
function renderForecast(){
 if(typeof window!=='undefined'&&!HISTORICAL.series&&typeof loadForecastWorkspace==='function')loadForecastWorkspace();
 const s=selectedForecast(),pairs=[['long_own','long_macro'],['common_own','common_macro'],['common_macro','common_usd'],['common_own','common_usd']],pair=pairs[Number(el('forecastPair').value||0)];
 const rows=LATEST.ablation.filter(r=>matches(r,s)&&r.base===pair[0]&&r.added===pair[1]);
 el('forecastTable').innerHTML=table(['Cấu hình gốc → thêm thông tin','Số ngày','Chênh lệch sai số','Khoảng tin cậy 95%','p','q (BH)'],rows.map(r=>[`${humanVariant(r.base)} → ${humanVariant(r.added)}`,r.n,latestNumber(r.mean_loss_new_minus_base),interval(r.ci_low,r.ci_high),prob(r.pvalue),prob(r.qvalue_bh)]));
 const b=LATEST.benchmarks.filter(r=>matches(r,s));
 el('benchmarkTable').innerHTML=table(['Cấu hình','Mốc so sánh','Số ngày','Chênh lệch sai số','Khoảng tin cậy 95%','q (BH)'],b.map(r=>[humanVariant(r.variant),humanVariant(r.benchmark),r.n,latestNumber(r.mean_loss_new_minus_base),interval(r.ci_low,r.ci_high),prob(r.qvalue_bh)]));
 const t=LATEST.sensitivity.filter(r=>matches(r,{asset:s.asset,target:s.target,model:s.model,scope:s.scope})&&r.variant===pair[1]);
 el('sensitivityTable').innerHTML=table(['Cấu hình / thay đổi','Số ngày','Chênh lệch sai số','Khoảng tin cậy 95%','q (BH)'],t.map(r=>[`${r.variant} / ${r.comparison}`,r.n,latestNumber(r.mean_loss_new_minus_base),interval(r.ci_low,r.ci_high),prob(r.qvalue_bh)]));
 el('forecastContext').textContent=`${scenarioNames[s.scenario]} · ${s.scope==='pooled'?'Gộp 2023–2026':s.scope} · ${s.target==='return'?'MSE return':'QLIKE squared return'} · ${rows.length?rows[0].n:'N/A'} paired origins. Native và matched có mẫu khác nhau; chỉ diễn giải timing/vintage qua các paired sensitivity đã ghép cả train/validation/test.`;
 renderImportance();if(HISTORICAL.series)renderHistoricalOos();
}
function renderFOMC(){
 const asset=el('eAsset').value,outcome=el('eOutcome').value;
 const rows=LATEST.fomc.filter(r=>r.asset===asset&&r.outcome===outcome);
 const bound=(x,side,unbounded)=>x===null?(unbounded?(side==='lower'?'−∞':'+∞'):'Chưa có'):Number(x).toFixed(4);
 el('fomcTable').innerHTML=table(['Loại thông tin','Hệ số thấp nhất','Hệ số cao nhất','Không bị chặn'],rows.map(r=>[{policy:'Chính sách',information:'Thông tin kinh tế'}[r.shock]||r.shock,bound(r.lower_per10bps,'lower',r.unbounded),bound(r.upper_per10bps,'upper',r.unbounded),r.unbounded?'Có':'Không']));
 const rg=LATEST.regimes.filter(r=>r.asset===asset&&r.outcome===outcome);
 el('regimeTable').innerHTML=table(['Hai nhóm so sánh','Loại thông tin','Cỡ mẫu hai nhóm','Chênh lệch (%)','q BH (HAC)','q BH (HC3)'],rg.map(r=>[r.contrast,r.shock,`${r.n_group0} / ${r.n_group1}`,latestNumber(r.beta),prob(r.qvalue_bh),prob(r.qvalue_hc3_bh)]));
}
function renderRV(){
 const s={asset:el('rvAsset').value,sampling_minutes:el('rvSampling').value,horizon_days:el('rvHorizon').value};
 const rows=LATEST.rvAblation.filter(r=>matches(r,s)),b=LATEST.rvBenchmarks.filter(r=>matches(r,s));
 el('rvTable').innerHTML=table(['Thay đổi nhóm dữ liệu','Số ngày','Chênh lệch QLIKE','Khoảng tin cậy 95%','q (BH)'],rows.map(r=>[`${humanVariant(r.base)} → ${humanVariant(r.added)}`,r.n_pairs,latestNumber(r.mean_loss_added_minus_base),interval(r.lower95,r.upper95),prob(r.qvalue_bh)]));
 el('rvBenchmarkTable').innerHTML=table(['Cấu hình / mốc so sánh','Số ngày','Chênh lệch QLIKE','Khoảng tin cậy 95%','q (BH)'],b.map(r=>[`${r.variant} / ${r.benchmark}`,r.n_pairs,latestNumber(r.mean_loss_added_minus_base),interval(r.lower95,r.upper95),prob(r.qvalue_bh)]));
}
function initializeRelease(){
 el('releaseSummary').textContent=LATEST.summary;
 el('pitTable').innerHTML=table(['Feature','Nguồn','Mức bằng chứng','Giả định còn lại'],LATEST.pit.map(r=>[r.feature,r.source,r.verification,r.remaining_assumption]));
 el('liveStatus').textContent=`Trạng thái đọc lúc ${LATEST.generatedLocal}: ${LATEST.live.prediction_files} forecast commits (${LATEST.live.prediction_rows} dự báo mô hình), ${LATEST.live.label_files} nhãn. Kỳ OOS kết thúc ${LATEST.live.fixed_end}; trạng thái đánh giá ${LATEST.live.performance}. ${LATEST.live.scheduler_installed?(LATEST.live.automation.provider==='github-actions'?'Tự động trên GitHub: pipeline mỗi giờ phút 15, giám sát phút 45; không cần bật máy cá nhân.':'Tự động: pipeline mỗi giờ phút 15, giám sát phút 45; máy bật, Admin đăng nhập và có mạng.'):'Chưa xác minh được lịch tự động.'} Lần vận hành gần nhất ${LATEST.live.last_run_local}.`;
 for(const outcome of [...new Set(LATEST.fomc.map(r=>r.outcome))])el('eOutcome').innerHTML+=`<option value="${esc(outcome)}">${esc(outcome==='intraday'?'Quanh thông báo · −10/+20 phút':outcome==='event_day'?'Ngày công bố':outcome.startsWith('post_')?'Sau '+outcome.slice(5)+' ngày':outcome)}</option>`;
 el('eOutcome').value='intraday';
 for(const id of ['fAsset','fScenario'])el(id).addEventListener('change',renderForecast);
 el('fScope').addEventListener('change',()=>{resetHistoricalRange();renderForecast();});
 for(const id of ['eAsset','eOutcome'])el(id).addEventListener('change',renderFOMC);
 for(const id of ['rvAsset','rvSampling','rvHorizon'])el(id).addEventListener('change',renderRV);
 initializeHistoricalOos();if(typeof window==='undefined'){renderFOMC();renderRV();}
}
initializeRelease();
