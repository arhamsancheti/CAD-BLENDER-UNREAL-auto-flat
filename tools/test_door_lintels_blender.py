import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from cad_processor.models import Wall
import subprocess
import json

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']

# Doors spec:
doors_spec = [
    # (name, p1, p2, thickness)
    ("Door_Bed2", (10100.0, 5812.5), (11600.0, 5812.5), 125.0),
    ("Door_Bed3", (11725.0, 5812.5), (13225.0, 5812.5), 125.0),
    ("Door_Master_Toilet", (15050.0, 5000.0), (15050.0, 5812.5), 125.0),
    ("Door_Toilet1", (3512.5, 2200.0), (3512.5, 3012.5), 125.0),
    ("Door_Toilet2", (7312.5, 2200.0), (7312.5, 3012.5), 125.0),
    ("Door_Entrance", (775.0, 4037.5), (2337.5, 4037.5), 125.0),
    ("Door_Bed3_Passage", (11662.5, 1125.0), (11662.5, 2187.5), 125.0),
    ("Door_Bed3_Balcony", (14987.5, 2187.5), (14987.5, 3312.5), 125.0),
]

door_lintels = []
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
        id=f"Door_Lintel_{i+1:02d}",
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
    door_lintels.append(w)

print(f"Created {len(door_lintels)} door lintel objects:")
for dl in door_lintels:
    print(f"  {dl.id}: L={dl.length:.0f}mm, base={dl.base:.0f}mm, H={dl.height:.0f}mm, bounds={dl.polygon}")
