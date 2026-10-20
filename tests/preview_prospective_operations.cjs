// Offline operational report QA in headless Chrome; no forecast/data mutations.
const fs = require('fs'), path = require('path'), {spawn} = require('child_process');
const {pathToFileURL} = require('url');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'outputs/research/evidence_20261019/prospective_operations');
const preview = path.join(out, 'preview');
const allowed = path.resolve(root, '.preview');
const profile = path.join(allowed, `prospective-operations-${process.pid}-${Date.now()}`);
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
  const result = await call('Runtime.evaluate', {expression, returnByValue:true});
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
    if (JSON.stringify(counts)!=='[8,2,14]') throw Error('Unexpected table coverage '+JSON.stringify(counts));
    const hrefs = await evaluate('Array.from(document.querySelectorAll("a[href]")).map(a=>a.getAttribute("href"))');
    const local = hrefs.filter(href=>!/^https?:/.test(href));
    for (const href of local) if (!fs.existsSync(path.resolve(out,href))) throw Error('Missing link '+href);
    await screenshot('report_desktop.png');
    await evaluate('document.querySelectorAll("section")[2].scrollIntoView()');
    await screenshot('coverage_desktop.png');
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:900,deviceScaleFactor:1,mobile:true});
    await evaluate('window.scrollTo(0,0)');
    const mobile = await evaluate('document.documentElement.scrollWidth<=innerWidth+1');
    await screenshot('report_mobile.png');
    const result = {browser:'Chrome',desktop_width:1280,mobile_width:390,
      desktop_no_horizontal_overflow:desktop,mobile_no_horizontal_overflow:mobile,
      rule_rows:counts[0],coverage_rows:counts[1],readiness_days:counts[2],
      local_links_verified:local.length,uncaught_errors:errors.length};
    fs.writeFileSync(path.join(out,'browser_validation.json'),JSON.stringify(result,null,2));
    if (!desktop || !mobile || errors.length) throw Error(JSON.stringify(result));
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
