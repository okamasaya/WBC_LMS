// 実際の現行ページを操作して、確定後の3種CSVとレポートを保存する。
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const root=process.env.CBT_TEST_BASE_URL || 'http://127.0.0.1:8000';
const output=process.env.PROTOTYPE_CSV_TEST_DIR || '/tmp/prototype_csv_audit';
async function save(page,kind){
 const folder=path.join(output,kind);fs.mkdirSync(folder,{recursive:true});
 const report=await page.locator('#report-text').inputValue();fs.writeFileSync(path.join(folder,'AI_Report.txt'),report);
 const manifest={mode:kind,is_synthetic:true,files:{},report:'AI_Report.txt'};
 for(const type of ['session','questions','raw']){
  const pending=page.waitForEvent('download');await page.locator(`[data-action=${type}]`).click();const download=await pending;
  await download.saveAs(path.join(folder,download.suggestedFilename()));manifest.files[type]=download.suggestedFilename();
 }
 fs.writeFileSync(path.join(folder,'manifest.json'),JSON.stringify(manifest,null,2));
}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.goto(root+'/prototype/language/JLPT_N2/Actual_N2_261030.html');
  await page.locator('#start').click();
  await page.locator('input[name=answer]').nth(0).check();await page.locator('input[name=confidence]').nth(1).check();
  await page.locator('#next').click();await page.locator('input[name=answer]').nth(1).check();await page.locator('input[name=confidence]').nth(3).check();
  await page.locator('#finish').click();await page.locator('#confirm-finish').click();
  await page.locator('#comp-btn-0-0').click();await page.locator('#comp-btn-1-3').click();await page.locator('.review-flag-cb').first().check();
  await page.locator('#generate-report').click();await page.locator('#output-section').waitFor({state:'visible'});
  assert.equal(await page.locator('.review-item').count(),30);await save(page,'Actual');
  console.log('PASS current Actual: answer/confidence, explanation understanding 0/3, review flag, finalized report and three real CSV downloads');
  await page.goto(root+'/prototype/language/JLPT_N2/Drill_N2_261031.html');
  await page.waitForFunction(()=>!document.querySelector('#start-exam').disabled);await page.locator('#start-exam').click();
  await page.locator('.option-btn').first().click();await page.locator('.conf-btn').nth(1).click();
  await page.getByRole('button',{name:'次の問題へ',exact:true}).click();await page.locator('.option-btn').nth(1).click();await page.locator('.conf-btn').nth(3).click();
  await page.getByRole('button',{name:'演習を終了して採点',exact:true}).click();
  await page.locator('#comp-btn-0-0').click();await page.locator('#comp-btn-1-3').click();await page.locator('#generate-report').click();
  await page.locator('#output-section').waitFor({state:'visible'});assert.equal(await page.locator('.review-item').count(),10);await save(page,'Drill');
  assert.deepEqual(errors,[]);
  console.log('PASS current JSON Drill: finalized report and three real CSV downloads with no JS errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
