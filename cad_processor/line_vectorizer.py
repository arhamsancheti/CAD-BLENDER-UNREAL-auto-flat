"""Plan picture -> CAD lines / poche wall outlines.

Architectural plans pasted into documents or PDFs are either:
1. Thin-line drawings (each wall = two parallel strokes, windows = 3-4 strokes).
2. Colored / grey-poche presentation plans (walls filled with solid grey poche, cyan/multi-line glazing).

This module detects which representation is used, extracts clean CAD geometry in millimetres,
and preserves any text labels (room names & dimensions) at their exact coordinates.
"""
import json
import logging
import os
from typing import List, Optional, Tuple

import cv2
import ezdxf
import numpy as np

logger = logging.getLogger(__name__)


def _runs_1d(row: np.ndarray, min_len: int):
    d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    keep = (ends - starts) >= min_len
    return starts[keep], ends[keep]


def _strokes(M: np.ndarray, min_len: int, bridge: int) -> List[Tuple[float, float, float, int]]:
    """Group long ink runs of consecutive rows into strokes -> (row_centre, start, end, thickness_rows)."""
    active = []                         # [first_row, last_row, s_lo, e_hi, rows]
    done = []
    for r in range(M.shape[0]):
        starts, ends = _runs_1d(M[r], min_len)
        merged = []
        for s, e in zip(starts.tolist(), ends.tolist()):
            if merged and s - merged[-1][1] <= bridge:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        nxt = []
        used = set()
        for s, e in merged:
            hit = None
            for k, g in enumerate(active):
                if k in used:
                    continue
                ov = min(e, g[3]) - max(s, g[2])
                if ov >= 0.6 * min(e - s, g[3] - g[2]) and abs((e - s) - (g[3] - g[2])) <= max(4, 0.15 * (g[3] - g[2])):
                    hit = k
                    break
            if hit is None:
                nxt.append([r, r, s, e, [(s, e)]])
            else:
                g = active[hit]
                used.add(hit)
                g[1] = r
                g[4].append((s, e))
                g[2], g[3] = min(g[2], s), max(g[3], e)
                nxt.append(g)
        for k, g in enumerate(active):
            if k not in used:
                done.append(g)
        active = nxt
    done += active
    out = []
    for r0, r1, _, _, spans in done:
        ss = sorted(s for s, _ in spans)
        es = sorted(e for _, e in spans)
        s_med, e_med = ss[len(ss) // 2], es[len(es) // 2]
        out.append((0.5 * (r0 + r1), float(s_med), float(e_med), r1 - r0 + 1))
    return out


def _strip_sheet_borders(mask: np.ndarray):
    """Zero out outer page/frame border lines near the edges of a rendered sheet."""
    H, W = mask.shape
    ey, ex = max(12, int(H * 0.06)), max(12, int(W * 0.04))
    for y in range(ey):
        if mask[y].mean() > 0.45:
            mask[y, :] = 0
    for y in range(H - ey, H):
        if mask[y].mean() > 0.45:
            mask[y, :] = 0
    for x in range(ex):
        if mask[:, x].mean() > 0.45:
            mask[:, x] = 0
    for x in range(W - ex, W):
        if mask[:, x].mean() > 0.45:
            mask[:, x] = 0


def has_poche_walls(im_bgr: np.ndarray) -> Tuple[bool, float]:
    """Detect whether `im_bgr` has solid grey-filled poche walls and return (is_poche, median_wall_px)."""
    if im_bgr is None or im_bgr.ndim != 3:
        return False, 0.0
    H, W, _ = im_bgr.shape
    if min(H, W) < 300:
        return False, 0.0
    b, g, r = im_bgr[:, :, 0].astype(int), im_bgr[:, :, 1].astype(int), im_bgr[:, :, 2].astype(int)
    gray = cv2.cvtColor(im_bgr, cv2.COLOR_BGR2GRAY)
    sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    poche = ((gray >= 60) & (gray <= 130) & (sat <= 18)).astype(np.uint8)
    _strip_sheet_borders(poche)
    poche_core = cv2.morphologyEx(poche, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    if float(poche_core.mean()) < 0.006:
        return False, 0.0
    min_len = max(14, int(min(H, W) * 0.015))
    h_open = cv2.morphologyEx(poche_core, cv2.MORPH_OPEN, np.ones((3, min_len), np.uint8))
    v_open = cv2.morphologyEx(poche_core, cv2.MORPH_OPEN, np.ones((min_len, 3), np.uint8))
    t_vals = []
    n_strips = 0
    for M in (h_open, v_open.T):
        for _, s, e, t in _strokes(M, min_len, bridge=3):
            if 7 <= t <= 40 and (e - s) >= max(min_len, 1.5 * t):
                n_strips += 1
                if (e - s) >= 2.5 * t:
                    t_vals.extend([float(t)] * int(max(1, (e - s) // 20)))
    if n_strips < 10 or not t_vals:
        return False, 0.0
    return True, float(np.median(t_vals))


def vectorize_poche_plan(
    im_bgr: np.ndarray,
    out_dxf: str,
    mm_per_px: Optional[float] = None,
    wall_mm: float = 150.0,
    text_labels: Optional[List[Tuple[str, float, float]]] = None,
) -> dict:
    """Vectorize a grey-poche architectural floor plan into a clean millimetre DXF (WALL_RASTER, WIN, DOOR)."""
    H, W, _ = im_bgr.shape
    b, g, r = im_bgr[:, :, 0].astype(int), im_bgr[:, :, 1].astype(int), im_bgr[:, :, 2].astype(int)
    gray = cv2.cvtColor(im_bgr, cv2.COLOR_BGR2GRAY)
    sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)

    poche = ((gray >= 60) & (gray <= 130) & (sat <= 18)).astype(np.uint8)
    dark_neutral = ((gray < 140) & (sat <= 28)).astype(np.uint8)
    cyan_glass = ((b - r >= 28) & (g >= 110) & (b >= 130)).astype(np.uint8)

    _strip_sheet_borders(poche)
    _strip_sheet_borders(dark_neutral)

    poche_core = cv2.morphologyEx(poche, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    wall_mask = cv2.dilate(poche_core, np.ones((5, 5), np.uint8)) & dark_neutral
    wall_mask = cv2.morphologyEx(wall_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    # Keep only the main building zone using dark_neutral
    k_zone = max(15, int(min(H, W) * 0.02))
    z_closed = cv2.morphologyEx(dark_neutral * 255, cv2.MORPH_CLOSE, np.ones((k_zone, k_zone), np.uint8))
    n_z, lab_z, st_z, _ = cv2.connectedComponentsWithStats((z_closed > 0).astype(np.uint8), connectivity=8)
    if n_z > 1:
        big_z = 1 + int(np.argmax(st_z[1:, cv2.CC_STAT_AREA]))
        zone = cv2.dilate((lab_z == big_z).astype(np.uint8), np.ones((k_zone * 2, k_zone * 2), np.uint8))
        wall_mask = wall_mask & zone
        dark_neutral = dark_neutral & zone
        cyan_glass = cyan_glass & zone

    # Fill small enclosed holes inside columns/walls (e.g. hollow column symbols)
    inv = (wall_mask == 0).astype(np.uint8)
    n_h, lab_h, st_h, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    for i in range(1, n_h):
        if st_h[i, cv2.CC_STAT_AREA] < (min(H, W) * 0.04) ** 2:
            x0, y0, w0, h0, _ = st_h[i]
            if x0 > 0 and y0 > 0 and x0 + w0 < W and y0 + h0 < H and max(w0, h0) <= min(H, W) * 0.08:
                wall_mask[lab_h == i] = 1

    # Extract H and V strips from wall_mask
    min_len = max(14, int(min(H, W) * 0.015))
    h_open = cv2.morphologyEx(wall_mask, cv2.MORPH_OPEN, np.ones((3, min_len), np.uint8))
    v_open = cv2.morphologyEx(wall_mask, cv2.MORPH_OPEN, np.ones((min_len, 3), np.uint8))

    strips = []
    t_vals = []
    for orient, M in (('H', h_open), ('V', v_open.T)):
        for c, s, e, t in _strokes(M, min_len, bridge=3):
            if t >= 6 and (e - s) >= max(min_len, 0.8 * t):
                p1, p2 = c - t / 2.0, c + t / 2.0
                strips.append([orient, float(p1), float(p2), float(s), float(e)])
                if 8 <= t <= 35 and (e - s) >= 3.0 * t:
                    t_vals.extend([float(t)] * int(max(1, (e - s) // 20)))

    t_px = float(np.median(t_vals)) if t_vals else 18.0
    scale = float(mm_per_px) if mm_per_px else (float(wall_mm) / max(t_px, 4.0))
    strips = [s for s in strips if (s[2] - s[1]) >= 0.45 * t_px and (s[4] - s[3]) >= max(min_len, 1.25 * (s[2] - s[1]))]

    # Merge collinear strips that touch or are within 4 px
    merged = []
    for orient in ('H', 'V'):
        st = sorted([s for s in strips if s[0] == orient], key=lambda x: (x[1], x[3]))
        used = [False] * len(st)
        for i in range(len(st)):
            if used[i]:
                continue
            used[i] = True
            _, p1, p2, s0, e0 = st[i]
            for j in range(i + 1, len(st)):
                if not used[j] and abs(st[j][1] - p1) <= 4.0 and abs(st[j][2] - p2) <= 4.0:
                    if st[j][3] <= e0 + 6.0 and st[j][4] >= s0 - 6.0:
                        s0, e0 = min(s0, st[j][3]), max(e0, st[j][4])
                        used[j] = True
            merged.append([orient, p1, p2, s0, e0])
    strips = merged

    # Extend strips slightly to meet perpendicular strips cleanly at L/T corners
    for s in strips:
        orient, p1, p2, s0, e0 = s
        perp = 'V' if orient == 'H' else 'H'
        for _, q1, q2, qs, qe in strips:
            if _ != perp:
                continue
            if min(qe + t_px, p2) - max(qs - t_px, p1) >= 0:
                if q1 - 0.8 * t_px <= s0 <= q2 + 0.8 * t_px:
                    s[3] = min(s[3], q1)
                if q1 - 0.8 * t_px <= e0 <= q2 + 0.8 * t_px:
                    s[4] = max(s[4], q2)

    win_boxes = []
    door_lines = []
    extra_stubs = []

    def check_span(orient, p1, p2, gs, ge, is_collinear: bool):
        w_span = ge - gs
        if w_span < 1.2 * t_px or w_span > 35.0 * t_px:
            return
        ia, ib = int(max(0, p1 - 2)), int(min((H if orient == 'H' else W), p2 + 3))
        sa, sb = int(max(0, gs + 2)), int(min((W if orient == 'H' else H), ge - 2))
        if ib <= ia or sb <= sa:
            return
        sub_dn = dark_neutral[ia:ib, sa:sb] if orient == 'H' else dark_neutral[sa:sb, ia:ib].T
        sub_cy = cyan_glass[ia:ib, sa:sb] if orient == 'H' else cyan_glass[sa:sb, ia:ib].T
        row_cov = sub_dn.mean(axis=1)
        n_rows = int((row_cov >= 0.45).sum())
        cy_cov = float(sub_cy.mean())
        if n_rows >= 2 or (cy_cov >= 0.08 and n_rows >= 1):
            win_boxes.append([orient, p1, p2, gs, ge])
        elif is_collinear and 2.5 * t_px <= w_span <= 11.5 * t_px:
            door_lines.append((orient, 0.5 * (p1 + p2), gs, ge))

    for orient in ('H', 'V'):
        st = sorted([s for s in strips if s[0] == orient], key=lambda x: (0.5 * (x[1] + x[2]), x[3]))
        for i in range(len(st)):
            _, p1, p2, s1, e1 = st[i]
            mid1 = 0.5 * (p1 + p2)
            best_j = None
            best_gap = 1e9
            for j in range(len(st)):
                if i == j:
                    continue
                _, q1, q2, s2, e2 = st[j]
                if abs(0.5 * (q1 + q2) - mid1) <= 0.65 * t_px and s2 >= e1 - 2.0:
                    gap = s2 - e1
                    if gap < best_gap:
                        best_gap = gap
                        best_j = j
            if best_j is not None and 1.2 * t_px <= best_gap <= 30.0 * t_px:
                _, q1, q2, s2, e2 = st[best_j]
                wp1, wp2 = max(p1, q1), min(p2, q2)
                if wp2 - wp1 < 0.5 * t_px:
                    wp1, wp2 = min(p1, q1), max(p2, q2)
                check_span(orient, wp1, wp2, e1, s2, is_collinear=True)

    # Detect cyan + multi-line glazing / balcony railing strips that aren't between two collinear poche stubs
    cy_closed = cv2.morphologyEx(cyan_glass, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n_c, _, st_c, _ = cv2.connectedComponentsWithStats(cy_closed, connectivity=8)
    for i in range(1, n_c):
        cx, cy, cw, ch, _ = st_c[i]
        l_c, t_c = max(cw, ch), min(cw, ch)
        if l_c < 3.5 * t_px or t_c > 1.8 * t_px or l_c < 4.0 * max(t_c, 1):
            continue
        orient = 'H' if cw >= ch else 'V'
        p_mid = (cy + 0.5 * ch) if orient == 'H' else (cx + 0.5 * cw)
        gs, ge = (float(cx), float(cx + cw)) if orient == 'H' else (float(cy), float(cy + ch))
        ia, ib = int(max(0, p_mid - 0.6 * t_px)), int(min((H if orient == 'H' else W), p_mid + 0.6 * t_px))
        sa, sb = int(max(0, gs)), int(min((W if orient == 'H' else H), ge))
        sub_wm = wall_mask[ia:ib, sa:sb] if orient == 'H' else wall_mask[sa:sb, ia:ib].T
        if float(sub_wm.mean()) > 0.25:
            continue
        sub_dn = dark_neutral[ia:ib, sa:sb] if orient == 'H' else dark_neutral[sa:sb, ia:ib].T
        if int((sub_dn.mean(axis=1) >= 0.35).sum()) < 2:
            continue
        if any(w[0] == orient and abs(0.5 * (w[1] + w[2]) - p_mid) <= t_px and min(w[4], ge) - max(w[3], gs) > 0.3 * (ge - gs) for w in win_boxes):
            continue
        p1, p2 = p_mid - 0.5 * t_px, p_mid + 0.5 * t_px
        for s_item in strips:
            if s_item[0] == orient and abs(0.5 * (s_item[1] + s_item[2]) - p_mid) <= 0.65 * t_px:
                p1, p2 = s_item[1], s_item[2]
                break
        perp = 'V' if orient == 'H' else 'H'
        mullion = 1.35 * t_px
        best_start_perp = None
        best_end_perp = None
        for s_other in strips:
            if s_other[0] == perp and s_other[3] - 6.5 * t_px <= p_mid <= s_other[4] + 6.5 * t_px:
                q1, q2 = s_other[1], s_other[2]
                if -t_px <= gs - q2 <= 9.0 * t_px:
                    if best_start_perp is None or abs(gs - q2) < abs(gs - best_start_perp[2]):
                        best_start_perp = s_other
                if -t_px <= q1 - ge <= 9.0 * t_px:
                    if best_end_perp is None or abs(q1 - ge) < abs(best_end_perp[1] - ge):
                        best_end_perp = s_other
        if best_start_perp is not None:
            q1, q2 = best_start_perp[1], best_start_perp[2]
            best_start_perp[3] = min(best_start_perp[3], p1)
            best_start_perp[4] = max(best_start_perp[4], p2)
            extra_stubs.append([orient, p1, p2, q1, q2 + mullion])
            gs = q2 + mullion
        if best_end_perp is not None:
            q1, q2 = best_end_perp[1], best_end_perp[2]
            best_end_perp[3] = min(best_end_perp[3], p1)
            best_end_perp[4] = max(best_end_perp[4], p2)
            extra_stubs.append([orient, p1, p2, q1 - mullion, q2])
            ge = q1 - mullion
        for s_item in strips:
            if s_item[0] == orient and abs(0.5 * (s_item[1] + s_item[2]) - p_mid) <= 0.8 * t_px:
                if 2.0 * t_px <= gs - s_item[4] <= 11.5 * t_px:
                    extra_stubs.append([orient, p1, p2, gs, gs + mullion])
                    door_lines.append((orient, 0.5 * (p1 + p2), s_item[4], gs))
                    gs = gs + mullion
                if 2.0 * t_px <= s_item[3] - ge <= 11.5 * t_px:
                    extra_stubs.append([orient, p1, p2, ge - mullion, ge])
                    door_lines.append((orient, 0.5 * (p1 + p2), ge, s_item[3]))
                    ge = ge - mullion
        if ge - gs >= 1.5 * t_px:
            win_boxes.append([orient, p1, p2, gs, ge])

    # Check strip ends that face a perpendicular wall across a doorway or passage (2.2..12.5 * t_px)
    for idx_s, (orient, p1, p2, s0, e0) in enumerate(list(strips)):
        if (e0 - s0) < 2.2 * t_px:
            continue
        perp = 'V' if orient == 'H' else 'H'
        perps = [x for x in strips if x[0] == perp]
        mid_p = 0.5 * (p1 + p2)
        has_parallel_overlap = any(
            idx_o != idx_s and o2 == orient and abs(0.5 * (op1 + op2) - mid_p) <= 1.6 * t_px
            and min(oe0, e0) - max(os0, s0) >= 0.5 * (e0 - s0)
            for idx_o, (o2, op1, op2, os0, oe0) in enumerate(strips)
        )
        if has_parallel_overlap:
            continue
        for end_side, pos_end in (('start', s0), ('end', e0)):
            pt_x, pt_y = (pos_end, mid_p) if orient == 'H' else (mid_p, pos_end)
            touches_other = False
            for idx_o, (o2, op1, op2, os0, oe0) in enumerate(strips):
                if idx_o == idx_s:
                    continue
                ox0, oy0, ox1, oy1 = (os0, op1, oe0, op2) if o2 == 'H' else (op1, os0, op2, oe0)
                if (ox0 - 1.2 * t_px <= pt_x <= ox1 + 1.2 * t_px) and (oy0 - 1.2 * t_px <= pt_y <= oy1 + 1.2 * t_px):
                    touches_other = True
                    break
            if touches_other:
                continue
            has_col = any(
                x[0] == orient and abs(0.5 * (x[1] + x[2]) - mid_p) <= 0.65 * t_px
                and (0 < pos_end - x[4] <= 30.0 * t_px if end_side == 'start' else 0 < x[3] - pos_end <= 30.0 * t_px)
                for x in strips
            )
            has_win = any(
                w[0] == orient and abs(0.5 * (w[1] + w[2]) - mid_p) <= 0.8 * t_px
                and (0 <= pos_end - w[4] <= 12.0 * t_px if end_side == 'start' else 0 <= w[3] - pos_end <= 12.0 * t_px)
                for w in win_boxes
            )
            if has_col or has_win:
                continue
            best_perp = None
            best_dist = 1e9
            for _, q1, q2, qs, qe in perps:
                if qs - 1.2 * t_px <= mid_p <= qe + 1.2 * t_px:
                    dist = (pos_end - q2) if end_side == 'start' else (q1 - pos_end)
                    if 2.2 * t_px <= dist <= 12.5 * t_px and dist < best_dist:
                        best_dist = dist
                        best_perp = (q1, q2, qs, qe)
            if best_perp is not None:
                q1, q2, qs, qe = best_perp
                stub_len = 1.4 * t_px
                if end_side == 'start':
                    extra_stubs.append([orient, p1, p2, q1, q2 + stub_len])
                    door_lines.append((orient, mid_p, q2 + stub_len, pos_end))
                else:
                    extra_stubs.append([orient, p1, p2, q1 - stub_len, q2])
                    door_lines.append((orient, mid_p, pos_end, q1 - stub_len))

    all_strips = strips + extra_stubs

    def to_cad(x_px: float, y_px: float) -> Tuple[float, float]:
        return (round(float(x_px) * scale, 2), round(float(H - y_px) * scale, 2))

    doc = ezdxf.new('R2010')
    doc.header['$INSUNITS'] = 4
    msp = doc.modelspace()
    for orient, p1, p2, s0, e0 in all_strips:
        x0, y0, x1, y1 = (s0, p1, e0, p2) if orient == 'H' else (p1, s0, p2, e0)
        msp.add_lwpolyline([to_cad(x0, y0), to_cad(x1, y0), to_cad(x1, y1), to_cad(x0, y1)], close=True,
                           dxfattribs={'layer': 'WALL_RASTER'})
    for orient, p1, p2, ws, we in win_boxes:
        for frac in (0.0, 0.33, 0.67, 1.0):
            pos = p1 + frac * (p2 - p1)
            if orient == 'H':
                msp.add_line(to_cad(ws, pos), to_cad(we, pos), dxfattribs={'layer': 'WIN'})
            else:
                msp.add_line(to_cad(pos, ws), to_cad(pos, we), dxfattribs={'layer': 'WIN'})
    for orient, mid, ds, de in door_lines:
        if orient == 'H':
            msp.add_line(to_cad(ds, mid), to_cad(de, mid), dxfattribs={'layer': 'DOOR'})
        else:
            msp.add_line(to_cad(mid, ds), to_cad(mid, de), dxfattribs={'layer': 'DOOR'})
    for txt, lx_px, ly_px in (text_labels or []):
        cx, cy = to_cad(lx_px, ly_px)
        msp.add_text(str(txt), dxfattribs={'layer': 'TEXT', 'insert': (cx, cy), 'height': 150.0})
    doc.saveas(out_dxf)

    def rect_mm(orient, p1, p2, s0, e0):
        x0, y0, x1, y1 = (s0, p1, e0, p2) if orient == 'H' else (p1, s0, p2, e0)
        a, b_pt = to_cad(x0, y1), to_cad(x1, y0)
        return [a[0], a[1], b_pt[0], b_pt[1]]

    review_report = {
        'engine': 'raster_walls',
        'source': os.path.basename(out_dxf),
        'size_px': [W, H],
        'mm_per_px': round(scale, 4),
        'scale_source': 'poche wall & schedule calibration' if mm_per_px else f'poche wall thickness {t_px:.1f} px = {wall_mm:.0f} mm',
        'thickness_modes_px': [round(t_px, 2)],
        'thickness_modes_mm': [round(t_px * scale)],
        'walls': [{'rect_px': [round(s0 if o == 'H' else p1, 1), round(p1 if o == 'H' else s0, 1),
                               round(e0 if o == 'H' else p2, 1), round(p2 if o == 'H' else e0, 1)],
                   'rect_mm': rect_mm(o, p1, p2, s0, e0), 'src': 'poche', 'term': ['corner', 'corner']}
                  for o, p1, p2, s0, e0 in all_strips],
        'windows': [{'rect_px': [round(ws if o == 'H' else p1, 1), round(p1 if o == 'H' else ws, 1),
                                 round(we if o == 'H' else p2, 1), round(p2 if o == 'H' else we, 1)],
                     'rect_mm': rect_mm(o, p1, p2, ws, we), 'sliding': True, 'inner_lines': 4}
                    for o, p1, p2, ws, we in win_boxes],
        'gaps': [],
        'rejected': [],
        'isolated': [],
        'trimmed': [],
        'dangling': [],
        'shafts': 0,
    }
    try:
        with open(out_dxf + '.review.json', 'w', encoding='utf-8') as fh:
            json.dump(review_report, fh)
    except OSError:
        pass

    logger.info('Poche plan vectorized to %d wall strips, %d windows, %d doors at %.3f mm/px',
                len(all_strips), len(win_boxes), len(door_lines), scale)
    return {
        'lines': len(all_strips) * 4,
        'filled_strokes': len(all_strips),
        'mm_per_px': scale,
        'min_len_px': min_len,
        'text_blobs_removed': 0,
        'engine': 'poche',
    }


def estimate_wall_px(png: str) -> float:
    """Typical wall thickness in pixels of a plan picture (either solid poche wall thickness or
    spacing between parallel thin-line wall strokes)."""
    im_bgr = cv2.imread(png, cv2.IMREAD_COLOR)
    if im_bgr is None:
        return 0.0
    is_poche, poche_t = has_poche_walls(im_bgr)
    if is_poche and poche_t >= 6.0:
        return poche_t
    g = cv2.cvtColor(im_bgr, cv2.COLOR_BGR2GRAY)
    bw = (g < 170).astype(np.uint8)
    _strip_sheet_borders(bw)
    min_len = max(12, int(max(g.shape) * 0.02))
    hist = {}
    for M in (bw, bw.T):
        st = sorted(_strokes(M, min_len, bridge=2))
        for i, (c1, s1, e1, t1) in enumerate(st):
            for c2, s2, e2, t2 in st[i + 1:]:
                d = c2 - c1
                if d > 80:
                    break
                if d < 3:
                    continue
                ov = min(e1, e2) - max(s1, s2)
                if ov >= 0.5 * min(e1 - s1, e2 - s2):
                    key = int(round(d))
                    hist[key] = hist.get(key, 0.0) + ov
                    break
    if not hist:
        return 0.0
    # Prefer wall thicknesses >= 6 px over 3..4 px window-glazing stroke spacing when present
    wide_keys = [k for k in hist if k >= 6]
    if wide_keys:
        best_wide = max(wide_keys, key=lambda k: hist.get(k - 1, 0) + 2 * hist[k] + hist.get(k + 1, 0))
        best_all = max(hist, key=lambda k: hist.get(k - 1, 0) + 2 * hist[k] + hist.get(k + 1, 0))
        score_wide = hist.get(best_wide - 1, 0) + 2 * hist[best_wide] + hist.get(best_wide + 1, 0)
        score_all = hist.get(best_all - 1, 0) + 2 * hist[best_all] + hist.get(best_all + 1, 0)
        if score_wide >= 0.25 * score_all:
            return float(best_wide)
    best = max(hist, key=lambda k: hist.get(k - 1, 0) + 2 * hist[k] + hist.get(k + 1, 0))
    return float(best)


def picture_to_lines_dxf(
    png: str,
    out_dxf: str,
    mm_per_px: float,
    min_len_mm: float = 120.0,
    fill_mm: float = 45.0,
    text_labels: Optional[List[Tuple[str, float, float]]] = None,
) -> dict:
    """Trace a plan picture into a millimetre DXF. Uses poche extraction when walls are grey-filled."""
    im_bgr = cv2.imread(png, cv2.IMREAD_COLOR)
    if im_bgr is None:
        raise RuntimeError(f'Could not read picture {png}')
    is_poche, _ = has_poche_walls(im_bgr)
    if is_poche:
        return vectorize_poche_plan(im_bgr, out_dxf, mm_per_px=mm_per_px, text_labels=text_labels)

    g = cv2.cvtColor(im_bgr, cv2.COLOR_BGR2GRAY)
    h, w = g.shape
    bw = (g < 170).astype(np.uint8)
    _strip_sheet_borders(bw)
    min_len = max(6, int(round(min_len_mm / mm_per_px)))
    fill_px = max(3.0, fill_mm / mm_per_px)

    # drop text / dimension figures / small symbols
    n_cc, lab_cc, st_cc, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    small = max(4.0, 450.0 / mm_per_px)
    col_min = 120.0 / mm_per_px
    keep = np.ones(n_cc, np.uint8)
    keep[0] = 0
    n_text = 0
    for i in range(1, n_cc):
        bw_i, bh_i, area_i = st_cc[i, cv2.CC_STAT_WIDTH], st_cc[i, cv2.CC_STAT_HEIGHT], st_cc[i, cv2.CC_STAT_AREA]
        if max(bw_i, bh_i) < small:
            fill = area_i / float(max(bw_i * bh_i, 1))
            if not (fill >= 0.6 and min(bw_i, bh_i) >= col_min):
                keep[i] = 0
                n_text += 1
    bw = keep[lab_cc].astype(np.uint8)

    # keep only the drawing itself (largest closed footprint), not titles / legends / notes around it
    k = max(5, int(max(h, w) * 0.012))
    closed = cv2.morphologyEx(bw * 255, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    pad = cv2.copyMakeBorder(closed, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    ff = pad.copy()
    cv2.floodFill(ff, np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8), (0, 0), 255)
    filled = (pad | cv2.bitwise_not(ff))[1:-1, 1:-1]
    n, lab, stats, _ = cv2.connectedComponentsWithStats((filled > 0).astype(np.uint8), connectivity=8)
    zone = None
    if n > 1:
        big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        zone = cv2.dilate((lab == big).astype(np.uint8), np.ones((2 * k + 1, 2 * k + 1), np.uint8))

    segs = []
    n_fill = 0
    for orient, M in (('H', bw), ('V', bw.T)):
        for c, s, e, t in _strokes(M, min_len, bridge=2):
            if t > fill_px:
                if (e - s) < 1.5 * t:
                    continue
                n_fill += 1
                edges = (c - t / 2.0, c + t / 2.0)
            else:
                edges = (c,)
            for cc in edges:
                if orient == 'H':
                    x0, y0, x1, y1 = s, cc, e, cc
                else:
                    x0, y0, x1, y1 = cc, s, cc, e
                if zone is not None:
                    mx, my = int(min(w - 1, max(0, (x0 + x1) / 2))), int(min(h - 1, max(0, (y0 + y1) / 2)))
                    if not zone[my, mx]:
                        continue
                segs.append((x0, y0, x1, y1))

    doc = ezdxf.new('R2010')
    doc.header['$INSUNITS'] = 4
    msp = doc.modelspace()
    doc.layers.add('PLAN_LINES')
    for x0, y0, x1, y1 in segs:
        msp.add_line((x0 * mm_per_px, (h - y0) * mm_per_px), (x1 * mm_per_px, (h - y1) * mm_per_px),
                     dxfattribs={'layer': 'PLAN_LINES'})
    for txt, lx_px, ly_px in (text_labels or []):
        msp.add_text(str(txt), dxfattribs={
            'layer': 'TEXT',
            'insert': (round(float(lx_px) * mm_per_px, 2), round(float(h - ly_px) * mm_per_px, 2)),
            'height': 150.0,
        })
    doc.saveas(out_dxf)
    rep = {'lines': len(segs), 'filled_strokes': n_fill, 'mm_per_px': mm_per_px, 'min_len_px': min_len,
           'text_blobs_removed': n_text}
    logger.info('Picture traced to %d CAD lines (%d filled wall strokes, %d text/symbol blobs removed) at %.3f mm/px',
                len(segs), n_fill, n_text, mm_per_px)
    return rep
