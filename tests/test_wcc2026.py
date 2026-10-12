"""WCC 2026 (capa temporal del concurso): conversor del KML y datos que lleva la app. Sin red."""
import json
import math
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import wcc2026_kml as K  # noqa: E402


def load():
    text = (ROOT / 'wcc2026.js').read_text(encoding='utf-8')
    return json.loads(text[text.index('{'):text.rindex('}') + 1])


def metres(c, o):
    return ((c[0] - o[0]) * 111320 * math.cos(math.radians(o[1])), (c[1] - o[1]) * 110574)


def area(poly):
    pts = [metres(c, poly[0]) for c in poly]
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2


def simple(poly):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    n = len(poly)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(i - j) in (1, n - 1):
                continue
            a, b, c, d = poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]
            if orient(c, d, a) * orient(c, d, b) < 0 and orient(a, b, c) * orient(a, b, d) < 0:
                return False
    return True


class ParserTests(unittest.TestCase):
    def test_corner_names_as_written_in_the_kml(self):
        self.assertEqual(K.corner_refs('Chasing | CanFish peg 4.2 + Chasing | CanFish peg 5.1'),
                         [('Chasing | CanFish', 4, 2), ('Chasing | CanFish', 5, 1)])
        self.assertEqual(K.corner_refs('Rippton 10.3 Rippton 11.2'), [('Rippton', 10, 3), ('Rippton', 11, 2)])
        self.assertEqual(K.corner_refs('Carp Couture 9.1 + 10.4'), [('Carp Couture', 9, 1), ('Carp Couture', 10, 4)])
        self.assertEqual(K.corner_refs('Powerbaits 9.3 + Powerbaits 10.4 + BoilieLAB 7.3 + 9.2 + BoilieLAB 10.3'),
                         [('Powerbaits', 9, 3), ('Powerbaits', 10, 4), ('BoilieLAB', 7, 3), ('BoilieLAB', 9, 2), ('BoilieLAB', 10, 3)])
        self.assertEqual(K.corner_refs('Chasing | CanFish peg 14.2 + PowerBaits 1.1'), [('Chasing | CanFish', 14, 2), ('Powerbaits', 1, 1)])
        self.assertEqual(K.corner_refs('Rippton P1.2 + P2.1'), [('Rippton', 1, 2), ('Rippton', 2, 1)])
        with self.assertRaises(ValueError):
            K.corner_refs('Equipo desconocido 3.1')

    def test_pegs_named_by_routes_boats_and_parkings(self):
        self.assertEqual(K.peg_refs('BP11: Access MEUS 1&2 7-12'), [('Meus', n) for n in (1, 2, 7, 8, 9, 10, 11, 12)])
        self.assertEqual(K.peg_refs('9: Nikl 14 and Chasing | CanFish 1-6'),
                         [('Nikl Carp Specialist', 14)] + [('Chasing | CanFish', n) for n in range(1, 7)])
        self.assertEqual(K.peg_refs('18: Meus 13&14, TKC 1-14, Trakker 1'),
                         [('Meus', 13), ('Meus', 14)] + [('The Key Carp Fishing', n) for n in range(1, 15)] + [('Trakker', 1)])
        self.assertEqual(K.peg_refs('Exit Lines 6,7,8,9 & 17'), [])
        self.assertEqual(K.peg_refs('Parking'), [])

    def test_minimal_kml_keeps_open_zones_open_and_drops_marshal_names(self):
        def pm(name, geom, desc='', style=''):
            return (f'<Placemark><name>{name}</name>' + (f'<description>{desc}</description>' if desc else '')
                    + (f'<styleUrl>{style}</styleUrl>' if style else '') + geom + '</Placemark>')
        pt = lambda x, y: f'<Point><coordinates>{x},{y},0</coordinates></Point>'
        line = lambda *c: '<LineString><coordinates>' + ' '.join(f'{x},{y},0' for x, y in c) + '</coordinates></LineString>'
        poly = lambda *c: '<Polygon><outerBoundaryIs><LinearRing><coordinates>' + ' '.join(f'{x},{y},0' for x, y in c) + '</coordinates></LinearRing></outerBoundaryIs></Polygon>'
        folder = lambda name, *items: f'<Folder><name>{name}</name>{"".join(items)}</Folder>'
        kml = ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
               + folder('Pegs', pm('Meus peg 1', pt(-5.40, 39.00)), pm('Meus peg 2', pt(-5.39, 39.00)))
               + folder('Peg co-ordinates', pm('Meus P1.1', pt(-5.401, 39.001)), pm('Meus 1.2 + Meus 2.1', pt(-5.395, 39.001)),
                        pm('Meus P1.3', pt(-5.395, 39.004)), pm('Meus 1.4 + 2.2', pt(-5.401, 39.004)))
               + folder('Borders', pm('Line 1', line((-5.395, 39.001), (-5.395, 39.004))))
               + folder('NO fishing zone', pm('NO fishing zone', poly((-5.38, 39.0), (-5.37, 39.0), (-5.37, 39.01), (-5.38, 39.0))))
               + folder('Boat chanel', pm('Line 2', line((-5.40, 39.005), (-5.38, 39.005))))
               + folder('Marshaling points', pm('Marshall point 3', pt(-5.41, 39.0), desc='Persona Inventada &amp; Otra Persona'))
               + folder('Access routes', pm('1: Meus 1-2', line((-5.45, 38.99), (-5.40, 39.0)), desc='Line 1 (red)', style='#line-FF0000-1200'))
               + folder('Transportation points', pm('BP1: Access Meus 1&amp;2', pt(-5.399, 39.0), desc='Boat Point 1'), pm('', pt(-5.3, 39.0)))
               + folder('#26WCC', pm('HQ', pt(-5.42, 39.02)))
               + folder('Car parking location', pm('Meus 1-2', pt(-5.402, 38.999)))
               + '</Document></kml>')
        data, log = K.convert(kml)
        self.assertEqual(data['zones'][0], [[-5.401, 39.001], [-5.395, 39.001], [-5.395, 39.004], [-5.401, 39.004]])
        self.assertEqual(data['zones'][1], 0)
        self.assertEqual(data['open'][1], [[-5.395, 39.001], [-5.401, 39.004]])
        self.assertEqual(data['marshal'], [{'n': 3, 'at': [-5.41, 39.0]}])
        self.assertNotIn('Persona', json.dumps(data, ensure_ascii=False))
        self.assertEqual([b['name'] for b in data['boats']], ['BP1: Access Meus 1&2'])
        self.assertEqual(data['routes'][0]['color'], '#ff0000')
        self.assertEqual(data['routes'][0]['pegs'], [[9, 1], [9, 2]])
        self.assertTrue(any('omitido' in line for line in log))
        self.assertIn('const WCC2026=', K.to_js(data, '01-01-2026'))


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.D = load()

    def test_sections_and_pegs(self):
        D = self.D
        self.assertEqual(len(D['secs']), 13)
        self.assertEqual(len(D['pegs']), 182)
        for s in range(13):
            self.assertEqual(sorted(p[1] for p in D['pegs'] if p[0] == s), list(range(1, 15)), D['secs'][s])
        for p in D['pegs']:
            self.assertTrue(-5.6 < p[2] < -5.25 and 38.95 < p[3] < 39.12, p)

    def test_zones_are_the_organisers_corners_never_invented(self):
        D = self.D
        self.assertEqual(len(D['zones']), 182)
        self.assertEqual(len(D['open']), 182)
        closed = [z for z in D['zones'] if z]
        self.assertEqual(len(closed), 161)
        for z, o in zip(D['zones'], D['open']):
            self.assertTrue(bool(z) != bool(o), 'each peg is either closed or open')
            if z:
                self.assertGreaterEqual(len(z), 3)
                self.assertTrue(simple(z), z)
                self.assertTrue(1e4 < area(z) < 6e5, area(z))
            else:
                self.assertIn(len(o), (1, 2))

    def test_no_personal_data(self):
        for m in self.D['marshal']:
            self.assertEqual(set(m), {'n', 'at'})
        text = json.dumps(self.D, ensure_ascii=False)
        self.assertNotRegex(text, r'@|\+\d{6,}|\b\d{9}\b')

    def test_inlined_in_the_page_and_not_published_on_its_own(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(html.count('const WCC2026='), 1)
        ignored = (ROOT / '.vercelignore').read_text(encoding='utf-8').split()
        self.assertIn('wcc2026.js', ignored)
        self.assertIn('tools/', ignored)
        self.assertRegex(html, r'id="wccSection"')


if __name__ == '__main__':
    unittest.main()
