import sys
sys.path.insert(0, '.')
from cad_processor.importer import CADImporter
from cad_processor.normalizer import UnitNormalizer
from cad_processor.pipeline import CADtoBlenderPipeline
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
import numpy as np

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
windows = [f for f in fills if f.opening == 'window']
offset = res['info']['offset_mm']

imp = CADImporter()
ents = imp.import_file('uploads/1791528835981_3_Bhk.dwg')
ents = UnitNormalizer().normalize(ents)

all_lines = []
for e in ents:
    for p0, p1 in zip(e.points, e.points[1:]):
        a = (p0[0] - offset[0], p0[1] - offset[1])
        b = (p1[0] - offset[0], p1[1] - offset[1])
        l = np.hypot(b[0] - a[0], b[1] - a[1])
        if l > 10:
            if a > b: a, b = b, a
            all_lines.append((a, b, l))

# Deduplicate
unique_lines = []
for a, b, l in all_lines:
    if not any(np.hypot(a[0]-ua[0], a[1]-ua[1]) < 10 and np.hypot(b[0]-ub[0], b[1]-ub[1]) < 10 for ua, ub, _ in unique_lines):
        unique_lines.append((a, b, l))

wall_union = unary_union([Polygon(w.polygon).buffer(5) for w in walls])
win_union = unary_union([Polygon(w.polygon).buffer(20) for w in windows])

# Lines that are NOT covered by walls and NOT covered by windows:
door_candidate_lines = []
for a, b, l in unique_lines:
    ls = LineString([a, b])
    if wall_union.intersection(ls).length < 0.3 * l and not win_union.intersects(ls):
        if 650.0 <= l <= 1700.0:
            # Check if both endpoints are close to walls!
            d0 = wall_union.distance(Point(a))
            d1 = wall_union.distance(Point(b))
            if d0 < 100.0 and d1 < 100.0:
                door_candidate_lines.append((a, b, l))

print(f"Detected {len(door_candidate_lines)} exact CAD doorway lines connecting walls:")
for a, b, l in sorted(door_candidate_lines, key=lambda x: -x[2]):
    print(f"  L={l:6.1f}mm: ({a[0]:6.1f}, {a[1]:6.1f}) -> ({b[0]:6.1f}, {b[1]:6.1f})")
