"""Relé de posiciones para «Compartir con mi compañero». Solo biblioteca estándar.

Cada sala (código de 8 letras) guarda únicamente la última posición de cada móvil, con caducidad, y una marca breve de quien se
va: sin historial y sin
registrar coordenadas en los logs. Todo va por POST con el código en el cuerpo, para que tampoco quede en los registros
de peticiones del alojamiento; solo el «ping» es GET. Almacén: Upstash Redis por su API REST si el entorno trae sus credenciales
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
MIN_TTL, MAX_TTL = 60, 24 * 3600
STALE = 60 * 60  # sin noticias de un móvil en 1 h: no se devuelve (la antigüedad de la posición ya la enseña el cliente)
LEFT_TTL = 10 * 60  # quien se va deja una marca 10 min, para distinguirlo de quien se quedó sin cobertura
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


def _clamped(value, low: float, high: float, digits: int):
    """Velocidad, rumbo y precisión: un dato raro del GPS no invalida la posición, se recorta o se descarta solo."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return round(min(high, max(low, v)), digits) if math.isfinite(v) else None


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
        "acc": _clamped(body.get("acc"), 0, 5000, 1) or 0,
        "spd": _clamped(body.get("spd"), 0, 100, 2),
        "crs": None if _clamped(body.get("crs"), -1e9, 1e9, 1) is None else round(float(body.get("crs")) % 360, 1),
        "fix": int(_clamped(body.get("fix"), 0, 86400, 0) or 0),  # segundos desde la posición GPS: con la pantalla apagada se reenvía la última
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

    def ping(self) -> bool:
        return True

    def put(self, room: str, member: str, value: str, ttl=None) -> None:
        """ttl None: no toca la caducidad de la sala (la marca de quien se va no debe acortarla)."""
        with self.lock:
            exp, members = self.rooms.get(room, (0, {}))
            members[member] = value
            if ttl is not None:
                exp = time.time() + ttl
            elif exp <= time.time():
                exp = time.time() + LEFT_TTL
            self.rooms[room] = (exp, members)

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

    def ping(self) -> bool:
        """Escritura y lectura reales: detecta credenciales caducadas o un token de solo lectura antes de salir al agua."""
        res = self._call("/pipeline", [["SET", KEY + "ping", "1", "EX", "60"], ["GET", KEY + "ping"]])
        return isinstance(res, list) and len(res) == 2 and res[1].get("result") == "1"

    def put(self, room: str, member: str, value: str, ttl=None) -> None:
        cmds = [["HSET", KEY + room, member, value]]
        if ttl is not None:
            cmds.append(["EXPIRE", KEY + room, str(ttl)])
        self._call("/pipeline", cmds)

    def get(self, room: str) -> dict[str, str]:
        res = self._call("", ["HGETALL", KEY + room])
        flat = (res.get("result") if isinstance(res, dict) else None) or []
        return {flat[i]: flat[i + 1] for i in range(0, len(flat) - 1, 2)}

    def delete(self, room: str, *members: str) -> None:
        if members:
            self._call("", ["HDEL", KEY + room, *members])


def rest_credentials(env=os.environ):
    """URL y token REST de Upstash. La integración de Vercel los llama UPSTASH_REDIS_REST_URL/_TOKEN o KV_REST_API_URL/_TOKEN,
    con el prefijo que se elija al conectar el almacén (p. ej. STORAGE_REST_API_URL). Nunca el token de solo lectura."""
    preferred = ["UPSTASH_REDIS_REST_URL", "KV_REST_API_URL"]
    others = sorted(k for k in env if k.endswith(("_REST_API_URL", "_REDIS_REST_URL")) and k not in preferred)
    for url_key in preferred + others:
        url, token = env.get(url_key, ""), env.get(url_key[:-3] + "TOKEN", "")
        if url.startswith("https://") and token:
            return url, token
    return None


