const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'..'),out=path.join(root,'outputs/research/robustness_20261019');
const source=fs.readFileSync(path.join(out,'dashboard.html'),'utf8'),script=source.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element{constructor(value=''){this.value=value;this.innerHTML='';this.textContent='';}addEventListener(){}}
const defaults={asset:'btc',horizon:'1',scenario:'baseline',yield:'us2y',regime:'full',equation:'btc_return_pct'};
const elements={};for(const m of source.matchAll(/id="([^"]+)"/g)){if(elements[m[1]])throw Error('Duplicate id');elements[m[1]]=new Element(defaults[m[1]]||'');}
const ctx=vm.createContext({document:{getElementById:id=>{if(!elements[id])throw Error('Missing '+id);return elements[id]}},console});
const run=s=>vm.runInContext(s,ctx,{timeout:10000});run(script);
function finite(ids){for(const id of ids)if(/NaN|undefined|Infinity/.test(elements[id].innerHTML+elements[id].textContent))throw Error('Nonfinite '+id);}
const scenarios=run('Array.from(new Set(DATA.monetary.map(r=>r.scenario)))');let monetary=0,joint=0;
for(const a of ['btc','eth'])for(let h=1;h<=30;h++)for(const s of scenarios){
 elements.asset.value=a;elements.horizon.value=String(h);elements.scenario.value=s;run('renderMonetary()');finite(['monetaryPoint','monetaryCI','monetarySupport','monetaryChart','monetaryTable']);
 const beta=run(`DATA.monetary.find(r=>r.asset==='${a}'&&r.horizon_days===${h}&&r.scenario==='${s}').difference_pct`);
 if(!elements.monetaryPoint.textContent.includes(Number(beta).toFixed(4)))throw Error('Wrong slope');
 if((elements.monetaryTable.innerHTML.match(/<tr>/g)||[]).length!==12)throw Error('Wrong scenario count');monetary++;
}
for(const y of ['us2y','us10y'])for(const r of ['full','pre2020','post2020']){
 elements.yield.value=y;elements.regime.value=r;run('equationOptions()');
 for(const e of ['btc_return_pct','eth_return_pct','vix_change','usd_return_pct',y+'_change_bps']){
  elements.equation.value=e;run('renderVAR()');finite(['varStatus','varChart','archTable','crossTable']);
  if((elements.archTable.innerHTML.match(/<tr>/g)||[]).length!==3)throw Error('ARCH rows');
  if((elements.crossTable.innerHTML.match(/<tr>/g)||[]).length!==6)throw Error('Cross rows');joint++;
 }
}
let links=0;for(const file of ['dashboard.html','report.html']){
 const html=fs.readFileSync(path.join(out,file),'utf8');for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g)){
  const url=m[1];if(/^(http|#|data:)/.test(url))continue;if(!fs.existsSync(path.resolve(out,url)))throw Error('Broken '+url);links++;
 }
}
const result={monetary_views:monetary,joint_residual_views:joint,finite_values:true,source_coefficients_verified:true,local_links_verified:links};fs.writeFileSync(path.join(out,'dashboard_validation.json'),JSON.stringify(result,null,2));console.log(result);
