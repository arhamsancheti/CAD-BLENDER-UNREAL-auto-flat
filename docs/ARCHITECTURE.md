# Pipeline & Geometric Architecture

This document details the 11-stage engineering architecture behind **CAD-BLENDER-UNREAL (Auto Flat)** (`cad_processor/`).

---

## 1. End-to-End Pipeline Stages (`cad_processor/pipeline.py`)

`CADtoBlenderPipeline.process()` executes a deterministic sequence of geometric and architectural stages, normalizing all inputs into a unified millimeter coordinate system centered at the building's local origin `(0, 0, 0)`:

1. **Multi-Format Ingestion (`importer.py`, `document_reader.py`, `image_importer.py`, `fbx_slicer.py`)**
   - `.dwg`: Converted transparently via bundled `tools/libredwg/dwg2dxf.exe` into `.dxf` and parsed with `ezdxf` (exploding nested `INSERT` block references and preserving layer names, lineweights, `TEXT`/`MTEXT` room labels, and door swing `ARC` entities).
   - `.pdf` / `.docx` / `.doc`: `document_reader.py` inspects both vector paths (`PyMuPDF` `page.get_drawings()`) and embedded floor-plan rasters while parsing written room schedules, ceiling heights, and finish specifications.
   - `.png` / `.jpg` / `.webp`: `image_importer.py` + `line_vectorizer.py` extract clean centerlines/wall bands and estimate real-world scale from dimension strings and room labels.
   - `.fbx`: `fbx_slicer.py` slices 3D reference meshes horizontally at mid-wall elevation (`1200 mm`–`1500 mm`) into exact 2D wall footprints.
2. **Multi-Drawing Sheet Splitting (`sheet_splitter.py`)**
   - Architectural CAD files frequently place multiple floor plans, structural framing sheets, or furniture layouts side-by-side in model space. `sheet_splitter.py` clusters spatial islands, scores architectural floor-plan density vs. title blocks, and allows selecting any drawing sheet independently.
3. **Unit Normalization (`normalizer.py`)**
   - Reads `$INSUNITS` headers and cross-validates against statistical door widths (`700–1100 mm`), wall thicknesses (`100–300 mm`), and room spans so mislabeled unitless drawings (`m`, `cm`, `ft`, `in`) always land in true `mm`.
4. **Geometry Cleaning (`cleaner.py`)**
   - Removes zero-length micro-segments, deduplicates overlapping CAD strokes, snaps near-coincident endpoints, and merges collinear segments per layer.
5. **Hybrid Wall & Opening Detection (`wall_detector.py`, `raster_walls.py`, `openings.py`)**
   - Detects parallel double-line wall pairs across structural/architectural layers (`75 mm`–`450 mm` thickness), closed poché hatches/polylines, and raster distance-transform wall bands.
   - Detects door swing arcs, window mullion triple/quad lines, ventilation louvers, and structural wall gaps.
6. **Wall Graph Topology Repair (`wall_graph.py`)**
   - Repairs CAD drafting micro-gaps (`<= conn_tol`, default `90–100 mm`) across L-corners, T-junctions, cross-junctions, and collinear breaks **with `0.0 mm` lateral wall-face shift** so interior room dimensions never drift.
   - Preserves intentional door/window openings (`>= min_opening`) and explicitly flags ambiguous intermediate gaps as `uncertain` for human/UI review rather than guessing silently.
7. **3D Overlap Resolution (`pipeline._resolve_3d_overlaps`)**
   - Subtracts vertical `[z0, z1]` solid wall intervals cleanly so wall junctions, sills (`0..sill`), and lintels (`head..wall_h`) never Z-fight or self-intersect in 3D.
8. **Architectural Room & Finish Synthesis (`architecture.py`)**
   - Polygonizes enclosed room cells (`Living/Dining`, `Master Bedroom`, `Bedroom`, `Kitchen`, `Washroom`, `Balcony`, `Dry Balcony`, `Entrance`, `Shaft/Duct`).
   - Generates per-room untriangulated floor slabs, `100 mm` skirting runs clipped cleanly at doorways, `900 mm × 600 mm` (3 ft × 2 ft) washroom wall tile grids clipped around washroom doors/ventilators, balcony glass + metal railings, L/straight kitchen counters with sink cutouts, and recessed cove ceilings with LED downlights.
9. **Clean Quad / Planar Blender Script Generation (`blender_generator.py`)**
   - Emits a standalone, zero-dependency Blender 4.x/5.x Python script (`*_walls_blender.py`).
10. **Automated Detection QA & Multi-Reference Diff (`detection_review.py`, `reference.py`)**
    - Runs 11 geometric & architectural sanity checks (`PASS` / `WARN` / `FAIL`) and optionally aligns secondary CAD/PNG/FBX references via IoU + rigid registration.
11. **Headless Blender Execution & Export (`app.py:/export_3d`, `validator.py`)**
    - Runs Blender in `--factory-startup` headless mode, validates scene collections and BVH geometry, and writes `.blend`, `*_Unreal.fbx`, and `*_3dsMax.fbx`.

---

## 2. Clean Quad / Planar Mesh Invariants (`blender_generator.py`)

A core requirement for architectural editing in Blender, Unreal Engine 5, and 3ds Max is **clean wireframe topology without diagonal triangulation clutter** and **independent wall editability**:

1. **Separate Watertight 2-Manifold Walls (`CONNECT_WALLS_INTO_ONE_MESH = False`)**
   - Every wall segment (`Wall_001`…), corner post, window sill (`Sill_*`), and structural lintel (`Head_*`) is built via `prism()` as an independent `bpy.types.Object` in `01_Structure > WALLS` (or `02_Openings > LINTELS`).
   - Every solid mesh has **0 non-manifold edges**, **0 zero-area faces**, and **0 triangles** (pure 4-vertex vertical quad sides + planar top/bottom caps).
2. **Collinear Vertex Pruning (`_clean_ring_mm`)**
   - Before extruding any 2D footprint, collinear boundary points (cross-product deviation `< 1.0 mm`) and micro-chamfer duplicates (`< 2.0 mm`) are removed so flat walls never receive unnecessary vertical split edges.
3. **Orthogonal Hole Splitting (`_split_holes_ortho`)**
   - Instead of calling `bmesh.ops.triangle_fill` on floor slabs or false ceilings that contain rectangular cutouts (such as kitchen sinks, recessed ceiling coves, or plumbing shafts), `_split_holes_ortho()` slices polygon holes along axis-aligned `X`/`Y` cutlines through hole bounds, decomposing holed slabs into clean, planar rectangles/n-gons with **zero diagonal cross-segments**.
4. **Smooth Shaded Cylinders (`_add_cyl_y`, `_build_downlights_mesh`)**
   - Curved hardware (door lever handles, barrel hinges, kitchen gooseneck faucets, and closed-rim recessed ceiling downlights) mark side quad faces `use_smooth = True` while keeping flat end-caps sharp (`use_smooth = False`).
5. **Quad-Preserving FBX Export (`export_for_unreal_and_3dsmax`)**
   - Both Unreal and 3ds Max FBX exporters explicitly pass `use_triangles=False`, preserving clean quad/planar faces across DCC tools.
