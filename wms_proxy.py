"""Proxy WMS de alcance limitado. Solo IGN/IDEEX; no es un proxy de URL libre.

No envía puntos ni notas. No utiliza claves ni servicios comerciales.
HTTPS verificado, respuesta limitada, timeout y redirecciones restringidas.
Si un servidor oficial falla o tarda, la misma petición se repite en los otros
servidores oficiales de esa fuente (solo los de la lista), dentro de un tiempo máximo.
"""
from __future__ import annotations
import http.client
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
    "flight45": ["https://www.ideex.es/CICTEX/ortoVuelo1945", "https://www.ideextremadura.com/CICTEX/ortoVuelo1945", "https://mapas.ideex.es/CICTEX/ortoVuelo1945"],
    "mtn50": ["https://www.ign.es/wms/primera-edicion-mtn"],
    "minutas": ["https://www.ign.es/wms/primera-edicion-mtn"],
    "badajoz": ["https://www.ideex.es/CICTEX/cartoBA45", "https://www.ideextremadura.com/CICTEX/cartoBA45", "https://mapas.ideex.es/CICTEX/cartoBA45"],
    "caminos": ["https://mapas.ideex.es/CICTEX/catalogoCaminosPublicos", "https://www.ideex.es/CICTEX/catalogoCaminosPublicos", "https://www.ideextremadura.com/CICTEX/catalogoCaminosPublicos"],
}
HOSTS = frozenset({"www.ign.es", "ign.es", "www.ideex.es", "ideex.es", "www.ideextremadura.com", "ideextremadura.com", "mapas.ideex.es"})
MAX_BYTES = 8 * 1024 * 1024
MAX_SECONDS = 26  # tiempo total por petición; Vercel corta la función a los 30 s
FETCH_ERRORS = (urllib.error.URLError, TimeoutError, ValueError, OSError, http.client.HTTPException)
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
    if operation == "getcapabilities" and set(q) - {"SERVICE", "REQUEST", "VERSION"}:
        raise ValueError("GetCapabilities solo admite SERVICE, REQUEST y VERSION")
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


def candidates(url: str) -> list[str]:
    """La misma petición en los servidores oficiales de su fuente, empezando por el pedido.

    Con un solo servidor se permite un segundo intento al mismo (útil ante un corte puntual)."""
    base, _, query = url.partition("?")
    for bases in SOURCES.values():
        if base in bases:
            i = bases.index(base)
            ordered = bases[i:] + bases[:i]
            return [b + "?" + query for b in ordered] if len(ordered) > 1 else [url, url]
    return [url]


def _fetch_once(url: str, timeout: float) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "OrellanaAtlas/0.6 (personal WMS viewer)", "Accept": "image/png,image/jpeg,text/xml,application/xml;q=0.9,*/*;q=0.5"})
    opener = urllib.request.build_opener(RestrictedRedirect())
    with opener.open(req, timeout=timeout) as response:
        data = response.read(MAX_BYTES + 1)
        content_type = response.headers.get("Content-Type", "application/octet-stream")
    if len(data) > MAX_BYTES:
        raise ValueError("La respuesta supera el límite de 8 MB")
    return data, content_type


def fetch_wms(url: str, operation: str) -> tuple[bytes, str]:
    if operation == "getcapabilities":
        with _LOCK:
            cached = _CAPS_CACHE.get(url)
            if cached and time.monotonic() - cached[0] < 3600:
                return cached[1], cached[2]
    started = time.monotonic()
    if not _GATE.acquire(timeout=12):
        raise TimeoutError("Demasiadas peticiones simultáneas; reintenta en unos segundos")
    try:
        if operation == "getcapabilities":
            data, content_type = _fetch_once(url, 16)
            if b"<" not in data[:300]:
                raise ValueError("El proveedor no devuelve un catálogo XML")
            with _LOCK:
                if len(_CAPS_CACHE) > 30:
                    _CAPS_CACHE.clear()
                _CAPS_CACHE[url] = (time.monotonic(), data, content_type)
            return data, content_type
        last: Exception | None = None
        for candidate in candidates(url):
            remaining = MAX_SECONDS - (time.monotonic() - started)
            if remaining < 4:
                break
            try:
                data, content_type = _fetch_once(candidate, min(15.0, remaining))
                kind = content_type.split(";")[0].strip().lower()
                if kind not in {"image/png", "image/jpeg"}:
                    # Un error del servidor en XML/HTML con estado 200: se prueba el siguiente servidor.
                    raise ValueError(f"La fuente no devolvió una imagen ({kind[:40]})")
                return data, content_type
            except FETCH_ERRORS as exc:
                last = exc
        raise last or TimeoutError("Sin tiempo para reintentar la fuente")
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
    try:
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
        pass  # el navegador ya no espera esta respuesta (dejó de necesitar la imagen)


def serve_wms(handler: BaseHTTPRequestHandler):
    try:
        url, operation = build_url(urllib.parse.urlsplit(handler.path).query)
    except (ValueError, TypeError) as exc:
        send_json(handler, 400, {"error": str(exc)})
        return
    try:
        data, content_type = fetch_wms(url, operation)
    except FETCH_ERRORS as exc:
        send_json(handler, 502, {"error": "La fuente WMS no respondió correctamente", "detail": str(exc)[:220]})
        return
    # Nunca se reenvía el tipo de contenido del proveedor tal cual: un error HTML/XML con
    # parámetros reflejados no debe servirse desde el origen de la app.
    if operation == "getmap":
        kind = content_type.split(";")[0].strip().lower()
        if kind not in {"image/png", "image/jpeg"}:
            send_json(handler, 502, {"error": "La fuente WMS no devolvió una imagen", "detail": kind[:60]})
            return
        content_type, cache = kind, "public, max-age=604800, s-maxage=604800, stale-while-revalidate=2592000"
    else:
        content_type, cache = "application/xml; charset=utf-8", "public, max-age=3600, s-maxage=86400"
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", cache)
    handler.send_header("Content-Security-Policy", "default-src 'none'; sandbox")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    try:
        handler.wfile.write(data)
    except (BrokenPipeError, ConnectionResetError):
        pass
