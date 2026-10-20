const fs=require('fs'),path=require('path'),vm=require('vm');
const out=path.join(__dirname,'outputs/research/completion');
const source=fs.readFileSync(path.join(out,'dashboard.html'),'utf8');
const code=source.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element{constructor(value=''){this.value=value;this.innerHTML='';this.textContent='';this.children=[];}addEventListener(){}appendChild(x){this.children.push(x);}}
const defaults={asset:'btc',regime:'full',shock:'vix_change',horizon:'0',interactionType:'post2020',interactionH:'0',eventAsset:'BTC',eventTerm:'STMT_10bps',rollingAsset:'btc',rollingShock:'vix_change',rollingEnd:'',target:'return',forecastModel:'elastic_net',forecastComparison:'0',analogueAsset:'btc',analogueShock:'vix_change',analogueState:'calm',analogueH:'0'};
const elements={};for(const m of source.matchAll(/id="([^"]+)"/g)){if(elements[m[1]])throw Error('Duplicate id '+m[1]);elements[m[1]]=new Element(defaults[m[1]]||'');}
const context=vm.createContext({document:{getElementById:id=>{if(!elements[id])throw Error('Missing element '+id);return elements[id]},createElement:()=>new Element()},console});
vm.runInContext(code,context,{timeout:5000});
const run=s=>vm.runInContext(s,context,{timeout:5000});
function valid(...ids){for(const id of ids)if(/NaN|undefined|Infinity/.test(elements[id].innerHTML+elements[id].textContent))throw Error('Invalid view '+id);}
const shocks=['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps'];let lp=0,rolling=0,analogues=0,forecasts=0,events=0;
for(const a of ['btc','eth'])for(const g of ['full','pre2020','post2020','calm','stress'])for(const s of shocks){
 elements.asset.value=a;elements.regime.value=g;elements.shock.value=s;run('refreshLP()');
 const state=['calm','stress'].includes(g),hs=state?[0,1,5,10,20]:[0,1,2,5,10,20,30];
 for(const h of hs){elements.horizon.value=String(h);run('drawLP()');valid('lpChart','lpPoint','lpCI','lpInference','lpSample');const r=run(`DATA.${state?'states':'lp'}.find(r=>r.asset==='${a}'&&r.regime==='${g}'&&r.shock==='${s}'&&r.horizon_sessions===${h})`);if(elements.lpPoint.textContent!==Number(r.beta_pct).toFixed(3)+'%')throw Error('Wrong state/LP beta');if(!elements.lpChart.innerHTML.includes('<polygon'))throw Error('Missing interval');lp++;}
}
for(const a of ['btc','eth'])for(const s of shocks){elements.rollingAsset.value=a;elements.rollingShock.value=s;run('refreshRolling()');for(const r of run(`DATA.rolling.filter(r=>r.asset==='${a}'&&r.shock==='${s}')`)){elements.rollingEnd.value=r.date_utc;run('drawRolling()');valid('rollingChart','rollingPoint','rollingCI');rolling++;}}
for(const a of ['btc','eth'])for(const s of shocks)for(const state of ['calm','stress'])for(const h of [0,1,5,10,20]){elements.analogueAsset.value=a;elements.analogueShock.value=s;elements.analogueState.value=state;elements.analogueH.value=String(h);run('renderAnalogues()');valid('analogueTable');if((elements.analogueTable.innerHTML.match(/<tr>/g)||[]).length!==6)throw Error('Need 5 historical examples');analogues++;}
for(const target of ['return','squared_return'])for(const model of ['elastic_net','gradient_boosting'])for(const pair of ['0','1','2','3']){elements.target.value=target;elements.forecastModel.value=model;elements.forecastComparison.value=pair;run('renderForecasts()');valid('forecastTable','selectedTable','forecastNote');if((elements.forecastTable.innerHTML.match(/<tr>/g)||[]).length!==3)throw Error('Need 2 asset comparisons');if((elements.selectedTable.innerHTML.match(/<tr>/g)||[]).length!==11)throw Error('Need 10 validation winners');forecasts++;}
for(const asset of ['BTC','ETH'])for(const term of ['MP1_10bps','MP2_10bps','STMT_10bps']){elements.eventAsset.value=asset;elements.eventTerm.value=term;run('renderEvents()');valid('eventChart','eventTable');events++;}
for(const name of ['dashboard.html','report.html'])for(const m of fs.readFileSync(path.join(out,name),'utf8').matchAll(/(?:href|src)="([^"]+)"/g)){const link=m[1];if(link.startsWith('http')||link.startsWith('#')||link.startsWith('data:'))continue;if(!fs.existsSync(path.resolve(out,link)))throw Error('Missing '+link+' in '+name);}
if(source.includes('fetch(')||source.includes('<script src=')||source.includes('__PAYLOAD__'))throw Error('Dashboard must be offline');
const result={LP_and_state_selections:lp,rolling_windows:rolling,historical_example_views:analogues,historical_example_rows:analogues*5,forecast_combinations:forecasts,FOMC_views:events,all_finite:true,local_links_verified:true,offline:true};
fs.writeFileSync(path.join(out,'dashboard_validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
