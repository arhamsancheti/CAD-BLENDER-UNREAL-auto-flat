import logging
from typing import List, Tuple

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .models import Wall

logger = logging.getLogger(__name__)

MIN_LENGTH = 100.0
MIN_THICKNESS = 40.0
DUP_CENTER_TOL = 5.0
CONTAINED_RATIO = 0.9
CLUSTER_GAP = 4500.0   # walls of one building are connected within max opening span (<= 4.5 m)


def _poly(w: Wall) -> Polygon:
    p = Polygon(w.polygon)
    return p if p.is_valid else p.buffer(0)


class WallValidator:
    """STEP 6 - fix invalid polygons, drop tiny/duplicate/contained walls, drop duplicate drawings."""

    def validate(self, walls: List[Wall], conn_tol: float = None, known_openings=None,
                 mm_per_px: float = None) -> Tuple[List[Wall], List[str]]:
        warnings: List[str] = []
        n0 = len(walls)
        self.topology = {}

        # tiny segments / invalid
        keep = []
        for w in walls:
            p = _poly(w)
            if p.is_empty or w.length < MIN_LENGTH or w.thickness < MIN_THICKNESS:
                continue
            keep.append(w)
        if n0 - len(keep):
            warnings.append(f"Removed {n0 - len(keep)} tiny/invalid wall pieces.")
        walls = keep

        # duplicate drawing copies or distant site/legend fragments (>8 m from main building)
        walls, msg = self._drop_duplicate_drawings(walls)
        if msg:
            warnings.append(msg)

        # connect corners, T-junctions, collinear breaks and stepped walls (real-world tolerance);
        # gaps too wide to be a break but too narrow to be an opening are reported, never closed
        from .wall_graph import default_tolerance, repair_topology
        tol = conn_tol or default_tolerance(walls, mm_per_px)
        walls, topo = repair_topology(walls, conn_tol=tol, known_openings=known_openings)
        self.topology = topo
        c = topo.get('counts', {})
        warnings.append(f"Connections repaired (tolerance {tol:.0f} mm): {c.get('L-corner', 0)} L-corners, "
                        f"{c.get('T-junction', 0)} T-junctions, {c.get('collinear', 0)} collinear breaks, "
                        f"{c.get('stepped', 0)} stepped joints; {topo.get('deduplicated', 0)} duplicates removed.")
        for u in topo.get('uncertain', []):
            warnings.append(f"Review: uncertain {u['width_mm']:.0f} mm wall gap at ({u['xy'][0]:.0f},{u['xy'][1]:.0f}) "
                            f"left open")

        # duplicates and walls contained inside another wall
        polys = [_poly(w) for w in walls]
        order = sorted(range(len(walls)), key=lambda i: -polys[i].area)
        kept_idx: List[int] = []
        dups = contained = 0
        for i in order:
            pi = polys[i]
            if pi.is_empty or pi.area < MIN_LENGTH * MIN_THICKNESS:
                continue
            drop = False
            for j in kept_idx:
                pj = polys[j]
                if not pi.envelope.intersects(pj.envelope):
                    continue
                inter = pi.intersection(pj).area
                if inter >= 0.75 * pi.area:
                    if abs(pi.area - pj.area) < 0.05 * pj.area:
                        dups += 1
                    else:
                        contained += 1
                    drop = True
                    break
            if not drop:
                kept_idx.append(i)
        walls = [walls[i] for i in sorted(kept_idx)]
        if dups:
            warnings.append(f"Removed {dups} duplicate walls.")
        if contained:
            warnings.append(f"Removed {contained} walls overlapped by another wall.")

        # gaps: report wall endpoints very close to but not touching another wall
        gaps = self._count_gaps(walls)
        if gaps:
            warnings.append(f"{gaps} small gaps (<50 mm) between walls detected.")
        return walls, warnings

    @staticmethod
    def connect_walls(walls: List[Wall], max_gap: float = 200.0) -> Tuple[List[Wall], str]:
        """
        LEGACY (superseded by wall_graph.repair_topology, which validate() now uses). Kept for reference.
        It bridged collinear gaps only up to 120 mm and required lateral alignment within 2.5 mm, so
        120-300 mm breaks and slightly offset pieces were left as silent holes.

        Closes corner gaps, connects T-junctions, and merges/bridges small collinear gaps
        so that all meeting walls touch flush face-to-end without tilting or overlapping.
        Every rectangular wall endpoint moves ONLY along its own original axis vector u,
        guaranteeing 0.0000 deg change in wall angle.
        """
        import math
        n = len(walls)
        if n < 2:
            return walls, ''

        # Record immutable axis parametrization for each rectangular wall:
        # P(s) = p0 + s * u, with s in [s0, s1]
        p0_list = []
        u_list = []
        n_list = []
        s0_list = []
        s1_list = []
        is_rect = []
        dropped = set()

        for w in walls:
            vx = w.end_point[0] - w.start_point[0]
            vy = w.end_point[1] - w.start_point[1]
            L = math.hypot(vx, vy)
            rect_flag = (getattr(w, 'shape', 'rectangle') == 'rectangle') and L >= 10.0
            if rect_flag:
                ux, uy = vx / L, vy / L
                # Snap near-orthogonal axis to exact 0 / 90 deg
                if abs(uy) <= 0.0105:
                    ux, uy = (1.0 if ux >= 0 else -1.0), 0.0
                    cy = round(0.5 * (w.start_point[1] + w.end_point[1]), 2)
                    p0 = (round(w.start_point[0], 2), cy)
                    L = abs(w.end_point[0] - w.start_point[0])
                elif abs(ux) <= 0.0105:
                    ux, uy = 0.0, (1.0 if uy >= 0 else -1.0)
                    cx = round(0.5 * (w.start_point[0] + w.end_point[0]), 2)
                    p0 = (cx, round(w.start_point[1], 2))
                    L = abs(w.end_point[1] - w.start_point[1])
                else:
                    p0 = (w.start_point[0], w.start_point[1])
                p0_list.append(p0)
                u_list.append((ux, uy))
                n_list.append((-uy, ux))
                s0_list.append(0.0)
                s1_list.append(L)
                is_rect.append(True)
            else:
                p0_list.append(w.start_point)
                u_list.append((1.0, 0.0))
                n_list.append((0.0, 1.0))
                s0_list.append(0.0)
                s1_list.append(L)
                is_rect.append(False)

        def get_pt(i: int, end: str) -> Tuple[float, float]:
            s = s0_list[i] if end == 's' else s1_list[i]
            return (p0_list[i][0] + s * u_list[i][0], p0_list[i][1] + s * u_list[i][1])

        def line_intersect_scalars(i: int, j: int):
            """Returns (si, sj, sin_a) where infinite lines i and j intersect."""
            ux1, uy1 = u_list[i]
            ux2, uy2 = u_list[j]
            cross = ux1 * uy2 - uy1 * ux2
            if abs(cross) < 1e-4:
                return None
            dx = p0_list[j][0] - p0_list[i][0]
            dy = p0_list[j][1] - p0_list[i][1]
            si = (dx * uy2 - dy * ux2) / cross
            sj = (dx * uy1 - dy * ux1) / cross
            return si, sj, abs(cross)

        l_snaps = t_snaps = c_snaps = 0
        locked_ends = set()   # (wall_idx, 's' | 'e')

        # 1. Merge or bridge collinear rectangular walls along their own axes
        for i in range(n):
            if not is_rect[i] or i in dropped:
                continue
            for j in range(i + 1, n):
                if not is_rect[j] or j in dropped:
                    continue
                ux1, uy1 = u_list[i]
                ux2, uy2 = u_list[j]
                dot = ux1 * ux2 + uy1 * uy2
                if abs(dot) < 0.9995:
                    continue
                nx1, ny1 = n_list[i]
                dx = p0_list[j][0] - p0_list[i][0]
                dy = p0_list[j][1] - p0_list[i][1]
                lateral = abs(dx * nx1 + dy * ny1)
                t1, t2 = walls[i].thickness, walls[j].thickness
                # Project j's interval onto i's axis
                ja = dx * ux1 + dy * uy1 + s0_list[j] * dot
                jb = dx * ux1 + dy * uy1 + s1_list[j] * dot
                j_lo, j_hi = min(ja, jb), max(ja, jb)
                i_lo, i_hi = s0_list[i], s1_list[i]

                # Same thickness and aligned centerline -> merge into one continuous wall if touching/close
                if lateral <= 2.5 and abs(t1 - t2) <= 5.0:
                    gap = max(i_lo - j_hi, j_lo - i_hi)
                    if gap <= 120.0:
                        s0_list[i] = min(i_lo, j_lo)
                        s1_list[i] = max(i_hi, j_hi)
                        dropped.add(j)
                        c_snaps += 1
                        continue

                # Stepped collinear walls of different thickness -> close longitudinal gap and lock meeting ends
                if lateral <= 0.5 * (t1 + t2) - 30.0:
                    if -20.0 <= j_lo - i_hi <= 150.0:
                        if j_lo > i_hi:
                            half_gap = 0.5 * (j_lo - i_hi)
                            s1_list[i] += half_gap
                            if ja <= jb:
                                s0_list[j] -= half_gap
                            else:
                                s1_list[j] += half_gap
                            c_snaps += 1
                        locked_ends.add((i, 'e'))
                        locked_ends.add((j, 's' if ja <= jb else 'e'))
                    elif -20.0 <= i_lo - j_hi <= 150.0:
                        if i_lo > j_hi:
                            half_gap = 0.5 * (i_lo - j_hi)
                            s0_list[i] -= half_gap
                            if ja <= jb:
                                s1_list[j] += half_gap
                            else:
                                s0_list[j] -= half_gap
                            c_snaps += 1
                        locked_ends.add((i, 's'))
                        locked_ends.add((j, 'e' if ja <= jb else 's'))

        # 2. Connect L-corners (endpoint to endpoint, flush non-overlapping corner joint)
        for i in range(n):
            if not is_rect[i] or i in dropped:
                continue
            for j in range(i + 1, n):
                if not is_rect[j] or j in dropped:
                    continue
                ux1, uy1 = u_list[i]
                ux2, uy2 = u_list[j]
                if abs(ux1 * ux2 + uy1 * uy2) > 0.707:
                    continue
                res = line_intersect_scalars(i, j)
                if res is None:
                    continue
                si, sj, sin_a = res
                t1, t2 = walls[i].thickness, walls[j].thickness
                tol = 0.5 * (t1 + t2) + max_gap

                # Check if intersection is near an unlocked endpoint of i and an unlocked endpoint of j
                end_i = None
                dist_i = 1e9
                for code, sval in (('s', s0_list[i]), ('e', s1_list[i])):
                    if (i, code) not in locked_ends and abs(si - sval) <= tol and abs(si - sval) < dist_i:
                        end_i, dist_i = code, abs(si - sval)
                end_j = None
                dist_j = 1e9
                for code, sval in (('s', s0_list[j]), ('e', s1_list[j])):
                    if (j, code) not in locked_ends and abs(sj - sval) <= tol and abs(sj - sval) < dist_j:
                        end_j, dist_j = code, abs(sj - sval)
                if end_i is None or end_j is None:
                    continue

                # Ensure moving the endpoints doesn't invert either wall
                ext_i = (0.5 * t2) / sin_a
                ext_j = (0.5 * t1) / sin_a
                len_i = s1_list[i] - s0_list[i]
                len_j = s1_list[j] - s0_list[j]
                if len_i < ext_i + MIN_LENGTH or len_j < ext_j + MIN_LENGTH:
                    continue

                # If either wall already protrudes > 15 mm past the outer face of the other wall,
                # it is a T-junction with a door/window jamb nib, NOT an L-corner (Step 3 handles it).
                if (end_i == 'e' and s1_list[i] > si + ext_i + 15.0) or (end_i == 's' and s0_list[i] < si - ext_i - 15.0):
                    continue
                if (end_j == 'e' and s1_list[j] > sj + ext_j + 15.0) or (end_j == 's' and s0_list[j] < sj - ext_j - 15.0):
                    continue

                # Primary wall extends through the corner to the outer corner;
                # secondary wall butts flush against the inner face of the primary wall (0 gap, 0 overlap)
                i_is_primary = (round(t1, 1), len_i) >= (round(t2, 1), len_j)
                if i_is_primary:
                    if end_i == 's':
                        s0_list[i] = si - ext_i
                    else:
                        s1_list[i] = si + ext_i
                    if end_j == 's':
                        s0_list[j] = sj + ext_j
                    else:
                        s1_list[j] = sj - ext_j
                else:
                    if end_j == 's':
                        s0_list[j] = sj - ext_j
                    else:
                        s1_list[j] = sj + ext_j
                    if end_i == 's':
                        s0_list[i] = si + ext_i
                    else:
                        s1_list[i] = si - ext_i

                locked_ends.add((i, end_i))
                locked_ends.add((j, end_j))
                l_snaps += 1

        # 3. Connect T-junctions (unlocked endpoint of w1 butts flush onto the side face of w2)
        for i in range(n):
            if not is_rect[i] or i in dropped:
                continue
            t1 = walls[i].thickness
            for end_i in ('s', 'e'):
                if (i, end_i) in locked_ends:
                    continue
                s_cur = s0_list[i] if end_i == 's' else s1_list[i]
                best_j = None
                best_dist = 1e9
                best_params = None
                for j in range(n):
                    if i == j or not is_rect[j] or j in dropped:
                        continue
                    ux1, uy1 = u_list[i]
                    ux2, uy2 = u_list[j]
                    if abs(ux1 * ux2 + uy1 * uy2) > 0.707:
                        continue
                    res = line_intersect_scalars(i, j)
                    if res is None:
                        continue
                    si, sj, sin_a = res
                    t2 = walls[j].thickness
                    tol = 0.5 * (t1 + t2) + max_gap
                    half_w1 = (0.5 * t1) / sin_a
                    # Intersection must lie within w2's span, and w2 must be able to cover w1's full width
                    if not (s0_list[j] - 25.0 <= sj <= s1_list[j] + 25.0):
                        continue
                    if (j, 's') in locked_ends and s0_list[j] > sj - half_w1 + 5.0:
                        continue
                    if (j, 'e') in locked_ends and s1_list[j] < sj + half_w1 - 5.0:
                        continue
                    face_off = (0.5 * t2) / sin_a
                    # Endpoint of w1 must be on the correct side of w2's centerline and NOT protruding past w2's far face
                    if end_i == 's' and (s1_list[i] <= si + face_off + MIN_LENGTH or s_cur < si - face_off - 15.0):
                        continue
                    if end_i == 'e' and (s0_list[i] >= si - face_off - MIN_LENGTH or s_cur > si + face_off + 15.0):
                        continue
                    s_target = (si + face_off) if end_i == 's' else (si - face_off)
                    out_span = max(0.0, s0_list[j] - sj, sj - s1_list[j])
                    d_int = abs(s_target - s_cur) + 2.0 * out_span
                    if abs(si - s_cur) <= tol and d_int < best_dist:
                        best_dist = d_int
                        best_j = j
                        best_params = (si, sj, sin_a, t2)

                if best_j is not None and best_params is not None:
                    si, sj, sin_a, t2 = best_params
                    face_off = (0.5 * t2) / sin_a
                    if end_i == 's':
                        s0_list[i] = si + face_off
                    else:
                        s1_list[i] = si - face_off
                    # Ensure w2 covers the full width of w1 at the T-junction if near w2's unlocked end
                    half_w1 = (0.5 * t1) / sin_a
                    if (best_j, 's') not in locked_ends and sj - half_w1 < s0_list[best_j] and s0_list[best_j] - (sj - half_w1) <= t1 + 30.0:
                        s0_list[best_j] = sj - half_w1
                    if (best_j, 'e') not in locked_ends and sj + half_w1 > s1_list[best_j] and (sj + half_w1) - s1_list[best_j] <= t1 + 30.0:
                        s1_list[best_j] = sj + half_w1
                    locked_ends.add((i, end_i))
                    t_snaps += 1

        # 4. Recompute polygons ONLY for rectangular walls; drop merged walls
        out_walls: List[Wall] = []
        for i, w in enumerate(walls):
            if i in dropped:
                continue
            if is_rect[i]:
                s0, s1 = s0_list[i], s1_list[i]
                L = s1 - s0
                if L < MIN_LENGTH:
                    continue
                ux, uy = u_list[i]
                nx, ny = n_list[i]
                p0x, p0y = p0_list[i]
                sx, sy = p0x + s0 * ux, p0y + s0 * uy
                ex, ey = p0x + s1 * ux, p0y + s1 * uy
                ht = 0.5 * w.thickness
                hx, hy = nx * ht, ny * ht
                w.start_point = (round(sx, 2), round(sy, 2))
                w.end_point = (round(ex, 2), round(ey, 2))
                w.length = round(L, 2)
                w.polygon = [
                    (round(sx + hx, 2), round(sy + hy, 2)),
                    (round(ex + hx, 2), round(ey + hy, 2)),
                    (round(ex - hx, 2), round(ey - hy, 2)),
                    (round(sx - hx, 2), round(sy - hy, 2)),
                ]
            out_walls.append(w)

        msg = f"Closed {l_snaps} L-corners, {t_snaps} T-junctions, and {c_snaps} collinear gaps."
        return out_walls, msg

    @staticmethod
    def _drop_duplicate_drawings(walls: List[Wall]) -> Tuple[List[Wall], str]:
        if len(walls) < 4:
            return walls, ''
        polys = [_poly(w).buffer(CLUSTER_GAP / 2) for w in walls]
        merged = unary_union(polys)
        comps = list(merged.geoms) if hasattr(merged, 'geoms') else [merged]
        if len(comps) < 2:
            return walls, ''
        clusters = []
        for comp in comps:
            members = [w for w, p in zip(walls, polys) if comp.intersects(p) and comp.contains(p.centroid)]
            area = sum(_poly(w).area for w in members)
            clusters.append((members, area))
        clusters.sort(key=lambda c: (-len(c[0]), -c[1]))
        main = clusters[0]
        copies = others = 0
        for members, area in clusters[1:]:
            if abs(len(members) - len(main[0])) <= 3 and abs(area - main[1]) <= 0.08 * main[1]:
                copies += 1              # same plan drawn again
            else:
                others += 1              # mirrored/partial copy, detail, other drawing
        msgs = []
        if copies:
            msgs.append(f"the same plan was drawn {copies + 1}x - used 1 copy")
        if others:
            msgs.append(f"ignored {others} other drawing fragment(s) far from the main plan")
        return list(main[0]), "File contains several drawings: " + "; ".join(msgs) + "."

    @staticmethod
    def _count_gaps(walls: List[Wall]) -> int:
        polys = [_poly(w) for w in walls]
        gaps = 0
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                d = polys[i].distance(polys[j])
                if 0 < d < 50:
                    gaps += 1
        return gaps
