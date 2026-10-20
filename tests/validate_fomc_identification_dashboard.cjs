const fs=require('fs'),path=require('path'),vm=require('vm');const root=path.resolve(__dirname,'..'),out=path.join(root,'outputs/research/fomc_identification_20261019');
const html=fs.readFileSync(path.join(out,'dashboard.html'),'utf8'),script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element{constructor(value=''){this.value=value;this.innerHTML='';this.textContent='';}addEventListener(){}}
const defaults={asset:'BTC',shock:'policy',regime:'full',outcome:'intraday'},els={};for(const m of html.matchAll(/id="([^"]+)"/g)){if(els[m[1]])throw Error('Duplicate id');els[m[1]]=new Element(defaults[m[1]]||'');}
const ctx=vm.createContext({document:{getElementById:id=>{if(!els[id])throw Error('Missing '+id);return els[id]}},console});const run=s=>vm.runInContext(s,ctx,{timeout:10000});run(script);
const lines=fs.readFileSync(path.join(out,'timing_estimates.csv'),'utf8').replace(/^\uFEFF/,'').trim().split(/\r?\n/),header=lines.shift().split(',');const rows=lines.map(line=>Object.fromEntries(line.split(',').map((v,i)=>[header[i],v])));let views=0;
for(const a of ['BTC','ETH'])for(const s of ['policy','information'])for(const g of ['full','pre2020','post2020'])for(const o of ['intraday','event_day',...Array.from({length:30},(_,i)=>'post_'+(i+1))]){
 els.asset.value=a;els.shock.value=s;els.regime.value=g;els.outcome.value=o;run('render()');
 for(const id of ['responsePoint','responseInference','timingTable','responseChart','differenceTable','rotationTable','influenceTable','sensitivityWarning'])if(/NaN|undefined|Infinity/.test(els[id].innerHTML+els[id].textContent))throw Error('Invalid '+id);
 const r=rows.find(r=>r.asset===a&&r.shock===s&&r.regime===g&&r.outcome===o);if(!els.responsePoint.textContent.includes(Number(r.beta_pct_per10bps).toFixed(4)))throw Error('Wrong source beta');
 if((els.rotationTable.innerHTML.match(/<tr>/g)||[]).length!==4)throw Error('Rotation rows');
 if((els.differenceTable.innerHTML.match(/<tr>/g)||[]).length!==3)throw Error('Difference rows');views++;
}
let links=0;for(const file of ['dashboard.html','report.html'])for(const m of fs.readFileSync(path.join(out,file),'utf8').matchAll(/(?:href|src)="([^"]+)"/g)){
 const url=m[1];if(/^(http|data:|#)/.test(url))continue;if(!fs.existsSync(path.resolve(out,url)))throw Error('Broken '+url);links++;
}
const result={response_views:views,source_coefficients_verified:true,rotation_and_direct_difference_views:views,finite_values:true,local_links_verified:links};fs.writeFileSync(path.join(out,'dashboard_validation.json'),JSON.stringify(result,null,2));console.log(result);
