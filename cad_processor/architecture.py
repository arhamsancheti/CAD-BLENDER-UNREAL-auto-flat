"""
Architectural finishing layer for the CAD -> Blender pipeline (all units: millimetres).

    detect_openings()  doors / passages / windows / ventilators found from the wall geometry
                       itself (wall-end gaps, end-to-face gaps, multi-line window symbols,
                       optional WIN/DOOR layer hints) -> sill / head pieces at exact elevations
    analyse()          room topology (polygonised voids), washroom classification from several
                       independent signals, 76.2 mm skirting runs, individual 3 ft x 2 ft wall
                       tiles with cut tiles, opening cut-outs and corner handling, and a
                       python-side validation report.

Nothing here is hard-coded to one drawing: every door, window and room is derived from the
detected walls and the raw CAD linework.
"""
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import split as shp_split
from shapely.ops import unary_union

from .models import Wall

logger = logging.getLogger(__name__)

# ── CENTRALIZED ARCHITECTURAL CONFIGURATION & SPECIFICATION (mm) ────────────────────
SPEC: Dict[str, float] = {
    'wall_h': 3000.0,                 # 3.0 m standard floor-to-ceiling wall height
    'door_head': 2100.0,              # 2.1 m standard door clear height
    'win_sill': 600.0,                # 0.6 m standard room window sill height
    'win_h': 1500.0,                  # 1.5 m standard window opening height (0.6 m -> 2.1 m)
    'vent_sill': 1200.0,              # 1.2 m washroom / small-room window sill height
    'vent_h': 900.0,                  # 0.9 m washroom / small-room window height (1.2 m -> 2.1 m)
    'vent_max_width': 1000.0,         # window symbols up to this width are ventilator candidates
    'lintel_h': 900.0,                # 0.9 m blue lintel height zone (2.1 m -> 3.0 m)
    'skirt_h': 100.0,                 # 100 mm default skirting height
    'skirt_t': 15.0,                  # 15 mm skirting thickness
    'floor_finish_t': 20.0,           # 20 mm independent room flooring thickness (-20 mm -> 0 mm FFL)
    'slab_t': 200.0,                  # 200 mm structural slab thickness
    'tile_w': 914.4,                  # 3 ft horizontal washroom tile width
    'tile_h': 609.6,                  # 2 ft vertical washroom tile height
    'tile_t': 9.0,                    # 9 mm washroom tile thickness
    'grout': 2.5,                     # 2.5 mm tile grout joint
    'tile_gap': 0.0,                  # tiles bonded directly to the wall face
    'min_cut': 200.0,                 # end cuts narrower than this trigger a balanced layout
    'panel_w': 1220.0,                # 4 ft wall-panel sheets (dry rooms), above skirting
    'panel_t': 12.0,                  # 12 mm panel thickness (skirting is 15 mm -> stands 3 mm proud)
    'panel_joint': 3.0,               # 3 mm V-joint between panel sheets
    'balcony_glass_t': 76.2,          # 3 in (76.2 mm) balcony safety glass envelope
    'balcony_glass_h': 1200.0,        # 1.2 m (~4 ft) balcony glass railing height
    'balcony_glass_joint': 5.0,
    'balcony_glass_max': 1200.0,
    'balcony_post_w': 40.0,           # 40 mm slim metal railing post width
    'balcony_rail_h': 35.0,           # 35 mm slim metal top handrail height
    'kitchen_counter_h': 860.0,       # 0.86 m kitchen countertop top height above FFL (0.85-0.90 m)
    'kitchen_counter_depth': 600.0,   # 0.60 m kitchen countertop depth
    'kitchen_counter_t': 40.0,        # 0.04 m countertop slab thickness (0.03-0.05 m)
    'kitchen_base_depth': 570.0,      # 0.57 m base cabinet support depth (0.55-0.60 m)
    'kitchen_backsplash_h': 600.0,    # 0.60 m backsplash height above countertop
    'kitchen_backsplash_t': 15.0,     # 15 mm backsplash thickness
    'recess_border_w': 450.0,         # 18 in perimeter soffit border around bedroom / hall recessed ceiling
    'recess_depth': 120.0,            # 120 mm upward recessed cavity into the ceiling slab (z = 3000 -> 3120 mm)
    'recess_drop_h': 50.0,            # 50 mm low-profile drop border below ceiling line (z = 2950 -> 3000 mm)
    'recess_lip_w': 60.0,             # 60 mm architectural indirect cove lip projecting into the tray cavity
    'recess_wall_gap': 15.0,          # 15 mm clearance from wall face (clears 12 mm wall panels by 3 mm)
    'downlight_r': 45.0,              # 90 mm diameter low-profile recessed downlight fixture
    'downlight_recess': 25.0,         # 25 mm upward recess of the light diffuser into the ceiling cavity
    'door_frame_w': 45.0,             # 45 mm wooden door frame jamb thickness
    'door_leaf_t': 42.0,              # 42 mm wooden door leaf thickness
    'door_handle_h': 1000.0,          # 1000 mm lever handle height above FFL
    'door_lever_len': 128.0,          # 128 mm silver door lever length on both sides
    'door_min': 600.0, 'door_max': 1250.0, 'gap_max': 3600.0,
}

CONFIG: Dict[str, object] = {
    'spec_mm': SPEC,
    'default_balcony_type': 'open',   # 'open' (glass railing) or 'dry' (no glass railing) when CAD label is absent
    'room_type_overrides': {},        # e.g. {'Room_06': 'kitchen', 'Room_15': 'dry_balcony'}
    'balcony_type_overrides': {},     # e.g. {'Room_15': 'dry'}
    'material_presets': {
        'floor_common': 'MAT_Floor_Common',
        'floor_master_wood': 'MAT_Floor_Master_Wood',
        'floor_entrance': 'MAT_Floor_Entrance',
        'floor_balcony': 'MAT_Floor_Balcony',
        'floor_washroom': 'MAT_Floor_Washroom',
        'skirting_common': 'MAT_Skirting_Common',
        'skirting_master': 'MAT_Skirting_Master',
        'skirting_entrance': 'MAT_Skirting_Entrance',
        'skirting_balcony': 'MAT_Skirting_Balcony',
        'lintel_blue': 'MAT_Lintel_Blue',
        'washroom_tiles': 'MAT_Washroom_Wall_Tiles',
        'balcony_glass': 'MAT_Balcony_Glass',
        'balcony_metal': 'MAT_Balcony_Railing_Metal',
        'kitchen_countertop': 'MAT_Kitchen_Countertop',
        'kitchen_base': 'MAT_Kitchen_Base',
    },
}

WASH_WORDS = re.compile(r'\b(M\.?\s*TOILET|C\.?\s*TOILET|TOILET|TOI|BATH|BATHROOM|WC|W\.C|WASH|WASHROOM|POWDER|LAV|LAVATORY|SHOWER)\b', re.I)
DRY_BALCONY_WORDS = re.compile(r'\b(DRY\.?\s*BALC(?:ONY)?\.?|DRY\s*YARD|UTILITY\s*BALC(?:ONY)?|WASH\s*AREA|SERVICE\s*BALC(?:ONY)?)\b', re.I)
DRY_WORDS = re.compile(
    r'\b(M\.?\s*BED(?:ROOM)?|MASTER\s*BED(?:ROOM)?|BED(?:ROOM)?|MASTER\s*SUITE|SUITE|SERVANT\s*ROOM|KITCHEN|PANTRY|LIVING|DINING|HALL|'
    r'ENT\.?\s*LOBBY|FIRE\s*LOBBY|LIFT\s*LOBBY|LOBBY|FOYER|ENTRANCE|PASSAGE|WIDEPASSAGE|STUDY(?:\s*ROOM)?|LIBRARY|'
    r'DRY\.?\s*BALC(?:ONY)?\.?|BALC(?:ONY)?\.?|SIT[\s\-]*OUT|TERRACE|DECK|PUJA|POOJA|STORE|BOX\s*ROOM|'
    r'W\.?I\.?W\.?|WALK[\s\-]*IN[\s\-]*WARDROBE|WARDROBE|DRESS(?:ING)?|UTILITY|FIRE\s*STAIR(?:CASE)?|STAIR(?:CASE)?|'
    r'FIRE\s*LIFT|LIFT)\b',
    re.I
)
FIXTURE_WORDS = re.compile(r'(WC|TOILET|COMMODE|EWC|IWC|BASIN|SHOWER|BATH|URINAL)', re.I)
KITCHEN_FIXTURE_WORDS = re.compile(r'(SINK|HOB|STOVE|COOK|BURNER|KITCH|FRIDGE|REFRIG)', re.I)
DIM_RE = re.compile(r'(\d+(?:\.\d+)?)\s*M?\s*[xX×]\s*(\d+(?:\.\d+)?)\s*M?', re.I)


def _parse_cad_room_label(raw_labels: List[str], min_dim_mm: float = 0.0, max_dim_mm: float = 0.0):
    """Parse CAD room text labels (including multi-line MTEXT and dimension strings like '4.3X3.35')
    into (canonical_use, display_name, cad_dim, clean_cad_text)."""
    dims_found = []
    cleaned_texts = []
    for raw in raw_labels:
        s = re.sub(r'\\[A-Za-z][^;]*;', ' ', str(raw))
        s = re.sub(r'[\r\n\t]+', ' ', s).strip()
        if not s:
            continue
        for m in DIM_RE.finditer(s):
            d_str = f"{m.group(1)} × {m.group(2)} m"
            if d_str not in dims_found:
                dims_found.append(d_str)
        name_part = re.sub(r"\d+(?:['’′\"”″.\-]|\s)*\d*['’′\"”″M]?\s*[xX×]\s*\d+(?:['’′\"”″.\-]|\s)*\d*['’′\"”″M]?", ' ', s, flags=re.I)
        name_part = DIM_RE.sub(' ', name_part)
        name_part = re.sub(r"\b\d+\s*['’′]\s*\d*\s*[\"”″]?\s*WIDE\b", ' ', name_part, flags=re.I)
        name_part = re.sub(r'\s+', ' ', name_part).strip(' .,-_/:;')
        if name_part and (WASH_WORDS.search(name_part) or DRY_WORDS.search(name_part)):
            if name_part not in cleaned_texts:
                cleaned_texts.append(name_part)

    joined = ' | '.join(cleaned_texts)
    up = joined.upper()
    use = None
    disp = None

    if re.search(r'\bKITCHEN\b', up):
        use, disp = 'kitchen', 'Kitchen'
    elif DRY_BALCONY_WORDS.search(up):
        use, disp = 'dry_balcony', 'Dry Balcony'
    elif re.search(r'\bC\.?\s*TOILET\b', up):
        use, disp = 'washroom', 'Common Toilet'
    elif re.search(r'\bM\.?\s*TOILET\b', up):
        use, disp = 'washroom', 'Master Toilet'
    elif WASH_WORDS.search(up) and not re.search(r'\b(BED|LIVING|DINING|KITCHEN)\b', up):
        use, disp = 'washroom', 'Toilet'
    elif re.search(r'\b(?:MASTER|M\.?)\s*BED', up):
        use, disp = 'master_bedroom', 'Master Bedroom'
    elif re.search(r'\bLIVING\b', up) and re.search(r'\bDIN(?:ING)?\b', up):
        use, disp = 'living_dining', 'Living & Dining'
    elif re.search(r'\bLIVING\b', up):
        use, disp = 'living', 'Living Room'
    elif re.search(r'\bDINING\b', up):
        use, disp = 'dining', 'Dining'
    elif re.search(r'\bBED(?:ROOM)?\b', up):
        use, disp = 'bedroom', 'Bedroom'
    elif re.search(r'\bSIT[\s\-]*OUT\b', up):
        use, disp = 'sit_out', 'Sit-Out / Balcony'
    elif re.search(r'\bBALC(?:ONY)?\b', up):
        use, disp = 'balcony', 'Balcony'
    elif re.search(r'\b(W\.?I\.?W\.?|WALK[\s\-]*IN[\s\-]*WARDROBE|WARDROBE|DRESS)\b', up):
        use, disp = 'walk_in_wardrobe', 'Walk-In Wardrobe'
    elif re.search(r'\bENT\.?\s*LOBBY\b', up):
        use, disp = 'entrance_lobby', 'Entrance Lobby'
    elif re.search(r'\bFIRE\s*LOBBY\b', up):
        use, disp = 'fire_lobby', 'Fire Lobby'
    elif re.search(r'\b(LOBBY|FOYER|ENTRANCE|PASSAGE|WIDEPASSAGE)\b', up):
        use, disp = 'lobby', 'Entrance / Lobby'
    elif re.search(r'\bFIRE\s*STAIR', up):
        use, disp = 'fire_staircase', 'Fire Staircase'
    elif re.search(r'\bSTAIR', up):
        use, disp = 'staircase', 'Staircase'
    elif re.search(r'\bFIRE\s*LIFT\b', up):
        use, disp = 'fire_lift', 'Fire Lift'
    elif re.search(r'\bLIFT\b', up):
        use, disp = 'lift', 'Lift'
    elif cleaned_texts:
        raw_u = re.sub(r'[^A-Za-z]+', '_', cleaned_texts[0]).strip('_').lower()
        # Strip any leftover single-letter 'x' token from dimension separators
        tokens = [tok for tok in raw_u.split('_') if tok and tok != 'x']
        if tokens:
            use = '_'.join(tokens)
            disp = ' '.join(tok.capitalize() for tok in tokens)

    cad_dim = ' / '.join(dims_found[:2]) if dims_found else (
        f"{max_dim_mm / 1000.0:.2f} × {min_dim_mm / 1000.0:.2f} m" if min_dim_mm > 0 and max_dim_mm > 0 else ''
    )
    return use, disp, cad_dim, joined


USE_DISPLAY_NAMES = {
    'master_bedroom': 'Master Bedroom',
    'master_suite': 'Master Suite / Dress',
    'bedroom': 'Bedroom',
    'living_dining': 'Living & Dining',
    'hall_dining': 'Living & Dining Hall',
    'living': 'Living Room',
    'dining': 'Dining',
    'kitchen': 'Kitchen',
    'washroom': 'Toilet / Washroom',
    'balcony': 'Balcony',
    'sit_out': 'Sit-Out / Balcony',
    'dry_balcony': 'Dry Balcony',
    'entrance_lobby': 'Entrance Lobby',
    'fire_lobby': 'Fire Lobby',
    'lobby': 'Lobby',
    'foyer': 'Entrance Foyer',
    'walk_in_wardrobe': 'Walk-In Wardrobe',
    'fire_staircase': 'Fire Staircase',
    'staircase': 'Staircase',
    'fire_lift': 'Fire Lift',
    'lift': 'Lift',
    'utility': 'Utility Room',
    'shaft': 'Service Shaft / Duct',
    'external': 'Exterior',
}


@dataclass
class Opening:
    id: str
    type: str                       # door | passage | window | vent
    p0: Tuple[float, float]
    p1: Tuple[float, float]
    thickness: float
    sill: float                     # bottom of the clear opening (mm above FFL)
    head: float                     # top of the clear opening
    source: str                     # how it was detected
    notes: List[str] = field(default_factory=list)

    @property
    def width(self) -> float:
        return math.dist(self.p0, self.p1)

    def rect(self) -> Polygon:
        d = np.subtract(self.p1, self.p0) / max(self.width, 1e-9)
        n = np.array([-d[1], d[0]]) * self.thickness / 2.0
        a, b = np.array(self.p0), np.array(self.p1)
        return Polygon([a + n, b + n, b - n, a - n])

    def to_dict(self) -> dict:
        return {'id': self.id, 'type': self.type, 'p0': [round(v, 1) for v in self.p0],
                'p1': [round(v, 1) for v in self.p1], 'width': round(self.width, 1),
                'thickness': round(self.thickness, 1), 'sill': self.sill, 'head': self.head,
                'height': round(self.head - self.sill, 1), 'source': self.source, 'notes': self.notes,
                'rect': [[round(x, 1), round(y, 1)] for x, y in list(self.rect().exterior.coords)[:-1]]}


