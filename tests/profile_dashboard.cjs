/* Real-browser interaction timings; use the same CPU setting before/after. */
const fs=require('fs'),path=require('path'),{spawn}=require('child_process'),{pathToFileURL}=require('url');
const root=path.resolve(__dirname,'..'),flag=name=>process.argv.find(x=>x.startsWith('--'+name+'='))?.split('=').slice(1).join('=');
const cpu=Number(flag('cpu')||4),label=flag('label')||'current',snapshot=path.join(root,flag('snapshot')||'dashboard/index.html'),url=flag('url')||pathToFileURL(snapshot).href;
const folder=path.join(root,'.verification/performance'),profile=path.join(root,'.preview','performance-'+process.pid+'-'+Date.now());
const pause=ms=>new Promise(r=>setTimeout(r,ms));let child,socket,serial=0;const pending=new Map(),errors=[],requests=[];
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++serial,timer=setTimeout(()=>{pending.delete(id);reject(Error('Timeout '+method));},45000);pending.set(id,{resolve:x=>{clearTimeout(timer);resolve(x);},reject});socket.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
(async()=>{
 fs.mkdirSync(folder,{recursive:true});fs.mkdirSync(profile,{recursive:true});
 try{
  child=spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',['--headless=new','--disable-gpu','--no-first-run','--disable-background-networking',`--user-data-dir=${profile}`,'--remote-debugging-port=0','about:blank'],{windowsHide:true,stdio:'ignore'});
  let port;for(let i=0;i<100;i++){const p=path.join(profile,'DevToolsActivePort');if(fs.existsSync(p)){port=fs.readFileSync(p,'utf8').split(/\r?\n/)[0];break;}await pause(100);}if(!port)throw Error('Chrome did not start');
  const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(tabs.find(x=>x.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
  socket.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);if(m.method==='Network.requestWillBeSent'&&!m.params.request.url.startsWith('data:'))requests.push(m.params.request.url);});
  await call('Page.enable');await call('Runtime.enable');await call('Network.enable');await call('Network.setCacheDisabled',{cacheDisabled:true});
  await call('Emulation.setCPUThrottlingRate',{rate:cpu});await call('Emulation.setDeviceMetricsOverride',{width:1365,height:900,deviceScaleFactor:1,mobile:false});
  await call('Page.addScriptToEvaluateOnNewDocument',{source:`window.__longTasks=[];new PerformanceObserver(list=>window.__longTasks.push(...list.getEntries().map(e=>({start:e.startTime,duration:e.duration})))).observe({type:'longtask',buffered:true});`});
  if(flag('trace')==='boot'){await call('Profiler.enable');await call('Profiler.start');}
  const started=Date.now();await call('Page.navigate',{url});let ready=false;
  for(let i=0;i<400;i++){ready=await evaluate("document.documentElement?.dataset.orbitStudioReady==='true'");if(ready)break;await pause(150);}if(!ready)throw Error('Dashboard failed to initialize '+JSON.stringify(errors));
  const bootWall=Date.now()-started;
  const replayDeferred=!requests.some(u=>/replay-[a-f0-9]+\.bin/.test(u));
  if(!replayDeferred)throw Error('Replay asset was eagerly fetched before forecast');
  if(flag('trace')==='boot'){const trace=await call('Profiler.stop');fs.writeFileSync(path.join(folder,label+'.cpuprofile'),JSON.stringify(trace.profile));}
  await pause(500);
  const boot=await evaluate(`({ready_ms:performance.now(),navigation:performance.getEntriesByType('navigation')[0]?.toJSON(),long_tasks:window.__longTasks.slice(),dom_nodes:document.querySelectorAll('*').length})`);
  await evaluate(`window.__renderCounts={};for(const name of ['renderResponse','renderForecast','renderHistoricalOos','renderRolling','renderFOMC','renderVAR','renderQuantile']){const original=window[name];window[name]=function(...args){window.__renderCounts[name]=(window.__renderCounts[name]||0)+1;return original.apply(this,args);};}`);
  const results=[];
  async function measure(name,action){const result=await evaluate(`(async()=>{window.__renderCounts={};const started=performance.now();${action};const handler=performance.now()-started;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));const paint=performance.now()-started;await new Promise(r=>setTimeout(r,470));return {name:${JSON.stringify(name)},handler_ms:handler,paint_ms:paint,render_counts:{...window.__renderCounts},long_tasks:window.__longTasks.filter(t=>t.start>=started),response_ms:document.documentElement.dataset.responseRenderMs};})()`);results.push(result);}
  if(flag('trace')==='navigation'){await call('Profiler.enable');await call('Profiler.start');}
  for(const [name,view] of [['fomc_first','fomc'],['advanced_first','advanced'],['transmission_return','transmission'],['fomc_warm','fomc'],['advanced_warm','advanced'],['transmission_warm','transmission']])await measure(name,`document.getElementById('tab-${view}').click()`);
  if(flag('trace')==='navigation'){const trace=await call('Profiler.stop');fs.writeFileSync(path.join(folder,label+'.cpuprofile'),JSON.stringify(trace.profile));}
  if(flag('trace')==='response'){await call('Profiler.enable');await call('Profiler.start');}
  await measure('asset_switch',"document.querySelector('[data-asset=eth]').click()");
  await measure('regime_switch',"document.querySelector('[data-regime=stress]').click()");
  await evaluate("window.__curveNode=document.getElementById('primaryCurve');window.__curvePath=window.__curveNode.getAttribute('d')");
  await measure('horizon_slider',"document.getElementById('horizonSlider').value='14';document.getElementById('horizonSlider').dispatchEvent(new Event('input',{bubbles:true}))");
  const horizonRetained=await evaluate("window.__curveNode===document.getElementById('primaryCurve')&&window.__curvePath===document.getElementById('primaryCurve').getAttribute('d')");
  await measure('horizon_preset',"document.querySelector('[data-horizon=\"30\"]').click()");
  if(flag('trace')==='response'){const trace=await call('Profiler.stop');fs.writeFileSync(path.join(folder,label+'.cpuprofile'),JSON.stringify(trace.profile));}
  const historyStart=Date.now();await evaluate("showWorkspace('forecast')");
  for(let i=0;i<300;i++){if(await evaluate("Boolean(HISTORICAL.series)&&document.getElementById('historyCount').textContent!==''&&document.getElementById('historyLoading').hidden"))break;await pause(100);}
  const history=await evaluate("({decode_ms:document.documentElement.dataset.historyLoadMs,rows:document.getElementById('historyCount').textContent,ready:Boolean(HISTORICAL.series)})");history.wall_ms=Date.now()-historyStart;if(!history.ready)throw Error('Replay did not load');await pause(500);
  await measure('forecast_model',"document.getElementById('forecastModel').value='gradient_boosting';document.getElementById('forecastModel').dispatchEvent(new Event('change',{bubbles:true}))");
  await measure('forecast_asset',"document.getElementById('fAsset').value='eth';document.getElementById('fAsset').dispatchEvent(new Event('change',{bubbles:true}))");
  await measure('historical_range',"document.getElementById('historyStart').value='2024-01-01';document.getElementById('historyStart').dispatchEvent(new Event('change',{bubbles:true}))");
  await measure('historical_day',"document.getElementById('historyDay').value='2025-01-02';document.getElementById('historyDay').dispatchEvent(new Event('change',{bubbles:true}))");
  await measure('return_transmission',"showWorkspace('transmission')");
  const result={url,cpu_throttle:cpu,html_bytes:fs.statSync(snapshot).size,cold_boot_wall_ms:bootWall,boot,history,interactions:results,horizon_reuses_curve:horizonRetained,replay_not_requested_at_boot:replayDeferred,replay_asset_requests:requests.filter(u=>/replay-[a-f0-9]+\.bin/.test(u)).length,uncaught_errors:errors.length};
  fs.writeFileSync(path.join(folder,label+'.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify({label,cpu,boot_ms:boot.ready_ms,boot_long_tasks:boot.long_tasks.map(t=>t.duration),history,interactions:results.map(r=>({name:r.name,handler_ms:r.handler_ms,paint_ms:r.paint_ms,render_counts:r.render_counts})),uncaught_errors:errors.length},null,2));if(errors.length)throw Error('Browser errors');
 }finally{if(socket&&socket.readyState===WebSocket.OPEN){try{await call('Browser.close');}catch{}socket.close();}if(child&&!child.killed)child.kill();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
