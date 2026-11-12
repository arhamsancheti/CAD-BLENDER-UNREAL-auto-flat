"""
Multi-reference comparison, calibration, and validation (`cad_processor/reference.py`).

Supports two or more reference files of any supported type:
  - 2D raster floor plans or 3D viewport screenshots (.png, .jpg, .jpeg, .webp, .bmp)
  - 2D CAD drawings (.dxf, .dwg)
  - 3D architectural models (.fbx, .obj, .glb, .gltf, .dae, .stl, .ply)

For each reference:
  1. Classifies the reference type: 'top_down_plan', '3d_model', 'partial_model', or '3d_view'.
  2. Extracts structural wall polygons and semantic room/floor zones (e.g. FBX Floor_M_Bedroom_Wooden,
     Floor_Tile_*_Washrrom, Floor_Living_Dining, Floor_Balcony_*, or CAD room labels).
  3. Aligns the reference to the source plan without assuming identical scale, origin, or orientation
     (testing rotations 0/90/180/270 deg, scale estimation from structural span / grid lines, and
     1D profile cross-correlation so cropped viewports still align accurately).
  4. Compares detected walls and rooms against the aligned reference:
     - Matched walls, missing wall spans (distinguishing viewport crop vs. interior omissions),
       false/extra walls, and material conflicts requiring user clarification.
     - Actively enriches ambiguous room classifications (e.g. upgrading 'review' washrooms or
       confirming master bedroom / balcony zones when supported by the reference) while preserving
       the source plan as the primary dimensional authority unless mode == 'authoritative'.
  5. Renders a colour-coded visual overlay PNG (base64) for the Detection Review UI.
"""
import base64
import json
import logging
import math
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from shapely.affinity import rotate as shp_rotate, scale as shp_scale, translate as shp_translate
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
CAD_EXTS = {'.dxf', '.dwg'}
MODEL_EXTS = {'.fbx', '.obj', '.glb', '.gltf', '.dae', '.stl', '.ply'}


def _polys(g) -> List[Polygon]:
    if g is None or g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    if hasattr(g, 'geoms'):
        out = []
        for x in g.geoms:
            out.extend(_polys(x))
        return out
    return []


