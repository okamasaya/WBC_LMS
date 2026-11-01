const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const folder=path.join(__dirname,'../data/mock_jlpt_n2_5_sessions');
const db=path.join(folder,'learning_logs.sqlite3');
const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json'),'utf8'));
const hash=()=>crypto.createHash('sha256').update(fs.readFileSync(db)).digest('hex');
const url=process.env.BKT_FLAT_TEST_URL || 'http://127.0.0.1:8055';
async function summary(page,text){await page.waitForFunction(value=>document.querySelector('#flat-summary')?.textContent.includes(value),text);}
async function choose(page,id,name){await page.locator('#'+id).click();await page.getByRole('option',{name,exact:true}).click();}
(async()=>{
 const before=hash();assert.equal(before,manifest.database_sha256);
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(15000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
  await page.goto(url);await summary(page,'表示対象 32行');
  await choose(page,'flat-dataset','JLPT N2・5回分（SQLite）');await summary(page,'表示対象 150行');
  assert.match(await page.locator('#flat-summary').textContent(),/SQLite.*5回分.*除外 0行/);
  const wrong=150-manifest.summary.correct_count;
  await choose(page,'flat-filter','不正解');await summary(page,`表示対象 ${wrong}行`);
  const pending=page.waitForEvent('download');await page.locator('#flat-export').click();const file=await pending;
  const stream=await file.createReadStream(),parts=[];for await(const part of stream)parts.push(part);
  const csv=Buffer.concat(parts).toString('utf8');assert.equal(csv.trim().split('\n').length,wrong+1);
  assert.ok(csv.includes('AssistedAfterLearning')&&csv.includes('UnderstandingLevel'));
  assert.ok(!csv.includes('ScoreRate')&&!csv.includes('QuestionText')&&!csv.includes('Explanation'));
  await choose(page,'flat-filter','正解');await summary(page,`表示対象 ${manifest.summary.correct_count}行`);
  await choose(page,'flat-filter','すべて');await summary(page,'表示対象 150行');
  await choose(page,'flat-dataset','全32パターン（合成データ）');await summary(page,'表示対象 32行');
  assert.deepEqual(errors,[]);assert.equal(hash(),before);
  assert.ok(!fs.existsSync(db+'-wal')&&!fs.existsSync(db+'-journal'));
  console.log(`PASS SQLite 5-session/150-answer selection, ${wrong} wrong/${manifest.summary.correct_count} correct filters and result CSV, dataset switching, no JS/HTTP errors, unchanged database SHA-256 and no WAL/journal`);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
