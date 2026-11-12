"""
Detection review & validation.

Runs automated geometric checks on the final wall set and renders a colour-coded preview of the
detection on top of the source (raster image or CAD linework):

    red            final walls                     magenta   repaired connections
    blue           window openings                 green     doors / passages
    yellow         UNCERTAIN - left open, needs a decision
    grey outline   candidates rejected as furniture / isolated fragments
    yellow circle  unexpected free wall end

Checks (each returns status PASS / WARN / FAIL with the offending locations):
    free_endpoints       wall ends that touch nothing (no wall, post, sill/lintel or opening)
    near_miss_junctions  walls closer than the connection tolerance but not touching
    duplicates           overlapping wall volumes
    thickness            walls whose thickness is not one of the drawing's wall thicknesses
    wall_holes           enclosed slivers inside the wall mass (junction holes)
    walls_in_openings    wall volume intruding into a clear opening
    room_boundaries      share of each room's boundary supported by drawn linework in the source
    face_shift           lateral movement of wall faces introduced by the repair (room-size guard)
    uncertain_gaps       gaps left open for review
    disconnected         wall groups not connected to the main structure
    geometry_validity    invalid / degenerate polygons
"""
import base64
import logging
import math
from typing import Dict, List, Optional

import cv2
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

COL = {
    'wall': (40, 40, 230), 'post': (40, 40, 160), 'fill': (170, 110, 40), 'window': (255, 170, 0),
    'door': (60, 220, 60), 'passage': (0, 140, 0), 'vent': (255, 230, 120), 'repair': (255, 0, 255),
    'uncertain': (0, 230, 255), 'rejected': (150, 150, 150), 'free': (0, 255, 255), 'room': (230, 230, 230),
}


def _poly(pts) -> Polygon:
    p = Polygon(pts)
    return p if p.is_valid else p.buffer(0)


def _status(n_bad: int, fail_at: int = 1, warn_only: bool = False) -> str:
    if n_bad <= 0:
        return 'PASS'
    return 'WARN' if warn_only or n_bad < fail_at else 'FAIL'


