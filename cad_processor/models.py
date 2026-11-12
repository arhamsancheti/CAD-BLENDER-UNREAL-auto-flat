from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any


@dataclass
class CADEntity:
    """A single geometric entity extracted from a CAD file."""
    entity_type: str
    layer: str
    points: List[Tuple[float, float]]
    is_closed: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def start_point(self) -> Tuple[float, float]:
        return self.points[0] if self.points else (0.0, 0.0)

    @property
    def end_point(self) -> Tuple[float, float]:
        return self.points[-1] if self.points else (0.0, 0.0)


@dataclass
class Wall:
    """A reconstructed wall (all units in millimetres)."""
    id: str
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    length: float
    thickness: float
    height: float = 3000.0
    polygon: List[Tuple[float, float]] = field(default_factory=list)
    wall_type: str = 'interior'   # 'interior' | 'exterior'
    layer: str = ''
    shape: str = 'rectangle'      # 'rectangle' | 'polygon'
    base: float = 0.0             # elevation of the bottom of this piece (mm)
    kind: str = 'wall'            # 'wall' | 'sill' | 'lintel'
    opening: str = ''             # for sill/lintel: 'window' | 'door' | 'opening'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'kind': self.kind,
            'opening': self.opening,
            'x1': round(self.start_point[0], 2),
            'y1': round(self.start_point[1], 2),
            'x2': round(self.end_point[0], 2),
            'y2': round(self.end_point[1], 2),
            'length': round(self.length, 2),
            'thickness': round(self.thickness, 2),
            'base': self.base,
            'height': self.height,
            'wall_type': self.wall_type,
            'layer': self.layer,
            'shape': self.shape,
            'polygon': [(round(x, 2), round(y, 2)) for x, y in self.polygon],
        }
