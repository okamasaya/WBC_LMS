const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const url=process.env.BKT_FLAT_TEST_URL || 'http://127.0.0.1:8055';
const fixture=path.join(__dirname,'fixtures/csv_import');
async function summary(page,text){await page.waitForFunction(value=>document.querySelector('#flat-summary')?.textContent.includes(value),text);}
async function downloadText(page,button){const pending=page.waitForEvent('download');await page.locator(button).click();const file=await pending;const stream=await file.createReadStream(),parts=[];for await(const part of stream)parts.push(part);return Buffer.concat(parts).toString('utf8');}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(15000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
  await page.goto(url);await summary(page,'表示対象 32行');
  await page.locator('#flat-upload input[type=file]').setInputFiles(['Session.csv','QuestionResult.csv','CBT_RAW.csv'].map(n=>path.join(fixture,n)));
  await page.waitForFunction(()=>document.querySelector('#flat-selected-files')?.textContent.includes('CBT_RAW.csv'));
  await page.locator('#flat-import').click();await summary(page,'表示対象 2行');
  assert.match(await page.locator('#flat-summary').textContent(),/除外 1行/);
  assert.match(await page.locator('#flat-summary').textContent(),/重複を除去 3行/);
  const csv=await downloadText(page,'#flat-export');assert.equal(csv.trim().split('\n').length,3);
  assert.ok(csv.includes('AssistedAfterLearning')&&csv.includes('UnderstandingLevel'));
  assert.ok(!csv.includes('Explanation')&&!csv.includes('ScoreRate')&&!csv.includes('QuestionText'));
  await page.locator('#flat-filter').click();await page.getByRole('option',{name:'不正解',exact:true}).click();await summary(page,'表示対象 1行');
  assert.equal((await downloadText(page,'#flat-export')).trim().split('\n').length,2);
  await page.locator('#flat-filter').click();await page.getByRole('option',{name:'すべて',exact:true}).click();await summary(page,'表示対象 2行');
  await page.locator('#flat-upload input[type=file]').setInputFiles(path.join(fixture,'Session.csv'));
  await page.locator('#flat-import').click();await summary(page,'表示対象 0行');
  await page.waitForFunction(()=>document.querySelector('#flat-import-status')?.textContent.includes('取り込めません'));
  assert.ok(await page.locator('#flat-export').isDisabled());
  console.log('PASS synthetic answered CSVs: three-file import, deduplication, missing identity, understanding 0, filtered result CSV, and failed-import stale-result clearing');
  if(process.env.BKT_REAL_CSV_FILES){
   const originals=JSON.parse(process.env.BKT_REAL_CSV_FILES);
   await page.locator('#flat-upload input[type=file]').setInputFiles(originals);await page.locator('#flat-import').click();
   await page.waitForFunction(()=>document.querySelector('#flat-import-status')?.textContent.includes('重複を除く 10行'));
   await summary(page,'除外 10行');assert.match(await page.locator('#flat-summary').textContent(),/重複を除去 10行/);
   assert.ok(await page.locator('#flat-export').isDisabled());assert.ok(await page.locator('#flat-export-model').isDisabled());
   const reasons=await downloadText(page,'#flat-export-excluded');assert.equal(reasons.trim().split('\n').length,21);
   assert.ok(reasons.includes('未回答')&&reasons.includes('重複'));
   console.log('PASS attached real three-file exports: 10 unique unanswered rows, 10 duplicate rows, zero inferred answers, disabled estimate downloads, and 20 reason rows');
  }
  await page.locator('#flat-clear-upload').click();
  // 直前も0件の場合があるため、件数だけでなくクリア処理と再描画の完了を待つ。
  await page.waitForFunction(()=>document.querySelector('#flat-import-status')?.textContent.includes('取込データをクリア')&&document.querySelector('#flat-export-excluded')?.disabled);
  await summary(page,'表示対象 0行');
  assert.ok(await page.locator('#flat-export').isDisabled());assert.ok(await page.locator('#flat-export-excluded').isDisabled());
  await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
  assert.deepEqual(errors,[]);
  console.log('PASS clear removes import/results/reasons and mobile layout without JS/HTTP errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
