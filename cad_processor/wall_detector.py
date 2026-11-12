import logging
import math
from typing import Any, Dict, List

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from .cleaner import CADCleaner
from .models import CADEntity

logger = logging.getLogger(__name__)

MIN_THICKNESS = 60.0
MAX_THICKNESS = 600.0
MAX_FALLBACK_SEGMENTS = 60000


def _ring_polygon(points) -> Polygon:
    poly = Polygon(points)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def _closing(geom, d: float):
    """Morphological closing: fills the gap between parallel wall edges with square end caps."""
    return geom.buffer(d, cap_style=3, join_style=2, mitre_limit=3.0).buffer(-d, join_style=2, mitre_limit=3.0)


class WallDetector:
    """
    STEP 4 - wall detection.

    1. Layer based: entities on WALL-like layers.
         * closed polylines  -> already a wall outline, kept as is
         * open lines/polys  -> closed (gap-filled) into wall outlines
    2. Geometry based (no wall layer): all remaining linework is gap-filled and
       the wall mass is split into rectangles using parallel edge pairs.
    """

    def __init__(self):
        self.method = ''
        self.windows = []
        self.corner_posts = []
        self.shaft_points = []

    def detect_walls(self, entities: List[CADEntity]) -> List[Dict[str, Any]]:
        wall_ents = [e for e in entities
                     if CADCleaner.is_wall_layer(e.layer) and e.entity_type != 'CIRCLE']
        # polylines drawn back to their start point without the "closed" flag are closed outlines
        fixed = []
        for e in wall_ents:
            if (not e.is_closed and len(e.points) >= 4 and e.entity_type in ('LWPOLYLINE', 'POLYLINE')
                    and math.dist(e.points[0], e.points[-1]) <= 2.0):
                e = CADEntity(e.entity_type, e.layer, list(e.points[:-1]), True, dict(e.attributes))
            fixed.append(e)
        wall_ents = fixed
        if wall_ents and all(e.layer == 'WALL_RASTER' for e in wall_ents):
            # produced by raster_walls: one closed rectangle per wall, junctions already analysed
            self.method = 'raster'
            out = []
            for e in wall_ents:
                if e.is_closed and len(e.points) >= 3:
                    p = _ring_polygon(e.points)
                    if not p.is_empty and p.geom_type == 'Polygon' and p.area > 0:
                        out.append({'polygon': p, 'layer': 'WALL_RASTER', 'method': 'raster'})
            return out
        if wall_ents:
            other = [e for e in entities if not CADCleaner.is_wall_layer(e.layer) and len(e.points) >= 2
                     and e.entity_type in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC')]
            if not self._wall_layer_covers_plan(wall_ents, other):
                logger.warning("Wall layer(s) %s lie away from the main drawing (%d other entities) - "
                               "ignoring them and detecting walls from the plan geometry",
                               sorted({e.layer for e in wall_ents}), len(other))
                self.method = 'geometry'
                return self._from_geometry(other)
            self.method = 'layer'
            return self._from_layers(wall_ents)
        self.method = 'geometry'
        return self._from_geometry(entities)

    @staticmethod
    def _wall_layer_covers_plan(wall_ents: List[CADEntity], other: List[CADEntity]) -> bool:
        """True when the WALL-named layer is the wall set of the drawing being read: it overlaps the bulk of the
        remaining plan linework. False when the remaining linework is a substantial drawing of its own located
        elsewhere (e.g. a reference/overlay wall layer drawn in another part of the sheet)."""
        if len(other) < 150:
            return True
        wx = np.array([p[0] for e in wall_ents for p in e.points], float)
        wy = np.array([p[1] for e in wall_ents for p in e.points], float)
        if wx.size == 0:
            return False
        mids = np.array([np.mean(e.points, axis=0) for e in other], float)
        pad = 0.05 * max(np.ptp(wx), np.ptp(wy), 1.0)
        inside = ((mids[:, 0] >= wx.min() - pad) & (mids[:, 0] <= wx.max() + pad) &
                  (mids[:, 1] >= wy.min() - pad) & (mids[:, 1] <= wy.max() + pad))
        # the plan linework (rooms, door arcs, fixtures, windows) normally sits inside the wall envelope
        return float(inside.mean()) >= 0.25

    @staticmethod
    def _snap_ortho_dir(u: np.ndarray, tol_sin: float = 0.014) -> np.ndarray:
        """Snap unit direction vector within ~0.8 deg of 0/90 deg to exact axis alignment."""
        if abs(u[1]) <= tol_sin:
            return np.array([1.0 if u[0] >= 0 else -1.0, 0.0])
        if abs(u[0]) <= tol_sin:
            return np.array([0.0, 1.0 if u[1] >= 0 else -1.0])
        return u

    # ── layer based ──────────────────────────────────────
    @staticmethod
    def is_structural_layer(layer: str) -> bool:
        """RCC columns / shear walls / pillars: kept at their full drawn size (often 300-900 mm thick)."""
        import re
        return bool(re.search(r'(^|[^A-Z])(COL|COLS|COLUMN|COLUMNS|PILLAR|PILLARS|SHEAR|RCC)([^A-Z]|$)', layer.upper()))

    def _structural_pieces(self, ents: List[CADEntity]) -> List[Dict[str, Any]]:
        """Columns and shear walls are drawn as closed outlines (sometimes as loose lines). They are never
        furniture, so none of the thickness filters apply: every closed outline becomes a solid piece."""
        from shapely.ops import polygonize
        polys = []
        lines = []
        for e in ents:
            if e.entity_type == 'HATCH':
                continue
            if e.is_closed and len(e.points) >= 3:
                p = _ring_polygon(e.points)
                if not p.is_empty and p.geom_type == 'Polygon':
                    polys.append(p)
            elif len(e.points) >= 2:
                lines.append(LineString(e.points))
        if lines:
            polys += [p for p in polygonize(unary_union(lines)) if p.area >= 1.0e4]
        if not polys:
            return []
        merged = unary_union(polys).buffer(0.5, join_style=2).buffer(-0.5, join_style=2)
        out = []
        for g in (merged.geoms if hasattr(merged, 'geoms') else [merged]):
            if g.geom_type != 'Polygon' or g.area < 1.0e4:
                continue
            g = Polygon(g.exterior)                      # a column outline is solid (no hatch islands)
            mrr = g.minimum_rotated_rectangle
            if not g.buffer(-700.0, join_style=2).is_empty:
                continue                                 # a room-sized loop (> 1.4 m solid), not a column / shear wall
            if g.area / max(mrr.area, 1e-6) > 0.92:
                out.append({'polygon': g, 'layer': 'COL', 'method': 'column'})
                continue
            # L / T shaped shear walls -> split into rectangles so every piece has a clean axis
            rects = self._split_by_edge_pairs(g, max_thickness=1200.0)
            cov = unary_union(rects) if rects else Polygon()
            if rects and cov.area >= 0.97 * g.area:
                # make the rectangles disjoint (largest first) so no part of the column is lost as a "duplicate"
                remaining = g
                for r in sorted(rects, key=lambda q: -q.area):
                    piece = r.intersection(remaining).buffer(0)
                    for pg in (piece.geoms if hasattr(piece, 'geoms') else [piece]):
                        if pg.geom_type == 'Polygon' and pg.area >= 1.0e4:
                            out.append({'polygon': pg, 'layer': 'COL', 'method': 'column'})
                    remaining = remaining.difference(piece).buffer(0)
                for pg in (remaining.geoms if hasattr(remaining, 'geoms') else [remaining]):
                    if pg.geom_type == 'Polygon' and pg.area >= 1.0e4:
                        out.append({'polygon': pg, 'layer': 'COL', 'method': 'column'})
            else:
                out.append({'polygon': g, 'layer': 'COL', 'method': 'column'})
        return out

    def _from_layers(self, ents: List[CADEntity]) -> List[Dict[str, Any]]:
        col_ents = [e for e in ents if self.is_structural_layer(e.layer)]
        columns = self._structural_pieces(col_ents)
        ents = [e for e in ents if not self.is_structural_layer(e.layer)]
        if not ents:
            return self._resolve_overlaps(columns)
        out: List[Dict[str, Any]] = []
        closed_polys: List[Polygon] = []
        open_lines = []

        hatch_polys = [
            _ring_polygon(e.points) for e in ents
            if e.entity_type == 'HATCH' and len(e.points) >= 3
        ]
        hatch_polys = [p for p in hatch_polys if not p.is_empty and p.geom_type == 'Polygon']
        has_wall_hatches = len(hatch_polys) >= 25
        hatch_zone = unary_union(hatch_polys).buffer(15.0) if has_wall_hatches else None

        for e in ents:
            up = e.layer.upper()
            if e.is_closed and len(e.points) >= 3:
                poly = _ring_polygon(e.points)
                if not poly.is_empty and poly.geom_type == 'Polygon':
                    if has_wall_hatches and 'BMA' in up and e.entity_type != 'HATCH':
                        if poly.intersection(hatch_zone).area < 0.25 * poly.area:
                            continue            # unhatched exterior ledge / projection outline on BMA layer
                    r = poly.minimum_rotated_rectangle
                    if r.geom_type == 'Polygon':
                        c = list(r.exterior.coords)
                        a, b = math.dist(c[0], c[1]), math.dist(c[1], c[2])
                        if poly.area / max(r.area, 1e-6) > 0.90 and min(a, b) < 60.0:
                            continue            # thin decorative trim / panelling strip (< 60 mm)
                        if poly.area / max(r.area, 1e-6) > 0.85 and min(a, b) > 350.0 and max(a, b) > 950.0:
                            continue            # kitchen counter / wardrobe / stair block (> 350 mm thick): not a wall
                        if poly.area / max(r.area, 1e-6) > 0.75 and min(a, b) > 1000 and max(a, b) < 2.5 * min(a, b):
                            continue            # huge blocky site solid: not a wall/column
                    closed_polys.append(poly)
            else:
                ln = LineString(e.points)
                if has_wall_hatches and 'BMA' in up:
                    if not ln.intersects(hatch_zone):
                        continue
                open_lines.append(ln)

        open_polys: List[Polygon] = []
        if open_lines:
            if len(open_lines) > 2000:
                open_lines = [l for l in open_lines if l.length >= 80.0]
            if len(open_lines) > 5000:
                chunks = [open_lines[i:i + 3000] for i in range(0, len(open_lines), 3000)]
                merged = unary_union([unary_union(c) for c in chunks])
            else:
                merged = unary_union(open_lines)
            from shapely.ops import polygonize
            wall_loops = [p for p in polygonize(merged) if p.area >= 1.5e4 and p.buffer(-220.0).is_empty]
            if len(wall_loops) >= 10:
                closed_polys.extend(wall_loops)
                rem_lines = merged.difference(unary_union(wall_loops).boundary.buffer(2.0))
            else:
                rem_lines = merged
            if not rem_lines.is_empty:
                close_d = 120.0 if len(closed_polys) >= 10 else (MAX_THICKNESS / 2.0)
                filled = _closing(rem_lines, close_d)
                for g in (filled.geoms if hasattr(filled, 'geoms') else [filled]):
                    if g.geom_type == 'Polygon' and g.area >= 2e4:
                        open_polys.append(g)

        all_raw = closed_polys + open_polys
        if not all_raw:
            return self._resolve_overlaps(columns)

        combined = unary_union(all_raw).buffer(0.5, join_style=2).buffer(-0.5, join_style=2)
        geoms = list(combined.geoms) if hasattr(combined, 'geoms') else [combined]
        layer = ents[0].layer
        max_split_t = 350.0
        min_keep_t = 60.0 if len(closed_polys) >= 10 else MIN_THICKNESS

        for g in geoms:
            if g.geom_type != 'Polygon' or g.area < 1.5e4:
                continue
            mrr = g.minimum_rotated_rectangle
            simp = g.simplify(0.5, preserve_topology=True)
            is_simple_rect = (g.area / max(mrr.area, 1e-6) > 0.92) and len(simp.exterior.coords) <= 6
            if is_simple_rect:
                rc = list(mrr.exterior.coords)[:4]
                d_min = min(math.dist(rc[0], rc[1]), math.dist(rc[1], rc[2]))
                d_max = max(math.dist(rc[0], rc[1]), math.dist(rc[1], rc[2]))
                if min_keep_t <= d_min and (d_min <= max_split_t or d_max <= 950.0):
                    out.append({'polygon': g, 'layer': layer, 'method': 'layer-rect'})
            else:
                rects = self._split_by_edge_pairs(g, max_thickness=max_split_t)
                if rects:
                    cov = unary_union(rects)
                    residual = g.difference(cov)
                    res_geoms = list(residual.geoms) if hasattr(residual, 'geoms') else [residual]
                    for rg in res_geoms:
                        if rg.geom_type != 'Polygon' or rg.area <= 5e3:
                            continue
                        rmrr = rg.minimum_rotated_rectangle
                        if rmrr.geom_type == 'Polygon' and rg.area / max(rmrr.area, 1e-6) >= 0.88:
                            rc_r = list(rmrr.exterior.coords)[:4]
                            if min(math.dist(rc_r[0], rc_r[1]), math.dist(rc_r[1], rc_r[2])) <= max_split_t:
                                rects.append(rmrr)
                        else:
                            r2 = self._split_by_edge_pairs(rg, max_thickness=max_split_t)
                            rects.extend(r2)
                            res2 = rg.difference(unary_union(r2) if r2 else Polygon())
                            for rg2 in (res2.geoms if hasattr(res2, 'geoms') else [res2]):
                                if rg2.geom_type == 'Polygon' and rg2.area > 5e3:
                                    rmrr2 = rg2.minimum_rotated_rectangle
                                    if rmrr2.geom_type == 'Polygon' and rg2.area / max(rmrr2.area, 1e-6) >= 0.85:
                                        rc_r2 = list(rmrr2.exterior.coords)[:4]
                                        if min(math.dist(rc_r2[0], rc_r2[1]), math.dist(rc_r2[1], rc_r2[2])) <= max_split_t:
                                            rects.append(rmrr2)
                    for r in rects:
                        rc = list(r.minimum_rotated_rectangle.exterior.coords)[:4]
                        d_min = min(math.dist(rc[0], rc[1]), math.dist(rc[1], rc[2]))
                        d_max = max(math.dist(rc[0], rc[1]), math.dist(rc[1], rc[2]))
                        if min_keep_t <= d_min and (d_min <= max_split_t or d_max <= 950.0):
                            out.append({'polygon': r, 'layer': layer, 'method': 'layer-pairs'})
                else:
                    out.append({'polygon': g, 'layer': layer, 'method': 'layer-open'})

        out = self._resolve_overlaps(columns + out)
        logger.info("Layer detection: %d candidate wall outlines (%d structural columns)", len(out), len(columns))
        return out

    @staticmethod
    def _resolve_overlaps(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Hatches, outlines and block copies often describe the same wall. Process biggest first;
        a piece that is >=75 % covered is a duplicate (dropped); a partly covered piece keeps only
        its uncovered remainder, so the final pieces never overlap.
        """
        from shapely.strtree import STRtree
        items = sorted(items, key=lambda it: (0 if it.get('method') == 'column' else 1, -it['polygon'].area))
        kept: List[Dict[str, Any]] = []
        geoms: List[Polygon] = []
        tree = None
        dirty = True
        for it in items:
            poly = it['polygon']
            if dirty:
                tree = STRtree(geoms) if geoms else None
                dirty = False
            overl = []
            if tree is not None:
                for idx in tree.query(poly):
                    if poly.intersects(geoms[idx]):
                        overl.append(geoms[idx])
            if overl:
                covered = unary_union(overl)
                rest = poly.difference(covered)
                parts = list(rest.geoms) if hasattr(rest, 'geoms') else [rest]
                if rest.area < 0.25 * poly.area:
                    # mostly a duplicate: keep only solid leftovers (a real notch / jamb), never thin slivers
                    parts = [p for p in parts if p.geom_type == 'Polygon' and p.area >= 2.0e4
                             and not p.buffer(-30.0, join_style=2).is_empty]
                    if not parts:
                        continue
                parts = [p for p in parts if p.geom_type == 'Polygon' and p.area > 5e3]
                new = [dict(it, polygon=p) for p in parts]
            else:
                new = [it]
            for n in new:
                kept.append(n)
                geoms.append(n['polygon'])
                dirty = True
        return kept

    @classmethod
    def _dedup_and_merge_lines(cls, raw_lines: List[ tuple ]) -> List[ tuple ]:
        """
        Fast O(N log N) deduplication and collinear merging of line segments.
        Snaps near-orthogonal segments (within 0.6 deg of 0/90 deg) to exact horizontal/vertical.
        """
        import collections
        buckets = collections.defaultdict(list)
        for a, b in raw_lines:
            v = b - a
            L = float(np.hypot(v[0], v[1]))
            if L <= 10.0:
                continue
            u = v / L
            # Snap near-horizontal or near-vertical segments around their midpoint
            if abs(u[1]) <= 0.0105:
                mid_y = round(0.5 * (a[1] + b[1]), 1)
                x0, x1 = min(a[0], b[0]), max(a[0], b[0])
                a = np.array([x0, mid_y], dtype=float)
                b = np.array([x1, mid_y], dtype=float)
                u = np.array([1.0, 0.0])
            elif abs(u[0]) <= 0.0105:
                mid_x = round(0.5 * (a[0] + b[0]), 1)
                y0, y1 = min(a[1], b[1]), max(a[1], b[1])
                a = np.array([mid_x, y0], dtype=float)
                b = np.array([mid_x, y1], dtype=float)
                u = np.array([0.0, 1.0])
            else:
                if u[0] < -1e-6 or (abs(u[0]) <= 1e-6 and u[1] < 0):
                    a, b = b, a
                    u = -u
            ang_key = round(math.degrees(math.atan2(u[1], u[0])), 1)
            n = np.array([-u[1], u[0]])
            perp = float(np.dot(a, n))
            s0, s1 = float(np.dot(a, u)), float(np.dot(b, u))
            if s0 > s1:
                s0, s1 = s1, s0
            buckets[ang_key].append((perp, s0, s1, u, n))

        merged_lines = []
        for ang_key, segs in buckets.items():
            segs.sort(key=lambda x: (x[0], x[1]))
            # Group segments whose perpendicular offsets are within 1.5 mm
            i = 0
            m = len(segs)
            while i < m:
                j = i + 1
                while j < m and abs(segs[j][0] - segs[i][0]) <= 1.5:
                    j += 1
                group = sorted(segs[i:j], key=lambda x: x[1])
                cur_p, cur_s0, cur_s1, u, n = group[0]
                p_sum = cur_p * (cur_s1 - cur_s0)
                w_sum = cur_s1 - cur_s0
                for p, s0, s1, _, _ in group[1:]:
                    if s0 <= cur_s1 + 2.0:
                        if s1 > cur_s1:
                            p_sum += p * (s1 - cur_s1)
                            w_sum += (s1 - cur_s1)
                            cur_s1 = s1
                    else:
                        avg_p = p_sum / max(w_sum, 1e-6)
                        p0 = u * cur_s0 + n * avg_p
                        p1 = u * cur_s1 + n * avg_p
                        merged_lines.append((p0, p1))
                        cur_p, cur_s0, cur_s1 = p, s0, s1
                        p_sum = p * (s1 - s0)
                        w_sum = s1 - s0
                avg_p = p_sum / max(w_sum, 1e-6)
                p0 = u * cur_s0 + n * avg_p
                p1 = u * cur_s1 + n * avg_p
                merged_lines.append((p0, p1))
                i = j
        return merged_lines

    # ── geometry based ───────────────────────────────────
    def _from_geometry(self, ents: List[CADEntity]) -> List[Dict[str, Any]]:
        import collections
        from shapely.geometry import box

        all_lines = []
        door_arcs = []
        for e in ents:
            # Exclude ARC and CIRCLE from wall edge lines (ARCs on single-layer plans are door swings)
            if e.entity_type in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'SPLINE'):
                pts = e.points + ([e.points[0]] if e.is_closed else [])
                for p0, p1 in zip(pts, pts[1:]):
                    a = np.array(p0, dtype=float)
                    b = np.array(p1, dtype=float)
                    if np.hypot(*(b - a)) > 10.0:
                        all_lines.append((a, b))
            elif e.entity_type == 'ARC' and len(e.points) >= 5:
                pts = e.points
                p_s = np.array(pts[0], dtype=float)
                p_m = np.array(pts[len(pts) // 2], dtype=float)
                p_e = np.array(pts[-1], dtype=float)
                ax_, ay_ = p_s
                bx_, by_ = p_m
                cx_, cy_ = p_e
                det = 2.0 * (ax_ * (by_ - cy_) + bx_ * (cy_ - ay_) + cx_ * (ay_ - by_))
                if abs(det) > 1e-3:
                    ux = ((ax_ * ax_ + ay_ * ay_) * (by_ - cy_) + (bx_ * bx_ + by_ * by_) * (cy_ - ay_) + (cx_ * cx_ + cy_ * cy_) * (ay_ - by_)) / det
                    uy = ((ax_ * ax_ + ay_ * ay_) * (cx_ - bx_) + (bx_ * bx_ + by_ * by_) * (ax_ - cx_) + (cx_ * cx_ + cy_ * cy_) * (bx_ - ax_)) / det
                    ctr = np.array([ux, uy], dtype=float)
                    rad = float(np.hypot(*(p_s - ctr)))
                    if 500.0 <= rad <= 1450.0:
                        angs = [math.atan2(p[1] - uy, p[0] - ux) for p in pts]
                        sweep = sum(abs((b_a - a_a + math.pi) % (2.0 * math.pi) - math.pi) for a_a, b_a in zip(angs, angs[1:]))
                        if math.radians(65.0) <= sweep <= math.radians(115.0):
                            door_arcs.append((ctr, p_s, p_e, rad))

        if not all_lines:
            return []

        unique_lines = self._dedup_and_merge_lines(all_lines)
        if len(unique_lines) > 4500:
            unique_lines.sort(key=lambda ab: -float(np.hypot(*(ab[1] - ab[0]))))
            unique_lines = unique_lines[:4500]
        n_lines = len(unique_lines)

        # Precompute line vectors, lengths, directions, normals
        L_arr = np.zeros(n_lines, dtype=float)
        U_arr = np.zeros((n_lines, 2), dtype=float)
        N_arr = np.zeros((n_lines, 2), dtype=float)
        A_arr = np.zeros((n_lines, 2), dtype=float)
        B_arr = np.zeros((n_lines, 2), dtype=float)
        for idx, (a, b) in enumerate(unique_lines):
            v = b - a
            l = float(np.hypot(v[0], v[1]))
            u = self._snap_ortho_dir(v / max(l, 1e-9))
            A_arr[idx] = a
            B_arr[idx] = b
            L_arr[idx] = l
            U_arr[idx] = u
            N_arr[idx] = (-u[1], u[0])

        # 0a. Detect diagonal X-crosses in service shafts / lift wells / ducts
        shaft_cross_indices = set()
        shaft_points = []
        diag_cand = [i for i in range(n_lines)
                     if 300.0 <= L_arr[i] <= 6000.0 and min(abs(U_arr[i, 0]), abs(U_arr[i, 1])) > 0.15]
        for idx_a in range(len(diag_cand)):
            i = diag_cand[idx_a]
            mid_i = 0.5 * (A_arr[i] + B_arr[i])
            for idx_b in range(idx_a + 1, len(diag_cand)):
                j = diag_cand[idx_b]
                if abs(L_arr[i] - L_arr[j]) > 120.0:
                    continue
                mid_j = 0.5 * (A_arr[j] + B_arr[j])
                if np.hypot(*(mid_i - mid_j)) <= 60.0 and abs(np.dot(U_arr[i], U_arr[j])) < 0.92:
                    shaft_cross_indices.add(i)
                    shaft_cross_indices.add(j)
                    shaft_points.append((float(0.5 * (mid_i[0] + mid_j[0])), float(0.5 * (mid_i[1] + mid_j[1]))))
        self.shaft_points = shaft_points

        # 0b. Detect staircase tread stacks (>= 4 parallel equal-length lines spaced 180..340 mm apart)
        stair_line_indices = set()
        stair_polys = []
        stair_cand = [i for i in range(n_lines) if 650.0 <= L_arr[i] <= 2600.0 and i not in shaft_cross_indices]
        for i in stair_cand:
            if i in stair_line_indices:
                continue
            a1, u1, n1, l1 = A_arr[i], U_arr[i], N_arr[i], L_arr[i]
            steps = [(0.0, i)]
            for j in stair_cand:
                if j == i:
                    continue
                if abs(L_arr[j] - l1) > 150.0 or abs(np.dot(u1, U_arr[j])) < 0.999:
                    continue
                da = float(np.dot(A_arr[j] - a1, n1))
                db = float(np.dot(B_arr[j] - a1, n1))
                if abs(da - db) > 3.0 or abs(da) > 4500.0:
                    continue
                t2a = float(np.dot(A_arr[j] - a1, u1))
                t2b = float(np.dot(B_arr[j] - a1, u1))
                lo, hi = min(t2a, t2b), max(t2a, t2b)
                if abs(lo) <= 120.0 and abs(hi - l1) <= 120.0:
                    steps.append((0.5 * (da + db), j))
            if len(steps) < 4:
                continue
            steps.sort(key=lambda x: x[0])
            # Group double-riser lines (within 45 mm) into tread clusters
            tread_groups = [[steps[0]]]
            for d_val, idx_val in steps[1:]:
                if abs(d_val - tread_groups[-1][-1][0]) <= 45.0:
                    tread_groups[-1].append((d_val, idx_val))
                else:
                    tread_groups.append([(d_val, idx_val)])
            if len(tread_groups) < 4:
                continue
            # Find contiguous run of >= 4 treads spaced 180..340 mm apart
            run = [tread_groups[0]]
            for grp in tread_groups[1:]:
                gap = grp[0][0] - run[-1][-1][0]
                if 180.0 <= gap <= 340.0:
                    run.append(grp)
                else:
                    if len(run) >= 4:
                        break
                    run = [grp]
            if len(run) >= 4:
                for grp in run:
                    for _, idx_val in grp:
                        stair_line_indices.add(idx_val)
                d_min = run[0][0][0] - 20.0
                d_max = run[-1][-1][0] + 20.0
                # Inset slightly along u1 (by 25 mm) so stairwell walls along the sides are NOT excluded
                p0 = a1 + u1 * 25.0 + n1 * d_min
                p1 = a1 + u1 * (l1 - 25.0) + n1 * d_min
                p2 = a1 + u1 * (l1 - 25.0) + n1 * d_max
                p3 = a1 + u1 * 25.0 + n1 * d_max
                stair_polys.append(Polygon([p0, p1, p2, p3]))

        if stair_polys:
            stair_zone = unary_union(stair_polys)
            for idx in range(n_lines):
                if idx not in stair_line_indices and L_arr[idx] < 3500.0:
                    seg = LineString([A_arr[idx], B_arr[idx]])
                    if stair_zone.contains(seg) or seg.intersection(stair_zone).length > 0.85 * L_arr[idx]:
                        stair_line_indices.add(idx)
            logger.info("Geometry fallback: excluded %d staircase lines across %d stair flights",
                        len(stair_line_indices), len(stair_polys))

        # 0c. Exclude facade louver fin combs (>= 5 short aligned parallel teeth spaced <= 260 mm apart)
        louver_line_indices = set()
        louver_boxes = []
        louver_cand = [i for i in range(n_lines)
                       if 45.0 <= L_arr[i] <= 260.0 and i not in stair_line_indices and i not in shaft_cross_indices]
        for i in louver_cand:
            if i in louver_line_indices:
                continue
            a1, u1, n1, l1 = A_arr[i], U_arr[i], N_arr[i], L_arr[i]
            fins = [(0.0, i)]
            for j in louver_cand:
                if j == i or abs(L_arr[j] - l1) > 20.0 or abs(np.dot(u1, U_arr[j])) < 0.999:
                    continue
                da = float(np.dot(A_arr[j] - a1, n1))
                db = float(np.dot(B_arr[j] - a1, n1))
                if abs(da - db) > 2.5 or abs(da) > 3000.0:
                    continue
                t2a = float(np.dot(A_arr[j] - a1, u1))
                t2b = float(np.dot(B_arr[j] - a1, u1))
                if abs(min(t2a, t2b)) <= 20.0 and abs(max(t2a, t2b) - l1) <= 20.0:
                    fins.append((0.5 * (da + db), j))
            if len(fins) < 6:
                continue
            fins.sort(key=lambda x: x[0])
            run_f = [fins[0]]
            for item_f in fins[1:]:
                if item_f[0] - run_f[-1][0] <= 260.0:
                    run_f.append(item_f)
                else:
                    if len(run_f) >= 6 and run_f[-1][0] - run_f[0][0] >= 450.0:
                        break
                    run_f = [item_f]
            if len(run_f) >= 6 and run_f[-1][0] - run_f[0][0] >= 450.0:
                for _, idx_f in run_f:
                    louver_line_indices.add(idx_f)
                d0_f, d1_f = run_f[0][0] - 15.0, run_f[-1][0] + 15.0
                louver_boxes.append(Polygon([
                    a1 - u1 * 10.0 + n1 * d0_f,
                    a1 + u1 * (l1 + 10.0) + n1 * d0_f,
                    a1 + u1 * (l1 + 10.0) + n1 * d1_f,
                    a1 - u1 * 10.0 + n1 * d1_f,
                ]))
        if louver_boxes:
            lz = unary_union(louver_boxes)
            for idx in range(n_lines):
                if idx not in louver_line_indices and L_arr[idx] <= 90.0:
                    if lz.contains(LineString([A_arr[idx], B_arr[idx]])):
                        louver_line_indices.add(idx)

        # 1. Histogram of parallel line distances to identify dominant wall thicknesses
        dist_counts = collections.defaultdict(int)
        sample_indices = [i for i in range(n_lines)
                          if L_arr[i] >= 150.0
                          and i not in stair_line_indices
                          and i not in shaft_cross_indices
                          and i not in louver_line_indices][:800]
        for idx_a in range(len(sample_indices)):
            i = sample_indices[idx_a]
            a1, u1, n1, l1 = A_arr[i], U_arr[i], N_arr[i], L_arr[i]
            for idx_b in range(idx_a + 1, len(sample_indices)):
                j = sample_indices[idx_b]
                if abs(np.dot(u1, U_arr[j])) < 0.9995:
                    continue
                da = float(np.dot(A_arr[j] - a1, n1))
                db = float(np.dot(B_arr[j] - a1, n1))
                if abs(da - db) > 2.5:
                    continue
                dist = 0.5 * abs(da + db)
                if not (60.0 <= dist <= 700.0):
                    continue
                t2a = float(np.dot(A_arr[j] - a1, u1))
                t2b = float(np.dot(B_arr[j] - a1, u1))
                lo, hi = max(0.0, min(t2a, t2b)), min(l1, max(t2a, t2b))
                if hi - lo > max(120.0, 0.9 * dist):
                    dist_counts[round(dist / 5.0) * 5.0] += 1

        wall_thicknesses = [d for d, c in dist_counts.items() if c >= 3 and 70.0 <= d <= 320.0]
        dominant_t = max(dist_counts.items(), key=lambda x: x[1])[0] if dist_counts else 200.0
        max_t = min(320.0, max(wall_thicknesses + [240.0]) + 20.0)
        logger.info("Geometry fallback: dominant thickness = %.0f mm, max wall thickness = %.0f mm", dominant_t, max_t)

        # 2. Detect multi-line window symbols (3 or 4 parallel lines across a single wall thickness,
        # including 3-line jamb-bounded windows and 4-line mitred L-corner / U-bay windows)
        long_turn_cands = [idx for idx in range(n_lines)
                           if L_arr[idx] >= 220.0
                           and idx not in stair_line_indices
                           and idx not in shaft_cross_indices
                           and idx not in louver_line_indices]

        def _has_perp_turn_endpoint(pt_xy: np.ndarray, u_vec: np.ndarray, tol: float = 8.0) -> bool:
            for k_idx in long_turn_cands:
                if abs(np.dot(u_vec, U_arr[k_idx])) > 0.15:
                    continue
                if np.hypot(*(A_arr[k_idx] - pt_xy)) <= tol or np.hypot(*(B_arr[k_idx] - pt_xy)) <= tol:
                    return True
            return False

        raw_windows = []
        win_line_indices = set()
        for i in range(n_lines):
            if i in stair_line_indices or i in shaft_cross_indices or i in louver_line_indices:
                continue
            a1, b1, u1, n1, l1 = A_arr[i], B_arr[i], U_arr[i], N_arr[i], L_arr[i]
            if l1 < 250.0 or l1 > 8000.0:
                continue
            cands = [(0.0, i, True, 0.0, l1)]
            for j in range(n_lines):
                if j == i or j in stair_line_indices or j in shaft_cross_indices or j in louver_line_indices:
                    continue
                if abs(np.dot(u1, U_arr[j])) < 0.999:
                    continue
                da = float(np.dot(A_arr[j] - a1, n1))
                db = float(np.dot(B_arr[j] - a1, n1))
                if abs(da - db) > 2.5:
                    continue
                dist_signed = 0.5 * (da + db)
                if not (15.0 <= abs(dist_signed) <= max_t + 10.0):
                    continue
                t2a = float(np.dot(A_arr[j] - a1, u1))
                t2b = float(np.dot(B_arr[j] - a1, u1))
                lo, hi = min(t2a, t2b), max(t2a, t2b)
                mitre_tol = min(abs(dist_signed) + 35.0, max_t + 25.0)
                ov = min(l1, hi) - max(0.0, lo)
                if ov < min(180.0, 0.70 * l1):
                    continue
                if abs(lo) < 45.0 and abs(hi - l1) < 45.0:
                    cands.append((dist_signed, j, True, lo, hi))
                elif lo <= mitre_tol and hi >= l1 - mitre_tol:
                    cands.append((dist_signed, j, False, lo, hi))

            cands.sort(key=lambda x: x[0])
            # Deduplicate offsets within 10 mm (preferring exact-length / shorter bounded glass lines)
            dedup = []
            for item in cands:
                d_val, idx_val, is_ex, lo, hi = item
                if not dedup or abs(d_val - dedup[-1][0]) >= 10.0:
                    dedup.append(item)
                else:
                    prev = dedup[-1]
                    if (is_ex and not prev[2]) or (is_ex == prev[2] and (hi - lo) < (prev[4] - prev[3])):
                        dedup[-1] = item

            # Extract contiguous chain containing 0.0 where consecutive gaps are <= 160 mm
            zero_pos = next((k for k, item in enumerate(dedup) if item[1] == i), None)
            if zero_pos is None:
                continue
            lo_k = hi_k = zero_pos
            while lo_k > 0 and dedup[lo_k][0] - dedup[lo_k - 1][0] <= 160.0:
                lo_k -= 1
            while hi_k + 1 < len(dedup) and dedup[hi_k + 1][0] - dedup[hi_k][0] <= 160.0:
                hi_k += 1
            chain = dedup[lo_k:hi_k + 1]
            while len(chain) > 1 and chain[-1][0] - chain[0][0] > max_t + 10.0:
                if abs(chain[-1][0]) >= abs(chain[0][0]):
                    chain.pop()
                else:
                    chain.pop(0)

            if len(chain) < 3:
                continue
            d_min, d_max = chain[0][0], chain[-1][0]
            if not (60.0 <= d_max - d_min <= max_t + 10.0):
                continue
            inner = chain[1:-1]
            min_clear = 20.0 if len(inner) == 1 else 14.0
            if not all(d_min + min_clear <= it[0] <= d_max - min_clear for it in inner):
                continue

            need = 3 if l1 <= 3500.0 else 4
            n_exact = sum(1 for it in chain if it[2])

            has_jamb_0 = has_jamb_1 = False
            for j_idx in range(n_lines):
                if j_idx in stair_line_indices or j_idx in shaft_cross_indices or j_idx in louver_line_indices:
                    continue
                if abs(np.dot(u1, U_arr[j_idx])) > 0.15:
                    continue
                pa = A_arr[j_idx] - a1
                pb = B_arr[j_idx] - a1
                s_j = 0.5 * float(np.dot(pa + pb, u1))
                if not (abs(s_j) <= 35.0 or abs(s_j - l1) <= 35.0):
                    continue
                na, nb = float(np.dot(pa, n1)), float(np.dot(pb, n1))
                n_lo, n_hi = min(na, nb), max(na, nb)
                if n_lo <= d_min + 15.0 and n_hi >= d_max - 15.0:
                    if abs(s_j) <= 35.0:
                        has_jamb_0 = True
                    if abs(s_j - l1) <= 35.0:
                        has_jamb_1 = True
                    if has_jamb_0 and has_jamb_1:
                        break

            mitre_0 = mitre_1 = False
            if len(inner) >= 2:
                if all(-(max_t + 25.0) <= it[3] <= abs(it[0]) + 35.0 for it in inner):
                    turns_0 = sum(
                        1 for it in inner
                        if _has_perp_turn_endpoint(a1 + u1 * it[3] + n1 * it[0], u1)
                    )
                    mitre_0 = turns_0 >= 2
                if all(l1 - (abs(it[0]) + 35.0) <= it[4] <= l1 + max_t + 25.0 for it in inner):
                    turns_1 = sum(
                        1 for it in inner
                        if _has_perp_turn_endpoint(a1 + u1 * it[4] + n1 * it[0], u1)
                    )
                    mitre_1 = turns_1 >= 2

            inner_ok_0 = (has_jamb_0 and all(abs(it[3]) < 45.0 for it in inner)) or mitre_0
            inner_ok_1 = (has_jamb_1 and all(abs(it[4] - l1) < 45.0 for it in inner)) or mitre_1

            valid_win = False
            if len(chain) >= need and n_exact >= need:
                valid_win = True
            elif l1 > 3500.0 and n_exact >= 3 and len(chain) >= 4:
                valid_win = True
            elif inner_ok_0 and inner_ok_1 and (len(inner) >= 2 or l1 <= 3600.0):
                valid_win = True

            if valid_win:
                s_w0 = min([0.0] + [it[3] for it in chain if it[3] >= -(max_t + 25.0)]) if (mitre_0 and not has_jamb_0) else 0.0
                s_w1 = max([l1] + [it[4] for it in chain if it[4] <= l1 + max_t + 25.0]) if (mitre_1 and not has_jamb_1) else l1
                p0 = a1 + u1 * s_w0 + n1 * d_min
                p1 = a1 + u1 * s_w1 + n1 * d_min
                p2 = a1 + u1 * s_w1 + n1 * d_max
                p3 = a1 + u1 * s_w0 + n1 * d_max
                poly = Polygon([p0, p1, p2, p3])
                raw_windows.append({
                    'length': s_w1 - s_w0, 'poly': poly, 'u': u1.copy(), 'n': n1.copy(),
                    'thick': d_max - d_min, 'mitre': (mitre_0 or mitre_1),
                })
                for it in inner:
                    win_line_indices.add(it[1])
                for it in (chain[0], chain[-1]):
                    if it[2]:
                        win_line_indices.add(it[1])

        # Deduplicate overlapping window candidates (preferring full mitre-extended spans)
        raw_windows.sort(key=lambda w: (-int(w['mitre']), -w['poly'].area))
        windows = []
        for w in raw_windows:
            if any(w['poly'].intersection(ex['poly']).area > 0.72 * min(w['poly'].area, ex['poly'].area) for ex in windows):
                continue
            windows.append(w)

        # Where perpendicular multi-line windows meet at an L-corner or U-bay corner, keep a solid corner post
        # and trim both window spans cleanly against it so neither window overlaps the corner post.
        corner_posts = []
        for ia in range(len(windows)):
            for ib in range(ia + 1, len(windows)):
                wa, wb = windows[ia], windows[ib]
                if abs(np.dot(wa['u'], wb['u'])) > 0.25:
                    continue
                pa, pb = wa['poly'], wb['poly']
                if not pa.buffer(25.0, join_style=2).intersects(pb.buffer(25.0, join_style=2)):
                    continue
                is_ortho_pair = (min(abs(wa['u'][0]), abs(wa['u'][1])) <= 0.015
                                 and min(abs(wb['u'][0]), abs(wb['u'][1])) <= 0.015)
                if is_ortho_pair:
                    if abs(wa['u'][0]) >= abs(wa['u'][1]):
                        hx0, hy0, hx1, hy1 = pa.bounds
                        vx0, vy0, vx1, vy1 = pb.bounds
                    else:
                        hx0, hy0, hx1, hy1 = pb.bounds
                        vx0, vy0, vx1, vy1 = pa.bounds
                    post = box(vx0, hy0, vx1, hy1)
                else:
                    inter = pa.buffer(12.0, join_style=2).intersection(pb.buffer(12.0, join_style=2))
                    if inter.is_empty:
                        continue
                    post = inter.minimum_rotated_rectangle
                if post.is_empty or post.area < 2.5e3:
                    continue
                if not any(post.intersection(cp).area > 0.5 * post.area for cp in corner_posts):
                    corner_posts.append(post)
                for w_item in (wa, wb):
                    rem = w_item['poly'].difference(post).buffer(0)
                    parts = [g for g in (rem.geoms if hasattr(rem, 'geoms') else [rem]) if g.geom_type == 'Polygon' and g.area > 5e3]
                    if parts:
                        best_p = max(parts, key=lambda g: g.area).minimum_rotated_rectangle
                        rc_w = list(best_p.exterior.coords)[:4]
                        w_len = max(math.dist(rc_w[0], rc_w[1]), math.dist(rc_w[1], rc_w[2]))
                        w_item['poly'] = best_p
                        w_item['length'] = w_len

        for w in windows:
            w['type'] = 'toilet' if w['length'] <= 1000.0 else 'standard'
        self.windows = windows
        self.corner_posts = corner_posts
        logger.info("Geometry fallback: detected %d multi-line window symbols (%d corner posts)", len(windows), len(corner_posts))

        # 2b. Exclude thin closed strips (15..62 mm thick, e.g. open door leaves and 25 mm shower glass)
        # so their long edges do not pair with adjacent walls to form bloated/shifted wall slabs
        thin_caps = [idx for idx in range(n_lines) if 14.0 <= L_arr[idx] <= 95.0]
        thin_strip_indices = set()
        for i in range(n_lines):
            if (i in stair_line_indices or i in shaft_cross_indices
                    or i in louver_line_indices or i in win_line_indices or i in thin_strip_indices):
                continue
            l1 = L_arr[i]
            if not (250.0 <= l1 <= 1600.0):
                continue
            a1, u1, n1 = A_arr[i], U_arr[i], N_arr[i]
            for j in range(i + 1, n_lines):
                if j in stair_line_indices or j in shaft_cross_indices or j in louver_line_indices or j in win_line_indices:
                    continue
                if abs(L_arr[j] - l1) > 80.0 or abs(np.dot(u1, U_arr[j])) < 0.999:
                    continue
                da = float(np.dot(A_arr[j] - a1, n1))
                db = float(np.dot(B_arr[j] - a1, n1))
                if abs(da - db) > 2.5:
                    continue
                dist = 0.5 * abs(da + db)
                if not (15.0 <= dist <= 62.0):
                    continue
                t2a = float(np.dot(A_arr[j] - a1, u1))
                t2b = float(np.dot(B_arr[j] - a1, u1))
                lo, hi = min(t2a, t2b), max(t2a, t2b)
                if min(l1, hi) - max(0.0, lo) < 0.85 * min(l1, L_arr[j]):
                    continue
                if abs(lo) <= 10.0 or abs(hi - l1) <= 10.0:
                    # Check if capped at either end by a short perpendicular segment covering the strip thickness
                    n_lo_strip, n_hi_strip = min(0.0, 0.5 * (da + db)), max(0.0, 0.5 * (da + db))
                    has_cap = False
                    for c_idx in thin_caps:
                        if abs(np.dot(u1, U_arr[c_idx])) > 0.15:
                            continue
                        pa = A_arr[c_idx] - a1
                        pb = B_arr[c_idx] - a1
                        sc_val = 0.5 * float(np.dot(pa + pb, u1))
                        if not (abs(sc_val) <= 15.0 or abs(sc_val - l1) <= 15.0 or abs(sc_val - lo) <= 15.0 or abs(sc_val - hi) <= 15.0):
                            continue
                        nca, ncb = float(np.dot(pa, n1)), float(np.dot(pb, n1))
                        if min(nca, ncb) <= n_lo_strip + 5.0 and max(nca, ncb) >= n_hi_strip - 5.0:
                            has_cap = True
                            break
                    if has_cap:
                        thin_strip_indices.add(i)
                        thin_strip_indices.add(j)

        # 3. Detect candidate wall slabs from parallel line pairs
        slab_records = []
        valid_indices = [
            i for i in range(n_lines)
            if L_arr[i] >= 80.0
            and i not in stair_line_indices
            and i not in shaft_cross_indices
            and i not in louver_line_indices
            and i not in thin_strip_indices
        ]
        for idx_a in range(len(valid_indices)):
            i = valid_indices[idx_a]
            a1, u1, n1, l1 = A_arr[i], U_arr[i], N_arr[i], L_arr[i]
            is_ortho = min(abs(u1[0]), abs(u1[1])) <= 0.015
            u_can = u1 if (u1[0] > 1e-6 or (abs(u1[0]) <= 1e-6 and u1[1] >= 0)) else -u1
            n_can = np.array([-u_can[1], u_can[0]])
            ang_can = round(math.degrees(math.atan2(u_can[1], u_can[0])), 1)
            for idx_b in range(idx_a + 1, len(valid_indices)):
                j = valid_indices[idx_b]
                if abs(np.dot(u1, U_arr[j])) < 0.9995:
                    continue
                da = float(np.dot(A_arr[j] - a1, n1))
                db = float(np.dot(B_arr[j] - a1, n1))
                if abs(da - db) > 2.5:
                    continue
                dist_signed = 0.5 * (da + db)
                dist = abs(dist_signed)
                if not (MIN_THICKNESS <= dist <= max_t):
                    continue
                t2a = float(np.dot(A_arr[j] - a1, u1))
                t2b = float(np.dot(B_arr[j] - a1, u1))
                lo, hi = max(0.0, min(t2a, t2b)), min(l1, max(t2a, t2b))
                overlap = hi - lo
                if overlap < max(80.0, 0.85 * dist):
                    continue
                # Non-orthogonal pairs must have strong mutual overlap to avoid accidental distant alignments
                if not is_ortho and overlap < 0.5 * min(l1, L_arr[j]):
                    continue
                p0 = a1 + u1 * lo
                p1 = a1 + u1 * hi
                off = n1 * dist_signed
                poly = Polygon([p0, p1, p1 + off, p0 + off])
                if poly.is_valid and poly.area > 0:
                    s0_c, s1_c = sorted((float(np.dot(p0, u_can)), float(np.dot(p1, u_can))))
                    p0_c, p1_c = sorted((float(np.dot(p0, n_can)), float(np.dot(p0 + off, n_can))))
                    slab_records.append((poly, ang_can, s0_c, s1_c, p0_c, p1_c, dist))

        # Reject exterior chajja / sunshade / ledge projections: wide slabs (>= 235 mm) glued face-to-face
        # alongside an already-detected thinner standard wall or multi-line window (60..230 mm)
        thin_refs = collections.defaultdict(list)
        for _, ang_c, s0_c, s1_c, p0_c, p1_c, d_c in slab_records:
            if 60.0 <= d_c <= 230.0:
                thin_refs[ang_c].append((s0_c, s1_c, p0_c, p1_c, d_c))
        for w in windows:
            uw = w['u']
            u_can = uw if (uw[0] > 1e-6 or (abs(uw[0]) <= 1e-6 and uw[1] >= 0)) else -uw
            n_can = np.array([-u_can[1], u_can[0]])
            ang_c = round(math.degrees(math.atan2(u_can[1], u_can[0])), 1)
            pts_w = np.asarray(w['poly'].exterior.coords[:-1], dtype=float)
            s_vals = pts_w @ u_can
            p_vals = pts_w @ n_can
            dw = float(p_vals.max() - p_vals.min())
            if 60.0 <= dw <= 230.0:
                thin_refs[ang_c].append((float(s_vals.min()), float(s_vals.max()), float(p_vals.min()), float(p_vals.max()), dw))

        slabs = []
        for poly, ang_c, s0_c, s1_c, p0_c, p1_c, d_c in slab_records:
            if d_c >= 235.0:
                span_len = max(s1_c - s0_c, 1e-6)
                is_chajja = False
                for rs0, rs1, rp0, rp1, rd in thin_refs.get(ang_c, ()):
                    if d_c < 1.35 * rd or (d_c + rd) < 340.0:
                        continue
                    if abs(p0_c - rp1) <= 4.0 or abs(p1_c - rp0) <= 4.0:
                        if min(s1_c, rs1) - max(s0_c, rs0) >= 0.45 * span_len:
                            is_chajja = True
                            break
                if is_chajja:
                    continue
            slabs.append(poly)

        wall_union = unary_union(slabs) if slabs else Polygon()

        # 4. Single-line centerline fallback (only used if no double-line wall slabs were found)
        if wall_union.is_empty:
            single_partitions = []
            for i in valid_indices:
                if i in win_line_indices or L_arr[i] < 350.0:
                    continue
                t = dominant_t if 80.0 <= dominant_t <= 200.0 else 200.0
                a, b, u = A_arr[i], B_arr[i], U_arr[i]
                n = np.array([-u[1], u[0]]) * (t / 2.0)
                poly = Polygon([a + n, b + n, b - n, a - n])
                single_partitions.append(poly)
            if single_partitions:
                logger.info("Geometry fallback: recovered %d single-line partition walls", len(single_partitions))
                wall_union = unary_union(single_partitions)

        # 5a. Cut untrimmed walls across doorways proven by a 90-deg door swing arc
        if door_arcs and not wall_union.is_empty:
            w_probe = wall_union.buffer(35.0, join_style=2)
            door_cuts = []
            for ctr, p_s, p_e, rad in door_arcs:
                arms = [(p_s, p_e), (p_e, p_s)]
                for p_wall, p_open in arms:
                    seg_w = LineString([ctr, p_wall])
                    seg_o = LineString([ctr, p_open])
                    if seg_w.length < 450.0:
                        continue
                    in_w = seg_w.intersection(w_probe).length / seg_w.length
                    in_o = seg_o.intersection(wall_union).length / max(seg_o.length, 1e-6)
                    if in_w >= 0.75 and in_o <= 0.30:
                        u_dw = self._snap_ortho_dir((ctr - p_wall) / max(float(np.hypot(*(ctr - p_wall))), 1e-9))
                        n_dw = np.array([-u_dw[1], u_dw[0]])
                        # Include adjacent door-frame jamb / open door-leaf thickness on latch & hinge sides when present
                        ext_latch = 0.0
                        ext_hinge = 0.0
                        for k_idx in range(n_lines):
                            if L_arr[k_idx] < 50.0 or abs(np.dot(u_dw, U_arr[k_idx])) > 0.15:
                                continue
                            s_latch = 0.5 * float(np.dot((A_arr[k_idx] - p_wall) + (B_arr[k_idx] - p_wall), u_dw))
                            if -65.0 <= s_latch <= -10.0 and L_arr[k_idx] >= 90.0:
                                ext_latch = max(ext_latch, -s_latch)
                            s_hinge = 0.5 * float(np.dot((A_arr[k_idx] - ctr) + (B_arr[k_idx] - ctr), u_dw))
                            if 15.0 <= s_hinge <= 65.0:
                                ext_hinge = max(ext_hinge, s_hinge)
                        c0 = p_wall - u_dw * ext_latch
                        c1 = ctr + u_dw * ext_hinge
                        cut_half_t = max_t + 40.0
                        door_cuts.append(Polygon([
                            c0 - n_dw * cut_half_t, c1 - n_dw * cut_half_t,
                            c1 + n_dw * cut_half_t, c0 + n_dw * cut_half_t,
                        ]))
                        break
            if door_cuts:
                wall_union = wall_union.difference(unary_union(door_cuts))
                logger.info("Geometry fallback: cut %d untrimmed doorway(s) proven by door swing arcs", len(door_cuts))

        # 5b. Subtract window openings (buffered across wall thickness only so jambs and corner posts stay exact)
        if windows and not wall_union.is_empty:
            win_boxes = []
            for w in windows:
                n_w = w['n'] * 6.0
                pts_w = np.asarray(w['poly'].exterior.coords[:-1], dtype=float)
                u_w = w['u']
                s_vals = pts_w @ u_w
                p_vals = pts_w @ w['n']
                s0_w, s1_w = float(s_vals.min()), float(s_vals.max())
                p0_w, p1_w = float(p_vals.min()) - 6.0, float(p_vals.max()) + 6.0
                win_boxes.append(Polygon([
                    u_w * s0_w + w['n'] * p0_w,
                    u_w * s1_w + w['n'] * p0_w,
                    u_w * s1_w + w['n'] * p1_w,
                    u_w * s0_w + w['n'] * p1_w,
                ]))
            win_cut = unary_union(win_boxes)
            if corner_posts:
                win_cut = win_cut.difference(unary_union(corner_posts))
            wall_union = wall_union.difference(win_cut)

        # 6. Decompose into clean rectangular wall pieces
        geoms = list(wall_union.geoms) if hasattr(wall_union, 'geoms') else ([wall_union] if not wall_union.is_empty else [])
        out: List[Dict[str, Any]] = []
        for g in geoms:
            if g.geom_type != 'Polygon' or g.area < 1e4:
                continue
            rects = self._split_by_edge_pairs(g, max_thickness=max_t)
            if rects:
                for rect in rects:
                    out.append({'polygon': rect, 'layer': 'geometry', 'method': 'geometry-pairs'})
                cov = unary_union(rects)
                residual = g.difference(cov)
                res_geoms = list(residual.geoms) if hasattr(residual, 'geoms') else [residual]
                for rg in res_geoms:
                    if rg.geom_type == 'Polygon' and rg.area > 8e3:
                        rmrr = rg.minimum_rotated_rectangle
                        if rmrr.geom_type == 'Polygon':
                            rc = list(rmrr.exterior.coords)[:4]
                            r_short = min(math.dist(rc[0], rc[1]), math.dist(rc[1], rc[2]))
                            if rg.area / max(rmrr.area, 1e-6) > 0.88 and MIN_THICKNESS <= r_short <= max_t + 10.0:
                                out.append({'polygon': rmrr, 'layer': 'geometry', 'method': 'geometry-residual'})
            else:
                mrr = g.minimum_rotated_rectangle
                if mrr.geom_type == 'Polygon':
                    rc = list(mrr.exterior.coords)[:4]
                    r_short = min(math.dist(rc[0], rc[1]), math.dist(rc[1], rc[2]))
                    if g.area / max(mrr.area, 1e-6) > 0.88 and r_short <= max_t + 20.0:
                        out.append({'polygon': mrr, 'layer': 'geometry', 'method': 'geometry-open'})

        out = self._bridge_column_boxes(out, all_lines, wall_union, windows=windows, corner_posts=corner_posts)
        out = self._resolve_overlaps(out)
        logger.info("Geometry detection: %d clean wall pieces", len(out))
        return out

    @staticmethod
    def _bridge_column_boxes(out, raw_lines, wall_union, windows=None, corner_posts=None) -> List[Dict[str, Any]]:
        """Small closed boxes drawn in thin lines (RCC columns, duct / shaft boxes, often with an X) that sit
        where two walls would meet. The double-line walls stop at the box, so without it the room behind
        leaks to the outside. A box that touches two separate wall/window ends becomes a solid column filling
        the corner (box + the wall ends it touches, flush against any window jamb)."""
        from shapely.ops import polygonize
        if wall_union.is_empty or not out:
            return out
        # test against the final wall pieces (the raw wall mass can contain a box whose two edges looked like a
        # wall pair but was dropped again when the mass was split into wall rectangles), plus subtracted windows
        solid_wall_union = unary_union([d['polygon'] for d in out])
        win_polys = [w['poly'] for w in (windows or [])]
        win_union = unary_union(win_polys) if win_polys else Polygon()
        envelope_union = unary_union([d['polygon'] for d in out] + win_polys + list(corner_posts or []))
        # raw segments (before collinear merging, which joins a box edge to the wall face it lines up with);
        # diagonals are left out so a box marked with an X stays one face
        short = []
        for a, b in raw_lines:
            v = b - a
            L = float(np.hypot(v[0], v[1]))
            if 100.0 <= L <= 1300.0 and min(abs(v[0]), abs(v[1])) <= 0.02 * L:
                u = v / L * 3.0                         # extend 3 mm so endpoints that stop a hair short still node
                short.append(LineString([np.round(a - u, 1), np.round(b + u, 1)]))
        if not short or len(short) > 6000:
            return out
        try:
            faces = list(polygonize(unary_union(short)))
        except Exception:
            return out
        # a box split by a mid line polygonizes into several small faces: also try them merged back together
        small = [f for f in faces if f.area <= 1.2e6]
        if small:
            merged = unary_union([f.buffer(1.0, join_style=2) for f in small]).buffer(-1.0, join_style=2)
            groups = [g for g in (merged.geoms if hasattr(merged, 'geoms') else [merged]) if g.geom_type == 'Polygon']
            faces = [f for f in small if f.area >= 0.025e6] + [Polygon(g.exterior) for g in groups]
        reach = 160.0
        added = []
        for f in faces:
            if not (0.025e6 <= f.area <= 1.1e6):
                continue
            mrr = f.minimum_rotated_rectangle
            if mrr.geom_type != 'Polygon' or f.area / max(mrr.area, 1e-6) < 0.9:
                continue
            c = list(mrr.exterior.coords)[:4]
            sa, sb = math.dist(c[0], c[1]), math.dist(c[1], c[2])
            if not (150.0 <= min(sa, sb) and max(sa, sb) <= 1100.0):
                continue
            if f.intersection(solid_wall_union).area > 0.4 * f.area:
                continue                                   # already wall
            if not win_union.is_empty and f.intersection(win_union).area > 0.3 * f.area:
                continue                                   # already window
            touch = f.buffer(reach, join_style=2).intersection(envelope_union)
            parts = [g for g in (touch.geoms if hasattr(touch, 'geoms') else [touch])
                     if g.geom_type == 'Polygon' and g.area > 2.0e3]
            if len(parts) < 2:
                continue                                   # touches one wall (or a single corner): furniture / fixture
            # the touched wall ends must be on different sides of the box (a real bridge, not two walls of one corner)
            cx, cy = f.centroid.x, f.centroid.y
            dirs = []
            for g in parts:
                dx, dy = g.centroid.x - cx, g.centroid.y - cy
                n = math.hypot(dx, dy) or 1.0
                dirs.append((dx / n, dy / n))
            if max(-(a[0] * b[0] + a[1] * b[1]) for k, a in enumerate(dirs) for b in dirs[k + 1:]) < -0.2:
                continue
            wall_touch = f.buffer(reach, join_style=2).intersection(solid_wall_union)
            wall_parts = [g for g in (wall_touch.geoms if hasattr(wall_touch, 'geoms') else [wall_touch])
                          if g.geom_type == 'Polygon' and g.area > 2.0e3]
            x0, y0, x1, y1 = unary_union([f] + wall_parts).bounds
            # extend across the full thickness of every wall it joins, so no sliver is left beside the column
            for d in out:
                p = d['polygon']
                if d.get('method') == 'column' or not p.intersects(f.buffer(reach, join_style=2)):
                    continue
                px0, py0, px1, py1 = p.bounds
                if px1 - px0 <= 400.0 and py1 - py0 > px1 - px0:          # vertical wall
                    x0, x1 = min(x0, px0), max(x1, px1)
                elif py1 - py0 <= 400.0 and px1 - px0 > py1 - py0:        # horizontal wall
                    y0, y1 = min(y0, py0), max(y1, py1)
            # snap flush up to any touched window jamb / corner post without extending into the window opening
            fx0, fy0, fx1, fy1 = f.bounds
            for wp in win_polys + list(corner_posts or []):
                if not wp.intersects(f.buffer(reach, join_style=2)):
                    continue
                wx0, wy0, wx1, wy1 = wp.bounds
                if wx1 <= fx0 + 5.0 and fx0 - wx1 <= reach:
                    x0 = min(x0, wx1)
                elif wx0 >= fx1 - 5.0 and wx0 - fx1 <= reach:
                    x1 = max(x1, wx0)
                if wy1 <= fy0 + 5.0 and fy0 - wy1 <= reach:
                    y0 = min(y0, wy1)
                elif wy0 >= fy1 - 5.0 and wy0 - fy1 <= reach:
                    y1 = max(y1, wy0)
            col = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            if col.area > 2.0e6 or any(col.intersection(a).area > 0.5 * col.area for a in added):
                continue
            added.append(col)
            out.append({'polygon': col, 'layer': 'COL', 'method': 'column'})
        if added:
            logger.info("Geometry detection: %d column / duct box(es) bridge wall ends", len(added))
        return out

    @classmethod
    def _split_by_edge_pairs(cls, poly: Polygon, max_thickness: float = MAX_THICKNESS) -> List[Polygon]:
        """
        Decompose a wall union polygon into clean, non-overlapping rectangular wall segments
        using antiparallel edge pairs. Extends rectangles across L/T corners so no corner squares
        or L-shaped residuals are left behind, and subtracts already-picked walls so pieces meet
        flush face-to-end without overlapping.
        """
        poly = poly.simplify(0.5, preserve_topology=True)
        rings = [np.asarray(poly.exterior.coords)] + [np.asarray(r.coords) for r in poly.interiors]
        edges = []
        for ring in rings:
            for a, b in zip(ring[:-1], ring[1:]):
                v = b - a
                l = float(np.hypot(v[0], v[1]))
                if l > 50.0:
                    u = cls._snap_ortho_dir(v / l)
                    edges.append((a, b, u, l))

        rects: List[Polygon] = []
        probe = poly.buffer(2.0, join_style=2)
        for i in range(len(edges)):
            a1, b1, d1, l1 = edges[i]
            n1 = np.array([-d1[1], d1[0]])
            for j in range(i + 1, len(edges)):
                a2, b2, d2, l2 = edges[j]
                if np.dot(d1, d2) > -0.9995:
                    continue
                da = float(np.dot(a2 - a1, n1))
                db = float(np.dot(b2 - a1, n1))
                if abs(da - db) > 2.5:
                    continue
                dist_signed = 0.5 * (da + db)
                dist = abs(dist_signed)
                if not (MIN_THICKNESS <= dist <= max_thickness):
                    continue
                t2a = float(np.dot(a2 - a1, d1))
                t2b = float(np.dot(b2 - a1, d1))
                t2_lo, t2_hi = min(t2a, t2b), max(t2a, t2b)
                lo = max(0.0, t2_lo)
                hi = min(l1, t2_hi)
                if hi - lo < 50.0:
                    continue
                off = n1 * dist_signed

                def _make_rect(s0, s1):
                    p0 = a1 + d1 * s0
                    p1 = a1 + d1 * s1
                    return Polygon([p0, p1, p1 + off, p0 + off])

                # Extend along the longer edge (across L/T junctions and step-outs) as far as both faces remain inside probe
                s_lo_bound = min(0.0, t2_lo)
                s_hi_bound = max(l1, t2_hi)
                if s_lo_bound < lo - 1.0 or s_hi_bound > hi + 1.0:
                    mid_s = 0.5 * (lo + hi)
                    sgn = 1.0 if dist_signed >= 0 else -1.0
                    n_in1 = n1 * (sgn * 3.0)
                    n_in2 = n1 * (dist_signed - sgn * 3.0)

                    def _span_at_mid(n_off):
                        seg_line = LineString([a1 + d1 * s_lo_bound + n_off, a1 + d1 * s_hi_bound + n_off])
                        inter = seg_line.intersection(probe)
                        parts = list(inter.geoms) if hasattr(inter, 'geoms') else ([inter] if not inter.is_empty else [])
                        for pt_g in parts:
                            if pt_g.geom_type == 'LineString':
                                c0 = np.asarray(pt_g.coords[0]) - a1
                                c1 = np.asarray(pt_g.coords[-1]) - a1
                                u0, u1 = float(np.dot(c0, d1)), float(np.dot(c1, d1))
                                if u0 > u1:
                                    u0, u1 = u1, u0
                                if u0 - 2.0 <= mid_s <= u1 + 2.0:
                                    return u0, u1
                        return lo, hi

                    sa0, sa1 = _span_at_mid(n_in1)
                    sb0, sb1 = _span_at_mid(n_in2)
                    cand_lo = min(lo, max(sa0, sb0))
                    cand_hi = max(hi, min(sa1, sb1))
                    if cand_lo < lo - 1.0 or cand_hi > hi + 1.0:
                        r_ext = _make_rect(cand_lo, cand_hi)
                        if probe.contains(r_ext):
                            lo, hi = cand_lo, cand_hi

                rect = _make_rect(lo, hi)
                if rect.area > 0 and probe.contains(rect):
                    rects.append(rect)

        rects.sort(key=lambda r: -r.area)
        picked: List[Polygon] = []
        covered = Polygon()
        for r in rects:
            if not covered.is_empty and r.intersects(covered):
                rem = r.difference(covered)
                if rem.is_empty or rem.area < 4e3:
                    continue
                parts = list(rem.geoms) if hasattr(rem, 'geoms') else [rem]
            else:
                parts = [r]
            for p in parts:
                if p.geom_type != 'Polygon' or p.area < 4e3:
                    continue
                mrr = p.minimum_rotated_rectangle
                if mrr.geom_type != 'Polygon' or p.area / max(mrr.area, 1e-6) < 0.92:
                    continue
                c = list(mrr.exterior.coords)[:4]
                sa, sb = math.dist(c[0], c[1]), math.dist(c[1], c[2])
                if max(sa, sb) < 60.0 or min(sa, sb) < MIN_THICKNESS - 5.0:
                    continue
                # Keep exact rectangle geometry
                clean_p = p.simplify(0.5, preserve_topology=True)
                if len(clean_p.exterior.coords) != 5:
                    clean_p = mrr
                picked.append(clean_p)
                covered = covered.union(clean_p)
        return picked

