"""Image segmentation of the floor plan (OpenCV), independent of CAD layer names.

The whole drawing (every layer) is rasterised at 20 mm/pixel. The empty space between the lines is
split into connected regions and every region is measured with a distance transform:

    * the region touching the image border         -> OUTSIDE
    * narrow, elongated regions (70-650 mm wide)   -> WALL BANDS (the inside of a wall drawn as 2 lines)
    * wide regions (> 1.5 m2)                       -> ROOMS / open spaces

Uses
    1. per-wall image support: how much of each detected wall is confirmed by a segmented wall band
    2. new wall candidates: wall bands that no detected wall covers (later recognised by the AI)
    3. a colour segmentation preview for the web page
"""
import base64
import logging
import math
from typing import Dict, List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

RES = 20.0            # mm per pixel
WALL_MIN, WALL_MAX = 70.0, 650.0
WINDOW_WORDS = ('WIN', 'GLASS', 'GLAZ')
FURN_WORDS = ('FURN', 'SANIT', 'FIXT', 'KITCH', 'STAIR', 'ELEV', 'DOTTED', 'TREAT', 'PANEL', 'CHANDELIER')


def _category(layer: str) -> str:
    up = layer.upper()
    if any(k in up for k in WINDOW_WORDS):
        return 'window'
    if any(k in up for k in FURN_WORDS):
        return 'furniture'
    if any(k in up for k in ('WALL', 'RCC', 'COL', 'PARTITION', 'BRICK', 'STRUCT')):
        return 'wall'
    return 'other'


