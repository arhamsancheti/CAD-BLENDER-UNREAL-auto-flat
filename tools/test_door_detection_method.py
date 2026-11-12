import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from cad_processor.models import Wall
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
import numpy as np

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
outline = res['outline']

def find_all_door_lintels(walls, existing_fills, outline, wall_height=3000.0, head_base=2100.0):
    foot = unary_union([Polygon(r) for r in outline if len(r) >= 3])
    wall_polys = [Polygon(w.polygon).buffer(0) for w in walls]
    wall_union = unary_union(wall_polys)
    win_union = unary_union([Polygon(f.polygon).buffer(15) for f in existing_fills if f.opening == 'window'])
    existing_lintel_union = unary_union([Polygon(f.polygon).buffer(15) for f in existing_fills if f.kind == 'lintel'])

    # Gather wall ends
    wall_ends = []
    for w in walls:
        a, b = np.array(w.start_point, float), np.array(w.end_point, float)
        d = b - a
        l = float(np.linalg.norm(d))
        if l < 200: continue
        u = d / l
        wall_ends.append((w, a, -u, w.thickness))
        wall_ends.append((w, b, u, w.thickness))

    door_lintels = []
    used_rects = []

    def try_add_door(pa, pb, ta, tb, name):
        g = pb - pa
        along = float(np.linalg.norm(g))
        if not (700 <= along <= 1650):
            return False
        mid = (pa + pb) / 2.0
        # Must be inside or on the footprint boundary
        if not (foot.buffer(10).contains(Point(mid))):
            return False
        # Must not cross outside into open air
        ls = LineString([pa, pb])
        if win_union and ls.intersects(win_union):
            return False
        if existing_lintel_union and existing_lintel_union.intersects(ls):
            return False
        t = max(ta, tb)
        u = g / along
        nrm = np.array([-u[1], u[0]])
        rect = Polygon([pa + nrm * t / 2, pb + nrm * t / 2, pb - nrm * t / 2, pa - nrm * t / 2])
        if any(rect.intersection(ur).area > 0.4 * rect.area for ur in used_rects):
            return False
        used_rects.append(rect)
        ring = [(round(x, 1), round(y, 1)) for x, y in list(rect.exterior.coords)[:-1]]
        door_lintels.append(Wall(
            id=f"Lintel_Door_{len(door_lintels)+1:02d}",
            start_point=(float(pa[0]), float(pa[1])),
            end_point=(float(pb[0]), float(pb[1])),
            length=along,
            thickness=t,
            height=wall_height - head_base,
            polygon=ring,
            wall_type="interior",
            layer="DOOR_LINTEL",
            base=head_base,
            kind="lintel",
            opening="door"
        ))
        return True

    # Check collinear wall end pairs
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
                try_add_door(pa, pb, ta, tb, f"collinear_{w1.id}_{w2.id}")

    # Check wall ends stopping with door gap at perpendicular wall
    for w, pa, da, ta in wall_ends:
        for dist in (812.5, 900.0, 950.0, 1000.0, 1062.5, 1125.0, 1500.0):
            target = pa + da * dist
            p_target = Point(target)
            for w_other in walls:
                if w_other.id == w.id: continue
                if Polygon(w_other.polygon).buffer(20).contains(p_target):
                    try_add_door(pa, target, ta, w_other.thickness, f"perp_{w.id}_{w_other.id}")
                    break

    return door_lintels

dls = find_all_door_lintels(walls, fills, outline)
print(f"Detected {len(dls)} door lintels:")
for d in dls:
    print(f"  {d.id}: L={d.length:.0f}mm, T={d.thickness:.0f}mm, base={d.base:.0f}mm, H={d.height:.0f}mm, ({d.start_point[0]:.0f},{d.start_point[1]:.0f}) -> ({d.end_point[0]:.0f},{d.end_point[1]:.0f})")
