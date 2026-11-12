import csv
import io
import json
import logging
from typing import Dict, List, Tuple

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .models import Wall

logger = logging.getLogger(__name__)


class WallDataExporter:
    """STEP 7 - structured wall data: recentre, number, classify exterior/interior, export."""

    outline: list = []      # outer boundary rings of the building (set by classify_walls)

    @staticmethod
    def recenter_and_number(walls: List[Wall]) -> Tuple[List[Wall], Tuple[float, float]]:
        """Move the plan so its lower-left corner is (0, 0) and number walls Wall_001..."""
        if not walls:
            return walls, (0.0, 0.0)
        xs = [x for w in walls for x, _ in w.polygon]
        ys = [y for w in walls for _, y in w.polygon]
        ox, oy = min(xs), min(ys)
        for w in walls:
            w.polygon = [(x - ox, y - oy) for x, y in w.polygon]
            w.start_point = (w.start_point[0] - ox, w.start_point[1] - oy)
            w.end_point = (w.end_point[0] - ox, w.end_point[1] - oy)
        # stable numbering: bottom-to-top, left-to-right (rows of 500 mm)
        walls.sort(key=lambda w: (round(((w.start_point[1] + w.end_point[1]) / 2) / 500), (w.start_point[0] + w.end_point[0]) / 2))
        for i, w in enumerate(walls, 1):
            w.id = f"Wall_{i:03d}"
        return walls, (ox, oy)

    @staticmethod
    def classify_walls(walls: List[Wall], extra: List[Wall] = None, lines=None,
                       outline: List[List[Tuple[float, float]]] = None) -> Dict[str, List[Wall]]:
        """Exterior = one face of the wall looks at the outside of the building.

        1. Footprint = union of walls + window/door pieces (`extra`), morphologically closed so door and
           balcony gaps are bridged, with all holes (rooms) filled.
        2. For every wall, a thin probe strip is placed just beyond each long face. If either probe lies
           mostly outside the footprint, that face is an outside face -> exterior wall.
        `extra` pieces (sills/lintels) are classified the same way.
        """
        from shapely.affinity import translate
        result = {'exterior': [], 'interior': []}
        if not walls:
            return result
        extra = extra or []
        polys = [Polygon(w.polygon).buffer(0) for w in walls]
        xpolys = [Polygon(w.polygon).buffer(0) for w in extra]

        use_outline = False
        if outline and any(len(rg) > 2 for rg in outline):
            foot_polys = [Polygon(rg).buffer(0) for rg in outline if len(rg) > 2]
            foot_cand = unary_union(foot_polys)
            total_wall_area = sum(p.area for p in polys)
            if foot_cand.area >= max(3.0 * total_wall_area, 100e6):
                WallDataExporter.outline = outline
                foot = foot_cand
                use_outline = True

        if not use_outline:
            closing = 550.0
            # +1 mm: walls that meet only at a corner point would otherwise leave the room behind them "open"
            barrier = unary_union(polys + xpolys).buffer(1.0, join_style=2)
            mass = barrier.buffer(closing, join_style=2, mitre_limit=2.0).buffer(-closing, join_style=2, mitre_limit=2.0)
            parts = [p for p in (mass.geoms if hasattr(mass, 'geoms') else [mass]) if p.geom_type == 'Polygon']
            if parts:                                                     # keep the main building mass
                big = max(p.area for p in parts)
                parts = [p for p in parts if p.area > 0.05 * big]
            else:
                big = 1.0
            foot_polys = [Polygon(p.exterior).buffer(0) for p in parts if hasattr(p, 'exterior') and p.exterior]
            foot = unary_union(foot_polys) if foot_polys else barrier.convex_hull
            foot_parts = [p for p in (foot.geoms if hasattr(foot, 'geoms') else [foot]) if p.geom_type == 'Polygon']
            WallDataExporter.outline = [
                [(round(x, 1), round(y, 1)) for x, y in list(p.exterior.coords)[:-1]]
                for p in foot_parts if p.area > 0.05 * big
            ]
        inside = foot.buffer(-10)
        everything = unary_union(polys + xpolys)

        def outside_face(w: Wall, p) -> bool:
            """True when, looking out of one long face, you reach the outside without crossing a wall."""
            if p.is_empty:
                return False
            others = everything.difference(p.buffer(15))
            (x1, y1), (x2, y2) = w.start_point, w.end_point
            L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            if w.shape == 'rectangle' and L > 1:
                ux, uy = (x2 - x1) / L, (y2 - y1) / L
                nx, ny = -uy, ux
                h = w.thickness / 2
                k = 0.4 * L                                  # middle 80 % of the wall
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                for s in (1, -1):
                    a0, a1 = h + 30, h + 900                 # strip 30..900 mm beyond the face
                    q = Polygon([(cx - ux * k + s * nx * a0, cy - uy * k + s * ny * a0),
                                 (cx + ux * k + s * nx * a0, cy + uy * k + s * ny * a0),
                                 (cx + ux * k + s * nx * a1, cy + uy * k + s * ny * a1),
                                 (cx - ux * k + s * nx * a1, cy - uy * k + s * ny * a1)])
                    if q.intersection(others).area > 0.2 * q.area:
                        continue                             # another wall stands in front of this face
                    if q.difference(inside).area / q.area > 0.35:
                        return True
                return False
            ring = p.buffer(600).difference(p.buffer(30)).difference(others)
            return bool(ring.area) and ring.difference(inside).area / ring.area > 0.25

        for w, p in zip(walls, polys):
            w.wall_type = 'exterior' if outside_face(w, p) else 'interior'
            result[w.wall_type].append(w)
        for w, p in zip(extra, xpolys):
            w.wall_type = 'exterior' if outside_face(w, p) else 'interior'
        logger.info("Classified %d exterior / %d interior", len(result['exterior']), len(result['interior']))
        return result

    @staticmethod
    def to_dicts(walls: List[Wall]) -> List[dict]:
        return [w.to_dict() for w in walls]

    @staticmethod
    def to_json(walls: List[Wall]) -> str:
        return json.dumps([w.to_dict() for w in walls], indent=2)

    @staticmethod
    def to_csv(walls: List[Wall]) -> str:
        buf = io.StringIO()
        wr = csv.writer(buf)
        wr.writerow(['id', 'kind', 'type', 'opening', 'x1', 'y1', 'x2', 'y2', 'length_mm', 'thickness_mm',
                     'base_mm', 'height_mm', 'layer'])
        for w in walls:
            d = w.to_dict()
            wr.writerow([d['id'], d['kind'], d['wall_type'], d['opening'], d['x1'], d['y1'], d['x2'], d['y2'],
                         d['length'], d['thickness'], d['base'], d['height'], d['layer']])
        return buf.getvalue()

    @staticmethod
    def to_summary(pieces: List[Wall], outline: list = None) -> str:
        walls = [w for w in pieces if w.kind == 'wall']
        fills = [w for w in pieces if w.kind != 'wall']
        if not walls:
            return "No walls detected."
        ext = [w for w in walls if w.wall_type == 'exterior']
        itr = [w for w in walls if w.wall_type == 'interior']
        outline = outline if outline is not None else WallDataExporter.outline
        lines = [
            f"Total walls     : {len(walls)}   total length {sum(w.length for w in walls) / 1000:.2f} m",
            f"Exterior walls  : {len(ext)}   length {sum(w.length for w in ext) / 1000:.2f} m",
            f"Interior walls  : {len(itr)}   length {sum(w.length for w in itr) / 1000:.2f} m",
            f"Wall volume     : {sum(Polygon(w.polygon).area * w.height for w in walls) / 1e9:.2f} m3",
            f"Opening pieces  : {len(fills)} (sills/lintels over windows and doors)",
        ]
        if outline:
            floor_area = sum(Polygon(r).area / 1e6 for r in outline if len(r) >= 3)
            lines.append(f"Floor slab area : {floor_area:.2f} m2 (built-in floor & ceiling slabs)")
            ceiling_h = max((w.base + w.height for w in pieces), default=3000.0) / 1000.0
            lines.append(f"Ceiling height  : {ceiling_h:.2f} m")
        lines.append("")
        for w in walls:
            lines.append(f"{w.id}  [{w.wall_type}]  "
                         f"({w.start_point[0]:.0f},{w.start_point[1]:.0f}) -> ({w.end_point[0]:.0f},{w.end_point[1]:.0f})  "
                         f"L={w.length:.0f}  T={w.thickness:.0f}  H={w.height:.0f}")
        if fills:
            lines.append("")
            for w in fills:
                lines.append(f"{w.id}  [{w.opening} {w.kind}]  L={w.length:.0f}  base={w.base:.0f}  H={w.height:.0f}")
        return "\n".join(lines)

    @staticmethod
    # DEPRECATED (unused): superseded by cad_processor/architecture.py (76.2 mm skirting, physical tiles).
    def compute_skirting(walls: List[Wall], outline: list, washroom_voids: list = None) -> list:
        """
        Computes 100mm high baseboard skirting running along the interior room walls.
        Stops at door openings so doorways have clear passage.
        Excludes washroom / toilet rooms which are tiled floor-to-ceiling.
        """
        if not walls or not outline:
            return []
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        foot = unary_union([Polygon(r).buffer(0) for r in outline if len(r) >= 3])
        wall_union = unary_union([Polygon(w.polygon).buffer(0) for w in walls if w.kind == 'wall'])
        wash_union = unary_union([Polygon(v).buffer(0) for v in washroom_voids if len(v) >= 3]) if washroom_voids else None

        interior_space = foot.difference(wall_union)
        if wash_union:
            interior_space = interior_space.difference(wash_union)
        interior_space = interior_space.buffer(0)

        skirting_raw = interior_space.difference(interior_space.buffer(-15.0))
        # Keep only adjacent to walls (not spanning open doorways):
        skirting_geom = skirting_raw.intersection(wall_union.buffer(16.0))
        parts = list(skirting_geom.geoms) if hasattr(skirting_geom, 'geoms') else [skirting_geom]
        rings = [
            [(round(x, 1), round(y, 1)) for x, y in list(p.exterior.coords)[:-1]]
            for p in parts if p.area > 500.0
        ]
        return rings

    @staticmethod
    # DEPRECATED (unused): superseded by cad_processor/architecture.py (76.2 mm skirting, physical tiles).
    def compute_washroom_tiles(walls: List[Wall], fills: List[Wall], outline: list) -> dict:
        """
        Computes 3D wall tile cladding ribbons for washroom / toilet walls,
        plus the 2D room void boundary for each washroom.
        Tile dimensions are 2 ft x 3 ft (0.6m x 0.9m) horizontal.
        Ribbons are 10mm thick interior cladding along the toilet room perimeters,
        stopping cleanly at doorways.
        """
        if not walls or not outline:
            return {'claddings': [], 'voids': []}
        from shapely.geometry import Polygon, Point
        from shapely.ops import unary_union

        foot = unary_union([Polygon(r).buffer(0) for r in outline if len(r) >= 3])
        w_polys = unary_union([Polygon(w.polygon).buffer(0) for w in walls if w.kind == 'wall'])
        l_polys = unary_union([Polygon(f.polygon).buffer(0) for f in fills if f.kind == 'lintel' and f.opening == 'door'])
        all_bounds = w_polys.union(l_polys)

        rooms = foot.difference(all_bounds)
        room_parts = list(rooms.geoms) if hasattr(rooms, 'geoms') else [rooms]

        # Ventilator windows are <= 800mm wide
        vents = [f for f in fills if f.opening == 'window' and (f.length <= 800.0 or any(k in f.layer.upper() for k in ('VENT', 'TOILET', 'WASH', 'BATH', 'WC')))]

        washrooms = []
        for v in vents:
            cx = sum(p[0] for p in v.polygon) / len(v.polygon)
            cy = sum(p[1] for p in v.polygon) / len(v.polygon)
            pv = Point(cx, cy)
            m = [r for r in room_parts if r.area > 1e6 and r.distance(pv) < 300.0]
            if m and m[0] not in washrooms:
                washrooms.append(m[0])

        claddings = []
        voids = []
        for i, w in enumerate(washrooms):
            # 10mm ribbon inside the room along the walls (stopping at doorways)
            ribbon = w.difference(w.buffer(-10.0)).intersection(w_polys.buffer(12.0))
            parts = list(ribbon.geoms) if hasattr(ribbon, 'geoms') else [ribbon]
            for p in parts:
                if p.area > 500.0:
                    coords = [(round(x, 1), round(y, 1)) for x, y in list(p.exterior.coords)[:-1]]
                    claddings.append({'name': f'Toilet_{i+1}', 'ring': coords})
            vcoords = [(round(x, 1), round(y, 1)) for x, y in list(w.exterior.coords)[:-1]]
            voids.append(vcoords)

        return {'claddings': claddings, 'voids': voids}

