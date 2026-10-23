"""Formato «cfn-fondo» (paquete del fondo por teselas): paquete sintético para las pruebas y comprobaciones del contrato del archivo.
No contiene datos reales: la cubeta es inventada, junto a Orellana, como la de test_priv_layer."""
import io
import math
import os
import struct
import sys
import tempfile
import unittest
from array import array

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import cfn_fondo as CF  # noqa: E402

R = 6378137.0
GROUND = 1.4
LAT0 = 39.0
CELL = GROUND / math.cos(math.radians(LAT0))
W0, N0 = -5.56, 39.0
X0 = R * math.radians(W0)
Y1 = R * math.log(math.tan(math.pi / 4 + math.radians(N0) / 2))
GRID = 96
TILE = 32
AP = 1
LEVELS = 2
LON = lambda x: math.degrees(x / R)
LAT = lambda y: math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)
SYNTH_BOUNDS = (W0, LAT(Y1 - GRID * CELL), LON(X0 + GRID * CELL), N0)   # [O, S, E, N] de la rejilla sintética


def base_grid(w=GRID, h=GRID):
    """Cubeta de hasta 18 m, tierra en las 12 columnas del este, un bloque sin sondeos al noroeste y un cauce (curvatura negativa) por el centro."""
    dm, meta, ct = [65535] * (w * h), bytearray(w * h), bytearray(w * h)
    cw = w - 12
    for j in range(h):
        for i in range(w):
            k = j * w + i
            if i >= cw:
                dm[k] = 0; meta[k] = (2 << 5) | 1
                continue
            if i < 10 and j < 10:
                dm[k] = 20; meta[k] = (3 << 5) | 1
                continue
            dx = (i - cw / 2) / (cw / 2); dy = (j - h / 2) / (h / 2)
            dm[k] = int(round(max(0.3, 18 * (1 - dx * dx) * (1 - dy * dy)) * 10)); meta[k] = (1 << 5) | 1
            ct[k] = (256 - 100) if abs(j - h / 2) < 2 else 0
    return dm, meta, ct, w, h


def pool(dm, meta, ct, w, h):
    """2×2 → 1 con las mismas reglas que el constructor: mayoría de kind (agua > tierra > sin sondeos), media de dm, media de ct del agua."""
    w2, h2 = w // 2, h // 2
    out_dm, out_meta, out_ct = [65535] * (w2 * h2), bytearray(w2 * h2), bytearray(w2 * h2)
    for j in range(h2):
        for i in range(w2):
            ks = [(2 * j) * w + 2 * i, (2 * j) * w + 2 * i + 1, (2 * j + 1) * w + 2 * i, (2 * j + 1) * w + 2 * i + 1]
            kinds = [meta[k] >> 5 for k in ks]
            counts = {kk: kinds.count(kk) for kk in (1, 2, 3)}
            chosen = 1 if counts[1] and counts[1] >= counts[2] and counts[1] >= counts[3] else 2 if counts[2] and counts[2] >= counts[3] else 3 if counts[3] else 0
            o = j * w2 + i
            if not chosen:
                continue
            sel = [k for k, kk in zip(ks, kinds) if kk == chosen]
            vals = [dm[k] for k in sel if dm[k] != 65535]
            out_dm[o] = 0 if chosen == 2 else int(round(sum(vals) / len(vals))) if vals else 65535
            out_meta[o] = (chosen << 5) | (meta[sel[0]] & 31)
            if chosen == 1:
                cs = [ct[k] - 256 if ct[k] > 127 else ct[k] for k in sel]
                out_ct[o] = int(round(sum(cs) / len(cs))) & 255
    return out_dm, out_meta, out_ct, w2, h2


