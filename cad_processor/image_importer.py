"""
Vectorize a 2D raster floor plan image (.png, .jpg, .jpeg, .webp, .bmp) into a clean
architectural DXF (with WALL, WIN, DOOR, and shaft cross entities in millimeters).
"""
import logging
import math
import os
from typing import List, Tuple

import cv2
import ezdxf
import numpy as np

logger = logging.getLogger(__name__)


def foreground_mask(gray: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Separate drawn linework from the paper / screen background.

    The previous implementation thresholded |pixel - global median|. On screenshots with a gradient
    or vignetted background (e.g. a CAD viewport) the background itself deviates from the global
    median by more than the threshold, so >60 % of the image became "linework" and wall pairing
    collapsed. Here the background is estimated *locally* (median filter on a 4x down-sampled copy,
    which removes thin lines but keeps slow shading), the line polarity (light-on-dark or
    dark-on-light) is detected automatically, and an Otsu threshold is taken on the residual.

    Returns (strength, mask): strength is a float32 contrast image (>= 0), mask is uint8 {0, 1}.
    """
    H, W = gray.shape
    f = 4 if min(H, W) >= 400 else 2
    small = cv2.resize(gray, (max(1, W // f), max(1, H // f)), interpolation=cv2.INTER_AREA)
    k = max(5, (int(min(small.shape) / 40) | 1))
    k = min(k, 31)
    bg = cv2.resize(cv2.medianBlur(small, k), (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    d = gray.astype(np.float32) - bg
    bright, dark = int((d > 12).sum()), int((d < -12).sum())
    d = d if bright >= dark else -d
    np.maximum(d, 0, out=d)
    vals = d[d > 6]
    if vals.size < 50:
        return d, (d > 10).astype(np.uint8)
    otsu, _ = cv2.threshold(np.clip(vals, 0, 255).astype(np.uint8).reshape(-1, 1), 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    t = max(8.0, 0.33 * float(otsu))       # anti-aliased lines straddling two rows render at ~50 % contrast
    mask = (d > t).astype(np.uint8)
    logger.info("Foreground: polarity=%s, threshold=%.1f, ink ratio=%.3f",
                'light-on-dark' if bright >= dark else 'dark-on-light', t, float(mask.mean()))
    return d, mask


def _get_merged_runs(mask: np.ndarray, diff_img: np.ndarray, min_len: int = 9) -> List[Tuple[float, float, float]]:
    """
    Extract 1D horizontal runs from `mask`, merge colinear runs separated by <= 2 px,
    and absorb adjacent-row anti-aliased fringes into the dominant run.
    Returns sorted list of (pos, start, end).
    """
    h, w = mask.shape
    raw = []
    for y in range(h):
        row = mask[y]
        if not row.any():
            continue
        padded = np.concatenate(([0], row, [0]))
        starts = np.where((padded[1:] == 1) & (padded[:-1] == 0))[0]
        ends = np.where((padded[1:] == 0) & (padded[:-1] == 1))[0]
        for s, e in zip(starts, ends):
            if e - s >= min_len:
                w_sum = float(diff_img[y, s:e].sum())
                raw.append([float(y), float(s), float(e - 1), max(w_sum, 1.0)])

    by_y = {}
    for y, s, e, w_sum in raw:
        by_y.setdefault(int(y), []).append([s, e, w_sum])

    row_runs = []
    for y, segs in sorted(by_y.items()):
        segs.sort()
        cs, ce, cw = segs[0]
        for s, e, w_sum in segs[1:]:
            if s <= ce + 2.0:
                ce = max(ce, e)
                cw += w_sum
            else:
                row_runs.append([float(y), cs, ce, cw])
                cs, ce, cw = s, e, w_sum
        row_runs.append([float(y), cs, ce, cw])

    order = sorted(range(len(row_runs)), key=lambda i: -(row_runs[i][2] - row_runs[i][1]))
    used = [False] * len(row_runs)
    merged = []
    for i in order:
        if used[i]:
            continue
        used[i] = True
        y1, s1, e1, w1 = row_runs[i]
        l1 = e1 - s1
        tot_y_w = y1 * w1
        tot_w = w1
        cur_s, cur_e = s1, e1
        for j in order:
            if used[j]:
                continue
            y2, s2, e2, w2 = row_runs[j]
            if abs(y2 - y1) <= 1.1:
                l2 = e2 - s2
                ov = min(cur_e, e2) - max(cur_s, s2)
                if ov >= 0.75 * min(l1, l2):
                    used[j] = True
                    if l2 >= 0.6 * l1:
                        tot_y_w += y2 * w2
                        tot_w += w2
                        cur_s = min(cur_s, s2)
                        cur_e = max(cur_e, e2)
        merged.append((tot_y_w / tot_w, cur_s, cur_e))
    return sorted(merged)


def _estimate_wall_thickness_px(
    h_runs: List[Tuple[float, float, float]],
    v_runs: List[Tuple[float, float, float]],
    h_mask: np.ndarray,
    v_mask: np.ndarray,
) -> float:
    """Find the dominant structural wall thickness in pixels from clean empty-interior parallel pairs."""
    samples = []
    for runs, perp_mask, is_vert in ((h_runs, v_mask, False), (v_runs, h_mask, True)):
        is_hatch = [False] * len(runs)
        for i, (p1, s1, e1) in enumerate(runs):
            sim = sum(
                1 for j, (p2, s2, e2) in enumerate(runs)
                if i != j and abs(p2 - p1) <= 25.0 and abs(s2 - s1) <= 6.0 and abs(e2 - e1) <= 6.0
            )
            if sim >= 3:
                is_hatch[i] = True
        for i, (p1, s1, e1) in enumerate(runs):
            if is_hatch[i]:
                continue
            for j in range(i + 1, len(runs)):
                if is_hatch[j]:
                    continue
                p2, s2, e2 = runs[j]
                d = p2 - p1
                if d < 5.0 or d > 28.0:
                    continue
                ov_s, ov_e = max(s1, s2), min(e1, e2)
                ov = ov_e - ov_s
                if ov < 35.0:
                    continue
                ia, ib = int(math.ceil(p1 + 1.5)), int(math.floor(p2 - 1.5))
                sa, sb = int(round(ov_s + 2)), int(round(ov_e - 2))
                if ib >= ia and sb > sa:
                    sub = perp_mask[ia:ib + 1, sa:sb] if not is_vert else perp_mask[sa:sb, ia:ib + 1]
                    if float(sub.mean()) > 0.05:
                        continue
                samples.append((d, ov))

    if not samples:
        return 9.0

    best_d = 9.0
    best_score = -1.0
    for d_cand in np.arange(5.5, 26.0, 0.25):
        score = sum(ov for d, ov in samples if abs(d - d_cand) <= 0.85)
        if score > best_score:
            best_score = score
            best_d = float(d_cand)

    near = [(d, ov) for d, ov in samples if abs(d - best_d) <= 1.0]
    weighted = sum(d * ov for d, ov in near) / max(sum(ov for _, ov in near), 1.0)
    return float(round(weighted))


def _extract_wall_strips(
    runs: List[Tuple[float, float, float]],
    perp_mask: np.ndarray,
    t_px: float,
    is_vert: bool = False,
) -> List[Tuple[float, float, float, float, float, float]]:
    """Return mutually exclusive clean wall strips (p1, p2, d, s, e, ov)."""
    is_hatch = [False] * len(runs)
    for i, (p1, s1, e1) in enumerate(runs):
        sim = sum(
            1 for j, (p2, s2, e2) in enumerate(runs)
            if i != j and abs(p2 - p1) <= 25.0 and abs(s2 - s1) <= 6.0 and abs(e2 - e1) <= 6.0
        )
        if sim >= 3:
            is_hatch[i] = True

    d_min = max(4.5, t_px - 1.2)
    d_max = t_px + 0.65
    cands = []
    for i, (p1, s1, e1) in enumerate(runs):
        if is_hatch[i]:
            continue
        for j in range(i + 1, len(runs)):
            if is_hatch[j]:
                continue
            p2, s2, e2 = runs[j]
            d = p2 - p1
            if d_min <= d <= d_max:
                ov_s = max(s1, s2)
                ov_e = min(e1, e2)
                ov = ov_e - ov_s
                if ov < max(16.0, 2.0 * t_px):
                    continue
                ia = int(math.ceil(p1 + 1.5))
                ib = int(math.floor(p2 - 1.5))
                sa = int(round(ov_s + 2))
                sb = int(round(ov_e - 2))
                perp_dens = 0.0
                if ib >= ia and sb > sa:
                    sub = perp_mask[ia:ib + 1, sa:sb] if not is_vert else perp_mask[sa:sb, ia:ib + 1]
                    perp_dens = float(sub.mean())
                if perp_dens > 0.08:
                    continue
                cands.append((p1, p2, d, ov_s, ov_e, ov))

    cands.sort(key=lambda c: (-c[5], abs(c[2] - (t_px - 0.15))))
    kept = []
    for c in cands:
        p1, p2, d, s, e, ov = c
        conflict = False
        for kp1, kp2, kd, ks, ke, kov in kept:
            if min(e, ke) - max(s, ks) >= 10.0:
                if min(p2, kp2) - max(p1, kp1) >= -0.5:
                    conflict = True
                    break
        if not conflict:
            kept.append(c)
    return sorted(kept, key=lambda c: (c[0], c[3]))


def _legacy_image_to_dxf(image_path: str, out_dxf_path: str) -> str:
    """
    LEGACY strip-pairing vectoriser (used only when the new raster engine finds no wall network).
    Convert a raster floor plan image (.png/.jpg/.jpeg/.webp/.bmp) into an architectural DXF file.
    """
    im_raw = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if im_raw is None:
        raise RuntimeError(f"Could not read image file: {image_path}")

    if im_raw.ndim == 3:
        if im_raw.shape[2] == 4:
            # Composite RGBA onto median RGB background if alpha has transparency
            alpha = im_raw[:, :, 3:4].astype(np.float32) / 255.0
            rgb = im_raw[:, :, :3].astype(np.float32)
            bg_rgb = np.median(rgb.reshape(-1, 3), axis=0)
            comp = rgb * alpha + bg_rgb * (1.0 - alpha)
            im = cv2.cvtColor(comp.astype(np.uint8), cv2.COLOR_BGR2GRAY)
        else:
            im = cv2.cvtColor(im_raw, cv2.COLOR_BGR2GRAY)
    else:
        im = im_raw

    H, W = im.shape
    diff, fg = foreground_mask(im)

    k_len = max(7, min(11, int(round(min(H, W) / 85.0))))
    h_mask = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((1, k_len), np.uint8))
    v_mask = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((k_len, 1), np.uint8))

    h_runs = _get_merged_runs(h_mask, diff, min_len=k_len)
    v_runs = _get_merged_runs(v_mask.T, diff.T, min_len=k_len)

    t_px = _estimate_wall_thickness_px(h_runs, v_runs, h_mask, v_mask)
    scale = 150.0 / max(t_px, 4.0)
    logger.info("Image floor plan %dx%d: dominant wall thickness=%.1f px -> scale=%.3f mm/px", W, H, t_px, scale)

    h_strips = _extract_wall_strips(h_runs, v_mask, t_px, is_vert=False)
    v_strips = _extract_wall_strips(v_runs, h_mask, t_px, is_vert=True)

    all_strips = ([('H', c[0], c[1], c[3], c[4]) for c in h_strips] +
                  [('V', c[0], c[1], c[3], c[4]) for c in v_strips])
    if not all_strips:
        raise RuntimeError("No structural wall pairs detected in the uploaded image.")

    def _strips_touch(a, b, tol: float) -> bool:
        ax0, ay0, ax1, ay1 = (a[3], a[1], a[4], a[2]) if a[0] == 'H' else (a[1], a[3], a[2], a[4])
        bx0, by0, bx1, by1 = (b[3], b[1], b[4], b[2]) if b[0] == 'H' else (b[1], b[3], b[2], b[4])
        return (ax0 - tol <= bx1 and bx0 - tol <= ax1 and ay0 - tol <= by1 and by0 - tol <= ay1)

    seed_len = max(80.0, min(120.0, 0.12 * max(W, H)))
    visited = [False] * len(all_strips)
    queue = [idx for idx, s in enumerate(all_strips) if (s[4] - s[3]) >= seed_len]
    if not queue:
        queue = [max(range(len(all_strips)), key=lambda idx: all_strips[idx][4] - all_strips[idx][3])]
    for idx in queue:
        visited[idx] = True
    tol_conn = t_px + 2.0
    while queue:
        cur = queue.pop(0)
        for nxt in range(len(all_strips)):
            if not visited[nxt] and _strips_touch(all_strips[cur], all_strips[nxt], tol=tol_conn):
                visited[nxt] = True
                queue.append(nxt)

    conn_strips = [s for idx, s in enumerate(all_strips) if visited[idx]]
    if len(conn_strips) < 8 and im_raw.ndim == 3 and im_raw.shape[2] >= 3:
        return _vectorize_solid_plan(im_raw[:, :, :3], out_dxf_path)

    # Group colinear strips on the same axis and heal T/cross-junction breaks (<= t_px + 2.5 px)
    clean_strips = []
    heal_gap = t_px + 2.5
    for orient in ('H', 'V'):
        st = [list(c) for c in conn_strips if c[0] == orient]
        used = [False] * len(st)
        for i in range(len(st)):
            if used[i]:
                continue
            grp = [st[i]]
            used[i] = True
            for j in range(i + 1, len(st)):
                if not used[j] and abs(st[j][1] - st[i][1]) <= 1.5 and abs(st[j][2] - st[i][2]) <= 1.5:
                    grp.append(st[j])
                    used[j] = True
            tot_l = sum(g[4] - g[3] for g in grp)
            p1 = sum(g[1] * (g[4] - g[3]) for g in grp) / tot_l
            p2 = sum(g[2] * (g[4] - g[3]) for g in grp) / tot_l
            grp.sort(key=lambda g: g[3])
            merged = [[p1, p2, grp[0][3], grp[0][4]]]
            for g in grp[1:]:
                if g[3] - merged[-1][3] <= heal_gap:
                    merged[-1][3] = max(merged[-1][3], g[4])
                else:
                    merged.append([p1, p2, g[3], g[4]])
            for m in merged:
                clean_strips.append([orient, m[0], m[1], m[2], m[3]])

    # Detect corner-flush doorways where one face continues 35..80 px across a doorway to a perpendicular wall
    jamb_stubs = []
    door_lines = []  # (orient, pos_mid, d_s, d_e)
    for orient, p1, p2, s, e in list(clean_strips):
        runs = h_runs if orient == 'H' else v_runs
        perp_orient = 'V' if orient == 'H' else 'H'
        perps = [c for c in clean_strips if c[0] == perp_orient]
        has_prev = any(c[0] == orient and abs(c[1] - p1) <= 1.5 and 0 < s - c[4] <= 10.5 * t_px for c in clean_strips)
        if not has_prev:
            for rp, rs, re in runs:
                if (abs(rp - p1) <= 1.2 or abs(rp - p2) <= 1.2) and rs < s - 3.3 * t_px and re >= s + 0.5 * t_px:
                    if 3.8 * t_px <= s - rs <= 9.0 * t_px:
                        for _, q1, q2, qs, qe in perps:
                            if q1 - 3.0 <= rs <= q2 + 3.0 and min(qe, p2) - max(qs, p1) >= -t_px:
                                jamb_end = q2 + t_px
                                jamb_stubs.append([orient, p1, p2, q1, jamb_end])
                                door_lines.append((orient, 0.5 * (p1 + p2), jamb_end, s))
                                break
        has_next = any(c[0] == orient and abs(c[1] - p1) <= 1.5 and 0 < c[3] - e <= 10.5 * t_px for c in clean_strips)
        if not has_next:
            for rp, rs, re in runs:
                if (abs(rp - p1) <= 1.2 or abs(rp - p2) <= 1.2) and re > e + 3.3 * t_px and rs <= e - 0.5 * t_px:
                    if 3.8 * t_px <= re - e <= 9.0 * t_px:
                        for _, q1, q2, qs, qe in perps:
                            if q1 - 3.0 <= re <= q2 + 3.0 and min(qe, p2) - max(qs, p1) >= -t_px:
                                jamb_start = q1 - t_px
                                jamb_stubs.append([orient, p1, p2, jamb_start, q2])
                                door_lines.append((orient, 0.5 * (p1 + p2), e, jamb_start))
                                break

    clean_strips.extend(jamb_stubs)

    # Extend strip endpoints that meet a perpendicular strip so L and T corners overlap cleanly
    for c in clean_strips:
        orient, p1, p2, s, e = c
        perp_orient = 'V' if orient == 'H' else 'H'
        for p_or, q1, q2, qs, qe in clean_strips:
            if p_or != perp_orient:
                continue
            if min(qe + heal_gap, p2) - max(qs - heal_gap, p1) >= 0:
                if q1 - 2.5 <= s <= q2 + 2.5:
                    c[3] = min(c[3], q1)
                if q1 - 2.5 <= e <= q2 + 2.5:
                    c[4] = max(c[4], q2)

    # Cut windows & ventilators out of wall strips where inner lines exist
    final_wall_strips = []
    win_boxes = []
    pier_min = 2.0 * t_px  # 18 px = 300 mm minimum corner pier

    for orient, p1, p2, s, e in clean_strips:
        runs = h_runs if orient == 'H' else v_runs
        inner = []
        for rp, rs, re in runs:
            if p1 + 1.5 <= rp <= p2 - 1.5:
                ov_s = max(s, rs)
                ov_e = min(e, re)
                if ov_e - ov_s >= 1.6 * t_px:
                    inner.append([ov_s, ov_e])
        if not inner:
            final_wall_strips.append((orient, p1, p2, s, e))
            continue
        inner.sort()
        merged_in = [inner[0]]
        for iv in inner[1:]:
            if iv[0] <= merged_in[-1][1] + 5.0:
                merged_in[-1][1] = max(merged_in[-1][1], iv[1])
            else:
                merged_in.append(iv)

        cur_s = s
        for ws, we in merged_in:
            raw_w = we - ws
            ws_c = max(ws, s + pier_min)
            we_c = min(we, e - pier_min)
            min_win_px = 6.9 * t_px  # ~62 px = 1033 mm (> 1000 mm vent threshold)
            if raw_w >= 5.7 * t_px and (we_c - ws_c) < min_win_px and (e - s) >= (min_win_px + 2 * pier_min):
                mid = 0.5 * (ws_c + we_c)
                ws_c = max(s + pier_min, mid - 0.5 * min_win_px)
                we_c = min(e - pier_min, ws_c + min_win_px)
            if we_c - ws_c >= 2.2 * t_px:
                if ws_c - cur_s >= 1.3 * t_px:
                    final_wall_strips.append((orient, p1, p2, cur_s, ws_c))
                win_boxes.append((orient, p1, p2, ws_c, we_c))
                cur_s = we_c
        if e - cur_s >= 1.3 * t_px:
            final_wall_strips.append((orient, p1, p2, cur_s, e))

    # Check colinear gaps between clean_strips for windows (>= 2 inner lines) or doorways
    for orient in ('H', 'V'):
        st = sorted([c for c in clean_strips if c[0] == orient], key=lambda x: (round(x[1]), x[3]))
        for i in range(len(st) - 1):
            if abs(st[i][1] - st[i + 1][1]) <= 1.5 and abs(st[i][2] - st[i + 1][2]) <= 1.5:
                gs, ge = st[i][4], st[i + 1][3]
                if 2.2 * t_px <= ge - gs <= 24.0 * t_px:
                    p1, p2 = st[i][1], st[i][2]
                    runs = h_runs if orient == 'H' else v_runs
                    n_in = sum(1 for rp, rs, re in runs if p1 + 1.5 <= rp <= p2 - 1.5 and min(ge, re) - max(gs, rs) >= 1.6 * t_px)
                    if n_in >= 2:
                        win_boxes.append((orient, p1, p2, gs, ge))
                    elif 3.3 * t_px <= ge - gs <= 11.0 * t_px:
                        door_lines.append((orient, 0.5 * (p1 + p2), gs, ge))

    # Automatically detect diagonal 'X' shaft crosses inside enclosed voids
    wall_mask = np.zeros((H, W), dtype=np.uint8)
    for orient, p1, p2, s, e in clean_strips:
        if orient == 'H':
            wall_mask[max(0, int(p1)):min(H, int(math.ceil(p2)) + 1), max(0, int(s)):min(W, int(math.ceil(e)) + 1)] = 1
        else:
            wall_mask[max(0, int(s)):min(H, int(math.ceil(e)) + 1), max(0, int(p1)):min(W, int(math.ceil(p2)) + 1)] = 1

    free_space = (wall_mask == 0).astype(np.uint8)
    n_cc, cc_labels, cc_stats, _ = cv2.connectedComponentsWithStats(free_space, connectivity=4)
    shaft_diags = []
    fg_dil = cv2.dilate(fg, np.ones((3, 3), np.uint8))
    for lbl in range(1, n_cc):
        vx0 = cc_stats[lbl, cv2.CC_STAT_LEFT]
        vy0 = cc_stats[lbl, cv2.CC_STAT_TOP]
        vw = cc_stats[lbl, cv2.CC_STAT_WIDTH]
        vh = cc_stats[lbl, cv2.CC_STAT_HEIGHT]
        if vx0 <= 1 or vy0 <= 1 or vx0 + vw >= W - 1 or vy0 + vh >= H - 1:
            continue
        if not (2.0 * t_px <= vw <= 18.0 * t_px and 2.0 * t_px <= vh <= 18.0 * t_px):
            continue
        # Sample both main diagonals of the void bounding box
        ts = np.linspace(0.15, 0.85, 25)
        xs_d1 = np.clip((vx0 + ts * (vw - 1)).astype(int), 0, W - 1)
        ys_d1 = np.clip((vy0 + ts * (vh - 1)).astype(int), 0, H - 1)
        ys_d2 = np.clip((vy0 + (1.0 - ts) * (vh - 1)).astype(int), 0, H - 1)
        d1_hit = float(fg_dil[ys_d1, xs_d1].mean())
        d2_hit = float(fg_dil[ys_d2, xs_d1].mean())
        if d1_hit >= 0.65 and d2_hit >= 0.65:
            shaft_diags.append((float(vx0), float(vy0), float(vx0 + vw), float(vy0 + vh)))

    doc = ezdxf.new('R2004')
    doc.header['$INSUNITS'] = 4  # millimeters
    msp = doc.modelspace()

    def to_cad(x_px: float, y_px: float) -> Tuple[float, float]:
        return (round(float(x_px) * scale, 2), round(float(H - y_px) * scale, 2))

    for orient, p1, p2, s, e in final_wall_strips:
        if orient == 'H':
            pts = [to_cad(s, p1), to_cad(e, p1), to_cad(e, p2), to_cad(s, p2)]
        else:
            pts = [to_cad(p1, s), to_cad(p2, s), to_cad(p2, e), to_cad(p1, e)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': 'WALL'})

    for orient, p1, p2, ws, we in win_boxes:
        for frac in (0.0, 0.33, 0.67, 1.0):
            pos = p1 + frac * (p2 - p1)
            if orient == 'H':
                msp.add_line(to_cad(ws, pos), to_cad(we, pos), dxfattribs={'layer': 'WIN'})
            else:
                msp.add_line(to_cad(pos, ws), to_cad(pos, we), dxfattribs={'layer': 'WIN'})

    for orient, pos_mid, ds, de in door_lines:
        if orient == 'H':
            msp.add_line(to_cad(ds, pos_mid), to_cad(de, pos_mid), dxfattribs={'layer': 'DOOR'})
        else:
            msp.add_line(to_cad(pos_mid, ds), to_cad(pos_mid, de), dxfattribs={'layer': 'DOOR'})

    for vx0, vy0, vx1, vy1 in shaft_diags:
        msp.add_line(to_cad(vx0, vy0), to_cad(vx1, vy1), dxfattribs={'layer': '0'})
        msp.add_line(to_cad(vx0, vy1), to_cad(vx1, vy0), dxfattribs={'layer': '0'})

    doc.saveas(out_dxf_path)
    logger.info(
        "Vectorized image %s -> %s (%d wall pieces, %d windows/vents, %d shafts)",
        os.path.basename(image_path), out_dxf_path, len(final_wall_strips), len(win_boxes), len(shaft_diags)
    )
    return out_dxf_path


def _vectorize_solid_plan(im_bgr: np.ndarray, out_dxf_path: str) -> str:
    """
    Vectorize a colored / solid-wall floor plan image (either solid white walls on a dark/colored
    background or solid dark-grey/black/red-outlined CAD walls & columns with blue windows).
    """
    H, W, _ = im_bgr.shape
    b = im_bgr[:, :, 0].astype(np.int32)
    g = im_bgr[:, :, 1].astype(np.int32)
    r = im_bgr[:, :, 2].astype(np.int32)
    gray = cv2.cvtColor(im_bgr, cv2.COLOR_BGR2GRAY)

    white_mask = ((r >= 235) & (g >= 235) & (b >= 235)).astype(np.uint8)
    white_ratio = float(white_mask.mean())

    if 0.015 <= white_ratio <= 0.22:
        wmask = white_mask
        is_white_wall_plan = True
        h_open = cv2.morphologyEx(wmask, cv2.MORPH_OPEN, np.ones((4, 16), np.uint8))
        v_open = cv2.morphologyEx(wmask, cv2.MORPH_OPEN, np.ones((16, 4), np.uint8))
        min_t, min_l = 5.0, 20.0
    else:
        is_white_wall_plan = False
        max_c = np.maximum(np.maximum(r, g), b)
        min_c = np.minimum(np.minimum(r, g), b)
        dark_gray = (r <= 125) & (g <= 125) & (b <= 125) & ((max_c - min_c) <= 20)
        red_outline = (r >= 165) & (g <= 65) & (b <= 65)
        wmask = cv2.morphologyEx((dark_gray | red_outline).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        h_open = cv2.morphologyEx(wmask, cv2.MORPH_OPEN, np.ones((2, 11), np.uint8))
        v_open = cv2.morphologyEx(wmask, cv2.MORPH_OPEN, np.ones((11, 2), np.uint8))
        min_t, min_l = 2.0, 11.0

    raw_strips = []
    thicknesses = []
    for orient, m in (('H', h_open), ('V', v_open)):
        n_cc, _, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        for i in range(1, n_cc):
            x, y, w_box, h_box, _ = stats[i]
            t = float(h_box if orient == 'H' else w_box)
            l = float(w_box if orient == 'H' else h_box)
            if min_t <= t <= 28.0 and l >= min_l:
                p1 = float(y if orient == 'H' else x)
                p2 = float((y + h_box) if orient == 'H' else (x + w_box))
                s = float(x if orient == 'H' else y)
                e = float((x + w_box) if orient == 'H' else (y + h_box))
                raw_strips.append([orient, p1, p2, s, e])
                if 3.0 <= t <= 16.0:
                    thicknesses.append(t)

    if not raw_strips:
        raise RuntimeError("No structural walls detected in the uploaded image.")

    t_px = float(np.median(thicknesses)) if thicknesses else 8.0
    scale = (180.0 if is_white_wall_plan else 150.0) / max(t_px, 3.0)
    heal_gap = t_px + 3.0

    # Group colinear strips and heal T-junction breaks
    clean_strips = []
    for orient in ('H', 'V'):
        st = [c for c in raw_strips if c[0] == orient]
        used = [False] * len(st)
        for i in range(len(st)):
            if used[i]:
                continue
            grp = [st[i]]
            used[i] = True
            for j in range(i + 1, len(st)):
                if not used[j] and abs(st[j][1] - st[i][1]) <= 2.5 and abs(st[j][2] - st[i][2]) <= 2.5:
                    grp.append(st[j])
                    used[j] = True
            tot_l = sum(g_s[4] - g_s[3] for g_s in grp)
            p1 = sum(g_s[1] * (g_s[4] - g_s[3]) for g_s in grp) / max(tot_l, 1.0)
            p2 = sum(g_s[2] * (g_s[4] - g_s[3]) for g_s in grp) / max(tot_l, 1.0)
            if p2 - p1 < max(3.5, 0.7 * t_px):
                mid = 0.5 * (p1 + p2)
                p1, p2 = mid - 0.5 * t_px, mid + 0.5 * t_px
            grp.sort(key=lambda g_s: g_s[3])
            merged = [[p1, p2, grp[0][3], grp[0][4]]]
            for g_s in grp[1:]:
                if g_s[3] - merged[-1][3] <= heal_gap:
                    merged[-1][3] = max(merged[-1][3], g_s[4])
                else:
                    merged.append([p1, p2, g_s[3], g_s[4]])
            for m_s in merged:
                clean_strips.append([orient, m_s[0], m_s[1], m_s[2], m_s[3]])

    # Detect enclosed dark shaft boxes (e.g. D.T. shaft between two vertical walls on white-wall plans)
    shaft_diags = []
    if is_white_wall_plan:
        v_list = sorted([c for c in clean_strips if c[0] == 'V'], key=lambda x: x[1])
        h_list = [c for c in clean_strips if c[0] == 'H']
        for i in range(len(v_list)):
            for j in range(i + 1, len(v_list)):
                vx0, vx1 = v_list[i][2], v_list[j][1]
                if not (4.0 * t_px <= vx1 - vx0 <= 12.0 * t_px):
                    continue
                ov_y0 = max(v_list[i][3], v_list[j][3])
                ov_y1 = min(v_list[i][4], v_list[j][4])
                if ov_y1 - ov_y0 < 2.5 * t_px:
                    continue
                for h_c in h_list:
                    if h_c[3] - t_px <= vx0 and h_c[4] + t_px >= vx1 and ov_y0 - t_px <= h_c[2] <= ov_y1 - 2.0 * t_px:
                        sy0 = int(round(h_c[2]))
                        sy1 = int(round(min(ov_y1, sy0 + 3.4 * t_px)))
                        sx0, sx1 = int(round(vx0 + 2)), int(round(vx1 - 2))
                        if sy1 > sy0 + 8 and sx1 > sx0 + 8:
                            patch = gray[sy0:sy1, sx0:sx1]
                            if float(patch.mean()) < 85.0:
                                clean_strips.append(['H', float(sy1), float(sy1 + t_px), v_list[i][1], v_list[j][2]])
                                shaft_diags.append((float(vx0), float(sy0), float(vx1), float(sy1)))

    # Extend strip endpoints that meet a perpendicular strip so L and T corners overlap cleanly
    for c in clean_strips:
        orient, p1, p2, s, e = c
        perp_orient = 'V' if orient == 'H' else 'H'
        for p_or, q1, q2, qs, qe in clean_strips:
            if p_or != perp_orient:
                continue
            if min(qe + heal_gap, p2) - max(qs - heal_gap, p1) >= 0:
                if q1 - 4.0 <= s <= q2 + 4.0:
                    c[3] = min(c[3], q1)
                if q1 - 4.0 <= e <= q2 + 4.0:
                    c[4] = max(c[4], q2)

    # Extract blue/cyan window lines (excluding pure blue text where G == R)
    if is_white_wall_plan:
        bmask = ((b - r >= 35) & (g - r >= 25) & (b >= 100)).astype(np.uint8)
    else:
        bmask = (((b - r >= 25) & (g >= 70) & (b >= 110)) | ((b - r >= 55) & (b >= 145))).astype(np.uint8)
    b_closed = cv2.morphologyEx(bmask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n_cc, _, b_stats, _ = cv2.connectedComponentsWithStats(b_closed, connectivity=8)

    blue_boxes = []
    for i in range(1, n_cc):
        bx, by, bw, bh, _ = b_stats[i]
        if max(bw, bh) >= max(14, int(2.2 * t_px)) and min(bw, bh) <= max(14, int(1.8 * t_px)):
            orient = 'H' if bw >= bh else 'V'
            p1 = float(by if orient == 'H' else bx)
            p2 = float((by + bh) if orient == 'H' else (bx + bw))
            s = float(bx if orient == 'H' else by)
            e = float((bx + bw) if orient == 'H' else (by + bh))
            blue_boxes.append((orient, p1, p2, s, e))

    win_boxes = []  # (orient, p1, p2, ws, we, layer)
    door_lines = []
    extra_piers = []
    pier_len = 1.8 * t_px

    brown_mask = ((r >= 50) & (r <= 145) & (g >= 20) & (g <= 100) & (b <= 70) & (r - b >= 18)).astype(np.uint8)

    def has_door_leaf(orient: str, p_mid: float, gs: float, ge: float) -> bool:
        if not is_white_wall_plan:
            return True
        pad = int(round(5.5 * t_px))
        if orient == 'H':
            x0, x1 = max(0, int(round(gs - 4))), min(W, int(round(ge + 4)))
            y0, y1 = max(0, int(round(p_mid - pad))), min(H, int(round(p_mid + pad)))
        else:
            x0, x1 = max(0, int(round(p_mid - pad))), min(W, int(round(p_mid + pad)))
            y0, y1 = max(0, int(round(gs - 4))), min(H, int(round(ge + 4)))
        return int(brown_mask[y0:y1, x0:x1].sum()) >= 15

    # Check collinear gaps between wall strips for blue windows or doorways
    used_blue = [False] * len(blue_boxes)
    for orient in ('H', 'V'):
        st = sorted([c for c in clean_strips if c[0] == orient], key=lambda x: (round(x[1] / 3.0), x[3]))
        for i in range(len(st) - 1):
            if abs(st[i][1] - st[i + 1][1]) <= 3.0 and abs(st[i][2] - st[i + 1][2]) <= 3.0:
                gs, ge = st[i][4], st[i + 1][3]
                if 1.8 * t_px <= ge - gs <= 28.0 * t_px:
                    p1, p2 = st[i][1], st[i][2]
                    hit_b = False
                    for bi, (bo, bp1, bp2, bs, be) in enumerate(blue_boxes):
                        if bo == orient and abs(0.5 * (bp1 + bp2) - 0.5 * (p1 + p2)) <= t_px + 3.0:
                            if min(ge + 4.0, be) - max(gs - 4.0, bs) >= 1.5 * t_px:
                                hit_b = True
                                used_blue[bi] = True
                    if hit_b:
                        win_boxes.append((orient, p1, p2, gs, ge, 'WIN'))
                    elif 3.0 * t_px <= ge - gs <= 9.5 * t_px and has_door_leaf(orient, 0.5 * (p1 + p2), gs, ge):
                        door_lines.append((orient, 0.5 * (p1 + p2), gs, ge))

    # Check remaining blue windows that span directly to/between perpendicular walls
    for bi, (bo, bp1, bp2, bs, be) in enumerate(blue_boxes):
        if used_blue[bi]:
            continue
        p_mid = 0.5 * (bp1 + bp2)
        p1, p2 = p_mid - 0.5 * t_px, p_mid + 0.5 * t_px
        col_strips = [c for c in clean_strips if c[0] == bo and abs(0.5 * (c[1] + c[2]) - p_mid) <= t_px + 3.0]
        perp_strips = [c for c in clean_strips if c[0] != bo and c[3] - t_px <= p_mid <= c[4] + t_px]
        if col_strips:
            p1, p2 = col_strips[0][1], col_strips[0][2]
        left_walls = [c[4] for c in col_strips if c[4] <= bs + t_px] + [c[2] for c in perp_strips if c[1] <= bs + t_px]
        right_walls = [c[3] for c in col_strips if c[3] >= be - t_px] + [c[1] for c in perp_strips if c[2] >= be - t_px]
        ws = max(left_walls) if left_walls else bs
        we = min(right_walls) if right_walls else be
        if we - ws >= 2.0 * t_px:
            has_left_col = any(abs(c[4] - ws) <= 3.0 for c in col_strips)
            has_right_col = any(abs(c[3] - we) <= 3.0 for c in col_strips)
            if not has_left_col and we - ws >= 5.0 * t_px:
                extra_piers.append([bo, p1, p2, ws - 0.5 * t_px, ws + pier_len])
                ws += pier_len
            if not has_right_col and we - ws >= 5.0 * t_px:
                extra_piers.append([bo, p1, p2, we - pier_len, we + 0.5 * t_px])
                we -= pier_len
            win_boxes.append((bo, p1, p2, ws, we, 'WIN'))

    # Detect corner-flush doorways (where a wall strip stops 3.2..7.5 * t_px short of a perpendicular wall)
    jamb_stub_len = 1.35 * t_px
    for orient, p1, p2, s, e in list(clean_strips):
        p_mid = 0.5 * (p1 + p2)
        perp_orient = 'V' if orient == 'H' else 'H'
        perps = [c for c in clean_strips if c[0] == perp_orient and c[3] - t_px <= p_mid <= c[4] + t_px]
        col_others = [c for c in clean_strips if c[0] == orient and abs(c[1] - p1) <= 3.0 and c[3] != s]
        has_win_s = any(wo == orient and abs(0.5 * (wp1 + wp2) - p_mid) <= t_px and abs(we - s) <= 2.5 * t_px for wo, wp1, wp2, ws, we, _ in win_boxes)
        has_win_e = any(wo == orient and abs(0.5 * (wp1 + wp2) - p_mid) <= t_px and abs(ws - e) <= 2.5 * t_px for wo, wp1, wp2, ws, we, _ in win_boxes)
        if not has_win_s and not any(0 < s - c[4] <= 10.0 * t_px for c in col_others):
            for _, q1, q2, qs, qe in perps:
                if 3.2 * t_px <= s - q2 <= 7.5 * t_px and has_door_leaf(orient, p_mid, q2, s):
                    jamb_end = q2 + jamb_stub_len
                    extra_piers.append([orient, p1, p2, q1, jamb_end])
                    door_lines.append((orient, p_mid, jamb_end, s))
                    break
        if not has_win_e and not any(0 < c[3] - e <= 10.0 * t_px for c in col_others):
            for _, q1, q2, qs, qe in perps:
                if 3.2 * t_px <= q1 - e <= 7.5 * t_px and has_door_leaf(orient, p_mid, e, q1):
                    jamb_start = q1 - jamb_stub_len
                    extra_piers.append([orient, p1, p2, jamb_start, q2])
                    door_lines.append((orient, p_mid, e, jamb_start))
                    break

    # Detect outer balcony multi-line railings between parallel wall ends on white-wall presentation plans
    if is_white_wall_plan:
        v_sorted = sorted([c for c in clean_strips if c[0] == 'V'], key=lambda x: x[1])
        min_v_y = min((c[3] for c in v_sorted), default=0.0)
        for i in range(len(v_sorted)):
            for j in range(i + 1, len(v_sorted)):
                vx0, vx1 = v_sorted[i][2], v_sorted[j][1]
                if not (6.0 * t_px <= vx1 - vx0 <= 25.0 * t_px):
                    continue
                if abs(v_sorted[i][3] - v_sorted[j][3]) <= 4.0 and v_sorted[i][3] <= min_v_y + 2.0 * t_px:
                    ry0 = int(round(min(v_sorted[i][3], v_sorted[j][3])))
                    ry1 = int(round(ry0 + t_px))
                    rx0, rx1 = int(round(vx0 + 4)), int(round(vx1 - 4))
                    if rx1 > rx0 and 0 <= ry0 < ry1 <= H:
                        band = gray[ry0:ry1, rx0:rx1]
                        wband = wmask[ry0:ry1, rx0:rx1]
                        if float((band > 95).mean()) >= 0.20 and float(wband.mean()) < 0.40:
                            extra_piers.append(['H', float(ry0), float(ry1), vx0 - 0.5 * t_px, vx0 + pier_len])
                            extra_piers.append(['H', float(ry0), float(ry1), vx1 - pier_len, vx1 + 0.5 * t_px])
                            win_boxes.append(('H', float(ry0), float(ry1), vx0 + pier_len, vx1 - pier_len, 'A-PARAPET WALL'))
        # Also check vertical outer railing on right side of dry balcony
        for vc in v_sorted:
            for hc in [c for c in clean_strips if c[0] == 'H']:
                if abs(hc[4] - vc[2]) <= 4.0 and 5.0 * t_px <= hc[1] - vc[4] <= 18.0 * t_px:
                    rx0, rx1 = int(round(vc[1])), int(round(vc[2]))
                    ry0, ry1 = int(round(vc[4] + 3)), int(round(hc[1] - 3))
                    if ry1 > ry0 and 0 <= rx0 < rx1 <= W:
                        band = gray[ry0:ry1, rx0:rx1]
                        wband = wmask[ry0:ry1, rx0:rx1]
                        if float((band > 95).mean()) >= 0.20 and float(wband.mean()) < 0.40:
                            extra_piers.append(['V', vc[1], vc[2], vc[4] - 0.5 * t_px, vc[4] + pier_len])
                            extra_piers.append(['V', vc[1], vc[2], hc[1] - pier_len, hc[1] + 0.5 * t_px])
                            win_boxes.append(('V', vc[1], vc[2], vc[4] + pier_len, hc[1] - pier_len, 'A-PARAPET WALL'))

    clean_strips.extend(extra_piers)

    doc = ezdxf.new('R2004')
    doc.header['$INSUNITS'] = 4  # millimeters
    msp = doc.modelspace()

    def to_cad(x_px: float, y_px: float) -> Tuple[float, float]:
        return (round(float(x_px) * scale, 2), round(float(H - y_px) * scale, 2))

    for orient, p1, p2, s, e in clean_strips:
        if orient == 'H':
            pts = [to_cad(s, p1), to_cad(e, p1), to_cad(e, p2), to_cad(s, p2)]
        else:
            pts = [to_cad(p1, s), to_cad(p2, s), to_cad(p2, e), to_cad(p1, e)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': 'WALL'})

    for orient, p1, p2, ws, we, wlayer in win_boxes:
        for frac in (0.0, 0.33, 0.67, 1.0):
            pos = p1 + frac * (p2 - p1)
            if orient == 'H':
                msp.add_line(to_cad(ws, pos), to_cad(we, pos), dxfattribs={'layer': wlayer})
            else:
                msp.add_line(to_cad(pos, ws), to_cad(pos, we), dxfattribs={'layer': wlayer})

    for orient, pos_mid, ds, de in door_lines:
        if orient == 'H':
            msp.add_line(to_cad(ds, pos_mid), to_cad(de, pos_mid), dxfattribs={'layer': 'DOOR'})
        else:
            msp.add_line(to_cad(pos_mid, ds), to_cad(pos_mid, de), dxfattribs={'layer': 'DOOR'})

    for vx0, vy0, vx1, vy1 in shaft_diags:
        msp.add_line(to_cad(vx0, vy0), to_cad(vx1, vy1), dxfattribs={'layer': '0'})
        msp.add_line(to_cad(vx0, vy1), to_cad(vx1, vy0), dxfattribs={'layer': '0'})

    doc.saveas(out_dxf_path)
    logger.info(
        "Vectorized solid-wall image -> %s (%d wall pieces, %d windows/parapets, %d doors, %d shafts)",
        out_dxf_path, len(clean_strips), len(win_boxes), len(door_lines), len(shaft_diags)
    )
    return out_dxf_path



# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  NEW ENTRY POINT - raster wall engine (raster_walls.py) with review report
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def _load_gray(image_path: str):
    im_raw = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if im_raw is None:
        raise RuntimeError(f"Could not read image file: {image_path}")
    if im_raw.ndim == 3:
        if im_raw.shape[2] == 4:
            alpha = im_raw[:, :, 3:4].astype(np.float32) / 255.0
            rgb = im_raw[:, :, :3].astype(np.float32)
            bg_rgb = np.median(rgb.reshape(-1, 3), axis=0)
            comp = (rgb * alpha + bg_rgb * (1.0 - alpha)).astype(np.uint8)
            return comp, cv2.cvtColor(comp, cv2.COLOR_BGR2GRAY)
        return im_raw, cv2.cvtColor(im_raw, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(im_raw, cv2.COLOR_GRAY2BGR), im_raw


def _shaft_crosses(fg: np.ndarray, bands, t_px: float) -> List[Tuple[float, float, float, float]]:
    """Enclosed voids crossed by both diagonals (service shafts / ducts drawn with an X)."""
    H, W = fg.shape
    wall_mask = np.zeros((H, W), np.uint8)
    for b in bands:
        x0, y0, x1, y1 = b.rect()
        wall_mask[max(0, int(y0)):min(H, int(math.ceil(y1)) + 1), max(0, int(x0)):min(W, int(math.ceil(x1)) + 1)] = 1
    free = (wall_mask == 0).astype(np.uint8)
    n_cc, _, st, _ = cv2.connectedComponentsWithStats(free, connectivity=4)
    fg_d = cv2.dilate(fg, np.ones((3, 3), np.uint8))
    out = []
    for k in range(1, n_cc):
        x0, y0, w, h = st[k, 0], st[k, 1], st[k, 2], st[k, 3]
        if x0 <= 1 or y0 <= 1 or x0 + w >= W - 1 or y0 + h >= H - 1:
            continue
        if not (2.0 * t_px <= w <= 40.0 * t_px and 2.0 * t_px <= h <= 40.0 * t_px):
            continue
        ts = np.linspace(0.15, 0.85, 25)
        xs = np.clip((x0 + ts * (w - 1)).astype(int), 0, W - 1)
        y_d1 = np.clip((y0 + ts * (h - 1)).astype(int), 0, H - 1)
        y_d2 = np.clip((y0 + (1.0 - ts) * (h - 1)).astype(int), 0, H - 1)
        if fg_d[y_d1, xs].mean() >= 0.65 and fg_d[y_d2, xs].mean() >= 0.65:
            out.append((float(x0), float(y0), float(x0 + w), float(y0 + h)))
    return out


def image_to_dxf(image_path: str, out_dxf_path: str, options: dict = None) -> str:
    """
    Convert a raster floor plan into an architectural DXF:
      WALL_RASTER  closed wall rectangles (mm)      WIN   4-line window symbols
      DOOR         door centre lines (door hints)   0     shaft X diagonals
    and write `<out>.review.json` with every repair, opening, uncertain gap, rejected candidate
    and the scale used, so the pipeline can show / validate the detection.

    options: wall_mm (thickness of the main wall, default 150), mm_per_px (overrides wall_mm),
             gap_max_mm, door_min_mm.
    """
    import json
    from .line_vectorizer import has_poche_walls, vectorize_poche_plan
    from .raster_walls import detect_line_plan

    opts = dict(options or {})
    im_bgr, gray = _load_gray(image_path)
    H, W = gray.shape
    is_poche, _ = has_poche_walls(im_bgr)
    if is_poche:
        vectorize_poche_plan(
            im_bgr,
            out_dxf_path,
            mm_per_px=opts.get('mm_per_px'),
            wall_mm=float(opts.get('wall_mm') or 150.0),
            text_labels=opts.get('text_labels'),
        )
        return out_dxf_path
    strength, fg = foreground_mask(gray)
    res = detect_line_plan(fg, strength, wall_mm=float(opts.get('wall_mm') or 150.0),
                           mm_per_px=opts.get('mm_per_px'), gap_max_mm=float(opts.get('gap_max_mm', 3600.0)),
                           door_min_mm=float(opts.get('door_min_mm', 600.0)))
    if not res.get('ok') or len(res['bands']) < 6:
        logger.warning("Raster engine found no wall network (%s) - trying legacy / solid-wall vectorisers",
                       res.get('reason', f"{len(res.get('bands', []))} walls"))
        out = _legacy_image_to_dxf(image_path, out_dxf_path)
        with open(out_dxf_path + '.review.json', 'w', encoding='utf-8') as fh:
            json.dump({'engine': 'legacy', 'size_px': [W, H], 'note': 'new raster engine found no double-line '
                       'wall network; legacy strip / solid-wall vectoriser used'}, fh)
        return out

    scale = res['scale']

    def to_cad(x_px: float, y_px: float) -> Tuple[float, float]:
        return (round(float(x_px) * scale, 2), round(float(H - y_px) * scale, 2))

    def rect_mm(r):
        a, b = to_cad(r[0], r[3]), to_cad(r[2], r[1])
        return [a[0], a[1], b[0], b[1]]

    doc = ezdxf.new('R2004')
    doc.header['$INSUNITS'] = 4
    msp = doc.modelspace()
    for b in res['bands']:
        x0, y0, x1, y1 = b.rect()
        msp.add_lwpolyline([to_cad(x0, y0), to_cad(x1, y0), to_cad(x1, y1), to_cad(x0, y1)], close=True,
                           dxfattribs={'layer': 'WALL_RASTER'})

    def win_symbol(o, p1, p2, s, e, layer='WIN'):
        for frac in (0.0, 0.33, 0.67, 1.0):
            pos = p1 + frac * (p2 - p1)
            if o == 'H':
                msp.add_line(to_cad(s, pos), to_cad(e, pos), dxfattribs={'layer': layer})
            else:
                msp.add_line(to_cad(pos, s), to_cad(pos, e), dxfattribs={'layer': layer})

    emitted = []
    for w in res['windows']:
        win_symbol(w.o, w.p1, w.p2, w.s, w.e)
        emitted.append(w)
    for g in res['gaps']:
        if g.kind == 'window' and not any(w.o == g.o and abs(w.mid - 0.5 * (g.p1 + g.p2)) <= 2.5 and
                                          min(w.e, g.e) - max(w.s, g.s) > 0.5 * g.width for w in emitted):
            win_symbol(g.o, g.p1, g.p2, g.s, g.e)
        elif g.kind == 'door':
            m = 0.5 * (g.p1 + g.p2)
            a, b = ((g.s, m), (g.e, m)) if g.o == 'H' else ((m, g.s), (m, g.e))
            msp.add_line(to_cad(*a), to_cad(*b), dxfattribs={'layer': 'DOOR'})
    shafts = _shaft_crosses(fg, res['bands'], res['t_main'])
    for x0, y0, x1, y1 in shafts:
        msp.add_line(to_cad(x0, y0), to_cad(x1, y1), dxfattribs={'layer': '0'})
        msp.add_line(to_cad(x0, y1), to_cad(x1, y0), dxfattribs={'layer': '0'})
    for txt, lx_px, ly_px in (opts.get('text_labels') or []):
        cx, cy = to_cad(lx_px, ly_px)
        msp.add_text(str(txt), dxfattribs={'layer': 'TEXT', 'insert': (cx, cy), 'height': 150.0})
    doc.saveas(out_dxf_path)

    report = {
        'engine': 'raster_walls', 'source': os.path.basename(image_path), 'size_px': [W, H],
        'mm_per_px': round(scale, 4),
        'scale_source': ('user-supplied mm/px' if opts.get('mm_per_px') else
                         f"main wall thickness {res['t_main']:.1f} px assumed = {float(opts.get('wall_mm') or 150.0):.0f} mm"),
        'thickness_modes_px': [round(m, 2) for m in res['modes']],
        'thickness_modes_mm': [round(m * scale) for m in res['modes']],
        'walls': [{'rect_px': [round(v, 1) for v in b.rect()], 'rect_mm': rect_mm(b.rect()), 'src': b.src,
                   'term': list(b.term)} for b in res['bands']],
        'windows': [{'rect_px': [round(v, 1) for v in w.rect()], 'rect_mm': rect_mm(w.rect()),
                     'sliding': w.sliding, 'inner_lines': w.n_inner} for w in res['windows']],
        'gaps': [{'id': g.id, 'kind': g.kind, 'reason': g.reason, 'rect_px': [round(v, 1) for v in g.rect()],
                  'rect_mm': rect_mm(g.rect()), 'width_mm': round(g.width * scale), 'o': g.o,
                  'evidence': g.evidence} for g in res['gaps']],
        'rejected': [dict(r, rect_mm=rect_mm(r['rect'])) for r in res['rejected']],
        'isolated': [dict(i, bbox_mm=rect_mm(i['bbox'])) for i in res['isolated']],
        'trimmed': [dict(t, xy_mm=list(to_cad(*t['xy']))) for t in res['trimmed']],
        'dangling': [dict(d, xy_mm=list(to_cad(*d['xy']))) for d in res['dangling']],
        'shafts': len(shafts),
    }
    def _np(o):
        if isinstance(o, np.generic):
            return o.item()
        raise TypeError(type(o).__name__)

    with open(out_dxf_path + '.review.json', 'w', encoding='utf-8') as fh:
        json.dump(report, fh, default=_np)
    logger.info("Vectorized %s -> %s: %d walls, %d windows, %d gaps classified, scale %.3f mm/px",
                os.path.basename(image_path), out_dxf_path, len(res['bands']), len(res['windows']),
                len(res['gaps']), scale)
    return out_dxf_path
