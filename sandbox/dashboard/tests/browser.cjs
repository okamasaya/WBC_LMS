const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const url = process.env.ALP_TEST_URL || 'http://127.0.0.1:8051';

// Use the current learner page's export implementation with entirely synthetic observations.
function fixtures() {
    const context = vm.createContext({window:{}});
    for (const name of ['resultData','resultReport']) vm.runInContext(fs.readFileSync(path.join(__dirname,'../../../prototype/assets/js/shared',name+'.js'),'utf8'),context);
    const questions = [0,1,2].map(i=>({id:'Q'+i,category_lv1:'言語知識',category_lv2:'文字',category_lv3:'漢字読み',question:'テスト問題 '+i,difficulty:3,options:[{text:'正解',isCorrect:true,rationale:'解説'},{text:'不正解',isCorrect:false},{text:'選択肢3',isCorrect:false},{text:'選択肢4',isCorrect:false}]}));
    const data=context.window.ResultData.build({questions,answers:[{selected:0,confidence:1,elapsedTimeMs:10000,answeredAt:'2026-10-31T00:00:10Z'},{selected:1,confidence:3,elapsedTimeMs:15000,answeredAt:'2026-10-31T00:00:25Z'},{selected:null,elapsedTimeMs:5000}],startedAt:Date.parse('2026-10-31T00:00:00Z'),endedAt:Date.parse('2026-10-31T00:00:30Z'),metadata:{examId:'JLPT_N2_LK',examType:'JLPT',examLevel:'N2',examTitle:'テスト用N2',mode:'Actual',useConfidence:true},resolveSkill:()=>({skillId:'SK_TEST_READING',skillName:'テスト・漢字読み'})});
    return ['questions','raw'].map(type=>({name:type+'.csv',mimeType:'text/csv',buffer:Buffer.from('\ufeff'+context.window.ResultReport.exportCsv(data,type).content)}));
}
(async()=>{
    const browser=await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
    try {
        const page=await browser.newPage({viewport:{width:1400,height:1000}});
        const errors=[];page.on('pageerror',error=>errors.push(error.message));
        await page.goto(url);
        await page.locator('#sample-data').click();
        await page.waitForFunction(()=>document.querySelector('#import-status').textContent.includes('推定対象 24件'));
        await page.waitForFunction(()=>!document.querySelector('#export-history').disabled);
        assert.match(await page.locator('#state-table').innerText(),/DEMO-A/);
        await page.locator('#student-filter').click();
        await page.getByRole('option',{name:'DEMO-B',exact:true}).click();
        await page.waitForFunction(()=>document.querySelector('#state-table').textContent.includes('DEMO-B'));
        assert.doesNotMatch(await page.locator('#state-table').innerText(),/DEMO-A/);
        console.log('PASS dashboard sample, charts and learner filter');

        const files=fixtures();
        await page.locator('#csv-upload input[type=file]').setInputFiles(files);
        await page.locator('#import-data').click();
        await page.waitForFunction(()=>document.querySelector('#import-status').textContent.includes('推定対象 0件'));
        await page.waitForFunction(()=>document.querySelector('#export-history').disabled);
        await page.locator('#fallback-student').fill('learner-test');
        await page.locator('#fallback-student').blur();
        await page.getByLabel('空欄の行は、すべて同じ1人のログです').check();
        await page.locator('#import-data').click();
        await page.waitForFunction(()=>document.querySelector('#import-status').textContent.includes('推定対象 2件'));
        await page.waitForFunction(()=>!document.querySelector('#export-history').disabled);
        assert.match(await page.locator('#import-status').innerText(),/除外 4件/);
        assert.match(await page.locator('#state-table').innerText(),/learner-test/);
        for(const [id,filename] of [['export-state','KnowledgeState.csv'],['export-history','KnowledgeStateHistory.csv'],['export-parameters','BKTParameter.csv']]) {
            const promise=page.waitForEvent('download');await page.locator('#'+id).click();
            const download=await promise;
            assert.equal(download.suggestedFilename(),filename);
            const text=fs.readFileSync(await download.path(),'utf8');
            if(id==='export-state') assert.match(text,/0\.216129032/);
            if(id==='export-history') {assert.match(text,/SK_TEST_READING/);assert.match(text,/RESULT_/);}
            if(id==='export-parameters') assert.match(text,/manual_assumption/);
        }
        console.log('PASS current QuestionResult and unified Raw exports, anonymous identity confirmation, deduplication, unanswered exclusion and BKT CSVs');
        await page.getByText('BKTパラメータを調整する（未校正の仮設定）',{exact:true}).click();
        await page.locator('#p-g').fill('0.95');await page.locator('#p-g').blur();
        await page.waitForFunction(()=>document.querySelector('#model-status').textContent.includes('Guess + Slip'));
        assert.equal(await page.locator('#export-state').isDisabled(),true);
        await page.locator('#p-g').fill('0.25');await page.locator('#p-g').blur();
        await page.waitForFunction(()=>!document.querySelector('#export-state').disabled);
        await page.setViewportSize({width:390,height:844});
        await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
        const screenshotDir=process.env.ALP_TEST_SCREENSHOT_DIR;
        if(screenshotDir){fs.mkdirSync(screenshotDir,{recursive:true});await page.screenshot({path:path.join(screenshotDir,'alp-mobile.png'),fullPage:true});}
        await page.locator('#clear-data').click();
        await page.waitForFunction(()=>document.querySelector('#import-status').textContent.includes('クリア'));
        await page.waitForFunction(()=>document.querySelector('#export-history').disabled);
        assert.match(await page.locator('#selected-files').innerText(),/まだファイル/);
        assert.doesNotMatch(await page.locator('#state-table').innerText(),/learner-test/);
        console.log('PASS invalid parameter clears estimates, recovery, mobile layout and clear data');
        assert.deepEqual(errors,[]);
    } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
