import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from shapely.geometry import box, Polygon
import numpy as np

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']

# Check the 3 washrooms
washrooms = [
    ("Toilet 1 (South-West)", box(3500, 0, 5200, 1800)),
    ("Toilet 2 (South-Center)", box(5000, 1600, 7400, 3100)),
    ("Toilet 3 (North-East)", box(14900, 5700, 16650, 7600)),
]

for name, b in washrooms:
    print(f"\n=== {name} ===")
    w_inside = [w for w in walls if Polygon(w.polygon).intersects(b)]
    f_inside = [f for f in fills if Polygon(f.polygon).intersects(b)]
    print(f"Walls in zone: {[w.id for w in w_inside]}")
    print(f"Fills in zone: {[f.id for f in f_inside]}")
    for w in w_inside:
        print(f"  {w.id}: ({w.start_point[0]:.0f}, {w.start_point[1]:.0f}) -> ({w.end_point[0]:.0f}, {w.end_point[1]:.0f}), L={w.length:.0f}, T={w.thickness:.0f}")