class Frame:
    """Maps recentred plan millimetres to preview pixels (source-image pixels for raster input)."""

    def __init__(self, offset, raster: Optional[dict], bounds):
        self.ox, self.oy = offset
        self.raster = raster
        if raster:
            self.H = raster['size_px'][1]
            self.W = raster['size_px'][0]
            self.k = 1.0 / raster['mm_per_px']
        else:
            x0, y0, x1, y1 = bounds
            self.x0, self.y1 = x0 - 600, y1 + 600
            span = max(x1 - x0 + 1200, y1 - y0 + 1200)
            self.k = 1600.0 / span
            self.W = int((x1 - x0 + 1200) * self.k)
            self.H = int((y1 - y0 + 1200) * self.k)

    def px(self, x: float, y: float):
        if self.raster:
            return (int(round((x + self.ox) * self.k)), int(round(self.H - (y + self.oy) * self.k)))
        return (int(round((x - self.x0) * self.k)), int(round((self.y1 - y) * self.k)))

    def poly(self, pts):
        return np.array([self.px(x, y) for x, y in pts], np.int32)

    def rect_mm_src(self, r):
        """rect_mm in source (pre-recentre) coordinates -> recentred polygon points."""
        x0, y0, x1, y1 = r
        x0, x1 = x0 - self.ox, x1 - self.ox
        y0, y1 = y0 - self.oy, y1 - self.oy
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def run(result: dict, offset, raster: Optional[dict] = None, topology: Optional[dict] = None,
        source_image: str = '', conn_tol: float = 100.0, modes_mm: Optional[List[float]] = None) -> Dict:
    """Build the review (checks + items + preview PNG) for a finished pipeline result."""
    pieces = result.get('walls', [])
    walls = [w for w in pieces if w.kind == 'wall']
    fills = [w for w in pieces if w.kind != 'wall']
    arch = result.get('architecture') or {}
    openings = arch.get('openings', [])
    rooms = arch.get('rooms', [])
    topology = topology or {}
    ox, oy = offset
    checks: List[Dict] = []
    items: List[Dict] = []

    wpolys = [_poly(w.polygon) for w in walls]
    fpolys = [_poly(f.polygon) for f in fills]
    orects = [_poly(o['rect']) for o in openings if o.get('rect')]
    solid = unary_union([p for p in wpolys + fpolys if not p.is_empty]).buffer(0.5, join_style=2).buffer(-0.5, join_style=2) if wpolys else Polygon()

    # ── geometry validity
    bad = [w.id for w, p in zip(walls, wpolys) if p.is_empty or not p.is_valid or p.area < 1.0 or len(w.polygon) < 3]
    checks.append({'id': 'geometry_validity', 'title': 'Invalid / degenerate wall polygons',
                   'status': _status(len(bad)), 'count': len(bad), 'detail': ', '.join(bad[:12])})

    # ── duplicates / overlapping wall volumes
    dups = []
    for i in range(len(walls)):
        for j in range(i + 1, len(walls)):
            a, b = wpolys[i], wpolys[j]
            if a.intersects(b):
                ar = a.intersection(b).area
                if ar > max(100.0, 0.01 * min(a.area, b.area)):
                    dups.append((walls[i].id, walls[j].id, ar))
    checks.append({'id': 'duplicates', 'title': 'Duplicate / overlapping wall segments',
                   'status': _status(len(dups)), 'count': len(dups),
                   'detail': '; '.join(f'{a}/{b} {ar / 1e4:.2f} dm2' for a, b, ar in dups[:10])})

    # ── free endpoints
    others_all = wpolys + fpolys + orects
    dangling_pts = [Point(d['xy_mm'][0] - ox, d['xy_mm'][1] - oy) for d in (raster or {}).get('dangling', []) if d.get('xy_mm')]
    free = []
    for k, w in enumerate(walls):
        if getattr(w, 'shape', 'rectangle') != 'rectangle' or len(w.polygon) != 4:
            continue
        c = w.polygon
        p01 = ((c[0], c[1]), (c[2], c[3]))
        p12 = ((c[1], c[2]), (c[3], c[0]))
        caps = p01 if math.dist(*p01[0]) <= math.dist(*p12[0]) else p12
        for cap in caps:
            seg = LineString(cap).buffer(2.0)
            touching = any(i != k and p.intersects(seg) for i, p in enumerate(wpolys)) or \
                any(p.intersects(seg) for p in fpolys) or any(p.buffer(conn_tol).intersects(seg) for p in orects)
            if not touching:
                m = seg.centroid
                # If raster detection verified this end is closed by a drawn cap line or viewport trim
                # (i.e. not in raster dangling ends), it is an intentional wing-wall / passage end
                if raster and not any(m.distance(dp) <= conn_tol for dp in dangling_pts):
                    continue
                free.append((w.id, m.x, m.y))
    checks.append({'id': 'free_endpoints', 'title': 'Unexpected disconnected wall endpoints',
                   'status': _status(len(free), warn_only=True), 'count': len(free),
                   'detail': '; '.join(f'{i} @({x:.0f},{y:.0f})' for i, x, y in free[:12])})
    for i, x, y in free:
        items.append({'kind': 'free_end', 'xy': [round(x, 1), round(y, 1)], 'wall': i,
                      'detail': 'wall end touches no wall, post, sill/lintel or opening'})

    # ── near-miss junctions
    near = []
    for i in range(len(walls)):
        for j in range(i + 1, len(walls)):
            d = wpolys[i].distance(wpolys[j])
            if 0.5 < d <= conn_tol:
                near.append((walls[i].id, walls[j].id, d))
    checks.append({'id': 'near_miss_junctions', 'title': 'Unresolved junctions (walls almost touching)',
                   'status': _status(len(near), warn_only=True), 'count': len(near),
                   'detail': '; '.join(f'{a}-{b} {d:.0f} mm' for a, b, d in near[:12])})

    # ── thickness
    if not modes_mm:
        hist: Dict[float, float] = {}
        counts_t: Dict[float, int] = {}
        for w in walls:
            if w.layer != 'POST':
                t = round(w.thickness / 5.0) * 5.0
                hist[t] = hist.get(t, 0.0) + w.length
                counts_t[t] = counts_t.get(t, 0) + 1
        top = sorted(hist.items(), key=lambda kv: -kv[1])
        modes_mm = [t for t, L in top[:4] if L >= 0.03 * top[0][1] or counts_t.get(t, 0) >= 2] if top else []
    off_t = [(w.id, w.thickness) for w in walls if w.layer != 'POST' and modes_mm and
             min(abs(w.thickness - m) / m for m in modes_mm) > 0.15]
    checks.append({'id': 'thickness', 'title': f'Wall thickness not in the drawing set {sorted(round(m) for m in modes_mm)} mm',
                   'status': _status(len(off_t), warn_only=True), 'count': len(off_t),
                   'detail': '; '.join(f'{i} {t:.0f} mm' for i, t in off_t[:12])})

    # ── holes in the wall mass
    holes = []
    for g in (solid.geoms if hasattr(solid, 'geoms') else [solid]):
        if g.geom_type != 'Polygon':
            continue
        for ring in g.interiors:
            hp = Polygon(ring)
            if hp.area < 0.25e6:                       # < 0.25 m2 : not a room, a junction hole
                holes.append(hp)
    checks.append({'id': 'wall_holes', 'title': 'Unexpected holes inside the wall geometry (< 0.25 m2)',
                   'status': _status(len(holes)), 'count': len(holes),
                   'detail': '; '.join(f'{h.area / 1e4:.1f} dm2 @({h.centroid.x:.0f},{h.centroid.y:.0f})' for h in holes[:10])})
    for h in holes:
        items.append({'kind': 'hole', 'xy': [round(h.centroid.x, 1), round(h.centroid.y, 1)],
                      'detail': f'{h.area / 1e4:.1f} dm2 enclosed hole in the wall mass'})

    # ── walls intruding into openings
    intr = []
    for o, r in zip([o for o in openings if o.get('rect')], orects):
        core = r.buffer(-5.0)
        if core.is_empty:
            continue
        for w, p in zip(walls, wpolys):
            a = p.intersection(core).area
            if a > 0.02 * core.area:
                intr.append((o['id'], w.id, a))
    checks.append({'id': 'walls_in_openings', 'title': 'Walls crossing intentional openings',
                   'status': _status(len(intr)), 'count': len(intr),
                   'detail': '; '.join(f'{w} in {o}' for o, w, _ in intr[:10])})

    # ── lateral face shift caused by the repair (room-size guard)
    shift = float(topology.get('max_lateral_shift_mm', 0.0))
    checks.append({'id': 'face_shift', 'title': 'Wall faces moved by connection repair (room dimensions)',
                   'status': 'PASS' if shift <= 5.0 else 'FAIL', 'count': int(shift > 5.0),
                   'detail': f'max lateral face movement {shift:.1f} mm (repairs only move wall ends along their axis)'})

    # ── room boundaries supported by source linework
    room_rows = []
    support_fn = _support_raster(source_image, raster, offset) if raster and source_image else \
        _support_underlay(result.get('underlay', []))
    weak_rooms = 0
    op_union = unary_union([r.buffer(30.0) for r in orects]) if orects else None
    for rm in rooms:
        ring = rm.get('ring') or []
        if len(ring) < 3:
            continue
        rp = _poly(ring)
        minx, miny, maxx, maxy = rp.bounds
        tot = sup = 0.0
        pts = list(rp.exterior.coords)
        for a, b in zip(pts, pts[1:]):
            seg = LineString([a, b])
            if op_union is not None:
                seg_d = seg.difference(op_union)
            else:
                seg_d = seg
            for part in (seg_d.geoms if hasattr(seg_d, 'geoms') else [seg_d]):
                if part.is_empty or part.length < 50:
                    continue
                L = part.length
                tot += L
                sup += L * support_fn(part)
        frac = sup / tot if tot > 0 else 1.0
        if frac < 0.8:
            weak_rooms += 1
        room_rows.append({'name': rm.get('name'), 'type': rm.get('type'), 'area_m2': rm.get('area_m2'),
                          'width_m': round((maxx - minx) / 1000.0, 2), 'depth_m': round((maxy - miny) / 1000.0, 2),
                          'boundary_support': round(frac, 2)})
    checks.append({'id': 'room_boundaries', 'title': 'Room boundaries matching drawn wall faces in the source (>= 80 %)',
                   'status': _status(weak_rooms, warn_only=True), 'count': weak_rooms,
                   'detail': '; '.join(f"{r['name']} {r['boundary_support']:.0%}" for r in room_rows if r['boundary_support'] < 0.8)})

    # ── uncertain gaps (raster engine + topology)
    resolved = set(result.get('_resolved_uncertain') or [])
    unc = []
    if raster:
        for g in raster.get('gaps', []):
            if g['kind'] == 'uncertain' and g['id'] not in resolved:
                pts = Frame(offset, raster, None).rect_mm_src(g['rect_mm'])
                c = _poly(pts).centroid
                rx0, ry0, rx1, ry1 = g['rect_mm']
                rx0, rx1, ry0, ry1 = rx0 - ox, rx1 - ox, ry0 - oy, ry1 - oy
                if g.get('o') == 'H':
                    p0, p1, th = [round(rx0, 1), round((ry0 + ry1) / 2, 1)], [round(rx1, 1), round((ry0 + ry1) / 2, 1)], round(abs(ry1 - ry0), 1)
                else:
                    p0, p1, th = [round((rx0 + rx1) / 2, 1), round(ry0, 1)], [round((rx0 + rx1) / 2, 1), round(ry1, 1)], round(abs(rx1 - rx0), 1)
                unc.append({'id': g['id'], 'xy': [round(c.x, 1), round(c.y, 1)], 'width_mm': g['width_mm'],
                            'p0': p0, 'p1': p1, 'thickness': th,
                            'rect': [list(p) for p in pts], 'detail': g['reason'], 'source': 'raster'})
    for k, u in enumerate(topology.get('uncertain', [])):
        gid = f'TOP_{k + 1:02d}'
        if gid in resolved:
            continue
        unc.append({'id': gid, 'xy': [u['xy'][0] - ox, u['xy'][1] - oy], 'width_mm': u['width_mm'],
                    'p0': [u['p0'][0] - ox, u['p0'][1] - oy], 'p1': [u['p1'][0] - ox, u['p1'][1] - oy],
                    'thickness': u['thickness'], 'detail': u['detail'], 'source': 'topology'})
    checks.append({'id': 'uncertain_gaps', 'title': 'Gaps left open for review (not silently closed)',
                   'status': _status(len(unc), warn_only=True), 'count': len(unc),
                   'detail': '; '.join(f"{u['id']} {u['width_mm']:.0f} mm" for u in unc[:12])})

    # ── disconnected groups
    groups = []
    if wpolys:
        allp = wpolys + fpolys
        n = len(allp)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        grown = [p.buffer(1.0) for p in allp]
        for i in range(n):
            for j in range(i + 1, n):
                if grown[i].intersects(grown[j]):
                    parent[find(i)] = find(j)
        comp: Dict[int, List[int]] = {}
        for i in range(len(wpolys)):
            comp.setdefault(find(i), []).append(i)
        sizes = sorted(comp.values(), key=lambda m: -sum(walls[i].length for i in m))
        for m in sizes[1:]:
            groups.append({'walls': [walls[i].id for i in m], 'length_m': round(sum(walls[i].length for i in m) / 1000, 2),
                           'xy': [round(wpolys[m[0]].centroid.x, 1), round(wpolys[m[0]].centroid.y, 1)]})
    if raster:
        for iso in raster.get('isolated', []):
            pts = Frame(offset, raster, None).rect_mm_src(iso['bbox_mm'])
            c = _poly(pts).centroid
            groups.append({'walls': [], 'length_m': round(iso.get('length_mm', 0) / 1000, 2),
                           'xy': [round(c.x, 1), round(c.y, 1)], 'note': 'isolated candidate group not used'})
    checks.append({'id': 'disconnected', 'title': 'Wall groups not connected to the main structure',
                   'status': _status(len(groups), warn_only=True), 'count': len(groups),
                   'detail': '; '.join(f"{g['length_m']} m @({g['xy'][0]:.0f},{g['xy'][1]:.0f})" for g in groups[:10])})

    # ── repairs
    repairs = []
    if raster:
        for g in raster.get('gaps', []):
            if g['kind'] == 'repaired':
                pts = Frame(offset, raster, None).rect_mm_src(g['rect_mm'])
                repairs.append({'rect': [list(p) for p in pts], 'detail': g['reason'], 'width_mm': g['width_mm'],
                                'source': 'raster'})
    for r in topology.get('repairs', []):
        repairs.append({'xy': [r['xy'][0] - ox, r['xy'][1] - oy], 'detail': f"{r['type']}: {r['detail']}",
                        'width_mm': r['size_mm'], 'source': 'topology'})

    review = {
        'checks': checks, 'items': items, 'uncertain': unc, 'repairs': repairs, 'groups': groups,
        'rooms': room_rows, 'conn_tol_mm': conn_tol,
        'summary': {s: sum(1 for c in checks if c['status'] == s) for s in ('PASS', 'WARN', 'FAIL')},
    }
    try:
        review['png_b64'] = _render(result, offset, raster, source_image, review, walls, fills, openings, rooms)
    except Exception as ex:                                     # preview must never break a scan
        logger.exception('review preview failed')
        review['png_error'] = str(ex)
    return review