def _band_shape(lab, i, stats) -> bool:
    """A wall band is a strip: either a filled, elongated rectangle, or a thin L/T/U-shaped strip.
    Triangles from X-crossed shafts/wardrobes and blobs are rejected."""
    x, y, w, h = (stats[i, k] for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
    m = (lab[y:y + h, x:x + w] == i).astype(np.uint8)
    pts = cv2.findNonZero(m)
    (_, _), (rw, rh), _ = cv2.minAreaRect(pts)
    rw, rh = max(rw, 1), max(rh, 1)
    fill = stats[i, cv2.CC_STAT_AREA] / (rw * rh)
    aspect = max(rw, rh) / min(rw, rh)
    if fill >= 0.72 and aspect >= 2.5:
        return True                                   # straight wall band
    # bent wall band (L/T/U): thin everywhere -> opening by 1/3 of its width removes almost nothing
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = cv2.convexHull(max(cs, key=cv2.contourArea))
    solidity = stats[i, cv2.CC_STAT_AREA] / max(cv2.contourArea(hull), 1)
    return fill < 0.45 and solidity < 0.5 and aspect >= 1.0 and stats[i, cv2.CC_STAT_AREA] > 300


def segment(lines: List[Tuple[str, List[Tuple[float, float]], bool]], walls, margin: float = 1500.0) -> Dict:
    """lines: (layer, points_mm, closed) already in the plan's (recentred) mm coordinates."""
    wl = [w for w in walls if w.kind == 'wall']
    xs = [p[0] for w in wl for p in w.polygon]
    ys = [p[1] for w in wl for p in w.polygon]
    x0, y0 = min(xs) - margin, min(ys) - margin
    W = int((max(xs) + margin - x0) / RES) + 1
    H = int((max(ys) + margin - y0) / RES) + 1

    def px(pts):
        return np.array([[(x - x0) / RES, H - 1 - (y - y0) / RES] for x, y in pts], dtype=np.int32)

    ink = np.zeros((H, W), np.uint8)
    for _layer, pts, closed in lines:
        if any(x0 - 5000 < x < x0 + W * RES + 5000 and y0 - 5000 < y < y0 + H * RES + 5000 for x, y in pts[:4]):
            cv2.polylines(ink, [px(pts)], bool(closed), 255, 1, lineType=cv2.LINE_8)
    free = (ink == 0).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(free, connectivity=4)
    dist = cv2.distanceTransform(free, cv2.DIST_L2, 5)

    border = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])).tolist())
    kind = np.zeros(n, np.uint8)          # 0 ink, 1 outside, 2 wall band, 3 room, 4 other/small
    width = np.zeros(n)
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if i in border:
            kind[i] = 1
            continue
        if area < 12:
            kind[i] = 4
            continue
        comp = dist[lab == i]
        wd = 2 * float(np.percentile(comp, 98)) * RES + RES          # band width in mm
        width[i] = wd
        length = area * RES * RES / max(wd, 1)
        if WALL_MIN <= wd <= WALL_MAX and length >= max(2.2 * wd, 350) and _band_shape(lab, i, stats):
            kind[i] = 2
        elif area * RES * RES > 1.5e6:
            kind[i] = 3
        else:
            kind[i] = 4
    band = (kind[lab] == 2).astype(np.uint8)

    border_mask = np.zeros((H, W), np.uint8)
    for b in border:
        border_mask[lab == b] = 1

    # Extract accurate building perimeter outline from inside_mask:
    inside_mask = (border_mask == 0).astype(np.uint8)
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    closed_env = cv2.morphologyEx(inside_mask, cv2.MORPH_CLOSE, k_close)
    contours, _ = cv2.findContours(closed_env, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    main_contours = [c for c in contours if cv2.contourArea(c) * (RES ** 2) > 1e7]

    outline_loops = []
    for c in main_contours:
        epsilon = 0.0025 * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, epsilon, True)
        ring = []
        for pt in approx:
            cx_px, cy_px = pt[0]
            ring.append((round(float(x0 + cx_px * RES), 1), round(float(y0 + (H - 1 - cy_px) * RES), 1)))
        if len(ring) > 2:
            outline_loops.append(ring)

    # ---- per-wall support --------------------------------------------------------------------
    wall_mask = np.zeros((H, W), np.uint8)
    support: Dict[str, float] = {}
    for w in wl:
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [px(w.polygon)], 1)
        wall_mask |= m
        core = cv2.erode(m, np.ones((3, 3), np.uint8)) if m.sum() > 40 else m
        tot = int(core.sum())
        support[w.id] = round(float((core & band).sum()) / tot, 2) if tot else 0.0

    # ---- new wall candidates (bands not covered by any detected wall) ------------------------
    covered = cv2.dilate(wall_mask, np.ones((5, 5), np.uint8))
    element_cross = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    kernel_touch = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    cands = []

    from shapely.geometry import LineString, Polygon
    from shapely.strtree import STRtree
    segs, lays, cats = [], [], []
    for layer, pts, closed in lines:
        pp = list(pts) + ([pts[0]] if closed else [])
        for a, b in zip(pp, pp[1:]):
            if a != b:
                segs.append(LineString([a, b]))
                lays.append(layer)
                cats.append(_category(layer))
    tree = STRtree(segs) if segs else None

    for i in range(1, n):
        if kind[i] != 2:
            continue
        m = (lab == i).astype(np.uint8)
        area = int(m.sum())
        if area * RES * RES < 1.5e5:                                  # < 0.15 m2: too small to matter
            continue
        if (m & (covered > 0)).sum() > 0.3 * area:
            continue

        mm = m.astype(np.uint8)
        cs, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        c = cv2.approxPolyDP(c, 1.0, True)
        poly = [(x0 + (p[0][0] + .5) * RES, y0 + (H - 1 - p[0][1] + .5) * RES) for p in c]
        if len(poly) < 3:
            continue
        geom = Polygon(poly).buffer(0)
        if geom.is_empty:
            continue
        if geom.geom_type == 'MultiPolygon':
            geom = max(geom.geoms, key=lambda g: g.area)
        ring = geom.exterior.buffer(45) if hasattr(geom, 'exterior') and geom.exterior else geom.buffer(45)

        # Check touching layers: filter out stairs
        stair_len = 0.0
        tot_len = 0.0
        furn_len = 0.0
        if tree:
            for j in tree.query(ring):
                il = segs[j].intersection(ring).length
                tot_len += il
                up_l = lays[j].upper()
                if 'STAIR' in up_l:
                    stair_len += il
                if cats[j] == 'furniture':
                    furn_len += il
        if tot_len > 0 and (stair_len / tot_len) > 0.3:
            continue                                                  # skip stair treads

        dilated = cv2.dilate(m, kernel_touch)
        touches_border = bool((dilated & border_mask).any())

        # If it touches furniture lines (>35% of perimeter or >0 for interior), skip it
        if tot_len > 0 and (furn_len / tot_len) > 0.35:
            continue
        if not touches_border and tot_len > 0 and furn_len > 0:
            continue

        mrr = geom.minimum_rotated_rectangle
        if mrr.geom_type != 'Polygon':
            continue
        coords = list(mrr.exterior.coords)[:4]
        s0 = math.dist(coords[0], coords[1])
        s1 = math.dist(coords[1], coords[2])
        L, T = max(s0, s1), min(s0, s1)

        w_type = 'exterior' if touches_border else 'interior'
        if w_type == 'interior':
            t_val = min(max(float(width[i]) if 70 <= width[i] <= 250 else float(T), 100.0), 200.0)
        else:
            t_val = min(max(float(width[i]) if 70 <= width[i] <= 300 else float(T), 150.0), 250.0)

        if L >= 350 and 60 <= T <= 650:
            if s0 >= s1:
                s_mid = ((coords[0][0] + coords[3][0]) / 2, (coords[0][1] + coords[3][1]) / 2)
                e_mid = ((coords[1][0] + coords[2][0]) / 2, (coords[1][1] + coords[2][1]) / 2)
            else:
                s_mid = ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
                e_mid = ((coords[2][0] + coords[3][0]) / 2, (coords[2][1] + coords[3][1]) / 2)
            poly_clean = [(round(float(a), 1), round(float(b), 1)) for a, b in list(geom.exterior.coords)[:-1]]
            cands.append({
                'poly': poly_clean, 'width': int(round(t_val)), 'area_m2': round(area * RES * RES / 1e6, 3),
                'start_point': (round(float(s_mid[0]), 1), round(float(s_mid[1]), 1)),
                'end_point': (round(float(e_mid[0]), 1), round(float(e_mid[1]), 1)),
                'length': round(float(L), 1), 'thickness': round(float(t_val), 1),
                'wall_type': w_type
            })
            cv2.fillPoly(covered, [px(poly_clean)], 1)
        elif T > 650:
            # Bent L-shaped / U-shaped band (e.g. balconies): decompose via skeleton
            skeleton = np.zeros_like(m)
            temp = np.zeros_like(m)
            m_thin = m.copy()
            done = False
            while not done:
                eroded = cv2.erode(m_thin, element_cross)
                temp = cv2.dilate(eroded, element_cross)
                temp = cv2.subtract(m_thin, temp)
                skeleton = cv2.bitwise_or(skeleton, temp)
                m_thin = eroded.copy()
                if cv2.countNonZero(m_thin) == 0:
                    done = True

            lines_p = cv2.HoughLinesP(skeleton, 1, np.pi/180, threshold=15,
                                      minLineLength=int(400/RES), maxLineGap=int(150/RES))
            if lines_p is not None:
                used_lines = []
                for lp in lines_p:
                    x1_px, y1_px, x2_px, y2_px = lp[0]
                    x1_mm = x0 + x1_px * RES
                    y1_mm = y0 + (H - 1 - y1_px) * RES
                    x2_mm = x0 + x2_px * RES
                    y2_mm = y0 + (H - 1 - y2_px) * RES
                    seg_len = math.hypot(x2_mm - x1_mm, y2_mm - y1_mm)
                    if seg_len < 400:
                        continue
                    mid_pt = ((x1_mm + x2_mm)/2, (y1_mm + y2_mm)/2)
                    if any(math.hypot(mid_pt[0] - u[0], mid_pt[1] - u[1]) < 300 for u in used_lines):
                        continue
                    used_lines.append(mid_pt)

                    t_seg = float(width[i]) if 70 <= width[i] <= 250 else 180.0
                    nx = -(y2_mm - y1_mm) / seg_len * t_seg / 2
                    ny = (x2_mm - x1_mm) / seg_len * t_seg / 2
                    seg_poly = [
                        (round(float(x1_mm + nx), 1), round(float(y1_mm + ny), 1)),
                        (round(float(x2_mm + nx), 1), round(float(y2_mm + ny), 1)),
                        (round(float(x2_mm - nx), 1), round(float(y2_mm - ny), 1)),
                        (round(float(x1_mm - nx), 1), round(float(y1_mm - ny), 1)),
                    ]
                    cands.append({
                        'poly': seg_poly, 'width': int(round(t_seg)),
                        'area_m2': round(seg_len * t_seg / 1e6, 3),
                        'start_point': (round(float(x1_mm), 1), round(float(y1_mm), 1)),
                        'end_point': (round(float(x2_mm), 1), round(float(y2_mm), 1)),
                        'length': round(float(seg_len), 1), 'thickness': round(float(t_seg), 1),
                        'wall_type': w_type
                    })
                    cv2.fillPoly(covered, [px(seg_poly)], 1)

    # ---- colour preview ----------------------------------------------------------------------
    pal = np.array([[40, 40, 40], [235, 235, 235], [60, 70, 230], [190, 230, 190], [215, 205, 175]], np.uint8)
    rng = np.random.default_rng(7)
    img = pal[kind[lab]]
    rooms = [i for i in range(1, n) if kind[i] == 3]
    for i in rooms:                                                   # each room its own pastel colour
        img[lab == i] = (rng.integers(150, 235, 3)).astype(np.uint8)
    img[ink > 0] = (40, 40, 40)
    edge = cv2.morphologyEx(wall_mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    img[edge] = (255, 140, 0)                                         # detected walls outlined orange
    for c in cands:
        cv2.polylines(img, [px(c['poly'])], True, (255, 0, 255), 2)   # candidates magenta
    scale = min(1.0, 1400 / max(W, H))
    if scale < 1:
        img = cv2.resize(img, (int(W * scale), int(H * scale)), interpolation=cv2.INTER_AREA)
    ok, png = cv2.imencode('.png', cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    n_rooms = len(rooms)
    vals = list(support.values())
    summary = {
        'rooms': n_rooms,
        'wall_bands': int((kind == 2).sum()),
        'confirmed_walls': sum(1 for v in vals if v >= 0.5),
        'weak_walls': sum(1 for v in vals if v < 0.2),
        'candidates': len(cands),
        'mean_support': round(float(np.mean(vals)), 2) if vals else 0,
    }
    logger.info('Segmentation: %s', summary)
    return {'support': support, 'candidates': cands, 'summary': summary,
            'outline': outline_loops,
            'png': base64.b64encode(png.tobytes()).decode() if ok else ''}
