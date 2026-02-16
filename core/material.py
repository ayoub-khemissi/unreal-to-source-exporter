import bpy
import bmesh
from mathutils import Vector


def detect_nocull_materials():
    """Detect materials with back-facing faces that need $nocull."""
    nocull_materials = set()

    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.normal_update()
            bm.faces.ensure_lookup_table()

            material_backfaces = {}

            for face in bm.faces:
                normal = face.normal
                face_center = face.calc_center_median()
                view_direction = (Vector((0, 0, 0)) - face_center).normalized()

                if normal.dot(view_direction) < 0:
                    mat = obj.material_slots[face.material_index].material if face.material_index < len(obj.material_slots) else None
                    if mat and mat not in material_backfaces:
                        material_backfaces[mat] = True

            for mat, b in material_backfaces.items():
                if b:
                    nocull_materials.add(mat.name)

            bm.free()

    return nocull_materials


def rename_textures():
    """Sanitize material names: replace dots, spaces, hyphens, colons with underscores."""
    print("[UTS] Renaming textures")
    for i in bpy.data.materials:
        if not i or i is None or not i.node_tree:
            continue

        for j in bpy.data.materials:
            if i.name.find(j.name) != -1:
                i.rename(i.name.replace(".", "_"))

        i.rename(i.name.replace(" ", "_").replace(".", "_").replace("-", "_").replace(":", "_"))