# ════════════════════════════════════════════════════════════════════════════
#  source support functions (fraction of a boundary segment backed by drawn lines)
# ════════════════════════════════════════════════════════════════════════════
def _support_raster(source_image: str, raster: dict, offset):
    from .image_importer import _load_gray, foreground_mask
    _, gray = _load_gray(source_image)
    _, fg = foreground_mask(gray)
    fg = cv2.dilate(fg, np.ones((5, 5), np.uint8))
    fr = Frame(offset, raster, None)
    H, W = fg.shape

    def fn(seg: LineString) -> float:
        n = max(4, int(seg.length * fr.k / 2))
        hit = 0
        for t in np.linspace(0, 1, n):
            p = seg.interpolate(t, normalized=True)
            x, y = fr.px(p.x, p.y)
            if 0 <= x < W and 0 <= y < H and fg[y, x]:
                hit += 1
        return hit / n
    return fn


def _support_underlay(underlay):
    segs = [LineString([(a, b), (c, d)]) for a, b, c, d in underlay if (a - c) ** 2 + (b - d) ** 2 > 400]
    if not segs:
        return lambda seg: 1.0
    from shapely.strtree import STRtree
    tree = STRtree(segs)

    def fn(seg: LineString) -> float:
        zone = seg.buffer(25.0)
        cand = [segs[i] for i in tree.query(zone)]
        if not cand:
            return 0.0
        cov = unary_union([c.buffer(25.0) for c in cand])
        return min(1.0, seg.intersection(cov).length / max(seg.length, 1e-6))
    return fn


