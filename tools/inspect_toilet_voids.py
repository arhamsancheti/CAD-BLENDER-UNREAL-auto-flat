import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from shapely.geometry import Polygon, box, LineString
from shapely.ops import unary_union
import numpy as np

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
outline = res['outline']

foot = unary_union([Polygon(r) for r in outline if len(r) >= 3])

# Washroom 1: South-West (approx X: 3512-5087, Y: 63-2200)
# Washroom 2: South-Center (approx X: 5087-7312, Y: 1688-3013)
# Washroom 3: North-East (approx X: 15050-16525, Y: 3313-5875)

toilet_boxes = {
    'Washroom_1': box(3512, 63, 5087, 2200),
    'Washroom_2': box(5087, 1688, 7312, 3013),
    'Washroom_3': box(14987, 3313, 16525, 5875),
}

for name, bx in toilet_boxes.items():
    print(f"\n--- {name} ---")
    w_touch = [w for w in walls if Polygon(w.polygon).intersects(bx.buffer(50))]
    print(f"Touching walls: {[w.id for w in w_touch]}")
    # find internal void
    t_void = bx.difference(unary_union([Polygon(w.polygon) for w in w_touch]))
    # keep main poly
    parts = list(t_void.geoms) if hasattr(t_void, 'geoms') else [t_void]
    parts = [p for p in parts if p.area > 5e5]
    if parts:
        main_void = parts[0]
        print(f"Internal void bounds: {main_void.bounds}, area={main_void.area/1e6:.2f} m2")
        coords = list(main_void.exterior.coords)[:-1]
        print(f"Boundary points ({len(coords)}): {coords}")
