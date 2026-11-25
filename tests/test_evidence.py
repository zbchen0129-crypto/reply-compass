import unittest
from checker_evidence import check
from core import Pipeline,AppError
from test_pipeline import BODY,REPLY,FakeModel

class EvidenceTests(unittest.TestCase):
    def audit(self):
        return dict(claims=[dict(candidate_quote='I cannot help Friday.',classification='new_decision',evidence=[],reason='新拒绝')],roles=dict(original_actor='self',candidate_actor='self',comparison='same_action',candidate_quote='help',evidence=[dict(message_id='m2',quote='Can you help Friday?')],reason='行动者相同'),stance=dict(matches='yes',candidate_quote='cannot',reason='拒绝'))
    def test_valid_refusal(self):
        result=check(FakeModel(self.audit()),Pipeline().prepare(BODY),REPLY['replies'][0]);self.assertEqual(result['checks'],[])
    def test_fabricated_source_rejected(self):
        v=self.audit();v['roles']['evidence'][0]['quote']='I am free at four'
        with self.assertRaises(AppError):check(FakeModel(v),Pipeline().prepare(BODY),REPLY['replies'][0])
    def test_supported_without_evidence_rejected(self):
        v=self.audit();v['claims'][0]['classification']='supported'
        with self.assertRaises(AppError):check(FakeModel(v),Pipeline().prepare(BODY),REPLY['replies'][0])
    def test_actor_mismatch_derived(self):
        v=self.audit();v['roles']['candidate_actor']='other'
        result=check(FakeModel(v),Pipeline().prepare(BODY),REPLY['replies'][0])
        self.assertEqual(result['checks'][0]['type'],'role_conflict')
    def test_conditional_not_treated_as_fact(self):
        v=self.audit();v['claims'][0]['classification']='conditional'
        self.assertEqual(check(FakeModel(v),Pipeline().prepare(BODY),REPLY['replies'][0])['checks'],[])
