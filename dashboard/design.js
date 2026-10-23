/* Orbit 3 presentation. Scientific functions, payload values and units stay intact. */
const ORBIT_VIEWS=['transmission','forecast','fomc','advanced','methods','operations'];
const ORBIT_SHOCKS=['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps','monetary'];
function orbitParseRoute(hash){
 const [path,query='']=String(hash||'').replace(/^#/,'').split('?');
 const aliases={responses:'transmission',rolling:'transmission',quantile:'advanced',joint:'advanced',rv:'forecast',pit:'methods',overview:'methods'};
 const p=new URLSearchParams(query),view=ORBIT_VIEWS.includes(path)?path:aliases[path]||'transmission';
 const asset=['btc','eth'].includes(p.get('asset'))?p.get('asset'):'btc',shock=ORBIT_SHOCKS.includes(p.get('shock'))?p.get('shock'):'vix_change',regime=['full','calm','stress'].includes(p.get('regime'))?p.get('regime'):'full';
 const h=Number(p.get('h')||1),horizon=Number.isInteger(h)&&h>=1&&h<=30?String(h):'1';
 return {view,asset,shock,regime,horizon,compare:p.get('compare')!=='0'};
}
function orbitCurveRows(asset,shock,regime){return (shock==='monetary'?DATA.monetary:DATA.daily).filter(r=>r.asset===asset&&r.shock===shock&&r.regime===regime).sort((a,b)=>a.horizon_days-b.horizon_days);}
function orbitLine(points){
 if(!points.length)return '';if(points.length<3)return points.map((p,i)=>(i?'L':'M')+p.map(v=>v.toFixed(2)).join(',')).join(' ');
 // Monotone cubic joins pass through every observed horizon without overshoot.
 const slopes=points.slice(1).map((p,i)=>(p[1]-points[i][1])/(p[0]-points[i][0]||1));
 const tangents=points.map((_,i)=>{if(!i)return slopes[0];if(i===points.length-1)return slopes.at(-1);const a=slopes[i-1],b=slopes[i];return a*b<=0?0:Math.sign(a)*Math.min(Math.abs((a+b)/2),3*Math.min(Math.abs(a),Math.abs(b)));});
 let path='M'+points[0].map(v=>v.toFixed(2)).join(',');
 for(let i=1;i<points.length;i++){const a=points[i-1],b=points[i],dx=(b[0]-a[0])/3;path+=` C${(a[0]+dx).toFixed(2)},${(a[1]+tangents[i-1]*dx).toFixed(2)} ${(b[0]-dx).toFixed(2)},${(b[1]-tangents[i]*dx).toFixed(2)} ${b[0].toFixed(2)},${b[1].toFixed(2)}`;}
 return path;
}
function orbitResponseScene(selected,other=[],analogue=[],size={width:720,height:330}){
 const values=selected.flatMap(r=>[r.lower95,r.upper95]).concat(other.map(r=>r.beta_pct),analogue.map(r=>r.observed_cumulative_pct));
 const low=Math.min(0,...values),high=Math.max(0,...values),pad=(high-low||1)*.11,min=low-pad,max=high+pad;
 const geometry={left:size.width<500?44:62,right:size.width-24,top:30,bottom:size.height-60,...size};
 const X=h=>geometry.left+(h-1)/29*(geometry.right-geometry.left),Y=v=>geometry.bottom-(v-min)/(max-min)*(geometry.bottom-geometry.top);
 const point=r=>[X(r.horizon_days),Y(r.beta_pct)];
 return {min,max,geometry,zero:Y(0),selected:selected.map(point),other:other.map(point),lower:selected.map(r=>[X(r.horizon_days),Y(r.lower95)]),upper:selected.map(r=>[X(r.horizon_days),Y(r.upper95)]),analogue:analogue.map(r=>[X(r.horizon_days),Y(r.observed_cumulative_pct)]),ticks:Array.from({length:5},(_,i)=>{const value=min+(max-min)*i/4;return {value,y:Y(value)};})};
}
function orbitStartStudio(){
 if(typeof window==='undefined'||!document.documentElement)return;
 const $=id=>document.getElementById(id),root=document.documentElement,reduce=matchMedia('(prefers-reduced-motion: reduce)');
 const numberFormats=new Map(),cellFormat=new Intl.NumberFormat('vi-VN',{maximumSignificantDigits:8});
 const number=(v,d=3)=>{if(!numberFormats.has(d))numberFormats.set(d,new Intl.NumberFormat('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d}));return numberFormats.get(d).format(Number(v));};
 const signed=(v,d=3)=>(v>0?'+':'')+number(v,d),percent=v=>signed(v)+'%';
 const dayFormat=new Intl.DateTimeFormat('vi-VN',{timeZone:'UTC'}),dateCache=new Map();
 const date=s=>{if(!dateCache.has(s))dateCache.set(s,dayFormat.format(new Date(s+'T00:00:00Z')));return dateCache.get(s);};
 const titles={transmission:['Từ vĩ mô đến crypto.','Một thay đổi kinh tế. Hai tài sản. 30 ngày phản ứng.'],forecast:['Dự báo phải được kiểm chứng.','Đối chiếu với kết quả đã xảy ra, rồi mới đọc các kiểm định.'],fomc:['Phản ứng quanh FOMC.','Xem kết quả chung từ nhiều cuộc họp hoặc diễn biến của từng thông báo.'],advanced:['Nhìn sâu hơn vào phản ứng.','Phân vị và VAR trả lời hai câu hỏi khác nhau.'],methods:['Biết nguồn. Hiểu giới hạn.','Phương pháp, thời điểm thông tin khả dụng và phạm vi kết luận.'],operations:['Dữ liệu mới đến đâu?','Theo dõi vận hành và dự báo mới theo kỳ đánh giá đã chốt.']};
 let toastTimer,view=root.dataset.workspace||'transmission',pinned=false,displayedPoint=null,animationFrame=null,liveScene=null,hoverDay=null,activeAnalogue=null,lockedAnalogue=null,rollingRange=null,rollingSelection='',brush=null,lastAdvanced='quantile';
 const chart=$('responseChart');
 window.orbitOwnsResponseChart=true;
 for(const id of ['asset','regime','horizon','mobileWorkspace']){$(id).setAttribute('tabindex','-1');$(id).setAttribute('aria-hidden','true');}
 const scientificTable=table;
 const localCell=value=>{if(typeof value==='number')return cellFormat.format(value);if(typeof value!=='string')return value;if(/^[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(value))return cellFormat.format(Number(value));if(value.startsWith('[')&&value.endsWith(']'))return value.replace(/[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi,n=>cellFormat.format(Number(n)));return value;};
 table=function(headers,rows){return scientificTable(headers,rows.map(row=>row.map(localCell)));};
 const analogueIndex=new Map(),analogueSeries=new Map();
 for(const row of DATA.analogues){const prefix=[row.asset,row.shock,row.regime].join('|'),key=prefix+'|'+row.horizon_days,seriesKey=prefix+'|'+row.date_utc;if(!analogueIndex.has(key))analogueIndex.set(key,[]);analogueIndex.get(key).push(row);if(!analogueSeries.has(seriesKey))analogueSeries.set(seriesKey,[]);analogueSeries.get(seriesKey).push(row);}
 for(const series of analogueSeries.values())series.sort((a,b)=>a.horizon_days-b.horizon_days);
 const seriesFor=row=>analogueSeries.get([row.asset,row.shock,row.regime,row.date_utc].join('|'))||[];
 function toast(message){clearTimeout(toastTimer);$('orbitToast').textContent=message;$('orbitToast').hidden=false;toastTimer=setTimeout(()=>$('orbitToast').hidden=true,2800);}
 window.orbitToast=toast;
 function setTheme(theme){root.dataset.theme=theme;$('themeToggle').setAttribute('aria-pressed',String(theme==='light'));$('themeToggle').setAttribute('aria-label',theme==='dark'?'Chuyển sang giao diện sáng':'Chuyển sang giao diện tối');try{localStorage.setItem('orbit-theme-aurora',theme);}catch(_){}}
 let savedTheme=null;try{savedTheme=localStorage.getItem('orbit-theme-aurora');}catch(_){}
 setTheme(savedTheme==='light'?'light':'dark');
 window.orbitToggleTheme=()=>{setTheme(root.dataset.theme==='dark'?'light':'dark');};
 $('themeToggle').addEventListener('click',window.orbitToggleTheme);
 // The active button paints its own background; no synchronous page layout.
 $('navActive').hidden=true;
 let urlFrame=null,urlTimer=null;
 function syncUrl(){if(urlFrame!==null)cancelAnimationFrame(urlFrame);if(urlTimer!==null)clearTimeout(urlTimer);urlFrame=requestAnimationFrame(()=>{urlFrame=null;urlTimer=setTimeout(()=>{urlTimer=null;try{const p=new URLSearchParams({asset:$('asset').value,shock:$('shock').value,regime:$('regime').value,h:$('horizon').value,compare:$('compareAssets').checked?'1':'0'}),hash='#'+view+'?'+p.toString();if(location.hash!==hash)history.replaceState(null,'',hash);}catch(_){}},0);});}
 const previousWorkspace=showWorkspace;
 let lastWorkspace=null;
 showWorkspace=function(next){
  if(!ORBIT_VIEWS.includes(next))next='transmission';
  if(next===lastWorkspace)return;
  lastWorkspace=next;
  const changed=view!==next;view=next;previousWorkspace(next);root.dataset.workspace=next;
  $('designBreadcrumb').textContent=WORKSPACE_NAMES[next];$('designTitle').textContent=titles[next][0];$('designDescription').textContent=titles[next][1];$('designEyebrow').textContent='MACRO × CRYPTO / '+String(ORBIT_VIEWS.indexOf(next)+1).padStart(2,'0');
  for(const key of ORBIT_VIEWS){const b=$('tab-'+key);if(key===next)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
  for(const b of document.querySelectorAll('.bottom-nav [data-goto]')){if(b.dataset.goto===next)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
  $('bottomMore').setAttribute('aria-current',['fomc','advanced','methods','operations'].includes(next)?'page':'false');
  $('topExport').setAttribute('aria-label','Tải CSV · '+WORKSPACE_NAMES[next]);
  if(changed&&!reduce.matches)for(const id of WORKSPACE_GROUPS[next]){const panel=$(id);panel.classList.remove('workspace-enter');requestAnimationFrame(()=>panel.classList.add('workspace-enter'));}
  if(next==='fomc'&&typeof window.orbitRenderFomc==='function')window.orbitRenderFomc();if(next==='advanced')varData();
  if(next==='operations'&&typeof window.orbitRenderLiveData==='function')window.orbitRenderLiveData();
  syncUrl();
 };
 function go(next){if(window.scrollY)window.scrollTo({top:0,behavior:'instant'});showWorkspace(next);for(const id of ['navDrawer','glossaryDialog'])if($(id).open)$(id).close();}
 for(const b of document.querySelectorAll('[data-goto]'))b.addEventListener('click',()=>go(b.dataset.goto));
 $('openNavigation').addEventListener('click',()=>{if(matchMedia('(max-width:760px)').matches)$('navDrawer').showModal();else $('collapseSidebar').click();});
 $('bottomMore').addEventListener('click',()=>$('navDrawer').showModal());
 $('collapseSidebar').addEventListener('click',()=>{const collapsed=root.dataset.navCollapsed!=='true';root.dataset.navCollapsed=String(collapsed);$('collapseSidebar').setAttribute('aria-expanded',String(!collapsed));$('collapseSidebar').setAttribute('aria-label',collapsed?'Mở rộng menu':'Thu gọn menu');try{localStorage.setItem('orbit-nav-collapsed',String(collapsed));}catch(_){}});
 $('learnMethods').addEventListener('click',()=>go('methods'));
 document.querySelector('.brand').addEventListener('click',e=>{e.preventDefault();go('transmission');});
 document.querySelector('.skip-link').addEventListener('click',e=>{e.preventDefault();$('mainContent').setAttribute('tabindex','-1');$('mainContent').focus();$('mainContent').scrollIntoView({block:'start',behavior:'instant'});});
 for(const b of document.querySelectorAll('[data-close]'))b.addEventListener('click',()=>$(b.dataset.close).close());
 const sheet=$('filterSheet'),controls=$('responseControls');
 $('openFilters').addEventListener('click',()=>{$('sheetControls').append(controls);sheet.showModal();});
 const restoreControls=()=>{$('controlHome').append(controls);};sheet.addEventListener('close',restoreControls);
 $('applyMobileFilters').addEventListener('click',()=>sheet.close());
 let resizeFrame=null;window.addEventListener('resize',()=>{if(sheet.open&&innerWidth>760)sheet.close();if(resizeFrame!==null)cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{resizeFrame=null;drawResponse(false);});});
 // Segmented controls retain native select IDs for research functions and tests.
 function syncControls(){
  const asset=$('asset').value,regime=$('regime').value,h=$('horizon').value;
  $('assetHelp').dataset.term=asset;
  for(const kind of ['asset','regime']){const value=$(kind).value,buttons=[...document.querySelectorAll('[data-'+kind+']')];buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset[kind]===value)));const thumb=document.querySelector('.'+kind+'-segment .segment-thumb');thumb.style.transform=`translateX(${buttons.findIndex(b=>b.dataset[kind]===value)*100}%)`;}
  $('horizonSlider').value=h;$('horizonOutput').textContent=h;
  for(const b of document.querySelectorAll('[data-horizon]'))b.setAttribute('aria-pressed',String(b.dataset.horizon===h));
  const name=$('shock').selectedOptions[0].textContent;$('mobileFilterLabel').textContent=`${asset.toUpperCase()} · ${name} · ${h} ngày`;
  $('designSampleMeta').textContent=asset.toUpperCase()+' · '+regime;syncUrl();
 }
 for(const key of ['asset','regime'])for(const b of document.querySelectorAll('[data-'+key+']'))b.addEventListener('click',()=>{if($(key).value===b.dataset[key])return;$(key).value=b.dataset[key];lockedAnalogue=null;renderResponse();});
 function chooseDay(h,pin=false){const value=String(Math.max(1,Math.min(30,h)));if($('horizon').value===value&&(!pin||pinned))return;$('horizon').value=value;if(pin)pinned=true;renderResponse();}
 for(const b of document.querySelectorAll('[data-horizon]'))b.addEventListener('click',()=>chooseDay(Number(b.dataset.horizon)));
 let sliderFrame=null;$('horizonSlider').addEventListener('input',()=>{const value=Number($('horizonSlider').value);$('horizonOutput').textContent=String(value);if(sliderFrame)cancelAnimationFrame(sliderFrame);sliderFrame=requestAnimationFrame(()=>{sliderFrame=null;chooseDay(value);});});
 $('compareAssets').addEventListener('change',()=>{drawResponse(false);syncUrl();});
 $('unpinResponse').addEventListener('click',()=>{pinned=false;drawResponse(false);$('pinState').textContent='NGÀY ĐANG CHỌN';$('unpinResponse').hidden=true;});
 function countPoint(value){const element=$('responsePoint');displayedPoint=value;element.dataset.finalValue=percent(value);element.textContent=percent(value);element.dataset.animating='false';}
 let responseTableKey='';
 function responseTable(){const details=$('responseDataTable').closest('details');if(!details.open)return;const key=[$('asset').value,$('shock').value,$('regime').value].join('|');if(key===responseTableKey)return;const rows=responseRows();$('responseDataTable').innerHTML=table(['Ngày','Tài sản','Ước lượng (%)','CI thấp','CI cao','n','BH q'],rows.map(r=>[r.horizon_days,r.asset.toUpperCase(),number(r.beta_pct),number(r.lower95),number(r.upper95),number(r.nobs,0),r.qvalue_bh===null?'—':number(r.qvalue_bh)]));responseTableKey=key;}
 $('responseDataTable').closest('details').addEventListener('toggle',responseTable);
 function responseDetail(){
  const rows=responseRows(),row=rows.find(r=>r.horizon_days===Number($('horizon').value));if(!row)return;
  const crosses=row.lower95<=0&&row.upper95>=0;
  $('responseMetricLabel').textContent=`${row.asset.toUpperCase()} · sau ${row.horizon_days} ngày`;countPoint(row.beta_pct);
  $('responseCI').textContent=`CI 95%: ${number(row.lower95)}% đến ${number(row.upper95)}%`;
  $('responseVerdict').textContent=crosses?'Chưa rõ chiều phản ứng: khoảng tin cậy chứa 0.':'Khoảng tin cậy nằm về một phía của 0. Cần đọc cùng BH q.';
  $('responseSample').textContent=number(row.nobs,0)+' quan sát'+(row.n_state===null?'':' · nhóm '+number(row.n_state,0));
  $('responseInference').textContent=row.qvalue_bh===null?'CI chế độ có tính covariance.':'BH q = '+number(row.qvalue_bh);
  $('certaintyBadge').textContent=crosses?'Chưa rõ chiều phản ứng':'CI không chứa 0';$('certaintyBadge').dataset.state=crosses?'unclear':'clear';
  $('pinState').textContent=pinned?'ĐÃ GHIM NGÀY '+row.horizon_days:'NGÀY ĐANG CHỌN';$('unpinResponse').hidden=!pinned;
  $('designSample').textContent=number(row.nobs,0)+' quan sát';
  const lo=Math.min(0,row.lower95),hi=Math.max(0,row.upper95),pad=(hi-lo||1)*.15,min=lo-pad,max=hi+pad,x=v=>(v-min)/(max-min)*100;
  $('intervalBand').style.left=x(row.lower95)+'%';$('intervalBand').style.width=(x(row.upper95)-x(row.lower95))+'%';$('intervalPoint').style.left=x(row.beta_pct)+'%';$('intervalZero').style.left=x(0)+'%';
  responseTable();
 }
 function currentAnalogueRows(){return activeAnalogue?seriesFor(activeAnalogue):[];}
 let responseSceneKey='';
 function drawResponse(animate=false){
  const mobile=matchMedia('(max-width:760px)').matches,key=[$('asset').value,$('shock').value,$('regime').value,$('compareAssets').checked,activeAnalogue?.date_utc||'',mobile].join('|');
  if(key===responseSceneKey&&liveScene&&$('primaryCurve')){
   const h=Number($('horizon').value),i=h-1,asset=$('asset').value,point=$('responseSelectedPoint'),otherPoint=$('responseOtherPoint');
   for(const attr of ['x1','x2'])$('responsePin').setAttribute(attr,liveScene.selected[i][0]);
   $('responsePin').style.opacity=pinned?'1':'.45';
   if(asset==='btc'){point.setAttribute('cx',liveScene.selected[i][0]);point.setAttribute('cy',liveScene.selected[i][1]);}else{point.setAttribute('x',liveScene.selected[i][0]-4.5);point.setAttribute('y',liveScene.selected[i][1]-4.5);}
   if(otherPoint&&liveScene.other[i]){if(asset==='eth'){otherPoint.setAttribute('cx',liveScene.other[i][0]);otherPoint.setAttribute('cy',liveScene.other[i][1]);}else{otherPoint.setAttribute('x',liveScene.other[i][0]-3.5);otherPoint.setAttribute('y',liveScene.other[i][1]-3.5);}}
   const row=responseRows()[i];chart.setAttribute('aria-label',`${asset.toUpperCase()}, ${$('shock').selectedOptions[0].textContent}, ngày ${h}: ${percent(row.beta_pct)}. CI ${number(row.lower95)} đến ${number(row.upper95)}%. Dùng mũi tên chọn ngày; Enter ghim.`);
   if(hoverDay)showTooltip(hoverDay);return;
  }
  if(animationFrame)cancelAnimationFrame(animationFrame);
  const selected=responseRows(),asset=$('asset').value,other=$('compareAssets').checked?orbitCurveRows(asset==='btc'?'eth':'btc',$('shock').value,$('regime').value):[],actual=currentAnalogueRows(),next=orbitResponseScene(selected,other,actual,mobile?{width:360,height:300}:{width:720,height:330}),g=next.geometry;
  responseSceneKey=key;
  chart.setAttribute('viewBox',`0 0 ${g.width} ${g.height}`);
  const otherClass=asset==='btc'?'eth':'btc';
  chart.innerHTML=`<title>Phản ứng ${asset.toUpperCase()} từ 1 đến 30 ngày</title><desc>Ước lượng lợi suất log cộng dồn, CI pointwise 95%. Mũi tên chọn ngày; Enter để ghim. Bảng dữ liệu nằm ngay dưới biểu đồ.</desc><defs><linearGradient id="responseBandGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--${asset})" stop-opacity=".18"/><stop offset="1" stop-color="var(--${asset})" stop-opacity=".025"/></linearGradient><clipPath id="responseClip"><rect x="${g.left-1}" y="${g.top}" width="${g.right-g.left+2}" height="${g.bottom-g.top+4}"/></clipPath></defs>`+
   next.ticks.map(t=>`<line class="plot-grid" x1="${g.left}" x2="${g.right}" y1="${t.y}" y2="${t.y}"/><text x="${g.left-12}" y="${t.y+4}" text-anchor="end">${number(t.value,2)}</text>`).join('')+
   `<line class="plot-zero" x1="${g.left}" x2="${g.right}" y1="${next.zero}" y2="${next.zero}"/>`+[1,7,14,21,30].map(h=>`<text x="${g.left+(h-1)/29*(g.right-g.left)}" y="${g.height-30}" text-anchor="middle">${h}</text>`).join('')+
   `<g clip-path="url(#responseClip)"><path id="responseBand" fill="url(#responseBandGradient)"/><path id="primaryCurve" class="curve-line curve-${asset}"/><path id="comparisonCurve" class="curve-line curve-${otherClass}"/><path id="analogueCurve" class="curve-analogue"/><line id="responsePin" class="chart-pin" y1="${g.top}" y2="${g.bottom+4}"/><line id="responseCrosshair" class="crosshair" y1="${g.top}" y2="${g.bottom+4}" hidden/><${asset==='btc'?'circle':'rect'} id="responseSelectedPoint" class="point-${asset}" ${asset==='btc'?'r="4.5"':'width="9" height="9"'}/>${other.length?`<${otherClass==='btc'?'circle':'rect'} id="responseOtherPoint" class="point-${otherClass}" ${otherClass==='btc'?'r="3.5"':'width="7" height="7"'}/>`:''}</g>`;
  const primary=$('primaryCurve'),comparison=$('comparisonCurve'),band=$('responseBand'),analogue=$('analogueCurve'),point=$('responseSelectedPoint'),otherPoint=$('responseOtherPoint'),h=Number($('horizon').value),i=h-1;
  $('responsePin').setAttribute('x1',next.selected[i][0]);$('responsePin').setAttribute('x2',next.selected[i][0]);$('responsePin').style.opacity=pinned?'1':'.45';
  function paint(scene){primary.setAttribute('d',orbitLine(scene.selected));comparison.setAttribute('d',orbitLine(scene.other));band.setAttribute('d',orbitLine(scene.upper)+' '+orbitLine(scene.lower.slice().reverse()).replace(/^M/,'L')+' Z');analogue.setAttribute('d',orbitLine(scene.analogue));if(asset==='btc'){point.setAttribute('cx',scene.selected[i][0]);point.setAttribute('cy',scene.selected[i][1]);}else{point.setAttribute('x',scene.selected[i][0]-4.5);point.setAttribute('y',scene.selected[i][1]-4.5);}if(otherPoint&&scene.other[i]){if(otherClass==='btc'){otherPoint.setAttribute('cx',scene.other[i][0]);otherPoint.setAttribute('cy',scene.other[i][1]);}else{otherPoint.setAttribute('x',scene.other[i][0]-3.5);otherPoint.setAttribute('y',scene.other[i][1]-3.5);}}liveScene=scene;}
  const previous=liveScene;
  if(animate&&!reduce.matches&&previous&&previous.selected.length===next.selected.length){const start=performance.now();function frame(now){const t=Math.min(1,(now-start)/400),ease=1-(1-t)**3,scene={...next};for(const key of ['selected','other','lower','upper','analogue'])scene[key]=next[key].map((p,j)=>p.map((v,k)=>previous[key]?.[j]?previous[key][j][k]+(v-previous[key][j][k])*ease:v));paint(scene);if(t<1)animationFrame=requestAnimationFrame(frame);else animationFrame=null;}animationFrame=requestAnimationFrame(frame);}else paint(next);
  chart.setAttribute('aria-label',`${asset.toUpperCase()}, ${$('shock').selectedOptions[0].textContent}, ngày ${h}: ${percent(selected[i].beta_pct)}. CI ${number(selected[i].lower95)} đến ${number(selected[i].upper95)}%. Dùng mũi tên chọn ngày; Enter ghim.`);
  $('analogueOverlayLabel').hidden=!activeAnalogue;$('analogueOverlayLabel').textContent=activeAnalogue?'Nét chấm: thực tế '+date(activeAnalogue.date_utc):'';
  document.querySelector('.btc-key').hidden=asset!=='btc'&&!other.length;document.querySelector('.eth-key').hidden=asset!=='eth'&&!other.length;
  if(hoverDay)showTooltip(hoverDay);
 }
 function showTooltip(h){
  if(!liveScene)return;hoverDay=h;
  const asset=$('asset').value,rows=responseRows(),r=rows[h-1],other=orbitCurveRows(asset==='btc'?'eth':'btc',$('shock').value,$('regime').value)[h-1];
  const values=$('compareAssets').checked?[r,other]:[r];
  $('responseTooltip').innerHTML=`<strong>Sau ${h} ngày ${pinned&&h===Number($('horizon').value)?'· đã ghim':''}</strong>`+values.map(v=>`<div class="tooltip-row ${v.asset}"><b>${v.asset.toUpperCase()}</b><span>${percent(v.beta_pct)}</span><small>CI ${number(v.lower95)}% → ${number(v.upper95)}%</small></div>`).join('');
  const line=$('responseCrosshair'),x=liveScene.geometry.left+(h-1)/29*(liveScene.geometry.right-liveScene.geometry.left);line.hidden=false;line.removeAttribute('hidden');line.setAttribute('x1',x);line.setAttribute('x2',x);
  const box=chart.getBoundingClientRect(),left=Math.min(Math.max(8,x/liveScene.geometry.width*box.width-130),Math.max(8,box.width-268));$('responseTooltip').style.left=left+'px';$('responseTooltip').style.top='8px';$('responseTooltip').hidden=false;
 }
 let pointerFrame=null;chart.addEventListener('pointermove',e=>{const box=chart.getBoundingClientRect(),g=liveScene.geometry,x=(e.clientX-box.left)/box.width*g.width;if(x<g.left||x>g.right)return;const h=Math.max(1,Math.min(30,Math.round(1+(x-g.left)/(g.right-g.left)*29)));if(h===hoverDay)return;if(pointerFrame)cancelAnimationFrame(pointerFrame);pointerFrame=requestAnimationFrame(()=>showTooltip(h));});
 chart.addEventListener('pointerleave',()=>{if(pointerFrame)cancelAnimationFrame(pointerFrame);hoverDay=null;$('responseTooltip').hidden=true;const line=$('responseCrosshair');if(line)line.setAttribute('hidden','');});
 chart.addEventListener('click',e=>{const box=chart.getBoundingClientRect(),g=liveScene.geometry,x=(e.clientX-box.left)/box.width*g.width;if(x>=g.left&&x<=g.right){chooseDay(Math.round(1+(x-g.left)/(g.right-g.left)*29),true);toast('Đã ghim ngày '+$('horizon').value);}});
 chart.addEventListener('keydown',e=>{const h=Number($('horizon').value);if(['ArrowLeft','ArrowRight','Home','End','Enter','Escape'].includes(e.key))e.preventDefault();if(e.key==='ArrowLeft')chooseDay(h-1,true);if(e.key==='ArrowRight')chooseDay(h+1,true);if(e.key==='Home')chooseDay(1,true);if(e.key==='End')chooseDay(30,true);if(e.key==='Enter'){pinned=!pinned;responseDetail();drawResponse(false);}if(e.key==='Escape'){$('unpinResponse').click();$('responseTooltip').hidden=true;}if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key))showTooltip(Number($('horizon').value));});
 function analogues(){
  const h=Number($('horizon').value),rows=analogueIndex.get([$('asset').value,$('shock').value,$('regime').value,h].join('|'))||[],container=$('analogueCards');container.replaceChildren();
  activeAnalogue=lockedAnalogue&&rows.find(r=>r.date_utc===lockedAnalogue)||null;
  for(const row of rows){const b=document.createElement('button');b.type='button';b.className='analogue-card';b.dataset.date=row.date_utc;b.setAttribute('aria-pressed',String(lockedAnalogue===row.date_utc));
   const series=seriesFor(row),lo=Math.min(0,...series.map(r=>r.observed_cumulative_pct)),hi=Math.max(0,...series.map(r=>r.observed_cumulative_pct)),y=v=>27-(v-lo)/(hi-lo||1)*25,points=series.map(r=>`${(r.horizon_days-1)/29*78},${y(r.observed_cumulative_pct)}`).join(' ');
   b.innerHTML=`<span><strong>${date(row.date_utc)}</strong><small>${number(row.shock_observed,2)} · ${h} ngày quan sát</small></span><svg viewBox="0 0 80 30" aria-hidden="true"><line x1="0" x2="80" y1="${y(0)}" y2="${y(0)}"/><polyline points="${points}"/></svg><span>${percent(row.observed_cumulative_pct)}</span>`;
   const preview=()=>{activeAnalogue=row;drawResponse(false);highlightRolling(row);};const leave=()=>{activeAnalogue=lockedAnalogue?rows.find(r=>r.date_utc===lockedAnalogue)||null:null;drawResponse(false);highlightRolling(activeAnalogue);};
   b.addEventListener('pointerenter',preview);b.addEventListener('pointerleave',leave);b.addEventListener('focus',preview);b.addEventListener('blur',leave);b.addEventListener('click',()=>{lockedAnalogue=lockedAnalogue===row.date_utc?null:row.date_utc;activeAnalogue=lockedAnalogue?row:null;for(const card of container.children)card.setAttribute('aria-pressed',String(card.dataset.date===lockedAnalogue));drawResponse(false);highlightRolling(activeAnalogue);});container.append(b);
  }
 }
 const beforeResponse=renderResponse;renderResponse=function(){const started=performance.now();beforeResponse();syncControls();responseDetail();analogues();drawResponse();root.dataset.responseRenderMs=(performance.now()-started).toFixed(1);};
 $('resetResponse').removeEventListener('click',resetResponse);$('resetResponse').addEventListener('click',()=>{pinned=false;lockedAnalogue=null;activeAnalogue=null;resetResponse();toast('Đã trở về BTC · VIX +5 · 1 ngày.');});
 $('exportResponse').addEventListener('click',()=>toast('Đã chuẩn bị CSV gồm 30 thời hạn và CI.'));
 // Rolling brushing uses the actual rolling dates, never the response-day axis.
 let rollingRows=[],rollingBounds=null;
 let rollingTableKey='';
 function rollingTable(){if(!$('rollingDataTable').closest('details').open)return;const key=[rollingSelection,...(rollingRange||[])].join('|');if(key===rollingTableKey)return;$('rollingDataTable').innerHTML=table(['Ngày UTC','Beta (%)','CI thấp','CI cao'],rollingRows.map(r=>[date(r.date_utc),number(r.beta_pct),number(r.beta_pct-1.96*r.se),number(r.beta_pct+1.96*r.se)]));rollingTableKey=key;}
 $('rollingDataTable').closest('details').addEventListener('toggle',rollingTable);
 function allRolling(){return DATA.rolling.filter(r=>r.asset===$('rollAsset').value&&r.shock===$('rollShock').value).sort((a,b)=>a.date_utc.localeCompare(b.date_utc));}
 const previousRolling=renderRolling;
 renderRolling=function(){
  const selection=$('rollAsset').value+'|'+$('rollShock').value;if(selection!==rollingSelection){rollingRange=null;rollingSelection=selection;}
  const all=allRolling();rollingRows=all.filter(r=>!rollingRange||(r.date_utc>=rollingRange[0]&&r.date_utc<=rollingRange[1]));if(rollingRows.length<2){rollingRows=all;rollingRange=null;}
  $('rollingStart').min=$('rollingEnd').min=all[0].date_utc;$('rollingStart').max=$('rollingEnd').max=all.at(-1).date_utc;
  $('rollingStart').value=rollingRows[0].date_utc;$('rollingEnd').value=rollingRows.at(-1).date_utc;
  const rows=rollingRows.map(r=>({x:Date.parse(r.date_utc+'T00:00:00Z'),y:r.beta_pct,lo:r.beta_pct-1.96*r.se,hi:r.beta_pct+1.96*r.se}));
  $('rollingChart').innerHTML=chartLegacy(rows,rows.length-1,'Ngày kết thúc cửa sổ · UTC')+'<g id="rollingHighlight"></g><rect id="rollingBrush" class="brush-region" y="35" height="235" width="0"/>';
  const first=rows[0].x,last=rows.at(-1).x;rollingBounds={first,last};
  $('rollingRangeLabel').textContent=`${date(rollingRows[0].date_utc)} — ${date(rollingRows.at(-1).date_utc)} · kéo để zoom, nhấp đúp đặt lại`+($('shock').value==='monetary'?' · Rolling daily '+$('rollShock').selectedOptions[0].textContent+', tách riêng STMT.':'');
  rollingTable();highlightRolling(activeAnalogue);
 };
 let rollingFrame=null,rollingTimer=null;
 window.orbitQueueRolling=()=>{if(rollingFrame!==null)cancelAnimationFrame(rollingFrame);if(rollingTimer!==null)clearTimeout(rollingTimer);$('rolling').setAttribute('aria-busy','true');rollingFrame=requestAnimationFrame(()=>{rollingFrame=null;rollingTimer=setTimeout(()=>{rollingTimer=null;renderRolling();$('rolling').setAttribute('aria-busy','false');},0);});};
 const chartLegacy=chartLegacyAlias;
 function highlightRolling(row){const g=$('rollingHighlight');if(!g||!rollingBounds)return;g.replaceChildren();if(!row)return;const x=d=>70+(Date.parse(d+'T00:00:00Z')-rollingBounds.first)/(rollingBounds.last-rollingBounds.first)*615,start=Math.max(70,x(row.date_utc)),end=Math.min(685,x(row.end_date_utc));if(end<70||start>685)return;g.innerHTML=`<rect x="${start}" y="35" width="${Math.max(3,end-start)}" height="235" class="selected-date"><title>Sự kiện ${row.date_utc}</title></rect>`;}
 for(const id of ['rollAsset','rollShock']){$(id).removeEventListener('change',previousRolling);$(id).addEventListener('change',renderRolling);}
 const roll=$('rollingChart'),rollX=e=>Math.max(70,Math.min(685,(e.clientX-roll.getBoundingClientRect().left)/roll.getBoundingClientRect().width*720));
 roll.addEventListener('pointerdown',e=>{if(e.button!==0)return;brush={start:rollX(e),id:e.pointerId};roll.setPointerCapture(e.pointerId);});
 roll.addEventListener('pointermove',e=>{if(!brush)return;const x=rollX(e);$('rollingBrush').setAttribute('x',Math.min(x,brush.start));$('rollingBrush').setAttribute('width',Math.abs(x-brush.start));});
 function endBrush(e){if(!brush)return;const end=rollX(e),start=brush.start;brush=null;if(Math.abs(end-start)<8)return;const toDate=x=>new Date(rollingBounds.first+(x-70)/615*(rollingBounds.last-rollingBounds.first)).toISOString().slice(0,10);rollingRange=[toDate(Math.min(start,end)),toDate(Math.max(start,end))];renderRolling();toast('Đã phóng to khoảng thời gian. Nhấp đúp để xem toàn kỳ.');}
 roll.addEventListener('pointerup',endBrush);roll.addEventListener('pointercancel',()=>{brush=null;const b=$('rollingBrush');if(b)b.setAttribute('width','0');});
 function resetRolling(){rollingRange=null;renderRolling();}roll.addEventListener('dblclick',resetRolling);$('resetRolling').addEventListener('click',resetRolling);roll.addEventListener('keydown',e=>{if(e.key==='Escape'||e.key==='Home'){e.preventDefault();resetRolling();}});
 $('applyRollingRange').addEventListener('click',()=>{const a=$('rollingStart').value,b=$('rollingEnd').value;if(!a||!b||a>b){toast('Chọn ngày bắt đầu trước ngày kết thúc.');return;}if(allRolling().filter(r=>r.date_utc>=a&&r.date_utc<=b).length<2){toast('Khoảng này cần ít nhất hai ước lượng rolling.');return;}rollingRange=[a,b];renderRolling();});
 // Forecast layers are display-only; losses and CSV always use the complete data.
 const visibleCurves=[true,true,true,true];
 function replayEnhance(){if(!HISTORICAL.series)return;const rows=historicalRows();for(const id of ['historyBaseLoss','historyAddedLoss','historyBenchmarkDelta'])$(id).textContent=localCell($(id).textContent);$('replayCompact').textContent=rows.length?`${rows.length.toLocaleString('vi-VN')} ngày · ${date(rows[0].date)} — ${date(rows.at(-1).date)} · dữ liệu lịch sử`: 'Không có ngày phù hợp. Chọn lại khoảng ngày.';const lines=$('historyPredictionChart').querySelectorAll('polyline');lines.forEach((line,i)=>{line.dataset.curve=String(i);line.style.display=visibleCurves[i]?'':'none';});
  const loss=$('historyLossChart').querySelector('svg'),line=loss?.querySelector('polyline');if(line){const pts=line.getAttribute('points').trim().split(/\s+/).map(p=>p.split(',').map(Number)),zero=loss.querySelector('line[stroke="#8ca5b3"]'),y=zero?Number(zero.getAttribute('y1')):null;if(pts.length&&Number.isFinite(y)&&!loss.querySelector('.loss-area')){const ns='http://www.w3.org/2000/svg',area=document.createElementNS(ns,'path');area.setAttribute('d',`M${pts[0][0]},${y} `+pts.map(p=>'L'+p.join(',')).join(' ')+` L${pts.at(-1)[0]},${y} Z`);area.setAttribute('fill','var(--mint)');area.setAttribute('opacity','.10');area.setAttribute('class','loss-area');loss.insertBefore(area,line);}}
 }
 window.orbitEnhanceReplay=replayEnhance;
 for(const b of $('replayLegend').querySelectorAll('button'))b.addEventListener('click',()=>{const i=Number(b.dataset.curve);if(visibleCurves[i]&&visibleCurves.filter(Boolean).length===1){toast('Giữ ít nhất một đường để đối chiếu.');return;}visibleCurves[i]=!visibleCurves[i];b.setAttribute('aria-pressed',String(visibleCurves[i]));replayEnhance();});
 const observer=new MutationObserver(()=>replayEnhance());observer.observe($('historyPointTable'),{childList:true});
 let varTableKey='';
 function modelHelp(){const help=$('forecastModel').closest('label').querySelector('[data-term]');if(help)help.dataset.term=$('forecastModel').value==='gradient_boosting'?'boosting':'elastic';}
 $('forecastModel').addEventListener('change',modelHelp);modelHelp();
 function varData(){const yieldName=$('varYield').value,shock=$('varShock').value==='yield'?yieldName+'_change_bps':$('varShock').value,key=[$('varAsset').value,yieldName,$('varRegime').value,$('varOrder').value,shock].join('|');if(key===varTableKey)return;varTableKey=key;const rows=DATA.var_irf.filter(r=>r.asset===$('varAsset').value&&r.yield_variable===yieldName&&r.regime===$('varRegime').value&&r.ordering===$('varOrder').value&&r.shock===shock);$('varDataTable').innerHTML=table(['Phiên','Phản ứng (%)','CI thấp','CI cao'],rows.map(r=>[r.horizon_sessions,number(r.response_pct),number(r.lower95),number(r.upper95)]));}
 for(const id of ['varAsset','varYield','varShock','varOrder','varRegime'])$(id).addEventListener('change',()=>{lastAdvanced='var';varData();});for(const id of ['qAsset','qRegime','qShock'])$(id).addEventListener('change',()=>lastAdvanced='quantile');
 function csvDownload(rows,name){if(!rows.length){toast('Chưa có dữ liệu phù hợp để tải.');return;}const columns=Object.keys(rows[0]),q=v=>'"'+String(v??'').replace(/"/g,'""')+'"',csv='\ufeff'+[columns,...rows.map(r=>columns.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n'),url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Đã chuẩn bị '+name);}
 function exportCurrent(){if(view==='transmission'){$('exportResponse').click();return;}if(view==='forecast'){if(!HISTORICAL.series){toast('Dữ liệu phát lại đang được chuẩn bị. Hãy thử lại sau.');return;}if($('exportHistoricalOos').disabled){toast('Chọn khoảng có dữ liệu trước khi tải CSV.');return;}$('exportHistoricalOos').click();toast('Đã chuẩn bị CSV dự báo và timing.');return;}if(view==='fomc'&&window.orbitExportFomc){window.orbitExportFomc();return;}if(view==='fomc'){csvDownload(LATEST.fomc.filter(r=>r.asset===$('eAsset').value&&r.outcome===$('eOutcome').value),'fomc_rotation_ranges.csv');return;}if(view==='methods'){csvDownload(LATEST.pit,'feature_sources.csv');return;}if(view==='operations'){csvDownload([{research_cutoff:(window.orbitStatus||ORBIT_STATUS).research_cutoff,last_success_utc:(window.orbitStatus||ORBIT_STATUS).worker?.last_success_utc,performance:(window.orbitStatus||ORBIT_STATUS).prospective?.performance,prediction_rows:(window.orbitStatus||ORBIT_STATUS).prospective?.prediction_rows,fixed_end:(window.orbitStatus||ORBIT_STATUS).prospective?.fixed_end}],'operations_snapshot.csv');return;}if(lastAdvanced==='quantile')csvDownload(DATA.quantile.filter(r=>r.asset===$('qAsset').value&&r.regime===$('qRegime').value&&r.shock===$('qShock').value),'quantile_effects.csv');else{const shock=$('varShock').value==='yield'?$('varYield').value+'_change_bps':$('varShock').value;csvDownload(DATA.var_irf.filter(r=>r.asset===$('varAsset').value&&r.yield_variable===$('varYield').value&&r.regime===$('varRegime').value&&r.ordering===$('varOrder').value&&r.shock===shock),'var_irf.csv');}}
 window.orbitExportCurrent=exportCurrent;$('topExport').addEventListener('click',exportCurrent);$('printDashboard').addEventListener('click',()=>window.print());
 window.orbitExportLiveForecast=()=>csvDownload((window.orbitStatus||ORBIT_STATUS).latest_forecasts||[],'latest_frozen_risk_forecasts.csv');
 document.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey||e.target.closest('input,select,textarea,[contenteditable=true]')||document.querySelector('dialog[open]'))return;if(/^[1-6]$/.test(e.key)){e.preventDefault();go(ORBIT_VIEWS[Number(e.key)-1]);}if(e.key==='['||e.key===']'){e.preventDefault();chooseDay(Number($('horizon').value)+(e.key===']'?1:-1));}if(e.key.toLowerCase()==='t'){e.preventDefault();window.orbitToggleTheme();}if(e.key==='?'){e.preventDefault();$('shortcutDialog').showModal();}});
 function applyRoute(){const route=orbitParseRoute(location.hash);for(const id of ['asset','shock','regime','horizon'])$(id).value=route[id];$('compareAssets').checked=route.compare;showWorkspace(route.view);renderResponse();}
 window.addEventListener('hashchange',applyRoute);
 const chartTitles=['quantileChart','varChart'];for(const id of chartTitles){$(id).setAttribute('tabindex','0');$(id).setAttribute('aria-describedby',id==='quantileChart'?'quantileTable':'varDataTable');}
 orbitStartFomc(csvDownload);
 applyRoute();renderRolling();if(HISTORICAL.series)replayEnhance();
 // Opacity needs no synchronous SVG geometry/layout during application boot.
 if(!reduce.matches){const path=$('primaryCurve');if(path)path.animate([{opacity:.4},{opacity:1}],{duration:140,easing:'ease-out'});}
 root.dataset.orbitStudioReady='true';
}
// Retain the original generic plotter for rolling, quantile and VAR validation.
const chartLegacyAlias=chart;
