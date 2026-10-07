"""Entrada opcional para Vercel; comparte el mismo proxy restringido."""
from http.server import BaseHTTPRequestHandler
from wms_proxy import serve_wms

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        serve_wms(self)
