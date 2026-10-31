import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const context = vm.createContext({window:{},structuredClone});
vm.runInContext(fs.readFileSync(new URL('../../prototype/assets/js/shared/examConfig.js',import.meta.url),'utf8'),context);
const {normalize} = context.window.ExamConfig;
const config = JSON.parse(fs.readFileSync(new URL('../../prototype/language/JLPT_N2/conf_JLPT_N2_LK.json',import.meta.url)));
test('one config supplies independent Actual quotas and Drill options',()=>{
 const before=JSON.stringify(config);
 const actual=normalize(config,'actual'),drill=normalize(config,'drill');
 assert.equal(actual.categories.reduce((n,c)=>n+c.count,0),30);
 assert.equal(actual.timeLimitMinutes,40);
 assert.equal(actual.shuffleOptions,false);
 assert.equal(drill.shuffleOptions,true);
 assert.equal(drill.defaultQuestionCount,10);
 assert.equal(drill.categories[0].skillId,actual.categories[0].skillId);
 assert.equal(JSON.stringify(config),before);
});
test('bad settings fail rather than silently using defaults',()=>{
 for(const drill of [{...config.drill,questionCounts:[]},{...config.drill,defaultQuestionCount:999},{...config.drill,recordConfidence:'false'},{...config.drill,difficultyModes:['unknown']},{...config.drill,defaultDifficultyMode:'unknown'}])assert.throws(()=>normalize({...config,drill},'drill'));
 assert.throws(()=>normalize({...config,questionFiles:[]},'drill'));
 assert.throws(()=>normalize({...config,categories:[config.categories[0],config.categories[0]]},'drill'));
 assert.throws(()=>normalize({...config,schemaVersion:99},'actual'));
});
test('legacy Actual config is accepted without changing its shape',()=>{
 const legacy=normalize(config,'actual');
 assert.equal(normalize(legacy,'actual').timeLimitMinutes,40);
 assert.throws(()=>normalize(legacy,'drill'),/schemaVersion: 2/);
});
