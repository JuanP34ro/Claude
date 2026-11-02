"""Formato «cfn-terreno» v1: la tierra de un embalse para el 3D de la app (solo biblioteca estándar).

Acompaña a un paquete «cfn-fondo» (tools/cfn_fondo.py) y comparte su rejilla: relieve de la tierra, volumen (oclusión ambiental),
ortofoto PNOA y vuelo americano de 1956, todo del IGN/CNIG (CC BY 4.0). La app lo importa una vez, lo guarda por archivos en
IndexedDB y el 3D (terra3d.js) lee cada imagen cuando la necesita. No lleva nada de la carta náutica.

Archivo:  b'CFNTERRA' | uint32 LE versión (1) | uint32 LE longitud de la cabecera | cabecera JSON (UTF-8) | archivos seguidos.
Cabecera: type 'cfn-terreno', v 1, name, source, built, origin [X, Y] (vértice noroeste en metros Mercator, igual que el paquete
  de fondo al que pertenece) y grid [ancho, alto] de ese paquete (así la app los empareja), index {dem, photo, rel, ams, ortho,
  filled, demNote}: la parte del índice del visor que describe la tierra (coordenadas del visor en metros sobre el terreno),
  files {nombre: [desplazamiento, longitud]} con desplazamientos relativos al inicio de los archivos.
Nombres: 'dem.png' (relieve a 10 m, decímetros en R/G, B = dato), 'ao.png' (volumen, gris), 'ortho.jpg' (foto de conjunto),
  'rel/X_Y.png' (piezas de relieve a 5,6 m), 'ph/*.wasm' y 'ams/*.wasm' (piezas de foto en WebP una tras otra, con su posición en
  index.photo.bundles e index.ams.groups) y 'ams/atlas.jpg'.
Uso:  python tools/cfn_terreno.py build <carpeta del visor con index.json> <salida.cfnterreno> [--filled AÑO]
      python tools/cfn_terreno.py info <archivo.cfnterreno>
"""
from __future__ import annotations

import argparse
import json
import os
import struct

MAGIC = b"CFNTERRA"
VERSION = 1
SKIP = ("index.json", "solapes.png")   # el índice va en la cabecera; los solapes salen de la carta, no de la tierra
INDEX_KEYS = ("dem", "photo", "rel", "ams", "ortho")


def write_terrain(path, header: dict, files: list[tuple[str, bytes]]) -> dict:
    """Escribe el archivo; devuelve la cabecera con la tabla de archivos."""
    table, off = {}, 0
    for name, data in files:
        if name in table:
            raise ValueError(f"archivo repetido: {name}")
        table[name] = [off, len(data)]
        off += len(data)
    head = dict(header, type="cfn-terreno", v=VERSION, files=table)
    hb = json.dumps(head, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with open(path, "wb") as f:
        f.write(MAGIC + struct.pack("<II", VERSION, len(hb)) + hb)
        for _, data in files:
            f.write(data)
    return head


class Terrain:
    """Lector: cabecera y archivos por nombre."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            if f.read(8) != MAGIC:
                raise ValueError("no es un paquete de terreno (cfn-terreno)")
            ver, hl = struct.unpack("<II", f.read(8))
            if ver != VERSION:
                raise ValueError(f"versión {ver} no admitida")
            self.header = json.loads(f.read(hl).decode("utf-8"))
            self.base = 16 + hl

    def read(self, name: str) -> bytes:
        off, n = self.header["files"][name]
        with open(self.path, "rb") as f:
            f.seek(self.base + off)
            return f.read(n)


def build(src_dir: str, out: str, filled: str | None = None) -> dict:
    idx = json.load(open(os.path.join(src_dir, "index.json"), encoding="utf-8"))
    names = []
    for root, _, fs in os.walk(src_dir):
        for fn in fs:
            rel = os.path.relpath(os.path.join(root, fn), src_dir).replace(os.sep, "/")
            if rel in SKIP or (rel.startswith("L") and rel.endswith(".wasm") and "/" not in rel):
                continue   # las teselas del fondo van en el paquete cfn-fondo
            names.append(rel)
    names.sort()
    files = [(n, open(os.path.join(src_dir, n), "rb").read()) for n in names]
    index = {k: idx[k] for k in INDEX_KEYS if k in idx}
    if filled:
        index["filled"] = filled
    if "dem" in idx:
        index["demNote"] = "Relieve de la tierra: " + idx["dem"].get("source", "MDT05 del IGN (CC BY 4.0)") + "; al tocar la tierra se lee su cota sobre el mar."
    header = dict(name=str(idx.get("name", "Embalse")).split(" · ")[0] + " · terreno IGN", source="IGN/CNIG (CC BY 4.0): MDT05, PNOA y vuelo americano 1956-57", built=idx.get("built", ""),
                  origin=idx["originMerc"], grid=idx["grid"], index=index)
    return write_terrain(out, header, files)


def main() -> None:
    ap = argparse.ArgumentParser(description="Paquete de terreno para el 3D de Carp Field Notes")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("src"); b.add_argument("out"); b.add_argument("--filled")
    i = sub.add_parser("info"); i.add_argument("path")
    a = ap.parse_args()
    if a.cmd == "build":
        h = build(a.src, a.out, a.filled)
        print(f"{a.out}: {len(h['files'])} archivos, {os.path.getsize(a.out) / 1e6:.1f} MB")
    else:
        t = Terrain(a.path)
        print(json.dumps({k: v for k, v in t.header.items() if k not in ("files", "index")}, ensure_ascii=False), len(t.header["files"]), "archivos")


if __name__ == "__main__":
    main()