def tiles_of(level, dm, meta, ct, w, h):
    n = TILE + 2 * AP
    for ty in range((h + TILE - 1) // TILE):
        for tx in range((w + TILE - 1) // TILE):
            tdm, tmeta, tct = [65535] * (n * n), bytearray(n * n), bytearray(n * n)
            inside = False
            for j in range(n):
                for i in range(n):
                    c, r = tx * TILE + i - AP, ty * TILE + j - AP
                    if 0 <= c < w and 0 <= r < h:
                        k = r * w + c; o = j * n + i
                        tdm[o], tmeta[o], tct[o] = dm[k], meta[k], ct[k]
                        if meta[k] and AP <= i < n - AP and AP <= j < n - AP:
                            inside = True
            if inside:
                yield level, tx, ty, CF.encode_tile(tdm, bytes(tmeta), bytes(tct), n)


def synthetic_pack_header():
    return dict(name='Paquete sintético (no es un dato real)', source='Rejilla inventada para la prueba automática', built='2026-10-23', crs='EPSG:3857',
                origin=[X0, Y1], cell=CELL, cellGround=GROUND, lat0=LAT0, tile=TILE, apron=AP, levels=LEVELS, grid=[GRID, GRID], bounds=list(SYNTH_BOUNDS),
                zmax=18.0, layers=[dict(id=1, name='Cubeta sintética')], ct=dict(scale=0.002), kinds={'0': 'sin dato', '1': 'agua', '2': 'tierra', '3': 'sin sondeos'})


def synthetic_pack_bytes():
    dm, meta, ct, w, h = base_grid()
    tiles = list(tiles_of(0, dm, meta, ct, w, h))
    dm1, meta1, ct1, w1, h1 = pool(dm, meta, ct, w, h)
    tiles += list(tiles_of(1, dm1, meta1, ct1, w1, h1))
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'prueba.cfnfondo')
        CF.write_pack(p, synthetic_pack_header(), tiles)
        return open(p, 'rb').read()


class CfnFondoFormat(unittest.TestCase):
    def test_delta_wraps(self):
        n = 3
        vals = [65535, 0, 65535, 1, 2, 65534, 7, 7, 7]
        lo, hi = CF.delta_encode(vals, n)
        self.assertEqual((len(lo), len(hi)), (9, 9))
        self.assertEqual(list(CF.delta_decode(lo, hi, n)), vals, 'las diferencias módulo 65536 vuelven a los valores de partida')

    def test_tile_round_trip(self):
        n = 4
        dm = [int((i * 7919) % 65536) for i in range(n * n)]
        meta = bytes([(1 << 5) | 3] * (n * n))
        ct = bytes([200] * (n * n))
        blob = CF.encode_tile(dm, meta, ct, n)
        d2, m2, c2 = CF.decode_tile(blob, n)
        self.assertEqual((list(d2), m2, c2), (dm, meta, ct))
        with self.assertRaises(ValueError):
            CF.decode_tile(blob, n + 1)

    def test_pack_contract(self):
        data = synthetic_pack_bytes()
        self.assertTrue(data.startswith(b'CFNFONDO'))
        ver, hlen = struct.unpack('<II', data[8:16])
        self.assertEqual(ver, 1)
        self.assertLess(len(data), 120000, 'un paquete de prueba pequeño')
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'p.cfnfondo')
            open(p, 'wb').write(data)
            pk = CF.Pack(p)
            h = pk.header
            self.assertEqual((h['type'], h['v'], h['tile'], h['apron'], h['levels'], h['grid']), ('cfn-fondo', 1, TILE, AP, LEVELS, [GRID, GRID]))
            self.assertEqual(len(h['tiles']), 9 + 4, 'tres por tres teselas en la base y dos por dos en el nivel 1')
            offs = sorted((t[3], t[4]) for t in h['tiles'])
            self.assertEqual(offs[0][0], 0)
            for (a, la), (b, _) in zip(offs, offs[1:]):
                self.assertEqual(a + la, b, 'los blobs van seguidos')
            self.assertEqual(16 + hlen + offs[-1][0] + offs[-1][1], len(data))
            W, S, E, N = h['bounds']
            self.assertTrue(W < E and S < N and abs(E - W) < 0.01)
            # centro de la cubeta: tesela (0,1,1), muestra interior (celda 42, 48) → unos 18 m de fondo, agua, capa 1
            dm, meta, ct = pk.tile(0, 1, 1)
            n = pk.n
            o = (48 - 32 + AP) * n + (42 - 32 + AP)
            self.assertEqual(meta[o] >> 5, 1)
            self.assertEqual(meta[o] & 31, 1)
            self.assertTrue(170 <= dm[o] <= 180, dm[o])
            self.assertEqual(ct[o], 256 - 100, 'curvatura negativa en el cauce')
            # tierra al este y sin sondeos al noroeste
            dm2, meta2, _ = pk.tile(0, 2, 1)
            self.assertEqual(meta2[(16 + AP) * n + (90 - 64 + AP)] >> 5, 2)
            self.assertEqual(dm2[(16 + AP) * n + (90 - 64 + AP)], 0)
            _, meta3, _ = pk.tile(0, 0, 0)
            self.assertEqual(meta3[(2 + AP) * n + (2 + AP)] >> 5, 3)
            self.assertIsNone(pk.tile(1, 5, 5))
            dm1, meta1, _ = pk.tile(1, 0, 0)
            self.assertEqual(meta1[(24 + AP) * n + (21 + AP)] >> 5, 1, 'el nivel 1 conserva el agua del centro')


if __name__ == '__main__':
    unittest.main()
