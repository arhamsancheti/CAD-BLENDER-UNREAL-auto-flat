import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import unary_union
import numpy as np

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
outline = res['outline']

foot = unary_union([Polygon(r) for r in outline if len(r) >= 3])
wall_polys = [Polygon(w.polygon).buffer(0) for w in walls]
wall_union = unary_union(wall_polys)

# Indoor room space is foot.difference(wall_union)
interior_space = foot.difference(wall_union)
# buffer by a tiny amount to clean topology
interior_space = interior_space.buffer(0)

# The boundary of the interior space consists of the interior faces of all walls + door opening lines!
# To place skirting:
# Skirting is placed along the interior boundaries of the rooms WHERE A WALL EXISTS (i.e. not across open doors)!
# Skirting depth: 15mm into the room.
# Height: 100mm (0.10m).

# If we take interior_space, and take its boundary:
# Boundary that touches wall_union is where walls are!
# We can take interior_space.difference(interior_space.buffer(-15.0)):
# This gives a 15mm border inside all rooms!
skirting_zone_raw = interior_space.difference(interior_space.buffer(-15.0))

# But we must NOT have skirting across door openings!
# A door opening is where wall_union is empty.
# So if we dilate wall_union by 1.0mm, and intersect with skirting_zone_raw:
# Any part of skirting_zone_raw that is adjacent to a wall is kept;
# any part bridging across a door (which touches no wall) is removed!
skirting_zone = skirting_zone_raw.intersection(wall_union.buffer(16.0))

# Clean into polygons
parts = list(skirting_zone.geoms) if hasattr(skirting_zone, 'geoms') else [skirting_zone]
clean_skirting = [p for p in parts if p.area > 500.0]

print(f"Total skirting pieces: {len(clean_skirting)}")
print(f"Total skirting area: {sum(p.area for p in clean_skirting)/1e6:.2f} m2")
xs = [pt[0] for p in clean_skirting for pt in p.exterior.coords]
ys = [pt[1] for p in clean_skirting for pt in p.exterior.coords]
print(f"Skirting bounds: X=[{min(xs):.1f}, {max(xs):.1f}], Y=[{min(ys):.1f}, {max(ys):.1f}]")
