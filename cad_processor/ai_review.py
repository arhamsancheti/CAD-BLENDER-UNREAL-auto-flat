"""AI review of detected walls: CAD geometry + Google Gemini vision.

How it works
1. The plan is split into overlapping zoomed tiles (more pixels per metre = more precise answers).
2. Each tile is rendered with grey CAD linework and the detected walls numbered, and sent to Gemini.
   Gemini flags detections that are not real walls and proposes walls that are missing.
3. Every proposed wall is SNAPPED to the real CAD geometry: we look for the pair of parallel CAD lines
   that the AI pointed at and take the exact centreline, length and thickness from them. Proposals with
   no matching line pair are kept but marked "unverified".
4. Results are only suggestions - the user reviews them on the preview and presses Apply edits.
"""
import base64
import io
import json
import logging
import math
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

import requests

try:  # use the OS certificate store (Python's own bundle fails on this PC: CERTIFICATE_VERIFY_FAILED)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash')
URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

PROMPT = """You are an expert architectural CAD reviewer. The image is part of a floor plan.
Grey lines = original CAD linework (walls, doors, windows, fixtures). Coloured filled shapes = walls
detected by an algorithm: RED = exterior, BLUE = interior, each labelled with its number.
Axes are in metres with a grid line every 1 m; give coordinates in MILLIMETRES (1 m = 1000).

Task:
1. "remove": numbers of coloured shapes that are NOT real walls (free-standing columns, planters,
   stairs, furniture, hatch artefacts, duplicates). Only numbers visible in this image.
2. "add": real walls drawn in grey (two parallel lines 75-450 mm apart forming a wall) that have NO
   coloured shape on them. Give the wall centreline end points in mm and the thickness in mm.
   Do NOT add window or door openings (thin multiple lines, door swings) - only solid wall runs.
3. "notes": one short sentence.
Be conservative: report only clear errors. Reply with JSON only."""

SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'remove': {'type': 'ARRAY', 'items': {'type': 'INTEGER'}},
        'add': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
            'x1': {'type': 'NUMBER'}, 'y1': {'type': 'NUMBER'}, 'x2': {'type': 'NUMBER'},
            'y2': {'type': 'NUMBER'}, 'thickness': {'type': 'NUMBER'}},
            'required': ['x1', 'y1', 'x2', 'y2', 'thickness']}},
        'notes': {'type': 'STRING'},
    },
    'required': ['remove', 'add', 'notes'],
}

Seg = Tuple[float, float, float, float]


def _num(w) -> int:
    return int(w.id.split('_')[1])


