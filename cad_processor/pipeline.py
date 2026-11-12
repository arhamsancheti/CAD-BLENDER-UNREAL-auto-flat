import logging
import time
from typing import Any, Dict, Optional

from cad_processor.blender_generator import BlenderScriptGenerator
from cad_processor.cleaner import CADCleaner
from cad_processor.importer import CADImporter
from cad_processor.normalizer import UnitNormalizer
from cad_processor.openings import OpeningFiller
from cad_processor.validator import WallValidator
from cad_processor.wall_builder import WallBuilder
from cad_processor.wall_data import WallDataExporter
from cad_processor.wall_detector import WallDetector

logger = logging.getLogger(__name__)


class CADtoBlenderPipeline:
    """Runs the 10-step CAD -> Blender wall pipeline and reports every step."""

    def process(self, filepath: str, wall_height: float = 3000.0, default_thickness: float = 200.0,
                source_units: Optional[str] = None, wall_layers=None, off_layers=None,
                options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """wall_layers / off_layers: layer names the user forces on / off as walls.
        options: image_wall_mm, image_mm_per_px (raster scale), conn_tol (mm), references (list of
        paths), reference_mode ('validate' | 'calibrate' | 'authoritative')."""
        CADCleaner.forced_on = set(wall_layers or [])
        CADCleaner.forced_off = set(off_layers or [])
        self.options = dict(options or {})
        try:
            res = self._process(filepath, wall_height, default_thickness, source_units)
            return self._document_scale_search(res, dict(options or {}),
                                               (filepath, wall_height, default_thickness, source_units))
        finally:
            CADCleaner.forced_on = set()
            CADCleaner.forced_off = set()

    @staticmethod
    def _doc_quality(res):
        dr = res.get('_doc_pic') if res and res.get('ok') else None
        return dr['quality'] if dr else (-1, -9.0, -1)

    def _document_scale_search(self, res, base_opts, args, max_runs: int = 7):
        """Word document with a plan picture: a pasted picture has no reliable scale, so try the scales the
        document suggests (room-schedule area vs footprint, documented wall thicknesses vs the drawn wall
        bands, room-size fit) with both picture engines (traced CAD lines / raster walls) and keep the run
        whose detected rooms agree best with the documented room sizes."""
        dr = res.get('_doc_pic') if res.get('ok') else None
        if not dr or base_opts.get('image_mm_per_px'):
            return res
        best, tried, runs = res, [(dr['engine'], dr['mpp'])], 0
        queue = []
        if dr['suggest']:
            queue.append((dr['engine'], dr['suggest'], 'room-size fit of the first run'))
        for o in dr['options']:
            if 'mm_per_px' in o:
                queue.append((o.get('engine', 'raster'), o['mm_per_px'], o['label']))
        if dr['engine'] == 'raster':
            for m in dr['modes_mm']:                   # each detected wall band taken as a documented wall thickness
                for t, lbl in ((dr['ext_t'], 'external'), (dr['int_t'], 'internal')):
                    if t and m:
                        queue.append(('raster', dr['mpp'] * float(t) / float(m),
                                      f'{lbl} wall {t:.0f} mm = detected band {m:.0f} mm'))
        while queue and runs < max_runs:
            cur_d = best.get('_doc_pic') or {}
            if cur_d.get('n_sized', 0) >= 3 and cur_d['quality'][0] >= max(3, min(5, cur_d['n_sized'] - 1)) and not cur_d.get('suggest'):
                break
            eng, mpp, why = queue.pop(0)
            is_poche = bool(cur_d.get('is_poche'))
            if mpp <= 0 or any((e == eng or is_poche) and abs(mpp / t - 1.0) < 0.02 for e, t in tried):
                continue
            tried.append((eng, mpp))
            runs += 1
            self.options = dict(base_opts, image_mm_per_px=mpp, image_engine=eng, _doc_search=True)
            logger.info('Document scale search: trying %s engine at %.3f mm/px (%s)', eng, mpp, why)
            r2 = self._process(*args)
            if self._doc_quality(r2) > self._doc_quality(best):
                best = r2
                d2 = r2['_doc_pic']
                if d2['suggest']:
                    queue.insert(0, (d2['engine'], d2['suggest'], 'room-size fit refinement'))
        d = best['_doc_pic']
        if runs:
            best['warnings'].insert(0, f"Document: plan picture read with the {'traced CAD line' if d['engine'] == 'lines' else 'raster wall'} "
                                       f"engine at {d['mpp']:.3f} mm/px - best of {runs + 1} scale/engine trials "
                                       f"({d['quality'][0]}/{d['n_sized']} documented rooms matched, {d['quality'][2]} rooms closed)")
        return best

    def _process(self, filepath, wall_height, default_thickness, source_units) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            'ok': False, 'error': '', 'walls': [], 'script': '', 'summary': '', 'warnings': [],
            'wall_json': '', 'wall_csv': '', 'steps': [], 'info': {},
        }
        opts = getattr(self, 'options', {}) or {}
        _orig_args = (filepath, wall_height, default_thickness, source_units)

        def step(name: str, detail: str):
            result['steps'].append({'name': name, 'detail': detail})
            logger.info("%s: %s", name, detail)

        try:
            t0 = time.time()
            imp = CADImporter()
            imp.image_options = {'wall_mm': opts.get('image_wall_mm'), 'mm_per_px': opts.get('image_mm_per_px'),
                                 'engine': opts.get('image_engine')}
            entities = imp.import_file(filepath)
            raster = imp.raster_report if (imp.raster_report or {}).get('engine') == 'raster_walls' else None
            result['raster'] = raster
            result['source_image'] = imp.source_image
            result['layers'] = [{'name': n, 'count': c, 'selected': CADCleaner.is_wall_layer(n)}
                                for n, c in sorted(imp.layer_stats.items(), key=lambda kv: -kv[1])]
            step('1 CAD import', f"{len(entities)} geometry entities on {len(imp.layers)} layers")
            doc = getattr(imp, 'document', None)
            doc_spec = {}
            if doc:
                doc_spec = dict(doc.get('spec') or {})
                applied = list(doc.get('applied', []))
                if doc_spec.get('wall_h'):
                    wall_height = float(doc_spec['wall_h'])
                    applied.append(f'wall height {wall_height:.0f} mm')
                t_int = doc_spec.get('int_wall_t') or doc_spec.get('wall_t')
                if t_int:
                    default_thickness = float(t_int)
                    applied.append(f'default (single-line) wall thickness {default_thickness:.0f} mm')
                doc['applied'] = applied
                sized = sum(1 for e in doc.get('schedule', []) if 'w_mm' in e or 'area_m2' in e)
                step('1b Document reading',
                     f"{doc['file']}: plan from {doc['plan_source']} ({doc['plan_reason']}); "
                     f"{len(doc_spec)} specification value(s) read; room schedule {len(doc.get('schedule', []))} "
                     f"room(s), {sized} with sizes; {doc['paragraph_count']} paragraphs, {doc['table_count']} tables, "
                     f"{doc['picture_count']} pictures")
                result['warnings'].extend(f'Document: {n}' for n in doc.get('notes', []))
            if raster:
                kinds: Dict[str, int] = {}
                for g in raster['gaps']:
                    kinds[g['kind']] = kinds.get(g['kind'], 0) + 1
                step('1a Raster wall detection',
                     f"{len(raster['walls'])} walls, {len(raster['windows'])} window symbols; wall thicknesses "
                     f"{raster['thickness_modes_mm']} mm; scale {raster['mm_per_px']} mm/px ({raster['scale_source']}); "
                     f"gaps: {', '.join(f'{v} {k}' for k, v in sorted(kinds.items())) or 'none'}; "
                     f"{len(raster['rejected'])} furniture-like candidates rejected, {len(raster['isolated'])} isolated "
                     f"groups, {len(raster['trimmed'])} walls trimmed at the image edge")
            if not entities:
                raise RuntimeError("No LINE/POLYLINE/ARC/SPLINE geometry found in the file.")

            norm = UnitNormalizer()
            entities = norm.normalize(entities, source_units, imp.insunits)
            step('2 Units -> mm', f"units {norm.detected}, scale x{norm.scale:g}")

            cleaner = CADCleaner()
            cleaned = cleaner.clean(entities)
            step('3 CAD cleaning', f"kept {len(cleaned)}, removed {len(entities) - len(cleaned)} "
                                   f"(furniture/text/hatch/doors/windows...)")

            # A sheet with several separate drawings (typical floors, unit plan, site plan ...): read one plan only
            if not raster:
                from cad_processor import sheet_splitter
                drawings = sheet_splitter.split_drawings(cleaned)
                if drawings:
                    chosen, why = sheet_splitter.choose_drawing(drawings, opts.get('drawing'))
                    bx0, by0, bx1, by1 = chosen['bbox']
                    m = 1500.0

                    def _in_box(pts, s=1.0):
                        cx = sum(p[0] for p in pts) / len(pts) * s
                        cy = sum(p[1] for p in pts) / len(pts) * s
                        return bx0 - m <= cx <= bx1 + m and by0 - m <= cy <= by1 + m

                    cleaned = [e for e in cleaned if e.points and _in_box(e.points)]
                    entities = [e for e in entities if e.points and _in_box(e.points)]
                    sc0 = norm.scale
                    imp.all_lines = [t for t in imp.all_lines if t[1] and _in_box(t[1], sc0)]
                    imp.labels = [t for t in imp.labels if _in_box([(t[1], t[2])], sc0)]
                    imp.inserts = [t for t in imp.inserts if _in_box([(t[1], t[2])], sc0)]
                    k_ch = drawings.index(chosen)
                    result['drawings'] = [{'index': k, 'w_mm': round(d['w']), 'h_mm': round(d['h']), 'entities': d['n'],
                                           'chosen': k == k_ch} for k, d in enumerate(drawings)]
                    result['warnings'].append(
                        f"The file holds {len(drawings)} separate drawings ({'; '.join(sheet_splitter.describe(drawings))}). "
                        f"Read drawing #{k_ch + 1} ({chosen['w'] / 1000:.1f} x {chosen['h'] / 1000:.1f} m): {why}.")
                    step('3a Sheet drawings', f"{len(drawings)} separate drawings on the sheet; using #{k_ch + 1} "
                                              f"({chosen['w'] / 1000:.1f} x {chosen['h'] / 1000:.1f} m, {len(cleaned)} entities) - {why}")

            detector = WallDetector()
            found = detector.detect_walls(cleaned)
            layers = ', '.join(cleaner.wall_layers) or 'none'
            step('4 Wall detection', f"{detector.method} based; wall layers: {layers}; {len(found)} outlines")
            if not found:
                raise RuntimeError(
                    "No walls found. The file has no WALL-named layer and the geometry fallback found nothing. "
                    f"Layers in file: {', '.join(imp.layers[:25])}")

            walls = WallBuilder().build_walls(found, wall_height, default_thickness)
            step('5 Reconstruction', f"{len(walls)} wall polygons with start/end/length/thickness")

            known = []
            if raster:
                for g in raster['gaps']:
                    if g['kind'] in ('door', 'window', 'opening', 'uncertain'):
                        x0, y0, x1, y1 = g['rect_mm']
                        if g['o'] == 'H':
                            known.append(((x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)))
                        else:
                            known.append((((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)))
            validator = WallValidator()
            conn_tol = opts.get('conn_tol')
            if not conn_tol and getattr(imp, 'vector_report', None) and imp.image_options.get('engine') == 'lines':
                # lines traced from a picture end within +-1.5 px of the true corner: close junction gaps
                # up to about one wall thickness (real openings are >= 450 mm)
                conn_tol = max(100.0, min(160.0, 12.0 * float(imp.image_options.get('mm_per_px') or 10.0)))
            walls, warns = validator.validate(walls, conn_tol=conn_tol, known_openings=known,
                                              mm_per_px=(raster or {}).get('mm_per_px'))
            topology = getattr(validator, 'topology', {}) or {}
            result['warnings'].extend(warns)
            step('6 Validation & connections', f"{len(walls)} walls after fixes; connection tolerance "
                                               f"{topology.get('conn_tol_mm', 0):.0f} mm; repairs {topology.get('counts', {})}; "
                                               f"{len(topology.get('uncertain', []))} uncertain gap(s) left open")

            exporter = WallDataExporter()
            walls, offset = exporter.recenter_and_number(walls)
            cls = exporter.classify_walls(walls)
            step('7 Wall data', f"{len(cls['exterior'])} exterior, {len(cls['interior'])} interior walls")

            from shapely.affinity import translate as _T
            from shapely.geometry import LineString as _L
            from shapely.geometry import Polygon as _P
            from shapely.ops import unary_union as _U
            from cad_processor import architecture as arch

            # CAD linework around the plan (recentred) - used by opening detection and the AI reviewer
            zx = [x for w in walls for x, _ in w.polygon]
            zy = [y for w in walls for _, y in w.polygon]
            lo_x, hi_x, lo_y, hi_y = min(zx) - 2500, max(zx) + 2500, min(zy) - 2500, max(zy) + 2500
            under = []
            for e in entities:
                if e.entity_type == 'HATCH' or len(e.points) < 2:
                    continue
                pts = [(x - offset[0], y - offset[1]) for x, y in e.points]
                if e.is_closed:
                    pts.append(pts[0])
                for p0, p1 in zip(pts, pts[1:]):
                    if lo_x <= p0[0] <= hi_x and lo_y <= p0[1] <= hi_y:
                        under.append((p0[0], p0[1], p1[0], p1[1]))
                if len(under) > 40000:
                    break
            result['underlay'] = under

            # Evidence for opening / room detection: window symbols, WIN/DOOR layer hints, labels, blocks
            plan_zone = _U([_P(w.polygon).buffer(6000) for w in walls])
            window_polys = [_T(w['poly'], xoff=-offset[0], yoff=-offset[1]) for w in getattr(detector, 'windows', [])]
            filler = OpeningFiller()
            for r in filler.window_runs(walls, entities, offset, wall_height, []):
                rp = _P(r.polygon)
                if plan_zone.intersects(rp) and not any(rp.equals_exact(q, 1.0) for q in window_polys):
                    window_polys.append(rp)
            win_hint, door_hint, door_arcs = [], [], []
            import math as _math
            for e in entities:
                if len(e.points) < 2:
                    continue
                up = e.layer.upper()
                if 'WIN' in up or 'GLASS' in up or 'DOOR' in up or 'PARAPET' in up or 'RAILING' in up:
                    g = _L([(x - offset[0], y - offset[1]) for x, y in e.points])
                    (door_hint if 'DOOR' in up else win_hint).append(g)
                    if e.entity_type == 'ARC' and 'DOOR' in up and len(e.points) >= 5:
                        pts = e.points
                        arc_len = sum(_math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
                        chord = _math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
                        if chord > 100.0 and 1.04 <= arc_len / chord <= 1.25:
                            rad = chord / 1.41421356
                            if 400.0 <= rad <= 1400.0:
                                p0_a = (pts[0][0] - offset[0], pts[0][1] - offset[1])
                                p1_a = (pts[-1][0] - offset[0], pts[-1][1] - offset[1])
                                pm_a = (pts[len(pts) // 2][0] - offset[0], pts[len(pts) // 2][1] - offset[1])
                                mx_a, my_a = 0.5 * (p0_a[0] + p1_a[0]), 0.5 * (p0_a[1] + p1_a[1])
                                dx_a, dy_a = p1_a[0] - p0_a[0], p1_a[1] - p0_a[1]
                                h_a = _math.sqrt(max(0.0, rad * rad - 0.25 * chord * chord))
                                nx_a, ny_a = -dy_a / chord, dx_a / chord
                                c_pos = (mx_a + h_a * nx_a, my_a + h_a * ny_a)
                                c_neg = (mx_a - h_a * nx_a, my_a - h_a * ny_a)
                                c_a = min((c_pos, c_neg), key=lambda c: abs(_math.hypot(pm_a[0] - c[0], pm_a[1] - c[1]) - rad))
                                door_arcs.append((c_a, p0_a, p1_a, rad))
                elif e.entity_type == 'ARC' and len(e.points) >= 5:
                    pts = e.points
                    arc_len = sum(_math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
                    chord = _math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
                    if chord > 100.0 and 1.04 <= arc_len / chord <= 1.25:
                        rad = chord / 1.41421356
                        if 400.0 <= rad <= 1400.0:
                            door_hint.append(_L([(x - offset[0], y - offset[1]) for x, y in pts]))
                            p0_a = (pts[0][0] - offset[0], pts[0][1] - offset[1])
                            p1_a = (pts[-1][0] - offset[0], pts[-1][1] - offset[1])
                            pm_a = (pts[len(pts) // 2][0] - offset[0], pts[len(pts) // 2][1] - offset[1])
                            mx_a, my_a = 0.5 * (p0_a[0] + p1_a[0]), 0.5 * (p0_a[1] + p1_a[1])
                            dx_a, dy_a = p1_a[0] - p0_a[0], p1_a[1] - p0_a[1]
                            h_a = _math.sqrt(max(0.0, rad * rad - 0.25 * chord * chord))
                            nx_a, ny_a = -dy_a / chord, dx_a / chord
                            c_pos = (mx_a + h_a * nx_a, my_a + h_a * ny_a)
                            c_neg = (mx_a - h_a * nx_a, my_a - h_a * ny_a)
                            c_a = min((c_pos, c_neg), key=lambda c: abs(_math.hypot(pm_a[0] - c[0], pm_a[1] - c[1]) - rad))
                            door_arcs.append((c_a, p0_a, p1_a, rad))
            sc = norm.scale
            shaft_pts = [(x - offset[0], y - offset[1], 99999.0) for x, y in getattr(detector, 'shaft_points', [])]
            if not shaft_pts and getattr(imp, 'all_lines', None):
                diags = []
                for lay, pts, _ in imp.all_lines:
                    if 'FURN' in lay.upper():
                        continue
                    for p0, p1 in zip(pts, pts[1:]):
                        x0, y0 = p0[0] * sc - offset[0], p0[1] * sc - offset[1]
                        x1, y1 = p1[0] * sc - offset[0], p1[1] * sc - offset[1]
                        if not (lo_x <= x0 <= hi_x and lo_y <= y0 <= hi_y):
                            continue
                        dx, dy = abs(x1 - x0), abs(y1 - y0)
                        L = _math.hypot(dx, dy)
                        if 400.0 <= L <= 8000.0 and 0.2 <= dx / max(dy, 1e-6) <= 5.0:
                            ang = _math.atan2(y1 - y0, x1 - x0) % _math.pi
                            diags.append(((x0 + x1) * 0.5, (y0 + y1) * 0.5, ang, L))
                for i in range(len(diags)):
                    mx1, my1, a1, L1 = diags[i]
                    for j in range(i + 1, len(diags)):
                        mx2, my2, a2, L2 = diags[j]
                        if _math.hypot(mx1 - mx2, my1 - my2) <= 100.0 and abs(a1 - a2) > 0.35:
                            shaft_pts.append(((mx1 + mx2) * 0.5, (my1 + my2) * 0.5, max(L1, L2)))
                            break
            det_posts = [_T(p, xoff=-offset[0], yoff=-offset[1]) for p in getattr(detector, 'corner_posts', [])]
            ctx = {
                'underlay': under, 'window_polys': window_polys,
                'parapet_polys': [p for p in getattr(filler, 'parapet_polys', []) if plan_zone.intersects(p)],
                'corner_posts': [p for p in det_posts + list(getattr(filler, 'corner_posts', [])) if plan_zone.intersects(p)],
                'win_hint': _U(win_hint) if win_hint else None, 'door_hint': _U(door_hint) if door_hint else None,
                'door_arcs': door_arcs,
                'shaft_points': shaft_pts,
                'labels': [(t, x * sc - offset[0], y * sc - offset[1]) for t, x, y in imp.labels],
                'inserts': [(b, x * sc - offset[0], y * sc - offset[1]) for b, x, y in imp.inserts],
            }
            spec = dict(arch.SPEC, wall_h=float(wall_height))
            if doc:
                for k in ('door_head', 'win_sill', 'win_h', 'vent_sill', 'vent_h', 'slab_t', 'skirt_h'):
                    if doc_spec.get(k) is not None:
                        spec[k] = float(doc_spec[k])
                        doc['applied'].append(f'{k} {spec[k]:.0f} mm')
                if doc_spec.get('win_sill') is not None and doc_spec.get('win_h') is None:
                    spec['win_h'] = max(300.0, spec['door_head'] - spec['win_sill'])   # window heads align with door heads
                if doc_spec.get('vent_sill') is not None and doc_spec.get('vent_h') is None:
                    spec['vent_h'] = max(300.0, spec['door_head'] - spec['vent_sill'])
                if doc_spec.get('vent_h') is not None and doc_spec.get('vent_sill') is None:
                    spec['vent_sill'] = max(0.0, spec['door_head'] - spec['vent_h'])
                for a, b in (('win_sill', 'win_h'), ('vent_sill', 'vent_h')):
                    if spec[a] + spec[b] > spec['wall_h'] - 50.0:
                        spec[b] = max(300.0, spec['wall_h'] - 50.0 - spec[a])
                spec['door_head'] = min(spec['door_head'], spec['wall_h'] - 50.0)
                spec['lintel_h'] = spec['wall_h'] - spec['door_head']
                ctx['schedule'] = list(doc.get('schedule') or [])
                ctx['schedule_allow_scale'] = (doc.get('plan_kind') == 'image'
                                               and (not opts.get('image_mm_per_px') or bool(opts.get('_doc_search'))))
            openings, fills, posts, op_notes = arch.detect_openings(walls, ctx, spec)
            dropped = set(ctx.get('dropped_wall_ids', []))
            walls = [w for w in walls if w.id not in dropped] + posts
            result['warnings'].extend(op_notes)
            if raster:
                extra = []
                for g in raster['gaps']:
                    if g['kind'] != 'door':
                        continue
                    x0, y0, x1, y1 = g['rect_mm']
                    x0, x1, y0, y1 = x0 - offset[0], x1 - offset[0], y0 - offset[1], y1 - offset[1]
                    if g['o'] == 'H':
                        p0, p1, t = (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2), abs(y1 - y0)
                    else:
                        p0, p1, t = ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1), abs(x1 - x0)
                    cand = arch.Opening('', 'door' if _math.dist(p0, p1) <= spec['door_max'] else 'passage',
                                        p0, p1, t, 0.0, spec['door_head'], 'raster door swing')
                    r = cand.rect()
                    if any(o.rect().intersection(r).area > 0.3 * r.area for o in openings + extra):
                        continue
                    if any(_P(w.polygon).intersection(r).area > 0.3 * r.area for w in walls):
                        continue
                    extra.append(cand)
                if extra:
                    for k, o in enumerate(extra):
                        o.id = f"{'Door' if o.type == 'door' else 'Passage'}_R{k + 1:02d}"
                    openings += extra
                    fills += arch.opening_pieces(extra, spec)
                    result['warnings'].append(f'{len(extra)} door(s) proven by a swing arc in the image added as openings')
            # openings that coincide with a gap the detector could not prove -> keep open, flag for review
            unc_zones = []
            for g in (raster or {}).get('gaps', []):
                if g['kind'] == 'uncertain':
                    x0, y0, x1, y1 = g['rect_mm']
                    unc_zones.append((g['id'], _P([(x0 - offset[0], y0 - offset[1]), (x1 - offset[0], y0 - offset[1]),
                                                   (x1 - offset[0], y1 - offset[1]), (x0 - offset[0], y1 - offset[1])])))
            for k, u in enumerate(topology.get('uncertain', [])):
                unc_zones.append((f'TOP_{k + 1:02d}', _L([(u['p0'][0] - offset[0], u['p0'][1] - offset[1]),
                                                          (u['p1'][0] - offset[0], u['p1'][1] - offset[1])]).buffer(60)))
            for o in openings:
                r = o.rect()
                for gid, z in unc_zones:
                    if r.intersects(z) and r.intersection(z).area > 0.3 * min(r.area, z.area):
                        o.notes.append(f'UNCERTAIN ({gid}): the drawing does not prove this is an opening - '
                                       f'left open, confirm or close it in the review')
                        result['warnings'].append(f'Review: {o.type} {o.width:.0f} mm at '
                                                  f'({(o.p0[0] + o.p1[0]) / 2:.0f},{(o.p0[1] + o.p1[1]) / 2:.0f}) is uncertain ({gid})')
            by_type = {}
            for o in openings:
                by_type[o.type] = by_type.get(o.type, 0) + 1
            step('7a Openings', ', '.join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in sorted(by_type.items())) +
                 f"; {len(posts)} CAD post(s); door head {spec['door_head']:.0f}, window {spec['win_sill']:.0f}-"
                 f"{spec['win_sill'] + spec['win_h']:.0f}, ventilator {spec['vent_sill']:.0f}-{spec['vent_sill'] + spec['vent_h']:.0f} mm")

            # Image segmentation of the full drawing for room analysis & validation
            try:
                from cad_processor.segmentation import segment
                non_arch_kw = (
                    'DIM', 'TEXT', 'TXT', 'ANNO', 'FURN', 'ELEC', 'SYMB', 'NOTE', 'DEFPOINTS',
                    'TITLE', 'GRID', 'AXIS', 'SANIT', 'FIXT', 'STAIR', 'ELEV', 'DOTTED',
                    'PLANT', 'TREE', 'AREA', 'LEVEL', 'HIDDEN', 'TREAT', 'PANEL', 'CHANDELIER',
                    'LELVEL', 'DT-', 'WD_', 'AUDIT', 'LIGHT', 'SANI', 'KITCH'
                )
                seg_lines = [(lay, [(x * sc - offset[0], y * sc - offset[1]) for x, y in pts], cl)
                             for lay, pts, cl in imp.all_lines if not any(k in lay.upper() for k in non_arch_kw)]
                seg = segment(seg_lines, walls)
                result['segmentation'] = seg
                sm = seg['summary']
                step('7d Layout analysis', f"{sm['rooms']} rooms, {sm['wall_bands']} wall bands; "
                     f"{sm['confirmed_walls']}/{len(walls)} walls confirmed by plan analysis")
            except Exception as ex:                                  # never break the scan
                logger.exception('segmentation failed')
                result['warnings'].append(f'Layout analysis skipped: {ex}')

            # 3D overlap resolution and clean piece filtering (removes tiny slivers and booleans colliding pieces)
            all_pieces = self._resolve_3d_overlaps(walls + fills)
            clean_pieces = [p for p in all_pieces if _P(p.polygon).area >= 1e4 and not (p.length < 100.0 and p.kind == 'wall')]
            walls = [p for p in clean_pieces if p.kind == 'wall']
            fills = [p for p in clean_pieces if p.kind != 'wall']
            n = 0
            for w in walls:                       # opening pieces and posts keep their descriptive ids
                if w.layer != 'POST':
                    n += 1
                    w.id = f"Wall_{n:03d}"
            step('7b Opening pieces', f"{len(fills)} sill/head pieces (walls stop at every opening; "
                                      f"pieces fill only the solid parts below and above the clear opening)")

            # Final exterior/interior classification & vector footprint
            cls = exporter.classify_walls(walls, fills, under)
            result['outline'] = exporter.outline
            step('7c Classification', f"{len(cls['exterior'])} exterior, {len(cls['interior'])} interior "
                                      f"(wall faces probed against the closed building footprint)")

            # Rooms, washrooms, skirting and individual wall tiles
            analysis = arch.analyse(walls, fills, openings, result['outline'], ctx, spec)
            analysis['glass_partitions'] = list(ctx.get('glass_partitions', []))
            rep = analysis['report']
            ds = rep.get('document_schedule')
            if doc and doc.get('plan_kind') == 'image':
                n_sized = sum(1 for e in doc.get('schedule', []) if 'w_mm' in e or 'area_m2' in e)
                matched = (ds or {}).get('matched', [])
                engine = 'raster' if raster else ('lines' if imp.image_options.get('engine') == 'lines' else 'raster')
                mpp = float((raster or {}).get('mm_per_px') or imp.image_options.get('mm_per_px') or 0.0)
                n_rooms = sum(1 for rm in analysis['rooms'] if rm['area_m2'] >= 2.0 and rm['type'] not in ('shaft', 'external'))
                scale_err = abs(_math.log(max(float((ds or {}).get('scale') or 1.0), 1e-3)))
                result['_doc_pic'] = {
                    'engine': engine, 'mpp': mpp,
                    'is_poche': bool((getattr(imp, 'vector_report', None) or {}).get('engine') == 'poche'
                                     or any(w.get('src') == 'poche' for w in (raster or {}).get('walls', []))),
                    'quality': (len(matched), round(-sum(m['cost'] for m in matched) / max(len(matched), 1) - 2.0 * scale_err, 3), n_rooms),
                    'n_sized': n_sized,
                    'suggest': (mpp * float(ds['scale']) if ds and ctx.get('schedule_allow_scale')
                                and abs(ds['scale'] - 1.0) > 0.02 and mpp else None),
                    'options': list(doc.get('scale_options', [])),
                    'modes_mm': list((raster or {}).get('thickness_modes_mm') or []),
                    'ext_t': doc_spec.get('ext_wall_t') or doc_spec.get('wall_t'),
                    'int_t': doc_spec.get('int_wall_t') or doc_spec.get('wall_t'),
                }
            if doc:
                if doc.get('plan_kind') == 'image':
                    if raster:
                        doc.setdefault('applied', []).append(
                            f"plan picture read with the raster wall engine at {float(raster.get('mm_per_px') or 0):.3f} mm/px "
                            f"({raster.get('scale_source', '')})")
                    else:
                        vr = getattr(imp, 'vector_report', None) or {}
                        doc.setdefault('applied', []).append(
                            f"plan picture traced into {vr.get('lines', 0)} CAD lines at {float(imp.image_options.get('mm_per_px') or 0):.3f} "
                            f"mm/px and read with the CAD wall engine")
                result['document'] = {
                    'file': doc['file'], 'plan_source': doc['plan_source'], 'plan_kind': doc['plan_kind'],
                    'plan_reason': doc['plan_reason'], 'spec': doc_spec, 'spec_found': doc.get('spec_found', []),
                    'applied': doc.get('applied', []), 'schedule': doc.get('schedule', []),
                    'schedule_match': ds or {}, 'notes': doc.get('notes', []), 'unit_hint': doc.get('unit_hint'),
                    'counts': {'paragraphs': doc['paragraph_count'], 'tables': doc['table_count'],
                               'pictures': doc['picture_count'], 'cad': doc['cad_count']},
                }
                if ds:
                    step('7g Document room schedule',
                         f"{len(ds['matched'])}/{len(doc.get('schedule', []))} documented rooms placed on the plan"
                         + (f" (scale x{ds['scale']:.3f})" if abs(ds['scale'] - 1.0) > 1e-6 else '')
                         + ('; ' + ', '.join(f"{m['name']} -> {m['room']}" for m in ds['matched'][:12]) if ds['matched'] else ''))
                    for e in ds.get('unmatched', []):
                        result['warnings'].append(f"Document: room '{e['name']}' from the schedule could not be matched to a "
                                                  f"room on the plan{' (no size given)' if 'w_mm' not in e and 'area_m2' not in e else ''}")
            washrooms = [r['name'] for r in analysis['rooms'] if r['type'] == 'washroom']
            step('7e Rooms', f"{len(analysis['rooms'])} rooms; washrooms: {', '.join(washrooms) or 'none'}; "
                             f"{len(rep['ambiguities'])} item(s) for review")
            step('7f Skirting & tiles', f"{len(analysis['skirting'])} skirting runs ({spec['skirt_h']} x {spec['skirt_t']:.0f} mm, "
                                        f"{rep['skirting']['total_length_m']} m); {len(analysis['tiles'])} individual wall tiles "
                                        f"({spec['tile_w']} x {spec['tile_h']} mm, {spec['grout']} mm joints)")
            result['warnings'].extend(rep['warnings'])
            result['warnings'].extend(f'Review: {a}' for a in rep['ambiguities'])
            result['_arch_ctx'] = ctx
            result['_spec'] = spec
            result['_openings'] = openings

            fills = arch.sync_opening_pieces(openings, fills, spec)
            all_pieces = walls + fills
            script = BlenderScriptGenerator().generate_script(
                all_pieces, clear_scene=True, outline=result['outline'], arch=analysis, underlay=under, spec=spec)
            step('8-10 Blender script', f"{len(all_pieces)} separate editable wall & opening meshes in "
                                        f"01_Structure > WALLS + 02_Openings > LINTELS (clean quad/planar topology)")

            result.update({
                'ok': True, 'walls': all_pieces, 'script': script,
                'summary': exporter.to_summary(all_pieces), 'wall_json': exporter.to_json(all_pieces),
                'wall_csv': exporter.to_csv(all_pieces),
                'architecture': analysis,
                'skirting': [s['ring'] for s in analysis['skirting']],
                'washroom_voids': [r['ring'] for r in analysis['rooms'] if r['type'] == 'washroom'],
                'washroom_tiles': analysis['tiles'],
            })
            xs = [x for w in walls for x, _ in w.polygon]
            ys = [y for w in walls for _, y in w.polygon]
            result['info'] = {
                'units': norm.detected, 'wall_layers': cleaner.wall_layers,
                'offset_mm': [round(offset[0], 1), round(offset[1], 1)],
                'width_mm': round(max(xs)), 'depth_mm': round(max(ys)),
                'total_length_m': round(sum(w.length for w in walls) / 1000, 2),
                'seconds': round(time.time() - t0, 1),
            }
            result['_offset'] = offset
            result['_topology'] = topology
            result['_raster'] = raster
            result['_source_image'] = imp.source_image if raster else ''
            try:
                from cad_processor import detection_review
                review = detection_review.run(result, offset, raster=raster, topology=topology,
                                              source_image=imp.source_image if raster else '',
                                              conn_tol=topology.get('conn_tol_mm') or 100.0,
                                              modes_mm=(raster or {}).get('thickness_modes_mm'))
                result['review'] = review
                sm = review['summary']
                step('11 Detection review', f"{sm['PASS']} checks passed, {sm['WARN']} warnings, {sm['FAIL']} failed; "
                     f"{len(review['uncertain'])} uncertain gap(s), {len(review['repairs'])} repaired connection(s)")
            except Exception as ex:
                logger.exception('detection review failed')
                result['warnings'].append(f'Detection review skipped: {ex}')
            refs = [r for r in (opts.get('references') or []) if r]
            if refs:
                try:
                    from cad_processor import reference
                    comp = reference.compare_all(refs, result, offset, raster=raster,
                                                 mode=opts.get('reference_mode', 'validate'))
                    result['references'] = comp
                    for c in comp.get('results', []):
                        step('12 Reference', f"{c.get('name')}: {c.get('summary', c.get('error', ''))}")
                except Exception as ex:
                    logger.exception('reference comparison failed')
                    result['warnings'].append(f'Reference comparison skipped: {ex}')
        except Exception as e:
            logger.exception("Pipeline failed")
            result['error'] = str(e)
        return result

    @staticmethod
    def _resolve_3d_overlaps(pieces: list) -> list:
        """
        Ensures NO two pieces overlap in 3D space:
        Walls and structural columns take precedence over sills/lintels.
        Overlapping 3D volumes are cleanly boolean-subtracted so meshes
        never collide, penetrate, or cause Z-fighting in Blender.
        """
        import copy
        import math
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        import shapely.validation
        out = []
        placed = []

        def priority_key(w):
            is_col = 'COL' in getattr(w, 'layer', '').upper()
            is_wall = (getattr(w, 'kind', 'wall') == 'wall')
            is_rec = (getattr(w, 'layer', '') == 'RECOVERED')
            p = 0 if is_col else (1 if is_wall and not is_rec else (2 if is_rec else (3 if w.kind == 'sill' else 4)))
            return (p, -getattr(w, 'length', 0))

        pieces_sorted = sorted(pieces, key=priority_key)
        for w in pieces_sorted:
            poly = Polygon(w.polygon).buffer(0)
            if poly.is_empty or poly.area < 1.0e4:
                continue
            z0, z1 = w.base, w.base + w.height
            z_overl = [p for p, b, h in placed if not (z1 <= b + 1e-2 or b + h <= z0 + 1e-2) and poly.intersects(p)]
            if z_overl:
                blocker = unary_union(z_overl)
                diff = poly.difference(blocker)
                if not diff.is_valid:
                    diff = shapely.validation.make_valid(diff)
                if diff.is_empty or diff.area < 1.0e4:
                    continue
            else:
                diff = poly

            if diff.geom_type == 'Polygon':
                geoms = [diff]
            elif hasattr(diff, 'geoms'):
                geoms = [g for g in diff.geoms if g.geom_type == 'Polygon' and g.area >= 1.0e4]
            else:
                geoms = []

            for idx, g in enumerate(geoms):
                g = g.simplify(0.5, preserve_topology=True)
                coords = [(round(x, 1), round(y, 1)) for x, y in list(g.exterior.coords)[:-1]]
                clean_coords = []
                for pt in coords:
                    if not clean_coords or math.hypot(pt[0] - clean_coords[-1][0], pt[1] - clean_coords[-1][1]) > 1.0:
                        clean_coords.append(pt)
                if len(clean_coords) > 1 and math.hypot(clean_coords[0][0] - clean_coords[-1][0], clean_coords[0][1] - clean_coords[-1][1]) <= 1.0:
                    clean_coords.pop()
                # Strip collinear or 180-degree folded spike vertices without shifting coordinates
                changed = True
                while changed and len(clean_coords) >= 3:
                    changed = False
                    n_pts = len(clean_coords)
                    for k in range(n_pts):
                        a = clean_coords[(k - 1) % n_pts]
                        b = clean_coords[k]
                        c = clean_coords[(k + 1) % n_pts]
                        v1x, v1y = b[0] - a[0], b[1] - a[1]
                        v2x, v2y = c[0] - b[0], c[1] - b[1]
                        l1 = math.hypot(v1x, v1y)
                        l2 = math.hypot(v2x, v2y)
                        if l1 <= 1.0 or l2 <= 1.0 or abs(v1x * v2y - v1y * v2x) / (l1 * l2) < 1e-3:
                            clean_coords.pop(k)
                            changed = True
                            break
                if len(clean_coords) >= 3:
                    piece = copy.copy(w)
                    if idx > 0:
                        piece.id = f"{w.id}_{idx+1}"
                    piece.polygon = clean_coords
                    out.append(piece)
                    placed.append((g, z0, z1))
        return out


