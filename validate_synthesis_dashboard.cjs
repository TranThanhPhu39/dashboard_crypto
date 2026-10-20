// Exercise every stored LP/rolling selection without browser dependencies.
const fs=require('fs'),path=require('path'),vm=require('vm');
const out=path.join(__dirname,'outputs/research/synthesis');
const source=fs.readFileSync(path.join(out,'dashboard.html'),'utf8');
const code=source.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element{constructor(value=''){this.value=value;this.innerHTML='';this.textContent='';this.children=[];}addEventListener(){}appendChild(x){this.children.push(x);}}
const defaults={asset:'btc',regime:'full',shock:'vix_change',horizon:'0',interactionType:'post2020',interactionH:'0',eventAsset:'BTC',eventTerm:'STMT_10bps',rollingAsset:'btc',rollingShock:'vix_change',rollingEnd:'',target:'return'};
const elements={};for(const m of source.matchAll(/id="([^"]+)"/g))elements[m[1]]=new Element(defaults[m[1]]||'');
const context=vm.createContext({document:{getElementById:id=>{if(!elements[id])throw Error('Missing element '+id);return elements[id]},createElement:()=>new Element()},console});
vm.runInContext(code,context,{timeout:5000});
function run(s){return vm.runInContext(s,context,{timeout:5000})}
function valid(...ids){for(const id of ids){const text=elements[id].innerHTML+elements[id].textContent;if(/NaN|undefined|Infinity/.test(text))throw Error('Non-finite view '+id);}}
let lpCount=0,rollCount=0,eventCount=0,interactionCount=0;
for(const a of ['btc','eth'])for(const g of ['full','pre2020','post2020'])for(const s of ['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps']){
 elements.asset.value=a;elements.regime.value=g;elements.shock.value=s;run('refreshLP()');
 for(const h of [0,1,2,5,10,20,30]){elements.horizon.value=String(h);run('drawLP()');valid('lpChart','lpPoint','lpCI','lpInference','lpSample');const r=run(`DATA.lp.find(r=>r.asset==='${a}'&&r.regime==='${g}'&&r.shock==='${s}'&&r.horizon_sessions===${h})`);if(elements.lpPoint.textContent!==Number(r.beta_pct).toFixed(3)+'%')throw Error('Wrong LP coefficient');if(!elements.lpChart.innerHTML.includes('<polygon'))throw Error('Missing LP CI');lpCount++;}
}
for(const a of ['btc','eth'])for(const s of ['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps']){
 elements.rollingAsset.value=a;elements.rollingShock.value=s;run('refreshRolling()');
 const rows=run(`DATA.rolling.filter(r=>r.asset==='${a}'&&r.shock==='${s}').sort((a,b)=>a.date_utc.localeCompare(b.date_utc))`);
 for(const r of rows){elements.rollingEnd.value=r.date_utc;run('drawRolling()');valid('rollingChart','rollingPoint','rollingCI','rollingDate');if(elements.rollingPoint.textContent!==Number(r.beta_pct).toFixed(3)+'%')throw Error('Wrong rolling coefficient');rollCount++;}
}
for(const a of ['BTC','ETH'])for(const term of ['MP1_10bps','MP2_10bps','STMT_10bps']){elements.eventAsset.value=a;elements.eventTerm.value=term;run('renderEvents()');valid('eventChart','eventTable','eventScale');if((elements.eventTable.innerHTML.match(/<tr>/g)||[]).length!==3)throw Error('Expected two event windows');eventCount++;}
for(const kind of ['post2020','stress_lag_vix_gt30'])for(const h of [0,1,5,10,20]){elements.interactionType.value=kind;elements.interactionH.value=String(h);run('renderInteractions()');valid('interactionTable');if((elements.interactionTable.innerHTML.match(/<tr>/g)||[]).length!==9)throw Error('Expected eight interaction rows');interactionCount++;}
for(const target of ['return','squared_return']){elements.target.value=target;run('renderForecasts()');valid('forecastTable');if((elements.forecastTable.innerHTML.match(/<tr>/g)||[]).length!==5)throw Error('Expected four forecast comparison rows');}
for(const [id,n] of [['baselineEventTable',6],['selectedTable',12],['varTable',12]])if((elements[id].innerHTML.match(/<tr>/g)||[]).length!==n+1)throw Error('Wrong static table '+id);
if(elements.findings.children.length!==7)throw Error('Missing synthesis findings');
for(const m of source.matchAll(/(?:href|src)="([^"]+)"/g)){const p=m[1];if(p.startsWith('http')||p.startsWith('#')||p.startsWith('data:'))continue;if(!fs.existsSync(path.resolve(out,p)))throw Error('Missing link '+p);}
const result={LP_selections_checked:lpCount,rolling_windows_checked:rollCount,FOMC_views_checked:eventCount,interaction_views_checked:interactionCount,forecast_targets_checked:2,baseline_FOMC_retained:true,VAR_supplementary:true,finite_charts_and_links:true,validation:'JavaScript state and data checks; browser rendering checked separately when available.'};
fs.writeFileSync(path.join(out,'dashboard_validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