def render_plan(walls, underlay: List[Seg], box=None) -> bytes:
    """PNG: grey CAD linework + numbered coloured walls, metre grid. box = (x0, x1, y0, y1) in mm."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    if box is None:
        xs = [p[0] for w in walls for p in w.polygon]
        ys = [p[1] for w in walls for p in w.polygon]
        box = (min(xs) - 1500, max(xs) + 1500, min(ys) - 1500, max(ys) + 1500)
    x0, x1, y0, y1 = box
    fig, ax = plt.subplots(figsize=(13, 13 * (y1 - y0) / (x1 - x0)))
    for (a, b, c, d) in underlay:
        if (x0 <= a <= x1 and y0 <= b <= y1) or (x0 <= c <= x1 and y0 <= d <= y1):
            ax.plot([a, c], [b, d], color='#808080', lw=.6)
    for w in walls:
        px = [p[0] for p in w.polygon]
        py = [p[1] for p in w.polygon]
        ext = w.wall_type == 'exterior'
        ax.fill(px, py, color='#e94560' if ext else '#4aa3ff', alpha=.5, lw=0)
        cx, cy = sum(px) / len(px), sum(py) / len(py)
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            ax.text(cx, cy, str(_num(w)), fontsize=9, ha='center', va='center', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=.1', fc='white', ec='none', alpha=.7))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    tx = list(range(int(math.ceil(x0 / 1000)) * 1000, int(x1) + 1, 1000))
    ty = list(range(int(math.ceil(y0 / 1000)) * 1000, int(y1) + 1, 1000))
    ax.set_xticks(tx)
    ax.set_yticks(ty)
    ax.set_xticklabels([f'{t / 1000:g}m' for t in tx], fontsize=8)
    ax.set_yticklabels([f'{t / 1000:g}m' for t in ty], fontsize=8)
    ax.grid(True, color='#d8d8d8', lw=.5)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    return buf.getvalue()


FALLBACK_MODELS = ['gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-flash-lite-latest',
                   'gemini-3.7-flash', 'gemini-flash-latest', 'gemini-3.5-flash', 'gemini-3.6-flash']
RETRY_CODES = (429, 500, 503, 504)


def _ask_gemini(png: bytes, api_key: str, model: str, prompt: str = None, schema: dict = None) -> Dict[str, Any]:
    """Call Gemini; on busy/overloaded errors retry with backoff, then try the next model.
    Returns the parsed JSON answer with an extra '_model' key (the model that answered)."""
    import time
    body = {
        'contents': [{'parts': [
            {'text': prompt or PROMPT},
            {'inline_data': {'mime_type': 'image/png', 'data': base64.b64encode(png).decode()}},
        ]}],
        'generationConfig': {'responseMimeType': 'application/json', 'responseSchema': schema or SCHEMA,
                             'temperature': 0.1},
    }
    chain = [model] + [m for m in FALLBACK_MODELS if m != model]
    last = ''
    for m in chain:
        for attempt in range(2):
            try:
                r = requests.post(URL.format(model=m), headers={'x-goog-api-key': api_key}, json=body,
                                  timeout=180)
            except requests.RequestException as e:
                raise RuntimeError(f'Cannot reach Google Gemini (check internet / firewall): {type(e).__name__}')
            if r.status_code == 200:
                try:
                    data = json.loads(r.json()['candidates'][0]['content']['parts'][0]['text'])
                except Exception as e:
                    last = f'{m}: unreadable answer ({e})'
                    break
                data['_model'] = m
                return data
            msg = r.text[:300]
            try:
                msg = r.json()['error']['message']
            except Exception:
                pass
            last = f'{m}: {r.status_code} {msg}'
            if r.status_code in (400, 401, 403):
                raise RuntimeError(f'Gemini error {r.status_code}: {msg}')   # bad key etc. - no point retrying
            if r.status_code not in RETRY_CODES or r.status_code == 429:
                break                                   # 404 model gone / 429 quota used up -> next model
            time.sleep(2)
        logger.warning('Gemini model %s failed (%s), trying next', m, last)
    raise RuntimeError(f'All Gemini models busy or unavailable. Last error: {last}')


def _tiles(walls, n: int = 2, overlap: float = 1500.0):
    xs = [p[0] for w in walls for p in w.polygon]
    ys = [p[1] for w in walls for p in w.polygon]
    X0, X1, Y0, Y1 = min(xs) - 800, max(xs) + 800, min(ys) - 800, max(ys) + 800
    sx, sy = (X1 - X0) / n, (Y1 - Y0) / n
    return [(X0 + i * sx - overlap, X0 + (i + 1) * sx + overlap,
             Y0 + j * sy - overlap, Y0 + (j + 1) * sy + overlap) for i in range(n) for j in range(n)]


def snap_to_cad(a: dict, underlay: List[Seg]) -> dict:
    """Move an approximate AI wall onto the exact pair of parallel CAD lines it refers to."""
    ax_, ay_, bx_, by_ = a['x1'], a['y1'], a['x2'], a['y2']
    L = math.hypot(bx_ - ax_, by_ - ay_)
    ux, uy = (bx_ - ax_) / L, (by_ - ay_) / L
    # AI directions are approximate: adopt the direction of the longest nearby CAD line within 15 deg
    mx, my = (ax_ + bx_) / 2, (ay_ + by_) / 2
    best_dir, best_len = None, 0.0
    for (x1, y1, x2, y2) in underlay:
        sl = math.hypot(x2 - x1, y2 - y1)
        if sl < 250 or sl <= best_len:
            continue
        dx, dy = (x2 - x1) / sl, (y2 - y1) / sl
        if abs(dx * ux + dy * uy) < math.cos(math.radians(15)):
            continue
        t = (mx - x1) * dx + (my - y1) * dy
        px, py = x1 + dx * max(0, min(sl, t)), y1 + dy * max(0, min(sl, t))
        if math.hypot(mx - px, my - py) < 600:
            best_dir, best_len = (dx, dy) if dx * ux + dy * uy > 0 else (-dx, -dy), sl
    if best_dir:
        ux, uy = best_dir
        ax_, ay_, bx_, by_ = mx - ux * L / 2, my - uy * L / 2, mx + ux * L / 2, my + uy * L / 2
    nx, ny = -uy, ux
    cands = []   # (offset, t_start, t_end)
    for (x1, y1, x2, y2) in underlay:
        sl = math.hypot(x2 - x1, y2 - y1)
        if sl < 250:
            continue
        if abs((x2 - x1) / sl * ux + (y2 - y1) / sl * uy) < math.cos(math.radians(4)):
            continue
        d1 = (x1 - ax_) * nx + (y1 - ay_) * ny
        d2 = (x2 - ax_) * nx + (y2 - ay_) * ny
        if abs(d1 - d2) > 15 or abs(d1) > 450:
            continue
        t1 = (x1 - ax_) * ux + (y1 - ay_) * uy
        t2 = (x2 - ax_) * ux + (y2 - ay_) * uy
        t1, t2 = min(t1, t2), max(t1, t2)
        if min(t2, L) - max(t1, 0) < 0.4 * min(L, t2 - t1):
            continue
        cands.append(((d1 + d2) / 2, t1, t2))
    best = None
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            di, si, ei = cands[i]
            dj, sj, ej = cands[j]
            th = abs(di - dj)
            if not 70 <= th <= 460:
                continue
            s, e = max(si, sj), min(ei, ej)
            if e - s < 250:
                continue
            c = (di + dj) / 2
            score = abs(c) + 0.3 * abs(th - a['t']) - 0.05 * (e - s)
            if best is None or score < best[0]:
                best = (score, c, th, s, e)
    if not best:
        return dict(a, snapped=False)
    _, c, th, s, e = best
    ox, oy = ax_ + nx * c, ay_ + ny * c
    return {'x1': round(ox + ux * s, 1), 'y1': round(oy + uy * s, 1),
            'x2': round(ox + ux * e, 1), 'y2': round(oy + uy * e, 1), 't': round(th, 1), 'snapped': True}


def _overlaps_existing(a: dict, walls) -> bool:
    """Check if proposed wall 'a' overlaps or duplicates any existing wall or opening."""
    import math
    from shapely.geometry import LineString, Polygon
    from shapely.ops import unary_union

    x1, y1, x2, y2 = a['x1'], a['y1'], a['x2'], a['y2']
    t = float(a.get('t', 200.0))
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 50:
        return True

    wall_polys = [Polygon(w.polygon).buffer(0) for w in walls
                  if getattr(w, 'polygon', None) and len(w.polygon) >= 3]
    if not wall_polys:
        return False
    cover = unary_union(wall_polys)

    # 1. Centerline intersection check
    line = LineString([(x1, y1), (x2, y2)])
    inter_len = line.intersection(cover).length
    if inter_len > 0.15 * line.length or inter_len > 150.0:
        return True

    # 2. Polygon area intersection check
    nx, ny = -(y2 - y1) / L * t / 2.0, (x2 - x1) / L * t / 2.0
    poly = Polygon([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]).buffer(0)
    inter_area = poly.intersection(cover).area
    corner_allowance = 1.25 * t * t
    if inter_area > 0.15 * poly.area and inter_area > 2000.0:
        return True
    if inter_area > corner_allowance:
        return True

    # 3. Parallel proximity check: reject double walls running parallel within 600 mm of existing walls
    buf_poly = poly.buffer(600.0, cap_style=2, join_style=2)
    if buf_poly.intersection(cover).area > 0.35 * buf_poly.area:
        return True

    return False


# ---------------------------------------------------------------------------------------------
# Stage 2: per-wall image classification. Every detected wall gets its own zoomed crop (the wall
# in orange, its surroundings in grey) and Gemini labels each crop. Many crops go in one image
# ("contact sheet") so a 70-wall plan needs only 3 requests.
# ---------------------------------------------------------------------------------------------
LABELS = ['wall', 'column', 'door_swing', 'window', 'furniture', 'stair', 'artifact']
CROP_PROMPT = """Each numbered panel is a zoomed crop of an architectural CAD floor plan (scale bar = 1 m).
The ORANGE filled shape in the centre of a panel is the item to classify. Grey lines = original CAD
drawing; light-blue shapes = other walls (context only).
Classify the ORANGE shape as one of:
- wall: a solid wall/partition/RCC wall: a straight or curved solid band, typically 75-600 mm thick,
  between two parallel CAD lines, usually joined to other walls (short wall stubs beside doors count).
