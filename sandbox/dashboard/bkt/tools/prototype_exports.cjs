// 現行の共通処理をそのまま実行する。CSV列や正誤・ラベルを別実装しない。
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'../../../..');
const files=['questionLoader','examConfig','resultData','resultReview','resultReport'];
function build(payload){
 const context=vm.createContext({window:{},structuredClone,document:{getElementById:()=>null}});
 for(const file of files) vm.runInContext(fs.readFileSync(path.join(root,'prototype/assets/js/shared',file+'.js'),'utf8'),context);
 const conf=JSON.parse(fs.readFileSync(path.join(root,'prototype/language/JLPT_N2/conf_JLPT_N2_LK.json'),'utf8'));
 const config=context.window.ExamConfig.normalize(conf,'actual');
 const bank=new Map();
 for(const file of conf.questionFiles) for(const raw of JSON.parse(fs.readFileSync(path.join(root,'prototype/language/JLPT_N2',file),'utf8'))) bank.set(raw.question_id,raw);
 const groups=new Map();for(const row of payload.tables.QuestionResult){if(!groups.has(row.SessionID))groups.set(row.SessionID,[]);groups.get(row.SessionID).push(row);}
 const sessions=[];
 for(const source of payload.tables.Session){
  const rows=groups.get(source.SessionID).sort((a,b)=>a.QuestionSequence-b.QuestionSequence);
  const questions=rows.map((row,index)=>context.convertQuestionFormat(bank.get(row.QuestionID),index));
  const answers=rows.map(row=>({selected:row.IsAnswered?row.UserAnswerDisplayedPosition-1:null,confidence:row.ConfidenceLevel,elapsedTimeMs:row.ResponseTimeMs,answeredAt:row.AnsweredAt,flagged:false}));
  const data=context.window.ResultData.build({questions,answers,startedAt:Date.parse(source.StartAt),endedAt:Date.parse(source.EndAt),metadata:{examId:config.examId,examType:config.examType,examLevel:config.examLevel,examTitle:config.examTitle||config.title,studentId:payload.identity==='anonymous'?null:source.StudentID,mode:'Actual',useConfidence:config.recordConfidence,difficultyMode:'all',sourceQuestionFiles:conf.questionFiles.join(' | ')},resolveSkill:q=>config.categories.find(c=>c.categoryLv1===q.category_lv1&&c.categoryLv2===q.category_lv2&&c.categoryLv3===q.category_lv3)});
  data.records.forEach((record,index)=>{if(rows[index].UnderstandingLevel!=null) context.window.ResultReview.toggleUnderstanding(record,index,rows[index].UnderstandingLevel);record.reviewFlag=false;});
  const exported={};for(const type of ['session','questions','raw']) exported[type]=context.window.ResultReport.exportCsv(data,type);
  sessions.push({mock_session_id:source.SessionID,mock_result_ids:rows.map(r=>r.ResultID),session_number:source.SessionNumber,session:data.summary,records:data.records,exports:exported,report:context.window.ResultReport.buildReport(data)});
 }
 return {schema:{Session:context.window.ResultReport.SESSION_CSV_COLUMNS,QuestionResult:context.window.ResultReport.QUESTION_RESULT_CSV_COLUMNS},sessions};
}
if(require.main===module){const input=fs.readFileSync(0,'utf8');process.stdout.write(JSON.stringify(build(JSON.parse(input))));}
module.exports={build};
