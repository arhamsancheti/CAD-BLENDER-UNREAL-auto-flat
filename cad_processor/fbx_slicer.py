"""
Headless Blender script to import an FBX, find the building mesh,
slice full-height structural walls at floor plan cut height,
extract partial-height sill/lintel/railing openings (windows, ventilators, doors, balcony railings)
and floor room labels, and write the 2D cross-section to DXF.
"""
import sys
import os
import math
import bpy
import bmesh
from mathutils import Vector


def _patch_blender_fbx_bug():
    """Workaround Blender 5.1 upstream bug where lamp.cycles.cast_shadow does not exist."""
    try:
        from io_scene_fbx import import_fbx
        orig_read_light = import_fbx.blen_read_light

        def safe_read_light(fbx_tmpl, fbx_obj, settings):
            try:
                return orig_read_light(fbx_tmpl, fbx_obj, settings)
            except AttributeError as e:
                if 'cast_shadow' in str(e):
                    return None
                raise

        import_fbx.blen_read_light = safe_read_light
    except Exception as e:
        print("Note on patch:", e)


def _extract_mesh_islands(obj):
    """Return list of (verts_coords, (x0, y0, x1, y1, z0, z1)) for each connected component in world space."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    visited = set()
    islands = []
    for v in bm.verts:
        if v.index in visited:
            continue
        comp = []
        q = [v]
        visited.add(v.index)
        while q:
            curr = q.pop()
            comp.append(curr.co.copy())
            for e in curr.link_edges:
                nv = e.other_vert(curr)
                if nv.index not in visited:
                    visited.add(nv.index)
                    q.append(nv)
        if not comp:
            continue
        xs = [p.x for p in comp]
        ys = [p.y for p in comp]
        zs = [p.z for p in comp]
        islands.append((comp, (min(xs), min(ys), max(xs), max(ys), min(zs), max(zs))))
    bm.free()
    return islands


def _extract_floor_info(obj):
    """Extract 2D bounding boxes of horizontal faces and representative interior point for a floor mesh."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bm.normal_update()
    face_boxes = []
    best_face = None
    best_area = -1.0
    for f in bm.faces:
        if abs(f.normal.z) >= 0.5 and len(f.verts) >= 3:
            xs = [v.co.x for v in f.verts]
            ys = [v.co.y for v in f.verts]
            area = f.calc_area()
            face_boxes.append((min(xs), min(ys), max(xs), max(ys)))
            if area > best_area:
                best_area = area
                c = f.calc_center_median()
                best_face = (c.x, c.y)
    if not face_boxes and bm.verts:
        xs = [v.co.x for v in bm.verts]
        ys = [v.co.y for v in bm.verts]
        face_boxes.append((min(xs), min(ys), max(xs), max(ys)))
        best_face = (0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys)))
    bm.free()
    return face_boxes, best_face


def _boxes_touch(box_a, face_boxes, tol=0.22):
    ax0, ay0, ax1, ay1 = box_a
    for bx0, by0, bx1, by1 in face_boxes:
        if (ax0 - tol <= bx1 and ax1 + tol >= bx0) and (ay0 - tol <= by1 and ay1 + tol >= by0):
            return True
    return False


def _write_minimal_dxf(wall_segs, layered_segs, texts, out_path):
    """Write standard R2004 DXF ASCII format with WALL, opening layers, and room TEXT entities."""
    all_pts = [s[0] for s in wall_segs] + [s[1] for s in wall_segs]
    for _lyr, s0, s1 in layered_segs:
        all_pts.extend([s0, s1])
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    dx = max(xs) - min(xs) if xs else 0
    dy = max(ys) - min(ys) if ys else 0
    max_span = max(dx, dy)
    if max_span <= 1e-6:
        scale = 1.0
    elif max_span < 0.5:
        scale = 12000.0 / max_span
    elif max_span < 250.0:
        scale = 1000.0
    else:
        scale = 1.0

    min_len_world = 5.0 / scale
    clean_walls = []
    for (x1, y1), (x2, y2) in wall_segs:
        if math.hypot(x2 - x1, y2 - y1) >= min_len_world:
            clean_walls.append(((x1, y1), (x2, y2)))

    if len(clean_walls) < 4:
        raise RuntimeError(
            f"FBX cross-section produced only {len(clean_walls)} line(s) (flat 2D image plane, not a 3D building mesh)."
        )

    lines = [
        "0", "SECTION",
        "2", "HEADER",
        "9", "$INSUNITS",
        "70", "4",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
    ]
    for (x1, y1), (x2, y2) in clean_walls:
        lines.extend([
            "0", "LINE",
            "8", "WALL",
            "10", f"{round(x1 * scale):.1f}",
            "20", f"{round(y1 * scale):.1f}",
            "30", "0.0",
            "11", f"{round(x2 * scale):.1f}",
            "21", f"{round(y2 * scale):.1f}",
            "31", "0.0",
        ])
    for lyr, (x1, y1), (x2, y2) in layered_segs:
        if math.hypot(x2 - x1, y2 - y1) * scale < 150.0:
            continue
        lines.extend([
            "0", "LINE",
            "8", lyr,
            "10", f"{round(x1 * scale):.1f}",
            "20", f"{round(y1 * scale):.1f}",
            "30", "0.0",
            "11", f"{round(x2 * scale):.1f}",
            "21", f"{round(y2 * scale):.1f}",
            "31", "0.0",
        ])
    for txt, (tx, ty) in texts:
        lines.extend([
            "0", "TEXT",
            "8", "A-TEXT",
            "10", f"{round(tx * scale):.1f}",
            "20", f"{round(ty * scale):.1f}",
            "30", "0.0",
            "40", "150.0",
            "1", txt,
        ])
    lines.extend([
        "0", "ENDSEC",
        "0", "EOF",
    ])
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(
        f"Saved {len(clean_walls)} wall segments, {len(layered_segs)} opening segments, "
        f"and {len(texts)} room labels to DXF: {out_path} (scale x{scale})"
    )


