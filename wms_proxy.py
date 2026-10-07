"""Proxy WMS de alcance limitado. Solo IGN/IDEEX; no es un proxy de URL libre.

No envía puntos ni notas. No utiliza claves ni servicios comerciales.
HTTPS verificado, respuesta limitada, timeout y redirecciones restringidas.
"""
from __future__ import annotations
import json
import math
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

SOURCES = {
    "pnoa": ["https://www.ign.es/wms-inspire/pnoa-ma"],
    "raster": ["https://www.ign.es/wms-inspire/mapa-raster"],
    "flight56": ["https://www.ign.es/wms/pnoa-historico"],
    "flight45": ["https://www.ideex.es/CICTEX/ortoVuelo1945", "https://www.ideextremadura.com/CICTEX/ortoVuelo1945"],
    "mtn50": ["https://www.ign.es/wms/primera-edicion-mtn"],
    "minutas": ["https://www.ign.es/wms/primera-edicion-mtn"],
    "badajoz": ["https://www.ideex.es/CICTEX/cartoBA45", "https://www.ideextremadura.com/CICTEX/cartoBA45"],
}
HOSTS = frozenset({"www.ign.es", "ign.es", "www.ideex.es", "ideex.es", "www.ideextremadura.com", "ideextremadura.com", "mapas.ideex.es"})
MAX_BYTES = 8 * 1024 * 1024
_CAPS_CACHE: dict[str, tuple[float, bytes, str]] = {}
_LOCK = threading.Lock()
_GATE = threading.BoundedSemaphore(8)

class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urllib.parse.urlsplit(newurl)
        if u.scheme != "https" or u.hostname not in HOSTS or u.username or u.password or u.port not in (None, 443):
            raise urllib.error.URLError("Redirección fuera de la lista de fuentes permitidas")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_url(query: str) -> tuple[str, str]:
    raw = urllib.parse.parse_qs(query, keep_blank_values=True, max_num_fields=32)
    if any(len(v) != 1 for v in raw.values()):
        raise ValueError("Parámetro duplicado")
    values = {k: v[0] for k, v in raw.items()}
    source = values.pop("source", "")
    if source not in SOURCES:
        raise ValueError("Fuente no permitida")
    try:
        endpoint = int(values.pop("endpoint", "0"))
    except ValueError as exc:
        raise ValueError("Índice de servidor incorrecto") from exc
    if not 0 <= endpoint < len(SOURCES[source]):
        raise ValueError("Servidor no permitido")
    q = {k.upper(): v for k, v in values.items()}
    if len(q) != len(values):
        raise ValueError("Parámetro duplicado")
    allowed = {"SERVICE", "REQUEST", "VERSION", "LAYERS", "STYLES", "FORMAT", "TRANSPARENT", "WIDTH", "HEIGHT", "BBOX", "CRS", "SRS"}
    if set(q) - allowed:
        raise ValueError("Parámetro WMS no permitido")
    if q.get("SERVICE", "").upper() != "WMS":
        raise ValueError("Solo se permite el servicio WMS")
    operation = q.get("REQUEST", "").lower()
    if operation not in {"getmap", "getcapabilities"}:
        raise ValueError("Operación no permitida")
    if q.get("VERSION") not in {"1.1.1", "1.3.0"}:
        raise ValueError("Versión WMS no permitida")
    if operation == "getmap":
        if q.get("FORMAT") not in {"image/png", "image/jpeg"}:
            raise ValueError("Formato de imagen no permitido")
        if q.get("CRS", q.get("SRS")) not in {"EPSG:3857", "EPSG:900913", "EPSG:102100"}:
            raise ValueError("Sistema de referencia no permitido")
        for key in ("WIDTH", "HEIGHT"):
            if not 1 <= int(q.get(key, "0")) <= 2048:
                raise ValueError("Dimensión de imagen fuera del límite")
        bbox = [float(v) for v in q.get("BBOX", "").split(",")]
        if len(bbox) != 4 or any(not math.isfinite(v) or abs(v) > 20037509 for v in bbox):
            raise ValueError("Extensión no válida")
        if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            raise ValueError("Extensión invertida")
        if not q.get("LAYERS") or len(q["LAYERS"]) > 500 or len(q.get("STYLES", "")) > 200:
            raise ValueError("Nombre de capa no válido")
    return SOURCES[source][endpoint] + "?" + urllib.parse.urlencode(q), operation


def fetch_wms(url: str, operation: str) -> tuple[bytes, str]:
    if operation == "getcapabilities":
        with _LOCK:
            cached = _CAPS_CACHE.get(url)
            if cached and time.monotonic() - cached[0] < 3600:
                return cached[1], cached[2]
    if not _GATE.acquire(timeout=3):
        raise TimeoutError("Demasiadas peticiones simultáneas; reintenta en unos segundos")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OrellanaAtlas/0.2 (personal WMS viewer)", "Accept": "image/png,image/jpeg,text/xml,application/xml;q=0.9,*/*;q=0.5"})
        opener = urllib.request.build_opener(RestrictedRedirect())
        with opener.open(req, timeout=16) as response:
            data = response.read(MAX_BYTES + 1)
            content_type = response.headers.get("Content-Type", "application/octet-stream")
        if len(data) > MAX_BYTES:
            raise ValueError("La respuesta supera el límite de 8 MB")
        if operation == "getcapabilities":
            if b"<" not in data[:300]:
                raise ValueError("El proveedor no devuelve un catálogo XML")
            with _LOCK:
                if len(_CAPS_CACHE) > 30:
                    _CAPS_CACHE.clear()
                _CAPS_CACHE[url] = (time.monotonic(), data, content_type)
        return data, content_type
    finally:
        _GATE.release()


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)


def serve_wms(handler: BaseHTTPRequestHandler):
    try:
        url, operation = build_url(urllib.parse.urlsplit(handler.path).query)
    except (ValueError, TypeError) as exc:
        send_json(handler, 400, {"error": str(exc)})
        return
    try:
        data, content_type = fetch_wms(url, operation)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        send_json(handler, 502, {"error": "La fuente WMS no respondió correctamente", "detail": str(exc)[:220]})
        return
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "public, max-age=3600" if operation == "getcapabilities" else "public, max-age=300")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    try:
        handler.wfile.write(data)
    except (BrokenPipeError, ConnectionResetError):
        pass
