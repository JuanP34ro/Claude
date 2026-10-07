#!/usr/bin/env python3
"""Local preview with an explicit, opt-in LAN mode. Python 3.10+; no packages.

python server.py              # Only this computer
python server.py --lan       # Trusted home Wi-Fi; other devices can open the app
No uploads, directory listings or access to arbitrary local files are provided.
"""
from __future__ import annotations
import argparse
import ipaddress
import socket
import threading
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from wms_proxy import send_json, serve_wms

ROOT = Path(__file__).resolve().parent
STATIC = {
    "/": "index.html", "/index.html": "index.html",
    "/manifest.webmanifest": "manifest.webmanifest", "/icon.svg": "icon.svg",
    "/apple-touch-icon.png": "apple-touch-icon.png",
    "/icon-192.png": "icon-192.png", "/icon-512.png": "icon-512.png",
}
PRIVATE_NETWORKS = tuple(ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))

def lan_addresses() -> list[str]:
    """Best effort IPv4 discovery. Does not send any packet to the Internet."""
    candidates = []
    try:
        # UDP connect selects a local route; no send() and no handshake occur.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 9))
            candidates.append(sock.getsockname()[0])
    except OSError:
        pass
    try:
        candidates.extend(info[4][0] for info in socket.getaddrinfo(
            socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM))
    except OSError:
        pass
    found = []
    for candidate in candidates:
        try:
            ip = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if any(ip in net for net in PRIVATE_NETWORKS) and str(ip) not in found:
            found.append(str(ip))
    return found

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/health":
            return send_json(self, 200, {
                "app": "orellana-atlas", "version": "0.3", "proxy": True,
                "lan": bool(getattr(self.server, "lan_enabled", False)),
            })
        if path == "/api/wms":
            return serve_wms(self)
        if path not in STATIC:
            return self.send_error(404, "Recurso no publicado")
        self.path = "/" + STATIC[path]
        super().do_GET()

    def do_HEAD(self):
        path = urllib.parse.urlsplit(self.path).path
        if path not in STATIC:
            return self.send_error(404, "Recurso no publicado")
        self.path = "/" + STATIC[path]
        super().do_HEAD()

    def log_message(self, fmt, *args):
        # Never log the requested WMS coordinates/full upstream URL.
        if "/api/wms" not in (str(args[0]) if args else ""):
            super().log_message(fmt, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Orellana Atlas — vista previa local")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--lan", action="store_true", help="Permitir acceso desde tu red local de confianza")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1024 y 65535")
    host = "0.0.0.0" if args.lan else "127.0.0.1"
    try:
        server = ThreadingHTTPServer((host, args.port), Handler)
    except OSError as exc:
        raise SystemExit(f"No se puede abrir el puerto {args.port}: {exc}. Usa --port con otro puerto.")
    server.lan_enabled = args.lan
    url = f"http://127.0.0.1:{args.port}/"
    print(f"\nORELLANA ATLAS 0.3\nEn este PC: {url}")
    if args.lan:
        print("\nEN TU IPHONE (misma Wi-Fi, Safari):")
        addresses = lan_addresses()
        for ip in addresses:
            print(f"  http://{ip}:{args.port}/")
        if not addresses:
            print(f"No se ha detectado una IP de red privada. Busca la IPv4 de tu PC y usa el puerto {args.port}.")
        print("\nSolo en una red de confianza. Esta vista previa no tiene contraseña.")
        print("En Windows permite Python solo en redes privadas. NO abras puertos en el router.")
        print("HTTP local: puedes marcar puntos a mano; el GPS del móvil requiere HTTPS.")
    print("\nMantén el PC encendido y esta ventana abierta. Ctrl+C para cerrar.\n", flush=True)
    if not args.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
