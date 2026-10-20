const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'..'),out=path.join(root,'outputs/research/latency_20261019');
const source=fs.readFileSync(path.join(out,'dashboard.html'),'utf8'),script=source.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element{constructor(value=''){this.value=value;this.textContent='';this.innerHTML='';}addEventListener(){}}
const defaults={asset:'btc',target:'squared_return',model:'elastic_net',pair:'0'},els={};
for(const match of source.matchAll(/id="([^"]+)"/g)){if(els[match[1]])throw Error('Duplicate id');els[match[1]]=new Element(defaults[match[1]]||'');}
const ctx=vm.createContext({document:{getElementById:id=>{if(!els[id])throw Error('Missing '+id);return els[id]}},console});const run=s=>vm.runInContext(s,ctx,{timeout:10000});run(script);
const csv=fs.readFileSync(path.join(out,'ablation_tests.csv'),'utf8').replace(/^\uFEFF/,'').trim().split(/\r?\n/);const header=csv.shift().split(',');const rows=csv.map(line=>Object.fromEntries(line.split(',').map((v,i)=>[header[i],v])));
let views=0;const pairs=[['long_own','long_macro'],['common_own','common_macro'],['common_macro','common_usd'],['common_own','common_usd']];
for(const a of ['btc','eth'])for(const t of ['return','squared_return'])for(const m of ['elastic_net','gradient_boosting'])for(let p=0;p<4;p++){
 els.asset.value=a;els.target.value=t;els.model.value=m;els.pair.value=String(p);run('render()');
 for(const id of ['comparisonPoint','comparisonInference','metricsTable','lossChart','benchmarkTable','timingTable'])if(/NaN|undefined|Infinity/.test(els[id].innerHTML+els[id].textContent))throw Error('Bad '+id);
 const r=rows.find(r=>r.asset===a&&r.target===t&&r.model===m&&r.base===pairs[p][0]&&r.added===pairs[p][1]);
 if(!els.comparisonPoint.textContent.includes(Number(r.mean_loss_added_minus_base).toFixed(6)))throw Error('Wrong source loss');
 for(const id of ['metricsTable','benchmarkTable','timingTable'])if((els[id].innerHTML.match(/<tr>/g)||[]).length!==3)throw Error('Wrong rows '+id);views++;
}
let links=0;for(const file of ['dashboard.html','report.html'])for(const m of fs.readFileSync(path.join(out,file),'utf8').matchAll(/(?:href|src)="([^"]+)"/g)){
 const url=m[1];if(/^(http|data:|#)/.test(url))continue;if(!fs.existsSync(path.resolve(out,url)))throw Error('Broken '+url);links++;
}
const result={matched_forecast_views:views,losses_verified_against_CSV:true,finite_values:true,local_links_verified:links};fs.writeFileSync(path.join(out,'dashboard_validation.json'),JSON.stringify(result,null,2));console.log(result);
