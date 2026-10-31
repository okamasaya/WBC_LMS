const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const url = process.env.IRIS_TEST_URL || 'http://127.0.0.1:8050';

// Plotly receives pointer events on its transparent drag layer, not SVG marks.
async function clickMark(page, selector) {
    const mark = page.locator(selector).first();
    await mark.waitFor({state:'visible'});
    await mark.scrollIntoViewIfNeeded();
    const box = await mark.boundingBox();
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}
async function countIs(page, count) {
    await page.waitForFunction(value => document.querySelector('#kpi-count')?.textContent === String(value), count);
}
async function brush(page, graph, left, top, right, bottom) {
    const plot = page.locator(`#${graph} .nsewdrag`);
    await plot.scrollIntoViewIfNeeded();
    const box = await plot.boundingBox();
    await page.mouse.move(box.x + box.width * left, box.y + box.height * top);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * right, box.y + box.height * bottom, {steps:15});
    await page.mouse.up();
}
(async()=>{
    const browser = await chromium.launch({executablePath:process.env.CBT_TEST_CHROMIUM || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
    try {
        const page = await browser.newPage({viewport:{width:1440,height:1100}});
        page.setDefaultTimeout(15000);
        const errors=[];page.on('pageerror',error=>errors.push(error.message));
        await page.goto(url);
        await countIs(page,150);
        assert.equal(await page.locator('#kpi-mean').innerText(),'5.84');
        await clickMark(page,'#iris-scatter path.point');
        await countIs(page,1);
        assert.equal(await page.locator('#kpi-std').innerText(),'—');
        await page.waitForFunction(()=>document.querySelectorAll('#iris-table td[data-dash-column="sample_no"]').length===1);
        assert.equal(await page.locator('#iris-scatter path.point').count(),150);
        await clickMark(page,'#iris-scatter path.point');
        await countIs(page,150);
        console.log('PASS real point click, linked table/KPIs, source context and same-point deselection');

        await clickMark(page,'#iris-bar .barlayer .point path');
        await countIs(page,50);
        assert.match(await page.locator('#selection-summary').innerText(),/setosa/);
        await clickMark(page,'#iris-scatter path.point');
        await countIs(page,1);
        assert.match(await page.locator('#selection-summary').innerText(),/散布図/);
        await page.locator('#clear-bar').click();
        await page.waitForFunction(()=>!document.querySelector('#selection-summary').textContent.includes('棒グラフ'));
        await countIs(page,1);
        assert.doesNotMatch(await page.locator('#selection-summary').innerText(),/棒グラフ/);
        await page.locator('#clear-scatter').click();
        await countIs(page,150);
        console.log('PASS category bar click, intersection with point selection and independent filter clearing');

        await page.locator('#species-dropdown').click();
        await page.getByRole('option',{name:'Versicolor',exact:true}).click();
        await countIs(page,50);
        await clickMark(page,'#iris-scatter path.point');
        await countIs(page,1);
        const rowId=Number(await page.locator('#iris-table td[data-dash-column="sample_no"]').first().innerText());
        assert.ok(rowId>=51 && rowId<=100);
        await page.locator('#reset-iris').click();
        await countIs(page,150);
        assert.match(await page.locator('#species-dropdown').innerText(),/すべて/);
        console.log('PASS Species base filter, stable row identity after regrouping, full reset');

        await brush(page,'iris-scatter',0.1,0.15,0.45,0.8);
        await page.waitForFunction(()=>{const n=Number(document.querySelector('#kpi-count').textContent);return n>1&&n<150;});
        const narrow=Number(await page.locator('#kpi-count').innerText());
        console.log(`PASS scatter range selected ${narrow} rows`);
        await brush(page,'iris-scatter',0.05,0.05,0.95,0.95);
        await page.waitForFunction(value=>Number(document.querySelector('#kpi-count').textContent)>value,narrow);
        assert.equal(await page.locator('#iris-scatter path.point').count(),150);
        await page.locator('#clear-scatter').click();await countIs(page,150);
        await page.waitForFunction(()=>document.querySelector('#selection-summary').textContent==='選択条件なし（全件）');
        await page.waitForFunction(()=>document.querySelectorAll('#iris-line path.point').length===300);
        await brush(page,'iris-line',0.1,0.05,0.3,0.95);
        await page.waitForFunction(()=>{const n=Number(document.querySelector('#kpi-count').textContent);return n>1&&n<150;});
        assert.match(await page.locator('#selection-summary').innerText(),/折れ線/);
        console.log('PASS real box selection, expansion without cumulative shrinking, line selection across two series');

        const screenshotDir=process.env.IRIS_TEST_SCREENSHOT_DIR;
        if(screenshotDir){fs.mkdirSync(screenshotDir,{recursive:true});await page.screenshot({path:path.join(screenshotDir,'iris-linked-desktop.png'),fullPage:true});}
        await page.locator('#reset-iris').click();await countIs(page,150);
        await page.setViewportSize({width:390,height:844});
        await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
        await clickMark(page,'#iris-bar .barlayer .point path');await countIs(page,50);
        if(screenshotDir)await page.screenshot({path:path.join(screenshotDir,'iris-linked-mobile.png'),fullPage:true});
        await page.locator('#reset-iris').click();await countIs(page,150);
        assert.deepEqual(errors,[]);
        console.log('PASS mobile chart selection/reset and no browser errors');
    }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
