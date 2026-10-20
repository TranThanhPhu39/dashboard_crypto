// Actual headless Chrome QA, using a workspace-local disposable browser profile.
const fs=require('fs'),path=require('path'),{spawn}=require('child_process'),{pathToFileURL}=require('url');
const root=__dirname,out=path.join(root,'outputs/research/completion'),qa=path.join(out,'preview');
const profile=path.resolve(root,'.preview',`completion-${process.pid}-${Date.now()}`);
const chrome='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));fs.mkdirSync(qa,{recursive:true});fs.mkdirSync(profile,{recursive:true});
let child,ws,serial=0;const pending=new Map(),errors=[];
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++serial;const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout '+method));},15000);pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v)},reject});ws.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function navigate(file){await call('Page.navigate',{url:pathToFileURL(path.join(out,file)).href});for(let i=0;i<60;i++){if(await evaluate("document.readyState==='complete' && Array.from(document.images).every(i=>i.complete)")){await sleep(200);return;}await sleep(100);}throw Error('Load timeout '+file);}
async function shot(name){await sleep(150);const r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(qa,name),Buffer.from(r.data,'base64'));}
(async()=>{
 try{
  child=spawn(chrome,['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,'--remote-debugging-port=0','about:blank'],{windowsHide:true,stdio:'ignore'});
  let port;for(let i=0;i<120;i++){const f=path.join(profile,'DevToolsActivePort');if(fs.existsSync(f)){port=fs.readFileSync(f,'utf8').split(/\r?\n/)[0];break;}await sleep(100);}if(!port)throw Error('Chrome did not start');
  const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
  ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);});
  await call('Page.enable');await call('Runtime.enable');await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1100,deviceScaleFactor:1,mobile:false});await navigate('dashboard.html');
  const counts=await evaluate(`(()=>{
    let lp=0,examples=0,forecast=0;
    for(const a of ['btc','eth'])for(const state of ['full','pre2020','post2020','calm','stress'])for(const s of Object.keys(DATA.shock_labels)){
      el('asset').value=a;el('regime').value=state;el('shock').value=s;refreshLP();
      const hs=['calm','stress'].includes(state)?[0,1,5,10,20]:[0,1,2,5,10,20,30];
      if(el('horizon').options.length!==hs.length)throw Error('Wrong horizon choices');
      for(const h of hs){el('horizon').value=String(h);drawLP();if(/NaN|undefined|Infinity/.test(el('lpChart').innerHTML+el('lpCI').textContent))throw Error('Bad chart');lp++;}
    }
    for(const a of ['btc','eth'])for(const s of Object.keys(DATA.shock_labels))for(const state of ['calm','stress'])for(const h of [0,1,5,10,20]){el('analogueAsset').value=a;el('analogueShock').value=s;el('analogueState').value=state;el('analogueH').value=String(h);renderAnalogues();if(el('analogueTable').querySelectorAll('tbody tr').length!==5)throw Error('Missing examples');examples++;}
    for(const t of ['return','squared_return'])for(const m of ['elastic_net','gradient_boosting'])for(const p of ['0','1','2','3']){el('target').value=t;el('forecastModel').value=m;el('forecastComparison').value=p;renderForecasts();if(el('forecastTable').querySelectorAll('tbody tr').length!==2)throw Error('Missing ablation');forecast++;}
    el('asset').value='btc';el('regime').value='stress';el('shock').value='vix_change';refreshLP();
    el('target').value='squared_return';el('forecastModel').value='gradient_boosting';el('forecastComparison').value='1';renderForecasts();
    return {lp,examples,forecast};
  })()`);
  const desktop=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');await shot('dashboard_desktop.png');
  for(const section of ['lp','analogues','forecast']){await evaluate(`document.getElementById('${section}').scrollIntoView();window.scrollBy(0,-10)`);await shot(`dashboard_${section}.png`);}
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
  await evaluate('window.scrollTo(0,0)');await shot('dashboard_mobile.png');
  const mobile=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
  await evaluate("document.getElementById('forecast').scrollIntoView();window.scrollBy(0,-10)");await shot('dashboard_mobile_forecast.png');
  await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1100,deviceScaleFactor:1,mobile:false});await navigate('report.html');
  const images=await evaluate('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)');const reportNoOverflow=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');await shot('report_desktop.png');
  const result={browser:'Chrome',desktop_width:1280,mobile_width:390,desktop_no_horizontal_overflow:desktop,mobile_no_horizontal_overflow:mobile,report_no_horizontal_overflow:reportNoOverflow,report_images_loaded:images,LP_and_state_selections:counts.lp,historical_views:counts.examples,forecast_combinations:counts.forecast,uncaught_errors:errors.length,screenshots:fs.readdirSync(qa).filter(n=>n.endsWith('.png'))};
  fs.writeFileSync(path.join(out,'browser_validation.json'),JSON.stringify(result,null,2));if(!desktop||!mobile||!images||!reportNoOverflow||errors.length)throw Error(JSON.stringify(result));console.log(JSON.stringify(result,null,2));
 }finally{
  if(ws&&ws.readyState===WebSocket.OPEN){try{await call('Browser.close')}catch{}ws.close();}if(child&&!child.killed)child.kill();await sleep(400);
  const allowed=path.resolve(root,'.preview')+path.sep;
  if(profile.startsWith(allowed)){try{fs.rmSync(profile,{recursive:true,force:true})}catch{}}
 }
})().catch(e=>{console.error(e.stack||String(e));process.exitCode=1;});
