const WORKSPACE_GROUPS={transmission:['responses','rolling','analoguePanel'],forecast:['forecast','rv'],fomc:['fomc'],advanced:['quantile','joint'],methods:['overview','pit','methods'],operations:['operations']};
const WORKSPACE_NAMES={transmission:'Truyền dẫn',forecast:'Dự báo rủi ro',fomc:'FOMC',advanced:'Phân vị & VAR',methods:'Phương pháp & nguồn',operations:'Dữ liệu & OOS'};
const renderedWorkspaces=new Set();
let forecastWorkspaceLoading=false;
async function loadForecastWorkspace(){
 if(typeof window==='undefined'){renderForecast();return;}
 if(forecastWorkspaceLoading)return;
 forecastWorkspaceLoading=true;
 const started=performance.now();
 const loading=el('historyLoading'),error=el('historyError');
 if(loading)loading.hidden=false;
 if(error)error.hidden=true;
 try{
  renderForecast();renderRV();
  await ensureHistoricalOos();
  if(loading)loading.hidden=true;
  if(el('forecast').hidden)return;
  renderForecast();renderRV();
  renderedWorkspaces.add('forecast');
  document.documentElement.dataset.historyLoadMs=(performance.now()-started).toFixed(1);
  if(typeof window.orbitUpdateForecast==='function')window.orbitUpdateForecast();
 }catch(exc){
  if(loading)loading.hidden=true;
  if(error){error.hidden=false;el('historyErrorText').textContent=exc.message;}
 }finally{forecastWorkspaceLoading=false;}
}
function showWorkspace(view){
 if(!WORKSPACE_GROUPS[view])view='transmission';
 for(const [key,ids] of Object.entries(WORKSPACE_GROUPS)){
  const pressed=String(key===view);if(el('tab-'+key).getAttribute('aria-pressed')!==pressed)el('tab-'+key).setAttribute('aria-pressed',pressed);
  for(const id of ids)if(el(id).hidden!==(key!==view))el(id).hidden=key!==view;
 }
 el('workspaceTitle').textContent=WORKSPACE_NAMES[view];
 if(typeof window!=='undefined'&&!renderedWorkspaces.has(view)){
  if(view==='forecast')loadForecastWorkspace();
  if(view==='advanced'){renderQuantile();renderVAR();}
  if(view==='fomc')renderFOMC();
  if(view!=='forecast')renderedWorkspaces.add(view);
 }
}
function responseCsv(){
 const columns=['asset','shock','regime','horizon_days','beta_pct','lower95','upper95','nobs','n_state'];
 const quote=value=>'"'+String(value===null||value===undefined?'':value).replace(/"/g,'""')+'"';
 return '\ufeff'+[columns.map(quote).join(','),...responseRows().map(row=>columns.map(c=>quote(row[c])).join(','))].join('\r\n');
}
function downloadResponseCsv(){
 const blob=new Blob([responseCsv()],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');
 link.href=url;link.download=`${el('asset').value}_${el('shock').value}_${el('regime').value}_response.csv`;
 link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function resetResponse(){
 for(const [id,value] of Object.entries({asset:'btc',shock:'vix_change',regime:'full',horizon:'1'}))el(id).value=value;
 renderResponse();
}
const renderResponseEstimate=renderResponse;
let lastRollingSelection='';
renderResponse=function(){
 renderResponseEstimate();
 const row=responseRows().find(r=>r.horizon_days===Number(el('horizon').value));
 const asset=el('asset').value.toUpperCase(),h=Number(el('horizon').value),state={full:'Toàn mẫu',calm:'Bình thường',stress:'Căng thẳng'}[el('regime').value];
 el('selectionLabel').textContent=`${asset} · ${state} · ${h} ngày`;
 el('responseMetricLabel').textContent=`Phản ứng cộng dồn tại ${h} ngày`;
 el('responseTiming').textContent=el('shock').value==='monetary'?'Monetary STMT · lợi suất các ngày sau FOMC · khoảng tin cậy 95% tại từng horizon.':'Local Projections · lợi suất cộng dồn theo ngày lịch · khoảng tin cậy 95% tại từng horizon.';
 el('responseCI').textContent=`Khoảng tin cậy 95%: [${fmt(row.lower95)}%; ${fmt(row.upper95)}%]`;
 el('responseSample').textContent=`Mẫu ước lượng: ${row.nobs} quan sát${row.n_state===null?'':`; chế độ: ${row.n_state}`}`;
 el('rollAsset').value=el('asset').value;
 if(el('shock').value!=='monetary')el('rollShock').value=el('shock').value;
 const rollingSelection=el('rollAsset').value+'|'+el('rollShock').value;
 if(rollingSelection!==lastRollingSelection){if(typeof window!=='undefined'&&typeof window.orbitQueueRolling==='function')window.orbitQueueRolling();else renderRolling();lastRollingSelection=rollingSelection;}
};
for(const id of ['asset','shock','regime','horizon']){
 el(id).removeEventListener('change',renderResponseEstimate);
 el(id).addEventListener('change',renderResponse);
}
for(const view of Object.keys(WORKSPACE_GROUPS))el('tab-'+view).addEventListener('click',()=>{
 if(typeof window!=='undefined'&&window.scrollY)window.scrollTo({top:0,behavior:'instant'});
 showWorkspace(view);
});
el('exportResponse').addEventListener('click',downloadResponseCsv);
el('resetResponse').addEventListener('click',resetResponse);
let initialWorkspace='transmission';
if(typeof window!=='undefined'){
 const target=window.location.hash.slice(1);
 for(const [group,ids] of Object.entries(WORKSPACE_GROUPS))if(ids.includes(target)||target===group)initialWorkspace=group;
}
showWorkspace(initialWorkspace);renderResponse();
