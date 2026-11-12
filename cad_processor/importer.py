import glob
import logging
import math
import os
import shutil
import subprocess
import tempfile
from typing import List, Tuple

import ezdxf

from .models import CADEntity

logger = logging.getLogger(__name__)


class CADImporter:
    """STEP 1 - read DXF (and DWG via ODA File Converter) into CADEntity list."""

    def __init__(self, arc_segments: int = 32, spline_segments: int = 64):
        self.arc_segments = arc_segments
        self.spline_segments = spline_segments
        self.insunits = 0          # $INSUNITS of the file (0 = unspecified)
        self.layers: List[str] = []
        self.all_lines: list = []       # (layer, points, closed) for EVERY layer - used by image segmentation
        self.layer_stats: dict = {}     # layer -> entity count (everything in the file, incl. block contents)
        self.labels: list = []          # (text, x, y) raw drawing units - room names such as TOILET / BED / KITCHEN
        self.inserts: list = []         # (block_name, x, y) raw drawing units - fixture symbols (WC, basin, ...)
        self.image_options: dict = {}   # raster input: {'wall_mm': .., 'mm_per_px': ..}
        self.raster_report = None       # review report written by the raster wall engine
        self.source_image = ''          # raster file actually vectorised (for previews)
        self.document = None            # Word document reading (plan source, specification, room schedule)

    # ── DWG ───────────────────────────────────────────────
    @staticmethod
    def _find_oda() -> str:
        exe = shutil.which("ODAFileConverter")
        if exe:
            return exe
        patterns = [
            r"C:\Program Files\ODA\*\ODAFileConverter.exe",
            r"C:\Program Files (x86)\ODA\*\ODAFileConverter.exe",
        ]
        for pat in patterns:
            hits = glob.glob(pat)
            if hits:
                return hits[0]
        return ""

    @staticmethod
    def _find_libredwg() -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        hits = glob.glob(os.path.join(base, "tools", "libredwg", "**", "dwg2dxf.exe"), recursive=True)
        return hits[0] if hits else (shutil.which("dwg2dxf") or "")

    def _convert_with_libredwg(self, filepath: str) -> str:
        exe = self._find_libredwg()
        if not exe:
            return ""
        out_dir = tempfile.mkdtemp(prefix="dwg2dxf_")
        out = os.path.join(out_dir, os.path.splitext(os.path.basename(filepath))[0] + ".dxf")
        try:
            # NOTE: "--as r2000" silently empties dynamic/anonymous blocks (walls inside them were lost);
            # r2004 output keeps every block, matching an AutoCAD-saved DXF entity for entity.
            subprocess.run([exe, "-y", "--as", "r2004", "-o", out, filepath],
                           capture_output=True, timeout=900)
        except Exception as ex:
            logger.warning("libredwg failed: %s", ex)
            return ""
        return out if os.path.exists(out) and os.path.getsize(out) > 1000 else ""

    def _convert_dwg(self, filepath: str) -> str:
        cached = os.path.splitext(os.path.abspath(filepath))[0] + ".dxf"
        if os.path.exists(cached) and os.path.getsize(cached) > 1000:
            logger.info("Using cached DXF for DWG: %s", cached)
            return cached
        out = self._convert_with_libredwg(filepath)
        if out:
            try:
                shutil.copy2(out, cached)
                out = cached
            except Exception as ex:
                logger.debug("Could not cache DXF at %s: %s", cached, ex)
            logger.info("DWG converted with LibreDWG -> %s", out)
            return out
        # Fallback: check if matching DXF already exists in uploads
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        # strip timestamp prefix if present
        clean_name = base_name.split('_', 1)[-1] if '_' in base_name else base_name
        uploads_dir = os.path.dirname(os.path.abspath(filepath))
        candidates = glob.glob(os.path.join(uploads_dir, f"*{clean_name}*.dxf")) if clean_name else []
        for cand in candidates:
            if os.path.exists(cand) and os.path.getsize(cand) > 1000:
                logger.info("Using matching DXF fallback for DWG: %s", cand)
                return cand

        exe = self._find_oda()
        if not exe:
            raise RuntimeError(
                "Could not convert this DWG automatically. Install the free 'ODA File Converter' "
                "(opendesign.com/guestfiles/oda_file_converter), or save the drawing as DXF "
                "(AutoCAD: SAVEAS > DXF) and upload that."
            )
        in_dir = os.path.dirname(os.path.abspath(filepath))
        out_dir = tempfile.mkdtemp(prefix="dwg2dxf_")
        name = os.path.basename(filepath)
        subprocess.run([exe, in_dir, out_dir, "ACAD2018", "DXF", "0", "1", name],
                       check=True, capture_output=True, timeout=600)
        out = os.path.join(out_dir, os.path.splitext(name)[0] + ".dxf")
        if not os.path.exists(out):
            raise RuntimeError("ODA File Converter did not produce a DXF.")
        return out

    @staticmethod
    def _find_blender() -> str:
        exe = shutil.which("blender")
        if exe:
            return exe
        patterns = [
            r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
            r"C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe",
        ]
        for pat in patterns:
            hits = glob.glob(pat)
            if hits:
                return hits[0]
        return ""

    IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    DOC_EXTS = (".docx", ".docm", ".dotx", ".dotm", ".doc", ".rtf", ".odt", ".pdf")

    def _read_document(self, filepath: str) -> str:
        """Word document -> plan file to vectorise (embedded DXF/DWG or the best plan picture).
        The written specification and room schedule are kept in self.document for the pipeline."""
        from .document_reader import read_document, CARPET_TO_FOOTPRINT
        doc = read_document(filepath)
        self.document = doc
        spec = doc.get('spec', {})
        doc['scale_options'] = []
        if doc['plan_kind'] == 'image':
            from .line_vectorizer import estimate_wall_px
            cands = []
            if doc.get('plan_dpi') and spec.get('scale'):
                # vector PDF page rendered at a known DPI + the drawing scale written on the sheet
                mpp = 25.4 / float(doc['plan_dpi']) * float(spec['scale'])
                cands.append({'engine': 'lines', 'mm_per_px': round(mpp, 4),
                              'label': f"drawing scale 1:{spec['scale']:.0f} on a page rendered at {doc['plan_dpi']:.0f} dpi "
                                       f"(traced CAD lines)"})
            if doc.get('footprint_px', 0) > 0 and doc.get('schedule_sized', 0) >= 3 and doc.get('schedule_area_m2', 0) >= 20.0:
                mpp = math.sqrt(doc['schedule_area_m2'] * 1e6 / CARPET_TO_FOOTPRINT / doc['footprint_px'])
                lbl = (f"room schedule area {doc['schedule_area_m2']:.1f} m2 vs plan footprint "
                       f"{doc['footprint_px']:.0f} px")
                cands.append({'engine': 'lines', 'mm_per_px': round(mpp, 4), 'label': lbl + ' (traced CAD lines)'})
                cands.append({'engine': 'raster', 'mm_per_px': round(mpp, 4), 'label': lbl + ' (raster walls)'})
            wall_px = estimate_wall_px(doc['plan_path'])
            doc['wall_px'] = wall_px
            t_ext = spec.get('ext_wall_t') or spec.get('wall_t')
            t_int = spec.get('int_wall_t') or spec.get('wall_t')
            if wall_px >= 3:
                for t, lbl in ((t_ext, 'external'), (t_int, 'internal')):
                    if t:
                        cands.append({'engine': 'lines', 'mm_per_px': round(float(t) / wall_px, 4),
                                      'label': f'{lbl} wall {t:.0f} mm = {wall_px:.0f} px wall band (traced CAD lines)'})
                if not (t_ext or t_int):
                    for t in (150.0, 230.0, 115.0):
                        cands.append({'engine': 'lines', 'mm_per_px': round(t / wall_px, 4),
                                      'label': f'assumed {t:.0f} mm wall = {wall_px:.0f} px wall band (traced CAD lines)'})
            if t_ext:
                cands.append({'engine': 'raster', 'wall_mm': float(t_ext),
                              'label': f'main wall thickness from the document = {t_ext:.0f} mm (raster walls)'})
            doc['scale_options'] = cands
            if cands and not self.image_options.get('wall_mm') and not self.image_options.get('mm_per_px'):
                for k in ('mm_per_px', 'wall_mm', 'engine'):
                    if k in cands[0]:
                        self.image_options[k] = cands[0][k]
                doc.setdefault('applied', []).append(f"plan scale from {cands[0]['label']}")
            elif self.image_options.get('mm_per_px'):
                mpp, eng = float(self.image_options['mm_per_px']), self.image_options.get('engine') or 'raster'
                hit = next((c for c in cands if c.get('engine') == eng and c.get('mm_per_px')
                            and abs(c['mm_per_px'] / mpp - 1.0) < 0.02), None)
                doc.setdefault('applied', []).append(
                    f"plan scale from {hit['label']}" if hit else
                    f"plan scale {mpp:.3f} mm/px refined so the detected rooms fit the documented room sizes")
        return doc['plan_path']

    def _convert_image(self, filepath: str) -> str:
        import json
        from .image_importer import image_to_dxf
        out_dir = tempfile.mkdtemp(prefix="img2dxf_")
        out_dxf = os.path.join(out_dir, os.path.splitext(os.path.basename(filepath))[0] + ".dxf")
        doc_labels = (self.document or {}).get('plan_labels')
        if self.image_options.get('engine') == 'lines' and self.image_options.get('mm_per_px'):
            from .line_vectorizer import picture_to_lines_dxf
            self.vector_report = picture_to_lines_dxf(
                filepath, out_dxf, float(self.image_options['mm_per_px']), text_labels=doc_labels
            )
            self.source_image = filepath
            if (self.vector_report or {}).get('engine') == 'poche':
                try:
                    with open(out_dxf + '.review.json', encoding='utf-8') as fh:
                        self.raster_report = json.load(fh)
                except (OSError, ValueError):
                    self.raster_report = None
            else:
                self.raster_report = None
            return out_dxf
        opts = dict(self.image_options)
        if doc_labels:
            opts['text_labels'] = doc_labels
        out = image_to_dxf(filepath, out_dxf, opts)
        self.source_image = filepath
        try:
            with open(out + '.review.json', encoding='utf-8') as fh:
                self.raster_report = json.load(fh)
        except (OSError, ValueError):
            self.raster_report = None
        return out

    def _find_matching_image_for_fbx(self, filepath: str) -> str:
        uploads_dir = os.path.dirname(os.path.abspath(filepath))
        base = os.path.splitext(os.path.basename(filepath))[0]
        clean = base.split("_", 1)[-1] if "_" in base else base
        if clean.lower().startswith("imagetostl.com_"):
            clean = clean[len("imagetostl.com_"):]
        for ext in self.IMAGE_EXTS:
            for pat in (f"*{clean}*{ext}", f"*{ext}"):
                hits = sorted(glob.glob(os.path.join(uploads_dir, pat)), key=os.path.getmtime, reverse=True)
                for h in hits:
                    if os.path.isfile(h) and os.path.getsize(h) > 500:
                        return h
        return ""

    def _convert_fbx(self, filepath: str) -> str:
        # Check if this FBX is an ImageToStl heightmap relief or flat image plane with a matching image
        base_lower = os.path.basename(filepath).lower()
        if "imagetostl.com_" in base_lower:
            img_cand = self._find_matching_image_for_fbx(filepath)
            if img_cand:
                logger.info("Using source floor plan image %s for ImageToStl FBX %s", img_cand, filepath)
                return self._convert_image(img_cand)
        exe = self._find_blender()
        if not exe:
            raise RuntimeError("Blender is required to process 3D FBX files. Please install Blender or provide a DXF/DWG/PNG file.")
        out_dir = tempfile.mkdtemp(prefix="fbx2dxf_")
        out_dxf = os.path.join(out_dir, os.path.splitext(os.path.basename(filepath))[0] + ".dxf")
        slicer_script = os.path.join(os.path.dirname(__file__), "fbx_slicer.py")
        cmd = [exe, "-b", "-P", slicer_script, "--", filepath, out_dxf, "0.35"]
        logger.info("Slicing FBX with Blender: %s", cmd)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if not os.path.exists(out_dxf) or os.path.getsize(out_dxf) < 100:
            img_cand = self._find_matching_image_for_fbx(filepath)
            if img_cand:
                logger.info("FBX was a 2D image plane; falling back to source image: %s", img_cand)
                return self._convert_image(img_cand)
            logger.error("FBX slicing output: %s\nSTDERR: %s", proc.stdout, proc.stderr)
            raise RuntimeError(
                "This FBX appears to be a flat 2D image plane without 3D wall geometry. "
                "Please upload your .png or .jpg floor plan image directly!"
            )
        logger.info("FBX converted to sliced DXF: %s", out_dxf)
        return out_dxf

    # ── helpers ───────────────────────────────────────────
    def _arc_points(self, e) -> List[Tuple[float, float]]:
        c, r = e.dxf.center, e.dxf.radius
        a0, a1 = math.radians(e.dxf.start_angle), math.radians(e.dxf.end_angle)
        if a1 <= a0:
            a1 += 2 * math.pi
        step = (a1 - a0) / self.arc_segments
        pts = [(c.x + r * math.cos(a0 + i * step), c.y + r * math.sin(a0 + i * step))
               for i in range(self.arc_segments + 1)]
        if hasattr(e, "ocs"):
            ocs = e.ocs()
            if ocs.transform:
                pts = [(float(w.x), float(w.y)) for w in (ocs.to_wcs((x, y, 0.0)) for x, y in pts)]
        return pts

    def _spline_points(self, e) -> List[Tuple[float, float]]:
        try:
            return [(float(p.x), float(p.y)) for p in e.construction_tool().approximate(self.spline_segments)]
        except Exception as ex:
            logger.warning("spline failed: %s", ex)
            return [(float(p[0]), float(p[1])) for p in getattr(e, "control_points", [])]

    @staticmethod
    def _hatch_rings(e) -> List[List[Tuple[float, float]]]:
        """Boundary rings of a HATCH as point lists (adaptive arc flattening). Holes are subtracted."""
        from ezdxf import path as ezpath
        from shapely.geometry import Polygon
        try:
            subs = list(ezpath.make_path(e).sub_paths())
        except Exception:
            return []
        shape = None
        polys = []
        for sp in subs:
            ctrl = list(sp.control_vertices())
            span = max((max(v.x for v in ctrl) - min(v.x for v in ctrl)),
                       (max(v.y for v in ctrl) - min(v.y for v in ctrl)), 1e-3) if len(ctrl) >= 2 else 1.0
            pts = [(float(v.x), float(v.y)) for v in sp.flattening(max(span * 0.005, 1e-4))]
            if len(pts) >= 3:
                p = Polygon(pts)
                p = p if p.is_valid else p.buffer(0)
                if not p.is_empty:
                    polys.append(p)
        polys.sort(key=lambda p: -p.area)
        for p in polys:                      # even-odd fill: nested rings become holes
            shape = p if shape is None else shape.symmetric_difference(p)
        if shape is None or shape.is_empty:
            return []
        parts = list(shape.geoms) if hasattr(shape, "geoms") else [shape]
        return [list(g.exterior.coords)[:-1] for g in parts if g.geom_type == "Polygon" and g.area > 1e-5]

    @staticmethod
    def _lwpoly_points(e) -> List[Tuple[float, float]]:
        from ezdxf import path as ezpath
        try:
            p_obj = ezpath.make_path(e)
            ctrl = list(p_obj.control_vertices())
            if len(ctrl) >= 2:
                span = max((max(v.x for v in ctrl) - min(v.x for v in ctrl)),
                           (max(v.y for v in ctrl) - min(v.y for v in ctrl)), 1e-3)
                return [(float(v.x), float(v.y)) for v in p_obj.flattening(max(span * 0.003, 1e-4))]
        except Exception:
            pass
        raw = list(e.get_points("xyb"))
        pts = [(float(p[0]), float(p[1])) for p in raw]
        if hasattr(e, "ocs"):
            ocs = e.ocs()
            if ocs.transform:
                pts = [(float(w.x), float(w.y)) for w in (ocs.to_wcs((x, y, 0.0)) for x, y in pts)]
        return pts

    # ── block explosion ───────────────────────────────────
    SKIP_INSERT_LAYERS = ("FURN", "SANIT", "PLANT", "TREE", "ELEC", "CHANDELIER", "BEAM")

    def _iter_entities(self, entities, parent_layer: str = "0", depth: int = 0):
        """Yield (entity, effective_layer). INSERTs are exploded (nested blocks too), because
        architectural DWGs often keep the whole plan, walls included, inside blocks."""
        from .cleaner import CADCleaner
        for e in entities:
            try:
                layer = e.dxf.layer
            except Exception:
                continue
            if layer == "0" and parent_layer != "0":
                layer = parent_layer            # entities on layer 0 inherit the INSERT layer
            if e.dxftype() == "INSERT":
                up = layer.upper()
                try:
                    ip = e.dxf.insert
                    self.inserts.append((str(e.dxf.name), float(ip.x), float(ip.y)))
                except Exception:
                    pass
                if "DOOR" in up or "WIN" in up:
                    yield e, layer              # keep the insert point as opening evidence
                if depth >= 5 or any(k in up for k in self.SKIP_INSERT_LAYERS):
                    continue
                # overhead / upper-floor reference blocks (e.g. 'TYPE1 ABOVE', 'WALL ABOVE') are not this floor
                if CADCleaner.is_above_layer(layer) or CADCleaner.is_above_layer(str(getattr(e.dxf, "name", ""))):
                    continue
                try:
                    yield from self._iter_entities(e.virtual_entities(), layer, depth + 1)
                except Exception as ex:
                    logger.debug("explode failed: %s", ex)
                continue
            yield e, layer

    @staticmethod
    def _wanted_layer(layer: str) -> bool:
        from .cleaner import CADCleaner
        up = layer.upper()
        if any(k in up for k in ("WIN", "DOOR", "GLASS", "PARAPET", "RAILING")):
            return True                         # needed as opening / balcony parapet evidence
        return not CADCleaner.is_excluded_layer(layer)

    # ── main ──────────────────────────────────────────────
    def import_file(self, filepath: str) -> List[CADEntity]:
        low = filepath.lower()
        if low.endswith(self.DOC_EXTS):
            filepath = self._read_document(filepath)
            low = filepath.lower()
        if low.endswith(".dwg"):
            filepath = self._convert_dwg(filepath)
        elif low.endswith(".fbx"):
            filepath = self._convert_fbx(filepath)
        elif low.endswith(self.IMAGE_EXTS):
            filepath = self._convert_image(filepath)

        doc = ezdxf.readfile(filepath)
        self.insunits = int(doc.header.get("$INSUNITS", 0) or 0)
        out: List[CADEntity] = []
        layers = set()
        seen_blocks = 0

        for e, layer in self._iter_entities(doc.modelspace()):
            if e.dxftype() not in ("TEXT", "MTEXT", "DIMENSION", "ATTRIB", "ATTDEF", "INSERT"):
                self.layer_stats[layer] = self.layer_stats.get(layer, 0) + 1
            wanted = self._wanted_layer(layer)
            t = e.dxftype()
            try:
                if t == "TEXT":
                    ip = e.dxf.insert
                    self.labels.append((str(e.dxf.text), float(ip.x), float(ip.y)))
                elif t == "MTEXT":
                    ip = e.dxf.insert
                    self.labels.append((e.plain_text(), float(ip.x), float(ip.y)))
                elif t in ("MULTILEADER", "MLEADER"):
                    ctx = getattr(e, "context", None)
                    mtext = getattr(ctx, "mtext", None) if ctx else None
                    raw_str = getattr(mtext, "default_content", "") if mtext else ""
                    if raw_str:
                        tip = None
                        for ldr in getattr(ctx, "leaders", []):
                            for ln in getattr(ldr, "lines", []):
                                verts = getattr(ln, "vertices", [])
                                if verts:
                                    tip = (float(verts[0].x), float(verts[0].y))
                                    break
                        if tip is None and mtext and getattr(mtext, "insert", None) is not None:
                            tip = (float(mtext.insert.x), float(mtext.insert.y))
                        if tip is not None:
                            self.labels.append((str(raw_str).replace("\\P", " "), tip[0], tip[1]))
                elif t == "INSERT":
                    ip = e.dxf.insert
                    self.inserts.append((str(e.dxf.name), float(ip.x), float(ip.y)))
            except Exception as ex:                       # labels are optional evidence only
                logger.debug("label skip %s: %s", t, ex)
            if not wanted and t not in ("LINE", "LWPOLYLINE", "POLYLINE", "ARC", "SPLINE", "CIRCLE"):
                continue
            pts: List[Tuple[float, float]] = []
            closed = False
            try:
                if t == "LINE":
                    pts = [(float(e.dxf.start.x), float(e.dxf.start.y)),
                           (float(e.dxf.end.x), float(e.dxf.end.y))]
                elif t == "LWPOLYLINE":
                    pts = self._lwpoly_points(e)
                    closed = bool(e.closed)
                elif t == "POLYLINE":
                    pts = [(float(p[0]), float(p[1])) for p in e.points()]
                    closed = bool(e.is_closed)
                elif t == "ARC":
                    pts = self._arc_points(e)
                elif t == "SPLINE":
                    pts = self._spline_points(e)
                    closed = bool(e.closed)
                elif t == "CIRCLE":
                    c, r = e.dxf.center, e.dxf.radius
                    if hasattr(e, "ocs") and e.ocs().transform:
                        cw = e.ocs().to_wcs((c.x, c.y, 0.0))
                        cx, cy = float(cw.x), float(cw.y)
                    else:
                        cx, cy = float(c.x), float(c.y)
                    pts = [(cx + r * math.cos(2 * math.pi * i / self.arc_segments),
                            cy + r * math.sin(2 * math.pi * i / self.arc_segments))
                           for i in range(self.arc_segments)]
                    closed = True
                elif t == "HATCH":
                    up = layer.upper()
                    from .cleaner import CADCleaner as _C
                    if not any(k in up for k in ("WALL", "RCC", "PARTITION", "COL", "MIVAN")) and layer not in _C.forced_on:
                        continue
                    for ring in self._hatch_rings(e):
                        out.append(CADEntity("HATCH", layer, ring, True))
                        layers.add(layer)
                    continue
                elif t == "INSERT":
                    ip = e.dxf.insert
                    out.append(CADEntity("INSERT", layer, [(float(ip.x), float(ip.y))], False,
                                         {"block": e.dxf.name}))
                    layers.add(layer)
                    continue
                else:
                    continue            # TEXT, DIMENSION ... ignored
            except Exception as ex:
                logger.debug("skip %s: %s", t, ex)
                continue
            if len(pts) < 2:
                continue
            if not closed and len(pts) >= 4 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= 1e-4:
                closed = True
                pts = pts[:-1]
            self.all_lines.append((layer, pts, closed))
            if not wanted:
                continue
            layers.add(layer)
            out.append(CADEntity(t, layer, pts, closed))

        self.layers = sorted(layers)
        # Fallback: if Modelspace had no room text labels (e.g. BaseFloorPlan.dxf where text blocks were unreferenced),
        # recover room labels from unreferenced MTEXT/TEXT blocks in doc.blocks and align to Modelspace bounds.
        import re as _re
        _room_kw = _re.compile(r'\b(BED|BEDROOM|KITCHEN|LIVING|DINING|TOILET|BATH|BALC|BALCONY|LOBBY|SIT[\s\-]*OUT|W\.?I\.?W)\b', _re.I)
        if not any(_room_kw.search(t) for t, _, _ in self.labels) and out:
            all_xs = [p[0] for ent in out for p in ent.points]
            all_ys = [p[1] for ent in out for p in ent.points]
            if all_xs and all_ys:
                ms_w = max(all_xs) - min(all_xs)
                ms_h = max(all_ys) - min(all_ys)
                ms_cx = 0.5 * (min(all_xs) + max(all_xs))
                ms_cy = 0.5 * (min(all_ys) + max(all_ys))
                blk_cands = []
                for blk in doc.blocks:
                    if blk.name.startswith('*'):
                        continue
                    b_lbls = []
                    for e in blk:
                        try:
                            if e.dxftype() == 'TEXT':
                                b_lbls.append((str(e.dxf.text), float(e.dxf.insert.x), float(e.dxf.insert.y)))
                            elif e.dxftype() == 'MTEXT':
                                b_lbls.append((e.plain_text(), float(e.dxf.insert.x), float(e.dxf.insert.y)))
                        except Exception:
                            pass
                    rm_hits = [x for x in b_lbls if _room_kw.search(x[0])]
                    if len(rm_hits) >= 8:
                        xs = [x[1] for x in rm_hits]
                        ys = [x[2] for x in rm_hits]
                        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
                        if 0.25 * ms_w <= bw <= 1.05 * ms_w and 0.4 * ms_h <= bh <= 1.2 * ms_h:
                            blk_cands.append((len(rm_hits), min(xs), max(xs), min(ys), max(ys), rm_hits))
                if blk_cands:
                    blk_cands.sort(key=lambda item: -item[0])
                    chosen = [blk_cands[0]]
                    # If the drawing is a two-wing plan and the best block covers one wing, include the complementary wing block
                    for cand in blk_cands[1:]:
                        if cand[2] < chosen[0][1] or cand[1] > chosen[0][2]:
                            chosen.append(cand)
                            break
                    comb = [lbl for c in chosen for lbl in c[5]]
                    c_xs = [x[1] for x in comb]
                    c_ys = [x[2] for x in comb]
                    b_cx = 0.5 * (min(c_xs) + max(c_xs))
                    b_cy = 0.5 * (min(c_ys) + max(c_ys))
                    for txt, lx, ly in comb:
                        self.labels.append((txt, lx - b_cx + ms_cx, ly - b_cy + ms_cy))
                    logger.info("Recovered %d room labels from %d unreferenced CAD text block(s)", len(comb), len(chosen))

        logger.info("Imported %d entities (blocks exploded), INSUNITS=%s, labels=%d", len(out), self.insunits, len(self.labels))
        return out
