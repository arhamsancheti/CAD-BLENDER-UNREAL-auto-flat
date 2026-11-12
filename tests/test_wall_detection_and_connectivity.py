"""Automated verification suite for wall detection, connectivity repair, multi-reference comparison,
detection review/validation checks, and headless Blender 3D architectural generation.

Run with:
    python tests/test_wall_detection_and_connectivity.py
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cad_processor.models import Wall
from cad_processor.pipeline import CADtoBlenderPipeline
from cad_processor.wall_graph import repair_topology


def _make_wall(wid: str, x1: float, y1: float, x2: float, y2: float, t: float = 200.0, h: float = 3000.0) -> Wall:
    import math
    L = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / L * (t / 2.0), (x2 - x1) / L * (t / 2.0)
    poly = [
        (x1 + nx, y1 + ny),
        (x2 + nx, y2 + ny),
        (x2 - nx, y2 - ny),
        (x1 - nx, y1 - ny),
    ]
    return Wall(
        id=wid,
        start_point=(x1, y1),
        end_point=(x2, y2),
        length=L,
        thickness=t,
        height=h,
        polygon=poly,
        layer='A-WALL',
    )


def test_synthetic_connectivity_and_opening_preservation() -> dict:
    """Verify Requirement 4 & 10:
    - Small L-corner gaps, T-junction gaps, collinear noise breaks, and cross-junction splits are repaired.
    - Intentional door (900 mm) and window (1500 mm) openings remain open.
    - Ambiguous gaps (220 mm, between conn_tol=100 mm and min_opening=550 mm) are NOT silently closed
      and are flagged as 'uncertain'.
    - Lateral wall face shift is 0.0 mm (room dimensions preserved).
    """
    print("\n=== [Test 1] Synthetic Wall Connectivity & Opening Preservation ===")
    walls = [
        # Bottom wall split by a 50 mm noise gap at x=2000..2050 and a 900 mm doorway at x=3200..4100
        _make_wall('W_Bot_1', 0.0, 0.0, 2000.0, 0.0, 200.0),
        _make_wall('W_Bot_2', 2050.0, 0.0, 3200.0, 0.0, 200.0),
        _make_wall('W_Bot_3', 4100.0, 0.0, 6000.0, 0.0, 200.0),
        # Left wall with a 60 mm L-corner gap at (0, 0) and a 1500 mm window opening at y=1500..3000
        _make_wall('W_Left_1', 0.0, 160.0, 0.0, 1500.0, 200.0),
        _make_wall('W_Left_2', 0.0, 3000.0, 0.0, 4000.0, 200.0),
        # Top wall split by an ambiguous 220 mm gap at x=2500..2720 (must remain open & flagged uncertain)
        _make_wall('W_Top_1', 0.0, 4000.0, 2500.0, 4000.0, 200.0),
        _make_wall('W_Top_2', 2720.0, 4000.0, 6000.0, 4000.0, 200.0),
        # Right wall connected at top/bottom
        _make_wall('W_Right', 6000.0, 0.0, 6000.0, 4000.0, 200.0),
        # Interior vertical partition with a 55 mm T-junction gap to bottom wall (stops at y=155 instead of y=100)
        _make_wall('W_Part', 2800.0, 155.0, 2800.0, 3900.0, 150.0),
    ]
    known_openings = [
        ((3200.0, 0.0), (4100.0, 0.0)),   # 900 mm door
        ((0.0, 1500.0), (0.0, 3000.0)),   # 1500 mm window
    ]
    repaired_walls, report = repair_topology(walls, conn_tol=100.0, min_opening=550.0, known_openings=known_openings)
    u = unary_union([Polygon(w.polygon).buffer(0) for w in repaired_walls])

    # 1. 50 mm collinear noise break at (2000..2050, 0) must be solid wall now
    noise_probe = LineString([(1950.0, 0.0), (2100.0, 0.0)]).buffer(20.0)
    assert u.intersection(noise_probe).area >= 0.95 * noise_probe.area, "50 mm collinear noise gap was not repaired!"

    # 2. 60 mm L-corner gap at (0, 0..160) must be solid corner now
    corner_probe = Polygon([(-80.0, -80.0), (80.0, -80.0), (80.0, 160.0), (-80.0, 160.0)])
    assert u.intersection(corner_probe).area >= 0.95 * corner_probe.area, "60 mm L-corner gap was not closed!"

    # 3. 55 mm T-junction gap at (2800, 100..155) must be solid T-junction now
    t_probe = Polygon([(2740.0, 90.0), (2860.0, 90.0), (2860.0, 160.0), (2740.0, 160.0)])
    assert u.intersection(t_probe).area >= 0.95 * t_probe.area, "55 mm T-junction gap was not closed!"

    # 4. 900 mm doorway at (3200..4100, 0) must remain open
    door_probe = LineString([(3300.0, 0.0), (4000.0, 0.0)]).buffer(30.0)
    assert u.intersection(door_probe).area == 0.0, "900 mm intentional doorway was erroneously closed!"

    # 5. 1500 mm window at (0, 1500..3000) must remain open
    win_probe = LineString([(0.0, 1600.0), (0.0, 2900.0)]).buffer(30.0)
    assert u.intersection(win_probe).area == 0.0, "1500 mm intentional window was erroneously closed!"

    # 6. 220 mm ambiguous gap at (2500..2720, 4000) must remain open AND be flagged in report['uncertain']
    amb_probe = LineString([(2540.0, 4000.0), (2680.0, 4000.0)]).buffer(30.0)
    assert u.intersection(amb_probe).area == 0.0, "220 mm ambiguous gap was silently closed!"
    assert len(report['uncertain']) == 1, f"Expected 1 uncertain gap, got {len(report['uncertain'])}"
    assert abs(report['uncertain'][0]['width_mm'] - 220.0) <= 5.0

    # 7. Room dimensions preserved (0.0 mm lateral shift)
    assert report['max_lateral_shift_mm'] == 0.0, f"Lateral shift {report['max_lateral_shift_mm']} != 0"

    summary = {
        'repairs': report['counts'],
        'uncertain_flagged': report['uncertain'],
        'max_lateral_shift_mm': report['max_lateral_shift_mm'],
        'door_open': True,
        'window_open': True,
    }
    print("  PASS:", json.dumps(summary))
    return summary


def _sample_path(sample_name: str, upload_fallback: str) -> str:
    """Resolve test fixture from curated samples/ directory first, falling back to local uploads/."""
    p_sample = os.path.join(ROOT, 'samples', sample_name)
    if os.path.isfile(p_sample):
        return p_sample
    return os.path.join(ROOT, 'uploads', upload_fallback)


def _find_blender_exe() -> str | None:
    """Locate Blender executable from BLENDER_EXE env, PATH, or Windows Program Files."""
    import glob
    import shutil
    if os.environ.get('CAD_NO_BLENDER') == '1':
        return None
    cands = [os.environ.get('BLENDER_EXE'), shutil.which('blender')]
    cands.extend(sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"), reverse=True))
    return next((c for c in cands if c and os.path.isfile(c)), None)


def test_existing_project_plans_and_multi_reference() -> dict:
    """Verify Requirement 3, 6, 7, 8, 9 across all project floor plans (.dxf, .docx, .pdf, .png, .fbx reference)."""
    print("\n=== [Test 2] End-to-End Pipeline & Multi-Reference Validation on Project Plans ===")
    out_dir = os.path.join(ROOT, 'output')
    os.makedirs(out_dir, exist_ok=True)
    results = {}

    has_blender = _find_blender_exe() is not None
    fbx_3bhk = _sample_path('3BHK_Type1_1266SQ.fbx', '1792227439399_3BHK_Type1_1266SQ.fbx')
    png_3bhk = _sample_path('3BHK_Flat.png', '1792227589833_3BHK_Flat.png')

    cases = [
        (
            '3_Bhk_DXF',
            _sample_path('3_Bhk.dxf', '1792048422385_3_Bhk.dxf'),
            {},
            3,
            0,
        ),
        (
            '2BHK_Windgates_DXF',
            _sample_path('2BHK_Type_01_Windgates.dxf', '1794046096499_2BHK_Type_01_Windgates.dxf'),
            {},
            2,
            2,
        ),
        (
            '3BHK_Spec_DOCX',
            _sample_path('3BHK_Specification.docx', '1793086283186_3BHK_Specification.docx'),
            {},
            3,
            0,
        ),
        (
            '3BHK_Spec_PDF',
            _sample_path('3BHK_Specification.pdf', '1793086268405_3BHK_Specification.pdf'),
            {},
            3,
            0,
        ),
        (
            '3BHK_Flat_PNG_with_Ref',
            png_3bhk,
            {'references': [fbx_3bhk if has_blender else png_3bhk]},
            3,
            0,
        ),
        (
            '2BHK_Flat_PNG',
            _sample_path('2BHK_Flat.png', '2BHK_Flat.png'),
            {},
            2,
            0,
        ),
    ]
    if has_blender:
        cases.insert(
            5,
            (
                '3BHK_Type1_FBX_Direct',
                fbx_3bhk,
                {},
                3,
                0,
            ),
        )
    else:
        print("  SKIP [3BHK_Type1_FBX_Direct]: Blender not installed (skipping 3D FBX slicing)")

    for label, path, opts, expected_washrooms, max_uncertain in cases:
        res = CADtoBlenderPipeline().process(path, options=opts)
        assert res['ok'], f"{label} failed: {res.get('error')}"
        rv = res['review']
        sm = rv['summary']
        assert sm['FAIL'] == 0, f"{label} had FAIL checks: {[c for c in rv['checks'] if c['status'] == 'FAIL']}"
        assert len(rv['uncertain']) <= max_uncertain, f"{label} had unexpected uncertain gaps: {rv['uncertain']}"

        # Save review preview image
        if rv.get('png_b64'):
            with open(os.path.join(out_dir, f'review_{label}.png'), 'wb') as fh:
                fh.write(base64.b64decode(rv['png_b64']))

        # Save Blender script for headless verification
        script_path = os.path.join(out_dir, f'verified_{label}_blender.py')
        with open(script_path, 'w', encoding='utf-8') as fh:
            fh.write(res['script'])

        rooms = res['architecture']['rooms']
        washrooms = [r for r in rooms if r['type'] == 'washroom']
        assert len(washrooms) == expected_washrooms, (
            f"{label}: expected {expected_washrooms} washrooms, got {len(washrooms)} ({[r['name'] for r in washrooms]})"
        )
        if label.startswith('3BHK_Flat_') or label.startswith('3BHK_Type1_'):
            floor_objs = {r.get('floor_obj') for r in rooms if r.get('floor_obj')}
            for req_floor in ('Floor_Balcony_01', 'Floor_Balcony_02', 'Floor_DryBalcony_01',
                              'Floor_MasterBedroom_Wood', 'Floor_Entrance_01',
                              'Floor_Washroom_01', 'Floor_Washroom_02', 'Floor_Washroom_03'):
                assert req_floor in floor_objs, f"{label}: missing expected floor {req_floor} in {sorted(floor_objs)}"
            if 'PNG' in label:
                assert 'Floor_Kitchen' in floor_objs, f"{label}: missing Floor_Kitchen in {sorted(floor_objs)}"
            else:
                assert ('Floor_Kitchen' in floor_objs or 'Floor_Living_Dining' in floor_objs), (
                    f"{label}: missing kitchen/living floor in {sorted(floor_objs)}"
                )
            bal_ops = [o for o in res['architecture']['openings'] if o.get('balcony') and not o.get('dry_balcony')]
            assert len(bal_ops) == 4, f"{label}: expected 4 open balcony railing edges (3 on M_Balcony + 1 on Main Balcony), got {len(bal_ops)}"

        ref_summary = None
        if opts.get('references'):
            refs = res.get('references', {}).get('results', [])
            assert len(refs) == 1 and refs[0]['ok'], f"Reference comparison failed on {label}"
            r0 = refs[0]
            assert r0['walls_confirmed'] >= 30, f"Too few confirmed walls: {r0['walls_confirmed']}"
            if r0.get('png_b64'):
                with open(os.path.join(out_dir, f'reference_{label}.png'), 'wb') as fh:
                    fh.write(base64.b64decode(r0['png_b64']))
            ref_summary = {
                'summary': r0['summary'],
                'walls_confirmed': r0['walls_confirmed'],
                'walls_total': r0['walls_total'],
                'room_matches': r0['room_matches'],
                'conflicts': r0['conflicts'],
            }

        results[label] = {
            'walls': sum(1 for w in res['walls'] if w.kind == 'wall'),
            'fills': sum(1 for w in res['walls'] if w.kind != 'wall'),
            'rooms': len(rooms),
            'washrooms': [f"{r['name']} ({r['area_m2']} m2)" for r in washrooms],
            'openings': len(res['architecture']['openings']),
            'skirting_runs': len(res['skirting']),
            'tiles': len(res['washroom_tiles']),
            'review_summary': sm,
            'repairs_count': len(rv['repairs']),
            'script_path': script_path,
            'reference': ref_summary,
        }
        print(f"  PASS [{label}]: {results[label]['walls']} walls, {results[label]['rooms']} rooms, "
              f"checks={sm}, repairs={results[label]['repairs_count']}")

    return results


def test_headless_blender_execution(script_path: str, require_balcony_railings: bool = True) -> dict:
    """Verify Requirement 5 & 8:
    Execute the generated Blender script in headless Blender 5.1 and inspect the generated 3D objects,
    collections, materials, wall heights, lintels, flooring, skirting, tiles, railings, and kitchen.
    """
    print(f"\n=== [Test 3] Headless Blender 3D Model Verification ({os.path.basename(script_path)}) ===")
    blender_exe = _find_blender_exe()
    if not blender_exe:
        print("  SKIP: Blender executable not found on this machine")
        return {'skipped': True}

    inspector_code = r"""
