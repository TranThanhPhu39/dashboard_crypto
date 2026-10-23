// Offline operational report QA in headless Chrome; no forecast/data mutations.
const fs = require('fs'), path = require('path'), {spawn} = require('child_process');
const {pathToFileURL} = require('url');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'outputs/research/release_20261025');
const preview = path.join(out, 'preview');
const allowed = path.resolve(root, '.preview');
const profile = path.join(allowed, `release-${process.pid}-${Date.now()}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let child, socket, serial = 0;
const pending = new Map(), errors = [];
function call(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++serial;
    const timer = setTimeout(() => {pending.delete(id); reject(Error('CDP timeout '+method));}, 45000);
    pending.set(id, {resolve: value => {clearTimeout(timer); resolve(value);}, reject});
    socket.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const result = await call('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true});
  if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function screenshot(name) {
  const result = await call('Page.captureScreenshot', {format:'png', captureBeyondViewport:false});
  fs.writeFileSync(path.join(preview, name), Buffer.from(result.data, 'base64'));
}
(async () => {
  fs.mkdirSync(preview, {recursive:true});
  fs.mkdirSync(profile, {recursive:true});
  try {
    child = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
      '--headless=new', '--disable-gpu', '--disable-background-networking', '--no-first-run',
      '--no-default-browser-check', `--user-data-dir=${profile}`, '--remote-debugging-port=0', 'about:blank'
    ], {windowsHide:true, stdio:'ignore'});
    let port;
    for (let i=0; i<120; i++) {
      const filename = path.join(profile, 'DevToolsActivePort');
      if (fs.existsSync(filename)) {port=fs.readFileSync(filename,'utf8').split(/\r?\n/)[0]; break;}
      await delay(100);
    }
    if (!port) throw Error('Chrome did not start');
    const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket = new WebSocket(tabs.find(tab => tab.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject) => {
      socket.addEventListener('open',resolve,{once:true});
      socket.addEventListener('error',reject,{once:true});
    });
    socket.addEventListener('message', event => {
      const msg=JSON.parse(event.data);
      if (msg.id && pending.has(msg.id)) {
        const item=pending.get(msg.id); pending.delete(msg.id);
        msg.error ? item.reject(Error(JSON.stringify(msg.error))) : item.resolve(msg.result);
      }
      if (msg.method==='Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails);
    });
    await call('Page.enable'); await call('Runtime.enable');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    await call('Page.navigate',{url:pathToFileURL(path.join(out,'report.html')).href});
    for (let i=0;i<60;i++) {
      if (await evaluate("document.readyState==='complete'")) break;
      await delay(100);
    }
    const desktop = await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    const counts = await evaluate('Array.from(document.querySelectorAll("table")).map(table=>table.tBodies[0].rows.length)');
    if (counts.length!==8) throw Error('Unexpected table coverage '+JSON.stringify(counts));
    const hrefs = await evaluate('Array.from(document.querySelectorAll("a[href]")).map(a=>a.getAttribute("href"))');
    const local = hrefs.filter(href=>!/^https?:/.test(href));
    for (const href of local) if (!fs.existsSync(path.resolve(out,href))) throw Error('Missing link '+href);
    await screenshot('report_desktop.png');
    await evaluate('document.querySelectorAll("h2")[5].scrollIntoView()');
    await screenshot('report_results_desktop.png');
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
    await evaluate('window.scrollTo(0,0)');
    const mobile = await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('report_mobile.png');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    await call('Page.navigate',{url:pathToFileURL(path.join(out,'oos_followup.html')).href});
    for(let i=0;i<60;i++){if(await evaluate("document.readyState==='complete' && document.title==='Kế hoạch và trạng thái OOS'"))break;await delay(100);}
    const oosDesktop=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    const oosLinks=await evaluate('Array.from(document.querySelectorAll("a[href]")).map(a=>a.getAttribute("href")).filter(href=>!/^https?:/.test(href))');
    for(const href of oosLinks)if(!fs.existsSync(path.resolve(out,href)))throw Error('Missing OOS link '+href);
    await screenshot('oos_desktop.png');
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
    const oosMobile=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('oos_mobile.png');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    await call('Page.navigate',{url:pathToFileURL(path.join(root,'outputs/automation_20261020/health.html')).href});
    for(let i=0;i<60;i++){if(await evaluate("document.readyState==='complete' && document.title==='Topic09 — Vận hành tự động'"))break;await delay(100);}
    const automationDesktop=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('automation_desktop.png');
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
    const automationMobile=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('automation_mobile.png');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    await call('Page.navigate',{url:pathToFileURL(path.join(root,'dashboard/index.html')).href});
    for(let i=0;i<60;i++){if(await evaluate("document.readyState==='complete' && Boolean(document.getElementById('liveStatus').textContent)"))break;await delay(100);}
    const dashboardDesktop=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    const startsWithEstimator=await evaluate("!document.getElementById('responses').hidden && document.getElementById('overview').hidden && document.getElementById('pit').hidden");
    const auroraLayoutWorks=await evaluate("document.documentElement.dataset.theme==='dark'&&document.querySelectorAll('#orbit-aurora').length===1&&getComputedStyle(document.querySelector('.workspace-nav')).flexDirection==='column'&&document.querySelector('.workspace-nav').getBoundingClientRect().right<document.querySelector('.app-header').getBoundingClientRect().left");
    const expandedWidth=await evaluate("document.querySelector('.workspace-nav').getBoundingClientRect().width");
    await evaluate("document.getElementById('collapseSidebar').click()");
    const sidebarCollapseWorks=await evaluate("document.documentElement.dataset.navCollapsed==='true'&&document.querySelector('.workspace-nav').getBoundingClientRect().width===80&&document.getElementById('collapseSidebar').getAttribute('aria-expanded')==='false'&&localStorage.getItem('orbit-nav-collapsed')==='true'");
    await screenshot('dashboard_sidebar_collapsed.png');
    await evaluate("document.getElementById('openNavigation').click()");
    const resizeBox=await evaluate("(()=>{const r=document.getElementById('sidebarResizer').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()");
    await call('Input.dispatchMouseEvent',{type:'mousePressed',x:resizeBox.x,y:resizeBox.y,button:'left',buttons:1,clickCount:1});
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:resizeBox.x+40,y:resizeBox.y,button:'left',buttons:1});
    await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
    await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:resizeBox.x+40,y:resizeBox.y,button:'left',buttons:0,clickCount:1});
    const sidebarResizeWorks=await evaluate(`document.querySelector('.workspace-nav').getBoundingClientRect().width===${expandedWidth+40}&&Number(localStorage.getItem('orbit-nav-width'))===${expandedWidth+40}`);
    if(!sidebarResizeWorks)console.log(JSON.stringify({resizeBox,actual:await evaluate("({width:document.querySelector('.workspace-nav').getBoundingClientRect().width,stored:localStorage.getItem('orbit-nav-width')})")}));
    await screenshot('dashboard_sidebar_resized.png');
    await evaluate("document.getElementById('collapseSidebar').click()");
    const previousOrigin=await evaluate('performance.timeOrigin');
    await call('Page.reload',{ignoreCache:true});
    for(let i=0;i<100;i++){if(await evaluate(`performance.timeOrigin!==${previousOrigin}&&document.documentElement?.dataset?.orbitStudioReady==='true'`))break;await delay(100);}
    const sidebarPersistenceWorks=await evaluate(`(()=>{if(document.documentElement.dataset.navCollapsed!=='true'||document.querySelector('.workspace-nav').getBoundingClientRect().width!==80)return false;document.getElementById('collapseSidebar').click();return document.querySelector('.workspace-nav').getBoundingClientRect().width===${expandedWidth+40}})()`);
    await evaluate("document.getElementById('sidebarResizer').dispatchEvent(new KeyboardEvent('keydown',{key:'Home',bubbles:true}))");
    await evaluate("document.getElementById('themeToggle').click()");
    await delay(180);
    const lightThemeWorks=await evaluate("document.documentElement.dataset.theme==='light'&&localStorage.getItem('orbit-theme-aurora')==='light'&&document.getElementById('themeModeLabel').textContent==='Sáng'");
    await screenshot('dashboard_aurora_light_desktop.png');
    await evaluate("document.getElementById('themeToggle').click()");
    await call('Emulation.setDeviceMetricsOverride',{width:1024,height:1000,deviceScaleFactor:1,mobile:false});
    const tabletLayoutWorks=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    await evaluate("document.getElementById('tab-fomc').click();window.scrollTo(0,0)");
    const fomcAggregateWorks=await evaluate("document.getElementById('designTitle').textContent==='Phản ứng quanh FOMC.'&&document.getElementById('fomcSampleDescription').textContent.includes('75')&&document.getElementById('fomcAggregateChart').querySelectorAll('circle').length===30&&document.getElementById('fomcAggregateChart').querySelector('.fomc-ci-band')!==null&&document.getElementById('fomcEventListTable').children.length===0");
    await screenshot('dashboard_fomc_aggregate_desktop.png');
    await evaluate("document.getElementById('fomcAggregateChart').scrollIntoView({block:'center'})");
    await screenshot('dashboard_fomc_aggregate_chart.png');
    await evaluate("document.getElementById('fomcEventTab').click()");
    const fomcEventsWork=await evaluate("(()=>{const el=id=>document.getElementById(id);if(el('fomcEventDate').options.length!==75||!el('fomcNextEvent').disabled)return false;const latest=el('fomcEventDate').value;el('fomcPreviousEvent').click();if(el('fomcEventDate').value===latest)return false;el('fomcNextEvent').click();if(el('fomcEventDate').value!==latest)return false;for(const e of [FOMC_RESEARCH.events[0],FOMC_RESEARCH.events.find(r=>r.event_time_et.endsWith('-05:00')),FOMC_RESEARCH.events.at(-1)])for(const asset of ['BTC','ETH']){el('fomcEventDate').value=e.date;el('eAsset').value=asset;el('eAsset').dispatchEvent(new Event('change'));if(el('fomcStatementLink').href!==e.statement_url||el('fomcEventChart').querySelectorAll('circle').length!==31||window.orbitFomcEventCsvRows().find(r=>r.window==='intraday').actual_log_return_pct!==e.assets[asset].returns.intraday)return false;}return el('fomcEventPanel').hidden===false&&el('fomcAggregatePanel').hidden===true})()");
    await screenshot('dashboard_fomc_event_desktop.png');
    const fomcDownloadFolder=path.join(preview,'downloads','fomc-'+Date.now());fs.mkdirSync(fomcDownloadFolder,{recursive:true});
    await call('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:fomcDownloadFolder});
    await call('Runtime.evaluate',{expression:"document.getElementById('topExport').click()",userGesture:true});
    const fomcFilename=await evaluate("'fomc_'+document.getElementById('fomcEventDate').value+'_eth_observations.csv'");
    const fomcCsvFile=path.join(fomcDownloadFolder,fomcFilename);
    for(let i=0;i<50&&!fs.existsSync(fomcCsvFile);i++)await delay(100);
    if(!fs.existsSync(fomcCsvFile))throw Error('FOMC CSV download missing');
    const fomcCsvWorks=fs.readFileSync(fomcCsvFile,'utf8').replace(/^\ufeff/,'').split('\r\n').length===64;
    await evaluate("document.getElementById('fomcEventWindow').value='post';document.getElementById('fomcEventWindow').dispatchEvent(new Event('change'));document.getElementById('fomcEventList').open=true");
    await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
    const fomcListWorks=await evaluate("document.getElementById('fomcEventListTable').querySelectorAll('tbody tr').length===75&&document.getElementById('fomcEventChart').querySelectorAll('circle').length===31");
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
    await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
    const fomcMobile=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await evaluate('window.scrollTo(0,0)');
    await screenshot('dashboard_fomc_event_mobile.png');
    await evaluate("document.getElementById('fomcEventChart').scrollIntoView({block:'center'})");
    await screenshot('dashboard_fomc_event_chart_mobile.png');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    const liveDataWorks=await evaluate("(()=>{showWorkspace('operations');const status=window.orbitStatus||ORBIT_STATUS,observations=status.capture?.observations||[],forecasts=status.latest_forecasts||[],count=id=>document.getElementById(id).querySelectorAll('tbody tr').length;return count('liveObservationTable')===observations.length&&count('liveForecastTable')===forecasts.length&&document.querySelector('.topbar-date').textContent.includes('Mẫu ước lượng')&&Boolean(document.getElementById('latestDataBadge').textContent)})()");
    const liveDesktop=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('dashboard_live_desktop.png');
    await evaluate("document.getElementById('liveObservationTable').scrollIntoView({block:'center'})");
    await screenshot('dashboard_live_tables_desktop.png');
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
    const liveMobile=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await evaluate('window.scrollTo(0,0)');
    await screenshot('dashboard_live_mobile.png');
    await evaluate("document.getElementById('liveForecastTable').scrollIntoView({block:'start'})");
    await screenshot('dashboard_live_forecasts_mobile.png');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    await evaluate("showWorkspace('transmission')");
    const noWarningOnMain=await evaluate("!document.body.innerText.includes('Chưa có untouched OOS') && !document.body.innerText.includes('causal identification vô điều kiện chưa được chứng nhận')");
    const tabButtonsWork=await evaluate("Object.entries(WORKSPACE_GROUPS).every(([group,ids])=>{document.getElementById('tab-'+group).click();return ids.every(id=>!document.getElementById(id).hidden) && document.getElementById('tab-'+group).getAttribute('aria-pressed')==='true'})");
    await evaluate("document.getElementById('tab-transmission').click()");
    await evaluate('window.scrollTo(0,0)');
    await screenshot('dashboard_desktop.png');
    await evaluate("document.getElementById('tab-forecast').click()");
    await evaluate("document.getElementById('forecast').scrollIntoView()");
    await screenshot('dashboard_forecast_desktop.png');
    await evaluate("document.getElementById('fAsset').value='eth';document.getElementById('target').value='return';document.getElementById('forecastModel').value='gradient_boosting';document.getElementById('forecastPair').value='2';document.getElementById('fScenario').value='matched_asof_d3';document.getElementById('fScope').value='pooled';document.getElementById('fScope').dispatchEvent(new Event('change'));document.getElementById('historyStart').value='2024-12-15';document.getElementById('historyEnd').value='2025-01-15';document.getElementById('historyEnd').dispatchEvent(new Event('change'));document.getElementById('historicalOos').scrollIntoView()");
    const historicalDatesWork=await evaluate("historicalRows().length>0 && historicalRows().every(r=>r.date>='2024-12-15'&&r.date<='2025-01-15') && new Set(historicalRows().map(r=>r.year)).size===2 && document.getElementById('historyModelHashes').textContent.includes('fold 2025')");
    const historicalDesktop=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('dashboard_history_desktop.png');
    const historicalDownloadFolder=path.join(preview,'downloads','history-'+Date.now());fs.mkdirSync(historicalDownloadFolder,{recursive:true});
    await call('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:historicalDownloadFolder});
    await call('Runtime.evaluate',{expression:"document.getElementById('exportHistoricalOos').click()",userGesture:true});
    const historicalCsvFile=path.join(historicalDownloadFolder,'historical_oos_eth_return_matched_asof_d3_2024-12-15_2025-01-15.csv');
    for(let i=0;i<50&&!fs.existsSync(historicalCsvFile);i++)await delay(100);
    if(!fs.existsSync(historicalCsvFile))throw Error('Historical CSV button produced no file');
    const historicalCsvWorks=fs.readFileSync(historicalCsvFile,'utf8')===await evaluate('historicalOosCsv()');
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
    await evaluate("document.getElementById('historicalOos').scrollIntoView()");
    const historicalMobile=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('dashboard_history_mobile.png');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    await evaluate("document.getElementById('tab-transmission').click()");
    await evaluate("document.getElementById('asset').value='eth';document.getElementById('shock').value='usd_return_pct';document.getElementById('regime').value='stress';document.getElementById('horizon').value='30';document.getElementById('horizon').dispatchEvent(new Event('change'))");
    await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
    const selectionWorks=await evaluate("document.getElementById('selectionLabel').textContent==='ETH · Căng thẳng · 30 ngày' && responseCsv().split('\\r\\n').length===31");
    const horizonReusesCurve=await evaluate("(()=>{const curve=document.getElementById('primaryCurve'),points=curve.getAttribute('d');document.querySelector('[data-horizon=\"14\"]').click();return curve===document.getElementById('primaryCurve') && points===curve.getAttribute('d') && document.getElementById('responseMetricLabel').textContent.includes('14')})()");
    await evaluate("document.querySelector('[data-horizon=\"30\"]').click()");
    await evaluate("document.getElementById('responseDataTable').closest('details').open=true;document.getElementById('rollingDataTable').closest('details').open=true");
    await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
    const lazyTablesWork=await evaluate("document.getElementById('responseDataTable').querySelectorAll('tbody tr').length===30&&document.getElementById('rollingDataTable').querySelectorAll('tbody tr').length>1");
    await evaluate("document.getElementById('responseDataTable').closest('details').open=false;document.getElementById('rollingDataTable').closest('details').open=false");
    const downloadFolder=path.join(preview,'downloads',String(Date.now()));fs.mkdirSync(downloadFolder,{recursive:true});
    await call('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloadFolder});
    await call('Runtime.evaluate',{expression:"document.getElementById('exportResponse').click()",userGesture:true});
    const csvFile=path.join(downloadFolder,'eth_usd_return_pct_stress_response.csv');
    for(let i=0;i<50&&!fs.existsSync(csvFile);i++)await delay(100);
    if(!fs.existsSync(csvFile))throw Error('CSV download button produced no file');
    const exported=fs.readFileSync(csvFile,'utf8'),expectedExport=await evaluate('responseCsv()');
    const csvDownloadWorks=exported===expectedExport && exported.replace(/^\ufeff/,'').split('\r\n').length===31;
    await evaluate("document.getElementById('resetResponse').click()");
    const resetWorks=await evaluate("document.getElementById('asset').value==='btc' && document.getElementById('horizon').value==='1'");
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
    await evaluate('window.scrollTo(0,0)');
    const dashboardMobile=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('dashboard_mobile.png');
    await evaluate("document.getElementById('openFilters').click()");
    const mobileFiltersWork=await evaluate("document.getElementById('filterSheet').open&&document.getElementById('filterSheet').contains(document.getElementById('responseControls'))");
    await screenshot('dashboard_aurora_mobile_filters.png');
    await evaluate("document.getElementById('applyMobileFilters').click()");
    await evaluate('new Promise(resolve=>requestAnimationFrame(resolve))');
    await evaluate("document.getElementById('openNavigation').click()");
    const mobileMenuWorks=await evaluate("(()=>{const d=document.getElementById('navDrawer');if(!d.open)return false;d.querySelector('[data-goto=fomc]').click();return !d.open&&!document.getElementById('fomc').hidden&&document.documentElement.scrollWidth<=innerWidth+1})()");
    const result = {browser:'Chrome',desktop_width:1280,mobile_width:390,
      desktop_no_horizontal_overflow:desktop,mobile_no_horizontal_overflow:mobile,
      oos_desktop_no_overflow:oosDesktop,oos_mobile_no_overflow:oosMobile,oos_local_links_verified:oosLinks.length,
      automation_desktop_no_overflow:automationDesktop,automation_mobile_no_overflow:automationMobile,
      dashboard_desktop_no_overflow:dashboardDesktop,dashboard_mobile_no_overflow:dashboardMobile,starts_with_estimator:startsWithEstimator,no_academic_warning_on_main:noWarningOnMain,workspace_buttons_work:tabButtonsWork,selection_controls_work:selectionWorks,reset_button_works:resetWorks,csv_download_matches_selected_curve:csvDownloadWorks,tables:counts.length,
      historical_dates_work:historicalDatesWork,historical_csv_download_matches:historicalCsvWorks,historical_desktop_no_overflow:historicalDesktop,historical_mobile_no_overflow:historicalMobile,
      local_links_verified:local.length,horizon_reuses_curve:horizonReusesCurve,lazy_detail_tables_verified:lazyTablesWork,live_data_tables_verified:liveDataWorks,live_desktop_no_overflow:liveDesktop,live_mobile_no_overflow:liveMobile,uncaught_errors:errors.length};
    Object.assign(result,{fomc_aggregate_verified:fomcAggregateWorks,fomc_event_selection_verified:fomcEventsWork,fomc_event_csv_verified:fomcCsvWorks,fomc_event_list_verified:fomcListWorks,fomc_mobile_no_overflow:fomcMobile});
    Object.assign(result,{aurora_vertical_navigation_verified:auroraLayoutWorks,sidebar_collapse_verified:sidebarCollapseWorks,sidebar_drag_resize_verified:sidebarResizeWorks,sidebar_persistence_verified:sidebarPersistenceWorks,light_theme_verified:lightThemeWorks,tablet_no_overflow:tabletLayoutWorks,mobile_filters_verified:mobileFiltersWork,mobile_navigation_verified:mobileMenuWorks});
    if(!auroraLayoutWorks||!sidebarCollapseWorks||!sidebarResizeWorks||!sidebarPersistenceWorks||!lightThemeWorks||!tabletLayoutWorks||!mobileFiltersWork||!mobileMenuWorks)throw Error('Aurora UI checks failed: '+JSON.stringify(result));
    if(!fomcAggregateWorks||!fomcEventsWork||!fomcCsvWorks||!fomcListWorks||!fomcMobile)throw Error('FOMC UI checks failed: '+JSON.stringify(result));
    fs.writeFileSync(path.join(out,'browser_validation.json'),JSON.stringify(result,null,2));
    if (!desktop || !mobile || !oosDesktop || !oosMobile || !automationDesktop || !automationMobile || !dashboardDesktop || !dashboardMobile || !startsWithEstimator || !noWarningOnMain || !tabButtonsWork || !selectionWorks || !resetWorks || !csvDownloadWorks || !historicalDatesWork || !historicalCsvWorks || !historicalDesktop || !historicalMobile || !horizonReusesCurve || !lazyTablesWork || !liveDataWorks || !liveDesktop || !liveMobile || errors.length) throw Error(JSON.stringify(result));
    console.log(JSON.stringify(result,null,2));
  } finally {
    if (socket && socket.readyState===WebSocket.OPEN) {
      try {await call('Browser.close');} catch {}
      socket.close();
    }
    if (child && !child.killed) child.kill();
    await delay(400);
    const relative = path.relative(allowed,path.resolve(profile));
    if (relative && !relative.startsWith('..') && !path.isAbsolute(relative)) {
      try {fs.rmSync(profile,{recursive:true,force:true});} catch {}
    }
  }
})().catch(error=>{console.error(error.stack||String(error));process.exitCode=1;});
