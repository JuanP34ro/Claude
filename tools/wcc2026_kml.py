"""Convierte el KML del mapa del World Carp Classic 2026 (Google My Maps) en wcc2026.js para la capa temporal del concurso.

Uso: python tools/wcc2026_kml.py mapa.kml            (escribe wcc2026.js en la raíz y un informe por pantalla)
Solo biblioteca estándar. Conserva la geometría de la organización tal cual: no simplifica, no inventa esquinas ni zonas.
De los puntos de comisarios solo guarda la posición y el número: sus descripciones llevan nombres de personas.
"""
from __future__ import annotations
import json, re, sys, collections
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {'k': 'http://www.opengis.net/kml/2.2'}
SECTIONS = [('Rippton', 'RIP'), ('Dynamite', 'DYN'), ('PB Products', 'PBP'), ('Nikl Carp Specialist', 'NIK'), ('Chasing | CanFish', 'CHA'),
            ('Powerbaits', 'POW'), ('BoilieLAB', 'BOI'), ('Primitiv', 'PRI'), ('Specimen Baits', 'SPE'), ('Meus', 'MEU'),
            ('The Key Carp Fishing', 'TKC'), ('Trakker', 'TRA'), ('Carp Couture', 'CCO')]
SIDX = {s: i for i, (s, _) in enumerate(SECTIONS)}
ALIAS = {s.lower(): s for s, _ in SECTIONS}
ALIAS.update({'nikl': 'Nikl Carp Specialist', 'chasing': 'Chasing | CanFish', 'specimen': 'Specimen Baits', 'tkc': 'The Key Carp Fishing',
              'carp-couture': 'Carp Couture'})
PEGS_PER_SECTION = 14


def clean(s: str | None) -> str:
    return re.sub(r'\s+', ' ', (s or '').replace('\xa0', ' ')).strip()


def section(name: str | None) -> str | None:
    """Nombre de sector normalizado («PowerBaits», «Chasing | CanFish peg», «MEUS»…) o None."""
    s = clean(name).strip(' +').strip()
    s = re.sub(r'\s*\b(peg|P)\s*$', '', s, flags=re.I).strip()
    return ALIAS.get(s.lower())


CORNER = re.compile(r'(?:(?P<sec>[A-Za-z][A-Za-z |\-]*?)\s*)?(?:\bP|\bpeg\s*)?(?P<peg>\d+)\.(?P<k>\d+)', re.I)


def corner_refs(name: str) -> list[tuple[str, int, int]]:
    """«Chasing | CanFish peg 4.2 + Chasing | CanFish peg 5.1» → [(sector, puesto, esquina), …].
    Admite nombres pegados sin «+» y referencias sin sector, que heredan el sector anterior («Carp Couture 9.1 + 10.4»)."""
    out, last = [], None
    for m in CORNER.finditer(clean(name)):
        raw = re.sub(r'^(P|peg)$', '', (m.group('sec') or '').strip(' +|'), flags=re.I)
        s = section(raw) if raw else None
        if raw and not s:
            raise ValueError(f'sector desconocido en la esquina {name!r}: {raw!r}')
        s = s or last
        if not s:
            raise ValueError(f'esquina sin sector: {name!r}')
        last = s
        out.append((s, int(m.group('peg')), int(m.group('k'))))
    return out


WORD = re.compile(r'\d+\s*-\s*\d+|\d+|[A-Za-z|][A-Za-z|\-]*')
NOISE = {'access', 'self-boat', 'boat', 'to', 'parking', 'turning', 'point', 'turn', 'for', 'peg', 'pegs', 'and', 'bp'}


