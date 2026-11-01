const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const base = process.env.IRIS_TEST_URL || 'http://127.0.0.1:8052';
async function count(page, value) {
 await page.waitForFunction(n => document.querySelector('#kpi-count')?.textContent === String(n), value);
}
async function point(page) {
 const mark=page.locator('#iris-scatter path.point').first();
 await mark.scrollIntoViewIfNeeded();const b=await mark.boundingBox();
 await page.mouse.click(b.x+b.width/2,b.y+b.height/2);
}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try {
  const a=await browser.newContext(), b=await browser.newContext();
  const pa=await a.newPage(), pb=await b.newPage();
  const errors=[];for(const p of [pa,pb]) {p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=400) errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});}
  await Promise.all([pa.goto(base),pb.goto(base)]);
  await Promise.all([count(pa,150),count(pb,150)]);
  await pa.locator('#iris-x').click();await pa.getByRole('option',{name:'petal_length',exact:true}).click();
  await pa.waitForFunction(()=>document.querySelector('#kpi-mean')?.textContent==='3.76');
  await point(pa);await count(pa,1);
  const query=await pa.locator('#iris-share').getAttribute('href');
  assert.equal(JSON.parse(new URLSearchParams(query).get('view')).filters.scatter.length,1);
  await pa.reload();await count(pa,1);
  await pa.waitForFunction(()=>document.querySelector('#iris-scatter .xtitle')?.textContent==='petal_length (cm)');
  console.log('PASS same-tab reload restores row selection and measurement axis');
  await count(pb,150);
  const hrefB=await pb.locator('#iris-share').getAttribute('href');
  assert.equal(JSON.parse(new URLSearchParams(hrefB).get('view')).x,'sepal_length');
  console.log('PASS two concurrent isolated browser contexts do not share filters or axes');
  await pb.goto(base+query);await count(pb,1);
  await pb.waitForFunction(()=>document.querySelector('#iris-scatter .xtitle')?.textContent==='petal_length (cm)');
  assert.match(await pb.locator('#iris-restore-status').innerText(),/共有URL/);
  await pb.reload();await count(pb,1);
  console.log('PASS shared URL restores selection/axes in another context and after reload');
  await pb.goto(base+'?view=invalid');await count(pb,150);
  await pb.waitForFunction(()=>document.querySelector('#iris-restore-status')?.textContent.includes('適用できません'));
  console.log('PASS malformed URL resets to defaults and explains the error');
  const empty='?'+new URLSearchParams({view:JSON.stringify({version:1,species:'all',x:'sepal_length',y:'sepal_width',filters:{scatter:[]}})});
  await pb.goto(base+empty);await count(pb,0);
  assert.equal(await pb.locator('#kpi-mean').innerText(),'—');
  await pb.locator('#reset-iris').click();await count(pb,150);
  console.log('PASS zero-row URL, empty KPI and recovery by reset');
  assert.deepEqual(errors,[]);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
