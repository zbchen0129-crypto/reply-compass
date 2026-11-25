import copy
import unittest
from core import AppError, Pipeline
from test_pipeline import BODY, REPLY, FakeModel

class RoleContractTests(unittest.TestCase):
    def test_edited_roles_reach_generation_and_check(self):
        body=copy.deepcopy(BODY)
        roles={'subject':'other','requester':'self','actor':'other','recipient':'self'}
        body['context']['items'][0]['roles']=roles
        model=FakeModel(REPLY,{'checks':[]})
        Pipeline(model).generate(body)
        for _, data in model.calls:
            self.assertEqual(data['user_reviewed_context']['items'][0]['roles'],roles)

    def test_unknown_and_non_applicable_roles_are_distinct(self):
        body=copy.deepcopy(BODY)
        body['context']['items'][0]['roles']['actor']='unknown'
        model=FakeModel(REPLY,{'checks':[]})
        Pipeline(model).generate(body)
        self.assertEqual(model.calls[0][1]['user_reviewed_context']['items'][0]['roles']['actor'],'unknown')

    def test_invalid_or_missing_roles_rejected_before_model_call(self):
        for roles in [None,{'actor':'third_person'}, {'subject':'self','requester':'self','actor':'invented','recipient':'self'}]:
            body=copy.deepcopy(BODY);model=FakeModel()
            if roles is None: del body['context']['items'][0]['roles']
            else:body['context']['items'][0]['roles']=roles
            with self.assertRaises(AppError):Pipeline(model).generate(body)
            self.assertFalse(model.calls)

    def test_new_intents_are_separate_and_do_not_rewrite_history(self):
        body=copy.deepcopy(BODY);body['directions']=['答应','有条件答应']
        replies={'replies':[dict(REPLY['replies'][0],direction=d) for d in body['directions']]}
        model=FakeModel(replies,{'checks':[]})
        Pipeline(model).generate(body)
        for _,data in model.calls:
            self.assertEqual(data['user_reviewed_context'],body['context'])
            self.assertEqual([i['direction'] for i in data['current_intents']],body['directions'])
            self.assertTrue(all(i['can_change_prior_decision'] for i in data['current_intents']))
            self.assertTrue(all(not i['permits_invented_details'] for i in data['current_intents']))

    def test_role_conflict_can_be_reported(self):
        checks={'checks':[{'reply_index':0,'type':'role_conflict','explanation':'执行者反转','related_message_ids':['m1']}]}
        result=Pipeline(FakeModel(REPLY,checks)).generate(BODY)
        self.assertEqual(result['checks'],checks['checks'])
        self.assertEqual(result['prompt_version'],'v3')