def env_hint(env=os.environ) -> list[str]:
    """Solo los nombres (nunca los valores) de las variables que parecen del almacén, para saber qué falta."""
    return sorted(k for k in env if re.search(r"KV|REDIS|UPSTASH", k))[:12]


def store_from_env(env=os.environ):
    creds = rest_credentials(env)
    return UpstashStore(*creds) if creds else None


def room_view(store, room: str, now: float) -> list[dict]:
    """Posiciones vigentes de la sala; borra de paso las caducadas para no guardarlas más de lo necesario."""
    members, out, gone = store.get(room), [], []
    for member, raw in members.items():
        try:
            fix = json.loads(raw)
            fresh = fix["until"] > now * 1000 and (fix.get("left") or fix["at"] > (now - STALE) * 1000)
        except (ValueError, KeyError, TypeError):
            fresh = False
        if fresh:
            out.append({"id": member, "left": True, "at": fix["at"]} if fix.get("left") else dict(fix, id=member))
        else:
            gone.append(member)
    if gone:
        store.delete(room, *gone)
    out.sort(key=lambda f: -f["at"])
    return out[:MAX_MEMBERS]


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    # Copia deliberada de wms_proxy.send_json: cada función de Vercel lleva solo su propio módulo (includeFiles).
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)


def _same_origin(handler: BaseHTTPRequestHandler) -> bool:
    """Solo peticiones de la propia app. El navegador lo declara en Sec-Fetch-Site; si no lo manda, se compara Origin con el host."""
    site = handler.headers.get("Sec-Fetch-Site", "").lower()
    if site:
        return site in ("same-origin", "none")
    origin = handler.headers.get("Origin")
    if not origin:
        return True
    hosts = {handler.headers.get("X-Forwarded-Host", ""), handler.headers.get("Host", "")}
    return urllib.parse.urlsplit(origin).netloc in hosts


def serve_share(handler: BaseHTTPRequestHandler, store) -> None:
    """GET ?ping=1 | POST {op: read|put|leave, room, member?, …}. Las lecturas van por POST para no dejar el código en los logs."""
    try:
        if not _same_origin(handler):
            raise ShareError(403, "Origen no permitido.")
        if handler.command == "GET":
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(handler.path).query)
            if not query.get("ping"):
                raise ShareError(405, "Método no permitido.")
            if store is None:
                return send_json(handler, 503, {"error": NOT_CONFIGURED, "variables": env_hint()})
            if not store.ping():
                raise ShareError(502, "El almacén de posiciones responde, pero no deja escribir. Revisa el token en Vercel.")
            return send_json(handler, 200, {"ok": True, "store": store.kind, "write": True})
        if handler.command != "POST":
            raise ShareError(405, "Método no permitido.")
        if store is None:
            raise ShareError(503, NOT_CONFIGURED)
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
        now, op, room = time.time(), body.get("op"), check_room(body.get("room"))
        if op == "read":
            return send_json(handler, 200, {"now": int(now * 1000), "members": room_view(store, room, now)})
        member = check_member(body.get("member"))
        if op == "put":
            fix, ttl = parse_fix(body, now)
            store.put(room, member, json.dumps(fix, separators=(",", ":")), ttl)
            # La respuesta trae ya la sala: una sola petición sirve de latido y de lectura.
            return send_json(handler, 200, {"ok": True, "until": fix["until"], "now": int(now * 1000),
                                            "members": [m for m in room_view(store, room, now) if m["id"] != member]})
        if op == "leave":
            # Una marca breve en vez de borrar: los demás distinguen «ha dejado de compartir» de «sin cobertura».
            mark = {"left": 1, "at": int(now * 1000), "until": int((now + LEFT_TTL) * 1000)}
            store.put(room, member, json.dumps(mark, separators=(",", ":")), None)
            return send_json(handler, 200, {"ok": True})
        raise ShareError(400, "Operación no válida.")
    except ShareError as exc:
        send_json(handler, exc.status, {"error": exc.message})
