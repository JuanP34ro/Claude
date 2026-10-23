"""Formato «cfn-fondo» v1: paquete de fondo por teselas para la capa propia de la app (solo biblioteca estándar).

Un paquete junta todas las rejillas de profundidad de un embalse en una pirámide de teselas (Web Mercator, EPSG:3857)
que la app importa una vez y lee tesela a tesela desde IndexedDB; así no hace falta cargar los JSON de cada zona.
El archivo no sabe de dónde salen los datos: lo dice el campo «source» de la cabecera.

Archivo:  b'CFNFONDO' | uint32 LE versión (1) | uint32 LE longitud de la cabecera | cabecera JSON (UTF-8) | blobs seguidos.
Cabecera (claves principales): type 'cfn-fondo', v 1, name, source, built, crs 'EPSG:3857', origin [X, Y] del vértice
  noroeste en metros Mercator, cell (tamaño de la celda base en metros Mercator), cellGround (metros reales aprox.),
  tile (celdas por lado, 256), apron (celdas de solape por lado, 1), levels (número de niveles), grid [ancho, alto] de la
  rejilla base en celdas, bounds [O, S, E, N] en grados, zmax (m), layers [{id, name, ...}], ct {scale}, tiles
  [[nivel, tx, ty, desplazamiento, longitud], ...] con desplazamientos relativos al inicio de los blobs.
Niveles: el nivel L tiene celdas de cell·2^L; la tesela (L, tx, ty) cubre las celdas de nivel L [tx·tile, (tx+1)·tile) ×
  [ty·tile, (ty+1)·tile), contadas desde origin hacia el este y hacia el sur. Cada blob trae n = tile + 2·apron muestras por
  lado (la fila y columna de solape con las vecinas permiten sombrear y trazar curvas sin costuras), de norte a sur y de
  oeste a este; la muestra (i, j) es la celda (tx·tile + i − apron, ty·tile + j − apron).
Blob = gzip(lo | hi | meta | ct), cada parte de n·n bytes:
  dm: profundidad en decímetros (uint16, 65535 = sin dato) codificada por filas como diferencias con la celda anterior
      (la primera de cada fila va tal cual), módulo 65536; lo = byte bajo, hi = byte alto de cada diferencia.
  meta: kind << 5 | id de capa (0..31). kind: 0 sin dato, 1 agua, 2 tierra, 3 sin sondeos en la carta (si lleva dm es un
      relleno para dar continuidad al relieve, nunca una lectura).
  ct: int8, curvatura transversal a la pendiente dividida por ct.scale y recortada a ±127 (negativa en cauces y vaguadas,
      positiva en lomas); 0 fuera del agua.
"""
from __future__ import annotations

import gzip
import json
import struct
from array import array
from typing import Iterable

MAGIC = b"CFNFONDO"
VERSION = 1
NONE = 65535


def delta_encode(dm: Iterable[int], n: int) -> tuple[bytes, bytes]:
    """Diferencias por filas de una rejilla n×n de uint16; devuelve los planos de bytes bajos y altos."""
    vals = array("H", dm)
    if len(vals) != n * n:
        raise ValueError("dm no mide n×n")
    lo = bytearray(n * n)
    hi = bytearray(n * n)
    for j in range(n):
        prev = 0
        base = j * n
        for i in range(n):
            v = vals[base + i]
            d = (v - prev) & 0xFFFF
            prev = v
            lo[base + i] = d & 255
            hi[base + i] = d >> 8
    return bytes(lo), bytes(hi)


def delta_decode(lo: bytes, hi: bytes, n: int) -> array:
    vals = array("H", bytes(2 * n * n))
    for j in range(n):
        prev = 0
        base = j * n
        for i in range(n):
            prev = (prev + lo[base + i] + (hi[base + i] << 8)) & 0xFFFF
            vals[base + i] = prev
    return vals


def encode_tile(dm: Iterable[int], meta: bytes, ct: bytes, n: int, level: int = 9) -> bytes:
    if len(meta) != n * n or len(ct) != n * n:
        raise ValueError("meta y ct deben medir n×n")
    lo, hi = delta_encode(dm, n)
    return gzip.compress(lo + hi + bytes(meta) + bytes(ct), compresslevel=level, mtime=0)


def decode_tile(blob: bytes, n: int) -> tuple[array, bytes, bytes]:
    raw = gzip.decompress(blob)
    if len(raw) != 4 * n * n:
        raise ValueError("la tesela no mide lo que dice la cabecera")
    k = n * n
    return delta_decode(raw[:k], raw[k:2 * k], n), raw[2 * k:3 * k], raw[3 * k:]


def write_pack(path, header: dict, tiles: Iterable[tuple[int, int, int, bytes]]) -> dict:
    """Escribe el paquete; añade a la cabecera type, v e índice de teselas. Devuelve la cabecera escrita."""
    index = []
    blobs = []
    off = 0
    for level, tx, ty, blob in tiles:
        index.append([int(level), int(tx), int(ty), off, len(blob)])
        blobs.append(blob)
        off += len(blob)
    head = dict(header)
    head.update(type="cfn-fondo", v=VERSION, tiles=index)
    hj = json.dumps(head, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with open(path, "wb") as f:
        f.write(MAGIC + struct.pack("<II", VERSION, len(hj)) + hj)
        for b in blobs:
            f.write(b)
    return head


class Pack:
    """Lector: cabecera en memoria y teselas leídas del archivo cuando se piden."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            if f.read(8) != MAGIC:
                raise ValueError("no es un paquete cfn-fondo")
            v, hlen = struct.unpack("<II", f.read(8))
            if v != VERSION:
                raise ValueError(f"versión {v} no admitida")
            self.header = json.loads(f.read(hlen).decode("utf-8"))
        self.base = 16 + hlen
        self.n = int(self.header["tile"]) + 2 * int(self.header.get("apron", 0))
        self.index = {(t[0], t[1], t[2]): (t[3], t[4]) for t in self.header["tiles"]}

    def blob(self, level: int, tx: int, ty: int) -> bytes | None:
        pos = self.index.get((level, tx, ty))
        if not pos:
            return None
        with open(self.path, "rb") as f:
            f.seek(self.base + pos[0])
            return f.read(pos[1])

    def tile(self, level: int, tx: int, ty: int):
        b = self.blob(level, tx, ty)
        return None if b is None else decode_tile(b, self.n)
