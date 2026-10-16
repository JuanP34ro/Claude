"""Relé de posiciones para «Compartir con mi compañero». Solo biblioteca estándar.

Cada sala (código de 8 letras) guarda únicamente la última posición de cada móvil, con caducidad: sin historial y sin
registrar coordenadas en los logs. Almacén: Upstash Redis por su API REST si el entorno trae sus credenciales
(UPSTASH_REDIS_REST_URL/TOKEN o KV_REST_API_URL/TOKEN, que añade la integración de Vercel); si no, en memoria, solo
para el servidor local y las pruebas. En Vercel sin credenciales responde 503: no simula un éxito.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

ROOM = re.compile(r"^[A-HJ-NP-Z2-9]{8}$")  # sin 0, O, 1 ni I, que se confunden al dictarlos
MEMBER = re.compile(r"^[a-z2-7]{12}$")
KEY = "cfn:share:"
MAX_BODY = 1024
MIN_TTL, MAX_TTL = 60, 12 * 3600
STALE = 15 * 60  # sin noticias de un móvil en 15 min: no se devuelve
MAX_MEMBERS = 6
NOT_CONFIGURED = "El servidor todavía no tiene activado el almacén para compartir posiciones (Upstash en Vercel)."


class ShareError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _num(value, low: float, high: float, field: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ShareError(400, f"Dato no válido: {field}")
    if not math.isfinite(v) or not low <= v <= high:
        raise ShareError(400, f"Dato fuera de rango: {field}")
    return v


def _opt(value, low: float, high: float, field: str, digits: int):
    return None if value is None else round(_num(value, low, high, field), digits)


def clean_name(value) -> str:
    name = re.sub(r"[\x00-\x1f\x7f<>]", "", str(value or "")).strip()
    return re.sub(r"\s+", " ", name)[:24] or "Compañero"


def check_room(room) -> str:
    room = str(room or "").upper().replace("-", "")
    if not ROOM.match(room):
        raise ShareError(400, "Código de sala no válido.")
    return room


def check_member(member) -> str:
    member = str(member or "")
    if not MEMBER.match(member):
        raise ShareError(400, "Identificador de móvil no válido.")
    return member


def parse_fix(body: dict, now: float) -> tuple[dict, int]:
    """Valida una posición enviada por el móvil. Devuelve lo que se guarda y su caducidad en segundos."""
    until = _num(body.get("until"), 0, 1e14, "until") / 1000
    ttl = int(min(MAX_TTL, max(MIN_TTL, until - now)))
    fix = {
        "name": clean_name(body.get("name")),
        "lat": round(_num(body.get("lat"), -90, 90, "lat"), 6),
        "lon": round(_num(body.get("lon"), -180, 180, "lon"), 6),
        "acc": round(_num(body.get("acc", 0), 0, 5000, "acc"), 1),
        "spd": _opt(body.get("spd"), 0, 100, "spd", 2),
        "crs": _opt(body.get("crs"), 0, 360, "crs", 1),
        "at": int(now * 1000),
        "until": int((now + ttl) * 1000),
    }
    return fix, ttl


class MemoryStore:
    """Almacén en memoria del proceso: servidor local y pruebas."""
    kind = "memory"

    def __init__(self):
        self.rooms: dict[str, tuple[float, dict[str, str]]] = {}
        self.lock = threading.Lock()

    def put(self, room: str, member: str, value: str, ttl: int) -> None:
        with self.lock:
            _, members = self.rooms.get(room, (0, {}))
            members[member] = value
            self.rooms[room] = (time.time() + ttl, members)

    def get(self, room: str) -> dict[str, str]:
        with self.lock:
            exp, members = self.rooms.get(room, (0, {}))
            if exp <= time.time():
                self.rooms.pop(room, None)
                return {}
            return dict(members)

    def delete(self, room: str, *members: str) -> None:
        with self.lock:
            _, current = self.rooms.get(room, (0, {}))
            for m in members:
                current.pop(m, None)


class UpstashStore:
    """Upstash Redis por REST: un hash por sala, con caducidad renovada por el último que escribe."""
    kind = "upstash"

    def __init__(self, url: str, token: str, timeout: float = 5):
        self.url, self.token, self.timeout = url.rstrip("/"), token, timeout

    def _call(self, path: str, payload) -> object:
        req = urllib.request.Request(self.url + path, data=json.dumps(payload).encode("utf-8"), method="POST",
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                data = json.loads(res.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            raise ShareError(502, "El almacén de posiciones no responde. Se reintentará.")
        items = data if isinstance(data, list) else [data]
        if any(isinstance(i, dict) and i.get("error") for i in items):
            raise ShareError(502, "El almacén de posiciones ha rechazado la operación.")
        return data

    def put(self, room: str, member: str, value: str, ttl: int) -> None:
        self._call("/pipeline", [["HSET", KEY + room, member, value], ["EXPIRE", KEY + room, str(ttl)]])

    def get(self, room: str) -> dict[str, str]:
        res = self._call("", ["HGETALL", KEY + room])
        flat = (res.get("result") if isinstance(res, dict) else None) or []
        return {flat[i]: flat[i + 1] for i in range(0, len(flat) - 1, 2)}

    def delete(self, room: str, *members: str) -> None:
        if members:
            self._call("", ["HDEL", KEY + room, *members])


def store_from_env(env=os.environ):
    url = env.get("UPSTASH_REDIS_REST_URL") or env.get("KV_REST_API_URL")
    token = env.get("UPSTASH_REDIS_REST_TOKEN") or env.get("KV_REST_API_TOKEN")
    return UpstashStore(url, token) if url and token else None


def room_view(store, room: str, now: float) -> list[dict]:
    """Posiciones vigentes de la sala; borra de paso las caducadas para no guardarlas más de lo necesario."""
    members, out, gone = store.get(room), [], []
    for member, raw in members.items():
        try:
            fix = json.loads(raw)
            fresh = fix["until"] > now * 1000 and fix["at"] > (now - STALE) * 1000
        except (ValueError, KeyError, TypeError):
            fresh = False
        if fresh:
            out.append(dict(fix, id=member))
        else:
            gone.append(member)
    if gone:
        store.delete(room, *gone)
    out.sort(key=lambda f: -f["at"])
    return out[:MAX_MEMBERS]


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)


def _same_origin(handler: BaseHTTPRequestHandler) -> bool:
    origin = handler.headers.get("Origin")
    if not origin:
        return True
    host = handler.headers.get("X-Forwarded-Host") or handler.headers.get("Host") or ""
    return urllib.parse.urlsplit(origin).netloc == host


def serve_share(handler: BaseHTTPRequestHandler, store) -> None:
    """GET ?ping=1 | GET ?room= | POST {room, member, ...} | DELETE ?room=&member="""
    try:
        if not _same_origin(handler):
            raise ShareError(403, "Origen no permitido.")
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(handler.path).query)
        q = lambda k: (query.get(k) or [""])[0]
        if handler.command == "GET" and q("ping"):
            if store is None:
                raise ShareError(503, NOT_CONFIGURED)
            return send_json(handler, 200, {"ok": True, "store": store.kind})
        if store is None:
            raise ShareError(503, NOT_CONFIGURED)
        now = time.time()
        if handler.command == "GET":
            room = check_room(q("room"))
            return send_json(handler, 200, {"now": int(now * 1000), "members": room_view(store, room, now)})
        if handler.command == "POST":
            try:
                length = int(handler.headers.get("Content-Length") or 0)
            except ValueError:
                raise ShareError(400, "Mensaje no válido.")
            if not 0 <= length <= MAX_BODY:
                raise ShareError(413, "Mensaje demasiado grande.")
            try:
                body = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                raise ShareError(400, "Mensaje no válido.")
            if not isinstance(body, dict):
                raise ShareError(400, "Mensaje no válido.")
            room, member = check_room(body.get("room")), check_member(body.get("member"))
            fix, ttl = parse_fix(body, now)
            store.put(room, member, json.dumps(fix, separators=(",", ":")), ttl)
            return send_json(handler, 200, {"ok": True, "until": fix["until"]})
        if handler.command == "DELETE":
            store.delete(check_room(q("room")), check_member(q("member")))
            return send_json(handler, 200, {"ok": True})
        raise ShareError(405, "Método no permitido.")
    except ShareError as exc:
        send_json(handler, exc.status, {"error": exc.message})
