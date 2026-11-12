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

doors_spec = [
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

# Skirting rings (in meters)
foot = unary_union([Polygon(r) for r in outline if len(r) >= 3])
wall_union = unary_union([Polygon(w.polygon).buffer(0) for w in walls])
interior_space = foot.difference(wall_union).buffer(0)
skirting_raw = interior_space.difference(interior_space.buffer(-15.0))
skirting_geom = skirting_raw.intersection(wall_union.buffer(16.0))
skirting_polys = list(skirting_geom.geoms) if hasattr(skirting_geom, 'geoms') else [skirting_geom]
skirting_rings = [[(round(x/1000.0, 4), round(y/1000.0, 4)) for x, y in p.exterior.coords[:-1]] for p in skirting_polys if p.area > 500.0]

# Washroom tile cladding rings (in meters)
washroom_boxes = [
    ("Washroom_1", box(3512, 63, 5087, 2200)),
    ("Washroom_2", box(5087, 1688, 7312, 3013)),
    ("Washroom_3", box(14987, 3313, 16525, 5875)),
]
washroom_tile_data = []
for wname, bx in washroom_boxes:
    w_touch = [w for w in walls if Polygon(w.polygon).intersects(bx.buffer(50))]
    t_void = bx.difference(unary_union([Polygon(w.polygon) for w in w_touch]))
    parts = list(t_void.geoms) if hasattr(t_void, 'geoms') else [t_void]
    parts = [p for p in parts if p.area > 5e5]
    if parts:
        mv = parts[0]
        # perimeter ribbon of 8mm tile thickness
        ribbon = mv.difference(mv.buffer(-8.0))
        rib_parts = list(ribbon.geoms) if hasattr(ribbon, 'geoms') else [ribbon]
        for r_part in rib_parts:
            if r_part.area > 500:
                coords = [(round(x/1000.0, 4), round(y/1000.0, 4)) for x, y in r_part.exterior.coords[:-1]]
                washroom_tile_data.append((wname, coords))

print(f"Prepared: {len(clean_pieces)} wall pieces, {len(skirting_rings)} skirting rings, {len(washroom_tile_data)} washroom tile ribbons.")
