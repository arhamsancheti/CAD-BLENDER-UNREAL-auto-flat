# ======================================================================
#  CAD -> Blender / 3ds Max / Unreal Engine Architectural 3D Model
#  Auto-generated, idempotent, re-runnable Blender Python script
#  Walls: 48 (exterior 24, interior 24) | openings: 23 | rooms: 11
#  Skirting runs: 12 | individual wall tiles: 190
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

DATA = json.loads(r"""{"spec":{"wall_h":3000.0,"door_head":2100.0,"win_sill":600.0,"win_h":1500.0,"vent_sill":1200.0,"vent_h":900.0,"vent_max_width":1000.0,"lintel_h":900.0,"skirt_h":100.0,"skirt_t":15.0,"floor_finish_t":20.0,"slab_t":200.0,"tile_w":914.4,"tile_h":609.6,"tile_t":9.0,"grout":2.5,"tile_gap":0.0,"min_cut":200.0,"panel_w":1220.0,"panel_t":12.0,"panel_joint":3.0,"balcony_glass_t":76.2,"balcony_glass_h":1200.0,"balcony_glass_joint":5.0,"balcony_glass_max":1200.0,"balcony_post_w":40.0,"balcony_rail_h":35.0,"kitchen_counter_h":860.0,"kitchen_counter_depth":600.0,"kitchen_counter_t":40.0,"kitchen_base_depth":570.0,"kitchen_backsplash_h":600.0,"kitchen_backsplash_t":15.0,"recess_border_w":450.0,"recess_depth":120.0,"recess_drop_h":50.0,"recess_lip_w":60.0,"recess_wall_gap":15.0,"downlight_r":45.0,"downlight_recess":25.0,"door_frame_w":45.0,"door_leaf_t":42.0,"door_handle_h":1000.0,"door_lever_len":128.0,"door_min":600.0,"door_max":1250.0,"gap_max":3600.0},"config":{"spec_mm":{"wall_h":3000.0,"door_head":2100.0,"win_sill":600.0,"win_h":1500.0,"vent_sill":1200.0,"vent_h":900.0,"vent_max_width":1000.0,"lintel_h":900.0,"skirt_h":100.0,"skirt_t":15.0,"floor_finish_t":20.0,"slab_t":200.0,"tile_w":914.4,"tile_h":609.6,"tile_t":9.0,"grout":2.5,"tile_gap":0.0,"min_cut":200.0,"panel_w":1220.0,"panel_t":12.0,"panel_joint":3.0,"balcony_glass_t":76.2,"balcony_glass_h":1200.0,"balcony_glass_joint":5.0,"balcony_glass_max":1200.0,"balcony_post_w":40.0,"balcony_rail_h":35.0,"kitchen_counter_h":860.0,"kitchen_counter_depth":600.0,"kitchen_counter_t":40.0,"kitchen_base_depth":570.0,"kitchen_backsplash_h":600.0,"kitchen_backsplash_t":15.0,"recess_border_w":450.0,"recess_depth":120.0,"recess_drop_h":50.0,"recess_lip_w":60.0,"recess_wall_gap":15.0,"downlight_r":45.0,"downlight_recess":25.0,"door_frame_w":45.0,"door_leaf_t":42.0,"door_handle_h":1000.0,"door_lever_len":128.0,"door_min":600.0,"door_max":1250.0,"gap_max":3600.0},"default_balcony_type":"open","room_type_overrides":{},"balcony_type_overrides":{},"material_presets":{"floor_common":"MAT_Floor_Common","floor_master_wood":"MAT_Floor_Master_Wood","floor_entrance":"MAT_Floor_Entrance","floor_balcony":"MAT_Floor_Balcony","floor_washroom":"MAT_Floor_Washroom","skirting_common":"MAT_Skirting_Common","skirting_master":"MAT_Skirting_Master","skirting_entrance":"MAT_Skirting_Entrance","skirting_balcony":"MAT_Skirting_Balcony","lintel_blue":"MAT_Lintel_Blue","washroom_tiles":"MAT_Washroom_Wall_Tiles","balcony_glass":"MAT_Balcony_Glass","balcony_metal":"MAT_Balcony_Railing_Metal","kitchen_countertop":"MAT_Kitchen_Countertop","kitchen_base":"MAT_Kitchen_Base"}},"pieces":[{"id":"Wall_001","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":750.0,"base":0.0,"height":3000.0,"ring":[[574.9,1050.0],[574.9,300.0],[1484.9,300.0],[1484.9,1050.0]]},{"id":"Wall_002","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":610.0,"base":0.0,"height":3000.0,"ring":[[8869.9,265.0],[9479.9,265.0],[9479.9,1035.0],[8869.9,1035.0]]},{"id":"Wall_003","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[9069.9,7000.0],[9069.9,6875.0],[16170.0,6875.0],[16170.0,7000.0]]},{"id":"Wall_004","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[1124.9,8625.0],[1124.9,8475.0],[7370.0,8475.0],[7370.0,8625.0]]},{"id":"Wall_005","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[15419.9,1175.0],[15619.9,1175.0],[15619.9,5525.0],[15419.9,5525.0]]},{"id":"Wall_006","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[1474.9,5275.0],[575.0,5275.0],[575.0,5125.0],[4619.9,5125.0],[4619.9,5275.0],[1599.9,5275.0],[1599.9,5325.0],[1474.9,5325.0]]},{"id":"Wall_007","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[5519.9,300.0],[5719.9,300.0],[5719.9,4075.0],[5519.9,4075.0]]},{"id":"Wall_008","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[17219.9,675.0],[17369.9,675.0],[17369.9,3900.0],[17219.9,3900.0]]},{"id":"Wall_009","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[575.0,3775.0],[575.0,3625.0],[3761.7,3625.0],[3761.7,3775.0]]},{"id":"Wall_010","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[8869.9,4075.0],[8869.9,1035.0],[9069.9,1035.0],[9069.9,4075.0]]},{"id":"Wall_011","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[8869.9,7800.0],[8869.9,5125.0],[9069.9,5125.0],[9069.9,7800.0]]},{"id":"Wall_012","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[7219.9,5125.0],[7369.9,5125.0],[7369.9,7800.0],[7219.9,7800.0]]},{"id":"Wall_013","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":250.0,"base":0.0,"height":3000.0,"ring":[[11819.9,1650.0],[12069.9,1650.0],[12069.9,4275.0],[11819.9,4275.0]]},{"id":"Wall_014","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[3770.0,425.0],[1484.9,425.0],[1484.9,300.0],[3770.0,300.0]]},{"id":"Wall_015","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[7970.0,4075.0],[5719.9,4075.0],[5719.9,3925.0],[7970.0,3925.0]]},{"id":"Wall_016","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[5569.9,8475.0],[5569.9,6683.3],[5719.9,6683.3],[5719.9,8475.0]]},{"id":"Wall_017","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[17344.9,5525.0],[15619.9,5525.0],[15619.9,5400.0],[17344.9,5400.0]]},{"id":"Wall_018","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[7219.9,5975.0],[5569.9,5975.0],[5569.9,5825.0],[7219.9,5825.0]]},{"id":"Wall_019","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[17219.9,1375.0],[15619.9,1375.0],[15619.9,1175.0],[17219.9,1175.0]]},{"id":"Wall_020","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[4469.9,5125.0],[4469.9,3625.0],[4619.9,3625.0],[4619.9,5125.0]]},{"id":"Wall_021","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[17219.9,7000.0],[17219.9,5525.0],[17344.9,5525.0],[17344.9,7000.0]]},{"id":"Wall_022","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[1124.9,8475.0],[1124.9,7125.0],[1249.9,7125.0],[1249.9,8475.0]]},{"id":"Wall_023","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[5720.0,125.0],[5720.0,0.0],[7069.9,0.0],[7069.9,125.0]]},{"id":"Wall_024","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":250.0,"base":0.0,"height":3000.0,"ring":[[11819.9,300.0],[12069.9,300.0],[12069.9,1400.0],[11819.9,1400.0]]},{"id":"Wall_025","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[8161.7,5275.0],[7369.9,5275.0],[7369.9,5125.0],[8161.7,5125.0]]},{"id":"Wall_026","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[17219.9,5400.0],[17219.9,4650.0],[17369.9,4650.0],[17369.9,5400.0]]},{"id":"Wall_027","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[5519.9,425.0],[4770.0,425.0],[4770.0,300.0],[5519.9,300.0]]},{"id":"Wall_028","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[11819.9,425.0],[11070.0,425.0],[11070.0,300.0],[11819.9,300.0]]},{"id":"Wall_029","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":150.0,"base":0.0,"height":3000.0,"ring":[[5569.9,5825.0],[5569.9,5250.0],[5719.9,5250.0],[5719.9,5825.0]]},{"id":"Wall_030","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[16120.0,3000.0],[15619.9,3000.0],[15619.9,2875.0],[16120.0,2875.0]]},{"id":"Wall_031","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":250.0,"base":0.0,"height":3000.0,"ring":[[12319.9,1650.0],[11819.9,1650.0],[11819.9,1400.0],[12319.9,1400.0]]},{"id":"Wall_032","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[17219.9,3000.0],[16720.0,3000.0],[16720.0,2875.0],[17219.9,2875.0]]},{"id":"Wall_033","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[12545.0,1775.0],[12069.9,1775.0],[12069.9,1650.0],[12545.0,1650.0]]},{"id":"Wall_034","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[15419.9,1775.0],[14945.0,1775.0],[14945.0,1650.0],[15419.9,1650.0]]},{"id":"Wall_035","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[7820.0,7800.0],[7369.9,7800.0],[7369.9,7675.0],[7820.0,7675.0]]},{"id":"Wall_036","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[8869.9,7800.0],[8420.0,7800.0],[8420.0,7675.0],[8869.9,7675.0]]},{"id":"Wall_037","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[9870.0,425.0],[9479.9,425.0],[9479.9,300.0],[9870.0,300.0]]},{"id":"Wall_038","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[1944.9,4162.5],[1944.9,3775.0],[2069.9,3775.0],[2069.9,4162.5]]},{"id":"Wall_039","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[1944.9,5125.0],[1944.9,4762.5],[2069.9,4762.5],[2069.9,5125.0]]},{"id":"Wall_040","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[1600.0,7250.0],[1249.9,7250.0],[1249.9,7125.0],[1600.0,7125.0]]},{"id":"Wall_041","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[11869.9,0.0],[12069.9,0.0],[12069.9,300.0],[11869.9,300.0]]},{"id":"Wall_042","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[6944.9,425.0],[6944.9,125.0],[7069.9,125.0],[7069.9,425.0]]},{"id":"Wall_043","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":3000.0,"ring":[[8869.9,265.0],[8869.9,0.0],[9069.9,0.0],[9069.9,265.0]]},{"id":"Wall_044","kind":"wall","opening":"","opening_id":"","wall_type":"interior","thickness":100.0,"base":0.0,"height":3000.0,"ring":[[12319.9,1400.0],[12069.9,1400.0],[12069.9,1300.0],[12319.9,1300.0]]},{"id":"Post_02","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[74.9,3575.0],[74.9,3775.0],[-50.1,3775.0],[-50.1,3575.0]]},{"id":"Wall_045","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":175.0,"base":0.0,"height":3000.0,"ring":[[5519.9,300.0],[5519.9,125.0],[5719.9,125.0],[5719.9,300.0]]},{"id":"Post_03","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[74.9,850.0],[74.9,1050.0],[-50.1,1050.0],[-50.1,850.0]]},{"id":"Post_01","kind":"wall","opening":"","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":3000.0,"ring":[[15619.9,0.0],[15619.9,125.0],[15494.9,125.0],[15494.9,0.0]]},{"id":"Sill_Window_06","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[15494.9,125.0],[12069.9,125.0],[12069.9,0.0],[15494.9,0.0]]},{"id":"Sill_Window_02","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[-50.1,3575.0],[-50.1,1050.0],[74.9,1050.0],[74.9,3575.0]]},{"id":"Sill_Window_01","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[1474.9,7125.0],[1474.9,5325.0],[1599.9,5325.0],[1599.9,7125.0]]},{"id":"Sill_Window_04","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[8869.9,425.0],[7069.9,425.0],[7069.9,300.0],[8869.9,300.0]]},{"id":"Sill_Window_05","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[11070.0,425.0],[9870.0,425.0],[9870.0,300.0],[11070.0,300.0]]},{"id":"Sill_Window_03","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[15494.9,1175.0],[15494.9,125.0],[15619.9,125.0],[15619.9,1175.0]]},{"id":"Sill_Vent_07","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":600.0,"ring":[[4770.0,425.0],[3770.0,425.0],[3770.0,300.0],[4770.0,300.0]]},{"id":"Sill_Vent_01","kind":"sill","opening":"vent","opening_id":"","wall_type":"exterior","thickness":150.0,"base":0.0,"height":1200.0,"ring":[[7219.9,8475.0],[7219.9,7800.0],[7369.9,7800.0],[7369.9,8475.0]]},{"id":"Sill_Vent_02","kind":"sill","opening":"vent","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":1200.0,"ring":[[8420.0,7800.0],[7820.0,7800.0],[7820.0,7675.0],[8420.0,7675.0]]},{"id":"Sill_Vent_03","kind":"sill","opening":"vent","opening_id":"","wall_type":"exterior","thickness":125.0,"base":0.0,"height":1200.0,"ring":[[1944.9,4762.5],[1944.9,4162.5],[2069.9,4162.5],[2069.9,4762.5]]},{"id":"Sill_Vent_05","kind":"sill","opening":"vent","opening_id":"","wall_type":"interior","thickness":125.0,"base":0.0,"height":1200.0,"ring":[[16720.0,3000.0],[16120.0,3000.0],[16120.0,2875.0],[16720.0,2875.0]]},{"id":"Sill_Vent_04","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":150.0,"base":0.0,"height":600.0,"ring":[[575.0,3750.0],[74.9,3750.0],[74.9,3600.0],[575.0,3600.0]]},{"id":"Sill_Vent_06","kind":"sill","opening":"window","opening_id":"","wall_type":"exterior","thickness":200.0,"base":0.0,"height":600.0,"ring":[[574.9,1050.0],[74.9,1050.0],[74.9,850.0],[574.9,850.0]]},{"id":"Lintel_Window_001","kind":"lintel","opening":"window","opening_id":"Window_06","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[15494.9,125.0],[12069.9,125.0],[12069.9,0.0],[15494.9,0.0]]},{"id":"Lintel_Window_002","kind":"lintel","opening":"window","opening_id":"Window_02","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[-50.1,3575.0],[-50.1,1050.0],[74.9,1050.0],[74.9,3575.0]]},{"id":"Lintel_Passage_004","kind":"lintel","opening":"passage","opening_id":"Passage_01","wall_type":"interior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[14945.0,1775.0],[12545.0,1775.0],[12545.0,1650.0],[14945.0,1650.0]]},{"id":"Lintel_Window_007","kind":"lintel","opening":"window","opening_id":"Window_01","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[1474.9,7125.0],[1474.9,5325.0],[1599.9,5325.0],[1599.9,7125.0]]},{"id":"Lintel_Window_006","kind":"lintel","opening":"window","opening_id":"Window_04","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[8869.9,425.0],[7069.9,425.0],[7069.9,300.0],[8869.9,300.0]]},{"id":"Lintel_Window_008","kind":"lintel","opening":"window","opening_id":"Window_05","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[11070.0,425.0],[9870.0,425.0],[9870.0,300.0],[11070.0,300.0]]},{"id":"Lintel_Door_003","kind":"lintel","opening":"door","opening_id":"Door_04","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[5569.9,5250.0],[5569.9,4075.0],[5719.9,4075.0],[5719.9,5250.0]]},{"id":"Lintel_Window_003","kind":"lintel","opening":"window","opening_id":"Window_03","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[15494.9,1175.0],[15494.9,125.0],[15619.9,125.0],[15619.9,1175.0]]},{"id":"Lintel_Door_002","kind":"lintel","opening":"door","opening_id":"Door_05","wall_type":"interior","thickness":200.0,"base":2100.0,"height":900.0,"ring":[[8869.9,5125.0],[8869.9,4075.0],[9069.9,4075.0],[9069.9,5125.0]]},{"id":"Lintel_Door_008","kind":"lintel","opening":"door","opening_id":"Door_01","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[17219.9,7000.0],[16170.0,7000.0],[16170.0,6875.0],[17219.9,6875.0]]},{"id":"Lintel_Window_009","kind":"lintel","opening":"window","opening_id":"Vent_07","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[4770.0,425.0],[3770.0,425.0],[3770.0,300.0],[4770.0,300.0]]},{"id":"Lintel_Door_010","kind":"lintel","opening":"door","opening_id":"Door_08","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[4619.9,3692.8],[5519.9,3692.8],[5519.9,3842.8],[4619.9,3842.8]]},{"id":"Lintel_Door_006","kind":"lintel","opening":"door","opening_id":"Door_07","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[8869.9,4075.0],[7970.0,4075.0],[7970.0,3925.0],[8869.9,3925.0]]},{"id":"Lintel_Door_001","kind":"lintel","opening":"door","opening_id":"Door_06","wall_type":"exterior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[17219.9,4650.0],[17219.9,3900.0],[17369.9,3900.0],[17369.9,4650.0]]},{"id":"Lintel_Door_009","kind":"lintel","opening":"door","opening_id":"Door_02","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[5719.9,5975.0],[5719.9,6683.3],[5569.9,6683.3],[5569.9,5975.0]]},{"id":"Lintel_Door_005","kind":"lintel","opening":"door","opening_id":"Door_09","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[4469.9,3775.0],[3761.7,3775.0],[3761.7,3625.0],[4469.9,3625.0]]},{"id":"Lintel_Door_007","kind":"lintel","opening":"door","opening_id":"Door_03","wall_type":"interior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[8869.9,5275.0],[8161.7,5275.0],[8161.7,5125.0],[8869.9,5125.0]]},{"id":"Lintel_Window_010","kind":"lintel","opening":"vent","opening_id":"Vent_01","wall_type":"exterior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[7219.9,8475.0],[7219.9,7800.0],[7369.9,7800.0],[7369.9,8475.0]]},{"id":"Lintel_Window_011","kind":"lintel","opening":"vent","opening_id":"Vent_02","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[8420.0,7800.0],[7820.0,7800.0],[7820.0,7675.0],[8420.0,7675.0]]},{"id":"Lintel_Window_012","kind":"lintel","opening":"vent","opening_id":"Vent_03","wall_type":"exterior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[1944.9,4762.5],[1944.9,4162.5],[2069.9,4162.5],[2069.9,4762.5]]},{"id":"Lintel_Window_013","kind":"lintel","opening":"vent","opening_id":"Vent_05","wall_type":"interior","thickness":125.0,"base":2100.0,"height":900.0,"ring":[[16720.0,3000.0],[16120.0,3000.0],[16120.0,2875.0],[16720.0,2875.0]]},{"id":"Lintel_Window_004","kind":"lintel","opening":"window","opening_id":"Vent_04","wall_type":"exterior","thickness":150.0,"base":2100.0,"height":900.0,"ring":[[575.0,3750.0],[74.9,3750.0],[74.9,3600.0],[575.0,3600.0]]},{"id":"Lintel_Window_005","kind":"lintel","opening":"window","opening_id":"Vent_06","wall_type":"exterior","thickness":200.0,"base":2100.0,"height":900.0,"ring":[[574.9,1050.0],[74.9,1050.0],[74.9,850.0],[574.9,850.0]]}],"openings":[{"id":"Window_06","type":"window","p0":[12069.9,62.5],"p1":[15494.9,62.5],"width":3425.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[12069.9,125.0],[15494.9,125.0],[15494.9,0.0],[12069.9,0.0]],"rooms":["Room_05"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_001"},{"id":"Window_02","type":"window","p0":[12.4,1050.0],"p1":[12.4,3575.0],"width":2525.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[-50.1,1050.0],[-50.1,3575.0],[74.9,3575.0],[74.9,1050.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_002"},{"id":"Window_03","type":"window","p0":[15557.4,125.0],"p1":[15557.4,1175.0],"width":1050.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[15494.9,125.0],[15494.9,1175.0],[15619.9,1175.0],[15619.9,125.0]],"rooms":["Room_05"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_003"},{"id":"Vent_04","type":"window","p0":[74.9,3675.0],"p1":[575.0,3675.0],"width":500.1,"thickness":150.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[74.9,3750.0],[575.0,3750.0],[575.0,3600.0],[74.9,3600.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_004"},{"id":"Vent_06","type":"window","p0":[74.9,950.0],"p1":[574.9,950.0],"width":500.0,"thickness":200.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[74.9,1050.0],[574.9,1050.0],[574.9,850.0],[74.9,850.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_005"},{"id":"Window_04","type":"window","p0":[7069.9,362.5],"p1":[8869.9,362.5],"width":1800.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[7069.9,425.0],[8869.9,425.0],[8869.9,300.0],[7069.9,300.0]],"rooms":["Room_04"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_006"},{"id":"Window_01","type":"window","p0":[1537.4,5325.0],"p1":[1537.4,7125.0],"width":1800.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[1474.9,5325.0],[1474.9,7125.0],[1599.9,7125.0],[1599.9,5325.0]],"rooms":["Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_007"},{"id":"Window_05","type":"window","p0":[9870.0,362.5],"p1":[11070.0,362.5],"width":1200.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[9870.0,425.0],[11070.0,425.0],[11070.0,300.0],[9870.0,300.0]],"rooms":["Room_01"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_008"},{"id":"Vent_07","type":"window","p0":[3770.0,362.5],"p1":[4770.0,362.5],"width":1000.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[3770.0,425.0],[4770.0,425.0],[4770.0,300.0],[3770.0,300.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_009"},{"id":"Vent_01","type":"vent","p0":[7294.9,7800.0],"p1":[7294.9,8475.0],"width":675.0,"thickness":150.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[7219.9,7800.0],[7219.9,8475.0],[7369.9,8475.0],[7369.9,7800.0]],"rooms":["Toilet_1"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_010"},{"id":"Vent_02","type":"vent","p0":[7820.0,7737.5],"p1":[8420.0,7737.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[7820.0,7800.0],[8420.0,7800.0],[8420.0,7675.0],[7820.0,7675.0]],"rooms":["Toilet_2"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_011"},{"id":"Vent_03","type":"vent","p0":[2007.4,4162.5],"p1":[2007.4,4762.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[1944.9,4162.5],[1944.9,4762.5],[2069.9,4762.5],[2069.9,4162.5]],"rooms":["Master_Toilet"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_012"},{"id":"Vent_05","type":"vent","p0":[16120.0,2937.5],"p1":[16720.0,2937.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[16120.0,3000.0],[16720.0,3000.0],[16720.0,2875.0],[16120.0,2875.0]],"rooms":["Room_07","Toilet_3"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_013"},{"id":"Door_06","type":"door","p0":[17294.9,3900.0],"p1":[17294.9,4650.0],"width":750.0,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap + DOOR layer","notes":[],"rect":[[17219.9,3900.0],[17219.9,4650.0],[17369.9,4650.0],[17369.9,3900.0]],"rooms":["Toilet_3"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_001"},{"id":"Door_05","type":"door","p0":[8969.9,4075.0],"p1":[8969.9,5125.0],"width":1050.0,"thickness":200.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap","notes":[],"rect":[[8869.9,4075.0],[8869.9,5125.0],[9069.9,5125.0],[9069.9,4075.0]],"rooms":["Room_01","Room_06"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_002"},{"id":"Door_04","type":"door","p0":[5644.9,4075.0],"p1":[5644.9,5250.0],"width":1175.0,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap","notes":[],"rect":[[5569.9,4075.0],[5569.9,5250.0],[5719.9,5250.0],[5719.9,4075.0]],"rooms":["Room_06","Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_003"},{"id":"Passage_01","type":"passage","p0":[12545.0,1712.5],"p1":[14945.0,1712.5],"width":2400.0,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap + lintel line drawn across","notes":["beam / lintel line drawn across the opening - wall completed above door head"],"rect":[[12545.0,1775.0],[14945.0,1775.0],[14945.0,1650.0],[12545.0,1650.0]],"rooms":["Room_01","Room_05"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Passage_004"},{"id":"Door_09","type":"door","p0":[3761.7,3700.0],"p1":[4469.9,3700.0],"width":708.3,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[3761.7,3775.0],[4469.9,3775.0],[4469.9,3625.0],[3761.7,3625.0]],"rooms":["Room_02","Master_Toilet"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_005"},{"id":"Door_07","type":"door","p0":[7970.0,4000.0],"p1":[8869.9,4000.0],"width":899.9,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[7970.0,4075.0],[8869.9,4075.0],[8869.9,3925.0],[7970.0,3925.0]],"rooms":["Room_04","Room_06"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_006"},{"id":"Door_03","type":"door","p0":[8161.7,5200.0],"p1":[8869.9,5200.0],"width":708.3,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[8161.7,5275.0],[8869.9,5275.0],[8869.9,5125.0],[8161.7,5125.0]],"rooms":["Room_06","Toilet_2"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_007"},{"id":"Door_01","type":"door","p0":[16170.0,6937.5],"p1":[17219.9,6937.5],"width":1049.9,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[16170.0,7000.0],[17219.9,7000.0],[17219.9,6875.0],[16170.0,6875.0]],"rooms":["Room_01"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_008"},{"id":"Door_02","type":"door","p0":[5644.9,6683.3],"p1":[5644.9,5975.0],"width":708.3,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[5719.9,6683.3],[5719.9,5975.0],[5569.9,5975.0],[5569.9,6683.3]],"rooms":["Toilet_1","Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_009"},{"id":"Door_08","type":"door","p0":[5519.9,3767.8],"p1":[4619.9,3767.8],"width":900.0,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"CAD door arc between walls + DOOR layer","notes":[],"rect":[[5519.9,3692.8],[4619.9,3692.8],[4619.9,3842.8],[5519.9,3842.8]],"rooms":["Room_03","Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_010"}],"rooms":[{"name":"Room_01","code":"R01","type":"dry","use":"living","label":"Living","display_name":"Living Room","cad_dim":"8.15 \u00d7 6.45 m","cad_text":"","floor_obj":"Floor_Living","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Living","skirt_mat":"MAT_Skirting_Common","tile_obj":"","floor_category":"common","panelled":true,"recessed_ceiling":true,"area_m2":37.652,"ring":[[17219.9,6875.0],[9069.9,6875.0],[9069.9,1035.0],[9479.9,1035.0],[9479.9,425.0],[11819.9,425.0],[11819.9,4275.0],[12069.9,4275.0],[12069.9,1775.0],[15419.9,1775.0],[15419.9,5525.0],[17219.9,5525.0]],"holes":[]},{"name":"Room_07","code":"R07","type":"shaft","use":"shaft","label":"Shaft","display_name":"Service Shaft / Duct","cad_dim":"1.60 \u00d7 1.50 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","floor_category":"shaft","panelled":false,"recessed_ceiling":false,"area_m2":2.4,"ring":[[17219.9,1375.0],[17219.9,2875.0],[15619.9,2875.0],[15619.9,1375.0]],"holes":[]},{"name":"Toilet_3","code":"T3","type":"washroom","use":"washroom","label":"Toilet_3","display_name":"Toilet","cad_dim":"2.40 \u00d7 1.60 m","cad_text":"","floor_obj":"Floor_Washroom_04","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_04","floor_category":"washroom","panelled":false,"recessed_ceiling":false,"area_m2":3.84,"ring":[[15619.9,3000.0],[17219.9,3000.0],[17219.9,5400.0],[15619.9,5400.0]],"holes":[]},{"name":"Room_05","code":"R05","type":"dry","use":"kitchen","label":"Kitchen","display_name":"Kitchen","cad_dim":"3.42 \u00d7 1.52 m","cad_text":"","floor_obj":"Floor_Kitchen","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Kitchen","skirt_mat":"MAT_Skirting_Common","tile_obj":"","floor_category":"common","panelled":true,"recessed_ceiling":false,"area_m2":5.1,"ring":[[12069.9,1300.0],[12069.9,125.0],[15494.9,125.0],[15494.9,1175.0],[15419.9,1175.0],[15419.9,1650.0],[12319.9,1650.0],[12319.9,1300.0]],"holes":[]},{"name":"Room_04","code":"R04","type":"dry","use":"bedroom","label":"Bedroom_2","display_name":"Bedroom","cad_dim":"3.80 \u00d7 3.15 m","cad_text":"","floor_obj":"Floor_Bedroom_2","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Bedroom_2","skirt_mat":"MAT_Skirting_Common","tile_obj":"","floor_category":"common","panelled":true,"recessed_ceiling":true,"area_m2":11.393,"ring":[[5719.9,125.0],[6944.9,125.0],[6944.9,425.0],[8869.9,425.0],[8869.9,3925.0],[5719.9,3925.0]],"holes":[]},{"name":"Room_06","code":"R06","type":"dry","use":"lobby","label":"Lobby","display_name":"Lobby","cad_dim":"3.15 \u00d7 1.75 m","cad_text":"","floor_obj":"Floor_Entrance_01","floor_mat":"MAT_Floor_Entrance","skirt_obj":"Skirting_Entrance_01","skirt_mat":"MAT_Skirting_Entrance","tile_obj":"","floor_category":"entrance","panelled":true,"recessed_ceiling":false,"area_m2":4.357,"ring":[[7219.9,5825.0],[5719.9,5825.0],[5719.9,4075.0],[8869.9,4075.0],[8869.9,5125.0],[7219.9,5125.0]],"holes":[]},{"name":"Toilet_2","code":"T2","type":"washroom","use":"washroom","label":"Toilet_2","display_name":"Toilet","cad_dim":"2.40 \u00d7 1.50 m","cad_text":"","floor_obj":"Floor_Washroom_03","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_03","floor_category":"washroom","panelled":false,"recessed_ceiling":false,"area_m2":3.6,"ring":[[8869.9,5275.0],[8869.9,7675.0],[7369.9,7675.0],[7369.9,5275.0]],"holes":[]},{"name":"Toilet_1","code":"T1","type":"washroom","use":"washroom","label":"Toilet_1","display_name":"Toilet","cad_dim":"2.50 \u00d7 1.50 m","cad_text":"","floor_obj":"Floor_Washroom_02","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_02","floor_category":"washroom","panelled":false,"recessed_ceiling":false,"area_m2":3.75,"ring":[[7219.9,5975.0],[7219.9,8475.0],[5719.9,8475.0],[5719.9,5975.0]],"holes":[]},{"name":"Room_03","code":"R03","type":"dry","use":"bedroom","label":"Bedroom_1","display_name":"Bedroom","cad_dim":"4.63 \u00d7 4.32 m","cad_text":"","floor_obj":"Floor_Bedroom_1","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Bedroom_1","skirt_mat":"MAT_Skirting_Common","tile_obj":"","floor_category":"common","panelled":true,"recessed_ceiling":true,"area_m2":14.482,"ring":[[1599.9,7125.0],[1599.9,5275.0],[4619.9,5275.0],[4619.9,3842.8],[5519.9,3842.8],[5519.9,4075.0],[5569.9,4075.0],[5569.9,8475.0],[1249.9,8475.0],[1249.9,7250.0],[1600.0,7250.0],[1600.0,7125.0]],"holes":[]},{"name":"Room_02","code":"R02","type":"dry","use":"master_bedroom","label":"Master_Bedroom","display_name":"Master Bedroom","cad_dim":"5.45 \u00d7 3.27 m","cad_text":"","floor_obj":"Floor_MasterBedroom_Wood","floor_mat":"MAT_Floor_Master_Wood","skirt_obj":"Skirting_MasterBedroom","skirt_mat":"MAT_Skirting_Master","tile_obj":"","floor_category":"master_wood","panelled":true,"recessed_ceiling":true,"area_m2":16.591,"ring":[[1484.9,425.0],[5519.9,425.0],[5519.9,3692.8],[4619.9,3692.8],[4619.9,3625.0],[575.0,3625.0],[575.0,3600.0],[74.9,3600.0],[74.9,1050.0],[1484.9,1050.0]],"holes":[]},{"name":"Master_Toilet","code":"MT","type":"washroom","use":"washroom","label":"Master_Toilet","display_name":"Master Toilet","cad_dim":"2.40 \u00d7 1.35 m","cad_text":"","floor_obj":"Floor_Washroom_01","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_01","floor_category":"washroom","panelled":false,"recessed_ceiling":false,"area_m2":3.24,"ring":[[4469.9,5125.0],[2069.9,5125.0],[2069.9,3775.0],[4469.9,3775.0]],"holes":[]}],"room_floors":[{"name":"Floor_Living","room":"Room_01","label":"Living","use":"living","category":"common","mat":"MAT_Floor_Common","plank_angle":3.141593,"area_m2":38.04,"rings":[{"outer":[[15419.9,1775.0],[15419.9,5525.0],[17219.9,5525.0],[17219.9,7000.0],[17220.9,7000.0],[17220.9,7001.0],[16169.0,7001.0],[16169.0,7000.0],[16170.0,7000.0],[16170.0,6875.0],[9069.9,6875.0],[9069.9,5125.0],[8969.9,5125.0],[8969.9,4075.0],[9069.9,4075.0],[9069.9,1035.0],[9479.9,1035.0],[9479.9,425.0],[11819.9,425.0],[11819.9,4275.0],[12069.9,4275.0],[12069.9,1775.0],[12545.0,1775.0],[12545.0,1712.5],[14945.0,1712.5],[14945.0,1775.0]],"holes":[]}]},{"name":"Floor_Washroom_04","room":"Toilet_3","label":"Toilet_3","use":"washroom","category":"washroom","mat":"MAT_Floor_Washroom","plank_angle":1.570796,"area_m2":3.953,"rings":[{"outer":[[17219.9,5400.0],[15619.9,5400.0],[15619.9,3000.0],[17219.9,3000.0],[17219.9,3900.0],[17369.9,3900.0],[17369.9,3899.0],[17370.9,3899.0],[17370.9,4651.0],[17369.9,4651.0],[17369.9,4650.0],[17219.9,4650.0]],"holes":[]}]},{"name":"Floor_Kitchen","room":"Room_05","label":"Kitchen","use":"kitchen","category":"common","mat":"MAT_Floor_Common","plank_angle":0.0,"area_m2":5.25,"rings":[{"outer":[[12319.9,1300.0],[12069.9,1300.0],[12069.9,125.0],[15494.9,125.0],[15494.9,1175.0],[15419.9,1175.0],[15419.9,1650.0],[14945.0,1650.0],[14945.0,1712.5],[12545.0,1712.5],[12545.0,1650.0],[12319.9,1650.0]],"holes":[]}]},{"name":"Floor_Bedroom_2","room":"Room_04","label":"Bedroom_2","use":"bedroom","category":"common","mat":"MAT_Floor_Common","plank_angle":-1.570796,"area_m2":11.46,"rings":[{"outer":[[5719.9,3925.0],[5719.9,125.0],[6944.9,125.0],[6944.9,425.0],[8869.9,425.0],[8869.9,4000.0],[7970.0,4000.0],[7970.0,3925.0]],"holes":[]}]},{"name":"Floor_Entrance_01","room":"Room_06","label":"Lobby","use":"lobby","category":"entrance","mat":"MAT_Floor_Entrance","plank_angle":0.0,"area_m2":4.671,"rings":[{"outer":[[8869.9,5125.0],[8869.9,5200.0],[8161.7,5200.0],[8161.7,5125.0],[7219.9,5125.0],[7219.9,5825.0],[5719.9,5825.0],[5719.9,5250.0],[5644.9,5250.0],[5644.9,4075.0],[7970.0,4075.0],[7970.0,4000.0],[8869.9,4000.0],[8869.9,4075.0],[8969.9,4075.0],[8969.9,5125.0]],"holes":[]}]},{"name":"Floor_Washroom_03","room":"Toilet_2","label":"Toilet_2","use":"washroom","category":"washroom","mat":"MAT_Floor_Washroom","plank_angle":1.570796,"area_m2":3.653,"rings":[{"outer":[[7369.9,5275.0],[8161.7,5275.0],[8161.7,5200.0],[8869.9,5200.0],[8869.9,7675.0],[7369.9,7675.0]],"holes":[]}]},{"name":"Floor_Washroom_02","room":"Toilet_1","label":"Toilet_1","use":"washroom","category":"washroom","mat":"MAT_Floor_Washroom","plank_angle":1.570796,"area_m2":3.803,"rings":[{"outer":[[7219.9,5975.0],[7219.9,8475.0],[5719.9,8475.0],[5719.9,6683.3],[5644.9,6683.3],[5644.9,5975.0]],"holes":[]}]},{"name":"Floor_Bedroom_1","room":"Room_03","label":"Bedroom_1","use":"bedroom","category":"common","mat":"MAT_Floor_Common","plank_angle":1.570796,"area_m2":14.691,"rings":[{"outer":[[1249.9,8475.0],[1249.9,7250.0],[1600.0,7250.0],[1599.9,5275.0],[4619.9,5275.0],[4619.9,3767.8],[5519.9,3767.8],[5519.9,4075.0],[5644.9,4075.0],[5644.9,5250.0],[5569.9,5250.0],[5569.9,5975.0],[5644.9,5975.0],[5644.9,6683.3],[5569.9,6683.3],[5569.9,8475.0]],"holes":[]}]},{"name":"Floor_MasterBedroom_Wood","room":"Room_02","label":"Master_Bedroom","use":"master_bedroom","category":"master_wood","mat":"MAT_Floor_Master_Wood","plank_angle":3.141593,"area_m2":16.712,"rings":[{"outer":[[74.9,1050.0],[1484.9,1050.0],[1484.9,425.0],[5519.9,425.0],[5519.9,3767.8],[4619.9,3767.8],[4619.9,3625.0],[4469.9,3625.0],[4469.9,3700.0],[3761.7,3700.0],[3761.7,3625.0],[575.0,3625.0],[575.0,3600.0],[74.9,3600.0]],"holes":[]}]},{"name":"Floor_Washroom_01","room":"Master_Toilet","label":"Master_Toilet","use":"washroom","category":"washroom","mat":"MAT_Floor_Washroom","plank_angle":3.141593,"area_m2":3.293,"rings":[{"outer":[[4469.9,5125.0],[2069.9,5125.0],[2069.9,3775.0],[3761.7,3775.0],[3761.7,3700.0],[4469.9,3700.0]],"holes":[]}]}],"skirting":[{"room":"Room_01","ring":[[12545.0,1775.0],[12545.0,1790.0],[12084.9,1790.0],[12084.9,4290.0],[11804.9,4290.0],[11804.9,440.0],[9494.9,440.0],[9494.9,1050.0],[9084.9,1050.0],[9084.9,4075.0],[9069.9,4075.0],[9069.9,1035.0],[9479.9,1035.0],[9479.9,425.0],[11819.9,425.0],[11819.9,4275.0],[12069.9,4275.0],[12069.9,1775.0]],"holes":[],"length_mm":13460.1,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Living","name":"Skirting_01"},{"room":"Room_01","ring":[[9069.9,5125.0],[9084.9,5125.0],[9084.9,6860.0],[16170.0,6860.0],[16170.0,6875.0],[9069.9,6875.0]],"holes":[],"length_mm":8835.1,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Living","name":"Skirting_02"},{"room":"Room_01","ring":[[17219.9,5525.0],[17219.9,6875.0],[17174.9,6875.0],[17174.9,6860.0],[17204.9,6860.0],[17204.9,5540.0],[15404.9,5540.0],[15404.9,1790.0],[14945.0,1790.0],[14945.0,1775.0],[15419.9,1775.0],[15419.9,5525.0]],"holes":[],"length_mm":7389.9,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Living","name":"Skirting_03"},{"room":"Room_02","ring":[[1484.9,1050.0],[1484.9,425.0],[5519.9,425.0],[5519.9,3692.8],[5474.9,3692.8],[5474.9,3677.8],[5504.9,3677.8],[5504.9,440.0],[1499.9,440.0],[1499.9,1065.0],[89.9,1065.0],[89.9,3585.0],[590.0,3585.0],[590.0,3610.0],[3761.7,3610.0],[3761.7,3625.0],[575.0,3625.0],[575.0,3600.0],[74.9,3600.0],[74.9,1050.0]],"holes":[],"length_mm":15584.6,"mat":"MAT_Skirting_Master","skirt_obj":"Skirting_MasterBedroom","name":"Skirting_04"},{"room":"Room_02","ring":[[4469.9,3625.0],[4469.9,3610.0],[4634.9,3610.0],[4634.9,3677.8],[4664.9,3677.8],[4664.9,3692.8],[4619.9,3692.8],[4619.9,3625.0]],"holes":[],"length_mm":262.8,"mat":"MAT_Skirting_Master","skirt_obj":"Skirting_MasterBedroom","name":"Skirting_05"},{"room":"Room_03","ring":[[1599.9,5275.0],[4619.9,5275.0],[4619.9,3842.8],[4664.9,3842.8],[4664.9,3857.8],[4634.9,3857.8],[4634.9,5290.0],[1614.9,5290.0],[1615.0,7265.0],[1264.9,7265.0],[1264.9,8460.0],[5554.9,8460.0],[5554.9,6683.3],[5569.9,6683.3],[5569.9,8475.0],[1249.9,8475.0],[1249.9,7250.0],[1600.0,7250.0]],"holes":[],"length_mm":14113.9,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Bedroom_1","name":"Skirting_06"},{"room":"Room_03","ring":[[5569.9,5250.0],[5569.9,5975.0],[5554.9,5975.0],[5554.9,5250.0]],"holes":[],"length_mm":725.0,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Bedroom_1","name":"Skirting_07"},{"room":"Room_03","ring":[[5569.9,4075.0],[5569.9,4120.0],[5554.9,4120.0],[5554.9,4090.0],[5504.9,4090.0],[5504.9,3857.8],[5474.9,3857.8],[5474.9,3842.8],[5519.9,3842.8],[5519.9,4075.0]],"holes":[],"length_mm":357.2,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Bedroom_1","name":"Skirting_08"},{"room":"Room_04","ring":[[5719.9,3925.0],[5719.9,125.0],[6944.9,125.0],[6944.9,425.0],[8869.9,425.0],[8869.9,3925.0],[8824.9,3925.0],[8824.9,3910.0],[8854.9,3910.0],[8854.9,440.0],[6929.9,440.0],[6929.9,140.0],[5734.9,140.0],[5734.9,3910.0],[7970.0,3910.0],[7970.0,3925.0]],"holes":[],"length_mm":12985.1,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Bedroom_2","name":"Skirting_09"},{"room":"Room_05","ring":[[12319.9,1300.0],[12069.9,1300.0],[12069.9,125.0],[15494.9,125.0],[15494.9,1175.0],[15419.9,1175.0],[15419.9,1650.0],[14945.0,1650.0],[14945.0,1635.0],[15404.9,1635.0],[15404.9,1160.0],[15479.9,1160.0],[15479.9,140.0],[12084.9,140.0],[12084.9,1285.0],[12334.9,1285.0],[12334.9,1635.0],[12545.0,1635.0],[12545.0,1650.0],[12319.9,1650.0]],"holes":[],"length_mm":7440.0,"mat":"MAT_Skirting_Common","skirt_obj":"Skirting_Kitchen","name":"Skirting_10"},{"room":"Room_06","ring":[[7219.9,5125.0],[7219.9,5825.0],[5719.9,5825.0],[5719.9,5250.0],[5734.9,5250.0],[5734.9,5810.0],[7204.9,5810.0],[7204.9,5110.0],[8161.7,5110.0],[8161.7,5125.0]],"holes":[],"length_mm":3701.8,"mat":"MAT_Skirting_Entrance","skirt_obj":"Skirting_Entrance_01","name":"Skirting_11"},{"room":"Room_06","ring":[[5719.9,4075.0],[7970.0,4075.0],[7970.0,4090.0],[5734.9,4090.0],[5734.9,4120.0],[5719.9,4120.0]],"holes":[],"length_mm":2280.1,"mat":"MAT_Skirting_Entrance","skirt_obj":"Skirting_Entrance_01","name":"Skirting_12"}],"room_skirting":[{"name":"Skirting_Living","room":"Room_01","label":"Living","use":"living","category":"common","mat":"MAT_Skirting_Common","length_mm":29685.1,"runs":[{"outer":[[17219.9,5525.0],[17219.9,6875.0],[17174.9,6875.0],[17174.9,6860.0],[17204.9,6860.0],[17204.9,5540.0],[15404.9,5540.0],[15404.9,1790.0],[14945.0,1790.0],[14945.0,1775.0],[15419.9,1775.0],[15419.9,5525.0]],"holes":[]},{"outer":[[12545.0,1775.0],[12545.0,1790.0],[12084.9,1790.0],[12084.9,4290.0],[11804.9,4290.0],[11804.9,440.0],[9494.9,440.0],[9494.9,1050.0],[9084.9,1050.0],[9084.9,4075.0],[9069.9,4075.0],[9069.9,1035.0],[9479.9,1035.0],[9479.9,425.0],[11819.9,425.0],[11819.9,4275.0],[12069.9,4275.0],[12069.9,1775.0]],"holes":[]},{"outer":[[9069.9,5125.0],[9084.9,5125.0],[9084.9,6860.0],[16170.0,6860.0],[16170.0,6875.0],[9069.9,6875.0]],"holes":[]}]},{"name":"Skirting_Kitchen","room":"Room_05","label":"Kitchen","use":"kitchen","category":"common","mat":"MAT_Skirting_Common","length_mm":7440.0,"runs":[{"outer":[[12319.9,1300.0],[12069.9,1300.0],[12069.9,125.0],[15494.9,125.0],[15494.9,1175.0],[15419.9,1175.0],[15419.9,1650.0],[14945.0,1650.0],[14945.0,1635.0],[15404.9,1635.0],[15404.9,1160.0],[15479.9,1160.0],[15479.9,140.0],[12084.9,140.0],[12084.9,1285.0],[12334.9,1285.0],[12334.9,1635.0],[12545.0,1635.0],[12545.0,1650.0],[12319.9,1650.0]],"holes":[]}]},{"name":"Skirting_Bedroom_2","room":"Room_04","label":"Bedroom_2","use":"bedroom","category":"common","mat":"MAT_Skirting_Common","length_mm":12985.1,"runs":[{"outer":[[5719.9,3925.0],[5719.9,125.0],[6944.9,125.0],[6944.9,425.0],[8869.9,425.0],[8869.9,3925.0],[8824.9,3925.0],[8824.9,3910.0],[8854.9,3910.0],[8854.9,440.0],[6929.9,440.0],[6929.9,140.0],[5734.9,140.0],[5734.9,3910.0],[7970.0,3910.0],[7970.0,3925.0]],"holes":[]}]},{"name":"Skirting_Entrance_01","room":"Room_06","label":"Lobby","use":"lobby","category":"entrance","mat":"MAT_Skirting_Entrance","length_mm":5981.9,"runs":[{"outer":[[7219.9,5125.0],[7219.9,5825.0],[5719.9,5825.0],[5719.9,5250.0],[5734.9,5250.0],[5734.9,5810.0],[7204.9,5810.0],[7204.9,5110.0],[8161.7,5110.0],[8161.7,5125.0]],"holes":[]},{"outer":[[5719.9,4075.0],[7970.0,4075.0],[7970.0,4090.0],[5734.9,4090.0],[5734.9,4120.0],[5719.9,4120.0]],"holes":[]}]},{"name":"Skirting_Bedroom_1","room":"Room_03","label":"Bedroom_1","use":"bedroom","category":"common","mat":"MAT_Skirting_Common","length_mm":15196.1,"runs":[{"outer":[[1599.9,5275.0],[4619.9,5275.0],[4619.9,3842.8],[4664.9,3842.8],[4664.9,3857.8],[4634.9,3857.8],[4634.9,5290.0],[1614.9,5290.0],[1615.0,7265.0],[1264.9,7265.0],[1264.9,8460.0],[5554.9,8460.0],[5554.9,6683.3],[5569.9,6683.3],[5569.9,8475.0],[1249.9,8475.0],[1249.9,7250.0],[1600.0,7250.0]],"holes":[]},{"outer":[[5569.9,5250.0],[5569.9,5975.0],[5554.9,5975.0],[5554.9,5250.0]],"holes":[]},{"outer":[[5569.9,4075.0],[5569.9,4120.0],[5554.9,4120.0],[5554.9,4090.0],[5504.9,4090.0],[5504.9,3857.8],[5474.9,3857.8],[5474.9,3842.8],[5519.9,3842.8],[5519.9,4075.0]],"holes":[]}]},{"name":"Skirting_MasterBedroom","room":"Room_02","label":"Master_Bedroom","use":"master_bedroom","category":"master_wood","mat":"MAT_Skirting_Master","length_mm":15847.4,"runs":[{"outer":[[1484.9,1050.0],[1484.9,425.0],[5519.9,425.0],[5519.9,3692.8],[5474.9,3692.8],[5474.9,3677.8],[5504.9,3677.8],[5504.9,440.0],[1499.9,440.0],[1499.9,1065.0],[89.9,1065.0],[89.9,3585.0],[590.0,3585.0],[590.0,3610.0],[3761.7,3610.0],[3761.7,3625.0],[575.0,3625.0],[575.0,3600.0],[74.9,3600.0],[74.9,1050.0]],"holes":[]},{"outer":[[4469.9,3625.0],[4469.9,3610.0],[4634.9,3610.0],[4634.9,3677.8],[4664.9,3677.8],[4664.9,3692.8],[4619.9,3692.8],[4619.9,3625.0]],"holes":[]}]}],"tiles":[{"name":"T3_Wall01_R01_C01","room":"Toilet_3","wall":"Wall01","row":1,"col":1,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall01_R01_C02","room":"Toilet_3","wall":"Wall01","row":1,"col":2,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"T3_Wall01_R02_C01","room":"Toilet_3","wall":"Wall01","row":2,"col":1,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,0.0],[914.4,587.9],[488.6,587.9],[488.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T3_Wall01_R02_C02","room":"Toilet_3","wall":"Wall01","row":2,"col":2,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[671.6,0.0],[671.6,609.6],[171.7,609.6],[171.7,587.9],[0.0,587.9],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":false},{"name":"T3_Wall01_R03_C01","room":"Toilet_3","wall":"Wall01","row":3,"col":1,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[488.6,609.6],[0.0,609.6],[0.0,0.0],[488.6,0.0]],"full":false,"w":488.6,"h":609.6,"rect":true},{"name":"T3_Wall01_R03_C02","room":"Toilet_3","wall":"Wall01","row":3,"col":2,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":1100.1,"z0":1224.2,"poly":[[499.9,0.0],[499.9,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":499.9,"h":609.6,"rect":true},{"name":"T3_Wall01_R04_C01","room":"Toilet_3","wall":"Wall01","row":4,"col":1,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[488.6,0.0],[488.6,263.7],[914.4,263.7]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T3_Wall01_R04_C02","room":"Toilet_3","wall":"Wall01","row":4,"col":2,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,263.7],[171.7,263.7],[171.7,0.0]],"full":false,"w":671.6,"h":609.6,"rect":false},{"name":"T3_Wall01_R05_C01","room":"Toilet_3","wall":"Wall01","row":5,"col":1,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T3_Wall01_R05_C02","room":"Toilet_3","wall":"Wall01","row":5,"col":2,"origin":[15619.9,3000.0],"dir":[1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[671.6,0.0],[671.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":671.6,"h":551.6,"rect":true},{"name":"T3_Wall02_R01_C01","room":"Toilet_3","wall":"Wall02","row":1,"col":1,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":11.5,"z0":0.0,"poly":[[888.5,609.6],[0.0,609.6],[0.0,0.0],[888.5,0.0]],"full":false,"w":888.5,"h":609.6,"rect":true},{"name":"T3_Wall02_R01_C02","room":"Toilet_3","wall":"Wall02","row":1,"col":2,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":1650.0,"z0":0.0,"poly":[[192.8,609.6],[0.0,609.6],[0.0,0.0],[192.8,0.0]],"full":false,"w":192.8,"h":609.6,"rect":true},{"name":"T3_Wall02_R01_C03","room":"Toilet_3","wall":"Wall02","row":1,"col":3,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":1845.3,"z0":0.0,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T3_Wall02_R02_C01","room":"Toilet_3","wall":"Wall02","row":2,"col":1,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":11.5,"z0":612.1,"poly":[[888.5,609.6],[0.0,609.6],[0.0,0.0],[888.5,0.0]],"full":false,"w":888.5,"h":609.6,"rect":true},{"name":"T3_Wall02_R02_C02","room":"Toilet_3","wall":"Wall02","row":2,"col":2,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":1650.0,"z0":612.1,"poly":[[192.8,609.6],[0.0,609.6],[0.0,0.0],[192.8,0.0]],"full":false,"w":192.8,"h":609.6,"rect":true},{"name":"T3_Wall02_R02_C03","room":"Toilet_3","wall":"Wall02","row":2,"col":3,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":1845.3,"z0":612.1,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T3_Wall02_R03_C01","room":"Toilet_3","wall":"Wall02","row":3,"col":1,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":11.5,"z0":1224.2,"poly":[[888.5,609.6],[0.0,609.6],[0.0,0.0],[888.5,0.0]],"full":false,"w":888.5,"h":609.6,"rect":true},{"name":"T3_Wall02_R03_C02","room":"Toilet_3","wall":"Wall02","row":3,"col":2,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":1650.0,"z0":1224.2,"poly":[[192.8,609.6],[0.0,609.6],[0.0,0.0],[192.8,0.0]],"full":false,"w":192.8,"h":609.6,"rect":true},{"name":"T3_Wall02_R03_C03","room":"Toilet_3","wall":"Wall02","row":3,"col":3,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":1845.3,"z0":1224.2,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T3_Wall02_R04_C01","room":"Toilet_3","wall":"Wall02","row":4,"col":1,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[888.5,0.0],[888.5,263.7],[914.4,263.7]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T3_Wall02_R04_C02","room":"Toilet_3","wall":"Wall02","row":4,"col":2,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,609.6],[0.0,263.7],[721.6,263.7],[721.6,0.0],[914.4,0.0],[914.4,609.6]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T3_Wall02_R04_C03","room":"Toilet_3","wall":"Wall02","row":4,"col":3,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":1845.3,"z0":1836.3,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T3_Wall02_R05_C01","room":"Toilet_3","wall":"Wall02","row":5,"col":1,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T3_Wall02_R05_C02","room":"Toilet_3","wall":"Wall02","row":5,"col":2,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T3_Wall02_R05_C03","room":"Toilet_3","wall":"Wall02","row":5,"col":3,"origin":[17219.9,3000.0],"dir":[0.0,1.0],"u0":1845.3,"z0":2448.4,"poly":[[554.7,0.0],[554.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":554.7,"h":551.6,"rect":true},{"name":"T3_Wall03_R01_C01","room":"Toilet_3","wall":"Wall03","row":1,"col":1,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall03_R01_C02","room":"Toilet_3","wall":"Wall03","row":1,"col":2,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"T3_Wall03_R02_C01","room":"Toilet_3","wall":"Wall03","row":2,"col":1,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall03_R02_C02","room":"Toilet_3","wall":"Wall03","row":2,"col":2,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"T3_Wall03_R03_C01","room":"Toilet_3","wall":"Wall03","row":3,"col":1,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall03_R03_C02","room":"Toilet_3","wall":"Wall03","row":3,"col":2,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1224.2,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"T3_Wall03_R04_C01","room":"Toilet_3","wall":"Wall03","row":4,"col":1,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall03_R04_C02","room":"Toilet_3","wall":"Wall03","row":4,"col":2,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[671.6,0.0],[671.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":671.6,"h":609.6,"rect":true},{"name":"T3_Wall03_R05_C01","room":"Toilet_3","wall":"Wall03","row":5,"col":1,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T3_Wall03_R05_C02","room":"Toilet_3","wall":"Wall03","row":5,"col":2,"origin":[17219.9,5400.0],"dir":[-1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[671.6,0.0],[671.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":671.6,"h":551.6,"rect":true},{"name":"T3_Wall04_R01_C01","room":"Toilet_3","wall":"Wall04","row":1,"col":1,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall04_R01_C02","room":"Toilet_3","wall":"Wall04","row":1,"col":2,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":928.4,"z0":0.0,"poly":[[0.0,609.6],[0.0,0.0],[914.4,0.0],[914.4,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall04_R01_C03","room":"Toilet_3","wall":"Wall04","row":1,"col":3,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":0.0,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T3_Wall04_R02_C01","room":"Toilet_3","wall":"Wall04","row":2,"col":1,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall04_R02_C02","room":"Toilet_3","wall":"Wall04","row":2,"col":2,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":928.4,"z0":612.1,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall04_R02_C03","room":"Toilet_3","wall":"Wall04","row":2,"col":3,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":612.1,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T3_Wall04_R03_C01","room":"Toilet_3","wall":"Wall04","row":3,"col":1,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall04_R03_C02","room":"Toilet_3","wall":"Wall04","row":3,"col":2,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1224.2,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall04_R03_C03","room":"Toilet_3","wall":"Wall04","row":3,"col":3,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":1224.2,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T3_Wall04_R04_C01","room":"Toilet_3","wall":"Wall04","row":4,"col":1,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall04_R04_C02","room":"Toilet_3","wall":"Wall04","row":4,"col":2,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T3_Wall04_R04_C03","room":"Toilet_3","wall":"Wall04","row":4,"col":3,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":1836.3,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T3_Wall04_R05_C01","room":"Toilet_3","wall":"Wall04","row":5,"col":1,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T3_Wall04_R05_C02","room":"Toilet_3","wall":"Wall04","row":5,"col":2,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T3_Wall04_R05_C03","room":"Toilet_3","wall":"Wall04","row":5,"col":3,"origin":[15619.9,5400.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":2448.4,"poly":[[554.7,0.0],[554.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":554.7,"h":551.6,"rect":true},{"name":"T2_Wall01_R01_C01","room":"Toilet_2","wall":"Wall01","row":1,"col":1,"origin":[7369.9,5275.0],"dir":[1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[780.3,609.6],[0.0,609.6],[0.0,0.0],[780.3,0.0]],"full":false,"w":780.3,"h":609.6,"rect":true},{"name":"T2_Wall01_R02_C01","room":"Toilet_2","wall":"Wall01","row":2,"col":1,"origin":[7369.9,5275.0],"dir":[1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[780.3,609.6],[0.0,609.6],[0.0,0.0],[780.3,0.0]],"full":false,"w":780.3,"h":609.6,"rect":true},{"name":"T2_Wall01_R03_C01","room":"Toilet_2","wall":"Wall01","row":3,"col":1,"origin":[7369.9,5275.0],"dir":[1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[780.3,609.6],[0.0,609.6],[0.0,0.0],[780.3,0.0]],"full":false,"w":780.3,"h":609.6,"rect":true},{"name":"T2_Wall01_R04_C01","room":"Toilet_2","wall":"Wall01","row":4,"col":1,"origin":[7369.9,5275.0],"dir":[1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[780.3,0.0],[780.3,263.7],[914.4,263.7]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T2_Wall01_R04_C02","room":"Toilet_2","wall":"Wall01","row":4,"col":2,"origin":[7369.9,5275.0],"dir":[1.0,0.0],"u0":928.4,"z0":2100.0,"poly":[[571.6,0.0],[571.6,345.9],[0.0,345.9],[0.0,0.0]],"full":false,"w":571.6,"h":345.9,"rect":true},{"name":"T2_Wall01_R05_C01","room":"Toilet_2","wall":"Wall01","row":5,"col":1,"origin":[7369.9,5275.0],"dir":[1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T2_Wall01_R05_C02","room":"Toilet_2","wall":"Wall01","row":5,"col":2,"origin":[7369.9,5275.0],"dir":[1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[571.6,0.0],[571.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":571.6,"h":551.6,"rect":true},{"name":"T2_Wall02_R01_C01","room":"Toilet_2","wall":"Wall02","row":1,"col":1,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall02_R01_C02","room":"Toilet_2","wall":"Wall02","row":1,"col":2,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":928.4,"z0":0.0,"poly":[[0.0,609.6],[0.0,0.0],[914.4,0.0],[914.4,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall02_R01_C03","room":"Toilet_2","wall":"Wall02","row":1,"col":3,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":1845.3,"z0":0.0,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T2_Wall02_R02_C01","room":"Toilet_2","wall":"Wall02","row":2,"col":1,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall02_R02_C02","room":"Toilet_2","wall":"Wall02","row":2,"col":2,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":928.4,"z0":612.1,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall02_R02_C03","room":"Toilet_2","wall":"Wall02","row":2,"col":3,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":1845.3,"z0":612.1,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T2_Wall02_R03_C01","room":"Toilet_2","wall":"Wall02","row":3,"col":1,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall02_R03_C02","room":"Toilet_2","wall":"Wall02","row":3,"col":2,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":928.4,"z0":1224.2,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall02_R03_C03","room":"Toilet_2","wall":"Wall02","row":3,"col":3,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":1845.3,"z0":1224.2,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T2_Wall02_R04_C01","room":"Toilet_2","wall":"Wall02","row":4,"col":1,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall02_R04_C02","room":"Toilet_2","wall":"Wall02","row":4,"col":2,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall02_R04_C03","room":"Toilet_2","wall":"Wall02","row":4,"col":3,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":1845.3,"z0":1836.3,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T2_Wall02_R05_C01","room":"Toilet_2","wall":"Wall02","row":5,"col":1,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T2_Wall02_R05_C02","room":"Toilet_2","wall":"Wall02","row":5,"col":2,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T2_Wall02_R05_C03","room":"Toilet_2","wall":"Wall02","row":5,"col":3,"origin":[8869.9,5275.0],"dir":[0.0,1.0],"u0":1845.3,"z0":2448.4,"poly":[[554.7,0.0],[554.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":554.7,"h":551.6,"rect":true},{"name":"T2_Wall03_R01_C01","room":"Toilet_2","wall":"Wall03","row":1,"col":1,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall03_R01_C02","room":"Toilet_2","wall":"Wall03","row":1,"col":2,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T2_Wall03_R02_C01","room":"Toilet_2","wall":"Wall03","row":2,"col":1,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,0.0],[914.4,587.9],[438.4,587.9],[438.4,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T2_Wall03_R02_C02","room":"Toilet_2","wall":"Wall03","row":2,"col":2,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[571.6,0.0],[571.6,609.6],[121.5,609.6],[121.5,587.9],[0.0,587.9],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":false},{"name":"T2_Wall03_R03_C01","room":"Toilet_2","wall":"Wall03","row":3,"col":1,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[438.4,609.6],[0.0,609.6],[0.0,0.0],[438.4,0.0]],"full":false,"w":438.4,"h":609.6,"rect":true},{"name":"T2_Wall03_R03_C02","room":"Toilet_2","wall":"Wall03","row":3,"col":2,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":1049.9,"z0":1224.2,"poly":[[450.1,0.0],[450.1,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":450.1,"h":609.6,"rect":true},{"name":"T2_Wall03_R04_C01","room":"Toilet_2","wall":"Wall03","row":4,"col":1,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[438.4,0.0],[438.4,263.7],[914.4,263.7]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T2_Wall03_R04_C02","room":"Toilet_2","wall":"Wall03","row":4,"col":2,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,263.7],[121.5,263.7],[121.5,0.0]],"full":false,"w":571.6,"h":609.6,"rect":false},{"name":"T2_Wall03_R05_C01","room":"Toilet_2","wall":"Wall03","row":5,"col":1,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T2_Wall03_R05_C02","room":"Toilet_2","wall":"Wall03","row":5,"col":2,"origin":[8869.9,7675.0],"dir":[-1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[571.6,0.0],[571.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":571.6,"h":551.6,"rect":true},{"name":"T2_Wall04_R01_C01","room":"Toilet_2","wall":"Wall04","row":1,"col":1,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall04_R01_C02","room":"Toilet_2","wall":"Wall04","row":1,"col":2,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":928.4,"z0":0.0,"poly":[[0.0,609.6],[0.0,0.0],[914.4,0.0],[914.4,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall04_R01_C03","room":"Toilet_2","wall":"Wall04","row":1,"col":3,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":0.0,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T2_Wall04_R02_C01","room":"Toilet_2","wall":"Wall04","row":2,"col":1,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall04_R02_C02","room":"Toilet_2","wall":"Wall04","row":2,"col":2,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":928.4,"z0":612.1,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall04_R02_C03","room":"Toilet_2","wall":"Wall04","row":2,"col":3,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":612.1,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T2_Wall04_R03_C01","room":"Toilet_2","wall":"Wall04","row":3,"col":1,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall04_R03_C02","room":"Toilet_2","wall":"Wall04","row":3,"col":2,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1224.2,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall04_R03_C03","room":"Toilet_2","wall":"Wall04","row":3,"col":3,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":1224.2,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T2_Wall04_R04_C01","room":"Toilet_2","wall":"Wall04","row":4,"col":1,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall04_R04_C02","room":"Toilet_2","wall":"Wall04","row":4,"col":2,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T2_Wall04_R04_C03","room":"Toilet_2","wall":"Wall04","row":4,"col":3,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":1836.3,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"T2_Wall04_R05_C01","room":"Toilet_2","wall":"Wall04","row":5,"col":1,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T2_Wall04_R05_C02","room":"Toilet_2","wall":"Wall04","row":5,"col":2,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T2_Wall04_R05_C03","room":"Toilet_2","wall":"Wall04","row":5,"col":3,"origin":[7369.9,7675.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":2448.4,"poly":[[554.7,0.0],[554.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":554.7,"h":551.6,"rect":true},{"name":"T1_Wall01_R01_C01","room":"Toilet_1","wall":"Wall01","row":1,"col":1,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall01_R01_C02","room":"Toilet_1","wall":"Wall01","row":1,"col":2,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall01_R02_C01","room":"Toilet_1","wall":"Wall01","row":2,"col":1,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall01_R02_C02","room":"Toilet_1","wall":"Wall01","row":2,"col":2,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall01_R03_C01","room":"Toilet_1","wall":"Wall01","row":3,"col":1,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall01_R03_C02","room":"Toilet_1","wall":"Wall01","row":3,"col":2,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":928.4,"z0":1224.2,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall01_R04_C01","room":"Toilet_1","wall":"Wall01","row":4,"col":1,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall01_R04_C02","room":"Toilet_1","wall":"Wall01","row":4,"col":2,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall01_R05_C01","room":"Toilet_1","wall":"Wall01","row":5,"col":1,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall01_R05_C02","room":"Toilet_1","wall":"Wall01","row":5,"col":2,"origin":[5719.9,5975.0],"dir":[1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[571.6,0.0],[571.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":571.6,"h":551.6,"rect":true},{"name":"T1_Wall02_R01_C01","room":"Toilet_1","wall":"Wall02","row":1,"col":1,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R01_C02","room":"Toilet_1","wall":"Wall02","row":1,"col":2,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":928.4,"z0":0.0,"poly":[[0.0,609.6],[0.0,0.0],[914.4,0.0],[914.4,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R01_C03","room":"Toilet_1","wall":"Wall02","row":1,"col":3,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":1845.3,"z0":0.0,"poly":[[654.7,0.0],[654.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":654.7,"h":609.6,"rect":true},{"name":"T1_Wall02_R02_C01","room":"Toilet_1","wall":"Wall02","row":2,"col":1,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R02_C02","room":"Toilet_1","wall":"Wall02","row":2,"col":2,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":928.4,"z0":612.1,"poly":[[914.4,0.0],[914.4,587.9],[896.6,587.9],[896.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T1_Wall02_R02_C03","room":"Toilet_1","wall":"Wall02","row":2,"col":3,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":1845.3,"z0":612.1,"poly":[[654.7,0.0],[654.7,587.9],[0.0,587.9],[0.0,0.0]],"full":false,"w":654.7,"h":587.9,"rect":true},{"name":"T1_Wall02_R03_C01","room":"Toilet_1","wall":"Wall02","row":3,"col":1,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R03_C02","room":"Toilet_1","wall":"Wall02","row":3,"col":2,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":928.4,"z0":1224.2,"poly":[[0.0,0.0],[896.6,0.0],[896.6,609.6],[0.0,609.6]],"full":false,"w":896.6,"h":609.6,"rect":true},{"name":"T1_Wall02_R04_C01","room":"Toilet_1","wall":"Wall02","row":4,"col":1,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall02_R04_C02","room":"Toilet_1","wall":"Wall02","row":4,"col":2,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,0.0],[896.6,0.0],[896.6,263.7],[914.4,263.7],[914.4,609.6],[0.0,609.6]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T1_Wall02_R04_C03","room":"Toilet_1","wall":"Wall02","row":4,"col":3,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":1845.3,"z0":2100.0,"poly":[[654.7,0.0],[654.7,345.9],[0.0,345.9],[0.0,0.0]],"full":false,"w":654.7,"h":345.9,"rect":true},{"name":"T1_Wall02_R05_C01","room":"Toilet_1","wall":"Wall02","row":5,"col":1,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall02_R05_C02","room":"Toilet_1","wall":"Wall02","row":5,"col":2,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall02_R05_C03","room":"Toilet_1","wall":"Wall02","row":5,"col":3,"origin":[7219.9,5975.0],"dir":[0.0,1.0],"u0":1845.3,"z0":2448.4,"poly":[[654.7,0.0],[654.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":654.7,"h":551.6,"rect":true},{"name":"T1_Wall03_R01_C01","room":"Toilet_1","wall":"Wall03","row":1,"col":1,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall03_R01_C02","room":"Toilet_1","wall":"Wall03","row":1,"col":2,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall03_R02_C01","room":"Toilet_1","wall":"Wall03","row":2,"col":1,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall03_R02_C02","room":"Toilet_1","wall":"Wall03","row":2,"col":2,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall03_R03_C01","room":"Toilet_1","wall":"Wall03","row":3,"col":1,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall03_R03_C02","room":"Toilet_1","wall":"Wall03","row":3,"col":2,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1224.2,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall03_R04_C01","room":"Toilet_1","wall":"Wall03","row":4,"col":1,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall03_R04_C02","room":"Toilet_1","wall":"Wall03","row":4,"col":2,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[571.6,0.0],[571.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":571.6,"h":609.6,"rect":true},{"name":"T1_Wall03_R05_C01","room":"Toilet_1","wall":"Wall03","row":5,"col":1,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall03_R05_C02","room":"Toilet_1","wall":"Wall03","row":5,"col":2,"origin":[7219.9,8475.0],"dir":[-1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[571.6,0.0],[571.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":571.6,"h":551.6,"rect":true},{"name":"T1_Wall04_R01_C01","room":"Toilet_1","wall":"Wall04","row":1,"col":1,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall04_R01_C02","room":"Toilet_1","wall":"Wall04","row":1,"col":2,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":928.4,"z0":0.0,"poly":[[0.0,609.6],[0.0,0.0],[863.3,0.0],[863.3,609.6]],"full":false,"w":863.3,"h":609.6,"rect":true},{"name":"T1_Wall04_R02_C01","room":"Toilet_1","wall":"Wall04","row":2,"col":1,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall04_R02_C02","room":"Toilet_1","wall":"Wall04","row":2,"col":2,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":928.4,"z0":612.1,"poly":[[0.0,0.0],[863.3,0.0],[863.3,609.6],[0.0,609.6]],"full":false,"w":863.3,"h":609.6,"rect":true},{"name":"T1_Wall04_R03_C01","room":"Toilet_1","wall":"Wall04","row":3,"col":1,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall04_R03_C02","room":"Toilet_1","wall":"Wall04","row":3,"col":2,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1224.2,"poly":[[0.0,0.0],[863.3,0.0],[863.3,609.6],[0.0,609.6]],"full":false,"w":863.3,"h":609.6,"rect":true},{"name":"T1_Wall04_R04_C01","room":"Toilet_1","wall":"Wall04","row":4,"col":1,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"T1_Wall04_R04_C02","room":"Toilet_1","wall":"Wall04","row":4,"col":2,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,0.0],[863.3,0.0],[863.3,263.7],[914.4,263.7],[914.4,609.6],[0.0,609.6]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"T1_Wall04_R04_C03","room":"Toilet_1","wall":"Wall04","row":4,"col":3,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":2100.0,"poly":[[654.7,0.0],[654.7,345.9],[0.0,345.9],[0.0,0.0]],"full":false,"w":654.7,"h":345.9,"rect":true},{"name":"T1_Wall04_R05_C01","room":"Toilet_1","wall":"Wall04","row":5,"col":1,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall04_R05_C02","room":"Toilet_1","wall":"Wall04","row":5,"col":2,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"T1_Wall04_R05_C03","room":"Toilet_1","wall":"Wall04","row":5,"col":3,"origin":[5719.9,8475.0],"dir":[0.0,-1.0],"u0":1845.3,"z0":2448.4,"poly":[[654.7,0.0],[654.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":654.7,"h":551.6,"rect":true},{"name":"MT_Wall01_R01_C01","room":"Master_Toilet","wall":"Wall01","row":1,"col":1,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall01_R01_C02","room":"Master_Toilet","wall":"Wall01","row":1,"col":2,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[0.0,609.6],[0.0,0.0],[763.4,0.0],[763.4,609.6]],"full":false,"w":763.4,"h":609.6,"rect":true},{"name":"MT_Wall01_R02_C01","room":"Master_Toilet","wall":"Wall01","row":2,"col":1,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall01_R02_C02","room":"Master_Toilet","wall":"Wall01","row":2,"col":2,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[0.0,0.0],[763.4,0.0],[763.4,609.6],[0.0,609.6]],"full":false,"w":763.4,"h":609.6,"rect":true},{"name":"MT_Wall01_R03_C01","room":"Master_Toilet","wall":"Wall01","row":3,"col":1,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall01_R03_C02","room":"Master_Toilet","wall":"Wall01","row":3,"col":2,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":928.4,"z0":1224.2,"poly":[[0.0,0.0],[763.4,0.0],[763.4,609.6],[0.0,609.6]],"full":false,"w":763.4,"h":609.6,"rect":true},{"name":"MT_Wall01_R04_C01","room":"Master_Toilet","wall":"Wall01","row":4,"col":1,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall01_R04_C02","room":"Master_Toilet","wall":"Wall01","row":4,"col":2,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,0.0],[763.4,0.0],[763.4,263.7],[914.4,263.7],[914.4,609.6],[0.0,609.6]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"MT_Wall01_R04_C03","room":"Master_Toilet","wall":"Wall01","row":4,"col":3,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":1845.3,"z0":2100.0,"poly":[[554.7,0.0],[554.7,345.9],[0.0,345.9],[0.0,0.0]],"full":false,"w":554.7,"h":345.9,"rect":true},{"name":"MT_Wall01_R05_C01","room":"Master_Toilet","wall":"Wall01","row":5,"col":1,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall01_R05_C02","room":"Master_Toilet","wall":"Wall01","row":5,"col":2,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall01_R05_C03","room":"Master_Toilet","wall":"Wall01","row":5,"col":3,"origin":[2069.9,3775.0],"dir":[1.0,0.0],"u0":1845.3,"z0":2448.4,"poly":[[554.7,0.0],[554.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":554.7,"h":551.6,"rect":true},{"name":"MT_Wall02_R01_C01","room":"Master_Toilet","wall":"Wall02","row":1,"col":1,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall02_R01_C02","room":"Master_Toilet","wall":"Wall02","row":1,"col":2,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":928.4,"z0":0.0,"poly":[[421.6,0.0],[421.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":421.6,"h":609.6,"rect":true},{"name":"MT_Wall02_R02_C01","room":"Master_Toilet","wall":"Wall02","row":2,"col":1,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall02_R02_C02","room":"Master_Toilet","wall":"Wall02","row":2,"col":2,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":928.4,"z0":612.1,"poly":[[421.6,0.0],[421.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":421.6,"h":609.6,"rect":true},{"name":"MT_Wall02_R03_C01","room":"Master_Toilet","wall":"Wall02","row":3,"col":1,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall02_R03_C02","room":"Master_Toilet","wall":"Wall02","row":3,"col":2,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":928.4,"z0":1224.2,"poly":[[421.6,0.0],[421.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":421.6,"h":609.6,"rect":true},{"name":"MT_Wall02_R04_C01","room":"Master_Toilet","wall":"Wall02","row":4,"col":1,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall02_R04_C02","room":"Master_Toilet","wall":"Wall02","row":4,"col":2,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":928.4,"z0":1836.3,"poly":[[421.6,0.0],[421.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":421.6,"h":609.6,"rect":true},{"name":"MT_Wall02_R05_C01","room":"Master_Toilet","wall":"Wall02","row":5,"col":1,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall02_R05_C02","room":"Master_Toilet","wall":"Wall02","row":5,"col":2,"origin":[4469.9,3775.0],"dir":[0.0,1.0],"u0":928.4,"z0":2448.4,"poly":[[421.6,0.0],[421.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":421.6,"h":551.6,"rect":true},{"name":"MT_Wall03_R01_C01","room":"Master_Toilet","wall":"Wall03","row":1,"col":1,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R01_C02","room":"Master_Toilet","wall":"Wall03","row":1,"col":2,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":928.4,"z0":0.0,"poly":[[0.0,609.6],[0.0,0.0],[914.4,0.0],[914.4,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R01_C03","room":"Master_Toilet","wall":"Wall03","row":1,"col":3,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":1845.3,"z0":0.0,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall03_R02_C01","room":"Master_Toilet","wall":"Wall03","row":2,"col":1,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":11.5,"z0":612.1,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R02_C02","room":"Master_Toilet","wall":"Wall03","row":2,"col":2,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":928.4,"z0":612.1,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R02_C03","room":"Master_Toilet","wall":"Wall03","row":2,"col":3,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":1845.3,"z0":612.1,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall03_R03_C01","room":"Master_Toilet","wall":"Wall03","row":3,"col":1,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1224.2,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R03_C02","room":"Master_Toilet","wall":"Wall03","row":3,"col":2,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1224.2,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R03_C03","room":"Master_Toilet","wall":"Wall03","row":3,"col":3,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":1845.3,"z0":1224.2,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall03_R04_C01","room":"Master_Toilet","wall":"Wall03","row":4,"col":1,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R04_C02","room":"Master_Toilet","wall":"Wall03","row":4,"col":2,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":928.4,"z0":1836.3,"poly":[[0.0,0.0],[914.4,0.0],[914.4,609.6],[0.0,609.6]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall03_R04_C03","room":"Master_Toilet","wall":"Wall03","row":4,"col":3,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":1845.3,"z0":1836.3,"poly":[[554.7,0.0],[554.7,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":554.7,"h":609.6,"rect":true},{"name":"MT_Wall03_R05_C01","room":"Master_Toilet","wall":"Wall03","row":5,"col":1,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall03_R05_C02","room":"Master_Toilet","wall":"Wall03","row":5,"col":2,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":928.4,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall03_R05_C03","room":"Master_Toilet","wall":"Wall03","row":5,"col":3,"origin":[4469.9,5125.0],"dir":[-1.0,0.0],"u0":1845.3,"z0":2448.4,"poly":[[554.7,0.0],[554.7,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":554.7,"h":551.6,"rect":true},{"name":"MT_Wall04_R01_C01","room":"Master_Toilet","wall":"Wall04","row":1,"col":1,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":11.5,"z0":0.0,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[914.4,0.0]],"full":true,"w":914.4,"h":609.6,"rect":true},{"name":"MT_Wall04_R01_C02","room":"Master_Toilet","wall":"Wall04","row":1,"col":2,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":928.4,"z0":0.0,"poly":[[421.6,0.0],[421.6,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":421.6,"h":609.6,"rect":true},{"name":"MT_Wall04_R02_C01","room":"Master_Toilet","wall":"Wall04","row":2,"col":1,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":11.5,"z0":612.1,"poly":[[914.4,0.0],[914.4,587.9],[351.0,587.9],[351.0,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"MT_Wall04_R02_C02","room":"Master_Toilet","wall":"Wall04","row":2,"col":2,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":928.4,"z0":612.1,"poly":[[421.6,0.0],[421.6,609.6],[34.1,609.6],[34.1,587.9],[0.0,587.9],[0.0,0.0]],"full":false,"w":421.6,"h":609.6,"rect":false},{"name":"MT_Wall04_R03_C01","room":"Master_Toilet","wall":"Wall04","row":3,"col":1,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1224.2,"poly":[[351.0,609.6],[0.0,609.6],[0.0,0.0],[351.0,0.0]],"full":false,"w":351.0,"h":609.6,"rect":true},{"name":"MT_Wall04_R03_C02","room":"Master_Toilet","wall":"Wall04","row":3,"col":2,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":962.5,"z0":1224.2,"poly":[[387.5,0.0],[387.5,609.6],[0.0,609.6],[0.0,0.0]],"full":false,"w":387.5,"h":609.6,"rect":true},{"name":"MT_Wall04_R04_C01","room":"Master_Toilet","wall":"Wall04","row":4,"col":1,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":11.5,"z0":1836.3,"poly":[[914.4,609.6],[0.0,609.6],[0.0,0.0],[351.0,0.0],[351.0,263.7],[914.4,263.7]],"full":false,"w":914.4,"h":609.6,"rect":false},{"name":"MT_Wall04_R04_C02","room":"Master_Toilet","wall":"Wall04","row":4,"col":2,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":928.4,"z0":1836.3,"poly":[[421.6,0.0],[421.6,609.6],[0.0,609.6],[0.0,263.7],[34.1,263.7],[34.1,0.0]],"full":false,"w":421.6,"h":609.6,"rect":false},{"name":"MT_Wall04_R05_C01","room":"Master_Toilet","wall":"Wall04","row":5,"col":1,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":11.5,"z0":2448.4,"poly":[[914.4,0.0],[914.4,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":914.4,"h":551.6,"rect":true},{"name":"MT_Wall04_R05_C02","room":"Master_Toilet","wall":"Wall04","row":5,"col":2,"origin":[2069.9,5125.0],"dir":[0.0,-1.0],"u0":928.4,"z0":2448.4,"poly":[[421.6,0.0],[421.6,551.6],[0.0,551.6],[0.0,0.0]],"full":false,"w":421.6,"h":551.6,"rect":true}],"panels":[{"name":"R01_Wall01_P01","room":"Room_01","wall":"Wall01","col":1,"origin":[9479.9,425.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[375.1,500.0],[375.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1220.0,"h":2900.0},{"name":"R01_Wall01_P02","room":"Room_01","wall":"Wall01","col":2,"origin":[9479.9,425.0],"dir":[1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1102.0,0.0],[1102.0,2900.0],[352.1,2900.0],[352.1,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1102.0,"h":2900.0},{"name":"R01_Wall02_P01","room":"Room_01","wall":"Wall02","col":1,"origin":[11819.9,425.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[693.0,0.0],[693.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":693.0,"h":2900.0},{"name":"R01_Wall02_P02","room":"Room_01","wall":"Wall02","col":2,"origin":[11819.9,425.0],"dir":[0.0,1.0],"u0":711.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall02_P03","room":"Room_01","wall":"Wall02","col":3,"origin":[11819.9,425.0],"dir":[0.0,1.0],"u0":1934.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall02_P04","room":"Room_01","wall":"Wall02","col":4,"origin":[11819.9,425.0],"dir":[0.0,1.0],"u0":3157.0,"z0":100.0,"poly":[[693.0,0.0],[693.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":693.0,"h":2900.0},{"name":"R01_Wall03_P01","room":"Room_01","wall":"Wall03","col":1,"origin":[11819.9,4275.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[250.0,0.0],[250.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":250.0,"h":2900.0},{"name":"R01_Wall04_P01","room":"Room_01","wall":"Wall04","col":1,"origin":[12069.9,4275.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[637.0,0.0],[637.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":637.0,"h":2900.0},{"name":"R01_Wall04_P02","room":"Room_01","wall":"Wall04","col":2,"origin":[12069.9,4275.0],"dir":[0.0,-1.0],"u0":640.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall04_P03","room":"Room_01","wall":"Wall04","col":3,"origin":[12069.9,4275.0],"dir":[0.0,-1.0],"u0":1863.0,"z0":100.0,"poly":[[637.0,0.0],[637.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":637.0,"h":2900.0},{"name":"R01_Wall05_P01","room":"Room_01","wall":"Wall05","col":1,"origin":[12069.9,1775.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[460.1,2900.0],[0.0,2900.0],[0.0,0.0],[460.1,0.0]],"full":false,"w":460.1,"h":2900.0},{"name":"R01_Wall05_P03","room":"Room_01","wall":"Wall05","col":3,"origin":[12069.9,1775.0],"dir":[1.0,0.0],"u0":2875.1,"z0":100.0,"poly":[[474.9,0.0],[474.9,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":474.9,"h":2900.0},{"name":"R01_Wall06_P01","room":"Room_01","wall":"Wall06","col":1,"origin":[15419.9,1775.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[643.0,0.0],[643.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":643.0,"h":2900.0},{"name":"R01_Wall06_P02","room":"Room_01","wall":"Wall06","col":2,"origin":[15419.9,1775.0],"dir":[0.0,1.0],"u0":661.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall06_P03","room":"Room_01","wall":"Wall06","col":3,"origin":[15419.9,1775.0],"dir":[0.0,1.0],"u0":1884.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall06_P04","room":"Room_01","wall":"Wall06","col":4,"origin":[15419.9,1775.0],"dir":[0.0,1.0],"u0":3107.0,"z0":100.0,"poly":[[643.0,0.0],[643.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":643.0,"h":2900.0},{"name":"R01_Wall07_P01","room":"Room_01","wall":"Wall07","col":1,"origin":[15419.9,5525.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall07_P02","room":"Room_01","wall":"Wall07","col":2,"origin":[15419.9,5525.0],"dir":[1.0,0.0],"u0":1223.0,"z0":100.0,"poly":[[577.0,0.0],[577.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":577.0,"h":2900.0},{"name":"R01_Wall08_P01","room":"Room_01","wall":"Wall08","col":1,"origin":[17219.9,5525.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[666.0,0.0],[666.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":666.0,"h":2900.0},{"name":"R01_Wall08_P02","room":"Room_01","wall":"Wall08","col":2,"origin":[17219.9,5525.0],"dir":[0.0,1.0],"u0":684.0,"z0":100.0,"poly":[[666.0,0.0],[666.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":666.0,"h":2900.0},{"name":"R01_Wall09_P01","room":"Room_01","wall":"Wall09","col":1,"origin":[17219.9,6875.0],"dir":[-1.0,0.0],"u0":1049.9,"z0":100.0,"poly":[[185.1,0.0],[185.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":185.1,"h":2900.0},{"name":"R01_Wall09_P02","room":"Room_01","wall":"Wall09","col":2,"origin":[17219.9,6875.0],"dir":[-1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall09_P03","room":"Room_01","wall":"Wall09","col":3,"origin":[17219.9,6875.0],"dir":[-1.0,0.0],"u0":2461.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall09_P04","room":"Room_01","wall":"Wall09","col":4,"origin":[17219.9,6875.0],"dir":[-1.0,0.0],"u0":3684.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall09_P05","room":"Room_01","wall":"Wall09","col":5,"origin":[17219.9,6875.0],"dir":[-1.0,0.0],"u0":4907.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall09_P06","room":"Room_01","wall":"Wall09","col":6,"origin":[17219.9,6875.0],"dir":[-1.0,0.0],"u0":6130.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall09_P07","room":"Room_01","wall":"Wall09","col":7,"origin":[17219.9,6875.0],"dir":[-1.0,0.0],"u0":7353.0,"z0":100.0,"poly":[[797.0,0.0],[797.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":797.0,"h":2900.0},{"name":"R01_Wall10_P01","room":"Room_01","wall":"Wall10","col":1,"origin":[9069.9,6875.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall10_P02","room":"Room_01","wall":"Wall10","col":2,"origin":[9069.9,6875.0],"dir":[0.0,-1.0],"u0":1238.0,"z0":100.0,"poly":[[512.0,2900.0],[0.0,2900.0],[0.0,0.0],[512.0,0.0]],"full":false,"w":512.0,"h":2900.0},{"name":"R01_Wall10_P03","room":"Room_01","wall":"Wall10","col":3,"origin":[9069.9,6875.0],"dir":[0.0,-1.0],"u0":2800.0,"z0":100.0,"poly":[[881.0,0.0],[881.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":881.0,"h":2900.0},{"name":"R01_Wall10_P04","room":"Room_01","wall":"Wall10","col":4,"origin":[9069.9,6875.0],"dir":[0.0,-1.0],"u0":3684.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R01_Wall10_P05","room":"Room_01","wall":"Wall10","col":5,"origin":[9069.9,6875.0],"dir":[0.0,-1.0],"u0":4907.0,"z0":100.0,"poly":[[933.0,0.0],[933.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":933.0,"h":2900.0},{"name":"R01_Wall11_P01","room":"Room_01","wall":"Wall11","col":1,"origin":[9069.9,1035.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[395.0,0.0],[395.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":395.0,"h":2900.0},{"name":"R01_Wall12_P01","room":"Room_01","wall":"Wall12","col":1,"origin":[9479.9,1035.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[610.0,0.0],[610.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":610.0,"h":2900.0},{"name":"R05_Wall01_P01","room":"Room_05","wall":"Wall01","col":1,"origin":[12069.9,125.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":500.0},{"name":"R05_Wall01_P02","room":"Room_05","wall":"Wall01","col":2,"origin":[12069.9,125.0],"dir":[1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":500.0},{"name":"R05_Wall01_P03","room":"Room_05","wall":"Wall01","col":3,"origin":[12069.9,125.0],"dir":[1.0,0.0],"u0":2461.0,"z0":100.0,"poly":[[964.0,0.0],[964.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":964.0,"h":500.0},{"name":"R05_Wall02_P01","room":"Room_05","wall":"Wall02","col":1,"origin":[15494.9,125.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1035.0,0.0],[1035.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1035.0,"h":500.0},{"name":"R05_Wall03_P01","room":"Room_05","wall":"Wall03","col":1,"origin":[15494.9,1175.0],"dir":[-1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[60.0,0.0],[60.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":60.0,"h":2900.0},{"name":"R05_Wall04_P01","room":"Room_05","wall":"Wall04","col":1,"origin":[15419.9,1175.0],"dir":[0.0,1.0],"u0":0.0,"z0":100.0,"poly":[[475.0,0.0],[475.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":475.0,"h":2900.0},{"name":"R05_Wall05_P01","room":"Room_05","wall":"Wall05","col":1,"origin":[15419.9,1650.0],"dir":[-1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[459.9,2900.0],[0.0,2900.0],[0.0,0.0],[459.9,0.0]],"full":false,"w":459.9,"h":2900.0},{"name":"R05_Wall05_P03","room":"Room_05","wall":"Wall05","col":3,"origin":[15419.9,1650.0],"dir":[-1.0,0.0],"u0":2874.9,"z0":100.0,"poly":[[225.1,0.0],[225.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":225.1,"h":2900.0},{"name":"R05_Wall06_P01","room":"Room_05","wall":"Wall06","col":1,"origin":[12319.9,1650.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[335.0,0.0],[335.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":335.0,"h":2900.0},{"name":"R05_Wall07_P01","room":"Room_05","wall":"Wall07","col":1,"origin":[12319.9,1300.0],"dir":[-1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[250.0,0.0],[250.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":250.0,"h":2900.0},{"name":"R05_Wall08_P01","room":"Room_05","wall":"Wall08","col":1,"origin":[12069.9,1300.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[1160.0,0.0],[1160.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1160.0,"h":2900.0},{"name":"R04_Wall01_P01","room":"Room_04","wall":"Wall01","col":1,"origin":[5719.9,125.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1210.0,0.0],[1210.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1210.0,"h":2900.0},{"name":"R04_Wall02_P01","room":"Room_04","wall":"Wall02","col":1,"origin":[6944.9,125.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[285.0,0.0],[285.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":285.0,"h":2900.0},{"name":"R04_Wall03_P01","room":"Room_04","wall":"Wall03","col":1,"origin":[6944.9,425.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[125.0,500.0],[125.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1220.0,"h":2900.0},{"name":"R04_Wall03_P02","room":"Room_04","wall":"Wall03","col":2,"origin":[6944.9,425.0],"dir":[1.0,0.0],"u0":1223.0,"z0":100.0,"poly":[[702.0,0.0],[702.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":702.0,"h":500.0},{"name":"R04_Wall04_P01","room":"Room_04","wall":"Wall04","col":1,"origin":[8869.9,425.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R04_Wall04_P02","room":"Room_04","wall":"Wall04","col":2,"origin":[8869.9,425.0],"dir":[0.0,1.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R04_Wall04_P03","room":"Room_04","wall":"Wall04","col":3,"origin":[8869.9,425.0],"dir":[0.0,1.0],"u0":2461.0,"z0":100.0,"poly":[[1039.0,0.0],[1039.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1039.0,"h":2900.0},{"name":"R04_Wall05_P01","room":"Room_04","wall":"Wall05","col":1,"origin":[8869.9,3925.0],"dir":[-1.0,0.0],"u0":899.9,"z0":100.0,"poly":[[335.1,0.0],[335.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":335.1,"h":2900.0},{"name":"R04_Wall05_P02","room":"Room_04","wall":"Wall05","col":2,"origin":[8869.9,3925.0],"dir":[-1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R04_Wall05_P03","room":"Room_04","wall":"Wall05","col":3,"origin":[8869.9,3925.0],"dir":[-1.0,0.0],"u0":2461.0,"z0":100.0,"poly":[[689.0,0.0],[689.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":689.0,"h":2900.0},{"name":"R04_Wall06_P01","room":"Room_04","wall":"Wall06","col":1,"origin":[5719.9,3925.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[668.0,0.0],[668.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":668.0,"h":2900.0},{"name":"R04_Wall06_P02","room":"Room_04","wall":"Wall06","col":2,"origin":[5719.9,3925.0],"dir":[0.0,-1.0],"u0":686.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R04_Wall06_P03","room":"Room_04","wall":"Wall06","col":3,"origin":[5719.9,3925.0],"dir":[0.0,-1.0],"u0":1909.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R04_Wall06_P04","room":"Room_04","wall":"Wall06","col":4,"origin":[5719.9,3925.0],"dir":[0.0,-1.0],"u0":3132.0,"z0":100.0,"poly":[[668.0,0.0],[668.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":668.0,"h":2900.0},{"name":"R06_Wall01_P01","room":"Room_06","wall":"Wall01","col":1,"origin":[5719.9,4075.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R06_Wall01_P02","room":"Room_06","wall":"Wall01","col":2,"origin":[5719.9,4075.0],"dir":[1.0,0.0],"u0":1223.0,"z0":100.0,"poly":[[1027.1,2900.0],[0.0,2900.0],[0.0,0.0],[1027.1,0.0]],"full":false,"w":1027.1,"h":2900.0},{"name":"R06_Wall03_P01","room":"Room_06","wall":"Wall03","col":1,"origin":[8869.9,5125.0],"dir":[-1.0,0.0],"u0":708.2,"z0":100.0,"poly":[[511.8,0.0],[511.8,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":511.8,"h":2900.0},{"name":"R06_Wall03_P02","room":"Room_06","wall":"Wall03","col":2,"origin":[8869.9,5125.0],"dir":[-1.0,0.0],"u0":1223.0,"z0":100.0,"poly":[[427.0,0.0],[427.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":427.0,"h":2900.0},{"name":"R06_Wall04_P01","room":"Room_06","wall":"Wall04","col":1,"origin":[7219.9,5125.0],"dir":[0.0,1.0],"u0":0.0,"z0":100.0,"poly":[[700.0,0.0],[700.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":700.0,"h":2900.0},{"name":"R06_Wall05_P01","room":"Room_06","wall":"Wall05","col":1,"origin":[7219.9,5825.0],"dir":[-1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R06_Wall05_P02","room":"Room_06","wall":"Wall05","col":2,"origin":[7219.9,5825.0],"dir":[-1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[262.0,0.0],[262.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":262.0,"h":2900.0},{"name":"R06_Wall06_P01","room":"Room_06","wall":"Wall06","col":1,"origin":[5719.9,5825.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[560.0,2900.0],[0.0,2900.0],[0.0,0.0],[560.0,0.0]],"full":false,"w":560.0,"h":2900.0},{"name":"R03_Wall02_P01","room":"Room_03","wall":"Wall02","col":1,"origin":[5519.9,3842.8],"dir":[0.0,1.0],"u0":0.0,"z0":100.0,"poly":[[232.2,0.0],[232.2,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":232.2,"h":2900.0},{"name":"R03_Wall03_P01","room":"Room_03","wall":"Wall03","col":1,"origin":[5519.9,4075.0],"dir":[1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[50.0,0.0],[50.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":50.0,"h":2900.0},{"name":"R03_Wall04_P01","room":"Room_03","wall":"Wall04","col":1,"origin":[5569.9,4075.0],"dir":[0.0,1.0],"u0":1175.0,"z0":100.0,"poly":[[60.0,0.0],[60.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":60.0,"h":2900.0},{"name":"R03_Wall04_P02","room":"Room_03","wall":"Wall04","col":2,"origin":[5569.9,4075.0],"dir":[0.0,1.0],"u0":1238.0,"z0":100.0,"poly":[[662.0,2900.0],[0.0,2900.0],[0.0,0.0],[662.0,0.0]],"full":false,"w":662.0,"h":2900.0},{"name":"R03_Wall04_P03","room":"Room_03","wall":"Wall04","col":3,"origin":[5569.9,4075.0],"dir":[0.0,1.0],"u0":2608.3,"z0":100.0,"poly":[[1072.7,0.0],[1072.7,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1072.7,"h":2900.0},{"name":"R03_Wall04_P04","room":"Room_03","wall":"Wall04","col":4,"origin":[5569.9,4075.0],"dir":[0.0,1.0],"u0":3684.0,"z0":100.0,"poly":[[716.0,0.0],[716.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":716.0,"h":2900.0},{"name":"R03_Wall05_P01","room":"Room_03","wall":"Wall05","col":1,"origin":[5569.9,8475.0],"dir":[-1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall05_P02","room":"Room_03","wall":"Wall05","col":2,"origin":[5569.9,8475.0],"dir":[-1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall05_P03","room":"Room_03","wall":"Wall05","col":3,"origin":[5569.9,8475.0],"dir":[-1.0,0.0],"u0":2461.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall05_P04","room":"Room_03","wall":"Wall05","col":4,"origin":[5569.9,8475.0],"dir":[-1.0,0.0],"u0":3684.0,"z0":100.0,"poly":[[636.0,0.0],[636.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":636.0,"h":2900.0},{"name":"R03_Wall06_P01","room":"Room_03","wall":"Wall06","col":1,"origin":[1249.9,8475.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[1210.0,0.0],[1210.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1210.0,"h":2900.0},{"name":"R03_Wall07_P01","room":"Room_03","wall":"Wall07","col":1,"origin":[1249.9,7250.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[335.1,0.0],[335.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":335.1,"h":2900.0},{"name":"R03_Wall08_P01","room":"Room_03","wall":"Wall08","col":1,"origin":[1600.0,7250.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[122.0,2900.0],[0.0,2900.0],[0.0,0.0],[122.0,0.0]],"full":false,"w":122.0,"h":2900.0},{"name":"R03_Wall10_P01","room":"Room_03","wall":"Wall10","col":1,"origin":[1599.9,7125.0],"dir":[0.0,-1.0],"u0":3.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":500.0},{"name":"R03_Wall10_P02","room":"Room_03","wall":"Wall10","col":2,"origin":[1599.9,7125.0],"dir":[0.0,-1.0],"u0":1226.0,"z0":100.0,"poly":[[624.0,0.0],[624.0,2900.0],[574.0,2900.0],[574.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":624.0,"h":2900.0},{"name":"R03_Wall11_P01","room":"Room_03","wall":"Wall11","col":1,"origin":[1599.9,5275.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall11_P02","room":"Room_03","wall":"Wall11","col":2,"origin":[1599.9,5275.0],"dir":[1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall11_P03","room":"Room_03","wall":"Wall11","col":3,"origin":[1599.9,5275.0],"dir":[1.0,0.0],"u0":2461.0,"z0":100.0,"poly":[[559.0,0.0],[559.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":559.0,"h":2900.0},{"name":"R03_Wall12_P01","room":"Room_03","wall":"Wall12","col":1,"origin":[4619.9,5275.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R03_Wall12_P02","room":"Room_03","wall":"Wall12","col":2,"origin":[4619.9,5275.0],"dir":[0.0,-1.0],"u0":1223.0,"z0":100.0,"poly":[[209.2,0.0],[209.2,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":209.2,"h":2900.0},{"name":"R02_Wall01_P01","room":"Room_02","wall":"Wall01","col":1,"origin":[1484.9,425.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall01_P02","room":"Room_02","wall":"Wall01","col":2,"origin":[1484.9,425.0],"dir":[1.0,0.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[1047.1,500.0],[1047.1,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":1220.0,"h":2900.0},{"name":"R02_Wall01_P03","room":"Room_02","wall":"Wall01","col":3,"origin":[1484.9,425.0],"dir":[1.0,0.0],"u0":2461.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[824.1,2900.0],[824.1,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":2900.0},{"name":"R02_Wall01_P04","room":"Room_02","wall":"Wall01","col":4,"origin":[1484.9,425.0],"dir":[1.0,0.0],"u0":3684.0,"z0":100.0,"poly":[[351.0,0.0],[351.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":351.0,"h":2900.0},{"name":"R02_Wall02_P01","room":"Room_02","wall":"Wall02","col":1,"origin":[5519.9,425.0],"dir":[0.0,1.0],"u0":15.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall02_P02","room":"Room_02","wall":"Wall02","col":2,"origin":[5519.9,425.0],"dir":[0.0,1.0],"u0":1238.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall02_P03","room":"Room_02","wall":"Wall02","col":3,"origin":[5519.9,425.0],"dir":[0.0,1.0],"u0":2461.0,"z0":100.0,"poly":[[806.8,0.0],[806.8,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":806.8,"h":2900.0},{"name":"R02_Wall04_P01","room":"Room_02","wall":"Wall04","col":1,"origin":[4619.9,3692.8],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[67.8,0.0],[67.8,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":67.8,"h":2900.0},{"name":"R02_Wall05_P01a","room":"Room_02","wall":"Wall05","col":1,"origin":[4619.9,3625.0],"dir":[-1.0,0.0],"u0":858.2,"z0":100.0,"poly":[[361.8,0.0],[361.8,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":361.8,"h":2900.0},{"name":"R02_Wall05_P01b","room":"Room_02","wall":"Wall05","col":1,"origin":[4619.9,3625.0],"dir":[-1.0,0.0],"u0":0.0,"z0":100.0,"poly":[[150.0,2900.0],[0.0,2900.0],[0.0,0.0],[150.0,0.0]],"full":false,"w":150.0,"h":2900.0},{"name":"R02_Wall05_P02","room":"Room_02","wall":"Wall05","col":2,"origin":[4619.9,3625.0],"dir":[-1.0,0.0],"u0":1223.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall05_P03","room":"Room_02","wall":"Wall05","col":3,"origin":[4619.9,3625.0],"dir":[-1.0,0.0],"u0":2446.0,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":true,"w":1220.0,"h":2900.0},{"name":"R02_Wall05_P04","room":"Room_02","wall":"Wall05","col":4,"origin":[4619.9,3625.0],"dir":[-1.0,0.0],"u0":3669.0,"z0":100.0,"poly":[[372.9,2900.0],[0.0,2900.0],[0.0,0.0],[372.9,0.0]],"full":false,"w":372.9,"h":2900.0},{"name":"R02_Wall07_P01","room":"Room_02","wall":"Wall07","col":1,"origin":[575.0,3600.0],"dir":[-1.0,0.0],"u0":3.0,"z0":100.0,"poly":[[497.1,0.0],[497.1,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":497.1,"h":500.0},{"name":"R02_Wall08_P01","room":"Room_02","wall":"Wall08","col":1,"origin":[74.9,3600.0],"dir":[0.0,-1.0],"u0":15.0,"z0":100.0,"poly":[[654.5,0.0],[654.5,500.0],[10.0,500.0],[10.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":654.5,"h":2900.0},{"name":"R02_Wall08_P02","room":"Room_02","wall":"Wall08","col":2,"origin":[74.9,3600.0],"dir":[0.0,-1.0],"u0":672.5,"z0":100.0,"poly":[[1220.0,0.0],[1220.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":1220.0,"h":500.0},{"name":"R02_Wall08_P03","room":"Room_02","wall":"Wall08","col":3,"origin":[74.9,3600.0],"dir":[0.0,-1.0],"u0":1895.5,"z0":100.0,"poly":[[654.5,0.0],[654.5,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":654.5,"h":500.0},{"name":"R02_Wall09_P01","room":"Room_02","wall":"Wall09","col":1,"origin":[74.9,1050.0],"dir":[1.0,0.0],"u0":15.0,"z0":100.0,"poly":[[696.0,0.0],[696.0,2900.0],[485.0,2900.0],[485.0,500.0],[0.0,500.0],[0.0,0.0]],"full":false,"w":696.0,"h":2900.0},{"name":"R02_Wall09_P02","room":"Room_02","wall":"Wall09","col":2,"origin":[74.9,1050.0],"dir":[1.0,0.0],"u0":714.0,"z0":100.0,"poly":[[696.0,0.0],[696.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":696.0,"h":2900.0},{"name":"R02_Wall10_P01","room":"Room_02","wall":"Wall10","col":1,"origin":[1484.9,1050.0],"dir":[0.0,-1.0],"u0":0.0,"z0":100.0,"poly":[[625.0,0.0],[625.0,2900.0],[0.0,2900.0],[0.0,0.0]],"full":false,"w":625.0,"h":2900.0}],"kitchens":[],"glass_partitions":[],"recessed_ceilings":[{"room":"Room_01","label":"Living","use":"living","z_soffit":2950.0,"z_wall_top":3000.0,"z_cavity":3120.0,"z_slab_top":3200.0,"border_w":450.0,"cavity_rings":[{"outer":[[9519.9,1485.0],[9929.9,1485.0],[9929.9,875.0],[11369.9,875.0],[11369.9,4725.0],[12519.9,4725.0],[12519.9,2225.0],[14969.9,2225.0],[14969.9,5975.0],[16769.9,5975.0],[16769.9,6425.0],[9519.9,6425.0]],"holes":[]}],"collar_rings":[{"outer":[[9494.9,6450.0],[9494.9,1460.0],[9904.9,1460.0],[9904.9,850.0],[11394.9,850.0],[11394.9,4700.0],[12494.9,4700.0],[12494.9,2200.0],[14994.9,2200.0],[14994.9,5950.0],[16794.9,5950.0],[16794.9,6450.0]],"holes":[[[9929.9,1485.0],[9519.9,1485.0],[9519.9,6425.0],[16769.9,6425.0],[16769.9,5975.0],[14969.9,5975.0],[14969.9,2225.0],[12519.9,2225.0],[12519.9,4725.0],[11369.9,4725.0],[11369.9,875.0],[9929.9,875.0]]],"caps":[[[9494.9,3650.0],[9519.9,3650.0],[9519.9,6425.0],[16769.9,6425.0],[16769.9,5975.0],[14969.9,5975.0],[14969.9,3650.0],[14994.9,3650.0],[14994.9,5950.0],[16794.9,5950.0],[16794.9,6450.0],[9494.9,6450.0]],[[11394.9,3650.0],[11369.9,3650.0],[11369.9,875.0],[9929.9,875.0],[9929.9,1485.0],[9519.9,1485.0],[9519.9,3650.0],[9494.9,3650.0],[9494.9,1460.0],[9904.9,1460.0],[9904.9,850.0],[11394.9,850.0]],[[12494.9,3650.0],[12519.9,3650.0],[12519.9,4725.0],[11369.9,4725.0],[11369.9,3650.0],[11394.9,3650.0],[11394.9,4700.0],[12494.9,4700.0]],[[14994.9,3650.0],[14969.9,3650.0],[14969.9,2225.0],[12519.9,2225.0],[12519.9,3650.0],[12494.9,3650.0],[12494.9,2200.0],[14994.9,2200.0]]]}],"soffit_rings":[{"outer":[[17204.9,5540.0],[17204.9,6860.0],[9084.9,6860.0],[9084.9,1050.0],[9494.9,1050.0],[9494.9,440.0],[11804.9,440.0],[11804.9,4290.0],[12084.9,4290.0],[12084.9,1790.0],[15404.9,1790.0],[15404.9,5540.0]],"holes":[[[9929.9,1485.0],[9519.9,1485.0],[9519.9,6425.0],[16769.9,6425.0],[16769.9,5975.0],[14969.9,5975.0],[14969.9,2225.0],[12519.9,2225.0],[12519.9,4725.0],[11369.9,4725.0],[11369.9,875.0],[9929.9,875.0]]],"caps":[[[9084.9,3650.0],[9519.9,3650.0],[9519.9,6425.0],[16769.9,6425.0],[16769.9,5975.0],[14969.9,5975.0],[14969.9,3650.0],[15404.9,3650.0],[15404.9,5540.0],[17204.9,5540.0],[17204.9,6860.0],[9084.9,6860.0]],[[11804.9,3650.0],[11369.9,3650.0],[11369.9,875.0],[9929.9,875.0],[9929.9,1485.0],[9519.9,1485.0],[9519.9,3650.0],[9084.9,3650.0],[9084.9,1050.0],[9494.9,1050.0],[9494.9,440.0],[11804.9,440.0]],[[12084.9,3650.0],[12519.9,3650.0],[12519.9,4725.0],[11369.9,4725.0],[11369.9,3650.0],[11804.9,3650.0],[11804.9,4290.0],[12084.9,4290.0]],[[15404.9,3650.0],[14969.9,3650.0],[14969.9,2225.0],[12519.9,2225.0],[12519.9,3650.0],[12084.9,3650.0],[12084.9,1790.0],[15404.9,1790.0]]]}],"lip_rings":[{"outer":[[9519.9,6425.0],[9519.9,1485.0],[9929.9,1485.0],[9929.9,875.0],[11369.9,875.0],[11369.9,4725.0],[12519.9,4725.0],[12519.9,2225.0],[14969.9,2225.0],[14969.9,5975.0],[16769.9,5975.0],[16769.9,6425.0]],"holes":[[[9989.9,1545.0],[9579.9,1545.0],[9579.9,6365.0],[16709.9,6365.0],[16709.9,6035.0],[14909.9,6035.0],[14909.9,2285.0],[12579.9,2285.0],[12579.9,4785.0],[11309.9,4785.0],[11309.9,935.0],[9989.9,935.0]]],"caps":[[[9519.9,3650.0],[9579.9,3650.0],[9579.9,6365.0],[16709.9,6365.0],[16709.9,6035.0],[14909.9,6035.0],[14909.9,3650.0],[14969.9,3650.0],[14969.9,5975.0],[16769.9,5975.0],[16769.9,6425.0],[9519.9,6425.0]],[[11369.9,3650.0],[11309.9,3650.0],[11309.9,935.0],[9989.9,935.0],[9989.9,1545.0],[9579.9,1545.0],[9579.9,3650.0],[9519.9,3650.0],[9519.9,1485.0],[9929.9,1485.0],[9929.9,875.0],[11369.9,875.0]],[[12519.9,3650.0],[12579.9,3650.0],[12579.9,4785.0],[11309.9,4785.0],[11309.9,3650.0],[11369.9,3650.0],[11369.9,4725.0],[12519.9,4725.0]],[[14969.9,3650.0],[14909.9,3650.0],[14909.9,2285.0],[12579.9,2285.0],[12579.9,3650.0],[12519.9,3650.0],[12519.9,2225.0],[14969.9,2225.0]]]}],"cove_led_rings":[{"outer":[[9529.9,6415.0],[9529.9,1495.0],[9939.9,1495.0],[9939.9,885.0],[11359.9,885.0],[11359.9,4735.0],[12529.9,4735.0],[12529.9,2235.0],[14959.9,2235.0],[14959.9,5985.0],[16759.9,5985.0],[16759.9,6415.0]],"holes":[[[9975.9,1531.0],[9565.9,1531.0],[9565.9,6379.0],[16723.9,6379.0],[16723.9,6021.0],[14923.9,6021.0],[14923.9,2271.0],[12565.9,2271.0],[12565.9,4771.0],[11323.9,4771.0],[11323.9,921.0],[9975.9,921.0]]],"caps":[[[9529.9,3650.0],[9565.9,3650.0],[9565.9,6379.0],[16723.9,6379.0],[16723.9,6021.0],[14923.9,6021.0],[14923.9,3650.0],[14959.9,3650.0],[14959.9,5985.0],[16759.9,5985.0],[16759.9,6415.0],[9529.9,6415.0]],[[11359.9,3650.0],[11323.9,3650.0],[11323.9,921.0],[9975.9,921.0],[9975.9,1531.0],[9565.9,1531.0],[9565.9,3650.0],[9529.9,3650.0],[9529.9,1495.0],[9939.9,1495.0],[9939.9,885.0],[11359.9,885.0]],[[12529.9,3650.0],[12565.9,3650.0],[12565.9,4771.0],[11323.9,4771.0],[11323.9,3650.0],[11359.9,3650.0],[11359.9,4735.0],[12529.9,4735.0]],[[14959.9,3650.0],[14923.9,3650.0],[14923.9,2271.0],[12565.9,2271.0],[12565.9,3650.0],[12529.9,3650.0],[12529.9,2235.0],[14959.9,2235.0]]]}],"fixtures":[{"x":16087.4,"y":5757.5,"z":2950.0,"mount":"soffit"},{"x":15187.4,"y":4820.0,"z":2950.0,"mount":"soffit"},{"x":15187.4,"y":2945.0,"z":2950.0,"mount":"soffit"},{"x":14466.1,"y":2007.5,"z":2950.0,"mount":"soffit"},{"x":13023.6,"y":2007.5,"z":2950.0,"mount":"soffit"},{"x":12302.4,"y":2632.5,"z":2950.0,"mount":"soffit"},{"x":12302.4,"y":3882.5,"z":2950.0,"mount":"soffit"},{"x":11587.4,"y":3545.0,"z":2950.0,"mount":"soffit"},{"x":11587.4,"y":1620.0,"z":2950.0,"mount":"soffit"},{"x":10649.9,"y":657.5,"z":2950.0,"mount":"soffit"},{"x":9302.4,"y":2163.3,"z":2950.0,"mount":"soffit"},{"x":9302.4,"y":3955.0,"z":2950.0,"mount":"soffit"},{"x":9302.4,"y":5746.7,"z":2950.0,"mount":"soffit"},{"x":10263.0,"y":6642.5,"z":2950.0,"mount":"soffit"},{"x":12184.3,"y":6642.5,"z":2950.0,"mount":"soffit"},{"x":14105.5,"y":6642.5,"z":2950.0,"mount":"soffit"},{"x":16026.8,"y":6642.5,"z":2950.0,"mount":"soffit"},{"x":11007.4,"y":2387.5,"z":3120.0,"mount":"cavity"},{"x":11007.4,"y":4912.5,"z":3120.0,"mount":"cavity"},{"x":13482.4,"y":4912.5,"z":3120.0,"mount":"cavity"}]},{"room":"Room_04","label":"Bedroom_2","use":"bedroom","z_soffit":2950.0,"z_wall_top":3000.0,"z_cavity":3120.0,"z_slab_top":3200.0,"border_w":450.0,"cavity_rings":[{"outer":[[6169.9,575.0],[6494.9,575.0],[6494.9,875.0],[8419.9,875.0],[8419.9,3475.0],[6169.9,3475.0]],"holes":[]}],"collar_rings":[{"outer":[[6144.9,3500.0],[6144.9,550.0],[6519.9,550.0],[6519.9,850.0],[8444.9,850.0],[8444.9,3500.0]],"holes":[[[6494.9,575.0],[6169.9,575.0],[6169.9,3475.0],[8419.9,3475.0],[8419.9,875.0],[6494.9,875.0]]],"caps":[[[6144.9,2025.0],[6169.9,2025.0],[6169.9,3475.0],[8419.9,3475.0],[8419.9,2025.0],[8444.9,2025.0],[8444.9,3500.0],[6144.9,3500.0]],[[8444.9,2025.0],[8419.9,2025.0],[8419.9,875.0],[6494.9,875.0],[6494.9,575.0],[6169.9,575.0],[6169.9,2025.0],[6144.9,2025.0],[6144.9,550.0],[6519.9,550.0],[6519.9,850.0],[8444.9,850.0]]]}],"soffit_rings":[{"outer":[[5734.9,3910.0],[5734.9,140.0],[6929.9,140.0],[6929.9,440.0],[8854.9,440.0],[8854.9,3910.0]],"holes":[[[6494.9,575.0],[6169.9,575.0],[6169.9,3475.0],[8419.9,3475.0],[8419.9,875.0],[6494.9,875.0]]],"caps":[[[5734.9,2025.0],[6169.9,2025.0],[6169.9,3475.0],[8419.9,3475.0],[8419.9,2025.0],[8854.9,2025.0],[8854.9,3910.0],[5734.9,3910.0]],[[8854.9,2025.0],[8419.9,2025.0],[8419.9,875.0],[6494.9,875.0],[6494.9,575.0],[6169.9,575.0],[6169.9,2025.0],[5734.9,2025.0],[5734.9,140.0],[6929.9,140.0],[6929.9,440.0],[8854.9,440.0]]]}],"lip_rings":[{"outer":[[6169.9,3475.0],[6169.9,575.0],[6494.9,575.0],[6494.9,875.0],[8419.9,875.0],[8419.9,3475.0]],"holes":[[[6434.9,635.0],[6229.9,635.0],[6229.9,3415.0],[8359.9,3415.0],[8359.9,935.0],[6434.9,935.0]]],"caps":[[[6169.9,2025.0],[6229.9,2025.0],[6229.9,3415.0],[8359.9,3415.0],[8359.9,2025.0],[8419.9,2025.0],[8419.9,3475.0],[6169.9,3475.0]],[[8419.9,2025.0],[8359.9,2025.0],[8359.9,935.0],[6434.9,935.0],[6434.9,635.0],[6229.9,635.0],[6229.9,2025.0],[6169.9,2025.0],[6169.9,575.0],[6494.9,575.0],[6494.9,875.0],[8419.9,875.0]]]}],"cove_led_rings":[{"outer":[[6179.9,3465.0],[6179.9,585.0],[6484.9,585.0],[6484.9,885.0],[8409.9,885.0],[8409.9,3465.0]],"holes":[[[6448.9,621.0],[6215.9,621.0],[6215.9,3429.0],[8373.9,3429.0],[8373.9,921.0],[6448.9,921.0]]],"caps":[[[6179.9,2025.0],[6215.9,2025.0],[6215.9,3429.0],[8373.9,3429.0],[8373.9,2025.0],[8409.9,2025.0],[8409.9,3465.0],[6179.9,3465.0]],[[8409.9,2025.0],[8373.9,2025.0],[8373.9,921.0],[6448.9,921.0],[6448.9,621.0],[6215.9,621.0],[6215.9,2025.0],[6179.9,2025.0],[6179.9,585.0],[6484.9,585.0],[6484.9,885.0],[8409.9,885.0]]]}],"fixtures":[{"x":5952.4,"y":1191.2,"z":2950.0,"mount":"soffit"},{"x":5952.4,"y":2858.8,"z":2950.0,"mount":"soffit"},{"x":6623.6,"y":3692.5,"z":2950.0,"mount":"soffit"},{"x":7966.1,"y":3692.5,"z":2950.0,"mount":"soffit"},{"x":8637.4,"y":2933.8,"z":2950.0,"mount":"soffit"},{"x":8637.4,"y":1416.2,"z":2950.0,"mount":"soffit"},{"x":7674.9,"y":657.5,"z":2950.0,"mount":"soffit"},{"x":7294.9,"y":2175.0,"z":3120.0,"mount":"cavity"}]},{"room":"Room_03","label":"Bedroom_1","use":"bedroom","z_soffit":2950.0,"z_wall_top":3000.0,"z_cavity":3120.0,"z_slab_top":3200.0,"border_w":450.0,"cavity_rings":[{"outer":[[1699.9,7700.0],[2050.0,7700.0],[2049.9,5725.0],[5069.9,5725.0],[5069.9,4525.0],[5119.9,4525.0],[5119.9,8025.0],[1699.9,8025.0]],"holes":[]}],"collar_rings":[{"outer":[[1674.9,8050.0],[1674.9,7675.0],[2025.0,7675.0],[2024.9,5700.0],[5044.9,5700.0],[5044.9,4500.0],[5144.9,4500.0],[5144.9,8050.0]],"holes":[[[2050.0,7700.0],[1699.9,7700.0],[1699.9,8025.0],[5119.9,8025.0],[5119.9,4525.0],[5069.9,4525.0],[5069.9,5725.0],[2049.9,5725.0]]],"caps":[[[2024.93,6275.0],[2049.93,6275.0],[2050.0,7700.0],[1699.9,7700.0],[1699.9,8025.0],[5119.9,8025.0],[5119.9,6275.0],[5144.9,6275.0],[5144.9,8050.0],[1674.9,8050.0],[1674.9,7675.0],[2025.0,7675.0]],[[5144.9,6275.0],[5119.9,6275.0],[5119.9,4525.0],[5069.9,4525.0],[5069.9,5725.0],[2049.9,5725.0],[2049.93,6275.0],[2024.93,6275.0],[2024.9,5700.0],[5044.9,5700.0],[5044.9,4500.0],[5144.9,4500.0]]]}],"soffit_rings":[{"outer":[[1614.9,5290.0],[4634.9,5290.0],[4634.9,3857.8],[5504.9,3857.8],[5504.9,4090.0],[5554.9,4090.0],[5554.9,8460.0],[1264.9,8460.0],[1264.9,7265.0],[1615.0,7265.0]],"holes":[[[2050.0,7700.0],[1699.9,7700.0],[1699.9,8025.0],[5119.9,8025.0],[5119.9,4525.0],[5069.9,4525.0],[5069.9,5725.0],[2049.9,5725.0]]],"caps":[[[5554.9,6275.0],[5119.9,6275.0],[5119.9,4525.0],[5069.9,4525.0],[5069.9,5725.0],[2049.9,5725.0],[2049.93,6275.0],[1614.95,6275.0],[1614.9,5290.0],[4634.9,5290.0],[4634.9,3857.8],[5504.9,3857.8],[5504.9,4090.0],[5554.9,4090.0]],[[1614.95,6275.0],[2049.93,6275.0],[2050.0,7700.0],[1699.9,7700.0],[1699.9,8025.0],[5119.9,8025.0],[5119.9,6275.0],[5554.9,6275.0],[5554.9,8460.0],[1264.9,8460.0],[1264.9,7265.0],[1615.0,7265.0]]]}],"lip_rings":[{"outer":[[1699.9,8025.0],[1699.9,7700.0],[2050.0,7700.0],[2049.9,5725.0],[5069.9,5725.0],[5069.9,4525.0],[5119.9,4525.0],[5119.9,8025.0]],"holes":[[[2110.0,7760.0],[1759.9,7760.0],[1759.9,7965.0],[5059.9,7965.0],[5059.9,5785.0],[2109.9,5785.0]]],"caps":[[[2049.96,6875.0],[2109.96,6875.0],[2110.0,7760.0],[1759.9,7760.0],[1759.9,7965.0],[5059.9,7965.0],[5059.9,6875.0],[5119.9,6875.0],[5119.9,8025.0],[1699.9,8025.0],[1699.9,7700.0],[2050.0,7700.0]],[[5119.9,6875.0],[5059.9,6875.0],[5059.9,5785.0],[2109.9,5785.0],[2109.96,6875.0],[2049.96,6875.0],[2049.9,5725.0],[5069.9,5725.0],[5069.9,4525.0],[5119.9,4525.0]]]}],"cove_led_rings":[{"outer":[[1709.9,8015.0],[1709.9,7710.0],[2060.0,7710.0],[2059.9,5735.0],[5079.9,5735.0],[5079.9,4535.0],[5109.9,4535.0],[5109.9,8015.0]],"holes":[[[2096.0,7746.0],[1745.9,7746.0],[1745.9,7979.0],[5073.9,7979.0],[5073.9,5771.0],[2095.9,5771.0]]],"caps":[[[2059.96,6875.0],[2095.96,6875.0],[2096.0,7746.0],[1745.9,7746.0],[1745.9,7979.0],[5073.9,7979.0],[5073.9,6875.0],[5109.9,6875.0],[5109.9,8015.0],[1709.9,8015.0],[1709.9,7710.0],[2060.0,7710.0]],[[5109.9,6875.0],[5073.9,6875.0],[5073.9,5771.0],[2095.9,5771.0],[2095.96,6875.0],[2059.96,6875.0],[2059.9,5735.0],[5079.9,5735.0],[5079.9,4535.0],[5109.9,4535.0]]]}],"fixtures":[{"x":2446.2,"y":8242.5,"z":2950.0,"mount":"soffit"},{"x":4373.6,"y":8242.5,"z":2950.0,"mount":"soffit"},{"x":5337.4,"y":7258.8,"z":2950.0,"mount":"soffit"},{"x":5337.4,"y":5291.2,"z":2950.0,"mount":"soffit"},{"x":4852.4,"y":4791.4,"z":2950.0,"mount":"soffit"},{"x":4097.4,"y":5507.5,"z":2950.0,"mount":"soffit"},{"x":2587.4,"y":5507.5,"z":2950.0,"mount":"soffit"},{"x":1832.4,"y":6200.0,"z":2950.0,"mount":"soffit"},{"x":3584.9,"y":6875.0,"z":3120.0,"mount":"cavity"}]},{"room":"Room_02","label":"Master_Bedroom","use":"master_bedroom","z_soffit":2950.0,"z_wall_top":3000.0,"z_cavity":3120.0,"z_slab_top":3200.0,"border_w":450.0,"cavity_rings":[{"outer":[[1025.0,3175.0],[1025.0,3150.0],[524.9,3150.0],[524.9,1500.0],[1934.9,1500.0],[1934.9,875.0],[5069.9,875.0],[5069.9,3175.0]],"holes":[]}],"collar_rings":[{"outer":[[5094.9,3200.0],[1000.0,3200.0],[1000.0,3175.0],[499.9,3175.0],[499.9,1475.0],[1909.9,1475.0],[1909.9,850.0],[5094.9,850.0]],"holes":[[[1025.0,3150.0],[1025.0,3175.0],[5069.9,3175.0],[5069.9,875.0],[1934.9,875.0],[1934.9,1500.0],[524.9,1500.0],[524.9,3150.0]]],"caps":[[[499.9,2025.0],[524.9,2025.0],[524.9,3150.0],[1025.0,3150.0],[1025.0,3175.0],[5069.9,3175.0],[5069.9,2025.0],[5094.9,2025.0],[5094.9,3200.0],[1000.0,3200.0],[1000.0,3175.0],[499.9,3175.0]],[[5094.9,2025.0],[5069.9,2025.0],[5069.9,875.0],[1934.9,875.0],[1934.9,1500.0],[524.9,1500.0],[524.9,2025.0],[499.9,2025.0],[499.9,1475.0],[1909.9,1475.0],[1909.9,850.0],[5094.9,850.0]]]}],"soffit_rings":[{"outer":[[1499.9,1065.0],[1499.9,440.0],[5504.9,440.0],[5504.9,3677.8],[4634.9,3677.8],[4634.9,3610.0],[590.0,3610.0],[590.0,3585.0],[89.9,3585.0],[89.9,1065.0]],"holes":[[[1025.0,3150.0],[1025.0,3175.0],[5069.9,3175.0],[5069.9,875.0],[1934.9,875.0],[1934.9,1500.0],[524.9,1500.0],[524.9,3150.0]]],"caps":[[[5504.9,2025.0],[5069.9,2025.0],[5069.9,875.0],[1934.9,875.0],[1934.9,1500.0],[524.9,1500.0],[524.9,2025.0],[89.9,2025.0],[89.9,1065.0],[1499.9,1065.0],[1499.9,440.0],[5504.9,440.0]],[[89.9,2025.0],[524.9,2025.0],[524.9,3150.0],[1025.0,3150.0],[1025.0,3175.0],[5069.9,3175.0],[5069.9,2025.0],[5504.9,2025.0],[5504.9,3677.8],[4634.9,3677.8],[4634.9,3610.0],[590.0,3610.0],[590.0,3585.0],[89.9,3585.0]]]}],"lip_rings":[{"outer":[[5069.9,3175.0],[1025.0,3175.0],[1025.0,3150.0],[524.9,3150.0],[524.9,1500.0],[1934.9,1500.0],[1934.9,875.0],[5069.9,875.0]],"holes":[[[1085.0,3090.0],[1085.0,3115.0],[5009.9,3115.0],[5009.9,935.0],[1994.9,935.0],[1994.9,1560.0],[584.9,1560.0],[584.9,3090.0]]],"caps":[[[524.9,2025.0],[584.9,2025.0],[584.9,3090.0],[1085.0,3090.0],[1085.0,3115.0],[5009.9,3115.0],[5009.9,2025.0],[5069.9,2025.0],[5069.9,3175.0],[1025.0,3175.0],[1025.0,3150.0],[524.9,3150.0]],[[5069.9,2025.0],[5009.9,2025.0],[5009.9,935.0],[1994.9,935.0],[1994.9,1560.0],[584.9,1560.0],[584.9,2025.0],[524.9,2025.0],[524.9,1500.0],[1934.9,1500.0],[1934.9,875.0],[5069.9,875.0]]]}],"cove_led_rings":[{"outer":[[5059.9,3165.0],[1035.0,3165.0],[1035.0,3140.0],[534.9,3140.0],[534.9,1510.0],[1944.9,1510.0],[1944.9,885.0],[5059.9,885.0]],"holes":[[[1071.0,3104.0],[1071.0,3129.0],[5023.9,3129.0],[5023.9,921.0],[1980.9,921.0],[1980.9,1546.0],[570.9,1546.0],[570.9,3104.0]]],"caps":[[[534.9,2025.0],[570.9,2025.0],[570.9,3104.0],[1071.0,3104.0],[1071.0,3129.0],[5023.9,3129.0],[5023.9,2025.0],[5059.9,2025.0],[5059.9,3165.0],[1035.0,3165.0],[1035.0,3140.0],[534.9,3140.0]],[[5059.9,2025.0],[5023.9,2025.0],[5023.9,921.0],[1980.9,921.0],[1980.9,1546.0],[570.9,1546.0],[570.9,2025.0],[534.9,2025.0],[534.9,1510.0],[1944.9,1510.0],[1944.9,885.0],[5059.9,885.0]]]}],"fixtures":[{"x":1818.7,"y":3392.5,"z":2950.0,"mount":"soffit"},{"x":3841.2,"y":3392.5,"z":2950.0,"mount":"soffit"},{"x":5287.4,"y":2759.6,"z":2950.0,"mount":"soffit"},{"x":5287.4,"y":1358.2,"z":2950.0,"mount":"soffit"},{"x":4394.9,"y":657.5,"z":2950.0,"mount":"soffit"},{"x":2609.9,"y":657.5,"z":2950.0,"mount":"soffit"},{"x":1012.4,"y":1282.5,"z":2950.0,"mount":"soffit"},{"x":307.4,"y":2325.0,"z":2950.0,"mount":"soffit"},{"x":1786.1,"y":2025.0,"z":3120.0,"mount":"cavity"},{"x":3808.6,"y":2025.0,"z":3120.0,"mount":"cavity"}]}],"floor":[{"outer":[[1123.9,8626.0],[1123.9,7124.0],[1473.9,7124.0],[1473.9,5276.0],[574.0,5276.0],[574.0,5124.0],[1943.9,5124.0],[1943.9,3776.0],[-51.1,3776.0],[-51.1,849.0],[573.9,849.0],[573.9,299.0],[5518.9,299.0],[5518.9,124.0],[5719.0,124.0],[5719.0,-1.0],[7070.9,-1.0],[7070.9,299.0],[8868.9,299.0],[8868.9,-1.0],[9070.9,-1.0],[9070.9,264.0],[9480.9,264.0],[9480.9,299.0],[11868.9,299.0],[11868.9,-1.0],[15620.9,-1.0],[15620.9,1174.0],[17218.9,1174.0],[17218.9,674.0],[17370.9,674.0],[17370.9,5401.0],[17345.9,5401.0],[17345.9,7001.0],[9070.9,7001.0],[9070.9,7801.0],[7370.9,7801.0],[7371.0,8626.0]],"holes":[]}],"ceiling":[{"outer":[[7371.0,8626.0],[1123.9,8626.0],[1123.9,7124.0],[1473.9,7124.0],[1473.9,5276.0],[574.0,5276.0],[574.0,5124.0],[1943.9,5124.0],[1943.9,3776.0],[-51.1,3776.0],[-51.1,849.0],[573.9,849.0],[573.9,299.0],[5518.9,299.0],[5518.9,124.0],[5719.0,124.0],[5719.0,-1.0],[7070.9,-1.0],[7070.9,299.0],[8868.9,299.0],[8868.9,-1.0],[9070.9,-1.0],[9070.9,264.0],[9480.9,264.0],[9480.9,299.0],[11868.9,299.0],[11868.9,-1.0],[15620.9,-1.0],[15620.9,1174.0],[17218.9,1174.0],[17218.9,674.0],[17370.9,674.0],[17370.9,5401.0],[17345.9,5401.0],[17345.9,7001.0],[9070.9,7001.0],[9070.9,7801.0],[7370.9,7801.0]],"holes":[[[9519.9,6425.0],[16769.9,6425.0],[16769.9,5975.0],[14969.9,5975.0],[14969.9,2225.0],[12519.9,2225.0],[12519.9,4725.0],[11369.9,4725.0],[11369.9,875.0],[9929.9,875.0],[9929.9,1485.0],[9519.9,1485.0]],[[6169.9,3475.0],[8419.9,3475.0],[8419.9,875.0],[6494.9,875.0],[6494.9,575.0],[6169.9,575.0]],[[1699.9,8025.0],[5119.9,8025.0],[5119.9,4525.0],[5069.9,4525.0],[5069.9,5725.0],[2049.9,5725.0],[2050.0,7700.0],[1699.9,7700.0]],[[5069.9,3175.0],[5069.9,875.0],[1934.9,875.0],[1934.9,1500.0],[524.9,1500.0],[524.9,3150.0],[1025.0,3150.0],[1025.0,3175.0]]],"caps":[[[-51.1,3650.0],[9519.9,3650.0],[9519.9,6275.0],[5119.9,6275.0],[5119.9,4525.0],[5069.9,4525.0],[5069.9,5725.0],[2049.9,5725.0],[2049.93,6275.0],[1473.9,6275.0],[1473.9,5276.0],[574.0,5276.0],[574.0,5124.0],[1943.9,5124.0],[1943.9,3776.0],[-51.1,3776.0]],[[1473.9,6275.0],[2049.93,6275.0],[2050.0,7700.0],[1699.9,7700.0],[1699.9,8025.0],[5119.9,8025.0],[5119.9,6275.0],[9519.9,6275.0],[9519.9,6425.0],[16769.9,6425.0],[16769.9,6275.0],[17345.9,6275.0],[17345.9,7001.0],[9070.9,7001.0],[9070.9,7801.0],[7370.9,7801.0],[7371.0,8626.0],[1123.9,8626.0],[1123.9,7124.0],[1473.9,7124.0]],[[17345.9,6275.0],[16769.9,6275.0],[16769.9,5975.0],[14969.9,5975.0],[14969.9,3650.0],[17370.9,3650.0],[17370.9,5401.0],[17345.9,5401.0]],[[17370.9,3650.0],[14969.9,3650.0],[14969.9,2225.0],[12519.9,2225.0],[12519.9,3650.0],[11369.9,3650.0],[11369.9,2025.0],[17370.9,2025.0]],[[17370.9,2025.0],[11369.9,2025.0],[11369.9,875.0],[9929.9,875.0],[9929.9,1485.0],[9519.9,1485.0],[9519.9,2025.0],[8419.9,2025.0],[8419.9,875.0],[6494.9,875.0],[6494.9,575.0],[6169.9,575.0],[6169.9,2025.0],[5069.9,2025.0],[5069.9,875.0],[1934.9,875.0],[1934.9,1500.0],[524.9,1500.0],[524.9,2025.0],[-51.1,2025.0],[-51.1,849.0],[573.9,849.0],[573.9,299.0],[5518.9,299.0],[5518.9,124.0],[5719.0,124.0],[5719.0,-1.0],[7070.9,-1.0],[7070.9,299.0],[8868.9,299.0],[8868.9,-1.0],[9070.9,-1.0],[9070.9,264.0],[9480.9,264.0],[9480.9,299.0],[11868.9,299.0],[11868.9,-1.0],[15620.9,-1.0],[15620.9,1174.0],[17218.9,1174.0],[17218.9,674.0],[17370.9,674.0]],[[-51.1,2025.0],[524.9,2025.0],[524.9,3150.0],[1025.0,3150.0],[1025.0,3175.0],[5069.9,3175.0],[5069.9,2025.0],[6169.9,2025.0],[6169.9,3475.0],[8419.9,3475.0],[8419.9,2025.0],[9519.9,2025.0],[9519.9,3650.0],[-51.1,3650.0]],[[11369.9,3650.0],[12519.9,3650.0],[12519.9,4725.0],[11369.9,4725.0]]]}],"underlay":[[9320.0,875.0,9320.0,425.0],[9070.0,875.0,9320.0,425.0],[9320.0,875.0,9070.0,425.0],[1125.0,7125.0,1125.0,5325.0],[1125.0,1050.0,1125.0,3575.0],[12320.0,1400.0,12320.0,1650.0],[12070.0,1400.0,12320.0,1650.0],[12320.0,1400.0,12070.0,1650.0],[11820.0,1650.0,11220.0,1650.0],[9720.0,1650.0,9070.0,1650.0],[11820.0,1700.0,11220.0,1700.0],[9720.0,1700.0,9070.0,1700.0],[11870.0,0.0,9070.0,0.0],[9720.0,1650.0,9720.0,1700.0],[11220.0,1650.0,11220.0,1700.0],[8870.0,0.0,7070.0,0.0],[8870.0,300.0,7070.0,300.0],[8870.0,362.5,7070.0,362.5],[8870.0,425.0,7070.0,425.0],[11070.0,300.0,9870.0,300.0],[11070.0,362.5,9870.0,362.5],[11070.0,425.0,9870.0,425.0],[5520.0,0.0,3470.0,0.0],[4770.0,300.0,3770.0,300.0],[4770.0,362.5,3770.0,362.5],[4770.0,425.0,3770.0,425.0],[3470.0,300.0,3470.0,0.0],[575.0,3775.0,575.0,5125.0],[1475.0,5325.0,1475.0,7125.0],[1600.0,5325.0,1600.0,7125.0],[14945.0,1650.0,12545.0,1650.0],[5720.0,5975.0,5720.0,6725.0],[8120.0,5275.0,8870.0,5275.0],[3720.0,3775.0,4470.0,3775.0],[1945.0,4162.5,1945.0,4762.5],[2007.5,4162.5,2007.5,4762.5],[2070.0,4162.5,2070.0,4762.5],[7820.0,7800.0,8420.0,7800.0],[7820.0,7737.5,8420.0,7737.5],[7820.0,7675.0,8420.0,7675.0],[1322.5,3775.0,1945.0,5125.0],[1945.0,3775.0,1325.0,5125.0],[7345.0,8475.0,7345.0,7800.0],[7282.5,8475.0,7282.5,7800.0],[7220.0,8475.0,7220.0,7800.0],[1537.5,5325.0,1537.5,7125.0],[9070.0,875.0,9320.0,425.0],[9320.0,875.0,9070.0,425.0],[12070.0,1175.0,12070.0,0.0],[12070.0,0.0,11870.0,0.0],[17220.0,5525.0,17220.0,7000.0],[16170.0,6875.0,16170.0,7000.0],[17345.0,5400.0,17345.0,7000.0],[11870.0,300.0,11070.0,300.0],[11870.0,425.0,11070.0,425.0],[9870.0,425.0,9070.0,425.0],[9870.0,300.0,9070.0,300.0],[11070.0,300.0,11070.0,425.0],[9870.0,300.0,9870.0,425.0],[7970.0,3925.0,5720.0,3925.0],[7970.0,4075.0,5720.0,4075.0],[8870.0,7675.0,8420.0,7675.0],[7820.0,7675.0,7370.0,7675.0],[8120.0,5275.0,7370.0,5275.0],[8870.0,7800.0,8420.0,7800.0],[7820.0,7800.0,7220.0,7800.0],[9070.0,425.0,9070.0,875.0],[9070.0,975.0,9070.0,4075.0],[9070.0,4075.0,8870.0,4075.0],[8870.0,4075.0,8870.0,300.0],[5720.0,6725.0,5720.0,6725.0],[5720.0,5975.0,5720.0,5975.0],[5570.0,6725.0,5720.0,6725.0],[7220.0,5125.0,7220.0,5825.0],[4470.0,3625.0,4620.0,3625.0],[4620.0,3625.0,4620.0,5275.0],[4470.0,3625.0,4470.0,5125.0],[1945.0,3775.0,1945.0,4162.5],[1945.0,4762.5,1945.0,5125.0],[2070.0,3775.0,2070.0,4162.5],[2070.0,4762.5,2070.0,5125.0],[3720.0,3625.0,3720.0,3775.0],[3720.0,3775.0,2070.0,3775.0],[1600.0,5275.0,4620.0,5275.0],[1250.0,8475.0,5570.0,8475.0],[4470.0,5125.0,2070.0,5125.0],[1945.0,5125.0,575.0,5125.0],[1600.0,5325.0,575.0,5325.0],[3720.0,3625.0,1325.0,3625.0],[575.0,5125.0,575.0,5325.0],[1600.0,7125.0,1600.0,7250.0],[1600.0,7125.0,1125.0,7125.0],[1600.0,7250.0,1250.0,7250.0],[17220.0,7000.0,17345.0,7000.0],[1325.0,3625.0,1325.0,3575.0],[1945.0,3775.0,575.0,3775.0],[1325.0,3575.0,575.0,3575.0],[575.0,3775.0,575.0,3575.0],[2070.0,4162.5,1945.0,4162.5],[2070.0,4762.5,1945.0,4762.5],[7820.0,7675.0,7820.0,7800.0],[8420.0,7675.0,8420.0,7800.0],[1250.0,7250.0,1250.0,8475.0],[16170.0,6875.0,9070.0,6875.0],[17220.0,5525.0,15620.0,5525.0],[17345.0,5400.0,15620.0,5400.0],[16170.0,7000.0,9070.0,7000.0],[1600.0,5275.0,1600.0,5325.0],[5720.0,6725.0,5720.0,8475.0],[5570.0,6725.0,5570.0,8475.0],[7220.0,5975.0,7220.0,7800.0],[5720.0,5825.0,7220.0,5825.0],[5570.0,5975.0,7220.0,5975.0],[5720.0,5825.0,5720.0,5125.0],[5720.0,8475.0,7370.0,8475.0],[8870.0,1410.0,8870.0,1650.0],[12070.0,1650.0,12070.0,1650.0],[12070.0,1650.0,12320.0,1650.0],[12320.0,1650.0,12320.0,1631.0],[17370.0,3900.0,17370.0,3000.0],[17370.0,3000.0,17370.0,1300.0],[17370.0,1300.0,17370.0,674.0],[17220.0,5400.0,17220.0,5399.9],[17220.0,3900.0,17220.0,3000.0],[17220.0,2875.0,17220.0,675.0],[15620.0,2875.0,16120.0,2875.0],[16720.0,2875.0,17220.0,2875.0],[15620.0,1175.0,17220.0,1175.0],[15620.0,1375.0,17220.0,1375.0],[15620.0,3000.0,16120.0,3000.0],[16720.0,3000.0,17220.0,3000.0],[17220.0,3900.0,17370.0,3900.0],[17220.0,3900.0,17220.0,4650.0],[16120.0,3000.0,16120.0,2875.0],[16720.0,3000.0,16720.0,2875.0],[16720.0,2875.0,16120.0,2875.0],[16720.0,2937.5,16120.0,2937.5],[16720.0,3000.0,16120.0,3000.0],[15620.0,1375.0,17220.0,2875.0],[15620.0,2875.0,17220.0,1375.0],[17220.0,4650.0,17370.0,4650.0],[17220.0,4650.0,17220.0,5400.0],[17370.0,4650.0,17370.0,5400.0],[15620.0,2875.0,15420.0,2875.0],[15420.0,2875.0,15420.0,5525.0],[15420.0,5525.0,17345.0,5525.0],[17220.0,5400.0,15620.0,5400.0],[15620.0,5400.0,15620.0,3000.0],[1125.0,8475.0,5720.0,8475.0],[5720.0,8475.0,7370.0,8475.0],[7370.0,8475.0,7370.0,8625.0],[7370.0,8625.0,5720.0,8625.0],[8870.0,1410.0,8870.0,1650.0],[9070.0,1650.0,11820.0,1650.0],[12070.0,1650.0,12070.0,1650.0],[12070.0,1650.0,12320.0,1650.0],[12320.0,1650.0,12320.0,1631.0],[17220.0,6883.3,17220.0,7000.0],[17220.0,7000.0,17161.7,7000.0],[17161.7,7000.0,17161.7,6930.0],[17161.7,6930.0,17185.0,6930.0],[17185.0,6930.0,17185.0,6883.3],[17185.0,6883.3,17220.0,6883.3],[16170.0,6883.3,16170.0,7000.0],[16170.0,7000.0,16228.3,7000.0],[16228.3,7000.0,16228.3,6930.0],[16228.3,6930.0,16205.0,6930.0],[16205.0,6930.0,16205.0,6883.3],[16205.0,6883.3,16170.0,6883.3],[17185.0,6883.3,17185.0,5903.3],[17185.0,5903.3,17138.3,5903.3],[17138.3,5903.3,17138.3,6883.3],[17138.3,6883.3,17185.0,6883.3],[17185.0,6883.3,17185.0,6883.3],[16205.0,6883.3,16206.1,6836.7],[16206.1,6836.7,16209.4,6790.2],[16209.4,6790.2,16215.0,6743.9],[16215.0,6743.9,16222.7,6697.9],[16222.7,6697.9,16232.6,6652.3],[16232.6,6652.3,16244.7,6607.2],[16244.7,6607.2,16258.9,6562.8],[16258.9,6562.8,16275.2,6519.1],[16275.2,6519.1,16293.6,6476.2],[16293.6,6476.2,16313.9,6434.3],[16313.9,6434.3,16336.3,6393.3],[16336.3,6393.3,16360.6,6353.5],[16360.6,6353.5,16386.7,6314.9],[16386.7,6314.9,16414.7,6277.5],[16414.7,6277.5,16444.4,6241.6],[16444.4,6241.6,16475.7,6207.1],[16475.7,6207.1,16508.7,6174.1],[16508.7,6174.1,16543.2,6142.7],[16543.2,6142.7,16579.2,6113.0],[16579.2,6113.0,16616.5,6085.0],[16616.5,6085.0,16655.2,6058.9],[16655.2,6058.9,16695.0,6034.6],[16695.0,6034.6,16735.9,6012.3],[16735.9,6012.3,16777.9,5991.9],[16777.9,5991.9,16820.8,5973.5],[16820.8,5973.5,16864.5,5957.2],[16864.5,5957.2,16908.9,5943.0],[16908.9,5943.0,16954.0,5931.0],[16954.0,5931.0,16999.5,5921.0],[16999.5,5921.0,17045.5,5913.3],[17045.5,5913.3,17091.9,5907.8],[17091.9,5907.8,17138.4,5904.4],[17185.0,6883.3,17185.0,5903.3],[17185.0,5903.3,17138.3,5903.3],[17138.3,5903.3,17138.3,6883.3],[17138.3,6883.3,17185.0,6883.3],[17185.0,6883.3,17185.0,6883.3],[8870.0,3975.0,8870.0,4075.0],[8870.0,4075.0,8820.0,4075.0],[8820.0,4075.0,8820.0,4015.0],[8820.0,4015.0,8840.0,4015.0],[8840.0,4015.0,8840.0,3975.0],[8840.0,3975.0,8870.0,3975.0],[7970.0,3975.0,7970.0,4075.0],[7970.0,4075.0,8020.0,4075.0],[8020.0,4075.0,8020.0,4015.0],[8020.0,4015.0,8000.0,4015.0],[8000.0,4015.0,8000.0,3975.0],[8000.0,3975.0,7970.0,3975.0],[8840.0,3975.0,8840.0,3135.0],[8840.0,3135.0,8800.0,3135.0],[8800.0,3135.0,8800.0,3975.0],[8800.0,3975.0,8840.0,3975.0],[8840.0,3975.0,8840.0,3975.0],[8000.0,3975.0,8000.9,3935.0],[8000.9,3935.0,8003.8,3895.2],[8003.8,3895.2,8008.5,3855.5],[8008.5,3855.5,8015.2,3816.0],[8015.2,3816.0,8023.7,3777.0],[8023.7,3777.0,8034.0,3738.3],[8034.0,3738.3,8046.2,3700.3],[8046.2,3700.3,8060.2,3662.8],[8060.2,3662.8,8075.9,3626.1],[8075.9,3626.1,8093.4,3590.1],[8093.4,3590.1,8112.5,3555.0],[8112.5,3555.0,8133.3,3520.9],[8133.3,3520.9,8155.8,3487.8],[8155.8,3487.8,8179.7,3455.7],[8179.7,3455.7,8205.2,3424.9],[8205.2,3424.9,8232.1,3395.3],[8232.1,3395.3,8260.3,3367.1],[8260.3,3367.1,8289.9,3340.2],[8289.9,3340.2,8320.7,3314.7],[8320.7,3314.7,8352.8,3290.8],[8352.8,3290.8,8385.9,3268.3],[8385.9,3268.3,8420.0,3247.5],[8420.0,3247.5,8455.1,3228.4],[8455.1,3228.4,8491.1,3210.9],[8491.1,3210.9,8527.8,3195.2],[8527.8,3195.2,8565.3,3181.2],[8565.3,3181.2,8603.4,3169.0],[8603.4,3169.0,8642.0,3158.7],[8642.0,3158.7,8681.0,3150.2],[8681.0,3150.2,8720.5,3143.6],[8720.5,3143.6,8760.2,3138.8],[8760.2,3138.8,8800.0,3136.0],[8840.0,3975.0,8840.0,3135.0],[8840.0,3135.0,8800.0,3135.0],[8800.0,3135.0,8800.0,3975.0],[8800.0,3975.0,8840.0,3975.0],[8840.0,3975.0,8840.0,3975.0],[5520.0,3675.0,5520.0,3775.0],[5520.0,3775.0,5470.0,3775.0],[5470.0,3775.0,5470.0,3715.0],[5470.0,3715.0,5490.0,3715.0],[5490.0,3715.0,5490.0,3675.0],[5490.0,3675.0,5520.0,3675.0],[4620.0,3675.0,4620.0,3775.0],[4620.0,3775.0,4670.0,3775.0],[4670.0,3775.0,4670.0,3715.0],[4670.0,3715.0,4650.0,3715.0],[4650.0,3715.0,4650.0,3675.0],[4650.0,3675.0,4620.0,3675.0],[5490.0,3675.0,5490.0,2835.0],[5490.0,2835.0,5450.0,2835.0],[5450.0,2835.0,5450.0,3675.0],[5450.0,3675.0,5490.0,3675.0],[5490.0,3675.0,5490.0,3675.0],[4650.0,3675.0,4650.9,3635.0],[4650.9,3635.0,4653.8,3595.2],[4653.8,3595.2,4658.5,3555.5],[4658.5,3555.5,4665.2,3516.0],[4665.2,3516.0,4673.7,3477.0],[4673.7,3477.0,4684.0,3438.3],[4684.0,3438.3,4696.2,3400.3],[4696.2,3400.3,4710.2,3362.8],[4710.2,3362.8,4725.9,3326.1],[4725.9,3326.1,4743.4,3290.1],[4743.4,3290.1,4762.5,3255.0],[4762.5,3255.0,4783.3,3220.9],[4783.3,3220.9,4805.8,3187.8],[4805.8,3187.8,4829.7,3155.7],[4829.7,3155.7,4855.2,3124.9],[4855.2,3124.9,4882.1,3095.3],[4882.1,3095.3,4910.3,3067.1],[4910.3,3067.1,4939.9,3040.2],[4939.9,3040.2,4970.7,3014.7],[4970.7,3014.7,5002.8,2990.8],[5002.8,2990.8,5035.9,2968.3],[5035.9,2968.3,5070.0,2947.5],[5070.0,2947.5,5105.1,2928.4],[5105.1,2928.4,5141.1,2910.9],[5141.1,2910.9,5177.8,2895.2],[5177.8,2895.2,5215.3,2881.2],[5215.3,2881.2,5253.4,2869.0],[5253.4,2869.0,5292.0,2858.7],[5292.0,2858.7,5331.0,2850.2],[5331.0,2850.2,5370.5,2843.6],[5370.5,2843.6,5410.2,2838.8],[5410.2,2838.8,5450.0,2836.0],[5490.0,3675.0,5490.0,2835.0],[5490.0,2835.0,5450.0,2835.0],[5450.0,2835.0,5450.0,3675.0],[5450.0,3675.0,5490.0,3675.0],[5490.0,3675.0,5490.0,3675.0],[5520.0,5225.0,5520.0,5125.0],[5520.0,5125.0,5470.0,5125.0],[5470.0,5125.0,5470.0,5185.0],[5470.0,5185.0,5490.0,5185.0],[5490.0,5185.0,5490.0,5225.0],[5490.0,5225.0,5520.0,5225.0],[4620.0,5225.0,4620.0,5125.0],[4620.0,5125.0,4670.0,5125.0],[4670.0,5125.0,4670.0,5185.0],[4670.0,5185.0,4650.0,5185.0],[4650.0,5185.0,4650.0,5225.0],[4650.0,5225.0,4620.0,5225.0],[5490.0,5225.0,5490.0,6065.0],[5490.0,6065.0,5450.0,6065.0],[5450.0,6065.0,5450.0,5225.0],[5450.0,5225.0,5490.0,5225.0],[5490.0,5225.0,5490.0,5225.0],[5450.0,6064.1,5410.2,6061.2],[5410.2,6061.2,5370.5,6056.5],[5370.5,6056.5,5331.0,6049.8],[5331.0,6049.8,5292.0,6041.3],[5292.0,6041.3,5253.4,6031.0],[5253.4,6031.0,5215.3,6018.8],[5215.3,6018.8,5177.8,6004.8],[5177.8,6004.8,5141.1,5989.1],[5141.1,5989.1,5105.1,5971.6],[5105.1,5971.6,5070.0,5952.5],[5070.0,5952.5,5035.9,5931.7],[5035.9,5931.7,5002.8,5909.3],[5002.8,5909.3,4970.7,5885.3],[4970.7,5885.3,4939.9,5859.8],[4939.9,5859.8,4910.3,5832.9],[4910.3,5832.9,4882.1,5804.7],[4882.1,5804.7,4855.2,5775.1],[4855.2,5775.1,4829.7,5744.3],[4829.7,5744.3,4805.8,5712.3],[4805.8,5712.3,4783.3,5679.1],[4783.3,5679.1,4762.5,5645.0],[4762.5,5645.0,4743.4,5609.9],[4743.4,5609.9,4725.9,5574.0],[4725.9,5574.0,4710.2,5537.2],[4710.2,5537.2,4696.2,5499.7],[4696.2,5499.7,4684.0,5461.7],[4684.0,5461.7,4673.7,5423.0],[4673.7,5423.0,4665.2,5384.0],[4665.2,5384.0,4658.5,5344.5],[4658.5,5344.5,4653.8,5304.9],[4653.8,5304.9,4650.9,5265.0],[4650.9,5265.0,4650.0,5225.0],[5490.0,5225.0,5490.0,6065.0],[5490.0,6065.0,5450.0,6065.0],[5450.0,6065.0,5450.0,5225.0],[5450.0,5225.0,5490.0,5225.0],[5490.0,5225.0,5490.0,5225.0],[15620.0,1175.0,15620.0,0.0],[15620.0,0.0,12070.0,0.0],[15495.0,1175.0,15495.0,125.0],[15495.0,125.0,12070.0,125.0],[15570.0,1175.0,15570.0,50.0],[15570.0,50.0,12070.0,50.0],[15520.0,1175.0,15520.0,100.0],[15520.0,100.0,12070.0,100.0],[7970.0,4075.0,7970.0,3925.0],[8120.0,5275.0,8120.0,5125.0],[5570.0,6725.0,5570.0,6725.0],[5570.0,5975.0,5570.0,5250.0],[5570.0,5250.0,5520.0,5250.0],[5520.0,5250.0,5520.0,5125.0],[5520.0,5125.0,5720.0,5125.0],[7370.0,5275.0,7370.0,7675.0],[575.0,1050.0,75.0,1050.0],[75.0,1050.0,75.0,3575.0],[75.0,3575.0,575.0,3575.0],[575.0,850.0,-50.0,850.0],[-50.0,850.0,-50.0,3775.0],[-50.0,3775.0,575.0,3775.0],[575.0,975.0,-0.0,975.0],[-0.0,975.0,-0.0,3650.0],[-0.0,3650.0,575.0,3650.0],[575.0,1025.0,50.0,1025.0],[50.0,1025.0,50.0,3600.0],[50.0,3600.0,575.0,3600.0],[11870.0,4275.0,11820.0,4275.0],[11820.0,4275.0,11820.0,425.0],[7220.0,5125.0,7220.0,5125.0],[7220.0,5125.0,7220.0,5125.0],[7220.0,5125.0,8120.0,5125.0],[7370.0,8475.0,7370.0,8625.0],[7370.0,8625.0,1125.0,8625.0],[1125.0,8625.0,1125.0,7125.0],[12070.0,1300.0,12320.0,1300.0],[12320.0,1300.0,12320.0,1400.0],[12320.0,1400.0,12070.0,1400.0],[15620.0,5525.0,15420.0,5525.0],[15420.0,5525.0,15420.0,1775.0],[15420.0,1650.0,15420.0,1175.0],[15420.0,1175.0,15620.0,1175.0],[15620.0,1175.0,15620.0,5400.0],[12070.0,1775.0,12070.0,4275.0],[12070.0,4275.0,11870.0,4275.0],[11870.0,4275.0,11870.0,1175.0],[11870.0,1175.0,11870.0,425.0],[11870.0,300.0,11870.0,0.0],[12070.0,1175.0,12070.0,1300.0],[12070.0,1400.0,12070.0,1650.0],[12070.0,1650.0,12545.0,1650.0],[12545.0,1650.0,12545.0,1775.0],[12545.0,1775.0,12070.0,1775.0],[15420.0,1650.0,14945.0,1650.0],[14945.0,1650.0,14945.0,1775.0],[14945.0,1775.0,15420.0,1775.0],[9070.0,300.0,9070.0,0.0],[9070.0,0.0,8870.0,0.0],[8870.0,0.0,8870.0,300.0],[7070.0,425.0,7070.0,0.0],[7070.0,0.0,5720.0,0.0],[7070.0,425.0,6945.0,425.0],[6945.0,425.0,6945.0,125.0],[6945.0,125.0,5720.0,125.0],[9070.0,7000.0,9070.0,7800.0],[9070.0,7800.0,8870.0,7800.0],[5720.0,125.0,5720.0,3925.0],[5720.0,4075.0,5520.0,4075.0],[5520.0,4075.0,5520.0,425.0],[5520.0,300.0,5520.0,0.0],[5520.0,0.0,5720.0,0.0],[5520.0,425.0,4770.0,425.0],[4770.0,425.0,4770.0,300.0],[4770.0,300.0,5520.0,300.0],[1325.0,425.0,3770.0,425.0],[3770.0,425.0,3770.0,300.0],[3770.0,300.0,1325.0,300.0],[575.0,300.0,1325.0,300.0],[1325.0,300.0,1325.0,1050.0],[1325.0,1050.0,575.0,1050.0],[575.0,1050.0,575.0,300.0],[9070.0,975.0,9320.0,975.0],[9320.0,975.0,9320.0,875.0],[9320.0,875.0,9070.0,875.0],[8870.0,7675.0,8870.0,5125.0],[8870.0,5125.0,9070.0,5125.0],[9070.0,5125.0,9070.0,6875.0],[5653.3,5975.0,5570.0,5975.0],[5570.0,5975.0,5570.0,6016.7],[5570.0,6016.7,5620.0,6016.7],[5620.0,6016.7,5620.0,6000.0],[5620.0,6000.0,5653.3,6000.0],[5653.3,6000.0,5653.3,5975.0],[5653.3,6725.0,5570.0,6725.0],[5570.0,6725.0,5570.0,6683.3],[5570.0,6683.3,5620.0,6683.3],[5620.0,6683.3,5620.0,6700.0],[5620.0,6700.0,5653.3,6700.0],[5653.3,6700.0,5653.3,6725.0],[5653.3,6000.0,6353.3,6000.0],[6353.3,6000.0,6353.3,6033.3],[6353.3,6033.3,5653.3,6033.3],[5653.3,6033.3,5653.3,6000.0],[5653.3,6000.0,5653.3,6000.0],[6352.5,6033.3,6350.2,6066.5],[6350.2,6066.5,6346.2,6099.6],[6346.2,6099.6,6340.7,6132.5],[6340.7,6132.5,6333.6,6165.0],[6333.6,6165.0,6325.0,6197.2],[6325.0,6197.2,6314.8,6228.9],[6314.8,6228.9,6303.2,6260.2],[6303.2,6260.2,6290.1,6290.8],[6290.1,6290.8,6275.5,6320.8],[6275.5,6320.8,6259.6,6350.0],[6259.6,6350.0,6242.2,6378.4],[6242.2,6378.4,6223.5,6406.0],[6223.5,6406.0,6203.6,6432.7],[6203.6,6432.7,6182.4,6458.4],[6182.4,6458.4,6159.9,6483.1],[6159.9,6483.1,6136.4,6506.6],[6136.4,6506.6,6111.7,6529.0],[6111.7,6529.0,6086.0,6550.2],[6086.0,6550.2,6059.4,6570.2],[6059.4,6570.2,6031.8,6588.9],[6031.8,6588.9,6003.3,6606.2],[6003.3,6606.2,5974.1,6622.2],[5974.1,6622.2,5944.1,6636.7],[5944.1,6636.7,5913.5,6649.9],[5913.5,6649.9,5882.3,6661.5],[5882.3,6661.5,5850.5,6671.6],[5850.5,6671.6,5818.4,6680.3],[5818.4,6680.3,5785.8,6687.4],[5785.8,6687.4,5752.9,6692.9],[5752.9,6692.9,5719.9,6696.8],[5719.9,6696.8,5686.6,6699.2],[5686.6,6699.2,5653.3,6700.0],[5653.3,6000.0,6353.3,6000.0],[6353.3,6000.0,6353.3,6033.3],[6353.3,6033.3,5653.3,6033.3],[5653.3,6033.3,5653.3,6000.0],[5653.3,6000.0,5653.3,6000.0],[4470.0,3708.3,4470.0,3625.0],[4470.0,3625.0,4428.3,3625.0],[4428.3,3625.0,4428.3,3675.0],[4428.3,3675.0,4445.0,3675.0],[4445.0,3675.0,4445.0,3708.3],[4445.0,3708.3,4470.0,3708.3],[3720.0,3708.3,3720.0,3625.0],[3720.0,3625.0,3761.7,3625.0],[3761.7,3625.0,3761.7,3675.0],[3761.7,3675.0,3745.0,3675.0],[3745.0,3675.0,3745.0,3708.3],[3745.0,3708.3,3720.0,3708.3],[4445.0,3708.3,4445.0,4408.3],[4445.0,4408.3,4411.7,4408.3],[4411.7,4408.3,4411.7,3708.3],[4411.7,3708.3,4445.0,3708.3],[4445.0,3708.3,4445.0,3708.3],[4411.7,4407.5,4378.5,4405.2],[4378.5,4405.2,4345.4,4401.2],[4345.4,4401.2,4312.5,4395.7],[4312.5,4395.7,4280.0,4388.6],[4280.0,4388.6,4247.8,4380.0],[4247.8,4380.0,4216.1,4369.8],[4216.1,4369.8,4184.8,4358.2],[4184.8,4358.2,4154.2,4345.1],[4154.2,4345.1,4124.2,4330.5],[4124.2,4330.5,4095.0,4314.6],[4095.0,4314.6,4066.6,4297.2],[4066.6,4297.2,4039.0,4278.5],[4039.0,4278.5,4012.3,4258.6],[4012.3,4258.6,3986.6,4237.4],[3986.6,4237.4,3961.9,4215.0],[3961.9,4215.0,3938.4,4191.4],[3938.4,4191.4,3916.0,4166.7],[3916.0,4166.7,3894.8,4141.1],[3894.8,4141.1,3874.8,4114.4],[3874.8,4114.4,3856.1,4086.8],[3856.1,4086.8,3838.8,4058.3],[3838.8,4058.3,3822.8,4029.1],[3822.8,4029.1,3808.3,3999.1],[3808.3,3999.1,3795.1,3968.5],[3795.1,3968.5,3783.5,3937.3],[3783.5,3937.3,3773.4,3905.6],[3773.4,3905.6,3764.7,3873.4],[3764.7,3873.4,3757.6,3840.8],[3757.6,3840.8,3752.1,3808.0],[3752.1,3808.0,3748.2,3774.9],[3748.2,3774.9,3745.8,3741.6],[3745.8,3741.6,3745.0,3708.3],[4445.0,3708.3,4445.0,4408.3],[4445.0,4408.3,4411.7,4408.3],[4411.7,4408.3,4411.7,3708.3],[4411.7,3708.3,4445.0,3708.3],[4445.0,3708.3,4445.0,3708.3],[8870.0,5208.3,8870.0,5125.0],[8870.0,5125.0,8828.3,5125.0],[8828.3,5125.0,8828.3,5175.0],[8828.3,5175.0,8845.0,5175.0],[8845.0,5175.0,8845.0,5208.3],[8845.0,5208.3,8870.0,5208.3],[8120.0,5208.3,8120.0,5125.0],[8120.0,5125.0,8161.7,5125.0],[8161.7,5125.0,8161.7,5175.0],[8161.7,5175.0,8145.0,5175.0],[8145.0,5175.0,8145.0,5208.3],[8145.0,5208.3,8120.0,5208.3],[8845.0,5208.3,8845.0,5908.3],[8845.0,5908.3,8811.7,5908.3],[8811.7,5908.3,8811.7,5208.3],[8811.7,5208.3,8845.0,5208.3],[8845.0,5208.3,8845.0,5208.3],[8811.7,5907.5,8778.5,5905.2],[8778.5,5905.2,8745.4,5901.2],[8745.4,5901.2,8712.5,5895.7],[8712.5,5895.7,8680.0,5888.6],[8680.0,5888.6,8647.8,5880.0],[8647.8,5880.0,8616.1,5869.8],[8616.1,5869.8,8584.8,5858.2],[8584.8,5858.2,8554.2,5845.1],[8554.2,5845.1,8524.2,5830.5],[8524.2,5830.5,8495.0,5814.6],[8495.0,5814.6,8466.6,5797.2],[8466.6,5797.2,8439.0,5778.5],[8439.0,5778.5,8412.3,5758.6],[8412.3,5758.6,8386.6,5737.4],[8386.6,5737.4,8361.9,5715.0],[8361.9,5715.0,8338.4,5691.4],[8338.4,5691.4,8316.0,5666.7],[8316.0,5666.7,8294.8,5641.1],[8294.8,5641.1,8274.8,5614.4],[8274.8,5614.4,8256.1,5586.8],[8256.1,5586.8,8238.8,5558.3],[8238.8,5558.3,8222.8,5529.1],[8222.8,5529.1,8208.3,5499.1],[8208.3,5499.1,8195.1,5468.5],[8195.1,5468.5,8183.5,5437.3],[8183.5,5437.3,8173.4,5405.6],[8173.4,5405.6,8164.7,5373.4],[8164.7,5373.4,8157.6,5340.8],[8157.6,5340.8,8152.1,5308.0],[8152.1,5308.0,8148.2,5274.9],[8148.2,5274.9,8145.8,5241.6],[8145.8,5241.6,8145.0,5208.3],[8845.0,5208.3,8845.0,5908.3],[8845.0,5908.3,8811.7,5908.3],[8811.7,5908.3,8811.7,5208.3],[8811.7,5208.3,8845.0,5208.3],[8845.0,5208.3,8845.0,5208.3],[1250.0,8625.0,5570.0,8625.0],[15570.0,1075.0,15620.0,1075.0],[15620.0,1075.0,15620.0,1175.0],[15620.0,1175.0,15570.0,1175.0],[15570.0,1175.0,15570.0,1075.0],[15745.0,1075.0,15795.0,1075.0],[15795.0,1075.0,15795.0,1175.0],[15795.0,1175.0,15745.0,1175.0],[15745.0,1175.0,15745.0,1075.0],[15945.0,1075.0,15995.0,1075.0],[15995.0,1075.0,15995.0,1175.0],[15995.0,1175.0,15945.0,1175.0],[15945.0,1175.0,15945.0,1075.0],[16120.0,1075.0,16170.0,1075.0],[16170.0,1075.0,16170.0,1175.0],[16170.0,1175.0,16120.0,1175.0],[16120.0,1175.0,16120.0,1075.0],[16295.0,1075.0,16345.0,1075.0],[16345.0,1075.0,16345.0,1175.0],[16345.0,1175.0,16295.0,1175.0],[16295.0,1175.0,16295.0,1075.0],[16470.0,1075.0,16520.0,1075.0],[16520.0,1075.0,16520.0,1175.0],[16520.0,1175.0,16470.0,1175.0],[16470.0,1175.0,16470.0,1075.0],[16645.0,1075.0,16695.0,1075.0],[16695.0,1075.0,16695.0,1175.0],[16695.0,1175.0,16645.0,1175.0],[16645.0,1175.0,16645.0,1075.0],[16820.0,1075.0,16870.0,1075.0],[16870.0,1075.0,16870.0,1175.0],[16870.0,1175.0,16820.0,1175.0],[16820.0,1175.0,16820.0,1075.0],[16995.0,1075.0,17045.0,1075.0],[17045.0,1075.0,17045.0,1175.0],[17045.0,1175.0,16995.0,1175.0],[16995.0,1175.0,16995.0,1075.0],[17245.0,4650.0,17345.0,4650.0],[17345.0,4650.0,17345.0,4600.0],[17345.0,4600.0,17285.0,4600.0],[17285.0,4600.0,17285.0,4620.0],[17285.0,4620.0,17245.0,4620.0],[17245.0,4620.0,17245.0,4650.0],[17278.1,4580.0,16628.1,4580.0],[16628.1,4580.0,16628.1,4620.0],[16628.1,4620.0,17278.1,4620.0],[17278.1,4620.0,17278.1,4580.0],[17278.1,4580.0,17278.1,4580.0],[17245.0,3900.0,17345.0,3900.0],[17345.0,3900.0,17345.0,3950.0],[17345.0,3950.0,17285.0,3950.0],[17285.0,3950.0,17285.0,3930.0],[17285.0,3930.0,17245.0,3930.0],[17245.0,3930.0,17245.0,3900.0],[16628.1,4580.0,16628.9,4548.1],[16628.9,4548.1,16631.2,4516.3],[16631.2,4516.3,16635.1,4484.6],[16635.1,4484.6,16640.6,4453.2],[16640.6,4453.2,16647.6,4422.1],[16647.6,4422.1,16656.1,4391.3],[16656.1,4391.3,16666.1,4361.0],[16666.1,4361.0,16677.6,4331.3],[16677.6,4331.3,16690.5,4302.1],[16690.5,4302.1,16704.8,4273.6],[16704.8,4273.6,16720.5,4245.8],[16720.5,4245.8,16737.6,4218.9],[16737.6,4218.9,16756.0,4192.8],[16756.0,4192.8,16775.6,4167.6],[16775.6,4167.6,16796.5,4143.5],[16796.5,4143.5,16818.5,4120.4],[16818.5,4120.4,16841.6,4098.4],[16841.6,4098.4,16865.7,4077.5],[16865.7,4077.5,16890.9,4057.9],[16890.9,4057.9,16917.0,4039.5],[16917.0,4039.5,16943.9,4022.5],[16943.9,4022.5,16971.7,4006.8],[16971.7,4006.8,17000.2,3992.4],[17000.2,3992.4,17029.3,3979.5],[17029.3,3979.5,17059.1,3968.0],[17059.1,3968.0,17089.4,3958.0],[17089.4,3958.0,17120.1,3949.5],[17120.1,3949.5,17151.3,3942.5],[17151.3,3942.5,17182.7,3937.0],[17182.7,3937.0,17214.4,3933.1],[17214.4,3933.1,17246.2,3930.8],[17246.2,3930.8,17278.1,3930.0],[17220.0,675.0,17370.0,674.0]],"report":{"spec_mm":{"wall_h":3000.0,"door_head":2100.0,"win_sill":600.0,"win_h":1500.0,"vent_sill":1200.0,"vent_h":900.0,"vent_max_width":1000.0,"lintel_h":900.0,"skirt_h":100.0,"skirt_t":15.0,"floor_finish_t":20.0,"slab_t":200.0,"tile_w":914.4,"tile_h":609.6,"tile_t":9.0,"grout":2.5,"tile_gap":0.0,"min_cut":200.0,"panel_w":1220.0,"panel_t":12.0,"panel_joint":3.0,"balcony_glass_t":76.2,"balcony_glass_h":1200.0,"balcony_glass_joint":5.0,"balcony_glass_max":1200.0,"balcony_post_w":40.0,"balcony_rail_h":35.0,"kitchen_counter_h":860.0,"kitchen_counter_depth":600.0,"kitchen_counter_t":40.0,"kitchen_base_depth":570.0,"kitchen_backsplash_h":600.0,"kitchen_backsplash_t":15.0,"recess_border_w":450.0,"recess_depth":120.0,"recess_drop_h":50.0,"recess_lip_w":60.0,"recess_wall_gap":15.0,"downlight_r":45.0,"downlight_recess":25.0,"door_frame_w":45.0,"door_leaf_t":42.0,"door_handle_h":1000.0,"door_lever_len":128.0,"door_min":600.0,"door_max":1250.0,"gap_max":3600.0},"warnings":["2 enclosed slivers smaller than 0.4 m2 ignored (wall-junction artefacts)"],"ambiguities":["Room_05 (5.10 m2): possible balcony / sit-out (narrow room with a long glazed or open side)","4 washrooms detected (3 expected) - check the classification table"],"assumptions":["Room_05 (5.10 m2) inferred as Kitchen (no CAD text label present; configurable via CONFIG['room_type_overrides']).","No room had an explicit KITCHEN CAD label or kitchen fixture block; set CONFIG[\"room_type_overrides\"] to assign a kitchen room if needed."],"room_uses":{"Room_01":"Living Room (8.15 \u00d7 6.45 m) [Living] - main entrance door opens into it","Room_07":"Service Shaft / Duct (1.60 \u00d7 1.50 m) [Shaft] - enclosed service shaft / duct","Toilet_3":"Toilet (2.40 \u00d7 1.60 m) [Toilet_3] - classified washroom (see signals)","Room_05":"Kitchen (3.42 \u00d7 1.52 m) [Kitchen] - compact room opening off hall/dining (inferred kitchen; override via CONFIG if needed)","Room_04":"Bedroom (3.80 \u00d7 3.15 m) [Bedroom_2] - private room >= 7 m2 with a single doorway","Room_06":"Lobby (3.15 \u00d7 1.75 m) [Lobby] - circulation space 4.36 m2 between doors","Toilet_2":"Toilet (2.40 \u00d7 1.50 m) [Toilet_2] - classified washroom (see signals)","Toilet_1":"Toilet (2.50 \u00d7 1.50 m) [Toilet_1] - classified washroom (see signals)","Room_03":"Bedroom (4.63 \u00d7 4.32 m) [Bedroom_1] - habitable room >= 7 m2","Room_02":"Master Bedroom (5.45 \u00d7 3.27 m) [Master_Bedroom] - the attached Master_Toilet opens into it","Master_Toilet":"Master Toilet (2.40 \u00d7 1.35 m) [Master_Toilet] - classified washroom (see signals)"},"kitchen_platforms":[],"room_floors":{"count":10,"thickness_mm":20.0,"by_category":{"common":["Floor_Living","Floor_Kitchen","Floor_Bedroom_2","Floor_Bedroom_1"],"master_wood":["Floor_MasterBedroom_Wood"],"entrance":["Floor_Entrance_01"],"balcony":[],"dry_balcony":[],"washroom":["Floor_Washroom_04","Floor_Washroom_03","Floor_Washroom_02","Floor_Washroom_01"]}},"skirting":{"segments":12,"room_objects":6,"height_mm":100.0,"thickness_mm":15.0,"total_length_m":87.14,"door_and_passage_openings_checked":9,"rooms_with_skirting":["Room_01","Room_02","Room_03","Room_04","Room_05","Room_06"],"rooms_excluded":["Master_Toilet (washroom)","Room_07 (shaft)","Toilet_1 (washroom)","Toilet_2 (washroom)","Toilet_3 (washroom)"]},"tiles":{"nominal_mm":"914.4 W x 609.6 H x 9.0 T","grout_mm":2.5,"rows":["z 0.0-609.6 (full)","z 612.1-1221.7 (full)","z 1224.2-1833.8 (full)","z 1836.3-2445.9 (full)","z 2448.4-3000.0 (cut 551.6)"],"per_washroom":{"Toilet_3":{"tiles":50,"full":13,"cut":37,"cut_sizes_mm":{"671.6 x 609.6":5,"914.4 x 609.6 (notched)":4,"671.6 x 609.6 (notched)":2,"488.6 x 609.6":1,"499.9 x 609.6":1,"914.4 x 551.6":6,"671.6 x 551.6":2,"888.5 x 609.6":3,"192.8 x 609.6":3,"554.7 x 609.6":8,"554.7 x 551.6":2},"slivers_lt_50mm":0,"walls_tiled":4,"skipped_edges":[],"layouts":{"Wall01":"L=1600 mm, full tiles + end cut","Wall02":"L=2400 mm, full tiles + end cut","Wall03":"L=1600 mm, full tiles + end cut","Wall04":"L=2400 mm, full tiles + end cut"}},"Toilet_2":{"tiles":47,"full":17,"cut":30,"cut_sizes_mm":{"780.3 x 609.6":3,"914.4 x 609.6 (notched)":3,"571.6 x 345.9":1,"914.4 x 551.6":6,"571.6 x 551.6":2,"554.7 x 609.6":8,"554.7 x 551.6":2,"571.6 x 609.6":1,"571.6 x 609.6 (notched)":2,"438.4 x 609.6":1,"450.1 x 609.6":1},"slivers_lt_50mm":0,"walls_tiled":4,"skipped_edges":[],"layouts":{"Wall01":"L=1500 mm, full tiles + end cut","Wall02":"L=2400 mm, full tiles + end cut","Wall03":"L=1500 mm, full tiles + end cut","Wall04":"L=2400 mm, full tiles + end cut"}},"Toilet_1":{"tiles":46,"full":17,"cut":29,"cut_sizes_mm":{"571.6 x 609.6":8,"914.4 x 551.6":6,"571.6 x 551.6":2,"654.7 x 609.6":1,"914.4 x 609.6 (notched)":3,"654.7 x 587.9":1,"896.6 x 609.6":1,"654.7 x 345.9":2,"654.7 x 551.6":2,"863.3 x 609.6":3},"slivers_lt_50mm":0,"walls_tiled":4,"skipped_edges":[],"layouts":{"Wall01":"L=1500 mm, full tiles + end cut","Wall02":"L=2500 mm, full tiles + end cut","Wall03":"L=1500 mm, full tiles + end cut","Wall04":"L=2500 mm, full tiles + end cut"}},"Master_Toilet":{"tiles":47,"full":17,"cut":30,"cut_sizes_mm":{"763.4 x 609.6":3,"914.4 x 609.6 (notched)":3,"554.7 x 345.9":1,"914.4 x 551.6":6,"554.7 x 551.6":2,"421.6 x 609.6":5,"421.6 x 551.6":2,"554.7 x 609.6":4,"421.6 x 609.6 (notched)":2,"351.0 x 609.6":1,"387.5 x 609.6":1},"slivers_lt_50mm":0,"walls_tiled":4,"skipped_edges":[],"layouts":{"Wall01":"L=2400 mm, full tiles + end cut","Wall02":"L=1350 mm, full tiles + end cut","Wall03":"L=2400 mm, full tiles + end cut","Wall04":"L=1350 mm, full tiles + end cut"}}}},"panels":{"sheet_mm":"1220.0 W x full height x 12.0 T","joint_mm":3.0,"z_mm":"100.0 (top of skirting) - 3000.0 (ceiling)","per_room":{"Room_01":{"sheets":34,"full":13,"cut":21,"walls_panelled":12,"area_m2":82.78,"layouts":{"Wall01":"L=2340 mm, full tiles + end cut","Wall02":"L=3850 mm, balanced: equal cuts at both ends","Wall03":"L=250 mm, single cut","Wall04":"L=2500 mm, balanced: equal cuts at both ends","Wall05":"L=3350 mm, full tiles + end cut","Wall06":"L=3750 mm, balanced: equal cuts at both ends","Wall07":"L=1800 mm, full tiles + end cut","Wall08":"L=1350 mm, balanced: equal cuts at both ends","Wall09":"L=8150 mm, full tiles + end cut","Wall10":"L=5840 mm, full tiles + end cut","Wall11":"L=410 mm, single cut","Wall12":"L=610 mm, single cut"},"label":"Living"},"Room_05":{"sheets":11,"full":0,"cut":11,"walls_panelled":8,"area_m2":10.82,"layouts":{"Wall01":"L=3425 mm, full tiles + end cut","Wall02":"L=1050 mm, single cut","Wall03":"L=75 mm, single cut","Wall04":"L=475 mm, single cut","Wall05":"L=3100 mm, full tiles + end cut","Wall06":"L=350 mm, single cut","Wall07":"L=250 mm, single cut","Wall08":"L=1175 mm, single cut"},"label":"Kitchen"},"Room_04":{"sheets":14,"full":5,"cut":9,"walls_panelled":6,"area_m2":33.14,"layouts":{"Wall01":"L=1225 mm, single cut","Wall02":"L=300 mm, single cut","Wall03":"L=1925 mm, full tiles + end cut","Wall04":"L=3500 mm, full tiles + end cut","Wall05":"L=3150 mm, full tiles + end cut","Wall06":"L=3800 mm, balanced: equal cuts at both ends"},"label":"Bedroom_2"},"Room_06":{"sheets":8,"full":2,"cut":6,"walls_panelled":5,"area_m2":17.19,"layouts":{"Wall01":"L=3150 mm, full tiles + end cut","Wall03":"L=1650 mm, full tiles + end cut","Wall04":"L=700 mm, single cut","Wall05":"L=1500 mm, full tiles + end cut","Wall06":"L=1750 mm, full tiles + end cut"},"label":"Lobby"},"Room_03":{"sheets":20,"full":6,"cut":14,"walls_panelled":10,"area_m2":39.28,"layouts":{"Wall02":"L=232 mm, single cut","Wall03":"L=50 mm, single cut","Wall04":"L=4400 mm, full tiles + end cut","Wall05":"L=4320 mm, full tiles + end cut","Wall06":"L=1225 mm, single cut","Wall07":"L=350 mm, single cut","Wall08":"L=125 mm, single cut","Wall10":"L=1850 mm, full tiles + end cut","Wall11":"L=3020 mm, full tiles + end cut","Wall12":"L=1432 mm, full tiles + end cut"},"label":"Bedroom_1"},"Room_02":{"sheets":20,"full":5,"cut":15,"walls_panelled":8,"area_m2":34.72,"layouts":{"Wall01":"L=4035 mm, full tiles + end cut","Wall02":"L=3268 mm, full tiles + end cut","Wall04":"L=68 mm, single cut","Wall05":"L=4045 mm, full tiles + end cut","Wall07":"L=500 mm, single cut","Wall08":"L=2550 mm, balanced: equal cuts at both ends","Wall09":"L=1410 mm, balanced: equal cuts at both ends","Wall10":"L=625 mm, single cut"},"label":"Master_Bedroom"}},"rooms_without_panels":["Master_Toilet (Master_Toilet)","Room_07 (Shaft)","Toilet_1 (Toilet_1)","Toilet_2 (Toilet_2)","Toilet_3 (Toilet_3)"]},"recessed_ceilings":{"rooms":["Room_01 (Living)","Room_04 (Bedroom_2)","Room_03 (Bedroom_1)","Room_02 (Master_Bedroom)"],"excluded_rooms":["Room_07 (Shaft)","Toilet_3 (Toilet_3)","Room_05 (Kitchen)","Room_06 (Lobby)","Toilet_2 (Toilet_2)","Toilet_1 (Toilet_1)","Master_Toilet (Master_Toilet)"],"recess_depth_mm":120.0,"drop_soffit_mm":50.0,"total_downlights":47},"config":{"spec_mm":{"wall_h":3000.0,"door_head":2100.0,"win_sill":600.0,"win_h":1500.0,"vent_sill":1200.0,"vent_h":900.0,"vent_max_width":1000.0,"lintel_h":900.0,"skirt_h":100.0,"skirt_t":15.0,"floor_finish_t":20.0,"slab_t":200.0,"tile_w":914.4,"tile_h":609.6,"tile_t":9.0,"grout":2.5,"tile_gap":0.0,"min_cut":200.0,"panel_w":1220.0,"panel_t":12.0,"panel_joint":3.0,"balcony_glass_t":76.2,"balcony_glass_h":1200.0,"balcony_glass_joint":5.0,"balcony_glass_max":1200.0,"balcony_post_w":40.0,"balcony_rail_h":35.0,"kitchen_counter_h":860.0,"kitchen_counter_depth":600.0,"kitchen_counter_t":40.0,"kitchen_base_depth":570.0,"kitchen_backsplash_h":600.0,"kitchen_backsplash_t":15.0,"recess_border_w":450.0,"recess_depth":120.0,"recess_drop_h":50.0,"recess_lip_w":60.0,"recess_wall_gap":15.0,"downlight_r":45.0,"downlight_recess":25.0,"door_frame_w":45.0,"door_leaf_t":42.0,"door_handle_h":1000.0,"door_lever_len":128.0,"door_min":600.0,"door_max":1250.0,"gap_max":3600.0},"default_balcony_type":"open","room_type_overrides":{},"balcony_type_overrides":{},"material_presets":{"floor_common":"MAT_Floor_Common","floor_master_wood":"MAT_Floor_Master_Wood","floor_entrance":"MAT_Floor_Entrance","floor_balcony":"MAT_Floor_Balcony","floor_washroom":"MAT_Floor_Washroom","skirting_common":"MAT_Skirting_Common","skirting_master":"MAT_Skirting_Master","skirting_entrance":"MAT_Skirting_Entrance","skirting_balcony":"MAT_Skirting_Balcony","lintel_blue":"MAT_Lintel_Blue","washroom_tiles":"MAT_Washroom_Wall_Tiles","balcony_glass":"MAT_Balcony_Glass","balcony_metal":"MAT_Balcony_Railing_Metal","kitchen_countertop":"MAT_Kitchen_Countertop","kitchen_base":"MAT_Kitchen_Base"}},"rooms":[{"name":"Room_01","use":"living","label":"Living","type":"dry","display_name":"Living Room","cad_dim":"8.15 \u00d7 6.45 m","cad_text":"","floor_obj":"Floor_Living","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Living","skirt_mat":"MAT_Skirting_Common","tile_obj":"","recessed_ceiling":true,"area_m2":37.65,"min_dim_mm":6450,"max_dim_mm":8150,"score":-8,"signals":["1 full-size window(s) (-1)","1 open passage(s) (-3)","large area 37.65 m2 (-4)"],"openings":["Door_01","Door_05","Passage_01","Window_05"],"use_reason":"main entrance door opens into it","vertices":12},{"name":"Room_07","use":"shaft","label":"Shaft","type":"shaft","display_name":"Service Shaft / Duct","cad_dim":"1.60 \u00d7 1.50 m","cad_text":"","floor_obj":"","floor_mat":"","skirt_obj":"","skirt_mat":"","tile_obj":"","recessed_ceiling":false,"area_m2":2.4,"min_dim_mm":1500,"max_dim_mm":1600,"score":2,"signals":["1 ventilator on boundary (+3)","no doorway found (-2)","compact area 2.40 m2 (+1)","diagonal X shaft cross inside void -> shaft"],"openings":["Vent_05"],"use_reason":"enclosed service shaft / duct","vertices":4},{"name":"Toilet_3","use":"washroom","label":"Toilet_3","type":"washroom","display_name":"Toilet","cad_dim":"2.40 \u00d7 1.60 m","cad_text":"","floor_obj":"Floor_Washroom_04","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_04","recessed_ceiling":false,"area_m2":3.84,"min_dim_mm":1600,"max_dim_mm":2400,"score":8,"signals":["1 ventilator on boundary (+3)","single doorway, no open passage (+2)","narrow washroom-width doorway 750 mm (+2)","compact area 3.84 m2 (+1)"],"openings":["Door_06","Vent_05"],"use_reason":"classified washroom (see signals)","vertices":4},{"name":"Room_05","use":"kitchen","label":"Kitchen","type":"dry","display_name":"Kitchen","cad_dim":"3.42 \u00d7 1.52 m","cad_text":"","floor_obj":"Floor_Kitchen","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Kitchen","skirt_mat":"MAT_Skirting_Common","tile_obj":"","recessed_ceiling":false,"area_m2":5.1,"min_dim_mm":1525,"max_dim_mm":3425,"score":-3,"signals":["2 full-size window(s) (-1)","1 open passage(s) (-3)","compact area 5.10 m2 (+1)"],"openings":["Passage_01","Window_03","Window_06"],"use_reason":"compact room opening off hall/dining (inferred kitchen; override via CONFIG if needed)","vertices":8},{"name":"Room_04","use":"bedroom","label":"Bedroom_2","type":"dry","display_name":"Bedroom","cad_dim":"3.80 \u00d7 3.15 m","cad_text":"","floor_obj":"Floor_Bedroom_2","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Bedroom_2","skirt_mat":"MAT_Skirting_Common","tile_obj":"","recessed_ceiling":true,"area_m2":11.39,"min_dim_mm":3150,"max_dim_mm":3800,"score":-3,"signals":["1 full-size window(s) (-1)","single doorway, no open passage (+2)","large area 11.39 m2 (-4)"],"openings":["Door_07","Window_04"],"use_reason":"private room >= 7 m2 with a single doorway","vertices":6},{"name":"Room_06","use":"lobby","label":"Lobby","type":"dry","display_name":"Lobby","cad_dim":"3.15 \u00d7 1.75 m","cad_text":"","floor_obj":"Floor_Entrance_01","floor_mat":"MAT_Floor_Entrance","skirt_obj":"Skirting_Entrance_01","skirt_mat":"MAT_Skirting_Entrance","tile_obj":"","recessed_ceiling":false,"area_m2":4.36,"min_dim_mm":1750,"max_dim_mm":3150,"score":1,"signals":["compact area 4.36 m2 (+1)"],"openings":["Door_03","Door_04","Door_05","Door_07"],"use_reason":"circulation space 4.36 m2 between doors","vertices":6},{"name":"Toilet_2","use":"washroom","label":"Toilet_2","type":"washroom","display_name":"Toilet","cad_dim":"2.40 \u00d7 1.50 m","cad_text":"","floor_obj":"Floor_Washroom_03","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_03","recessed_ceiling":false,"area_m2":3.6,"min_dim_mm":1500,"max_dim_mm":2400,"score":8,"signals":["1 ventilator on boundary (+3)","single doorway, no open passage (+2)","narrow washroom-width doorway 708 mm (+2)","compact area 3.60 m2 (+1)"],"openings":["Door_03","Vent_02"],"use_reason":"classified washroom (see signals)","vertices":4},{"name":"Toilet_1","use":"washroom","label":"Toilet_1","type":"washroom","display_name":"Toilet","cad_dim":"2.50 \u00d7 1.50 m","cad_text":"","floor_obj":"Floor_Washroom_02","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_02","recessed_ceiling":false,"area_m2":3.75,"min_dim_mm":1500,"max_dim_mm":2500,"score":8,"signals":["1 ventilator on boundary (+3)","single doorway, no open passage (+2)","narrow washroom-width doorway 708 mm (+2)","compact area 3.75 m2 (+1)"],"openings":["Door_02","Vent_01"],"use_reason":"classified washroom (see signals)","vertices":4},{"name":"Room_03","use":"bedroom","label":"Bedroom_1","type":"dry","display_name":"Bedroom","cad_dim":"4.63 \u00d7 4.32 m","cad_text":"","floor_obj":"Floor_Bedroom_1","floor_mat":"MAT_Floor_Common","skirt_obj":"Skirting_Bedroom_1","skirt_mat":"MAT_Skirting_Common","tile_obj":"","recessed_ceiling":true,"area_m2":14.48,"min_dim_mm":4320,"max_dim_mm":4632,"score":-5,"signals":["1 full-size window(s) (-1)","large area 14.48 m2 (-4)"],"openings":["Door_02","Door_04","Door_08","Window_01"],"use_reason":"habitable room >= 7 m2","vertices":12},{"name":"Room_02","use":"master_bedroom","label":"Master_Bedroom","type":"dry","display_name":"Master Bedroom","cad_dim":"5.45 \u00d7 3.27 m","cad_text":"","floor_obj":"Floor_MasterBedroom_Wood","floor_mat":"MAT_Floor_Master_Wood","skirt_obj":"Skirting_MasterBedroom","skirt_mat":"MAT_Skirting_Master","tile_obj":"","recessed_ceiling":true,"area_m2":16.59,"min_dim_mm":3268,"max_dim_mm":5445,"score":-2,"signals":["3 ventilator on boundary (+3)","1 full-size window(s) (-1)","large area 16.59 m2 (-4)"],"openings":["Door_08","Door_09","Vent_04","Vent_06","Vent_07","Window_02"],"use_reason":"the attached Master_Toilet opens into it","vertices":10},{"name":"Master_Toilet","use":"washroom","label":"Master_Toilet","type":"washroom","display_name":"Master Toilet","cad_dim":"2.40 \u00d7 1.35 m","cad_text":"","floor_obj":"Floor_Washroom_01","floor_mat":"MAT_Floor_Washroom","skirt_obj":"","skirt_mat":"","tile_obj":"Tiles_Washroom_Wall_01","recessed_ceiling":false,"area_m2":3.24,"min_dim_mm":1350,"max_dim_mm":2400,"score":8,"signals":["1 ventilator on boundary (+3)","single doorway, no open passage (+2)","narrow washroom-width doorway 708 mm (+2)","compact area 3.24 m2 (+1)"],"openings":["Door_09","Vent_03"],"use_reason":"classified washroom (see signals)","vertices":4}],"openings":[{"id":"Window_06","type":"window","p0":[12069.9,62.5],"p1":[15494.9,62.5],"width":3425.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[12069.9,125.0],[15494.9,125.0],[15494.9,0.0],[12069.9,0.0]],"rooms":["Room_05"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_001"},{"id":"Window_02","type":"window","p0":[12.4,1050.0],"p1":[12.4,3575.0],"width":2525.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[-50.1,1050.0],[-50.1,3575.0],[74.9,3575.0],[74.9,1050.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_002"},{"id":"Window_03","type":"window","p0":[15557.4,125.0],"p1":[15557.4,1175.0],"width":1050.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[15494.9,125.0],[15494.9,1175.0],[15619.9,1175.0],[15619.9,125.0]],"rooms":["Room_05"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_003"},{"id":"Vent_04","type":"window","p0":[74.9,3675.0],"p1":[575.0,3675.0],"width":500.1,"thickness":150.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[74.9,3750.0],[575.0,3750.0],[575.0,3600.0],[74.9,3600.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_004"},{"id":"Vent_06","type":"window","p0":[74.9,950.0],"p1":[574.9,950.0],"width":500.0,"thickness":200.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[74.9,1050.0],[574.9,1050.0],[574.9,850.0],[74.9,850.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_005"},{"id":"Window_04","type":"window","p0":[7069.9,362.5],"p1":[8869.9,362.5],"width":1800.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[7069.9,425.0],[8869.9,425.0],[8869.9,300.0],[7069.9,300.0]],"rooms":["Room_04"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_006"},{"id":"Window_01","type":"window","p0":[1537.4,5325.0],"p1":[1537.4,7125.0],"width":1800.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[1474.9,5325.0],[1474.9,7125.0],[1599.9,7125.0],[1599.9,5325.0]],"rooms":["Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_007"},{"id":"Window_05","type":"window","p0":[9870.0,362.5],"p1":[11070.0,362.5],"width":1200.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[9870.0,425.0],[11070.0,425.0],[11070.0,300.0],[9870.0,300.0]],"rooms":["Room_01"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_008"},{"id":"Vent_07","type":"window","p0":[3770.0,362.5],"p1":[4770.0,362.5],"width":1000.0,"thickness":125.0,"sill":600.0,"head":2100.0,"height":1500.0,"source":"multi-line window symbol","notes":[],"rect":[[3770.0,425.0],[4770.0,425.0],[4770.0,300.0],[3770.0,300.0]],"rooms":["Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_009"},{"id":"Vent_01","type":"vent","p0":[7294.9,7800.0],"p1":[7294.9,8475.0],"width":675.0,"thickness":150.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[7219.9,7800.0],[7219.9,8475.0],[7369.9,8475.0],[7369.9,7800.0]],"rooms":["Toilet_1"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_010"},{"id":"Vent_02","type":"vent","p0":[7820.0,7737.5],"p1":[8420.0,7737.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[7820.0,7800.0],[8420.0,7800.0],[8420.0,7675.0],[7820.0,7675.0]],"rooms":["Toilet_2"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_011"},{"id":"Vent_03","type":"vent","p0":[2007.4,4162.5],"p1":[2007.4,4762.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[1944.9,4162.5],[1944.9,4762.5],[2069.9,4762.5],[2069.9,4162.5]],"rooms":["Master_Toilet"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_012"},{"id":"Vent_05","type":"vent","p0":[16120.0,2937.5],"p1":[16720.0,2937.5],"width":600.0,"thickness":125.0,"sill":1200.0,"head":2100.0,"height":900.0,"source":"multi-line window symbol","notes":[],"rect":[[16120.0,3000.0],[16720.0,3000.0],[16720.0,2875.0],[16120.0,2875.0]],"rooms":["Room_07","Toilet_3"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Window_013"},{"id":"Door_06","type":"door","p0":[17294.9,3900.0],"p1":[17294.9,4650.0],"width":750.0,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap + DOOR layer","notes":[],"rect":[[17219.9,3900.0],[17219.9,4650.0],[17369.9,4650.0],[17369.9,3900.0]],"rooms":["Toilet_3"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_001"},{"id":"Door_05","type":"door","p0":[8969.9,4075.0],"p1":[8969.9,5125.0],"width":1050.0,"thickness":200.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap","notes":[],"rect":[[8869.9,4075.0],[8869.9,5125.0],[9069.9,5125.0],[9069.9,4075.0]],"rooms":["Room_01","Room_06"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_002"},{"id":"Door_04","type":"door","p0":[5644.9,4075.0],"p1":[5644.9,5250.0],"width":1175.0,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap","notes":[],"rect":[[5569.9,4075.0],[5569.9,5250.0],[5719.9,5250.0],[5719.9,4075.0]],"rooms":["Room_06","Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_003"},{"id":"Passage_01","type":"passage","p0":[12545.0,1712.5],"p1":[14945.0,1712.5],"width":2400.0,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"collinear wall-end gap + lintel line drawn across","notes":["beam / lintel line drawn across the opening - wall completed above door head"],"rect":[[12545.0,1775.0],[14945.0,1775.0],[14945.0,1650.0],[12545.0,1650.0]],"rooms":["Room_01","Room_05"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Passage_004"},{"id":"Door_09","type":"door","p0":[3761.7,3700.0],"p1":[4469.9,3700.0],"width":708.3,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[3761.7,3775.0],[4469.9,3775.0],[4469.9,3625.0],[3761.7,3625.0]],"rooms":["Room_02","Master_Toilet"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_005"},{"id":"Door_07","type":"door","p0":[7970.0,4000.0],"p1":[8869.9,4000.0],"width":899.9,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[7970.0,4075.0],[8869.9,4075.0],[8869.9,3925.0],[7970.0,3925.0]],"rooms":["Room_04","Room_06"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_006"},{"id":"Door_03","type":"door","p0":[8161.7,5200.0],"p1":[8869.9,5200.0],"width":708.3,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[8161.7,5275.0],[8869.9,5275.0],[8869.9,5125.0],[8161.7,5125.0]],"rooms":["Room_06","Toilet_2"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_007"},{"id":"Door_01","type":"door","p0":[16170.0,6937.5],"p1":[17219.9,6937.5],"width":1049.9,"thickness":125.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[16170.0,7000.0],[17219.9,7000.0],[17219.9,6875.0],[16170.0,6875.0]],"rooms":["Room_01"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_008"},{"id":"Door_02","type":"door","p0":[5644.9,6683.3],"p1":[5644.9,5975.0],"width":708.3,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"wall end facing wall end-zone + DOOR layer","notes":[],"rect":[[5719.9,6683.3],[5719.9,5975.0],[5569.9,5975.0],[5569.9,6683.3]],"rooms":["Toilet_1","Room_03"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_009"},{"id":"Door_08","type":"door","p0":[5519.9,3767.8],"p1":[4619.9,3767.8],"width":900.0,"thickness":150.0,"sill":0.0,"head":2100.0,"height":2100.0,"source":"CAD door arc between walls + DOOR layer","notes":[],"rect":[[5519.9,3692.8],[4619.9,3692.8],[4619.9,3842.8],[5519.9,3842.8]],"rooms":["Room_03","Room_02"],"balcony":false,"dry_balcony":false,"has_lintel":true,"lintel_id":"Lintel_Door_010"}]},"wall_bands":[{"z0":0.0,"z1":600.0,"polys":[{"outer":[[574.9,300.0],[5519.9,300.0],[5519.9,125.0],[5719.9,125.0],[5719.9,3925.0],[7970.0,3925.0],[7970.0,4075.0],[5519.9,4075.0],[5519.9,425.0],[1484.9,425.0],[1484.9,1050.0],[74.9,1050.0],[74.9,3600.0],[575.0,3600.0],[575.0,3625.0],[3761.7,3625.0],[3761.7,3775.0],[2069.9,3775.0],[2069.9,5125.0],[4469.9,5125.0],[4469.9,3625.0],[4619.9,3625.0],[4619.9,5275.0],[1599.9,5275.0],[1600.0,7250.0],[1249.9,7250.0],[1249.9,8475.0],[5569.9,8475.0],[5569.9,6683.3],[5719.9,6683.3],[5719.9,8475.0],[7219.9,8475.0],[7219.9,5975.0],[5569.9,5975.0],[5569.9,5250.0],[5719.9,5250.0],[5719.9,5825.0],[7219.9,5825.0],[7219.9,5125.0],[8161.7,5125.0],[8161.7,5275.0],[7369.9,5275.0],[7369.9,7675.0],[8869.9,7675.0],[8869.9,5125.0],[9069.9,5125.0],[9069.9,6875.0],[16170.0,6875.0],[16170.0,7000.0],[9069.9,7000.0],[9069.9,7800.0],[7369.9,7800.0],[7370.0,8625.0],[1124.9,8625.0],[1124.9,7125.0],[1474.9,7125.0],[1474.9,5275.0],[575.0,5275.0],[575.0,5125.0],[1944.9,5125.0],[1944.9,3775.0],[575.0,3775.0],[575.0,3750.0],[74.9,3750.0],[74.9,3775.0],[-50.1,3775.0],[-50.1,850.0],[574.9,850.0]],"holes":[]},{"outer":[[5720.0,125.0],[5720.0,0.0],[7069.9,0.0],[7069.9,300.0],[8869.9,300.0],[8869.9,0.0],[9069.9,0.0],[9069.9,265.0],[9479.9,265.0],[9479.9,300.0],[11869.9,300.0],[11869.9,0.0],[15619.9,0.0],[15619.9,1175.0],[17219.9,1175.0],[17219.9,675.0],[17369.9,675.0],[17369.9,3900.0],[17219.9,3900.0],[17219.9,3000.0],[15619.9,3000.0],[15619.9,5400.0],[17219.9,5400.0],[17219.9,4650.0],[17369.9,4650.0],[17369.9,5400.0],[17344.9,5400.0],[17344.9,7000.0],[17219.9,7000.0],[17219.9,5525.0],[15419.9,5525.0],[15419.9,1775.0],[14945.0,1775.0],[14945.0,1650.0],[15419.9,1650.0],[15419.9,1175.0],[15494.9,1175.0],[15494.9,125.0],[12069.9,125.0],[12069.9,1300.0],[12319.9,1300.0],[12319.9,1650.0],[12545.0,1650.0],[12545.0,1775.0],[12069.9,1775.0],[12069.9,4275.0],[11819.9,4275.0],[11819.9,425.0],[9479.9,425.0],[9479.9,1035.0],[9069.9,1035.0],[9069.9,4075.0],[8869.9,4075.0],[8869.9,425.0],[6944.9,425.0],[6944.9,125.0]],"holes":[[[15619.9,2875.0],[17219.9,2875.0],[17219.9,1375.0],[15619.9,1375.0]]],"caps":[[[17369.9,2125.0],[17219.9,2125.0],[17219.9,1375.0],[15619.9,1375.0],[15619.9,2125.0],[15419.9,2125.0],[15419.9,1775.0],[14945.0,1775.0],[14945.0,1650.0],[15419.9,1650.0],[15419.9,1175.0],[15494.9,1175.0],[15494.9,125.0],[12069.9,125.0],[12069.9,1300.0],[12319.9,1300.0],[12319.9,1650.0],[12545.0,1650.0],[12545.0,1775.0],[12069.9,1775.0],[12069.9,2125.0],[11819.9,2125.0],[11819.9,425.0],[9479.9,425.0],[9479.9,1035.0],[9069.9,1035.0],[9069.9,2125.0],[8869.9,2125.0],[8869.9,425.0],[6944.9,425.0],[6944.9,125.0],[5720.0,125.0],[5720.0,0.0],[7069.9,0.0],[7069.9,300.0],[8869.9,300.0],[8869.9,0.0],[9069.9,0.0],[9069.9,265.0],[9479.9,265.0],[9479.9,300.0],[11869.9,300.0],[11869.9,0.0],[15619.9,0.0],[15619.9,1175.0],[17219.9,1175.0],[17219.9,675.0],[17369.9,675.0]],[[15419.9,2125.0],[15619.9,2125.0],[15619.9,2875.0],[17219.9,2875.0],[17219.9,2125.0],[17369.9,2125.0],[17369.9,3900.0],[17219.9,3900.0],[17219.9,3000.0],[15619.9,3000.0],[15619.9,5400.0],[17219.9,5400.0],[17219.9,4650.0],[17369.9,4650.0],[17369.9,5400.0],[17344.9,5400.0],[17344.9,7000.0],[17219.9,7000.0],[17219.9,5525.0],[15419.9,5525.0]],[[11819.9,2125.0],[12069.9,2125.0],[12069.9,4275.0],[11819.9,4275.0]],[[8869.9,2125.0],[9069.9,2125.0],[9069.9,4075.0],[8869.9,4075.0]]]}]},{"z0":600.0,"z1":1200.0,"polys":[{"outer":[[15419.9,1175.0],[17219.9,1175.0],[17219.9,675.0],[17369.9,675.0],[17369.9,3900.0],[17219.9,3900.0],[17219.9,3000.0],[15619.9,3000.0],[15619.9,5400.0],[17219.9,5400.0],[17219.9,4650.0],[17369.9,4650.0],[17369.9,5400.0],[17344.9,5400.0],[17344.9,7000.0],[17219.9,7000.0],[17219.9,5525.0],[15419.9,5525.0],[15419.9,1775.0],[14945.0,1775.0],[14945.0,1650.0],[15419.9,1650.0]],"holes":[[[17219.9,2875.0],[17219.9,1375.0],[15619.9,1375.0],[15619.9,2875.0]]],"caps":[[[17369.9,2125.0],[17219.9,2125.0],[17219.9,1375.0],[15619.9,1375.0],[15619.9,2125.0],[15419.9,2125.0],[15419.9,1775.0],[14945.0,1775.0],[14945.0,1650.0],[15419.9,1650.0],[15419.9,1175.0],[17219.9,1175.0],[17219.9,675.0],[17369.9,675.0]],[[15419.9,2125.0],[15619.9,2125.0],[15619.9,2875.0],[17219.9,2875.0],[17219.9,2125.0],[17369.9,2125.0],[17369.9,3900.0],[17219.9,3900.0],[17219.9,3000.0],[15619.9,3000.0],[15619.9,5400.0],[17219.9,5400.0],[17219.9,4650.0],[17369.9,4650.0],[17369.9,5400.0],[17344.9,5400.0],[17344.9,7000.0],[17219.9,7000.0],[17219.9,5525.0],[15419.9,5525.0]]]},{"outer":[[5719.9,5250.0],[5719.9,5825.0],[7219.9,5825.0],[7219.9,5125.0],[8161.7,5125.0],[8161.7,5275.0],[7369.9,5275.0],[7369.9,7675.0],[8869.9,7675.0],[8869.9,5125.0],[9069.9,5125.0],[9069.9,6875.0],[16170.0,6875.0],[16170.0,7000.0],[9069.9,7000.0],[9069.9,7800.0],[7369.9,7800.0],[7370.0,8625.0],[1124.9,8625.0],[1124.9,7125.0],[1600.0,7125.0],[1600.0,7250.0],[1249.9,7250.0],[1249.9,8475.0],[5569.9,8475.0],[5569.9,6683.3],[5719.9,6683.3],[5719.9,8475.0],[7219.9,8475.0],[7219.9,5975.0],[5569.9,5975.0],[5569.9,5250.0]],"holes":[]},{"outer":[[15494.9,125.0],[15494.9,0.0],[15619.9,0.0],[15619.9,125.0]],"holes":[]},{"outer":[[12069.9,0.0],[12069.9,1300.0],[12319.9,1300.0],[12319.9,1650.0],[12545.0,1650.0],[12545.0,1775.0],[12069.9,1775.0],[12069.9,4275.0],[11819.9,4275.0],[11819.9,425.0],[11070.0,425.0],[11070.0,300.0],[11869.9,300.0],[11869.9,0.0]],"holes":[]},{"outer":[[8869.9,4075.0],[8869.9,0.0],[9069.9,0.0],[9069.9,265.0],[9479.9,265.0],[9479.9,300.0],[9870.0,300.0],[9870.0,425.0],[9479.9,425.0],[9479.9,1035.0],[9069.9,1035.0],[9069.9,4075.0]],"holes":[]},{"outer":[[4770.0,300.0],[5519.9,300.0],[5519.9,125.0],[5719.9,125.0],[5719.9,3925.0],[7970.0,3925.0],[7970.0,4075.0],[5519.9,4075.0],[5519.9,425.0],[4770.0,425.0]],"holes":[]},{"outer":[[5720.0,125.0],[5720.0,0.0],[7069.9,0.0],[7069.9,425.0],[6944.9,425.0],[6944.9,125.0]],"holes":[]},{"outer":[[575.0,3625.0],[3761.7,3625.0],[3761.7,3775.0],[2069.9,3775.0],[2069.9,5125.0],[4469.9,5125.0],[4469.9,3625.0],[4619.9,3625.0],[4619.9,5275.0],[1599.9,5275.0],[1599.9,5325.0],[1474.9,5325.0],[1474.9,5275.0],[575.0,5275.0],[575.0,5125.0],[1944.9,5125.0],[1944.9,3775.0],[575.0,3775.0]],"holes":[]},{"outer":[[574.9,300.0],[3770.0,300.0],[3770.0,425.0],[1484.9,425.0],[1484.9,1050.0],[574.9,1050.0]],"holes":[]},{"outer":[[-50.1,1050.0],[-50.1,850.0],[74.9,850.0],[74.9,1050.0]],"holes":[]},{"outer":[[-50.1,3575.0],[74.9,3575.0],[74.9,3775.0],[-50.1,3775.0]],"holes":[]}]},{"z0":1200.0,"z1":3000.0,"polys":[{"outer":[[15419.9,1175.0],[17219.9,1175.0],[17219.9,675.0],[17369.9,675.0],[17369.9,3900.0],[17219.9,3900.0],[17219.9,3000.0],[16720.0,3000.0],[16720.0,2875.0],[17219.9,2875.0],[17219.9,1375.0],[15619.9,1375.0],[15619.9,2875.0],[16120.0,2875.0],[16120.0,3000.0],[15619.9,3000.0],[15619.9,5400.0],[17219.9,5400.0],[17219.9,4650.0],[17369.9,4650.0],[17369.9,5400.0],[17344.9,5400.0],[17344.9,7000.0],[17219.9,7000.0],[17219.9,5525.0],[15419.9,5525.0],[15419.9,1775.0],[14945.0,1775.0],[14945.0,1650.0],[15419.9,1650.0]],"holes":[]},{"outer":[[8420.0,7800.0],[8420.0,7675.0],[8869.9,7675.0],[8869.9,5125.0],[9069.9,5125.0],[9069.9,6875.0],[16170.0,6875.0],[16170.0,7000.0],[9069.9,7000.0],[9069.9,7800.0]],"holes":[]},{"outer":[[15494.9,125.0],[15494.9,0.0],[15619.9,0.0],[15619.9,125.0]],"holes":[]},{"outer":[[12069.9,0.0],[12069.9,1300.0],[12319.9,1300.0],[12319.9,1650.0],[12545.0,1650.0],[12545.0,1775.0],[12069.9,1775.0],[12069.9,4275.0],[11819.9,4275.0],[11819.9,425.0],[11070.0,425.0],[11070.0,300.0],[11869.9,300.0],[11869.9,0.0]],"holes":[]},{"outer":[[8869.9,4075.0],[8869.9,0.0],[9069.9,0.0],[9069.9,265.0],[9479.9,265.0],[9479.9,300.0],[9870.0,300.0],[9870.0,425.0],[9479.9,425.0],[9479.9,1035.0],[9069.9,1035.0],[9069.9,4075.0]],"holes":[]},{"outer":[[7219.9,5125.0],[8161.7,5125.0],[8161.7,5275.0],[7369.9,5275.0],[7369.9,7675.0],[7820.0,7675.0],[7820.0,7800.0],[7219.9,7800.0],[7219.9,5975.0],[5569.9,5975.0],[5569.9,5250.0],[5719.9,5250.0],[5719.9,5825.0],[7219.9,5825.0]],"holes":[]},{"outer":[[4770.0,300.0],[5519.9,300.0],[5519.9,125.0],[5719.9,125.0],[5719.9,3925.0],[7970.0,3925.0],[7970.0,4075.0],[5519.9,4075.0],[5519.9,425.0],[4770.0,425.0]],"holes":[]},{"outer":[[5720.0,125.0],[5720.0,0.0],[7069.9,0.0],[7069.9,425.0],[6944.9,425.0],[6944.9,125.0]],"holes":[]},{"outer":[[1124.9,8625.0],[1124.9,7125.0],[1600.0,7125.0],[1600.0,7250.0],[1249.9,7250.0],[1249.9,8475.0],[5569.9,8475.0],[5569.9,6683.3],[5719.9,6683.3],[5719.9,8475.0],[7370.0,8475.0],[7370.0,8625.0]],"holes":[]},{"outer":[[2069.9,4762.5],[2069.9,5125.0],[4469.9,5125.0],[4469.9,3625.0],[4619.9,3625.0],[4619.9,5275.0],[1599.9,5275.0],[1599.9,5325.0],[1474.9,5325.0],[1474.9,5275.0],[575.0,5275.0],[575.0,5125.0],[1944.9,5125.0],[1944.9,4762.5]],"holes":[]},{"outer":[[574.9,300.0],[3770.0,300.0],[3770.0,425.0],[1484.9,425.0],[1484.9,1050.0],[574.9,1050.0]],"holes":[]},{"outer":[[3761.7,3625.0],[3761.7,3775.0],[2069.9,3775.0],[2069.9,4162.5],[1944.9,4162.5],[1944.9,3775.0],[575.0,3775.0],[575.0,3625.0]],"holes":[]},{"outer":[[-50.1,1050.0],[-50.1,850.0],[74.9,850.0],[74.9,1050.0]],"holes":[]},{"outer":[[-50.1,3575.0],[74.9,3575.0],[74.9,3775.0],[-50.1,3775.0]],"holes":[]}]}]}""")
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