- column: a solid square/rectangular structural column.
- door_swing: door leaf or swing arc, or a curved thin shape inside a doorway.
- window: thin multi-line glazing/frame inside a wall opening.
- furniture: furniture, sanitary fixture, kitchen counter, wardrobe.
- stair: stair steps.
- artifact: hatch sliver, tiny fragment, duplicate or anything else that is not a building element.
Give a confidence 0..1. Return one entry for EVERY panel number. JSON only."""
CROP_SCHEMA = {
    'type': 'OBJECT',
    'properties': {'items': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
        'n': {'type': 'INTEGER'}, 'label': {'type': 'STRING', 'enum': LABELS},
        'confidence': {'type': 'NUMBER'}}, 'required': ['n', 'label', 'confidence']}}},
    'required': ['items'],
}


def render_crop_sheet(targets, walls, underlay: List[Seg], cols: int = 5) -> bytes:
    """One PNG with a zoomed, numbered panel per target wall."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows = max(1, math.ceil(len(targets) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.6, rows * 2.6))
    axes = [axes] if rows * cols == 1 else list(getattr(axes, 'flat', axes))
    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([])
    for ax, t in zip(axes, targets):
        xs = [p[0] for p in t.polygon]; ys = [p[1] for p in t.polygon]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 900
        x0, x1, y0, y1 = cx - half, cx + half, cy - half, cy + half
        for (a, b, c, d) in underlay:
            if min(a, c) <= x1 and max(a, c) >= x0 and min(b, d) <= y1 and max(b, d) >= y0:
                ax.plot([a, c], [b, d], color='#707070', lw=.6)
        for w in walls:
            if w is t:
                continue
            px = [p[0] for p in w.polygon]; py = [p[1] for p in w.polygon]
            if min(px) <= x1 and max(px) >= x0 and min(py) <= y1 and max(py) >= y0:
                ax.fill(px, py, color='#9cc8ff', alpha=.45, lw=0)
        ax.fill(xs, ys, color='#ff8c00', alpha=.85, lw=0)
        ax.plot([x0 + 150, x0 + 1150], [y0 + 150, y0 + 150], color='k', lw=2)       # 1 m scale bar
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
        ax.set_title(str(_num(t)), fontsize=11, fontweight='bold')
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=90)
    plt.close(fig)
    return buf.getvalue()


