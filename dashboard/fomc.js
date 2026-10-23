/* Presentation of saved FOMC observations and coefficients. No fit or prediction. */
function orbitFomcPoints(event,asset,windowName){
 const series=event.assets[asset];
 return windowName==='intraday'?series.minute_path.map(([x,y])=>({x,y})):
  [{x:0,y:0},...Array.from({length:30},(_,i)=>({x:i+1,y:series.returns['post_'+(i+1)]}))];
}
function orbitFomcPlot(rows,{width=720,marker=null,xLabel='',yLabel='',title=''}={}){
 if(!rows.length)return '';
 const values=rows.flatMap(r=>[r.y,...(r.lo===undefined?[]:[r.lo,r.hi])]);
 if(!rows.every(r=>Number.isFinite(r.x))||!values.every(Number.isFinite))throw Error('Nonfinite FOMC plot value');
 const left=62,right=width-18,top=30,bottom=228,lo=Math.min(0,...values),hi=Math.max(0,...values),pad=(hi-lo||1)*.12,min=lo-pad,max=hi+pad;
 const first=rows[0].x,last=rows.at(-1).x,x=v=>left+(v-first)/(last-first||1)*(right-left),y=v=>bottom-(v-min)/(max-min)*(bottom-top);
 const f=new Intl.NumberFormat('vi-VN',{maximumFractionDigits:2}),line=points=>points.map((p,i)=>(i?'L':'M')+x(p.x).toFixed(3)+','+y(p.y).toFixed(3)).join(' ');
 let svg=`<title>${esc(title)}</title><text x="8" y="15" class="fomc-axis-label">${esc(yLabel)}</text>`;
 for(let i=0;i<5;i++){const value=min+(max-min)*i/4,py=y(value);svg+=`<line x1="${left}" x2="${right}" y1="${py}" y2="${py}" class="fomc-grid"/><text x="${left-8}" y="${py+4}" text-anchor="end" class="fomc-axis-label">${f.format(value)}</text>`;}
 svg+=`<line x1="${left}" x2="${right}" y1="${y(0)}" y2="${y(0)}" class="fomc-zero"/>`;
 const ticks=first<0?[-10,0,10,20]:[first,7,14,21,30];
 for(const tick of ticks)svg+=`<text x="${x(tick)}" y="${bottom+22}" text-anchor="middle" class="fomc-axis-label">${tick}</text>`;
 if(rows.every(r=>r.lo!==undefined)){const upper=rows.map(r=>({x:r.x,y:r.hi})),lower=rows.map(r=>({x:r.x,y:r.lo})).reverse();svg+=`<path d="${line(upper)} ${line(lower).replace(/^M/,'L')} Z" class="fomc-ci-band"/>`;}
 if(marker!==null&&marker>=first&&marker<=last)svg+=`<line x1="${x(marker)}" x2="${x(marker)}" y1="${top}" y2="${bottom}" class="fomc-event-marker"/><text x="${x(marker)+5}" y="${top+12}" class="fomc-axis-label">FOMC</text>`;
 svg+=`<path d="${line(rows)}" class="fomc-response-line"/>`;
 for(const row of rows)svg+=`<circle cx="${x(row.x)}" cy="${y(row.y)}" r="2.2" class="fomc-point"><title>${row.x}: ${f.format(row.y)}${row.lo===undefined?'':'; CI ['+f.format(row.lo)+'; '+f.format(row.hi)+']'}</title></circle>`;
 return svg+`<text x="${(left+right)/2}" y="278" text-anchor="middle" class="fomc-axis-label">${esc(xLabel)}</text>`;
}
function orbitStartFomc(download){
 const $=id=>document.getElementById(id),data=FOMC_RESEARCH;
 const dates=new Intl.DateTimeFormat('vi-VN',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'UTC'});
 const date=value=>dates.format(new Date(value+'T00:00:00Z'));
 const fmt=new Intl.NumberFormat('vi-VN',{maximumFractionDigits:4}),signed=v=>(v>0?'+':'')+fmt.format(v);
 const name=shock=>shock==='policy'?'Chính sách':'Thông tin kinh tế';
 const events=[...data.events].reverse();let mode='aggregate',ready=false,lastKey='',listBuilt=false;
 const width=()=>matchMedia('(max-width:760px)').matches?360:720;
 function prepare(){
  if(ready)return;ready=true;const s=data.sample;
  $('fomcSampleDescription').textContent=`${s.count} thông báo trong mẫu BTC/ETH · ${date(s.first_date)}–${date(s.last_date)} · ${s.pre2020} trước 2020 / ${s.post2020} từ 2020.`;
  $('fomcEventListSummary').textContent=`Danh sách ${s.count} thông báo dùng trong mẫu`;
  $('fomcEventDate').innerHTML=events.map(e=>`<option value="${e.date}">FOMC ${date(e.date)} · ${e.event_time_et.slice(11,16)} Eastern</option>`).join('');
 }
 function plot(id,rows,options){const el=$(id),w=width();el.setAttribute('viewBox',`0 0 ${w} 290`);el.innerHTML=orbitFomcPlot(rows,{width:w,...options});}
 const oldFomc=renderFOMC;
 function aggregate(){
  oldFomc();const asset=$('eAsset').value,outcome=$('eOutcome').value,shock=$('fomcAggregateShock').value;
  $('fomcSummary').innerHTML=LATEST.fomc.filter(r=>r.asset===asset&&r.outcome===outcome).map(r=>`<article class="fomc-card"><span>${name(r.shock)} · ${asset}</span><strong>${r.lower_per10bps===null?(r.unbounded?'−∞':'—'):fmt.format(r.lower_per10bps)} → ${r.upper_per10bps===null?(r.unbounded?'+∞':'—'):fmt.format(r.upper_per10bps)}%</strong><p>Miền hệ số tổng hợp từ ${data.sample.count} sự kiện.</p><small>+10 bps thành phần PC1 · miền nhận dạng</small></article>`).join('');
  const saved=data.intervals.filter(r=>r.asset===asset&&r.shock===shock&&r.outcome.startsWith('post_')).sort((a,b)=>Number(a.outcome.slice(5))-Number(b.outcome.slice(5)));
  plot('fomcAggregateChart',saved.map(r=>({x:Number(r.outcome.slice(5)),y:r.beta,lo:r.lower95,hi:r.upper95})),{xLabel:'Ngày sau thông báo · cộng dồn, không gồm ngày công bố',yLabel:'Phản ứng (% / +10 bps)',title:`${asset}: phản ứng với thành phần ${name(shock)}`});
  $('fomcAggregateCaption').textContent=`${asset} · ${name(shock)} · ${data.sample.count} thông báo · đường: hệ số tại phép tách tham chiếu; vùng tô: CI bootstrap 95% (${saved[0].draws} lượt).`;
  $('fomcReferenceTable').innerHTML=table(['Thành phần','Hệ số (% / +10 bps)','CI bootstrap thấp','CI bootstrap cao','Lượt bootstrap'],data.intervals.filter(r=>r.asset===asset&&r.outcome===outcome).map(r=>[name(r.shock),r.beta,r.lower95,r.upper95,r.draws]));
 }
 function selected(){return events.find(e=>e.date===$('fomcEventDate').value);}
 function eventCsv(){
  const e=selected(),asset=$('eAsset').value,s=e.assets[asset],common={date:e.date,asset,event_time_et:e.event_time_et,event_time_utc:e.event_time_utc,statement_url:e.statement_url,policy_bps:e.policy_bps,information_bps:e.information_bps};
  return [...s.minute_path.map(([minute,value])=>({...common,window:'intraday_path',minute_from_announcement:minute,horizon_days:'',actual_log_return_pct:value})),...Object.entries(s.returns).map(([window,value])=>({...common,window,minute_from_announcement:'',horizon_days:window.startsWith('post_')?Number(window.slice(5)):'',actual_log_return_pct:value}))];
 }
 function eventView(){
  const e=selected(),asset=$('eAsset').value,s=e.assets[asset],windowName=$('fomcEventWindow').value,index=events.indexOf(e);
  $('fomcPreviousEvent').disabled=index===events.length-1;$('fomcNextEvent').disabled=index===0;
  $('fomcEventTitle').textContent=`Thông báo FOMC ngày ${date(e.date)}`;
  $('fomcEventTime').textContent=`${e.event_time_et.slice(11,16)} US Eastern (UTC${e.event_time_et.slice(19)}) = ${e.event_time_utc.slice(11,16)} UTC · ${e.stress?'Căng thẳng: VIX trước sự kiện ≥25':'Bình thường: VIX trước sự kiện <25'}`;
  $('fomcStatementLink').href=e.statement_url;
  $('fomcEventShocks').innerHTML=`<span>Shock chính sách <strong>${signed(e.policy_bps)} bps</strong></span><span>Shock thông tin kinh tế <strong>${signed(e.information_bps)} bps</strong></span>`;
  $('fomcEventReturns').innerHTML=[['intraday','−10/+20 phút'],['event_day','Ngày công bố · UTC'],['post_7','7 ngày tiếp theo'],['post_30','30 ngày tiếp theo']].map(([key,label])=>`<article><span>${asset} · ${label}</span><strong>${signed(s.returns[key])}%</strong><small>Lợi suất thực tế</small></article>`).join('');
  $('fomcEventChartTitle').textContent=`${asset} · ${windowName==='intraday'?'Diễn biến quanh giờ công bố':'Diễn biến 30 ngày tiếp theo'}`;
  plot('fomcEventChart',orbitFomcPoints(e,asset,windowName),{marker:windowName==='intraday'?0:null,xLabel:windowName==='intraday'?'Phút so với giờ thông báo · mốc giá tại −10 phút':'Ngày sau thông báo · mốc giá là cuối ngày công bố UTC',yLabel:'Log return thực tế (%)',title:`${asset}, FOMC ${date(e.date)}: diễn biến thực tế`});
  $('fomcEventCaption').textContent=windowName==='intraday'?'Nguồn: Coinbase '+asset+'/USD, giá đóng nến 1 phút; đường bắt đầu từ 0 tại −10 phút. Vạch đứng là giờ thông báo.':'Nguồn: Coin Metrics '+asset+'/USD, giá ngày UTC. Lợi suất cộng dồn ngày 1–h bắt đầu sau ngày công bố; không nối với lợi suất cửa sổ phút.';
  $('fomcEventTable').innerHTML=table(['Cửa sổ','Lợi suất thực tế (%)'],Object.entries(s.returns).map(([key,value])=>[key==='intraday'?'−10/+20 phút':key==='event_day'?'Ngày công bố · UTC':'Sau '+key.slice(5)+' ngày · cộng dồn',value]));
 }
 function render(){
  prepare();const key=[mode,$('eAsset').value,$('eOutcome').value,$('fomcAggregateShock').value,$('fomcEventDate').value,$('fomcEventWindow').value,width()].join('|');
  if(key===lastKey)return;lastKey=key;if(mode==='aggregate')aggregate();else eventView();
 }
 function setMode(next){
  mode=next;for(const [id,value] of [['fomcAggregateTab','aggregate'],['fomcEventTab','event']]){$(id).setAttribute('aria-selected',String(value===mode));$(id).tabIndex=value===mode?0:-1;}
  $('fomcAggregatePanel').hidden=mode!=='aggregate';$('fomcEventPanel').hidden=mode!=='event';render();
 }
 renderFOMC=render;window.orbitRenderFomc=render;
 for(const id of ['eAsset','eOutcome']){$(id).removeEventListener('change',oldFomc);$(id).addEventListener('change',render);}
 for(const id of ['fomcAggregateShock','fomcEventDate','fomcEventWindow'])$(id).addEventListener('change',render);
 $('fomcAggregateTab').addEventListener('click',()=>setMode('aggregate'));$('fomcEventTab').addEventListener('click',()=>setMode('event'));
 for(const id of ['fomcAggregateTab','fomcEventTab'])$(id).addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();setMode(e.key==='Home'?'aggregate':e.key==='End'?'event':mode==='event'?'aggregate':'event');$(mode==='aggregate'?'fomcAggregateTab':'fomcEventTab').focus();}});
 for(const [id,step] of [['fomcPreviousEvent',1],['fomcNextEvent',-1]])$(id).addEventListener('click',()=>{const index=events.indexOf(selected())+step;if(events[index]){$('fomcEventDate').value=events[index].date;render();}});
 $('fomcEventList').addEventListener('toggle',()=>{
  if(!$('fomcEventList').open||listBuilt)return;prepare();listBuilt=true;
  $('fomcEventListTable').innerHTML='<table><thead><tr><th>Thông báo</th><th>US Eastern</th><th>UTC</th><th>BTC −10/+20 phút</th><th>ETH −10/+20 phút</th></tr></thead><tbody>'+events.map(e=>`<tr><td><button type="button" class="fomc-date-link" data-fomc-date="${e.date}">${date(e.date)}</button></td><td>${e.event_time_et.slice(11,16)} (${esc(e.event_time_et.slice(19))})</td><td>${e.event_time_utc.slice(11,16)}</td><td>${signed(e.assets.BTC.returns.intraday)}%</td><td>${signed(e.assets.ETH.returns.intraday)}%</td></tr>`).join('')+'</tbody></table>';
 });
 $('fomcEventListTable').addEventListener('click',e=>{const b=e.target.closest('[data-fomc-date]');if(b){$('fomcEventDate').value=b.dataset.fomcDate;setMode('event');$('fomcEventDate').focus();}});
 $('exportFomcEvent').addEventListener('click',()=>download(eventCsv(),`fomc_${$('fomcEventDate').value}_${$('eAsset').value.toLowerCase()}_observations.csv`));
 window.orbitExportFomc=()=>mode==='event'?$('exportFomcEvent').click():download(LATEST.fomc.filter(r=>r.asset===$('eAsset').value&&r.outcome===$('eOutcome').value),'fomc_rotation_ranges.csv');
 window.orbitFomcEventCsvRows=eventCsv;
 let resize=null;window.addEventListener('resize',()=>{if(document.documentElement.dataset.workspace!=='fomc')return;if(resize!==null)cancelAnimationFrame(resize);resize=requestAnimationFrame(()=>{resize=null;render();});});
}
