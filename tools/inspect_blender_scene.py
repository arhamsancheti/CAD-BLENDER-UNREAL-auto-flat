import subprocess

inspect_code = '''
import bpy
import mathutils

print("=== DETAILED BLENDER SCENE INSPECTION ===")
for col in bpy.data.collections:
    print(f"\\n[Collection: {col.name}] (objects: {len(col.objects)})")
    for obj in col.objects[:12]:
        mw = obj.matrix_world
        bbox = [mw @ mathutils.Vector(corner) for corner in obj.bound_box]
        min_x, max_x = min(v.x for v in bbox), max(v.x for v in bbox)
        min_y, max_y = min(v.y for v in bbox), max(v.y for v in bbox)
        min_z, max_z = min(v.z for v in bbox), max(v.z for v in bbox)
        mats = [m.name for m in obj.data.materials if m] if hasattr(obj.data, 'materials') else []
        print(f"  {obj.name:32s} | Z=[{min_z:.2f}, {max_z:.2f}]m | X=[{min_x:.2f}, {max_x:.2f}] | Y=[{min_y:.2f}, {max_y:.2f}] | mats={mats}")

print("\\n=== MATERIALS IN SCENE ===")
for m in bpy.data.materials:
    print(f"  Material: {m.name}")
    if m.node_tree:
        for node in m.node_tree.nodes:
            if node.type == "TEX_BRICK":
                rh = node.inputs["Row Height"].default_value
                bw = node.inputs["Brick Width"].default_value
                ms = node.inputs["Mortar Size"].default_value
                print(f"    -> Brick Node: Row Height={rh}m (2ft), Width={bw}m (3ft), Mortar={ms}m")

active = bpy.context.view_layer.objects.active
print(f"\\nActive Object: {active.name if active else 'None'}")
'''

with open('output/test_detailed_inspect.py', 'w', encoding='utf-8') as f:
    with open('output/test_full_architecture_run.py', 'r', encoding='utf-8') as fr:
        f.write(fr.read() + '\n' + inspect_code)

blender_exe = r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
cmd = [blender_exe, '--background', '--python', 'output/test_detailed_inspect.py']
proc = subprocess.run(cmd, capture_output=True, text=True)
print(proc.stdout[-3500:])