def peg_refs(text: str) -> list[tuple[str, int]]:
    """Puestos citados en el nombre de una ruta, barca o parking: «BP11: Access MEUS 1&2 7-12» → Meus 1, 2 y 7 a 12.
    Los números sin sector toman el último sector nombrado. «Exit Lines 6,7…» habla de rutas, no de puestos."""
    text = re.sub(r'^\s*(BP\d+|\d+)\s*:\s*', '', clean(text))
    if re.match(r'^exit\b', text, re.I):
        return []
    out, cur, words = [], None, []
    for m in WORD.finditer(text):
        t = m.group(0)
        if not t[0].isdigit():
            if t.lower() not in NOISE:
                words.append(t)
            continue
        for i in range(len(words)):
            s = section(' '.join(words[i:]))
            if s:
                cur = s
                break
        words = []
        if cur is None:
            continue
        a, b = (int(x) for x in re.split(r'\s*-\s*', t)) if '-' in t else (int(t), int(t))
        out += [(cur, n) for n in range(a, b + 1) if 1 <= n <= PEGS_PER_SECTION]
    return out


def _name(pm) -> str:
    return clean(pm.findtext('k:name', default='', namespaces=NS))


def _desc(pm) -> str:
    d = pm.findtext('k:description', default='', namespaces=NS) or ''
    d = re.sub(r'<br\s*/?>', '\n', d, flags=re.I)
    d = re.sub(r'<[^>]+>', ' ', d)
    return '\n'.join(clean(x) for x in d.split('\n') if clean(x))


def _coords(el) -> list[list[float]]:
    c = el.find('.//k:coordinates', NS) if el is not None else None
    return [[round(float(v), 6) for v in p.split(',')[:2]] for p in c.text.split()] if c is not None else []


def _kind(pm) -> str | None:
    for t in ('Point', 'LineString', 'Polygon'):
        if pm.find('.//k:' + t, NS) is not None:
            return t
    return None


def _color(pm) -> str | None:
    m = re.search(r'-([0-9A-Fa-f]{6})-', pm.findtext('k:styleUrl', default='', namespaces=NS) or '')
    return '#' + m.group(1).lower() if m else None


def _refs(text: str) -> list[list[int]]:
    return [[SIDX[s], n] for s, n in peg_refs(text)]


