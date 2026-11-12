import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
from cad_processor.openings import OpeningFiller
import numpy as np
from shapely.geometry import Polygon, LineString

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']

filler = OpeningFiller()
ends = []
for i, w in enumerate(walls):
    a, b = np.array(w.start_point, float), np.array(w.end_point, float)
    d = (b - a) / np.linalg.norm(b - a)
    ends.append((i, a, -d, w.thickness, w.id))
    ends.append((i, b, d, w.thickness, w.id))

pairs = []
for p in range(len(ends)):
    for q in range(p + 1, len(ends)):
        i, pa, da, ta, ida = ends[p]
        j, pb, db, tb, idb = ends[q]
        if i == j: continue
        dot = np.dot(da, db)
        if dot > -0.95: continue
        g = pb - pa
        along = float(np.dot(g, da))
        lateral = abs(float(g[0] * -da[1] + g[1] * da[0]))
        if 600 <= along <= 2200 and lateral <= 100:
            print(f"Candidate: {ida} -> {idb}: along={along:.1f}, lateral={lateral:.1f}, dot={dot:.3f}")