import bpy, bmesh, json, os, sys

# Run the generated architectural script
script_file = sys.argv[sys.argv.index('--') + 1]
require_railings = os.environ.get('CAD_REQUIRE_RAILINGS', '1') == '1'
with open(script_file, 'r', encoding='utf-8') as fh:
    exec(compile(fh.read(), script_file, 'exec'), {'__name__': '__main__'})

cols = sorted(c.name for c in bpy.data.collections)
objs = list(bpy.data.objects)
mats = sorted(m.name for m in bpy.data.materials)

wall_obj = bpy.data.objects.get('Building_Walls_Connected')
if wall_obj is not None:
    wall_objs = [wall_obj]
else:
    assert 'WALLS' in bpy.data.collections, "Neither Building_Walls_Connected nor WALLS collection found!"
    wall_objs = [o for o in bpy.data.collections['WALLS'].all_objects if o.type == 'MESH']
    assert len(wall_objs) >= 8, f"Expected separate editable wall meshes in WALLS, got {len(wall_objs)}"

# Verify height == 3.0 m and clean, untriangulated manifold mesh geometry across all wall objects
zs = [(o.matrix_world @ v.co).z for o in wall_objs for v in o.data.vertices]
min_z, max_z = min(zs), max(zs)
assert abs(min_z - 0.0) < 1e-3 and abs(max_z - 3.0) < 1e-2, f"Unexpected wall Z bounds: {min_z}..{max_z}"

