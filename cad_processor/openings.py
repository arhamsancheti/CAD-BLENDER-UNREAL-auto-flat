import logging
import math
from typing import List, Tuple

import numpy as np
from shapely.affinity import translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .models import CADEntity, Wall

logger = logging.getLogger(__name__)

MIN_GAP = 300.0
MAX_GAP = 3600.0
HEAD_BASE = 2100.0     # Door & window lintel base: 2.1 m (2100 mm)
WINDOW_H = 1500.0      # Standard window height: 5 ft (~1500 mm)
VENT_WINDOW_H = 900.0  # Toilet/ventilator window height: 0.9 m (900 mm)


class OpeningFiller:
    """
    Walls stop at windows/doors.  This finds gaps between two collinear walls, decides
    window / door / plain opening from the WIN* / DOOR* layers, and creates
        window  -> sill (standard 5ft window: 0-600mm; toilet window 0.9m: 0-1200mm) + lintel (2100mm-top)
        door    -> lintel only (2100mm-top)
        opening -> lintel only (2100mm-top)
    Those pieces are listed separately (kind = sill / lintel) and do not count as walls.
    """

    @staticmethod
    def get_window_sill_height(length: float, layer: str = '') -> float:
        """
        Sill height calculation based on user requirements:
        - Door: 2.1m opening (no sill)
        - Windows 5ft (1500mm): with 2.1m lintel -> sill = 2100 - 1500 = 600mm
        - Toilet window 0.9m (900mm): with 2.1m lintel -> sill = 2100 - 900 = 1200mm
        - Large sliding/balcony doors (> 2200mm): no sill (0mm)
        """
        if length > 2200.0:
            return 0.0
        up = layer.upper()
        if length <= 1000.0 or any(k in up for k in ('TOILET', 'WASH', 'BATH', 'WC', 'POWDER', 'VENT')):
            return HEAD_BASE - VENT_WINDOW_H   # 1200.0 mm
        return HEAD_BASE - WINDOW_H           # 600.0 mm


    def find(self, walls: List[Wall], all_entities: List[CADEntity],
             offset: Tuple[float, float], height: float) -> List[Wall]:
        ox, oy = offset
        win_geoms, door_geoms = [], []
        for e in all_entities:
            up = e.layer.upper()
            if 'WIN' in up or 'GLASS' in up:
                kind = win_geoms
            elif 'DOOR' in up:
                kind = door_geoms
            else:
                continue
            if len(e.points) == 1:
                g = Point(e.points[0][0] - ox, e.points[0][1] - oy).buffer(600)
            else:
                g = LineString([(x - ox, y - oy) for x, y in e.points])
            kind.append(g)
        win = unary_union(win_geoms) if win_geoms else None
        door = unary_union(door_geoms) if door_geoms else None

        # wall ends: (wall index, point, outward direction, normal, thickness)
        ends = []
        for i, w in enumerate(walls):
            if w.kind != 'wall' or w.shape != 'rectangle' or w.length < 250:
                continue
            a, b = np.array(w.start_point, float), np.array(w.end_point, float)
            d = (b - a) / np.linalg.norm(b - a)
            ends.append((i, a, -d, w.thickness))
            ends.append((i, b, d, w.thickness))

        wall_polys = [Polygon(w.polygon) for w in walls]
        pairs = []
        for p in range(len(ends)):
            for q in range(p + 1, len(ends)):
                i, pa, da, ta = ends[p]
                j, pb, db, tb = ends[q]
                if i == j or np.dot(da, db) > -0.98:
                    continue
                g = pb - pa
                along = float(np.dot(g, da))
                lateral = abs(float(g[0] * -da[1] + g[1] * da[0]))
                if not (MIN_GAP <= along <= MAX_GAP):
                    continue
                if lateral > 0.5 * max(ta, tb) + 25 or not (0.7 <= ta / tb <= 1.43):
                    continue
                gap_line = LineString([pa, pb])
                if any(gap_line.intersection(wall_polys[k]).length > 10.0 for k in range(len(walls)) if k != i and k != j):
                    continue
                pairs.append((along, p, q))
        pairs.sort()
        used, out = set(), []
        n_s = n_h = 0
        for along, p, q in pairs:
            if p in used or q in used:
                continue
            i, pa, da, ta = ends[p]
            j, pb, db, tb = ends[q]
            t = max(ta, tb)
            nrm = np.array([-da[1], da[0]])
            rect = Polygon([pa + nrm * t / 2, pb + nrm * t / 2, pb - nrm * t / 2, pa - nrm * t / 2])
            if any(rect.buffer(-5).intersection(wall_polys[k]).area > 500.0 for k in range(len(walls)) if k != i and k != j):
                continue
            probe = rect.buffer(150)
            if win is not None and probe.intersects(win):
                otype = 'window'
            elif door is not None and rect.buffer(700).intersects(door):
                otype = 'door'
            else:
                otype = 'opening'
            used.update((p, q))
            wtype = walls[i].wall_type
            ring = [tuple(c) for c in list(rect.exterior.coords)[:-1]]
            pieces = []
            if otype == 'window':
                sill_h = self.get_window_sill_height(along, walls[i].layer)
                if sill_h > 0:
                    pieces.append(('sill', 0.0, sill_h))
            pieces.append(('lintel', HEAD_BASE, max(height - HEAD_BASE, 100.0)))
            for kind, base, h in pieces:
                if kind == 'sill':
                    n_s += 1
                    pid = f"Sill_{n_s:03d}"
                else:
                    n_h += 1
                    pid = f"Lintel_{n_h:03d}"
                out.append(Wall(id=pid, start_point=(float(pa[0]), float(pa[1])),
                                end_point=(float(pb[0]), float(pb[1])), length=along, thickness=t,
                                height=h, polygon=ring, wall_type=wtype, layer=walls[i].layer,
                                base=base, kind=kind, opening=otype))
        logger.info("Opening fill: %d gaps -> %d pieces", len(used) // 2, len(out))
        return out

    def window_runs(self, walls: List[Wall], all_entities: List[CADEntity], offset: Tuple[float, float],
                    height: float, existing: List[Wall]) -> List[Wall]:
        """
        Windows/glazing drawn as WIN/GLASS lines or balcony PARAPET/RAILING outlines.
        Separates horizontal and vertical segments so L-shaped windows and parapets
        split cleanly into orthogonal strips with solid corner posts at their intersections.
        """
        ox, oy = offset
        self.corner_posts: List[Polygon] = []
        self.parapet_polys: List[Polygon] = []

        has_railing_layer = any('RAILING' in e.layer.upper() for e in all_entities)
        segs_by_cat = {'WIN': {'H': [], 'V': []}, 'PARAPET': {'H': [], 'V': []}}
        for e in all_entities:
            up = e.layer.upper()
            if 'WIN' in up or 'GLASS' in up:
                cat = 'WIN'
            elif 'RAILING' in up or ('PARAPET' in up and not has_railing_layer):
                cat = 'PARAPET'
            elif 'PARAPET' in up:
                cat = 'WIN'
            else:
                continue
            if len(e.points) < 2:
                continue
            pts = [(x - ox, y - oy) for x, y in e.points]
            if e.is_closed and len(pts) >= 3:
                pts.append(pts[0])
            for p0, p1 in zip(pts, pts[1:]):
                dx, dy = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
                L = math.hypot(dx, dy)
                if L < 220.0:
                    continue
                if dx >= dy * 4.0:
                    y_m = 0.5 * (p0[1] + p1[1])
                    segs_by_cat[cat]['H'].append(box(min(p0[0], p1[0]) - 80.0, y_m - 85.0, max(p0[0], p1[0]) + 80.0, y_m + 85.0))
                elif dy >= dx * 4.0:
                    x_m = 0.5 * (p0[0] + p1[0])
                    segs_by_cat[cat]['V'].append(box(x_m - 85.0, min(p0[1], p1[1]) - 80.0, x_m + 85.0, max(p0[1], p1[1]) + 80.0))

        if not any(segs_by_cat[c][ori] for c in segs_by_cat for ori in ('H', 'V')):
            return []

        wall_u = unary_union([Polygon(w.polygon).buffer(1.0, join_style=2) for w in walls if len(w.polygon) >= 3])
        covered = unary_union([Polygon(w.polygon).buffer(30.0) for w in walls + existing if len(w.polygon) >= 3])

        raw_strips = {'H': [], 'V': []}
        for cat in ('PARAPET', 'WIN'):
            for ori in ('H', 'V'):
                b_list = segs_by_cat[cat][ori]
                if not b_list:
                    continue
                u = unary_union(b_list)
                comps = list(u.geoms) if hasattr(u, 'geoms') else [u]
                for comp in comps:
                    core = comp.buffer(-80.0, join_style=2)
                    if core.is_empty:
                        core = comp.buffer(-40.0, join_style=2)
                    if not wall_u.is_empty:
                        core = core.difference(wall_u)
                    sub_comps = list(core.geoms) if hasattr(core, 'geoms') else [core]
                    for sc in sub_comps:
                        if sc.is_empty:
                            continue
                        minx, miny, maxx, maxy = sc.bounds
                        L = (maxx - minx) if ori == 'H' else (maxy - miny)
                        T = (maxy - miny) if ori == 'H' else (maxx - minx)
                        if L < 250.0 or T > 320.0:
                            continue
                        T_use = 150.0
                        if ori == 'H':
                            ym = 0.5 * (miny + maxy)
                            r = box(minx, ym - T_use / 2.0, maxx, ym + T_use / 2.0)
                        else:
                            xm = 0.5 * (minx + maxx)
                            r = box(xm - T_use / 2.0, miny, xm + T_use / 2.0, maxy)
                        raw_strips[ori].append((cat, r))

        # Generate solid corner posts where horizontal and vertical window/parapet runs meet without a wall
        for idx_h, (cat_h, rh) in enumerate(raw_strips['H']):
            for idx_v, (cat_v, rv) in enumerate(raw_strips['V']):
                if rh.buffer(45.0).intersects(rv.buffer(45.0)):
                    hx0, hy0, hx1, hy1 = rh.bounds
                    vx0, vy0, vx1, vy1 = rv.bounds
                    post = box(vx0, hy0, vx1, hy1)
                    if wall_u.is_empty or post.intersection(wall_u).area < 0.3 * post.area:
                        if not any(post.intersection(cp).area > 0.5 * post.area for cp in self.corner_posts):
                            self.corner_posts.append(post)
                        # Extend H and V strips so they meet the corner post with 0 mm gap
                        rh = box(min(hx0, vx0), hy0, max(hx1, vx1), hy1)
                        rv = box(vx0, min(vy0, hy0), vx1, max(vy1, hy1))
                        raw_strips['H'][idx_h] = (cat_h, rh)
                        raw_strips['V'][idx_v] = (cat_v, rv)

        block_u = unary_union(([wall_u] if not wall_u.is_empty else []) + self.corner_posts)
        out: List[Wall] = []
        for ori in ('H', 'V'):
            for cat, r in raw_strips[ori]:
                rem = r.difference(block_u) if not block_u.is_empty else r
                if not rem.is_empty:
                    eroded = rem.buffer(-25.0, join_style=2)
                    if not eroded.is_empty:
                        rem = eroded.buffer(25.0, join_style=2)
                parts = list(rem.geoms) if hasattr(rem, 'geoms') else [rem]
                for p in parts:
                    if p.is_empty or p.area < 1e4:
                        continue
                    minx, miny, maxx, maxy = p.bounds
                    L = (maxx - minx) if ori == 'H' else (maxy - miny)
                    T = (maxy - miny) if ori == 'H' else (maxx - minx)
                    if L < 250.0 or T > 320.0:
                        continue
                    if ori == 'H':
                        ym = 0.5 * (miny + maxy)
                        p0, p1 = (minx, ym), (maxx, ym)
                        rect = box(minx, ym - T / 2.0, maxx, ym + T / 2.0)
                    else:
                        xm = 0.5 * (minx + maxx)
                        p0, p1 = (xm, miny), (xm, maxy)
                        rect = box(xm - T / 2.0, miny, xm + T / 2.0, maxy)
                    if not covered.is_empty and rect.intersection(covered).area > 0.4 * rect.area:
                        continue
                    covered = unary_union([covered, rect.buffer(20.0)]) if not covered.is_empty else rect.buffer(20.0)
                    if cat == 'PARAPET':
                        self.parapet_polys.append(rect)
                    ring = [tuple(q) for q in list(rect.exterior.coords)[:-1]]
                    pieces = []
                    sill_h = 600.0 if cat == 'PARAPET' else self.get_window_sill_height(L, cat)
                    if sill_h > 0:
                        pieces.append(('sill', 0.0, sill_h))
                    pieces.append(('lintel', HEAD_BASE, max(height - HEAD_BASE, 100.0)))
                    for kind, base, h in pieces:
                        out.append(Wall(id='', start_point=p0, end_point=p1, length=L,
                                        thickness=T, height=h, polygon=ring, wall_type='exterior' if cat == 'PARAPET' else 'interior',
                                        layer=cat, base=base, kind=kind, opening='window'))
        logger.info("Window runs: %d pieces (%d corner posts, %d parapet segments)",
                    len(out), len(self.corner_posts), len(self.parapet_polys))
        return out

    def from_geometric_windows(self, windows: list, height: float, offset: Tuple[float, float]) -> List[Wall]:
        """
        Creates Sill and Lintel pieces from geometric window symbols detected in drawings
        (where windows are drawn as multi-line clusters directly on the Plan layer).
        """
        ox, oy = offset
        out: List[Wall] = []
        n_s = n_h = 0
        for w in windows:
            poly_geom = w['poly']
            shifted = translate(poly_geom, xoff=-ox, yoff=-oy)
            mrr = shifted.minimum_rotated_rectangle
            if mrr.geom_type != 'Polygon':
                continue
            c = list(mrr.exterior.coords)[:4]
            d1 = math.dist(c[0], c[1])
            d2 = math.dist(c[1], c[2])
            L, T = max(d1, d2), min(d1, d2)
            if d1 >= d2:
                s_mid = ((c[0][0] + c[3][0]) / 2, (c[0][1] + c[3][1]) / 2)
                e_mid = ((c[1][0] + c[2][0]) / 2, (c[1][1] + c[2][1]) / 2)
            else:
                s_mid = ((c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2)
                e_mid = ((c[2][0] + c[3][0]) / 2, (c[2][1] + c[3][1]) / 2)

            ring = [tuple(pt) for pt in list(shifted.exterior.coords)[:-1]]

            # Standard window (5ft / 1500mm): 600mm sill -> 1500mm opening -> 2100mm lintel
            # Toilet ventilator (0.9m / 900mm): 1200mm sill -> 900mm opening -> 2100mm lintel
            if w.get('type') == 'toilet' or L <= 1000.0:
                sill_h = HEAD_BASE - VENT_WINDOW_H   # 1200mm
            else:
                sill_h = HEAD_BASE - WINDOW_H        # 600mm

            lintel_base = HEAD_BASE
            lintel_h = max(height - lintel_base, 100.0)

            # Sill
            n_s += 1
            out.append(Wall(
                id=f"Sill_{n_s:03d}", start_point=s_mid, end_point=e_mid, length=L, thickness=T,
                height=sill_h, polygon=ring, wall_type='exterior', layer='WINDOW',
                base=0.0, kind='sill', opening='window'
            ))

            # Lintel
            n_h += 1
            out.append(Wall(
                id=f"Lintel_{n_h:03d}", start_point=s_mid, end_point=e_mid, length=L, thickness=T,
                height=lintel_h, polygon=ring, wall_type='exterior', layer='WINDOW',
                base=lintel_base, kind='lintel', opening='window'
            ))
        logger.info("Geometric windows: %d pieces created", len(out))
        return out

    # find_door_lintels() was removed: it used a hard-coded list of door coordinates for one drawing.
    # Doors are now detected from the wall geometry in cad_processor/architecture.py (detect_openings).
