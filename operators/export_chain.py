import concurrent.futures
import math
import os
import re
import subprocess

import bpy
from bpy.props import BoolProperty, EnumProperty
from vmflib import vmf

from .. import utils
from ..core.helpers import get_prefs
from ..core.model import run_process
from ..core.vmf import create_prop_entity
import io_scene_valvesource.utils


class UTS_OT_ExportChain(bpy.types.Operator):
    bl_idname = "uts.export_chain"
    bl_label = "UTS: Export Chain"
    bl_options = {'REGISTER'}

    addLayout = 'VIEW3D_MT_object'

    export_mode: EnumProperty(
        name="Mode d'export",
        items=[
            ('ALL', "Tous les objets", "Exporter tous les meshes de la scene"),
            ('SELECTED', "Selection", "Exporter uniquement les meshes selectionnes"),
        ],
        default='ALL',
    )

    prepare_forexport: BoolProperty(
        name="prepare_forexport",
        description="Preparer pour l'exportation",
    )

    output_vmf: BoolProperty(
        name="output_vmf",
        description="Sortie VMF",
    )

    export_models: BoolProperty(
        name="export_models",
        description="Exportation des modeles",
    )

    export_materials: BoolProperty(
        name="export_materials",
        description="Exportation des materiaux",
    )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.label(text='Mode:')
        col.prop(self, "export_mode", expand=True)
        layout.separator()
        col = layout.column()
        col.label(text='Parameters:')
        col.prop(self, "prepare_forexport")
        col.prop(self, "output_vmf")
        col.prop(self, "export_materials")
        col.prop(self, "export_models")
        layout.separator()
        col = layout.column()

    def _should_include(self, obj, user_selected_names):
        if user_selected_names is None:
            return True
        return obj.name.split(".")[0] in user_selected_names

    def execute(self, context):
        prefs = get_prefs()
        original_scene_name = bpy.context.scene.name

        os.makedirs(prefs.temp_path, exist_ok=True)
        os.makedirs(prefs.temp_path_models, exist_ok=True)

        utils.clearCollections()

        if self.export_mode == 'SELECTED':
            user_selected_names = set()
            for obj in bpy.context.selected_objects:
                base_name = obj.name.split(".")[0]
                user_selected_names.add(base_name)
                user_selected_names.add(base_name + "_collision")
            if not user_selected_names:
                self.report({'WARNING'}, "Aucun objet selectionne.")
                return {'CANCELLED'}
        else:
            user_selected_names = None

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Clear objects not in viewlayer (only in ALL mode to avoid destroying selected objects)
        if user_selected_names is None:
            objects_to_delete = [obj for obj in bpy.context.scene.objects if obj.name not in bpy.context.view_layer.objects]
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects_to_delete:
                obj.select_set(True)

            bpy.ops.object.delete()

        if self.prepare_forexport:
            utils.clearMaterialsNames()
            bpy.context.view_layer.update()

            bpy.ops.object.select_all(action='DESELECT')
            listObjects = []

            for obj in bpy.data.objects:
                if not self._should_include(obj, user_selected_names):
                    continue
                if obj.type == 'MESH' and obj.name.find("Replaced") == -1 or (obj.name.find("col") != -1 and obj.name.find("collision") == -1)\
                        or not obj.name in bpy.context.view_layer.objects or obj.hide_render or obj.hide_get():
                    listObjects.append(obj)

            count = 0
            for obj in listObjects:
                count += 1
                print("Deleting object: " + str(count) + "/" + str(len(listObjects)))

            bpy.ops.outliner.orphans_purge()
            for material in bpy.data.materials:
                if not material.users:
                    bpy.data.materials.remove(material)

            print("Materials cleared")

            bpy.ops.object.make_local(type='ALL')
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
            print("Origin geometry centered")

            copyObjects = [obj for obj in bpy.data.objects if self._should_include(obj, user_selected_names)]
            for obj in copyObjects:
                if obj.type != 'MESH':
                    continue
                if obj.name.endswith("_collision") and not self.output_vmf:
                    continue

                name_common = obj.name.split(".")[0].replace("_Replaced", "")
                name_common = re.sub(r'[^\w\-]', '_', name_common)

                obj.rename(name_common)

        # Store world positions before any deduplication/transform
        world_origins = {}
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                world_origins[obj.name.split(".")[0]] = obj.location.copy()

        modelsData = {}
        m = vmf.ValveMap()
        copyObjects = [obj for obj in bpy.data.objects if self._should_include(obj, user_selected_names)]

        for obj in copyObjects:
            name_common = obj.name.split(".")[0]

            if self.output_vmf:
                create_prop_entity(obj, name_common)

            if name_common not in modelsData:
                modelsData[name_common] = obj
                obj.rename(name_common)
            elif user_selected_names is None:
                bpy.data.objects.remove(obj, do_unlink=True)

        print("Pre-process done")
        if self.output_vmf:
            vmf_output = os.path.join(prefs.temp_path, "output_uts.vmf")
            m.write_vmf(vmf_output)

        if self.export_materials:
            for material in bpy.data.materials:
                if not material.users:
                    bpy.data.materials.remove(material)

            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.uts.ue_texture_export()

        if self.export_models:
            print("Start: Export Models")
            copyObjects = [obj for obj in bpy.data.objects if self._should_include(obj, user_selected_names)]
            selected = []
            bpy.ops.object.select_all(action='DESELECT')

            for ob in copyObjects:
                if ob.name + "_collision" in copyObjects:
                    ob2 = copyObjects[ob.name + "_collision"]

                    if ob.rotation_euler != ob2.rotation_euler:
                        print("not same")

            clearedAngles = {}

            for ob in copyObjects:
                if ob.name.find("_collision") == -1 and ob.name.find("convex_") == -1:
                    clearedAngles[ob.name] = ob.rotation_euler.copy()
                else:
                    ob.select_set(True)

            bpy.ops.object.select_all(action='DESELECT')

            print("Start Renaming")
            c = 0

            for ob in copyObjects:
                if ob.name not in bpy.context.view_layer.objects:
                    continue
                if not (ob.hide_render or ob.hide_get()) and ob.name.find("_collision") == -1 and ob.name.find(
                        "convex_") == -1:
                    ob.select_set(True)
                    bpy.context.view_layer.objects.active = ob

            if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.type == 'MESH':
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            for ob in copyObjects:
                c = c + 1
                if ob.name not in bpy.context.view_layer.objects:
                    continue
                clean_name = ob.name.split(".")[0]
                clean_name = re.sub(r'[^\w\-]', '_', clean_name)
                ob.rename(clean_name)
                if ob.data:
                    ob.data.rename(clean_name)

                print("Fix Angles Progress: ", c, len(copyObjects))

                if not (ob.hide_render or ob.hide_get()) and ob.name.find("_collision") == -1 and ob.name.find(
                        "convex_") == -1:
                    ob.rotation_euler = (0, 0, math.radians(-90))

                    if (ob.name + "_collision") in bpy.data.objects:
                        bpy.data.objects[ob.name + "_collision"].rotation_euler = (0, 0, math.radians(-90))

                    selected.append(ob.name)
                    bpy.context.view_layer.objects.active = ob
                    ob.select_set(True)

            bpy.ops.object.select_all(action='DESELECT')
            selected = []
            copyObjects = [obj for obj in bpy.data.objects if self._should_include(obj, user_selected_names)]

            for ob in copyObjects:
                if ob.name not in bpy.context.view_layer.objects:
                    continue
                if not (ob.hide_render or ob.hide_get()) and ob.name.find("_collision") == -1 and ob.name.find("convex_") == -1:
                    selected.append(ob.name)

            print('[UTS] Exporting ', len(selected), ' models...')

            chunks = []
            buffer = []

            for obj in bpy.data.objects:
                if not self._should_include(obj, user_selected_names):
                    continue
                if obj.name.endswith("_collision"):
                    continue

                if len(buffer) > 200:
                    chunks.append(buffer)
                    buffer = []

                buffer.append(obj.name)

                if obj.name + "_collision" in bpy.data.objects:
                    buffer.append(obj.name + "_collision")

            chunks.append(buffer)

            textureOutputAlt = prefs.temp_path_models

            for index, chunk in enumerate(chunks):
                new_scene = bpy.data.scenes.new(name=f"SubprojectScene_{index + 1}")
                bpy.context.window.scene = new_scene

                bpy.data.scenes[bpy.context.scene.name].vs.export_path = textureOutputAlt
                bpy.data.scenes[bpy.context.scene.name].vs.export_format = "SMD"

                for objn in chunk:
                    obj = bpy.data.objects[objn]
                    for scene in bpy.data.scenes:
                        if obj.name in scene.collection.objects:
                            scene.collection.objects.unlink(obj)

                    new_scene.collection.objects.link(obj)

                for obj in new_scene.collection.objects:
                    if obj.name.find("_collision") != -1:
                        obj.hide_set(True)

                if bpy.context.active_object and bpy.context.active_object.mode and bpy.context.active_object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode='OBJECT')

                for i in range(4):
                    print("[UTS] Exporting models. Stage ", i + 1, "/3")

                    bpy.ops.object.select_all(action='DESELECT')

                    new_scene = bpy.data.scenes[f"SubprojectScene_{index + 1}"]

                    for obName in selected:
                        name = obName

                        if i == 2:
                            name = obName + "_lod1"
                        elif i == 3:
                            name = obName + "_collision"

                        if not name in new_scene.collection.objects:
                            continue
                        ob = new_scene.collection.objects[name]

                        if i == 1:
                            ob.rename(obName + "_lod1")
                        elif i == 2:
                            ob.rename(obName + "_lod2")

                        if i == 2 or i == 1 and ob.type == 'MESH':
                            mod = ob.modifiers.new('dec', 'DECIMATE')

                            if mod:
                                mod.decimate_type = 'DISSOLVE'
                                mod.delimit = {'UV'}
                                mod.angle_limit = math.radians(i == 1 and 10 or 30)
                                mod.decimate_type = 'DISSOLVE'

                            if ob.data and hasattr(ob.data, "polygons") and len(ob.data.polygons) > 30:
                                ob.hide_set(True)

                    if i == 3:
                        bpy.ops.object.select_all(action='DESELECT')

                        for obj in new_scene.collection.objects:
                            obj.hide_set(obj.name.find("_collision") == -1)
                            obj.select_set(obj.name.find("_collision") != -1)

                        for obj in new_scene.collection.objects:
                            if not obj.hide_viewport and obj.data and hasattr(obj.data, "polygons") and len(obj.data.polygons) > 250:
                                mod = obj.modifiers.new('dec', 'DECIMATE')
                                mod.decimate_type = 'DISSOLVE'
                                mod.delimit = {'UV'}
                                mod.angle_limit = math.radians(4)

                        bpy.ops.object.shade_smooth()
                        bpy.ops.object.select_all(action='DESELECT')

                    for obj in new_scene.collection.objects:
                        bpy.context.view_layer.objects.active = obj
                        break

                    bpy.ops.object.select_all(action='DESELECT')
                    for obj in bpy.context.scene.objects:
                        if not obj.hide_viewport:
                            obj.select_set(True)
                            bpy.context.view_layer.objects.active = obj

                    if bpy.context.view_layer.objects.active:
                        bpy.context.view_layer.objects.active.location.x += 0.001
                        bpy.context.view_layer.objects.active.location.x -= 0.001

                    try:
                        io_scene_valvesource.utils.State.update_scene(bpy.context.scene)
                    except Exception as e:
                        print(f"[UTS] Failed to update Valve Source scene state: {e}")

                    bpy.ops.export_scene.smd(export_scene=True)

                    for obj in bpy.data.scenes[f"SubprojectScene_{index + 1}"].collection.objects:
                        modif = obj.modifiers.get("dec")
                        if modif:
                            obj.modifiers.remove(obj.modifiers.get("dec"))

                        modif2 = obj.modifiers.get("weld")
                        if modif2:
                            obj.modifiers.remove(obj.modifiers.get("weld"))

                for obName in selected:
                    with open(textureOutputAlt + "\\" + obName + "_idle.smd", "w") as f:
                        f.write("""version 1
nodes
0 "joint0" -1
end
skeleton
time 0
0 0.000000 0.000000 0.000000 0 0.000000 0.000000
end""")

                    # 1 Blender meter = 39.3701 Source units (inches)
                    SOURCE_SCALE = 39.3701

                    loc = world_origins.get(obName)
                    if loc:
                        origin_cmd = f'$origin {loc.x * SOURCE_SCALE:.6f} {loc.y * SOURCE_SCALE:.6f} {loc.z * SOURCE_SCALE:.6f} -90'
                    else:
                        origin_cmd = '$autocenter'

                    qcData = f"""$scale {SOURCE_SCALE:.6f}
$modelname "{prefs.model_prefix}/{obName}.mdl"
$cdmaterials "{prefs.material_prefix}_override" "{prefs.material_prefix}"
$staticprop
$body studio "{obName}.smd"
$sequence idle "{obName}_idle"
$surfaceprop "no_decal"
{origin_cmd}"""

                    for i in range(1, 3):
                        if os.path.isfile(textureOutputAlt + "\\" + obName + f"_lod{i}.smd"):
                            qcData += f"""
$lod {3500 + (i-1) * 1500}
{{
    replacemodel "{obName}.smd" "{obName}_lod{i}.smd"
}}"""

                    if os.path.isfile(textureOutputAlt + "\\" + obName + "_collision.smd"):
                        qcData += f"""
$collisionmodel "{obName}_collision.smd" {{
    $concave
    $maxconvexpieces 512
    $automass
}}"""

                    with open(textureOutputAlt + "\\" + obName + ".qc", "w") as f:
                        f.write(qcData)

                    print(f"[UTS] QC written: {textureOutputAlt}\\{obName}.qc")

            print(f"[UTS] Starting studiomdl compilation for {len(selected)} models...")
            print(f"[UTS] Models to compile: {selected}")

            results = []
            for obName in selected:
                print(f"[UTS] Compiling {obName}...")
                output = run_process(obName)
                print(f"[UTS] Output for {obName}:\n{output}\n")
                if output.count('\n') >= 3:
                    results.append(output)

            output_log = os.path.join(prefs.temp_path, "output.txt")
            with open(output_log, "w") as f:
                f.write("\n\n".join(results))

            subprocess.Popen(["notepad", output_log])

        # Cleanup: restore objects to a clean scene and reset visibility
        try:
            restore_scene = bpy.data.scenes.new(name=original_scene_name + "_restore")
            bpy.context.window.scene = restore_scene

            # First pass: collect all objects from temp scenes and link to restore
            for obj in list(bpy.data.objects):
                try:
                    if obj.name not in restore_scene.collection.objects:
                        restore_scene.collection.objects.link(obj)
                except Exception:
                    pass

            # Second pass: remove temp scenes (now safe, objects are already linked elsewhere)
            for scene in list(bpy.data.scenes):
                if scene.name.startswith("SubprojectScene_"):
                    try:
                        bpy.data.scenes.remove(scene)
                    except Exception:
                        pass

            for obj in restore_scene.collection.objects:
                obj.hide_set(False)
        except Exception as e:
            print(f"[UTS] Cleanup error (non-fatal): {e}")

        return {'FINISHED'}
