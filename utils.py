import os
import math

import bpy
from PIL import Image
from srctools import VTF
from srctools.vtf import ImageFormats as VTFFormats
from srctools.vtf import VTFFlags


def PILToVTF(img: Image, fmt) -> VTF:
    """Convert a PIL Image to a VTF texture, resizing to the closest power of two."""
    def closest_power_of_two(n):
        return 2 ** round(math.log2(n))

    new_width = closest_power_of_two(img.width)
    new_height = closest_power_of_two(img.height)

    if new_width > 2048:
        new_width = 2048
    if new_height > 2048:
        new_height = 2048

    if new_width != img.width or new_height != img.height:
        print(f"[UTS] Resizing texture from {img.width}x{img.height} to {new_width}x{new_height}")
        img = img.resize((new_width, new_height), Image.LANCZOS)

    v = VTF(img.width, img.height, frames=1, fmt=fmt, version=(7, 4), flags=VTFFlags.EIGHTBITALPHA)

    if fmt == VTFFormats.DXT5:
        v.flags = VTFFlags.EIGHTBITALPHA

    v.get(frame=0).copy_from(img.convert('RGBA').tobytes())
    return v


def clearCollections():
    """Move all objects to master collection and remove all other collections."""
    master_collection = bpy.context.scene.collection
    for coll in bpy.data.collections:
        for obj in coll.objects[:]:
            master_collection.objects.link(obj)
            coll.objects.unlink(obj)

    for coll in bpy.data.collections[:]:
        if coll == master_collection:
            continue
        for scene in bpy.data.scenes:
            if coll.name in scene.collection.children:
                scene.collection.children.unlink(coll)
        bpy.data.collections.remove(coll)


def clearMaterialsNames():
    """Strip .001 etc. suffixes from material names."""
    for mat in bpy.data.materials:
        mat.rename(mat.name.split('.')[0])


def copyOrigin(object_a, object_b):
    """Move object_a's origin to match object_b's world position."""
    new_origin_local = object_a.matrix_world.inverted() @ object_b.matrix_world.translation
    for vertex in object_a.data.vertices:
        vertex.co -= new_origin_local
    object_a.matrix_world.translation = object_b.matrix_world.translation
