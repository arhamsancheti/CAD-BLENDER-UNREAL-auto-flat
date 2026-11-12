import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
import numpy as np

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
windows = [f for f in fills if f.opening == 'window']

# List all walls and their endpoints
print(f"Total walls: {len(walls)}")
print(f"Existing window sills: {len([f for f in fills if f.kind == 'sill'])}")
print(f"Existing lintels: {len([f for f in fills if f.kind == 'lintel'])}")

# Check every pair of wall endpoints that could be a door opening
# Doors typically have gap between 700mm and 1600mm
# And door openings are between walls
wall_polys = [Polygon(w.polygon).buffer(0) for w in walls]
wall_union = unary_union(wall_polys)

# Find all endpoints of walls
endpoints = []
for i, w in enumerate(walls):
    p0, p1 = np.array(w.start_point), np.array(w.end_point)
    endpoints.append((i, p0, 'start', w))
    endpoints.append((i, p1, 'end', w))

print("\n--- CHECKING DOOR CANDIDATES ---")
candidates = []
for i in range(len(endpoints)):
    w_idx1, p1, which1, w1 = endpoints[i]
    for j in range(i + 1, len(endpoints)):
        w_idx2, p2, which2, w2 = endpoints[j]
        if w_idx1 == w_idx2:
            continue
        dist = np.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if 650.0 <= dist <= 1650.0:
            # Check if this gap is already covered by a window or existing lintel
            ls = LineString([p1, p2])
            is_win = False
            for win in windows:
                if ls.intersects(Polygon(win.polygon).buffer(10)):
                    is_win = True
                    break
            if not is_win:
                candidates.append((dist, p1, p2, w1, w2))

candidates.sort(key=lambda x: x[0])
print(f"Found {len(candidates)} door candidate pairs:")
for dist, p1, p2, w1, w2 in candidates:
    print(f"  Dist {dist:6.1f} mm: ({p1[0]:.0f}, {p1[1]:.0f}) [{w1.id}] -> ({p2[0]:.0f}, {p2[1]:.0f}) [{w2.id}]")
