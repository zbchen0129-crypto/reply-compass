import copy
import unittest
from core import Pipeline, AppError
from test_pipeline import BODY, REPLY, FakeModel
from scripts.evaluate_checker import score, load_cases
from pathlib import Path

class CheckerTests(unittest.TestCase):
    def test_isolated_checker_calls_model_once_with_fixed_candidates(self):
        model=FakeModel({'checks':[]}); body=dict(copy.deepcopy(BODY),candidates=copy.deepcopy(REPLY['replies']))
        result=Pipeline(model).check(body)
        self.assertEqual(len(model.calls),1)
        self.assertEqual(model.calls[0][1]['candidates'],REPLY['replies'])
        self.assertEqual(result['check_status'],'completed')
    def test_bad_candidate_blocked_before_call(self):
        model=FakeModel();body=dict(copy.deepcopy(BODY),candidates=copy.deepcopy(REPLY['replies']))
        body['candidates'][0]['evidence_ids']=['missing']
        with self.assertRaises(AppError):Pipeline(model).check(body)
        self.assertEqual(model.calls,[])
    def test_reminder_is_not_false_positive(self):
        cases=[{'id':'ok','expected_error_types':[]}]
        results=[{'id':'ok','response':{'checks':[{'type':'new_commitment'}]}}]
        self.assertEqual(score(cases,results)['counts']['true_negative'],1)
    def test_failure_and_wrong_type_are_separate(self):
        cases=[{'id':'bad','expected_error_types':['role_conflict']},{'id':'failed','expected_error_types':['stance_conflict']},{'id':'pending','expected_error_types':[]}]
        results=[{'id':'bad','response':{'checks':[{'type':'missing_answer'}]}},{'id':'failed','error':{'status':504}}]
        counts=score(cases,results)['counts']
        self.assertEqual(counts['true_positive'],1)
        self.assertEqual(counts['target_hits'],0)
        self.assertEqual(counts['failed'],1)
        self.assertEqual(counts['not_run'],1)
        self.assertEqual(counts['false_negative'],0)
    def test_dataset_valid_and_labels_not_in_request(self):
        data=load_cases(Path('evals/checker-fixed-v1.json'))
        self.assertEqual(len(data['cases']),8)
        for case in data['cases']:
            self.assertNotIn('expected_error_types',case['request'])
            self.assertNotIn('rubric',case['request'])