# ════════════════════════════════════════════════════════════════════════════════════
#  OPENINGS
# ════════════════════════════════════════════════════════════════════════════════════
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def _rect(p0, p1, t) -> Polygon:
    d = _unit(np.subtract(p1, p0))
    n = np.array([-d[1], d[0]]) * t / 2.0
    a, b = np.asarray(p0, float), np.asarray(p1, float)
    return Polygon([a + n, b + n, b - n, a - n])


def _classify_width(w: float, spec=SPEC) -> str:
    return 'door' if w <= spec['door_max'] else 'passage'


def _elevations(otype: str, spec=SPEC) -> Tuple[float, float]:
    if otype == 'window':
        return spec['win_sill'], spec['win_sill'] + spec['win_h']
    if otype == 'vent':
        return spec['vent_sill'], spec['vent_sill'] + spec['vent_h']
    return 0.0, spec['door_head']


def _find_posts(p0, p1, t, underlay) -> List[Tuple[float, float]]:
    """Small masonry posts / mullions drawn inside a gap: pairs of short CAD lines that cross
    the wall line (length ~ wall thickness) a short distance apart. Returns [(s0, s1)] along gap."""
    d = _unit(np.subtract(p1, p0))
    n = np.array([-d[1], d[0]])
    g = math.dist(p0, p1)
    pos = []
    for x1, y1, x2, y2 in underlay:
        sv = np.array([x2 - x1, y2 - y1], float)
        L = np.linalg.norm(sv)
        if L < 1e-6 or abs(np.dot(sv / L, d)) > 0.1 or not (0.6 * t <= L <= 1.4 * t):
            continue
        m = np.array([(x1 + x2) / 2, (y1 + y2) / 2]) - np.asarray(p0, float)
        s, lat = float(np.dot(m, d)), float(np.dot(m, n))
        if 40.0 <= s <= g - 40.0 and abs(lat) <= t / 2.0:
            pos.append(s)
    pos = sorted(pos)
    uniq = []
    for s in pos:
        if not uniq or s - uniq[-1] > 5.0:
            uniq.append(s)
    posts, i = [], 0
    while i + 1 < len(uniq):
        if 40.0 <= uniq[i + 1] - uniq[i] <= 450.0:
            posts.append((uniq[i], uniq[i + 1]))
            i += 2
        else:
            i += 1
    return posts


def _closed_posts(underlay, lo: float = 80.0, hi: float = 450.0, tol: float = 2.0) -> List[Polygon]:
    """Small closed rectangles drawn in the CAD (masonry posts / columns between openings):
    four short lines, both sides lo..hi mm, whose endpoints meet. Returns square polygons."""
    segs = []
    for x1, y1, x2, y2 in underlay:
        L = math.hypot(x2 - x1, y2 - y1)
        if lo - tol <= L <= hi + tol:
            segs.append((np.array([x1, y1], float), np.array([x2, y2], float), L))

    def has_seg(p, q):
        for a, b, _ in segs:
            if (np.linalg.norm(a - p) <= tol and np.linalg.norm(b - q) <= tol) or \
               (np.linalg.norm(a - q) <= tol and np.linalg.norm(b - p) <= tol):
                return True
        return False

    out: List[Polygon] = []
    for i in range(len(segs)):
        a1, b1, L1 = segs[i]
        d1 = (b1 - a1) / L1
        for j in range(i + 1, len(segs)):
            a2, b2, L2 = segs[j]
            if abs(L1 - L2) > tol or abs(abs(np.dot(d1, (b2 - a2) / L2)) - 1.0) > 1e-3:
                continue
            if np.dot(d1, b2 - a2) < 0:            # orient the second side like the first
                a2, b2 = b2, a2
            side = a2 - a1
            w = np.linalg.norm(side)
            if not (lo - tol <= w <= hi + tol) or abs(np.dot(side / w, d1)) > 1e-3:
                continue
            if not (has_seg(a1, a2) and has_seg(b1, b2)):
                continue
            sq = Polygon([tuple(a1), tuple(b1), tuple(b2), tuple(a2)]).buffer(0)
            if sq.area > 0 and not any(sq.equals_exact(o, tol) or sq.symmetric_difference(o).area < 50.0 for o in out):
                out.append(sq)
    return out


