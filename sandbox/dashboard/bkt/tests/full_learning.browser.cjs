const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const url=process.env.BKT_FULL_TEST_URL||'http://127.0.0.1:8057';
const output=process.env.BKT_FULL_TEST_DIR||'/tmp/bkt_full_learning';
const db=path.join(__dirname,'../data/mock_jlpt_n2_full_15_sessions/learning_logs.sqlite3');
const digest=()=>crypto.createHash('sha256').update(fs.readFileSync(db)).digest('hex');
async function choose(page,id,name){await page.locator('#'+id).click();await page.getByRole('option',{name,exact:true}).click();}
async function count(page,n){await page.waitForFunction(n=>document.querySelector('#full-selection')?.textContent.includes(n.toLocaleString('en-US')+'回答'),n);}
async function download(page,id){const wait=page.waitForEvent('download');await page.locator('#'+id).click();const file=await wait;return fs.readFileSync(await file.path(),'utf8').replace(/^\uFEFF/,'');}
(async()=>{
 const before=digest();fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1536,height:1100}});page.setDefaultTimeout(20000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
  await page.goto(url);await count(page,1605);
  await page.waitForFunction(()=>document.querySelectorAll('#full-skills td[data-dash-column="SkillName"]').length===19);
  const initial=await page.locator('#full-kpis').innerText();
  const all=await download(page,'full-export-details');assert.equal(all.trim().split('\n').length,1606);
  const history=await download(page,'full-export-sessions');assert.equal(history.trim().split('\n').length,16);
  const domains=await download(page,'full-export-domains');assert.equal(domains.trim().split('\n').length,4);
  assert.ok(all.includes('CategoryLevel1')&&all.includes('ConfidenceLevel')&&all.includes('UnderstandingLevel'));
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  console.log('PASS 15 sessions, 19 skills, 1605 answers, three domains and full-row exports');
  for(const [domain,n] of [['言語知識',810],['読解',315],['聴解',480]]){
   await choose(page,'full-domain',domain);await count(page,n);
   const text=await download(page,'full-export-details');assert.equal(text.trim().split('\n').length,n+1);
  }
  await choose(page,'full-domain','読解');await count(page,315);
  await choose(page,'full-group','内容理解');await count(page,210);
  await choose(page,'full-skill','読解 · 内容理解（中文）');await count(page,135);
  await choose(page,'full-session','第1回');await count(page,9);
  await page.waitForFunction(()=>document.querySelectorAll('#full-answers td[data-dash-column="SkillName"]').length===9);
  const selected=await download(page,'full-export-details');assert.equal(selected.trim().split('\n').length,10);
  assert.ok(selected.includes('内容理解（中文）'));assert.ok(!selected.includes('聴解'));
  const metadata=JSON.parse(await download(page,'full-export-model'));
  assert.equal(metadata.filters.domain,'読解');assert.equal(metadata.filters.group,'内容理解');
  assert.equal(metadata.scope,'independent_answers_same_prior');
  console.log('PASS domain -> group -> skill -> session -> nine answer details and matching CSV/model metadata');
  await choose(page,'full-domain','聴解');await count(page,32); // Child selection resets, session stays.
  await page.locator('#full-reset').click();await count(page,1605);
  const bar=page.locator('#full-domain-chart .barlayer .point path').nth(1);
  await bar.click({force:true});await count(page,315);
  await page.waitForFunction(()=>document.querySelectorAll('#full-skill-chart .barlayer .point path').length===5);
  await page.locator('#full-skill-chart .barlayer .point path').first().click({force:true});
  await count(page,75);
  await page.locator('#full-reset').click();await count(page,1605);
  await choose(page,'full-source','CSV（同内容の控え）');await count(page,1605);
  await page.waitForFunction(()=>document.querySelector('#full-status')?.textContent.includes('CSV 読込済み'));
  assert.equal(await page.locator('#full-kpis').innerText(),initial);
  assert.equal(await download(page,'full-export-details'),all);
  await page.locator('#full-metric').getByText('モデル試算',{exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#full-trend .ytitle')?.textContent==='モデル試算の平均');
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);assert.equal(digest(),before);
  console.log('PASS parent resets, chart drill-down, all-filter reset, SQLite/CSV parity, independent model, mobile and unchanged DB');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
