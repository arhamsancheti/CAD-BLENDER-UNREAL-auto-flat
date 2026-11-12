import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
import numpy as np

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
windows = [f for f in fills if f.opening == 'window']

# Candidate door openings in the 3BHK flat:
# Let's check collinear walls and perpendicular walls where doors exist.
# Standard door widths: 750mm to 1600mm.

# Let's inspect the exact coordinates of door gaps:
doors_spec = [
    # (name, p1, p2, thickness, orientation)
    # 1. Door to Bedroom 2:
    ("Door_Bed2", (10100, 5813), (11600, 5813), 125.0),
    # 2. Door to Bedroom 3:
    ("Door_Bed3", (11725, 5813), (13225, 5813), 125.0),
    # 3. Door to Master Toilet:
    ("Door_Master_Toilet", (14987, 5000), (14987, 5813), 125.0),
    # 4. Door to Toilet 1 (South-West):
    ("Door_Toilet1", (3512, 2200), (3512, 3013), 125.0),
    # 5. Door to Toilet 2 (South-Center):
    ("Door_Toilet2", (7312, 2200), (7312, 3013), 125.0),
    # 6. Door between living / dining (already Lintel_004):
    ("Door_Living_Passage", (8187, 3075), (8187, 4075), 125.0),
    # 7. Entrance door / Living opening:
    ("Door_Entrance", (775, 4038), (2337, 4038), 125.0),
    # 8. Door / opening near Bed 3 shaft:
    ("Door_Bed3_Passage", (11662, 1125), (11662, 2188), 125.0),
    # 9. Door to Bed 3 / Balcony:
    ("Door_Bed3_Balcony", (14987, 2188), (14987, 3313), 125.0),
]

print("Checking door lintel candidates:")
for name, p1, p2, t in doors_spec:
    L = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
    print(f"  {name:20s}: L={L:6.1f}mm, T={t:.0f}mm, ({p1[0]:.0f},{p1[1]:.0f}) -> ({p2[0]:.0f},{p2[1]:.0f})")
