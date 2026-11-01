import copy
import csv
import json
import math
from io import StringIO
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from sandbox.dashboard.bkt.assisted_model import AuxiliaryAssumptions, combinations, estimate_flat, update_flat
from sandbox.dashboard.bkt.model import BKTParameters, update
from sandbox.dashboard.bkt.flat_app import app


class AssistedModelTests(unittest.TestCase):
    def test_no_auxiliaries_reproduces_classic(self):
        for correct in [True,False]:
            expected=update(.2,correct,BKTParameters())
            actual=update_flat(correct)
            self.assertEqual(actual['PredictedCorrect'],expected[0])
            self.assertEqual(actual['AssistedPosterior'],expected[1])
            self.assertEqual(actual['AssistedAfterLearning'],expected[2])

    def test_power_likelihood_matches_hand_calculation(self):
        actual=update_flat(True,1,3)
        a=.2*(.9**1.5);b=.8*(.25**1.5)
        posterior=a/(a+b)
        self.assertAlmostEqual(actual['AssistedPosterior'],posterior)
        self.assertAlmostEqual(actual['AssistedAfterLearning'],posterior+(1-posterior)*.1)

    def test_confidence_direction_for_correct_and_wrong(self):
        correct=[update_flat(True,c,3)['AssistedPosterior'] for c in range(1,5)]
        wrong=[update_flat(False,c,3)['AssistedPosterior'] for c in range(1,5)]
        self.assertEqual(correct,sorted(correct,reverse=True))
        self.assertEqual(wrong,sorted(wrong))
        self.assertTrue(all(value>.2 for value in correct))
        self.assertTrue(all(value<.2 for value in wrong))

    def test_understanding_only_changes_later_transition(self):
        results=[update_flat(True,2,u) for u in range(4)]
        self.assertEqual(len({r['AssistedPosterior'] for r in results}),1)
        self.assertEqual(len({r['PredictedCorrect'] for r in results}),1)
        for result, expected in zip(results,[.025,.05,.075,.1]):
            self.assertAlmostEqual(result['EffectiveLearning'],expected)
        self.assertEqual([r['AssistedAfterLearning'] for r in results],sorted(r['AssistedAfterLearning'] for r in results))

    def test_all_32_patterns_are_finite_probabilities(self):
        result=estimate_flat(combinations())
        self.assertEqual(len(result['records']),32)
        self.assertEqual(result['excluded'],[])
        self.assertEqual({r['PredictedCorrect'] for r in result['records']},{.38})
        for row in result['records']:
            for key in ['ClassicPosterior','ClassicAfterLearning','AssistedPosterior','AssistedAfterLearning','NextCorrect']:
                self.assertTrue(math.isfinite(row[key]) and 0<=row[key]<=1)

    def test_missing_is_different_from_understanding_zero(self):
        missing=update_flat(False,None,None)
        zero=update_flat(False,None,0)
        self.assertTrue(missing['UnderstandingMissing'])
        self.assertFalse(zero['UnderstandingMissing'])
        self.assertEqual(missing['LearningScale'],1)
        self.assertEqual(zero['LearningScale'],.25)
        self.assertGreater(missing['AssistedAfterLearning'],zero['AssistedAfterLearning'])

    def test_invalid_levels_are_rejected(self):
        for confidence in [0,5,True,1.5,math.nan,'bad']:
            with self.subTest(confidence=confidence),self.assertRaises(ValueError):
                update_flat(True,confidence,3)
        for understanding in [-1,4,False,2.5,math.inf,'bad']:
            with self.subTest(understanding=understanding),self.assertRaises(ValueError):
                update_flat(True,2,understanding)

    def test_invalid_assumptions_are_rejected(self):
        for values in [None,[],[1,2,3],[0,1,1,1],[True,1,1,1],[math.inf,1,1,1]]:
            with self.subTest(values=values),self.assertRaises(ValueError):
                AuxiliaryAssumptions(confidence_weights=values)
        with self.assertRaises(ValueError):AuxiliaryAssumptions(understanding_scales=(0,.5,1,1.1))

    def test_extreme_priors_and_weights_are_stable(self):
        for prior in [0,1,1e-200,1-1e-15]:
            for correct in [True,False]:
                value=update_flat(correct,1,3,BKTParameters(p_l0=prior),AuxiliaryAssumptions(confidence_weights=(1e308,1,1,1)))
                self.assertTrue(math.isfinite(value['AssistedAfterLearning']))
        with self.assertRaises(ValueError):update_flat(True,1,3,BKTParameters(p_l0=0,p_g=0))

    def test_duplicate_features_and_conflicting_versions(self):
        row={'ResultID':'r','IsCorrect':True,'ConfidenceLevel':1,'UnderstandingLevel':0}
        result=estimate_flat([row,row.copy()])
        self.assertEqual(len(result['records']),1)
        self.assertEqual(len(result['excluded']),1)
        for change in [{'UnderstandingLevel':3},{'ConfidenceLevel':4},{'IsCorrect':False},{'StudentID':'another'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                estimate_flat([row,{**row,**change}])

    def test_raw_input_unchanged_and_identity_not_required(self):
        raw=[{'IsCorrect':'FALSE','ConfidenceLevel':' 1 ','UnderstandingLevel':'0'}]
        original=copy.deepcopy(raw)
        result=estimate_flat(raw)
        self.assertEqual(raw,original)
        self.assertFalse(result['records'][0]['IsCorrect'])
        self.assertIsNone(result['records'][0]['ResultID'])

    def test_invalid_and_unanswered_rows_are_explained(self):
        result=estimate_flat([{'IsAnswered':False,'IsCorrect':False},{'IsCorrect':'maybe'},{'IsCorrect':True,'ConfidenceLevel':0},None])
        self.assertEqual(result['records'],[])
        self.assertEqual(len(result['excluded']),4)
        self.assertIn('未回答',result['excluded'][0]['Reason'])

    def test_no_history_or_student_skill_dependency(self):
        raw=[{'ResultID':'one','IsCorrect':True,'ConfidenceLevel':2,'UnderstandingLevel':3},
             {'ResultID':'two','StudentID':'different','SkillID':'other','IsCorrect':True,'ConfidenceLevel':2,'UnderstandingLevel':3}]
        result=estimate_flat(raw)['records']
        self.assertEqual(result[0]['AssistedAfterLearning'],result[1]['AssistedAfterLearning'])
        reverse=estimate_flat(list(reversed(raw)))['records']
        self.assertEqual({r['ResultID']:r['AssistedAfterLearning'] for r in result},{r['ResultID']:r['AssistedAfterLearning'] for r in reverse})

    def test_no_learning_and_input_limit(self):
        result=update_flat(True,1,3,BKTParameters(p_t=0))
        self.assertEqual(result['AssistedAfterLearning'],result['AssistedPosterior'])
        with self.assertRaises(ValueError):estimate_flat([{}]*50001)


class FlatHTTPTests(unittest.TestCase):
    def callback(self,contains,changed,values):
        key=next(key for key in app.callback_map if contains in key)
        definition=app.callback_map[key]
        outputs=definition['output'];multiple=isinstance(outputs,list)
        items=outputs if multiple else [outputs]
        output_json=[{'id':item.component_id,'property':item.component_property} for item in items]
        payload={'output':key,'outputs':output_json if multiple else output_json[0],
                 'inputs':[{**item,'value':values.get(item['id'])} for item in definition['inputs']],
                 'state':[{**item,'value':values.get(item['id'])} for item in definition['state']],
                 'changedPropIds':[changed]}
        with app.server.test_client() as client:response=client.post('/_dash-update-component',json=payload)
        self.assertEqual(response.status_code,200,response.get_data(as_text=True))
        return response.get_json()['response']

    def inputs(self,**changes):
        return {'flat-correct':1,'flat-confidence':2,'flat-understanding':3,'flat-l0':.2,'flat-t':.1,'flat-g':.25,'flat-s':.1,'flat-dataset':'patterns','flat-filter':'all',**changes}

    def test_layout_patterns_and_cell_selection(self):
        with app.server.test_client() as client:
            for route in ['/','/_dash-layout','/_dash-dependencies','/assets/flat.css']:
                with client.get(route) as response:
                    self.assertEqual(response.status_code,200)
        rendered=self.callback('flat-analysis.data','flat-correct.value',self.inputs())
        self.assertEqual(len(rendered['flat-table']['data']),32)
        self.assertEqual(len(rendered['flat-wrong']['figure']['data'][0]['z']),4)
        clicked=self.callback('flat-correct.value','flat-wrong.clickData',{'flat-wrong':{'points':[{'x':1,'y':0}]}})
        self.assertEqual(clicked['flat-correct']['value'],0)
        self.assertEqual(clicked['flat-understanding']['value'],0)

    def test_invalid_parameters_clear_outputs(self):
        result=self.callback('flat-analysis.data','flat-g.value',self.inputs(**{'flat-g':.95}))
        self.assertIsNone(result['flat-analysis']['data'])
        self.assertEqual(result['flat-table']['data'],[])
        self.assertTrue(result['flat-export']['disabled'])

    def test_filtered_csv_and_model_assumptions_export(self):
        rendered=self.callback('flat-analysis.data','flat-filter.value',self.inputs(**{'flat-filter':'wrong'}))
        state=rendered['flat-analysis']['data']
        result=self.callback('flat-download.data','flat-export.n_clicks',{'flat-export':1,'flat-analysis':state})
        rows=list(csv.DictReader(StringIO(result['flat-download']['data']['content'].lstrip('\ufeff'))))
        self.assertEqual(len(rows),16)
        self.assertTrue(all(row['IsCorrect']=='False' for row in rows))
        result=self.callback('flat-download.data','flat-export-model.n_clicks',{'flat-export-model':1,'flat-analysis':state})
        metadata=json.loads(result['flat-download']['data']['content'])
        self.assertEqual(metadata['assumptions']['confidence_weights'],[1.5,1,.75,.5])
        self.assertEqual(metadata['scope'],'independent_answers_same_prior')


if __name__=='__main__':unittest.main()
