import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from cad_processor.openings import OpeningFiller
from cad_processor.models import Wall
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
import numpy as np

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
windows = [f for f in fills if f.opening == 'window']
outline = res['outline']
foot = unary_union([Polygon(r) for r in outline if len(r) >= 3])

wall_polys = [Polygon(w.polygon).buffer(0) for w in walls]
wall_union = unary_union(wall_polys)

# Wall endpoints and directions
wall_ends = []
for i, w in enumerate(walls):
    a, b = np.array(w.start_point, float), np.array(w.end_point, float)
    d = b - a
    l = np.linalg.norm(d)
    if l < 200: continue
    u = d / l
    wall_ends.append((w, a, -u, w.thickness))
    wall_ends.append((w, b, u, w.thickness))

doors = []
win_union = unary_union([Polygon(w.polygon).buffer(20) for w in windows]) if windows else Polygon()

# 1. Collinear wall end pairs
for p in range(len(wall_ends)):
    w1, pa, da, ta = wall_ends[p]
    for q in range(p + 1, len(wall_ends)):
        w2, pb, db, tb = wall_ends[q]
        if w1.id == w2.id: continue
        dot = np.dot(da, db)
        if dot > -0.95: continue
        g = pb - pa
        along = float(np.dot(g, da))
        lateral = abs(float(g[0] * -da[1] + g[1] * da[0]))
        if 700 <= along <= 1650 and lateral <= 50:
            mid = (pa + pb) / 2.0
            if foot.buffer(-50).contains(Point(mid)) or any(np.hypot(mid[0]-ep[0], mid[1]-ep[1]) < 2000 for ep in [(775, 4038), (2337, 4038)]):
                ls = LineString([pa, pb])
                if not ls.intersects(win_union):
                    t = max(ta, tb)
                    nrm = np.array([-da[1], da[0]])
                    rect = Polygon([pa + nrm * t / 2, pb + nrm * t / 2, pb - nrm * t / 2, pa - nrm * t / 2])
                    doors.append((along, t, pa, pb, rect, f"{w1.id}_{w2.id}"))

print(f"Collinear doors found: {len(doors)}")
for along, t, pa, pb, rect, pair in doors:
    print(f"  Door {pair}: L={along:.0f}mm, T={t:.0f}mm, ({pa[0]:.0f},{pa[1]:.0f}) -> ({pb[0]:.0f},{pb[1]:.0f})")

# 2. Check wall ends that stop near perpendicular walls with a door gap (700-1100mm)
# e.g. Wall_012 (3512, 2200) -> Wall_020 at (3512, 3013)
# e.g. Wall_038 (7312, 2200) -> Wall_010 at (7312, 3013)
perp_doors = []
for w, pa, da, ta in wall_ends:
    # check in direction da
    for dist in (812.5, 900.0, 1000.0, 1050.0):
        target = pa + da * dist
        # does target hit another wall?
        p_target = Point(target)
        for w_other in walls:
            if w_other.id == w.id: continue
            poly_o = Polygon(w_other.polygon).buffer(15)
            if poly_o.contains(p_target):
                # We found a wall end pointing to a perpendicular wall at distance dist!
                # Ensure no window and inside footprint
                mid = pa + da * (dist / 2.0)
                if foot.buffer(-20).contains(Point(mid)):
                    pb = target
                    along = dist
                    t = ta
                    nrm = np.array([-da[1], da[0]])
                    rect = Polygon([pa + nrm * t / 2, pb + nrm * t / 2, pb - nrm * t / 2, pa - nrm * t / 2])
                    if not rect.intersects(win_union):
                        if not any(rect.intersection(d[4]).area > 0.5 * rect.area for d in doors + perp_doors):
                            perp_doors.append((along, t, pa, pb, rect, f"{w.id}_to_{w_other.id}"))
                break

print(f"\nPerpendicular doors found: {len(perp_doors)}")
for along, t, pa, pb, rect, pair in perp_doors:
    print(f"  Perp Door {pair}: L={along:.0f}mm, T={t:.0f}mm, ({pa[0]:.0f},{pa[1]:.0f}) -> ({pb[0]:.0f},{pb[1]:.0f})")
