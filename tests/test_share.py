"""«Compartir con mi compañero»: validaciones, almacenes y servicio /api/share. Sin red externa."""
import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server  # noqa: E402
import share_relay as S  # noqa: E402

ROOM, ME, YOU = "ABCDEFGH", "abcdefghijkm", "zyxwvutsrqpn"


def fix(**over):
    body = {"room": ROOM, "member": ME, "name": "Juan", "lat": 39.0061, "lon": -5.4077, "acc": 6, "spd": 1.2, "crs": 270,
            "until": (time.time() + 3600) * 1000}
    body.update(over)
    return body


class ValidationTests(unittest.TestCase):
    def test_codes(self):
        self.assertEqual(S.check_room("abcd-efgh"), "ABCDEFGH")
        for bad in ("ABCDEFG", "ABCDEFGO", "ABCDEFG1", "", None):
            with self.assertRaises(S.ShareError):
                S.check_room(bad)
        with self.assertRaises(S.ShareError):
            S.check_member("ABCDEFGHIJKL")

    def test_fix_is_validated_rounded_and_capped(self):
        now = time.time()
        f, ttl = S.parse_fix(fix(lat=39.00612345678, until=(now + 99 * 3600) * 1000, name=" <b>Juan</b>\n "), now)
        self.assertEqual(f["lat"], 39.006123)
        self.assertEqual(ttl, S.MAX_TTL)
        self.assertEqual(f["name"], "bJuan/b")
        self.assertEqual(f["at"], int(now * 1000))
        for bad in (dict(lat=91), dict(lon="x"), dict(until=None)):
            with self.assertRaises(S.ShareError):
                S.parse_fix(fix(**bad), now)
        # a GPS glitch in speed, course or accuracy never drops the position: it is clamped or left out
        f, ttl = S.parse_fix(fix(spd=150, crs=-90, acc=-1, until=0), now)
        self.assertEqual((f["spd"], f["crs"], f["acc"]), (100, 270, 0))
        f, _ = S.parse_fix(fix(spd=float("nan"), crs=None, acc="x"), now)
        self.assertEqual((f["spd"], f["crs"], f["acc"]), (None, None, 0))
        self.assertEqual(ttl, S.MIN_TTL)

    def test_room_view_drops_expired_and_stale(self):
        store, now = S.MemoryStore(), time.time()
        good, _ = S.parse_fix(fix(), now)
        old, _ = S.parse_fix(fix(), now - S.STALE - 5)
        store.put(ROOM, ME, json.dumps(good), 3600)
        store.put(ROOM, YOU, json.dumps(old), 3600)
        view = S.room_view(store, ROOM, now)
        self.assertEqual([m["id"] for m in view], [ME])
        self.assertNotIn(YOU, store.get(ROOM), "stale positions are deleted, not kept")

    def test_memory_room_expires(self):
        store = S.MemoryStore()
        store.put(ROOM, ME, "{}", 1)
        with patch("share_relay.time.time", return_value=time.time() + 5):
            self.assertEqual(store.get(ROOM), {})


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class UpstashTests(unittest.TestCase):
    def test_commands_and_parsing(self):
        calls = []

        def fake(req, timeout):
            body = json.loads(req.data)
            calls.append((req.full_url, body, req.headers))
            if "pipeline" not in req.full_url:
                return FakeResponse({"result": [ME, "{}"]})
            return FakeResponse([{"result": "OK"}, {"result": "1"}] if body[0][0] == "SET" else [{"result": 1}, {"result": 1}])
        store = S.UpstashStore("https://example.upstash.io/", "secret")
        with patch("share_relay.urllib.request.urlopen", fake):
            self.assertTrue(store.ping())
            store.put(ROOM, ME, "{}", 120)
            self.assertEqual(store.get(ROOM), {ME: "{}"})
            store.delete(ROOM, ME)
        self.assertEqual(calls[0][1][0][:2], ["SET", S.KEY + "ping"])
        self.assertEqual(calls[1][0], "https://example.upstash.io/pipeline")
        self.assertEqual(calls[1][1], [["HSET", S.KEY + ROOM, ME, "{}"], ["EXPIRE", S.KEY + ROOM, "120"]])
        self.assertEqual(calls[1][2]["Authorization"], "Bearer secret")
        self.assertEqual(calls[3][1], ["HDEL", S.KEY + ROOM, ME])

    def test_ping_detects_a_store_that_cannot_write(self):
        store = S.UpstashStore("https://example.upstash.io", "read-only")
        with patch("share_relay.urllib.request.urlopen", return_value=FakeResponse([{"error": "NOPERM"}, {"result": None}])):
            with self.assertRaises(S.ShareError):
                store.ping()
        with patch("share_relay.urllib.request.urlopen", return_value=FakeResponse([{"result": "OK"}, {"result": None}])):
            self.assertFalse(store.ping())

    def test_store_errors_are_reported_not_hidden(self):
        store = S.UpstashStore("https://example.upstash.io", "t")
        with patch("share_relay.urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            with self.assertRaises(S.ShareError) as e:
                store.get(ROOM)
        self.assertEqual(e.exception.status, 502)
        with patch("share_relay.urllib.request.urlopen", return_value=FakeResponse({"error": "WRONGPASS"})):
            with self.assertRaises(S.ShareError):
                store.get(ROOM)

    def test_env_names(self):
        self.assertIsNone(S.store_from_env({}))
        self.assertEqual(S.store_from_env({"KV_REST_API_URL": "https://a", "KV_REST_API_TOKEN": "t"}).url, "https://a")
        self.assertEqual(S.store_from_env({"UPSTASH_REDIS_REST_URL": "https://b", "UPSTASH_REDIS_REST_TOKEN": "t"}).url, "https://b")
        # custom prefix chosen when connecting the store; the read-only token is never used
        store = S.store_from_env({"STORAGE_REST_API_URL": "https://c", "STORAGE_REST_API_TOKEN": "rw", "STORAGE_REST_API_READ_ONLY_TOKEN": "ro"})
        self.assertEqual((store.url, store.token), ("https://c", "rw"))
        self.assertIsNone(S.store_from_env({"KV_REST_API_URL": "https://d", "KV_REST_API_READ_ONLY_TOKEN": "ro"}))
        self.assertIsNone(S.store_from_env({"REDIS_URL": "rediss://default:x@host:6379"}))

    def test_hint_lists_names_only(self):
        env = {"KV_REST_API_URL": "https://secret-host", "KV_REST_API_TOKEN": "secret", "REDIS_URL": "rediss://x", "PATH": "/bin"}
        self.assertEqual(S.env_hint(env), ["KV_REST_API_TOKEN", "KV_REST_API_URL", "REDIS_URL"])


class Quiet(server.Handler):
    def log_message(self, *args):
        pass


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_port}/api/share"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def call(self, body=None, query="", headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + query, data=data, method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def test_share_roundtrip(self):
        with patch.object(server, "SHARE_STORE", S.MemoryStore()):
            self.assertEqual(self.call(query="?ping=1"), (200, {"ok": True, "store": "memory", "write": True}))
            status, data = self.call(dict(fix(), op="put"))
            self.assertEqual(status, 200)
            self.assertEqual(data["members"], [], "your own position is not echoed back")
            status, data = self.call(dict(fix(member=YOU, name="Pepe", lat=39.0071), op="put"))
            self.assertEqual([m["name"] for m in data["members"]], ["Juan"], "a put answers with the rest of the room")
            status, data = self.call({"room": ROOM, "op": "read"})
            self.assertEqual(status, 200)
            self.assertEqual(sorted(m["name"] for m in data["members"]), ["Juan", "Pepe"])
            self.assertEqual(self.call({"room": ROOM, "member": YOU, "op": "leave"})[0], 200)
            self.assertEqual([m["id"] for m in self.call({"room": ROOM, "op": "read"})[1]["members"]], [ME])

    def test_rejections(self):
        with patch.object(server, "SHARE_STORE", S.MemoryStore()):
            self.assertEqual(self.call(dict(fix(lat=200), op="put"))[0], 400)
            self.assertEqual(self.call(dict(fix(room="0000"), op="put"))[0], 400)
            self.assertEqual(self.call({"room": ROOM, "op": "steal"})[0], 400)
            self.assertEqual(self.call({"x": "y" * 2000})[0], 413)
            self.assertEqual(self.call(query=f"?room={ROOM}")[0], 405, "room codes never travel in a URL")
            same = self.base.split("/api")[0]
            self.assertEqual(self.call({"room": ROOM, "op": "read"}, headers={"Origin": "https://evil.example"})[0], 403)
            self.assertEqual(self.call({"room": ROOM, "op": "read"}, headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"})[0], 403)
            self.assertEqual(self.call({"room": ROOM, "op": "read"}, headers={"Origin": same})[0], 200)
            # the browser's own declaration wins even when the platform rewrites the Host header
            self.assertEqual(self.call({"room": ROOM, "op": "read"}, headers={"Origin": "https://orellana-atlas.vercel.app", "Sec-Fetch-Site": "same-origin"})[0], 200)

    def test_without_store_it_says_so(self):
        with patch.object(server, "SHARE_STORE", None), patch.dict("os.environ", {"REDIS_URL": "rediss://secret"}):
            status, data = self.call(query="?ping=1")
        self.assertEqual(status, 503)
        self.assertIn("Upstash", data["error"])
        self.assertIn("REDIS_URL", data["variables"])
        self.assertNotIn("secret", json.dumps(data))

    def test_vercel_adapter_does_not_log(self):
        sys.path.insert(0, str(ROOT / "api"))
        import share as adapter
        self.assertTrue(hasattr(adapter.handler, "do_POST") and not hasattr(adapter.handler, "do_DELETE"))
        self.assertIsNone(adapter.handler.log_message(None, "%s", "/api/share?room=ABCDEFGH"))


if __name__ == "__main__":
    unittest.main()
