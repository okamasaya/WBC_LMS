const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.env.BIKE_TEST_URL || 'http://127.0.0.1:8053';
async function hasCount(page,n) {
 try {await page.waitForFunction(value=>document.querySelector('#bike-kpi')?.textContent.includes(`抽出 ${value}行`),n.toLocaleString('en-US'));}
 catch(e) {throw new Error(`Expected ${n} rows; actual: ${await page.locator('#bike-kpi').innerText()}; navigation: ${await page.locator('#bike-navigation').innerText()}`);}
}
async function choose(page,id,name) {await page.locator('#'+id).click();await page.getByRole('option',{name,exact:true}).click();}
async function clickPoint(page) {
 await page.waitForLoadState('networkidle');
 const point=page.locator('#bike-series .cartesianlayer .scatterlayer path.point').first();
 await point.scrollIntoViewIfNeeded();
 await page.mouse.move(5,5);
 await page.locator('#bike-series .hoverlayer .hovertext').waitFor({state:'hidden'});
 const b=await point.boundingBox();
 await page.mouse.move(b.x+b.width/2,b.y+b.height/2);
 // Plotlyはhoverでクリック対象の点を確定する。対象が確定してから押す。
 await page.locator('#bike-series .hoverlayer .hovertext').waitFor({state:'visible'});
 await page.mouse.down();await page.mouse.up();
}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(15000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
  await page.goto(base);await hasCount(page,366);
  assert.match(await page.locator('#bike-kpi').innerText(),/2,049,576/);
  assert.equal(await page.locator('#bike-series .cartesianlayer .scatterlayer path.point').count(),12);
  const plot=page.locator('#bike-series .nsewdrag').first();await plot.scrollIntoViewIfNeeded();const box=await plot.boundingBox();
  await page.mouse.move(box.x+box.width*.15,box.y+box.height*.15);await page.mouse.down();await page.mouse.move(box.x+box.width*.45,box.y+box.height*.85,{steps:20});await page.mouse.up();
  await page.waitForFunction(()=>!!document.querySelector('#bike-series .js-plotly-plot')?.layout.xaxis.range);
  await hasCount(page,366);
  console.log('PASS actual mouse zoom changes viewport without filtering KPI');
  await page.locator('#bike-apply').click();
  await page.waitForFunction(()=>{const t=document.querySelector('#bike-kpi')?.textContent||'';return t.includes('抽出')&&!t.includes('抽出 366行');});
  const count=Number((await page.locator('#bike-kpi').innerText()).match(/抽出 ([\d,]+)行/)[1].replaceAll(',',''));
  assert.ok(count>1 && count<366);
  const pending=page.waitForEvent('download');await page.locator('#bike-export').click();const file=await pending;
  const stream=await file.createReadStream(),chunks=[];for await(const chunk of stream)chunks.push(chunk);
  const csv=Buffer.concat(chunks).toString('utf8');assert.equal(csv.trim().split('\n').length,count+1);
  await page.locator('#bike-back').click();await hasCount(page,366);
  console.log('PASS apply zoom filters KPI/details/CSV consistently; back restores full period');
  await page.locator('#bike-reset').click();await hasCount(page,366);
  await page.waitForFunction(()=>document.querySelector('#bike-navigation')?.textContent.includes('初期表示'));
  await page.waitForFunction(()=>{const g=document.querySelector('#bike-series .js-plotly-plot');return g&&!g.classList.contains('dash-graph--pending')&&g.data[0].x.length===12&&g.data[0].x[0].startsWith('2012-01-01');});
  await clickPoint(page);await hasCount(page,31);
  await page.waitForFunction(()=>document.querySelector('#bike-level')?.textContent.includes('日別'));
  await clickPoint(page);await hasCount(page,24);
  await page.waitForFunction(()=>document.querySelector('#bike-level')?.textContent.includes('時間別'));
  assert.match(await page.locator('#bike-table').innerText(),/hr/);
  await page.locator('#bike-back').click();await hasCount(page,31);
  await page.locator('#bike-back').click();await hasCount(page,366);
  console.log('PASS real monthly point -> daily -> hourly drill, source switch and two-level back');
  await choose(page,'bike-level','週別（月曜始まり）');await hasCount(page,366);
  await page.waitForFunction(()=>document.querySelector('#bike-series .gtitle')?.textContent.includes('週別'));
  await choose(page,'bike-statistic','観測1行あたりの平均');
  await page.waitForFunction(()=>document.querySelector('#bike-series .gtitle')?.textContent.includes('観測行平均'));
  await choose(page,'bike-metric','登録利用');
  await page.waitForFunction(()=>document.querySelector('#bike-series .gtitle')?.textContent.includes('登録利用'));
  assert.equal(await page.locator('#bike-comparison .legendtext').count(),2);
  assert.equal(await page.locator('#bike-moving .legendtext').count(),2);
  console.log('PASS weekly grouping, observed-row mean, metric switch, comparison and rolling chart');
  // フィルター変更が全表示に伝わり、0行からリセットで復帰できる。
  await page.locator('#bike-weather [aria-label="Clear selection"]').click();
  await hasCount(page,0);
  await page.waitForFunction(()=>document.querySelector('#bike-series')?.textContent.includes('条件に合うデータ'));
  assert.match(await page.locator('#bike-series').innerText(),/条件に合うデータ/);
  await page.locator('#bike-reset').click();await hasCount(page,366);
  await page.waitForLoadState('networkidle');
  const resetPlot=page.locator('#bike-series .nsewdrag').first();await resetPlot.scrollIntoViewIfNeeded();
  const rb=await resetPlot.boundingBox();
  await page.mouse.move(rb.x+rb.width*.2,rb.y+rb.height*.2);await page.mouse.down();
  await page.mouse.move(rb.x+rb.width*.4,rb.y+rb.height*.8,{steps:15});await page.mouse.up();
  await page.waitForFunction(()=>{const r=document.querySelector('#bike-series .js-plotly-plot')?.layout.xaxis.range;return r&&(Date.parse(r[1])-Date.parse(r[0]))/86400000<150;});
  await page.locator('#bike-reset').click();await hasCount(page,366);
  await page.waitForFunction(()=>{const r=document.querySelector('#bike-series .js-plotly-plot')?.layout.xaxis.range;return r&&(Date.parse(r[1])-Date.parse(r[0]))/86400000>300;});
  console.log('PASS reset restores viewport even when filter values are unchanged');
  await page.setViewportSize({width:390,height:844});
  await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
  assert.deepEqual(errors,[]);
  console.log('PASS empty-filter recovery, mobile width and no JS/HTTP errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
