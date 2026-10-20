// Real headless Chrome QA through local DevTools; no browser package or server needed.
const fs=require('fs'),path=require('path'),{spawn}=require('child_process'),{pathToFileURL}=require('url');
const root=__dirname,out=path.join(root,'outputs/research/synthesis'),qa=path.join(out,'preview');
const chrome='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const profile=path.resolve(root,'.preview',`synthesis-${process.pid}-${Date.now()}`);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
fs.mkdirSync(qa,{recursive:true});fs.mkdirSync(profile,{recursive:true});
let child,ws,serial=0;const pending=new Map(),errors=[];
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++serial;const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout '+method));},12000);pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v)},reject});ws.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
async function navigate(file){await call('Page.navigate',{url:pathToFileURL(path.join(out,file)).href});for(let i=0;i<60;i++){if(await evaluate("document.readyState==='complete' && Array.from(document.images).every(i=>i.complete)")){await sleep(250);return;}await sleep(100);}throw Error('Page did not finish '+file);}
async function shot(name){await sleep(150);const image=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(qa,name),Buffer.from(image.data,'base64'));}
(async()=>{
 try{
  child=spawn(chrome,['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,'--remote-debugging-port=0','about:blank'],{windowsHide:true,stdio:'ignore'});
  let port;for(let i=0;i<120;i++){const f=path.join(profile,'DevToolsActivePort');if(fs.existsSync(f)){port=fs.readFileSync(f,'utf8').split(/\r?\n/)[0];break;}await sleep(100);}if(!port)throw Error('Chrome DevTools did not start');
  const tabs=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();const tab=tabs.find(t=>t.type==='page');
  ws=new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
  ws.addEventListener('message',e=>{const msg=JSON.parse(e.data);if(msg.id&&pending.has(msg.id)){const p=pending.get(msg.id);pending.delete(msg.id);msg.error?p.reject(Error(JSON.stringify(msg.error))):p.resolve(msg.result);}if(msg.method==='Runtime.exceptionThrown')errors.push(msg.params.exceptionDetails);});
  await call('Page.enable');await call('Runtime.enable');
  await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1100,deviceScaleFactor:1,mobile:false});
  await navigate('dashboard.html');
  const interactions=await evaluate(`(()=>{let n=0;for(const a of ['btc','eth'])for(const g of ['full','pre2020','post2020'])for(const s of Object.keys(DATA.shock_labels)){el('asset').value=a;el('regime').value=g;el('shock').value=s;refreshLP();for(const h of [0,1,2,5,10,20,30]){el('horizon').value=String(h);drawLP();if(/NaN|undefined|Infinity/.test(el('lpChart').innerHTML+el('lpPoint').textContent))throw Error('Bad LP');n++;}}for(const a of ['BTC','ETH'])for(const t of ['MP1_10bps','MP2_10bps','STMT_10bps']){el('eventAsset').value=a;el('eventTerm').value=t;renderEvents();if(el('eventTable').querySelectorAll('tbody tr').length!==2)throw Error('Bad event table');}el('asset').value='btc';el('regime').value='full';el('shock').value='vix_change';el('horizon').value='0';refreshLP();el('eventAsset').value='BTC';el('eventTerm').value='STMT_10bps';renderEvents();return {lp:n,event:6};})()`);
  const desktop=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
  await shot('dashboard_desktop.png');
  await evaluate("document.getElementById('fomc').scrollIntoView();window.scrollBy(0,-12)");await shot('dashboard_fomc.png');
  await evaluate("document.getElementById('rolling').scrollIntoView();window.scrollBy(0,-12)");await shot('dashboard_rolling.png');
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
  await evaluate('window.scrollTo(0,0)');await shot('dashboard_mobile.png');
  const mobile=await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
  await evaluate("document.getElementById('lp').scrollIntoView();window.scrollBy(0,-8)");await shot('dashboard_mobile_lp.png');
  await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1100,deviceScaleFactor:1,mobile:false});
  await navigate('report.html');
  const imagesOK=await evaluate('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)');
  await shot('report_desktop.png');
  const result={actual_headless_browser:'Chrome',desktop_width:1280,mobile_width:390,desktop_no_horizontal_overflow:desktop,mobile_no_horizontal_overflow:mobile,report_images_loaded:imagesOK,real_browser_LP_states:interactions.lp,real_browser_FOMC_states:interactions.event,uncaught_page_errors:errors.length,screenshots:fs.readdirSync(qa).filter(n=>n.endsWith('.png'))};
  fs.writeFileSync(path.join(out,'browser_validation.json'),JSON.stringify(result,null,2));
  if(!desktop||!mobile||!imagesOK||errors.length)throw Error(JSON.stringify(result));
  console.log(JSON.stringify(result,null,2));
 }finally{
  if(ws&&ws.readyState===WebSocket.OPEN){try{await call('Browser.close')}catch{}ws.close();}
  if(child&&!child.killed)child.kill();
  await sleep(400);
  // Only remove the absolute, task-created profile under this workspace.
  const allowed=path.resolve(root,'.preview')+path.sep;
  if(profile.startsWith(allowed)){try{fs.rmSync(profile,{recursive:true,force:true})}catch{}}
 }
})().catch(e=>{console.error(e.stack||String(e));process.exitCode=1;});
