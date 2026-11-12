"""
Format-independent wall topology repair (all units mm).

Works on the rectangular `Wall` pieces produced by any detector (CAD layers, CAD geometry,
raster images, sliced 3D models) and makes intended connections explicit:

  1. normalise   - snap near-orthogonal axes (<= 0.6 deg) to exact 0 / 90 deg
  2. dedupe      - drop walls contained in another; merge overlapping collinear duplicates
  3. collinear   - merge aligned pieces of the same wall separated by <= conn_tol
                   (gaps between conn_tol and the minimum opening width are reported as
                   UNCERTAIN and left open - they are never silently closed)
  4. junctions   - L-corners (primary wall runs to the outer corner, secondary butts its inner
                   face), T-junctions (stem ends exactly on the through-wall face, overshoots
                   trimmed), stepped collinear walls of different thickness
  5. report      - every repair with its location and size, every uncertain gap

Tolerances are real-world millimetres derived from the wall thicknesses actually present in the
drawing (and the raster resolution for images), never pixel guesses.
"""
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from shapely.geometry import LineString, Polygon

from .models import Wall

logger = logging.getLogger(__name__)

ORTHO_SIN = 0.0105          # ~0.6 deg


@dataclass
class _Axis:
    px: float
    py: float
    ux: float
    uy: float
    s0: float
    s1: float
    t: float
    rect: bool

    def pt(self, s: float) -> Tuple[float, float]:
        return (self.px + s * self.ux, self.py + s * self.uy)

    @property
    def nx(self) -> float:
        return -self.uy

    @property
    def ny(self) -> float:
        return self.ux


