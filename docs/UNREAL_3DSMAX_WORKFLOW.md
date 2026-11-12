# Blender, Unreal Engine 5 & 3ds Max Workflow Guide

Every 3D export from **CAD-BLENDER-UNREAL (Auto Flat)** produces three synchronized 3D assets plus a quick-reference sheet:

- `<Name>.blend` — Native **Blender 4.x / 5.x** project
- `<Name>_Unreal.fbx` — **Unreal Engine 5.x** ready FBX
- `<Name>_3dsMax.fbx` — **Autodesk 3ds Max** ready FBX
- `<Name>_IMPORT_NOTES.txt` — Quick import parameter checklist

---

## 1. Editing Walls & Finishes in Blender 4.x / 5.x

Open `<Name>.blend` directly in Blender (or run `<Name>_blender.py` via **Scripting > Open > Run Script**):

- **Select & Edit Individual Walls**:
  - Expand `01_Structure > WALLS` in the Outliner.
  - Every wall (`Wall_001`, `Wall_002`, …) and window sill (`Sill_*`) is an **independent, watertight quad mesh** with clean planar faces and zero diagonal wireframe cross-lines.
  - Press `Tab` to enter Edit Mode on any single wall: push/pull faces along `X`/`Y`/`Z`, add loop cuts (`Ctrl+R`), bevel edges (`Ctrl+B`), or assign custom accent-wall materials without affecting neighboring walls.
- **Toggle Ceiling for Interior Walkthroughs / Top-Down Views**:
  - Click the eye/camera icon next to `01_Structure > CEILING` in the Outliner to inspect the interior layout from above while keeping all `3.0 m` walls, blue lintels (`02_Openings > LINTELS`), doors, windows, kitchen, and washroom tiles visible.
- **Customize Architectural Specifications**:
  - At the top of any generated `*_blender.py` script, toggle flags or dimensions and re-run:
    - `CONNECT_WALLS_INTO_ONE_MESH = False` (`False` = separate editable walls; `True` = single merged wall shell)
    - `BUILD_WALL_PANELS = False` (`True` adds decorative Living/Master Bedroom wall wainscotting panels)

---

## 2. Importing into Unreal Engine 5 (UE 5.1 – 5.5+)

Use **`<Name>_Unreal.fbx`** (exported at `1 unit = 1 cm`, `-Y Forward`, `Z Up`, `mesh_smooth_type='FACE'`, `use_triangles=False`):

1. In the **Content Browser**, click **Import** and select `<Name>_Unreal.fbx` (or use **File > Import Into Level…** to preserve the full scene hierarchy as Blueprint/Actor components).
2. Recommended FBX Import Options:
   - **Combine Meshes**: **Unchecked (`False`)** — keeps every wall, door, window, floor slab, washroom tile panel, and railing as a separate Static Mesh so you can move, hide, or swap materials per wall inside UE5!
   - **Import Normals and Tangents** (Normal Import Method: *Import Normals and Tangents*).
   - **Generate Lightmap UVs**: **Checked (`True`)** if baking static lighting with GPU Lightmass; optional if using **Lumen** dynamic global illumination.
   - **Build Nanite**: Optional (`True` for opaque structural walls/slabs; keep **Unchecked** on translucent glass meshes using `Window_Glass_Mat` and `MAT_Balcony_Glass`).
   - **Convert Scene Unit**: **Checked** (scale matches UE5 centimeters 1:1 — a `3000 mm` wall imports at exact `300 cm` height).
3. **Material Slots Ready for Quixel Megascans / Substrate**:
   - `Wall_Mat` — Interior/exterior painted plaster walls
   - `MAT_Lintel_Blue` — Structural lintel beams above openings (replace with `Wall_Mat` once reviewed, or keep for BIM/construction visualization)
   - `MAT_Floor_Master_Wood` — Master bedroom engineered wood flooring
   - `MAT_Floor_Common` — Living/dining/bedroom vitrified floor tiles
   - `MAT_Floor_Washroom` & `MAT_Washroom_Wall_Tiles` — Anti-skid floor + 3 ft × 2 ft (`900 × 600 mm`) wall tiles
   - `MAT_Floor_Balcony` — Exterior balcony tile finish
   - `Window_Glass_Mat` & `MAT_Balcony_Glass` — Translucent architectural glass
   - `Door_Wood_Mat`, `Door_Dark_Wood_Mat`, `Hardware_Metal_Mat` — Doors & smooth metallic hardware
   - `MAT_Kitchen_Granite`, `MAT_Kitchen_Cabinet`, `MAT_Kitchen_Steel` — Kitchen counter, cabinetry & sink

---

## 3. Importing into Autodesk 3ds Max (V-Ray / Corona / Arnold)

Use **`<Name>_3dsMax.fbx`** (exported with `Y Up`, `-Z Forward`, `use_triangles=False` for clean Editable Poly quads):

1. Set **Customize > Units Setup > System Unit Setup** to **Millimeters** or **Meters** (with **Automatic** scale conversion enabled in the FBX importer).
2. Go to **File > Import > Import…** and select `<Name>_3dsMax.fbx`.
3. In the **FBX Import** dialog:
   - **Preset**: *Autodesk Media & Entertainment*
   - **Geometry > Smoothing Groups**: **Checked**
   - **Geometry > Turbosmooth**: **Unchecked**
   - **Units > Automatic**: **Checked**
4. Every wall in `WALLS` arrives as a clean **Editable Poly** / **Editable Mesh** with pure quad/planar polygons — zero diagonal hidden-edge clutter — ready for **UVW Map (Box)** modifiers and V-Ray / Corona material libraries.