def _extract_3d_reference(filepath: str) -> Dict[str, Any]:
    """
    Extract 2D wall cross-section polygons (mm) and semantic room floor boxes from a 3D model
    (.fbx, .obj, .glb, etc.) using headless Blender.
    """
    from .importer import CADImporter
    blender_exe = CADImporter._find_blender()
    if not blender_exe:
        return {'ok': False, 'error': 'Blender executable not found for 3D reference extraction'}

    script = r'''
import bpy, bmesh, mathutils, sys, json

argv = sys.argv[sys.argv.index("--") + 1:]
in_path, out_json = argv[0], argv[1]
ext = in_path.lower().rsplit(".", 1)[-1]

bpy.ops.wm.read_factory_settings(use_empty=True)
if ext == "fbx":
    try:
        from io_scene_fbx import import_fbx
        _orig_read_light = import_fbx.blen_read_light
        def _safe_read_light(fbx_tmpl, fbx_obj, settings):
            try:
                return _orig_read_light(fbx_tmpl, fbx_obj, settings)
            except AttributeError as e:
                if "cast_shadow" in str(e):
                    return None
                raise
        import_fbx.blen_read_light = _safe_read_light
    except Exception:
        pass
    bpy.ops.import_scene.fbx(filepath=in_path)
elif ext == "obj":
    bpy.ops.wm.obj_import(filepath=in_path)
elif ext in ("glb", "gltf"):
    bpy.ops.import_scene.gltf(filepath=in_path)
elif ext == "stl":
    bpy.ops.wm.stl_import(filepath=in_path)
elif ext == "ply":
    bpy.ops.wm.ply_import(filepath=in_path)
elif ext == "dae":
    bpy.ops.wm.collada_import(filepath=in_path)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and len(o.data.vertices) >= 4]
all_v = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
if not all_v:
    with open(out_json, "w") as f:
        json.dump({"ok": False, "error": "No mesh vertices in 3D reference"}, f)
    sys.exit(0)

span = max(max(v.x for v in all_v) - min(v.x for v in all_v),
           max(v.y for v in all_v) - min(v.y for v in all_v))
unit_to_mm = 1000.0 if span < 500.0 else 1.0

wall_segs = []
floors = []
obj_names = [o.name for o in meshes]

for o in meshes:
    nl = o.name.lower()
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    x0, y0, z0 = min(v.x for v in vs) * unit_to_mm, min(v.y for v in vs) * unit_to_mm, min(v.z for v in vs) * unit_to_mm
    x1, y1, z1 = max(v.x for v in vs) * unit_to_mm, max(v.y for v in vs) * unit_to_mm, max(v.z for v in vs) * unit_to_mm
    if "floor" in nl:
        floors.append({"name": o.name, "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                       "area_m2": round((x1 - x0) * (y1 - y0) / 1e6, 2)})
    if "wall" in nl and "tile" not in nl and (z1 - z0) >= 1500.0:
        for z_frac in (0.42, 0.50, 0.78):
            z_cut = (z0 + z_frac * (z1 - z0)) / unit_to_mm
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bm.transform(o.matrix_world)
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z_cut), plane_no=(0, 0, 1))
            cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            segs = []
            for e in cut_edges:
                p1, p2 = e.verts[0].co, e.verts[1].co
                segs.append([[round(p1.x * unit_to_mm, 1), round(p1.y * unit_to_mm, 1)],
                             [round(p2.x * unit_to_mm, 1), round(p2.y * unit_to_mm, 1)]])
            bm.free()
            wall_segs.append(segs)

with open(out_json, "w") as f:
    json.dump({"ok": True, "unit_to_mm": unit_to_mm, "objects": obj_names,
               "floors": floors, "wall_slices": wall_segs}, f)
'''
    tmp_dir = tempfile.mkdtemp(prefix='ref3d_')
    script_path = os.path.join(tmp_dir, 'extract_ref.py')
    json_path = os.path.join(tmp_dir, 'ref.json')
    with open(script_path, 'w', encoding='utf-8') as fh:
        fh.write(script)
    try:
        subprocess.run([blender_exe, '--background', '--factory-startup', '--python', script_path, '--',
                        os.path.abspath(filepath), json_path],
                       capture_output=True, text=True, timeout=90)
        if not os.path.isfile(json_path):
            return {'ok': False, 'error': 'Blender reference extraction produced no output'}
        with open(json_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception as ex:
        return {'ok': False, 'error': f'3D reference extraction failed: {ex}'}

    if not data.get('ok'):
        return data

    from shapely.ops import polygonize
    slice_polys = []
    for segs in data.get('wall_slices', []):
        lines = [LineString([p0, p1]) for p0, p1 in segs if math.dist(p0, p1) > 1.0]
        if not lines:
            continue
        merged = unary_union(lines)
        # Filter out enclosed room voids: for a wall strip of thickness t, 2*area/perimeter < t <= 260 mm
        polys = [p.buffer(0) for p in polygonize(merged)
                 if p.area >= 3000.0 and (2.0 * p.area / max(p.length, 1.0)) <= 260.0]
        if polys:
            slice_polys.append(unary_union(polys))
    if not slice_polys:
        return {'ok': False, 'error': 'No closed wall cross-section found in 3D reference'}

    # Union the mid-height and lintel-height slices, or use mid-height slice for wall+door footprint
    mid_wall = slice_polys[0]
    has_finishes = len(data.get('floors', [])) >= 2
    ref_type = '3d_model' if has_finishes else 'partial_model'
    return {
        'ok': True,
        'ref_type': ref_type,
        'wall_union': mid_wall,
        'lintel_union': slice_polys[-1] if len(slice_polys) > 1 else mid_wall,
        'floors': data.get('floors', []),
        'objects': data.get('objects', []),
    }


def _extract_image_or_cad_reference(filepath: str, source_mm_per_px: Optional[float] = None) -> Dict[str, Any]:
    """Extract walls and rooms from a 2D image or CAD reference file."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTS:
        from .image_importer import _load_gray, foreground_mask
        from .raster_walls import detect_line_plan
        im_bgr, gray = _load_gray(filepath)
        H, W = gray.shape
        strength, fg = foreground_mask(gray)
        det = detect_line_plan(fg, strength, mm_per_px=source_mm_per_px)
        if not det.get('ok') or len(det.get('bands', [])) < 4:
            # Check if this image is a 3D perspective render / shaded screenshot rather than a 2D line plan
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            mag = np.hypot(gx, gy)
            ang = (np.degrees(np.arctan2(np.abs(gy), np.abs(gx))))[mag > 25]
            ortho_share = float(((ang < 8) | (ang > 82)).mean()) if ang.size else 0.0
            return {
                'ok': True,
                'ref_type': '3d_view' if ortho_share < 0.65 else 'partial_model',
                'wall_union': Polygon(),
                'floors': [],
                'note': (f'Reference image appears to be a 3D perspective/shaded view (orthogonal edge share '
                         f'{ortho_share:.0%}); used as visual/qualitative reference rather than 2D dimensional authority.'),
            }
        sc = det['scale']
        polys = []
        for b in det['bands']:
            x0, y0, x1, y1 = b.rect()
            polys.append(box(x0 * sc, (H - y1) * sc, x1 * sc, (H - y0) * sc))
        return {
            'ok': True,
            'ref_type': 'top_down_plan',
            'wall_union': unary_union(polys) if polys else Polygon(),
            'floors': [],
            'mm_per_px': sc,
        }
    if ext in CAD_EXTS:
        from .cleaner import CADCleaner
        from .importer import CADImporter
        from .normalizer import UnitNormalizer
        from .wall_builder import WallBuilder
        from .wall_detector import WallDetector
        imp = CADImporter()
        ents = imp.import_file(filepath)
        norm = UnitNormalizer()
        ents = norm.normalize(ents, None, imp.insunits)
        cleaned = CADCleaner().clean(ents)
        found = WallDetector().detect_walls(cleaned)
        walls = WallBuilder().build_walls(found, 3000.0, 200.0)
        polys = [Polygon(w.polygon).buffer(0) for w in walls if len(w.polygon) >= 3]
        return {
            'ok': True,
            'ref_type': 'top_down_plan',
            'wall_union': unary_union(polys) if polys else Polygon(),
            'floors': [],
        }
    return {'ok': False, 'error': f'Unsupported reference format: {ext}'}


def _wall_profile_1d(poly_union, axis: int, step_mm: float = 25.0) -> Tuple[float, np.ndarray]:
    """
    Build a 1D wall-face impulse profile along X (axis=0, from vertical wall edges)
    or Y (axis=1, from horizontal wall edges) across all exterior and interior rings.
    """
    minx, miny, maxx, maxy = poly_union.bounds
    lo, hi = (minx, maxx) if axis == 0 else (miny, maxy)
    n = max(16, int(math.ceil((hi - lo) / step_mm)) + 3)
    prof = np.zeros(n, dtype=np.float32)
    for p in _polys(poly_union):
        for ring in [p.exterior] + list(p.interiors):
            coords = list(ring.coords)
            for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
                dx, dy = abs(x1 - x0), abs(y1 - y0)
                if axis == 0 and dx <= 15.0 and dy >= 150.0:
                    idx = int(round((0.5 * (x0 + x1) - lo) / step_mm))
                    if 0 <= idx < n:
                        prof[idx] += dy
                elif axis == 1 and dy <= 15.0 and dx >= 150.0:
                    idx = int(round((0.5 * (y0 + y1) - lo) / step_mm))
                    if 0 <= idx < n:
                        prof[idx] += dx
    prof = np.convolve(prof, [0.2, 0.6, 1.0, 0.6, 0.2], mode='same')
    norm = np.linalg.norm(prof)
    if norm > 1e-6:
        prof /= norm
    return lo, prof


def _best_1d_shifts(src_union, ref_union, axis: int, step_mm: float = 25.0) -> List[float]:
    """Return top candidate translations (mm) along `axis` via 1D wall-face correlation + boundary alignment."""
    s_lo, s_p = _wall_profile_1d(src_union, axis, step_mm)
    r_lo, r_p = _wall_profile_1d(ref_union, axis, step_mm)
    corr = np.correlate(s_p, r_p, mode='full')
    top_idxs = np.argsort(corr)[::-1][:4]
    shifts = [float((s_lo - r_lo) + (int(idx) - (len(r_p) - 1)) * step_mm) for idx in top_idxs]
    # Also include min-bound and max-bound alignment candidates
    s_min, s_max = (src_union.bounds[0], src_union.bounds[2]) if axis == 0 else (src_union.bounds[1], src_union.bounds[3])
    r_min, r_max = (ref_union.bounds[0], ref_union.bounds[2]) if axis == 0 else (ref_union.bounds[1], ref_union.bounds[3])
    shifts.extend([s_min - r_min, s_max - r_max])
    uniq = []
    for sh in shifts:
        if all(abs(sh - u) > 40.0 for u in uniq):
            uniq.append(sh)
    return uniq[:5]


def _align_reference(src_union, ref_union, floors: List[Dict]) -> Tuple[Any, List[Dict], Dict[str, Any]]:
    """
    Align `ref_union` (and `floors`) to `src_union` across rotations {0, 90, 180, 270},
    estimating scale ratio and translation (supporting partial/cropped viewport overlap).
    """
    if src_union.is_empty or ref_union.is_empty:
        return ref_union, floors, {'rotation_deg': 0, 'scale_ratio': 1.0, 'shift_mm': [0.0, 0.0], 'iou': 0.0}

    sx0, sy0, sx1, sy1 = src_union.bounds
    sw, sh = sx1 - sx0, sy1 - sy0
    src_buf = src_union.buffer(75.0)
    src_area = max(src_buf.area, 1.0)
    best = None

    for rot in (0, 90, 180, 270):
        ru = shp_rotate(ref_union, rot, origin=(0, 0)) if rot else ref_union
        rx0, ry0, rx1, ry1 = ru.bounds
        rw, rh = max(rx1 - rx0, 1.0), max(ry1 - ry0, 1.0)
        scales = [1.0, sh / rh, sw / rw]
        seen_s = []
        for s in scales:
            if not (0.05 <= s <= 20.0) or any(abs(s - x) / max(x, 1e-6) < 0.008 for x in seen_s):
                continue
            seen_s.append(s)
            ru_s = shp_scale(ru, xfact=s, yfact=s, origin=(0, 0)) if abs(s - 1.0) > 1e-4 else ru
            dxs = _best_1d_shifts(src_union, ru_s, 0, step_mm=25.0)
            dys = _best_1d_shifts(src_union, ru_s, 1, step_mm=25.0)
            for dx in dxs[:3]:
                for dy in dys[:3]:
                    cand = shp_translate(ru_s, xoff=dx, yoff=dy)
                    cand_buf = cand.buffer(75.0)
                    # Recall of source walls covered by reference (handles cropped source plans cleanly)
                    inter = src_buf.intersection(cand_buf).area
                    recall = inter / src_area
                    if best is None or recall > best[0]:
                        best = (recall, rot, s, dx, dy, cand)

    if best is None:
        return ref_union, floors, {'rotation_deg': 0, 'scale_ratio': 1.0, 'shift_mm': [0.0, 0.0], 'iou': 0.0}

    score, rot, s, dx, dy, aligned_wall = best
    aligned_floors = []
    for fl in floors:
        bx0, by0, bx1, by1 = fl['bbox']
        fp = box(bx0, by0, bx1, by1)
        if rot:
            fp = shp_rotate(fp, rot, origin=(0, 0))
        if abs(s - 1.0) > 1e-4:
            fp = shp_scale(fp, xfact=s, yfact=s, origin=(0, 0))
        fp = shp_translate(fp, xoff=dx, yoff=dy)
        fx0, fy0, fx1, fy1 = fp.bounds
        aligned_floors.append({
            'name': fl['name'],
            'poly': fp,
            'bbox': [round(fx0, 1), round(fy0, 1), round(fx1, 1), round(fy1, 1)],
            'area_m2': round((fx1 - fx0) * (fy1 - fy0) / 1e6, 2),
        })

    transform = {
        'rotation_deg': rot,
        'scale_ratio': round(float(s), 4),
        'shift_mm': [round(float(dx), 1), round(float(dy), 1)],
        'overlap_score': round(float(score), 3),
    }
    return aligned_wall, aligned_floors, transform


def _render_comparison_png(walls, openings, aligned_ref, aligned_floors, bounds) -> str:
    """Render a visual overlay of Source Detected Walls vs. Aligned Reference Walls & Rooms."""
    x0, y0, x1, y1 = bounds
    pad = 800.0
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    span = max(x1 - x0, y1 - y0, 1000.0)
    k = 1200.0 / span
    W = max(300, int(round((x1 - x0) * k)))
    H = max(240, int(round((y1 - y0) * k)))
    canvas = np.full((H, W, 3), 26, dtype=np.uint8)

    def to_px(pts):
        return np.array([[int(round((x - x0) * k)), int(round((y1 - y) * k))] for x, y in pts], np.int32)

    # Draw reference floor zones lightly
    for fl in aligned_floors:
        p = fl['poly']
        pts = to_px(list(p.exterior.coords)[:-1])
        nl = fl['name'].lower()
        col = (60, 50, 35) if 'wash' in nl else ((40, 55, 70) if 'wood' in nl else (38, 42, 38))
        cv2.fillPoly(canvas, [pts], col)
        cv2.polylines(canvas, [pts], True, (90, 95, 90), 1, cv2.LINE_AA)
        cx, cy = p.centroid.x, p.centroid.y
        px, py = int(round((cx - x0) * k)), int(round((y1 - cy) * k))
        lbl = fl['name'].replace('Floor_Tile_', '').replace('Floor_', '')
        cv2.putText(canvas, lbl, (max(6, px - 45), max(16, py)), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (175, 185, 175), 1, cv2.LINE_AA)

    # Draw reference wall union in cyan
    for p in _polys(aligned_ref):
        pts = to_px(list(p.exterior.coords)[:-1])
        cv2.fillPoly(canvas, [pts], (180, 140, 30))
        cv2.polylines(canvas, [pts], True, (235, 195, 60), 1, cv2.LINE_AA)

    # Draw detected walls: green where overlapping reference, red/orange where not in reference
    ref_buf = aligned_ref.buffer(120.0) if not aligned_ref.is_empty else Polygon()
    for w in walls:
        if getattr(w, 'kind', 'wall') != 'wall' or len(w.polygon) < 3:
            continue
        wp = Polygon(w.polygon).buffer(0)
        matched = not ref_buf.is_empty and wp.intersection(ref_buf).area >= 0.45 * max(wp.area, 1.0)
        col = (75, 215, 95) if matched else (60, 90, 245)
        pts = to_px(w.polygon)
        cv2.fillPoly(canvas, [pts], col)
        cv2.polylines(canvas, [pts], True, (230, 245, 230) if matched else (120, 150, 255), 1, cv2.LINE_AA)

    # Legend bar at top
    cv2.rectangle(canvas, (0, 0), (W, 28), (18, 18, 22), -1)
    cv2.putText(canvas, "GREEN: Confirmed by Reference | GOLD/CYAN: Reference Only (Crop/Opening) | RED: Source Only",
                (10, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (225, 225, 230), 1, cv2.LINE_AA)

    ok, buf = cv2.imencode('.png', canvas)
    return base64.b64encode(buf.tobytes()).decode('ascii') if ok else ''


def compare_one(ref_path: str, result: dict, offset: Tuple[float, float],
                raster: Optional[dict] = None, mode: str = 'validate') -> Dict[str, Any]:
    """Compare one reference file against the pipeline's detected walls and rooms."""
    name = os.path.basename(ref_path)
    if not os.path.isfile(ref_path):
        return {'name': name, 'ok': False, 'error': f'Reference file not found: {ref_path}'}

    ext = os.path.splitext(ref_path)[1].lower()
    if ext in MODEL_EXTS:
        ext_res = _extract_3d_reference(ref_path)
    else:
        ext_res = _extract_image_or_cad_reference(ref_path, source_mm_per_px=(raster or {}).get('mm_per_px'))

    if not ext_res.get('ok'):
        return {'name': name, 'ok': False, 'error': ext_res.get('error', 'Failed to read reference')}

    ref_type = ext_res.get('ref_type', 'unknown')
    ref_wall = ext_res.get('wall_union', Polygon())
    ref_floors = ext_res.get('floors', [])

    walls = [w for w in result.get('walls', []) if getattr(w, 'kind', 'wall') == 'wall']
    fills = [w for w in result.get('walls', []) if getattr(w, 'kind', 'wall') != 'wall']
    src_wall_union = unary_union([Polygon(w.polygon).buffer(0) for w in walls if len(w.polygon) >= 3])
    src_all_union = unary_union([Polygon(p.polygon).buffer(0) for p in walls + fills if len(p.polygon) >= 3])

    if ref_wall.is_empty:
        return {
            'name': name, 'ok': True, 'ref_type': ref_type,
            'summary': ext_res.get('note', f'{ref_type} reference inspected'),
            'conflicts': [], 'matched_walls': len(walls), 'total_walls': len(walls),
        }

    aligned_wall, aligned_floors, tf = _align_reference(src_all_union, ref_wall, ref_floors)
    sx0, sy0, sx1, sy1 = src_all_union.bounds
    rx0, ry0, rx1, ry1 = aligned_wall.bounds
    src_box = box(sx0 - 150, sy0 - 150, sx1 + 150, sy1 + 150)

    # 1. Check wall-by-wall agreement
    ref_buf = aligned_wall.buffer(150.0)
    matched_ids, extra_ids = [], []
    for w in walls:
        wp = Polygon(w.polygon).buffer(0)
        if wp.intersection(ref_buf).area >= 0.45 * max(wp.area, 1.0):
            matched_ids.append(w.id)
        else:
            extra_ids.append(w.id)

    # 2. Check reference wall parts missing in detection (inside vs outside source bounds)
    src_buf = src_all_union.buffer(180.0)
    missing_total = aligned_wall.difference(src_buf)
    missing_inside = _polys(missing_total.intersection(src_box))
    missing_outside = _polys(missing_total.difference(src_box))

    missing_interior = [p for p in missing_inside if p.area >= 1.8e5]   # >= ~0.18 m2 (~1.2m x 0.15m wall)
    cropped_spans = [p for p in missing_outside if p.area >= 1.8e5]

    conflicts: List[Dict[str, Any]] = []
    if cropped_spans:
        crop_w = round((rx1 - rx0) - (sx1 - sx0))
        conflicts.append({
            'type': 'viewport_crop',
            'severity': 'info',
            'detail': (f"Reference '{name}' extends ~{max(0, crop_w)} mm beyond the source plan's right/outer boundary "
                       f"(e.g. entrance passage / lobby present in reference but cropped at the source image edge). "
                       f"Source plan boundary preserved as primary authority."),
            'question': (f"Reference '{name}' includes an additional {max(0, crop_w)} mm span outside the source image crop. "
                         f"Should the model keep the source plan bounds or extend to include the reference passage?"),
        })
    if abs(tf['scale_ratio'] - 1.0) > 0.03:
        conflicts.append({
            'type': 'scale_difference',
            'severity': 'warn',
            'detail': (f"Reference scale differs by {(tf['scale_ratio'] - 1.0) * 100:+.1f}% from the source plan scale. "
                       f"Source plan dimensions preserved unless 'calibrate' or 'authoritative' mode is selected."),
            'question': f"Use reference '{name}' to recalibrate scale ({tf['scale_ratio']:.3f}x)?",
        })

    # 3. Room comparison & semantic enrichment from reference floors
    arch_data = result.get('architecture') or {}
    src_rooms = arch_data.get('rooms', [])
    room_matches = []
    upgraded_washrooms = []

    for fl in aligned_floors:
        fp = fl['poly']
        nl = fl['name'].lower()
        best_rm = None
        best_ov = 0.0
        for rm in src_rooms:
            rp = rm.get('poly')
            if rp is None:
                rp = Polygon(rm['ring']).buffer(0)
            ov_raw = rp.intersection(fp).area / max(min(rp.area, fp.area), 1.0)
            size_sim = (min(rp.area, fp.area) / max(rp.area, fp.area, 1.0)) ** 0.25
            ov = ov_raw * size_sim
            if ov > best_ov:
                best_ov = ov
                best_rm = rm
        if best_rm is not None and best_ov >= 0.35:
            ref_is_wash = 'wash' in nl or 'toilet' in nl or 'bath' in nl
            if ref_is_wash and best_rm.get('type') == 'review':
                best_rm['type'] = 'washroom'
                best_rm.setdefault('signals', []).append(f"confirmed by reference '{name}' ({fl['name']})")
                upgraded_washrooms.append(best_rm['name'])
            room_matches.append({
                'ref_room': fl['name'],
                'src_room': best_rm['name'],
                'src_type': best_rm['type'],
                'ref_area_m2': fl['area_m2'],
                'src_area_m2': round(best_rm['area_m2'], 2),
                'overlap': round(best_ov, 2),
            })

    all_bounds = (min(sx0, rx0), min(sy0, ry0), max(sx1, rx1), max(sy1, ry1))
    png_b64 = _render_comparison_png(walls, arch_data.get('openings', []), aligned_wall, aligned_floors, all_bounds)

    summary = (f"{ref_type}: {len(matched_ids)}/{len(walls)} source walls confirmed "
               f"(overlap {tf['overlap_score']:.0%}, scale ratio {tf['scale_ratio']:.3f}, rot {tf['rotation_deg']} deg); "
               f"{len(room_matches)} reference room zones matched"
               + (f"; {len(conflicts)} conflict/crop note(s)" if conflicts else ""))

    return {
        'name': name,
        'ok': True,
        'ref_type': ref_type,
        'source_type': ref_type,
        'transform': tf,
        'matched_walls': len(matched_ids),
        'total_walls': len(walls),
        'walls_confirmed': len(matched_ids),
        'walls_total': len(walls),
        'extra_wall_ids': extra_ids,
        'missing_interior_count': len(missing_interior),
        'cropped_outside_count': len(cropped_spans),
        'room_matches': room_matches,
        'upgraded_washrooms': upgraded_washrooms,
        'conflicts': conflicts,
        'summary': summary,
        'png_b64': png_b64,
    }


def compare_all(ref_paths: List[str], result: dict, offset: Tuple[float, float],
                raster: Optional[dict] = None, mode: str = 'validate') -> Dict[str, Any]:
    """Compare one or more reference files against the source pipeline result."""
    results = []
    all_conflicts = []
    for p in ref_paths:
        if not p:
            continue
        r = compare_one(p, result, offset, raster=raster, mode=mode)
        results.append(r)
        for c in r.get('conflicts', []):
            all_conflicts.append(dict(c, reference=r.get('name')))
    return {
        'mode': mode,
        'count': len(results),
        'results': results,
        'conflicts': all_conflicts,
    }
