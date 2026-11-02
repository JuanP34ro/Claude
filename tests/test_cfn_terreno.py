"""Formato «cfn-terreno»: escribir y leer un paquete de terreno sintético (sin red ni datos reales)."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import cfn_terreno as CT


class CfnTerreno(unittest.TestCase):
    def test_round_trip(self):
        files = [('dem.png', b'\x89PNG fake dem'), ('rel/0_0.png', b'rel'), ('ph/p1_0_0.wasm', b'webp-pieces')]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 't.cfnterreno')
            h = CT.write_terrain(p, dict(name='Sintético · terreno IGN', origin=[-600000.0, 4750000.0], grid=[96, 96], index={'dem': {'w': 2, 'h': 2}}), files)
            self.assertEqual(h['type'], 'cfn-terreno'); self.assertEqual(h['v'], 1)
            t = CT.Terrain(p)
            self.assertEqual(t.header['origin'], [-600000.0, 4750000.0])
            for name, data in files:
                self.assertEqual(t.read(name), data)
            with open(p, 'rb') as f:
                self.assertEqual(f.read(8), CT.MAGIC)

    def test_build_skips_chart_files(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 'site'); os.makedirs(os.path.join(src, 'rel'))
            json.dump({'name': 'Embalse X · fondo según la carta', 'built': '2026-11-02', 'originMerc': [1.0, 2.0], 'grid': [10, 10], 'dem': {'w': 1, 'h': 1, 'source': 'MDT05'}, 'pairs': [1]}, open(os.path.join(src, 'index.json'), 'w'))
            for n, b in (('L0-q0.wasm', b'chart'), ('L4.wasm', b'chart'), ('solapes.png', b'chart'), ('dem.png', b'dem'), ('rel/0_0.png', b'r')):
                open(os.path.join(src, n), 'wb').write(b)
            h = CT.build(src, os.path.join(d, 'o.cfnterreno'), filled='1961')
            self.assertEqual(sorted(h['files']), ['dem.png', 'rel/0_0.png'])   # nada de la carta: ni teselas del fondo ni solapes
            self.assertEqual(h['name'], 'Embalse X · terreno IGN'); self.assertEqual(h['index']['filled'], '1961'); self.assertNotIn('pairs', h['index'])


if __name__ == '__main__':
    unittest.main()