non_manifold = 0
zero_faces = 0
triangle_faces = 0
total_wall_verts = 0
total_wall_faces = 0
for o in wall_objs:
    total_wall_verts += len(o.data.vertices)
    total_wall_faces += len(o.data.polygons)
    triangle_faces += sum(1 for p in o.data.polygons if len(p.vertices) == 3)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    non_manifold += sum(1 for e in bm.edges if not e.is_manifold)
    zero_faces += sum(1 for f in bm.faces if f.calc_area() <= 1e-8)
    bm.free()

required_cols = [
    '01_Structure', '02_Openings', '03_Flooring',
    '04_Skirting', '05_Washroom_Tiles', '06_Balcony',
    '07_Kitchen', '08_Materials_And_Lighting'
]
for rc in required_cols:
    assert rc in cols, f"Missing required collection {rc}"

assert 'MAT_Lintel_Blue' in mats, "Missing MAT_Lintel_Blue material"
assert 'MAT_Floor_Master_Wood' in mats, "Missing MAT_Floor_Master_Wood material"
assert 'MAT_Floor_Common' in mats, "Missing MAT_Floor_Common material"
assert 'MAT_Floor_Balcony' in mats, "Missing MAT_Floor_Balcony material"
assert 'MAT_Floor_Entrance' in mats, "Missing MAT_Floor_Entrance material"
assert 'MAT_Washroom_Wall_Tiles' in mats, "Missing MAT_Washroom_Wall_Tiles material"
assert 'MAT_Balcony_Glass' in mats, "Missing MAT_Balcony_Glass material"
assert 'Window_Glass_Mat' in mats, "Missing Window_Glass_Mat material"

