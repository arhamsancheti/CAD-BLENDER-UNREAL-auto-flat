import logging
import math
from typing import Any, Dict, List

from shapely.geometry import Polygon

from .models import Wall

logger = logging.getLogger(__name__)


class WallBuilder:
    """STEP 5 - turn detected outlines into Wall objects (start, end, length, thickness, polygon)."""

    def build_walls(self, wall_data: List[Dict[str, Any]], default_height: float = 3000.0,
                    default_thickness: float = 200.0) -> List[Wall]:
        walls: List[Wall] = []
        for item in wall_data:
            poly: Polygon = item['polygon']
            if poly.is_empty or poly.area < 1.0:
                continue
            mrr = poly.minimum_rotated_rectangle
            if mrr.geom_type != 'Polygon':
                continue
            c = list(mrr.exterior.coords)[:4]
            side_a = math.dist(c[0], c[1])
            side_b = math.dist(c[1], c[2])
            if side_a >= side_b:
                long_len, short_len = side_a, side_b
                s_mid = ((c[0][0] + c[3][0]) / 2, (c[0][1] + c[3][1]) / 2)
                e_mid = ((c[1][0] + c[2][0]) / 2, (c[1][1] + c[2][1]) / 2)
            else:
                long_len, short_len = side_b, side_a
                s_mid = ((c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2)
                e_mid = ((c[2][0] + c[3][0]) / 2, (c[2][1] + c[3][1]) / 2)

            simp = poly.simplify(3.0, preserve_topology=True)
            is_rect = poly.area / max(mrr.area, 1e-6) > 0.94 and len(simp.exterior.coords) <= 6
            thickness = short_len if is_rect else 2.0 * poly.area / max(poly.length, 1e-6)
            if thickness <= 1.0:
                thickness = default_thickness

            if is_rect and long_len > 10.0:
                dx = e_mid[0] - s_mid[0]
                dy = e_mid[1] - s_mid[1]
                if abs(dy) <= 0.0105 * long_len:
                    cy = round(0.5 * (s_mid[1] + e_mid[1]), 2)
                    x0, x1 = round(min(s_mid[0], e_mid[0]), 2), round(max(s_mid[0], e_mid[0]), 2)
                    s_mid, e_mid = (x0, cy), (x1, cy)
                    long_len = x1 - x0
                    ht = round(thickness / 2.0, 2)
                    ring = [(x0, round(cy + ht, 2)), (x1, round(cy + ht, 2)),
                            (x1, round(cy - ht, 2)), (x0, round(cy - ht, 2))]
                elif abs(dx) <= 0.0105 * long_len:
                    cx = round(0.5 * (s_mid[0] + e_mid[0]), 2)
                    y0, y1 = round(min(s_mid[1], e_mid[1]), 2), round(max(s_mid[1], e_mid[1]), 2)
                    s_mid, e_mid = (cx, y0), (cx, y1)
                    long_len = y1 - y0
                    ht = round(thickness / 2.0, 2)
                    ring = [(round(cx - ht, 2), y0), (round(cx - ht, 2), y1),
                            (round(cx + ht, 2), y1), (round(cx + ht, 2), y0)]
                else:
                    ring = [(round(x, 2), round(y, 2)) for x, y in list(mrr.exterior.coords)[:-1]]
            else:
                ring = [(round(x, 2), round(y, 2)) for x, y in list(simp.exterior.coords)[:-1]]

            walls.append(Wall(
                id='', start_point=s_mid, end_point=e_mid, length=long_len,
                thickness=round(thickness, 2),
                height=default_height, polygon=ring, layer=item.get('layer', ''),
                shape='rectangle' if is_rect else 'polygon'))
        logger.info("Built %d walls", len(walls))
        return walls
