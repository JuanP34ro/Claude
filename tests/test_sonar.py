"""Lectura de registros .sl2 de Lowrance: registro sintético con posiciones conocidas, aligerado y rechazos."""
import importlib.util
import math
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sl2_to_json", ROOT / "tools" / "sl2_to_json.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def frame(channel=0, z_m=5.0, lon=None, lat=None, temp=None, spd=None, t=0, packet=16):
    """Un ping con la misma disposición que escribe la sonda (cabecera de 144 bytes + eco)."""
    head = bytearray(144)
    struct.pack_into("<HH", head, 32, channel, packet)
    struct.pack_into("<f", head, 64, z_m / S.FEET)
    flags = 0
    if lon is not None:
        x, y = S.encode(lon, lat)
        struct.pack_into("<ii", head, 108, x, y)
        flags |= S.HAS_POSITION
    if temp is not None:
        struct.pack_into("<f", head, 104, temp)
        flags |= S.HAS_TEMPERATURE
    if spd is not None:
        struct.pack_into("<f", head, 100, spd / 1.852)
        flags |= S.HAS_SPEED
    struct.pack_into("<H", head, 132, flags)
    struct.pack_into("<I", head, 140, t)
    return bytes(head) + bytes(packet)


def synthetic_sl2(n=200, step_m=1.0, lon0=-5.4068, lat0=39.0064, bearing=60.0):
    """Un recorrido recto de n pings a 1 s, con profundidad que crece de 2 a 12 m, temperatura 19,5 °C y eco de relleno."""
    out = bytearray(struct.pack("<HHHH", 2, 1, 3200, 0))
    for i in range(n):
        d = i * step_m
        lat = lat0 + d * math.cos(math.radians(bearing)) / 110574
        lon = lon0 + d * math.sin(math.radians(bearing)) / (111320 * math.cos(math.radians(lat0)))
        out += frame(channel=0 if i % 2 == 0 else 2, z_m=2 + 10 * i / max(1, n - 1), lon=lon, lat=lat, temp=19.5, spd=3.6, t=i * 1000)
    return bytes(out)


class Sl2Tests(unittest.TestCase):
    def test_position_roundtrip(self):
        for lon, lat in ((-5.4068, 39.0064), (12.38, 59.05), (0.0, 0.0), (-73.98, -33.4)):
            x, y = S.encode(lon, lat)
            lon2, lat2 = S.lonlat(x, y)
            self.assertAlmostEqual(lon, lon2, places=5)
            self.assertAlmostEqual(lat, lat2, places=5)

    def test_synthetic_log_is_read_and_thinned(self):
        data = synthetic_sl2()
        out = S.soundings(data, min_m=3.0)
        self.assertEqual(out["frames"], 200)
        self.assertTrue(50 <= out["n"] <= 70, out["n"])   # roughly one every 3 m of a 199 m line (positions are quantised to the metre)
        self.assertEqual((out["zmin"], out["zmax"]), (2.0, 12.0))
        self.assertEqual((out["tmin"], out["tmax"]), (19.5, 19.5))
        self.assertEqual(out["dur"], 199)
        lon, lat, z, temp, t = out["pts"][0]
        self.assertAlmostEqual(lon, -5.4068, places=4)
        self.assertAlmostEqual(lat, 39.0064, places=4)
        self.assertEqual((z, temp, t), (2.0, 19.5, 0))
        self.assertTrue(all(0 < p[2] <= 12 for p in out["pts"]))

    def test_frames_without_position_or_depth_are_skipped(self):
        data = struct.pack("<HHHH", 2, 1, 3200, 0) + frame(z_m=4.0) + frame(z_m=0.0, lon=-5.4, lat=39.0) + frame(channel=5, z_m=4.0, lon=-5.4, lat=39.0)
        with self.assertRaises(ValueError):
            S.soundings(data)
        data += frame(z_m=4.0, lon=-5.4, lat=39.0)
        self.assertEqual(S.soundings(data)["n"], 1)

    def test_other_formats_are_refused(self):
        with self.assertRaises(ValueError):
            S.soundings(struct.pack("<HHHH", 3, 1, 3200, 0) + bytes(200))
        with self.assertRaises(ValueError):
            S.soundings(b"GIF89a" + bytes(200))
        with self.assertRaises(ValueError):
            S.soundings(b"")

    def test_truncated_tail_is_ignored(self):
        data = synthetic_sl2(n=10)[:-7]
        self.assertEqual(S.soundings(data, min_m=0)["frames"], 9)


if __name__ == "__main__":
    unittest.main()
