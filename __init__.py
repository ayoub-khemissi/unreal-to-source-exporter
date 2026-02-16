import bpy

bl_info = {
    "name": "Unreal to Source Exporter (UTS)",
    "author": "Akulla",
    "version": (2, 0),
    "blender": (4, 0, 0),
    "description": "Export Unreal Engine assets to Source 1 (GMod) — models, textures & VMF",
    "category": "Import-Export",
}

ADDON_PACKAGE = __package__


def register():
    from .preferences import UTS_Prefs
    from .operators import operator_classes
    from .ui import ui_classes

    bpy.utils.register_class(UTS_Prefs)
    for cls in operator_classes:
        bpy.utils.register_class(cls)
    for cls in ui_classes:
        bpy.utils.register_class(cls)


def unregister():
    from .preferences import UTS_Prefs
    from .operators import operator_classes
    from .ui import ui_classes

    for cls in reversed(ui_classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(operator_classes):
        bpy.utils.unregister_class(cls)
    bpy.utils.unregister_class(UTS_Prefs)


if __name__ == "__main__":
    register()
