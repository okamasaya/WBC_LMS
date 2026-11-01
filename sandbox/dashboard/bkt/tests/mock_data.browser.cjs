const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const url=process.env.BKT_FLAT_TEST_URL || 'http://127.0.0.1:8055';
async function summary(page,text){await page.waitForFunction(value=>document.querySelector('#flat-summary')?.textContent.includes(value),text);}
async function choose(page,id,name){await page.locator('#'+id).click();await page.getByRole('option',{name,exact:true}).click();}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(15000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
  await page.goto(url);await summary(page,'表示対象 32行');
  await choose(page,'flat-dataset','JLPT N2・20回分のモック');await summary(page,'表示対象 600行');
  assert.match(await page.locator('#flat-summary').textContent(),/除外 0行/);
  await choose(page,'flat-filter','不正解');await summary(page,'表示対象 272行');
  const pending=page.waitForEvent('download');await page.locator('#flat-export').click();const download=await pending;
  const stream=await download.createReadStream(),chunks=[];for await(const chunk of stream)chunks.push(chunk);
  const csv=Buffer.concat(chunks).toString('utf8');assert.equal(csv.trim().split('\n').length,273);
  assert.ok(csv.includes('SessionNumber')&&csv.includes('UnderstandingRecordedAt'));
  await choose(page,'flat-filter','正解');await summary(page,'表示対象 328行');
  await choose(page,'flat-filter','すべて');await summary(page,'表示対象 600行');
  await page.locator('#flat-summary').scrollIntoViewIfNeeded();
  await page.screenshot({path:'/tmp/bkt_mock_600_dashboard.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('PASS CSV-backed 600 mock answers, zero exclusions, 272 wrong/328 correct filters and 272-row CSV export without JS/HTTP errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
