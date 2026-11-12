"""CAD -> Blender wall extractor : local web app.  Run:  python app.py  then open http://127.0.0.1:5000"""
import logging
import os
import re
import time
import traceback

from flask import Flask, jsonify, render_template, request, send_file

from cad_processor.pipeline import CADtoBlenderPipeline

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE, 'uploads')
OUTPUT_DIR = os.path.join(BASE, 'output')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)


def _load_config():
    """Built-in settings (Gemini key) from config.json next to app.py. Kept on the server only."""
    import json
    try:
        with open(os.path.join(BASE, 'config.json'), encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


CONFIG = _load_config()
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def _float(name, default):
    try:
        return float(request.form.get(name, default))
    except (TypeError, ValueError):
        return default


JOBS = {}


def _run(job, on, off):
    info = JOBS[job]
    p = info['params']
    opts = {
        'references': info.get('references', []),
        'reference_mode': p.get('reference_mode', 'validate'),
    }
    if p.get('conn_tol'):
        opts['conn_tol'] = float(p['conn_tol'])
    if p.get('drawing') not in (None, ''):
        opts['drawing'] = int(p['drawing'])
    res = CADtoBlenderPipeline().process(
        info['path'], wall_height=p['wall_height'], default_thickness=p['default_thickness'],
        source_units=p['source_units'], wall_layers=on, off_layers=off, options=opts)
    if not res['ok']:
        return jsonify({'error': res['error'], 'steps': res['steps'], 'layers': res.get('layers', []),
                        'job_id': job}), 422
    info['last'] = res
    return _respond(job, res)


def _respond(job, res):
    info = JOBS[job]
    files = {}
    for key, name, text in (('script', f'{job}_walls_blender.py', res['script']),
                            ('json', f'{job}_walls.json', res['wall_json']),
                            ('csv', f'{job}_walls.csv', res['wall_csv'])):
        with open(os.path.join(OUTPUT_DIR, name), 'w', encoding='utf-8') as fh:
            fh.write(text)
        files[key] = name
    pieces = [w.to_dict() for w in res['walls']]
    walls = [q for q in pieces if q['kind'] == 'wall']
    clean_under = []
    for seg in res.get('underlay', []):
        x1, y1, x2, y2 = seg
        if (x2 - x1)**2 + (y2 - y1)**2 >= 22500:  # >= 150 mm
            clean_under.append([round(x1), round(y1), round(x2), round(y2)])
            if len(clean_under) >= 1500:
                break
    outline = res.get('outline', [])
    from shapely.geometry import Polygon
    floor_area_m2 = round(sum(Polygon(r).area / 1e6 for r in outline if len(r) >= 3), 2)
    ceiling_height_m = round(max((w['base'] + w['height'] for w in pieces), default=3000.0) / 1000.0, 2)
    return jsonify({
        'job_id': job, 'filename': info['filename'], 'layers': res.get('layers', []),
        'wall_count': len(walls),
        'exterior_count': sum(1 for w in walls if w['wall_type'] == 'exterior'),
        'interior_count': sum(1 for w in walls if w['wall_type'] == 'interior'),
        'exterior_length_m': round(sum(w['length'] for w in walls if w['wall_type'] == 'exterior') / 1000, 2),
        'interior_length_m': round(sum(w['length'] for w in walls if w['wall_type'] == 'interior') / 1000, 2),
        'floor_area_m2': floor_area_m2,
        'ceiling_height_m': ceiling_height_m,
        'opening_count': len(pieces) - len(walls), 'outline': outline,
        'skirting': res.get('skirting', []),
        'washroom_tiles': res.get('washroom_tiles', []),
        'washroom_voids': res.get('washroom_voids', []),
        'skirting_count': len(res.get('skirting', [])),
        'washroom_count': len(res.get('washroom_voids', [])),
        'rooms': [{k: r.get(k) for k in ('name', 'label', 'use', 'type', 'area_m2', 'panelled',
                                         'floor_obj', 'floor_mat', 'floor_category', 'skirt_obj', 'tile_obj', 'ring', 'holes')}
                  for r in (res.get('architecture') or {}).get('rooms', [])],
        'openings': [{k: o.get(k) for k in ('id', 'type', 'width', 'sill', 'head', 'rooms', 'balcony',
                                            'dry_balcony', 'has_lintel', 'lintel_id', 'p0', 'p1', 'thickness', 'rect')}
                     for o in (res.get('architecture') or {}).get('openings', [])],
        'kitchens': (res.get('architecture') or {}).get('kitchens', []),
        'document': res.get('document'),
        'tile_count': len(res.get('washroom_tiles', [])),
        'panel_count': len((res.get('architecture') or {}).get('panels', [])),
        'underlay': clean_under,
        'walls': pieces, 'summary': res['summary'], 'warnings': res['warnings'],
        'steps': res['steps'], 'info': res['info'], 'script': res['script'], 'files': files,
        'segmentation': {k: (res.get('segmentation') or {}).get(k) for k in ('summary', 'png', 'support')},
        'review': res.get('review'),
        'references': res.get('references'),
        'drawings': res.get('drawings'),
    })


@app.route('/ai_review', methods=['POST'])
def ai_review():
    """Ask a vision AI (Gemini) to flag wrong walls and propose missing ones. Suggestions only."""
    try:
        from cad_processor import ai_review as ai
        d = request.get_json(force=True)
        job = str(d.get('job_id', ''))
        if job not in JOBS or 'last' not in JOBS[job]:
            return jsonify({'error': 'Unknown job - upload the file again.'}), 404
        key = (d.get('api_key') or CONFIG.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY', '')).strip()
        res = JOBS[job]['last']
        seg = res.get('segmentation') or {}
        out = ai.review(res['walls'], res.get('underlay', []), key, model=d.get('model') or CONFIG.get('gemini_model', ''),
                        tiles=int(d.get('tiles', 2)), candidates=seg.get('candidates'), support=seg.get('support'))
        return jsonify(out)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 502


@app.route('/add_outer_walls', methods=['POST'])
def add_outer_walls():
    """Build a 100% connected, gap-free outer boundary wall loop along the full building perimeter,
    plus any orthogonal missed wall bands from segmentation."""
    try:
        from collections import Counter
        from math import hypot, atan2, pi
        from shapely.geometry import LineString, Polygon as ShpPoly
        from shapely.geometry.polygon import orient
        from shapely.ops import unary_union, polygonize

        d = request.get_json(force=True)
        job = str(d.get('job_id', ''))
        if job not in JOBS or 'last' not in JOBS[job]:
            return jsonify({'error': 'Unknown job - upload the file again.'}), 404
        res = JOBS[job]['last']

        # Keep all original detected walls (strip any previously added BOUNDARY walls so clicking twice is idempotent)
        existing_walls = [w for w in res['walls'] if w.kind == 'wall' and w.layer != 'BOUNDARY']
        fills = [w for w in res['walls'] if w.kind != 'wall']
        if not existing_walls and not res.get('outline'):
            return jsonify({'error': 'No building outline available. Upload a plan and scan first.'}), 422

        # Use explicit thickness if given, otherwise match the modal wall thickness of the plan
        if d.get('thickness'):
            thickness = float(d['thickness'])
        elif existing_walls:
            thickness = float(Counter(round(w.thickness, 1) for w in existing_walls).most_common(1)[0][0])
        else:
            thickness = float(JOBS[job]['params'].get('default_thickness', 200.0))

        # --- Helper: Clean and orthogonalize a perimeter ring ---
        def clean_orthogonal_ring(ring, tol=25.0):
            if len(ring) < 3:
                return ring
            poly = ShpPoly(ring).buffer(0)
            if poly.is_empty:
                return ring
            if poly.geom_type == 'MultiPolygon':
                poly = max(poly.geoms, key=lambda g: g.area)
            simp = orient(poly.simplify(tol, preserve_topology=True), 1.0)
            pts = [(float(x), float(y)) for x, y in list(simp.exterior.coords)[:-1]]
            if len(pts) < 3:
                return ring

            # 1. Remove very short segments (< 50 mm) and merge near-collinear consecutive edges (within 5 deg)
            merge_tol = 5.0 * pi / 180.0
            changed = True
            while changed and len(pts) >= 4:
                changed = False
                new_pts = []
                n = len(pts)
                i = 0
                while i < n:
                    p_prev = new_pts[-1] if new_pts else pts[(i - 1) % n]
                    p_cur = pts[i]
                    p_next = pts[(i + 1) % n]
                    L1 = hypot(p_cur[0] - p_prev[0], p_cur[1] - p_prev[1])
                    L2 = hypot(p_next[0] - p_cur[0], p_next[1] - p_cur[1])
                    if L2 < 50.0 and len(pts) > 3:
                        changed = True
                        i += 1
                        continue
                    if L1 > 1.0 and L2 > 1.0:
                        a1 = atan2(p_cur[1] - p_prev[1], p_cur[0] - p_prev[0])
                        a2 = atan2(p_next[1] - p_cur[1], p_next[0] - p_cur[0])
                        da = abs(a1 - a2)
                        if da > pi:
                            da = 2 * pi - da
                        if da < merge_tol:
                            changed = True
                            i += 1
                            continue
                    new_pts.append(p_cur)
                    i += 1
                pts = new_pts

            # 2. Snap near-horizontal/vertical edges (within 4 deg) to exact 90-degree corners
            snap_tol = 4.0 * pi / 180.0
            n = len(pts)
            dirs, vals = [], []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                dx, dy = bx - ax, by - ay
                ang = abs(atan2(dy, dx))
                if ang < snap_tol or abs(ang - pi) < snap_tol:
                    dirs.append('H')
                    vals.append(round((ay + by) / 2.0, 1))
                elif abs(ang - pi / 2.0) < snap_tol:
                    dirs.append('V')
                    vals.append(round((ax + bx) / 2.0, 1))
                else:
                    dirs.append('D')
                    vals.append(None)

            snapped = list(pts)
            for i in range(n):
                prev_e = (i - 1) % n
                cur_e = i
                if dirs[prev_e] == 'H' and dirs[cur_e] == 'V':
                    snapped[i] = (vals[cur_e], vals[prev_e])
                elif dirs[prev_e] == 'V' and dirs[cur_e] == 'H':
                    snapped[i] = (vals[prev_e], vals[cur_e])
                elif dirs[cur_e] == 'H':
                    snapped[i] = (round(snapped[i][0], 1), vals[cur_e])
                elif dirs[cur_e] == 'V':
                    snapped[i] = (vals[cur_e], round(snapped[i][1], 1))

            # 3. Remove any duplicate or collinear vertices created by snapping
            final_pts = []
            m = len(snapped)
            for i in range(m):
                p_prev = final_pts[-1] if final_pts else snapped[(i - 1) % m]
                p_cur = snapped[i]
                p_next = snapped[(i + 1) % m]
                if hypot(p_cur[0] - p_prev[0], p_cur[1] - p_prev[1]) < 10.0:
                    continue
                a1 = atan2(p_cur[1] - p_prev[1], p_cur[0] - p_prev[0])
                a2 = atan2(p_next[1] - p_cur[1], p_next[0] - p_cur[0])
                da = abs(a1 - a2)
                if da > pi:
                    da = 2 * pi - da
                if da < 1e-3:
                    continue
                final_pts.append(p_cur)

            return final_pts if len(final_pts) >= 3 else ring

        # --- Recover full floor-plan perimeter (including rooms/balconies bounded by underlay lines) ---
        wall_polys = [ShpPoly(w.polygon).buffer(0) for w in existing_walls + fills if len(w.polygon) >= 3]
        wall_polys = [p for p in wall_polys if not p.is_empty]
        wall_union = unary_union(wall_polys) if wall_polys else ShpPoly()

        existing_outline_polys = [ShpPoly(rg).buffer(0) for rg in (res.get('outline') or []) if len(rg) >= 3]
        existing_outline_polys = [p for p in existing_outline_polys if not p.is_empty]

        underlay = res.get('underlay') or []
        valid_faces = []
        if underlay and not wall_union.is_empty:
            lines = [LineString([(round(u[0], 1), round(u[1], 1)), (round(u[2], 1), round(u[3], 1))])
                     for u in underlay if hypot(u[2] - u[0], u[3] - u[1]) >= 10.0]
            for p in wall_polys:
                if p.geom_type == 'Polygon':
                    lines.append(LineString(list(p.exterior.coords)))
            noded = unary_union(lines)
            faces = list(polygonize(noded))
            wall_zone = wall_union.buffer(150.0)
            valid_faces = [f for f in faces if f.area <= 150e6 and f.intersects(wall_zone)]

        raw_parts = wall_polys + existing_outline_polys + valid_faces
        if not raw_parts:
            return jsonify({'error': 'No building geometry available.'}), 422

        raw_mass = unary_union(raw_parts).buffer(0)
        closed_mass = raw_mass.buffer(550.0, join_style=2, mitre_limit=2.0).buffer(-550.0, join_style=2, mitre_limit=2.0)
        if closed_mass.is_empty:
            closed_mass = raw_mass
        geoms = [closed_mass] if closed_mass.geom_type == 'Polygon' else list(getattr(closed_mass, 'geoms', []))
        geoms = [g for g in geoms if g.area >= 1e6] or geoms

        clean_outline = []
        add_list = []
        t = thickness

        for g in geoms:
            g_ccw = orient(g, 1.0)
            raw_ring = [(float(x), float(y)) for x, y in list(g_ccw.exterior.coords)[:-1]]
            ring = clean_orthogonal_ring(raw_ring, tol=25.0)
            if len(ring) < 3:
                continue
            # Ensure CCW orientation for exact inward normal & corner turns
            ring_poly = orient(ShpPoly(ring).buffer(0), 1.0)
            if ring_poly.geom_type == 'MultiPolygon':
                ring_poly = max(ring_poly.geoms, key=lambda p: p.area)
            ring = [(float(x), float(y)) for x, y in list(ring_poly.exterior.coords)[:-1]]
            clean_outline.append([[round(x, 1), round(y, 1)] for x, y in ring])

            n = len(ring)
            # Precompute unit direction vectors and inward normals for every perimeter edge
            u_dirs = []
            for i in range(n):
                ax, ay = ring[i]
                bx, by = ring[(i + 1) % n]
                L = hypot(bx - ax, by - ay)
                if L < 1e-6:
                    u_dirs.append((1.0, 0.0))
                else:
                    u_dirs.append(((bx - ax) / L, (by - ay) / L))

            # Build 100% watertight connected ribbon segments around the entire ring
            for i in range(n):
                p0 = ring[i]
                p1 = ring[(i + 1) % n]
                ux, uy = u_dirs[i]
                nx, ny = -uy, ux  # inward normal for CCW ring
                u_prev_x, u_prev_y = u_dirs[(i - 1) % n]
                u_next_x, u_next_y = u_dirs[(i + 1) % n]

                # Turn at start vertex p0 (from edge i-1 to edge i)
                cross_start = u_prev_x * uy - u_prev_y * ux
                dot_start = u_prev_x * ux + u_prev_y * uy
                if abs(dot_start) < 0.15:  # orthogonal corner
                    s_ext = 0.0 if cross_start > 0 else t
                else:
                    s_ext = t / 2.0

                # Turn at end vertex p1 (from edge i to edge i+1)
                cross_end = ux * u_next_y - uy * u_next_x
                dot_end = ux * u_next_x + uy * u_next_y
                if abs(dot_end) < 0.15:  # orthogonal corner
                    e_ext = 0.0 if cross_end > 0 else t
                else:
                    e_ext = t / 2.0

                # Extended outer edge endpoints
                a_out = (p0[0] - ux * s_ext, p0[1] - uy * s_ext)
                b_out = (p1[0] + ux * e_ext, p1[1] + uy * e_ext)
                # Extended inner edge endpoints (inset by thickness t)
                b_in = (b_out[0] + nx * t, b_out[1] + ny * t)
                a_in = (a_out[0] + nx * t, a_out[1] + ny * t)

                # Wall centerline (midway between outer and inner edge)
                cx1, cy1 = a_out[0] + nx * (t / 2.0), a_out[1] + ny * (t / 2.0)
                cx2, cy2 = b_out[0] + nx * (t / 2.0), b_out[1] + ny * (t / 2.0)
                poly = [
                    (round(a_out[0], 2), round(a_out[1], 2)),
                    (round(b_out[0], 2), round(b_out[1], 2)),
                    (round(b_in[0], 2), round(b_in[1], 2)),
                    (round(a_in[0], 2), round(a_in[1], 2)),
                ]
                add_list.append({
                    'x1': cx1, 'y1': cy1, 'x2': cx2, 'y2': cy2,
                    't': t, 'polygon': poly, 'wall_type': 'exterior'
                })

        # Clip outer boundary segments against existing window/door/balcony openings so windows & doors are never blocked
        open_rects = [ShpPoly(o['rect']).buffer(35.0, join_style=2) for o in (res.get('openings') or []) if len(o.get('rect', [])) >= 3]
        if open_rects:
            open_union = unary_union(open_rects)
            clipped_add = []
            for a in add_list:
                sp = ShpPoly(a['polygon']).buffer(0)
                if sp.is_empty:
                    continue
                diff = sp.difference(open_union)
                if diff.is_empty:
                    continue
                parts = [diff] if diff.geom_type == 'Polygon' else [p for p in getattr(diff, 'geoms', []) if p.geom_type == 'Polygon']
                for p in parts:
                    if p.area < 5000.0:
                        continue
                    mrr = p.minimum_rotated_rectangle
                    if mrr.geom_type != 'Polygon':
                        continue
                    mc = list(mrr.exterior.coords)[:4]
                    d01, d12 = hypot(mc[1][0] - mc[0][0], mc[1][1] - mc[0][1]), hypot(mc[2][0] - mc[1][0], mc[2][1] - mc[1][1])
                    if max(d01, d12) < 120.0:
                        continue
                    if d01 >= d12:
                        p_a = (0.5 * (mc[0][0] + mc[3][0]), 0.5 * (mc[0][1] + mc[3][1]))
                        p_b = (0.5 * (mc[1][0] + mc[2][0]), 0.5 * (mc[1][1] + mc[2][1]))
                    else:
                        p_a = (0.5 * (mc[0][0] + mc[1][0]), 0.5 * (mc[0][1] + mc[1][1]))
                        p_b = (0.5 * (mc[2][0] + mc[3][0]), 0.5 * (mc[2][1] + mc[3][1]))
                    ring_pts = [(round(x, 2), round(y, 2)) for x, y in list(orient(p, 1.0).exterior.coords)[:-1]]
                    clipped_add.append({
                        'x1': p_a[0], 'y1': p_a[1], 'x2': p_b[0], 'y2': p_b[1],
                        't': a['t'], 'polygon': ring_pts, 'wall_type': 'exterior'
                    })
            if clipped_add:
                add_list = clipped_add

        # --- Preview mode: return count so the UI can ask for confirmation ---
        preview = bool(d.get('preview', False))
        total_len_m = round(sum(hypot(a['x2'] - a['x1'], a['y2'] - a['y1']) for a in add_list) / 1000.0, 2)
        if preview:
            return jsonify({
                'preview': True,
                'count': len(add_list),
                'total_length_m': total_len_m,
                'segments': [{'x1': round(a['x1']), 'y1': round(a['y1']),
                              'x2': round(a['x2']), 'y2': round(a['y2']),
                              'length_mm': round(hypot(a['x2'] - a['x1'], a['y2'] - a['y1']))}
                             for a in add_list],
                'existing_wall_count': len(existing_walls),
                'message': f'{len(add_list)} connected outer boundary walls ({total_len_m} m total) will be ADDED '
                           f'around the full floor-plan perimeter.\n'
                           f'All {len(existing_walls)} existing walls, rooms, and tiles will be preserved.',
            })

        # --- Confirmed: append the connected boundary walls and update outline/script ---
        from cad_processor.models import Wall
        from cad_processor.wall_data import WallDataExporter
        from cad_processor.blender_generator import BlenderScriptGenerator
        from cad_processor import architecture as arch

        height = JOBS[job]['params']['wall_height']
        spec = res.get('_spec') or dict(arch.SPEC, wall_h=float(height))
        walls = list(existing_walls)
        existing_count = len(walls)

        for a in add_list:
            x1, y1, x2, y2, wt = float(a['x1']), float(a['y1']), float(a['x2']), float(a['y2']), float(a['t'])
            L = hypot(x2 - x1, y2 - y1)
            if L < 1.0 or wt < 1.0:
                continue
            walls.append(Wall(
                id='', start_point=(x1, y1), end_point=(x2, y2),
                length=L, thickness=wt, height=height,
                polygon=a['polygon'], layer='BOUNDARY',
                wall_type=a.get('wall_type', 'exterior')
            ))

        top = max([int(w.id.split('_')[1]) for w in walls if w.id.startswith('Wall_')] or [0])
        for w in walls:
            if not w.id:
                top += 1
                w.id = f'Wall_{top:03d}'

        # Preserve existing architecture analysis (rooms, skirting, tiles, openings, kitchens)
        # while updating the outer floor/ceiling slab rings to match the full building perimeter.
        existing_analysis = dict(res.get('architecture') or {})
        if clean_outline:
            res['outline'] = clean_outline
            if existing_analysis.get('floor'):
                existing_analysis['floor'] = [{'outer': rg, 'holes': []} for rg in clean_outline]
            if existing_analysis.get('ceiling'):
                existing_analysis['ceiling'] = [{'outer': rg, 'holes': []} for rg in clean_outline]

        pieces = walls + fills
        ex = WallDataExporter()
        res.update({
            'walls': pieces,
            'architecture': existing_analysis,
            'script': BlenderScriptGenerator().generate_script(
                pieces, clear_scene=True, outline=res.get('outline'), arch=existing_analysis,
                underlay=res.get('underlay'), spec=spec),
            'summary': ex.to_summary(pieces),
            'wall_json': ex.to_json(pieces),
            'wall_csv': ex.to_csv(pieces),
        })
        added_count = len(walls) - existing_count
        res['info']['total_length_m'] = round(sum(w.length for w in walls) / 1000.0, 2)
        res['warnings'] = [w for w in res.get('warnings', []) if 'outer boundary wall' not in w] + [
            f'Added {added_count} connected outer boundary wall(s) ({total_len_m} m). Existing {existing_count} walls preserved.'
        ]
        try:
            from cad_processor import detection_review
            offset = res.get('_offset', (0.0, 0.0))
            raster = res.get('_raster')
            topology = res.get('_topology') or {}
            res['review'] = detection_review.run(
                res, offset, raster=raster, topology=topology,
                source_image=res.get('_source_image', ''),
                conn_tol=topology.get('conn_tol_mm') or 100.0,
                modes_mm=(raster or {}).get('thickness_modes_mm'))
        except Exception:
            traceback.print_exc()
        return _respond(job, res)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Server error: {e}'}), 500


@app.route('/edit', methods=['POST'])
def edit():
    """Manual corrections: remove detected walls by id, add walls, or override uncertain gaps."""
    try:
        from math import hypot
        from cad_processor.models import Wall
        from cad_processor.wall_data import WallDataExporter
        from cad_processor.blender_generator import BlenderScriptGenerator
        from cad_processor import architecture as arch
        d = request.get_json(force=True)
        job = str(d.get('job_id', ''))
        if job not in JOBS or 'last' not in JOBS[job]:
            return jsonify({'error': 'Unknown job - upload the file again.'}), 404
        res = JOBS[job]['last']
        remove = set(d.get('remove', []))
        height = JOBS[job]['params']['wall_height']
        spec = res.get('_spec') or dict(arch.SPEC, wall_h=float(height))
        walls = [w for w in res['walls'] if w.kind == 'wall' and w.id not in remove]
        fills = [w for w in res['walls'] if w.kind != 'wall' and w.id not in remove]
        openings = [o for o in res.get('_openings', []) if f'Head_{o.id}' not in remove and o.id not in remove]
        resolved = set(res.get('_resolved_uncertain') or [])

        add_list = list(d.get('add', []))
        override_notes = []
        for ov in d.get('gap_overrides', []):
            gid = str(ov.get('id', ''))
            act = str(ov.get('action', 'keep_open'))
            if gid:
                resolved.add(gid)
            x1, y1 = float(ov.get('x1', 0)), float(ov.get('y1', 0))
            x2, y2 = float(ov.get('x2', 0)), float(ov.get('y2', 0))
            t = float(ov.get('t') or JOBS[job]['params'].get('default_thickness', 200.0))
            L = hypot(x2 - x1, y2 - y1)
            if act == 'close_wall' and L >= 1.0:
                add_list.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 't': t})
                override_notes.append(f'closed {gid} as wall ({L:.0f} mm)')
            elif act in ('door', 'window', 'passage') and L >= 1.0:
                sill = spec['win_sill'] if act == 'window' else 0.0
                head = (spec['win_sill'] + spec['win_h']) if act == 'window' else spec['door_head']
                op = arch.Opening(f"User_{act.title()}_{gid or len(openings)+1}", act, (x1, y1), (x2, y2), t, sill, head, f'user override ({gid})')
                openings.append(op)
                fills.extend(arch.opening_pieces([op], spec))
                override_notes.append(f'marked {gid} as {act} ({L:.0f} mm)')
            else:
                override_notes.append(f'kept {gid} open')

        for a in add_list:
            x1, y1, x2, y2, t = (float(a[k]) for k in ('x1', 'y1', 'x2', 'y2', 't'))
            L = hypot(x2 - x1, y2 - y1)
            if L < 1 or t < 1:
                continue
            nx, ny = -(y2 - y1) / L * t / 2, (x2 - x1) / L * t / 2
            poly = [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
            walls.append(Wall(id='', start_point=(x1, y1), end_point=(x2, y2), length=L, thickness=t,
                              height=height, polygon=poly, layer='MANUAL'))
        if not walls:
            return jsonify({'error': 'No walls left.'}), 422
        # keep existing ids stable (AI labels refer to them); new walls continue the numbering
        top = max([int(w.id.split('_')[1]) for w in walls if w.id.startswith('Wall_')] or [0])
        for w in walls:
            if not w.id:
                top += 1
                w.id = f'Wall_{top:03d}'
        from cad_processor.pipeline import CADtoBlenderPipeline
        pieces = CADtoBlenderPipeline._resolve_3d_overlaps(walls + fills)
        walls = [w for w in pieces if w.kind == 'wall']
        fills = [w for w in pieces if w.kind != 'wall']
        ex = WallDataExporter()
        ex.classify_walls(walls, fills, res.get('underlay', []), outline=res.get('outline'))
        analysis = arch.analyse(walls, fills, openings, ex.outline, res.get('_arch_ctx') or {}, spec)
        fills = arch.sync_opening_pieces(openings, fills, spec)
        pieces = walls + fills
        res['_openings'] = openings
        res['_resolved_uncertain'] = resolved
        res.update({
            'walls': pieces, 'outline': ex.outline,
            'script': BlenderScriptGenerator().generate_script(pieces, clear_scene=True, outline=ex.outline, arch=analysis,
                                                               underlay=res.get('underlay'), spec=spec),
            'summary': ex.to_summary(pieces), 'wall_json': ex.to_json(pieces), 'wall_csv': ex.to_csv(pieces),
            'architecture': analysis,
            'skirting': [s['ring'] for s in analysis['skirting']],
            'washroom_voids': [r['ring'] for r in analysis['rooms'] if r['type'] == 'washroom'],
            'washroom_tiles': analysis['tiles'],
        })
        res['info']['total_length_m'] = round(sum(w.length for w in walls) / 1000, 2)
        edit_msg = f'Manual edit: {len(remove)} removed, {len(add_list)} added.'
        if override_notes:
            edit_msg += ' Overrides: ' + ', '.join(override_notes)
        res['warnings'] = res['warnings'] + [edit_msg]
        try:
            from cad_processor import detection_review
            offset = res.get('_offset', (0.0, 0.0))
            raster = res.get('_raster')
            topology = res.get('_topology') or {}
            res['review'] = detection_review.run(
                res, offset, raster=raster, topology=topology,
                source_image=res.get('_source_image', ''),
                conn_tol=topology.get('conn_tol_mm') or 100.0,
                modes_mm=(raster or {}).get('thickness_modes_mm'))
        except Exception:
            traceback.print_exc()
        return _respond(job, res)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Server error: {e}'}), 500


@app.route('/add_reference', methods=['POST'])
def add_reference():
    """Upload one or more reference plans/models and compare against the active job."""
    try:
        job = str(request.form.get('job_id', ''))
        if job not in JOBS or 'last' not in JOBS[job]:
            return jsonify({'error': 'Unknown job - upload the primary file first.'}), 404
        ref_files = request.files.getlist('references')
        mode = request.form.get('reference_mode', 'validate')
        JOBS[job]['params']['reference_mode'] = mode
        saved = list(JOBS[job].get('references', []))
        for rf in ref_files:
            if not rf or not rf.filename:
                continue
            ext = os.path.splitext(rf.filename)[1].lower()
            if ext not in ('.dxf', '.dwg', '.fbx', '.obj', '.glb', '.gltf', '.dae', '.stl', '.ply', '.png', '.jpg', '.jpeg', '.webp', '.bmp'):
                continue
            safe = re.sub(r'[^A-Za-z0-9._-]+', '_', rf.filename)
            rpath = os.path.join(UPLOAD_DIR, f'{job}_ref_{len(saved)+1}_{safe}')
            rf.save(rpath)
            saved.append(rpath)
        JOBS[job]['references'] = saved
        if mode in ('calibrate', 'authoritative'):
            return _run(job, [], [])
        res = JOBS[job]['last']
        from cad_processor import reference
        comp = reference.compare_all(saved, res, res.get('_offset', (0.0, 0.0)),
                                     raster=res.get('_raster'), mode=mode)
        res['references'] = comp
        return _respond(job, res)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Server error: {e}'}), 500


@app.route('/rescan', methods=['POST'])
def rescan():
    try:
        d = request.get_json(force=True)
        job = str(d.get('job_id', ''))
        if job not in JOBS:
            return jsonify({'error': 'Unknown job - upload the file again.'}), 404
        for k in ('wall_height', 'default_thickness', 'conn_tol'):
            if d.get(k):
                JOBS[job]['params'][k] = float(d[k])
        if d.get('reference_mode'):
            JOBS[job]['params']['reference_mode'] = str(d['reference_mode'])
        if 'drawing' in d:
            JOBS[job]['params']['drawing'] = d.get('drawing')
        return _run(job, d.get('wall_layers', []), d.get('off_layers', []))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Server error: {e}'}), 500


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    try:
        f = request.files.get('file')
        if not f or not f.filename:
            return jsonify({'error': 'No file selected.'}), 400
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ('.dxf', '.dwg', '.pdf', '.svg', '.fbx', '.png', '.jpg', '.jpeg', '.webp', '.bmp',
                       '.docx', '.docm', '.dotx', '.dotm', '.doc', '.rtf', '.odt'):
            return jsonify({'error': f'"{ext or "no extension"}" files are not supported. Supported formats: .dxf, .dwg, '
                                     '.fbx, .png, .jpg, .jpeg, .webp, .bmp, PDF, and Word .docx / .doc '
                                     '(plan picture or DXF inside + written specification)'}), 400

        job = str(int(time.time() * 1000))
        safe = re.sub(r'[^A-Za-z0-9._-]+', '_', f.filename)
        path = os.path.join(UPLOAD_DIR, f'{job}_{safe}')
        f.save(path)

        ref_paths = []
        for idx, rf in enumerate(request.files.getlist('references')):
            if not rf or not rf.filename:
                continue
            rext = os.path.splitext(rf.filename)[1].lower()
            if rext in ('.dxf', '.dwg', '.fbx', '.obj', '.glb', '.gltf', '.dae', '.stl', '.ply', '.png', '.jpg', '.jpeg', '.webp', '.bmp'):
                rsafe = re.sub(r'[^A-Za-z0-9._-]+', '_', rf.filename)
                rpath = os.path.join(UPLOAD_DIR, f'{job}_ref_{idx+1}_{rsafe}')
                rf.save(rpath)
                ref_paths.append(rpath)

        units = request.form.get('source_units', 'auto')
        conn_tol_raw = request.form.get('conn_tol', '').strip()
        params = {'wall_height': _float('wall_height', 3000.0),
                  'default_thickness': _float('default_thickness', 200.0),
                  'source_units': None if units == 'auto' else units,
                  'conn_tol': float(conn_tol_raw) if conn_tol_raw else None,
                  'reference_mode': request.form.get('reference_mode', 'validate')}
        JOBS[job] = {'path': path, 'filename': f.filename, 'params': params, 'references': ref_paths}
        return _run(job, [], [])
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Server error: {e}'}), 500


@app.route('/download/<filename>')
def download(filename):
    name = os.path.basename(filename)
    path = os.path.join(OUTPUT_DIR, name)
    if not os.path.isfile(path):
        return jsonify({'error': 'File not found'}), 404
    return send_file(path, as_attachment=True)


def _find_blender():
    """Blender executable: config.json 'blender_exe', env BLENDER_EXE, PATH, or the newest install in Program Files."""
    import glob
    import shutil
    for cand in (CONFIG.get('blender_exe'), os.environ.get('BLENDER_EXE'), shutil.which('blender')):
        if cand and os.path.isfile(cand):
            return cand
    found = sorted(glob.glob(r'C:\Program Files\Blender Foundation\Blender*\blender.exe'), reverse=True)
    return found[0] if found else None


@app.route('/export_3d', methods=['POST'])
def export_3d():
    """Build the full 3D model in headless Blender and export it for Unreal Engine and 3ds Max."""
    import json
    import subprocess
    try:
        d = request.get_json(force=True)
        job = str(d.get('job_id', ''))
        if job not in JOBS or 'last' not in JOBS[job]:
            return jsonify({'error': 'Unknown job - upload the file again.'}), 404
        blender = _find_blender()
        if not blender:
            return jsonify({'error': 'Blender not found. Install Blender 4.x/5.x or set "blender_exe" in config.json.'}), 500
        script = os.path.join(OUTPUT_DIR, f'{job}_walls_blender.py')
        with open(script, 'w', encoding='utf-8') as fh:
            fh.write(JOBS[job]['last']['script'])
        out_dir = os.path.join(OUTPUT_DIR, f'{job}_3d')
        os.makedirs(out_dir, exist_ok=True)
        stem = re.sub(r'[^A-Za-z0-9_-]+', '_', os.path.splitext(JOBS[job]['filename'])[0]).strip('_') or 'Model'
        env = dict(os.environ, CAD_EXPORT_DIR=out_dir, CAD_EXPORT_NAME=stem)
        proc = subprocess.run([blender, '-b', '--factory-startup', '-P', script], capture_output=True,
                              text=True, encoding='utf-8', errors='replace', env=env, timeout=600)
        result, validation = None, None
        for line in proc.stdout.splitlines():
            if line.startswith('EXPORT_RESULT_JSON:'):
                result = json.loads(line.split(':', 1)[1])
            elif line.startswith('VALIDATION:'):
                validation = line.split(':', 1)[1].strip()
        if not result:
            tail = '\n'.join((proc.stdout + '\n' + proc.stderr).splitlines()[-25:])
            return jsonify({'error': f'Blender export failed (code {proc.returncode}).\n{tail}'}), 500
        files = [{'name': os.path.basename(p), 'size_kb': round(os.path.getsize(p) / 1024, 1),
                  'url': f'/download_3d/{job}/{os.path.basename(p)}'} for p in result['files'] if os.path.isfile(p)]
        return jsonify({'ok': True, 'files': files, 'objects': result.get('objects', {}),
                        'validation': validation, 'folder': out_dir, 'blender': blender})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Blender took longer than 10 minutes.'}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Server error: {e}'}), 500


@app.route('/download_3d/<job>/<filename>')
def download_3d(job, filename):
    path = os.path.join(OUTPUT_DIR, f'{re.sub(r"[^0-9]", "", job)}_3d', os.path.basename(filename))
    if not os.path.isfile(path):
        return jsonify({'error': 'File not found'}), 404
    return send_file(path, as_attachment=True)


if __name__ == '__main__':
    try:
        from waitress import serve
        print("Serving app with Waitress WSGI server on http://127.0.0.1:5000 ...")
        serve(app, host='127.0.0.1', port=5000, threads=6, channel_timeout=600)
    except Exception as e:
        print(f"Fallback to Flask development server: {e}")
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