def detect_openings(walls: List[Wall], ctx: dict, spec: dict = SPEC):
    """Returns (openings, fill_pieces, post_walls, report_notes).
    Wall ids that were replaced by a CAD post are listed in ctx['dropped_wall_ids']."""
    H = spec['wall_h']
    underlay = ctx.get('underlay', [])
    hints_win, hints_door = ctx.get('win_hint'), ctx.get('door_hint')
    notes: List[str] = []

    # ── 0. closed CAD posts / columns + window/parapet L-corner posts become solid full-height pieces
    posts: List[Wall] = []
    dropped: List[str] = []
    wall_polys = {w.id: Polygon(w.polygon).buffer(0) for w in walls if w.kind == 'wall' and len(w.polygon) >= 3}
    win_poly_union = unary_union([wp.buffer(25.0) for wp in ctx.get('window_polys', []) if not wp.is_empty]) if ctx.get('window_polys') else Polygon()
    raw_closed_posts = []
    for sq in _closed_posts(underlay):
        # Never turn a window/ventilator symbol or door opening box into a full-height solid wall post
        if not win_poly_union.is_empty and sq.intersects(win_poly_union):
            continue
        if hints_win is not None and not hints_win.is_empty and sq.distance(hints_win) <= 120.0:
            continue
        if hints_door is not None and not hints_door.is_empty and sq.distance(hints_door) <= 120.0:
            continue
        raw_closed_posts.append(sq)
    cand_posts = raw_closed_posts + list(ctx.get('corner_posts', []))
    for sq in cand_posts:
        if any(p.intersection(sq).area > 0.9 * sq.area for p in wall_polys.values()):
            continue                                   # already part of a correctly detected wall
        if any(Polygon(pw.polygon).intersection(sq).area > 0.5 * sq.area for pw in posts):
            continue
        for wid, p in wall_polys.items():
            if p.area > 0 and p.intersection(sq).area > 0.5 * p.area and wid not in dropped:
                dropped.append(wid)                    # a sliver mis-detected inside the post outline
        c = list(sq.minimum_rotated_rectangle.exterior.coords)[:4]
        e1, e2 = math.dist(c[0], c[1]), math.dist(c[1], c[2])
        if e1 >= e2:
            a = ((c[0][0] + c[3][0]) / 2, (c[0][1] + c[3][1]) / 2); b = ((c[1][0] + c[2][0]) / 2, (c[1][1] + c[2][1]) / 2)
        else:
            a = ((c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2); b = ((c[2][0] + c[3][0]) / 2, (c[2][1] + c[3][1]) / 2)
        posts.append(Wall(id=f"Post_{len(posts) + 1:02d}", start_point=a, end_point=b, length=max(e1, e2),
                          thickness=min(e1, e2), height=H,
                          polygon=[(round(x, 1), round(y, 1)) for x, y in list(sq.exterior.coords)[:-1]],
                          wall_type='interior', layer='POST', base=0.0, kind='wall'))
        notes.append(f"CAD post {min(e1, e2):.0f} x {max(e1, e2):.0f} mm at ({sq.centroid.x:.0f},{sq.centroid.y:.0f}) "
                     f"modelled as a full-height solid" + (f" (replaced sliver {', '.join(dropped[-1:])})" if dropped else ''))
    ctx['dropped_wall_ids'] = dropped
    real = [w for w in walls if w.kind == 'wall' and w.id not in dropped] + posts
    polys = [Polygon(w.polygon).buffer(0) for w in real]

    # ── 1. window symbols -> window / ventilator openings snapped to the adjoining walls
    parapet_polys = ctx.get('parapet_polys', [])
    windows: List[Opening] = []
    for wp in ctx.get('window_polys', []):
        mrr = wp.minimum_rotated_rectangle
        if mrr.geom_type != 'Polygon':
            continue
        c = list(mrr.exterior.coords)[:4]
        d1, d2 = math.dist(c[0], c[1]), math.dist(c[1], c[2])
        if d1 >= d2:
            a = ((c[0][0] + c[3][0]) / 2, (c[0][1] + c[3][1]) / 2)
            b = ((c[1][0] + c[2][0]) / 2, (c[1][1] + c[2][1]) / 2)
        else:
            a = ((c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2)
            b = ((c[2][0] + c[3][0]) / 2, (c[2][1] + c[3][1]) / 2)
        T = min(d1, d2)
        mid = np.add(a, b) / 2.0
        d = _unit(np.subtract(b, a))
        half = math.dist(a, b) / 2.0
        ends, thick, lat_shifts, jambs = [], [], [], []
        free_jambs = []
        n_vec = np.array([-d[1], d[0]])
        for sgn in (-1, 1):                     # ray from the centre to the wall that closes each end
            ray = LineString([mid, mid + sgn * d * (half + 155.0)])
            best = None
            for k, p in enumerate(polys):
                if ray.intersects(p):
                    hit = ray.intersection(p)
                    dist = min(Point(mid).distance(Point(q)) for q in _coords(hit))
                    if best is None or dist < best[0]:
                        best = (dist, k)
            if best and best[0] >= half - 90.0:
                if best[0] <= half + 15.0:
                    ends.append(mid + sgn * d * best[0])          # closes the small cut gap
                else:
                    # the symbol already ends at the jamb; the strip up to the wall is solid
                    ends.append(mid + sgn * d * half)
                    jambs.append((mid + sgn * d * half, mid + sgn * d * best[0], best[1]))
                w = real[best[1]]
                wd = _unit(np.subtract(w.end_point, w.start_point))
                if abs(np.dot(wd, d)) > 0.95:          # collinear neighbour -> borrow its thickness & lateral centerline
                    thick.append((w.length, w.thickness))
                    w_mid = 0.5 * (np.asarray(w.start_point, float) + np.asarray(w.end_point, float))
                    lat_off = float(np.dot(w_mid - mid, n_vec))
                    if abs(lat_off) <= 15.0:
                        lat_shifts.append((w.length, lat_off))
            else:
                ends.append(mid + sgn * d * half)
                if best is None:
                    free_jambs.append(mid + sgn * d * half)
        if lat_shifts:
            best_lat = max(lat_shifts, key=lambda x: x[0])[1]
            ends = [e + n_vec * best_lat for e in ends]
        t_cand = max(thick, key=lambda x: x[0])[1] if thick else T
        t = float(t_cand) if thick and abs(t_cand - T) < 60 else max(T, 100.0)
        for ja, jb, k in jambs:
            # grow the wall that closes this end so the corner block is solid full height
            grown = polys[k].union(_rect(ja, jb, t)).buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
            if grown.geom_type != 'Polygon':
                continue
            grown = grown.simplify(0.5, preserve_topology=True)
            real[k].polygon = [(round(x, 1), round(y, 1)) for x, y in list(grown.exterior.coords)[:-1]]
            polys[k] = Polygon(real[k].polygon).buffer(0)
            notes.append(f"Window symbol ends {math.dist(ja, jb):.0f} mm short of the wall at "
                         f"({ja[0]:.0f},{ja[1]:.0f}) - corner made solid (opening kept at the CAD extent)")
        width = math.dist(ends[0], ends[1])
        is_parapet = any(wp.intersection(pp).area > 0.4 * wp.area for pp in parapet_polys)
        otype = 'window' if is_parapet else ('vent' if width <= spec['vent_max_width'] else 'window')
        sill, head = _elevations(otype, spec)
        if is_parapet:
            sill = spec['win_sill']
            head = sill + spec.get('balcony_glass_h', 1066.8)
        op_obj = Opening('', otype, tuple(ends[0]), tuple(ends[1]), t, sill, head,
                         'balcony parapet' if is_parapet else 'multi-line window symbol')
        op_obj.is_parapet = is_parapet
        op_obj._free_jambs = free_jambs
        windows.append(op_obj)
    # A window must sit inside a wall: drop glass symbols with an unsupported jamb (no wall / post / adjoining
    # window within 155 mm), e.g. a glass shower partition standing free inside a washroom.
    kept_windows = []
    for k, o in enumerate(windows):
        fj = getattr(o, '_free_jambs', [])
        if fj and (not o.is_parapet or len(fj) >= 2):
            others = [w.rect().buffer(40.0) for m, w in enumerate(windows) if m != k]
            if not all(any(r.contains(Point(p)) for r in others) for p in fj):
                notes.append(f"Glass symbol {math.dist(o.p0, o.p1):.0f} mm at "
                             f"({(o.p0[0] + o.p1[0]) / 2:.0f},{(o.p0[1] + o.p1[1]) / 2:.0f}) has a jamb that meets no wall "
                             f"- free-standing glass partition (modelled as a glass panel, not a wall opening)")
                if not o.is_parapet and math.dist(o.p0, o.p1) >= 400.0:
                    ctx.setdefault('glass_partitions', []).append({
                        'p0': [round(float(o.p0[0]), 1), round(float(o.p0[1]), 1)],
                        'p1': [round(float(o.p1[0]), 1), round(float(o.p1[1]), 1)],
                        'width': round(math.dist(o.p0, o.p1), 1), 'height': spec['door_head']})
                continue
        kept_windows.append(o)
    windows = kept_windows
    win_rects = [o.rect() for o in windows]

    def blocked_by_window(r: Polygon) -> bool:
        return any(r.intersection(wr).area > 0.3 * min(r.area, wr.area) for wr in win_rects)

    # ── 2. free wall ends
    ends = []          # (wall idx, point, outward dir, thickness)
    for i, w in enumerate(real):
        if w.length < 150:
            continue
        a, b = np.array(w.start_point, float), np.array(w.end_point, float)
        d = _unit(b - a)
        ends.append((i, a, -d, w.thickness))
        ends.append((i, b, d, w.thickness))

    def end_is_free(e) -> bool:
        i, p, d, t = e
        probe = Point(p + d * 3.0).buffer(4.0)
        return not any(k != i and probe.intersects(polys[k]) for k in range(len(polys)))

    free = [e for e in ends if end_is_free(e)]
    gaps = []          # (p0, p1, t, wall_i, wall_j|None, source)
    used = set()

    # ── 3. collinear end-to-end gaps
    cand = []
    for p in range(len(free)):
        for q in range(p + 1, len(free)):
            i, pa, da, ta = free[p]
            j, pb, db, tb = free[q]
            if i == j or np.dot(da, db) > -0.98:
                continue
            g = pb - pa
            along = float(np.dot(g, da))
            lateral = abs(float(g[0] * -da[1] + g[1] * da[0]))
            if not (300.0 <= along <= spec['gap_max']) or lateral > 0.5 * max(ta, tb) + 25:
                continue
            if not (0.7 <= ta / tb <= 1.43):
                continue
            line = LineString([pa, pb])
            if any(line.intersection(polys[k]).length > 10.0 for k in range(len(polys)) if k not in (i, j)):
                continue
            cand.append((along, p, q))
    def face_blocked(pa, pb, t_gap, excl_a, excl_b=None) -> bool:
        """True if either side (+n or -n) immediately outside the gap face is inside a parallel solid wall or window."""
        pa_a, pb_a = np.asarray(pa, float), np.asarray(pb, float)
        dg = _unit(pb_a - pa_a)
        ng = np.array([-dg[1], dg[0]])
        for frac in (0.1, 0.5, 0.9):
            pt_base = pa_a + frac * (pb_a - pa_a)
            for sgn in (-1.0, 1.0):
                pt = Point(pt_base + sgn * ng * (0.5 * t_gap + 45.0))
                if any(polys[m].contains(pt) for m in range(len(polys)) if m != excl_a and m != excl_b) or any(wr.contains(pt) for wr in win_rects):
                    return True
        return False

    def end_is_l_corner(wall_idx, p_pt, d_vec, t_val) -> bool:
        """True when a perpendicular wall or window already abuts the side of wall_idx right at its end p_pt (forming an L/T-corner)."""
        ng = np.array([-d_vec[1], d_vec[0]])
        p_in = np.asarray(p_pt, float) - d_vec * min(40.0, 0.25 * real[wall_idx].length)
        for sgn in (-1.0, 1.0):
            pt = Point(p_in + sgn * ng * (0.5 * t_val + 35.0))
            if any(polys[m].contains(pt) for m in range(len(polys)) if m != wall_idx) or any(wr.contains(pt) for wr in win_rects):
                return True
        return False

    for along, p, q in sorted(cand):
        if p in used or q in used:
            continue
        i, pa, da, ta = free[p]
        j, pb, db, tb = free[q]
        if abs(da[0]) >= 0.999:
            d_axis = np.array([1.0 if da[0] > 0 else -1.0, 0.0])
        elif abs(da[1]) >= 0.999:
            d_axis = np.array([0.0, 1.0 if da[1] > 0 else -1.0])
        else:
            d_axis = da
        along_ax = float(np.dot(pb - pa, d_axis))
        if abs(ta - tb) <= 4.0:
            use_a = real[i].length >= real[j].length
        else:
            use_a = ta <= tb
        t_use = ta if use_a else tb
        if use_a:
            p0_gap = np.asarray(pa, float)
            p1_gap = p0_gap + d_axis * along_ax
        else:
            p1_gap = np.asarray(pb, float)
            p0_gap = p1_gap - d_axis * along_ax
        r = _rect(p0_gap, p1_gap, t_use)
        if (blocked_by_window(r) or face_blocked(p0_gap, p1_gap, t_use, i, j)
                or any(r.buffer(-5.0).intersects(polys[m]) for m in range(len(polys)) if m not in (i, j))):
            used.update((p, q))          # the gap is a window or already closed by a solid wall
            continue
        used.update((p, q))
        gaps.append((tuple(p0_gap), tuple(p1_gap), t_use, i, j, 'collinear wall-end gap'))

    # ── 4. posts inside gaps (split wide gaps at small masonry posts drawn in the CAD)
    n_closed = len(posts)
    split_gaps = []

    def split_by_posts(gp):
        p0, p1, t, i, j, src = gp
        pts = _find_posts(p0, p1, t, underlay)
        if not pts:
            return [gp]
        d = _unit(np.subtract(p1, p0))
        out, s_prev = [], 0.0
        for s0, s1 in pts:
            a, b = np.asarray(p0) + d * s_prev, np.asarray(p0) + d * s0
            if s0 - s_prev >= 300.0:
                out.append((tuple(a), tuple(b), t, i, j, src + ' (split at CAD post)'))
            pa, pb = np.asarray(p0) + d * s0, np.asarray(p0) + d * s1
            posts.append(Wall(id=f"Post_{len(posts) + 1:02d}", start_point=tuple(pa), end_point=tuple(pb),
                              length=s1 - s0, thickness=t, height=H,
                              polygon=[tuple(c) for c in list(_rect(pa, pb, t).exterior.coords)[:-1]],
                              wall_type=real[i].wall_type, layer='POST', base=0.0, kind='wall'))
            s_prev = s1
        g = math.dist(p0, p1)
        if g - s_prev >= 300.0:
            out.append((tuple(np.asarray(p0) + d * s_prev), tuple(p1), t, i, j, src + ' (split at CAD post)'))
        return out

    for gp in gaps:
        split_gaps.extend(split_by_posts(gp))
    gaps = split_gaps

    # ── 5. end-to-face gaps: a free wall end facing the END zone of another wall / post
    obstacles = [(k, polys[k], real[k]) for k in range(len(real))] + \
                [(1000 + n, Polygon(pw.polygon), pw) for n, pw in enumerate(posts[n_closed:])]
    used_pts = [np.asarray(g[0]) for g in gaps] + [np.asarray(g[1]) for g in gaps]
    for e in free:
        i, p, d, t = e
        if any(np.linalg.norm(p - u) < 5.0 for u in used_pts):
            continue
        ray = LineString([p + d * 1.0, p + d * spec['gap_max']])
        hit = None
        for k, poly, w in obstacles:
            if k == i or not ray.intersects(poly):
                continue
            dist = min(Point(p).distance(Point(q)) for q in _coords(ray.intersection(poly)))
            if hit is None or dist < hit[0]:
                hit = (dist, k, w)
        if hit is None:
            continue
        g, k, w = hit
        if not (spec['door_min'] - 100.0 <= g <= spec['gap_max']):
            continue
        hp = p + d * g
        # corner-aligned rule: the gap must close onto the end zone of the target (or onto a post,
        # or align with a collinear wall continuing on the opposite face of the target through-wall)
        ok = w.layer == 'POST'
        if not ok:
            a, b = np.array(w.start_point, float), np.array(w.end_point, float)
            wd = _unit(b - a)
            s = float(np.dot(hp - a, wd))
            end_tol = w.thickness / 2.0 + t / 2.0 + (250.0 if g <= spec['door_max'] else 15.0)
            ok = min(abs(s), abs(w.length - s)) <= end_tol
            if not ok and g <= spec['door_max'] and (hints_door is None or not end_is_l_corner(i, p, d, t)):
                opp = Point(hp + d * (w.thickness + 10.0))
                ok = any(m not in (i, k) and polys[m].distance(opp) <= 50.0 for m in range(len(polys)))
        r = _rect(p, hp, t)
        if not ok and g <= spec['door_max'] and hints_door is not None:
            ok = r.buffer(120.0).intersects(hints_door)
        if not ok:
            notes.append(f"Rejected end-to-face gap {g:.0f} mm at ({p[0]:.0f},{p[1]:.0f}): it meets the middle "
                         f"of a wall (corridor continuation, not a doorway)")
            continue
        if (blocked_by_window(r) or face_blocked(p, hp, t, i, k)
                or any(r.buffer(-5).intersects(polys[m]) for m in range(len(polys)) if m != i)
                or any(r.intersection(_rect(g[0], g[1], g[2])).area > 0.2 * min(r.area, _rect(g[0], g[1], g[2]).area) for g in gaps)):
            continue
        gaps.append((tuple(p), tuple(hp), t, i, None, 'wall end facing wall end-zone'))
        used_pts += [p, hp]

    # ── 5b. 90° CAD door-arc doorways between opposing wall faces (e.g. T-junction / square-nib doors)
    for c_pt, p_a, p_b, rad in (ctx.get('door_arcs') or []):
        if not (spec['door_min'] - 100.0 <= rad <= spec['door_max']):
            continue
        c_arr = np.asarray(c_pt, float)
        near_c = [(k_o, poly_o, w_o) for k_o, poly_o, w_o in obstacles if poly_o.distance(Point(c_arr)) <= 125.0]
        if not near_c:
            continue
        matched_arc = False
        for p_closed, p_open in ((p_a, p_b), (p_b, p_a)):
            if matched_arc:
                break
            pc_arr = np.asarray(p_closed, float)
            po_arr = np.asarray(p_open, float)
            arm_len = math.dist(c_arr, pc_arr)
            if arm_len < 300.0:
                continue
            u_dr = _unit(pc_arr - c_arr)
            if abs(u_dr[1]) <= 0.085:
                u_dr = np.array([1.0 if u_dr[0] >= 0 else -1.0, 0.0])
            elif abs(u_dr[0]) <= 0.085:
                u_dr = np.array([0.0, 1.0 if u_dr[1] >= 0 else -1.0])
            n_dr = np.array([-u_dr[1], u_dr[0]])
            # Skip if an existing parallel doorway already overlaps this arc arm longitudinally and sits within 220 mm laterally
            already_covered = False
            for g in gaps:
                ga, gb = np.asarray(g[0], float), np.asarray(g[1], float)
                if abs(np.dot(u_dr, _unit(gb - ga))) <= 0.8:
                    continue
                gs0, gs1 = float(np.dot(ga - c_arr, u_dr)), float(np.dot(gb - c_arr, u_dr))
                glo, ghi = min(gs0, gs1), max(gs0, gs1)
                glat = abs(0.5 * float(np.dot((ga + gb) - 2.0 * c_arr, n_dr)))
                if min(arm_len, ghi) - max(0.0, glo) >= 0.35 * arm_len and glat <= 220.0:
                    already_covered = True
                    break
            if already_covered:
                matched_arc = True
                break
            near_p = [(k_o, poly_o, w_o) for k_o, poly_o, w_o in obstacles if poly_o.distance(Point(pc_arr)) <= 125.0]
            if not near_p:
                continue
            for k_a, poly_a, w_a in near_c:
                if matched_arc:
                    break
                clip_a = poly_a.intersection(Point(c_arr).buffer(260.0))
                pts_a = _coords(clip_a)
                if not pts_a:
                    continue
                sa_vals = [float(np.dot(np.asarray(pt, float) - c_arr, u_dr)) for pt in pts_a]
                la_vals = [float(np.dot(np.asarray(pt, float) - c_arr, n_dr)) for pt in pts_a]
                s0 = max(sa_vals)
                la0, la1 = min(la_vals), max(la_vals)
                if abs(s0) > 150.0:
                    continue
                for k_b, poly_b, w_b in near_p:
                    if k_b == k_a:
                        continue
                    clip_b = poly_b.intersection(Point(pc_arr).buffer(240.0))
                    pts_b = _coords(clip_b)
                    if not pts_b:
                        continue
                    sb_vals = [float(np.dot(np.asarray(pt, float) - c_arr, u_dr)) for pt in pts_b]
                    lb_vals = [float(np.dot(np.asarray(pt, float) - c_arr, n_dr)) for pt in pts_b]
                    s1 = min(sb_vals)
                    lb0, lb1 = min(lb_vals), max(lb_vals)
                    g_w = s1 - s0
                    if not (spec['door_min'] - 100.0 <= g_w <= spec['door_max']) or abs(g_w - rad) > 220.0:
                        continue
                    ov_lo, ov_hi = max(la0, lb0), min(la1, lb1)
                    if ov_hi - ov_lo < 40.0:
                        continue
                    t_dr = min(w_a.thickness, w_b.thickness)
                    lat_mid = 0.5 * (ov_lo + ov_hi)
                    q0 = c_arr + u_dr * s0 + n_dr * lat_mid
                    q1 = c_arr + u_dr * s1 + n_dr * lat_mid
                    r = _rect(q0, q1, t_dr)
                    r_trim = _rect(q0 + u_dr * 12.0, q1 - u_dr * 12.0, max(20.0, t_dr - 20.0))
                    # Check neither side (+n/-n) along middle of doorway is inside ANY wall (rejects open-leaf arms)
                    mid_blocked = False
                    for frac in (0.25, 0.5, 0.75):
                        pt_m = q0 + frac * (q1 - q0)
                        for sgn in (-1.0, 1.0):
                            pt_side = Point(pt_m + sgn * n_dr * (0.5 * t_dr + 45.0))
                            if any(poly_o.contains(pt_side) for _, poly_o, _ in obstacles) or any(wr.contains(pt_side) for wr in win_rects):
                                mid_blocked = True
                                break
                        if mid_blocked:
                            break
                    if (mid_blocked or blocked_by_window(r)
                            or any(r_trim.intersects(poly_o) for _, poly_o, _ in obstacles)
                            or any(r.intersection(_rect(g[0], g[1], g[2])).area > 0.15 * min(r.area, _rect(g[0], g[1], g[2]).area) for g in gaps)):
                        continue
                    gaps.append((tuple(q0), tuple(q1), t_dr, k_a if k_a < len(real) else 0,
                                 k_b if k_b < len(real) else None, 'CAD door arc between walls'))
                    matched_arc = True
                    break

    # ── 6. type + elevations
    openings: List[Opening] = list(windows)
    all_solid = unary_union(polys + win_rects + [_rect(g[0], g[1], g[2]) for g in gaps])

    def faces_outside(p0, p1, t_gap=150.0) -> bool:
        """True when one side of the gap looks straight out of the building (no wall within 25 m)."""
        m = (np.asarray(p0, float) + np.asarray(p1, float)) / 2.0
        d = _unit(np.subtract(p1, p0))
        n = np.array([-d[1], d[0]])
        d0 = max(120.0, 0.5 * t_gap + 30.0)
        return any(not LineString([m + s * n * d0, m + s * n * 25000.0]).intersects(all_solid) for s in (-1, 1))

    def has_window_symbol_in_gap(p0, p1, t) -> bool:
        """True when the CAD underlay draws >=3 parallel window lines (or >=2 inner glass lines) across the gap."""
        a = np.asarray(p0, float)
        W = math.dist(p0, p1)
        if W < 250.0:
            return False
        d = _unit(np.subtract(p1, p0))
        n = np.array([-d[1], d[0]])
        lats = []
        for x1, y1, x2, y2 in underlay:
            sv = np.array([x2 - x1, y2 - y1], float)
            L = float(np.linalg.norm(sv))
            if L < 0.55 * W or abs(np.dot(sv / L, d)) < 0.995:
                continue
            p_a = np.array([x1, y1], float) - a
            p_b = np.array([x2, y2], float) - a
            lat_a, lat_b = float(np.dot(p_a, n)), float(np.dot(p_b, n))
            if abs(lat_a - lat_b) > 3.0:
                continue
            lat = 0.5 * (lat_a + lat_b)
            if abs(lat) > 0.5 * t + 15.0:
                continue
            s_a, s_b = float(np.dot(p_a, d)), float(np.dot(p_b, d))
            s_lo, s_hi = min(s_a, s_b), max(s_a, s_b)
            if min(W, s_hi) - max(0.0, s_lo) >= 0.55 * W:
                if not any(abs(lat - ex) < 8.0 for ex in lats):
                    lats.append(lat)
        inner = [lat for lat in lats if abs(lat) <= 0.5 * t - 12.0]
        return len(lats) >= 3 or len(inner) >= 2

    def has_lintel_line(p0, p1, t) -> bool:
        """True when the CAD draws a line straight across the gap inside the wall band (the usual
        plan convention for a beam / lintel over an opening): the wall above must be completed."""
        a = np.asarray(p0, float)
        W = math.dist(p0, p1)
        if W < 250.0:
            return False
        d = _unit(np.subtract(p1, p0))
        n = np.array([-d[1], d[0]])
        cover = []
        for x1, y1, x2, y2 in underlay:
            sv = np.array([x2 - x1, y2 - y1], float)
            L = float(np.linalg.norm(sv))
            if L < 0.3 * W or abs(np.dot(sv / L, d)) < 0.995:
                continue
            p_a = np.array([x1, y1], float) - a
            p_b = np.array([x2, y2], float) - a
            lat_a, lat_b = float(np.dot(p_a, n)), float(np.dot(p_b, n))
            if abs(lat_a - lat_b) > 3.0 or abs(0.5 * (lat_a + lat_b)) > 0.5 * t + 15.0:
                continue
            s_a, s_b = float(np.dot(p_a, d)), float(np.dot(p_b, d))
            lo, hi = max(0.0, min(s_a, s_b)), min(W, max(s_a, s_b))
            if hi - lo > 1.0:
                cover.append((lo, hi))
        cover.sort()
        covered, cur_lo, cur_hi = 0.0, None, None
        for lo, hi in cover:
            if cur_hi is None or lo > cur_hi + 5.0:
                if cur_hi is not None:
                    covered += cur_hi - cur_lo
                cur_lo, cur_hi = lo, hi
            else:
                cur_hi = max(cur_hi, hi)
        if cur_hi is not None:
            covered += cur_hi - cur_lo
        return covered >= 0.9 * W

    for p0, p1, t, i, j, src in gaps:
        r = _rect(p0, p1, t)
        width = math.dist(p0, p1)
        otype = _classify_width(width, spec)
        d_gap = _unit(np.subtract(p1, p0))
        trim = min(120.0, 0.2 * width)
        r_inner = _rect(np.asarray(p0, float) + d_gap * trim, np.asarray(p1, float) - d_gap * trim, t)
        win_sym = has_window_symbol_in_gap(p0, p1, t)
        win_hit = win_sym or (hints_win is not None and r_inner.buffer(60.0).intersects(hints_win))
        door_hit = (not win_sym) and (hints_door is not None and r.buffer(500).intersects(hints_door))
        is_l_passage = (src == 'wall end facing wall end-zone' and end_is_l_corner(i, p0, d_gap, t))
        lintel_line = (otype == 'passage' and not (win_hit or door_hit) and has_lintel_line(p0, p1, t))
        if (otype == 'passage' and not (win_hit or door_hit)
                and (faces_outside(p0, p1, t) or is_l_passage)):
            notes.append(f"Gap {width:.0f} mm at ({(p0[0] + p1[0]) / 2:.0f},{(p0[1] + p1[1]) / 2:.0f}) has no window/door symbol "
                         f"- treated as an open recess / room span (no wall infill above)")
            continue
        if win_hit:
            otype = 'vent' if width <= spec['vent_max_width'] else 'window'
            src += ' + window symbol' if win_sym else ' + WIN layer'
        elif door_hit:
            otype = 'door' if width <= spec['door_max'] else 'passage'
            src += ' + DOOR layer'
        elif width < spec['door_min']:
            otype = 'vent'
            src += ' + narrow (< door_min)'
        sill, head = _elevations(otype, spec)
        o = Opening('', otype, p0, p1, t, sill, head, src)
        if lintel_line and otype == 'passage':
            o.lintel_line = True
            o.source += ' + lintel line drawn across'
            o.notes.append('beam / lintel line drawn across the opening - wall completed above door head')
        if width < spec['door_min'] and otype in ('door', 'passage'):
            o.notes.append(f'narrow opening {width:.0f} mm (< {spec["door_min"]:.0f}) - check drawing')
        openings.append(o)

    # stable ids by type then position
    counters: Dict[str, int] = {}
    prefix = {'door': 'Door', 'passage': 'Passage', 'window': 'Window', 'vent': 'Vent'}
    for o in sorted(openings, key=lambda o: (o.type, round(-(o.p0[1] + o.p1[1]) / 2, -2), (o.p0[0] + o.p1[0]) / 2)):
        counters[o.type] = counters.get(o.type, 0) + 1
        o.id = f"{prefix[o.type]}_{counters[o.type]:02d}"

    pieces = opening_pieces(openings, spec)
    return openings, pieces, posts, notes


def opening_pieces(openings: List[Opening], spec: dict = SPEC) -> List[Wall]:
    H = spec['wall_h']
    out: List[Wall] = []
    for o in openings:
        ring = [tuple(c) for c in list(o.rect().exterior.coords)[:-1]]
        if o.sill > 0:
            out.append(Wall(id=f"Sill_{o.id}", start_point=o.p0, end_point=o.p1, length=o.width,
                            thickness=o.thickness, height=o.sill, polygon=ring, layer='OPENING',
                            base=0.0, kind='sill', opening=o.type))
        if (o.head < H and (o.type != 'passage' or getattr(o, 'lintel_line', False))
                and not getattr(o, 'balcony', False)):
            out.append(Wall(id=f"Head_{o.id}", start_point=o.p0, end_point=o.p1, length=o.width,
                            thickness=o.thickness, height=H - o.head, polygon=ring, layer='OPENING',
                            base=o.head, kind='lintel', opening=o.type))
    return out


def _coords(geom):
    if geom.is_empty:
        return []
    if hasattr(geom, 'geoms'):
        out = []
        for g in geom.geoms:
            out += _coords(g)
        return out
    if geom.geom_type == 'Polygon':
        return list(geom.exterior.coords)
    return list(geom.coords)


# ════════════════════════════════════════════════════════════════════════════════════
#  ROOMS
# ════════════════════════════════════════════════════════════════════════════════════
def _polys(g) -> List[Polygon]:
    if g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    if hasattr(g, 'geoms'):
        out = []
        for x in g.geoms:
            out += _polys(x)
        return out
    return []


def _boundary_segments(ring_pts, pieces, opening_by_id):
    """ring_pts: CCW list of points (no repeat). For every edge returns typed sub-segments
    [(s0, s1, type, opening_id)] where type in wall|window|vent|door|passage|open."""
    piece_polys = [(Polygon(p.polygon).buffer(0), p) for p in pieces]
    edges = []
    n = len(ring_pts)
    for e in range(n):
        a, b = np.array(ring_pts[e], float), np.array(ring_pts[(e + 1) % n], float)
        L = float(np.linalg.norm(b - a))
        if L < 1e-6:
            continue
        d = (b - a) / L
        out_n = np.array([d[1], -d[0]])                 # right side of a CCW ring = outside the room
        probe = LineString([a + out_n * 3.0, b + out_n * 3.0])
        intervals = []
        for poly, p in piece_polys:
            if not probe.intersects(poly):
                continue
            for seg in _line_parts(probe.intersection(poly)):
                ss = sorted(float(np.dot(np.asarray(q) - (a + out_n * 3.0), d)) for q in seg.coords)
                s_lo, s_hi = max(0.0, ss[0]), min(L, ss[-1])
                if s_hi - s_lo > 0.5:
                    if p.kind != 'wall':
                        pd = _unit(np.subtract(p.end_point, p.start_point))
                        if abs(float(np.dot(pd, d))) <= 0.85 or (s_hi - s_lo) < 200.0:
                            # Perpendicular opening grazing the room corner -> treat as solid wall corner
                            intervals.append((s_lo, s_hi, None))
                            continue
                    intervals.append((s_lo, s_hi, p))
        cuts = sorted({0.0, L} | {x for s0, s1, _ in intervals for x in (s0, s1)})
        segs = []
        for s0, s1 in zip(cuts, cuts[1:]):
            if s1 - s0 < 1e-6:
                continue
            m = (s0 + s1) / 2
            cover = [p for x0, x1, p in intervals if x0 - 1e-6 <= m <= x1 + 1e-6]
            if any(p is None or p.kind == 'wall' for p in cover):
                typ, oid = 'wall', ''
            elif cover:
                oid = cover[0].id.split('_', 1)[1]
                typ = opening_by_id[oid].type if oid in opening_by_id else cover[0].opening or 'passage'
            else:
                typ, oid = 'open', ''
            if segs and segs[-1][2] == typ and segs[-1][3] == oid:
                segs[-1] = (segs[-1][0], s1, typ, oid)
            else:
                segs.append((s0, s1, typ, oid))
        # absorb numerical slivers (< 3 mm) into the neighbour
        clean = []
        for s in segs:
            if s[1] - s[0] < 3.0 and clean:
                clean[-1] = (clean[-1][0], s[1], clean[-1][2], clean[-1][3])
            else:
                clean.append(s)
        if len(clean) > 1 and clean[0][1] - clean[0][0] < 3.0:
            clean[1] = (clean[0][0], clean[1][1], clean[1][2], clean[1][3])
            clean = clean[1:]
        edges.append({'a': tuple(a), 'b': tuple(b), 'L': L, 'd': tuple(d), 'segs': clean})
    return edges


def _line_parts(g):
    if g.is_empty:
        return []
    if g.geom_type == 'LineString':
        return [g]
    if hasattr(g, 'geoms'):
        out = []
        for x in g.geoms:
            out += _line_parts(x)
        return out
    return []


def _ring_ccw(poly: Polygon, tol: float = 0.005) -> List[Tuple[float, float]]:
    p = orient(poly.simplify(tol, preserve_topology=True), sign=1.0)
    pts = list(p.exterior.coords)[:-1]
    return [(float(x), float(y)) for x, y in pts]


# ════════════════════════════════════════════════════════════════════════════════════
#  MAIN ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════════
def analyse(walls: List[Wall], fills: List[Wall], openings: List[Opening], outline: list,
            ctx: dict, spec: dict = SPEC) -> dict:
    report: Dict[str, object] = {'spec_mm': dict(spec), 'warnings': [], 'ambiguities': []}
    pieces = [p for p in walls + fills if len(p.polygon) >= 3]
    opening_by_id = {o.id: o for o in openings}

    foot = unary_union([Polygon(r).buffer(0) for r in outline if len(r) >= 3]) if outline else None
    solids = unary_union([Polygon(p.polygon).buffer(0) for p in pieces])
    if foot is None or foot.is_empty:
        foot = solids.convex_hull
        report['warnings'].append('No building outline available - convex hull used as footprint')
    foot = foot.union(solids).buffer(0)
    # rooms are split off with walls grown by 1 mm (walls that meet only at a corner point must still close a room),
    # then each room is grown back to the exact wall faces
    exact_free = foot.difference(solids).buffer(0)
    voids = _polys(foot.difference(solids.buffer(1.0, join_style=2)).buffer(0))
    voids = [g for v in voids for g in _polys(v.buffer(1.0, join_style=2).intersection(exact_free))]
    voids = [v.buffer(-0.5, join_style=2).buffer(0.5, join_style=2) for v in voids]   # drop hairline slivers
    voids = [g for v in voids for g in _polys(v)]

    labels = ctx.get('labels', [])
    inserts = ctx.get('inserts', [])

    rooms = []
    tiny = 0
    for v in voids:
        if v.area < 0.4e6:
            tiny += 1
            continue
        ring = _ring_ccw(v)
        edges = _boundary_segments(ring, pieces, opening_by_id)
        op_ids = sorted({s[3] for e in edges for s in e['segs'] if s[3]})
        mrr = v.minimum_rotated_rectangle
        mc = list(mrr.exterior.coords)[:4]
        dims = sorted([math.dist(mc[0], mc[1]), math.dist(mc[1], mc[2])])
        open_len = sum(s[1] - s[0] for e in edges for s in e['segs'] if s[2] == 'open')
        room_inserts = [b for b, x, y in inserts if v.contains(Point(x, y))]
        rooms.append({'poly': v, 'ring': ring, 'holes': [list(h.coords)[:-1] for h in v.interiors],
                      'edges': edges, 'openings': op_ids, 'area_m2': v.area / 1e6,
                      'min_dim': dims[0], 'max_dim': dims[1], 'open_len': open_len,
                      'labels': [], 'fixtures': room_inserts})
    if tiny:
        report['warnings'].append(f'{tiny} enclosed slivers smaller than 0.4 m2 ignored (wall-junction artefacts)')

    # Match room labels to rooms, handling interior holes, close boundary proximity, and leader callouts
    # where a small room's label (e.g. "C.TOILET 1.5X2.45", "BALCONY 1.1X2.15") is placed inside an adjacent larger room.
    if rooms and labels:
        ext_polys = [Polygon(rm['poly'].exterior) for rm in rooms]
        for t, x, y in labels:
            pt = Point(x, y)
            cand_idx = next((idx for idx, rm in enumerate(rooms) if rm['poly'].contains(pt)), None)
            if cand_idx is None and (WASH_WORDS.search(t) or DRY_WORDS.search(t)):
                containing = [idx for idx, ep in enumerate(ext_polys) if ep.contains(pt)]
                if containing:
                    cand_idx = min(containing, key=lambda idx: rooms[idx]['area_m2'])
                else:
                    nearest_idx = min(range(len(rooms)), key=lambda idx: rooms[idx]['poly'].distance(pt))
                    if rooms[nearest_idx]['poly'].distance(pt) <= 450.0:
                        cand_idx = nearest_idx
            if cand_idx is None:
                continue
            m_dim = DIM_RE.search(t)
            lbl_area = (float(m_dim.group(1)) * float(m_dim.group(2))) if m_dim else None
            if (lbl_area is not None and 0.8 <= lbl_area <= 6.5
                    and rooms[cand_idx]['area_m2'] > max(6.8, 1.85 * lbl_area)
                    and not re.search(r'\b(LIVING|DINING|HALL)\b', t, re.I)):
                is_wash_t = bool(WASH_WORDS.search(t))
                nearby = [
                    idx2 for idx2 in range(len(rooms))
                    if idx2 != cand_idx
                    and 0.35 * lbl_area <= rooms[idx2]['area_m2'] <= 1.75 * lbl_area
                    and rooms[idx2]['poly'].distance(pt) <= 3800.0
                    and (
                        (is_wash_t and not any(DRY_WORDS.search(l2) and not WASH_WORDS.search(l2) for l2 in rooms[idx2]['labels']))
                        or (not is_wash_t and not any(WASH_WORDS.search(l2) for l2 in rooms[idx2]['labels'])
                            and not any(FIXTURE_WORDS.search(b) for b in rooms[idx2]['fixtures']))
                    )
                ]
                if nearby:
                    best_nb = min(
                        nearby,
                        key=lambda idx2: (
                            0 if (is_wash_t and any(FIXTURE_WORDS.search(b) for b in rooms[idx2]['fixtures'])) else 1,
                            1 if (is_wash_t and any(WASH_WORDS.search(l2) for l2 in rooms[idx2]['labels'])) else 0,
                            rooms[idx2]['poly'].distance(pt),
                        ),
                    )
                    if t not in rooms[best_nb]['labels']:
                        rooms[best_nb]['labels'].append(t)
                    continue
                if is_wash_t or re.search(r'\b(BALC|LOBBY|W\.?I\.?W)\b', t, re.I):
                    # Leader callout for an adjacent small space; do not attach to a large room
                    continue
            if t not in rooms[cand_idx]['labels']:
                rooms[cand_idx]['labels'].append(t)

    # Room schedule written in a Word document: place each documented room on the plan by its size
    # (raster plans also get the drawing scale that best explains the documented sizes).
    schedule = ctx.get('schedule') or []
    if rooms and schedule:
        from .document_reader import match_schedule
        sm = match_schedule(rooms, schedule, bool(ctx.get('schedule_allow_scale')))
        s_fac = sm['scale']
        matched = []
        for k, e, cost in sm['pairs']:
            rm = rooms[k]
            has_room_word = any(WASH_WORDS.search(t) or DRY_WORDS.search(t) for t in rm['labels'])
            size_txt = (f"{e['w_mm'] / 1000:.2f}X{e['l_mm'] / 1000:.2f}" if 'w_mm' in e else '')
            if not has_room_word:
                rm['labels'].append(f"{e['name'].upper()} {size_txt}".strip())
            rm['doc_name'] = e['name']
            matched.append({'name': e['name'], 'room_idx': k, 'cost': round(cost, 3),
                            'doc_size': (f"{e['w_mm'] / 1000:.2f} x {e['l_mm'] / 1000:.2f} m" if 'w_mm' in e
                                         else f"{e.get('area_m2', 0):.2f} m2"),
                            'plan_size': f"{rm['min_dim'] * s_fac / 1000:.2f} x {rm['max_dim'] * s_fac / 1000:.2f} m, "
                                         f"{rm['area_m2'] * s_fac * s_fac:.2f} m2",
                            'kept_cad_label': has_room_word})
        report['document_schedule'] = {'scale': s_fac, 'matched': matched, 'unmatched': sm['unmatched']}


    # opening -> rooms adjacency (from verified edge segments)
    for o in openings:
        o_rooms = [k for k, rm in enumerate(rooms) if o.id in rm['openings']]
        o.notes = [n for n in o.notes if not n.startswith('rooms:')]
        setattr(o, 'rooms', o_rooms)

    # ── washroom & shaft classification from independent signals
    shaft_pts = [(Point(sp[0], sp[1]), float(sp[2]) if len(sp) > 2 else 99999.0) for sp in ctx.get('shaft_points', [])]
    total_plan_doors = sum(1 for o in openings if o.type in ('door', 'passage'))
    has_wide_room_doors = any(o.type == 'door' and math.dist(o.p0, o.p1) >= 880.0 for o in openings)
    for k, rm in enumerate(rooms):
        sig, score = [], 0
        kinds = [opening_by_id[i].type for i in rm['openings'] if i in opening_by_id]
        n_vent, n_win = kinds.count('vent'), kinds.count('window')
        n_door, n_pass = kinds.count('door'), kinds.count('passage')
        room_diag = math.hypot(rm['min_dim'], rm['max_dim'])
        has_parapet_op = any(getattr(opening_by_id[i], 'is_parapet', False) for i in rm['openings'] if i in opening_by_id)
        has_x_cross = (
            rm['area_m2'] <= 15.0
            and not has_parapet_op
            and any(rm['poly'].contains(pt) and l_diag >= 0.50 * room_diag for pt, l_diag in shaft_pts)
        )
        has_room_label = any(WASH_WORDS.search(t) or DRY_WORDS.search(t) for t in rm['labels'])
        has_wash_lbl = any(WASH_WORDS.search(t) for t in rm['labels'])
        has_dry_lbl = any(DRY_WORDS.search(t) and not DRY_BALCONY_WORDS.search(t) for t in rm['labels'])
        if has_wash_lbl and not (has_dry_lbl and rm['area_m2'] >= 5.5):
            score += 8; sig.append('CAD label says washroom (+8)')
        if has_dry_lbl and (not has_wash_lbl or rm['area_m2'] >= 5.5):
            score -= 5; sig.append('CAD label says dry room (-5)')
        fx = [b for b in rm['fixtures'] if FIXTURE_WORDS.search(b)]
        if fx:
            score += 4; sig.append(f'sanitary fixture blocks {fx[:3]} (+4)')
        if n_vent:
            score += 3; sig.append(f'{n_vent} ventilator on boundary (+3)')
        if n_win:
            score -= 1; sig.append(f'{n_win} full-size window(s) (-1)')
        if n_door == 1 and n_pass == 0:
            score += 2; sig.append('single doorway, no open passage (+2)')
            if not has_room_label and has_wide_room_doors and 1.2 <= rm['area_m2'] <= 5.5:
                d_op = next((opening_by_id[i] for i in rm['openings'] if i in opening_by_id and opening_by_id[i].type == 'door'), None)
                if d_op is not None and math.dist(d_op.p0, d_op.p1) <= 800.0:
                    score += 2; sig.append(f'narrow washroom-width doorway {math.dist(d_op.p0, d_op.p1):.0f} mm (+2)')
        if n_pass:
            score -= 3; sig.append(f'{n_pass} open passage(s) (-3)')
        if n_door + n_pass == 0:
            score -= 2; sig.append('no doorway found (-2)')
        if 1.2 <= rm['area_m2'] <= 6.5:
            score += 1; sig.append(f'compact area {rm["area_m2"]:.2f} m2 (+1)')
        elif 6.5 < rm['area_m2'] <= 9.0:
            score -= 2; sig.append(f'medium area {rm["area_m2"]:.2f} m2 (-2)')
        elif rm['area_m2'] > 9.0:
            score -= 4; sig.append(f'large area {rm["area_m2"]:.2f} m2 (-4)')
        if rm['min_dim'] < 900.0:
            score -= 2; sig.append(f'narrow ({rm["min_dim"]:.0f} mm) (-2)')
        if rm['open_len'] > 300.0:
            score -= 3; sig.append(f'{rm["open_len"]:.0f} mm of boundary open to outside (-3)')
        rm['score'], rm['signals'] = score, sig
        rm['type'] = 'washroom' if score >= 5 else ('review' if score >= 3 else 'dry')
        if rm['open_len'] > 300.0 and rm['type'] != 'washroom' and not has_room_label:
            rm['type'] = 'external'
        elif rm['type'] != 'washroom' and not has_room_label:
            if has_x_cross:
                rm['type'] = 'shaft'
                sig.append('diagonal X shaft cross inside void -> shaft')
            elif total_plan_doors >= 2 and (n_door + n_pass == 0) and not has_parapet_op and rm['open_len'] < 100.0 and (
                (n_win == 0 and rm['area_m2'] <= 6.0)
                or (rm['area_m2'] <= 6.5 and not any(len(getattr(opening_by_id.get(oid), 'rooms', [])) == 1 for oid in rm['openings']))
            ):
                rm['type'] = 'shaft'
                sig.append('completely enclosed void with no doorway -> shaft/duct')
            elif rm['area_m2'] >= 200.0 or (rm['area_m2'] >= 88.0 and n_door == 0 and (n_vent + n_win) >= 3):
                rm['type'] = 'external'
                sig.append('large courtyard / setback space with exterior windows/ventilators -> external')
            elif rm['min_dim'] < 1350.0 and rm['max_dim'] > 12000.0:
                rm['type'] = 'external'
                sig.append('narrow perimeter setback strip -> external')

    def neighbours(k):
        out = []
        for oid in rooms[k]['openings']:
            o = opening_by_id.get(oid)
            if o is None or o.type not in ('door', 'passage'):
                continue
            out += [m for m in getattr(o, 'rooms', []) if m != k]
        return out

    # Propagate external classification to border voids whose only doorways/passages open into external areas
    for k, rm in enumerate(rooms):
        if rm['type'] in ('dry', 'review') and not any(WASH_WORDS.search(t) or DRY_WORDS.search(t) for t in rm['labels']):
            nb = neighbours(k)
            if nb and all(rooms[m]['type'] == 'external' for m in nb):
                rm['type'] = 'external'
                rm['signals'].append('only connects to external setback -> external')

    # possible balconies (reported, still treated as dry rooms)
    for rm in rooms:
        if rm['type'] == 'dry' and rm['area_m2'] >= 2.0:
            glazed = sum(s[1] - s[0] for e in rm['edges'] for s in e['segs']
                         if s[2] in ('window', 'passage') and len(getattr(opening_by_id.get(s[3]), 'rooms', [])) <= 1)
            if (rm['min_dim'] <= 2100.0 and glazed >= 0.4 * rm['max_dim']) or (
                rm['min_dim'] <= 2650.0 and rm['max_dim'] >= 2.2 * rm['min_dim'] and glazed >= 0.75 * rm['max_dim']
            ):
                rm['flags'] = ['possible balcony / sit-out (narrow room with a long glazed or open side)']

    # naming: Master_Toilet = washroom whose doorway opens into a private room (or via a private dressing vestibule)
    wash = [k for k, rm in enumerate(rooms) if rm['type'] == 'washroom']
    largest = max((k for k, rm in enumerate(rooms) if rm['type'] != 'external'),
                  key=lambda k: rooms[k]['area_m2'], default=-1)

    master, best = None, None
    for k in wash:
        for m in neighbours(k):
            if m == largest or rooms[m]['type'] != 'dry':
                continue
            cand_m = m
            vest_m = None
            suite_area = rooms[m]['area_m2']
            if suite_area < 7.0:
                bed_nbs = [
                    b for b in neighbours(m)
                    if b != largest and rooms[b]['type'] == 'dry' and rooms[b]['area_m2'] >= 7.0
                    and [x for x in neighbours(b) if rooms[x]['type'] != 'washroom' and not rooms[x].get('flags')] == [m]
                ]
                if len(bed_nbs) == 1:
                    vest_m = m
                    cand_m = bed_nbs[0]
                    suite_area = rooms[cand_m]['area_m2'] + rooms[vest_m]['area_m2']
                else:
                    continue
            dry_links = [
                x for x in neighbours(vest_m if vest_m is not None else cand_m)
                if rooms[x]['type'] != 'washroom' and x != cand_m and not rooms[x].get('flags')
            ]
            if len(dry_links) > 3:
                continue
            has_priv_bal = any(rooms[x].get('flags') for x in range(len(rooms)) if x != cand_m and any(
                cand_m in getattr(opening_by_id.get(oid), 'rooms', []) for oid in rooms[x]['openings']
            ))
            key = (len(dry_links), 0 if has_priv_bal else 1, -suite_area)
            if best is None or key < best:
                master, best = k, key
                rooms[k]['master_of'] = cand_m
                rooms[k]['master_vestibule'] = vest_m
    others = sorted([k for k in wash if k != master], key=lambda k: (rooms[k]['poly'].centroid.x, rooms[k]['poly'].centroid.y))
    for n, k in enumerate(others):
        rooms[k]['name'], rooms[k]['code'] = f'Toilet_{n + 1}', f'T{n + 1}'
    if master is not None:
        rooms[master]['name'], rooms[master]['code'] = 'Master_Toilet', 'MT'
    dry_n = 0
    for k in sorted(range(len(rooms)), key=lambda k: -rooms[k]['area_m2']):
        if 'name' not in rooms[k]:
            dry_n += 1
            rooms[k]['name'] = f"Room_{dry_n:02d}"
            rooms[k]['code'] = f"R{dry_n:02d}"
    for rm in rooms:
        if rm['type'] == 'review':
            report['ambiguities'].append(f"{rm['name']} ({rm['area_m2']:.2f} m2) scored {rm['score']} - "
                                         f"could be a washroom; signals: {'; '.join(rm['signals'])}")
        for f in rm.get('flags', []):
            report['ambiguities'].append(f"{rm['name']} ({rm['area_m2']:.2f} m2): {f}")
    if len(wash) != 3:
        report['ambiguities'].append(f'{len(wash)} washrooms detected (3 expected) - check the classification table')

    for o in openings:
        o.rooms_named = [rooms[m]['name'] for m in getattr(o, 'rooms', [])]

    _room_uses(rooms, openings, opening_by_id, master, report)
    ds_rep = report.get('document_schedule')
    if ds_rep:
        for m in ds_rep['matched']:
            rm = rooms[m['room_idx']]
            m['room'] = rm['name']
            if rm.get('doc_name') and rm['type'] != 'shaft':
                rm['display_name'] = rm['doc_name']          # the name written in the document
                rm['use_reason'] = f"document room schedule '{rm['doc_name']}' ({m['doc_size']})"
    _assign_room_materials_meta(rooms)

    door_lintel_n, win_lintel_n = 0, 0
    for o in openings:
        rs = getattr(o, 'rooms', [])
        non_shaft_rs = [r for r in rs if rooms[r]['type'] not in ('shaft', 'external')]
        open_bal_uses = ('balcony', 'sit_out', 'sitout', 'terrace', 'deck')
        is_dry_bal = len(non_shaft_rs) == 1 and rooms[non_shaft_rs[0]].get('use') == 'dry_balcony'
        is_open_bal_room = (
            len(non_shaft_rs) == 1
            and (rooms[non_shaft_rs[0]].get('use') or '') in open_bal_uses
            and (getattr(o, 'is_parapet', False) or o.type in ('window', 'vent'))
        )
        # Glazing on the outer edge of an open balcony (or a CAD parapet/railing line not bordering a non-balcony room)
        # -> 1.2 m (4 ft) balcony glass railing. Dry balconies and standard rooms do NOT receive balcony glass railings.
        o.dry_balcony = bool(is_dry_bal and (getattr(o, 'is_parapet', False) or o.type in ('window', 'vent')))
        o.balcony = (not is_dry_bal) and (
            is_open_bal_room or (bool(getattr(o, 'is_parapet', False)) and not non_shaft_rs)
        )
        if o.balcony:
            o.type = 'window'
            o.sill = spec['win_sill']
            o.head = o.sill + spec.get('balcony_glass_h', 1200.0)
            o.has_lintel = False
            o.lintel_id = ''
        elif o.dry_balcony:
            o.type = 'window'
            o.sill = spec['win_sill']
            o.head = spec['win_sill'] + spec['win_h']
            o.has_lintel = o.head < spec['wall_h']
            if o.has_lintel:
                win_lintel_n += 1
                o.lintel_id = f"Lintel_Window_{win_lintel_n:03d}"
            else:
                o.lintel_id = ''
        elif o.type == 'passage':
            # Section 3: Do not create a lintel beam across an open passage where no door or window exists,
            # unless the drawing itself draws the beam / lintel line straight across the opening.
            if getattr(o, 'lintel_line', False) and o.head < spec['wall_h']:
                o.sill = 0.0
                o.head = spec['door_head']
                o.has_lintel = True
                door_lintel_n += 1
                o.lintel_id = f"Lintel_Passage_{door_lintel_n:03d}"
            else:
                o.has_lintel = False
                o.lintel_id = ''
        elif o.type == 'door':
            o.sill = 0.0
            o.head = spec['door_head']
            o.has_lintel = True
            door_lintel_n += 1
            o.lintel_id = f"Lintel_Door_{door_lintel_n:03d}"
        elif o.type in ('window', 'vent'):
            # If a window only serves a washroom, enforce washroom sill height (1.2 m)
            if rs and all(rooms[r]['type'] == 'washroom' for r in rs):
                o.type = 'vent'
                o.sill = spec['vent_sill']
                o.head = spec['vent_sill'] + spec['vent_h']
            elif rs and all(rooms[r]['type'] == 'dry' for r in rs):
                o.type = 'window'
                o.sill, o.head = _elevations('window', spec)
            else:
                o.sill, o.head = _elevations(o.type, spec)
            o.has_lintel = o.head < spec['wall_h']
            if o.has_lintel:
                win_lintel_n += 1
                o.lintel_id = f"Lintel_Window_{win_lintel_n:03d}"
            else:
                o.lintel_id = ''
        else:
            o.has_lintel = False
            o.lintel_id = ''

    kitchens = _kitchen_platforms(rooms, opening_by_id, spec, report)
    room_floors = _room_floors(rooms, openings, walls, spec, report)
    skirting, room_skirting = _skirting(rooms, spec, report, kitchens=kitchens)
    tiles = _tiles(rooms, spec, report)
    panels = _panels(rooms, opening_by_id, spec, report)
    recessed_ceilings = _recessed_ceilings(rooms, spec, report)

    # ── python-side report
    report['config'] = CONFIG
    report['rooms'] = [{'name': rm['name'], 'use': rm['use'], 'label': rm['label'], 'type': rm['type'],
                        'display_name': rm.get('display_name', rm['label']),
                        'cad_dim': rm.get('cad_dim', ''),
                        'cad_text': rm.get('cad_text', ''),
                        'floor_obj': rm.get('floor_obj', ''), 'floor_mat': rm.get('floor_mat', ''),
                        'skirt_obj': rm.get('skirt_obj', ''), 'skirt_mat': rm.get('skirt_mat', ''),
                        'tile_obj': rm.get('tile_obj', ''),
                        'recessed_ceiling': rm.get('recessed_ceiling', False),
                        'area_m2': round(rm['area_m2'], 2),
                        'min_dim_mm': round(rm['min_dim']), 'max_dim_mm': round(rm['max_dim']),
                        'score': rm['score'], 'signals': rm['signals'], 'openings': rm['openings'],
                        'use_reason': rm['use_reason'], 'vertices': len(rm['ring'])} for rm in rooms]
    report['openings'] = [dict(o.to_dict(), rooms=o.rooms_named, balcony=o.balcony,
                               dry_balcony=getattr(o, 'dry_balcony', False),
                               has_lintel=getattr(o, 'has_lintel', False),
                               lintel_id=getattr(o, 'lintel_id', '')) for o in openings]
    return {
        'rooms': [{'name': rm['name'], 'code': rm['code'], 'type': rm['type'], 'use': rm['use'], 'label': rm['label'],
                   'display_name': rm.get('display_name', rm['label']),
                   'cad_dim': rm.get('cad_dim', ''),
                   'cad_text': rm.get('cad_text', ''),
                   'floor_obj': rm.get('floor_obj', ''), 'floor_mat': rm.get('floor_mat', ''),
                   'skirt_obj': rm.get('skirt_obj', ''), 'skirt_mat': rm.get('skirt_mat', ''),
                   'tile_obj': rm.get('tile_obj', ''), 'floor_category': rm.get('floor_category', ''),
                   'panelled': rm['panelled'], 'recessed_ceiling': rm.get('recessed_ceiling', False),
                   'area_m2': round(rm['area_m2'], 3), 'ring': [[round(x, 1), round(y, 1)] for x, y in rm['ring']],
                   'holes': [[[round(x, 1), round(y, 1)] for x, y in h] for h in rm['holes']]} for rm in rooms],
        'openings': [dict(o.to_dict(), rooms=o.rooms_named, balcony=o.balcony,
                          dry_balcony=getattr(o, 'dry_balcony', False),
                          has_lintel=getattr(o, 'has_lintel', False),
                          lintel_id=getattr(o, 'lintel_id', '')) for o in openings],
        'room_floors': room_floors,
        'skirting': skirting,
        'room_skirting': room_skirting,
        'tiles': tiles,
        'panels': panels,
        'kitchens': kitchens,
        'recessed_ceilings': recessed_ceilings,
        'floor': _floor_rings(foot),
        'ceiling': _ceiling_rings(foot, recessed_ceilings),
        'report': report,
    }


def sync_opening_pieces(openings: List[Opening], fills: List[Wall], spec: dict = SPEC) -> List[Wall]:
    """Synchronize sill/lintel pieces with room-classified opening elevations and lintel names.
    Removes lintel beams across open passages and balcony railings."""
    H = spec['wall_h']
    op_map = {o.id: o for o in openings}
    out: List[Wall] = []
    for f in fills:
        base_id = f.id.split('_', 1)[1] if '_' in f.id else f.id
        # Strip any _2, _3 suffix from 3D overlap splitting when matching the opening id
        oid = base_id
        if oid not in op_map and '_' in oid:
            parts = oid.rsplit('_', 1)
            if parts[1].isdigit() and parts[0] in op_map:
                oid = parts[0]
        o = op_map.get(oid)
        if o is None:
            out.append(f)
            continue
        if f.kind == 'sill':
            if o.sill <= 0:
                continue
            f.height = o.sill
            f.opening = o.type
            out.append(f)
        elif f.kind == 'lintel':
            if (not getattr(o, 'has_lintel', False) or getattr(o, 'balcony', False)
                    or (o.type == 'passage' and not getattr(o, 'lintel_line', False))):
                continue
            f.base = o.head
            f.height = H - o.head
            f.opening = o.type
            f.opening_id = o.id
            suf = f.id[len(f"Head_{oid}"):] if f.id.startswith(f"Head_{oid}") else ''
            f.id = (o.lintel_id or f"Lintel_{o.id}") + suf
            out.append(f)
        else:
            out.append(f)
    return out


def _is_recessed_ceiling_room(rm: dict) -> bool:
    """Recessed architectural ceilings are installed ONLY in bedrooms and halls (living / dining)."""
    if rm.get('type') != 'dry' or rm.get('area_m2', 0.0) < 7.0 or rm.get('min_dim', 0.0) < 1800.0:
        return False
    u = (rm.get('use') or '').lower()
    if any(ex in u for ex in ('balcony', 'sit_out', 'washroom', 'toilet', 'bath', 'kitchen', 'pantry', 'wardrobe',
                              'servant', 'box_room', 'store', 'utility', 'lobby', 'foyer', 'shaft', 'external',
                              'puja', 'pooja', 'stair', 'lift')):
        return False
    return any(inc in u for inc in ('bed', 'master_suite', 'suite', 'living', 'hall', 'dining'))


def _room_uses(rooms, openings, opening_by_id, master, report):
    """Professional room use from plan topology (CAD labels and manual overrides win when present):
    washroom / balcony / dry_balcony / master_bedroom / living / hall_dining / kitchen / bedroom / foyer / lobby."""
    overrides = CONFIG.get('room_type_overrides', {}) or {}
    bal_overrides = CONFIG.get('balcony_type_overrides', {}) or {}
    default_bal_type = CONFIG.get('default_balcony_type', 'open')

    def links(k):
        out = []
        for oid in rooms[k]['openings']:
            o = opening_by_id.get(oid)
            if o is not None and o.type in ('door', 'passage'):
                out.append(o)
        return out

    plan_has_explicit_kitchen = any(
        (_parse_cad_room_label(r0.get('labels', []), r0.get('min_dim', 0.0), r0.get('max_dim', 0.0))[0] == 'kitchen')
        or any(KITCHEN_FIXTURE_WORDS.search(b) for b in r0.get('fixtures', []))
        or ('kitchen' in (overrides.get(r0['name']) or ''))
        for r0 in rooms
    )
    for k, rm in enumerate(rooms):
        parsed_use, parsed_disp, cad_dim, cad_text = _parse_cad_room_label(
            rm.get('labels', []), rm.get('min_dim', 0.0), rm.get('max_dim', 0.0)
        )
        rm['cad_dim'] = cad_dim
        rm['cad_text'] = cad_text
        rm['_parsed_disp'] = parsed_disp
        if rm['name'] in overrides:
            rm['use'], rm['use_reason'] = overrides[rm['name']], 'manual CONFIG room_type_overrides'
            continue
        dry_bal_lbl = next((t for t in rm['labels'] if DRY_BALCONY_WORDS.search(t)), None)
        kitch_fx = [b for b in rm.get('fixtures', []) if KITCHEN_FIXTURE_WORDS.search(b)]
        has_parapet = any(getattr(opening_by_id.get(oid), 'is_parapet', False) for oid in rm['openings'])
        n_win_rm = sum(1 for oid in rm['openings'] if oid in opening_by_id and opening_by_id[oid].type in ('window', 'vent'))
        has_interior_passage = any(o.type == 'passage' and len(getattr(o, 'rooms', [])) >= 2 for o in links(k))
        if rm['type'] == 'washroom':
            rm['use'] = 'washroom'
            rm['use_reason'] = f'CAD label "{cad_text}"' if cad_text else 'classified washroom (see signals)'
        elif rm['type'] == 'shaft':
            rm['use'], rm['use_reason'] = 'shaft', 'enclosed service shaft / duct'
        elif rm['type'] == 'external':
            rm['use'], rm['use_reason'] = 'external', 'outdoor setback / courtyard / open border'
        elif (dry_bal_lbl and parsed_use != 'kitchen') or parsed_use == 'dry_balcony' or bal_overrides.get(rm['name']) == 'dry':
            rm['use'], rm['use_reason'] = 'dry_balcony', f'dry balcony ({cad_text or dry_bal_lbl or "CONFIG override"})'
        elif parsed_use and parsed_use != 'washroom':
            rm['use'], rm['use_reason'] = parsed_use, f'CAD label "{cad_text}"'
            if ('balcony' in rm['use'] or 'sit_out' in rm['use']) and bal_overrides.get(rm['name']) == 'dry':
                rm['use'] = 'dry_balcony'
        elif kitch_fx:
            rm['use'], rm['use_reason'] = 'kitchen', f'kitchen fixture block(s) {kitch_fx[:2]}'
        elif has_parapet and rm['area_m2'] <= 10.0 and rm['min_dim'] <= 2650.0:
            b_use = 'dry_balcony' if (bal_overrides.get(rm['name']) == 'dry' or default_bal_type == 'dry') else 'balcony'
            rm['use'], rm['use_reason'] = b_use, 'bounded by balcony parapet / railing'
        elif rm.get('flags') and not (not plan_has_explicit_kitchen and not has_parapet and has_interior_passage and 4.0 <= rm['area_m2'] <= 14.5):
            b_use = 'dry_balcony' if (bal_overrides.get(rm['name']) == 'dry' or default_bal_type == 'dry') else 'balcony'
            rm['use'], rm['use_reason'] = b_use, 'narrow room (<= 2.1 m) whose long side is an outer glazed edge'
        elif rm['area_m2'] < 2.0 or (len(links(k)) >= 3 and n_win_rm == 0 and rm['min_dim'] <= 2200.0 and rm['area_m2'] <= 9.5):
            rm['use'], rm['use_reason'] = 'lobby', f'circulation space {rm["area_m2"]:.2f} m2 between doors'
        elif master is not None and rooms[master].get('master_of') == k:
            rm['use'], rm['use_reason'] = 'master_bedroom', 'the attached Master_Toilet opens into it'
        elif master is not None and rooms[master].get('master_vestibule') == k:
            rm['use'], rm['use_reason'] = 'master_suite', 'private dressing vestibule between Master_Bedroom and Master_Toilet'
        elif any(len(getattr(o, 'rooms', [])) == 1 for o in links(k)):
            if rm['area_m2'] >= 9.0:
                rm['use'], rm['use_reason'] = 'living', 'main entrance door opens into it'
            else:
                rm['use'], rm['use_reason'] = 'foyer', f'entrance foyer {rm["area_m2"]:.2f} m2 at outer doorway'
        else:
            rm['use'], rm['use_reason'] = None, ''
    rest = sorted([k for k, rm in enumerate(rooms) if rm['use'] is None], key=lambda k: -rooms[k]['area_m2'])
    if rest and rooms[rest[0]]['area_m2'] >= 15.0 and len(links(rest[0])) >= 3:
        rooms[rest[0]]['use'], rooms[rest[0]]['use_reason'] = 'hall_dining', 'largest room, hub for several doors'
        rest = rest[1:]
    has_kitchen = any('kitchen' in (rm.get('use') or '') for rm in rooms)
    kitch_cand = None
    if not has_kitchen and rest:
        cands = [k for k in reversed(rest) if 4.0 <= rooms[k]['area_m2'] <= 14.5]
        if cands:
            kitch_cand = max(
                cands,
                key=lambda k: (
                    1 if any(o.type == 'passage' for o in links(k)) else 0,
                    1 if any(opening_by_id[oid].type in ('window', 'vent') for oid in rooms[k]['openings'] if oid in opening_by_id) else 0,
                    -rooms[k]['area_m2'],
                ),
            )
    for k in rest:
        rm = rooms[k]
        if k == kitch_cand:
            rm['use'] = 'kitchen'
            rm['use_reason'] = 'compact room opening off hall/dining (inferred kitchen; override via CONFIG if needed)'
            report.setdefault('assumptions', []).append(
                f"{rm['name']} ({rm['area_m2']:.2f} m2) inferred as Kitchen (no CAD text label present; configurable via CONFIG['room_type_overrides'])."
            )
        elif rm['area_m2'] >= 7.0:
            rm['use'], rm['use_reason'] = 'bedroom', 'private room >= 7 m2 with a single doorway' if len(links(k)) == 1 else 'habitable room >= 7 m2'
        else:
            rm['use'], rm['use_reason'] = 'utility', 'small dry room'
    # Reclassify small utility balconies attached exclusively to a kitchen as dry_balcony (no glass railing)
    for k, rm in enumerate(rooms):
        if rm['use'] == 'balcony' and rm['area_m2'] <= 6.5 and rm['name'] not in overrides and rm['name'] not in bal_overrides and not rm['labels']:
            adj_uses = set()
            for oid in rm['openings']:
                o = opening_by_id.get(oid)
                if o is None:
                    continue
                for r2 in getattr(o, 'rooms', []):
                    if r2 != k and rooms[r2]['type'] == 'dry' and 'balcony' not in (rooms[r2].get('use') or ''):
                        adj_uses.add(rooms[r2].get('use') or '')
            if adj_uses and all('kitchen' in u for u in adj_uses):
                rm['use'] = 'dry_balcony'
                rm['use_reason'] = 'utility dry balcony connected to kitchen'
    counts, seen = {}, {}
    for rm in rooms:
        counts[rm['use']] = counts.get(rm['use'], 0) + 1
    for rm in sorted(rooms, key=lambda r: -r['area_m2']):
        u = rm['use']
        if u == 'washroom':
            rm['label'] = rm['name']
            if rm['name'] == 'Master_Toilet':
                rm['display_name'] = 'Master Toilet'
            elif rm.get('_parsed_disp') in ('Common Toilet', 'Toilet'):
                rm['display_name'] = rm['_parsed_disp']
            else:
                rm['display_name'] = 'Toilet'
            continue
        seen[u] = seen.get(u, 0) + 1
        base = '_'.join(w.capitalize() for w in u.split('_'))
        rm['label'] = base + (f'_{seen[u]}' if counts[u] > 1 else '')
        p_disp = rm.get('_parsed_disp')
        if p_disp in ('Toilet', 'Common Toilet'):
            p_disp = None
        rm['display_name'] = p_disp or USE_DISPLAY_NAMES.get(u) or base.replace('_', ' ')
    for rm in rooms:
        # wall panels: habitable dry rooms only (no washrooms - they are tiled, no balconies/shafts/lifts/stairs)
        rm['panelled'] = rm['type'] == 'dry' and not any(
            k in (rm['use'] or '') for k in ('balcony', 'sit_out', 'washroom', 'utility', 'shaft', 'external', 'lift', 'stair')
        )
        rm['recessed_ceiling'] = _is_recessed_ceiling_room(rm)
    report['room_uses'] = {rm['name']: f"{rm['display_name']} ({rm['cad_dim']}) [{rm['label']}] - {rm['use_reason']}" for rm in rooms}


def _assign_room_materials_meta(rooms):
    """Assign room-specific floor & skirting object names and reusable material preset names (Sections 4-6)."""
    master_rooms = sorted(
        [rm for rm in rooms if rm['type'] == 'dry' and any(k in (rm.get('use') or '') for k in ('master_bedroom', 'master_suite', 'master_bed'))],
        key=lambda r: -r['area_m2'],
    )
    for idx, rm in enumerate(master_rooms, 1):
        suf = '' if idx == 1 else f'_{idx:02d}'
        rm['floor_obj'] = f'Floor_MasterBedroom_Wood{suf}'
        rm['skirt_obj'] = f'Skirting_MasterBedroom{suf}'
        rm['floor_mat'] = 'MAT_Floor_Master_Wood'
        rm['skirt_mat'] = 'MAT_Skirting_Master'
        rm['floor_category'] = 'master_wood'

    ent_idx, bal_idx, dbal_idx, wash_idx = 0, 0, 0, 0
    for rm in sorted(rooms, key=lambda r: (r['poly'].centroid.x, r['poly'].centroid.y)):
        if rm.get('floor_category'):
            continue
        u = (rm.get('use') or '').lower()
        if rm['type'] in ('external', 'shaft'):
            rm['floor_obj'] = ''
            rm['skirt_obj'] = ''
            rm['floor_mat'] = ''
            rm['skirt_mat'] = ''
            rm['floor_category'] = rm['type']
        elif rm['type'] == 'washroom':
            wash_idx += 1
            rm['floor_obj'] = f'Floor_Washroom_{wash_idx:02d}'
            rm['skirt_obj'] = ''
            rm['tile_obj'] = f'Tiles_Washroom_Wall_{wash_idx:02d}'
            rm['floor_mat'] = 'MAT_Floor_Washroom'
            rm['skirt_mat'] = ''
            rm['floor_category'] = 'washroom'
        elif u in ('foyer', 'entrance', 'lobby', 'passage', 'entrance_passage', 'entrance_lobby', 'fire_lobby'):
            ent_idx += 1
            rm['floor_obj'] = f'Floor_Entrance_{ent_idx:02d}'
            rm['skirt_obj'] = f'Skirting_Entrance_{ent_idx:02d}'
            rm['floor_mat'] = 'MAT_Floor_Entrance'
            rm['skirt_mat'] = 'MAT_Skirting_Entrance'
            rm['floor_category'] = 'entrance'
        elif u == 'dry_balcony':
            dbal_idx += 1
            rm['floor_obj'] = f'Floor_DryBalcony_{dbal_idx:02d}'
            rm['skirt_obj'] = f'Skirting_DryBalcony_{dbal_idx:02d}'
            rm['floor_mat'] = 'MAT_Floor_Balcony'
            rm['skirt_mat'] = 'MAT_Skirting_Balcony'
            rm['floor_category'] = 'dry_balcony'
        elif 'balcony' in u or 'sit_out' in u:
            bal_idx += 1
            rm['floor_obj'] = f'Floor_Balcony_{bal_idx:02d}'
            rm['skirt_obj'] = f'Skirting_Balcony_{bal_idx:02d}'
            rm['floor_mat'] = 'MAT_Floor_Balcony'
            rm['skirt_mat'] = 'MAT_Skirting_Balcony'
            rm['floor_category'] = 'balcony'
        else:
            rm['floor_obj'] = f"Floor_{rm['label']}"
            rm['skirt_obj'] = f"Skirting_{rm['label']}"
            rm['floor_mat'] = 'MAT_Floor_Common'
            rm['skirt_mat'] = 'MAT_Skirting_Common'
            rm['floor_category'] = 'common'


def _room_floors(rooms, openings, walls, spec, report) -> List[dict]:
    """Generate independent, exact room-boundary floor polygons (including doorway threshold half-strips
    clipped against solid walls so floors never spill into adjacent rooms or underneath walls)."""
    wall_union = unary_union([Polygon(w.polygon).buffer(0) for w in walls if w.kind == 'wall' and len(w.polygon) >= 3])
    room_polys = {k: rm['poly'] for k, rm in enumerate(rooms) if rm['type'] not in ('external', 'shaft')}
    for o in openings:
        if o.type not in ('door', 'passage'):
            continue
        rs = [k for k in getattr(o, 'rooms', []) if k in room_polys]
        if not rs:
            continue
        o_rect = o.rect().buffer(1.0, join_style=2).difference(wall_union)
        if o_rect.is_empty:
            continue
        if len(rs) == 1:
            room_polys[rs[0]] = room_polys[rs[0]].union(o_rect)
        else:
            p0, p1 = np.asarray(o.p0, float), np.asarray(o.p1, float)
            d = _unit(p1 - p0)
            cut_line = LineString([tuple(p0 - d * 100.0), tuple(p1 + d * 100.0)])
            halves = _polys(shp_split(o_rect, cut_line))
            for h_poly in halves:
                best_k = min(rs, key=lambda k: rooms[k]['poly'].distance(h_poly.centroid))
                room_polys[best_k] = room_polys[best_k].union(h_poly)

    out = []
    for k, rm in enumerate(rooms):
        if k not in room_polys or not rm.get('floor_obj'):
            continue
        f_geom = room_polys[k].difference(wall_union).buffer(0)
        rings = [_ring_dict(p) for p in _polys(f_geom) if p.area >= 1.0e4]
        if not rings:
            continue
        # Longest wall direction for consistent wooden plank orientation in Master Bedroom
        longest_e = max(rm['edges'], key=lambda e: e['L']) if rm.get('edges') else {'d': (1.0, 0.0)}
        plank_ang = math.atan2(longest_e['d'][1], longest_e['d'][0])
        out.append({
            'name': rm['floor_obj'],
            'room': rm['name'],
            'label': rm['label'],
            'use': rm['use'],
            'category': rm['floor_category'],
            'mat': rm['floor_mat'],
            'plank_angle': round(plank_ang, 6),
            'area_m2': round(f_geom.area / 1e6, 3),
            'rings': rings,
        })
    report['room_floors'] = {
        'count': len(out),
        'thickness_mm': spec.get('floor_finish_t', 20.0),
        'by_category': {
            cat: [f['name'] for f in out if f['category'] == cat]
            for cat in ('common', 'master_wood', 'entrance', 'balcony', 'dry_balcony', 'washroom')
        },
    }
    return out


def _kitchen_platforms(rooms, opening_by_id, spec, report) -> List[dict]:
    """Generate straight or L-shaped kitchen platform (base support, stone countertop slab, and backsplash)
    along solid kitchen walls while preserving movement space and avoiding doors and windows."""
    c_depth = spec.get('kitchen_counter_depth', 600.0)
    b_depth = spec.get('kitchen_base_depth', 570.0)
    c_h = spec.get('kitchen_counter_h', 860.0)
    c_t = spec.get('kitchen_counter_t', 40.0)
    bs_h = spec.get('kitchen_backsplash_h', 600.0)
    bs_t = spec.get('kitchen_backsplash_t', 15.0)
    out = []
    kitch_idx = 0
    for rm in rooms:
        u = (rm.get('use') or '').lower()
        if rm['type'] != 'dry' or 'kitchen' not in u:
            continue
        if rm['min_dim'] < c_depth + 800.0:
            continue
        wall_off = spec.get('panel_t', 12.0) if rm.get('panelled') else 0.0
        edges = rm['edges']
        n = len(edges)
        cands = []
        for ei, e in enumerate(edges):
            if e['L'] < 1200.0:
                continue
            prev = edges[(ei - 1) % n]
            nxt = edges[(ei + 1) % n]
            # Check if adjoining perpendicular walls have a door/passage/low-sill window near the corner
            pad_start, pad_end = 0.0, 0.0
            for s0_p, s1_p, typ_p, oid_p in prev['segs']:
                if prev['L'] - s0_p <= c_depth + 250.0 and typ_p != 'wall':
                    o_p = opening_by_id.get(oid_p)
                    if typ_p in ('door', 'passage', 'open'):
                        pad_start = max(pad_start, c_depth + 350.0)
                    elif typ_p in ('window', 'vent') and (o_p is None or o_p.sill < c_h + 50.0):
                        pad_start = max(pad_start, c_depth + 100.0)
            for s0_n, s1_n, typ_n, oid_n in nxt['segs']:
                if s1_n <= c_depth + 250.0 and typ_n != 'wall':
                    o_n = opening_by_id.get(oid_n)
                    if typ_n in ('door', 'passage', 'open'):
                        pad_end = max(pad_end, c_depth + 350.0)
                    elif typ_n in ('window', 'vent') and (o_n is None or o_n.sill < c_h + 50.0):
                        pad_end = max(pad_end, c_depth + 100.0)
            for s0, s1, typ, _oid in e['segs']:
                if typ != 'wall':
                    continue
                u0 = max(s0 + (150.0 if s0 > 1.0 else pad_start), 0.0)
                u1 = min(s1 - (150.0 if s1 < e['L'] - 1.0 else pad_end), e['L'])
                if u1 - u0 >= 1200.0:
                    cands.append({'ei': ei, 'u0': u0, 'u1': u1, 'len': u1 - u0,
                                  'touches_start': u0 <= 15.0, 'touches_end': u1 >= e['L'] - 15.0})
        if not cands:
            continue
        primary = max(cands, key=lambda c: c['len'])
        selected = [primary]
        # Add adjacent perpendicular wall leg for an L-shaped counter if it meets cleanly at a solid corner
        for c in sorted(cands, key=lambda x: -x['len']):
            if c['ei'] == primary['ei']:
                continue
            if c['ei'] == (primary['ei'] + 1) % n and primary['touches_end'] and c['touches_start']:
                selected.append(c)
                break
            if c['ei'] == (primary['ei'] - 1) % n and primary['touches_start'] and c['touches_end']:
                selected.append(c)
                break

        def build_leg_union(depth_mm):
            polys = []
            for leg in selected:
                e = edges[leg['ei']]
                a, d = np.array(e['a'], float), np.array(e['d'], float)
                nin = np.array([-d[1], d[0]], float)
                p0 = a + d * leg['u0'] + nin * wall_off
                p1 = a + d * leg['u1'] + nin * wall_off
                polys.append(Polygon([p0, p1, p1 + nin * depth_mm, p0 + nin * depth_mm]))
            u_poly = unary_union(polys).intersection(rm['poly'].buffer(-wall_off if wall_off > 0 else 0.0, join_style=2))
            return u_poly.buffer(0)

        base_geom = build_leg_union(b_depth)
        top_geom = build_leg_union(c_depth)
        bs_geom = build_leg_union(bs_t)
        if top_geom.is_empty or base_geom.is_empty:
            continue
        kitch_idx += 1
        shape_kind = 'L-shaped' if len(selected) > 1 else 'straight'
        out.append({
            'id': f'Kitchen_{kitch_idx:02d}',
            'room': rm['name'],
            'label': rm['label'],
            'shape': shape_kind,
            'base_name': f'Kitchen_Base_{kitch_idx:02d}',
            'counter_name': f'Kitchen_Countertop_{kitch_idx:02d}',
            'backsplash_name': f'Kitchen_Backsplash_{kitch_idx:02d}',
            'z_base_0': 0.0,
            'z_base_1': round(c_h - c_t, 1),
            'z_top_0': round(c_h - c_t, 1),
            'z_top_1': round(c_h, 1),
            'z_bs_0': round(c_h, 1),
            'z_bs_1': round(c_h + bs_h, 1),
            'counter_depth_mm': c_depth,
            'base_depth_mm': b_depth,
            'counter_thickness_mm': c_t,
            'base_rings': [_ring_dict(p) for p in _polys(base_geom) if p.area >= 1.0e4],
            'counter_rings': [_ring_dict(p) for p in _polys(top_geom) if p.area >= 1.0e4],
            'backsplash_rings': [_ring_dict(p) for p in _polys(bs_geom) if p.area >= 2.0e3],
            '_footprint_poly': top_geom.buffer(wall_off + 2.0, join_style=2),
        })
    report['kitchen_platforms'] = [
        {'id': k['id'], 'room': k['room'], 'label': k['label'], 'shape': k['shape'],
         'height_mm': c_h, 'counter_depth_mm': c_depth, 'base_depth_mm': b_depth}
        for k in out
    ]
    if not out:
        report.setdefault('assumptions', []).append(
            'No room had an explicit KITCHEN CAD label or kitchen fixture block; '
            'set CONFIG["room_type_overrides"] to assign a kitchen room if needed.'
        )
    return out


# ════════════════════════════════════════════════════════════════════════════════════
#  WALL PANELS  (dry rooms: 1220 mm sheets, 3 mm joints, skirting top -> ceiling, 12 mm)
# ════════════════════════════════════════════════════════════════════════════════════
PANEL_ON = ('wall', 'window', 'vent', 'door', 'passage')


def _zprofile(reg, u0, u1, zb, Z):
    """Union of the z-intervals covered by region `reg` within u0..u1 -> shapely geometry in a unit strip."""
    if reg.is_empty:
        return Polygon()
    parts = _polys(reg.intersection(box(u0, zb, u1, Z)))
    return unary_union([box(0, p.bounds[1], 1, p.bounds[3]) for p in parts if p.bounds[3] - p.bounds[1] > 1.0]) if parts else Polygon()


def _panels(rooms, opening_by_id, spec, report) -> List[dict]:
    W, g, T = spec.get('panel_w', 1220.0), spec.get('panel_joint', 3.0), spec.get('panel_t', 12.0)
    Z, zb = spec['wall_h'], spec['skirt_h']
    out, per_room = [], {}
    for rm in rooms:
        if not rm.get('panelled'):
            continue
        edges = rm['edges']
        n = len(edges)
        # 1. raw panel region of every edge in (u along the edge, z).
        # Note: leave the 2.1-3.0 m lintel zone above doors and windows open so blue lintel beams remain visible!
        regs = []
        for e in edges:
            if e['L'] < 30.0:
                regs.append(Polygon())
                continue
            region = []
            for s0, s1, typ, oid in e['segs']:
                o = opening_by_id.get(oid)
                if typ == 'wall':
                    region.append(box(s0, zb, s1, Z))
                elif typ in ('window', 'vent'):
                    sill = o.sill if o else _elevations(typ, spec)[0]
                    if sill > zb + 1.0:
                        region.append(box(s0, zb, s1, sill))
            regs.append(unary_union(region) if region else Polygon())
        start = min(range(n), key=lambda k: (round(edges[k]['a'][1]), round(edges[k]['a'][0])))
        stats = {'sheets': 0, 'full': 0, 'cut': 0, 'walls_panelled': 0, 'area_m2': 0.0, 'layouts': {}}
        # 2. corners: inside corner -> butt against the previous wall's panels; outside corner -> flush at wall corner (no overhang)
        for wi in range(n):
            ei = (start + wi) % n
            e, pi_, ni_ = edges[ei], (ei - 1) % n, (ei + 1) % n
            prev, nxt = edges[pi_], edges[ni_]
            reg = regs[ei]
            if reg.is_empty or e['L'] < 30.0:
                continue
            d, dp = np.array(e['d']), np.array(prev['d'])
            cross = dp[0] * d[1] - dp[1] * d[0]
            prof_prev = _zprofile(regs[pi_], prev['L'] - 1.0, prev['L'], zb, Z)
            u_start = 0.0
            if prev['L'] < 30.0:
                reg = reg.difference(box(0.0, zb, g, Z))
                u_start = g
            elif cross > 1e-6 and not prof_prev.is_empty:
                reg = reg.difference(box(0.0, zb, T + g, Z))
                u_start = T + g
            if nxt['L'] < 30.0:
                reg = reg.difference(box(max(u_start, e['L'] - g), zb, e['L'], Z))
            reg = reg.buffer(0)
            if reg.is_empty:
                continue
            wall_name = f"Wall{wi + 1:02d}"
            cols, how = _columns(e['L'] - u_start, W, g, spec['min_cut'])
            stats['layouts'][wall_name] = f"L={e['L']:.0f} mm, {how}"
            stats['walls_panelled'] += 1
            for c, (u0, ww) in enumerate(cols):
                cell = box(u_start + u0, zb, u_start + u0 + ww, Z)
                parts = [q for p in _polys(cell.intersection(reg)) for q in _split_holes(p) if q.area >= 400.0]
                for k, q in enumerate(parts):
                    q = orient(q.simplify(0.05, preserve_topology=True), 1.0)
                    minx, minz, maxx, maxz = q.bounds
                    full = abs(maxx - minx - W) < 0.05 and abs(q.area - W * (Z - zb)) < 1.0
                    out.append({
                        'name': f"{rm['code']}_{wall_name}_P{c + 1:02d}" + (chr(97 + k) if len(parts) > 1 else ''),
                        'room': rm['name'], 'wall': wall_name, 'col': c + 1,
                        'origin': [round(e['a'][0], 3), round(e['a'][1], 3)], 'dir': [round(d[0], 9), round(d[1], 9)],
                        'u0': round(minx, 3), 'z0': round(minz, 3),
                        'poly': [[round(x - minx, 3), round(z - minz, 3)] for x, z in list(q.exterior.coords)[:-1]],
                        'full': full, 'w': round(maxx - minx, 1), 'h': round(maxz - minz, 1)})
                    stats['sheets'] += 1
                    stats['full' if full else 'cut'] += 1
                    stats['area_m2'] += q.area / 1e6
        stats['area_m2'] = round(stats['area_m2'], 2)
        per_room[rm['name']] = dict(stats, label=rm['label'])
    report['panels'] = {'sheet_mm': f"{W} W x full height x {T} T", 'joint_mm': g,
                        'z_mm': f"{zb} (top of skirting) - {Z} (ceiling)", 'per_room': per_room,
                        'rooms_without_panels': sorted(f"{rm['name']} ({rm['label']})" for rm in rooms if not rm.get('panelled'))}
    return out



def _ring_dict(p: Polygon) -> dict:
    p = orient(p.simplify(0.3, preserve_topology=True), 1.0)
    return {
        'outer': [[round(x, 1), round(y, 1)] for x, y in list(p.exterior.coords)[:-1]],
        'holes': [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in p.interiors],
    }


def _recessed_ceilings(rooms, spec, report) -> List[dict]:
    """Low-profile architectural recessed ceiling (tray cavity set upward into the ceiling slab
    + perimeter drop soffit + indirect LED cove channel + recessed downlights) in bedrooms and halls only."""
    wall_gap = spec.get('recess_wall_gap', 15.0)
    border_nom = spec.get('recess_border_w', 450.0)
    lip_w = spec.get('recess_lip_w', 60.0)
    drop_h = spec.get('recess_drop_h', 50.0)
    recess_d = spec.get('recess_depth', 120.0)
    wall_h = spec['wall_h']
    out = []
    for rm in rooms:
        if not rm.get('recessed_ceiling'):
            continue
        poly = rm['poly']
        border_w = min(border_nom, max(240.0, rm['min_dim'] * 0.18))
        outer_soffit = poly.buffer(-wall_gap, join_style=2, mitre_limit=4.0)
        cavity_raw = poly.buffer(-border_w, join_style=2, mitre_limit=4.0)
        if hasattr(cavity_raw, 'interiors') or hasattr(cavity_raw, 'geoms'):
            bridged = []
            for p in _polys(cavity_raw):
                for h in list(p.interiors):
                    hc = Polygon(h).centroid
                    minx, miny, maxx, maxy = p.bounds
                    p = p.difference(LineString([(hc.x, miny - 10.0), (hc.x, maxy + 10.0)]).buffer(25.0, join_style=2))
                bridged.extend(_polys(p))
            cavity_polys = [p for p in bridged if p.area >= 0.6e6]
        else:
            cavity_polys = [p for p in _polys(cavity_raw) if p.area >= 0.6e6]
        if not cavity_polys:
            border_w = max(180.0, rm['min_dim'] * 0.14)
            cavity_raw = poly.buffer(-border_w, join_style=2, mitre_limit=4.0)
            cavity_polys = [p for p in _polys(cavity_raw) if not p.interiors and p.area >= 0.3e6]
        if not cavity_polys or outer_soffit.is_empty:
            continue
        cavity_union = unary_union(cavity_polys)
        soffit_geom = outer_soffit.difference(cavity_union)
        inner_lip = cavity_union.buffer(-lip_w, join_style=2, mitre_limit=4.0)
        lip_geom = cavity_union.difference(inner_lip) if not inner_lip.is_empty else Polygon()
        cove_led_geom = (cavity_union.buffer(-10.0, join_style=2, mitre_limit=4.0)
                         .difference(inner_lip.buffer(14.0, join_style=2, mitre_limit=4.0))) if not inner_lip.is_empty else Polygon()
        collar_geom = cavity_union.buffer(25.0, join_style=2, mitre_limit=4.0).difference(cavity_union)

        # Architectural recessed downlight fixtures (perimeter soffit + upper recessed ceiling plane)
        fixtures = []
        soffit_safe = soffit_geom.buffer(-75.0, join_style=2)
        mid_track = poly.buffer(-0.5 * (wall_gap + border_w), join_style=2, mitre_limit=4.0)
        for mp in _polys(mid_track):
            coords = list(mp.exterior.coords)
            for p0, p1 in zip(coords, coords[1:]):
                seg_l = math.dist(p0, p1)
                if seg_l < 900.0:
                    continue
                n_pts = 1 if seg_l < 2200.0 else max(2, min(4, int(round(seg_l / 1800.0))))
                for i in range(n_pts):
                    t = (i + 0.5) / n_pts
                    px = p0[0] + (p1[0] - p0[0]) * t
                    py = p0[1] + (p1[1] - p0[1]) * t
                    if not soffit_safe.is_empty and soffit_safe.contains(Point(px, py)):
                        if all(math.hypot(px - f['x'], py - f['y']) >= 600.0 for f in fixtures):
                            fixtures.append({'x': round(px, 1), 'y': round(py, 1),
                                             'z': round(wall_h - drop_h, 1), 'mount': 'soffit'})
        for cp in cavity_polys:
            cav_safe = cp.buffer(-max(250.0, lip_w + 150.0), join_style=2)
            if cav_safe.is_empty:
                cav_safe = cp.buffer(-80.0, join_style=2)
            if cav_safe.is_empty:
                continue
            minx, miny, maxx, maxy = cav_safe.bounds
            wx, wy = maxx - minx, maxy - miny
            nx = max(1, min(3, int(round(wx / 2200.0))))
            ny = max(1, min(3, int(round(wy / 2200.0))))
            for ix in range(nx):
                for iy in range(ny):
                    px = minx + (ix + 0.5) * wx / nx
                    py = miny + (iy + 0.5) * wy / ny
                    if cav_safe.contains(Point(px, py)):
                        fixtures.append({'x': round(px, 1), 'y': round(py, 1),
                                         'z': round(wall_h + recess_d, 1), 'mount': 'cavity'})

        out.append({
            'room': rm['name'],
            'label': rm['label'],
            'use': rm['use'],
            'z_soffit': round(wall_h - drop_h, 1),
            'z_wall_top': round(wall_h, 1),
            'z_cavity': round(wall_h + recess_d, 1),
            'z_slab_top': round(wall_h + spec['slab_t'], 1),
            'border_w': round(border_w, 1),
            'cavity_rings': [_ring_dict(p) for p in cavity_polys],
            'collar_rings': [_ring_dict(p) for p in _polys(collar_geom) if p.area >= 1.0e4],
            'soffit_rings': [_ring_dict(p) for p in _polys(soffit_geom) if p.area >= 2.0e4],
            'lip_rings': [_ring_dict(p) for p in _polys(lip_geom) if p.area >= 1.0e4],
            'cove_led_rings': [_ring_dict(p) for p in _polys(cove_led_geom) if p.area >= 5.0e3],
            'fixtures': fixtures,
            '_cavity_poly': cavity_union,
        })
    report['recessed_ceilings'] = {
        'rooms': [f"{r['room']} ({r['label']})" for r in out],
        'excluded_rooms': [f"{rm['name']} ({rm['label']})" for rm in rooms if not rm.get('recessed_ceiling')],
        'recess_depth_mm': recess_d,
        'drop_soffit_mm': drop_h,
        'total_downlights': sum(len(r['fixtures']) for r in out),
    }
    return out


def _ceiling_rings(foot, recessed_ceilings=None) -> List[dict]:
    cavities = unary_union([r['_cavity_poly'] for r in (recessed_ceilings or []) if r.get('_cavity_poly') is not None])
    for r in (recessed_ceilings or []):
        r.pop('_cavity_poly', None)
    out = []
    for p in _polys(foot):
        ext = Polygon(p.exterior.coords).simplify(0.5, preserve_topology=True)
        if cavities and not cavities.is_empty:
            ext = ext.difference(cavities)
        for q in _polys(ext):
            q = orient(q.simplify(0.5, preserve_topology=True), 1.0)
            out.append({'outer': [[round(x, 1), round(y, 1)] for x, y in list(q.exterior.coords)[:-1]],
                        'holes': [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in q.interiors]})
    return out


def _floor_rings(foot) -> List[dict]:
    out = []
    for p in _polys(foot):
        p = orient(p.simplify(0.5, preserve_topology=True), 1.0)
        out.append({'outer': [[round(x, 1), round(y, 1)] for x, y in list(p.exterior.coords)[:-1]],
                    'holes': [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in p.interiors]})
    return out


# ════════════════════════════════════════════════════════════════════════════════════
#  SKIRTING  (76.2 mm x 15 mm, dry rooms only, stops at door / passage jambs)
# ════════════════════════════════════════════════════════════════════════════════════
SKIRT_ON = ('wall', 'window', 'vent')


def _skirting(rooms, spec, report, kitchens=None):
    t = spec['skirt_t']
    kitch_by_room = {}
    for k in (kitchens or []):
        fp = k.pop('_footprint_poly', None)
        if fp is not None and not fp.is_empty:
            kitch_by_room.setdefault(k['room'], []).append(fp)

    out = []
    room_skirting = []
    checked_doors = set()
    for rm in rooms:
        if rm['type'] in ('washroom', 'external', 'shaft'):
            continue
        poly = rm['poly']
        inner = poly.buffer(-t, join_style=2, mitre_limit=10.0)
        ribbon = poly.difference(inner)
        strips, corner_pts = [], []
        n = len(rm['edges'])
        for ei, e in enumerate(rm['edges']):
            a, d = np.array(e['a']), np.array(e['d'])
            nin = np.array([-d[1], d[0]])
            for s0, s1, typ, oid in e['segs']:
                if typ in ('door', 'passage'):
                    checked_doors.add(oid)
                if typ not in SKIRT_ON:
                    continue
                p0, p1 = a + d * s0, a + d * s1
                strips.append(Polygon([p0, p1, p1 + nin * (t * 3), p0 + nin * (t * 3)]))
            # corner square only where both edges meeting at the end vertex carry skirting
            nxt = rm['edges'][(ei + 1) % n]
            if e['segs'] and nxt['segs'] and e['segs'][-1][2] in SKIRT_ON and nxt['segs'][0][2] in SKIRT_ON:
                corner_pts.append(np.array(e['b']))
        zone = unary_union(strips + [box(c[0] - 3 * t, c[1] - 3 * t, c[0] + 3 * t, c[1] + 3 * t) for c in corner_pts])
        for h in rm['holes']:                                  # columns standing inside the room
            hp = Polygon(h)
            zone = zone.union(hp.buffer(t * 3, join_style=2))
        skirt = ribbon.intersection(zone)
        if rm['name'] in kitch_by_room:
            skirt = skirt.difference(unary_union(kitch_by_room[rm['name']]))
        rm_runs = []
        for p_raw in _polys(skirt):
            g = p_raw.simplify(0.2, preserve_topology=True)
            if g.area < 30.0 * t:            # shorter than 30 mm
                continue
            length = g.area / t
            run_item = {'room': rm['name'], 'ring': [[round(x, 2), round(y, 2)] for x, y in list(orient(g, 1.0).exterior.coords)[:-1]],
                        'holes': [[[round(x, 2), round(y, 2)] for x, y in list(h.coords)[:-1]] for h in g.interiors],
                        'length_mm': round(length, 1),
                        'mat': rm.get('skirt_mat', 'MAT_Skirting_Common'),
                        'skirt_obj': rm.get('skirt_obj', f"Skirting_{rm['name']}")}
            out.append(run_item)
            rm_runs.append({'outer': run_item['ring'], 'holes': run_item['holes'], 'length_mm': run_item['length_mm']})
        if rm_runs and rm.get('skirt_obj'):
            room_skirting.append({
                'name': rm['skirt_obj'],
                'room': rm['name'],
                'label': rm['label'],
                'use': rm['use'],
                'category': rm.get('floor_category', 'common'),
                'mat': rm.get('skirt_mat', 'MAT_Skirting_Common'),
                'length_mm': round(sum(r['length_mm'] for r in rm_runs), 1),
                'runs': rm_runs,
            })
    out.sort(key=lambda s: (s['room'], -s['length_mm']))
    for k, s in enumerate(out):
        s['name'] = f"Skirting_{k + 1:02d}"
    report['skirting'] = {'segments': len(out), 'room_objects': len(room_skirting),
                          'height_mm': spec['skirt_h'], 'thickness_mm': spec['skirt_t'],
                          'total_length_m': round(sum(s['length_mm'] for s in out) / 1000, 2),
                          'door_and_passage_openings_checked': len(checked_doors),
                          'rooms_with_skirting': sorted({s['room'] for s in out}),
                          'rooms_excluded': sorted(rm['name'] + f" ({rm['type']})" for rm in rooms
                                                   if rm['type'] in ('washroom', 'external', 'shaft'))}
    return out, room_skirting


# ════════════════════════════════════════════════════════════════════════════════════
#  WASHROOM TILES  (individual 914.4 x 609.6 mm tiles, 2.5 mm joints, cut tiles, cut-outs)
# ════════════════════════════════════════════════════════════════════════════════════
def _columns(E, W, g, min_cut):
    """Horizontal layout along an effective run of length E -> [(u0, width)]."""
    if E <= 0:
        return [], 'none'
    n_full = int(math.floor((E + g) / (W + g) + 1e-9))
    if n_full == 0:
        return [(0.0, E)], 'single cut'
    used = n_full * W + (n_full - 1) * g
    rem = E - used
    cols = [(k * (W + g), W) for k in range(n_full)]
    if rem <= g + 0.5:
        return cols, 'full tiles only'
    cut = rem - g
    if cut >= min_cut:
        return cols + [(used + g, cut)], 'full tiles + end cut'
    n_mid = n_full - 1
    c = (E - n_mid * W - (n_mid + 1) * g) / 2.0
    cols = [(0.0, c)] + [(c + g + k * (W + g), W) for k in range(n_mid)] + [(E - c, c)]
    return cols, 'balanced: equal cuts at both ends'


def _rows(Z, Hh, g):
    n_full = int(math.floor((Z + g) / (Hh + g) + 1e-9))
    rows = [(k * (Hh + g), Hh) for k in range(n_full)]
    used = n_full * Hh + (n_full - 1) * g
    if Z - used > g + 0.5:
        rows.append((used + g, Z - used - g))
    return rows


def _split_holes(p: Polygon) -> List[Polygon]:
    if not p.interiors:
        return [p]
    c = Polygon(p.interiors[0]).centroid
    minx, miny, maxx, maxy = p.bounds
    parts = shp_split(p, LineString([(c.x, miny - 1), (c.x, maxy + 1)]))
    out = []
    for q in _polys(parts):
        out += _split_holes(q)
    return out


def _tiles(rooms, spec, report) -> List[dict]:
    W, Hh, T, g, off, Z = spec['tile_w'], spec['tile_h'], spec['tile_t'], spec['grout'], spec['tile_gap'], spec['wall_h']
    rows = _rows(Z, Hh, g)
    tiles = []
    per_room = {}
    for rm in rooms:
        if rm['type'] != 'washroom':
            continue
        code, edges = rm['code'], rm['edges']
        n = len(edges)
        # wall numbering starts at the edge whose start point is lowest-left -> deterministic
        start = min(range(n), key=lambda k: (round(edges[k]['a'][1]), round(edges[k]['a'][0])))
        stats = {'tiles': 0, 'full': 0, 'cut': 0, 'cut_sizes_mm': {}, 'slivers_lt_50mm': 0,
                 'walls_tiled': 0, 'skipped_edges': [], 'layouts': {}}
        for wi in range(n):
            ei = (start + wi) % n
            e = edges[ei]
            prev = edges[(ei - 1) % n]
            nxt = edges[(ei + 1) % n]
            prev2 = edges[(ei - 2) % n]
            d, dp = np.array(e['d']), np.array(prev['d'])
            convex = (dp[0] * d[1] - dp[1] * d[0]) > 1e-6      # left turn on CCW ring = inside corner of walls
            prev_tiled = any(s[2] in ('wall', 'window', 'vent', 'door', 'passage') for s in prev['segs'][-1:])
            L = e['L']
            wall_name = f"Wall{wi + 1:02d}"
            if L < 30.0 or (nxt['L'] < 30.0 and L < 100.0):
                stats['skipped_edges'].append(f"{wall_name} (L={L:.0f} mm)")
                continue
            if prev['L'] < 30.0:
                u_start = (prev2['L'] + off + T + g) if prev2['L'] < 100.0 else (off + T + g)
            else:
                u_start = (off + T + g) if (convex and prev_tiled) else 0.0
            u_end = L - off                                    # movement gap against the abutting wall
            region = []
            for s0, s1, typ, oid in e['segs']:
                if typ == 'wall':
                    region.append(box(s0, 0, s1, Z))
                elif typ in ('window', 'vent'):
                    o_sill = spec['win_sill'] if typ == 'window' else spec['vent_sill']
                    o_head = o_sill + (spec['win_h'] if typ == 'window' else spec['vent_h'])
                    region += [box(s0, 0, s1, o_sill), box(s0, o_head, s1, Z)]
                elif typ in ('door', 'passage'):
                    region.append(box(s0, spec['door_head'], s1, Z))
            reg = unary_union(region).intersection(box(u_start, 0, u_end, Z)) if region else Polygon()
            if reg.is_empty or u_end - u_start < 30.0:
                stats['skipped_edges'].append(f"{wall_name} (L={L:.0f} mm)")
                continue
            cols, how = _columns(u_end - u_start, W, g, spec['min_cut'])
            stats['layouts'][wall_name] = f"L={L:.0f} mm, {how}"
            stats['walls_tiled'] += 1
            for r, (z0, hh) in enumerate(rows):
                for c, (u0, ww) in enumerate(cols):
                    u0a = u_start + u0
                    cell = box(u0a, z0, u0a + ww, z0 + hh)
                    piece = cell.intersection(reg)
                    parts = [q for p in _polys(piece) for q in _split_holes(p) if q.area >= 400.0]
                    for pi, q in enumerate(parts):
                        q = orient(q.simplify(0.05, preserve_topology=True), 1.0)
                        minx, minz, maxx, maxz = q.bounds
                        full = (abs(q.area - W * Hh) < 1.0 and abs(maxx - minx - W) < 0.05 and abs(maxz - minz - Hh) < 0.05)
                        mrr = q.minimum_rotated_rectangle
                        mc = list(mrr.exterior.coords)[:4]
                        minw = min(math.dist(mc[0], mc[1]), math.dist(mc[1], mc[2]))
                        name = f"{code}_{wall_name}_R{r + 1:02d}_C{c + 1:02d}" + (chr(97 + pi) if len(parts) > 1 else '')
                        tiles.append({
                            'name': name, 'room': rm['name'], 'wall': wall_name, 'row': r + 1, 'col': c + 1,
                            'origin': [round(e['a'][0], 3), round(e['a'][1], 3)], 'dir': [round(d[0], 9), round(d[1], 9)],
                            'u0': round(minx, 3), 'z0': round(minz, 3),
                            'poly': [[round(x - minx, 3), round(z - minz, 3)] for x, z in list(q.exterior.coords)[:-1]],
                            'full': full, 'w': round(maxx - minx, 1), 'h': round(maxz - minz, 1),
                            'rect': len(q.exterior.coords) == 5 and abs(q.area - (maxx - minx) * (maxz - minz)) < 1.0,
                        })
                        stats['tiles'] += 1
                        if full:
                            stats['full'] += 1
                        else:
                            stats['cut'] += 1
                            key = f"{maxx - minx:.1f} x {maxz - minz:.1f}" + ('' if tiles[-1]['rect'] else ' (notched)')
                            stats['cut_sizes_mm'][key] = stats['cut_sizes_mm'].get(key, 0) + 1
                            if minw < 50.0:
                                stats['slivers_lt_50mm'] += 1
        per_room[rm['name']] = stats
    report['tiles'] = {'nominal_mm': f"{W} W x {Hh} H x {T} T", 'grout_mm': g,
                       'rows': [f"z {z0:.1f}-{z0 + h:.1f} ({'full' if abs(h - Hh) < 0.01 else 'cut %.1f' % h})" for z0, h in rows],
                       'per_washroom': per_room}
    return tiles
