// Exercise the generated local dashboard without a browser or external dependencies.
const fs=require('fs'),vm=require('vm'),path=require('path');
const root=__dirname, file=path.join(root,'outputs/research/dashboard/index.html');
const html=fs.readFileSync(file,'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element {
 constructor(value=''){this.value=value;this.innerHTML='';this.textContent='';this.children=[];}
 addEventListener(){} appendChild(x){this.children.push(x);}
}
const elements={asset:new Element('btc'),method:new Element('lp'),regime:new Element('full'),shock:new Element('vix_change'),horizon:new Element('0'),chart:new Element(),point:new Element(),interval:new Element(),inference:new Element(),methodNote:new Element(),target:new Element('return'),forecastTable:new Element(),findings:new Element()};
const context=vm.createContext({document:{getElementById:id=>elements[id],createElement:()=>new Element()},console});
vm.runInContext(script,context,{timeout:5000});
let checked=0;
for(const asset of ['btc','eth'])for(const method of ['lp','var'])for(const regime of ['full','pre2020','post2020'])for(const shock of ['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps']){
 Object.assign(elements.asset,{value:asset});Object.assign(elements.method,{value:method});Object.assign(elements.regime,{value:regime});Object.assign(elements.shock,{value:shock});
 vm.runInContext('refresh()',context);
 for(const horizon of [0,1,5,10,20,30]){
  elements.horizon.value=String(horizon);vm.runInContext('draw()',context);
  if(/NaN|undefined|Infinity/.test(elements.chart.innerHTML+elements.point.textContent+elements.interval.textContent))throw Error('Invalid chart: '+[asset,method,regime,shock,horizon]);
  if(!elements.chart.innerHTML.includes('<polygon'))throw Error('Missing confidence interval');checked++;
 }
}
for(const target of ['return','squared_return']){
 elements.target.value=target;vm.runInContext('forecasts()',context);
 if((elements.forecastTable.innerHTML.match(/<tr>/g)||[]).length!==5)throw Error('Forecast comparison must contain 4 model/asset rows');
}
if(elements.findings.children.length<5)throw Error('Missing findings');
for(const relative of [...html.matchAll(/href="([^"]+)"/g)].map(x=>x[1])){
 if(!relative.startsWith('http')&&!fs.existsSync(path.resolve(path.dirname(file),relative)))throw Error('Missing dashboard link '+relative);
}
const report={dashboard_combinations_checked:checked,forecast_targets_checked:2,findings_count:elements.findings.children.length,links_exist:true,validation:'JavaScript logic and file links; not a real-browser render test',browser_preview:'CUA initialization failed: missing kernel asset path'};
fs.writeFileSync(path.join(root,'outputs/research/dashboard_validation.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
