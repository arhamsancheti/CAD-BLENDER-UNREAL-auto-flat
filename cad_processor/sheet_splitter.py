"""Split a CAD sheet that holds several separate drawings (typical floors, unit plans, site / key plans,
details) into individual drawings, and pick the one to build walls from.

Architectural DWGs are often whole sheets: e.g. three typical-floor plans, one enlarged flat plan and a site
plan side by side in model space. Reading all of them as one plan merges unrelated walls (and is slow), so the
linework is grouped into spatially separate clusters first.
"""
import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

SITE_PLAN_MAX_MM = 80000.0       # drawings larger than this (either side) are site / layout plans, not floor plans
UNIT_PLAN_MAX_MM = 32000.0       # a single dwelling unit fits in this
MIN_DRAWING_ENTS = 60


def split_drawings(entities, gap_mm: float = 2000.0) -> List[Dict]:
    """Cluster entities (already in mm) into separate drawings. Returns a list sorted by entity count:
    {'idx': [entity indices], 'bbox': (x0, y0, x1, y1), 'w': .., 'h': .., 'n': ..}."""
    import cv2
    pts = [np.asarray(e.points, float) for e in entities]
    valid = [i for i, p in enumerate(pts) if p.ndim == 2 and len(p) >= 1]
    if len(valid) < 2 * MIN_DRAWING_ENTS:
        return []
    allp = np.vstack([pts[i] for i in valid])
    x0, y0 = allp.min(0)
    x1, y1 = allp.max(0)
    span = max(x1 - x0, y1 - y0, 1.0)
    cell = max(span / 800.0, 50.0)
    W, H = int((x1 - x0) / cell) + 3, int((y1 - y0) / cell) + 3
    if W * H > 4.0e6:
        return []
    grid = np.zeros((H, W), np.uint8)
    for i in valid:
        q = ((pts[i] - [x0, y0]) / cell).astype(np.int32) + 1
        if len(q) == 1:
            grid[q[0, 1], q[0, 0]] = 1
            continue
        for a, b in zip(q, q[1:]):
            cv2.line(grid, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 1, 1)
    k = max(3, int(math.ceil(gap_mm / cell)) | 1)
    grid = cv2.dilate(grid, np.ones((k, k), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(grid, connectivity=8)
    if n <= 2:
        return []
    groups: Dict[int, List[int]] = {}
    for i in valid:
        c = ((pts[i].mean(0) - [x0, y0]) / cell).astype(np.int32) + 1
        groups.setdefault(int(lab[c[1], c[0]]), []).append(i)
    out = []
    for g, idx in groups.items():
        if g == 0 or len(idx) < MIN_DRAWING_ENTS:
            continue
        gp = np.vstack([pts[i] for i in idx])
        bx0, by0 = gp.min(0)
        bx1, by1 = gp.max(0)
        out.append({'idx': idx, 'bbox': (float(bx0), float(by0), float(bx1), float(by1)),
                    'w': float(bx1 - bx0), 'h': float(by1 - by0), 'n': len(idx)})
    out.sort(key=lambda d: -d['n'])
    return out if len(out) >= 2 else []


def choose_drawing(drawings: List[Dict], pick: Optional[int] = None) -> Tuple[Optional[Dict], str]:
    """Pick the floor plan to read. Site / layout plans are skipped; a single-dwelling plan is preferred over
    whole-floor plans (the walls, rooms, tiles and skirting are built per flat)."""
    if not drawings:
        return None, ''
    if pick is not None and 0 <= int(pick) < len(drawings):
        return drawings[int(pick)], f'drawing #{int(pick) + 1} chosen by the user'
    plans = [d for d in drawings if max(d['w'], d['h']) <= SITE_PLAN_MAX_MM and min(d['w'], d['h']) >= 3000.0]
    if not plans:
        return drawings[0], 'largest drawing on the sheet'
    units = [d for d in plans if max(d['w'], d['h']) <= UNIT_PLAN_MAX_MM]
    if units and len(units) < len(plans):
        best = max(units, key=lambda d: d['n'])
        return best, 'single-dwelling plan preferred over the whole-floor / site plans on the same sheet'
    best = max(plans, key=lambda d: d['n'])
    return best, 'most detailed floor plan on the sheet (site / layout plans skipped)'


def describe(drawings: List[Dict]) -> List[str]:
    return [f"#{k + 1}: {d['w'] / 1000:.1f} x {d['h'] / 1000:.1f} m, {d['n']} entities" for k, d in enumerate(drawings)]