def process_fbx(fbx_path, out_dxf_path, cut_z_ratio=0.35):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if hasattr(bpy.ops.wm, 'fbx_import'):
        bpy.ops.wm.fbx_import(filepath=fbx_path)
    else:
        try:
            import addon_utils
            addon_utils.enable('io_scene_fbx', default_set=True)
        except Exception:
            pass
        _patch_blender_fbx_bug()
        bpy.ops.import_scene.fbx(
            filepath=fbx_path,
            use_image_search=False,
            use_anim=False,
            use_custom_props=False,
            use_subsurf=False,
        )

    mesh_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not mesh_objs:
        raise RuntimeError("No 3D mesh objects found in the FBX file.")

    min_z = float('inf')
    max_z = float('-inf')
    for obj in mesh_objs:
        for corner in obj.bound_box:
            world_pt = obj.matrix_world @ Vector(corner)
            if world_pt.z < min_z:
                min_z = world_pt.z
            if world_pt.z > max_z:
                max_z = world_pt.z

    total_height = max_z - min_z
    cut_z = min_z if total_height <= 0.001 else (min_z + total_height * max(cut_z_ratio, 0.50))
    print(f"FBX height range: {min_z:.3f} to {max_z:.3f} (cut plane Z = {cut_z:.3f})")

    NON_WALL_KEYWORDS = (
        'chair', 'table', 'bed', 'sofa', 'plant', 'tv', 'laptop', 'lamp', 'decor',
        'cushion', 'pillow', 'curtain', 'cloth', 'carpet', 'blanket', 'commode',
        'sink', 'faucet', 'vase', 'book', 'shoe', 'clothes', 'accessory', 'mug',
        'plate', 'handle', 'mirror', 'picture', 'frame', 'light', 'chandelier',
        'pot', 'shelf_item', 'props', 'tile', 'skarting', 'skirting', 'floor',
    )

    # 1. Identify floor meshes for room labels and balcony/indoor adjacency
    floor_infos = []  # (category, label_str, face_boxes, rep_pt)
    obj_names_lower = {o.name.lower() for o in mesh_objs}
    for obj in mesh_objs:
        nl = obj.name.lower()
        zs = [(obj.matrix_world @ Vector(c)).z for c in obj.bound_box]
        dz = max(zs) - min(zs)
        is_floor = ('floor' in nl) or (nl == 'line015' and 'line019' in obj_names_lower and dz <= 0.25 * total_height)
        if not is_floor:
            continue
        fboxes, rep_pt = _extract_floor_info(obj)
        if not fboxes or rep_pt is None:
            continue
        if 'dry' in nl or nl == 'line015':
            cat, lbl = 'dry_balcony', 'DRY BALCONY'
        elif 'balcony' in nl:
            cat, lbl = 'balcony', 'BALCONY'
        elif 'm_bedroom' in nl or 'master' in nl or 'wooden' in nl:
            cat, lbl = 'master_bedroom', 'MASTER BEDROOM'
        elif 'bedroom' in nl:
            cat, lbl = 'bedroom', 'BEDROOM'
        elif any(w in nl for w in ('washrrom', 'washroom', 'toilet', 'bath')):
            cat, lbl = 'washroom', 'TOILET'
        elif any(w in nl for w in ('living', 'dining', 'hall')):
            cat, lbl = 'living_dining', 'LIVING DINING'
        elif any(w in nl for w in ('passage', 'foyer', 'entrance')):
            cat, lbl = 'foyer', 'FOYER'
        else:
            cat, lbl = 'indoor', ''
        floor_infos.append((cat, lbl, fboxes, rep_pt))

    balcony_fboxes = [fb for cat, _l, fbs, _p in floor_infos if cat == 'balcony' for fb in fbs]
    indoor_fboxes = [fb for cat, _l, fbs, _p in floor_infos if cat not in ('balcony', 'dry_balcony') for fb in fbs]
    texts = [(lbl, pt) for _cat, lbl, _fbs, pt in floor_infos if lbl and pt is not None]

    # 2. Separate full-height wall objects from partial-height opening/beam objects (e.g. Bims)
    wall_objs = []
    partial_islands = []  # (x0, y0, x1, y1, z0, z1)
    fallback_candidates = []

    for obj in mesh_objs:
        nl = obj.name.lower()
        if nl in ('line015', 'line019') or any(k in nl for k in NON_WALL_KEYWORDS):
            continue
        zs = [(obj.matrix_world @ Vector(c)).z for c in obj.bound_box]
        xs = [(obj.matrix_world @ Vector(c)).x for c in obj.bound_box]
        ys = [(obj.matrix_world @ Vector(c)).y for c in obj.bound_box]
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        dz = max(zs) - min(zs)
        if min(zs) <= cut_z <= max(zs):
            fallback_candidates.append(obj)
        if (dz >= 0.8 and max(dx, dy) >= 0.3) or max(dx, dy) >= 1.0:
            islands = _extract_mesh_islands(obj)
            full_h = 0
            part_h = 0
            for _verts, (ix0, iy0, ix1, iy1, iz0, iz1) in islands:
                if iz0 <= min_z + 0.30 * total_height and iz1 >= max_z - 0.30 * total_height:
                    full_h += 1
                else:
                    part_h += 1
                    partial_islands.append((ix0, iy0, ix1, iy1, iz0, iz1))
            if full_h > 0 and full_h >= part_h:
                wall_objs.append(obj)

    if not wall_objs:
        wall_objs = fallback_candidates

    print(
        f"Slicing {len(wall_objs)} structural wall mesh(es); "
        f"analyzing {len(partial_islands)} partial-height opening/beam island(s)."
    )

    wall_segs = []
    plane_co = Vector((0.0, 0.0, cut_z))
    plane_no = Vector((0.0, 0.0, 1.0))

    for obj in wall_objs:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        res = bmesh.ops.bisect_plane(
            bm,
            geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
            plane_co=plane_co,
            plane_no=plane_no,
            clear_inner=False,
            clear_outer=False,
        )
        cut_edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        for e in cut_edges:
            v1, v2 = e.verts[0].co, e.verts[1].co
            wall_segs.append(((v1.x, v1.y), (v2.x, v2.y)))
        bm.free()

    # 3. Classify partial-height islands grouped by 2D XY bounding box into A-RAILING, A-WIN, A-WIN_VENT, A-DOOR
    by_xy = {}
    for ix0, iy0, ix1, iy1, iz0, iz1 in partial_islands:
        key = (round(ix0, 2), round(iy0, 2), round(ix1, 2), round(iy1, 2))
        by_xy.setdefault(key, []).append((iz0, iz1))

    layered_segs = []
    for (x0, y0, x1, y1), z_ranges in sorted(by_xy.items()):
        dx = x1 - x0
        dy = y1 - y0
        L = max(dx, dy)
        T = min(dx, dy)
        if L < 0.25 or T > 0.45 or L < T * 1.2:
            continue
        low_sills = [(z0, z1) for z0, z1 in z_ranges if z0 <= min_z + 0.18 * total_height and z1 < max_z - 0.20 * total_height]
        high_lintels = [(z0, z1) for z0, z1 in z_ranges if z0 >= min_z + 0.55 * total_height]
        touches_bal = _boxes_touch((x0, y0, x1, y1), balcony_fboxes, tol=0.22)
        touches_ind = _boxes_touch((x0, y0, x1, y1), indoor_fboxes, tol=0.22)

        layer = None
        if low_sills:
            sill_h = max(z1 - min_z for _z0, z1 in low_sills)
            if sill_h >= 0.42 * total_height:
                layer = 'A-WIN_VENT'
            elif touches_bal and not touches_ind:
                layer = 'A-RAILING'
            else:
                layer = 'A-WIN'
        elif high_lintels:
            if touches_bal or L > 2.2:
                layer = 'A-WIN'
            else:
                layer = 'A-DOOR'

        if not layer:
            continue

        if dx >= dy:
            ym = 0.5 * (y0 + y1)
            layered_segs.append((layer, (x0, ym), (x1, ym)))
        else:
            xm = 0.5 * (x0 + x1)
            layered_segs.append((layer, (xm, y0), (xm, y1)))

    if not wall_segs:
        raise RuntimeError("No cross-section edges intersected the cut plane.")

    _write_minimal_dxf(wall_segs, layered_segs, texts, out_dxf_path)


if __name__ == '__main__':
    args = sys.argv
    if '--' in args:
        idx = args.index('--')
        fbx_in = args[idx + 1]
        dxf_out = args[idx + 2]
        ratio = float(args[idx + 3]) if len(args) > idx + 3 else 0.35
        process_fbx(fbx_in, dxf_out, ratio)
