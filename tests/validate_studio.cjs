/* Exercise the new comparison renderer against the frozen scientific payload. */
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'dashboard/index.html'),'utf8');
const DATA=JSON.parse(source.match(/const DATA=(.*?);\s*const HISTORICAL=/s)[1]);
const context=vm.createContext({DATA,URLSearchParams,chart:()=>{}});
vm.runInContext(fs.readFileSync(path.join(root,'dashboard/design.js'),'utf8'),context);
const run=(code)=>vm.runInContext(code,context);
assert.strictEqual(run("orbitParseRoute('#forecast?asset=eth&shock=monetary&regime=stress&h=30&compare=0').horizon"),'30');
assert.strictEqual(run("orbitParseRoute('#joint').view"),'advanced');
assert.strictEqual(run("orbitParseRoute('#<script>?asset=x&shock=x&regime=x&h=Infinity').view"),'transmission');
assert.strictEqual(run("orbitParseRoute('#transmission?h=1.5').horizon"),'1');
assert.strictEqual(run("orbitParseRoute('#transmission?h=31').horizon"),'1');
assert.strictEqual(run("orbitParseRoute('#forecast?compare=0').compare"),false);
let checked=0;
for(const asset of ['btc','eth'])for(const shock of ['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps','monetary'])for(const regime of ['full','calm','stress']){
 const rows=run(`orbitCurveRows('${asset}','${shock}','${regime}')`);
 const other=run(`orbitCurveRows('${asset==='btc'?'eth':'btc'}','${shock}','${regime}')`);
 assert.strictEqual(rows.length,30);assert.strictEqual(other.length,30);
 context.selected=rows;context.other=other;
 const before=JSON.stringify(rows);
 for(const size of [{width:720,height:330},{width:360,height:300}]){
  context.size=size;const scene=run('orbitResponseScene(selected,other,[],size)'),g=scene.geometry;
  const invert=y=>scene.min+(g.bottom-y)/(g.bottom-g.top)*(scene.max-scene.min);
  rows.forEach((row,i)=>{
   assert(Math.abs(invert(scene.selected[i][1])-row.beta_pct)<1e-11);
   assert(Math.abs(invert(scene.lower[i][1])-row.lower95)<1e-11);
   assert(Math.abs(invert(scene.upper[i][1])-row.upper95)<1e-11);
   assert(Math.abs(invert(scene.other[i][1])-other[i].beta_pct)<1e-11);
   assert.strictEqual(scene.selected[i][0],g.left+i/29*(g.right-g.left));
   checked++;
  });
  assert(scene.zero>=g.top&&scene.zero<=g.bottom);
  assert.strictEqual(run('orbitLine(orbitResponseScene(selected,other,[],size).selected)').match(/ C/g).length,29);
 }
 assert.strictEqual(JSON.stringify(rows),before,'Renderer mutated estimates');
}
assert.strictEqual(run('orbitLine([])'),'');
assert.strictEqual(run('orbitLine([[0,1],[1,2]])'),'M0.00,1.00 L1.00,2.00');
// Render an actual unbounded FOMC row, rather than interpreting null as zero.
const LATEST=JSON.parse(source.match(/const LATEST=(.*?);\s*const el=/s)[1]);
const missingLower=LATEST.fomc.find(r=>r.lower_per10bps===null&&r.unbounded);
const elements={eAsset:{value:missingLower.asset},eOutcome:{value:missingLower.outcome},fomcTable:{},regimeTable:{}};
context.LATEST=LATEST;context.el=id=>elements[id];context.table=(headers,rows)=>JSON.stringify(rows);context.prob=x=>String(x);context.latestNumber=x=>String(x);
const release=fs.readFileSync(path.join(root,'dashboard/release_functions.js'),'utf8');
vm.runInContext(release.slice(release.indexOf('function renderFOMC()'),release.indexOf('function renderRV()')),context);
run('renderFOMC()');
assert(JSON.parse(elements.fomcTable.innerHTML).some(row=>row[1]==='−∞'),'Unbounded lower limit lost its sign');
console.log(JSON.stringify({comparison_and_CI_points_checked:checked,desktop_mobile_projection:true,route_allowlist:true,payload_unmodified:true,unbounded_FOMC_direction:true},null,2));
