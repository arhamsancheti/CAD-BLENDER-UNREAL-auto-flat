import sys
sys.path.insert(0, '.')
from cad_processor.importer import CADImporter
from cad_processor.normalizer import UnitNormalizer
from cad_processor.pipeline import CADtoBlenderPipeline
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
import numpy as np

imp = CADImporter()
ents = imp.import_file('uploads/1791528835981_3_Bhk.dwg')
norm = UnitNormalizer()
ents = norm.normalize(ents)

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
offset = res['info']['offset_mm']
walls = [w for w in res['walls'] if w.kind == 'wall']

# Let's inspect all lines in ents recentered by offset
all_lines = []
for e in ents:
    for p0, p1 in zip(e.points, e.points[1:] if not e.is_closed else e.points[1:] + [e.points[0]]):
        a = (p0[0] - offset[0], p0[1] - offset[1])
        b = (p1[0] - offset[0], p1[1] - offset[1])
        l = np.hypot(b[0] - a[0], b[1] - a[1])
        if l > 10:
            all_lines.append((a, b, l, e.layer))

print(f"Total lines: {len(all_lines)}")

# Find lines that are NOT covered by walls
wall_poly_union = unary_union([Polygon(w.polygon).buffer(5) for w in walls])
free_lines = []
for a, b, l, lay in all_lines:
    ls = LineString([a, b])
    if wall_poly_union.intersection(ls).length < 0.5 * l:
        free_lines.append((a, b, l, lay))

print(f"Lines not covered by walls: {len(free_lines)}")
for a, b, l, lay in sorted(free_lines, key=lambda x: -x[2]):
    print(f"  Len {l:6.1f} mm | ({a[0]:6.1f}, {a[1]:6.1f}) -> ({b[0]:6.1f}, {b[1]:6.1f}) | {lay}")
