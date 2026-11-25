import copy
import unittest
from checker_dimensions import check,DIMENSIONS
from core import Pipeline,AppError
from test_pipeline import BODY,REPLY,FakeModel

class DimensionTests(unittest.TestCase):
    def verdicts(self):
        return {k:dict(status='pass',candidate_quote='I cannot help Friday.',reason='匹配',source_message_ids=['m1']) for k in DIMENSIONS}
    def test_fail_and_uncertain_remain_distinct(self):
        v=self.verdicts();v['roles']['status']='fail';v['facts']['status']='uncertain'
        result=check(FakeModel(v),Pipeline().prepare(BODY),REPLY['replies'][0])
        self.assertEqual(result['checks'][0]['type'],'role_conflict')
        self.assertEqual(result['uncertain_dimensions'],['facts'])
    def test_invented_quote_rejected(self):
        v=self.verdicts();v['roles']['candidate_quote']='not in reply'
        with self.assertRaises(AppError):check(FakeModel(v),Pipeline().prepare(BODY),REPLY['replies'][0])
    def test_missing_dimension_rejected(self):
        v=self.verdicts();del v['roles']
        with self.assertRaises(AppError):check(FakeModel(v),Pipeline().prepare(BODY),REPLY['replies'][0])
