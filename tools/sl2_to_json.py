"""Sondeos de un registro .sl2 de Lowrance (Elite-4 CHIRP y similares) a JSON. Solo biblioteca estándar.

Formato documentado por la comunidad (opensounder/sounder-log-formats): cabecera de archivo de 8 bytes (formato 2 = .sl2); cada ping
lleva 144 bytes de cabecera y después el eco. Aquí solo se leen las cabeceras: profundidad (pies), posición (Mercator esférico sobre el
radio polar), temperatura, velocidad y tiempo. Mismo criterio que el importador de la app: solo pings con posición GPS, aligerados a uno
cada pocos metros. Uso: python tools/sl2_to_json.py registro.sl2 > sondeos.json
"""
from __future__ import annotations

import json
import math
import struct
import sys

R = 6356752.3142
FEET = 0.3048
HEADER, FRAME = 8, 144
HAS_POSITION, HAS_TEMPERATURE, HAS_SPEED = 0x10, 0x04, 0x02


def lonlat(x: int, y: int) -> tuple[float, float]:
    return x / R * 180 / math.pi, (2 * math.atan(math.exp(y / R)) - math.pi / 2) * 180 / math.pi


def encode(lon: float, lat: float) -> tuple[int, int]:
    """Inverso de lonlat, para pruebas y registros sintéticos."""
    return round(lon * math.pi / 180 * R), round(math.log(math.tan(math.pi / 4 + lat * math.pi / 360)) * R)


def frames(data: bytes):
    """Cabeceras de ping, en orden. Lanza ValueError si no es un .sl2."""
    if len(data) < HEADER:
        raise ValueError("El archivo está vacío.")
    fmt = struct.unpack_from("<H", data, 0)[0]
    if fmt == 3:
        raise ValueError("Es un registro .sl3 (HDS, Elite Ti): de momento solo se leen .sl2.")
    if fmt != 2:
        raise ValueError("No parece un registro de sonda Lowrance (.sl2).")
    pos = HEADER
    while pos + FRAME <= len(data):
        channel, packet = struct.unpack_from("<HH", data, pos + 32)
        if pos + FRAME + packet > len(data):
            break
        depth_ft = struct.unpack_from("<f", data, pos + 64)[0]
        speed, temp, x, y = struct.unpack_from("<ffii", data, pos + 100)
        flags = struct.unpack_from("<H", data, pos + 132)[0]
        t = struct.unpack_from("<I", data, pos + 140)[0]
        lon, lat = lonlat(x, y) if flags & HAS_POSITION else (None, None)
        yield {"channel": channel, "flags": flags, "z": depth_ft * FEET, "lon": lon, "lat": lat,
               "temp": temp if flags & HAS_TEMPERATURE else None, "spd": speed * 1.852 if flags & HAS_SPEED else None, "t": t}
        pos += FRAME + packet


def distance(a, b) -> float:
    """Metros entre dos (lon, lat) para distancias cortas."""
    dx = (b[0] - a[0]) * 111320 * math.cos(math.radians((a[1] + b[1]) / 2))
    dy = (b[1] - a[1]) * 110574
    return math.hypot(dx, dy)


def soundings(data: bytes, min_m: float = 3.0) -> dict:
    pts, last, n_frames = [], None, 0
    zs, temps, ts = [], [], []
    for f in frames(data):
        n_frames += 1
        if f["channel"] not in (0, 1, 2) or f["lon"] is None or not 0 < f["z"] < 300 or abs(f["lat"]) > 85:
            continue
        ll = (f["lon"], f["lat"])
        if not ll[0] and not ll[1]:
            continue
        ts.append(f["t"])
        if last is None or distance(last, ll) >= min_m:
            temp = None if f["temp"] is None else round(f["temp"], 1)
            pts.append([round(ll[0], 6), round(ll[1], 6), round(f["z"], 1), temp, f["t"]])
            last = ll
            zs.append(f["z"])
            if temp is not None:
                temps.append(temp)
    if not pts:
        raise ValueError(f"Se han leído {n_frames} pings pero ninguno trae posición GPS: graba con el GPS de la sonda fijado.")
    return {"n": len(pts), "frames": n_frames, "zmin": round(min(zs), 1), "zmax": round(max(zs), 1),
            "tmin": min(temps) if temps else None, "tmax": max(temps) if temps else None,
            "dur": round((max(ts) - min(ts)) / 1000), "pts": pts}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], "rb") as fh:
        out = soundings(fh.read())
    json.dump(out, sys.stdout, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