def default_tolerance(walls: List[Wall], mm_per_px: Optional[float] = None) -> float:
    """Connection tolerance: 60 % of the median wall thickness, 40..150 mm, plus 2 px for rasters."""
    ts = sorted(w.thickness for w in walls if w.kind == 'wall' and w.thickness > 0)
    t_med = ts[len(ts) // 2] if ts else 150.0
    tol = min(150.0, max(40.0, 0.6 * t_med))
    if mm_per_px:
        tol = max(tol, 2.5 * mm_per_px)
    return round(tol, 1)


def _axis_of(w: Wall) -> _Axis:
    vx, vy = w.end_point[0] - w.start_point[0], w.end_point[1] - w.start_point[1]
    L = math.hypot(vx, vy)
    rect = getattr(w, 'shape', 'rectangle') == 'rectangle' and L >= 10.0 and len(w.polygon) == 4
    if not rect:
        return _Axis(w.start_point[0], w.start_point[1], 1.0, 0.0, 0.0, L, w.thickness, False)
    ux, uy = vx / L, vy / L
    px, py = w.start_point
    if abs(uy) <= ORTHO_SIN:                       # horizontal: exact axis through the mid-height
        cy = 0.5 * (w.start_point[1] + w.end_point[1])
        x0, x1 = sorted((w.start_point[0], w.end_point[0]))
        return _Axis(x0, cy, 1.0, 0.0, 0.0, x1 - x0, w.thickness, True)
    if abs(ux) <= ORTHO_SIN:
        cx = 0.5 * (w.start_point[0] + w.end_point[0])
        y0, y1 = sorted((w.start_point[1], w.end_point[1]))
        return _Axis(cx, y0, 0.0, 1.0, 0.0, y1 - y0, w.thickness, True)
    return _Axis(px, py, ux, uy, 0.0, L, w.thickness, True)


def _rel(a: _Axis, b: _Axis):
    """b relative to a: (dot of directions, lateral offset of b's line from a's line, b's interval on a)."""
    dot = a.ux * b.ux + a.uy * b.uy
    dx, dy = b.px - a.px, b.py - a.py
    lat = dx * a.nx + dy * a.ny
    base = dx * a.ux + dy * a.uy
    j0, j1 = base + b.s0 * dot, base + b.s1 * dot
    return dot, lat, min(j0, j1), max(j0, j1)


def _intersect(a: _Axis, b: _Axis):
    cross = a.ux * b.uy - a.uy * b.ux
    if abs(cross) < 1e-4:
        return None
    dx, dy = b.px - a.px, b.py - a.py
    sa = (dx * b.uy - dy * b.ux) / cross
    sb = (dx * a.uy - dy * a.ux) / cross
    return sa, sb, abs(cross)


def repair_topology(walls: List[Wall], conn_tol: Optional[float] = None, min_opening: float = 450.0,
                    known_openings: Optional[List[Tuple[Tuple[float, float], Tuple[float, float]]]] = None,
                    min_length: float = 80.0) -> Tuple[List[Wall], Dict]:
    """
    Repair wall connectivity. Returns (walls, report).
    known_openings: (p0, p1) centre-line segments of openings already established by the detector;
    collinear gaps that coincide with one are reported as openings, not as uncertain.
    """
    rep: Dict = {'conn_tol_mm': None, 'repairs': [], 'uncertain': [], 'deduplicated': 0, 'polygon_walls': 0,
                 'max_lateral_shift_mm': 0.0}
    if not walls:
        return walls, rep
    tol = float(conn_tol) if conn_tol else default_tolerance(walls)
    rep['conn_tol_mm'] = tol
    known = [LineString(seg).buffer(60.0) for seg in (known_openings or [])]
    ax = [_axis_of(w) for w in walls]
    rep['polygon_walls'] = sum(1 for a in ax if not a.rect)
    dead = set()
    locked = set()                                 # (index, 's' | 'e')

    def add_repair(kind, x, y, size, detail):
        rep['repairs'].append({'type': kind, 'xy': [round(x, 1), round(y, 1)], 'size_mm': round(size, 1),
                               'detail': detail})

    # ── 2 + 3. duplicates and collinear pieces of the same wall
    changed = True
    while changed:
        changed = False
        for i in range(len(walls)):
            if i in dead or not ax[i].rect:
                continue
            for j in range(len(walls)):
                if j == i or j in dead or not ax[j].rect:
                    continue
                a, b = ax[i], ax[j]
                dot, lat, j0, j1 = _rel(a, b)
                if abs(dot) < 0.9995:
                    continue
                same_t = abs(a.t - b.t) <= max(5.0, 0.1 * min(a.t, b.t))
                if abs(lat) > max(3.0, 0.12 * min(a.t, b.t)) or not same_t:
                    continue
                gap = max(a.s0 - j1, j0 - a.s1)
                g0, g1 = (a.s1, j0) if j0 >= a.s1 else (j1, a.s0)
                is_tj_bridge = False
                if gap > tol:
                    # Check if the gap between collinear pieces a and b is the exact footprint
                    # of a perpendicular wall meeting or crossing this line (T/X-junction split)
                    for k in range(len(walls)):
                        if k in dead or k in (i, j) or not ax[k].rect:
                            continue
                        c = ax[k]
                        if abs(a.ux * c.ux + a.uy * c.uy) > 0.2:
                            continue
                        res = _intersect(a, c)
                        if res is None:
                            continue
                        sa, sc, sn = res
                        half_c = 0.5 * c.t / sn
                        half_a = 0.5 * a.t / sn
                        if gap <= c.t / sn + tol and g0 >= sa - half_c - tol and g1 <= sa + half_c + tol:
                            if c.s0 - half_a - tol <= sc <= c.s1 + half_a + tol:
                                is_tj_bridge = True
                                break
                    if not is_tj_bridge:
                        continue
                if gap > 0:
                    gx, gy = a.pt(a.s1 + gap / 2 if j0 >= a.s1 else a.s0 - gap / 2)
                    add_repair('T-junction' if is_tj_bridge else 'collinear', gx, gy, gap,
                               'merged through-wall across perpendicular T/X-junction'
                               if is_tj_bridge else f'merged two aligned pieces of one wall across a {gap:.0f} mm break')
                else:
                    rep['deduplicated'] += 1 if (j0 >= a.s0 - 1 and j1 <= a.s1 + 1) else 0
                a.s0, a.s1 = min(a.s0, j0), max(a.s1, j1)
                shift = abs(lat) + abs(b.t - a.t) / 2.0
                rep['max_lateral_shift_mm'] = max(rep.get('max_lateral_shift_mm', 0.0), round(shift, 2))
                a.t = max(a.t, b.t)
                dead.add(j)
                changed = True
                break
            if changed:
                break

    # contained walls (any orientation): drop walls >= 90 % inside a bigger one
    polys = {i: Polygon(walls[i].polygon).buffer(0) for i in range(len(walls)) if i not in dead}
    order = sorted(polys, key=lambda i: -polys[i].area)
    for k, i in enumerate(order):
        if i in dead or polys[i].is_empty:
            continue
        for j in order[k + 1:]:
            if j in dead or polys[j].is_empty or not polys[i].intersects(polys[j]):
                continue
            if polys[i].intersection(polys[j]).area >= 0.9 * polys[j].area:
                dead.add(j)
                rep['deduplicated'] += 1

    live = [i for i in range(len(walls)) if i not in dead and ax[i].rect]

    # ── 4a. stepped collinear walls of different thickness (one face flush): meet at the gap centre
    for ii, i in enumerate(live):
        for j in live[ii + 1:]:
            a, b = ax[i], ax[j]
            dot, lat, j0, j1 = _rel(a, b)
            if abs(dot) < 0.9995 or abs(lat) > 0.5 * (a.t + b.t) - 20.0 or abs(lat) <= max(3.0, 0.12 * min(a.t, b.t)):
                continue
            for a_end, gap in (('e', j0 - a.s1), ('s', a.s0 - j1)):
                if not (-20.0 <= gap <= tol):
                    continue
                b_end = ('s' if dot > 0 else 'e') if a_end == 'e' else ('e' if dot > 0 else 's')
                if gap > 0:
                    half = gap / 2.0
                    if a_end == 'e':
                        a.s1 += half
                    else:
                        a.s0 -= half
                    if b_end == 's':
                        b.s0 -= half
                    else:
                        b.s1 += half
                    x, y = a.pt(a.s1 if a_end == 'e' else a.s0)
                    add_repair('stepped', x, y, gap, 'closed the gap between two collinear walls of different thickness')
                locked.add((i, a_end))
                locked.add((j, b_end))

    # ── 4b. L-corners: two free ends near the intersection of the centre lines
    for ii, i in enumerate(live):
        for j in live[ii + 1:]:
            a, b = ax[i], ax[j]
            if abs(a.ux * b.ux + a.uy * b.uy) > 0.2:
                continue
            res = _intersect(a, b)
            if res is None:
                continue
            si, sj, sn = res
            ea = min((('s', a.s0), ('e', a.s1)), key=lambda e: abs(e[1] - si))
            eb = min((('s', b.s0), ('e', b.s1)), key=lambda e: abs(e[1] - sj))
            if (i, ea[0]) in locked or (j, eb[0]) in locked:
                continue
            ext_a, ext_b = 0.5 * b.t / sn, 0.5 * a.t / sn
            # each end must stop no further than (half the other wall + tol) from the centre-line crossing
            if abs(ea[1] - si) > ext_a + tol or abs(eb[1] - sj) > ext_b + tol:
                continue
            # the crossing must lie beyond / at the end, not in the middle of either wall (that is a T or X)
            if (ea[0] == 'e' and si < a.s1 - ext_a - tol) or (ea[0] == 's' and si > a.s0 + ext_a + tol):
                continue
            if (eb[0] == 'e' and sj < b.s1 - ext_b - tol) or (eb[0] == 's' and sj > b.s0 + ext_b + tol):
                continue
            if (a.s1 - a.s0) < ext_a + min_length or (b.s1 - b.s0) < ext_b + min_length:
                continue
            before = (a.s0, a.s1, b.s0, b.s1)
            a_primary = (round(a.t, 1), a.s1 - a.s0) >= (round(b.t, 1), b.s1 - b.s0)
            P, Q, sP, sQ, eP, eQ, xP, xQ = (a, b, si, sj, ea[0], eb[0], ext_a, ext_b) if a_primary else \
                                           (b, a, sj, si, eb[0], ea[0], ext_b, ext_a)
            if eP == 's':
                P.s0 = sP - xP
            else:
                P.s1 = sP + xP
            if eQ == 's':
                Q.s0 = sQ + xQ
            else:
                Q.s1 = sQ - xQ
            moved = max(abs(before[0] - a.s0), abs(before[1] - a.s1), abs(before[2] - b.s0), abs(before[3] - b.s1))
            locked.add((i, ea[0]))
            locked.add((j, eb[0]))
            if moved > 0.5:
                x, y = a.pt(si)
                add_repair('L-corner', x, y, moved, 'corner closed: primary wall runs to the outer corner, the other '
                                                    'butts flush against its inner face')

    # ── 4c. T-junctions: a free end near the side face of a through wall
    for i in live:
        a = ax[i]
        for end in ('s', 'e'):
            if (i, end) in locked:
                continue
            s_end = a.s0 if end == 's' else a.s1
            best = None
            for j in live:
                if j == i:
                    continue
                b = ax[j]
                if abs(a.ux * b.ux + a.uy * b.uy) > 0.2:
                    continue
                res = _intersect(a, b)
                if res is None:
                    continue
                si, sj, sn = res
                face = 0.5 * b.t / sn
                half_a = 0.5 * a.t / sn
                if not (b.s0 + half_a - tol <= sj <= b.s1 - half_a + tol):
                    continue                          # crossing must be within the through wall
                target = si - face if end == 'e' else si + face
                delta = target - s_end if end == 'e' else s_end - target    # >0 : extend, <0 : trim overshoot
                if not (-b.t <= delta <= tol):
                    continue
                # the stem must lie on one side of the through wall (not cross it -> X junction)
                other = a.s0 if end == 'e' else a.s1
                if (end == 'e' and other > si - face) or (end == 's' and other < si + face):
                    continue
                if best is None or abs(delta) < abs(best[0]):
                    best = (delta, j, target, sj, half_a)
            if best is None:
                continue
            delta, j, target, sj, half_a = best
            if end == 'e':
                a.s1 = target
            else:
                a.s0 = target
            b = ax[j]
            # make sure the through wall covers the stem's full width (it may stop a little short)
            if (j, 's') not in locked and sj - half_a < b.s0 and b.s0 - (sj - half_a) <= tol:
                b.s0 = sj - half_a
            if (j, 'e') not in locked and sj + half_a > b.s1 and (sj + half_a) - b.s1 <= tol:
                b.s1 = sj + half_a
            locked.add((i, end))
            if abs(delta) > 0.5:
                x, y = a.pt(target)
                add_repair('T-junction', x, y, abs(delta), ('stem extended' if delta > 0 else 'overshoot trimmed') +
                           ' to the face of the through wall')

    # ── rebuild rectangles
    out: List[Wall] = []
    for i, w in enumerate(walls):
        if i in dead:
            continue
        a = ax[i]
        if a.rect:
            L = a.s1 - a.s0
            if L < min_length:
                continue
            sx, sy = a.pt(a.s0)
            ex, ey = a.pt(a.s1)
            hx, hy = a.nx * a.t / 2.0, a.ny * a.t / 2.0
            w.start_point = (round(sx, 2), round(sy, 2))
            w.end_point = (round(ex, 2), round(ey, 2))
            w.length = round(L, 2)
            w.thickness = round(a.t, 2)
            w.polygon = [(round(sx + hx, 2), round(sy + hy, 2)), (round(ex + hx, 2), round(ey + hy, 2)),
                         (round(ex - hx, 2), round(ey - hy, 2)), (round(sx - hx, 2), round(sy - hy, 2))]
        out.append(w)

    # ── uncertain collinear gaps (between tol and the smallest real opening, after junctions resolved)
    out_ax = [_axis_of(w) for w in out]
    out_polys = [Polygon(w.polygon).buffer(0) for w in out]
    for i in range(len(out)):
        if not out_ax[i].rect:
            continue
        for j in range(i + 1, len(out)):
            if not out_ax[j].rect:
                continue
            a, b = out_ax[i], out_ax[j]
            dot, lat, j0, j1 = _rel(a, b)
            if abs(dot) < 0.9995 or abs(lat) > max(3.0, 0.12 * min(a.t, b.t)):
                continue
            gap = max(a.s0 - j1, j0 - a.s1)
            if not (tol < gap < min_opening):
                continue
            g0, g1 = (a.s1, j0) if j0 >= a.s1 else (j1, a.s0)
            seg = LineString([a.pt(g0), a.pt(g1)])
            if any(k.contains(seg) for k in known):
                continue
            if any(k not in (i, j) and out_polys[k].intersects(seg.buffer(2.0)) for k in range(len(out))):
                continue
            m = seg.interpolate(0.5, normalized=True)
            rep['uncertain'].append({'xy': [round(m.x, 1), round(m.y, 1)], 'width_mm': round(gap, 1),
                                     'p0': [round(c, 1) for c in seg.coords[0]],
                                     'p1': [round(c, 1) for c in seg.coords[-1]],
                                     'thickness': round(min(a.t, b.t), 1),
                                     'detail': f'{gap:.0f} mm collinear gap: wider than the connection tolerance '
                                               f'({tol:.0f} mm) but narrower than any opening ({min_opening:.0f} mm)'})

    counts: Dict[str, int] = {}
    for r in rep['repairs']:
        counts[r['type']] = counts.get(r['type'], 0) + 1
    rep['counts'] = counts
    logger.info("Topology repair (tol %.0f mm): %s; %d duplicates; %d uncertain gaps",
                tol, counts, rep['deduplicated'], len(rep['uncertain']))
    return out, rep

