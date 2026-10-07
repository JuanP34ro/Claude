from http.server import BaseHTTPRequestHandler
from wms_proxy import send_json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, 200, {"app": "orellana-atlas", "version": "0.2", "proxy": True})
