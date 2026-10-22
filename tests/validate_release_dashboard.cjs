const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'..'),out=path.join(root,'outputs/research/release_20261025');
const source=fs.readFileSync(path.join(root,'dashboard/index.html'),'utf8');
let code=source.match(/<script>([\s\S]*?)<\/script>/)[1];
// Browser loads the identical frozen payload on first opening Forecast.
// Decode it here so every scientific view is still checked synchronously.
const compressed=code.match(/const HISTORY_ARCHIVE_GZIP_B64="([A-Za-z0-9+/=]+)";/);
if(compressed){const text=require('zlib').gunzipSync(Buffer.from(compressed[1],'base64')).toString('utf8');code=code.replace(/const HISTORICAL=.*?;\s*const HISTORY_ARCHIVE_GZIP_B64="[A-Za-z0-9+/=]+";/s,'const HISTORICAL='+text+';');}
class Element{constructor(value=''){this.value=value;this.innerHTML='';this.textContent='';this.children=[];this.attributes={};this.hidden=false;}addEventListener(){}removeEventListener(){}appendChild(x){this.children.push(x);}setAttribute(k,v){this.attributes[k]=String(v);}getAttribute(k){return this.attributes[k];}}
const defaults={asset:'btc',shock:'vix_change',regime:'full',horizon:'1',qAsset:'btc',qRegime:'full',qShock:'vix_change',varAsset:'btc',varRegime:'full',varYield:'us2y',varShock:'vix_change',varOrder:'macro_first',target:'squared_return',forecastModel:'elastic_net',forecastPair:'0',iAsset:'btc',iVariant:'common_usd',rollAsset:'btc',rollShock:'vix_change',fAsset:'btc',fScenario:'native_asof_d3',fScope:'pooled',eAsset:'BTC',eOutcome:'intraday',rvAsset:'BTC',rvSampling:'5',rvHorizon:'1'};
const elements={};for(const m of source.matchAll(/id="([^"]+)"/g)){if(elements[m[1]])throw Error('Duplicate id');elements[m[1]]=new Element(defaults[m[1]]||'');}
const context=vm.createContext({document:{getElementById:id=>{if(!elements[id])throw Error('Missing '+id);return elements[id]},createElement:()=>new Element()},console});vm.runInContext(code,context,{timeout:10000});const run=s=>vm.runInContext(s,context,{timeout:10000});
const historicalSource=JSON.parse(fs.readFileSync(path.join(root,'dashboard/historical_oos_data.json'),'utf8'));
if(JSON.stringify(run('HISTORICAL.series'))!==JSON.stringify(historicalSource.series)||JSON.stringify(run('HISTORICAL.folds'))!==JSON.stringify(historicalSource.folds))throw Error('Embedded historical predictions/timing differ from source');
if(elements.responses.hidden||elements.rolling.hidden||!elements.overview.hidden||!elements.pit.hidden)throw Error('Wrong default workspace');
for(const group of ['transmission','forecast','fomc','advanced','methods','operations']){
 run(`showWorkspace('${group}')`);
 for(const [key,ids] of Object.entries(run('WORKSPACE_GROUPS')))for(const id of ids)if(elements[id].hidden!==(key!==group))throw Error('Incorrect workspace visibility');
 if(elements['tab-'+group].getAttribute('aria-pressed')!=='true')throw Error('Tab accessibility state missing');
}
run("showWorkspace('transmission')");
function valid(...ids){for(const id of ids)if(/NaN|undefined|Infinity/.test(elements[id].textContent+elements[id].innerHTML))throw Error('Invalid '+id);}
const shocks=['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps'];let views=0,quantile=0,irf=0,forecasts=0,importance=0,rolling=0;
for(const a of ['btc','eth'])for(const s of [...shocks,'monetary'])for(const r of ['full','calm','stress'])for(let h=1;h<=30;h++){
 elements.asset.value=a;elements.shock.value=s;elements.regime.value=r;elements.horizon.value=String(h);run('renderResponse()');valid('responseChart','responsePoint','responseCI','responseSample','responseInference','responseTiming','analogueTable','differenceTable');
 const row=run(`DATA.${s==='monetary'?'monetary':'daily'}.find(q=>q.asset==='${a}'&&q.shock==='${s}'&&q.regime==='${r}'&&q.horizon_days===${h})`);if(elements.responsePoint.textContent!==Number(row.beta_pct).toFixed(3)+'%')throw Error('Wrong coefficient');const n=(elements.analogueTable.innerHTML.match(/<tr>/g)||[]).length-1;if(n<1||n>5)throw Error('Bad analogue count '+n);views++;
 const csv=run('responseCsv()'),lines=csv.replace(/^\ufeff/,'').split('\r\n');
 if(lines.length!==31||!lines[0].includes('"lower95"')||!lines[0].includes('"upper95"'))throw Error('CSV curve/CI missing');
 const fields=lines[h].slice(1,-1).split('","');if(fields[0]!==a||fields[1]!==s||fields[2]!==r||Number(fields[3])!==h||Number(fields[4])!==row.beta_pct)throw Error('CSV does not match selected estimate');
}
for(const a of ['btc','eth'])for(const r of ['full','pre2020','post2020'])for(const s of shocks){elements.qAsset.value=a;elements.qRegime.value=r;elements.qShock.value=s;run('renderQuantile()');valid('quantileChart','quantileTable');quantile++;}
for(const a of ['btc','eth'])for(const r of ['full','pre2020','post2020'])for(const y of ['us2y','us10y'])for(const s of ['vix_change','usd_return_pct','yield'])for(const o of ['crypto_first','macro_first','reverse_macro']){elements.varAsset.value=a;elements.varRegime.value=r;elements.varYield.value=y;elements.varShock.value=s;elements.varOrder.value=o;run('renderVAR()');valid('varChart','varDiagnostics');irf++;}
for(const asset of ['btc','eth'])for(const t of ['return','squared_return'])for(const m of ['elastic_net','gradient_boosting'])for(const scenario of ['native_asof_d3','matched_asof_d3','matched_latest_d3','matched_asof_d4'])for(const scope of ['pooled','2023','2024','2025','2026'])for(const pair of ['0','1','2','3']){
 elements.fAsset.value=asset;elements.target.value=t;elements.forecastModel.value=m;elements.forecastPair.value=pair;elements.fScenario.value=scenario;elements.fScope.value=scope;run('resetHistoricalRange();renderForecast()');valid('forecastTable','benchmarkTable','sensitivityTable','forecastContext','historyPredictionChart','historyLossChart','historyPointTable','historyTimingTable','historyContext');
 const pairs=[['long_own','long_macro'],['common_own','common_macro'],['common_macro','common_usd'],['common_own','common_usd']];
 const row=run(`LATEST.ablation.find(q=>q.asset==='${asset}'&&q.target==='${t}'&&q.model==='${m}'&&q.scenario==='${scenario}'&&String(q.scope)==='${scope}'&&q.base==='${pairs[pair][0]}'&&q.added==='${pairs[pair][1]}')`);
 if(!row||!elements.forecastTable.innerHTML.includes(Number(row.mean_loss_new_minus_base).toPrecision(5)))throw Error('Incorrect nested estimate');
 if((elements.forecastTable.innerHTML.match(/<tr>/g)||[]).length!==2)throw Error('Wrong macro row count');
 if((elements.benchmarkTable.innerHTML.match(/<tr>/g)||[]).length!==6)throw Error('Wrong benchmark row count');
 if((elements.sensitivityTable.innerHTML.match(/<tr>/g)||[]).length!==4)throw Error('Wrong sensitivity row count');
 const expected=historicalSource.series[[asset,scenario,pairs[pair][1],t].join('|')].filter(r=>scope==='pooled'||String(r[6])===scope),column=m==='elastic_net'?2:3;
 if(Number(elements.historyCount.textContent)!==expected.length)throw Error('Historical count differs from frozen CSV');
 const loss=r=>t==='return'?(r[1]-r[column])**2:Math.log(r[column])+r[1]/r[column],mean=expected.reduce((v,r)=>v+loss(r),0)/expected.length;
 if(elements.historyAddedLoss.textContent!==mean.toPrecision(5))throw Error('Historical loss differs from predictions');
 const csvRows=run('historicalOosCsv()').replace(/^\ufeff/,'').split('\r\n');
 if(csvRows.length!==expected.length+1)throw Error('Wrong historical CSV coverage');
 const first=csvRows[1].slice(1,-1).split('","');
 if(first[5]!==expected[0][0]+'T00:00:00Z'||Number(first[9])!==expected[0][1]||Number(first[11])!==expected[0][column])throw Error('Historical CSV does not match selected forecasts');
 if(first[0]!== (scenario==='matched_latest_d3'?'historical_ex_post_oracle':'historical_pseudo_oos'))throw Error('Historical/oracle interpretation lost');
 forecasts++;
}
// Deliberately cross an annual refit boundary and check custom dates, not only preset years.
elements.fAsset.value='eth';elements.target.value='return';elements.forecastModel.value='gradient_boosting';elements.forecastPair.value='2';elements.fScenario.value='matched_asof_d3';elements.fScope.value='pooled';
elements.historyStart.value='2024-12-15';elements.historyEnd.value='2025-01-15';run('renderHistoricalOos()');
const custom=run('historicalRows()');if(!custom.length||!custom.every(r=>r.date>='2024-12-15'&&r.date<='2025-01-15')||new Set(custom.map(r=>r.year)).size!==2)throw Error('Custom historical dates/refit boundary broken');
elements.historyDay.value=custom[0].date;run('renderHistoryPoint()');if(!elements.historyModelHashes.textContent.includes('fold 2024'))throw Error('Wrong model for 2024 origin');
elements.historyDay.value=custom[custom.length-1].date;run('renderHistoryPoint()');if(!elements.historyModelHashes.textContent.includes('fold 2025'))throw Error('Wrong model for 2025 origin');
elements.historyStart.value=custom[0].date;elements.historyEnd.value=custom[0].date;run('renderHistoricalOos()');if(elements.historyCount.textContent!=='1'||!/circle/.test(elements.historyPredictionChart.innerHTML))throw Error('Single-day replay missing');
elements.historyStart.value='2026-01-01';elements.historyEnd.value='2025-01-01';run('renderHistoricalOos()');if(!elements.exportHistoricalOos.disabled||elements.historyPredictionChart.innerHTML!=='')throw Error('Inverted historical dates accepted');
elements.historyStart.value='2000-01-01';elements.historyEnd.value='2000-01-02';run('renderHistoricalOos()');if(elements.historyCount.textContent!=='0'||!elements.exportHistoricalOos.disabled)throw Error('Missing dates fabricated forecasts');
run('resetHistoricalRange();renderHistoricalOos()');
for(const a of ['btc','eth'])for(const v of ['long_own','long_macro','common_own','common_macro','common_usd'])for(const t of ['return','squared_return'])for(const m of ['elastic_net','gradient_boosting']){elements.iAsset.value=a;elements.iVariant.value=v;elements.target.value=t;elements.forecastModel.value=m;run('renderImportance()');valid('importanceTable');importance++;}
for(const a of ['btc','eth'])for(const s of shocks){elements.rollAsset.value=a;elements.rollShock.value=s;run('renderRolling()');valid('rollingChart');rolling++;}
let fomc=0,rv=0;
for(const a of ['BTC','ETH'])for(const o of run('[...new Set(LATEST.fomc.map(q=>q.outcome))]')){elements.eAsset.value=a;elements.eOutcome.value=o;run('renderFOMC()');valid('fomcTable','regimeTable');if((elements.fomcTable.innerHTML.match(/<tr>/g)||[]).length!==3)throw Error('FOMC components missing');if((elements.regimeTable.innerHTML.match(/<tr>/g)||[]).length!==5)throw Error('Regime tests missing');fomc++;}
for(const a of ['BTC','ETH'])for(const s of ['5','15'])for(const h of ['1','7']){elements.rvAsset.value=a;elements.rvSampling.value=s;elements.rvHorizon.value=h;run('renderRV()');valid('rvTable','rvBenchmarkTable');if((elements.rvTable.innerHTML.match(/<tr>/g)||[]).length!==5)throw Error('Wrong RV ablations');if((elements.rvBenchmarkTable.innerHTML.match(/<tr>/g)||[]).length!==16)throw Error('Wrong RV benchmarks');rv++;}
valid('pitTable','liveStatus','releaseSummary');
run('resetResponse()');if(elements.asset.value!=='btc'||elements.shock.value!=='vix_change'||elements.regime.value!=='full'||elements.horizon.value!=='1')throw Error('Reset failed');
for(const m of source.matchAll(/(?:href|src)="([^"]+)"/g)){const link=m[1];if(link.startsWith('http')||link.startsWith('#')||link.startsWith('data:'))continue;if(!fs.existsSync(path.resolve(root,'dashboard',link)))throw Error('Broken '+link);}
const result={response_views_1_to_30_days:views,csv_estimates_checked:views,workspace_tabs:6,reset_verified:true,quantile_views:quantile,joint_VAR_views:irf,nested_forecast_views:forecasts,historical_replay_views:forecasts,historical_csv_values_checked:true,custom_date_and_annual_refit_verified:true,single_day_and_empty_range_verified:true,fomc_views:fomc,rv_views:rv,importance_views:importance,rolling_views:rolling,all_finite:true,local_links_verified:true};fs.writeFileSync(path.join(out,'dashboard_validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
