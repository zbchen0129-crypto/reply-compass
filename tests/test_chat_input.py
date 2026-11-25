import unittest
from chat_input import normalize
from core import parse_chat,AppError

class PasteTests(unittest.TestCase):
    def test_named_requires_identity(self):
        body={'text':'Mike: Hello\nAlex: Hi'}
        self.assertTrue(normalize(body)['needs_identity'])
        result=normalize(dict(body,self_name='Alex'))
        self.assertEqual(parse_chat(result['canonical'])[0]['speaker'],'other')
    def test_timestamp_and_content_colon_preserved(self):
        r=normalize({'text':'[10:30] Mike: Link: https://example.com\n[10:31] Alex: yes','self_name':'Mike'})
        self.assertIn('Link: https://example.com',r['canonical'])
    def test_single_incoming_with_colon(self):
        r=normalize({'text':'Meet at 4:30?\nBring snacks.','mode':'incoming'})
        self.assertEqual(len(parse_chat(r['canonical'])),1)
        self.assertIn('4:30',r['canonical'])
    def test_standard_no_identity_needed(self):
        self.assertFalse(normalize({'text':'我：hi\n对方：hello'})['needs_identity'])
    def test_ambiguous_group_and_limits_rejected(self):
        for text in ['Hello there','A: hi\nB: hi\nC: hi','x'*18001,'A: hi\n'*241,'https://example.com']:
            with self.assertRaises(AppError):normalize({'text':text})
    def test_invalid_identity(self):
        with self.assertRaises(AppError):normalize({'text':'A: hi\nB: hi','self_name':'Z'})