lintels = (
    [o.name for o in bpy.data.collections['LINTELS'].all_objects if o.type == 'MESH']
    if 'LINTELS' in bpy.data.collections
    else [o.name for o in objs if 'Lintel' in o.name or o.name.startswith('Head_')]
)
floors = [o.name for o in bpy.data.collections['03_Flooring'].all_objects]
skirtings = [o.name for o in bpy.data.collections['04_Skirting'].all_objects]
tiles = [o.name for o in objs if 'Tiles_' in o.name]
railings = [o.name for o in bpy.data.collections['06_Balcony'].all_objects]
balcony_glass = [o.name for o in bpy.data.collections['BALCONY_GLASS'].all_objects]
window_glasses = [o.name for o in objs if '_Glass_' in o.name]
kitchen = [o.name for o in objs if 'Kitchen' in o.name]

assert len(lintels) > 0, "No blue lintel objects generated"
assert len(floors) >= 6, f"Expected separate room floors in 03_Flooring, got {floors}"
if require_railings:
    assert any('Balcony' in f for f in floors), f"Missing balcony floor in {floors}"
    assert any('MasterBedroom_Wood' in f for f in floors), f"Missing MasterBedroom_Wood floor in {floors}"
    assert len(balcony_glass) >= 1 and len(railings) >= 2, f"Expected balcony glass panels and metal railings, got {railings}"