# ════════════════════════════════════════════════════════════════════════════
#  preview rendering
# ════════════════════════════════════════════════════════════════════════════
def _render(result, offset, raster, source_image, review, walls, fills, openings, rooms) -> str:
    xs = [x for w in walls for x, _ in w.polygon] or [0, 1]
    ys = [y for w in walls for _, y in w.polygon] or [0, 1]
    fr = Frame(offset, raster, (min(xs), min(ys), max(xs), max(ys)))
    if raster and source_image:
        from .image_importer import _load_gray
        bgr, _ = _load_gray(source_image)
        base = (bgr.astype(np.float32) * 0.55).astype(np.uint8)
    else:
        base = np.full((fr.H, fr.W, 3), 28, np.uint8)
        for a, b, c, d in result.get('underlay', [])[:40000]:
            cv2.line(base, fr.px(a, b), fr.px(c, d), (105, 105, 105), 1)
    src = base.copy()
    ov = base.copy()
    for rm in rooms:
        ring = rm.get('ring') or []
        if len(ring) >= 3 and rm.get('type') not in ('shaft', 'external'):
            fcat = rm.get('floor_category') or ''
            fcol = {
                'master_wood': (48, 82, 128),
                'balcony': (75, 115, 145),
                'dry_balcony': (95, 105, 110),
                'entrance': (95, 85, 75),
                'washroom': (125, 105, 45),
                'common': (72, 78, 84),
            }.get(fcat, (65, 65, 65))
            cv2.fillPoly(ov, [fr.poly(ring)], fcol)
    for f in fills:
        cv2.fillPoly(ov, [fr.poly(f.polygon)], COL['fill'])
    for w in walls:
        cv2.fillPoly(ov, [fr.poly(w.polygon)], COL['post'] if w.layer == 'POST' else COL['wall'])
    img = cv2.addWeighted(ov, 0.85, base, 0.15, 0)
    for w in walls:
        cv2.polylines(img, [fr.poly(w.polygon)], True, (255, 255, 255), 1)
    for o in openings:
        if o.get('rect'):
            c = (255, 255, 0) if o.get('balcony') else COL.get(o['type'], (255, 255, 255))
            cv2.polylines(img, [fr.poly(o['rect'])], True, c, 2)
    if raster:
        for r in raster.get('rejected', []):
            cv2.polylines(img, [fr.poly(fr.rect_mm_src(r['rect_mm']))], True, COL['rejected'], 1)
        for iso in raster.get('isolated', []):
            cv2.polylines(img, [fr.poly(fr.rect_mm_src(iso['bbox_mm']))], True, COL['rejected'], 1)
    for r in review['repairs']:
        if 'rect' in r:
            cv2.fillPoly(img, [fr.poly(r['rect'])], COL['repair'])
        else:
            cv2.drawMarker(img, fr.px(*r['xy']), COL['repair'], cv2.MARKER_DIAMOND, 10, 2)
    for u in review['uncertain']:
        if 'rect' in u:
            cv2.polylines(img, [fr.poly(u['rect'])], True, COL['uncertain'], 2)
        else:
            cv2.line(img, fr.px(*u['p0']), fr.px(*u['p1']), COL['uncertain'], 3)
        x, y = fr.px(*u['xy'])
        cv2.putText(img, u['id'], (x + 6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COL['uncertain'], 1, cv2.LINE_AA)
    for it in review['items']:
        if it['kind'] == 'free_end':
            cv2.circle(img, fr.px(*it['xy']), 7, COL['free'], 2)
        elif it['kind'] == 'hole':
            cv2.drawMarker(img, fr.px(*it['xy']), (0, 0, 255), cv2.MARKER_TILTED_CROSS, 14, 2)
    for rm in rooms:
        ring = rm.get('ring') or []
        if len(ring) >= 3 and rm.get('type') != 'external':
            c = _poly(ring).representative_point()
            x, y = fr.px(c.x, c.y)
            lbl = rm.get('label') or rm.get('name', '')
            cv2.putText(img, lbl, (x - 36, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36,
                        (240, 240, 240), 1, cv2.LINE_AA)
    # legend
    lg = [(COL['wall'], 'detected wall'), (COL['repair'], 'repaired connection'), (COL['window'], 'window glass'),
          ((255, 255, 0), 'balcony glass railing (1.2m)'), (COL['door'], 'door / passage'),
          (COL['uncertain'], 'uncertain - review'), (COL['free'], 'free wall end')]
    y = 18
    for col_v, label in lg:
        cv2.rectangle(img, (10, y - 10), (24, y + 2), col_v, -1)
        cv2.putText(img, label, (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (240, 240, 240), 1, cv2.LINE_AA)
        y += 18
    # side-by-side comparison: source | detection
    gap = np.full((img.shape[0], 8, 3), 255, np.uint8)
    combo = np.hstack([src, gap, img])
    cv2.putText(combo, 'SOURCE', (10, combo.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(combo, 'DETECTED + REPAIRED', (src.shape[1] + 18, combo.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 2)
    ok, buf = cv2.imencode('.png', combo)
    return base64.b64encode(buf.tobytes()).decode('ascii') if ok else ''
