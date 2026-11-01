const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const url=process.env.BKT_FLAT_TEST_URL || 'http://127.0.0.1:8055';
async function choose(page,id,name){await page.locator('#'+id).click();await page.getByRole('option',{name,exact:true}).click();}
async function summary(page,text){await page.waitForFunction(value=>document.querySelector('#flat-summary')?.textContent.includes(value),text);}
async function value(page,index,text){await page.waitForFunction(({index,text})=>document.querySelectorAll('#flat-single strong')[index]?.textContent===text,{index,text});}
async function downloadedText(download){const stream=await download.createReadStream(),parts=[];for await(const part of stream)parts.push(part);return Buffer.concat(parts).toString('utf8');}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(15000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
  await page.goto(url);await summary(page,'表示対象 32行');
  await value(page,1,'0.4737');await value(page,2,'0.5263');
  await choose(page,'flat-confidence','自信がある');await value(page,1,'0.6307');await value(page,2,'0.6676');
  await choose(page,'flat-understanding','全然分からない');await value(page,1,'0.6307');await value(page,2,'0.6399');
  await page.locator('#flat-confidence [aria-label="Clear selection"]').click();await value(page,1,'0.4737');
  await page.locator('#flat-understanding [aria-label="Clear selection"]').click();await value(page,2,'0.5263');
  console.log('PASS confidence direction, explanation-only learning transition and neutral missing auxiliaries');
  const plot=page.locator('#flat-right .nsewdrag').first();await plot.scrollIntoViewIfNeeded();
  const box=await plot.boundingBox();await page.mouse.move(box.x+box.width*.875,box.y+box.height*.125);
  await page.locator('#flat-right .hoverlayer .hovertext').waitFor({state:'visible'});
  await page.mouse.down();await page.mouse.up();
  await page.waitForFunction(()=>document.querySelector('#flat-confidence')?.textContent.includes('直感に近い'));
  await page.waitForFunction(()=>document.querySelector('#flat-understanding')?.textContent.includes('理解できた'));
  await value(page,1,'0.3217');
  console.log('PASS actual 32-pattern heatmap click updates all three interactive inputs');
  await choose(page,'flat-filter','不正解');await summary(page,'表示対象 16行');
  let pending=page.waitForEvent('download');await page.locator('#flat-export').click();let file=await pending;
  assert.equal(file.suggestedFilename(),'bkt_assisted_flat_results.csv');
  const csv=await downloadedText(file);const lines=csv.trim().split('\n');assert.equal(lines.length,17);
  assert.ok(lines[0].includes('AssistedAfterLearning')&&lines[0].includes('ConfidenceLevel'));
  const correctIndex=lines[0].replace(/^\uFEFF/,'').split(',').indexOf('IsCorrect');assert.ok(lines.slice(1).every(line=>line.split(',')[correctIndex]==='False'));
  pending=page.waitForEvent('download');await page.locator('#flat-export-model').click();file=await pending;
  const metadata=JSON.parse(await downloadedText(file));assert.deepEqual(metadata.assumptions.confidence_weights,[1.5,1,.75,.5]);
  assert.equal(metadata.scope,'independent_answers_same_prior');assert.equal(metadata.parameter_source,'manual_assumption');
  console.log('PASS filtered 16-row CSV and explicit model-assumption JSON download');
  await choose(page,'flat-dataset','既存の架空ログ24回答（各回答は独立に評価）');await summary(page,'表示対象 10行');
  await choose(page,'flat-filter','すべて');await summary(page,'表示対象 24行');
  await page.getByText('仮パラメータと補助項目の扱い',{exact:true}).click();
  await page.locator('#flat-g').fill('0.95');await page.locator('#flat-g').blur();
  await page.waitForFunction(()=>document.querySelector('#flat-status')?.textContent.includes('Guess + Slip'));
  assert.equal(await page.locator('#flat-export').isDisabled(),true);
  assert.equal(await page.locator('#flat-table td').count(),0);
  await page.locator('#flat-g').fill('0.25');await page.locator('#flat-g').blur();await summary(page,'表示対象 24行');
  await page.locator('.flat-heatmaps').screenshot({path:'/tmp/bkt_assisted_flat_patterns.png'});
  await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
  assert.deepEqual(errors,[]);
  console.log('PASS synthetic 24-answer data, invalid-parameter clearing/recovery and mobile layout without JS/HTTP errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
