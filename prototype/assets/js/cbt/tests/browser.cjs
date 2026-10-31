const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const url = `${process.env.CBT_TEST_BASE_URL || 'http://127.0.0.1:8000'}/prototype/language/JLPT_N2/Actual_N2_261030.html`;
const config = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../../../../language/JLPT_N2/conf_JLPT_N2_LK.json')));
// Read RFC-style quoted CSV, including the question/explanation newlines.
function readCsv(text) {
 const rows = []; let row = [], cell = '', quoted = false;
 text = text.replace(/^\uFEFF/, '');
 for (let i = 0; i < text.length; i++) {
  const c = text[i];
  if (c === '"') {
   if (quoted && text[i + 1] === '"') { cell += '"'; i++; }
   else quoted = !quoted;
  } else if (c === ',' && !quoted) { row.push(cell); cell = ''; }
  else if (c === '\n' && !quoted) { row.push(cell.replace(/\r$/, '')); rows.push(row); row = []; cell = ''; }
  else cell += c;
 }
 return rows.slice(1).map(row => Object.fromEntries(rows[0].map((header, i) => [header, row[i]])));
}
(async () => {
 const browser = await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try {
 const page = await browser.newPage();
 await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', {value:{writeText: async text => { window.copiedReport = text; }}, configurable:true}));
 const errors = []; page.on('pageerror', e => errors.push(e.message));
 await page.goto(url); await page.locator('#start').waitFor({state:'visible'});
 assert.match(await page.locator('#summary').innerText(), /30問/);
 await page.locator('#start').click();
 assert.equal(await page.locator('#palette button').count(), 30);
 assert.equal(await page.locator('#previous').isDisabled(), true);
 await page.locator('input[name=answer]').nth(0).check();
 await page.locator('input[name=confidence]').nth(1).check();
 assert.equal(await page.locator('#reviews').innerText(), '');
 assert.equal(await page.locator('.review-rationale').count(), 0);
 await page.locator('#flag').click();
 await page.locator('#next').click();
 await page.locator('#palette button').nth(0).click();
 assert.equal(await page.locator('input[name=answer]').nth(0).isChecked(), true);
 assert.equal(await page.locator('input[name=confidence]').nth(1).isChecked(), true);
 assert.equal(await page.locator('#flag').getAttribute('aria-pressed'), 'true');
 await page.locator('input[name=answer]').nth(1).check();
 assert.equal(await page.locator('input[name=confidence]:checked').count(), 0);
 await page.locator('#clear-answer').click();
 assert.equal(await page.locator('input[name=answer]:checked').count(), 0);
 await page.locator('input[name=answer]').nth(0).check();
 await page.locator('input[name=confidence]').nth(1).check();
 await page.locator('#palette button').nth(29).click();
 assert.equal(await page.locator('#next').isDisabled(), true);
 await page.locator('#finish').click();
 assert.match(await page.locator('#finish-summary').innerText(), /未回答 29問.*あとで確認 1問/);
 await page.locator('#cancel-finish').click();
 assert.equal(await page.locator('#finish-dialog').isVisible(), false);
 await page.locator('#finish').click(); await page.locator('#confirm-finish').click();
 assert.equal(await page.locator('#exam-screen').isVisible(), false);
 assert.equal(await page.locator('.review-item').count(), 30);
 assert.equal(await page.locator('#category-results tr').count(), 9);
 assert.equal(await page.locator('.review-rationale').count(), 30);
 await page.locator('#comp-btn-0-3').click();
 assert.equal(await page.locator('#comp-btn-0-3').getAttribute('aria-pressed'), 'true');
 await page.locator('#comp-btn-0-3').click();
 assert.equal(await page.locator('#comp-btn-0-3').getAttribute('aria-pressed'), 'false');
 await page.locator('#comp-btn-0-0').click();
 assert.equal(await page.locator('#comp-btn-0-0').getAttribute('aria-pressed'), 'true');
 await page.locator('.review-flag-cb').first().check();
 assert.equal(await page.locator('.review-flag-cb').first().isChecked(), true);
 assert.match(await page.locator('#review-item-1 .review-q').innerText(), /未回答/);
 assert.equal(await page.locator('#review-item-1 .correct-answer').isVisible(), true);
 assert.equal(await page.locator('.review-rationale').first().isVisible(), true);
 console.log('PASS: actual 30-question config, navigation, flags, answer/confidence retention/reset, clear, no early explanations, finish confirmation and results');
 page.once('dialog', dialog => dialog.dismiss());
 await page.locator('#generate-report').click();
 assert.equal(await page.locator('#output-section').isVisible(), false);
 assert.equal(await page.locator('#comp-warn-1').isVisible(), true);
 page.once('dialog', dialog => dialog.accept());
 await page.locator('#generate-report').click();
 const actualReport = await page.locator('#report-text').inputValue();
 const aiData = JSON.parse(actualReport.split('=== AI_ANALYSIS_DATA_JSON ===\n')[1]);
 assert.equal(aiData.session.mode, 'Actual');
 assert.equal(aiData.session.questionCount, 30);
 assert.equal(aiData.questions[0].confidence, '2 (少し自信がある)');
 assert.equal(aiData.questions[0].explanationUnderstanding, '0 (全然分からない)');
 assert.equal(aiData.questions[0].review, true);
 await page.locator('[data-action=copy]').click();
 await page.waitForFunction(() => !!window.copiedReport);
 assert.equal(await page.evaluate(() => window.copiedReport), actualReport);
 await page.locator('.review-flag-cb').first().uncheck();
 assert.equal(await page.locator('#output-section').isVisible(), false);
 assert.equal(await page.locator('#report-text').inputValue(), '');
 await page.locator('#comp-btn-0-3').click();
 page.once('dialog', dialog => dialog.accept());
 await page.locator('#generate-report').click();
 for (const type of ['questions', 'session', 'raw']) {
  const promise = page.waitForEvent('download');
  await page.locator(`[data-action=${type}]`).click();
  const download = await promise;
  const csv = fs.readFileSync(await download.path(), 'utf8');
  if (type === 'questions') {
   const rows = readCsv(csv);
   assert.equal(rows.length, 30);
   assert.equal(rows[0].Mode, 'Actual');
   assert.equal(rows[0].UnderstandingLevel, '3');
   assert.equal(rows[0].ReviewFlag, 'FALSE');
   assert.equal(rows[0].DuringExamReviewFlag, 'TRUE');
   assert.equal(rows[0].ConfidenceLevel, '2');
   assert.ok(rows[0].SkillID.startsWith('SK_JLPT_N2_'));
   assert.equal(rows[1].IsAnswered, 'FALSE');
   assert.equal(rows[1].AnsweredAt, '');
   assert.equal(rows[1].StudentID, '');
  } else if (type === 'session') {
   const [session] = readCsv(csv);
   assert.equal(session.Mode, 'Actual');
   assert.equal(session.TotalQuestions, '30');
   assert.equal(session.AnsweredQuestions, '1');
   assert.equal(session.UnansweredQuestions, '29');
   assert.equal(session.UseConfidence, 'TRUE');
   assert.ok(session.SourceQuestionFiles.includes('JLPT_N2_LK_Ch.json'));
  } else {
   assert.match(csv, /=== Session ===/);
   assert.match(csv, /=== QuestionResult ===/);
  }
 }
 console.log('PASS: Actual report cancel/confirm, AI data, clipboard, invalidation/re-generation, three CSV exports and typed answer/timestamp/skill fields');


 const timed = await browser.newPage(); await timed.clock.install();
 await timed.goto(url); await timed.locator('#start').click(); await timed.locator('#finish').click();
 await timed.clock.fastForward(40 * 60 * 1000 + 1000);
 assert.equal(await timed.locator('#finish-dialog').isVisible(), false);
 assert.match(await timed.locator('#finish-reason').innerText(), /自動/);
 assert.match(await timed.locator('#score').innerText(), /0 \/ 30/);
 assert.match(await timed.locator('#review-item-0 .review-ans').first().innerText(), /2400.0秒/);
 timed.once('dialog', dialog => dialog.accept());
 await timed.locator('#generate-report').click();
 assert.match(await timed.locator('#report-text').inputValue(), /模擬試験/);
 console.log('PASS: time expiry during confirmation, all-unanswered score, automatic finalization, per-question time capped at deadline and report');

 const mobile = await browser.newPage({viewport:{width:390,height:844}});
 await mobile.route('**/conf_JLPT_N2_LK.json', route => route.fulfill({json:{...config,recordConfidence:false}}));
 await mobile.goto(url); await mobile.locator('#start').click();
 assert.equal(await mobile.locator('#confidence').isVisible(), false);
 assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
 await mobile.locator('#palette button').nth(20).click();
 assert.match(await mobile.locator('#progress').innerText(), /問題 21/);
 await mobile.locator('#finish').click(); await mobile.locator('#confirm-finish').click();
 assert.equal(await mobile.locator('#review-item-0 .review-rationale').isVisible(), true);
 assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
 assert.doesNotMatch(await mobile.locator('#review-item-0 .review-ans').first().innerText(), /自信度/);
 mobile.once('dialog', dialog => dialog.accept());
 await mobile.locator('#generate-report').click();
 assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
 assert.match(await mobile.locator('#report-text').inputValue(), /自信度記録: なし/);
 await mobile.evaluate(() => {
  Object.defineProperty(navigator, 'clipboard', {value:undefined,configurable:true});
  document.execCommand = () => false;
 });
 await mobile.locator('[data-action=copy]').click();
 assert.match(await mobile.locator('.result-output-status').innerText(), /手動でコピー/);
 console.log('PASS: confidence-disabled configuration, mobile layout/results/report and manual clipboard fallback');

 const bad = await browser.newPage();
 await bad.route('**/conf_JLPT_N2_LK.json', route => route.fulfill({json:{...config,categories:[{...config.categories[0],count:999999}]}}));
 await bad.goto(url); await bad.locator('#error').waitFor({state:'visible'});
 assert.match(await bad.locator('#error').innerText(), /しかありません/);
 assert.equal(await bad.locator('#start').isVisible(), false);
 await bad.unroute('**/conf_JLPT_N2_LK.json');
 await bad.route('**/data/JLPT_N2_LK_Ch.json', route => route.fulfill({status:404,body:'missing'}));
 await bad.reload(); await bad.locator('#error').waitFor({state:'visible'});
 assert.match(await bad.locator('#error').innerText(), /404/);
 console.log('PASS: insufficient category pool and missing bank block start');
 // The drill page uses the same cards; its raw logs and exports must retain review edits.
 const drill = await browser.newPage();
 drill.on('pageerror', e => errors.push(e.message));
 drill.on('dialog', dialog => dialog.accept());
 await drill.goto(url.replace('Actual_N2_261030.html', 'separete_drill_261026.html'));
 await drill.waitForFunction(() => typeof originalQuizData !== 'undefined' && originalQuizData.length > 0);
 await drill.evaluate(() => startExam());
 await drill.locator('.option-btn').first().click();
 await drill.locator('.conf-btn').first().click();
 assert.equal(await drill.locator('#instant-feedback').isVisible(), true);
 await drill.evaluate(() => submitExam());
 assert.equal(await drill.locator('#review-list .review-item').count(), 10);
 assert.equal(await drill.locator('#review-list .review-rationale').first().isVisible(), true);
 await drill.locator('#comp-btn-0-3').click();
 await drill.locator('.review-flag-cb').first().check();
 assert.equal(await drill.evaluate(() => rawLogArray[0].understandingLevel), 3);
 assert.match(await drill.evaluate(() => actualSummary.sourceQuestionFiles), /JLPT_N2_LK_Ch.json/);
 assert.equal(await drill.evaluate(() => rawLogArray[0].reviewFlag), true);
 await drill.locator('#comp-btn-0-3').click();
 assert.equal(await drill.evaluate(() => rawLogArray[0].understandingLevel), null);
 await drill.evaluate(() => finalizeAndGenerateReport());
 assert.equal(await drill.locator('#output-section').isVisible(), true);
 await drill.locator('#comp-btn-0-0').click();
 assert.equal(await drill.locator('#output-section').isVisible(), false);
 await drill.evaluate(() => finalizeAndGenerateReport());
 const report = await drill.locator('#report-text').inputValue();
 assert.match(report, /全然分からない/);
 assert.match(report, /要復習フラグ: TRUE/);
 const downloadPromise = drill.waitForEvent('download');
 await drill.evaluate(() => downloadQuestionResultCSV());
 const download = await downloadPromise;
 assert.match(download.suggestedFilename(), /^QuestionResult_/);
 const csv = fs.readFileSync(await download.path(), 'utf8');
 assert.match(csv, /UnderstandingLevel/);
 assert.match(csv, /全然分からない/);
 console.log('PASS: drill practice instant feedback, shared results, understanding toggle, raw log updates, report generation and CSV download');
 assert.deepEqual(errors, []);
 } finally { await browser.close(); }
})().catch(e=>{console.error(e); process.exit(1)});
