import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import matplotlib.pyplot as plt

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
outline = res['outline']

# Let's find interior rooms by computing polygon difference of outline and walls
foot = unary_union([Polygon(r) for r in outline if len(r) >= 3])
wall_union = unary_union([Polygon(w.polygon).buffer(1) for w in walls])
# subtract walls from footprint
interior_void = foot.difference(wall_union)
rooms = [p for p in (interior_void.geoms if hasattr(interior_void, 'geoms') else [interior_void]) if p.area > 1e6] # > 1 m2

print(f"Detected {len(rooms)} room zones:")
for i, r in enumerate(rooms):
    cx, cy = r.centroid.x, r.centroid.y
    print(f"  Zone {i+1}: Area={r.area/1e6:.2f} m2, Center=({cx:.0f}, {cy:.0f}), Bounds={r.bounds}")

