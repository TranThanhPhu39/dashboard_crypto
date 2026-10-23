/* Verify every event path and saved CI used by the new FOMC view. */
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'dashboard/index.html'),'utf8');
const data=JSON.parse(source.match(/const FOMC_RESEARCH=(.*?);\s*\/\* Presentation of saved FOMC/s)[1]);
const context=vm.createContext({FOMC_RESEARCH:data,esc:x=>String(x)});
vm.runInContext(fs.readFileSync(path.join(root,'dashboard/fomc.js'),'utf8'),context);
assert.strictEqual(data.sample.count,75);assert.strictEqual(data.events.length,75);
assert.strictEqual(data.sample.first_date,'2016-09-21');assert.strictEqual(data.sample.last_date,'2026-07-29');
let points=0;
for(const event of data.events)for(const asset of ['BTC','ETH']){
 context.event=event;context.asset=asset;
 assert.strictEqual(new Date(event.event_time_et).valueOf(),new Date(event.event_time_utc).valueOf());
 assert(event.statement_url.endsWith('monetary'+event.date.replace(/-/g,'')+'a.htm'));
 for(const windowName of ['intraday','post']){
  context.windowName=windowName;
  const rows=vm.runInContext('orbitFomcPoints(event,asset,windowName)',context);
  assert.strictEqual(rows.length,31);assert.strictEqual(rows[0].y,0);
  for(let i=0;i<31;i++)assert.strictEqual(rows[i].y,windowName==='intraday'?event.assets[asset].minute_path[i][1]:i===0?0:event.assets[asset].returns['post_'+i]);
  context.rows=rows;
  for(const width of [360,720]){
   context.width=width;
   const html=vm.runInContext("orbitFomcPlot(rows,{width,marker:windowName==='intraday'?0:null})",context);
   assert(!/NaN|undefined|Infinity/.test(html));assert.strictEqual((html.match(/<circle /g)||[]).length,31);
  }
  points+=rows.length;
 }
}
for(const asset of ['BTC','ETH'])for(const shock of ['policy','information']){
 const rows=data.intervals.filter(r=>r.asset===asset&&r.shock===shock&&r.outcome.startsWith('post_')).sort((a,b)=>Number(a.outcome.slice(5))-Number(b.outcome.slice(5)));
 assert.strictEqual(rows.length,30);context.rows=rows.map(r=>({x:Number(r.outcome.slice(5)),y:r.beta,lo:r.lower95,hi:r.upper95}));
 const html=vm.runInContext('orbitFomcPlot(rows)',context);assert(html.includes('fomc-ci-band'));assert(!/NaN|Infinity/.test(html));
}
context.rows=[{x:1,y:null}];assert.throws(()=>vm.runInContext('orbitFomcPlot(rows)',context),/Nonfinite/);
console.log(JSON.stringify({fomc_events:75,event_path_points_checked:points,median_rotation_intervals:data.intervals.length,eastern_utc_alignment:true,desktop_mobile_plots:true}));
