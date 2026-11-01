const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.BIKE_TEST_URL || 'http://127.0.0.1:8053';
async function ready(page){await page.waitForFunction(()=>document.querySelector('#bike-kpi')?.textContent.includes('抽出 366行'));await page.waitForLoadState('networkidle');await page.locator('#bike-kpi').waitFor({state:'visible'});}
function callback(page,id){return page.waitForResponse(r=>r.url().includes('_dash-update-component')&&r.request().postDataJSON()?.changedPropIds?.includes(id));}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(15000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400) errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
  await page.addInitScript(()=>{window.print=()=>{window.__printCalled=true;};});
  await page.goto(base);await ready(page);
  const handle=page.locator('#bike-series .rangeslider-grabber-min');
  await handle.scrollIntoViewIfNeeded();const hb=await handle.boundingBox();
  await page.mouse.move(hb.x+hb.width/2,hb.y+hb.height/2);await page.mouse.down();
  await page.mouse.move(hb.x+hb.width/2+200,hb.y+hb.height/2,{steps:20});await page.mouse.up();
  await page.waitForFunction(()=>Date.parse(document.querySelector('#bike-series .js-plotly-plot')?.layout.xaxis.range[0])>Date.parse('2012-02-01'));
  assert.match(await page.locator('#bike-kpi').textContent(),/抽出 366行/);
  await page.locator('#bike-apply').click();
  await page.waitForFunction(()=>{const t=document.querySelector('#bike-kpi')?.textContent||'';return t.includes('抽出')&&!t.includes('抽出 366行');});
  await page.locator('#bike-back').click();await ready(page);
  console.log('PASS actual range-slider drag, viewport-only zoom, apply-to-all and back');
  await page.locator('#bike-backend').click();await page.getByRole('option',{name:'SQLite（ローカルDB）',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#bike-refresh-status')?.textContent.startsWith('SQLITE'));
  await ready(page);assert.match(await page.locator('#bike-kpi').innerText(),/2,049,576/);
  const hitBefore=Number((await page.locator('#bike-processing').textContent()).match(/hit=(\d+)/)[1]);
  const reload=callback(page,'bike-refresh.n_clicks');await page.locator('#bike-refresh').click();
  const response=await (await reload).json();assert.equal(response.response['bike-data'].data.backend,'sqlite');
  await page.waitForFunction(n=>Number(document.querySelector('#bike-processing')?.textContent.match(/hit=(\d+)/)?.[1])>n,hitBefore);
  console.log('PASS CSV/SQLite switch, actual SQL-backed KPI and manual refresh reuses cached aggregation');
  assert.equal(await page.locator('#bike-table td[data-dash-column="instant"]').count(),15);
  const first=Number(await page.locator('#bike-table td[data-dash-column="instant"]').first().innerText());
  await page.locator('#bike-table .next-page').click();
  await page.waitForFunction(n=>Number(document.querySelector('#bike-table td[data-dash-column="instant"]')?.textContent)===n,first+15);
  await page.locator('#bike-table .first-page').click();
  await page.waitForFunction(n=>Number(document.querySelector('#bike-table td[data-dash-column="instant"]')?.textContent)===n,first);
  await page.locator('#bike-table th[data-dash-column="cnt"] .column-header--sort').click();
  const min=Math.min(...fs.readFileSync('sandbox/dashboard/data/bike/day.csv','utf8').trim().split('\n').slice(1).map(line=>line.trim().split(',')).filter(row=>row[1].startsWith('2012')).map(row=>Number(row.at(-1))));
  await page.waitForFunction(n=>Number(document.querySelector('#bike-table td[data-dash-column="cnt"]')?.textContent)===n,min);
  console.log('PASS server-side next/first page and global numeric sorting with only 15 rendered rows');
  const tick=callback(page,'bike-refresh-clock.n_intervals');
  await page.getByText('60秒ごとに再読込',{exact:true}).click();
  // 実テストではIntervalだけ1秒へ短縮。実際のタイマー発火とHTTP応答を確認。
  await page.evaluate(()=>window.dash_clientside.set_props('bike-refresh-clock',{interval:1000}));
  const tickResponse=await (await tick).json();assert.equal(tickResponse.response['bike-data'].data.backend,'sqlite');
  await page.getByText('60秒ごとに再読込',{exact:true}).click();await ready(page);
  console.log('PASS automatic timer performs a real refresh (test interval shortened to 1s)');
  const imagePromise=page.waitForEvent('download');
  await page.locator('#bike-series .modebar [data-title="Download plot as a PNG"]').click();
  const image=await imagePromise;assert.equal(image.suggestedFilename(),'bike-series.png');
  const stream=await image.createReadStream(), chunks=[];for await(const chunk of stream)chunks.push(chunk);
  const png=Buffer.concat(chunks);assert.deepEqual([...png.subarray(0,8)],[137,80,78,71,13,10,26,10]);
  fs.writeFileSync('/tmp/bike_operations_series.png',png);
  await page.locator('#bike-print').click();await page.waitForFunction(()=>window.__printCalled===true);
  const pdf=await page.pdf({format:'A4',printBackground:true,path:'/tmp/bike_operations.pdf'});
  assert.equal(pdf.subarray(0,4).toString(),'%PDF');
  console.log('PASS PNG download, print-button wiring and Chromium PDF generation');
  assert.deepEqual(errors,[]);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
