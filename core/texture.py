import os
import shutil

import bpy
import imageio
from PIL import Image
from srctools.vtf import ImageFormats as VTFFormats

from .. import utils
from .helpers import get_prefs, get_save_dir


_already_created_textures = {}


def reset_texture_cache():
    """Clear the texture creation cache. Call at the start of each export run."""
    global _already_created_textures
    _already_created_textures = {}


def create_texture(texImg, bumpImg, matData, aoImg=None, roughnessImg=None,
                   metallicImg=None, color=None, asMapTexture=False,
                   no_cull=False, is_transparent=False):
    """Create VTF + VMT files for a single material."""
    print(f"[UTS] === create_texture START for material: {matData.name} ===")
    print(f"[UTS]   texImg type={type(texImg).__name__}, bumpImg={'None' if bumpImg is None else type(bumpImg).__name__}")
    print(f"[UTS]   get_save_dir() = {get_save_dir()}")

    texDir, bumpDir = texImg, bumpImg

    if not isinstance(texImg, str):
        texDir = os.path.normpath(bpy.path.abspath(texImg.filepath, library=texImg.library))

    if bumpImg and not isinstance(bumpImg, str):
        bumpDir = os.path.normpath(bpy.path.abspath(bumpImg.filepath, library=bumpImg.library))

    print(f"[UTS]   texDir = {texDir}")
    print(f"[UTS]   texDir exists = {os.path.isfile(texDir) if isinstance(texDir, str) else 'N/A'}")
    assert isinstance(bumpDir, str) or bumpDir is None

    # Copy textures png to the save dir
    texName = ("mapTex_" if asMapTexture else "") + matData.name
    bumpName = ""

    if texName in _already_created_textures:
        print(f"[UTS]   SKIPPED (already created): {texName}")
        return

    _already_created_textures[texName] = True

    if isinstance(bumpImg, str):
        folder_texture = bumpImg.split("/")
        bumpName = ("mapTex_" if asMapTexture else "") + os.path.splitext((folder_texture[len(folder_texture) - 1]))[0]
    elif bumpImg:
        bumpName = ("mapTex_" if asMapTexture else "") + bumpImg.name

    filename, file_extension = os.path.splitext(texDir.replace("\\", "/"))
    texturePath = ""
    bumpPath = ""

    if texDir.find(".tga") == -1:
        # Convert to TGA if needed
        try:
            img = imageio.imread(texDir)
            print(f"[UTS]   imageio.imread OK, shape={img.shape}")
        except Exception as e:
            print(f"[UTS] Error reading {texDir} with imageio: {e}")
            fallback_success = False
            if not isinstance(texImg, str):
                print(f"[UTS] Attempting to recover by saving {texImg.name} to temp TGA...")
                try:
                    safe_name = bpy.path.clean_name(texImg.name)
                    os.makedirs(get_save_dir(), exist_ok=True)
                    temp_path = get_save_dir() + "temp_fallback_" + safe_name + ".tga"

                    texImg.save_render(filepath=temp_path)

                    if os.path.exists(temp_path):
                        print(f"[UTS] Successfully saved fallback to {temp_path}")
                        img = imageio.imread(temp_path)
                        texDir = temp_path
                        filename = os.path.splitext(texDir.replace("\\", "/"))[0]
                        fallback_success = True
                except Exception as e2:
                    print(f"[UTS] Fallback save failed: {e2}")

            if not fallback_success:
                print(f"[UTS] critical failure reading texture {texDir}")
                return

        img_pil = Image.fromarray(img)

        tga_path = filename + ".tga"
        try:
            img_pil.save(tga_path)
            print(f"[UTS]   TGA saved to: {tga_path}")
        except Exception as e:
            print(f"[UTS]   Cannot save TGA to original dir ({tga_path}): {e}")
            print(f"[UTS]   Saving TGA to get_save_dir() instead...")
            os.makedirs(get_save_dir(), exist_ok=True)
            tga_path = get_save_dir() + os.path.basename(filename) + ".tga"
            filename = os.path.splitext(tga_path.replace("\\", "/"))[0]
            img_pil.save(tga_path)
            print(f"[UTS]   TGA saved to fallback: {tga_path}")
        texturePath = tga_path

        if bumpImg:
            img_pil = Image.fromarray(imageio.imread(bumpDir))
            bumpPath = filename[:filename.rfind('/')] + "/" + bumpName[:(bumpName.find('.'))] + ".tga"
            img_pil.save(bumpPath)
            print("[UTS] Convert", bumpDir, "to", bumpPath)

        print("[UTS] Convert", texDir, "to", filename + ".tga", texDir.replace("\\", "/"))
    else:
        texturePath = get_save_dir() + texName + os.path.splitext(texImg.name)[1]
        shutil.copy(texDir, texturePath)

        print("[UTS] Copy", texDir, "to", texturePath)
        if bumpImg:
            bumpPath = get_save_dir() + bumpName
            shutil.copy(bumpDir, bumpPath)
            print("[UTS] Copy", bumpDir, "to", bumpPath)

    # Check for transparency
    image = imageio.imread(texturePath)

    if not is_transparent and (image.shape[2] == 4 and (image[:, :, 3] < 250).any()):
        is_transparent = True

    if bumpImg:
        print("We have a bumpmap")
    else:
        print("We don't have a bumpmap")

    final_path = get_prefs().material_prefix + "/"
    fileNameOfPath = os.path.basename(filename)

    if is_transparent:
        if texturePath.lower().find("opaque") != -1:
            is_transparent = False

        for i in {"T_st01_00_ground01D_D"}:
            if texturePath.lower().find(i.lower()) != -1:
                is_transparent = False
                break

    os.makedirs(os.path.dirname(os.path.join(get_save_dir(), matData.name + ".vmt")), exist_ok=True)

    if color:
        color = [float(x) for x in color]

        if len(color) == 4:
            del color[3]

        maxValue = max(color)

        if maxValue <= 0:
            maxValue = 1

        color = [x / maxValue for x in color]

        if abs(max(color) - min(color)) < 0.05:
            color = None
        else:
            for c in range(3):
                if color[c] > 1:
                    color[c] = 1 + (color[c] - 1) / 2
                elif color[c] < 1:
                    color[c] = 1 - (1 - color[c]) / 2

    # Write VMT + VTF
    bumpNameWithoutExtension = None

    dir = get_save_dir() + matData.name + ".vmt"
    prefs = get_prefs()

    if os.path.isfile(dir):
        os.remove(dir)

    shader = prefs.shader_type if not asMapTexture else 'LightMappedGeneric'

    with open(dir, "w") as f:
        f.write(f'"{shader}"\n')
        f.write('{\n')
        f.write(f'\t"$basetexture" "{final_path}{fileNameOfPath}"\n')

        if bumpImg:
            bumpNameWithoutExtension = os.path.splitext(bumpName)[0]
            f.write(f'\t"$bumpmap" "{final_path}{bumpNameWithoutExtension}"\n')

        if is_transparent:
            f.write('\t"$translucent" 1\n')
            f.write('\t"$alphatest" 1\n')

        if color:
            f.write(f'\t$color "[{color[0]} {color[1]} {color[2]}]"\n')
            f.write(f'\t$color2 "[{color[0]} {color[1]} {color[2]}]"\n')

        if shader == 'VertexLitGeneric':
            f.write('\t"$model" 1\n')

        if prefs.enable_phong:
            f.write('\n\t// Phong\n')
            f.write('\t"$phong" 1\n')
            f.write(f'\t"$phongexponent" {int(prefs.phong_exponent)}\n')
            f.write(f'\t"$phongboost" {round(prefs.phong_boost, 2)}\n')
            f.write('\t"$phongfresnelranges" "[0.05 0.5 1]"\n')

        if prefs.enable_envmap:
            f.write('\n\t// Envmap\n')
            f.write('\t"$envmap" "env_cubemap"\n')
            f.write(f'\t"$envmaptint" "[{round(prefs.envmap_tint, 2)} {round(prefs.envmap_tint, 2)} {round(prefs.envmap_tint, 2)}]"\n')
            if bumpImg:
                f.write('\t"$normalmapalphaenvmapmask" 1\n')

        if no_cull:
            f.write('\n\t"$nocull" 1\n')

        f.write('}')

    # Create VTF
    with open(get_save_dir() + fileNameOfPath + ".vtf", 'wb') as targetfile:
        utils.PILToVTF(Image.open(filename + ".tga"), VTFFormats.DXT5 if is_transparent else VTFFormats.DXT1).save(targetfile)

    if bumpImg:
        with open(get_save_dir() + bumpNameWithoutExtension + ".vtf", 'wb') as targetfile:
            utils.PILToVTF(Image.open(bumpPath), VTFFormats.RGBA8888 if is_transparent else VTFFormats.RGB888).save(targetfile)
