const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const db=path.join(root,'data/mock_jlpt_n2_5_sessions/learning_logs.sqlite3');
const url=process.env.BKT_LEARNING_TEST_URL || 'http://127.0.0.1:8056';
const output=process.env.BKT_LEARNING_TEST_DIR || '/tmp/bkt_learning_dashboard';
async function choose(page,id,name){await page.locator('#'+id).click();await page.getByRole('option',{name,exact:true}).click();}
async function tableRows(page,id,column,count){await page.waitForFunction(({id,column,count})=>document.querySelectorAll(`#${id} td[data-dash-column="${column}"]`).length===count,{id,column,count});}
async function downloadText(page,id){const pending=page.waitForEvent('download');await page.locator('#'+id).click();const file=await pending;const stream=await file.createReadStream(),chunks=[];for await(const part of stream)chunks.push(part);return Buffer.concat(chunks).toString('utf8');}
(async()=>{
 const hash=()=>crypto.createHash('sha256').update(fs.readFileSync(db)).digest('hex');const before=hash();
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  fs.mkdirSync(output,{recursive:true});
  const page=await browser.newPage({viewport:{width:1536,height:1100}});page.setDefaultTimeout(15000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
  await page.goto(url);await tableRows(page,'learning-skill-table','SkillName',9);await tableRows(page,'learning-history','Date',5);
  const initial=await page.locator('.learning-kpi strong').allTextContents();
  assert.deepEqual(initial,['54.0%','1.94 / 3','34.3%','37.18秒','5回']);
  const history=await downloadText(page,'learning-export-history');assert.equal(history.trim().split('\n').length,6);
  const all=await downloadText(page,'learning-export-details');assert.equal(all.trim().split('\n').length,151);
  assert.ok(!all.split('\n')[0].includes('ScoreRate')&&!all.split('\n')[0].includes('QuestionText'));
  console.log('PASS SQLite initial KPIs, nine categories, five sessions, 150-answer download and separate observed/self-report/model metrics');
  const bars=page.locator('#learning-category-chart .barlayer .point path');let clicked=false;
  for(let i=0;i<await bars.count();i++){const bar=bars.nth(i),box=await bar.boundingBox();if(box&&box.width>10&&box.height>1){await bar.click({force:true});clicked=true;break;}}
  assert.ok(clicked);await tableRows(page,'learning-skill-table','SkillName',1);
  const filtered=await downloadText(page,'learning-export-details');assert.ok(filtered.trim().split('\n').length<151);
  const model=JSON.parse(await downloadText(page,'learning-export-model'));assert.notEqual(model.filters.skill,'__all__');assert.equal(model.scope,'independent_answers_same_prior');
  await page.locator('#learning-reset').click();await tableRows(page,'learning-skill-table','SkillName',9);
  await page.getByRole('textbox',{name:'Start Date',exact:true}).fill('2026/09/07');
  await page.getByRole('textbox',{name:'Start Date',exact:true}).press('Enter');
  await page.getByRole('textbox',{name:'Start Date',exact:true}).blur();
  await tableRows(page,'learning-history','Date',3);
  assert.equal((await downloadText(page,'learning-export-details')).trim().split('\n').length,91);
  await page.getByRole('radio',{name:'モデル試算',exact:true}).check();
  await page.waitForFunction(()=>document.querySelector('#learning-trend-chart .js-plotly-plot')?.layout?.yaxis?.range?.[1]===1);
  assert.match(await page.locator('#learning-trend-note').textContent(),/独立回答/);
  console.log('PASS real bar click filters all panels/exports, reset, date range to 90 answers and model trend without invented confidence band');
  await choose(page,'learning-source','CSV（同内容の控え）');
  await page.waitForFunction(()=>document.querySelector('#learning-load-status')?.textContent.startsWith('CSV'));
  await tableRows(page,'learning-history','Date',5);assert.deepEqual(await page.locator('.learning-kpi strong').allTextContents(),initial);
  assert.equal((await downloadText(page,'learning-export-skills')).trim().split('\n').length,10);
  await choose(page,'learning-source','SQLite（標準）');
  await page.waitForFunction(()=>document.querySelector('#learning-load-status')?.textContent.startsWith('SQLite'));
  await page.getByRole('radio',{name:'自己申告の理解度',exact:true}).check();
  await page.waitForFunction(()=>document.querySelector('#learning-trend-chart .js-plotly-plot')?.layout?.yaxis?.range?.[1]===3);
  await page.locator('h1').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
  await page.locator('#details summary').click();
  await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
  await page.locator('#learning-history').evaluate(e=>{e.scrollLeft=e.scrollWidth;});
  await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);assert.equal(hash(),before);
  console.log('PASS SQLite/CSV source parity, all summary exports, responsive desktop/mobile with scrollable tables, no JS/HTTP errors and unchanged SQLite hash');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
