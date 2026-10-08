"""Offline checks: no requests to map providers, GitHub or hosting services."""
from __future__ import annotations
import json
import struct
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import build
import server
from wms_proxy import build_url, RestrictedRedirect

ROOT = Path(__file__).resolve().parents[1]

class BuildTests(unittest.TestCase):
    def test_html_is_current(self):
        self.assertEqual((ROOT / 'index.html').read_text(encoding='utf-8'), build.render())

    def test_manifest_icons(self):
        data = json.loads((ROOT / 'manifest.webmanifest').read_text())
        self.assertEqual(data['scope'], './')
        self.assertEqual(data['start_url'], './')
        for name, size in [('apple-touch-icon.png', 180), ('icon-192.png', 192), ('icon-512.png', 512)]:
            image = (ROOT / name).read_bytes()
            self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', image[16:24]), (size, size))

    def test_context_and_privacy_files(self):
        self.assertTrue((ROOT / 'AGENTS.md').exists())
        self.assertTrue((ROOT / 'SIGUIENTE_PASO_CODEX.md').exists())
        ignored = (ROOT / '.gitignore').read_text()
        for term in ['.env', '.vercel/', 'backups/', 'Orellana_*.json']:
            self.assertIn(term, ignored)

class QuietHandler(server.Handler):
    def log_message(self, *args):
        pass

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)

    def test_health(self):
        with urllib.request.urlopen(self.base + '/api/health', timeout=3) as response:
            data = json.load(response)
            self.assertEqual(data['app'], 'orellana-atlas')
            self.assertEqual(data['version'], '0.6')
            self.assertTrue(data['proxy'])
            self.assertFalse(data['lan'])

    def test_only_public_assets(self):
        for path in server.STATIC:
            with self.subTest(path=path):
                with urllib.request.urlopen(self.base + path, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                    self.assertGreater(len(response.read()), 0)

    def test_private_files_and_directories_not_served(self):
        for path in ['/server.py', '/wms_proxy.py', '/README.md', '/.env', '/.git/config',
                     '/tests/', '/app.js', '/..%2fREADME.md', '/%2e%2e/etc/passwd']:
            with self.subTest(path=path):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(self.base + path, timeout=3)
                self.assertEqual(error.exception.code, 404)

    def test_head_respects_allowlist(self):
        req = urllib.request.Request(self.base + '/index.html', method='HEAD')
        with urllib.request.urlopen(req, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b'')
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(self.base + '/.env', method='HEAD'), timeout=3)
        self.assertEqual(error.exception.code, 404)

    def test_arbitrary_proxy_target_rejected_without_network(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.base + '/api/wms?source=external&url=http://127.0.0.1/', timeout=3)
        self.assertEqual(error.exception.code, 400)

class ProxyTests(unittest.TestCase):
    def query(self, **kwargs):
        params = dict(source='pnoa', SERVICE='WMS', REQUEST='GetMap', VERSION='1.3.0',
                      LAYERS='OI.OrthoimageCoverage', STYLES='', FORMAT='image/png',
                      WIDTH='512', HEIGHT='512', CRS='EPSG:3857', BBOX='-610000,4700000,-600000,4710000')
        params.update(kwargs)
        return urllib.parse.urlencode(params)

    def test_valid_getmap(self):
        url, operation = build_url(self.query())
        self.assertTrue(url.startswith('https://www.ign.es/wms-inspire/pnoa-ma?'))
        self.assertEqual(operation, 'getmap')

    def test_capabilities(self):
        _, op = build_url('source=caminos&SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0')
        self.assertEqual(op, 'getcapabilities')
        _, operation = build_url('source=flight45&SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0')
        self.assertEqual(operation, 'getcapabilities')

    def test_invalid_parameters(self):
        for change in [dict(source='external'), dict(endpoint='99'), dict(REQUEST='GetFeatureInfo'),
                       dict(CRS='EPSG:4326'), dict(WIDTH='100000'), dict(BBOX='nan,1,2,3'),
                       dict(BBOX='5,6,1,2'), dict(url='https://localhost/')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_url(self.query(**change))

    def test_capabilities_rejects_map_params(self):
        with self.assertRaises(ValueError):
            build_url('source=pnoa&SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0&LAYERS=x')

    def test_proxy_only_serves_images_for_getmap(self):
        import wms_proxy
        class H:
            def __init__(self, path):
                self.path, self.status, self.headers, self.body = path, None, {}, b''
                self.wfile = self
            def send_response(self, code): self.status = code
            def send_header(self, k, v): self.headers[k] = v
            def end_headers(self): pass
            def write(self, b): self.body += b
        q = '/api/wms?' + ProxyTests.query(self)
        with patch('wms_proxy.fetch_wms', return_value=(b'<html><script>x</script></html>', 'text/html')):
            h = H(q); wms_proxy.serve_wms(h)
        self.assertEqual(h.status, 502)
        self.assertNotIn(b'<script>', h.body)
        with patch('wms_proxy.fetch_wms', return_value=(b'\x89PNG', 'image/png; charset=binary')):
            h = H(q); wms_proxy.serve_wms(h)
        self.assertEqual((h.status, h.headers['Content-Type']), (200, 'image/png'))
        self.assertIn('sandbox', h.headers['Content-Security-Policy'])
        with patch('wms_proxy.fetch_wms', return_value=(b'<WMS_Capabilities/>', 'text/html')):
            h = H('/api/wms?source=pnoa&SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0'); wms_proxy.serve_wms(h)
        self.assertEqual(h.headers['Content-Type'], 'application/xml; charset=utf-8')

    def test_duplicate_params(self):
        for suffix in ['&WIDTH=12', '&width=12']:
            with self.assertRaises(ValueError):
                build_url(self.query() + suffix)

    def test_redirect_safety(self):
        redirect = RestrictedRedirect()
        req = urllib.request.Request('https://www.ign.es/wms-inspire/pnoa-ma')
        for target in ['http://www.ign.es/maps', 'https://127.0.0.1/maps', 'https://evil.invalid/maps']:
            with self.assertRaises(urllib.error.URLError):
                redirect.redirect_request(req, None, 302, 'Found', {}, target)

class LanTests(unittest.TestCase):
    def test_only_private_addresses_are_shown(self):
        with patch('server.socket.socket', side_effect=OSError), patch('server.socket.getaddrinfo', return_value=[
            (2, 1, 6, '', ('127.0.0.1', 0)), (2, 1, 6, '', ('192.168.1.4', 0)),
            (2, 1, 6, '', ('192.168.1.4', 0)), (2, 1, 6, '', ('203.0.113.2', 0)),
        ]):
            self.assertEqual(server.lan_addresses(), ['192.168.1.4'])

if __name__ == '__main__':
    unittest.main()
