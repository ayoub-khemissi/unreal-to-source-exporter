import os
import math
import subprocess

import bpy
import bmesh
import mathutils
from bpy.props import IntProperty
from os import path as os_path

from .. import utils
from ..core.helpers import get_prefs


class UTS_OT_CreateCollisions(bpy.types.Operator):
    bl_idname = "uts.create_collisions"
    bl_label = "UTS: Create Collisions"
    bl_options = {'REGISTER'}

    addLayout = 'VIEW3D_MT_object'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    prep_resolution: IntProperty(
        name="prep_resolution",
        description="control the detail level of the pre-processed mesh.",
        default=80,
        min=20,
        max=100
    )

    mcts_iteration: IntProperty(
        name="mcts_iteration",
        description="number of search iterations in MCTS",
        default=300,
        min=60,
        max=2000
    )

    mcts_depth: IntProperty(
        name="mcts_depth",
        description="max search depth in MCTS",
        default=4,
        min=2,
        max=6
    )

    convex_hull: IntProperty(
        name="convex_hull",
        description="max # convex hulls in the result, -1 for no maximum limitation, works only when merge is enabled",
        default=16,
        min=1,
        max=2048,
    )

    def execute(self, context):
        print('[UTS] Call collisions with ', len(bpy.data.objects), ' objects')
        selected = bpy.context.selected_objects
        utils.clearCollections()

        for ob in selected:
            ob.select_set(False)

        prefs = get_prefs()
        directory = prefs.temp_path

        # Pre compute GTA Col
        meshes_to_join = {}
        for obj in selected:
            if obj.type == 'EMPTY':
                haveCol = obj.name.endswith(".col")
                recObj = obj

                while (not haveCol and recObj.parent):
                    recObj = recObj.parent
                    haveCol = obj.name.endswith(".col") and recObj.type == 'EMPTY'

                if haveCol:
                    for child in recObj.children:
                        if child.type == 'MESH':
                            if not recObj in meshes_to_join:
                                meshes_to_join[recObj] = []
                            meshes_to_join[recObj].append(child)
                        child.select_set(False)
            elif not obj.name.endswith(".col"):
                obj.rename(obj.name.replace(".", "_"))

                if "data" in obj:
                    obj.data.rename(obj.name)

        # Create collision
        markForCreation = []
        for ob in selected:
            if ob.name.endswith("_collision"):
                print("This is a collision object already")
                continue

            searchName = ob.name + ".col"

            if searchName in bpy.data.objects:
                for obj, childrens in meshes_to_join.items():
                    if len(childrens) == 0:
                        continue

                    for j in childrens:
                        j.select_set(True)

                    bpy.context.view_layer.objects.active = childrens[0]
                    bpy.ops.object.join()

                    assert obj.name.find(".col") != -1

                    originalName = obj.name
                    bpy.context.view_layer.objects.active.rename(obj.name.replace(".col", "_model_collision"))

                    if "data" in bpy.context.view_layer.objects.active:
                        bpy.context.view_layer.objects.active.data.name.rename(bpy.context.view_layer.objects.active.name)
                    bpy.ops.object.shade_smooth()
                    bpy.ops.object.select_all(action='DESELECT')

                    print('[UTS] Created collision GTA: ', bpy.context.view_layer.objects.active.name)

                    nameOfParent = originalName.replace(".col", "_model")

                    for i in bpy.data.objects:
                        if i.name == nameOfParent:
                            utils.copyOrigin(bpy.context.view_layer.objects.active, i)
                            break

                for obj in bpy.context.scene.objects:
                    if obj.type == 'EMPTY' or obj.name.find('Bound Poly Mesh') != -1:
                        bpy.data.objects.remove(obj)
            else:
                filename = ''.join(c for c in ob.name if c.isalnum() or c in (' ', '.', '_')).rstrip()
                obj_filename = os_path.join(directory, f'{filename}.obj')
                out = os_path.join(directory, f'{filename}_out.obj')

                bpy.ops.object.select_all(action='DESELECT')
                ob.select_set(True)
                bpy.context.view_layer.objects.active = ob
                bpy.ops.wm.obj_export(filepath=obj_filename, export_selected_objects=True)
                markForCreation.append([ob, obj_filename, out, filename])

        print("[UTS] Mark for creation:", len(markForCreation))

        if len(markForCreation) > 0:
            for i in markForCreation:
                (ob, obj_filename, out, fileName) = i
                p = subprocess.Popen([prefs.coacd_path,
                                      "-i", obj_filename,
                                      "-o", out,
                                      "-t", "0.03",
                                      "-pr", str(self.prep_resolution),
                                      "-mi", str(self.mcts_iteration),
                                      "-md", str(self.mcts_depth),
                                      "-c", str(self.convex_hull),
                                      "-mn", "30",
                                      "-d",
                                      "--max-ch-vertex", "128"])

                p.communicate()
                p.wait()

            for (ob, obj_filename, out, filename) in markForCreation:
                if len(bpy.context.selected_objects) == 0:
                    continue

                bpy.ops.wm.obj_import(filepath=out)

                bpy.context.scene.cursor.location = ob.location
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

                bpy.ops.object.join()

                bpy.ops.object.shade_smooth()
                bpy.context.selected_objects[0].rename(filename + '_collision')

                if "data" in bpy.context.selected_objects[0]:
                    bpy.context.selected_objects[0].data.rename(bpy.context.selected_objects[0].name)

                # Delete the obj file and the mdl file
                for i in [f'{filename}.obj', f'{filename}_out.obj', f'{filename}.mtl', f'{filename}_out.mtl']:
                    path = os_path.join(directory, i)
                    if os_path.exists(path):
                        os.remove(path)

                print('[UTS] Created collision CoACD: ', bpy.context.selected_objects[0].name)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.label(text='CoACD Parameters:')
        col.prop(self, 'mcts_depth')
        col.prop(self, 'mcts_iteration')
        col.prop(self, 'prep_resolution')
        col.prop(self, 'convex_hull')
        layout.separator()
        col = layout.column()
        col.label(text='WARNING:', icon='ERROR')
        col.label(text='  Processing can take several minutes per object!')
        col.label(text='  ALL selected objects will be processed sequentially!')
        col.label(text='  See Console Window for progress...')


