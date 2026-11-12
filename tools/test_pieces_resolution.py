import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from cad_processor.models import Wall
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
import numpy as np
import subprocess

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
outline = res['outline']

# 8 door lintels to add
doors_spec = [
    # (name, (x1, y1), (x2, y2), thickness)
    ("Lintel_Door_Bed2", (10100.0, 5812.5), (11600.0, 5812.5), 125.0),
    ("Lintel_Door_Bed3", (11725.0, 5812.5), (13225.0, 5812.5), 125.0),
    ("Lintel_Door_MasterToilet", (14987.5, 5000.0), (14987.5, 5812.5), 125.0),
    ("Lintel_Door_Toilet1", (3512.5, 2200.0), (3512.5, 3012.5), 125.0),
    ("Lintel_Door_Toilet2", (7312.5, 2200.0), (7312.5, 3012.5), 125.0),
    ("Lintel_Door_Entrance", (775.0, 4037.5), (2337.5, 4037.5), 125.0),
    ("Lintel_Door_Bed3Passage", (11662.5, 1125.0), (11662.5, 2187.5), 125.0),
    ("Lintel_Door_Bed3Balcony", (14987.5, 2187.5), (14987.5, 3312.5), 125.0),
]

door_lintel_walls = []
for i, (dname, (x1, y1), (x2, y2), t) in enumerate(doors_spec):
    dx, dy = x2 - x1, y2 - y1
    L = (dx*dx + dy*dy)**0.5
    ux, uy = dx / L, dy / L
    nx, ny = -uy * (t / 2.0), ux * (t / 2.0)
    poly = [
        (round(x1 + nx, 1), round(y1 + ny, 1)),
        (round(x2 + nx, 1), round(y2 + ny, 1)),
        (round(x2 - nx, 1), round(y2 - ny, 1)),
        (round(x1 - nx, 1), round(y1 - ny, 1)),
    ]
    w = Wall(
        id=dname,
        start_point=(x1, y1),
        end_point=(x2, y2),
        length=L,
        thickness=t,
        height=900.0,
        polygon=poly,
        wall_type="interior",
        layer="DOOR_LINTEL",
        base=2100.0,
        kind="lintel",
        opening="door",
    )
    door_lintel_walls.append(w)

all_pieces = CADtoBlenderPipeline._resolve_3d_overlaps(walls + fills + door_lintel_walls)
clean_pieces = [p for p in all_pieces if Polygon(p.polygon).area >= 1e4 and not (p.length < 100.0 and p.kind == 'wall')]

# Renumber cleanly
real_walls = [p for p in clean_pieces if p.kind == 'wall']
real_fills = [p for p in clean_pieces if p.kind != 'wall']
for i, w in enumerate(real_walls):
    w.id = f"Wall_{i+1:03d}"
ns = nl = 0
for f in real_fills:
    if f.kind == 'sill':
        ns += 1
        f.id = f"Sill_{ns:03d}"
    else:
        nl += 1
        if f.opening == 'door':
            f.id = f"Lintel_Door_{nl:02d}"
        else:
            f.id = f"Lintel_Win_{nl:02d}"

print(f"Clean walls: {len(real_walls)}")
print(f"Clean opening pieces: {len(real_fills)} (Sills: {ns}, Lintels: {nl})")