assert len(skirtings) >= 4, f"Expected separate skirting meshes in 04_Skirting, got {skirtings}"
assert len(tiles) >= 2, f"Expected washroom tile meshes, got {tiles}"
assert len(window_glasses) >= 4, f"Expected window/ventilator glass panes, got {window_glasses}"

report = {
    'collections': cols,
    'total_objects': len(objs),
    'separate_wall_meshes': len(wall_objs),
    'wall_z_range_m': [round(min_z, 3), round(max_z, 3)],
    'wall_vertices': total_wall_verts,
    'wall_faces': total_wall_faces,
    'wall_triangle_faces': triangle_faces,
    'wall_non_manifold_edges': non_manifold,
    'wall_zero_area_faces': zero_faces,
    'lintel_count': len(lintels),
    'floor_objects': floors,
    'skirting_count': len(skirtings),
    'washroom_tile_objects': tiles,
    'balcony_glass_objects': balcony_glass,
    'railing_objects': railings,
    'window_glass_count': len(window_glasses),
    'kitchen_objects': kitchen,
}
print("BLENDER_VERIFY_JSON:" + json.dumps(report))
"""
    inspector_path = os.path.join(ROOT, 'output', '_blender_verify_runner.py')
    with open(inspector_path, 'w', encoding='utf-8') as fh:
        fh.write(inspector_code)

    export_dir = os.path.join(ROOT, 'output', '_test_export', os.path.splitext(os.path.basename(script_path))[0])
    env = dict(
        os.environ,
        CAD_EXPORT_DIR=export_dir,
        CAD_EXPORT_NAME='Test_Model',
        CAD_REQUIRE_RAILINGS='1' if require_balcony_railings else '0',
    )
    proc = subprocess.run(
        [blender_exe, '-b', '--factory-startup', '-P', inspector_path, '--', script_path],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Blender failed (code {proc.returncode}):\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    for fn in ('Test_Model_Unreal.fbx', 'Test_Model_3dsMax.fbx', 'Test_Model.blend'):
        fp = os.path.join(export_dir, fn)
        assert os.path.isfile(fp) and os.path.getsize(fp) > 10000, f"Missing Unreal/3ds Max export file {fp}"

    marker = "BLENDER_VERIFY_JSON:"
    for line in proc.stdout.splitlines():
        if marker in line:
            data = json.loads(line.split(marker, 1)[1])
            assert data['wall_non_manifold_edges'] == 0, f"Non-manifold wall edges: {data['wall_non_manifold_edges']}"
            assert data['wall_zero_area_faces'] == 0, f"Zero-area wall faces: {data['wall_zero_area_faces']}"
            assert data['wall_triangle_faces'] == 0, f"Triangulated wall faces found: {data['wall_triangle_faces']}"
            print("  PASS:", json.dumps(data))
            return data
    raise RuntimeError(f"Did not find {marker} in Blender output:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")


import unittest


class TestCADBlenderUnrealSuite(unittest.TestCase):
    """Standard unittest discovery entrypoint for local runs and GitHub Actions CI."""

    def test_01_synthetic_connectivity(self):
        res = test_synthetic_connectivity_and_opening_preservation()
        self.assertTrue(res['door_open'])
        self.assertTrue(res['window_open'])
        self.assertEqual(res['max_lateral_shift_mm'], 0.0)

    def test_02_pipeline_and_blender_verification(self):
        r2 = test_existing_project_plans_and_multi_reference()
        self.assertIn('3_Bhk_DXF', r2)
        self.assertIn('2BHK_Windgates_DXF', r2)
        self.assertIn('3BHK_Spec_DOCX', r2)
        self.assertIn('3BHK_Spec_PDF', r2)
        for key in ('3BHK_Flat_PNG_with_Ref', '3BHK_Type1_FBX_Direct', '3_Bhk_DXF'):
            if key in r2:
                test_headless_blender_execution(r2[key]['script_path'], require_balcony_railings=True)
        test_headless_blender_execution(r2['2BHK_Windgates_DXF']['script_path'], require_balcony_railings=False)


if __name__ == '__main__':
    r1 = test_synthetic_connectivity_and_opening_preservation()
    r2 = test_existing_project_plans_and_multi_reference()
    r3_png = test_headless_blender_execution(r2['3BHK_Flat_PNG_with_Ref']['script_path'], require_balcony_railings=True)
    if '3BHK_Type1_FBX_Direct' in r2:
        r3_fbx = test_headless_blender_execution(r2['3BHK_Type1_FBX_Direct']['script_path'], require_balcony_railings=True)
    r3_dxf = test_headless_blender_execution(r2['3_Bhk_DXF']['script_path'], require_balcony_railings=True)
    r3_wg = test_headless_blender_execution(r2['2BHK_Windgates_DXF']['script_path'], require_balcony_railings=False)
    print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY.")
