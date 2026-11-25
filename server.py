"""Local-only HTTP API and static frontend. Run: python3 server.py."""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from core import AppError, Pipeline, PROMPT_VERSION
from chat_input import normalize
from local_config import load_env, ConfigError

WEB = Path(__file__).parent / 'web'


class Handler(SimpleHTTPRequestHandler):
    pipeline = Pipeline()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, *args):
        pass  # Never log chat payloads or URLs.

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        super().end_headers()

    def json_response(self, status, data):
        encoded = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def allowed(self):
        port = self.server.server_port
        hosts = {f'localhost:{port}', f'127.0.0.1:{port}'}
        return self.headers.get('Host') in hosts and self.headers.get('Origin', '') in {'', *(f'http://{h}' for h in hosts)}

    def do_GET(self):
        if not self.allowed():
            return self.json_response(403, {'error': '仅允许本机同源访问。'})
        if self.path == '/api/status':
            return self.json_response(200, {'ready': self.pipeline.model.ready, 'provider': 'OpenAI', 'prompt_version': PROMPT_VERSION, 'capabilities': ['checker_v1', 'paste_v1'], 'model': os.environ.get('OPENAI_MODEL', '')})
        if urlsplit(self.path).path not in {'/', '/index.html', '/style.css', '/app.js', '/live.js'}:
            return self.json_response(404, {'error': '路径不存在。'})
        super().do_GET()

    def do_POST(self):
        try:
            if not self.allowed():
                raise AppError('仅允许本机同源访问。', 403)
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise AppError('需要 application/json。', 415)
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                raise AppError('请求长度无效。') from None
            if not 0 < size <= 128000:
                raise AppError('请求为空或超过大小限制。', 413)
            self.connection.settimeout(10)
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise AppError('请求必须是对象。')
            if self.path == '/api/normalize':
                result = normalize(body)
            elif self.path == '/api/extract':
                result = self.pipeline.extract(body)
            elif self.path == '/api/check':
                result = self.pipeline.check(body)
            elif self.path == '/api/generate':
                result = self.pipeline.generate(body)
            else:
                raise AppError('接口不存在。', 404)
            self.json_response(200, result)
        except AppError as exc:
            self.json_response(exc.status, {'error': str(exc)})
        except (ValueError, UnicodeError, TimeoutError):
            self.json_response(400, {'error': '请求无效或读取超时。'})
        except Exception:
            self.json_response(500, {'error': '内部处理失败。请重试。'})


if __name__ == '__main__':
    try:
        load_env()
    except ConfigError as exc:
        raise SystemExit(str(exc)) from None
    server = ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8765'))), Handler)
    print(f'Reply Compass: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
