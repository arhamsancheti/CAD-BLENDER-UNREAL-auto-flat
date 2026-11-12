import logging
import statistics
from typing import List, Optional, Union

from .models import CADEntity

logger = logging.getLogger(__name__)

# $INSUNITS code -> millimetres per unit
INSUNITS_TO_MM = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}
NAME_TO_MM = {
    'millimeters': 1.0, 'mm': 1.0,
    'centimeters': 10.0, 'cm': 10.0,
    'meters': 1000.0, 'm': 1000.0,
    'inches': 25.4, 'inch': 25.4,
    'feet': 304.8, 'ft': 304.8,
}


class UnitNormalizer:
    """STEP 2 - convert every coordinate to millimetres."""

    def __init__(self):
        self.detected: str = ''
        self.scale: float = 1.0

    def _guess_from_walls(self, entities: List[CADEntity]) -> Optional[float]:
        """Wall thickness heuristic: pick the unit that makes median wall thickness 80-600 mm."""
        sides = []
        for e in entities:
            if e.is_closed and 'WALL' in e.layer.upper() and 'HATCH' not in e.layer.upper():
                xs = [p[0] for p in e.points]
                ys = [p[1] for p in e.points]
                s = min(max(xs) - min(xs), max(ys) - min(ys))
                if s > 0:
                    sides.append(s)
        if len(sides) < 3:
            return None
        med = statistics.median(sides)
        for factor in (1.0, 10.0, 1000.0, 25.4, 304.8):
            if 80.0 <= med * factor <= 600.0:
                return factor
        return None

    def _guess_from_geometry(self, entities: List[CADEntity]) -> Optional[float]:
        """Geometry extent heuristic: architectural residential plans are typically 5m to 120m across."""
        all_pts = [p for e in entities for p in e.points]
        if not all_pts:
            return None
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        extent = max(max(xs) - min(xs), max(ys) - min(ys))
        if extent <= 0:
            return None
        if 2.0 <= extent <= 120.0:
            return 1000.0   # Extent in meters -> scale to mm
        elif 120.0 < extent <= 400.0:
            return 304.8    # Extent in feet -> scale to mm
        elif extent > 2500.0:
            return 1.0      # Already in millimeters
        return None

    def normalize(self, entities: List[CADEntity],
                  source_units: Optional[Union[str, int]] = None,
                  insunits: int = 0) -> List[CADEntity]:
        scale = None
        if source_units and str(source_units).lower() not in ('auto', 'none', ''):
            scale = NAME_TO_MM.get(str(source_units).lower())
            self.detected = f"user: {source_units}"
        if scale is None and insunits in INSUNITS_TO_MM:
            scale = INSUNITS_TO_MM[insunits]
            self.detected = f"file header ($INSUNITS={insunits})"
        if scale is None:
            scale = self._guess_from_walls(entities)
            if scale is not None:
                self.detected = "guessed from wall thickness"
        if scale is None:
            scale = self._guess_from_geometry(entities)
            if scale is not None:
                self.detected = f"auto-detected from extent (scale x{scale:g})"
        if scale is None:
            scale = 1.0
            self.detected = "assumed millimetres"
        self.scale = scale
        logger.info("Units: %s -> scale %s", self.detected, scale)
        if scale == 1.0:
            return entities
        return [CADEntity(e.entity_type, e.layer,
                          [(x * scale, y * scale) for x, y in e.points],
                          e.is_closed, dict(e.attributes)) for e in entities]
