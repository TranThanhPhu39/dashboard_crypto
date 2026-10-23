/* Cold boot, lazy decoder, failure/retry and accent-insensitive glossary. */
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'dashboard/index.html'),'utf8');
const code=source.match(/<script>([\s\S]*?)<\/script>/)[1];
assert(code.includes('/* ORBIT DESIGN START */'),'Theme/navigation handlers are outside the application script');
class Element{constructor(value=''){this.value=value;this.innerHTML='';this.textContent='';this.hidden=false;this.attrs={};this.listeners={};}addEventListener(k,f){(this.listeners[k]??=new Set()).add(f);}removeEventListener(k,f){this.listeners[k]?.delete(f);}appendChild(){}setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k];}}
const defaults={asset:'btc',shock:'vix_change',regime:'full',horizon:'1',qAsset:'btc',qRegime:'full',qShock:'vix_change',varAsset:'btc',varRegime:'full',varYield:'us2y',varShock:'vix_change',varOrder:'macro_first',target:'squared_return',forecastModel:'elastic_net',forecastPair:'0',iAsset:'btc',iVariant:'common_usd',rollAsset:'btc',rollShock:'vix_change',fAsset:'btc',fScenario:'native_asof_d3',fScope:'pooled',eAsset:'BTC',eOutcome:'intraday',rvAsset:'BTC',rvSampling:'5',rvHorizon:'1'};
const elements={};for(const m of source.matchAll(/id="([^"]+)"/g))elements[m[1]]=new Element(defaults[m[1]]||'');
const ctx=vm.createContext({window:{location:{hash:''}},document:{getElementById:id=>elements[id],createElement:()=>new Element()},console,Promise,Uint8Array,atob,Response,Blob});
const started=performance.now();vm.runInContext(code,ctx);const bootMs=performance.now()-started;
const run=s=>vm.runInContext(s,ctx);
assert.strictEqual(run('HISTORICAL.series'),null);
for(const id of ['forecastTable','historyPredictionChart','fomcTable','quantileChart','varChart'])assert.strictEqual(elements[id].innerHTML,'','Hidden workspace eagerly rendered: '+id);
assert.strictEqual(elements.responsePoint.textContent,'-0.234%');
assert(run("orbitSearchTerms('khoang tin cay').some(t=>t[0]==='ci')"));
assert(run("orbitSearchTerms('OSS').some(t=>t[0]==='oos')"));
assert(!run("orbitSearchTerms('OOS').some(t=>t[0]==='boosting')"));
assert(run("orbitSearchTerms('ĐỘ NHẠY').some(t=>t[0]==='rolling')"));
assert(run("ORBIT_TERMS.every(t=>orbitSearchTerms(t[1].split(' · ')[0]).some(r=>r[0]===t[0]))"),'A contextual help button cannot find its own definition');
assert(run("orbitSearchTerms('Khoảng tin cậy 95%').some(t=>t[0]==='ci')"));
(async()=>{
 await assert.rejects(run('ensureHistoricalOos()'),/Chrome|Edge/);
 assert.strictEqual(run('HISTORICAL.series'),null);
 ctx.DecompressionStream=DecompressionStream;ctx.fetch=fetch;
 await run('ensureHistoricalOos()');
 const original=JSON.parse(fs.readFileSync(path.join(root,'dashboard/historical_oos_data.json')));
 assert.strictEqual(JSON.stringify(run('HISTORICAL.series')),JSON.stringify(original.series));
 assert.strictEqual(JSON.stringify(run('HISTORICAL.folds')),JSON.stringify(original.folds));
 assert.strictEqual(elements.responsePoint.textContent,'-0.234%');
 console.log(JSON.stringify({cold_boot_ms:Number(bootMs.toFixed(1)),hidden_workspaces_deferred:true,decoder_failure_and_retry:true,immutable_predictions:true,glossary_accent_search:true,html_bytes:Buffer.byteLength(source)},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
