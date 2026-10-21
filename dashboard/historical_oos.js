const historyPairs=[['long_own','long_macro'],['common_own','common_macro'],['common_macro','common_usd'],['common_own','common_usd']];
const historyColumns={elastic_net:2,gradient_boosting:3,historical_mean:4,natural_benchmark:5};
const historyVariantNames={long_own:'Chỉ crypto',long_macro:'Có vĩ mô',common_own:'Chỉ crypto',common_macro:'Có vĩ mô',common_usd:'Có vĩ mô & USD'};
const historyCache=new Map();
const historyShift=(day,n)=>new Date(Date.parse(day+'T00:00:00Z')+n*86400000).toISOString().slice(0,10);
const historyKey=(s,variant)=>[s.asset,s.scenario,variant,s.target].join('|');
const historyLoss=(actual,predicted,target)=>target==='return'?(actual-predicted)**2:Math.log(predicted)+actual/predicted;
function historySelection(){return {...selectedForecast(),pair:historyPairs[Number(el('forecastPair').value||0)]};}
function historyBounds(){const scope=el('fScope').value;return scope==='pooled'?[HISTORICAL.date_min,HISTORICAL.date_max]:[scope+'-01-01',[scope+'-12-31',HISTORICAL.date_max].sort()[0]];}
function resetHistoricalRange(){
 const [start,end]=historyBounds();
 for(const id of ['historyStart','historyEnd']){el(id).min=start;el(id).max=end;}
 el('historyStart').value=start;el('historyEnd').value=end;
}
function historicalRows(){
 const s=historySelection(),cacheKey=[s.asset,s.scenario,s.target,s.model,...s.pair].join('|');
 if(!historyCache.has(cacheKey)){
  const left=HISTORICAL.series[historyKey(s,s.pair[0])],right=HISTORICAL.series[historyKey(s,s.pair[1])];
  const lookup=new Map(left.map(r=>[r[0],r])),col=historyColumns[s.model],benchmark=s.target==='return'?'historical_mean':'natural_benchmark';
  const rows=right.map(r=>{const base=lookup.get(r[0]);if(!base||base[1]!==r[1])throw Error('Historical origins/targets are not paired');
   return {date:r[0],actual:r[1],base:base[col],added:r[col],benchmark:r[historyColumns[benchmark]],year:r[6]};});
  historyCache.set(cacheKey,rows);
 }
 const start=el('historyStart').value,end=el('historyEnd').value;
 return historyCache.get(cacheKey).filter(r=>r.date>=start&&r.date<=end&&(s.scope==='pooled'||String(r.year)===s.scope));
}
function historyChart(rows,curves,label){
 const W=900,H=270,L=82,R=18,T=18,B=40;
 const all=curves.flatMap(c=>c.values),minimum=Math.min(0,...all),maximum=Math.max(0,...all),pad=(maximum-minimum||1)*.08,lo=minimum-pad,hi=maximum+pad;
 const first=Date.parse(rows[0].date+'T00:00:00Z'),last=Date.parse(rows[rows.length-1].date+'T00:00:00Z');
 const x=i=>last===first?(L+W-R)/2:L+(Date.parse(rows[i].date+'T00:00:00Z')-first)/(last-first)*(W-L-R),y=v=>T+(hi-v)/(hi-lo)*(H-T-B);
 let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${label}">`;
 for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4;svg+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="#dce7eb"/><text x="2" y="${y(v)+4}">${Number(v).toPrecision(3)}</text>`;}
 svg+=`<line x1="${L}" x2="${W-R}" y1="${y(0)}" y2="${y(0)}" stroke="#8ca5b3" stroke-dasharray="4 4"/>`;
 for(const curve of curves){const points=curve.values.map((v,i)=>`${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(' ');svg+=`<polyline fill="none" stroke="${curve.color}" stroke-width="${curve.color==='#64748b'?1:1.8}" points="${points}"/>`;if(rows.length===1)svg+=`<circle cx="${x(0)}" cy="${y(curve.values[0])}" r="4" fill="${curve.color}"/>`;}
 return svg+`<text x="${L}" y="${H-10}">${rows[0].date}</text><text text-anchor="end" x="${W-R}" y="${H-10}">${rows[rows.length-1].date} · UTC</text></svg>`;
}
function historyFold(s,variant,row){return HISTORICAL.folds[historyKey(s,variant)+'|'+row.year];}
function renderHistoryPoint(rows=historicalRows()){
 if(!rows.length)return;
 const s=historySelection(),row=rows.find(r=>r.date===el('historyDay').value)||rows[rows.length-1];
 el('historyDay').value=row.date;
 const base=historyFold(s,s.pair[0],row),added=historyFold(s,s.pair[1],row),lag=s.scenario==='matched_asof_d4'?4:3,info=historyShift(row.date,-lag),availability=historyShift(info,2);
 el('historyPointTable').innerHTML=table(['Origin UTC','Thực tế','Base','Added','Benchmark','Δloss added − base'],[[row.date,latestNumber(row.actual),latestNumber(row.base),latestNumber(row.added),latestNumber(row.benchmark),latestNumber(historyLoss(row.actual,row.added,s.target)-historyLoss(row.actual,row.base,s.target))]]);
 const pass=base.last_fit_label_available<=base.fit_cutoff&&base.last_tuning_label_available<=base.fit_cutoff&&added.last_fit_label_available<=added.fit_cutoff&&added.last_tuning_label_available<=added.fit_cutoff&&availability<=historyShift(row.date,-1);
 if(!pass)throw Error('Historical chronology violation');
 el('historyTimingTable').innerHTML=table(['Mốc / quy tắc','Base','Added'],[
  ['Information day',info,info],['Market observation day',historyShift(info,-1),historyShift(info,-1)],
  ['Giả định feature khả dụng (00:00 UTC)',availability,availability],['Receipt cutoff (00:00 UTC)',historyShift(row.date,-1),historyShift(row.date,-1)],
  ['Fit cutoff (00:00 UTC)',base.fit_cutoff,added.fit_cutoff],['Nhãn train cuối cùng khả dụng',base.last_fit_label_available,added.last_fit_label_available],
  ['Nhãn tuning cuối cùng khả dụng',base.last_tuning_label_available,added.last_tuning_label_available],['Số hàng train',base.n_fit,added.n_fit],
  ['Target close (00:00 UTC)',historyShift(row.date,1),historyShift(row.date,1)],['Nhãn target khả dụng (00:00 UTC)',historyShift(row.date,2),historyShift(row.date,2)],['Chronology', 'Đạt','Đạt']]);
 el('historyModelHashes').textContent=`Model ${s.model} · fold ${row.year} · Base SHA-256: ${base.model_sha256[s.model]} · Added SHA-256: ${added.model_sha256[s.model]}`;
}
function renderHistoricalOos(){
 const s=historySelection(),start=el('historyStart').value,end=el('historyEnd').value,rows=historicalRows(),oracle=s.scenario==='matched_latest_d3';
 const empty=!start||!end||start>end||!rows.length;
 el('exportHistoricalOos').disabled=empty;el('historyDay').disabled=empty;
 if(empty){
  el('historyContext').textContent=start>end?'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.':'Không có origins đủ điều kiện trong khoảng này; chọn khoảng ngày khác.';
  for(const id of ['historyCount','historyBaseLoss','historyAddedLoss','historyBenchmarkDelta'])el(id).textContent=id==='historyCount'?'0':'—';
  for(const id of ['historyPredictionChart','historyLossChart','historyPointTable','historyTimingTable','historyDay'])el(id).innerHTML='';
  el('historyLossSummary').textContent='';el('historyModelHashes').textContent='';return;
 }
 const selected=el('historyDay').value;el('historyDay').innerHTML=rows.map(r=>`<option value="${r.date}">${r.date}</option>`).join('');
 el('historyDay').value=rows.some(r=>r.date===selected)?selected:rows[rows.length-1].date;
 const mean=values=>values.reduce((a,b)=>a+b,0)/values.length,base=rows.map(r=>historyLoss(r.actual,r.base,s.target)),added=rows.map(r=>historyLoss(r.actual,r.added,s.target)),bench=rows.map(r=>historyLoss(r.actual,r.benchmark,s.target));
 const delta=added.map((v,i)=>v-base[i]);let sum=0;const cumulative=delta.map(v=>sum+=v);
 el('historyCount').textContent=String(rows.length);el('historyBaseLoss').textContent=latestNumber(mean(base));el('historyAddedLoss').textContent=latestNumber(mean(added));el('historyBenchmarkDelta').textContent=latestNumber(mean(added)-mean(bench));
 el('historyContext').textContent=`${s.asset.toUpperCase()} · ${s.pair[0].startsWith('long')?'Mẫu dài':'Mẫu chung 2019+'} · ${historyVariantNames[s.pair[0]]} → ${historyVariantNames[s.pair[1]]} · ${rows[0].date} đến ${rows[rows.length-1].date} · ${s.target==='return'?'MSE log return; benchmark bình quân train':'QLIKE squared return; benchmark bình quân r² 30 ngày'}. ${oracle?'EX POST ORACLE: counterfactual dùng vintage mới, không phải dự báo as-of.':'Phát lại ngoài mẫu lịch sử theo fold thời gian.'} Ngày thiếu đầu vào được loại, không nội suy dự báo.`;
 el('historyPredictionChart').innerHTML=historyChart(rows,[{values:rows.map(r=>r.actual),color:'#64748b'},{values:rows.map(r=>r.base),color:'#ad5f2c'},{values:rows.map(r=>r.added),color:'#087196'},{values:rows.map(r=>r.benchmark),color:'#7e67a6'}],'Dự báo lịch sử và thực tế');
 el('historyLossChart').innerHTML=historyChart(rows,[{values:cumulative,color:'#087196'}],'Loss added trừ base cộng dồn');
 el('historyLossSummary').textContent=`Δloss trung bình added − base: ${latestNumber(mean(delta))}; tổng: ${latestNumber(sum)}. Âm là added tốt hơn trong khoảng đang chọn. Thống kê mô tả, không có kiểm định significance cho đoạn tùy chọn.`;
 renderHistoryPoint(rows);
}
function historicalOosCsv(){
 const s=historySelection(),lag=s.scenario==='matched_asof_d4'?4:3;
 const columns=['evaluation_mode','asset','target','model','scenario','origin_utc','outer_year','base_variant','added_variant','actual','base_predicted','added_predicted','benchmark_predicted','base_loss','added_loss','benchmark_loss','information_day','assumed_feature_available_utc','receipt_cutoff_utc','fit_cutoff_utc','base_last_train_label_available','added_last_train_label_available','last_tuning_label_available','target_close_utc','target_label_available_utc','base_model_sha256','added_model_sha256','payload_sha256'];
 const quote=x=>'"'+String(x===undefined||x===null?'':x).replace(/"/g,'""')+'"',atMidnight=x=>x+'T00:00:00Z';
 const rows=historicalRows().map(r=>{const base=historyFold(s,s.pair[0],r),added=historyFold(s,s.pair[1],r),info=historyShift(r.date,-lag);
  return [s.scenario==='matched_latest_d3'?'historical_ex_post_oracle':HISTORICAL.mode,s.asset,s.target,s.model,s.scenario,atMidnight(r.date),r.year,...s.pair,r.actual,r.base,r.added,r.benchmark,historyLoss(r.actual,r.base,s.target),historyLoss(r.actual,r.added,s.target),historyLoss(r.actual,r.benchmark,s.target),info,atMidnight(historyShift(info,2)),atMidnight(historyShift(r.date,-1)),atMidnight(base.fit_cutoff),base.last_fit_label_available,added.last_fit_label_available,added.last_tuning_label_available,atMidnight(historyShift(r.date,1)),atMidnight(historyShift(r.date,2)),base.model_sha256[s.model],added.model_sha256[s.model],HISTORICAL.audit.data_sha256];});
 return '\ufeff'+[columns,...rows].map(r=>r.map(quote).join(',')).join('\r\n');
}
function initializeHistoricalOos(){
 resetHistoricalRange();
 el('historyAuditBadge').textContent=`Đã kiểm chứng ${HISTORICAL.audit.artifacts_replayed} mô hình`;
 el('historyAuditDetail').textContent=`Đã tính lại ${HISTORICAL.audit.learned_predictions_checked} dự báo từ artifacts và ${HISTORICAL.audit.benchmark_predictions_checked} benchmark predictions; đối chiếu với CSV đã khóa, kiểm tra fold chronology và train-only scaling. Không huấn luyện lại model. SHA-256 bộ hiển thị: ${HISTORICAL.audit.data_sha256}.`;
 for(const id of ['historyStart','historyEnd'])el(id).addEventListener('change',renderHistoricalOos);
 el('historyDay').addEventListener('change',()=>renderHistoryPoint());
 el('resetHistoricalOos').addEventListener('click',()=>{resetHistoricalRange();renderHistoricalOos();});
 el('exportHistoricalOos').addEventListener('click',()=>{
  const url=URL.createObjectURL(new Blob([historicalOosCsv()],{type:'text/csv;charset=utf-8'})),link=document.createElement('a'),s=historySelection();
  link.href=url;link.download=`historical_oos_${s.asset}_${s.target}_${s.scenario}_${el('historyStart').value}_${el('historyEnd').value}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 });
}
