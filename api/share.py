"""Entrada de Vercel para «Compartir con mi compañero»; la lógica y las validaciones están en share_relay.py."""
from http.server import BaseHTTPRequestHandler
from share_relay import serve_share, store_from_env

STORE = store_from_env()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        serve_share(self, STORE)

    def do_POST(self):
        serve_share(self, STORE)

    def log_message(self, *args):
        # No se registran códigos de sala ni posiciones.
        pass
