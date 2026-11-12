import logging
import re
from typing import List, Dict

from .models import CADEntity

logger = logging.getLogger(__name__)

# Layers containing any of these words are never walls.
REMOVE_KEYWORDS = [
    'DIM', 'TEXT', 'TXT', 'ANNO', 'FURN', 'ELEC', 'SYMB', 'DOOR', 'WIN',
    'GLASS', 'NOTE', 'DEFPOINTS', 'TITLE', 'GRID', 'AXIS', 'SANIT', 'FIXTURE',
    'STAIR', 'ELEV', 'DOTTED', 'PLANT', 'TREE', 'AREA', 'LEVEL', 'HIDDEN',
    'TREATMENT', 'CHANDELIER', 'LELVEL', 'DT-', 'WD_', 'CEILING', 'LIGHT',
    'LOUVRE', 'CHAJJA', 'PARAPET', 'RAILING', 'BEAM', 'FALSE', 'HUTCH', 'PATT',
]
# Elements ABOVE the plan cut (upper-floor walls, overhead beams, projections) are drawn dashed over the
# plan for reference only - e.g. a 'WALL ABOVE' layer inside a 'TYPE 1 ABOVE' block. They are never the
# walls of this floor, even though the layer name contains 'WALL'.
ABOVE_RE = re.compile(r'(^|[^A-Z])(ABOVE|ABV|OVERHEAD|OVER[\s_\-]*HEAD|UPPER|PROJECTION|PROJ|BELOW|'
                      r'FLOOR[\s_\-]*ABOVE|ROOF|TERRACE[\s_\-]*ABOVE)([^A-Z]|$)')
# Layers containing any of these are wall candidates.
WALL_KEYWORDS = ['WALL', 'MUUR', 'WAND', 'PARTITION', 'BRICK', 'RCC', 'STRUCT', 'COLUMN', 'MIVAN', 'COL']
EXACT_WALL_LAYERS = {'COL', 'A-WALL', 'WALLS', 'WL'}


class CADCleaner:
    """STEP 3 - drop dimensions, text, furniture, symbols, hatching; keep wall candidates."""

    def __init__(self):
        self.report: Dict[str, int] = {}
        self.wall_layers: List[str] = []

    # user overrides from the layer picker (set per scan by the pipeline)
    forced_on: set = set()      # layers the user wants treated as walls
    forced_off: set = set()     # layers the user wants ignored

    @staticmethod
    def is_above_layer(layer: str) -> bool:
        """Overhead / upper-floor reference layer (e.g. 'WALL ABOVE', 'BEAM OVERHEAD', 'UPPER FLOOR')."""
        return bool(ABOVE_RE.search(layer.upper()))

    @staticmethod
    def is_excluded_layer(layer: str) -> bool:
        if layer in CADCleaner.forced_on:
            return False
        if layer in CADCleaner.forced_off:
            return True
        up = layer.upper()
        if any(k in up for k in REMOVE_KEYWORDS):
            return True
        if CADCleaner.is_above_layer(layer):
            return True
        # hatch layers are only useful when they hatch walls or columns (e.g. HATCH_WALL, COLUMN HATCH, A-MIVAN HATCH)
        if 'HATCH' in up and not any(k in up for k in ('WALL', 'RCC', 'COL', 'MIVAN', 'PARTITION')):
            return True
        return False

    @staticmethod
    def is_wall_layer(layer: str) -> bool:
        if layer in CADCleaner.forced_off:
            return False
        if layer in CADCleaner.forced_on:
            return True
        up = layer.upper()
        if CADCleaner.is_excluded_layer(layer):
            return False
        if up.strip() in EXACT_WALL_LAYERS:
            return True
        return any(k in up for k in WALL_KEYWORDS)

    def clean(self, entities: List[CADEntity]) -> List[CADEntity]:
        kept: List[CADEntity] = []
        removed: Dict[str, int] = {}
        for e in entities:
            if self.is_excluded_layer(e.layer):
                removed[e.layer] = removed.get(e.layer, 0) + 1
                continue
            kept.append(e)
        self.report = removed
        self.wall_layers = sorted({e.layer for e in kept if self.is_wall_layer(e.layer)})
        logger.info("Cleaning: kept %d / %d entities; wall layers=%s",
                    len(kept), len(entities), self.wall_layers)
        return kept
