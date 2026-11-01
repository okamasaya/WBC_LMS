// sample_dsbd_iris.py をポート8052で起動して実行する。
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium', headless:true,args:['--no-sandbox']});
 try {
  const page = await browser.newPage();
  const errors=[]; page.on('pageerror', e=>errors.push(e.message));
  await page.goto(process.env.IRIS_TEST_URL || 'http://127.0.0.1:8052');
  await page.waitForFunction(()=>document.querySelector('#kpi-count')?.textContent==='150');
  await page.locator('#iris-x').click();
  await page.getByRole('option',{name:'petal_length',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#kpi-mean')?.textContent==='3.76');
  await page.waitForFunction(()=>document.querySelector('#iris-scatter .xtitle')?.textContent==='petal_length (cm)');
  await page.locator('#species-dropdown').click();
  await page.getByRole('option',{name:'Setosa',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#kpi-count')?.textContent==='50');
  const pending=page.waitForEvent('download');
  await page.locator('#iris-export').click();
  const download=await pending;
  assert.equal(download.suggestedFilename(),'iris_filtered.csv');
  const stream=await download.createReadStream();const chunks=[];
  for await(const chunk of stream) chunks.push(chunk);
  const csv=Buffer.concat(chunks).toString('utf8');
  assert.equal(csv.trim().split('\n').length,51);
  assert.ok(!csv.includes('versicolor'));
  await page.locator('#reset-iris').click();
  await page.waitForFunction(()=>document.querySelector('#kpi-count')?.textContent==='150');
  assert.deepEqual(errors,[]);
  console.log('PASS sample: axis/KPI callback, species selection, filtered 50-row CSV and reset');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
