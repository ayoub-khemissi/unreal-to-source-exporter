import os
import string
import time

import bpy
import numpy as np
from PIL import Image
from bpy.props import BoolProperty

from .. import utils
from ..core.helpers import get_prefs, get_save_dir
from ..core.material import detect_nocull_materials, rename_textures
from ..core.texture import create_texture, reset_texture_cache


class UTS_OT_UETextureExport(bpy.types.Operator):
    bl_idname = "uts.ue_texture_export"
    bl_label = "UTS: UE Texture to Source"
    bl_options = {'REGISTER'}

    addLayout = 'VIEW3D_MT_object'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    map_texture: BoolProperty(
        name="map_texture",
        description="LightMappedGeneric si coche (Texture pour mapper)",
    )

    def execute(self, context):
        reset_texture_cache()
        utils.clearMaterialsNames()
        print('\n[UTS] ====== UETextureExport START ======')
        print(f'[UTS] get_save_dir() = {get_save_dir()}')
        print(f'[UTS] get_save_dir() exists = {os.path.isdir(get_save_dir())}')
        print(f'[UTS] Total materials in scene: {len(bpy.data.materials)}')

        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.make_local(type='SELECT_OBDATA_MATERIAL')

        rename_textures()

        newImgs = []
        texPack = detect_nocull_materials()

        for i in bpy.data.materials:
            if not i or i is None or not i.node_tree:
                continue
            bumpMap, tex = None, None
            firstUsedTex = None

            isNoCull = i.name in texPack

            for j in i.node_tree.nodes:
                if type(j).__name__ == "ShaderNodeTexImage":
                    if not j.image:
                        print(f"[UTS]   Skipping texture node '{j.name}' in material '{i.name}' -- no image assigned")
                        continue

                    texName = j.image.name
                    texFilePath = os.path.normpath(bpy.path.abspath(j.image.filepath, library=j.image.library)) if j.image.filepath else ""
                    texFileBase = os.path.splitext(os.path.basename(texFilePath))[0].lower() if texFilePath else ""

                    texName = texName.split(".")[0].rstrip(string.digits).strip("_").lower()

                    if texName.endswith("_m"):
                        continue

                    if "emissive" in texName or "emissive" in texFileBase:
                        print(f"[UTS]   Skipping EMISSIVE texture: '{j.image.name}' (path: {texFilePath})")
                        continue

                    used = False
                    for output in j.outputs:
                        if output.is_linked:
                            used = True
                            break

                    if not used:
                        i.node_tree.nodes.remove(j)
                        continue

                    print(f"[UTS]   Material '{i.name}' has texture node: '{j.image.name}' (cleaned name: '{texName}', file: '{texFileBase}')")

                    if firstUsedTex is None:
                        firstUsedTex = j

                    names_to_check = [texName, texFileBase]

                    is_normal = any(
                        n.endswith("_n") or n.endswith("_normal") or n.endswith("_nao")
                        for n in names_to_check
                    )
                    is_basecolor = any(
                        n.endswith("_basecolor") or n.endswith("_bc") or n.endswith("_b") or
                        n.endswith("_hrm") or n.endswith("_diffuse") or n.endswith("_albedo") or
                        n.endswith("_color") or n.endswith("_base") or n.endswith("_diff") or
                        n.endswith("_d") or "albedotransparency" in n or
                        "basecolor" in n or "diffuse" in n
                        for n in names_to_check
                    )

                    if is_normal:
                        bumpMap = j
                        print(f"[UTS]     -> Identified as NORMAL map")
                    elif is_basecolor:
                        tex = j
                        print(f"[UTS]     -> Identified as BASE COLOR")

                    if bumpMap and tex:
                        break

            # Fallback: first connected non-emissive texture
            if tex is None and firstUsedTex is not None:
                print(f"[UTS]   No naming convention match for '{i.name}', using fallback texture: '{firstUsedTex.image.name}'")
                tex = firstUsedTex

            # Deeper fallback: trace Principled BSDF Base Color input
            if tex is None:
                print(f"[UTS]   No texture nodes found directly for '{i.name}', tracing Principled BSDF inputs...")
                for node in i.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        base_color_input = node.inputs.get('Base Color')
                        if base_color_input and base_color_input.is_linked:
                            visited = set()
                            queue = [base_color_input.links[0].from_node]
                            while queue:
                                current = queue.pop(0)
                                if current in visited:
                                    continue
                                visited.add(current)
                                if current.type == 'TEX_IMAGE' and current.image:
                                    print(f"[UTS]   Found texture through BSDF trace: '{current.image.name}'")
                                    tex = current
                                    break
                                for inp in current.inputs:
                                    if inp.is_linked:
                                        queue.append(inp.links[0].from_node)
                        if tex:
                            break

            # Search for roughness, metallic, AO
            extraData = {
                "roughness": None,
                "metallic": None,
                "ao": None
            }

            for j in i.node_tree.nodes:
                if type(j).__name__ == "ShaderNodeSeparateColor":
                    inputImage = None
                    for k in j.inputs:
                        if k.is_linked:
                            inputImage = k.links[0].from_node
                            break

                    if not inputImage:
                        continue

                    picDir = inputImage.image.filepath_raw

                    if picDir.startswith("//"):
                        picDir = bpy.path.abspath(picDir)
                    try:
                        image = Image.open(picDir)

                        image_array = np.array(image)
                        red_channel = image_array[:, :, 0]
                        green_channel = image_array[:, :, 1]
                        blue_channel = image_array[:, :, 2]

                        red_image = Image.fromarray(red_channel, mode='L')
                        green_image = Image.fromarray(green_channel, mode='L')
                        blue_image = Image.fromarray(blue_channel, mode='L')

                        base_path = picDir.rsplit('.', 1)[0]
                        red_image_path = f'{base_path}_metallic_map.png'
                        green_image_path = f'{base_path}_roughness_map.png'
                        blue_image_path = f'{base_path}_ao_map.png'

                        red_image.save(red_image_path)
                        green_image.save(green_image_path)
                        blue_image.save(blue_image_path)

                        extraData["roughness"] = green_image_path
                        extraData["metallic"] = red_image_path
                        extraData["ao"] = blue_image_path
                    except Exception as e:
                        print(f"[UTS] Failed to process image {picDir}: {e}")
                        continue

            # Check for multiply shader color
            multiplyShader = None
            for j in i.node_tree.nodes:
                if type(j).__name__ == "ShaderNodeMix":
                    for output in j.outputs:
                        if output.is_linked:
                            multiplyShader = j.inputs[7].default_value
                            break

            texDir = tex.image if tex else None
            if tex:
                print("Found texture", tex.image.name, "for", i.name)
            else:
                print("[WARNING] Didn't find any fitting textures for", i)

                if multiplyShader:
                    print("Found multiply shader, using it: ", [x for x in multiplyShader])

                    color = (int(multiplyShader[0]*255), int(multiplyShader[1]*255), int(multiplyShader[2]*255), int(multiplyShader[3]*255))
                    d = get_prefs().temp_path + "mapTex_" + i.name + ".png"
                    image = Image.new("RGB", (512, 512), color)
                    image.save(d)

                    time.sleep(1)
                    print("Saving here: ", d)
                    texDir = d
                else:
                    print("We bake it instead.")
                    newImgs.append([i.node_tree.nodes, tex, None, i, isNoCull])

            if bumpMap:
                print("Found bumpmap", bumpMap.image.name, "for", i.name)
            else:
                print("[WARNING] Didn't find any fitting bumpmap for", i)

            if texDir:
                try:
                    create_texture(texDir, bumpMap.image if bumpMap else None, i,
                                   extraData["roughness"], extraData["metallic"], extraData["ao"],
                                   multiplyShader, asMapTexture=self.map_texture, no_cull=isNoCull,
                                   is_transparent=False)
                except Exception as e:
                    print(f"[UTS] !!! EXCEPTION in create_texture for material '{i.name}': {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[UTS]   No texDir for material '{i.name}', skipping create_texture")

        if len(newImgs) == 0:
            print("No texture to bake")
        else:
            print(f"{len(newImgs)} textures to bake (baking disabled)")

        return {'FINISHED'}


class UTS_OT_GTATextureExport(bpy.types.Operator):
    """GTA texture export stub. Baking functionality removed."""
    bl_idname = "uts.gta_texture_export"
    bl_label = "UTS: GTA Texture to Source"
    bl_options = {'REGISTER'}

    addLayout = 'VIEW3D_MT_object'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    map_texture: BoolProperty(
        name="map_texture",
        description="LightMappedGeneric si coche (Texture pour mapper)",
    )

    def execute(self, context):
        reset_texture_cache()
        utils.clearMaterialsNames()
        selected = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')

        for i in selected:
            i.select_set(True)
            bpy.context.view_layer.objects.active = i

        for i in selected:
            i.rename(i.name.replace(".", "_"))

            if "data" in i:
                i.data.rename(i.name)

        rename_textures()

        # NOTE: bakeTextures was removed (dead code: body started with `if True: return`).
        # GTA texture export needs reimplementation if required in the future.
        print("[UTS] GTA texture export: baking not yet implemented")

        return {'FINISHED'}
