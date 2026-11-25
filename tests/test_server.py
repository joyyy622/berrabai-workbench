"""Exercise the real HTTP handlers using a disposable database and mocked AI."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(server, 'DB', Path(cls.temp.name) / 'test.sqlite3')
        cls.password_patch = patch.object(server, 'ADMIN_PASSWORD', 'synthetic-test-password')
        cls.db_patch.start()
        cls.password_patch.start()
        server.init()
        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        cls.password_patch.stop()
        cls.db_patch.stop()
        server.SESSIONS.clear()
        cls.temp.cleanup()

    def request(self, method, path, data=None, cookie=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port, timeout=5)
        headers = {'Content-Type': 'application/json'}
        if cookie:
            headers['Cookie'] = cookie
        connection.request(method, path, json.dumps(data) if data is not None else None, headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def login(self):
        status, headers, body = self.request('POST', '/api/login', {'password':'synthetic-test-password'})
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        return headers['Set-Cookie'].split(';', 1)[0]

    def test_business_endpoints_require_login(self):
        for method, path, data in [('GET','/api/business/state',None),('POST','/api/business/state',{}),('POST','/api/business/feeds',{}),('POST','/api/business/analyze',{})]:
            with self.subTest(path=path, method=method):
                self.assertEqual(self.request(method, path, data)[0], 401)
        self.assertEqual(self.request('POST','/api/login',{'password':'wrong'})[0], 401)

    def test_save_conflict_and_logout(self):
        cookie = self.login()
        status, _, body = self.request('GET','/api/business/state',cookie=cookie)
        self.assertEqual(status, 200)
        state = json.loads(body)
        state['state']['events'].append({'id':'synthetic-event','date':'2026-11-25','title':'Test event','note':'','type':'上新'})
        self.assertEqual(self.request('POST','/api/business/state',state,cookie)[0], 200)
        self.assertEqual(self.request('POST','/api/business/state',state,cookie)[0], 400)
        self.assertEqual(self.request('POST','/api/logout',{},cookie)[0], 200)
        self.assertEqual(self.request('GET','/api/business/state',cookie=cookie)[0], 401)

    def test_static_files_and_database_are_separated(self):
        status, _, body = self.request('GET','/')
        self.assertEqual(status, 200)
        self.assertIn('经营灵感室'.encode(), body)
        for path in ['/../berrabai.sqlite3', '/berrabai.sqlite3', '/.env']:
            self.assertEqual(self.request('GET',path)[0], 404)

    def test_analysis_uses_selected_context_and_does_not_call_real_model(self):
        cookie = self.login()
        with patch.object(server, 'ai', return_value='Synthetic analysis') as ai:
            status, _, body = self.request('POST','/api/business/analyze',{'question':'Test question','context':'Synthetic summary'},cookie)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['answer'], 'Synthetic analysis')
            messages = ai.call_args.args[0]
            self.assertIn('Synthetic summary', messages[-1]['content'])
            self.assertIn('Test question', messages[-1]['content'])


if __name__ == '__main__':
    unittest.main()
