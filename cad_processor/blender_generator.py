"""STEPS 8-10 - generate a self-contained, re-runnable Blender (4.x / 5.x) script for the whole flat."""
import json
from typing import List, Optional

from .models import Wall

_TEMPLATE = r'''# ======================================================================
#  CAD -> Blender / 3ds Max / Unreal Engine Architectural 3D Model
#  Auto-generated, idempotent, re-runnable Blender Python script
#  Walls: __COUNT__ (exterior __EXT__, interior __INT__) | openings: __NOPEN__ | rooms: __NROOM__
#  Skirting runs: __NSKIRT__ | individual wall tiles: __NTILE__
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

DATA = json.loads(r"""__DATA__""")
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
'''


class BlenderScriptGenerator:
    """STEPS 8-10 - build, clean, name, organise and validate the model inside Blender."""

    @staticmethod
    def _clean_ring_mm(pts, tol_dup: float = 0.05, tol_collinear_mm: float = 0.01, keep_pts=None) -> list:
        import math
        keep = keep_pts or set()
        out = []
        for x, y in pts:
            p = (round(float(x), 2), round(float(y), 2))
            if not out:
                out.append(p)
            else:
                d = math.hypot(p[0] - out[-1][0], p[1] - out[-1][1])
                if d > tol_dup or (p in keep and p != out[-1]):
                    out.append(p)
        if len(out) > 1:
            d0 = math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1])
            if out[0] == out[-1] or (d0 <= tol_dup and out[-1] not in keep):
                out.pop()
        changed = True
        while changed and len(out) >= 4:
            changed = False
            n = len(out)
            for i in range(n):
                b = out[i]
                if b in keep:
                    continue
                a, c = out[(i - 1) % n], out[(i + 1) % n]
                v1x, v1y = b[0] - a[0], b[1] - a[1]
                v2x, v2y = c[0] - b[0], c[1] - b[1]
                vx, vy = c[0] - a[0], c[1] - a[1]
                l1, l2, lac = math.hypot(v1x, v1y), math.hypot(v2x, v2y), math.hypot(vx, vy)
                if l1 <= tol_dup or l2 <= tol_dup or lac <= tol_dup:
                    out.pop(i)
                    changed = True
                    break
                if (v1x * v2x + v1y * v2y) > 0.0 and abs(v1x * vy - v1y * vx) / lac <= tol_collinear_mm:
                    out.pop(i)
                    changed = True
                    break
        return [[p[0], p[1]] for p in out]

    @classmethod
    def _split_holes_ortho(cls, poly, _depth: int = 0) -> list:
        from shapely.geometry import LineString, Polygon as _P
        from shapely.geometry.polygon import orient
        from shapely.ops import split as shp_split
        valid_holes = [h for h in poly.interiors if _P(h).area >= 4.0]
        if len(valid_holes) != len(poly.interiors):
            poly = _P(poly.exterior.coords, valid_holes).buffer(0)
            if poly.geom_type != 'Polygon':
                out = []
                for g in getattr(poly, 'geoms', []):
                    if g.geom_type == 'Polygon' and g.area >= 1.0:
                        out.extend(cls._split_holes_ortho(g, _depth + 1))
                return out
        if not poly.interiors or _depth > 64:
            return [orient(poly, 1.0)]
        h0 = poly.interiors[0]
        hx0, hy0, hx1, hy1 = h0.bounds
        all_ys = [c[1] for c in poly.exterior.coords] + [c[1] for r in poly.interiors for c in r.coords]
        ym = round(0.5 * (hy0 + hy1), 2)
        yc = ym
        for dy in (0.0, 0.17, -0.17, 0.37, -0.37, 0.71, -0.71, 1.13, -1.13, 1.73, -1.73, 2.57, -2.57):
            cand = round(ym + dy, 2)
            if hy0 + 0.05 < cand < hy1 - 0.05 and all(abs(vy - cand) > 0.05 for vy in all_ys):
                yc = cand
                break
        minx, miny, maxx, maxy = poly.bounds
        cut = LineString([(minx - 100.0, yc), (maxx + 100.0, yc)])
        try:
            parts = shp_split(poly, cut)
            sub = [g for g in getattr(parts, 'geoms', [parts]) if g.geom_type == 'Polygon' and g.area >= 1.0]
        except Exception:
            sub = []
        if not sub or (len(sub) == 1 and len(sub[0].interiors) >= len(poly.interiors)):
            return [orient(poly, 1.0)]
        out = []
        for g in sub:
            out.extend(cls._split_holes_ortho(g, _depth + 1))
        return out

    @classmethod
    def _prep_rings_list(cls, ring_dicts: list, tol_collinear_mm: float = 0.05) -> list:
        from collections import Counter
        from shapely.geometry import Polygon as _P
        from shapely.geometry.polygon import orient
        out = []
        for d in (ring_dicts or []):
            outer_in = d.get('outer') or []
            if len(outer_in) < 3:
                continue
            holes_in = [h for h in d.get('holes', []) if len(h) >= 3]
            try:
                p = _P(outer_in, holes_in).buffer(0)
            except Exception:
                c_out = cls._clean_ring_mm(outer_in, tol_collinear_mm=tol_collinear_mm)
                if len(c_out) >= 3:
                    out.append({'outer': c_out, 'holes': []})
                continue
            geoms = [p] if p.geom_type == 'Polygon' else [g for g in getattr(p, 'geoms', []) if g.geom_type == 'Polygon']
            for g in geoms:
                if g.area < 1.0:
                    continue
                vh = [h for h in g.interiors if _P(h).area >= 4.0]
                g2 = _P(g.exterior.coords, vh).buffer(0)
                sub_geoms = [g2] if g2.geom_type == 'Polygon' else [sg for sg in getattr(g2, 'geoms', []) if sg.geom_type == 'Polygon']
                for sg in sub_geoms:
                    if sg.area < 1.0:
                        continue
                    sg = orient(sg, 1.0)
                    if not sg.interiors:
                        c_out = cls._clean_ring_mm(list(sg.exterior.coords)[:-1], tol_collinear_mm=tol_collinear_mm)
                        if len(c_out) >= 3:
                            out.append({'outer': c_out, 'holes': []})
                    else:
                        cap_polys = cls._split_holes_ortho(sg)
                        if all(not cp.interiors for cp in cap_polys):
                            raw_caps = []
                            for cp in cap_polys:
                                rc = [(round(float(x), 2), round(float(y), 2)) for x, y in list(orient(cp, 1.0).exterior.coords)[:-1]]
                                rc = [rc[i] for i in range(len(rc)) if rc[i] != rc[(i - 1) % len(rc)]]
                                if len(rc) >= 3:
                                    raw_caps.append(rc)
                            v_counts = Counter(pt for rc in raw_caps for pt in set(rc))
                            shared = {pt for pt, cnt in v_counts.items() if cnt >= 2}
                            caps_clean = [cls._clean_ring_mm(rc, tol_collinear_mm=tol_collinear_mm, keep_pts=shared) for rc in raw_caps]
                            caps_clean = [cc for cc in caps_clean if len(cc) >= 3]
                            c_out = cls._clean_ring_mm(list(sg.exterior.coords)[:-1], tol_collinear_mm=tol_collinear_mm, keep_pts=shared)
                            c_holes = [cls._clean_ring_mm(list(orient(_P(h), -1.0).exterior.coords)[:-1],
                                                          tol_collinear_mm=tol_collinear_mm, keep_pts=shared) for h in sg.interiors]
                            c_holes = [ch for ch in c_holes if len(ch) >= 3]
                            out.append({'outer': c_out, 'holes': c_holes, 'caps': caps_clean})
                        else:
                            c_out = cls._clean_ring_mm(list(sg.exterior.coords)[:-1], tol_collinear_mm=tol_collinear_mm)
                            c_holes = [cls._clean_ring_mm(list(h.coords)[:-1], tol_collinear_mm=tol_collinear_mm) for h in sg.interiors]
                            out.append({'outer': c_out, 'holes': [ch for ch in c_holes if len(ch) >= 3]})
        return out

    @classmethod
    def _clean_piece_ring(cls, poly_pts) -> list:
        from shapely.geometry import Polygon as _P
        from shapely.geometry.polygon import orient
        try:
            p = _P(poly_pts).buffer(0)
            if p.geom_type == 'Polygon' and not p.interiors and p.area >= 1.0:
                pts = list(orient(p, 1.0).exterior.coords)[:-1]
                res = cls._clean_ring_mm(pts, tol_dup=0.05, tol_collinear_mm=0.01)
                if len(res) >= 3:
                    return res
        except Exception:
            pass
        return cls._clean_ring_mm(poly_pts, tol_dup=0.05, tol_collinear_mm=0.01)

    @classmethod
    def _prep_item_with_ring(cls, item: dict, tol_collinear_mm: float = 0.05) -> dict:
        d = dict(item)
        prepped = cls._prep_rings_list([{'outer': d.get('ring', []), 'holes': d.get('holes', [])}],
                                       tol_collinear_mm=tol_collinear_mm)
        if prepped:
            d['ring'] = prepped[0]['outer']
            d['holes'] = prepped[0]['holes']
            if prepped[0].get('caps'):
                d['caps'] = prepped[0]['caps']
        else:
            d['ring'] = cls._clean_ring_mm(d.get('ring', []), tol_collinear_mm=tol_collinear_mm)
            d['holes'] = [cls._clean_ring_mm(h, tol_collinear_mm=tol_collinear_mm) for h in d.get('holes', [])]
        return d

    @staticmethod
    def generate_script(walls: List[Wall], clear_scene: bool = True, outline=None, arch: Optional[dict] = None,
                        underlay=None, spec: Optional[dict] = None, **_legacy) -> str:
        from .architecture import CONFIG, SPEC
        cls = BlenderScriptGenerator
        spec = dict(spec or SPEC)
        arch = arch or {'rooms': [], 'openings': [], 'room_floors': [], 'skirting': [], 'room_skirting': [],
                        'tiles': [], 'panels': [], 'kitchens': [], 'recessed_ceilings': [], 'floor': [], 'report': {}}
        raw_floor = arch.get('floor') or [{'outer': [list(p) for p in r], 'holes': []} for r in (outline or []) if len(r) >= 3]
        floor = cls._prep_rings_list(raw_floor, tol_collinear_mm=0.05)
        raw_ceiling = arch.get('ceiling') or raw_floor
        ceiling = cls._prep_rings_list(raw_ceiling, tol_collinear_mm=0.05)
        pieces = []
        for w in walls:
            if len(w.polygon) < 3:
                continue
            c_ring = cls._clean_piece_ring(w.polygon)
            if len(c_ring) < 3:
                continue
            pieces.append({
                'id': w.id, 'kind': w.kind, 'opening': w.opening, 'opening_id': getattr(w, 'opening_id', ''),
                'wall_type': w.wall_type, 'thickness': round(w.thickness, 1),
                'base': round(w.base, 2), 'height': round(w.height, 2),
                'ring': c_ring,
            })
        rooms_clean = [cls._prep_item_with_ring(r, tol_collinear_mm=0.05) for r in arch.get('rooms', [])]
        room_floors_clean = [
            dict(rf, rings=cls._prep_rings_list(rf.get('rings', []), tol_collinear_mm=0.05))
            for rf in arch.get('room_floors', [])
        ]
        skirting_clean = [cls._prep_item_with_ring(s, tol_collinear_mm=0.05) for s in arch.get('skirting', [])]
        room_skirting_clean = [
            dict(rs, runs=cls._prep_rings_list(rs.get('runs', []), tol_collinear_mm=0.05))
            for rs in arch.get('room_skirting', [])
        ]
        kitchens_clean = [
            dict(
                k,
                base_rings=cls._prep_rings_list(k.get('base_rings', []), tol_collinear_mm=0.05),
                counter_rings=cls._prep_rings_list(k.get('counter_rings', []), tol_collinear_mm=0.05),
                backsplash_rings=cls._prep_rings_list(k.get('backsplash_rings', []), tol_collinear_mm=0.05),
            )
            for k in arch.get('kitchens', [])
        ]
        recessed_clean = [
            dict(
                rc,
                cavity_rings=cls._prep_rings_list(rc.get('cavity_rings', []), tol_collinear_mm=0.05),
                collar_rings=cls._prep_rings_list(rc.get('collar_rings', []), tol_collinear_mm=0.05),
                soffit_rings=cls._prep_rings_list(rc.get('soffit_rings', []), tol_collinear_mm=0.05),
                lip_rings=cls._prep_rings_list(rc.get('lip_rings', []), tol_collinear_mm=0.05),
                cove_led_rings=cls._prep_rings_list(rc.get('cove_led_rings', []), tol_collinear_mm=0.05),
            )
            for rc in arch.get('recessed_ceilings', [])
        ]
        und = [[round(v, 1) for v in s] for s in (underlay or [])[:20000]]
        wall_non_lintel = [w for w in walls if w.kind != 'lintel']
        wall_bands_clean = [
            dict(b, polys=cls._prep_rings_list(b.get('polys', []), tol_collinear_mm=0.05))
            for b in cls.wall_bands(wall_non_lintel)
        ]
        data = {'spec': spec, 'config': CONFIG, 'pieces': pieces,
                'openings': arch['openings'], 'rooms': rooms_clean,
                'room_floors': room_floors_clean,
                'skirting': skirting_clean, 'room_skirting': room_skirting_clean,
                'tiles': arch['tiles'], 'panels': arch.get('panels', []),
                'kitchens': kitchens_clean,
                'glass_partitions': arch.get('glass_partitions', []),
                'recessed_ceilings': recessed_clean,
                'floor': floor, 'ceiling': ceiling,
                'underlay': und, 'report': arch.get('report', {}),
                'wall_bands': wall_bands_clean}
        real = [w for w in walls if w.kind == 'wall']
        ext = sum(1 for w in real if w.wall_type == 'exterior')
        payload = json.dumps(data, separators=(',', ':'), default=str)
        assert '"""' not in payload
        return (_TEMPLATE.replace('__DATA__', payload)
                .replace('__COUNT__', str(len(real))).replace('__EXT__', str(ext)).replace('__INT__', str(len(real) - ext))
                .replace('__NOPEN__', str(len(arch['openings']))).replace('__NROOM__', str(len(arch['rooms'])))
                .replace('__NSKIRT__', str(len(arch['skirting']))).replace('__NTILE__', str(len(arch['tiles']))))

    @staticmethod
    def floor_plinth(floor: list, room_floors: list) -> list:
        """Footprint area NOT covered by a room finish floor (under walls, sills, shafts edges) -> rings in mm.
        Built from z = -floor_finish to 0 so the structural slab meets every wall base with no slit."""
        from shapely.geometry import Polygon as _P
        from shapely.geometry.polygon import orient
        from shapely.ops import unary_union
        try:
            foot = unary_union([_P(f['outer'], [h for h in f.get('holes', []) if len(h) >= 3]).buffer(0)
                                for f in floor if len(f.get('outer', [])) >= 3])
            fin = unary_union([_P(r['outer'], [h for h in r.get('holes', []) if len(h) >= 3]).buffer(0)
                               for rf in room_floors for r in rf.get('rings', []) if len(r.get('outer', [])) >= 3])
            rest = foot.difference(fin) if not fin.is_empty else foot
            rest = rest.buffer(0.2, join_style=2).buffer(-0.2, join_style=2)
        except Exception:
            return []
        geoms = [rest] if rest.geom_type == 'Polygon' else [g for g in getattr(rest, 'geoms', []) if g.geom_type == 'Polygon']
        out = []
        for g in geoms:
            if g.area < 100.0:
                continue
            g = orient(g.simplify(0.2, preserve_topology=True), 1.0)
            out.append({'outer': [[round(x, 2), round(y, 2)] for x, y in list(g.exterior.coords)[:-1]],
                        'holes': [[[round(x, 2), round(y, 2)] for x, y in list(h.coords)[:-1]] for h in g.interiors]})
        return out

    @staticmethod
    def wall_bands(walls: List[Wall]) -> list:
        """Merged wall footprint for every height interval between piece bases/tops (mm)."""
        from shapely.geometry import Polygon as _P
        from shapely.geometry.polygon import orient
        from shapely.ops import unary_union
        solid = [w for w in walls if len(w.polygon) >= 3]
        zs = sorted({round(w.base, 2) for w in solid} | {round(w.base + w.height, 2) for w in solid})
        bands = []
        for z0, z1 in zip(zs, zs[1:]):
            polys = [_P(w.polygon).buffer(0) for w in solid
                     if w.base <= z0 + 1e-6 and w.base + w.height >= z1 - 1e-6]
            if not polys:
                continue
            u = unary_union(polys)
            u = u.buffer(0.5, join_style=2).buffer(-0.5, join_style=2)      # heal sub-millimeter (<1.0 mm) gaps
            geoms = [u] if u.geom_type == 'Polygon' else [g for g in getattr(u, 'geoms', []) if g.geom_type == 'Polygon']
            items = []
            for g in geoms:
                if g.area < 1.0:
                    continue
                g = orient(g.simplify(0.2, preserve_topology=True), 1.0)
                items.append({'outer': [[round(x, 2), round(y, 2)] for x, y in list(g.exterior.coords)[:-1]],
                              'holes': [[[round(x, 2), round(y, 2)] for x, y in list(h.coords)[:-1]] for h in g.interiors]})
            if bands and bands[-1]['polys'] == items and abs(bands[-1]['z1'] - z0) < 1e-6:
                bands[-1]['z1'] = z1                                             # same footprint -> extend band
            else:
                bands.append({'z0': z0, 'z1': z1, 'polys': items})
        return bands

    @staticmethod
    def save_script(script: str, filepath: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(script)