class UTS_OT_CreateOOB(bpy.types.Operator):
    bl_idname = "uts.create_oob"
    bl_label = "UTS: OOB"
    bl_options = {'REGISTER'}

    addLayout = 'VIEW3D_MT_object'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        def convex_hull_world(obj):
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            ret = bmesh.ops.convex_hull(bm, input=bm.verts)
            hull_faces = [elem for elem in ret['geom'] if isinstance(elem, bmesh.types.BMFace)]
            hull_verts = list({v for v in bm.verts if v.select})
            hull_points = [obj.matrix_world @ v.co for v in hull_verts]

            hull_faces_data = []
            for face in hull_faces:
                local_normal = face.normal.copy()
                world_normal = obj.matrix_world.to_3x3() @ local_normal
                world_normal.normalize()
                face_verts_world = [obj.matrix_world @ v.co for v in face.verts]
                hull_faces_data.append({'normal': world_normal, 'verts': face_verts_world})

            bm.free()
            return hull_points, hull_faces_data

        def convex_hull_2d(points):
            points = sorted(set(points))
            if len(points) <= 1:
                return points
            lower = []
            for p in points:
                while len(lower) >= 2 and (
                        (lower[-1][0] - lower[-2][0]) * (p[1] - lower[-2][1]) - (lower[-1][1] - lower[-2][1]) * (
                        p[0] - lower[-2][0])) <= 0:
                    lower.pop()
                lower.append(p)
            upper = []
            for p in reversed(points):
                while len(upper) >= 2 and (
                        (upper[-1][0] - upper[-2][0]) * (p[1] - upper[-2][1]) - (upper[-1][1] - upper[-2][1]) * (
                        p[0] - upper[-2][0])) <= 0:
                    upper.pop()
                upper.append(p)
            return lower[:-1] + upper[:-1]

        obj = bpy.context.active_object
        if obj is None or obj.type != 'MESH':
            print("Veuillez selectionner un objet de type Mesh.")
            return {'CANCELLED'}

        hull_points, hull_faces_data = convex_hull_world(obj)
        origin = obj.matrix_world.translation.copy()
        hull_points_centered = [p - origin for p in hull_points]
        hull_faces_data_centered = []
        for face_data in hull_faces_data:
            shifted = [v - origin for v in face_data['verts']]
            hull_faces_data_centered.append({'normal': face_data['normal'], 'verts': shifted})

        best_volume = float('inf')
        best_params = None
        candidate_normals = []

        for face_data in hull_faces_data_centered:
            n = face_data['normal'].copy()
            skip = False
            for cn in candidate_normals:
                if abs(n.dot(cn)) > 0.999:
                    skip = True
                    break
            if skip:
                continue
            candidate_normals.append(n.copy())

            verts = face_data['verts']
            if len(verts) < 2:
                continue
            v0 = verts[0]
            v1 = verts[1]
            u = (v1 - v0)
            u = u - n * u.dot(n)
            if u.length < 1e-6:
                continue
            u.normalize()
            v = n.cross(u)
            v.normalize()

            pts_candidate = []
            for p in hull_points_centered:
                a = p.dot(u)
                b = p.dot(v)
                c = p.dot(n)
                pts_candidate.append((a, b, c))
            pts_2d = [(a, b) for (a, b, c) in pts_candidate]
            zs = [c for (a, b, c) in pts_candidate]
            min_z = min(zs)
            max_z = max(zs)

            hull_2d = convex_hull_2d(pts_2d)
            if len(hull_2d) < 2:
                continue

            for i in range(len(hull_2d)):
                j = (i + 1) % len(hull_2d)
                p_i = hull_2d[i]
                p_j = hull_2d[j]
                edge_dx = p_j[0] - p_i[0]
                edge_dy = p_j[1] - p_i[1]
                angle = math.atan2(edge_dy, edge_dx)
                cos_angle = math.cos(angle)
                sin_angle = math.sin(angle)
                rotated = []
                for (a, b) in pts_2d:
                    x_rot = cos_angle * a + sin_angle * b
                    y_rot = -sin_angle * a + cos_angle * b
                    rotated.append((x_rot, y_rot))
                xs = [p[0] for p in rotated]
                ys = [p[1] for p in rotated]
                min_x = min(xs)
                max_x = max(xs)
                min_y = min(ys)
                max_y = max(ys)
                width = max_x - min_x
                height = max_y - min_y
                depth = max_z - min_z
                volume = width * height * depth
                if volume < best_volume:
                    best_volume = volume
                    best_params = {
                        'u': u.copy(),
                        'v': v.copy(),
                        'n': n.copy(),
                        'angle': angle,
                        'min_x': min_x,
                        'max_x': max_x,
                        'min_y': min_y,
                        'max_y': max_y,
                        'min_z': min_z,
                        'max_z': max_z
                    }

        if best_params is None:
            print("Aucune boite trouvee.")
            return {'CANCELLED'}

        u = best_params['u']
        v = best_params['v']
        n = best_params['n']
        angle = best_params['angle']
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        u_rot = u * cos_angle - v * sin_angle
        v_rot = u * sin_angle + v * cos_angle

        min_x = best_params['min_x']
        max_x = best_params['max_x']
        min_y = best_params['min_y']
        max_y = best_params['max_y']
        min_z = best_params['min_z']
        max_z = best_params['max_z']

        center_candidate = mathutils.Vector(((min_x + max_x) / 2,
                                             (min_y + max_y) / 2,
                                             (min_z + max_z) / 2))
        half_extents = mathutils.Vector(((max_x - min_x) / 2,
                                         (max_y - min_y) / 2,
                                         (max_z - min_z) / 2))

        corners_candidate = []
        for dx in (-half_extents.x, half_extents.x):
            for dy in (-half_extents.y, half_extents.y):
                for dz in (-half_extents.z, half_extents.z):
                    corner = mathutils.Vector((center_candidate.x + dx,
                                               center_candidate.y + dy,
                                               center_candidate.z + dz))
                    corners_candidate.append(corner)

        corners_world = [u_rot * corner.x + v_rot * corner.y + n * corner.z for corner in corners_candidate]
        corners_world = [pt + origin for pt in corners_world]

        R_candidate = mathutils.Matrix((u_rot, v_rot, n)).to_quaternion()
        R_obj = obj.matrix_world.to_quaternion()
        delta = R_candidate @ R_obj.inverted()
        corners_corrected = [delta.inverted() @ pt for pt in corners_world]

        mat_inv = obj.matrix_world.inverted()
        corners_local = [mat_inv @ pt for pt in corners_corrected]

        faces = [
            (0, 1, 3, 2),
            (4, 6, 7, 5),
            (0, 2, 6, 4),
            (1, 5, 7, 3),
            (0, 4, 5, 1),
            (2, 3, 7, 6)
        ]

        mesh_box = bpy.data.meshes.new(obj.name + "_collision_mesh")
        mesh_box.from_pydata(corners_local, [], faces)
        mesh_box.update()
        obj_box = bpy.data.objects.new(obj.name + "_collision", mesh_box)
        obj_box.matrix_world = obj.matrix_world.copy()
        bpy.context.collection.objects.link(obj_box)

        bpy.ops.object.select_all(action='DESELECT')
        obj_box.select_set(True)
        bpy.context.view_layer.objects.active = obj_box

        bpy.ops.object.shade_smooth()
        bpy.context.selected_objects[0].rename(obj.name + '_collision')
        bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')
        print("[UTS] OBB generated, volume =", best_volume)

        return {'FINISHED'}