def _cand_to_wall(poly) -> dict:
    """Centre line + thickness of a segmentation band (via its minimum rotated rectangle)."""
    from shapely.geometry import Polygon
    p = Polygon(poly).buffer(0)
    r = p.minimum_rotated_rectangle
    c = list(r.exterior.coords)[:4]
    e = [math.dist(c[i], c[(i + 1) % 4]) for i in range(4)]
    i = 0 if e[0] >= e[1] else 1                       # long side starts at corner i
    t = min(e[0], e[1])
    a, b, cc, d = c[i], c[(i + 1) % 4], c[(i + 2) % 4], c[(i + 3) % 4]
    s = ((a[0] + d[0]) / 2, (a[1] + d[1]) / 2)
    f = ((b[0] + cc[0]) / 2, (b[1] + cc[1]) / 2)
    return {'x1': round(s[0], 1), 'y1': round(s[1], 1), 'x2': round(f[0], 1), 'y2': round(f[1], 1),
            't': round(t, 1), 'fill': p.area / max(r.area, 1)}


def review(walls, underlay: List[Seg], api_key: str, model: str = '', tiles: int = 2,
           candidates=None, support=None) -> Dict[str, Any]:
    """Two-stage AI check combined with CAD geometry.

    Stage 1 (plan tiles): flags wrong walls and proposes missing ones (proposals snapped to CAD lines).
    Stage 2 (per-wall crops): labels every detected wall (wall / column / door_swing / window / ...).
    Decision per wall (3 independent signals: CAD shape, stage-1 vote, stage-2 label):
      * stage 2 says wall/column with confidence >= 0.5      -> keep (overrides a stage-1 vote)
      * stage 2 says non-wall (conf >= 0.6):
          - odd CAD shape (not a clean rectangle)             -> remove
          - clean CAD wall rectangle                          -> remove only if stage 1 also voted
      * no stage-2 answer: odd shape + stage-1 vote           -> remove
    Image segmentation (optional) adds two more signals:
      * support[wall_id] < 0.3 (no wall band in the raster) + non-wall label -> remove even a clean rectangle
      * candidates (wall-like bands with no detected wall) are shown to the AI as Cand_9xx panels;
        labelled wall/column with confidence >= 0.7 and rectangular -> added as a wall
    Returns remove / kept / add / unverified / labels (per wall id) / model info.
    """
    if not api_key:
        raise RuntimeError('No Gemini API key configured (config.json -> gemini_api_key).')
    model = model or DEFAULT_MODEL
    wall_list = [w for w in walls if w.kind == 'wall']
    boxes = _tiles(wall_list, tiles) if tiles > 1 else [None]
    jobs = [('tile', render_plan(wall_list, underlay, b), PROMPT, SCHEMA) for b in boxes]
    per_sheet = 25
    for i in range(0, len(wall_list), per_sheet):
        jobs.append(('crop', render_crop_sheet(wall_list[i:i + per_sheet], wall_list, underlay),
                     CROP_PROMPT, CROP_SCHEMA))
    from types import SimpleNamespace
    support = support or {}
    cands = [] if len(wall_list) >= 20 else [
        SimpleNamespace(id=f'Cand_{901 + k}', polygon=[tuple(p) for p in c['poly']], kind='cand', src=c)
        for k, c in enumerate((candidates or [])[:50])
    ]
    for i in range(0, len(cands), per_sheet):
        jobs.append(('crop', render_crop_sheet(cands[i:i + per_sheet], wall_list, underlay),
                     CROP_PROMPT, CROP_SCHEMA))

    def safe(job):
        kind, png, prompt, schema = job
        try:
            return kind, _ask_gemini(png, api_key, model, prompt, schema)
        except RuntimeError as e:
            if 'error 4' in str(e):          # bad key / bad request: report it
                raise
            logger.warning('AI %s request failed: %s', kind, e)
            return kind, {'_error': str(e)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(safe, jobs))
    ok = [(k, a) for k, a in answers if '_error' not in a]
    if not ok:
        raise RuntimeError(answers[0][1]['_error'])

    valid = {_num(w): w for w in wall_list + cands}
    xs = [p[0] for w in wall_list for p in w.polygon]
    ys = [p[1] for w in wall_list for p in w.polygon]
    bx0, bx1, by0, by1 = min(xs) - 500, max(xs) + 500, min(ys) - 500, max(ys) + 500
    votes: Dict[str, int] = {}
    labels: Dict[str, dict] = {}
    raw_adds, notes = [], []
    for kind, data in ok:
        if kind == 'crop':
            for it in data.get('items', []):
                w = valid.get(it.get('n'))
                if w is not None and it.get('label') in LABELS:
                    labels[w.id] = {'label': it['label'], 'conf': round(float(it.get('confidence', 0)), 2)}
            continue
        for n in set(data.get('remove', [])):
            if n in valid and not valid[n].id.startswith('Cand_'):
                votes[valid[n].id] = votes.get(valid[n].id, 0) + 1
        notes.append(str(data.get('notes', '')).strip())
        for a in data.get('add', []):
            try:
                x1, y1, x2, y2, t = (float(a[k]) for k in ('x1', 'y1', 'x2', 'y2', 'thickness'))
            except (KeyError, TypeError, ValueError):
                continue
            if not (bx0 <= min(x1, x2) and max(x1, x2) <= bx1 and by0 <= min(y1, y2) and max(y1, y2) <= by1):
                continue
            if math.hypot(x2 - x1, y2 - y1) < 300 or not 60 <= t <= 800:
                continue
            raw_adds.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 't': t})

    placed_walls = list(walls)
    adds: List[dict] = []
    unverified: List[dict] = []
    for a in raw_adds:
        s_ = snap_to_cad(a, underlay)
        if _overlaps_existing(s_, placed_walls):
            continue
        mx, my = (s_['x1'] + s_['x2']) / 2, (s_['y1'] + s_['y2']) / 2
        if any(math.hypot(mx - (b['x1'] + b['x2']) / 2, my - (b['y1'] + b['y2']) / 2) < 300
               for b in adds + unverified):
            continue   # same wall proposed by two overlapping tiles
        (adds if s_['snapped'] else unverified).append(s_)
        if s_['snapped']:
            x1, y1, x2, y2, t = s_['x1'], s_['y1'], s_['x2'], s_['y2'], s_['t']
            L = math.hypot(x2 - x1, y2 - y1)
            if L > 1:
                nx, ny = -(y2 - y1) / L * t / 2.0, (x2 - x1) / L * t / 2.0
                placed_walls.append(SimpleNamespace(
                    polygon=[(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
                ))

    # segmentation candidates confirmed by the per-crop AI -> new walls (exact raster geometry)
    cand_labels, cand_added = {}, []
    for c in cands:
        lab = labels.pop(c.id, None)
        if not lab:
            continue
        cand_labels[c.id] = lab
        if lab['label'] not in ('wall', 'column') or lab['conf'] < 0.7:
            continue
        try:
            g = _cand_to_wall(c.polygon)
        except Exception:
            continue
        L = math.hypot(g['x2'] - g['x1'], g['y2'] - g['y1'])
        if g['fill'] < 0.7 or not 60 <= g['t'] <= 800 or L < 250:
            continue                                  # L/T shaped or odd band: leave it
        g['snapped'] = True
        g['source'] = 'segmentation'
        if _overlaps_existing(g, placed_walls) or any(
                math.hypot((g['x1'] + g['x2']) / 2 - (b['x1'] + b['x2']) / 2,
                           (g['y1'] + g['y2']) / 2 - (b['y1'] + b['y2']) / 2) < 300 for b in adds):
            continue
        g.pop('fill', None)
        adds.append(g)
        cand_added.append(c.id)
        x1, y1, x2, y2, t = g['x1'], g['y1'], g['x2'], g['y2'], g['t']
        L = math.hypot(x2 - x1, y2 - y1)
        if L > 1:
            nx, ny = -(y2 - y1) / L * t / 2.0, (x2 - x1) / L * t / 2.0
            placed_walls.append(SimpleNamespace(
                polygon=[(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
            ))

    remove, kept = [], []
    for w in wall_list:
        lab = labels.get(w.id)
        voted = w.id in votes
        clean = w.shape == 'rectangle' and 100 <= w.thickness <= 700      # proper CAD wall rectangle
        if lab and lab['label'] in ('wall', 'column') and lab['conf'] >= 0.5:
            if voted:
                kept.append(w.id)
            continue
        weak = w.id in support and support[w.id] < 0.3            # image shows no wall band here
        if lab and lab['conf'] >= 0.6:
            if not clean:
                remove.append(w.id)
            else:
                kept.append(w.id)
            continue
        if voted:
            (kept if clean else remove).append(w.id)
    n_tiles = sum(1 for j in jobs if j[0] == 'tile')
    logger.info('AI review (%s): %d requests, labels %d, remove %s, kept %s, add %d, unverified %d', model,
                len(jobs), len(labels), remove, kept, len(adds), len(unverified))
    return {'remove': remove, 'kept': kept, 'add': adds, 'unverified': unverified, 'labels': labels,
            'notes': ' '.join(n for n in notes if n)[:600],
            'model': ', '.join(sorted({a.get('_model', model) for _, a in ok})),
            'calls': len(jobs), 'tiles': n_tiles, 'failed_calls': len(answers) - len(ok),
            'labelled': len(labels), 'wall_total': len(wall_list),
            'cand_total': len(cands), 'cand_labels': cand_labels, 'cand_added': cand_added}