def convert(kml: str | bytes) -> tuple[dict, list[str]]:
    root = ET.fromstring(kml)
    doc = root.find('k:Document', NS)
    F = {clean(f.findtext('k:name', default='', namespaces=NS)): f for f in doc.findall('k:Folder', NS)}
    log: list[str] = []
    pegs = []
    for p in F['Pegs'].findall('.//k:Placemark', NS):
        m = re.match(r'^(.*?)\s+peg\s+(\d+)\s*$', _name(p), re.I)
        s = section(m.group(1)) if m else None
        if not s:
            raise ValueError(f'puesto con nombre inesperado: {_name(p)!r}')
        pegs.append([SIDX[s], int(m.group(2))] + _coords(p)[0])
    pegs.sort(key=lambda r: (r[0], r[1]))
    corners: dict[tuple[int, int], dict[int, list[float]]] = collections.defaultdict(dict)
    for p in F['Peg co-ordinates'].findall('.//k:Placemark', NS):
        at = _coords(p)[0]
        for s, n, k in corner_refs(_name(p)):
            corners[(SIDX[s], n)][k] = at
    zones, open_ = [], []
    for s, n, *_ in pegs:
        cs = corners.get((s, n), {})
        pts = [cs[k] for k in sorted(cs)]
        zones.append(pts if len(pts) >= 3 else 0)
        open_.append(pts if len(pts) < 3 else 0)
        if len(pts) < 3:
            log.append(f'zona sin cerrar: {SECTIONS[s][0]} {n} ({len(pts)} esquina(s) con su nombre)')
    borders = [_coords(p) for p in F['Borders'].findall('.//k:Placemark', NS)]
    areas = [{'kind': 'local' if 'local' in _name(p).lower() else 'no', 'pts': _coords(p.find('.//k:outerBoundaryIs', NS))}
             for p in F['NO fishing zone'].findall('.//k:Placemark', NS)]
    chan = [_coords(p) for p in F['Boat chanel'].findall('.//k:Placemark', NS)]
    routes, turns = [], []
    for p in F['Access routes'].findall('.//k:Placemark', NS):
        name, desc = _name(p), _desc(p)
        item = {'name': name, 'desc': desc, 'pegs': _refs(name)}
        if _kind(p) == 'LineString':
            m = re.match(r'^(\d+)\s*:', name)
            item.update(num=m.group(1) if m else '', color=_color(p) or '#e2c587', pts=_coords(p))
            routes.append(item)
        else:
            item['at'] = _coords(p)[0]
            turns.append(item)
    boats = []
    for p in F['Transportation points'].findall('.//k:Placemark', NS):
        if not _name(p):
            log.append('punto de barca sin nombre: omitido')
            continue
        boats.append({'name': _name(p), 'desc': _desc(p), 'at': _coords(p)[0], 'pegs': _refs(_name(p))})
    parks = [{'name': _name(p), 'desc': _desc(p), 'at': _coords(p)[0], 'pegs': _refs(_name(p))}
             for p in F['Car parking location'].findall('.//k:Placemark', NS)]
    marshal = []
    for p in F['Marshaling points'].findall('.//k:Placemark', NS):
        m = re.search(r'(\d+)\s*$', _name(p))
        marshal.append({'n': int(m.group(1)) if m else 0, 'at': _coords(p)[0]})
    marshal.sort(key=lambda x: x['n'])
    venue = []
    for p in F['#26WCC'].findall('.//k:Placemark', NS):
        item = {'name': _name(p)}
        if _kind(p) == 'Polygon':
            item['poly'] = _coords(p.find('.//k:outerBoundaryIs', NS))
        else:
            item['at'] = _coords(p)[0]
        venue.append(item)
    told = collections.Counter((s, n) for coll in (routes, turns, boats, parks) for it in coll for s, n in it['pegs'])
    silent = [f'{SECTIONS[s][0]} {n}' for s, n, *_ in pegs if not told[(s, n)]]
    log.append(f'puestos sin ruta, barca ni parking que los nombre: {len(silent)}' + (f' → {", ".join(silent)}' if silent else ''))
    title = clean(doc.findtext('k:name', default='', namespaces=NS)) or 'WCC 2026'
    data = {'source': f'Mapa «{title}» de Google My Maps (KML)', 'secs': [list(s) for s in SECTIONS], 'pegs': pegs, 'zones': zones,
            'open': open_, 'borders': borders, 'areas': areas, 'chan': chan, 'routes': routes, 'turns': turns, 'boats': boats,
            'parks': parks, 'marshal': marshal, 'venue': venue}
    return data, log


def to_js(data: dict, exported: str) -> str:
    data = dict(data, source=f"{data['source']} exportado el {exported}")
    return ('/* WCC 2026 · capa temporal del concurso (19–24 oct 2026, embalse de Orellana), generada con tools/wcc2026_kml.py\n'
            '   desde el KML del mapa del concurso. Solo geometría y textos de la organización; los comisarios van sin nombres.\n'
            '   Se quita al acabar el concurso: ver «Capa temporal WCC 2026» en README.md. */\n'
            'const WCC2026=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')


def main() -> None:
    import argparse, datetime
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('kml', type=Path)
    ap.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent / 'wcc2026.js')
    ap.add_argument('--exported', default=datetime.date.today().strftime('%d-%m-%Y'), help='fecha de exportación del KML')
    a = ap.parse_args()
    data, log = convert(a.kml.read_bytes())
    a.out.write_text(to_js(data, a.exported), encoding='utf-8')
    print('\n'.join(log))
    print(f'{a.out.name}: {len(data["pegs"])} puestos, {sum(1 for z in data["zones"] if z)} zonas cerradas, {len(data["borders"])} límites, '
          f'{len(data["routes"])} rutas, {len(data["boats"])} barcas, {len(data["parks"])} parkings, {len(data["marshal"])} comisarios')


if __name__ == '__main__':
    main()
