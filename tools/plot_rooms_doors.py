import sys
sys.path.insert(0, '.')
from cad_processor.pipeline import CADtoBlenderPipeline
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from shapely.geometry import Polygon

pipe = CADtoBlenderPipeline()
res = pipe.process('uploads/1791528835981_3_Bhk.dwg')
walls = [w for w in res['walls'] if w.kind == 'wall']
fills = [w for w in res['walls'] if w.kind != 'wall']
outline = res['outline']

fig, ax = plt.subplots(figsize=(16, 8))

for r in outline:
    ax.add_patch(MplPoly(r, closed=True, facecolor='#f8fafc', edgecolor='#cbd5e1', lw=2.0, linestyle='--'))

for w in walls:
    c = '#3b82f6' if w.wall_type == 'interior' else '#ef4444'
    ax.add_patch(MplPoly(w.polygon, closed=True, facecolor=c, edgecolor='black', lw=0.8, alpha=0.7))
    cx = sum(p[0] for p in w.polygon) / len(w.polygon)
    cy = sum(p[1] for p in w.polygon) / len(w.polygon)
    ax.text(cx, cy, w.id, fontsize=7, ha='center', va='center', weight='bold')

for f in fills:
    c = '#06b6d4' if f.kind == 'sill' else '#fbbf24'
    ax.add_patch(MplPoly(f.polygon, closed=True, facecolor=c, edgecolor='black', lw=1.0, alpha=0.8))
    cx = sum(p[0] for p in f.polygon) / len(f.polygon)
    cy = sum(p[1] for p in f.polygon) / len(f.polygon)
    ax.text(cx, cy, f.id, fontsize=6, ha='center', va='center', color='darkred')

ax.set_aspect('equal')
ax.set_xlim(-500, 17500)
ax.set_ylim(-500, 8000)
ax.grid(True, linestyle=':', alpha=0.6)
plt.title("3BHK Floor Plan Analysis: Walls (Red/Blue), Windows (Cyan), Lintels (Yellow)")
plt.tight_layout()
plt.savefig('output/rooms_and_doors_analysis.png', dpi=200)
print("Saved analysis to output/rooms_and_doors_analysis.png")
