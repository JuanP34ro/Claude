"""Formato «cfn-capa» (capa propia de fondo): rejilla sintética para las pruebas y comprobaciones del contrato del archivo.
No contiene datos reales: la rejilla es una cubeta inventada junto a Orellana."""
import base64
import json
import struct
import unittest


def synthetic_layer(w=40, h=60, bounds=(-5.56, 38.99, -5.55, 39.0)):
    """Cubeta de hasta 18 m con una franja de tierra al este y una celda sin dato; devuelve el dict del archivo."""
    z = []
    land = []
    for j in range(h):
        for i in range(w):
            if i >= w - 6:
                z.append(0)
                land.append(1)
                continue
            dx = (i - (w - 6) / 2) / ((w - 6) / 2)
            dy = (j - h / 2) / (h / 2)
            z.append(int(round(max(0.3, 18 * (1 - dx * dx) * (1 - dy * dy)) * 10)))
            land.append(0)
    z[2 * w + 2] = 65535
    bits = bytearray((len(land) + 7) // 8)
    for k, v in enumerate(land):
        if v:
            bits[k >> 3] |= 0x80 >> (k & 7)
    return {
        "type": "cfn-capa", "v": 1, "name": "Prueba sintética (no es un dato real)",
        "source": "Rejilla inventada para la prueba automática", "bounds": list(bounds), "w": w, "h": h,
        "z": base64.b64encode(struct.pack(f"<{w * h}H", *z)).decode("ascii"),
        "land": base64.b64encode(bytes(bits)).decode("ascii"),
    }


def synthetic_layer_bytes(**kw):
    return json.dumps(synthetic_layer(**kw)).encode("utf-8")


class PrivLayerFormat(unittest.TestCase):
    def test_contract(self):
        d = synthetic_layer()
        self.assertEqual((d["type"], d["v"]), ("cfn-capa", 1))
        w, h = d["w"], d["h"]
        raw = base64.b64decode(d["z"])
        self.assertEqual(len(raw), w * h * 2, "z es uint16 little-endian, una celda por valor")
        vals = struct.unpack(f"<{w * h}H", raw)
        self.assertEqual(vals[2 * w + 2], 65535, "65535 marca «sin dato»")
        self.assertTrue(all(v == 65535 or v <= 180 for v in vals), "decímetros, nunca más de 18 m aquí")
        bits = base64.b64decode(d["land"])
        self.assertGreaterEqual(len(bits), (w * h + 7) // 8)
        land = [(bits[k >> 3] >> (7 - (k & 7))) & 1 for k in range(w * h)]
        self.assertEqual(sum(land), 6 * h, "la franja de tierra ocupa seis columnas")
        W, S, E, N = d["bounds"]
        self.assertTrue(W < E and S < N and abs(N) < 85)
        self.assertLess(len(json.dumps(d)), 20000, "una rejilla de prueba pequeña")


if __name__ == "__main__":
    unittest.main()
