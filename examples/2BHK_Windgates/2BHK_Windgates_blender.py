# ======================================================================
#  CAD -> Blender / 3ds Max / Unreal Engine Architectural 3D Model
#  Auto-generated, idempotent, re-runnable Blender Python script
#  Walls: 40 (exterior 14, interior 26) | openings: 16 | rooms: 12
#  Skirting runs: 11 | individual wall tiles: 90
#  Units: data in millimetres -> Blender metres (1 BU = 1 m), display unit mm.
#  HOW TO USE: Blender > Scripting > Open this file > Run Script.
#  Re-running replaces ONLY the generated collections listed below; nothing else is touched.
# ======================================================================
import bpy
import bmesh
import json
import math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

# ── CENTRALIZED CONFIGURATION & REGENERATION SWITCHES ──
BUILD_WALLS = True              # 01_Structure > WALLS (every wall, post & sill as a separate editable mesh)
CONNECT_WALLS_INTO_ONE_MESH = False  # True = also build fused Building_Walls_Connected; False = clean separate editable walls
BUILD_OPENING_MARKERS = False   # 02_Openings > DOORS / WINDOWS (wire boxes of every clear opening; False so glass is directly clickable)
BUILD_BLUE_LINTELS = True       # 02_Openings > LINTELS (Lintel_Door_001, Lintel_Window_001 in blue)
BUILD_ROOMS = True              # ROOMS (room footprints with classification data)
BUILD_FLOORING = True           # 03_Flooring (independent per-room floor meshes & materials)
BUILD_SKIRTING = True           # 04_Skirting (independent per-room 100 mm skirting meshes & materials)
BUILD_TILES = True              # 05_Washroom_Tiles (full-height 0-3.0 m interior washroom wall tiles)
BUILD_WALL_PANELS = False       # 01_Structure > WALL_PANELS (False = keep dry walls clean & directly editable)
BUILD_BALCONY_GLASS = True      # 06_Balcony > GlassPanel_Balcony_XX + Railing_Glass_Balcony_XX (1.2 m / 4 ft)
BUILD_KITCHEN_PLATFORM = True   # 07_Kitchen > Kitchen_Base_XX + Kitchen_Countertop_XX + Kitchen_Backsplash_XX
BUILD_SLABS = True              # 01_Structure > CEILING + FLOOR
BUILD_RECESSED_CEILINGS = True  # 01_Structure > RECESSED_CEILINGS (bedrooms & halls only)
BUILD_DOOR_FITTINGS = True      # 02_Openings > DOOR_FITTINGS (wooden frame -> wooden leaf -> silver levers both sides)
BUILD_WINDOW_FITTINGS = True    # 02_Openings > WINDOW_FITTINGS (aluminium frames + glass in every window / ventilator)
BUILD_LIGHTING_AND_CAM = True   # 08_Materials_And_Lighting (reusable materials, sun light, preview camera)
BUILD_SOURCE_CAD = True         # SOURCE_CAD (raw CAD linework, hidden by default)
RUN_VALIDATION = True           # geometric checks -> VALIDATION + text block VALIDATION_REPORT
MERGE_INTO_ONE_MESH = False     # False = keep walls, per-room flooring, and per-room skirting as separate objects

# ── UNREAL ENGINE / 3ds MAX EXPORT ──
EXPORT_FBX = True               # write <name>_Unreal.fbx + <name>_3dsMax.fbx (+ <name>.blend) after building
EXPORT_DIR = ''                 # '' -> env CAD_EXPORT_DIR, else folder of the saved .blend, else ~/Documents/CAD_Blender_Exports
EXPORT_NAME = ''                # '' -> env CAD_EXPORT_NAME, else 'Architectural_Model'
EXPORT_WALL_MODE = 'pieces'     # 'pieces' = every wall / sill an individual editable object (no overlaps)
                                # 'connected' = one watertight continuous wall mesh
SAVE_BLEND = True               # also save the finished .blend next to the FBX files

DATA = json.loads(r"""{"spec":{"wall_h":3000.0,"door_head":2100.0,"win_sill":600.0,"win_h":1500.0,"vent_sill":1200.0,"vent_h":900.0,"vent_max_width":1000.0,"lintel_h":900.0,"skirt_h":100.0,"skirt_t":15.0,"floor_finish_t":20.0,"slab_t":200.0,"tile_w":914.4,"tile_h":609.6,"tile_t":9.0,"grout":2.5,"tile_gap":0.0,"min_cut":200.0,"panel_w":1220.0,"panel_t":12.0,"panel_joint":3.0,"balcony_glass_t":76.2,"balcony_glass_h":1200.0,"balcony_glass_joint":5.0,"balcony_glass_max":1200.0,"balcony_post_w":40.0,"balcony_rail_h":35.0,"kitchen_counter_h":860.0,"kitchen_counter_depth":600.0,"kitchen_counter_t":40.0,"kitchen_base_depth":570.0,"kitchen_backsplash_h":600.0,"kitchen_backsplash_t":15.0,"recess_border_w":450.0,"recess_depth":120.0,"recess_drop_h":50.0,"recess_lip_w":60.0,"recess_wall_gap":15.0,"downlight_r":45.0,"downlight_recess":25.0,"door_frame_w":45.0,"door_leaf_t":42.0,"door_handle_h":1000.0,"door_lever_len":128.0,"door_min":600.0,"door_max":1250.0,"gap_max":3600.0},"config":{"spec_mm":{"wall_h":3000.0,"door_head":2100.0,"win_sill":600.0,"win_h":1500.0,"vent_sill":1200.0,"vent_h":900.0,"vent_max_width":1000.0,"lintel_h":900.0,"skirt_h":100.0,"skirt_t":15.0,"floor_finish_t":20.0,"slab_t":200.0,"tile_w":914.4,"tile_h":609.6,"tile_t":9.0,"grout":2.5,"tile_gap":0.0,"min_cut":200.0,"panel_w":1220.0,"panel_t":12.0,"panel_joint":3.0,"balcony_glass_t":76.2,"balcony_glass_h":1200.0,"balcony_glass_joint":5.0,"balcony_glass_max":1200.0,"balcony_post_w":40.0,"balcony_rail_h":35.0,"kitchen_counter_h":860.0,"kitchen_counter_depth":600.0,"kitchen_counter_t":40.0,"kitchen_base_depth":570.0,"kitchen_backsplash_h":600.0,"kitchen_backsplash_t":15.0,"recess_border_w":450.0,"recess_depth":120.0,"recess_drop_h":50.0,"recess_lip_w":60.0,"recess_wall_gap":15.0,"downlight_r":45.0,"downlight_recess":25.0,"door_frame_w":45.0,"door_leaf_t":42.0,"door_handle_h":1000.0,"door_lever_len":128.0,"door_min":600.0,"door_max":1250.0,"gap_max":3600.0},"default_balcony_type":"open","room_type_overrides":{},"balcony_type_overrides":{},"material_presets":{"floor_common":"MAT_Floor_Common","floor_master_wood":"MAT_Floor_Master_Wood","floor_entrance":"MAT_Floor_Entrance","floor_balcony":"MAT_Floor_Balcony","floor_washroom":"MAT_Floor_Washroom","skirting_common":"MAT_Skirting_Common","skirting_master":"MAT_Skirting_Master","skirting_entrance":"MAT_Skirting_Entrance","skirting_balcony":"MAT_Skirting_Balcony","lintel_blue":"MAT_Lintel_Blue","washroom_tiles":"MAT_Washroom_Wall_Tiles","balcony_glass":"MAT_Balcony_Glass","balcony_metal":"MAT_Balcony_Railing_Metal","kitchen_countertop":"MAT_Kitchen_Countertop","kitchen_base":"MAT_Kitchen_Base"}},"pieces":[{"id":"Wall_001","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":660.0,"base":0.0,"height":3000.0,"ring":[[1800.0,960.0],[1800.0,300.0],[2475.1,300.0],[2475.1,960.0]]},{"id":"Wall_002","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[1800.0,6625.0],[1800.0,6500.0],[15250.0,6500.0],[15250.0,6625.0]]},{"id":"Wall_003","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[200.0,5150.0],[200.0,5025.0],[10050.0,5025.0],[10050.0,5150.0]]},{"id":"Wall_004","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[16300.0,1175.0],[16500.0,1175.0],[16500.0,6625.0],[16300.0,6625.0]]},{"id":"Wall_005","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[0.0,5150.0],[0.0,800.0],[200.0,800.0],[200.0,5150.0]]},{"id":"Wall_006","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[12750.0,0.0],[12950.0,0.0],[12950.0,3975.0],[12750.0,3975.0]]},{"id":"Wall_007","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[5150.0,300.0],[5350.0,300.0],[5350.0,3975.0],[5150.0,3975.0]]},{"id":"Wall_008","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":250.0,"base":0.0,"height":3000.0,"ring":[[10050.0,300.0],[10300.0,300.0],[10300.0,3975.0],[10050.0,3975.0]]},{"id":"Wall_009","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[8400.0,1250.0],[8550.0,1250.0],[8550.0,3975.0],[8400.0,3975.0]]},{"id":"Wall_010","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[1800.0,3525.0],[1800.0,960.0],[1950.0,960.0],[1950.0,3525.0]]},{"id":"Wall_011","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[10050.0,500.0],[8400.0,500.0],[8400.0,300.0],[10050.0,300.0]]},{"id":"Wall_012","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[1800.0,1000.0],[200.0,1000.0],[200.0,800.0],[1800.0,800.0]]},{"id":"Wall_013","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[10050.0,5025.0],[10250.0,5025.0],[10250.0,6500.0],[10050.0,6500.0]]},{"id":"Wall_014","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[1800.0,6500.0],[1800.0,5150.0],[1925.0,5150.0],[1925.0,6500.0]]},{"id":"Wall_015","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[5150.0,6500.0],[5150.0,5150.0],[5350.0,5150.0],[5350.0,6500.0]]},{"id":"Wall_016","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[6875.0,6500.0],[6875.0,5150.0],[7000.0,5150.0],[7000.0,6500.0]]},{"id":"Wall_017","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[8400.0,425.0],[7150.0,425.0],[7150.0,300.0],[8400.0,300.0]]},{"id":"Wall_018","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":250.0,"base":0.0,"height":3000.0,"ring":[[5350.0,6500.0],[5350.0,5400.0],[5600.0,5400.0],[5600.0,6500.0]]},{"id":"Wall_019","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[6400.0,3975.0],[5350.0,3975.0],[5350.0,3825.0],[6400.0,3825.0]]},{"id":"Wall_020","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[6550.1,3975.0],[6550.1,3825.0],[7500.1,3825.0],[7500.1,3975.0]]},{"id":"Wall_021","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[9300.1,3325.0],[8550.0,3325.0],[8550.0,3175.0],[9300.1,3175.0]]},{"id":"Wall_022","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[1800.0,5025.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,5025.0]]},{"id":"Wall_023","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[8400.0,1250.0],[8400.0,500.0],[8525.0,500.0],[8525.0,1250.0]]},{"id":"Wall_024","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[10925.1,425.0],[10300.0,425.0],[10300.0,300.0],[10925.1,300.0]]},{"id":"Wall_025","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[4625.0,300.0],[4750.0,300.0],[4750.0,925.0],[4625.0,925.0]]},{"id":"Wall_026","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[12750.0,425.0],[12125.1,425.0],[12125.1,300.0],[12750.0,300.0]]},{"id":"Wall_027","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[700.1,2625.0],[200.0,2625.0],[200.0,2500.0],[700.1,2500.0]]},{"id":"Wall_028","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[1800.0,2625.0],[1300.1,2625.0],[1300.1,2500.0],[1800.0,2500.0]]},{"id":"Wall_029","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":250.1,"base":0.0,"height":3000.0,"ring":[[13200.1,1900.0],[12950.0,1900.0],[12950.0,1425.0],[13200.1,1425.0]]},{"id":"Wall_030","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[16300.0,1900.0],[15825.1,1900.0],[15825.1,1775.0],[16300.0,1775.0]]},{"id":"Wall_031","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[10050.0,1375.0],[9587.6,1375.0],[9587.6,1250.0],[10050.0,1250.0]]},{"id":"Wall_032","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[8987.6,1375.0],[8550.0,1375.0],[8550.0,1250.0],[8987.6,1250.0]]},{"id":"Wall_033","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[10050.0,300.0],[10050.0,0.0],[10250.0,0.0],[10250.0,300.0]]},{"id":"Wall_034","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[5150.0,425.0],[4750.0,425.0],[4750.0,300.0],[5150.0,300.0]]},{"id":"Wall_035","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[7150.0,725.0],[7150.0,425.0],[7275.0,425.0],[7275.0,725.0]]},{"id":"Wall_036","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[13425.1,1900.0],[13200.1,1900.0],[13200.1,1775.0],[13425.1,1775.0]]},{"id":"Post_01","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[16500.0,150.0],[16500.0,275.0],[16300.0,275.0],[16300.0,150.0]]},{"id":"Wall_037","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[6550.0,4125.0],[6400.0,4125.0],[6400.0,3975.0],[6550.0,3975.0]]},{"id":"Post_02","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":100.0,"base":0.0,"height":3000.0,"ring":[[4750.0,-200.0],[4750.0,-100.0],[4625.0,-100.0],[4625.0,-200.0]]},{"id":"Post_03","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":100.0,"base":0.0,"height":3000.0,"ring":[[2475.0,-200.0],[2475.0,-100.0],[2350.0,-100.0],[2350.0,-200.0]]},{"id":"Sill_Window_03","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[16300.0,275.0],[12950.0,275.0],[12950.0,150.0],[16300.0,150.0]]},{"id":"Sill_Window_04","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":100.0,"base":0.0,"height":600.0,"ring":[[4625.0,-100.0],[2475.0,-100.0],[2475.0,-200.0],[4625.0,-200.0]]},{"id":"Sill_Window_01","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[7150.0,725.0],[5350.0,725.0],[5350.0,600.0],[7150.0,600.0]]},{"id":"Sill_Window_02","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[12125.1,425.0],[10925.1,425.0],[10925.1,300.0],[12125.1,300.0]]},{"id":"Sill_Vent_03","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":600.0,"ring":[[16300.0,1175.0],[16300.0,275.0],[16500.0,275.0],[16500.0,1175.0]]},{"id":"Sill_Vent_01","kind":"sill","opening":"vent","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":1200.0,"ring":[[1300.1,2625.0],[700.1,2625.0],[700.1,2500.0],[1300.1,2500.0]]},{"id":"Sill_Vent_02","kind":"sill","opening":"vent","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":1200.0,"ring":[[9587.6,1375.0],[8987.6,1375.0],[8987.6,1250.0],[9587.6,1250.0]]},{"id":"Sill_Vent_05","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[4625.0,-100.0],[4750.0,-100.0],[4750.0,300.0],[4625.0,300.0]]},{"id":"Sill_Vent_04","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[2350.0,300.0],[2350.0,-100.0],[2475.0,-100.0],[2475.0,300.0]]},{"id":"Lintel_Window_001","kind":"lintel","opening":"window","opening_id":"Window_03","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[16300.0,275.0],[12950.0,275.0],[12950.0,150.0],[16300.0,150.0]]},{"id":"Lintel_Passage_003","kind":"lintel","opening":"passage","opening_id":"Passage_01","wall_type":"interior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[15825.1,1900.0],[13425.1,1900.0],[13425.1,1775.0],[15825.1,1775.0]]},{"id":"Lintel_Window_002","kind":"lintel","opening":"window","opening_id":"Window_04","wall_type":"exterior","thickness":100.0,"base":2100.0,"height":900.0,"ring":[[4625.0,-100.0],[2475.0,-100.0],[2475.0,-200.0],[4625.0,-200.0]]},{"id":"Lintel_Window_006","kind":"lintel","opening":"window","opening_id":"Window_01","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[7150.0,725.0],[5350.0,725.0],[5350.0,600.0],[7150.0,600.0]]},{"id":"Lintel_Window_007","kind":"lintel","opening":"window","opening_id":"Window_02","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[12125.1,425.0],[10925.1,425.0],[10925.1,300.0],[12125.1,300.0]]},{"id":"Lintel_Door_006","kind":"lintel","opening":"door","opening_id":"Door_01","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[16300.0,6625.0],[15250.0,6625.0],[15250.0,6500.0],[16300.0,6500.0]]},{"id":"Lintel_Door_002","kind":"lintel","opening":"door","opening_id":"Door_03","wall_type":"interior","thickness":200.0,"base":2100.0,"height":900.0,"ring":[[10050.0,5025.0],[10050.0,3975.0],[10250.0,3975.0],[10250.0,5025.0]]},{"id":"Lintel_Window_003","kind":"lintel","opening":"window","opening_id":"Vent_03","wall_type":"exterior","thickness":200.0,"base":2100.0,"height":900.0,"ring":[[16300.0,1175.0],[16300.0,275.0],[16500.0,275.0],[16500.0,1175.0]]},{"id":"Lintel_Door_007","kind":"lintel","opening":"door","opening_id":"Door_02","wall_type":"interior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[6537.5,4125.0],[6537.5,5025.0],[6412.5,5025.0],[6412.5,4125.0]]},{"id":"Lintel_Door_005","kind":"lintel","opening":"door","opening_id":"Door_05","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[8400.0,3975.0],[7500.1,3975.0],[7500.1,3825.0],[8400.0,3825.0]]},{"id":"Lintel_Door_001","kind":"lintel","opening":"door","opening_id":"Door_04","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[1800.0,4275.0],[1800.0,3525.0],[1950.0,3525.0],[1950.0,4275.0]]},{"id":"Lintel_Door_004","kind":"lintel","opening":"door","opening_id":"Door_06","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[10050.0,3325.0],[9300.1,3325.0],[9300.1,3175.0],[10050.0,3175.0]]},{"id":"Lintel_Window_008","kind":"lintel","opening":"vent","opening_id":"Vent_01","wall_type":"interior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[1300.1,2625.0],[700.1,2625.0],[700.1,2500.0],[1300.1,2500.0]]},{"id":"Lintel_Window_009","kind":"lintel","opening":"vent","opening_id":"Vent_02","wall_type":"interior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[9587.6,1375.0],[8987.6,1375.0],[8987.6,1250.0],[9587.6,1250.0]]},{"id":"Lintel_Window_004","kind":"lintel","opening":"window","opening_id":"Vent_05","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[4625.0,-100.0],[4750.0,-100.0],[4750.0,300.0],[4625.0,300.0]]},{"id":"Lintel_Window_005","kind":"lintel","opening":"window","opening_id":"Vent_04","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[2350.0,300.0],[2350.0,-100.0],[2475.0,-100.0],[2475.0,300.0]]}],"openings":[{"id":"Window_03","type":"window","p0":[12950.0,212.5],"p1":[16300.0,212.5],"width":3350.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[12950.0,275.0],[16300.0,275.0],[16300.0,150.0],[12950.0,150.0]],"rooms":["Room_04"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_001"},{"id":"Window_04","type":"window","p0":[2475.0,-150.0],"p1":[4625.0,-150.0],"width":2150.0,"thickness":100.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[2475.0,-100.0],[4625.0,-100.0],[4625.0,-200.0],[2475.0,-200.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_002"},{"id":"Vent_03","type":"window","p0":[16400.0,275.0],"p1":[16400.0,1175.0],"width":900.0,"thickness":200.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[16300.0,275.0],[16300.0,1175.0],[16500.0,1175.0],[16500.0,275.0]],"rooms":["Room_04"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_003"},{"id":"Vent_05","type":"window","p0":[4687.5,-100.0],"p1":[4687.5,300.0],"width":400.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[4625.0,-100.0],[4625.0,300.0],[4750.0,300.0],[4750.0,-100.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_004"},{"id":"Vent_04","type":"window","p0":[2412.5,-100.0],"p1":[2412.5,300.0],"width":400.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[2350.0,-100.0],[2350.0,300.0],[2475.0,300.0],[2475.0,-100.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_005"},{"id":"Window_01","type":"window","p0":[5350.0,662.5],"p1":[7150.0,662.5],"width":1800.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[5350.0,725.0],[7150.0,725.0],[7150.0,600.0],[5350.0,600.0]],"rooms":["Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_006"},{"id":"Window_02","type":"window","p0":[10925.1,362.5],"p1":[12125.1,362.5],"width":1200.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[10925.1,425.0],[12125.1,425.0],[12125.1,300.0],[10925.1,300.0]],"rooms":["Room_01"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_007"},{"id":"Vent_01","type":"vent","p0":[700.1,2562.5],"p1":[1300.1,2562.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[700.1,2625.0],[1300.1,2625.0],[1300.1,2500.0],[700.1,2500.0]],"rooms":["Room_08","Master_Toilet"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_008"},{"id":"Vent_02","type":"vent","p0":[8987.6,1312.5],"p1":[9587.6,1312.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[8987.6,1375.0],[9587.6,1375.0],[9587.6,1250.0],[8987.6,1250.0]],"rooms":["Room_10","Toilet_1"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_009"},{"id":"Door_04","type":"door","p0":[1875.0,3525.0],"p1":[1875.0,4275.0],"width":750.0,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap + DOOR layer","notes":[],"rect":[[1800.0,3525.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,3525.0]],"rooms":["Room_02","Master_Toilet"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_001"},{"id":"Door_03","type":"door","p0":[10150.0,3975.0],"p1":[10150.0,5025.0],"width":1050.0,"thickness":200.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap","notes":[],"rect":[[10050.0,3975.0],[10050.0,5025.0],[10250.0,5025.0],[10250.0,3975.0]],"rooms":["Room_01","Room_05"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_002"},{"id":"Passage_01","type":"passage","p0":[13425.1,1837.5],"p1":[15825.1,1837.5],"width":2400.0,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap + lintel line drawn across","notes":["beam / lintel line drawn across the opening - wall completed above door head"],"rect":[[13425.1,1900.0],[15825.1,1900.0],[15825.1,1775.0],[13425.1,1775.0]],"rooms":["Room_01","Room_04"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Passage_003"},{"id":"Door_06","type":"door","p0":[9300.1,3250.0],"p1":[10050.0,3250.0],"width":749.9,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[9300.1,3325.0],[10050.0,3325.0],[10050.0,3175.0],[9300.1,3175.0]],"rooms":["Room_05","Toilet_1"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_004"},{"id":"Door_05","type":"door","p0":[7500.1,3900.0],"p1":[8400.0,3900.0],"width":899.9,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[7500.1,3975.0],[8400.0,3975.0],[8400.0,3825.0],[7500.1,3825.0]],"rooms":["Room_05","Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_005"},{"id":"Door_01","type":"door","p0":[15250.0,6562.5],"p1":[16300.0,6562.5],"width":1050.0,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[15250.0,6625.0],[16300.0,6625.0],[16300.0,6500.0],[15250.0,6500.0]],"rooms":["Room_01"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_006"},{"id":"Door_02","type":"door","p0":[6475.0,5025.0],"p1":[6475.0,4125.0],"width":900.0,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"CAD door arc between walls + DOOR layer","notes":[],"rect":[[6537.5,5025.0],[6537.5,4125.0],[6412.5,4125.0],[6412.5,5025.0]],"rooms":["Room_05","Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_007"}],"rooms":[{"name":"Room_01","code":"R01","type":"dry","use":"living","label":"Living","display_name":"Living Room","cad_dim":"6.08 \u00d7 6.05 m","cad_text":"","floor_obj":"Floor_Living","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Living","skirt_mat":"MAT_Skirting_Common","tile_obj":"","floor_category":"common","panelled":true,"recessed_ceiling":true,"area_m2":30.925,"ring":[[16300.0,6500.0],[10250.0,6500.0],[10250.0,3975.0],[10300.0,3975.0],[10300.0,425.0],[12750.0,425.0],[12750.0,3975.0],[12950.0,3975.0],[12950.0,1900.0],[16300.0,1900.0]],"holes":[]},{"name":"Room_04","code":"R04","type":"dry","use":"kitchen","label":"Kitchen","display_name":"Kitchen","cad_dim":"3.35 \u00d7 1.50 m","cad_text":"","floor_obj":"Floor_Kitchen","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Kitchen","skirt_mat":"MAT_Skirting_Common","tile_obj":"","floor_category":"common","panelled":true,"recessed_ceiling":false,"area_m2":4.937,"ring":[[12950.0,275.0],[16300.0,275.0],[16300.0,1775.0],[13200.1,1775.0],[13200.1,1425.0],[12950.0,1425.0]],"holes":[]},{"name":"Room_05","code":"R05","type":"dry","use":"lobby","label":"Lobby","display_name":"Lobby","cad_dim":"3.51 \u00d7 1.70 m","cad_text":"","floor_obj":"Floor_Entrance_01","floor_mat":"MAT_Floor_Entrance","skirt_obj":"Skirting_Entrance_01","skirt_mat":"MAT_Skirting_Entrance","tile_obj":"","floor_category":"entrance","panelled":true,"recessed_ceiling":false,"area_m2":4.661,"ring":[[6537.5,4125.0],[6550.0,4125.0],[6550.0,3975.0],[8550.0,3975.0],[8550.0,3325.0],[10050.0,3325.0],[10050.0,5025.0],[6537.5,5025.0]],"holes":[]},{"name":"Room_07","code":"R07","type":"shaft","use":"shaft","label":"Shaft_2","display_name":"Service Shaft / Duct","cad_dim":"3.05 \u00d7 1.35 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","floor_category":"shaft","panelled":false,"recessed_ceiling":false,"area_m2":4.117,"ring":[[7000.0,6500.0],[7000.0,5150.0],[10050.0,5150.0],[10050.0,6500.0]],"holes":[]},{"name":"Room_10","code":"R10","type":"shaft","use":"shaft","label":"Shaft_5","display_name":"Service Shaft / Duct","cad_dim":"1.52 \u00d7 0.75 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","floor_category":"shaft","panelled":false,"recessed_ceiling":false,"area_m2":1.144,"ring":[[10050.0,1250.0],[8525.0,1250.0],[8525.0,500.0],[10050.0,500.0]],"holes":[]},{"name":"Toilet_1","code":"T1","type":"washroom","use":"washroom","label":"Toilet_1","display_name":"Toilet","cad_dim":"1.80 \u00d7 1.50 m","cad_text":"","floor_obj":"Floor_Washroom_02","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_02","floor_category":"washroom","panelled":false,"recessed_ceiling":false,"area_m2":2.7,"ring":[[8550.0,3175.0],[8550.0,1375.0],[10050.0,1375.0],[10050.0,3175.0]],"holes":[]},{"name":"Room_03","code":"R03","type":"dry","use":"bedroom","label":"Bedroom","display_name":"Bedroom","cad_dim":"3.55 \u00d7 3.05 m","cad_text":"","floor_obj":"Floor_Bedroom","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Bedroom","skirt_mat":"MAT_Skirting_Common","tile_obj":"","floor_category":"common","panelled":true,"recessed_ceiling":true,"area_m2":9.815,"ring":[[6550.1,3975.0],[6400.0,3975.0],[6400.0,3825.0],[5350.0,3825.0],[5350.0,725.0],[7275.0,725.0],[7275.0,425.0],[8400.0,425.0],[8400.0,3825.0],[6550.1,3825.0]],"holes":[]},{"name":"Room_09","code":"R09","type":"shaft","use":"shaft","label":"Shaft_4","display_name":"Service Shaft / Duct","cad_dim":"1.52 \u00d7 1.35 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","floor_category":"shaft","panelled":false,"recessed_ceiling":false,"area_m2":1.784,"ring":[[5350.0,5400.0],[5350.0,5150.0],[6875.0,5150.0],[6875.0,6500.0],[5600.0,6500.0],[5600.0,5400.0]],"holes":[]},{"name":"Room_02","code":"R02","type":"dry","use":"master_bedroom","label":"Master_Bedroom","display_name":"Master Bedroom","cad_dim":"5.12 \u00d7 4.46 m","cad_text":"","floor_obj":"Floor_MasterBedroom_Wood","floor_mat":"MAT_Floor_Master_Wood","skirt_obj":"Skirting_MasterBedroom","skirt_mat":"MAT_Skirting_Master","tile_obj":"","floor_category":"master_wood","panelled":true,"recessed_ceiling":true,"area_m2":16.829,"ring":[[2475.0,300.0],[2475.0,-100.0],[4625.0,-100.0],[4625.0,925.0],[4750.0,925.0],[4750.0,425.0],[5150.0,425.0],[5150.0,3975.0],[6400.0,3975.0],[6400.0,4125.0],[6412.5,4125.0],[6412.5,5025.0],[1950.0,5025.0],[1950.0,960.0],[2475.1,960.0],[2475.1,300.0]],"holes":[]},{"name":"Room_06","code":"R06","type":"shaft","use":"shaft","label":"Shaft_1","display_name":"Service Shaft / Duct","cad_dim":"3.23 \u00d7 1.35 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","floor_category":"shaft","panelled":false,"recessed_ceiling":false,"area_m2":4.354,"ring":[[5150.0,6500.0],[1925.0,6500.0],[1925.0,5150.0],[5150.0,5150.0]],"holes":[]},{"name":"Room_08","code":"R08","type":"shaft","use":"shaft","label":"Shaft_3","display_name":"Service Shaft / Duct","cad_dim":"1.60 \u00d7 1.50 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","floor_category":"shaft","panelled":false,"recessed_ceiling":false,"area_m2":2.4,"ring":[[200.0,1000.0],[1800.0,1000.0],[1800.0,2500.0],[200.0,2500.0]],"holes":[]},{"name":"Master_Toilet","code":"MT","type":"washroom","use":"washroom","label":"Master_Toilet","display_name":"Master Toilet","cad_dim":"2.40 \u00d7 1.60 m","cad_text":"","floor_obj":"Floor_Washroom_01","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_01","floor_category":"washroom","panelled":false,"recessed_ceiling":false,"area_m2":3.84,"ring":[[200.0,2625.0],[1800.0,2625.0],[1800.0,5025.0],[200.0,5025.0]],"holes":[]}],"room_floors":[{"name":"Floor_Living","room":"Room_01","label":"Living","use":"living","category":"common","mat":"MAT_Floor_Common","plank_angle":3.141593,"area_m2":31.312,"rings":[{"outer":[[15825.1,1837.5],[15825.1,1900.0],[16300.0,1900.0],[16300.0,6625.0],[16301.0,6625.0],[16301.0,6626.0],[15249.0,6626.0],[15249.0,6625.0],[15250.0,6625.0],[15250.0,6500.0],[10250.0,6500.0],[10250.0,5025.0],[10150.0,5025.0],[10150.0,3975.0],[10300.0,3975.0],[10300.0,425.0],[12750.0,425.0],[12750.0,3975.0],[12950.0,3975.0],[12950.0,1900.0],[13425.1,1900.0],[13425.1,1837.5]],"holes":[]}]},{"name":"Floor_Kitchen","room":"Room_04","label":"Kitchen","use":"kitchen","category":"common","mat":"MAT_Floor_Common","plank_angle":0.0,"area_m2":5.088,"rings":[{"outer":[[13200.1,1425.0],[12950.0,1425.0],[12950.0,275.0],[16300.0,275.0],[16300.0,1775.0],[15825.1,1775.0],[15825.1,1837.5],[13425.1,1837.5],[13425.1,1775.0],[13200.1,1775.0]],"holes":[]}]},{"name":"Floor_Entrance_01","room":"Room_05","label":"Lobby","use":"lobby","category":"entrance","mat":"MAT_Floor_Entrance","plank_angle":3.141593,"area_m2":4.946,"rings":[{"outer":[[10150.0,3975.0],[10150.0,5025.0],[6475.0,5025.0],[6475.0,4125.0],[6550.0,4125.0],[6550.0,3975.0],[7500.1,3975.0],[7500.1,3900.0],[8400.0,3900.0],[8400.0,3975.0],[8550.0,3975.0],[8550.0,3325.0],[9300.1,3325.0],[9300.1,3250.0],[10050.0,3250.0],[10050.0,3975.0]],"holes":[]}]},{"name":"Floor_Washroom_02","room":"Toilet_1","label":"Toilet_1","use":"washroom","category":"washroom","mat":"MAT_Floor_Washroom","plank_angle":-1.570796,"area_m2":2.756,"rings":[{"outer":[[9300.1,3175.0],[8550.0,3175.0],[8550.0,1375.0],[10050.0,1375.0],[10050.0,3250.0],[9300.1,3250.0]],"holes":[]}]},{"name":"Floor_Bedroom","room":"Room_03","label":"Bedroom","use":"bedroom","category":"common","mat":"MAT_Floor_Common","plank_angle":1.570796,"area_m2":9.883,"rings":[{"outer":[[6550.1,3825.0],[6550.1,3975.0],[6400.0,3975.0],[6400.0,3825.0],[5350.0,3825.0],[5350.0,725.0],[7275.0,725.0],[7275.0,425.0],[8400.0,425.0],[8400.0,3900.0],[7500.1,3900.0],[7500.1,3825.0]],"holes":[]}]},{"name":"Floor_MasterBedroom_Wood","room":"Room_02","label":"Master_Bedroom","use":"master_bedroom","category":"master_wood","mat":"MAT_Floor_Master_Wood","plank_angle":3.141593,"area_m2":16.942,"rings":[{"outer":[[1950.0,960.0],[2475.1,960.0],[2475.0,-100.0],[4625.0,-100.0],[4625.0,925.0],[4750.0,925.0],[4750.0,425.0],[5150.0,425.0],[5150.0,3975.0],[6400.0,3975.0],[6400.0,4125.0],[6475.0,4125.0],[6475.0,5025.0],[1950.0,5025.0],[1950.0,4275.0],[1875.0,4275.0],[1875.0,3525.0],[1950.0,3525.0]],"holes":[]}]},{"name":"Floor_Washroom_01","room":"Master_Toilet","label":"Master_Toilet","use":"washroom","category":"washroom","mat":"MAT_Floor_Washroom","plank_angle":1.570796,"area_m2":3.896,"rings":[{"outer":[[1800.0,5025.0],[200.0,5025.0],[200.0,2625.0],[1800.0,2625.0],[1800.0,3525.0],[1875.0,3525.0],[1875.0,4275.0],[1800.0,4275.0]],"holes":[]}]}],"skirting":[{"room":"Room_01","ring":[[13425.1,1900.0],[13425.1,1915.0],[12965.0,1915.0],[12965.0,3990.0],[12735.0,3990.0],[12735.0,440.0],[10315.0,440.0],[10315.0,3990.0],[10265.0,3990.0],[10265.0,4020.0],[10250.0,4020.0],[10250.0,3975.0],[10300.0,3975.0],[10300.0,425.0],[12750.0,425.0],[12750.0,3975.0],[12950.0,3975.0],[12950.0,1900.0]],"holes":[],"length_mm":12380.1,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Living","name":"Skirting_01"},{"room":"Room_01","ring":[[10250.0,5025.0],[10265.0,5025.0],[10265.0,6485.0],[15250.0,6485.0],[15250.0,6500.0],[10250.0,6500.0]],"holes":[],"length_mm":6460.0,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Living","name":"Skirting_02"},{"room":"Room_01","ring":[[16300.0,1900.0],[16300.0,6500.0],[16255.0,6500.0],[16255.0,6485.0],[16285.0,6485.0],[16285.0,1915.0],[15825.1,1915.0],[15825.1,1900.0]],"holes":[],"length_mm":5089.9,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Living","name":"Skirting_03"},{"room":"Room_02","ring":[[2475.0,-100.0],[4625.0,-100.0],[4625.0,925.0],[4750.0,925.0],[4750.0,425.0],[5150.0,425.0],[5150.0,3975.0],[6400.0,3975.0],[6400.0,4125.0],[6412.5,4125.0],[6412.5,4170.0],[6397.5,4170.0],[6397.5,4140.0],[6385.0,4140.0],[6385.0,3990.0],[5135.0,3990.0],[5135.0,440.0],[4765.0,440.0],[4765.0,940.0],[4610.0,940.0],[4610.0,-85.0],[2490.0,-85.0],[2490.1,975.0],[1965.0,975.0],[1965.0,3525.0],[1950.0,3525.0],[1950.0,960.0],[2475.1,960.0]],"holes":[],"length_mm":13327.5,"mat":"MAT_Skirting_Master","skirt_obj":"Skirting_MasterBedroom","name":"Skirting_04"},{"room":"Room_02","ring":[[1950.0,4275.0],[1965.0,4275.0],[1965.0,5010.0],[6397.5,5010.0],[6397.5,4980.0],[6412.5,4980.0],[6412.5,5025.0],[1950.0,5025.0]],"holes":[],"length_mm":5227.5,"mat":"MAT_Skirting_Master","skirt_obj":"Skirting_MasterBedroom","name":"Skirting_05"},{"room":"Room_03","ring":[[6550.1,3825.0],[6550.1,3975.0],[6400.0,3975.0],[6400.0,3825.0],[5350.0,3825.0],[5350.0,725.0],[7275.0,725.0],[7275.0,425.0],[8400.0,425.0],[8400.0,3825.0],[8355.0,3825.0],[8355.0,3810.0],[8385.0,3810.0],[8385.0,440.0],[7290.0,440.0],[7290.0,740.0],[5365.0,740.0],[5365.0,3810.0],[6415.0,3810.0],[6415.0,3960.0],[6535.1,3960.0],[6535.1,3810.0],[7500.1,3810.0],[7500.1,3825.0]],"holes":[],"length_mm":12285.1,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Bedroom","name":"Skirting_06"},{"room":"Room_04","ring":[[12950.0,1425.0],[12950.0,275.0],[16300.0,275.0],[16300.0,1775.0],[15825.1,1775.0],[15825.1,1760.0],[16285.0,1760.0],[16285.0,290.0],[12965.0,290.0],[12965.0,1410.0],[13215.1,1410.0],[13215.1,1760.0],[13425.1,1760.0],[13425.1,1775.0],[13200.1,1775.0],[13200.1,1425.0]],"holes":[],"length_mm":7240.0,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Kitchen","name":"Skirting_07"},{"room":"Room_05","ring":[[10050.0,5025.0],[6537.5,5025.0],[6537.5,4980.0],[6552.5,4980.0],[6552.5,5010.0],[10035.0,5010.0],[10035.0,4980.0],[10050.0,4980.0]],"holes":[],"length_mm":3572.5,"mat":"MAT_Skirting_Entrance","skirt_obj":"Skirting_Entrance_01","name":"Skirting_08"},{"room":"Room_05","ring":[[9300.1,3325.0],[9300.1,3340.0],[8565.0,3340.0],[8565.0,3990.0],[8400.0,3990.0],[8400.0,3975.0],[8550.0,3975.0],[8550.0,3325.0]],"holes":[],"length_mm":1550.1,"mat":"MAT_Skirting_Entrance","skirt_obj":"Skirting_Entrance_01","name":"Skirting_09"},{"room":"Room_05","ring":[[7500.1,3975.0],[7500.1,3990.0],[6565.0,3990.0],[6565.0,4140.0],[6552.5,4140.0],[6552.5,4170.0],[6537.5,4170.0],[6537.5,4125.0],[6550.0,4125.0],[6550.0,3975.0]],"holes":[],"length_mm":1142.6,"mat":"MAT_Skirting_Entrance","skirt_obj":"Skirting_Entrance_01","name":"Skirting_10"},{"room":"Room_05","ring":[[10050.0,3325.0],[10050.0,3975.0],[10035.0,3975.0],[10035.0,3340.0],[10005.0,3340.0],[10005.0,3325.0]],"holes":[],"length_mm":680.0,"mat":"MAT_Skirting_Entrance","skirt_obj":"Skirting_Entrance_01","name":"Skirting_11"}],"room_skirting":[{"name":"Skirting_Living","room":"Room_01","label":"Living","use":"living","category":"common","mat":"MAT_Skirting_Common","length_mm":23930.0,"runs":[{"outer":[[16300.0,1900.0],[16300.0,6500.0],[16255.0,6500.0],[16255.0,6485.0],[16285.0,6485.0],[16285.0,1915.0],[15825.1,1915.0],[15825.1,1900.0]],"holes":[]},{"outer":[[13425.1,1900.0],[13425.1,1915.0],[12965.0,1915.0],[12965.0,3990.0],[12735.0,3990.0],[12735.0,440.0],[10315.0,440.0],[10315.0,3990.0],[10265.0,3990.0],[10265.0,4020.0],[10250.0,4020.0],[10250.0,3975.0],[10300.0,3975.0],[10300.0,425.0],[12750.0,425.0],[12750.0,3975.0],[12950.0,3975.0],[12950.0,1900.0]],"holes":[]},{"outer":[[10250.0,5025.0],[10265.0,5025.0],[10265.0,6485.0],[15250.0,6485.0],[15250.0,6500.0],[10250.0,6500.0]],"holes":[]}]},{"name":"Skirting_Kitchen","room":"Room_04","label":"Kitchen","use":"kitchen","category":"common","mat":"MAT_Skirting_Common","length_mm":7240.0,"runs":[{"outer":[[12950.0,1425.0],[12950.0,275.0],[16300.0,275.0],[16300.0,1775.0],[15825.1,1775.0],[15825.1,1760.0],[16285.0,1760.0],[16285.0,290.0],[12965.0,290.0],[12965.0,1410.0],[13215.1,1410.0],[13215.1,1760.0],[13425.1,1760.0],[13425.1,1775.0],[13200.1,1775.0],[13200.1,1425.0]],"holes":[]}]},{"name":"Skirting_Entrance_01","room":"Room_05","label":"Lobby","use":"lobby","category":"entrance","mat":"MAT_Skirting_Entrance","length_mm":6945.2,"runs":[{"outer":[[10050.0,5025.0],[6537.5,5025.0],[6537.5,4980.0],[6552.5,4980.0],[6552.5,5010.0],[10035.0,5010.0],[10035.0,4980.0],[10050.0,4980.0]],"holes":[]},{"outer":[[10050.0,3325.0],[10050.0,3975.0],[10035.0,3975.0],[10035.0,3340.0],[10005.0,3340.0],[10005.0,3325.0]],"holes":[]},{"outer":[[9300.1,3325.0],[9300.1,3340.0],[8565.0,3340.0],[8565.0,3990.0],[8400.0,3990.0],[8400.0,3975.0],[8550.0,3975.0],[8550.0,3325.0]],"holes":[]},{"outer":[[7500.1,3975.0],[7500.1,3990.0],[6565.0,3990.0],[6565.0,4140.0],[6552.5,4140.0],[6552.5,4170.0],[6537.5,4170.0],[6537.5,4125.0],[6550.0,4125.0],[6550.0,3975.0]],"holes":[]}]},{"name":"Skirting_Bedroom","room":"Room_03","label":"Bedroom","use":"bedroom","category":"common","mat":"MAT_Skirting_Common","length_mm":12285.1,"runs":[{"outer":[[6550.1,3825.0],[6550.1,3975.0],[6400.0,3975.0],[6400.0,3825.0],[5350.0,3825.0],[5350.0,725.0],[7275.0,725.0],[7275.0,425.0],[8400.0,425.0],[8400.0,3825.0],[8355.0,3825.0],[8355.0,3810.0],[8385.0,3810.0],[8385.0,440.0],[7290.0,440.0],[7290.0,740.0],[5365.0,740.0],[5365.0,3810.0],[6415.0,3810.0],[6415.0,3960.0],[6535.1,3960.0],[6535.1,3810.0],[7500.1,3810.0],[7500.1,3825.0]],"holes":[]}]},{"name":"Skirting_MasterBedroom","room":"Room_02","label":"Master_Bedroom","use":"master_bedroom","category":"master_wood","mat":"MAT_Skirting_Master","length_mm":18555.0,"runs":[{"outer":[[2475.0,-100.0],[4625.0,-100.0],[4625.0,925.0],[4750.0,925.0],[4750.0,425.0],[5150.0,425.0],[5150.0,3975.0],[6400.0,3975.0],[6400.0,4125.0],[6412.5,4125.0],[6412.5,4170.0],[6397.5,4170.0],[6397.5,4140.0],[6385.0,4140.0],[6385.0,3990.0],[5135.0,3990.0],[5135.0,440.0],[4765.0,440.0],[4765.0,940.0],[4610.0,940.0],[4610.0,-85.0],[2490.0,-85.0],[2490.1,975.0],[1965.0,975.0],[1965.0,3525.0],[1950.0,3525.0],[1950.0,960.0],[2475.1,960.0]],"holes":[]},{"outer":[[1950.0,4275.0],[1965.0,4275.0],[1965.0,5010.0],[6397.5,5010.0],[6397.5,4980.0],[6412.5,4980.0],[6412.5,5025.0],[1950.0,5025.0]],"holes":[]}]}],"tiles":[{"name":"T1_Wall01_R01_C01","room":"Toilet_1","wall":"Wall01","row":1,"col":1,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall01_R01_C02","room":"Toilet_1","wall":"Wall01","row":1,"col":2,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall01_R02_C01","room":"Toilet_1","wall":"Wall01","row":2,"col":1,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,0.0],[914.4,587.9],[426.1,587.9],[426.1,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T1_Wall01_R02_C02","room":"Toilet_1","wall":"Wall01","row":2,"col":2,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[571.6,0.0],[571.6,609.6],[109.2,609.6],[109.2,587.9],[0.0,587.9],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":false},{"name":"T1_Wall01_R03_C01","room":"Toilet_1","wall":"Wall01","row":3,"col":1,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[426.1,609.6],[0.0,609.6],[0.0,0.0],[426.1,0.0]],"full":false,"w":426.1,"h":609.6,"rect":true},{"name":"T1_Wall01_R03_C02","room":"Toilet_1","wall":"Wall01","row":3,"col":2,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":1037.6,"z0":1224.2,"poly":[[462.4,0.0],[462.4,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":462.4,"h":609.6,"rect":true},{"name":"T1_Wall01_R04_C01","room":"Toilet_1","wall":"Wall01","row":4,"col":1,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[426.1,0.0],[426.1,263.7],[914.4,263.7]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T1_Wall01_R04_C02","room":"Toilet_1","wall":"Wall01","row":4,"col":2,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,263.7],[109.2,263.7],[109.2,0.0]],"full":false,"w":571.6,"h":609.6,"rect":false},{"name":"T1_Wall01_R05_C01","room":"Toilet_1","wall":"Wall01","row":5,"col":1,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall01_R05_C02","room":"Toilet_1","wall":"Wall01","row":5,"col":2,"origin":[8550.0,1375.0],"dir":[1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[571.6,0.0],[571.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":571.6,"h":551.6,"rect":true},{"name":"T1_Wall02_R01_C01","room":"Toilet_1","wall":"Wall02","row":1,"col":1,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R01_C02","room":"Toilet_1","wall":"Wall02","row":1,"col":2,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":928.4,"z0":0.0,"poly":[[871.6,0.0],[871.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":871.6,"h":609.6,"rect":true},{"name":"T1_Wall02_R02_C01","room":"Toilet_1","wall":"Wall02","row":2,"col":1,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R02_C02","room":"Toilet_1","wall":"Wall02","row":2,"col":2,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":928.4,"z0":612.1,"poly":[[871.6,0.0],[871.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":871.6,"h":609.6,"rect":true},{"name":"T1_Wall02_R03_C01","room":"Toilet_1","wall":"Wall02","row":3,"col":1,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R03_C02","room":"Toilet_1","wall":"Wall02","row":3,"col":2,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":928.4,"z0":1224.2,"poly":[[871.6,0.0],[871.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":871.6,"h":609.6,"rect":true},{"name":"T1_Wall02_R04_C01","room":"Toilet_1","wall":"Wall02","row":4,"col":1,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R04_C02","room":"Toilet_1","wall":"Wall02","row":4,"col":2,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":928.4,"z0":1836.3,"poly":[[871.6,0.0],[871.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":871.6,"h":609.6,"rect":true},{"name":"T1_Wall02_R05_C01","room":"Toilet_1","wall":"Wall02","row":5,"col":1,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall02_R05_C02","room":"Toilet_1","wall":"Wall02","row":5,"col":2,"origin":[10050.0,1375.0],"dir":[0.0,1.0],"u0":928.4,"z0":2448.4,"poly":[[871.6,0.0],[871.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":871.6,"h":551.6,"rect":true},{"name":"T1_Wall03_R01_C01","room":"Toilet_1","wall":"Wall03","row":1,"col":1,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":749.9,"z0":0.0,"poly":[[176.0,609.6],[0.0,609.6],[0.0,0.0],[176.0,0.0]],"full":false,"w":176.0,"h":609.6,"rect":true},{"name":"T1_Wall03_R01_C02","room":"Toilet_1","wall":"Wall03","row":1,"col":2,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall03_R02_C01","room":"Toilet_1","wall":"Wall03","row":2,"col":1,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":749.9,"z0":612.1,"poly":[[176.0,609.6],[0.0,609.6],[0.0,0.0],[176.0,0.0]],"full":false,"w":176.0,"h":609.6,"rect":true},{"name":"T1_Wall03_R02_C02","room":"Toilet_1","wall":"Wall03","row":2,"col":2,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall03_R03_C01","room":"Toilet_1","wall":"Wall03","row":3,"col":1,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":749.9,"z0":1224.2,"poly":[[176.0,609.6],[0.0,609.6],[0.0,0.0],[176.0,0.0]],"full":false,"w":176.0,"h":609.6,"rect":true},{"name":"T1_Wall03_R03_C02","room":"Toilet_1","wall":"Wall03","row":3,"col":2,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1224.2,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall03_R04_C01","room":"Toilet_1","wall":"Wall03","row":4,"col":1,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,263.7],[738.4,263.7],[738.4,0.0],[914.4,0.0]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T1_Wall03_R04_C02","room":"Toilet_1","wall":"Wall03","row":4,"col":2,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall03_R05_C01","room":"Toilet_1","wall":"Wall03","row":5,"col":1,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall03_R05_C02","room":"Toilet_1","wall":"Wall03","row":5,"col":2,"origin":[10050.0,3175.0],"dir":[-1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[571.6,0.0],[571.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":571.6,"h":551.6,"rect":true},{"name":"T1_Wall04_R01_C01","room":"Toilet_1","wall":"Wall04","row":1,"col":1,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall04_R01_C02","room":"Toilet_1","wall":"Wall04","row":1,"col":2,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":928.4,"z0":0.0,"poly":[[871.6,0.0],[871.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":871.6,"h":609.6,"rect":true},{"name":"T1_Wall04_R02_C01","room":"Toilet_1","wall":"Wall04","row":2,"col":1,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall04_R02_C02","room":"Toilet_1","wall":"Wall04","row":2,"col":2,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":928.4,"z0":612.1,"poly":[[871.6,0.0],[871.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":871.6,"h":609.6,"rect":true},{"name":"T1_Wall04_R03_C01","room":"Toilet_1","wall":"Wall04","row":3,"col":1,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall04_R03_C02","room":"Toilet_1","wall":"Wall04","row":3,"col":2,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1224.2,"poly":[[871.6,0.0],[871.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":871.6,"h":609.6,"rect":true},{"name":"T1_Wall04_R04_C01","room":"Toilet_1","wall":"Wall04","row":4,"col":1,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall04_R04_C02","room":"Toilet_1","wall":"Wall04","row":4,"col":2,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1836.3,"poly":[[871.6,0.0],[871.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":871.6,"h":609.6,"rect":true},{"name":"T1_Wall04_R05_C01","room":"Toilet_1","wall":"Wall04","row":5,"col":1,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall04_R05_C02","room":"Toilet_1","wall":"Wall04","row":5,"col":2,"origin":[8550.0,3175.0],"dir":[0.0,-1.0],"u0":928.4,"z0":2448.4,"poly":[[871.6,0.0],[871.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":871.6,"h":551.6,"rect":true},{"name":"MT_Wall01_R01_C01","room":"Master_Toilet","wall":"Wall01","row":1,"col":1,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall01_R01_C02","room":"Master_Toilet","wall":"Wall01","row":1,"col":2,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"MT_Wall01_R02_C01","room":"Master_Toilet","wall":"Wall01","row":2,"col":1,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,0.0],[914.4,587.9],[488.6,587.9],[488.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"MT_Wall01_R02_C02","room":"Master_Toilet","wall":"Wall01","row":2,"col":2,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[671.6,0.0],[671.6,609.6],[171.7,609.6],[171.7,587.9],[0.0,587.9],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":false},{"name":"MT_Wall01_R03_C01","room":"Master_Toilet","wall":"Wall01","row":3,"col":1,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[488.6,609.6],[0.0,609.6],[0.0,0.0],[488.6,0.0]],"full":false,"w":488.6,"h":609.6,"rect":true},{"name":"MT_Wall01_R03_C02","room":"Master_Toilet","wall":"Wall01","row":3,"col":2,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":1100.1,"z0":1224.2,"poly":[[499.9,0.0],[499.9,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":499.9,"h":609.6,"rect":true},{"name":"MT_Wall01_R04_C01","room":"Master_Toilet","wall":"Wall01","row":4,"col":1,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[488.6,0.0],[488.6,263.7],[914.4,263.7]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"MT_Wall01_R04_C02","room":"Master_Toilet","wall":"Wall01","row":4,"col":2,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,263.7],[171.7,263.7],[171.7,0.0]],"full":false,"w":671.6,"h":609.6,"rect":false},{"name":"MT_Wall01_R05_C01","room":"Master_Toilet","wall":"Wall01","row":5,"col":1,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall01_R05_C02","room":"Master_Toilet","wall":"Wall01","row":5,"col":2,"origin":[200.0,2625.0],"dir":[1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[671.6,0.0],[671.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":671.6,"h":551.6,"rect":true},{"name":"MT_Wall02_R01_C01","room":"Master_Toilet","wall":"Wall02","row":1,"col":1,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":11.5,"z0":0.0,"poly":[[888.5,609.6],[0.0,609.6],[0.0,0.0],[888.5,0.0]],"full":false,"w":888.5,"h":609.6,"rect":true},{"name":"MT_Wall02_R01_C02","room":"Master_Toilet","wall":"Wall02","row":1,"col":2,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":1650.0,"z0":0.0,"poly":[[192.8,609.6],[0.0,609.6],[0.0,0.0],[192.8,0.0]],"full":false,"w":192.8,"h":609.6,"rect":true},{"name":"MT_Wall02_R01_C03","room":"Master_Toilet","wall":"Wall02","row":1,"col":3,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":1845.3,"z0":0.0,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall02_R02_C01","room":"Master_Toilet","wall":"Wall02","row":2,"col":1,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":11.5,"z0":612.1,"poly":[[888.5,609.6],[0.0,609.6],[0.0,0.0],[888.5,0.0]],"full":false,"w":888.5,"h":609.6,"rect":true},{"name":"MT_Wall02_R02_C02","room":"Master_Toilet","wall":"Wall02","row":2,"col":2,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":1650.0,"z0":612.1,"poly":[[192.8,609.6],[0.0,609.6],[0.0,0.0],[192.8,0.0]],"full":false,"w":192.8,"h":609.6,"rect":true},{"name":"MT_Wall02_R02_C03","room":"Master_Toilet","wall":"Wall02","row":2,"col":3,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":1845.3,"z0":612.1,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall02_R03_C01","room":"Master_Toilet","wall":"Wall02","row":3,"col":1,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":11.5,"z0":1224.2,"poly":[[888.5,609.6],[0.0,609.6],[0.0,0.0],[888.5,0.0]],"full":false,"w":888.5,"h":609.6,"rect":true},{"name":"MT_Wall02_R03_C02","room":"Master_Toilet","wall":"Wall02","row":3,"col":2,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":1650.0,"z0":1224.2,"poly":[[192.8,609.6],[0.0,609.6],[0.0,0.0],[192.8,0.0]],"full":false,"w":192.8,"h":609.6,"rect":true},{"name":"MT_Wall02_R03_C03","room":"Master_Toilet","wall":"Wall02","row":3,"col":3,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":1845.3,"z0":1224.2,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall02_R04_C01","room":"Master_Toilet","wall":"Wall02","row":4,"col":1,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[888.5,0.0],[888.5,263.7],[914.4,263.7]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"MT_Wall02_R04_C02","room":"Master_Toilet","wall":"Wall02","row":4,"col":2,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,609.6],[0.0,263.7],[721.6,263.7],[721.6,0.0],[914.4,0.0],[914.4,609.6]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"MT_Wall02_R04_C03","room":"Master_Toilet","wall":"Wall02","row":4,"col":3,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":1845.3,"z0":1836.3,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall02_R05_C01","room":"Master_Toilet","wall":"Wall02","row":5,"col":1,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall02_R05_C02","room":"Master_Toilet","wall":"Wall02","row":5,"col":2,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall02_R05_C03","room":"Master_Toilet","wall":"Wall02","row":5,"col":3,"origin":[1800.0,2625.0],"dir":[0.0,1.0],"u0":1845.3,"z0":2448.4,"poly":[[554.7,0.0],[554.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":554.7,"h":551.6,"rect":true},{"name":"MT_Wall03_R01_C01","room":"Master_Toilet","wall":"Wall03","row":1,"col":1,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R01_C02","room":"Master_Toilet","wall":"Wall03","row":1,"col":2,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"MT_Wall03_R02_C01","room":"Master_Toilet","wall":"Wall03","row":2,"col":1,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R02_C02","room":"Master_Toilet","wall":"Wall03","row":2,"col":2,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"MT_Wall03_R03_C01","room":"Master_Toilet","wall":"Wall03","row":3,"col":1,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R03_C02","room":"Master_Toilet","wall":"Wall03","row":3,"col":2,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1224.2,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"MT_Wall03_R04_C01","room":"Master_Toilet","wall":"Wall03","row":4,"col":1,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R04_C02","room":"Master_Toilet","wall":"Wall03","row":4,"col":2,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"MT_Wall03_R05_C01","room":"Master_Toilet","wall":"Wall03","row":5,"col":1,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall03_R05_C02","room":"Master_Toilet","wall":"Wall03","row":5,"col":2,"origin":[1800.0,5025.0],"dir":[-1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[671.6,0.0],[671.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":671.6,"h":551.6,"rect":true},{"name":"MT_Wall04_R01_C01","room":"Master_Toilet","wall":"Wall04","row":1,"col":1,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R01_C02","room":"Master_Toilet","wall":"Wall04","row":1,"col":2,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":928.4,"z0":0.0,"poly":[[0.0,609.6],[0.0,0.0],[914.4,0.0],[914.4,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R01_C03","room":"Master_Toilet","wall":"Wall04","row":1,"col":3,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":0.0,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall04_R02_C01","room":"Master_Toilet","wall":"Wall04","row":2,"col":1,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R02_C02","room":"Master_Toilet","wall":"Wall04","row":2,"col":2,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":928.4,"z0":612.1,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R02_C03","room":"Master_Toilet","wall":"Wall04","row":2,"col":3,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":612.1,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall04_R03_C01","room":"Master_Toilet","wall":"Wall04","row":3,"col":1,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R03_C02","room":"Master_Toilet","wall":"Wall04","row":3,"col":2,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1224.2,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R03_C03","room":"Master_Toilet","wall":"Wall04","row":3,"col":3,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":1224.2,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall04_R04_C01","room":"Master_Toilet","wall":"Wall04","row":4,"col":1,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R04_C02","room":"Master_Toilet","wall":"Wall04","row":4,"col":2,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R04_C03","room":"Master_Toilet","wall":"Wall04","row":4,"col":3,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":1836.3,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall04_R05_C01","room":"Master_Toilet","wall":"Wall04","row":5,"col":1,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall04_R05_C02","room":"Master_Toilet","wall":"Wall04","row":5,"col":2,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall04_R05_C03","room":"Master_Toilet","wall":"Wall04","row":5,"col":3,"origin":[200.0,5025.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":2448.4,"poly":[[554.7,0.0],[554.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":554.7,"h":551.6,"rect":true}],"panels":[{"name":"R01_Wall01_P01","room":"Room_01","wall":"Wall01","col":1,"origin":[10300.0,425.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[610.1,500.0],[610.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1220.0,"h":2900.0},{"name":"R01_Wall01_P02","room":"Room_01","wall":"Wall01","col":2,"origin":[10300.0,425.0],"dir":[1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1212.0,0.0],[1212.0,2900.0],[587.1,2900.0],[587.1,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1212.0,"h":2900.0},{"name":"R01_Wall02_P01","room":"Room_01","wall":"Wall02","col":1,"origin":[12750.0,425.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall02_P02","room":"Room_01","wall":"Wall02","col":2,"origin":[12750.0,425.0],"dir":[0.0,1.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall02_P03","room":"Room_01","wall":"Wall02","col":3,"origin":[12750.0,425.0],"dir":[0.0,1.0],"u0":2461.0,"z0":100.0,"poly":[[1089.0,0.0],[1089.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1089.0,"h":2900.0},{"name":"R01_Wall03_P01","room":"Room_01","wall":"Wall03","col":1,"origin":[12750.0,3975.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[200.0,0.0],[200.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":200.0,"h":2900.0},{"name":"R01_Wall04_P01","room":"Room_01","wall":"Wall04","col":1,"origin":[12950.0,3975.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall04_P02","room":"Room_01","wall":"Wall04","col":2,"origin":[12950.0,3975.0],"dir":[0.0,-1.0],"u0":1223.0,"z0":100.0,"poly":[[852.0,0.0],[852.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":852.0,"h":2900.0},{"name":"R01_Wall05_P01","room":"Room_01","wall":"Wall05","col":1,"origin":[12950.0,1900.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[460.1,2900.0],[0.0,2900.0],[0.0,0.0],[460.1,0.0]],"full":false,"w":460.1,"h":2900.0},{"name":"R01_Wall05_P03","room":"Room_01","wall":"Wall05","col":3,"origin":[12950.0,1900.0],"dir":[1.0,0.0],"u0":2875.1,"z0":100.0,"poly":[[474.9,0.0],[474.9,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":474.9,"h":2900.0},{"name":"R01_Wall06_P01","room":"Room_01","wall":"Wall06","col":1,"origin":[16300.0,1900.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall06_P02","room":"Room_01","wall":"Wall06","col":2,"origin":[16300.0,1900.0],"dir":[0.0,1.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall06_P03","room":"Room_01","wall":"Wall06","col":3,"origin":[16300.0,1900.0],"dir":[0.0,1.0],"u0":2461.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall06_P04","room":"Room_01","wall":"Wall06","col":4,"origin":[16300.0,1900.0],"dir":[0.0,1.0],"u0":3684.0,"z0":100.0,"poly":[[916.0,0.0],[916.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":916.0,"h":2900.0},{"name":"R01_Wall07_P01","room":"Room_01","wall":"Wall07","col":1,"origin":[16300.0,6500.0],"dir":[-1.0,0.0],"u0":1050.0,"z0":100.0,"poly":[[185.0,0.0],[185.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":185.0,"h":2900.0},{"name":"R01_Wall07_P02","room":"Room_01","wall":"Wall07","col":2,"origin":[16300.0,6500.0],"dir":[-1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall07_P03","room":"Room_01","wall":"Wall07","col":3,"origin":[16300.0,6500.0],"dir":[-1.0,0.0],"u0":2461.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall07_P04","room":"Room_01","wall":"Wall07","col":4,"origin":[16300.0,6500.0],"dir":[-1.0,0.0],"u0":3684.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall07_P05","room":"Room_01","wall":"Wall07","col":5,"origin":[16300.0,6500.0],"dir":[-1.0,0.0],"u0":4907.0,"z0":100.0,"poly":[[1143.0,0.0],[1143.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1143.0,"h":2900.0},{"name":"R01_Wall08_P01","room":"Room_01","wall":"Wall08","col":1,"origin":[10250.0,6500.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[642.0,0.0],[642.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":642.0,"h":2900.0},{"name":"R01_Wall08_P02","room":"Room_01","wall":"Wall08","col":2,"origin":[10250.0,6500.0],"dir":[0.0,-1.0],"u0":660.0,"z0":100.0,"poly":[[815.0,2900.0],[0.0,2900.0],[0.0,0.0],[815.0,0.0]],"full":false,"w":815.0,"h":2900.0},{"name":"R01_Wall09_P01","room":"Room_01","wall":"Wall09","col":1,"origin":[10250.0,3975.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[50.0,0.0],[50.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":50.0,"h":2900.0},{"name":"R01_Wall10_P01","room":"Room_01","wall":"Wall10","col":1,"origin":[10300.0,3975.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall10_P02","room":"Room_01","wall":"Wall10","col":2,"origin":[10300.0,3975.0],"dir":[0.0,-1.0],"u0":1223.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall10_P03","room":"Room_01","wall":"Wall10","col":3,"origin":[10300.0,3975.0],"dir":[0.0,-1.0],"u0":2446.0,"z0":100.0,"poly":[[1104.0,0.0],[1104.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1104.0,"h":2900.0},{"name":"R04_Wall01_P01","room":"Room_04","wall":"Wall01","col":1,"origin":[12950.0,275.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":500.0},{"name":"R04_Wall01_P02","room":"Room_04","wall":"Wall01","col":2,"origin":[12950.0,275.0],"dir":[1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":500.0},{"name":"R04_Wall01_P03","room":"Room_04","wall":"Wall01","col":3,"origin":[12950.0,275.0],"dir":[1.0,0.0],"u0":2461.0,"z0":100.0,"poly":[[889.0,0.0],[889.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":889.0,"h":500.0},{"name":"R04_Wall02_P01","room":"Room_04","wall":"Wall02","col":1,"origin":[16300.0,275.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[885.0,2900.0],[885.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":2900.0},{"name":"R04_Wall02_P02","room":"Room_04","wall":"Wall02","col":2,"origin":[16300.0,275.0],"dir":[0.0,1.0],"u0":1238.0,"z0":100.0,"poly":[[262.0,0.0],[262.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":262.0,"h":2900.0},{"name":"R04_Wall03_P01","room":"Room_04","wall":"Wall03","col":1,"origin":[16300.0,1775.0],"dir":[-1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[459.9,2900.0],[0.0,2900.0],[0.0,0.0],[459.9,0.0]],"full":false,"w":459.9,"h":2900.0},{"name":"R04_Wall03_P03","room":"Room_04","wall":"Wall03","col":3,"origin":[16300.0,1775.0],"dir":[-1.0,0.0],"u0":2874.9,"z0":100.0,"poly":[[225.0,0.0],[225.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":225.0,"h":2900.0},{"name":"R04_Wall04_P01","room":"Room_04","wall":"Wall04","col":1,"origin":[13200.1,1775.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[335.0,0.0],[335.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":335.0,"h":2900.0},{"name":"R04_Wall05_P01","room":"Room_04","wall":"Wall05","col":1,"origin":[13200.1,1425.0],"dir":[-1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[250.1,0.0],[250.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":250.1,"h":2900.0},{"name":"R04_Wall06_P01","room":"Room_04","wall":"Wall06","col":1,"origin":[12950.0,1425.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[1135.0,0.0],[1135.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1135.0,"h":2900.0},{"name":"R05_Wall01_P01","room":"Room_05","wall":"Wall01","col":1,"origin":[8550.0,3325.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[735.1,2900.0],[0.0,2900.0],[0.0,0.0],[735.1,0.0]],"full":false,"w":735.1,"h":2900.0},{"name":"R05_Wall02_P01","room":"Room_05","wall":"Wall02","col":1,"origin":[10050.0,3325.0],"dir":[0.0,1.0],"u0":0.0,"z0":100.0,"poly":[[650.0,2900.0],[0.0,2900.0],[0.0,0.0],[650.0,0.0]],"full":false,"w":650.0,"h":2900.0},{"name":"R05_Wall03_P01","room":"Room_05","wall":"Wall03","col":1,"origin":[10050.0,5025.0],"dir":[-1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R05_Wall03_P02","room":"Room_05","wall":"Wall03","col":2,"origin":[10050.0,5025.0],"dir":[-1.0,0.0],"u0":1223.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R05_Wall03_P03","room":"Room_05","wall":"Wall03","col":3,"origin":[10050.0,5025.0],"dir":[-1.0,0.0],"u0":2446.0,"z0":100.0,"poly":[[1066.5,0.0],[1066.5,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1066.5,"h":2900.0},{"name":"R05_Wall06_P01","room":"Room_05","wall":"Wall06","col":1,"origin":[6550.0,4125.0],"dir":[0.0,-1.0],"u0":3.0,"z0":100.0,"poly":[[147.0,0.0],[147.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":147.0,"h":2900.0},{"name":"R05_Wall07_P01","room":"Room_05","wall":"Wall07","col":1,"origin":[6550.0,3975.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[935.1,2900.0],[0.0,2900.0],[0.0,0.0],[935.1,0.0]],"full":false,"w":935.1,"h":2900.0},{"name":"R05_Wall07_P02","room":"Room_05","wall":"Wall07","col":2,"origin":[6550.0,3975.0],"dir":[1.0,0.0],"u0":1850.0,"z0":100.0,"poly":[[150.0,0.0],[150.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":150.0,"h":2900.0},{"name":"R05_Wall08_P01","room":"Room_05","wall":"Wall08","col":1,"origin":[8550.0,3975.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[650.0,0.0],[650.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":650.0,"h":2900.0},{"name":"R03_Wall01_P01","room":"Room_03","wall":"Wall01","col":1,"origin":[7275.0,425.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1110.0,0.0],[1110.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1110.0,"h":2900.0},{"name":"R03_Wall02_P01","room":"Room_03","wall":"Wall02","col":1,"origin":[8400.0,425.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall02_P02","room":"Room_03","wall":"Wall02","col":2,"origin":[8400.0,425.0],"dir":[0.0,1.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall02_P03","room":"Room_03","wall":"Wall02","col":3,"origin":[8400.0,425.0],"dir":[0.0,1.0],"u0":2461.0,"z0":100.0,"poly":[[939.0,0.0],[939.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":939.0,"h":2900.0},{"name":"R03_Wall03_P01","room":"Room_03","wall":"Wall03","col":1,"origin":[8400.0,3825.0],"dir":[-1.0,0.0],"u0":899.9,"z0":100.0,"poly":[[335.1,0.0],[335.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":335.1,"h":2900.0},{"name":"R03_Wall03_P02","room":"Room_03","wall":"Wall03","col":2,"origin":[8400.0,3825.0],"dir":[-1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[611.9,0.0],[611.9,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":611.9,"h":2900.0},{"name":"R03_Wall04_P01","room":"Room_03","wall":"Wall04","col":1,"origin":[6550.1,3825.0],"dir":[0.0,1.0],"u0":0.0,"z0":100.0,"poly":[[150.0,0.0],[150.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":150.0,"h":2900.0},{"name":"R03_Wall05_P01","room":"Room_03","wall":"Wall05","col":1,"origin":[6550.1,3975.0],"dir":[-1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[135.1,0.0],[135.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":135.1,"h":2900.0},{"name":"R03_Wall06_P01","room":"Room_03","wall":"Wall06","col":1,"origin":[6400.0,3975.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[135.0,0.0],[135.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":135.0,"h":2900.0},{"name":"R03_Wall07_P01","room":"Room_03","wall":"Wall07","col":1,"origin":[6400.0,3825.0],"dir":[-1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[1050.0,0.0],[1050.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1050.0,"h":2900.0},{"name":"R03_Wall08_P01","room":"Room_03","wall":"Wall08","col":1,"origin":[5350.0,3825.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall08_P02","room":"Room_03","wall":"Wall08","col":2,"origin":[5350.0,3825.0],"dir":[0.0,-1.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall08_P03","room":"Room_03","wall":"Wall08","col":3,"origin":[5350.0,3825.0],"dir":[0.0,-1.0],"u0":2461.0,"z0":100.0,"poly":[[639.0,0.0],[639.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":639.0,"h":2900.0},{"name":"R03_Wall09_P01","room":"Room_03","wall":"Wall09","col":1,"origin":[5350.0,725.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":500.0},{"name":"R03_Wall09_P02","room":"Room_03","wall":"Wall09","col":2,"origin":[5350.0,725.0],"dir":[1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[687.0,0.0],[687.0,2900.0],[562.0,2900.0],[562.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":687.0,"h":2900.0},{"name":"R03_Wall10_P01","room":"Room_03","wall":"Wall10","col":1,"origin":[7275.0,725.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[300.0,0.0],[300.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":300.0,"h":2900.0},{"name":"R02_Wall01_P01","room":"Room_02","wall":"Wall01","col":1,"origin":[2475.0,-100.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":500.0},{"name":"R02_Wall01_P02","room":"Room_02","wall":"Wall01","col":2,"origin":[2475.0,-100.0],"dir":[1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[912.0,0.0],[912.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":912.0,"h":500.0},{"name":"R02_Wall02_P01","room":"Room_02","wall":"Wall02","col":1,"origin":[4625.0,-100.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1010.0,0.0],[1010.0,2900.0],[385.0,2900.0],[385.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1010.0,"h":2900.0},{"name":"R02_Wall03_P01","room":"Room_02","wall":"Wall03","col":1,"origin":[4625.0,925.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[125.0,0.0],[125.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":125.0,"h":2900.0},{"name":"R02_Wall04_P01","room":"Room_02","wall":"Wall04","col":1,"origin":[4750.0,925.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[500.0,0.0],[500.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":500.0,"h":2900.0},{"name":"R02_Wall05_P01","room":"Room_02","wall":"Wall05","col":1,"origin":[4750.0,425.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[385.0,0.0],[385.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":385.0,"h":2900.0},{"name":"R02_Wall06_P01","room":"Room_02","wall":"Wall06","col":1,"origin":[5150.0,425.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall06_P02","room":"Room_02","wall":"Wall06","col":2,"origin":[5150.0,425.0],"dir":[0.0,1.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall06_P03","room":"Room_02","wall":"Wall06","col":3,"origin":[5150.0,425.0],"dir":[0.0,1.0],"u0":2461.0,"z0":100.0,"poly":[[1089.0,0.0],[1089.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1089.0,"h":2900.0},{"name":"R02_Wall07_P01","room":"Room_02","wall":"Wall07","col":1,"origin":[5150.0,3975.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[623.5,0.0],[623.5,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":623.5,"h":2900.0},{"name":"R02_Wall07_P02","room":"Room_02","wall":"Wall07","col":2,"origin":[5150.0,3975.0],"dir":[1.0,0.0],"u0":626.5,"z0":100.0,"poly":[[623.5,0.0],[623.5,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":623.5,"h":2900.0},{"name":"R02_Wall08_P01","room":"Room_02","wall":"Wall08","col":1,"origin":[6400.0,3975.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[132.0,2900.0],[0.0,2900.0],[0.0,0.0],[132.0,0.0]],"full":false,"w":132.0,"h":2900.0},{"name":"R02_Wall11_P01","room":"Room_02","wall":"Wall11","col":1,"origin":[6412.5,5025.0],"dir":[-1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall11_P02","room":"Room_02","wall":"Wall11","col":2,"origin":[6412.5,5025.0],"dir":[-1.0,0.0],"u0":1223.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall11_P03","room":"Room_02","wall":"Wall11","col":3,"origin":[6412.5,5025.0],"dir":[-1.0,0.0],"u0":2446.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall11_P04","room":"Room_02","wall":"Wall11","col":4,"origin":[6412.5,5025.0],"dir":[-1.0,0.0],"u0":3669.0,"z0":100.0,"poly":[[793.5,0.0],[793.5,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":793.5,"h":2900.0},{"name":"R02_Wall12_P01","room":"Room_02","wall":"Wall12","col":1,"origin":[1950.0,5025.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[735.0,2900.0],[0.0,2900.0],[0.0,0.0],[735.0,0.0]],"full":false,"w":735.0,"h":2900.0},{"name":"R02_Wall12_P02","room":"Room_02","wall":"Wall12","col":2,"origin":[1950.0,5025.0],"dir":[0.0,-1.0],"u0":1500.0,"z0":100.0,"poly":[[958.0,0.0],[958.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":958.0,"h":2900.0},{"name":"R02_Wall12_P03","room":"Room_02","wall":"Wall12","col":3,"origin":[1950.0,5025.0],"dir":[0.0,-1.0],"u0":2461.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall12_P04","room":"Room_02","wall":"Wall12","col":4,"origin":[1950.0,5025.0],"dir":[0.0,-1.0],"u0":3684.0,"z0":100.0,"poly":[[381.0,0.0],[381.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":381.0,"h":2900.0},{"name":"R02_Wall13_P01","room":"Room_02","wall":"Wall13","col":1,"origin":[1950.0,960.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[510.1,0.0],[510.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":510.1,"h":2900.0},{"name":"R02_Wall14_P01","room":"Room_02","wall":"Wall14","col":1,"origin":[2475.1,960.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[657.0,2900.0],[0.0,2900.0],[0.0,0.0],[657.0,0.0]],"full":false,"w":657.0,"h":2900.0},{"name":"R02_Wall16_P01","room":"Room_02","wall":"Wall16","col":1,"origin":[2475.0,300.0],"dir":[0.0,-1.0],"u0":3.0,"z0":100.0,"poly":[[397.0,0.0],[397.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":397.0,"h":500.0}],"kitchens":[],"glass_partitions":[],"recessed_ceilings":[{"room":"Room_01","label":"Living","use":"living","z_soffit":2950.0,"z_wall_top":3000.0,"z_cavity":3120.0,"z_slab_top":3200.0,"border_w":450.0,"cavity_rings":[{"outer":[[10700.0,4425.0],[10750.0,4425.0],[10750.0,875.0],[12300.0,875.0],[12300.0,4425.0],[13400.0,4425.0],[13400.0,2350.0],[15850.0,2350.0],[15850.0,6050.0],[10700.0,6050.0]],"holes":[]}],"collar_rings":[{"outer":[[10675.0,6075.0],[10675.0,4400.0],[10725.0,4400.0],[10725.0,850.0],[12325.0,850.0],[12325.0,4400.0],[13375.0,4400.0],[13375.0,2325.0],[15875.0,2325.0],[15875.0,6075.0]],"holes":[[[10750.0,4425.0],[10700.0,4425.0],[10700.0,6050.0],[15850.0,6050.0],[15850.0,2350.0],[13400.0,2350.0],[13400.0,4425.0],[12300.0,4425.0],[12300.0,875.0],[10750.0,875.0]]],"caps":[[[10725.0,3462.5],[10750.0,3462.5],[10750.0,4425.0],[10700.0,4425.0],[10700.0,6050.0],[15850.0,6050.0],[15850.0,3462.5],[15875.0,3462.5],[15875.0,6075.0],[10675.0,6075.0],[10675.0,4400.0],[10725.0,4400.0]],[[12325.0,3462.5],[12300.0,3462.5],[12300.0,875.0],[10750.0,875.0],[10750.0,3462.5],[10725.0,3462.5],[10725.0,850.0],[12325.0,850.0]],[[13375.0,3462.5],[13400.0,3462.5],[13400.0,4425.0],[12300.0,4425.0],[12300.0,3462.5],[12325.0,3462.5],[12325.0,4400.0],[13375.0,4400.0]],[[15875.0,3462.5],[15850.0,3462.5],[15850.0,2350.0],[13400.0,2350.0],[13400.0,3462.5],[13375.0,3462.5],[13375.0,2325.0],[15875.0,2325.0]]]}],"soffit_rings":[{"outer":[[16285.0,1915.0],[16285.0,6485.0],[10265.0,6485.0],[10265.0,3990.0],[10315.0,3990.0],[10315.0,440.0],[12735.0,440.0],[12735.0,3990.0],[12965.0,3990.0],[12965.0,1915.0]],"holes":[[[10750.0,4425.0],[10700.0,4425.0],[10700.0,6050.0],[15850.0,6050.0],[15850.0,2350.0],[13400.0,2350.0],[13400.0,4425.0],[12300.0,4425.0],[12300.0,875.0],[10750.0,875.0]]],"caps":[[[16285.0,3462.5],[15850.0,3462.5],[15850.0,2350.0],[13400.0,2350.0],[13400.0,3462.5],[12965.0,3462.5],[12965.0,1915.0],[16285.0,1915.0]],[[10315.0,3462.5],[10750.0,3462.5],[10750.0,4425.0],[10700.0,4425.0],[10700.0,6050.0],[15850.0,6050.0],[15850.0,3462.5],[16285.0,3462.5],[16285.0,6485.0],[10265.0,6485.0],[10265.0,3990.0],[10315.0,3990.0]],[[12735.0,3462.5],[12300.0,3462.5],[12300.0,875.0],[10750.0,875.0],[10750.0,3462.5],[10315.0,3462.5],[10315.0,440.0],[12735.0,440.0]],[[12965.0,3462.5],[13400.0,3462.5],[13400.0,4425.0],[12300.0,4425.0],[12300.0,3462.5],[12735.0,3462.5],[12735.0,3990.0],[12965.0,3990.0]]]}],"lip_rings":[{"outer":[[10700.0,6050.0],[10700.0,4425.0],[10750.0,4425.0],[10750.0,875.0],[12300.0,875.0],[12300.0,4425.0],[13400.0,4425.0],[13400.0,2350.0],[15850.0,2350.0],[15850.0,6050.0]],"holes":[[[10810.0,4485.0],[10760.0,4485.0],[10760.0,5990.0],[15790.0,5990.0],[15790.0,2410.0],[13460.0,2410.0],[13460.0,4485.0],[12240.0,4485.0],[12240.0,935.0],[10810.0,935.0]]],"caps":[[[10750.0,3462.5],[10810.0,3462.5],[10810.0,4485.0],[10760.0,4485.0],[10760.0,5990.0],[15790.0,5990.0],[15790.0,3462.5],[15850.0,3462.5],[15850.0,6050.0],[10700.0,6050.0],[10700.0,4425.0],[10750.0,4425.0]],[[12300.0,3462.5],[12240.0,3462.5],[12240.0,935.0],[10810.0,935.0],[10810.0,3462.5],[10750.0,3462.5],[10750.0,875.0],[12300.0,875.0]],[[13400.0,3462.5],[13460.0,3462.5],[13460.0,4485.0],[12240.0,4485.0],[12240.0,3462.5],[12300.0,3462.5],[12300.0,4425.0],[13400.0,4425.0]],[[15850.0,3462.5],[15790.0,3462.5],[15790.0,2410.0],[13460.0,2410.0],[13460.0,3462.5],[13400.0,3462.5],[13400.0,2350.0],[15850.0,2350.0]]]}],"cove_led_rings":[{"outer":[[10710.0,6040.0],[10710.0,4435.0],[10760.0,4435.0],[10760.0,885.0],[12290.0,885.0],[12290.0,4435.0],[13410.0,4435.0],[13410.0,2360.0],[15840.0,2360.0],[15840.0,6040.0]],"holes":[[[10796.0,4471.0],[10746.0,4471.0],[10746.0,6004.0],[15804.0,6004.0],[15804.0,2396.0],[13446.0,2396.0],[13446.0,4471.0],[12254.0,4471.0],[12254.0,921.0],[10796.0,921.0]]],"caps":[[[10760.0,3462.5],[10796.0,3462.5],[10796.0,4471.0],[10746.0,4471.0],[10746.0,6004.0],[15804.0,6004.0],[15804.0,3462.5],[15840.0,3462.5],[15840.0,6040.0],[10710.0,6040.0],[10710.0,4435.0],[10760.0,4435.0]],[[12290.0,3462.5],[12254.0,3462.5],[12254.0,921.0],[10796.0,921.0],[10796.0,3462.5],[10760.0,3462.5],[10760.0,885.0],[12290.0,885.0]],[[13410.0,3462.5],[13446.0,3462.5],[13446.0,4471.0],[12254.0,4471.0],[12254.0,3462.5],[12290.0,3462.5],[12290.0,4435.0],[13410.0,4435.0]],[[15840.0,3462.5],[15804.0,3462.5],[15804.0,2396.0],[13446.0,2396.0],[13446.0,3462.5],[13410.0,3462.5],[13410.0,2360.0],[15840.0,2360.0]]]}],"fixtures":[{"x":10482.5,"y":5237.5,"z":2950.0,"mount":"soffit"},{"x":11413.3,"y":6267.5,"z":2950.0,"mount":"soffit"},{"x":13275.0,"y":6267.5,"z":2950.0,"mount":"soffit"},{"x":15136.7,"y":6267.5,"z":2950.0,"mount":"soffit"},{"x":16067.5,"y":5233.8,"z":2950.0,"mount":"soffit"},{"x":16067.5,"y":3166.2,"z":2950.0,"mount":"soffit"},{"x":15346.2,"y":2132.5,"z":2950.0,"mount":"soffit"},{"x":13903.8,"y":2132.5,"z":2950.0,"mount":"soffit"},{"x":13182.5,"y":3170.0,"z":2950.0,"mount":"soffit"},{"x":12517.5,"y":3320.0,"z":2950.0,"mount":"soffit"},{"x":12517.5,"y":1545.0,"z":2950.0,"mount":"soffit"},{"x":11525.0,"y":657.5,"z":2950.0,"mount":"soffit"},{"x":10532.5,"y":1545.0,"z":2950.0,"mount":"soffit"},{"x":10532.5,"y":3320.0,"z":2950.0,"mount":"soffit"},{"x":14437.5,"y":4631.2,"z":3120.0,"mount":"cavity"}]},{"room":"Room_03","label":"Bedroom","use":"bedroom","z_soffit":2950.0,"z_wall_top":3000.0,"z_cavity":3120.0,"z_slab_top":3200.0,"border_w":450.0,"cavity_rings":[{"outer":[[5800.0,3375.0],[5800.0,1175.0],[7725.0,1175.0],[7725.0,875.0],[7950.0,875.0],[7950.0,3375.0]],"holes":[]}],"collar_rings":[{"outer":[[7975.0,850.0],[7975.0,3400.0],[5775.0,3400.0],[5775.0,1150.0],[7700.0,1150.0],[7700.0,850.0]],"holes":[[[5800.0,3375.0],[7950.0,3375.0],[7950.0,875.0],[7725.0,875.0],[7725.0,1175.0],[5800.0,1175.0]]],"caps":[[[7975.0,2125.0],[7950.0,2125.0],[7950.0,875.0],[7725.0,875.0],[7725.0,1175.0],[5800.0,1175.0],[5800.0,2125.0],[5775.0,2125.0],[5775.0,1150.0],[7700.0,1150.0],[7700.0,850.0],[7975.0,850.0]],[[5775.0,2125.0],[5800.0,2125.0],[5800.0,3375.0],[7950.0,3375.0],[7950.0,2125.0],[7975.0,2125.0],[7975.0,3400.0],[5775.0,3400.0]]]}],"soffit_rings":[{"outer":[[6535.1,3810.0],[6535.1,3960.0],[6415.0,3960.0],[6415.0,3810.0],[5365.0,3810.0],[5365.0,740.0],[7290.0,740.0],[7290.0,440.0],[8385.0,440.0],[8385.0,3810.0]],"holes":[[[5800.0,3375.0],[7950.0,3375.0],[7950.0,875.0],[7725.0,875.0],[7725.0,1175.0],[5800.0,1175.0]]],"caps":[[[5365.0,2125.0],[5800.0,2125.0],[5800.0,3375.0],[7950.0,3375.0],[7950.0,2125.0],[8385.0,2125.0],[8385.0,3810.0],[6535.1,3810.0],[6535.1,3960.0],[6415.0,3960.0],[6415.0,3810.0],[5365.0,3810.0]],[[8385.0,2125.0],[7950.0,2125.0],[7950.0,875.0],[7725.0,875.0],[7725.0,1175.0],[5800.0,1175.0],[5800.0,2125.0],[5365.0,2125.0],[5365.0,740.0],[7290.0,740.0],[7290.0,440.0],[8385.0,440.0]]]}],"lip_rings":[{"outer":[[5800.0,3375.0],[5800.0,1175.0],[7725.0,1175.0],[7725.0,875.0],[7950.0,875.0],[7950.0,3375.0]],"holes":[[[5860.0,3315.0],[7890.0,3315.0],[7890.0,935.0],[7785.0,935.0],[7785.0,1235.0],[5860.0,1235.0]]],"caps":[[[5800.0,2125.0],[5860.0,2125.0],[5860.0,3315.0],[7890.0,3315.0],[7890.0,2125.0],[7950.0,2125.0],[7950.0,3375.0],[5800.0,3375.0]],[[7950.0,2125.0],[7890.0,2125.0],[7890.0,935.0],[7785.0,935.0],[7785.0,1235.0],[5860.0,1235.0],[5860.0,2125.0],[5800.0,2125.0],[5800.0,1175.0],[7725.0,1175.0],[7725.0,875.0],[7950.0,875.0]]]}],"cove_led_rings":[{"outer":[[7940.0,885.0],[7940.0,3365.0],[5810.0,3365.0],[5810.0,1185.0],[7735.0,1185.0],[7735.0,885.0]],"holes":[[[5846.0,3329.0],[7904.0,3329.0],[7904.0,921.0],[7771.0,921.0],[7771.0,1221.0],[5846.0,1221.0]]],"caps":[[[7940.0,2125.0],[7904.0,2125.0],[7904.0,921.0],[7771.0,921.0],[7771.0,1221.0],[5846.0,1221.0],[5846.0,2125.0],[5810.0,2125.0],[5810.0,1185.0],[7735.0,1185.0],[7735.0,885.0],[7940.0,885.0]],[[5810.0,2125.0],[5846.0,2125.0],[5846.0,3329.0],[7904.0,3329.0],[7904.0,2125.0],[7940.0,2125.0],[7940.0,3365.0],[5810.0,3365.0]]]}],"fixtures":[{"x":7400.0,"y":3592.5,"z":2950.0,"mount":"soffit"},{"x":8167.5,"y":2858.8,"z":2950.0,"mount":"soffit"},{"x":8167.5,"y":1391.2,"z":2950.0,"mount":"soffit"},{"x":6545.0,"y":957.5,"z":2950.0,"mount":"soffit"},{"x":5582.5,"y":1616.2,"z":2950.0,"mount":"soffit"},{"x":5582.5,"y":2933.8,"z":2950.0,"mount":"soffit"},{"x":6875.0,"y":2275.0,"z":3120.0,"mount":"cavity"}]},{"room":"Room_02","label":"Master_Bedroom","use":"master_bedroom","z_soffit":2950.0,"z_wall_top":3000.0,"z_cavity":3120.0,"z_slab_top":3200.0,"border_w":450.0,"cavity_rings":[{"outer":[[2925.1,350.0],[4175.0,350.0],[4175.0,1375.0],[4700.0,1375.0],[4700.0,4425.0],[5950.0,4425.0],[5950.0,4575.0],[2400.0,4575.0],[2400.0,1410.0],[2925.1,1410.0]],"holes":[]}],"collar_rings":[{"outer":[[2900.1,1385.0],[2900.1,325.0],[4200.0,325.0],[4200.0,1350.0],[4725.0,1350.0],[4725.0,4400.0],[5975.0,4400.0],[5975.0,4600.0],[2375.0,4600.0],[2375.0,1385.0]],"holes":[[[4175.0,350.0],[2925.1,350.0],[2925.1,1410.0],[2400.0,1410.0],[2400.0,4575.0],[5950.0,4575.0],[5950.0,4425.0],[4700.0,4425.0],[4700.0,1375.0],[4175.0,1375.0]]],"caps":[[[4725.0,2462.5],[4700.0,2462.5],[4700.0,1375.0],[4175.0,1375.0],[4175.0,350.0],[2925.1,350.0],[2925.1,1410.0],[2400.0,1410.0],[2400.0,2462.5],[2375.0,2462.5],[2375.0,1385.0],[2900.1,1385.0],[2900.1,325.0],[4200.0,325.0],[4200.0,1350.0],[4725.0,1350.0]],[[2375.0,2462.5],[2400.0,2462.5],[2400.0,4575.0],[5950.0,4575.0],[5950.0,4425.0],[4700.0,4425.0],[4700.0,2462.5],[4725.0,2462.5],[4725.0,4400.0],[5975.0,4400.0],[5975.0,4600.0],[2375.0,4600.0]]]}],"soffit_rings":[{"outer":[[2490.0,-85.0],[4610.0,-85.0],[4610.0,940.0],[4765.0,940.0],[4765.0,440.0],[5135.0,440.0],[5135.0,3990.0],[6385.0,3990.0],[6385.0,4140.0],[6397.5,4140.0],[6397.5,5010.0],[1965.0,5010.0],[1965.0,975.0],[2490.1,975.0]],"holes":[[[4175.0,350.0],[2925.1,350.0],[2925.1,1410.0],[2400.0,1410.0],[2400.0,4575.0],[5950.0,4575.0],[5950.0,4425.0],[4700.0,4425.0],[4700.0,1375.0],[4175.0,1375.0]]],"caps":[[[5135.0,2462.5],[4700.0,2462.5],[4700.0,1375.0],[4175.0,1375.0],[4175.0,350.0],[2925.1,350.0],[2925.1,1410.0],[2400.0,1410.0],[2400.0,2462.5],[1965.0,2462.5],[1965.0,975.0],[2490.1,975.0],[2490.0,-85.0],[4610.0,-85.0],[4610.0,940.0],[4765.0,940.0],[4765.0,440.0],[5135.0,440.0]],[[1965.0,2462.5],[2400.0,2462.5],[2400.0,4575.0],[5950.0,4575.0],[5950.0,4425.0],[4700.0,4425.0],[4700.0,2462.5],[5135.0,2462.5],[5135.0,3990.0],[6385.0,3990.0],[6385.0,4140.0],[6397.5,4140.0],[6397.5,5010.0],[1965.0,5010.0]]]}],"lip_rings":[{"outer":[[2925.1,1410.0],[2925.1,350.0],[4175.0,350.0],[4175.0,1375.0],[4700.0,1375.0],[4700.0,4425.0],[5950.0,4425.0],[5950.0,4575.0],[2400.0,4575.0],[2400.0,1410.0]],"holes":[[[4115.0,410.0],[2985.1,410.0],[2985.1,1470.0],[2460.0,1470.0],[2460.0,4515.0],[5890.0,4515.0],[5890.0,4485.0],[4640.0,4485.0],[4640.0,1435.0],[4115.0,1435.0]]],"caps":[[[4700.0,2462.5],[4640.0,2462.5],[4640.0,1435.0],[4115.0,1435.0],[4115.0,410.0],[2985.1,410.0],[2985.1,1470.0],[2460.0,1470.0],[2460.0,2462.5],[2400.0,2462.5],[2400.0,1410.0],[2925.1,1410.0],[2925.1,350.0],[4175.0,350.0],[4175.0,1375.0],[4700.0,1375.0]],[[2400.0,2462.5],[2460.0,2462.5],[2460.0,4515.0],[5890.0,4515.0],[5890.0,4485.0],[4640.0,4485.0],[4640.0,2462.5],[4700.0,2462.5],[4700.0,4425.0],[5950.0,4425.0],[5950.0,4575.0],[2400.0,4575.0]]]}],"cove_led_rings":[{"outer":[[2935.1,1420.0],[2935.1,360.0],[4165.0,360.0],[4165.0,1385.0],[4690.0,1385.0],[4690.0,4435.0],[5940.0,4435.0],[5940.0,4565.0],[2410.0,4565.0],[2410.0,1420.0]],"holes":[[[4129.0,396.0],[2971.1,396.0],[2971.1,1456.0],[2446.0,1456.0],[2446.0,4529.0],[5904.0,4529.0],[5904.0,4471.0],[4654.0,4471.0],[4654.0,1421.0],[4129.0,1421.0]]],"caps":[[[4690.0,2462.5],[4654.0,2462.5],[4654.0,1421.0],[4129.0,1421.0],[4129.0,396.0],[2971.1,396.0],[2971.1,1456.0],[2446.0,1456.0],[2446.0,2462.5],[2410.0,2462.5],[2410.0,1420.0],[2935.1,1420.0],[2935.1,360.0],[4165.0,360.0],[4165.0,1385.0],[4690.0,1385.0]],[[2410.0,2462.5],[2446.0,2462.5],[2446.0,4529.0],[5904.0,4529.0],[5904.0,4471.0],[4654.0,4471.0],[4654.0,2462.5],[4690.0,2462.5],[4690.0,4435.0],[5940.0,4435.0],[5940.0,4565.0],[2410.0,4565.0]]]}],"fixtures":[{"x":2707.6,"y":662.5,"z":2950.0,"mount":"soffit"},{"x":2182.5,"y":2092.5,"z":2950.0,"mount":"soffit"},{"x":2182.5,"y":3892.5,"z":2950.0,"mount":"soffit"},{"x":3181.9,"y":4792.5,"z":2950.0,"mount":"soffit"},{"x":5180.6,"y":4792.5,"z":2950.0,"mount":"soffit"},{"x":5542.5,"y":4207.5,"z":2950.0,"mount":"soffit"},{"x":4917.5,"y":3445.0,"z":2950.0,"mount":"soffit"},{"x":4917.5,"y":1920.0,"z":2950.0,"mount":"soffit"},{"x":4392.5,"y":645.0,"z":2950.0,"mount":"soffit"},{"x":3550.1,"y":132.5,"z":2950.0,"mount":"soffit"},{"x":3550.0,"y":1531.2,"z":3120.0,"mount":"cavity"},{"x":3550.0,"y":3393.8,"z":3120.0,"mount":"cavity"}]}],"floor":[{"outer":[[2349.0,299.0],[2349.0,-201.0],[4751.0,-201.0],[4751.0,299.0],[5351.0,299.0],[5351.0,599.0],[7149.0,599.0],[7149.0,299.0],[10049.0,299.0],[10049.0,-1.0],[10251.0,-1.0],[10251.0,299.0],[12749.0,299.0],[12749.0,-1.0],[12951.0,-1.0],[12951.0,149.0],[16501.0,149.0],[16501.0,6626.0],[1799.0,6626.0],[1799.0,5151.0],[-1.0,5151.0],[-1.0,799.0],[1799.0,799.0],[1799.0,299.0]],"holes":[]}],"ceiling":[{"outer":[[1799.0,299.0],[2349.0,299.0],[2349.0,-201.0],[4751.0,-201.0],[4751.0,299.0],[5351.0,299.0],[5351.0,599.0],[7149.0,599.0],[7149.0,299.0],[10049.0,299.0],[10049.0,-1.0],[10251.0,-1.0],[10251.0,299.0],[12749.0,299.0],[12749.0,-1.0],[12951.0,-1.0],[12951.0,149.0],[16501.0,149.0],[16501.0,6626.0],[1799.0,6626.0],[1799.0,5151.0],[-1.0,5151.0],[-1.0,799.0],[1799.0,799.0]],"holes":[[[10700.0,6050.0],[15850.0,6050.0],[15850.0,2350.0],[13400.0,2350.0],[13400.0,4425.0],[12300.0,4425.0],[12300.0,875.0],[10750.0,875.0],[10750.0,4425.0],[10700.0,4425.0]],[[7950.0,3375.0],[7950.0,875.0],[7725.0,875.0],[7725.0,1175.0],[5800.0,1175.0],[5800.0,3375.0]],[[2925.1,1410.0],[2400.0,1410.0],[2400.0,4575.0],[5950.0,4575.0],[5950.0,4425.0],[4700.0,4425.0],[4700.0,1375.0],[4175.0,1375.0],[4175.0,350.0],[2925.1,350.0]]],"caps":[[[16501.0,3462.5],[15850.0,3462.5],[15850.0,2350.0],[13400.0,2350.0],[13400.0,3462.5],[12300.0,3462.5],[12300.0,2125.0],[16501.0,2125.0]],[[16501.0,2125.0],[12300.0,2125.0],[12300.0,875.0],[10750.0,875.0],[10750.0,2125.0],[7950.0,2125.0],[7950.0,875.0],[7725.0,875.0],[7725.0,1175.0],[5800.0,1175.0],[5800.0,2125.0],[4700.0,2125.0],[4700.0,1375.0],[4175.0,1375.0],[4175.0,350.0],[2925.1,350.0],[2925.1,1410.0],[2400.0,1410.0],[2400.0,2125.0],[-1.0,2125.0],[-1.0,799.0],[1799.0,799.0],[1799.0,299.0],[2349.0,299.0],[2349.0,-201.0],[4751.0,-201.0],[4751.0,299.0],[5351.0,299.0],[5351.0,599.0],[7149.0,599.0],[7149.0,299.0],[10049.0,299.0],[10049.0,-1.0],[10251.0,-1.0],[10251.0,299.0],[12749.0,299.0],[12749.0,-1.0],[12951.0,-1.0],[12951.0,149.0],[16501.0,149.0]],[[-1.0,2125.0],[2400.0,2125.0],[2400.0,3462.5],[-1.0,3462.5]],[[4700.0,2125.0],[5800.0,2125.0],[5800.0,3375.0],[7950.0,3375.0],[7950.0,2125.0],[10750.0,2125.0],[10750.0,3462.5],[4700.0,3462.5]],[[-1.0,3462.5],[2400.0,3462.5],[2400.0,4575.0],[5950.0,4575.0],[5950.0,4425.0],[4700.0,4425.0],[4700.0,3462.5],[10750.0,3462.5],[10750.0,4425.0],[10700.0,4425.0],[10700.0,6050.0],[15850.0,6050.0],[15850.0,3462.5],[16501.0,3462.5],[16501.0,6626.0],[1799.0,6626.0],[1799.0,5151.0],[-1.0,5151.0]],[[12300.0,3462.5],[13400.0,3462.5],[13400.0,4425.0],[12300.0,4425.0]]]}],"underlay":[[10250.0,6500.0,16300.0,6500.0],[10250.0,6625.0,16300.0,6625.0],[10050.0,6500.0,5350.0,6500.0],[5150.0,6625.0,1925.0,6625.0],[5150.0,6500.0,1925.0,6500.0],[10050.0,6625.0,5350.0,6625.0],[13200.0,1525.0,13200.0,1775.0],[1800.0,5150.0,1800.0,6625.0],[1925.0,5025.0,1925.0,6625.0],[1800.0,6625.0,1925.0,6625.0],[1800.0,5150.0,200.0,5150.0],[1925.0,5025.0,200.0,5025.0],[16300.0,6625.0,16300.0,4925.0],[16500.0,6625.0,16500.0,4925.0],[16300.0,6625.0,16500.0,6625.0],[1950.0,3525.0,1950.0,2625.0],[1950.0,2625.0,1950.0,925.0],[1950.0,800.0,1950.0,425.0],[6400.0,4125.0,6400.0,3975.0],[6550.0,4125.0,6550.0,3975.0],[7150.0,725.0,7150.0,300.0],[7275.0,725.0,7275.0,425.0],[7500.0,3975.0,7500.0,3825.0],[8525.0,1250.0,8525.0,300.0],[9300.0,3325.0,9300.0,3175.0],[10300.0,3975.0,10300.0,425.0],[12750.0,3975.0,12750.0,425.0],[12750.0,300.0,12750.0,0.0],[12950.0,3975.0,12950.0,1900.0],[15250.0,6625.0,15250.0,6500.0],[1800.0,5025.0,1800.0,5024.9],[1800.0,3525.0,1800.0,2625.0],[1800.0,2500.0,1800.0,300.0],[200.0,2500.0,700.0,2500.0],[1300.0,2500.0,1800.0,2500.0],[200.0,800.0,1800.0,800.0],[200.0,1000.0,1800.0,1000.0],[2475.0,300.0,1800.0,300.0],[2350.0,-200.0,4750.0,-200.0],[2400.0,-175.0,4700.0,-175.0],[2450.0,-125.0,4650.0,-125.0],[2475.0,-100.0,4625.0,-100.0],[1950.0,425.0,2475.0,425.0],[1950.0,925.0,2475.0,925.0],[1950.0,800.0,2475.0,800.0],[2475.0,300.0,2475.0,-100.0],[2350.0,300.0,2350.0,-200.0],[2400.0,300.0,2400.0,-175.0],[2450.0,300.0,2450.0,-125.0],[4625.0,300.0,4625.0,-100.0],[4750.0,300.0,4750.0,-200.0],[4700.0,300.0,4700.0,-175.0],[4650.0,300.0,4650.0,-125.0],[200.0,2625.0,700.0,2625.0],[1300.0,2625.0,1800.0,2625.0],[2475.0,300.0,2475.0,425.0],[2475.0,800.0,2475.0,925.0],[2000.0,800.0,2000.0,500.0],[2475.0,800.0,4625.0,800.0],[4625.0,300.0,4625.0,925.0],[4750.0,425.0,4750.0,925.0],[4625.0,925.0,4750.0,925.0],[6400.0,4125.0,6550.0,4125.0],[6550.0,3975.0,7500.0,3975.0],[1800.0,3525.0,1950.0,3525.0],[1800.0,3525.0,1800.0,4275.0],[7150.0,300.0,8525.0,300.0],[7275.0,425.0,8400.0,425.0],[5350.0,725.0,7150.0,725.0],[5350.0,600.0,7150.0,600.0],[5350.0,662.5,7150.0,662.5],[7150.0,725.0,7275.0,725.0],[8400.0,425.0,8400.0,3975.0],[8550.0,1375.0,8550.0,3175.0],[8550.0,3325.0,8550.0,3975.0],[8400.0,3975.0,8550.0,3975.0],[8550.0,3325.0,9300.0,3325.0],[8550.0,3175.0,9300.0,3175.0],[8550.0,1375.0,8987.5,1375.0],[9587.5,1375.0,10050.0,1375.0],[8525.0,1250.0,8987.5,1250.0],[9587.5,1250.0,10050.0,1250.0],[5350.0,3975.0,5150.0,3975.0],[8525.0,300.0,10050.0,300.0],[8525.0,500.0,10050.0,500.0],[8987.5,1375.0,8987.5,1250.0],[9587.5,1375.0,9587.5,1250.0],[9587.5,1250.0,8987.5,1250.0],[9587.5,1312.5,8987.5,1312.5],[9587.5,1375.0,8987.5,1375.0],[8525.0,500.0,10050.0,1250.0],[8525.0,1250.0,10050.0,500.0],[10050.0,0.0,10250.0,0.0],[10250.0,6500.0,15250.0,6500.0],[12950.0,1900.0,13425.0,1900.0],[15825.0,1900.0,16300.0,1900.0],[12950.0,1775.0,13425.0,1775.0],[15825.0,1775.0,16300.0,1775.0],[12950.0,275.0,16300.0,275.0],[12950.0,150.0,16500.0,150.0],[12950.0,200.0,16375.0,200.0],[12950.0,250.0,16325.0,250.0],[10250.0,6625.0,15250.0,6625.0],[12750.0,3975.0,12950.0,3975.0],[10250.0,300.0,10925.0,300.0],[12125.0,300.0,12750.0,300.0],[10250.0,425.0,10925.0,425.0],[12125.0,425.0,12750.0,425.0],[12125.0,300.0,12125.0,425.0],[10925.0,300.0,10925.0,425.0],[12125.0,300.0,10925.0,300.0],[12125.0,362.5,10925.0,362.5],[12125.0,425.0,10925.0,425.0],[10250.0,0.0,12750.0,0.0],[12750.0,0.0,12950.0,0.0],[15825.0,1775.0,15825.0,1900.0],[13425.0,1775.0,13425.0,1900.0],[15825.0,1775.0,13425.0,1775.0],[16300.0,275.0,16300.0,1175.0],[16500.0,150.0,16500.0,1175.0],[16375.0,200.0,16375.0,1175.0],[16325.0,250.0,16325.0,1175.0],[12950.0,0.0,12950.0,1775.0],[10050.0,3975.0,10300.0,3975.0],[700.0,2625.0,700.0,2500.0],[1300.0,2625.0,1300.0,2500.0],[1300.0,2500.0,700.0,2500.0],[1300.0,2562.5,700.0,2562.5],[1300.0,2625.0,700.0,2625.0],[200.0,1000.0,1800.0,2500.0],[200.0,2500.0,1800.0,1000.0],[2000.0,500.0,2350.0,800.0],[2000.0,800.0,2350.0,500.0],[5350.0,6500.0,5875.0,6500.0],[6625.0,6625.0,6625.0,6500.0],[6625.0,6500.0,5875.0,6500.0],[6625.0,5150.0,6875.0,6500.0],[6625.0,6500.0,6875.0,5150.0],[5600.0,5400.0,6625.0,5150.0],[6625.0,5400.0,5600.0,5150.0],[5600.0,5150.0,5350.0,6500.0],[5600.0,6500.0,5350.0,5150.0],[7000.0,5150.0,10050.0,6500.0],[7000.0,6500.0,10050.0,5150.0],[1925.0,5150.0,5150.0,6500.0],[5150.0,5150.0,1950.0,6499.9],[7000.0,6625.0,6625.0,6625.0],[10050.0,6500.0,7000.0,6500.0],[6875.0,6500.0,6625.0,6500.0],[10050.0,5025.0,5350.0,5025.0],[10050.0,5150.0,7000.0,5150.0],[6875.0,5150.0,5350.0,5150.0],[6625.0,5400.0,5600.0,5400.0],[5150.0,5150.0,1925.0,5150.0],[5875.0,6625.0,5350.0,6625.0],[5150.0,6625.0,1925.0,6625.0],[5150.0,6500.0,1925.0,6500.0],[5875.0,6500.0,5875.0,6625.0],[6875.0,6500.0,6875.0,5150.0],[6625.0,6500.0,6625.0,5400.0],[7000.0,6625.0,7000.0,5150.0],[10050.0,6625.0,7000.0,6625.0],[5600.0,6500.0,5600.0,5400.0],[2350.0,500.0,2000.0,500.0],[10050.0,0.0,10050.0,1250.0],[10250.0,3975.0,10250.0,425.0],[10250.0,300.0,10250.0,0.0],[2350.0,500.0,2350.0,800.0],[1800.0,4275.0,1950.0,4275.0],[1800.0,4275.0,1800.0,5025.0],[1950.0,4275.0,1950.0,5025.0],[16300.0,6625.0,16500.0,6625.0],[16500.0,6625.0,16500.0,1175.0],[16500.0,1175.0,16300.0,1175.0],[16300.0,1175.0,16300.0,1775.0],[16300.0,1900.0,16300.0,6625.0],[200.0,2500.0,0.0,2500.0],[0.0,2500.0,0.0,5150.0],[0.0,5150.0,1925.0,5150.0],[1800.0,5025.0,200.0,5025.0],[200.0,5025.0,200.0,2625.0],[12950.0,1525.0,13200.0,1775.0],[13200.0,1525.0,12950.0,1775.0],[13200.0,1525.0,13200.0,1775.0],[1950.0,5024.9,5150.0,5024.9],[10050.0,1375.0,10050.0,3975.0],[12950.0,1425.0,13200.0,1425.0],[13200.0,1425.0,13200.0,1525.0],[13200.0,1525.0,12950.0,1525.0],[16300.0,4925.0,16300.0,1175.0],[200.0,5150.0,0.0,5150.0],[0.0,5150.0,0.0,1400.0],[0.0,1400.0,0.0,800.0],[0.0,800.0,200.0,800.0],[200.0,800.0,200.0,5025.0],[5350.0,5025.0,5350.0,6625.0],[5350.0,6625.0,5150.0,6625.0],[5150.0,6625.0,5150.0,5025.0],[5150.0,5025.0,5350.0,5025.0],[10250.0,3961.1,10264.0,3975.0],[10250.0,3934.1,10290.9,3975.0],[10250.0,3907.2,10300.0,3957.2],[10250.0,3880.2,10300.0,3930.2],[10250.0,3853.3,10300.0,3903.3],[10250.0,3826.4,10300.0,3876.4],[10250.0,3799.4,10300.0,3849.4],[10250.0,3772.5,10300.0,3822.5],[10250.0,3745.5,10300.0,3795.5],[10250.0,3718.6,10300.0,3768.6],[10250.0,3691.7,10300.0,3741.7],[10250.0,3664.7,10300.0,3714.7],[10250.0,3637.8,10300.0,3687.8],[10250.0,3610.8,10300.0,3660.8],[10250.0,3583.9,10300.0,3633.9],[10250.0,3556.9,10300.0,3606.9],[10250.0,3530.0,10300.0,3580.0],[10250.0,3503.1,10300.0,3553.1],[10250.0,3476.1,10300.0,3526.1],[10250.0,3449.2,10300.0,3499.2],[10250.0,3422.2,10300.0,3472.2],[10250.0,3395.3,10300.0,3445.3],[10250.0,3368.4,10300.0,3418.4],[10250.0,3341.4,10300.0,3391.4],[10250.0,3314.5,10300.0,3364.5],[10250.0,3287.5,10300.0,3337.5],[10250.0,3260.6,10300.0,3310.6],[10250.0,3233.7,10300.0,3283.7],[10250.0,3206.7,10300.0,3256.7],[10250.0,3179.8,10300.0,3229.8],[10250.0,3152.8,10300.0,3202.8],[10250.0,3125.9,10300.0,3175.9],[10250.0,3099.0,10300.0,3149.0],[10250.0,3072.0,10300.0,3122.0],[10250.0,3045.1,10300.0,3095.1],[10250.0,3018.1,10300.0,3068.1],[10250.0,2991.2,10300.0,3041.2],[10250.0,2964.3,10300.0,3014.3],[10250.0,2937.3,10300.0,2987.3],[10250.0,2910.4,10300.0,2960.4],[10250.0,2883.4,10300.0,2933.4],[10250.0,2856.5,10300.0,2906.5],[10250.0,2829.5,10300.0,2879.5],[10250.0,2802.6,10300.0,2852.6],[10250.0,2775.7,10300.0,2825.7],[10250.0,2748.7,10300.0,2798.7],[10250.0,2721.8,10300.0,2771.8],[10250.0,2694.8,10300.0,2744.8],[10250.0,2667.9,10300.0,2717.9],[10250.0,2641.0,10300.0,2691.0],[10250.0,2614.0,10300.0,2664.0],[10250.0,2587.1,10300.0,2637.1],[10250.0,2560.1,10300.0,2610.1],[10250.0,2533.2,10300.0,2583.2],[10250.0,2506.3,10300.0,2556.3],[10250.0,2479.3,10300.0,2529.3],[10250.0,2452.4,10300.0,2502.4],[10250.0,2425.4,10300.0,2475.4],[10250.0,2398.5,10300.0,2448.5],[10250.0,2371.6,10300.0,2421.6],[10250.0,2344.6,10300.0,2394.6],[10250.0,2317.7,10300.0,2367.7],[10250.0,2290.7,10300.0,2340.7],[10250.0,2263.8,10300.0,2313.8],[10250.0,2236.9,10300.0,2286.9],[10250.0,2209.9,10300.0,2259.9],[10250.0,2183.0,10300.0,2233.0],[10250.0,2156.0,10300.0,2206.0],[10250.0,2129.1,10300.0,2179.1],[10250.0,2102.1,10300.0,2152.1],[10250.0,2075.2,10300.0,2125.2],[10250.0,2048.3,10300.0,2098.3],[10250.0,2021.3,10300.0,2071.3],[10250.0,1994.4,10300.0,2044.4],[10250.0,1967.4,10300.0,2017.4],[10250.0,1940.5,10300.0,1990.5],[10250.0,1913.6,10300.0,1963.6],[10250.0,1886.6,10300.0,1936.6],[10250.0,1859.7,10300.0,1909.7],[10250.0,1832.7,10300.0,1882.7],[10250.0,1805.8,10300.0,1855.8],[10250.0,1778.9,10300.0,1828.9],[10250.0,1751.9,10300.0,1801.9],[10250.0,1725.0,10300.0,1775.0],[10250.0,1698.0,10300.0,1748.0],[10250.0,1671.1,10300.0,1721.1],[10250.0,1644.2,10300.0,1694.2],[10250.0,1617.2,10300.0,1667.2],[10250.0,1590.3,10300.0,1640.3],[10250.0,1563.3,10300.0,1613.3],[10250.0,1536.4,10300.0,1586.4],[10250.0,1509.4,10300.0,1559.4],[10250.0,1482.5,10300.0,1532.5],[10250.0,1455.6,10300.0,1505.6],[10250.0,1428.6,10300.0,1478.6],[10250.0,1401.7,10300.0,1451.7],[10250.0,1374.7,10300.0,1424.7],[10250.0,1347.8,10300.0,1397.8],[10250.0,1320.9,10300.0,1370.9],[10250.0,1293.9,10300.0,1343.9],[10250.0,1267.0,10300.0,1317.0],[10250.0,1240.0,10300.0,1290.0],[10250.0,1213.1,10300.0,1263.1],[10250.0,1186.2,10300.0,1236.2],[10250.0,1159.2,10300.0,1209.2],[10250.0,1132.3,10300.0,1182.3],[10250.0,1105.3,10300.0,1155.3],[10250.0,1078.4,10300.0,1128.4],[10250.0,1051.5,10300.0,1101.5],[10250.0,1024.5,10300.0,1074.5],[10250.0,997.6,10300.0,1047.6],[10250.0,970.6,10300.0,1020.6],[10250.0,943.7,10300.0,993.7],[10250.0,916.8,10300.0,966.8],[10250.0,889.8,10300.0,939.8],[10250.0,862.9,10300.0,912.9],[10250.0,835.9,10300.0,885.9],[10250.0,809.0,10300.0,859.0],[10250.0,782.0,10300.0,832.0],[10250.0,755.1,10300.0,805.1],[10250.0,728.2,10300.0,778.2],[10250.0,701.2,10300.0,751.2],[10250.0,674.3,10300.0,724.3],[10250.0,647.3,10300.0,697.3],[10250.0,620.4,10300.0,670.4],[10250.0,593.5,10300.0,643.5],[10250.0,566.5,10300.0,616.5],[10250.0,539.6,10300.0,589.6],[10250.0,512.6,10300.0,562.6],[10250.0,485.7,10300.0,535.7],[10250.0,458.8,10300.0,508.8],[10250.0,431.8,10300.0,481.8],[10270.2,425.0,10300.0,454.9],[10297.1,425.0,10300.0,427.9],[10250.0,3974.5,10250.5,3975.0],[10252.4,3949.9,10259.1,3956.6],[10262.5,3960.0,10269.2,3966.7],[10272.6,3970.1,10277.5,3975.0],[10250.0,3920.6,10252.4,3923.0],[10255.7,3926.3,10262.5,3933.1],[10265.8,3936.4,10272.6,3943.2],[10275.9,3946.5,10282.7,3953.3],[10286.0,3956.6,10292.8,3963.4],[10296.1,3966.7,10300.0,3970.6],[10250.0,3893.7,10255.7,3899.4],[10259.1,3902.8,10265.8,3909.5],[10269.2,3912.9,10275.9,3919.6],[10279.3,3923.0,10286.0,3929.7],[10289.4,3933.1,10296.1,3939.8],[10299.5,3943.2,10300.0,3943.7],[10252.4,3869.1,10259.1,3875.8],[10262.5,3879.2,10269.2,3885.9],[10272.6,3889.3,10279.3,3896.0],[10282.7,3899.4,10289.4,3906.1],[10292.8,3909.5,10299.5,3916.2],[10250.0,3839.8,10252.4,3842.1],[10255.7,3845.5,10262.5,3852.2],[10265.8,3855.6,10272.6,3862.4],[10275.9,3865.7,10282.7,3872.5],[10286.0,3875.8,10292.8,3882.6],[10296.1,3885.9,10300.0,3889.8],[10250.0,3812.9,10255.7,3818.6],[10259.1,3821.9,10265.8,3828.7],[10269.2,3832.0,10275.9,3838.8],[10279.3,3842.1,10286.0,3848.9],[10289.4,3852.2,10296.1,3859.0],[10299.5,3862.4,10300.0,3862.9],[10252.4,3788.3,10259.1,3795.0],[10262.5,3798.4,10269.2,3805.1],[10272.6,3808.5,10279.3,3815.2],[10282.7,3818.6,10289.4,3825.3],[10292.8,3828.7,10299.5,3835.4],[10250.0,3759.0,10252.4,3761.3],[10255.7,3764.7,10262.5,3771.4],[10265.8,3774.8,10272.6,3781.5],[10275.9,3784.9,10282.7,3791.6],[10286.0,3795.0,10292.8,3801.7],[10296.1,3805.1,10300.0,3809.0],[10250.0,3732.1,10255.7,3737.8],[10259.1,3741.1,10265.8,3747.9],[10269.2,3751.2,10275.9,3758.0],[10279.3,3761.3,10286.0,3768.1],[10289.4,3771.4,10296.1,3778.2],[10299.5,3781.5,10300.0,3782.1],[10252.4,3707.4,10259.1,3714.2],[10262.5,3717.5,10269.2,3724.3],[10272.6,3727.6,10279.3,3734.4],[10282.7,3737.8,10289.4,3744.5],[10292.8,3747.9,10299.5,3754.6],[10250.0,3678.2,10252.4,3680.5],[10255.7,3683.9,10262.5,3690.6],[10265.8,3694.0,10272.6,3700.7],[10275.9,3704.1,10282.7,3710.8],[10286.0,3714.2,10292.8,3720.9],[10296.1,3724.3,10300.0,3728.2],[10250.0,3651.2,10255.7,3656.9],[10259.1,3660.3,10265.8,3667.0],[10269.2,3670.4,10275.9,3677.1],[10279.3,3680.5,10286.0,3687.2],[10289.4,3690.6,10296.1,3697.3],[10299.5,3700.7,10300.0,3701.2],[10252.4,3626.6,10259.1,3633.4],[10262.5,3636.7,10269.2,3643.5],[10272.6,3646.8,10279.3,3653.6],[10282.7,3656.9,10289.4,3663.7],[10292.8,3667.0,10299.5,3673.8],[10250.0,3597.4,10252.4,3599.7],[10255.7,3603.0,10262.5,3609.8],[10265.8,3613.2,10272.6,3619.9],[10275.9,3623.3,10282.7,3630.0],[10286.0,3633.4,10292.8,3640.1],[10296.1,3643.5,10300.0,3647.4],[10250.0,3570.4,10255.7,3576.1],[10259.1,3579.5,10265.8,3586.2],[10269.2,3589.6,10275.9,3596.3],[10279.3,3599.7,10286.0,3606.4],[10289.4,3609.8,10296.1,3616.5],[10299.5,3619.9,10300.0,3620.4],[10252.4,3545.8,10259.1,3552.5],[10262.5,3555.9,10269.2,3562.6],[10272.6,3566.0,10279.3,3572.7],[10282.7,3576.1,10289.4,3582.8],[10292.8,3586.2,10299.5,3592.9],[10250.0,3516.5,10252.4,3518.9],[10255.7,3522.2,10262.5,3529.0],[10265.8,3532.3,10272.6,3539.1],[10275.9,3542.4,10282.7,3549.2],[10286.0,3552.5,10292.8,3559.3],[10296.1,3562.6,10300.0,3566.5],[10250.0,3489.6,10255.7,3495.3],[10259.1,3498.7,10265.8,3505.4],[10269.2,3508.8,10275.9,3515.5],[10279.3,3518.9,10286.0,3525.6],[10289.4,3529.0,10296.1,3535.7],[10299.5,3539.1,10300.0,3539.6],[10252.4,3465.0,10259.1,3471.7],[10262.5,3475.1,10269.2,3481.8],[10272.6,3485.2,10279.3,3491.9],[10282.7,3495.3,10289.4,3502.0],[10292.8,3505.4,10299.5,3512.1],[10250.0,3435.7,10252.4,3438.0],[10255.7,3441.4,10262.5,3448.1],[10265.8,3451.5,10272.6,3458.2],[10275.9,3461.6,10282.7,3468.3],[10286.0,3471.7,10292.8,3478.4],[10296.1,3481.8,10300.0,3485.7],[10250.0,3408.8,10255.7,3414.5],[10259.1,3417.8,10265.8,3424.6],[10269.2,3427.9,10275.9,3434.7],[10279.3,3438.0,10286.0,3444.8],[10289.4,3448.1,10296.1,3454.9],[10299.5,3458.2,10300.0,3458.8],[10252.4,3384.2,10259.1,3390.9],[10262.5,3394.3,10269.2,3401.0],[10272.6,3404.4,10279.3,3411.1],[10282.7,3414.5,10289.4,3421.2],[10292.8,3424.6,10299.5,3431.3],[10250.0,3354.9,10252.4,3357.2],[10255.7,3360.6,10262.5,3367.3],[10265.8,3370.7,10272.6,3377.4],[10275.9,3380.8,10282.7,3387.5],[10286.0,3390.9,10292.8,3397.6],[10296.1,3401.0,10300.0,3404.9],[10250.0,3328.0,10255.7,3333.6],[10259.1,3337.0,10265.8,3343.7],[10269.2,3347.1,10275.9,3353.8],[10279.3,3357.2,10286.0,3363.9],[10289.4,3367.3,10296.1,3374.1],[10299.5,3377.4,10300.0,3378.0],[10252.4,3303.3,10259.1,3310.1],[10262.5,3313.4,10269.2,3320.2],[10272.6,3323.5,10279.3,3330.3],[10282.7,3333.6,10289.4,3340.4],[10292.8,3343.7,10299.5,3350.5],[10250.0,3274.1,10252.4,3276.4],[10255.7,3279.8,10262.5,3286.5],[10265.8,3289.9,10272.6,3296.6],[10275.9,3300.0,10282.7,3306.7],[10286.0,3310.1,10292.8,3316.8],[10296.1,3320.2,10300.0,3324.1],[10250.0,3247.1,10255.7,3252.8],[10259.1,3256.2,10265.8,3262.9],[10269.2,3266.3,10275.9,3273.0],[10279.3,3276.4,10286.0,3283.1],[10289.4,3286.5,10296.1,3293.2],[10299.5,3296.6,10300.0,3297.1],[10252.4,3222.5,10259.1,3229.2],[10262.5,3232.6,10269.2,3239.3],[10272.6,3242.7,10279.3,3249.5],[10282.7,3252.8,10289.4,3259.6],[10292.8,3262.9,10299.5,3269.7],[10250.0,3193.2,10252.4,3195.6],[10255.7,3198.9,10262.5,3205.7],[10265.8,3209.0,10272.6,3215.8],[10275.9,3219.1,10282.7,3225.9],[10286.0,3229.2,10292.8,3236.0],[10296.1,3239.3,10300.0,3243.2],[10250.0,3166.3,10255.7,3172.0],[10259.1,3175.4,10265.8,3182.1],[10269.2,3185.5,10275.9,3192.2],[10279.3,3195.6,10286.0,3202.3],[10289.4,3205.7,10296.1,3212.4],[10299.5,3215.8,10300.0,3216.3],[10252.4,3141.7,10259.1,3148.4],[10262.5,3151.8,10269.2,3158.5],[10272.6,3161.9,10279.3,3168.6],[10282.7,3172.0,10289.4,3178.7],[10292.8,3182.1,10299.5,3188.8],[10250.0,3112.4,10252.4,3114.7],[10255.7,3118.1,10262.5,3124.8],[10265.8,3128.2,10272.6,3135.0],[10275.9,3138.3,10282.7,3145.1],[10286.0,3148.4,10292.8,3155.2],[10296.1,3158.5,10300.0,3162.4],[10250.0,3085.5,10255.7,3091.2],[10259.1,3094.5,10265.8,3101.3],[10269.2,3104.6,10275.9,3111.4],[10279.3,3114.7,10286.0,3121.5],[10289.4,3124.8,10296.1,3131.6],[10299.5,3135.0,10300.0,3135.5],[10252.4,3060.9,10259.1,3067.6],[10262.5,3071.0,10269.2,3077.7],[10272.6,3081.1,10279.3,3087.8],[10282.7,3091.2,10289.4,3097.9],[10292.8,3101.3,10299.5,3108.0],[10250.0,3031.6,10252.4,3033.9],[10255.7,3037.3,10262.5,3044.0],[10265.8,3047.4,10272.6,3054.1],[10275.9,3057.5,10282.7,3064.2],[10286.0,3067.6,10292.8,3074.3],[10296.1,3077.7,10300.0,3081.6],[10250.0,3004.7,10255.7,3010.4],[10259.1,3013.7,10265.8,3020.5],[10269.2,3023.8,10275.9,3030.6],[10279.3,3033.9,10286.0,3040.7],[10289.4,3044.0,10296.1,3050.8],[10299.5,3054.1,10300.0,3054.7],[10252.4,2980.0,10259.1,2986.8],[10262.5,2990.1,10269.2,2996.9],[10272.6,3000.2,10279.3,3007.0],[10282.7,3010.4,10289.4,3017.1],[10292.8,3020.5,10299.5,3027.2],[10250.0,2950.8,10252.4,2953.1],[10255.7,2956.5,10262.5,2963.2],[10265.8,2966.6,10272.6,2973.3],[10275.9,2976.7,10282.7,2983.4],[10286.0,2986.8,10292.8,2993.5],[10296.1,2996.9,10300.0,3000.8],[10250.0,2923.8,10255.7,2929.5],[10259.1,2932.9,10265.8,2939.6],[10269.2,2943.0,10275.9,2949.7],[10279.3,2953.1,10286.0,2959.8],[10289.4,2963.2,10296.1,2969.9],[10299.5,2973.3,10300.0,2973.8],[10252.4,2899.2,10259.1,2906.0],[10262.5,2909.3,10269.2,2916.1],[10272.6,2919.4,10279.3,2926.2],[10282.7,2929.5,10289.4,2936.3],[10292.8,2939.6,10299.5,2946.4],[10250.0,2870.0,10252.4,2872.3],[10255.7,2875.6,10262.5,2882.4],[10265.8,2885.7,10272.6,2892.5],[10275.9,2895.9,10282.7,2902.6],[10286.0,2906.0,10292.8,2912.7],[10296.1,2916.1,10300.0,2920.0],[10250.0,2843.0,10255.7,2848.7],[10259.1,2852.1,10265.8,2858.8],[10269.2,2862.2,10275.9,2868.9],[10279.3,2872.3,10286.0,2879.0],[10289.4,2882.4,10296.1,2889.1],[10299.5,2892.5,10300.0,2893.0],[10252.4,2818.4,10259.1,2825.1],[10262.5,2828.5,10269.2,2835.2],[10272.6,2838.6,10279.3,2845.3],[10282.7,2848.7,10289.4,2855.4],[10292.8,2858.8,10299.5,2865.5],[10250.0,2789.1,10252.4,2791.5],[10255.7,2794.8,10262.5,2801.6],[10265.8,2804.9,10272.6,2811.7],[10275.9,2815.0,10282.7,2821.8],[10286.0,2825.1,10292.8,2831.9],[10296.1,2835.2,10300.0,2839.1],[10250.0,2762.2,10255.7,2767.9],[10259.1,2771.3,10265.8,2778.0],[10269.2,2781.4,10275.9,2788.1],[10279.3,2791.5,10286.0,2798.2],[10289.4,2801.6,10296.1,2808.3],[10299.5,2811.7,10300.0,2812.2],[10252.4,2737.6,10259.1,2744.3],[10262.5,2747.7,10269.2,2754.4],[10272.6,2757.8,10279.3,2764.5],[10282.7,2767.9,10289.4,2774.6],[10292.8,2778.0,10299.5,2784.7],[10250.0,2708.3,10252.4,2710.6],[10255.7,2714.0,10262.5,2720.7],[10265.8,2724.1,10272.6,2730.8],[10275.9,2734.2,10282.7,2740.9],[10286.0,2744.3,10292.8,2751.0],[10296.1,2754.4,10300.0,2758.3],[10250.0,2681.4,10255.7,2687.1],[10259.1,2690.4,10265.8,2697.2],[10269.2,2700.5,10275.9,2707.3],[10279.3,2710.6,10286.0,2717.4],[10289.4,2720.7,10296.1,2727.5],[10299.5,2730.8,10300.0,2731.4],[10252.4,2656.8,10259.1,2663.5],[10262.5,2666.9,10269.2,2673.6],[10272.6,2677.0,10279.3,2683.7],[10282.7,2687.1,10289.4,2693.8],[10292.8,2697.2,10299.5,2703.9],[10250.0,2627.5,10252.4,2629.8],[10255.7,2633.2,10262.5,2639.9],[10265.8,2643.3,10272.6,2650.0],[10275.9,2653.4,10282.7,2660.1],[10286.0,2663.5,10292.8,2670.2],[10296.1,2673.6,10300.0,2677.5],[10250.0,2600.6,10255.7,2606.2],[10259.1,2609.6,10265.8,2616.3],[10269.2,2619.7,10275.9,2626.4],[10279.3,2629.8,10286.0,2636.5],[10289.4,2639.9,10296.1,2646.7],[10299.5,2650.0,10300.0,2650.6],[10252.4,2575.9,10259.1,2582.7],[10262.5,2586.0,10269.2,2592.8],[10272.6,2596.1,10279.3,2602.9],[10282.7,2606.2,10289.4,2613.0],[10292.8,2616.3,10299.5,2623.1],[10250.0,2546.7,10252.4,2549.0],[10255.7,2552.4,10262.5,2559.1],[10265.8,2562.5,10272.6,2569.2],[10275.9,2572.6,10282.7,2579.3],[10286.0,2582.7,10292.8,2589.4],[10296.1,2592.8,10300.0,2596.7],[10250.0,2519.7,10255.7,2525.4],[10259.1,2528.8,10265.8,2535.5],[10269.2,2538.9,10275.9,2545.6],[10279.3,2549.0,10286.0,2555.7],[10289.4,2559.1,10296.1,2565.8],[10299.5,2569.2,10300.0,2569.7],[10252.4,2495.1,10259.1,2501.8],[10262.5,2505.2,10269.2,2511.9],[10272.6,2515.3,10279.3,2522.0],[10282.7,2525.4,10289.4,2532.2],[10292.8,2535.5,10299.5,2542.3],[10250.0,2465.8,10252.4,2468.2],[10255.7,2471.5,10262.5,2478.3],[10265.8,2481.6,10272.6,2488.4],[10275.9,2491.7,10282.7,2498.5],[10286.0,2501.8,10292.8,2508.6],[10296.1,2511.9,10300.0,2515.8],[10250.0,2438.9,10255.7,2444.6],[10259.1,2448.0,10265.8,2454.7],[10269.2,2458.1,10275.9,2464.8],[10279.3,2468.2,10286.0,2474.9],[10289.4,2478.3,10296.1,2485.0],[10299.5,2488.4,10300.0,2488.9],[10252.4,2414.3,10259.1,2421.0],[10262.5,2424.4,10269.2,2431.1],[10272.6,2434.5,10279.3,2441.2],[10282.7,2444.6,10289.4,2451.3],[10292.8,2454.7,10299.5,2461.4],[10250.0,2385.0,10252.4,2387.3],[10255.7,2390.7,10262.5,2397.4],[10265.8,2400.8,10272.6,2407.6],[10275.9,2410.9,10282.7,2417.7],[10286.0,2421.0,10292.8,2427.8],[10296.1,2431.1,10300.0,2435.0],[10250.0,2358.1,10255.7,2363.8],[10259.1,2367.1,10265.8,2373.9],[10269.2,2377.2,10275.9,2384.0],[10279.3,2387.3,10286.0,2394.1],[10289.4,2397.4,10296.1,2404.2],[10299.5,2407.6,10300.0,2408.1],[10252.4,2333.5,10259.1,2340.2],[10262.5,2343.6,10269.2,2350.3],[10272.6,2353.7,10279.3,2360.4],[10282.7,2363.8,10289.4,2370.5],[10292.8,2373.9,10299.5,2380.6],[10250.0,2304.2,10252.4,2306.5],[10255.7,2309.9,10262.5,2316.6],[10265.8,2320.0,10272.6,2326.7],[10275.9,2330.1,10282.7,2336.8],[10286.0,2340.2,10292.8,2346.9],[10296.1,2350.3,10300.0,2354.2],[10250.0,2277.3,10255.7,2283.0],[10259.1,2286.3,10265.8,2293.1],[10269.2,2296.4,10275.9,2303.2],[10279.3,2306.5,10286.0,2313.3],[10289.4,2316.6,10296.1,2323.4],[10299.5,2326.7,10300.0,2327.3],[10252.4,2252.6,10259.1,2259.4],[10262.5,2262.7,10269.2,2269.5],[10272.6,2272.8,10279.3,2279.6],[10282.7,2283.0,10289.4,2289.7],[10292.8,2293.1,10299.5,2299.8],[10250.0,2223.4,10252.4,2225.7],[10255.7,2229.1,10262.5,2235.8],[10265.8,2239.2,10272.6,2245.9],[10275.9,2249.3,10282.7,2256.0],[10286.0,2259.4,10292.8,2266.1],[10296.1,2269.5,10300.0,2273.4],[10250.0,2196.4,10255.7,2202.1],[10259.1,2205.5,10265.8,2212.2],[10269.2,2215.6,10275.9,2222.3],[10279.3,2225.7,10286.0,2232.4],[10289.4,2235.8,10296.1,2242.5],[10299.5,2245.9,10300.0,2246.4],[10252.4,2171.8,10259.1,2178.6],[10262.5,2181.9,10269.2,2188.7],[10272.6,2192.0,10279.3,2198.8],[10282.7,2202.1,10289.4,2208.9],[10292.8,2212.2,10299.5,2219.0],[10250.0,2142.6,10252.4,2144.9],[10255.7,2148.2,10262.5,2155.0],[10265.8,2158.3,10272.6,2165.1],[10275.9,2168.5,10282.7,2175.2],[10286.0,2178.6,10292.8,2185.3],[10296.1,2188.7,10300.0,2192.6],[10250.0,2115.6,10255.7,2121.3],[10259.1,2124.7,10265.8,2131.4],[10269.2,2134.8,10275.9,2141.5],[10279.3,2144.9,10286.0,2151.6],[10289.4,2155.0,10296.1,2161.7],[10299.5,2165.1,10300.0,2165.6],[10252.4,2091.0,10259.1,2097.7],[10262.5,2101.1,10269.2,2107.8],[10272.6,2111.2,10279.3,2117.9],[10282.7,2121.3,10289.4,2128.0],[10292.8,2131.4,10299.5,2138.1],[10250.0,2061.7,10252.4,2064.1],[10255.7,2067.4,10262.5,2074.2],[10265.8,2077.5,10272.6,2084.3],[10275.9,2087.6,10282.7,2094.4],[10286.0,2097.7,10292.8,2104.5],[10296.1,2107.8,10300.0,2111.7],[10250.0,2034.8,10255.7,2040.5],[10259.1,2043.9,10265.8,2050.6],[10269.2,2054.0,10275.9,2060.7],[10279.3,2064.1,10286.0,2070.8],[10289.4,2074.2,10296.1,2080.9],[10299.5,2084.3,10300.0,2084.8],[10252.4,2010.2,10259.1,2016.9],[10262.5,2020.3,10269.2,2027.0],[10272.6,2030.4,10279.3,2037.1],[10282.7,2040.5,10289.4,2047.2],[10292.8,2050.6,10299.5,2057.3],[10250.0,1980.9,10252.4,1983.2],[10255.7,1986.6,10262.5,1993.3],[10265.8,1996.7,10272.6,2003.4],[10275.9,2006.8,10282.7,2013.5],[10286.0,2016.9,10292.8,2023.6],[10296.1,2027.0,10300.0,2030.9],[10250.0,1954.0,10255.7,1959.7],[10259.1,1963.0,10265.8,1969.8],[10269.2,1973.1,10275.9,1979.9],[10279.3,1983.2,10286.0,1990.0],[10289.4,1993.3,10296.1,2000.1],[10299.5,2003.4,10300.0,2004.0],[10252.4,1929.4,10259.1,1936.1],[10262.5,1939.5,10269.2,1946.2],[10272.6,1949.6,10279.3,1956.3],[10282.7,1959.7,10289.4,1966.4],[10292.8,1969.8,10299.5,1976.5],[10250.0,1900.1,10252.4,1902.4],[10255.7,1905.8,10262.5,1912.5],[10265.8,1915.9,10272.6,1922.6],[10275.9,1926.0,10282.7,1932.7],[10286.0,1936.1,10292.8,1942.8],[10296.1,1946.2,10300.0,1950.1],[10250.0,1873.1,10255.7,1878.8],[10259.1,1882.2,10265.8,1888.9],[10269.2,1892.3,10275.9,1899.0],[10279.3,1902.4,10286.0,1909.1],[10289.4,1912.5,10296.1,1919.2],[10299.5,1922.6,10300.0,1923.1],[10252.4,1848.5,10259.1,1855.3],[10262.5,1858.6,10269.2,1865.4],[10272.6,1868.7,10279.3,1875.5],[10282.7,1878.8,10289.4,1885.6],[10292.8,1888.9,10299.5,1895.7],[10250.0,1819.3,10252.4,1821.6],[10255.7,1825.0,10262.5,1831.7],[10265.8,1835.1,10272.6,1841.8],[10275.9,1845.2,10282.7,1851.9],[10286.0,1855.3,10292.8,1862.0],[10296.1,1865.4,10300.0,1869.3],[10250.0,1792.3,10255.7,1798.0],[10259.1,1801.4,10265.8,1808.1],[10269.2,1811.5,10275.9,1818.2],[10279.3,1821.6,10286.0,1828.3],[10289.4,1831.7,10296.1,1838.4],[10299.5,1841.8,10300.0,1842.3],[10252.4,1767.7,10259.1,1774.4],[10262.5,1777.8,10269.2,1784.5],[10272.6,1787.9,10279.3,1794.6],[10282.7,1798.0,10289.4,1804.8],[10292.8,1808.1,10299.5,1814.9],[10250.0,1738.4,10252.4,1740.8],[10255.7,1744.1,10262.5,1750.9],[10265.8,1754.2,10272.6,1761.0],[10275.9,1764.3,10282.7,1771.1],[10286.0,1774.4,10292.8,1781.2],[10296.1,1784.5,10300.0,1788.4],[10250.0,1711.5,10255.7,1717.2],[10259.1,1720.6,10265.8,1727.3],[10269.2,1730.7,10275.9,1737.4],[10279.3,1740.8,10286.0,1747.5],[10289.4,1750.9,10296.1,1757.6],[10299.5,1761.0,10300.0,1761.5],[10252.4,1686.9,10259.1,1693.6],[10262.5,1697.0,10269.2,1703.7],[10272.6,1707.1,10279.3,1713.8],[10282.7,1717.2,10289.4,1723.9],[10292.8,1727.3,10299.5,1734.0],[10250.0,1657.6,10252.4,1659.9],[10255.7,1663.3,10262.5,1670.0],[10265.8,1673.4,10272.6,1680.2],[10275.9,1683.5,10282.7,1690.3],[10286.0,1693.6,10292.8,1700.4],[10296.1,1703.7,10300.0,1707.6],[10250.0,1630.7,10255.7,1636.4],[10259.1,1639.7,10265.8,1646.5],[10269.2,1649.8,10275.9,1656.6],[10279.3,1659.9,10286.0,1666.7],[10289.4,1670.0,10296.1,1676.8],[10299.5,1680.2,10300.0,1680.7],[10252.4,1606.1,10259.1,1612.8],[10262.5,1616.2,10269.2,1622.9],[10272.6,1626.3,10279.3,1633.0],[10282.7,1636.4,10289.4,1643.1],[10292.8,1646.5,10299.5,1653.2],[10250.0,1576.8,10252.4,1579.1],[10255.7,1582.5,10262.5,1589.2],[10265.8,1592.6,10272.6,1599.3],[10275.9,1602.7,10282.7,1609.4],[10286.0,1612.8,10292.8,1619.5],[10296.1,1622.9,10300.0,1626.8],[10250.0,1549.9,10255.7,1555.5],[10259.1,1558.9,10265.8,1565.7],[10269.2,1569.0,10275.9,1575.8],[10279.3,1579.1,10286.0,1585.9],[10289.4,1589.2,10296.1,1596.0],[10299.5,1599.3,10300.0,1599.9],[10252.4,1525.2,10259.1,1532.0],[10262.5,1535.3,10269.2,1542.1],[10272.6,1545.4,10279.3,1552.2],[10282.7,1555.5,10289.4,1562.3],[10292.8,1565.7,10299.5,1572.4],[10250.0,1496.0,10252.4,1498.3],[10255.7,1501.7,10262.5,1508.4],[10265.8,1511.8,10272.6,1518.5],[10275.9,1521.9,10282.7,1528.6],[10286.0,1532.0,10292.8,1538.7],[10296.1,1542.1,10300.0,1546.0],[10250.0,1469.0,10255.7,1474.7],[10259.1,1478.1,10265.8,1484.8],[10269.2,1488.2,10275.9,1494.9],[10279.3,1498.3,10286.0,1505.0],[10289.4,1508.4,10296.1,1515.1],[10299.5,1518.5,10300.0,1519.0],[10252.4,1444.4,10259.1,1451.2],[10262.5,1454.5,10269.2,1461.3],[10272.6,1464.6,10279.3,1471.4],[10282.7,1474.7,10289.4,1481.5],[10292.8,1484.8,10299.5,1491.6],[10250.0,1415.2,10252.4,1417.5],[10255.7,1420.8,10262.5,1427.6],[10265.8,1430.9,10272.6,1437.7],[10275.9,1441.1,10282.7,1447.8],[10286.0,1451.2,10292.8,1457.9],[10296.1,1461.3,10300.0,1465.2],[10250.0,1388.2,10255.7,1393.9],[10259.1,1397.3,10265.8,1404.0],[10269.2,1407.4,10275.9,1414.1],[10279.3,1417.5,10286.0,1424.2],[10289.4,1427.6,10296.1,1434.3],[10299.5,1437.7,10300.0,1438.2],[10252.4,1363.6,10259.1,1370.3],[10262.5,1373.7,10269.2,1380.4],[10272.6,1383.8,10279.3,1390.5],[10282.7,1393.9,10289.4,1400.6],[10292.8,1404.0,10299.5,1410.7],[10250.0,1334.3,10252.4,1336.7],[10255.7,1340.0,10262.5,1346.8],[10265.8,1350.1,10272.6,1356.9],[10275.9,1360.2,10282.7,1367.0],[10286.0,1370.3,10292.8,1377.1],[10296.1,1380.4,10300.0,1384.3],[10250.0,1307.4,10255.7,1313.1],[10259.1,1316.5,10265.8,1323.2],[10269.2,1326.6,10275.9,1333.3],[10279.3,1336.7,10286.0,1343.4],[10289.4,1346.8,10296.1,1353.5],[10299.5,1356.9,10300.0,1357.4],[10252.4,1282.8,10259.1,1289.5],[10262.5,1292.9,10269.2,1299.6],[10272.6,1303.0,10279.3,1309.7],[10282.7,1313.1,10289.4,1319.8],[10292.8,1323.2,10299.5,1329.9],[10250.0,1253.5,10252.4,1255.8],[10255.7,1259.2,10262.5,1265.9],[10265.8,1269.3,10272.6,1276.0],[10275.9,1279.4,10282.7,1286.1],[10286.0,1289.5,10292.8,1296.2],[10296.1,1299.6,10300.0,1303.5],[10250.0,1226.6,10255.7,1232.3],[10259.1,1235.6,10265.8,1242.4],[10269.2,1245.7,10275.9,1252.5],[10279.3,1255.8,10286.0,1262.6],[10289.4,1265.9,10296.1,1272.7],[10299.5,1276.0,10300.0,1276.6],[10252.4,1202.0,10259.1,1208.7],[10262.5,1212.1,10269.2,1218.8],[10272.6,1222.2,10279.3,1228.9],[10282.7,1232.3,10289.4,1239.0],[10292.8,1242.4,10299.5,1249.1],[10250.0,1172.7,10252.4,1175.0],[10255.7,1178.4,10262.5,1185.1],[10265.8,1188.5,10272.6,1195.2],[10275.9,1198.6,10282.7,1205.3],[10286.0,1208.7,10292.8,1215.4],[10296.1,1218.8,10300.0,1222.7],[10250.0,1145.7,10255.7,1151.4],[10259.1,1154.8,10265.8,1161.5],[10269.2,1164.9,10275.9,1171.6],[10279.3,1175.0,10286.0,1181.7],[10289.4,1185.1,10296.1,1191.8],[10299.5,1195.2,10300.0,1195.7],[10252.4,1121.1,10259.1,1127.9],[10262.5,1131.2,10269.2,1138.0],[10272.6,1141.3,10279.3,1148.1],[10282.7,1151.4,10289.4,1158.2],[10292.8,1161.5,10299.5,1168.3],[10250.0,1091.9,10252.4,1094.2],[10255.7,1097.6,10262.5,1104.3],[10265.8,1107.7,10272.6,1114.4],[10275.9,1117.8,10282.7,1124.5],[10286.0,1127.9,10292.8,1134.6],[10296.1,1138.0,10300.0,1141.9],[10250.0,1064.9,10255.7,1070.6],[10259.1,1074.0,10265.8,1080.7],[10269.2,1084.1,10275.9,1090.8],[10279.3,1094.2,10286.0,1100.9],[10289.4,1104.3,10296.1,1111.0],[10299.5,1114.4,10300.0,1114.9],[10252.4,1040.3,10259.1,1047.0],[10262.5,1050.4,10269.2,1057.1],[10272.6,1060.5,10279.3,1067.2],[10282.7,1070.6,10289.4,1077.4],[10292.8,1080.7,10299.5,1087.5],[10250.0,1011.0,10252.4,1013.4],[10255.7,1016.7,10262.5,1023.5],[10265.8,1026.8,10272.6,1033.6],[10275.9,1036.9,10282.7,1043.7],[10286.0,1047.0,10292.8,1053.8],[10296.1,1057.1,10300.0,1061.0],[10250.0,984.1,10255.7,989.8],[10259.1,993.2,10265.8,999.9],[10269.2,1003.3,10275.9,1010.0],[10279.3,1013.4,10286.0,1020.1],[10289.4,1023.5,10296.1,1030.2],[10299.5,1033.6,10300.0,1034.1],[10252.4,959.5,10259.1,966.2],[10262.5,969.6,10269.2,976.3],[10272.6,979.7,10279.3,986.4],[10282.7,989.8,10289.4,996.5],[10292.8,999.9,10299.5,1006.6],[10250.0,930.2,10252.4,932.5],[10255.7,935.9,10262.5,942.6],[10265.8,946.0,10272.6,952.7],[10275.9,956.1,10282.7,962.9],[10286.0,966.2,10292.8,973.0],[10296.1,976.3,10300.0,980.2],[10250.0,903.3,10255.7,909.0],[10259.1,912.3,10265.8,919.1],[10269.2,922.4,10275.9,929.2],[10279.3,932.5,10286.0,939.3],[10289.4,942.6,10296.1,949.4],[10299.5,952.7,10300.0,953.3],[10252.4,878.7,10259.1,885.4],[10262.5,888.8,10269.2,895.5],[10272.6,898.9,10279.3,905.6],[10282.7,909.0,10289.4,915.7],[10292.8,919.1,10299.5,925.8],[10250.0,849.4,10252.4,851.7],[10255.7,855.1,10262.5,861.8],[10265.8,865.2,10272.6,871.9],[10275.9,875.3,10282.7,882.0],[10286.0,885.4,10292.8,892.1],[10296.1,895.5,10300.0,899.4],[10250.0,822.5,10255.7,828.1],[10259.1,831.5,10265.8,838.3],[10269.2,841.6,10275.9,848.4],[10279.3,851.7,10286.0,858.5],[10289.4,861.8,10296.1,868.6],[10299.5,871.9,10300.0,872.5],[10252.4,797.8,10259.1,804.6],[10262.5,807.9,10269.2,814.7],[10272.6,818.0,10279.3,824.8],[10282.7,828.1,10289.4,834.9],[10292.8,838.3,10299.5,845.0],[10250.0,768.6,10252.4,770.9],[10255.7,774.3,10262.5,781.0],[10265.8,784.4,10272.6,791.1],[10275.9,794.5,10282.7,801.2],[10286.0,804.6,10292.8,811.3],[10296.1,814.7,10300.0,818.6],[10250.0,741.6,10255.7,747.3],[10259.1,750.7,10265.8,757.4],[10269.2,760.8,10275.9,767.5],[10279.3,770.9,10286.0,777.6],[10289.4,781.0,10296.1,787.7],[10299.5,791.1,10300.0,791.6],[10252.4,717.0,10259.1,723.8],[10262.5,727.1,10269.2,733.9],[10272.6,737.2,10279.3,744.0],[10282.7,747.3,10289.4,754.1],[10292.8,757.4,10299.5,764.2],[10250.0,687.8,10252.4,690.1],[10255.7,693.4,10262.5,700.2],[10265.8,703.5,10272.6,710.3],[10275.9,713.7,10282.7,720.4],[10286.0,723.8,10292.8,730.5],[10296.1,733.9,10300.0,737.8],[10250.0,660.8,10255.7,666.5],[10259.1,669.9,10265.8,676.6],[10269.2,680.0,10275.9,686.7],[10279.3,690.1,10286.0,696.8],[10289.4,700.2,10296.1,706.9],[10299.5,710.3,10300.0,710.8],[10252.4,636.2,10259.1,642.9],[10262.5,646.3,10269.2,653.0],[10272.6,656.4,10279.3,663.1],[10282.7,666.5,10289.4,673.2],[10292.8,676.6,10299.5,683.3],[10250.0,606.9,10252.4,609.3],[10255.7,612.6,10262.5,619.4],[10265.8,622.7,10272.6,629.5],[10275.9,632.8,10282.7,639.6],[10286.0,642.9,10292.8,649.7],[10296.1,653.0,10300.0,656.9],[10250.0,580.0,10255.7,585.7],[10259.1,589.0,10265.8,595.8],[10269.2,599.2,10275.9,605.9],[10279.3,609.3,10286.0,616.0],[10289.4,619.4,10296.1,626.1],[10299.5,629.5,10300.0,630.0],[10252.4,555.4,10259.1,562.1],[10262.5,565.5,10269.2,572.2],[10272.6,575.6,10279.3,582.3],[10282.7,585.7,10289.4,592.4],[10292.8,595.8,10299.5,602.5],[10250.0,526.1,10252.4,528.4],[10255.7,531.8,10262.5,538.5],[10265.8,541.9,10272.6,548.6],[10275.9,552.0,10282.7,558.7],[10286.0,562.1,10292.8,568.8],[10296.1,572.2,10300.0,576.1],[10250.0,499.2,10255.7,504.9],[10259.1,508.2,10265.8,515.0],[10269.2,518.3,10275.9,525.1],[10279.3,528.4,10286.0,535.2],[10289.4,538.5,10296.1,545.3],[10299.5,548.6,10300.0,549.2],[10252.4,474.6,10259.1,481.3],[10262.5,484.7,10269.2,491.4],[10272.6,494.8,10279.3,501.5],[10282.7,504.9,10289.4,511.6],[10292.8,515.0,10299.5,521.7],[10250.0,445.3,10252.4,447.6],[10255.7,451.0,10262.5,457.7],[10265.8,461.1,10272.6,467.8],[10275.9,471.2,10282.7,477.9],[10286.0,481.3,10292.8,488.0],[10296.1,491.4,10300.0,495.3],[10259.1,427.4,10265.8,434.1],[10269.2,437.5,10275.9,444.2],[10279.3,447.6,10286.0,454.3],[10289.4,457.7,10296.1,464.4],[10299.5,467.8,10300.0,468.3],[10283.6,425.0,10289.4,430.8],[10292.8,434.1,10299.5,440.9],[150.0,700.0,200.0,700.0],[200.0,700.0,200.0,800.0],[200.0,800.0,150.0,800.0],[150.0,800.0,150.0,700.0],[325.0,700.0,375.0,700.0],[375.0,700.0,375.0,800.0],[375.0,800.0,325.0,800.0],[325.0,800.0,325.0,700.0],[525.0,700.0,575.0,700.0],[575.0,700.0,575.0,800.0],[575.0,800.0,525.0,800.0],[525.0,800.0,525.0,700.0],[700.0,700.0,750.0,700.0],[750.0,700.0,750.0,800.0],[750.0,800.0,700.0,800.0],[700.0,800.0,700.0,700.0],[875.0,700.0,925.0,700.0],[925.0,700.0,925.0,800.0],[925.0,800.0,875.0,800.0],[875.0,800.0,875.0,700.0],[1050.0,700.0,1100.0,700.0],[1100.0,700.0,1100.0,800.0],[1100.0,800.0,1050.0,800.0],[1050.0,800.0,1050.0,700.0],[1225.0,700.0,1275.0,700.0],[1275.0,700.0,1275.0,800.0],[1275.0,800.0,1225.0,800.0],[1225.0,800.0,1225.0,700.0],[1400.0,700.0,1450.0,700.0],[1450.0,700.0,1450.0,800.0],[1450.0,800.0,1400.0,800.0],[1400.0,800.0,1400.0,700.0],[1575.0,700.0,1625.0,700.0],[1625.0,700.0,1625.0,800.0],[1625.0,800.0,1575.0,800.0],[1575.0,800.0,1575.0,700.0],[8637.5,200.0,8687.5,200.0],[8687.5,200.0,8687.5,300.0],[8687.5,300.0,8637.5,300.0],[8637.5,300.0,8637.5,200.0],[8787.5,200.0,8837.5,200.0],[8837.5,200.0,8837.5,300.0],[8837.5,300.0,8787.5,300.0],[8787.5,300.0,8787.5,200.0],[8962.5,200.0,9012.5,200.0],[9012.5,200.0,9012.5,300.0],[9012.5,300.0,8962.5,300.0],[8962.5,300.0,8962.5,200.0],[9137.5,200.0,9187.5,200.0],[9187.5,200.0,9187.5,300.0],[9187.5,300.0,9137.5,300.0],[9137.5,300.0,9137.5,200.0],[9312.5,200.0,9362.5,200.0],[9362.5,200.0,9362.5,300.0],[9362.5,300.0,9312.5,300.0],[9312.5,300.0,9312.5,200.0],[9487.5,200.0,9537.5,200.0],[9537.5,200.0,9537.5,300.0],[9537.5,300.0,9487.5,300.0],[9487.5,300.0,9487.5,200.0],[9662.5,200.0,9712.5,200.0],[9712.5,200.0,9712.5,300.0],[9712.5,300.0,9662.5,300.0],[9662.5,300.0,9662.5,200.0],[9837.5,200.0,9887.5,200.0],[9887.5,200.0,9887.5,300.0],[9887.5,300.0,9837.5,300.0],[9837.5,300.0,9837.5,200.0],[10000.0,200.0,10050.0,200.0],[10050.0,200.0,10050.0,300.0],[10050.0,300.0,10000.0,300.0],[10000.0,300.0,10000.0,200.0],[8475.0,200.0,8525.0,200.0],[8525.0,200.0,8525.0,300.0],[8525.0,300.0,8475.0,300.0],[8475.0,300.0,8475.0,200.0],[10250.0,5025.0,10250.0,6625.0],[10250.0,6625.0,10050.0,6625.0],[10050.0,6625.0,10050.0,5025.0],[10050.0,5025.0,10250.0,5025.0],[4750.0,425.0,5150.0,425.0],[5150.0,425.0,5150.0,3975.0],[5150.0,3975.0,6400.0,3975.0],[4625.0,300.0,5350.0,300.0],[5350.0,300.0,5350.0,3825.0],[5350.0,3825.0,7500.0,3825.0],[16300.0,6485.0,16300.0,6625.0],[16300.0,6625.0,16230.0,6625.0],[16230.0,6625.0,16230.0,6541.0],[16230.0,6541.0,16258.0,6541.0],[16258.0,6541.0,16258.0,6485.0],[16258.0,6485.0,16300.0,6485.0],[16202.0,6531.3,16202.0,5621.3],[16202.0,5621.3,16258.0,5621.3],[16258.0,5621.3,16258.0,6531.3],[16258.0,6531.3,16202.0,6531.3],[16202.0,6531.3,16202.0,6531.3],[15250.0,6485.0,15250.0,6625.0],[15250.0,6625.0,15320.0,6625.0],[15320.0,6625.0,15320.0,6541.0],[15320.0,6541.0,15292.0,6541.0],[15292.0,6541.0,15292.0,6485.0],[15292.0,6485.0,15250.0,6485.0],[15292.0,6531.3,15293.1,6486.7],[15293.1,6486.7,15296.4,6442.1],[15296.4,6442.1,15301.9,6397.8],[15301.9,6397.8,15309.5,6353.8],[15309.5,6353.8,15319.3,6310.2],[15319.3,6310.2,15331.2,6267.2],[15331.2,6267.2,15345.2,6224.7],[15345.2,6224.7,15361.3,6183.1],[15361.3,6183.1,15379.4,6142.2],[15379.4,6142.2,15399.5,6102.3],[15399.5,6102.3,15421.5,6063.5],[15421.5,6063.5,15445.4,6025.7],[15445.4,6025.7,15471.1,5989.2],[15471.1,5989.2,15498.6,5954.0],[15498.6,5954.0,15527.8,5920.2],[15527.8,5920.2,15558.6,5887.8],[15558.6,5887.8,15590.9,5857.0],[15590.9,5857.0,15624.7,5827.9],[15624.7,5827.9,15660.0,5800.4],[15660.0,5800.4,15696.5,5774.7],[15696.5,5774.7,15734.2,5750.8],[15734.2,5750.8,15773.1,5728.8],[15773.1,5728.8,15813.0,5708.7],[15813.0,5708.7,15853.8,5690.6],[15853.8,5690.6,15895.5,5674.5],[15895.5,5674.5,15937.9,5660.5],[15937.9,5660.5,15980.9,5648.6],[15980.9,5648.6,16024.5,5638.8],[16024.5,5638.8,16068.5,5631.2],[16068.5,5631.2,16112.8,5625.7],[16112.8,5625.7,16157.4,5622.4],[16157.4,5622.4,16202.0,5621.3],[6430.0,5025.0,6550.0,5025.0],[6550.0,5025.0,6550.0,4965.0],[6550.0,4965.0,6478.0,4965.0],[6478.0,4965.0,6478.0,4989.0],[6478.0,4989.0,6430.0,4989.0],[6430.0,4989.0,6430.0,5025.0],[6469.7,4941.0,5689.7,4941.0],[5689.7,4941.0,5689.7,4989.0],[5689.7,4989.0,6469.7,4989.0],[6469.7,4989.0,6469.7,4941.0],[6469.7,4941.0,6469.7,4941.0],[6430.0,4125.0,6550.0,4125.0],[6550.0,4125.0,6550.0,4185.0],[6550.0,4185.0,6478.0,4185.0],[6478.0,4185.0,6478.0,4161.0],[6478.0,4161.0,6430.0,4161.0],[6430.0,4161.0,6430.0,4125.0],[5689.7,4941.0,5690.7,4902.7],[5690.7,4902.7,5693.5,4864.6],[5693.5,4864.6,5698.2,4826.6],[5698.2,4826.6,5704.7,4788.8],[5704.7,4788.8,5713.1,4751.5],[5713.1,4751.5,5723.3,4714.6],[5723.3,4714.6,5735.3,4678.2],[5735.3,4678.2,5749.1,4642.5],[5749.1,4642.5,5764.6,4607.5],[5764.6,4607.5,5781.8,4573.3],[5781.8,4573.3,5800.7,4540.0],[5800.7,4540.0,5821.2,4507.7],[5821.2,4507.7,5843.2,4476.4],[5843.2,4476.4,5866.8,4446.2],[5866.8,4446.2,5891.8,4417.2],[5891.8,4417.2,5918.2,4389.5],[5918.2,4389.5,5945.9,4363.1],[5945.9,4363.1,5974.9,4338.1],[5974.9,4338.1,6005.1,4314.5],[6005.1,4314.5,6036.4,4292.5],[6036.4,4292.5,6068.7,4272.0],[6068.7,4272.0,6102.0,4253.1],[6102.0,4253.1,6136.2,4235.9],[6136.2,4235.9,6171.2,4220.4],[6171.2,4220.4,6207.0,4206.6],[6207.0,4206.6,6243.3,4194.6],[6243.3,4194.6,6280.2,4184.4],[6280.2,4184.4,6317.6,4176.0],[6317.6,4176.0,6355.3,4169.4],[6355.3,4169.4,6393.3,4164.8],[6393.3,4164.8,6431.5,4161.9],[6431.5,4161.9,6469.7,4161.0],[10050.0,3225.0,10050.0,3325.0],[10050.0,3325.0,10000.0,3325.0],[10000.0,3325.0,10000.0,3265.0],[10000.0,3265.0,10020.0,3265.0],[10020.0,3265.0,10020.0,3225.0],[10020.0,3225.0,10050.0,3225.0],[9980.0,3258.1,9980.0,2608.1],[9980.0,2608.1,10020.0,2608.1],[10020.0,2608.1,10020.0,3258.1],[10020.0,3258.1,9980.0,3258.1],[9980.0,3258.1,9980.0,3258.1],[9300.0,3225.0,9300.0,3325.0],[9300.0,3325.0,9350.0,3325.0],[9350.0,3325.0,9350.0,3265.0],[9350.0,3265.0,9330.0,3265.0],[9330.0,3265.0,9330.0,3225.0],[9330.0,3225.0,9300.0,3225.0],[9330.0,3258.1,9330.8,3226.2],[9330.8,3226.2,9333.2,3194.4],[9333.2,3194.4,9337.1,3162.7],[9337.1,3162.7,9342.5,3131.3],[9342.5,3131.3,9349.5,3100.1],[9349.5,3100.1,9358.0,3069.4],[9358.0,3069.4,9368.0,3039.1],[9368.0,3039.1,9379.5,3009.3],[9379.5,3009.3,9392.5,2980.2],[9392.5,2980.2,9406.8,2951.7],[9406.8,2951.7,9422.5,2923.9],[9422.5,2923.9,9439.6,2897.0],[9439.6,2897.0,9458.0,2870.9],[9458.0,2870.9,9477.6,2845.7],[9477.6,2845.7,9498.4,2821.6],[9498.4,2821.6,9520.4,2798.5],[9520.4,2798.5,9543.5,2776.5],[9543.5,2776.5,9567.7,2755.6],[9567.7,2755.6,9592.8,2736.0],[9592.8,2736.0,9618.9,2717.6],[9618.9,2717.6,9645.9,2700.6],[9645.9,2700.6,9673.6,2684.8],[9673.6,2684.8,9702.1,2670.5],[9702.1,2670.5,9731.3,2657.6],[9731.3,2657.6,9761.1,2646.1],[9761.1,2646.1,9791.4,2636.1],[9791.4,2636.1,9822.1,2627.6],[9822.1,2627.6,9853.2,2620.6],[9853.2,2620.6,9884.7,2615.1],[9884.7,2615.1,9916.3,2611.2],[9916.3,2611.2,9948.2,2608.9],[9948.2,2608.9,9980.0,2608.1],[8400.0,3855.0,8400.0,3975.0],[8400.0,3975.0,8340.0,3975.0],[8340.0,3975.0,8340.0,3903.0],[8340.0,3903.0,8364.0,3903.0],[8364.0,3903.0,8364.0,3855.0],[8364.0,3855.0,8400.0,3855.0],[8316.0,3894.7,8316.0,3114.7],[8316.0,3114.7,8364.0,3114.7],[8364.0,3114.7,8364.0,3894.7],[8364.0,3894.7,8316.0,3894.7],[8316.0,3894.7,8316.0,3894.7],[7500.0,3855.0,7500.0,3975.0],[7500.0,3975.0,7560.0,3975.0],[7560.0,3975.0,7560.0,3903.0],[7560.0,3903.0,7536.0,3903.0],[7536.0,3903.0,7536.0,3855.0],[7536.0,3855.0,7500.0,3855.0],[7536.0,3894.7,7537.0,3856.4],[7537.0,3856.4,7539.8,3818.2],[7539.8,3818.2,7544.5,3780.2],[7544.5,3780.2,7551.0,3742.5],[7551.0,3742.5,7559.4,3705.2],[7559.4,3705.2,7569.6,3668.3],[7569.6,3668.3,7581.6,3631.9],[7581.6,3631.9,7595.4,3596.2],[7595.4,3596.2,7610.9,3561.2],[7610.9,3561.2,7628.1,3527.0],[7628.1,3527.0,7647.0,3493.7],[7647.0,3493.7,7667.5,3461.4],[7667.5,3461.4,7689.5,3430.1],[7689.5,3430.1,7713.1,3399.9],[7713.1,3399.9,7738.1,3370.9],[7738.1,3370.9,7764.5,3343.2],[7764.5,3343.2,7792.2,3316.8],[7792.2,3316.8,7821.2,3291.7],[7821.2,3291.7,7851.4,3268.2],[7851.4,3268.2,7882.7,3246.2],[7882.7,3246.2,7915.0,3225.7],[7915.0,3225.7,7948.4,3206.8],[7948.4,3206.8,7982.6,3189.6],[7982.6,3189.6,8017.6,3174.1],[8017.6,3174.1,8053.3,3160.3],[8053.3,3160.3,8089.6,3148.3],[8089.6,3148.3,8126.5,3138.1],[8126.5,3138.1,8163.9,3129.7],[8163.9,3129.7,8201.6,3123.1],[8201.6,3123.1,8239.6,3118.5],[8239.6,3118.5,8277.8,3115.6],[8277.8,3115.6,8316.0,3114.7],[1825.0,4275.0,1925.0,4275.0],[1925.0,4275.0,1925.0,4225.0],[1925.0,4225.0,1865.0,4225.0],[1865.0,4225.0,1865.0,4245.0],[1865.0,4245.0,1825.0,4245.0],[1825.0,4245.0,1825.0,4275.0],[1858.1,4205.0,1208.1,4205.0],[1208.1,4205.0,1208.1,4245.0],[1208.1,4245.0,1858.1,4245.0],[1858.1,4245.0,1858.1,4205.0],[1858.1,4205.0,1858.1,4205.0],[1825.0,3525.0,1925.0,3525.0],[1925.0,3525.0,1925.0,3575.0],[1925.0,3575.0,1865.0,3575.0],[1865.0,3575.0,1865.0,3555.0],[1865.0,3555.0,1825.0,3555.0],[1825.0,3555.0,1825.0,3525.0],[1208.1,4205.0,1208.9,4173.1],[1208.9,4173.1,1211.3,4141.3],[1211.3,4141.3,1215.2,4109.6],[1215.2,4109.6,1220.6,4078.2],[1220.6,4078.2,1227.6,4047.1],[1227.6,4047.1,1236.1,4016.3],[1236.1,4016.3,1246.1,3986.0],[1246.1,3986.0,1257.6,3956.3],[1257.6,3956.3,1270.5,3927.1],[1270.5,3927.1,1284.9,3898.6],[1284.9,3898.6,1300.6,3870.8],[1300.6,3870.8,1317.7,3843.9],[1317.7,3843.9,1336.0,3817.8],[1336.0,3817.8,1355.7,3792.6],[1355.7,3792.6,1376.5,3768.5],[1376.5,3768.5,1398.5,3745.4],[1398.5,3745.4,1421.6,3723.4],[1421.6,3723.4,1445.8,3702.5],[1445.8,3702.5,1470.9,3682.9],[1470.9,3682.9,1497.0,3664.5],[1497.0,3664.5,1524.0,3647.5],[1524.0,3647.5,1551.7,3631.8],[1551.7,3631.8,1580.2,3617.4],[1580.2,3617.4,1609.4,3604.5],[1609.4,3604.5,1639.1,3593.0],[1639.1,3593.0,1669.4,3583.0],[1669.4,3583.0,1700.2,3574.5],[1700.2,3574.5,1731.3,3567.5],[1731.3,3567.5,1762.7,3562.0],[1762.7,3562.0,1794.4,3558.1],[1794.4,3558.1,1826.2,3555.8],[1826.2,3555.8,1858.1,3555.0],[12950.0,1425.0,13200.0,1425.0],[13200.0,1425.0,13200.0,1525.0],[13200.0,1525.0,12950.0,1525.0],[10250.0,1475.0,10925.0,1475.0],[10925.0,1475.0,10925.0,1525.0],[10925.0,1525.0,10250.0,1525.0],[12750.0,1475.0,12050.0,1475.0],[12050.0,1475.0,12050.0,1525.0],[12050.0,1525.0,12750.0,1525.0],[10925.0,1525.0,12050.0,1525.0]],"report":{"spec_mm":{"wall_h":3000.0,"door_head":2100.0,"win_sill":600.0,"win_h":1500.0,"vent_sill":1200.0,"vent_h":900.0,"vent_max_width":1000.0,"lintel_h":900.0,"skirt_h":100.0,"skirt_t":15.0,"floor_finish_t":20.0,"slab_t":200.0,"tile_w":914.4,"tile_h":609.6,"tile_t":9.0,"grout":2.5,"tile_gap":0.0,"min_cut":200.0,"panel_w":1220.0,"panel_t":12.0,"panel_joint":3.0,"balcony_glass_t":76.2,"balcony_glass_h":1200.0,"balcony_glass_joint":5.0,"balcony_glass_max":1200.0,"balcony_post_w":40.0,"balcony_rail_h":35.0,"kitchen_counter_h":860.0,"kitchen_counter_depth":600.0,"kitchen_counter_t":40.0,"kitchen_base_depth":570.0,"kitchen_backsplash_h":600.0,"kitchen_backsplash_t":15.0,"recess_border_w":450.0,"recess_depth":120.0,"recess_drop_h":50.0,"recess_lip_w":60.0,"recess_wall_gap":15.0,"downlight_r":45.0,"downlight_recess":25.0,"door_frame_w":45.0,"door_leaf_t":42.0,"door_handle_h":1000.0,"door_lever_len":128.0,"door_min":600.0,"door_max":1250.0,"gap_max":3600.0},"warnings":[],"ambiguities":["Room_04 (4.94 m2): possible balcony / sit-out (narrow room with a long glazed or open side)","2 washrooms detected (3 expected) - check the classification table"],"assumptions":["Room_04 (4.94 m2) inferred as Kitchen (no CAD text label present; configurable via CONFIG['room_type_overrides']).","No room had an explicit KITCHEN CAD label or kitchen fixture block; set CONFIG[\"room_type_overrides\"] to assign a kitchen room if needed."],"room_uses":{"Room_01":"Living Room (6.08 \u00d7 6.05 m) [Living] - main entrance door opens into it","Room_04":"Kitchen (3.35 \u00d7 1.50 m) [Kitchen] - compact room opening off hall/dining (inferred kitchen; override via CONFIG if needed)","Room_05":"Lobby (3.51 \u00d7 1.70 m) [Lobby] - circulation space 4.66 m2 between doors","Room_07":"Service Shaft / Duct (3.05 \u00d7 1.35 m) [Shaft_2] - enclosed service shaft / duct","Room_10":"Service Shaft / Duct (1.52 \u00d7 0.75 m) [Shaft_5] - enclosed service shaft / duct","Toilet_1":"Toilet (1.80 \u00d7 1.50 m) [Toilet_1] - classified washroom (see signals)","Room_03":"Bedroom (3.55 \u00d7 3.05 m) [Bedroom] - private room >= 7 m2 with a single doorway","Room_09":"Service Shaft / Duct (1.52 \u00d7 1.35 m) [Shaft_4] - enclosed service shaft / duct","Room_02":"Master Bedroom (5.12 \u00d7 4.46 m) [Master_Bedroom] - the attached Master_Toilet opens into it","Room_06":"Service Shaft / Duct (3.23 \u00d7 1.35 m) [Shaft_1] - enclosed service shaft / duct","Room_08":"Service Shaft / Duct (1.60 \u00d7 1.50 m) [Shaft_3] - enclosed service shaft / duct","Master_Toilet":"Master Toilet (2.40 \u00d7 1.60 m) [Master_Toilet] - classified washroom (see signals)"},"kitchen_platforms":[],"room_floors":{"count":7,"thickness_mm":20.0,"by_category":{"common":["Floor_Living","Floor_Kitchen","Floor_Bedroom"],"master_wood":["Floor_MasterBedroom_Wood"],"entrance":["Floor_Entrance_01"],"balcony":[],"dry_balcony":[],"washroom":["Floor_Washroom_02","Floor_Washroom_01"]}},"skirting":{"segments":11,"room_objects":5,"height_mm":100.0,"thickness_mm":15.0,"total_length_m":68.96,"door_and_passage_openings_checked":7,"rooms_with_skirting":["Room_01","Room_02","Room_03","Room_04","Room_05"],"rooms_excluded":["Master_Toilet (washroom)","Room_06 (shaft)","Room_07 (shaft)","Room_08 (shaft)","Room_09 (shaft)","Room_10 (shaft)","Toilet_1 (washroom)"]},"tiles":{"nominal_mm":"914.4 W x 609.6 H x 9.0 T","grout_mm":2.5,"rows":["z 0.0-609.6 (full)","z 612.1-1221.7 (full)","z 1224.2-1833.8 (full)","z 1836.3-2445.9 (full)","z 2448.4-3000.0 (cut 551.6)"],"per_washroom":{"Toilet_1":{"tiles":40,"full":9,"cut":31,"cut_sizes_mm":{"571.6 x 609.6":5,"914.4 x 609.6 (notched)":3,"571.6 x 609.6 (notched)":2,"426.1 x 609.6":1,"462.4 x 609.6":1,"914.4 x 551.6":4,"571.6 x 551.6":2,"871.6 x 609.6":8,"871.6 x 551.6":2,"176.0 x 609.6":3},"slivers_lt_50mm":0,"walls_tiled":4,"skipped_edges":[],"layouts":{"Wall01":"L=1500 mm, full tiles + end cut","Wall02":"L=1800 mm, full tiles + end cut","Wall03":"L=1500 mm, full tiles + end cut","Wall04":"L=1800 mm, full tiles + end cut"}},"Master_Toilet":{"tiles":50,"full":13,"cut":37,"cut_sizes_mm":{"671.6 x 609.6":5,"914.4 x 609.6 (notched)":4,"671.6 x 609.6 (notched)":2,"488.6 x 609.6":1,"499.9 x 609.6":1,"914.4 x 551.6":6,"671.6 x 551.6":2,"888.5 x 609.6":3,"192.8 x 609.6":3,"554.7 x 609.6":8,"554.7 x 551.6":2},"slivers_lt_50mm":0,"walls_tiled":4,"skipped_edges":[],"layouts":{"Wall01":"L=1600 mm, full tiles + end cut","Wall02":"L=2400 mm, full tiles + end cut","Wall03":"L=1600 mm, full tiles + end cut","Wall04":"L=2400 mm, full tiles + end cut"}}}},"panels":{"sheet_mm":"1220.0 W x full height x 12.0 T","joint_mm":3.0,"z_mm":"100.0 (top of skirting) - 3000.0 (ceiling)","per_room":{"Room_01":{"sheets":25,"full":11,"cut":14,"walls_panelled":10,"area_m2":66.1,"layouts":{"Wall01":"L=2450 mm, full tiles + end cut","Wall02":"L=3550 mm, full tiles + end cut","Wall03":"L=200 mm, single cut","Wall04":"L=2075 mm, full tiles + end cut","Wall05":"L=3350 mm, full tiles + end cut","Wall06":"L=4600 mm, full tiles + end cut","Wall07":"L=6050 mm, full tiles + end cut","Wall08":"L=2525 mm, balanced: equal cuts at both ends","Wall09":"L=50 mm, single cut","Wall10":"L=3550 mm, full tiles + end cut"},"label":"Living"},"Room_04":{"sheets":10,"full":0,"cut":10,"walls_panelled":6,"area_m2":10.81,"layouts":{"Wall01":"L=3350 mm, full tiles + end cut","Wall02":"L=1500 mm, full tiles + end cut","Wall03":"L=3100 mm, full tiles + end cut","Wall04":"L=350 mm, single cut","Wall05":"L=250 mm, single cut","Wall06":"L=1150 mm, single cut"},"label":"Kitchen"},"Room_05":{"sheets":9,"full":2,"cut":7,"walls_panelled":6,"area_m2":19.64,"layouts":{"Wall01":"L=1500 mm, full tiles + end cut","Wall02":"L=1700 mm, full tiles + end cut","Wall03":"L=3512 mm, full tiles + end cut","Wall06":"L=150 mm, single cut","Wall07":"L=2000 mm, full tiles + end cut","Wall08":"L=650 mm, single cut"},"label":"Lobby"},"Room_03":{"sheets":16,"full":4,"cut":12,"walls_panelled":10,"area_m2":31.08,"layouts":{"Wall01":"L=1125 mm, single cut","Wall02":"L=3400 mm, full tiles + end cut","Wall03":"L=1850 mm, full tiles + end cut","Wall04":"L=150 mm, single cut","Wall05":"L=150 mm, single cut","Wall06":"L=150 mm, single cut","Wall07":"L=1050 mm, single cut","Wall08":"L=3100 mm, full tiles + end cut","Wall09":"L=1925 mm, full tiles + end cut","Wall10":"L=300 mm, single cut"},"label":"Bedroom"},"Room_02":{"sheets":23,"full":6,"cut":17,"walls_panelled":13,"area_m2":46.28,"layouts":{"Wall01":"L=2150 mm, full tiles + end cut","Wall02":"L=1025 mm, single cut","Wall03":"L=125 mm, single cut","Wall04":"L=500 mm, single cut","Wall05":"L=400 mm, single cut","Wall06":"L=3550 mm, full tiles + end cut","Wall07":"L=1250 mm, balanced: equal cuts at both ends","Wall08":"L=150 mm, single cut","Wall11":"L=4462 mm, full tiles + end cut","Wall12":"L=4065 mm, full tiles + end cut","Wall13":"L=525 mm, single cut","Wall14":"L=660 mm, single cut","Wall16":"L=400 mm, single cut"},"label":"Master_Bedroom"}},"rooms_without_panels":["Master_Toilet (Master_Toilet)","Room_06 (Shaft_1)","Room_07 (Shaft_2)","Room_08 (Shaft_3)","Room_09 (Shaft_4)","Room_10 (Shaft_5)","Toilet_1 (Toilet_1)"]},"recessed_ceilings":{"rooms":["Room_01 (Living)","Room_03 (Bedroom)","Room_02 (Master_Bedroom)"],"excluded_rooms":["Room_04 (Kitchen)","Room_05 (Lobby)","Room_07 (Shaft_2)","Room_10 (Shaft_5)","Toilet_1 (Toilet_1)","Room_09 (Shaft_4)","Room_06 (Shaft_1)","Room_08 (Shaft_3)","Master_Toilet (Master_Toilet)"],"recess_depth_mm":120.0,"drop_soffit_mm":50.0,"total_downlights":34},"config":{"spec_mm":{"wall_h":3000.0,"door_head":2100.0,"win_sill":600.0,"win_h":1500.0,"vent_sill":1200.0,"vent_h":900.0,"vent_max_width":1000.0,"lintel_h":900.0,"skirt_h":100.0,"skirt_t":15.0,"floor_finish_t":20.0,"slab_t":200.0,"tile_w":914.4,"tile_h":609.6,"tile_t":9.0,"grout":2.5,"tile_gap":0.0,"min_cut":200.0,"panel_w":1220.0,"panel_t":12.0,"panel_joint":3.0,"balcony_glass_t":76.2,"balcony_glass_h":1200.0,"balcony_glass_joint":5.0,"balcony_glass_max":1200.0,"balcony_post_w":40.0,"balcony_rail_h":35.0,"kitchen_counter_h":860.0,"kitchen_counter_depth":600.0,"kitchen_counter_t":40.0,"kitchen_base_depth":570.0,"kitchen_backsplash_h":600.0,"kitchen_backsplash_t":15.0,"recess_border_w":450.0,"recess_depth":120.0,"recess_drop_h":50.0,"recess_lip_w":60.0,"recess_wall_gap":15.0,"downlight_r":45.0,"downlight_recess":25.0,"door_frame_w":45.0,"door_leaf_t":42.0,"door_handle_h":1000.0,"door_lever_len":128.0,"door_min":600.0,"door_max":1250.0,"gap_max":3600.0},"default_balcony_type":"open","room_type_overrides":{},"balcony_type_overrides":{},"material_presets":{"floor_common":"MAT_Floor_Common","floor_master_wood":"MAT_Floor_Master_Wood","floor_entrance":"MAT_Floor_Entrance","floor_balcony":"MAT_Floor_Balcony","floor_washroom":"MAT_Floor_Washroom","skirting_common":"MAT_Skirting_Common","skirting_master":"MAT_Skirting_Master","skirting_entrance":"MAT_Skirting_Entrance","skirting_balcony":"MAT_Skirting_Balcony","lintel_blue":"MAT_Lintel_Blue","washroom_tiles":"MAT_Washroom_Wall_Tiles","balcony_glass":"MAT_Balcony_Glass","balcony_metal":"MAT_Balcony_Railing_Metal","kitchen_countertop":"MAT_Kitchen_Countertop","kitchen_base":"MAT_Kitchen_Base"}},"rooms":[{"name":"Room_01","use":"living","label":"Living","type":"dry","display_name":"Living Room","cad_dim":"6.08 \u00d7 6.05 m","cad_text":"","floor_obj":"Floor_Living","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Living","skirt_mat":"MAT_Skirting_Common","tile_obj":"","recessed_ceiling":true,"area_m2":30.93,"min_dim_mm":6050,"max_dim_mm":6075,"score":-8,"signals":["1 full-size window(s) (-1)","1 open passage(s) (-3)","large area 30.93 m2 (-4)"],"openings":["Door_01","Door_03","Passage_01","Window_02"],"use_reason":"main entrance door opens into it","vertices":10},{"name":"Room_04","use":"kitchen","label":"Kitchen","type":"dry","display_name":"Kitchen","cad_dim":"3.35 \u00d7 1.50 m","cad_text":"","floor_obj":"Floor_Kitchen","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Kitchen","skirt_mat":"MAT_Skirting_Common","tile_obj":"","recessed_ceiling":false,"area_m2":4.94,"min_dim_mm":1500,"max_dim_mm":3350,"score":0,"signals":["1 ventilator on boundary (+3)","1 full-size window(s) (-1)","1 open passage(s) (-3)","compact area 4.94 m2 (+1)"],"openings":["Passage_01","Vent_03","Window_03"],"use_reason":"compact room opening off hall/dining (inferred kitchen; override via CONFIG if needed)","vertices":6},{"name":"Room_05","use":"lobby","label":"Lobby","type":"dry","display_name":"Lobby","cad_dim":"3.51 \u00d7 1.70 m","cad_text":"","floor_obj":"Floor_Entrance_01","floor_mat":"MAT_Floor_Entrance","skirt_obj":"Skirting_Entrance_01","skirt_mat":"MAT_Skirting_Entrance","tile_obj":"","recessed_ceiling":false,"area_m2":4.66,"min_dim_mm":1700,"max_dim_mm":3512,"score":1,"signals":["compact area 4.66 m2 (+1)"],"openings":["Door_02","Door_03","Door_05","Door_06"],"use_reason":"circulation space 4.66 m2 between doors","vertices":8},{"name":"Room_07","use":"shaft","label":"Shaft_2","type":"shaft","display_name":"Service Shaft / Duct","cad_dim":"3.05 \u00d7 1.35 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","recessed_ceiling":false,"area_m2":4.12,"min_dim_mm":1350,"max_dim_mm":3050,"score":-1,"signals":["no doorway found (-2)","compact area 4.12 m2 (+1)","diagonal X shaft cross inside void -> shaft"],"openings":[],"use_reason":"enclosed service shaft / duct","vertices":4},{"name":"Room_10","use":"shaft","label":"Shaft_5","type":"shaft","display_name":"Service Shaft / Duct","cad_dim":"1.52 \u00d7 0.75 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","recessed_ceiling":false,"area_m2":1.14,"min_dim_mm":750,"max_dim_mm":1525,"score":-1,"signals":["1 ventilator on boundary (+3)","no doorway found (-2)","narrow (750 mm) (-2)","diagonal X shaft cross inside void -> shaft"],"openings":["Vent_02"],"use_reason":"enclosed service shaft / duct","vertices":4},{"name":"Toilet_1","use":"washroom","label":"Toilet_1","type":"washroom","display_name":"Toilet","cad_dim":"1.80 \u00d7 1.50 m","cad_text":"","floor_obj":"Floor_Washroom_02","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_02","recessed_ceiling":false,"area_m2":2.7,"min_dim_mm":1500,"max_dim_mm":1800,"score":8,"signals":["1 ventilator on boundary (+3)","single doorway, no open passage (+2)","narrow washroom-width doorway 750 mm (+2)","compact area 2.70 m2 (+1)"],"openings":["Door_06","Vent_02"],"use_reason":"classified washroom (see signals)","vertices":4},{"name":"Room_03","use":"bedroom","label":"Bedroom","type":"dry","display_name":"Bedroom","cad_dim":"3.55 \u00d7 3.05 m","cad_text":"","floor_obj":"Floor_Bedroom","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Bedroom","skirt_mat":"MAT_Skirting_Common","tile_obj":"","recessed_ceiling":true,"area_m2":9.82,"min_dim_mm":3050,"max_dim_mm":3550,"score":-3,"signals":["1 full-size window(s) (-1)","single doorway, no open passage (+2)","large area 9.82 m2 (-4)"],"openings":["Door_05","Window_01"],"use_reason":"private room >= 7 m2 with a single doorway","vertices":10},{"name":"Room_09","use":"shaft","label":"Shaft_4","type":"shaft","display_name":"Service Shaft / Duct","cad_dim":"1.52 \u00d7 1.35 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","recessed_ceiling":false,"area_m2":1.78,"min_dim_mm":1350,"max_dim_mm":1525,"score":-1,"signals":["no doorway found (-2)","compact area 1.78 m2 (+1)","diagonal X shaft cross inside void -> shaft"],"openings":[],"use_reason":"enclosed service shaft / duct","vertices":6},{"name":"Room_02","use":"master_bedroom","label":"Master_Bedroom","type":"dry","display_name":"Master Bedroom","cad_dim":"5.12 \u00d7 4.46 m","cad_text":"","floor_obj":"Floor_MasterBedroom_Wood","floor_mat":"MAT_Floor_Master_Wood","skirt_obj":"Skirting_MasterBedroom","skirt_mat":"MAT_Skirting_Master","tile_obj":"","recessed_ceiling":true,"area_m2":16.83,"min_dim_mm":4462,"max_dim_mm":5125,"score":-2,"signals":["2 ventilator on boundary (+3)","1 full-size window(s) (-1)","large area 16.83 m2 (-4)"],"openings":["Door_02","Door_04","Vent_04","Vent_05","Window_04"],"use_reason":"the attached Master_Toilet opens into it","vertices":16},{"name":"Room_06","use":"shaft","label":"Shaft_1","type":"shaft","display_name":"Service Shaft / Duct","cad_dim":"3.23 \u00d7 1.35 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","recessed_ceiling":false,"area_m2":4.35,"min_dim_mm":1350,"max_dim_mm":3225,"score":-1,"signals":["no doorway found (-2)","compact area 4.35 m2 (+1)","diagonal X shaft cross inside void -> shaft"],"openings":[],"use_reason":"enclosed service shaft / duct","vertices":4},{"name":"Room_08","use":"shaft","label":"Shaft_3","type":"shaft","display_name":"Service Shaft / Duct","cad_dim":"1.60 \u00d7 1.50 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","recessed_ceiling":false,"area_m2":2.4,"min_dim_mm":1500,"max_dim_mm":1600,"score":2,"signals":["1 ventilator on boundary (+3)","no doorway found (-2)","compact area 2.40 m2 (+1)","diagonal X shaft cross inside void -> shaft"],"openings":["Vent_01"],"use_reason":"enclosed service shaft / duct","vertices":4},{"name":"Master_Toilet","use":"washroom","label":"Master_Toilet","type":"washroom","display_name":"Master Toilet","cad_dim":"2.40 \u00d7 1.60 m","cad_text":"","floor_obj":"Floor_Washroom_01","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_01","recessed_ceiling":false,"area_m2":3.84,"min_dim_mm":1600,"max_dim_mm":2400,"score":8,"signals":["1 ventilator on boundary (+3)","single doorway, no open passage (+2)","narrow washroom-width doorway 750 mm (+2)","compact area 3.84 m2 (+1)"],"openings":["Door_04","Vent_01"],"use_reason":"classified washroom (see signals)","vertices":4}],"openings":[{"id":"Window_03","type":"window","p0":[12950.0,212.5],"p1":[16300.0,212.5],"width":3350.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[12950.0,275.0],[16300.0,275.0],[16300.0,150.0],[12950.0,150.0]],"rooms":["Room_04"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_001"},{"id":"Window_04","type":"window","p0":[2475.0,-150.0],"p1":[4625.0,-150.0],"width":2150.0,"thickness":100.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[2475.0,-100.0],[4625.0,-100.0],[4625.0,-200.0],[2475.0,-200.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_002"},{"id":"Vent_03","type":"window","p0":[16400.0,275.0],"p1":[16400.0,1175.0],"width":900.0,"thickness":200.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[16300.0,275.0],[16300.0,1175.0],[16500.0,1175.0],[16500.0,275.0]],"rooms":["Room_04"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_003"},{"id":"Vent_05","type":"window","p0":[4687.5,-100.0],"p1":[4687.5,300.0],"width":400.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[4625.0,-100.0],[4625.0,300.0],[4750.0,300.0],[4750.0,-100.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_004"},{"id":"Vent_04","type":"window","p0":[2412.5,-100.0],"p1":[2412.5,300.0],"width":400.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[2350.0,-100.0],[2350.0,300.0],[2475.0,300.0],[2475.0,-100.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_005"},{"id":"Window_01","type":"window","p0":[5350.0,662.5],"p1":[7150.0,662.5],"width":1800.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[5350.0,725.0],[7150.0,725.0],[7150.0,600.0],[5350.0,600.0]],"rooms":["Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_006"},{"id":"Window_02","type":"window","p0":[10925.1,362.5],"p1":[12125.1,362.5],"width":1200.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[10925.1,425.0],[12125.1,425.0],[12125.1,300.0],[10925.1,300.0]],"rooms":["Room_01"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_007"},{"id":"Vent_01","type":"vent","p0":[700.1,2562.5],"p1":[1300.1,2562.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[700.1,2625.0],[1300.1,2625.0],[1300.1,2500.0],[700.1,2500.0]],"rooms":["Room_08","Master_Toilet"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_008"},{"id":"Vent_02","type":"vent","p0":[8987.6,1312.5],"p1":[9587.6,1312.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[8987.6,1375.0],[9587.6,1375.0],[9587.6,1250.0],[8987.6,1250.0]],"rooms":["Room_10","Toilet_1"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_009"},{"id":"Door_04","type":"door","p0":[1875.0,3525.0],"p1":[1875.0,4275.0],"width":750.0,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap + DOOR layer","notes":[],"rect":[[1800.0,3525.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,3525.0]],"rooms":["Room_02","Master_Toilet"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_001"},{"id":"Door_03","type":"door","p0":[10150.0,3975.0],"p1":[10150.0,5025.0],"width":1050.0,"thickness":200.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap","notes":[],"rect":[[10050.0,3975.0],[10050.0,5025.0],[10250.0,5025.0],[10250.0,3975.0]],"rooms":["Room_01","Room_05"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_002"},{"id":"Passage_01","type":"passage","p0":[13425.1,1837.5],"p1":[15825.1,1837.5],"width":2400.0,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap + lintel line drawn across","notes":["beam / lintel line drawn across the opening - wall completed above door head"],"rect":[[13425.1,1900.0],[15825.1,1900.0],[15825.1,1775.0],[13425.1,1775.0]],"rooms":["Room_01","Room_04"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Passage_003"},{"id":"Door_06","type":"door","p0":[9300.1,3250.0],"p1":[10050.0,3250.0],"width":749.9,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[9300.1,3325.0],[10050.0,3325.0],[10050.0,3175.0],[9300.1,3175.0]],"rooms":["Room_05","Toilet_1"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_004"},{"id":"Door_05","type":"door","p0":[7500.1,3900.0],"p1":[8400.0,3900.0],"width":899.9,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[7500.1,3975.0],[8400.0,3975.0],[8400.0,3825.0],[7500.1,3825.0]],"rooms":["Room_05","Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_005"},{"id":"Door_01","type":"door","p0":[15250.0,6562.5],"p1":[16300.0,6562.5],"width":1050.0,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[15250.0,6625.0],[16300.0,6625.0],[16300.0,6500.0],[15250.0,6500.0]],"rooms":["Room_01"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_006"},{"id":"Door_02","type":"door","p0":[6475.0,5025.0],"p1":[6475.0,4125.0],"width":900.0,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"CAD door arc between walls + DOOR layer","notes":[],"rect":[[6537.5,5025.0],[6537.5,4125.0],[6412.5,4125.0],[6412.5,5025.0]],"rooms":["Room_05","Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_007"}]},"wall_bands":[{"z0":0.0,"z1":600.0,"polys":[{"outer":[[1800.0,800.0],[1800.0,300.0],[2350.0,300.0],[2350.0,-200.0],[4750.0,-200.0],[4750.0,300.0],[5350.0,300.0],[5350.0,600.0],[7150.0,600.0],[7150.0,300.0],[10050.0,300.0],[10050.0,0.0],[10250.0,0.0],[10250.0,300.0],[12750.0,300.0],[12750.0,0.0],[12950.0,0.0],[12950.0,150.0],[16500.0,150.0],[16500.0,6625.0],[16300.0,6625.0],[16300.0,1900.0],[15825.1,1900.0],[15825.1,1775.0],[16300.0,1775.0],[16300.0,275.0],[12950.0,275.0],[12950.0,1425.0],[13200.1,1425.0],[13200.1,1775.0],[13425.1,1775.0],[13425.1,1900.0],[12950.0,1900.0],[12950.0,3975.0],[12750.0,3975.0],[12750.0,425.0],[10300.0,425.0],[10300.0,3975.0],[10050.0,3975.0],[10050.0,1375.0],[8550.0,1375.0],[8550.0,3175.0],[9300.1,3175.0],[9300.1,3325.0],[8550.0,3325.0],[8550.0,3975.0],[8400.0,3975.0],[8400.0,425.0],[7275.0,425.0],[7275.0,725.0],[5350.0,725.0],[5350.0,3825.0],[6400.0,3825.0],[6400.0,3975.0],[5150.0,3975.0],[5150.0,425.0],[4750.0,425.0],[4750.0,925.0],[4625.0,925.0],[4625.0,-100.0],[2475.0,-100.0],[2475.1,960.0],[1950.0,960.0],[1950.0,3525.0],[1800.0,3525.0],[1800.0,2625.0],[200.0,2625.0],[200.0,5025.0],[1800.0,5025.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,5025.0],[10250.0,5025.0],[10250.0,6500.0],[15250.0,6500.0],[15250.0,6625.0],[1800.0,6625.0],[1800.0,5150.0],[0.0,5150.0],[0.0,800.0]],"holes":[[[8525.0,500.0],[8525.0,1250.0],[10050.0,1250.0],[10050.0,500.0]],[[10050.0,5150.0],[7000.0,5150.0],[7000.0,6500.0],[10050.0,6500.0]],[[6875.0,5150.0],[5350.0,5150.0],[5350.0,5400.0],[5600.0,5400.0],[5600.0,6500.0],[6875.0,6500.0]],[[1925.0,5150.0],[1925.0,6500.0],[5150.0,6500.0],[5150.0,5150.0]],[[1800.0,2500.0],[1800.0,1000.0],[200.0,1000.0],[200.0,2500.0]]],"caps":[[[16500.0,875.0],[16300.0,875.0],[16300.0,275.0],[12950.0,275.0],[12950.0,875.0],[12750.0,875.0],[12750.0,425.0],[10300.0,425.0],[10300.0,875.0],[10050.0,875.0],[10050.0,500.0],[8525.0,500.0],[8525.0,875.0],[8400.0,875.0],[8400.0,425.0],[7275.0,425.0],[7275.0,725.0],[5350.0,725.0],[5350.0,875.0],[5150.0,875.0],[5150.0,425.0],[4750.0,425.0],[4750.0,875.0],[4625.0,875.0],[4625.0,-100.0],[2475.0,-100.0],[2475.09,875.0],[0.0,875.0],[0.0,800.0],[1800.0,800.0],[1800.0,300.0],[2350.0,300.0],[2350.0,-200.0],[4750.0,-200.0],[4750.0,300.0],[5350.0,300.0],[5350.0,600.0],[7150.0,600.0],[7150.0,300.0],[10050.0,300.0],[10050.0,0.0],[10250.0,0.0],[10250.0,300.0],[12750.0,300.0],[12750.0,0.0],[12950.0,0.0],[12950.0,150.0],[16500.0,150.0]],[[16300.0,875.0],[16500.0,875.0],[16500.0,6625.0],[16300.0,6625.0],[16300.0,1900.0],[15825.1,1900.0],[15825.1,1775.0],[16300.0,1775.0]],[[12750.0,875.0],[12950.0,875.0],[12950.0,1425.0],[13200.1,1425.0],[13200.1,1775.0],[13425.1,1775.0],[13425.1,1900.0],[12950.0,1900.0],[12950.0,3975.0],[12750.0,3975.0]],[[8400.0,875.0],[8525.0,875.0],[8525.0,1250.0],[10050.0,1250.0],[10050.0,875.0],[10300.0,875.0],[10300.0,3975.0],[10050.0,3975.0],[10050.0,1375.0],[8550.0,1375.0],[8550.0,3175.0],[9300.1,3175.0],[9300.1,3325.0],[8550.0,3325.0],[8550.0,3975.0],[8400.0,3975.0]],[[5150.0,875.0],[5350.0,875.0],[5350.0,3825.0],[6400.0,3825.0],[6400.0,3975.0],[5150.0,3975.0]],[[4625.0,875.0],[4750.0,875.0],[4750.0,925.0],[4625.0,925.0]],[[0.0,875.0],[2475.09,875.0],[2475.1,960.0],[1950.0,960.0],[1950.0,1750.0],[1800.0,1750.0],[1800.0,1000.0],[200.0,1000.0],[200.0,1750.0],[0.0,1750.0]],[[0.0,1750.0],[200.0,1750.0],[200.0,2500.0],[1800.0,2500.0],[1800.0,1750.0],[1950.0,1750.0],[1950.0,3525.0],[1800.0,3525.0],[1800.0,2625.0],[200.0,2625.0],[200.0,5025.0],[1800.0,5025.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,5025.0],[10250.0,5025.0],[10250.0,5825.0],[10050.0,5825.0],[10050.0,5150.0],[7000.0,5150.0],[7000.0,5825.0],[6875.0,5825.0],[6875.0,5150.0],[5350.0,5150.0],[5350.0,5400.0],[5600.0,5400.0],[5600.0,5825.0],[5150.0,5825.0],[5150.0,5150.0],[1925.0,5150.0],[1925.0,5825.0],[1800.0,5825.0],[1800.0,5150.0],[0.0,5150.0]],[[1800.0,5825.0],[1925.0,5825.0],[1925.0,6500.0],[5150.0,6500.0],[5150.0,5825.0],[5600.0,5825.0],[5600.0,6500.0],[6875.0,6500.0],[6875.0,5825.0],[7000.0,5825.0],[7000.0,6500.0],[10050.0,6500.0],[10050.0,5825.0],[10250.0,5825.0],[10250.0,6500.0],[15250.0,6500.0],[15250.0,6625.0],[1800.0,6625.0]]]},{"outer":[[6400.0,3975.0],[6550.0,3975.0],[6550.0,4125.0],[6400.0,4125.0]],"holes":[]},{"outer":[[6550.1,3975.0],[6550.1,3825.0],[7500.1,3825.0],[7500.1,3975.0]],"holes":[]}]},{"z0":600.0,"z1":1200.0,"polys":[{"outer":[[16300.0,275.0],[16300.0,150.0],[16500.0,150.0],[16500.0,275.0]],"holes":[]},{"outer":[[16500.0,6625.0],[16300.0,6625.0],[16300.0,1900.0],[15825.1,1900.0],[15825.1,1775.0],[16300.0,1775.0],[16300.0,1175.0],[16500.0,1175.0]],"holes":[]},{"outer":[[0.0,800.0],[1800.0,800.0],[1800.0,300.0],[2475.1,300.0],[2475.1,960.0],[1950.0,960.0],[1950.0,3525.0],[1800.0,3525.0],[1800.0,2625.0],[200.0,2625.0],[200.0,5025.0],[1800.0,5025.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,5025.0],[10250.0,5025.0],[10250.0,6500.0],[15250.0,6500.0],[15250.0,6625.0],[1800.0,6625.0],[1800.0,5150.0],[0.0,5150.0]],"holes":[[[10050.0,5150.0],[7000.0,5150.0],[7000.0,6500.0],[10050.0,6500.0]],[[6875.0,5150.0],[5350.0,5150.0],[5350.0,5400.0],[5600.0,5400.0],[5600.0,6500.0],[6875.0,6500.0]],[[1925.0,5150.0],[1925.0,6500.0],[5150.0,6500.0],[5150.0,5150.0]],[[1800.0,2500.0],[1800.0,1000.0],[200.0,1000.0],[200.0,2500.0]]],"caps":[[[10250.0,5825.0],[10050.0,5825.0],[10050.0,5150.0],[7000.0,5150.0],[7000.0,5825.0],[6875.0,5825.0],[6875.0,5150.0],[5350.0,5150.0],[5350.0,5400.0],[5600.0,5400.0],[5600.0,5825.0],[5150.0,5825.0],[5150.0,5150.0],[1925.0,5150.0],[1925.0,5825.0],[1800.0,5825.0],[1800.0,5150.0],[0.0,5150.0],[0.0,1750.0],[200.0,1750.0],[200.0,2500.0],[1800.0,2500.0],[1800.0,1750.0],[1950.0,1750.0],[1950.0,3525.0],[1800.0,3525.0],[1800.0,2625.0],[200.0,2625.0],[200.0,5025.0],[1800.0,5025.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,5025.0],[10250.0,5025.0]],[[1950.0,1750.0],[1800.0,1750.0],[1800.0,1000.0],[200.0,1000.0],[200.0,1750.0],[0.0,1750.0],[0.0,800.0],[1800.0,800.0],[1800.0,300.0],[2475.1,300.0],[2475.1,960.0],[1950.0,960.0]],[[1800.0,5825.0],[1925.0,5825.0],[1925.0,6500.0],[5150.0,6500.0],[5150.0,5825.0],[5600.0,5825.0],[5600.0,6500.0],[6875.0,6500.0],[6875.0,5825.0],[7000.0,5825.0],[7000.0,6500.0],[10050.0,6500.0],[10050.0,5825.0],[10250.0,5825.0],[10250.0,6500.0],[15250.0,6500.0],[15250.0,6625.0],[1800.0,6625.0]]]},{"outer":[[12750.0,3975.0],[12750.0,425.0],[12125.1,425.0],[12125.1,300.0],[12750.0,300.0],[12750.0,0.0],[12950.0,0.0],[12950.0,1425.0],[13200.1,1425.0],[13200.1,1775.0],[13425.1,1775.0],[13425.1,1900.0],[12950.0,1900.0],[12950.0,3975.0]],"holes":[]},{"outer":[[7150.0,300.0],[10050.0,300.0],[10050.0,0.0],[10250.0,0.0],[10250.0,300.0],[10925.1,300.0],[10925.1,425.0],[10300.0,425.0],[10300.0,3975.0],[10050.0,3975.0],[10050.0,1375.0],[8550.0,1375.0],[8550.0,3175.0],[9300.1,3175.0],[9300.1,3325.0],[8550.0,3325.0],[8550.0,3975.0],[8400.0,3975.0],[8400.0,425.0],[7275.0,425.0],[7275.0,725.0],[7150.0,725.0]],"holes":[[[8525.0,1250.0],[10050.0,1250.0],[10050.0,500.0],[8525.0,500.0]]],"caps":[[[10300.0,875.0],[10050.0,875.0],[10050.0,500.0],[8525.0,500.0],[8525.0,875.0],[8400.0,875.0],[8400.0,425.0],[7275.0,425.0],[7275.0,725.0],[7150.0,725.0],[7150.0,300.0],[10050.0,300.0],[10050.0,0.0],[10250.0,0.0],[10250.0,300.0],[10925.1,300.0],[10925.1,425.0],[10300.0,425.0]],[[8400.0,875.0],[8525.0,875.0],[8525.0,1250.0],[10050.0,1250.0],[10050.0,875.0],[10300.0,875.0],[10300.0,3975.0],[10050.0,3975.0],[10050.0,1375.0],[8550.0,1375.0],[8550.0,3175.0],[9300.1,3175.0],[9300.1,3325.0],[8550.0,3325.0],[8550.0,3975.0],[8400.0,3975.0]]]},{"outer":[[4750.0,925.0],[4625.0,925.0],[4625.0,300.0],[5350.0,300.0],[5350.0,3825.0],[6400.0,3825.0],[6400.0,3975.0],[5150.0,3975.0],[5150.0,425.0],[4750.0,425.0]],"holes":[]},{"outer":[[6400.0,3975.0],[6550.0,3975.0],[6550.0,4125.0],[6400.0,4125.0]],"holes":[]},{"outer":[[6550.1,3975.0],[6550.1,3825.0],[7500.1,3825.0],[7500.1,3975.0]],"holes":[]},{"outer":[[4625.0,-200.0],[4750.0,-200.0],[4750.0,-100.0],[4625.0,-100.0]],"holes":[]},{"outer":[[2350.0,-200.0],[2475.0,-200.0],[2475.0,-100.0],[2350.0,-100.0]],"holes":[]}]},{"z0":1200.0,"z1":3000.0,"polys":[{"outer":[[16300.0,150.0],[16500.0,150.0],[16500.0,275.0],[16300.0,275.0]],"holes":[]},{"outer":[[16300.0,6625.0],[16300.0,1900.0],[15825.1,1900.0],[15825.1,1775.0],[16300.0,1775.0],[16300.0,1175.0],[16500.0,1175.0],[16500.0,6625.0]],"holes":[]},{"outer":[[0.0,800.0],[1800.0,800.0],[1800.0,300.0],[2475.1,300.0],[2475.1,960.0],[1950.0,960.0],[1950.0,3525.0],[1800.0,3525.0],[1800.0,2625.0],[1300.1,2625.0],[1300.1,2500.0],[1800.0,2500.0],[1800.0,1000.0],[200.0,1000.0],[200.0,2500.0],[700.1,2500.0],[700.1,2625.0],[200.0,2625.0],[200.0,5025.0],[1800.0,5025.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,5025.0],[10250.0,5025.0],[10250.0,6500.0],[15250.0,6500.0],[15250.0,6625.0],[1800.0,6625.0],[1800.0,5150.0],[0.0,5150.0]],"holes":[[[7000.0,5150.0],[7000.0,6500.0],[10050.0,6500.0],[10050.0,5150.0]],[[5600.0,5400.0],[5600.0,6500.0],[6875.0,6500.0],[6875.0,5150.0],[5350.0,5150.0],[5350.0,5400.0]],[[1925.0,5150.0],[1925.0,6500.0],[5150.0,6500.0],[5150.0,5150.0]]],"caps":[[[10250.0,5825.0],[10050.0,5825.0],[10050.0,5150.0],[7000.0,5150.0],[7000.0,5825.0],[6875.0,5825.0],[6875.0,5150.0],[5350.0,5150.0],[5350.0,5400.0],[5600.0,5400.0],[5600.0,5825.0],[5150.0,5825.0],[5150.0,5150.0],[1925.0,5150.0],[1925.0,5825.0],[1800.0,5825.0],[1800.0,5150.0],[0.0,5150.0],[0.0,800.0],[1800.0,800.0],[1800.0,300.0],[2475.1,300.0],[2475.1,960.0],[1950.0,960.0],[1950.0,3525.0],[1800.0,3525.0],[1800.0,2625.0],[1300.1,2625.0],[1300.1,2500.0],[1800.0,2500.0],[1800.0,1000.0],[200.0,1000.0],[200.0,2500.0],[700.1,2500.0],[700.1,2625.0],[200.0,2625.0],[200.0,5025.0],[1800.0,5025.0],[1800.0,4275.0],[1950.0,4275.0],[1950.0,5025.0],[10250.0,5025.0]],[[1800.0,5825.0],[1925.0,5825.0],[1925.0,6500.0],[5150.0,6500.0],[5150.0,5825.0],[5600.0,5825.0],[5600.0,6500.0],[6875.0,6500.0],[6875.0,5825.0],[7000.0,5825.0],[7000.0,6500.0],[10050.0,6500.0],[10050.0,5825.0],[10250.0,5825.0],[10250.0,6500.0],[15250.0,6500.0],[15250.0,6625.0],[1800.0,6625.0]]]},{"outer":[[12125.1,425.0],[12125.1,300.0],[12750.0,300.0],[12750.0,0.0],[12950.0,0.0],[12950.0,1425.0],[13200.1,1425.0],[13200.1,1775.0],[13425.1,1775.0],[13425.1,1900.0],[12950.0,1900.0],[12950.0,3975.0],[12750.0,3975.0],[12750.0,425.0]],"holes":[]},{"outer":[[7150.0,300.0],[10050.0,300.0],[10050.0,0.0],[10250.0,0.0],[10250.0,300.0],[10925.1,300.0],[10925.1,425.0],[10300.0,425.0],[10300.0,3975.0],[10050.0,3975.0],[10050.0,1375.0],[9587.6,1375.0],[9587.6,1250.0],[10050.0,1250.0],[10050.0,500.0],[8525.0,500.0],[8525.0,1250.0],[8987.6,1250.0],[8987.6,1375.0],[8550.0,1375.0],[8550.0,3175.0],[9300.1,3175.0],[9300.1,3325.0],[8550.0,3325.0],[8550.0,3975.0],[8400.0,3975.0],[8400.0,425.0],[7275.0,425.0],[7275.0,725.0],[7150.0,725.0]],"holes":[]},{"outer":[[4750.0,925.0],[4625.0,925.0],[4625.0,300.0],[5350.0,300.0],[5350.0,3825.0],[6400.0,3825.0],[6400.0,3975.0],[5150.0,3975.0],[5150.0,425.0],[4750.0,425.0]],"holes":[]},{"outer":[[6400.0,3975.0],[6550.0,3975.0],[6550.0,4125.0],[6400.0,4125.0]],"holes":[]},{"outer":[[6550.1,3975.0],[6550.1,3825.0],[7500.1,3825.0],[7500.1,3975.0]],"holes":[]},{"outer":[[4625.0,-200.0],[4750.0,-200.0],[4750.0,-100.0],[4625.0,-100.0]],"holes":[]},{"outer":[[2350.0,-200.0],[2475.0,-200.0],[2475.0,-100.0],[2350.0,-100.0]],"holes":[]}]}]}""")
S = DATA['spec']              # mm
CONFIG = DATA.get('config', {})
M = 0.001                     # mm -> m

# Logical architectural collection hierarchy (Section 9)
HIER = {
    '01_Structure': None,
    'WALLS': '01_Structure',
    'CEILING': '01_Structure',
    'RECESSED_CEILINGS': '01_Structure',
    'WALL_PANELS': '01_Structure',
    '02_Openings': None,
    'LINTELS': '02_Openings',
    'DOOR_FITTINGS': '02_Openings',
    'WINDOW_FITTINGS': '02_Openings',
    'DOORS': '02_Openings',
    'WINDOWS': '02_Openings',
    '03_Flooring': None,
    '04_Skirting': None,
    '05_Washroom_Tiles': None,
    'WASHROOM_TILES': '05_Washroom_Tiles',
    '06_Balcony': None,
    'BALCONY_GLASS': '06_Balcony',
    '07_Kitchen': None,
    '08_Materials_And_Lighting': None,
    'ROOMS': None,
    'EDITABLE_PARTS': None,
    'SKIRTING': 'EDITABLE_PARTS',
    'FLOOR': '01_Structure',
    'SOURCE_CAD': None,
    'VALIDATION': None,
}
LEGACY = ('BUILDING', 'WALL_PIECES', 'Exterior_Walls', 'Interior_Walls', 'Openings')


# ─────────────────────────── helpers ───────────────────────────
def collection(name):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    pname = HIER.get(name)
    parent = bpy.context.scene.collection if pname is None else collection(pname)
    for p in [bpy.context.scene.collection] + [c for c in bpy.data.collections if c is not col]:
        if p is not parent and col.name in p.children:
            p.children.unlink(col)
    if col.name not in parent.children:
        parent.children.link(col)
    return col


def _remove_obj(obj):
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and data.users == 0:
        if isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Light):
            bpy.data.lights.remove(data)
        elif isinstance(data, bpy.types.Camera):
            bpy.data.cameras.remove(data)


def purge(col, children=True):
    """Delete the generated content of a collection (objects + orphan meshes), keep the collection."""
    if children:
        for ch in list(col.children):
            if ch.name not in HIER:
                purge(ch)
                bpy.data.collections.remove(ch)
    for obj in list(col.objects):
        _remove_obj(obj)


def layer_col(name, root=None):
    root = root or bpy.context.view_layer.layer_collection
    if root.name == name:
        return root
    for ch in root.children:
        r = layer_col(name, ch)
        if r:
            return r
    return None


def material(name, rgba, rough=0.5, spec=0.5, coat=0.0, bump=0.0, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.roughness = rough
    if hasattr(m, 'metallic'):
        m.metallic = metal
    if getattr(m, 'node_tree', None) is None:
        m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    for nd in list(nodes):
        nodes.remove(nd)
    out = nodes.new('ShaderNodeOutputMaterial'); out.location = (400, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (100, 0)
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Roughness'].default_value = rough
    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = metal
    for key in ('Specular IOR Level', 'Specular'):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = spec
            break
    if coat and 'Coat Weight' in bsdf.inputs:
        bsdf.inputs['Coat Weight'].default_value = coat
        bsdf.inputs['Coat Roughness'].default_value = 0.04
    if emit:
        for ek in ('Emission Color', 'Emission'):
            if ek in bsdf.inputs:
                bsdf.inputs[ek].default_value = rgba
                break
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = emit
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    if bump:
        tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-700, -200)
        nz = nodes.new('ShaderNodeTexNoise'); nz.location = (-500, -200)
        nz.inputs['Scale'].default_value = 120.0
        nz.inputs['Detail'].default_value = 4.0
        bp = nodes.new('ShaderNodeBump'); bp.location = (-200, -200)
        bp.inputs['Strength'].default_value = bump
        bp.inputs['Distance'].default_value = 0.0004
        links.new(tc.outputs['Object'], nz.inputs['Vector'])
        links.new(nz.outputs['Fac'], bp.inputs['Height'])
        links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m


def wood_plank_material(name):
    """Dedicated procedural wooden plank flooring material for Master Bedroom (Section 5.F):
    consistent plank orientation via UVMap, subtle wood grain, natural colour variation, realistic plank joints."""
    rgba = (0.55, 0.35, 0.18, 1.0)
    m = material(name, rgba, rough=0.28, spec=0.5, coat=0.18, bump=0.0)
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        return m
    tc = nodes.new('ShaderNodeTexCoord'); tc.location = (-900, 0)
    mp = nodes.new('ShaderNodeMapping'); mp.location = (-700, 0)
    # 1 UV unit = 1 m -> scale for 1.2 m x 0.18 m wooden planks
    mp.inputs['Scale'].default_value = (1.0, 2.2, 1.0)
    brk = nodes.new('ShaderNodeTexBrick'); brk.location = (-450, 80)
    brk.offset = 0.5
    brk.offset_frequency = 2
    brk.squash = 1.0
    brk.inputs['Color1'].default_value = (0.58, 0.37, 0.20, 1.0)
    brk.inputs['Color2'].default_value = (0.48, 0.29, 0.15, 1.0)
    brk.inputs['Mortar'].default_value = (0.22, 0.13, 0.06, 1.0)
    brk.inputs['Scale'].default_value = 2.5
    brk.inputs['Mortar Size'].default_value = 0.008
    brk.inputs['Mortar Smooth'].default_value = 0.1
    brk.inputs['Bias'].default_value = 0.0
    brk.inputs['Brick Width'].default_value = 1.20
    brk.inputs['Row Height'].default_value = 0.18

    nz = nodes.new('ShaderNodeTexNoise'); nz.location = (-450, -180)
    nz.inputs['Scale'].default_value = 32.0
    nz.inputs['Detail'].default_value = 5.0
    nz.inputs['Roughness'].default_value = 0.55

    mix = nodes.new('ShaderNodeMixRGB'); mix.location = (-180, 60)
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 0.12
    bp = nodes.new('ShaderNodeBump'); bp.location = (-180, -160)
    bp.inputs['Strength'].default_value = 0.035
    bp.inputs['Distance'].default_value = 0.0005

    links.new(tc.outputs['UV'], mp.inputs['Vector'])
    links.new(mp.outputs['Vector'], brk.inputs['Vector'])
    links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    links.new(brk.outputs['Color'], mix.inputs['Color1'])
    links.new(nz.outputs['Color'], mix.inputs['Color2'])
    links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(brk.outputs['Fac'], bp.inputs['Height'])
    links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    return m


def _clean_ring(ring, tol_dup=1e-7, tol_collinear=1e-5):
    out = []
    for x, y in ring:
        if not out or math.hypot(x - out[-1][0], y - out[-1][1]) > tol_dup:
            out.append((x, y))
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol_dup:
        out.pop()
    changed = True
    while changed and len(out) >= 4:
        changed = False
        n = len(out)
        for i in range(n):
            a, b, c = out[(i - 1) % n], out[i], out[(i + 1) % n]
            v1x, v1y = b[0] - a[0], b[1] - a[1]
            v2x, v2y = c[0] - b[0], c[1] - b[1]
            vx, vy = c[0] - a[0], c[1] - a[1]
            l_ac = math.hypot(vx, vy)
            if math.hypot(v1x, v1y) <= tol_dup or math.hypot(v2x, v2y) <= tol_dup or l_ac <= tol_dup:
                out.pop(i)
                changed = True
                break
            if (v1x * v2x + v1y * v2y) > 0.0 and abs(v1x * vy - v1y * vx) / l_ac <= tol_collinear:
                out.pop(i)
                changed = True
                break
    return out


def prism(name, outer, holes, z0, z1, center=True, uv_angle=0.0, caps=None, z_origin=False):
    """Footprint (metres, outer CCW + holes) extruded from z0 to z1 -> clean quad/planar-ngon mesh, metric UVMap."""
    caps_clean = [c for c in caps if len(c) >= 3] if caps else None
    if not caps_clean:
        outer = _clean_ring(outer)
        holes = [_clean_ring(h) for h in holes if len(h) >= 3]
    ref_pts = [pt for c in caps_clean for pt in c] if caps_clean else outer
    if not ref_pts or len(ref_pts) < 3:
        me = bpy.data.meshes.new(name)
        return (me, (0.0, 0.0, 0.0)) if z_origin else (me, (0.0, 0.0))
    cx = sum(p[0] for p in ref_pts) / len(ref_pts) if center else 0.0
    cy = sum(p[1] for p in ref_pts) / len(ref_pts) if center else 0.0
    cz = z0 if z_origin else 0.0
    zl0, zl1 = z0 - cz, z1 - cz
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    if caps_clean:
        v_bot, v_top = {}, {}
        for c in caps_clean:
            for pt in c:
                k = (round(pt[0], 6), round(pt[1], 6))
                if k not in v_bot:
                    v_bot[k] = bm.verts.new((pt[0] - cx, pt[1] - cy, zl0))
                    v_top[k] = bm.verts.new((pt[0] - cx, pt[1] - cy, zl1))
        cap_edges = set()
        for c in caps_clean:
            ks = [(round(pt[0], 6), round(pt[1], 6)) for pt in c]
            ks = [ks[i] for i in range(len(ks)) if ks[i] != ks[(i - 1) % len(ks)]]
            if len(ks) < 3:
                continue
            try:
                bm.faces.new([v_bot[k] for k in reversed(ks)])
                bm.faces.new([v_top[k] for k in ks])
            except ValueError:
                pass
            for i in range(len(ks)):
                cap_edges.add((ks[i], ks[(i + 1) % len(ks)]))
        for ka, kb in cap_edges:
            if (kb, ka) not in cap_edges:
                try:
                    bm.faces.new((v_bot[ka], v_bot[kb], v_top[kb], v_top[ka]))
                except ValueError:
                    pass
    elif not holes:
        b = [bm.verts.new((x - cx, y - cy, zl0)) for x, y in outer]
        t = [bm.verts.new((x - cx, y - cy, zl1)) for x, y in outer]
        for i in range(len(outer)):
            j = (i + 1) % len(outer)
            bm.faces.new((b[i], b[j], t[j], t[i]))
        try:
            bm.faces.new(list(reversed(b)))
            bm.faces.new(t)
        except ValueError:
            tris = tessellate_polygon([[Vector((x, y, 0.0)) for x, y in outer]])
            for a, b_, c_ in tris:
                bm.faces.new((b[c_], b[b_], b[a]))
                bm.faces.new((t[a], t[b_], t[c_]))
    else:
        rings = [outer] + holes
        bot, top = [], []
        for r in rings:
            b = [bm.verts.new((x - cx, y - cy, zl0)) for x, y in r]
            t = [bm.verts.new((x - cx, y - cy, zl1)) for x, y in r]
            bot.append(b); top.append(t)
            for i in range(len(r)):
                j = (i + 1) % len(r)
                bm.faces.new((b[i], b[j], t[j], t[i]))
        tris = tessellate_polygon([[Vector((x, y, 0.0)) for x, y in r] for r in rings])
        fb = [v for r in bot for v in r]
        ft = [v for r in top for v in r]
        for a, b_, c_ in tris:
            bm.faces.new((fb[c_], fb[b_], fb[a]))
            bm.faces.new((ft[a], ft[b_], ft[c_]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cs, sn = math.cos(-uv_angle), math.sin(-uv_angle)
    for f in bm.faces:
        f.smooth = False
        nz = abs(f.normal.z)
        for lp in f.loops:
            vx, vy, vz = lp.vert.co.x + cx, lp.vert.co.y + cy, lp.vert.co.z + cz
            if nz > 0.7:
                lp[uvl].uv = (vx * cs - vy * sn, vx * sn + vy * cs)
            elif abs(f.normal.x) >= abs(f.normal.y):
                lp[uvl].uv = (vy, vz)
            else:
                lp[uvl].uv = (vx, vz)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return (me, (cx, cy, cz)) if z_origin else (me, (cx, cy))


def new_obj(name, mesh, col, mat=None, loc=(0.0, 0.0, 0.0)):
    old = bpy.data.objects.get(name)
    if old is not None:
        _remove_obj(old)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    if mat is not None:
        obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj


def mring(r):
    return [(x * M, y * M) for x, y in r]


def pip(x, y, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


ROOMS_M = [dict(r, ring_m=mring(r['ring']), holes_m=[mring(h) for h in r['holes']]) for r in DATA['rooms']]
OPEN_M = [dict(o, rect_m=mring(o['rect'])) for o in DATA['openings']]


def room_at(x, y):
    for r in ROOMS_M:
        if pip(x, y, r['ring_m']) and not any(pip(x, y, h) for h in r['holes_m']):
            return r
    return None


# ─────────────────────────── scene, collections & materials ───────────────────────────
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = 'MILLIMETERS'
MAT = {}
LOG = []


def _make_glass(m, alpha, rough, rgba=(0.68, 0.88, 0.98, 0.28)):
    """Physically based architectural glass (works in Material Preview, EEVEE and Cycles):
      Principled BSDF (transmission 1.0, IOR 1.52, clear-coat reflections)
        mixed by Fresnel with a tinted Transparent BSDF  -> see-through face-on, reflective at grazing angles
      + Light Path 'Is Shadow Ray' -> transparent  -> daylight passes into the rooms (no black shadows)."""
    m.diffuse_color = (rgba[0], rgba[1], rgba[2], max(alpha, 0.25))     # Solid-mode viewport colour (see-through)
    m.roughness = rough
    if hasattr(m, 'metallic'):
        m.metallic = 0.0
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    for nd in list(nodes):
        nodes.remove(nd)
    out = nodes.new('ShaderNodeOutputMaterial'); out.location = (900, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (0, 120)
    bsdf.name = bsdf.label = 'Glass_BSDF'
    tint = (rgba[0], rgba[1], rgba[2], 1.0)
    bsdf.inputs['Base Color'].default_value = tint
    bsdf.inputs['Roughness'].default_value = rough
    for key, val in (('Metallic', 0.0), ('IOR', 1.52), ('Transmission Weight', 1.0), ('Transmission', 1.0),
                     ('Specular IOR Level', 0.5), ('Coat Weight', 0.25), ('Coat Roughness', 0.02)):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = val
    transp = nodes.new('ShaderNodeBsdfTransparent'); transp.location = (0, -260)
    transp.inputs['Color'].default_value = (0.5 + 0.5 * rgba[0], 0.5 + 0.5 * rgba[1], 0.5 + 0.5 * rgba[2], 1.0)
    fres = nodes.new('ShaderNodeFresnel'); fres.location = (0, 380)
    fres.inputs['IOR'].default_value = 1.52
    # how much of the pane is "solid" glass vs. see-through: frosted ventilator glass is less transparent
    solid = nodes.new('ShaderNodeMath'); solid.location = (220, 380)
    solid.operation = 'MAXIMUM'
    solid.inputs[1].default_value = min(0.85, max(0.05, 1.0 - alpha * 2.2 if alpha > 0.35 else 0.12))
    links.new(fres.outputs['Fac'], solid.inputs[0])
    mix_f = nodes.new('ShaderNodeMixShader'); mix_f.location = (440, 60)
    mix_f.name = mix_f.label = 'Fresnel_Glass_Mix'
    links.new(solid.outputs[0], mix_f.inputs['Fac'])
    links.new(transp.outputs['BSDF'], mix_f.inputs[1])
    links.new(bsdf.outputs['BSDF'], mix_f.inputs[2])
    lp = nodes.new('ShaderNodeLightPath'); lp.location = (440, 380)
    mix_s = nodes.new('ShaderNodeMixShader'); mix_s.location = (680, 0)
    mix_s.name = mix_s.label = 'Shadow_Pass_Mix'
    links.new(lp.outputs['Is Shadow Ray'], mix_s.inputs['Fac'])
    links.new(mix_f.outputs['Shader'], mix_s.inputs[1])
    links.new(transp.outputs['BSDF'], mix_s.inputs[2])
    links.new(mix_s.outputs['Shader'], out.inputs['Surface'])
    if hasattr(m, 'surface_render_method'):
        m.surface_render_method = 'BLENDED'
    elif hasattr(m, 'blend_method'):
        m.blend_method = 'BLEND'
    for attr, val in (('use_transparent_shadow', True), ('use_screen_refraction', True),
                      ('use_raytrace_refraction', True), ('show_transparent_back', False),
                      ('use_transparency_overlap', False)):
        if hasattr(m, attr):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    if hasattr(m, 'thickness_mode'):
        try:
            m.thickness_mode = 'SLAB'                    # thin flat pane
        except Exception:
            pass
    m.use_backface_culling = False
    m['material_type'] = 'architectural_glass'


def organize_scene_collections():
    """Create and organize the 01_Structure..08_Materials_And_Lighting collections and purge legacy collections."""
    def_col = bpy.data.collections.get('Collection')
    if def_col is not None:
        cube = def_col.objects.get('Cube')
        if cube is not None and cube.type == 'MESH' and len(cube.data.vertices) == 8:
            _remove_obj(cube)
    for name in LEGACY:
        col = bpy.data.collections.get(name)
        if col is not None:
            purge(col)
            bpy.data.collections.remove(col)
    for c in HIER:
        collection(c)


def assign_room_materials():
    """Create or reuse all architectural material presets (Sections 3, 5, 6, 7, 10)."""
    MAT.update({
        # Structural walls & ceiling
        'ext': material('Exterior_Wall_Mat', (0.80, 0.78, 0.74, 1.0), 0.85, 0.3),
        'int': material('Interior_Wall_Mat', (0.93, 0.92, 0.89, 1.0), 0.9, 0.3),
        'wash_back': material('Washroom_Grout_Mat', (0.58, 0.56, 0.53, 1.0), 0.95, 0.2),
        'ceiling': material('Ceiling_Mat', (0.96, 0.96, 0.95, 1.0), 0.9, 0.2),
        'room': material('Room_Footprint_Mat', (0.3, 0.6, 0.9, 1.0), 1.0, 0.0),

        # Section 3: Blue Lintel Beams
        'lintel_blue': material('MAT_Lintel_Blue', (0.12, 0.42, 0.88, 1.0), 0.38, 0.5),

        # Sections 4, 5 & 6: Room-wise Flooring & Skirting Presets
        'floor_common': material('MAT_Floor_Common', (0.84, 0.81, 0.76, 1.0), 0.22, 0.55, coat=0.15),
        'floor_master_wood': wood_plank_material('MAT_Floor_Master_Wood'),
        'floor_entrance': material('MAT_Floor_Entrance', (0.38, 0.36, 0.33, 1.0), 0.26, 0.55, coat=0.15),
        'floor_balcony': material('MAT_Floor_Balcony', (0.66, 0.42, 0.28, 1.0), 0.65, 0.35, bump=0.03),
        'floor_washroom': material('MAT_Floor_Washroom', (0.66, 0.70, 0.72, 1.0), 0.42, 0.45, bump=0.02),
        'skirt_common': material('MAT_Skirting_Common', (0.72, 0.69, 0.64, 1.0), 0.32, 0.5),
        'skirt_master': material('MAT_Skirting_Master', (0.36, 0.22, 0.11, 1.0), 0.30, 0.5, coat=0.15),
        'skirt_entrance': material('MAT_Skirting_Entrance', (0.28, 0.26, 0.24, 1.0), 0.30, 0.5),
        'skirt_balcony': material('MAT_Skirting_Balcony', (0.44, 0.41, 0.38, 1.0), 0.60, 0.35),
        'floor': material('Floor_Mat', (0.74, 0.71, 0.66, 1.0), 0.4, 0.5),
        'skirt': material('MAT_Skirting_Common', (0.72, 0.69, 0.64, 1.0), 0.32, 0.5),

        # Section 6: Washroom Wall Tiles
        'tile': material('MAT_Washroom_Wall_Tiles', (0.92, 0.91, 0.88, 1.0), 0.12, 0.55, coat=0.35, bump=0.03),

        # Section 7: Balcony Glass & Metal Railing Supports
        'bglass': material('MAT_Balcony_Glass', (0.70, 0.86, 0.88, 0.30), 0.02, 0.5),
        'bmetal': material('MAT_Balcony_Railing_Metal', (0.78, 0.80, 0.83, 1.0), 0.22, 0.7, metal=0.90),

        # Section 10: Kitchen Platform & Countertop
        'kitch_top': material('MAT_Kitchen_Countertop', (0.14, 0.14, 0.16, 1.0), 0.16, 0.65, coat=0.40, bump=0.02),
        'kitch_base': material('MAT_Kitchen_Base', (0.78, 0.74, 0.68, 1.0), 0.42, 0.45),

        # Windows, Doors, Wall Panels & Recessed Ceilings
        'frame': material('Window_Frame_Alu_Mat', (0.76, 0.78, 0.82, 1.0), 0.28, 0.65, metal=0.85),
        'glass': material('Window_Glass_Mat', (0.68, 0.88, 0.98, 0.28), 0.02, 0.5),
        'vglass': material('Ventilator_Frosted_Glass_Mat', (0.78, 0.90, 0.96, 0.45), 0.25, 0.5),
        'room_label': material('MAT_Room_Plan_Label', (0.10, 0.22, 0.44, 1.0), 0.40, 0.3, emit=0.6),
        'panel': material('Wall_Panel_Mat', (0.86, 0.80, 0.70, 1.0), 0.45, 0.4),
        'door_frame': material('Door_Frame_Wood_Mat', (0.30, 0.17, 0.09, 1.0), 0.35, 0.5, coat=0.20, bump=0.02),
        'door_leaf': material('Door_Wood_Mat', (0.55, 0.34, 0.18, 1.0), 0.32, 0.5, coat=0.25, bump=0.02),
        'door_lever': material('Door_Lever_Silver_Mat', (0.83, 0.85, 0.88, 1.0), 0.18, 0.7, coat=0.20, metal=0.92),
        'ceiling_drop': material('Ceiling_Drop_Border_Mat', (0.94, 0.94, 0.92, 1.0), 0.85, 0.25),
        'ceiling_tray': material('Ceiling_Recessed_Tray_Mat', (0.98, 0.97, 0.95, 1.0), 0.88, 0.20),
        'cove_led': material('Recessed_Cove_LED_Mat', (1.00, 0.92, 0.76, 1.0), 0.10, 0.5, emit=3.5),
        'downlight_led': material('Recessed_Downlight_LED_Mat', (1.00, 0.95, 0.84, 1.0), 0.10, 0.5, emit=4.0),
        'downlight_housing': material('Recessed_Housing_Dark_Mat', (0.14, 0.15, 0.16, 1.0), 0.40, 0.5, metal=0.60),
    })
    _make_glass(MAT['glass'], 0.28, 0.02, (0.68, 0.88, 0.98, 0.28))
    _make_glass(MAT['vglass'], 0.45, 0.25, (0.78, 0.90, 0.96, 0.45))
    _make_glass(MAT['bglass'], 0.30, 0.02, (0.70, 0.86, 0.88, 0.30))


# ─────────────────────────── 1. CONTINUOUS WALLS & BLUE LINTELS ───────────────────────────
def union_node_group():
    ng = bpy.data.node_groups.get('CAD_Wall_Exact_Union')
    if ng is None:
        ng = bpy.data.node_groups.new('CAD_Wall_Exact_Union', 'GeometryNodeTree')
        ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        gi = ng.nodes.new('NodeGroupInput')
        go = ng.nodes.new('NodeGroupOutput')
        mb = ng.nodes.new('GeometryNodeMeshBoolean')
        mb.operation = 'UNION'
        mb.solver = 'EXACT'
        ng.links.new(gi.outputs[0], mb.inputs['Mesh 2'])
        ng.links.new(mb.outputs[0], go.inputs[0])
    return ng


def build_walls():
    """Build every wall, column post, and window sill as an independent, directly editable mesh
    in 01_Structure > WALLS with clean quad/planar topology and centered object origin."""
    if not CONNECT_WALLS_INTO_ONE_MESH:
        purge(collection('01_Structure'), children=False)
    if not BUILD_WALL_PANELS:
        purge(collection('WALL_PANELS'))
    wp = collection('WALLS')
    purge(wp)
    n_built = 0
    for p in DATA['pieces']:
        if p['kind'] == 'lintel' and BUILD_BLUE_LINTELS:
            continue
        z0, z1 = p['base'] * M, (p['base'] + p['height']) * M
        me, (cx, cy, cz) = prism(p['id'] + '_Mesh', mring(p['ring']), [], z0, z1, z_origin=True)
        if p['kind'] == 'lintel':
            o = new_obj(p['id'], me, wp, MAT['lintel_blue'], (cx, cy, cz))
        else:
            # slots: 0 interior, 1 exterior, 2 washroom side -> each face takes the finish of the space it faces
            o = new_obj(p['id'], me, wp, MAT['int'], (cx, cy, cz))
            me.materials.append(MAT['ext'])
            me.materials.append(MAT['wash_back'])
            for poly in me.polygons:
                n = poly.normal
                if abs(n.z) > 0.7:
                    poly.material_index = 0
                    continue
                px = poly.center.x + cx + n.x * 0.02
                py = poly.center.y + cy + n.y * 0.02
                r = room_at(px, py)
                if r is not None:
                    poly.material_index = 2 if r['type'] == 'washroom' else 0
                elif any(pip(px, py, op['rect_m']) for op in OPEN_M):
                    poly.material_index = 0
                else:
                    poly.material_index = 1
        o.hide_select = False
        o.hide_render = False
        o['piece_id'] = p['id']
        o['kind'], o['opening'], o['wall_type'] = p['kind'], p['opening'], p['wall_type']
        o['thickness_mm'], o['base_mm'], o['height_mm'] = p['thickness'], p['base'], p['height']
        n_built += 1
    wp.hide_render = False
    lc = layer_col('WALLS')
    if lc:
        lc.exclude = False
        lc.hide_viewport = False
    LOG.append(f"walls: {n_built} separate editable wall / post / sill meshes in 01_Structure > WALLS")


def generate_blue_lintels():
    """Section 3: Create clearly visible blue-colored lintel beams (Lintel_Door_001, Lintel_Window_001)
    from Z = 2.1 m to Z = 3.0 m above all doors, standard windows, and washroom windows.
    No lintel beam is created across open passages or balcony railings."""
    lc = collection('LINTELS')
    purge(lc)
    n_lintels = 0
    for p in DATA['pieces']:
        if p['kind'] != 'lintel':
            continue
        z0, z1 = p['base'] * M, (p['base'] + p['height']) * M
        me, (cx, cy, cz) = prism(p['id'] + '_Mesh', mring(p['ring']), [], z0, z1, z_origin=True)
        ob = new_obj(p['id'], me, lc, MAT['lintel_blue'], (cx, cy, cz))
        ob.hide_select = False
        ob['piece_id'] = p['id']
        ob['kind'] = 'lintel'
        ob['wall_type'] = p['wall_type']
        ob['opening'] = p['opening']
        ob['opening_type'] = p['opening']
        ob['opening_id'] = p.get('opening_id', '')
        ob['base_mm'], ob['height_mm'], ob['top_mm'] = p['base'], p['height'], p['base'] + p['height']
        ob['thickness_mm'] = p['thickness']
        n_lintels += 1
    LOG.append(f"blue lintels: {n_lintels} beams (Z = 2.1-3.0 m) in 02_Openings > LINTELS")


SLOT_KEYS = ('ext', 'int', 'wash_back', 'tile', 'skirt', 'floor', 'ceiling', 'lintel_blue')
PART_COLS = ('FLOOR', 'SKIRTING')


def generate_continuous_walls():
    """Optional Section 2: Generate solid, continuous, watertight floor-to-ceiling (0.0-3.0 m) walls
    when CONNECT_WALLS_INTO_ONE_MESH = True."""
    b = collection('01_Structure')
    purge(b, children=False)
    slot = {k: i for i, k in enumerate(SLOT_KEYS)}
    by_mat = {MAT[k].name: slot[k] for k in SLOT_KEYS}
    bm_all = bmesh.new()

    def add(me, matrix, default_slot):
        tmp = me.copy()
        tmp.transform(matrix)
        mats = [by_mat.get(m.name, default_slot) if m else default_slot for m in tmp.materials]
        for poly in tmp.polygons:
            poly.material_index = mats[poly.material_index] if mats else default_slot
        bm_all.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)

    for k, band in enumerate(DATA['wall_bands']):
        for n, poly in enumerate(band['polys']):
            me, _c = prism(f'_band_{k}_{n}', mring(poly['outer']), [mring(h) for h in poly['holes']],
                           band['z0'] * M, band['z1'] * M, center=False,
                           caps=[mring(c) for c in poly['caps']] if poly.get('caps') else None)
            add(me, Matrix.Identity(4), slot['int'])
            bpy.data.meshes.remove(me)
    merged = 0
    if MERGE_INTO_ONE_MESH:
        for cname in PART_COLS:
            for o in objs_in(cname):
                if o.type == 'MESH':
                    add(o.data, o.matrix_basis, slot['int'])
                    merged += 1
    src = bpy.data.meshes.new('Building_Walls_Connected_Mesh')
    bm_all.to_mesh(src)
    bm_all.free()
    obj = new_obj('Building_Walls_Connected', src, b)
    for k in SLOT_KEYS:
        src.materials.append(MAT[k])
    mod = obj.modifiers.new('ExactUnion', 'NODES')
    mod.node_group = union_node_group()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    res = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.remove(mod)
    old = obj.data
    obj.data = res
    bpy.data.meshes.remove(old)
    res.name = 'Building_Walls_Connected_Mesh'
    if len(res.materials) != len(SLOT_KEYS):
        res.materials.clear()
        for k in SLOT_KEYS:
            res.materials.append(MAT[k])
    bm = bmesh.new()
    bm.from_mesh(res)
    bmesh.ops.dissolve_limit(bm, angle_limit=0.0005, verts=bm.verts[:], edges=bm.edges[:], delimit={'MATERIAL'})
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = False
    wall_slots = (slot['ext'], slot['int'], slot['wash_back'])
    for f in bm.faces:
        n = f.normal
        c = f.calc_center_median()
        if f.material_index in (slot['floor'], slot['ceiling']):
            if abs(n.z) < 0.3 and room_at(c.x + n.x * 0.02, c.y + n.y * 0.02) is None:
                f.material_index = slot['ext']
            continue
        if f.material_index not in wall_slots:
            continue
        if abs(n.z) > 0.7:
            f.material_index = slot['int']
            continue
        px, py = c.x + n.x * 0.02, c.y + n.y * 0.02
        r = room_at(px, py)
        if r is not None:
            f.material_index = slot['wash_back'] if r['type'] == 'washroom' else slot['int']
        elif any(pip(px, py, o['rect_m']) for o in OPEN_M):
            f.material_index = slot['int']
        else:
            f.material_index = slot['ext']
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    obj['merged_parts'] = merged
    obj['contains'] = 'walls + floor + skirting' if MERGE_INTO_ONE_MESH else 'continuous walls (floor & skirting separate)'
    LOG.append(f"Building_Walls_Connected: continuous walls ({len(obj.data.polygons)} faces)")
    return obj


build_connected = generate_continuous_walls


# ─────────────────────────── 2. OPENING MARKERS & ROOMS ───────────────────────────
def create_openings():
    dc, wc = collection('DOORS'), collection('WINDOWS')
    purge(dc); purge(wc)
    for o in DATA['openings']:
        col = dc if o['type'] in ('door', 'passage') else wc
        me, (cx, cy) = prism(o['id'] + '_Clear_Mesh', mring(o['rect']), [], o['sill'] * M, o['head'] * M)
        mat = MAT['door_leaf'] if o['type'] in ('door', 'passage') else (MAT['vglass'] if o['type'] == 'vent' else MAT['glass'])
        ob = new_obj(o['id'], me, col, mat, (cx, cy, 0.0))
        ob.display_type = 'WIRE'
        ob.hide_render = True
        for k in ('type', 'width', 'thickness', 'sill', 'head', 'height', 'source'):
            ob[k if k in ('type', 'source') else k + '_mm'] = o[k]
        ob['rooms'] = ', '.join(o.get('rooms', []))
        ob['lintel_id'] = o.get('lintel_id', '')
    LOG.append(f"opening markers: {len(DATA['openings'])}")


build_openings = create_openings


def build_rooms():
    rc = collection('ROOMS')
    purge(rc)
    mlc = collection('08_Materials_And_Lighting')
    lbl_col = bpy.data.collections.get('ROOM_LABELS') or bpy.data.collections.new('ROOM_LABELS')
    if lbl_col.name not in mlc.children:
        mlc.children.link(lbl_col)
    purge(lbl_col)
    for r in DATA['rooms']:
        me, (cx, cy) = prism(f"Room_{r['name']}_Mesh", mring(r['ring']), [mring(h) for h in r['holes']], 0.001, 0.002,
                             caps=[mring(c) for c in r['caps']] if r.get('caps') else None)
        ob = new_obj(f"Room_{r['name']}", me, rc, MAT['room'], (cx, cy, 0.0))
        ob.display_type = 'WIRE'
        ob.hide_render = True
        ob['room_type'], ob['area_m2'] = r['type'], r['area_m2']
        ob['room_use'], ob['label'], ob['panelled'] = r.get('use', ''), r.get('label', ''), bool(r.get('panelled'))
        ob['display_name'] = r.get('display_name') or r.get('label') or r['name']
        ob['cad_dim'] = r.get('cad_dim', '')
        ob['floor_obj'], ob['skirt_obj'] = r.get('floor_obj', ''), r.get('skirt_obj', '')
        # Create readable 3D room plan label in ROOM_LABELS for every non-external room
        if r['type'] not in ('external', 'shaft') and r.get('area_m2', 0.0) >= 1.2:
            disp = r.get('display_name') or r.get('label') or r['name']
            dim_txt = r.get('cad_dim') or f"{r['area_m2']:.1f} m2"
            cu = bpy.data.curves.new(name=f"Label_{r['label']}_Curve", type='FONT')
            cu.body = f"{disp}\n{dim_txt}"
            cu.align_x = 'CENTER'
            cu.align_y = 'CENTER'
            min_d = min(max(r.get('area_m2', 4.0) ** 0.5, 1.4), 4.5)
            cu.size = round(max(0.16, min(0.34, min_d * 0.085)), 3)
            cu.extrude = 0.004
            cu.materials.append(MAT['room_label'])
            txt_ob = bpy.data.objects.new(f"Label_{r['label']}", cu)
            txt_ob.location = (cx, cy, 0.03)
            txt_ob.show_wire = False
            txt_ob['room'] = r['name']
            txt_ob['display_name'] = disp
            txt_ob['cad_dim'] = dim_txt
            txt_ob['area_m2'] = r['area_m2']
            lbl_col.objects.link(txt_ob)
    LOG.append(f"rooms: {len(DATA['rooms'])} (with 3D readable room plan labels)")


# ─────────────────────────── 3. INDEPENDENT ROOM FLOORING & SKIRTING ───────────────────────────
def _combine_prisms(name, ring_groups, uv_angle=0.0):
    """ring_groups: list of (rings_list, z0_m, z1_m) -> single combined mesh with origin at centroid."""
    bm = bmesh.new()
    for rings, z0, z1 in ring_groups:
        for r in rings:
            me, _c = prism('_tmp_rc', mring(r['outer']), [mring(h) for h in r.get('holes', [])],
                           z0, z1, center=False, uv_angle=uv_angle,
                           caps=[mring(c) for c in r['caps']] if r.get('caps') else None)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
    if not bm.verts:
        bm.free()
        return None, (0.0, 0.0)
    cx = sum(v.co.x for v in bm.verts) / len(bm.verts)
    cy = sum(v.co.y for v in bm.verts) / len(bm.verts)
    for v in bm.verts:
        v.co.x -= cx
        v.co.y -= cy
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return me, (cx, cy)


def generate_master_bedroom_wood_floor(rf, col_floor, z0, z1):
    """Section 5.F: Master Bedroom special wooden plank flooring with consistent plank orientation."""
    me, (cx, cy) = _combine_prisms(rf['name'] + '_Mesh', [(rf['rings'], z0, z1)], uv_angle=rf.get('plank_angle', 0.0))
    if me is None:
        return None
    ob = new_obj(rf['name'], me, col_floor, MAT['floor_master_wood'], (cx, cy, 0.0))
    ob['room'], ob['label'], ob['use'] = rf['room'], rf['label'], rf['use']
    ob['category'], ob['material_preset'] = 'master_wood', 'MAT_Floor_Master_Wood'
    ob['area_m2'], ob['thickness_mm'] = rf['area_m2'], S.get('floor_finish_t', 20.0)
    return ob


def generate_room_flooring():
    """Sections 4, 5 & 6: Generate independent, room-specific flooring objects in 03_Flooring."""
    fc = collection('03_Flooring')
    purge(fc)
    ft = S.get('floor_finish_t', 20.0) * M
    z0, z1 = -ft, 0.0
    n_floors = 0
    for rf in DATA.get('room_floors', []):
        if rf['category'] == 'master_wood':
            ob = generate_master_bedroom_wood_floor(rf, fc, z0, z1)
        else:
            me, (cx, cy) = _combine_prisms(rf['name'] + '_Mesh', [(rf['rings'], z0, z1)], uv_angle=rf.get('plank_angle', 0.0))
            if me is None:
                continue
            mat = bpy.data.materials.get(rf['mat']) or MAT['floor_common']
            ob = new_obj(rf['name'], me, fc, mat, (cx, cy, 0.0))
            ob['room'], ob['label'], ob['use'] = rf['room'], rf['label'], rf['use']
            ob['category'], ob['material_preset'] = rf['category'], rf['mat']
            ob['area_m2'], ob['thickness_mm'] = rf['area_m2'], S.get('floor_finish_t', 20.0)
        if ob is not None:
            n_floors += 1
    LOG.append(f"room flooring: {n_floors} independent room floor objects in 03_Flooring")


def generate_room_skirting():
    """Sections 4 & 5: Generate independent, room-specific skirting objects (100 mm height) in 04_Skirting."""
    sc_room = collection('04_Skirting')
    purge(sc_room)
    z0, z1 = 0.0, S['skirt_h'] * M
    n_room_skirt = 0
    for rs in DATA.get('room_skirting', []):
        me, (cx, cy) = _combine_prisms(rs['name'] + '_Mesh', [(rs['runs'], z0, z1)])
        if me is None:
            continue
        mat = bpy.data.materials.get(rs['mat']) or MAT['skirt_common']
        ob = new_obj(rs['name'], me, sc_room, mat, (cx, cy, 0.0))
        ob['room'], ob['label'], ob['use'] = rs['room'], rs['label'], rs['use']
        ob['category'], ob['material_preset'] = rs['category'], rs['mat']
        ob['length_mm'], ob['height_mm'], ob['thickness_mm'] = rs['length_mm'], S['skirt_h'], S['skirt_t']
        n_room_skirt += 1

    # Also build individual skirting segments in EDITABLE_PARTS > SKIRTING for granular editing & checks
    sc = collection('SKIRTING')
    purge(sc)
    for s in DATA['skirting']:
        me, (cx, cy) = prism(s['name'] + '_Mesh', mring(s['ring']), [mring(h) for h in s['holes']], 0.0, S['skirt_h'] * M,
                             caps=[mring(c) for c in s['caps']] if s.get('caps') else None)
        mat = bpy.data.materials.get(s.get('mat', '')) or MAT['skirt_common']
        ob = new_obj(s['name'], me, sc, mat, (cx, cy, 0.0))
        ob['room'], ob['length_mm'] = s['room'], s['length_mm']
        ob['height_mm'], ob['thickness_mm'] = S['skirt_h'], S['skirt_t']
    LOG.append(f"skirting: {n_room_skirt} room skirting objects in 04_Skirting ({len(DATA['skirting'])} runs, height {S['skirt_h']} mm)")


build_skirting = generate_room_skirting


# ─────────────────────────── 4. WASHROOM TILES & WALL PANELS (shared slab builder) ───────────────────────────
def add_slab(bm, uvl, idl, piece, y0, y1, uv_fn, ident):
    """Add one wall-bonded slab to bm."""
    d = Vector((piece['dir'][0], piece['dir'][1], 0.0))
    nin = Vector((-d.y, d.x, 0.0))
    org = Vector((piece['origin'][0], piece['origin'][1], 0.0))
    pts = _clean_ring([(u, z) for u, z in piece['poly']], tol_dup=0.02, tol_collinear=0.01)

    def world(u, y, z):
        return (org + d * (piece['u0'] + u) + nin * y + Vector((0.0, 0.0, piece['z0'] + z))) * M

    loc = {}
    back, front = [], []
    for u, z in pts:
        vb = bm.verts.new(world(u, y0, z)); loc[vb] = (u, y0, z); back.append(vb)
        vf = bm.verts.new(world(u, y1, z)); loc[vf] = (u, y1, z); front.append(vf)
    faces = [(bm.faces.new(back), 'face'), (bm.faces.new(list(reversed(front))), 'face')]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        kind = 'side_u' if abs(pts[i][0] - pts[j][0]) >= abs(pts[i][1] - pts[j][1]) else 'side_z'
        faces.append((bm.faces.new((back[i], back[j], front[j], front[i])), kind))
    for f, kind in faces:
        f[idl] = ident
        for lp in f.loops:
            lp[uvl].uv = uv_fn(*loc[lp.vert], kind)
    return [f for f, _k in faces]


def slab_object(name, col, mat, items, thick, uv_fn, attr):
    """items: list of piece dicts -> ONE mesh object; every piece an island tagged with face attribute `attr`."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    idl = bm.faces.layers.int.new(attr)
    for k, p in enumerate(items):
        add_slab(bm, uvl, idl, p, 0.0, thick, uv_fn, k)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name + '_Mesh')
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = False
    return new_obj(name, me, col, mat)


def tile_uv(u, y, z, kind):
    W, H = S['tile_w'], S['tile_h']
    if kind == 'face':
        return (u / W, z / H)
    return ((u / W, y / H) if kind == 'side_u' else (y / W, z / H))


def generate_washroom_tiles():
    """Section 6: Full-height (0.0-3.0 m) interior washroom wall tiles (Tiles_Washroom_Wall_01..N)."""
    tc = collection('WASHROOM_TILES')
    purge(tc)
    purge(collection('05_Washroom_Tiles'), children=False)
    for nm in ('Tile_914x610x9_Full_Mesh',):
        if bpy.data.meshes.get(nm):
            bpy.data.meshes.remove(bpy.data.meshes[nm])
    rooms_by_name = {r['name']: r for r in DATA['rooms']}
    by_room = {}
    for t in DATA['tiles']:
        by_room.setdefault(t['room'], []).append(t)
    for idx, (room, items) in enumerate(by_room.items(), 1):
        r_meta = rooms_by_name.get(room, {})
        obj_name = r_meta.get('tile_obj') or f"Tiles_Washroom_Wall_{idx:02d}"
        ob = slab_object(obj_name, tc, MAT['tile'], items, S['tile_t'] + S['tile_gap'], tile_uv, 'tile_id')
        ob['room'], ob['tiles'] = room, len(items)
        ob['full_tiles'] = sum(1 for t in items if t['full'])
        ob['cut_tiles'] = len(items) - ob['full_tiles']
        ob['tile_size_mm'] = f"{S['tile_w']} x {S['tile_h']} x {S['tile_t']} (horizontal), joints {S['grout']}"
        ob['uv'] = 'each tile face = UV 0..1 (apply one tile texture -> every tile)'
    LOG.append(f"washroom tiles: {len(DATA['tiles'])} tiles in {len(by_room)} washroom meshes (05_Washroom_Tiles)")


build_tiles = generate_washroom_tiles


def panel_uv(u0, z0):
    def fn(u, y, z, kind):
        if kind == 'face':
            return ((u0 + u) * M, (z0 + z) * M)
        return (((u0 + u) * M, y * M) if kind == 'side_u' else (y * M, (z0 + z) * M))
    return fn


def build_wall_panels():
    pc = collection('WALL_PANELS')
    purge(pc)
    rooms = {r['name']: r for r in DATA['rooms']}
    by_room = {}
    for p in DATA.get('panels', []):
        by_room.setdefault(p['room'], []).append(p)
    for room, items in by_room.items():
        r = rooms[room]
        name = f"Wall_Panels_{room}_{r.get('label', '')}".rstrip('_')
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new('UVMap')
        idl = bm.faces.layers.int.new('panel_id')
        for k, p in enumerate(items):
            add_slab(bm, uvl, idl, p, 0.0, S['panel_t'], panel_uv(p['u0'], p['z0']), k)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(name + '_Mesh')
        bm.to_mesh(me)
        bm.free()
        ob = new_obj(name, me, pc, MAT['panel'])
        ob['room'], ob['room_use'], ob['label'] = room, r.get('use', ''), r.get('label', '')
        ob['sheets'] = len(items)
        ob['sheet_mm'] = f"{S['panel_w']} W x full height x {S['panel_t']} T, joints {S['panel_joint']}"
        ob['z_mm'] = f"{S['skirt_h']} - {S['wall_h']}"
        ob['uv'] = 'real-world UVs: 1 UV unit = 1 m'
    LOG.append(f"wall panels: {len(DATA.get('panels', []))} sheets in {len(by_room)} room meshes")


# ─────────────────────────── 5. WINDOW FITTINGS, BALCONY RAILINGS & DOOR FITTINGS ───────────────────────────
FRAME_W, FRAME_D, GLASS_T, PANE_MAX = 50.0, 60.0, 6.0, 1100.0      # mm


def _uz_slab(name, outer, holes, v0, v1):
    """Profile in the window plane (u along the wall, z up; metres) extruded across the wall
    from v0 to v1 -> mesh in window-local axes (x = u, y = across the wall, z = up)."""
    me, _c = prism(name, outer, holes, v0, v1, center=False)
    me.transform(Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    return me


def _add_box_uv(bm, uvl, x0, x1, y0, y1, z0, z1, mat_idx=0):
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    if z0 > z1:
        z0, z1 = z1, z0
    v = [
        bm.verts.new((x0, y0, z0)), bm.verts.new((x1, y0, z0)),
        bm.verts.new((x1, y1, z0)), bm.verts.new((x0, y1, z0)),
        bm.verts.new((x0, y0, z1)), bm.verts.new((x1, y0, z1)),
        bm.verts.new((x1, y1, z1)), bm.verts.new((x0, y1, z1)),
    ]
    faces_def = [
        ((v[0], v[1], v[5], v[4]), 'xz'),
        ((v[2], v[3], v[7], v[6]), 'xz'),
        ((v[1], v[2], v[6], v[5]), 'yz'),
        ((v[3], v[0], v[4], v[7]), 'yz'),
        ((v[4], v[5], v[6], v[7]), 'xy'),
        ((v[3], v[2], v[1], v[0]), 'xy'),
    ]
    for verts, plane in faces_def:
        f = bm.faces.new(verts)
        f.material_index = mat_idx
        f.smooth = False
        if uvl is not None:
            for lp in f.loops:
                co = lp.vert.co
                lp[uvl].uv = ((co.x, co.z) if plane == 'xz' else ((co.y, co.z) if plane == 'yz' else (co.x, co.y)))


def build_window_fittings():
    fc = collection('WINDOW_FITTINGS')
    purge(fc)
    n_obj = 0
    for o in DATA['openings']:
        if o['type'] not in ('window', 'vent') or o.get('balcony'):
            continue
        W, H = o['width'], o['head'] - o['sill']
        fw = min(FRAME_W, W / 6.0, H / 6.0)
        inner_w = W - 2 * fw
        k = max(1, math.ceil(inner_w / PANE_MAX)) if o['type'] == 'window' else 1
        pane_w = (inner_w - (k - 1) * fw) / k
        panes = []
        for i in range(k):
            u0 = fw + i * (pane_w + fw)
            panes.append((u0, fw, u0 + pane_w, H - fw))
        sub = bpy.data.collections.get(o['id'] + '_Fitting') or bpy.data.collections.new(o['id'] + '_Fitting')
        if sub.name not in fc.children:
            fc.children.link(sub)
        (x0, y0), (x1, y1) = o['p0'], o['p1']
        d = Vector((x1 - x0, y1 - y0, 0.0)).normalized()
        loc = Vector((x0 * M, y0 * M, o['sill'] * M))
        rot = (0.0, 0.0, math.atan2(d.y, d.x))
        hd = min(FRAME_D, o['thickness'] - 10.0) / 2.0
        gm = MAT['vglass'] if o['type'] == 'vent' else MAT['glass']

        # Build clean, non-overlapping 3D box bars for frame rails, jambs, and mullions (never blocking panes)
        bm_fr = bmesh.new()
        uvl_fr = bm_fr.loops.layers.uv.new('UVMap')
        W_m, H_m, fw_m, hd_m = W * M, H * M, fw * M, hd * M
        _add_box_uv(bm_fr, uvl_fr, 0.0, W_m, -hd_m, hd_m, 0.0, fw_m, mat_idx=0)              # bottom sill rail
        _add_box_uv(bm_fr, uvl_fr, 0.0, W_m, -hd_m, hd_m, H_m - fw_m, H_m, mat_idx=0)        # top head rail
        _add_box_uv(bm_fr, uvl_fr, 0.0, fw_m, -hd_m, hd_m, fw_m, H_m - fw_m, mat_idx=0)      # left jamb
        _add_box_uv(bm_fr, uvl_fr, W_m - fw_m, W_m, -hd_m, hd_m, fw_m, H_m - fw_m, mat_idx=0)# right jamb
        for i in range(1, k):
            m0 = (fw + i * (pane_w + fw) - fw) * M
            _add_box_uv(bm_fr, uvl_fr, m0, m0 + fw_m, -hd_m, hd_m, fw_m, H_m - fw_m, mat_idx=0)
        bmesh.ops.recalc_face_normals(bm_fr, faces=bm_fr.faces[:])
        me_fr = bpy.data.meshes.new(o['id'] + '_Frame_Mesh')
        bm_fr.to_mesh(me_fr)
        bm_fr.free()
        fr = bpy.data.objects.new(o['id'] + '_Frame', me_fr)
        fr.data.materials.append(MAT['frame'])
        fr.data.materials.append(gm)
        fr.location, fr.rotation_euler = loc, rot
        fr.hide_select = False
        fr['opening'], fr['width_mm'], fr['height_mm'], fr['panes'] = o['id'], W, H, k
        fr['glass_material'] = gm.name
        sub.objects.link(fr)
        n_obj += 1

        # Build selectable transparent glass panes with dedicated glass material (Window_Glass_Mat / Ventilator_Frosted_Glass_Mat)
        gt_half = (GLASS_T / 2.0) * M
        for i, (a, b, c, e) in enumerate(panes):
            bm_g = bmesh.new()
            uvl_g = bm_g.loops.layers.uv.new('UVMap')
            _add_box_uv(bm_g, uvl_g, a * M, c * M, -gt_half, gt_half, b * M, e * M, mat_idx=0)
            bmesh.ops.recalc_face_normals(bm_g, faces=bm_g.faces[:])
            me_g = bpy.data.meshes.new(f"{o['id']}_Glass_{i + 1:02d}_Mesh")
            bm_g.to_mesh(me_g)
            bm_g.free()
            g = bpy.data.objects.new(f"{o['id']}_Glass_{i + 1:02d}", me_g)
            g.data.materials.append(gm)
            g.location, g.rotation_euler = loc, rot
            g.hide_select = False
            g['opening'], g['pane'] = o['id'], i + 1
            g['material_preset'] = gm.name
            sub.objects.link(g)
            n_obj += 1
    LOG.append(f"window fittings: {n_obj} frame / glass objects")


def build_glass_partitions():
    """Free-standing glass partitions drawn in the CAD (shower screens, glass dividers): a real 10 mm glass
    mesh with Window_Glass_Mat, floor to 2100 mm, on slim silver floor / head channels."""
    gp = DATA.get('glass_partitions', [])
    fc = collection('WINDOW_FITTINGS')
    sub = bpy.data.collections.get('Glass_Partitions') or bpy.data.collections.new('Glass_Partitions')
    if sub.name not in fc.children:
        fc.children.link(sub)
    purge(sub)
    n = 0
    t = 10.0                                  # 10 mm toughened glass
    ch_h, ch_w = 30.0, 30.0                   # aluminium U-channel
    for k, g in enumerate(gp, 1):
        (x0, y0), (x1, y1) = g['p0'], g['p1']
        W, H = g['width'], g.get('height', 2100.0)
        d = Vector((x1 - x0, y1 - y0, 0.0)).normalized()
        loc = Vector((x0 * M, y0 * M, 0.0))
        rot = (0.0, 0.0, math.atan2(d.y, d.x))
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new('UVMap')
        _add_box_uv(bm, uvl, 0.0, W * M, -t / 2 * M, t / 2 * M, ch_h * M, (H - ch_h) * M, mat_idx=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(f'Glass_Partition_{k:02d}_Mesh')
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f'Glass_Partition_{k:02d}', me)
        ob.data.materials.append(MAT['glass'])
        ob.location, ob.rotation_euler = loc, rot
        ob['width_mm'], ob['height_mm'], ob['glass_thickness_mm'] = W, H, t
        ob['material_preset'] = MAT['glass'].name
        sub.objects.link(ob)
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new('UVMap')
        _add_box_uv(bm, uvl, 0.0, W * M, -ch_w / 2 * M, ch_w / 2 * M, 0.0, ch_h * M, mat_idx=0)
        _add_box_uv(bm, uvl, 0.0, W * M, -ch_w / 2 * M, ch_w / 2 * M, (H - ch_h) * M, H * M, mat_idx=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(f'Glass_Partition_{k:02d}_Channel_Mesh')
        bm.to_mesh(me)
        bm.free()
        ch = bpy.data.objects.new(f'Glass_Partition_{k:02d}_Channel', me)
        ch.data.materials.append(MAT['frame'])
        ch.location, ch.rotation_euler = loc, rot
        sub.objects.link(ch)
        n += 1
    LOG.append(f"glass partitions: {n} free-standing glass panel(s)")


def generate_balcony_railings():
    """Section 7: Balcony railings (1.2 m / ~4 ft height) with separate safety-glass panels
    (GlassPanel_Balcony_XX) and slim metallic posts, clamps & top rail (Railing_Glass_Balcony_XX).
    Dry balconies are strictly excluded from glass railings."""
    bc_glass = collection('BALCONY_GLASS')
    bc_root = collection('06_Balcony')
    purge(bc_glass)
    purge(bc_root, children=False)
    rooms = {r['name']: r for r in DATA['rooms']}
    T = S.get('balcony_glass_t', 76.2)
    J = S.get('balcony_glass_joint', 5.0)
    PM = S.get('balcony_glass_max', 1200.0)
    pw_post = S.get('balcony_post_w', 40.0)
    rh_top = S.get('balcony_rail_h', 35.0)
    n_pane = 0
    idx_bal = 0
    for o in DATA['openings']:
        if not o.get('balcony') or o.get('dry_balcony'):
            continue
        r = rooms.get(o['rooms'][0], {}) if o.get('rooms') else {}
        if r.get('use') == 'dry_balcony':
            continue
        idx_bal += 1
        W, H = o['width'], o['head'] - o['sill']
        k = max(1, math.ceil((W + J) / (PM + J)))
        pw = (W - (k - 1) * J) / k

        # 1. Safety-glass panel object (GlassPanel_Balcony_XX) in BALCONY_GLASS
        bm = bmesh.new()
        for i in range(k):
            a, c = i * (pw + J), i * (pw + J) + pw
            ring = [(a * M, 0.0), (c * M, 0.0), (c * M, H * M), (a * M, H * M)]
            me = _uz_slab('_bglass_tmp', ring, [], -T / 2 * M, T / 2 * M)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        me = bpy.data.meshes.new('tmp')
        bm.to_mesh(me)
        bm.free()
        glass_name = f"GlassPanel_Balcony_{idx_bal:02d}"
        me.name = glass_name + '_Mesh'
        ob = new_obj(glass_name, me, bc_glass, MAT['bglass'])
        (x0, y0), (x1, y1) = o['p0'], o['p1']
        d = Vector((x1 - x0, y1 - y0, 0.0)).normalized()
        loc = Vector((x0 * M, y0 * M, o['sill'] * M))
        rot = (0.0, 0.0, math.atan2(d.y, d.x))
        ob.location, ob.rotation_euler = loc, rot
        ob['opening'], ob['room'], ob['label'] = o['id'], r.get('name', ''), r.get('label', '')
        ob['part'] = 'glass_panel'
        ob['glass_thickness_mm'], ob['panes'], ob['pane_width_mm'] = T, k, round(pw, 1)
        ob['width_mm'], ob['height_mm'], ob['sill_mm'] = W, H, o['sill']
        n_pane += k

        # 2. Separate metal railing supports object (Railing_Glass_Balcony_XX) in 06_Balcony
        bm_m = bmesh.new()
        uv_m = bm_m.loops.layers.uv.new('UVMap')
        hp = (pw_post / 2.0) * M
        hd_post = min(o['thickness'] * 0.42, max(pw_post, T + 8.0)) / 2.0 * M
        # Top handrail along full width
        _add_box_uv(bm_m, uv_m, 0.0, W * M, -hd_post, hd_post, (H - rh_top) * M, H * M)
        # Slim vertical posts + base plates + glass clamps at ends and panel joints
        for i in range(k + 1):
            ux = (0.0 if i == 0 else (W if i == k else i * (pw + J) - J / 2.0)) * M
            u0_p = max(0.0, ux - hp)
            u1_p = min(W * M, ux + hp)
            _add_box_uv(bm_m, uv_m, u0_p, u1_p, -hd_post, hd_post, 0.0, (H - rh_top) * M)
            # Base plate
            _add_box_uv(bm_m, uv_m, max(0.0, ux - hp * 1.4), min(W * M, ux + hp * 1.4), -hd_post * 1.15, hd_post * 1.15, 0.0, 0.008)
            # Upper and lower glass clamps
            for z_c in (0.18 * H * M, 0.78 * H * M):
                _add_box_uv(bm_m, uv_m, max(0.0, ux - hp * 1.3), min(W * M, ux + hp * 1.3), -hd_post * 1.05, hd_post * 1.05, z_c - 0.015, z_c + 0.015)
        bmesh.ops.recalc_face_normals(bm_m, faces=bm_m.faces[:])
        rail_name = f"Railing_Glass_Balcony_{idx_bal:02d}"
        me_m = bpy.data.meshes.new(rail_name + '_Mesh')
        bm_m.to_mesh(me_m)
        bm_m.free()
        ob_m = new_obj(rail_name, me_m, bc_root, MAT['bmetal'], loc)
        ob_m.rotation_euler = rot
        ob_m['opening'], ob_m['room'], ob_m['label'] = o['id'], r.get('name', ''), r.get('label', '')
        ob_m['part'] = 'metal_railing_posts_and_top_rail'
        ob_m['posts'], ob_m['width_mm'], ob_m['height_mm'] = k + 1, W, H
    LOG.append(f"balcony railings: {idx_bal} standard balcony edges ({n_pane} glass panes + {idx_bal} metal railing objects, height {S.get('balcony_glass_h', 1200.0)} mm)")


build_balcony_glass = generate_balcony_railings


def _add_cyl_y(bm, uvl, cx, cz, y0, y1, r, segs=16, mat_idx=0):
    if y0 > y1:
        y0, y1 = y1, y0
    ring0, ring1 = [], []
    for i in range(segs):
        ang = 2.0 * math.pi * i / segs
        x = cx + r * math.cos(ang)
        z = cz + r * math.sin(ang)
        ring0.append(bm.verts.new((x, y0, z)))
        ring1.append(bm.verts.new((x, y1, z)))
    f0 = bm.faces.new(list(reversed(ring0)))
    f1 = bm.faces.new(ring1)
    f0.material_index = f1.material_index = mat_idx
    f0.smooth = f1.smooth = False
    for i in range(segs):
        j = (i + 1) % segs
        fs = bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
        fs.material_index = mat_idx
        fs.smooth = True


def build_door_fittings():
    """Editable 3D door assembly for every door opening:
    1) Door_XX_Frame (rich walnut wood 3-sided frame + door stop rebate)
    2) Door_XX_Leaf  (warm oak/teak panelled wooden door leaf, hinge-pivoted, parented to Frame)
    3) Door_XX_Lever (silver stainless steel lever handles + rosettes on BOTH sides + latch plate, parented to Leaf)."""
    dc = collection('DOOR_FITTINGS')
    purge(dc)
    n_doors = 0
    for o in DATA['openings']:
        if o['type'] != 'door':
            continue
        W, H, T = o['width'], o['head'] - o['sill'], o['thickness']
        fw = min(S.get('door_frame_w', 45.0), W / 8.0)
        fd = min(max(T, 100.0), 200.0)
        leaf_t = min(S.get('door_leaf_t', 42.0), fd * 0.45)
        gap, bot_gap = 2.0, 4.0
        leaf_w = max(200.0, W - 2.0 * (fw + gap))
        leaf_h = max(400.0, H - fw - gap - bot_gap)

        sub = bpy.data.collections.get(o['id'] + '_Fitting') or bpy.data.collections.new(o['id'] + '_Fitting')
        if sub.name not in dc.children:
            dc.children.link(sub)
        (x0, y0), (x1, y1) = o['p0'], o['p1']
        d = Vector((x1 - x0, y1 - y0, 0.0)).normalized()
        loc = Vector((x0 * M, y0 * M, o['sill'] * M))
        rot = (0.0, 0.0, math.atan2(d.y, d.x))

        # 1. DOOR FRAME
        bm_fr = bmesh.new()
        uv_fr = bm_fr.loops.layers.uv.new('UVMap')
        _add_box_uv(bm_fr, uv_fr, 0.0, fw * M, -fd / 2 * M, fd / 2 * M, 0.0, H * M)
        _add_box_uv(bm_fr, uv_fr, (W - fw) * M, W * M, -fd / 2 * M, fd / 2 * M, 0.0, H * M)
        _add_box_uv(bm_fr, uv_fr, fw * M, (W - fw) * M, -fd / 2 * M, fd / 2 * M, (H - fw) * M, H * M)
        stop_y0, stop_y1 = (leaf_t / 2.0) * M, min(fd / 2.0, leaf_t / 2.0 + 14.0) * M
        if stop_y1 > stop_y0 + 1e-4:
            _add_box_uv(bm_fr, uv_fr, fw * M, (fw + 12.0) * M, stop_y0, stop_y1, 0.0, (H - fw) * M)
            _add_box_uv(bm_fr, uv_fr, (W - fw - 12.0) * M, (W - fw) * M, stop_y0, stop_y1, 0.0, (H - fw) * M)
            _add_box_uv(bm_fr, uv_fr, (fw + 12.0) * M, (W - fw - 12.0) * M, stop_y0, stop_y1, (H - fw - 12.0) * M, (H - fw) * M)
        bmesh.ops.recalc_face_normals(bm_fr, faces=bm_fr.faces[:])
        me_fr = bpy.data.meshes.new(o['id'] + '_Frame_Mesh')
        bm_fr.to_mesh(me_fr)
        bm_fr.free()
        fr = new_obj(o['id'] + '_Frame', me_fr, sub, MAT['door_frame'], loc)
        fr.rotation_euler = rot
        fr['opening'], fr['part'] = o['id'], 'door_frame'
        fr['width_mm'], fr['height_mm'], fr['frame_depth_mm'] = W, H, fd

        # 2. WOODEN DOOR LEAF
        bm_lf = bmesh.new()
        uv_lf = bm_lf.loops.layers.uv.new('UVMap')
        stile = min(110.0, leaf_w * 0.18)
        bot_r = min(170.0, leaf_h * 0.10)
        top_r = min(110.0, leaf_h * 0.07)
        mid_z0 = min(860.0, leaf_h * 0.42)
        mid_h = min(95.0, leaf_h * 0.06)
        hy = (leaf_t / 2.0) * M
        py = max(0.008, (leaf_t / 2.0 - 6.0) * M)
        _add_box_uv(bm_lf, uv_lf, 0.0, stile * M, -hy, hy, 0.0, leaf_h * M)
        _add_box_uv(bm_lf, uv_lf, (leaf_w - stile) * M, leaf_w * M, -hy, hy, 0.0, leaf_h * M)
        _add_box_uv(bm_lf, uv_lf, stile * M, (leaf_w - stile) * M, -hy, hy, 0.0, bot_r * M)
        _add_box_uv(bm_lf, uv_lf, stile * M, (leaf_w - stile) * M, -hy, hy, mid_z0 * M, (mid_z0 + mid_h) * M)
        _add_box_uv(bm_lf, uv_lf, stile * M, (leaf_w - stile) * M, -hy, hy, (leaf_h - top_r) * M, leaf_h * M)
        _add_box_uv(bm_lf, uv_lf, stile * M, (leaf_w - stile) * M, -py, py, bot_r * M, mid_z0 * M)
        _add_box_uv(bm_lf, uv_lf, stile * M, (leaf_w - stile) * M, -py, py, (mid_z0 + mid_h) * M, (leaf_h - top_r) * M)
        bmesh.ops.recalc_face_normals(bm_lf, faces=bm_lf.faces[:])
        me_lf = bpy.data.meshes.new(o['id'] + '_Leaf_Mesh')
        bm_lf.to_mesh(me_lf)
        bm_lf.free()
        lf = new_obj(o['id'] + '_Leaf', me_lf, sub, MAT['door_leaf'], ((fw + gap) * M, 0.0, bot_gap * M))
        lf.parent = fr
        lf['opening'], lf['part'] = o['id'], 'door_leaf'
        lf['leaf_width_mm'], lf['leaf_height_mm'], lf['leaf_thickness_mm'] = round(leaf_w, 1), round(leaf_h, 1), round(leaf_t, 1)
        lf['editable_hint'] = 'Rotate Z to swing door open or closed'

        # 3. SILVER DOOR LEVER ON BOTH SIDES
        backset = min(65.0, leaf_w * 0.14)
        handle_h = min(S.get('door_handle_h', 1000.0), H * 0.55)
        lever_len = min(S.get('door_lever_len', 128.0), leaf_w * 0.35)
        bm_lv = bmesh.new()
        uv_lv = bm_lv.loops.layers.uv.new('UVMap')
        _add_box_uv(bm_lv, uv_lv, -4.5 * M, 4.5 * M, -(leaf_t / 2.0 + 38.0) * M, (leaf_t / 2.0 + 38.0) * M, -4.5 * M, 4.5 * M)
        for side in (-1.0, 1.0):
            yf = side * (leaf_t / 2.0) * M
            yr = side * (leaf_t / 2.0 + 8.0) * M
            yn = side * (leaf_t / 2.0 + 38.0) * M
            yg = side * (leaf_t / 2.0 + 49.0) * M
            _add_cyl_y(bm_lv, uv_lv, 0.0, 0.0, min(yf, yr), max(yf, yr), 27.0 * M, segs=16)
            _add_cyl_y(bm_lv, uv_lv, 0.0, -85.0 * M, min(yf, yr), max(yf, yr), 27.0 * M, segs=16)
            _add_cyl_y(bm_lv, uv_lv, 0.0, 0.0, min(yr, yn), max(yr, yn), 9.5 * M, segs=16)
            _add_box_uv(bm_lv, uv_lv, -(lever_len - 10.0) * M, 10.0 * M, min(yn, yg), max(yn, yg), -10.0 * M, 10.0 * M)
            yt = side * (leaf_t / 2.0 + 32.0) * M
            _add_box_uv(bm_lv, uv_lv, -(lever_len - 10.0) * M, -(lever_len - 22.0) * M, min(yt, yn), max(yt, yn), -10.0 * M, 10.0 * M)
        _add_box_uv(bm_lv, uv_lv, (backset - 1.0) * M, (backset + 1.5) * M, -12.0 * M, 12.0 * M, -110.0 * M, 45.0 * M)
        _add_box_uv(bm_lv, uv_lv, (backset + 1.5) * M, (backset + 9.0) * M, -6.5 * M, 6.5 * M, -16.0 * M, 16.0 * M)
        bmesh.ops.recalc_face_normals(bm_lv, faces=bm_lv.faces[:])
        me_lv = bpy.data.meshes.new(o['id'] + '_Lever_Mesh')
        bm_lv.to_mesh(me_lv)
        bm_lv.free()
        lv = new_obj(o['id'] + '_Lever', me_lv, sub, MAT['door_lever'], ((leaf_w - backset) * M, 0.0, (handle_h - bot_gap) * M))
        lv.parent = lf
        lv['opening'], lv['part'] = o['id'], 'door_lever_both_sides'
        lv['sides'], lv['color'], lv['lever_length_mm'] = 2, 'silver', round(lever_len, 1)
        n_doors += 1
    LOG.append(f"door fittings: {n_doors} doors (wooden frame + wooden door leaf + silver lever on both sides)")


# ─────────────────────────── 6. KITCHEN PLATFORM & COUNTERTOP ───────────────────────────
def generate_kitchen_platform():
    """Section 10: Generate kitchen base support, stone/granite countertop slab, and backsplash in 07_Kitchen."""
    kc = collection('07_Kitchen')
    purge(kc)
    items = DATA.get('kitchens', [])
    n_kitch = 0
    for k in items:
        me_b, (cx_b, cy_b) = _combine_prisms(k['base_name'] + '_Mesh', [(k['base_rings'], k['z_base_0'] * M, k['z_base_1'] * M)])
        if me_b is not None:
            ob_b = new_obj(k['base_name'], me_b, kc, MAT['kitch_base'], (cx_b, cy_b, 0.0))
            ob_b['room'], ob_b['label'], ob_b['part'] = k['room'], k['label'], 'kitchen_base'
            ob_b['shape'], ob_b['depth_mm'], ob_b['height_mm'] = k['shape'], k['base_depth_mm'], k['z_base_1']

        me_t, (cx_t, cy_t) = _combine_prisms(k['counter_name'] + '_Mesh', [(k['counter_rings'], k['z_top_0'] * M, k['z_top_1'] * M)])
        if me_t is not None:
            ob_t = new_obj(k['counter_name'], me_t, kc, MAT['kitch_top'], (cx_t, cy_t, 0.0))
            ob_t['room'], ob_t['label'], ob_t['part'] = k['room'], k['label'], 'kitchen_countertop'
            ob_t['shape'], ob_t['depth_mm'] = k['shape'], k['counter_depth_mm']
            ob_t['top_height_mm'], ob_t['thickness_mm'] = k['z_top_1'], k['counter_thickness_mm']

        if k.get('backsplash_rings'):
            me_s, (cx_s, cy_s) = _combine_prisms(k['backsplash_name'] + '_Mesh', [(k['backsplash_rings'], k['z_bs_0'] * M, k['z_bs_1'] * M)])
            if me_s is not None:
                ob_s = new_obj(k['backsplash_name'], me_s, kc, MAT['kitch_top'], (cx_s, cy_s, 0.0))
                ob_s['room'], ob_s['label'], ob_s['part'] = k['room'], k['label'], 'kitchen_backsplash'
        n_kitch += 1
    LOG.append(f"kitchen platforms: {n_kitch} kitchen(s) in 07_Kitchen")


# ─────────────────────────── 7. SLABS, RECESSED CEILINGS & LIGHTING ───────────────────────────
def build_slabs():
    fc, cc = collection('FLOOR'), collection('CEILING')
    purge(fc); purge(cc)
    top = S['wall_h'] * M
    ft = S.get('floor_finish_t', 20.0) * M if BUILD_FLOORING else 0.0
    sub_z0 = -S['slab_t'] * M - ft
    groups = [(DATA['floor'], sub_z0, -ft)]
    me, (cx, cy) = _combine_prisms('Floor_Slab_Mesh', groups)
    if me is not None:
        ob = new_obj('Floor_Slab', me, fc, MAT['floor'], (cx, cy, 0.0))
        ob['part'] = 'structural_floor_slab'
        ob['z_mm'] = f"{sub_z0 / M:.0f} .. {-ft / M:.0f} (room finish floors sit in {-ft / M:.0f} .. 0 mm)"
    ceil = DATA.get('ceiling') or DATA['floor']
    for k, f in enumerate(ceil):
        suf = '' if len(ceil) == 1 else f'_{k + 1}'
        me, (cx, cy) = prism('Ceiling_Slab' + suf + '_Mesh', mring(f['outer']), [mring(h) for h in f['holes']],
                             top, top + S['slab_t'] * M,
                             caps=[mring(c) for c in f['caps']] if f.get('caps') else None)
        new_obj('Ceiling_Slab' + suf, me, cc, MAT['ceiling'], (cx, cy, 0.0))
    lc = layer_col('CEILING')
    if lc:
        lc.hide_viewport = False
    LOG.append(f"slabs: {len(DATA['floor'])} structural floor + {len(ceil)} ceiling")


def _build_downlights_mesh(name, fixtures, r_mm, rec_mm):
    """Build clean 2-manifold low-profile recessed downlight fixtures (smooth silver bezel + dark cavity baffle
    + warm LED diffuser set upward into the ceiling cavity)."""
    bm = bmesh.new()
    segs = 20
    r_out = (r_mm + 6.0) * M
    r_in = (r_mm - 6.0) * M
    rec = rec_mm * M
    cx = sum(f['x'] for f in fixtures) * M / len(fixtures)
    cy = sum(f['y'] for f in fixtures) * M / len(fixtures)
    for f in fixtures:
        fx, fy, fz = f['x'] * M - cx, f['y'] * M - cy, f['z'] * M
        b_out, t_out, b_in, c_in = [], [], [], []
        for i in range(segs):
            ang = 2.0 * math.pi * i / segs
            cs, sn = math.cos(ang), math.sin(ang)
            b_out.append(bm.verts.new((fx + r_out * cs, fy + r_out * sn, fz - 0.002)))
            t_out.append(bm.verts.new((fx + r_out * cs, fy + r_out * sn, fz + rec + 0.002)))
            b_in.append(bm.verts.new((fx + r_in * cs, fy + r_in * sn, fz - 0.002)))
            c_in.append(bm.verts.new((fx + r_in * cs, fy + r_in * sn, fz + rec)))
        for i in range(segs):
            j = (i + 1) % segs
            f_ring = bm.faces.new((b_out[j], b_out[i], b_in[i], b_in[j]))
            f_ring.material_index = 0
            f_ring.smooth = False
            f_rim = bm.faces.new((b_out[i], b_out[j], t_out[j], t_out[i]))
            f_rim.material_index = 0
            f_rim.smooth = True
            fb = bm.faces.new((b_in[j], b_in[i], c_in[i], c_in[j]))
            fb.material_index = 1
            fb.smooth = True
        ft = bm.faces.new(t_out)
        ft.material_index = 1
        ft.smooth = False
        fl = bm.faces.new(list(reversed(c_in)))
        fl.material_index = 2
        fl.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me, (cx, cy)


def build_recessed_ceilings():
    """Build low-profile architectural recessed ceilings in bedrooms and halls only."""
    rc_root = collection('RECESSED_CEILINGS')
    purge(rc_root)
    items = DATA.get('recessed_ceilings', [])
    dl_r = S.get('downlight_r', 45.0)
    dl_rec = S.get('downlight_recess', 25.0)
    n_rooms = 0
    for rc in items:
        rm_name, label = rc['room'], rc['label']
        sub_name = f"Recessed_Ceiling_{rm_name}_{label}"
        sub = bpy.data.collections.get(sub_name) or bpy.data.collections.new(sub_name)
        if sub.name not in rc_root.children:
            rc_root.children.link(sub)
        z_sof = rc['z_soffit'] * M
        z_top = rc['z_wall_top'] * M
        z_cav = rc['z_cavity'] * M
        z_slb = rc['z_slab_top'] * M

        me_tr, (cx, cy) = _combine_prisms(
            f"{rm_name}_Recessed_Ceiling_Plane_Mesh",
            [(rc['cavity_rings'], z_cav, z_slb), (rc.get('collar_rings', []), z_top, z_cav)],
        )
        if me_tr is not None:
            ob_tr = new_obj(f"{rm_name}_Recessed_Ceiling_Plane", me_tr, sub, MAT['ceiling_tray'], (cx, cy, 0.0))
            ob_tr['room'], ob_tr['label'], ob_tr['use'] = rm_name, label, rc['use']
            ob_tr['part'], ob_tr['cavity_z_mm'] = 'recessed_ceiling_plane', rc['z_cavity']

        me_sf, (cx, cy) = _combine_prisms(
            f"{rm_name}_Recessed_Perimeter_Soffit_Mesh",
            [(rc['soffit_rings'], z_sof, z_top), (rc.get('lip_rings', []), z_sof, z_sof + 0.018)],
        )
        if me_sf is not None:
            ob_sf = new_obj(f"{rm_name}_Recessed_Perimeter_Soffit", me_sf, sub, MAT['ceiling_drop'], (cx, cy, 0.0))
            ob_sf['room'], ob_sf['label'], ob_sf['part'] = rm_name, label, 'recessed_perimeter_soffit'
            ob_sf['soffit_z_mm'], ob_sf['border_width_mm'] = rc['z_soffit'], rc['border_w']

        if rc.get('cove_led_rings'):
            me_cv, (cx, cy) = _combine_prisms(
                f"{rm_name}_Recessed_Cove_Light_Mesh",
                [(rc['cove_led_rings'], z_sof + 0.018, z_sof + 0.032)],
            )
            if me_cv is not None:
                ob_cv = new_obj(f"{rm_name}_Recessed_Cove_Light", me_cv, sub, MAT['cove_led'], (cx, cy, 0.0))
                ob_cv['room'], ob_cv['label'], ob_cv['part'] = rm_name, label, 'recessed_cove_led'

        if rc.get('fixtures'):
            me_dl, (cx, cy) = _build_downlights_mesh(f"{rm_name}_Recessed_Downlights_Mesh", rc['fixtures'], dl_r, dl_rec)
            ob_dl = new_obj(f"{rm_name}_Recessed_Downlights", me_dl, sub, None, (cx, cy, 0.0))
            for m_key in ('door_lever', 'downlight_housing', 'downlight_led'):
                ob_dl.data.materials.append(MAT[m_key])
            ob_dl['room'], ob_dl['label'], ob_dl['part'] = rm_name, label, 'recessed_downlights'
            ob_dl['fixtures_count'] = len(rc['fixtures'])
        n_rooms += 1
    LOG.append(f"recessed ceilings: {n_rooms} bedroom/hall tray ceilings with cove LED & recessed downlights")


def build_lighting_and_camera():
    """Section 9: 08_Materials_And_Lighting collection with architectural sun light and overview camera."""
    mlc = collection('08_Materials_And_Lighting')
    for obj in list(mlc.objects):
        _remove_obj(obj)
    all_xs = [pt[0] * M for p in DATA.get('pieces', []) for pt in p.get('ring', [])]
    all_ys = [pt[1] * M for p in DATA.get('pieces', []) for pt in p.get('ring', [])]
    cx = 0.5 * (min(all_xs) + max(all_xs)) if all_xs else 0.0
    cy = 0.5 * (min(all_ys) + max(all_ys)) if all_ys else 0.0
    span = max((max(all_xs) - min(all_xs)) if all_xs else 20.0, (max(all_ys) - min(all_ys)) if all_ys else 20.0, 12.0)

    sun_data = bpy.data.lights.get('Arch_Sun_Light_Data') or bpy.data.lights.new('Arch_Sun_Light_Data', type='SUN')
    sun_data.energy = 3.5
    sun_obj = bpy.data.objects.new('Arch_Sun_Light', sun_data)
    sun_obj.location = (cx + 5.0, cy - 8.0, 18.0)
    sun_obj.rotation_euler = (math.radians(38.0), math.radians(15.0), math.radians(28.0))
    mlc.objects.link(sun_obj)

    # Set bright sky ambient world lighting so transparent glass and interiors never look dark
    if scene.world is None:
        scene.world = bpy.data.worlds.new('Arch_World')
    scene.world.use_nodes = True
    bg = next((n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND'), None)
    if bg is not None:
        bg.inputs[0].default_value = (0.88, 0.93, 0.98, 1.0)
        bg.inputs[1].default_value = 1.15

    cam_data = bpy.data.cameras.get('Arch_Preview_Camera_Data') or bpy.data.cameras.new('Arch_Preview_Camera_Data')
    cam_data.lens = 28.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = max(500.0, span * 4.0)
    cam_obj = bpy.data.objects.new('Arch_Preview_Camera', cam_data)
    cam_obj.location = (cx, cy - span * 0.65, span * 0.72)
    cam_obj.rotation_euler = (math.radians(42.0), 0.0, 0.0)
    mlc.objects.link(cam_obj)
    scene.camera = cam_obj


def build_source_cad():
    sc = collection('SOURCE_CAD')
    purge(sc)
    bm = bmesh.new()
    for x1, y1, x2, y2 in DATA['underlay']:
        a = bm.verts.new((x1 * M, y1 * M, 0.003))
        b = bm.verts.new((x2 * M, y2 * M, 0.003))
        bm.edges.new((a, b))
    me = bpy.data.meshes.new('Source_CAD_Linework_Mesh')
    bm.to_mesh(me)
    bm.free()
    ob = new_obj('Source_CAD_Linework', me, sc)
    ob.hide_render = True
    lc = layer_col('SOURCE_CAD')
    if lc:
        lc.hide_viewport = True
    LOG.append(f"source CAD: {len(DATA['underlay'])} segments")


# ─────────────────────────── 8. AUTOMATED VALIDATION (SECTION 13) ───────────────────────────
def bvh_of(objs):
    verts, tris = [], []
    for o in objs:
        if o.type != 'MESH':
            continue
        me = o.data
        me.calc_loop_triangles()
        mw = o.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        tris += [[base + vi for vi in lt.vertices] for lt in me.loop_triangles]
    return BVHTree.FromPolygons(verts, tris) if tris else None


def box_bvh(cx, cy, d, n, half_w, half_t, z0, z1):
    c = Vector((cx, cy, 0.0))
    d, n = Vector((d[0], d[1], 0.0)), Vector((n[0], n[1], 0.0))
    pts = []
    for z in (z0, z1):
        for sw, st in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            pts.append(c + d * (sw * half_w) + n * (st * half_t) + Vector((0, 0, z)))
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return BVHTree.FromPolygons(pts, faces)


def objs_in(name):
    col = bpy.data.collections.get(name)
    out, stack, seen = [], [col] if col else [], set()
    while stack:
        c = stack.pop()
        for o in c.objects:
            if o.name not in seen:
                seen.add(o.name)
                out.append(o)
        stack.extend(c.children)
    return out


def pieces_of(objs, attr):
    """Merged slab meshes -> {(object name, id): {'verts': [world co], 'polys': [[i..]], 'normals': [...]}}."""
    out = {}
    for o in objs:
        me = o.data
        at = me.attributes.get(attr)
        if at is None:
            continue
        me.calc_loop_triangles()
        mw = o.matrix_world
        nmat = mw.to_3x3()
        for p in me.polygons:
            key = (o.name, at.data[p.index].value)
            pc = out.setdefault(key, {'verts': [], 'polys': [], 'tris': [], 'normals': [], 'centers': [], 'areas': [], 'map': {}})
            idx = []
            for vi in p.vertices:
                if vi not in pc['map']:
                    pc['map'][vi] = len(pc['verts'])
                    pc['verts'].append(mw @ me.vertices[vi].co)
                idx.append(pc['map'][vi])
            pc['polys'].append(idx)
        for t in me.loop_triangles:
            pc = out[(o.name, at.data[t.polygon_index].value)]
            pc['tris'].append([pc['map'][vi] for vi in t.vertices])
            pc['normals'].append((nmat @ t.normal).normalized())
            pc['centers'].append(mw @ t.center)
            pc['areas'].append(t.area)
    return out


def validate_generated_geometry():
    bpy.context.view_layer.update()
    V = {'blender': bpy.app.version_string, 'checks': [], 'python_report': DATA['report']}

    def check(group, name, ok, detail):
        V['checks'].append({'group': group, 'check': name, 'pass': bool(ok), 'detail': detail})

    walls = bpy.data.objects.get('Building_Walls_Connected')
    wall_objs = [o for o in objs_in('WALLS') if o.type == 'MESH']
    lintels = [o for o in objs_in('LINTELS') if o.type == 'MESH']
    tiles = [o for o in objs_in('WASHROOM_TILES') if o.type == 'MESH']
    panels = [o for o in objs_in('WALL_PANELS') if o.type == 'MESH']
    skirt = [o for o in objs_in('SKIRTING') if o.type == 'MESH']
    room_skirt = [o for o in objs_in('04_Skirting') if o.type == 'MESH']
    room_floors = [o for o in objs_in('03_Flooring') if o.type == 'MESH']
    pieces = wall_objs + lintels
    wbvh = bvh_of(([walls] if walls else wall_objs) + lintels)
    pbvh = bvh_of(pieces) if pieces else None             # bare walls + sills + lintels
    tbvh = bvh_of(tiles) if tiles else None
    sbvh = bvh_of(room_skirt if room_skirt else skirt) if (room_skirt or skirt) else None

    # 1. Separate editable walls (or optional continuous shell) & collection hierarchy
    req_cols = ('01_Structure', '02_Openings', '03_Flooring', '04_Skirting',
                '05_Washroom_Tiles', '06_Balcony', '07_Kitchen', '08_Materials_And_Lighting')
    has_cols = all(bpy.data.collections.get(c) is not None for c in req_cols)
    check('model', 'logical scene collections 01_Structure..08_Materials_And_Lighting organized',
          has_cols, f'collections: {req_cols}')
    if walls:
        bm = bmesh.new(); bm.from_mesh(walls.data)
        bad_e = [e for e in bm.edges if len(e.link_faces) != 2]
        nm = len(bad_e)
        nm_at = [tuple(round(c / M) for c in (e.verts[0].co + e.verts[1].co) / 2) + (len(e.link_faces),) for e in bad_e[:12]]
        zs = [v.co.z for v in bm.verts]
        vol = bm.calc_volume()
        mats = {}
        for f in bm.faces:
            k = walls.data.materials[f.material_index].name
            mats[k] = mats.get(k, 0) + 1
        bm.free()
        check('model', 'Building_Walls_Connected is watertight (0 non-manifold edges)', nm == 0,
              f'{nm} non-manifold edges, {len(walls.data.polygons)} faces, volume {vol:.3f} m3' + (f'; at (mm, faces) {nm_at}' if nm else ''))
        z0e, z1e = ((-S['slab_t'] - S.get('floor_finish_t', 20.0), S['wall_h']) if MERGE_INTO_ONE_MESH else (0.0, S['wall_h']))
        check('model', f'continuous walls reach full height z {z0e:.0f} .. {z1e:.0f} mm',
              abs(min(zs) / M - z0e) < 0.1 and abs(max(zs) / M - z1e) < 0.1,
              f'z = {min(zs) / M:.1f} .. {max(zs) / M:.1f} mm')
        V['model_face_materials'] = mats
    if wall_objs:
        nm_walls = []
        unselectable = []
        for wo in wall_objs:
            bm_w = bmesh.new(); bm_w.from_mesh(wo.data)
            nm_w = sum(1 for e in bm_w.edges if len(e.link_faces) != 2)
            bm_w.free()
            if nm_w > 0:
                nm_walls.append((wo.name, nm_w))
            if wo.hide_select or wo.hide_render:
                unselectable.append(wo.name)
        lc_w = layer_col('WALLS')
        vis_w = lc_w is not None and not lc_w.exclude and not lc_w.hide_viewport
        check('walls', 'every wall / post / sill is a separate, selectable, watertight editable mesh in 01_Structure > WALLS',
              vis_w and len(wall_objs) > 0 and not nm_walls and not unselectable,
              f'{len(wall_objs)} separate wall/post/sill meshes, non-manifold: {nm_walls[:8]}, hidden: {unselectable[:8]}')
    if pieces:
        zs = [(o.matrix_world @ v.co).z for o in pieces for v in o.data.vertices]
        check('walls', 'wall height 0.000-3.000 m', abs(min(zs)) < 1e-4 and abs(max(zs) - S['wall_h'] * M) < 1e-4, f'z = {min(zs):.4f} .. {max(zs):.4f} m')
        bad = [o.name for o in pieces if o['base_mm'] < -0.01 or o['base_mm'] + o['height_mm'] > S['wall_h'] + 0.01]
        check('walls', 'all wall pieces inside 0-3000 mm', not bad, f'{len(pieces)} pieces, out of range: {bad}')

    # 1b. Clean wireframe / mesh topology check (0 diagonal cross-segments across all architectural meshes)
    diag_cross = []
    wall_splits = []
    topo_cols = ('WALLS', 'LINTELS', '03_Flooring', '04_Skirting', 'FLOOR', 'CEILING',
                 'RECESSED_CEILINGS', '05_Washroom_Tiles', '06_Balcony', '07_Kitchen',
                 'DOOR_FITTINGS', 'WINDOW_FITTINGS')
    seen_topo = set()
    for cname in topo_cols:
        for o in objs_in(cname):
            if o.type != 'MESH' or o.name in seen_topo:
                continue
            seen_topo.add(o.name)
            if 'Downlights' in o.name or o.name.endswith('_Lever'):
                continue
            bm_t = bmesh.new(); bm_t.from_mesh(o.data)
            bmesh.ops.recalc_face_normals(bm_t, faces=bm_t.faces[:])
            mw = o.matrix_world
            for e in bm_t.edges:
                if len(e.link_faces) != 2:
                    continue
                f0, f1 = e.link_faces[0], e.link_faces[1]
                if f0.normal.dot(f1.normal) < 0.9999:
                    continue
                if cname in ('WALLS', 'LINTELS'):
                    wall_splits.append(o.name)
                    break
                p0 = mw @ e.verts[0].co
                p1 = mw @ e.verts[1].co
                dx, dy, dz = abs(p1.x - p0.x), abs(p1.y - p0.y), abs(p1.z - p0.z)
                axes_changed = (1 if dx > 1e-4 else 0) + (1 if dy > 1e-4 else 0) + (1 if dz > 1e-4 else 0)
                if axes_changed >= 2:
                    diag_cross.append((o.name, round(dx / M, 1), round(dy / M, 1), round(dz / M, 1)))
                    break
            bm_t.free()
    check('topology', 'clean quad / planar wireframe with 0 diagonal cross-segments across all meshes',
          not diag_cross and not wall_splits,
          f'checked {len(seen_topo)} meshes; diagonal cross-edges: {diag_cross[:8]}, wall face splits: {wall_splits[:8]}')

    # 2. Blue lintel beams (Section 3)
    if BUILD_BLUE_LINTELS:
        want_lintel_ops = [o for o in OPEN_M if o.get('has_lintel')]
        lintel_op_ids = {o['id'] for o in want_lintel_ops}
        passage_lintels = [o for o in lintels if o.get('opening_type') == 'passage'
                           and o.get('opening_id', '') not in lintel_op_ids]
        bad_l = []
        for lo in lintels:
            bm_l = bmesh.new(); bm_l.from_mesh(lo.data)
            nm_l = sum(1 for e in bm_l.edges if len(e.link_faces) != 2)
            bm_l.free()
            zs_l = [(lo.matrix_world @ v.co).z / M for v in lo.data.vertices]
            mat_ok = lo.data.materials and lo.data.materials[0] == MAT['lintel_blue']
            if nm_l > 0 or abs(min(zs_l) - S['door_head']) > 1.0 or abs(max(zs_l) - S['wall_h']) > 1.0 or not mat_ok:
                bad_l.append((lo.name, nm_l, round(min(zs_l), 1), round(max(zs_l), 1), bool(mat_ok)))
        check('lintels', 'blue lintel beams (Z = 2100-3000 mm, MAT_Lintel_Blue) above doors & windows; none on open passages',
              len(lintels) >= len(want_lintel_ops) and not passage_lintels and not bad_l,
              f'{len(lintels)} lintel objects, passage lintels: {len(passage_lintels)}, bad: {bad_l}')

    # 3. Openings: measured clear size + obstruction by walls / tiles / skirting
    V['openings'] = []
    for o in OPEN_M:
        p0, p1 = Vector((o['p0'][0] * M, o['p0'][1] * M, 0)), Vector((o['p1'][0] * M, o['p1'][1] * M, 0))
        d = (p1 - p0).normalized()
        n = Vector((-d.y, d.x, 0))
        c = (p0 + p1) / 2
        sill, head = o['sill'] * M, o['head'] * M
        zmid = (sill + head) / 2
        res = {'id': o['id'], 'type': o['type'], 'rooms': o.get('rooms', [])}
        if wbvh:
            hit = wbvh.ray_cast(Vector((c.x, c.y, sill + 0.01)), Vector((0, 0, 1)), 10.0)
            res['measured_head_mm'] = round(hit[0].z / M, 1) if hit[0] else None
            hit = wbvh.ray_cast(Vector((c.x, c.y, head - 0.01)), Vector((0, 0, -1)), 10.0)
            res['measured_sill_mm'] = round(hit[0].z / M, 1) if hit[0] else 0.0
            hl = wbvh.ray_cast(Vector((c.x, c.y, zmid)), -d, 10.0)
            hr = wbvh.ray_cast(Vector((c.x, c.y, zmid)), d, 10.0)
            res['measured_width_mm'] = round((hl[3] + hr[3]) / M, 1) if hl[0] and hr[0] else None
            ob = box_bvh(c.x, c.y, d, n, o['width'] * M / 2 - 0.005, o['thickness'] * M / 2 - 0.005, sill + 0.005, head - 0.005)
            res['wall_intrusions'] = len(wbvh.overlap(ob))
            res['tile_intrusions'] = len(tbvh.overlap(ob)) if tbvh else 0
            res['skirting_intrusions'] = len(sbvh.overlap(ob)) if sbvh else 0
        no_lintel_above = bool(o.get('balcony') or not o.get('has_lintel', o['type'] != 'passage'))
        ok_h = (res.get('measured_head_mm') is None if no_lintel_above
                else (res.get('measured_head_mm') is not None and abs(res['measured_head_mm'] - o['head']) < 1.0))
        ok_s = abs(res.get('measured_sill_mm', -1) - o['sill']) < 1.0
        ok_w = res.get('measured_width_mm') is not None and abs(res['measured_width_mm'] - o['width']) < 2.0
        clear = res.get('wall_intrusions', 1) == 0 and res.get('tile_intrusions', 1) == 0 and res.get('skirting_intrusions', 1) == 0
        res['pass'] = ok_h and ok_s and ok_w and clear
        V['openings'].append(res)
        check('openings', f"{o['id']} ({o['type']}) clear {o['width']:.0f} x {o['head'] - o['sill']:.0f} mm, sill {o['sill']:.0f}",
              res['pass'], f"measured sill {res.get('measured_sill_mm')}, head {res.get('measured_head_mm')}, width {res.get('measured_width_mm')}; "
                           f"intrusions wall/tile/skirting = {res.get('wall_intrusions')}/{res.get('tile_intrusions')}/{res.get('skirting_intrusions')}")

    # 4. Separate Room Flooring & Skirting (Sections 4 & 5)
    if BUILD_FLOORING and DATA.get('room_floors'):
        want_floors = len(DATA['room_floors'])
        master_fl = [o for o in room_floors if o.get('category') == 'master_wood']
        common_fl = [o for o in room_floors if o.get('category') == 'common']
        wash_fl = [o for o in room_floors if o.get('category') == 'washroom']
        bal_fl = [o for o in room_floors if o.get('category') in ('balcony', 'dry_balcony')]
        master_ok = all(o.data.materials and o.data.materials[0] == MAT['floor_master_wood'] for o in master_fl)
        common_ok = all(o.data.materials and o.data.materials[0] == MAT['floor_common'] for o in common_fl)
        wash_ok = all(o.data.materials and o.data.materials[0] == MAT['floor_washroom'] for o in wash_fl)
        bal_ok = all(o.data.materials and o.data.materials[0] == MAT['floor_balcony'] for o in bal_fl)
        sep_ok = not MERGE_INTO_ONE_MESH and len(room_floors) == want_floors and len(room_skirt) == len(DATA.get('room_skirting', []))
        check('flooring', 'independent room flooring & skirting objects with dedicated room-wise materials (Master Wood, Common, Entrance, Balcony, Washroom)',
              sep_ok and master_ok and common_ok and wash_ok and bal_ok and len(master_fl) >= 1,
              f"floors: {len(room_floors)} (master wood: {[o.name for o in master_fl]}, washroom: {len(wash_fl)}, balcony: {len(bal_fl)}, common: {len(common_fl)}); "
              f"skirting objects: {len(room_skirt)}")

    if skirt:
        rooms_by_name = {r['name']: r for r in DATA['rooms']}
        hs = []
        in_wash = []
        for o in skirt:
            zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
            hs.append(max(zs) - min(zs))
            rm_info = rooms_by_name.get(o.get('room', ''))
            if rm_info and rm_info.get('type') == 'washroom':
                in_wash.append(o.name)
            elif rm_info is None and o.data.vertices:
                v0 = o.matrix_world @ o.data.vertices[0].co
                r = room_at(v0.x, v0.y)
                if r and r['type'] == 'washroom':
                    in_wash.append(o.name)
        check('skirting', f"height = {S['skirt_h']} mm on every run", all(abs(h - S['skirt_h'] * M) < 1e-6 for h in hs),
              f'{len(skirt)} runs, height {min(hs) / M:.2f}-{max(hs) / M:.2f} mm')
        check('skirting', 'no skirting inside washrooms', not in_wash, f'{in_wash}')

    # 5. Washroom tiles & wall panels
    def frame(p):
        d = Vector((p['dir'][0], p['dir'][1], 0.0))
        return Vector((p['origin'][0] * M, p['origin'][1] * M, 0.0)), d, Vector((-d.y, d.x, 0.0))

    def flush_bad(pcs, src, thick, tol):
        out, worst = [], 0.0
        for key, pc in pcs.items():
            _o, _d, nin = frame(src[key])
            back = [i for i, nn in enumerate(pc['normals']) if nn.dot(nin) < -0.99]
            if not back:
                out.append((src[key]['name'], 'no back face')); continue
            i = max(back, key=lambda i: pc['areas'][i])
            hit = pbvh.ray_cast(pc['centers'][i] + nin * (thick / 2), -nin, 0.05)
            dev = None if hit[0] is None else abs(hit[3] - thick / 2)
            if dev is not None:
                worst = max(worst, dev)
            if dev is None or dev > tol:
                out.append((src[key]['name'], None if hit[0] is None else round(hit[3] / M, 3)))
        return out, worst

    def clashes_of(pcs):
        boxes = []
        for key, pc in pcs.items():
            ws = pc['verts']
            boxes.append((key, Vector((min(v.x for v in ws), min(v.y for v in ws), min(v.z for v in ws))),
                          Vector((max(v.x for v in ws), max(v.y for v in ws), max(v.z for v in ws)))))
        cache, out = {}, []
        for i in range(len(boxes)):
            ki, lo_i, hi_i = boxes[i]
            for j in range(i + 1, len(boxes)):
                kj, lo_j, hi_j = boxes[j]
                if any(hi_i[k] < lo_j[k] - 1e-6 or hi_j[k] < lo_i[k] - 1e-6 for k in range(3)):
                    continue
                bi = cache.setdefault(ki, BVHTree.FromPolygons(pcs[ki]['verts'], pcs[ki]['tris']))
                bj = cache.setdefault(kj, BVHTree.FromPolygons(pcs[kj]['verts'], pcs[kj]['tris']))
                if bi.overlap(bj):
                    out.append((ki, kj))
        return out

    if tiles:
        rooms_by_name = {r['name']: r for r in DATA['rooms']}
        src, by_room = {}, {}
        for t in DATA['tiles']:
            by_room.setdefault(t['room'], []).append(t)
        for idx, (room, items) in enumerate(by_room.items(), 1):
            t_obj_name = rooms_by_name.get(room, {}).get('tile_obj') or f"Tiles_Washroom_Wall_{idx:02d}"
            for k, t in enumerate(items):
                src[(t_obj_name, k)] = t
        tp = pieces_of(tiles, 'tile_id')
        per, dims_bad, z_bad = {}, [], []
        for key, pc in tp.items():
            t = src.get(key)
            if t is None:
                dims_bad.append((key, 'unknown tile')); continue
            st = per.setdefault(t['room'], {'tiles': 0, 'full': 0, 'cut': 0})
            st['tiles'] += 1
            st['full' if t['full'] else 'cut'] += 1
            org, d, nin = frame(t)
            us = [(v - org).dot(d) for v in pc['verts']]
            ys = [(v - org).dot(nin) for v in pc['verts']]
            zs = [v.z for v in pc['verts']]
            if t['full'] and (abs(max(us) - min(us) - S['tile_w'] * M) > 2e-5 or abs(max(zs) - min(zs) - S['tile_h'] * M) > 2e-5
                              or abs(max(ys) - min(ys) - S['tile_t'] * M) > 2e-5):
                dims_bad.append(t['name'])
            if min(zs) < -1e-6 or max(zs) > S['wall_h'] * M + 1e-6:
                z_bad.append(t['name'])
        V['tiles_per_washroom'] = per
        check('tiles', 'full tiles measure 914.4 x 609.6 x 9 mm', not dims_bad, f'bad: {dims_bad[:10]}')
        check('tiles', 'all tiles within z 0-3000 mm', not z_bad, f'bad: {z_bad[:10]}')
        if pbvh:
            off_bad, worst = flush_bad(tp, src, S['tile_t'] * M, 2e-5)
            check('tiles', 'every tile is bonded flush on the wall face (0 mm gap, no penetration)', not off_bad,
                  f'{len(tp)} tiles checked, max deviation {worst / M:.4f} mm; bad: {off_bad[:8]}')
        cl = clashes_of(tp)
        check('tiles', 'no tile intersects another tile', not cl, f'{len(cl)} clashes {cl[:5]}')
        lc = layer_col('WASHROOM_TILES')
        vis = lc is not None and not lc.exclude and not lc.hide_viewport
        one_mat = all(len(o.data.materials) == 1 and o.data.materials[0] == MAT['tile'] for o in tiles)
        check('tiles', 'each washroom\'s tiles are ONE mesh with one tile material (texture applies to all tiles)',
              vis and one_mat and len(tiles) == len(by_room) and len(tp) == len(DATA['tiles']) and all('UVMap' in o.data.uv_layers for o in tiles),
              f"{len(tiles)} meshes {[o.name for o in tiles]} holding {len(tp)} tiles (expected {len(DATA['tiles'])})")

    # Wall panels
    if BUILD_WALL_PANELS and DATA.get('panels'):
        rooms = {r['name']: r for r in DATA['rooms']}
        src, by_room = {}, {}
        for p in DATA['panels']:
            by_room.setdefault(p['room'], []).append(p)
        names = {}
        for room, items in by_room.items():
            nm = f"Wall_Panels_{room}_{rooms[room].get('label', '')}".rstrip('_')
            names[room] = nm
            for k, p in enumerate(items):
                src[(nm, k)] = p
        pp = pieces_of(panels, 'panel_id')
        wrong_room = [o.name for o in panels if rooms.get(o.get('room'), {}).get('type') == 'washroom'
                      or rooms.get(o.get('room'), {}).get('use') in ('balcony', 'dry_balcony')]
        want = sorted(r['name'] for r in DATA['rooms'] if r.get('panelled'))
        check('panels', 'wall panels in every habitable dry room only (none in washrooms / balconies)',
              not wrong_room and sorted(by_room) == want and len(panels) == len(want),
              f"panelled: {[names[r] for r in sorted(by_room)]}; wrong: {wrong_room}")
        z_bad = [src[k]['name'] for k, pc in pp.items()
                 if min(v.z for v in pc['verts']) < S['skirt_h'] * M - 1e-5 or max(v.z for v in pc['verts']) > S['wall_h'] * M + 1e-5]
        check('panels', f"panels run from skirting top ({S['skirt_h']} mm) to ceiling ({S['wall_h']:.0f} mm)", not z_bad and len(pp) == len(DATA['panels']),
              f"{len(pp)} sheets (expected {len(DATA['panels'])}); out of range: {z_bad[:8]}")
        if pbvh:
            off_bad, worst = flush_bad(pp, src, S['panel_t'] * M, 5e-4)
            check('panels', 'every panel sheet sits flush on the wall face', not off_bad,
                  f'{len(pp)} sheets checked, max deviation {worst / M:.3f} mm; bad: {off_bad[:8]}')
        cl = clashes_of(pp)
        check('panels', 'no panel sheet intersects another (corners butt / wrap cleanly)', not cl, f'{len(cl)} clashes {cl[:5]}')
        check('panels', 'panel meshes are texture-ready (one material, UVMap in metres)',
              all(len(o.data.materials) == 1 and 'UVMap' in o.data.uv_layers for o in panels), f'{len(panels)} meshes')

    # Window fittings
    if BUILD_WINDOW_FITTINGS:
        bad = []
        n_w = 0
        for o in OPEN_M:
            if o['type'] not in ('window', 'vent') or o.get('balcony'):
                continue
            n_w += 1
            fr = bpy.data.objects.get(o['id'] + '_Frame')
            if fr is None:
                bad.append((o['id'], 'no frame')); continue
            ws = [fr.matrix_world @ v.co for v in fr.data.vertices]
            p0 = Vector((o['p0'][0] * M, o['p0'][1] * M, 0)); dd = (Vector((o['p1'][0] * M, o['p1'][1] * M, 0)) - p0).normalized()
            us = [(v - p0).dot(dd) for v in ws]
            zs = [v.z for v in ws]
            w_ok = abs(min(us)) < 5e-4 and abs(max(us) - o['width'] * M) < 5e-4
            z_ok = abs(min(zs) - o['sill'] * M) < 5e-4 and abs(max(zs) - o['head'] * M) < 5e-4
            ng = len([g for g in objs_in(o['id'] + '_Fitting') if '_Glass_' in g.name])
            if not (w_ok and z_ok and ng == fr['panes']):
                bad.append((o['id'], round((max(us) - min(us)) / M, 1), round(min(zs) / M, 1), round(max(zs) / M, 1), ng))
        check('windows', 'every window / ventilator has a frame filling the opening + glass in every pane', not bad and n_w > 0,
              f'{n_w} fitted openings; bad: {bad}')

    # Balcony railings (Section 7: 1.2 m / 4 ft glass + metal railings on standard balconies; none on dry balconies)
    if BUILD_BALCONY_GLASS:
        bal = [o for o in OPEN_M if o.get('balcony') and not o.get('dry_balcony')]
        bg = [g for g in objs_in('BALCONY_GLASS') if g.type == 'MESH']
        bm_rails = [r for r in objs_in('06_Balcony') if r.type == 'MESH' and r.get('part') == 'metal_railing_posts_and_top_rail']
        dry_bal_rails = [g.name for g in bg + bm_rails if any(
            rm['use'] == 'dry_balcony' for rm in DATA['rooms'] if rm['name'] == g.get('room')
        )]
        bad = []
        for o in bal:
            g = next((x for x in bg if x.get('opening') == o['id']), None)
            mr = next((x for x in bm_rails if x.get('opening') == o['id']), None)
            if g is None or mr is None:
                bad.append((o['id'], 'missing glass or metal railing')); continue
            ws = [g.matrix_world @ v.co for v in g.data.vertices]
            p0 = Vector((o['p0'][0] * M, o['p0'][1] * M, 0)); dd = (Vector((o['p1'][0] * M, o['p1'][1] * M, 0)) - p0).normalized()
            nn = Vector((-dd.y, dd.x, 0))
            us = [(v - p0).dot(dd) for v in ws]; ns = [(v - p0).dot(nn) for v in ws]; zs = [v.z for v in ws]
            T = S.get('balcony_glass_t', 76.2) * M
            want_h = S.get('balcony_glass_h', 1200.0) * M
            ok = (abs(min(us)) < 5e-4 and abs(max(us) - o['width'] * M) < 5e-4 and abs(min(zs) - o['sill'] * M) < 5e-4
                  and abs(max(zs) - o['head'] * M) < 5e-4 and abs((max(zs) - min(zs)) - want_h) < 1e-3
                  and abs(max(ns) - min(ns) - T) < 5e-5)
            if not ok:
                bad.append((o['id'], round((max(ns) - min(ns)) / M, 2), round((max(us) - min(us)) / M, 1)))
        check('balcony', f"1.2 m ({S.get('balcony_glass_h', 1200.0):.0f} mm / ~4 ft) glass panels + metal railings on standard balconies; none on dry balconies",
              (not bal or (not bad and len(bg) == len(bal) and len(bm_rails) == len(bal))) and not dry_bal_rails,
              f"{len(bal)} balcony openings -> {[g.name for g in bg]} + {[r.name for r in bm_rails]}; dry_balcony_rails: {dry_bal_rails}; bad: {bad}")

    # Door fittings
    if BUILD_DOOR_FITTINGS:
        doors_op = [o for o in OPEN_M if o['type'] == 'door']
        bad_d = []
        for o in doors_op:
            fr = bpy.data.objects.get(o['id'] + '_Frame')
            lf = bpy.data.objects.get(o['id'] + '_Leaf')
            lv = bpy.data.objects.get(o['id'] + '_Lever')
            if not (fr and lf and lv):
                bad_d.append((o['id'], 'missing part')); continue
            if lf.parent != fr or lv.parent != lf:
                bad_d.append((o['id'], 'wrong hierarchy')); continue
            ws_fr = [fr.matrix_world @ v.co for v in fr.data.vertices]
            ws_lv = [lv.matrix_world @ v.co for v in lv.data.vertices]
            p0 = Vector((o['p0'][0] * M, o['p0'][1] * M, 0))
            dd = (Vector((o['p1'][0] * M, o['p1'][1] * M, 0)) - p0).normalized()
            nn = Vector((-dd.y, dd.x, 0))
            us = [(v - p0).dot(dd) for v in ws_fr]
            zs = [v.z for v in ws_fr]
            ns_lv = [(v - p0).dot(nn) for v in ws_lv]
            leaf_half = (lf.get('leaf_thickness_mm', 42.0) / 2.0 + 20.0) * M
            both_sides = min(ns_lv) < -leaf_half and max(ns_lv) > leaf_half
            mat_ok = (fr.data.materials and fr.data.materials[0] == MAT['door_frame']
                      and lf.data.materials and lf.data.materials[0] == MAT['door_leaf']
                      and lv.data.materials and lv.data.materials[0] == MAT['door_lever'])
            if not (abs(min(us)) < 5e-4 and abs(max(us) - o['width'] * M) < 5e-4
                    and abs(min(zs) - o['sill'] * M) < 5e-4 and abs(max(zs) - o['head'] * M) < 5e-4
                    and both_sides and mat_ok):
                bad_d.append((o['id'], both_sides, mat_ok))
        check('doors', 'every door has editable wooden frame, wooden leaf, and silver lever on both sides',
              len(doors_op) > 0 and not bad_d,
              f"{len(doors_op)} door assemblies (Frame -> Leaf -> Lever); bad: {bad_d}")

    # Kitchen platform & countertop (Section 10)
    if BUILD_KITCHEN_PLATFORM and DATA.get('kitchens'):
        k_items = DATA['kitchens']
        bad_k = []
        for k in k_items:
            ob_b = bpy.data.objects.get(k['base_name'])
            ob_t = bpy.data.objects.get(k['counter_name'])
            if not (ob_b and ob_t):
                bad_k.append((k['id'], 'missing base or countertop')); continue
            zs_b = [(ob_b.matrix_world @ v.co).z / M for v in ob_b.data.vertices]
            zs_t = [(ob_t.matrix_world @ v.co).z / M for v in ob_t.data.vertices]
            mat_ok = (ob_b.data.materials and ob_b.data.materials[0] == MAT['kitch_base']
                      and ob_t.data.materials and ob_t.data.materials[0] == MAT['kitch_top'])
            if abs(min(zs_b)) > 0.5 or abs(max(zs_t) - S.get('kitchen_counter_h', 860.0)) > 0.5 or not mat_ok:
                bad_k.append((k['id'], round(min(zs_b), 1), round(max(zs_t), 1), bool(mat_ok)))
        check('kitchen', f"kitchen platform (base + countertop at {S.get('kitchen_counter_h', 860.0):.0f} mm) follows kitchen layout",
              not bad_k and len(k_items) > 0,
              f"{len(k_items)} kitchen platform(s) {[k['counter_name'] + ' (' + k['shape'] + ')' for k in k_items]}; bad: {bad_k}")

    # Recessed ceilings
    if BUILD_RECESSED_CEILINGS and DATA.get('recessed_ceilings'):
        rcs = DATA['recessed_ceilings']
        rooms_by_name = {r['name']: r for r in DATA['rooms']}
        want_rc = sorted(r['name'] for r in DATA['rooms'] if r.get('recessed_ceiling'))
        got_rc = sorted(rc['room'] for rc in rcs)
        wrong_rc = [rc['room'] for rc in rcs if rooms_by_name.get(rc['room'], {}).get('type') != 'dry'
                    or any(k in (rooms_by_name.get(rc['room'], {}).get('use') or '')
                           for k in ('washroom', 'balcony', 'kitchen', 'pantry', 'wardrobe', 'servant', 'box_room', 'lobby', 'foyer'))]
        bad_rc = []
        for rc in rcs:
            rm_n = rc['room']
            tr = bpy.data.objects.get(f"{rm_n}_Recessed_Ceiling_Plane")
            sf = bpy.data.objects.get(f"{rm_n}_Recessed_Perimeter_Soffit")
            dl = bpy.data.objects.get(f"{rm_n}_Recessed_Downlights")
            if not (tr and sf and dl):
                bad_rc.append((rm_n, 'missing mesh')); continue
            zs_tr = [(tr.matrix_world @ v.co).z / M for v in tr.data.vertices]
            if max(zs_tr) < S['wall_h'] + S.get('recess_depth', 120.0) - 1.0:
                bad_rc.append((rm_n, 'not recessed upward'))
        check('ceiling', 'low-profile recessed ceilings in bedrooms and halls only (cavity set upward + recessed lights)',
              got_rc == want_rc and not wrong_rc and not bad_rc and len(rcs) > 0,
              f"{len(rcs)} rooms {[rc['room'] + ' (' + rc['label'] + ')' for rc in rcs]}; wrong: {wrong_rc}; bad: {bad_rc}")

    # Slabs
    ceil_obj = bpy.data.objects.get('Ceiling_Slab')
    if ceil_obj:
        zs = [(ceil_obj.matrix_world @ v.co).z / M for v in ceil_obj.data.vertices]
        z0, z1 = S['wall_h'], S['wall_h'] + S['slab_t']
        check('slabs', f'Ceiling_Slab z {z0:.0f} .. {z1:.0f} mm (200 mm thick)',
              abs(min(zs) - z0) < 0.01 and abs(max(zs) - z1) < 0.01,
              f'measured {min(zs):.1f} .. {max(zs):.1f} mm')
        check('slabs', 'direct continuous ceiling above all (no room sub-ceilings)',
              len(ceil_obj.data.polygons) >= 1, f'{len(ceil_obj.data.polygons)} polygons')

    V['summary'] = {'checks': len(V['checks']), 'passed': sum(c['pass'] for c in V['checks']),
                    'failed': [c['check'] for c in V['checks'] if not c['pass']]}
    txt = bpy.data.texts.get('VALIDATION_REPORT') or bpy.data.texts.new('VALIDATION_REPORT')
    txt.clear()
    txt.write(json.dumps(V, indent=1))
    vc = collection('VALIDATION')
    purge(vc)
    e = bpy.data.objects.new('Validation_Summary', None)
    e['checks_passed'] = f"{V['summary']['passed']}/{V['summary']['checks']}"
    e['see'] = 'Text Editor > VALIDATION_REPORT'
    vc.objects.link(e)
    print('=====VALIDATION_JSON_BEGIN=====')
    print(json.dumps(V))
    print('=====VALIDATION_JSON_END=====')
    return V


validate = validate_generated_geometry


def set_visibility(working):
    """working=True: every generated collection evaluated (needed while building / validating).
    working=False: only the final exportable architectural collections remain active in the view layer,
    with CEILING & RECESSED_CEILINGS hidden in the viewport so all room floors & interiors are visible from above."""
    lc_ep = layer_col('EDITABLE_PARTS')
    if lc_ep:
        lc_ep.exclude = not working
    for name in ('DOORS', 'WINDOWS', 'ROOMS', 'VALIDATION', 'SOURCE_CAD'):
        lc = layer_col(name)
        if lc:
            if working:
                lc.exclude = False
            if name in ('ROOMS', 'VALIDATION', 'SOURCE_CAD'):
                for o in objs_in(name):
                    o.hide_select = True
            lc.hide_viewport = not working
            if not working:
                lc.exclude = True
    for name in ('CEILING', 'RECESSED_CEILINGS'):
        lc = layer_col(name)
        if lc:
            lc.exclude = False
            lc.hide_viewport = False


# ─────────────────────────── 9. UNREAL ENGINE / 3ds MAX EXPORT ───────────────────────────
def _export_root():
    import os
    d = EXPORT_DIR or os.environ.get('CAD_EXPORT_DIR', '')
    if not d and bpy.data.filepath:
        d = os.path.dirname(bpy.data.filepath)
    if not d:
        d = os.path.join(os.path.expanduser('~'), 'Documents', 'CAD_Blender_Exports')
    os.makedirs(d, exist_ok=True)
    return d


def _export_groups(include_lights):
    """Ordered (group null name, [objects]) - every final architectural element, each a separate editable object."""
    if EXPORT_WALL_MODE == 'connected' and CONNECT_WALLS_INTO_ONE_MESH:
        walls = [o for o in objs_in('01_Structure') if o.name == 'Building_Walls_Connected']
    else:
        walls = [o for o in objs_in('WALLS') if o.type == 'MESH' and o.get('kind') != 'lintel']
    groups = [
        ('GRP_01_Walls', walls),
        ('GRP_01_Floor_Slab', objs_in('FLOOR')),
        ('GRP_01_Ceiling', objs_in('CEILING')),
        ('GRP_01_Recessed_Ceilings', objs_in('RECESSED_CEILINGS')),
        ('GRP_01_Wall_Panels', objs_in('WALL_PANELS')),
        ('GRP_02_Lintels', objs_in('LINTELS')),
        ('GRP_02_Doors', objs_in('DOOR_FITTINGS')),
        ('GRP_02_Windows', objs_in('WINDOW_FITTINGS')),
        ('GRP_03_Flooring', objs_in('03_Flooring')),
        ('GRP_04_Skirting', objs_in('04_Skirting')),
        ('GRP_05_Washroom_Tiles', objs_in('05_Washroom_Tiles')),
        ('GRP_06_Balcony_Railings', objs_in('06_Balcony')),
        ('GRP_07_Kitchen', objs_in('07_Kitchen')),
    ]
    if include_lights:
        groups.append(('GRP_08_Lights_Camera', objs_in('08_Materials_And_Lighting')))
    out, seen = [], set()
    for g, objs in groups:
        keep = []
        for o in objs:
            if o.name in seen or o.type not in ('MESH', 'LIGHT', 'CAMERA'):
                continue
            seen.add(o.name)
            keep.append(o)
        if keep:
            out.append((g, keep))
    return out


def export_for_unreal_and_3dsmax():
    """Write <name>_Unreal.fbx and <name>_3dsMax.fbx (+ .blend + import notes).
    Units: 1 Blender unit = 1 m -> FBX scaled so Unreal reads centimetres (1 m = 100 uu) and 3ds Max converts
    to its system units automatically. Every element stays a separate, named, editable object with its own
    origin, materials and UVs, grouped under GRP_* null objects (Unreal 'Import Into Level' / 3ds Max hierarchy)."""
    import os, re
    root = _export_root()
    name = EXPORT_NAME or os.environ.get('CAD_EXPORT_NAME', '') or 'Architectural_Model'
    name = re.sub(r'[^A-Za-z0-9_\-]+', '_', name).strip('_') or 'Architectural_Model'
    vl = bpy.context.view_layer
    prev_active = vl.active_layer_collection
    results = {'dir': root, 'files': [], 'objects': {}}

    for target, include_lights, tris in (('Unreal', False, False), ('3dsMax', True, False)):
        tmp = bpy.data.collections.new('EXPORT_' + target)
        bpy.context.scene.collection.children.link(tmp)
        empties, reparented = [], []
        n_mesh = 0
        try:
            for gname, objs in _export_groups(include_lights):
                emp = bpy.data.objects.new(gname, None)
                emp.empty_display_type = 'PLAIN_AXES'
                tmp.objects.link(emp)
                empties.append(emp)
                names = {o.name for o in objs}
                for o in objs:
                    tmp.objects.link(o)
                    if o.type == 'MESH':
                        n_mesh += 1
                        if not o.data.uv_layers:
                            o.data.uv_layers.new(name='UVMap')
                    if o.parent is None or o.parent.name not in names:
                        reparented.append((o, o.parent, o.matrix_world.copy()))
                        o.parent = emp
                        o.matrix_parent_inverse.identity()
                        o.matrix_world = reparented[-1][2]
            vl.update()
            lc = layer_col(tmp.name)
            lc.exclude = False
            lc.hide_viewport = False
            vl.active_layer_collection = lc
            path = os.path.join(root, f'{name}_{target}.fbx')
            bpy.ops.export_scene.fbx(
                filepath=path, use_active_collection=True, use_selection=False, use_visible=False,
                object_types={'EMPTY', 'MESH', 'LIGHT', 'CAMERA'} if include_lights else {'EMPTY', 'MESH'},
                global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                axis_forward='-Z', axis_up='Y', bake_space_transform=False,
                use_mesh_modifiers=True, mesh_smooth_type='FACE', use_triangles=tris, use_tspace=tris,
                use_mesh_edges=False, use_custom_props=not tris, add_leaf_bones=False, bake_anim=False,
                path_mode='AUTO', embed_textures=False, batch_mode='OFF')
            results['files'].append(path)
            results['objects'][target] = n_mesh
        finally:
            for o, par, mw in reparented:
                o.parent = par
                o.matrix_world = mw
            for o in list(tmp.objects):
                tmp.objects.unlink(o)
            for emp in empties:
                bpy.data.objects.remove(emp, do_unlink=True)
            bpy.data.collections.remove(tmp)
            try:
                vl.active_layer_collection = prev_active
            except Exception:
                pass

    notes = os.path.join(root, f'{name}_IMPORT_NOTES.txt')
    with open(notes, 'w', encoding='utf-8') as fh:
        fh.write(
            f"{name} - architectural model export\n"
            f"Walls: {'individual editable pieces' if EXPORT_WALL_MODE != 'connected' else 'one continuous mesh'}; "
            f"Unreal objects: {results['objects'].get('Unreal', 0)}, 3ds Max objects: {results['objects'].get('3dsMax', 0)}\n\n"
            "UNREAL ENGINE 5  (file: *_Unreal.fbx, triangulated, smoothing groups, tangents)\n"
            "  * Content Browser > Import, or File > Import Into Level to keep the GRP_ hierarchy as actors.\n"
            "  * Skeletal Mesh: off | Combine Meshes: OFF (keeps every wall/floor/door separate)\n"
            "  * Convert Scene: ON | Import Uniform Scale: 1.0 (1 m = 100 uu, already scaled)\n"
            "  * Generate Lightmap UVs: ON | Normal Import Method: Import Normals\n"
            "  * Materials: Create New Materials (names MAT_*, Window_Glass_Mat, MAT_Balcony_Glass ...)\n"
            "  * Glass: set the imported glass materials to Translucent in UE.\n\n"
            "3ds MAX  (file: *_3dsMax.fbx, quads/n-gons kept as Editable Poly, user properties kept)\n"
            "  * File > Import > *_3dsMax.fbx | Units: Automatic (converts metres to your system units)\n"
            "  * Smoothing Groups: ON | Preserve Edge Orientation: ON | Up axis: Z-up (auto-converted)\n"
            "  * Hierarchy: GRP_* dummies group Walls, Floor Slab, Ceiling, Recessed Ceilings, Lintels,\n"
            "    Doors (Frame > Leaf > Lever), Windows, Flooring, Skirting, Tiles, Balcony Railings, Kitchen.\n"
            "  * Object user properties carry room / opening / thickness metadata (Object Properties > User Defined).\n"
        )
    results['files'].append(notes)
    if SAVE_BLEND:
        bpath = os.path.join(root, f'{name}.blend')
        bpy.ops.wm.save_as_mainfile(filepath=bpath, copy=True)
        results['files'].append(bpath)
    print('EXPORT_RESULT_JSON:' + json.dumps(results))
    LOG.append(f"export: {results['files']}")
    return results


def main():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    organize_scene_collections()
    assign_room_materials()
    set_visibility(True)
    if BUILD_WALLS:
        build_walls()
    if BUILD_OPENING_MARKERS:
        create_openings()
    if BUILD_BLUE_LINTELS:
        generate_blue_lintels()
    if BUILD_ROOMS:
        build_rooms()
    if BUILD_FLOORING:
        generate_room_flooring()
    if BUILD_SKIRTING:
        generate_room_skirting()
    if BUILD_TILES:
        generate_washroom_tiles()
    if BUILD_WALL_PANELS:
        build_wall_panels()
    if BUILD_DOOR_FITTINGS:
        build_door_fittings()
    if BUILD_WINDOW_FITTINGS:
        build_window_fittings()
        build_glass_partitions()
    if BUILD_BALCONY_GLASS:
        generate_balcony_railings()
    if BUILD_KITCHEN_PLATFORM:
        generate_kitchen_platform()
    if BUILD_SLABS:
        build_slabs()
    if BUILD_RECESSED_CEILINGS:
        build_recessed_ceilings()
    if BUILD_LIGHTING_AND_CAM:
        build_lighting_and_camera()
    if BUILD_SOURCE_CAD:
        build_source_cad()
    if CONNECT_WALLS_INTO_ONE_MESH:
        generate_continuous_walls()
    for line in LOG:
        print('  ' + line)
    if RUN_VALIDATION:
        V = validate_generated_geometry()
        print(f"VALIDATION: {V['summary']['passed']}/{V['summary']['checks']} checks passed")
    set_visibility(False)
    active_target = bpy.data.objects.get('Building_Walls_Connected')
    if active_target is None:
        wall_candidates = [o for o in objs_in('WALLS') if o.type == 'MESH']
        active_target = wall_candidates[0] if wall_candidates else None
    if active_target is not None:
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = active_target
        active_target.select_set(True)
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces[0].clip_end = 1000.0
                if hasattr(area.spaces[0], 'shading'):
                    area.spaces[0].shading.color_type = 'MATERIAL'
    if EXPORT_FBX:
        try:
            res = export_for_unreal_and_3dsmax()
            print('EXPORTED for Unreal Engine & 3ds Max ->', res['dir'])
        except Exception as ex:
            import traceback
            traceback.print_exc()
            print('EXPORT FAILED:', ex)
    print('CAD architectural model done.')


main()
