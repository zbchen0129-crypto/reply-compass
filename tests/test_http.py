import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from server import Handler
from core import Pipeline

class Socket:
    def __init__(self, request): self.input=io.BytesIO(request);self.output=bytearray()
    def makefile(self,*args): return self.input
    def sendall(self,data): self.output.extend(data)
    def settimeout(self,*args): pass

class HTTPTests(unittest.TestCase):
    def request(self, path, body=None, host='127.0.0.1:8765', origin=None):
        payload=json.dumps(body).encode() if body is not None else b''
        method='POST' if body is not None else 'GET'
        headers=f'{method} {path} HTTP/1.0\r\nHost: {host}\r\n'
        if origin: headers+=f'Origin: {origin}\r\n'
        if body is not None: headers+=f'Content-Type: application/json\r\nContent-Length: {len(payload)}\r\n'
        sock=Socket(headers.encode()+b'\r\n'+payload)
        Handler(sock,('127.0.0.1',0),SimpleNamespace(server_port=8765))
        head,data=bytes(sock.output).split(b'\r\n\r\n',1)
        return int(head.split()[1]),data
    def test_page_and_assets(self):
        for path in ['/','/app.js','/live.js','/style.css']:
            self.assertEqual(self.request(path)[0],200)
    def test_private_files_not_served(self):
        for path in ['/../core.py','/.env','/server.py']:
            self.assertEqual(self.request(path)[0],404)
    def test_cross_origin_blocked(self):
        self.assertEqual(self.request('/api/status',origin='https://example.com')[0],403)
        self.assertEqual(self.request('/api/status',host='evil.test:8765')[0],403)
    def test_missing_credentials_explicit(self):
        with patch.dict('os.environ',{},clear=True):
            status,body=self.request('/api/status');self.assertFalse(json.loads(body)['ready'])
            status,body=self.request('/api/extract',{'chat':'我：Hello\n对方：Hi'})
            self.assertEqual(status,503);self.assertIn('OPENAI_API_KEY',json.loads(body)['error'])
    def test_checker_route_uses_fixed_candidate(self):
        from test_pipeline import BODY, REPLY, FakeModel
        model=FakeModel({'checks':[]})
        with patch.object(Handler,'pipeline',Pipeline(model)):
            status,body=self.request('/api/check',dict(BODY,candidates=REPLY['replies']))
        self.assertEqual(status,200)
        self.assertEqual(len(model.calls),1)
        self.assertEqual(json.loads(body)['check_status'],'completed')

    def test_bad_body(self):
        self.assertEqual(self.request('/api/extract',[])[0],400)
        self.assertEqual(self.request('/api/extract',{'chat':'unlabelled'})[0],400)

if __name__=='__main__':unittest.main()
