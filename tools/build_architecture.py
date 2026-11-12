"""Build the architectural Blender model for a CAD plan, end to end.

    python tools/build_architecture.py [path/to/plan.dwg|dxf] [--shots DIR] [--name 3BHK]

1. runs the CAD pipeline (walls, openings, rooms/washrooms, skirting, tiles, slabs)
2. writes  output/<name>_architecture_blender.py   (re-runnable Blender script)
           output/<name>_architecture_data.json     (rooms / openings / tile stats)
3. runs Blender in the background (factory startup), executes the script TWICE to prove
   idempotent re-runs, saves output/<name>_architecture.blend and writes
   output/<name>_validation_report.json from the in-Blender geometric validation
4. renders review screenshots (Workbench) with the ceiling hidden
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BLENDER_CANDIDATES = [
    os.environ.get('BLENDER_EXE', ''),
    r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe',
    r'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe',
    r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe',
    'blender',
]

RUNNER = r'''
import bpy, sys, json, math, os
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
script_path, blend_out, shots_dir, report_out = argv[:4]

# factory startup scene: remove only the default cube (it would sit inside the flat)
cube = bpy.data.objects.get('Cube')
if cube is not None and cube.type == 'MESH' and len(cube.data.vertices) == 8:
    bpy.data.objects.remove(cube, do_unlink=True)

def snapshot():
    return {
        'objects': len(bpy.data.objects), 'meshes': len(bpy.data.meshes),
        'materials': sorted(m.name for m in bpy.data.materials),
        'collections': sorted(c.name for c in bpy.data.collections),
        'node_groups': sorted(g.name for g in bpy.data.node_groups),
        'dup_names': sorted(n for n in [o.name for o in bpy.data.objects] + [m.name for m in bpy.data.materials] +
                            [c.name for c in bpy.data.collections] + [g.name for g in bpy.data.node_groups]
                            if len(n) > 4 and n[-4] == '.' and n[-3:].isdigit()),
    }

code = compile(open(script_path, encoding='utf-8').read(), script_path, 'exec')
exec(code, {'__name__': '__main__'})
first = snapshot()
exec(code, {'__name__': '__main__'})          # re-run in the same file: must not duplicate anything
second = snapshot()
idem = {'first_run': first, 'second_run': second,
        'same_object_count': first['objects'] == second['objects'],
        'same_materials': first['materials'] == second['materials'],
        'same_collections': first['collections'] == second['collections'],
        'no_numbered_duplicates': not second['dup_names']}
idem['passed'] = all(v for k, v in idem.items() if k not in ('first_run', 'second_run'))
print('=====IDEMPOTENCY_JSON_BEGIN=====')
print(json.dumps(idem))
print('=====IDEMPOTENCY_JSON_END=====')

hier = {}
def walk(col, depth=0):
    hier.setdefault('lines', []).append('  ' * depth + f"{col.name}  ({len(col.objects)} objects)")
    for ch in col.children:
        walk(ch, depth + 1)
walk(bpy.context.scene.collection)
print('=====HIERARCHY_BEGIN=====')
print('\n'.join(hier['lines']))
print('=====HIERARCHY_END=====')

bpy.ops.wm.save_as_mainfile(filepath=blend_out, check_existing=False, compress=True)
print('SAVED', blend_out, os.path.getsize(blend_out))

# ── review renders (not saved into the .blend) ──
if shots_dir and shots_dir != '-':
    os.makedirs(shots_dir, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_shadows = True
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    sc.view_settings.view_transform = 'Standard'
    sc.display.shadow_focus = 0.8
    sc.render.film_transparent = False
    sc.world and setattr(sc.world, 'color', (0.9, 0.92, 0.95))
    hide = ('SOURCE_CAD', 'ROOMS', 'DOORS', 'WINDOWS', 'VALIDATION', 'EDITABLE_PARTS')
    for name in hide:
        c = bpy.data.collections.get(name)
        stack = [c] if c else []
        while stack:
            cc = stack.pop()
            for o in cc.objects:
                o.hide_render = True
            stack.extend(cc.children)

    model = bpy.data.objects.get('Building_Walls_Connected')
    ceil = bpy.data.objects.get('Ceiling_Slab')

    cam_data = bpy.data.cameras.new('Review_Cam')
    cam = bpy.data.objects.new('Review_Cam', cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    bb = [model.matrix_world @ Vector(v) for v in model.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), 0)); hi = Vector((max(v.x for v in bb), max(v.y for v in bb), 3))
    mid = (lo + hi) / 2

    def shoot(name, loc, target, lens=24.0, ortho=None, res=(1600, 1000)):
        cam.location = Vector(loc)
        d = Vector(target) - Vector(loc)
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        if ortho:
            cam_data.type = 'ORTHO'; cam_data.ortho_scale = ortho
        else:
            cam_data.type = 'PERSP'; cam_data.lens = lens
        cam_data.clip_start = 0.01; cam_data.clip_end = 200
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = os.path.join(shots_dir, name + '.png')
        bpy.ops.render.render(write_still=True)
        print('SHOT', sc.render.filepath)

    rc_col = bpy.data.collections.get('RECESSED_CEILINGS')
    rc_objs = []
    if rc_col:
        st = [rc_col]
        while st:
            cc = st.pop()
            rc_objs.extend(cc.objects)
            st.extend(cc.children)

    def set_ceil_hide(flag):
        if ceil:
            ceil.hide_render = flag
        for ro in rc_objs:
            ro.hide_render = flag

    shots = json.loads(argv[4]) if len(argv) > 4 else []
    set_ceil_hide(False)
    shoot('arch_overview_with_ceiling', (mid.x - 6.0, lo.y - 9.0, 13.0), (mid.x, mid.y, 0.0), lens=26)
    set_ceil_hide(True)
    shoot('arch_top_down', (mid.x, mid.y, 40.0), (mid.x, mid.y + 0.0001, 0.0),
          ortho=max(hi.x - lo.x, (hi.y - lo.y) * 1.6) * 1.05, res=(1800, 1000))
    shoot('arch_overview', (mid.x - 6.0, lo.y - 9.0, 13.0), (mid.x, mid.y, 0.0), lens=26)
    for s in shots:
        set_ceil_hide(not s.get('show_ceiling', False))
        shoot(s['name'], s['loc'], s['target'], lens=s.get('lens', 24), res=tuple(s.get('res', (1600, 1000))))
    set_ceil_hide(False)
'''


def find_blender():
    for c in BLENDER_CANDIDATES:
        if c and (os.path.isfile(c) or c == 'blender'):
            return c
    raise SystemExit('Blender not found - set BLENDER_EXE')


def between(text, a, b):
    if a not in text or b not in text:
        return None
    return text.split(a, 1)[1].split(b, 1)[0].strip()


def review_shots(arch):
    """Camera positions derived from the detected rooms / openings (metres)."""
    M = 0.001
    shots = []
    ops = {o['id']: o for o in arch['openings']}
    rooms = {r['name']: r for r in arch['rooms']}

    def centroid(ring):
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    def view_of(o, room_name, dist=2.6, z=1.55, side=0.9, lens=20, name=None):
        (x0, y0), (x1, y1) = o['p0'], o['p1']
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        cx, cy = centroid(rooms[room_name]['ring'])
        nx, ny = cx - mx, cy - my
        L = (nx * nx + ny * ny) ** 0.5 or 1.0
        nx, ny = nx / L, ny / L
        tx, ty = (x1 - x0), (y1 - y0)
        T = (tx * tx + ty * ty) ** 0.5 or 1.0
        tx, ty = tx / T, ty / T
        loc = ((mx + nx * dist * 1000 + tx * side * 1000) * M, (my + ny * dist * 1000 + ty * side * 1000) * M, z)
        tgt = (mx * M, my * M, (o['sill'] + o['head']) / 2 * M)
        shots.append({'name': name or f"arch_{o['id'].lower()}", 'loc': loc, 'target': tgt, 'lens': lens})

    # a door, a window and a washroom ventilator, each seen from the room it serves
    for want in ('door', 'window', 'vent'):
        cands = [o for o in arch['openings'] if o['type'] == want and o.get('rooms')]
        if want == 'vent':
            cands = [o for o in cands if any(r in rooms and rooms[r]['type'] == 'washroom' for r in o['rooms'])]
        if not cands:
            continue
        o = max(cands, key=lambda o: o['width'])
        rn = next((r for r in o['rooms'] if r in rooms and (want != 'vent' or rooms[r]['type'] == 'washroom')), None)
        if rn is None:
            continue
        if want == 'vent':
            view_of(o, rn, dist=1.1, z=1.45, side=0.35, lens=14, name=f"arch_tiles_{rn.lower()}")
        else:
            view_of(o, rn, dist=3.0, side=1.2, lens=20)
    # skirting close-up: low view of the jamb of the widest door in a dry room
    dry_doors = [o for o in arch['openings'] if o['type'] in ('door', 'passage')
                 and any(r in rooms and rooms[r]['type'] == 'dry' for r in o.get('rooms', []))]
    if dry_doors:
        o = max(dry_doors, key=lambda o: o['width'])
        rn = next(r for r in o['rooms'] if r in rooms and rooms[r]['type'] == 'dry')
        (x0, y0), (x1, y1) = o['p0'], o['p1']
        cx, cy = centroid(rooms[rn]['ring'])
        nx, ny = cx - x0, cy - y0
        L = (nx * nx + ny * ny) ** 0.5
        loc = ((x0 + nx / L * 900) * M, (y0 + ny / L * 900) * M, 0.42)
        shots.append({'name': 'arch_skirting_closeup', 'loc': loc, 'target': (x0 * M, y0 * M, 0.04), 'lens': 28})
    # every washroom: wide interior view of its tiles
    for r in arch['rooms']:
        if r['type'] != 'washroom':
            continue
        cx, cy = centroid(r['ring'])
        far = max(r['ring'], key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
        loc = ((cx + (cx - far[0]) * 0.55) * M, (cy + (cy - far[1]) * 0.55) * M, 1.6)
        shots.append({'name': f"arch_washroom_{r['name'].lower()}", 'loc': loc, 'target': (far[0] * M, far[1] * M, 1.2),
                      'lens': 12})
    # recessed ceiling interior view (looking up inside the largest recessed-ceiling room)
    rc_rooms = [r for r in arch['rooms'] if r.get('recessed_ceiling')]
    if rc_rooms:
        rm = max(rc_rooms, key=lambda r: r['area_m2'])
        cx, cy = centroid(rm['ring'])
        far = max(rm['ring'], key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
        loc = ((cx + (far[0] - cx) * 0.45) * M, (cy + (far[1] - cy) * 0.45) * M, 1.35)
        shots.append({'name': 'arch_recessed_ceiling', 'loc': loc, 'target': (cx * M, cy * M, 3.08),
                      'lens': 15, 'show_ceiling': True})
    # door + silver lever close-up
    door_cands = [o for o in arch['openings'] if o['type'] == 'door' and o.get('rooms')]
    if door_cands:
        o = max(door_cands, key=lambda o: o['width'])
        rn = next((r for r in o['rooms'] if r in rooms and rooms[r]['type'] == 'dry'), o['rooms'][0])
        (x0, y0), (x1, y1) = o['p0'], o['p1']
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        cx, cy = centroid(rooms[rn]['ring'])
        nx, ny = cx - mx, cy - my
        L = (nx * nx + ny * ny) ** 0.5 or 1.0
        nx, ny = nx / L, ny / L
        tx, ty = (x1 - x0), (y1 - y0)
        T = (tx * tx + ty * ty) ** 0.5 or 1.0
        tx, ty = tx / T, ty / T
        # Latch/lever is near p1 (u = leaf_w - backset)
        lx, ly = x0 + (x1 - x0) * 0.85, y0 + (y1 - y0) * 0.85
        loc = ((lx + nx * 950 - tx * 250) * M, (ly + ny * 950 - ty * 250) * M, 1.12)
        shots.append({'name': 'arch_door_lever_closeup', 'loc': loc, 'target': (lx * M, ly * M, 0.98), 'lens': 28})
    # kitchen platform + blue lintel shot
    k_rooms = [r for r in arch['rooms'] if 'kitchen' in (r.get('use') or '').lower()]
    if k_rooms:
        kr = k_rooms[0]
        cx, cy = centroid(kr['ring'])
        xs = [p[0] for p in kr['ring']]; ys = [p[1] for p in kr['ring']]
        loc = ((min(xs) + 450.0) * M, (max(ys) - 350.0) * M, 2.25)
        tgt = ((max(xs) - 600.0) * M, (min(ys) + 600.0) * M, 0.75)
        shots.append({'name': 'arch_kitchen_platform', 'loc': loc, 'target': tgt, 'lens': 18})
    # master bedroom wood floor + skirting + blue lintel shot
    m_rooms = [r for r in arch['rooms'] if r.get('floor_category') == 'master_wood']
    if m_rooms:
        mr = max(m_rooms, key=lambda r: r['area_m2'])
        cx, cy = centroid(mr['ring'])
        xs = [p[0] for p in mr['ring']]; ys = [p[1] for p in mr['ring']]
        loc = ((cx + 600.0) * M, (cy - 900.0) * M, 1.95)
        tgt = ((min(xs) + 900.0) * M, (max(ys) - 900.0) * M, 0.75)
        shots.append({'name': 'arch_master_bedroom_wood', 'loc': loc, 'target': tgt, 'lens': 18})
    return shots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', nargs='?', default=os.path.join(ROOT, 'uploads', '1791528835981_3_Bhk.dwg'))
    ap.add_argument('--name', default='3BHK')
    ap.add_argument('--out', default=os.path.join(ROOT, 'output'))
    ap.add_argument('--shots', default='-')
    args = ap.parse_args()

    from cad_processor.pipeline import CADtoBlenderPipeline
    res = CADtoBlenderPipeline().process(args.plan)
    if not res['ok']:
        raise SystemExit('pipeline failed: ' + res['error'])
    for s in res['steps']:
        print(f"[{s['name']}] {s['detail']}")
    os.makedirs(args.out, exist_ok=True)
    base = os.path.join(args.out, f'{args.name}_architecture')
    script_path = base + '_blender.py'
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(res['script'])
    arch = res['architecture']
    with open(base + '_data.json', 'w', encoding='utf-8') as f:
        json.dump({'report': arch['report'], 'openings': arch['openings'], 'rooms': arch['rooms'],
                   'warnings': res['warnings'], 'steps': res['steps']}, f, indent=1, default=float)

    blend_out = base + '.blend'
    report_out = os.path.join(args.out, f'{args.name}_validation_report.json')
    runner = os.path.join(args.out, '_blender_runner.py')
    with open(runner, 'w', encoding='utf-8') as f:
        f.write(RUNNER)
    cmd = [find_blender(), '--background', '--factory-startup', '--python', runner, '--',
           script_path, blend_out, args.shots, report_out, json.dumps(review_shots(arch))]
    print('running Blender ...')
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    log = p.stdout + '\n' + p.stderr
    with open(base + '_blender_log.txt', 'w', encoding='utf-8') as f:
        f.write(log)
    val = between(log, '=====VALIDATION_JSON_BEGIN=====', '=====VALIDATION_JSON_END=====')
    idem = between(log, '=====IDEMPOTENCY_JSON_BEGIN=====', '=====IDEMPOTENCY_JSON_END=====')
    hier = between(log, '=====HIERARCHY_BEGIN=====', '=====HIERARCHY_END=====')
    out = {'blender_exit_code': p.returncode, 'blend_saved': os.path.isfile(blend_out),
           'validation': json.loads(val.splitlines()[-1]) if val else None,
           'idempotency': json.loads(idem) if idem else None, 'hierarchy': hier}
    with open(report_out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    print('Blender exit code', p.returncode, '| blend saved:', out['blend_saved'])
    if out['validation']:
        sm = out['validation']['summary']
        print(f"validation: {sm['passed']}/{sm['checks']} passed")
        for c in out['validation'].get('checks', []):
            if not c.get('pass'):
                print('  FAIL', c.get('group'), c.get('check'), c.get('detail'))
    else:
        print('no validation output - see', base + '_blender_log.txt')
        print(log[-3000:])
    if out['idempotency']:
        print('idempotent re-run:', out['idempotency']['passed'], out['idempotency']['second_run']['dup_names'][:10])
    print(hier or '')


if __name__ == '__main__':
    main()
