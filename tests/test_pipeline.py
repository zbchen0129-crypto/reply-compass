import copy
import json
import unittest
from unittest.mock import patch
from core import AppError, Pipeline, OpenAIModel, parse_chat, CONTEXT, validate

CHAT = '我：Friday is packed.\n对方：Can you help Friday?'
CONTEXT_DATA = {'items':[{'id':'c1','kind':'fact','text':'周五很忙','roles':{'subject':'self','requester':'not_applicable','actor':'not_applicable','recipient':'not_applicable'},'source_message_ids':['m1']}]}
REPLY = {'replies':[{'direction':'拒绝','text':'I cannot help Friday.','introduced_commitments':[], 'assumptions':[], 'evidence_ids':['m1','m2']}]}
BODY = {'chat':CHAT, 'context':CONTEXT_DATA, 'preferences':{'tone':'warm','emoji':False,'language':'English'}, 'directions':['拒绝']}

class FakeModel:
    def __init__(self,*results): self.results=list(results); self.calls=[]
    def call(self,task,data,schema):
        self.calls.append((task,copy.deepcopy(data)))
        result=self.results.pop(0)
        if isinstance(result,Exception): raise result
        return copy.deepcopy(result)

class Tests(unittest.TestCase):
    def test_parser(self):
        self.assertEqual(parse_chat(CHAT)[1]['id'],'m2')
        for text in ['', 'anonymous text', '我：hello', '我：a\n我：b', '我：x\n对方：'+ 'x'*20001]:
            with self.assertRaises(AppError): parse_chat(text)
    def test_extract_sources(self):
        self.assertEqual(Pipeline(FakeModel(CONTEXT_DATA)).extract({'chat':CHAT})['context'],CONTEXT_DATA)
        bad=copy.deepcopy(CONTEXT_DATA);bad['items'][0]['source_message_ids']=['m99']
        with self.assertRaises(AppError) as cm: Pipeline(FakeModel(bad)).extract({'chat':CHAT})
        self.assertEqual(cm.exception.status,502)
    def test_corrected_context_reaches_both_calls(self):
        body=copy.deepcopy(BODY);body['context']['items'][0]['text']='我只能帮十分钟'
        model=FakeModel(REPLY,{'checks':[]})
        result=Pipeline(model).generate(body)
        self.assertEqual(result['check_status'],'completed')
        self.assertTrue(all(c[1]['user_reviewed_context']==body['context'] for c in model.calls))
    def test_invalid_input_never_calls_model(self):
        for field,value in [('directions',['拒绝','拒绝']),('preferences',{'tone':'angry'}),('context',{'items':[dict(CONTEXT_DATA['items'][0],source_message_ids=['missing'])]})]:
            body=copy.deepcopy(BODY);body[field]=value; model=FakeModel()
            with self.assertRaises(AppError):Pipeline(model).generate(body)
            self.assertFalse(model.calls)
    def test_wrong_direction_rejected(self):
        bad=copy.deepcopy(REPLY);bad['replies'][0]['direction']='答应'
        with self.assertRaises(AppError):Pipeline(FakeModel(bad)).generate(BODY)
    def test_checker_failure_is_not_success(self):
        with self.assertRaises(AppError):Pipeline(FakeModel(REPLY,AppError('timeout',504))).generate(BODY)
    def test_invalid_check_index(self):
        check={'checks':[{'reply_index':2,'type':'new_commitment','explanation':'check','related_message_ids':['m1']}]}
        with self.assertRaises(AppError):Pipeline(FakeModel(REPLY,check)).generate(BODY)
    def test_schema_rejects_extra_fields(self):
        with self.assertRaises(AppError): validate({'items':[],'secret':1},CONTEXT)
    def test_no_credentials(self):
        with patch.dict('os.environ',{},clear=True):
            self.assertFalse(OpenAIModel().ready)
            with self.assertRaises(AppError) as cm:OpenAIModel().call('x',{},CONTEXT)
            self.assertEqual(cm.exception.status,503)
    def test_transport_contract(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self, size=-1): return json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(CONTEXT_DATA)}]}]}).encode()
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-key','OPENAI_MODEL':'test-model'}), patch('urllib.request.urlopen',return_value=Response()) as send:
            result=OpenAIModel().call('Extract',{'messages':[]},CONTEXT)
            self.assertEqual(result,CONTEXT_DATA)
            payload=json.loads(send.call_args.args[0].data)
            self.assertFalse(payload['store']);self.assertTrue(payload['text']['format']['strict'])

if __name__=='__main__':unittest.main()
