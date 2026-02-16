import bpy


def get_prefs():
    """Return the addon preferences. Uses deferred import to avoid circular imports."""
    from .. import ADDON_PACKAGE
    return bpy.context.preferences.addons[ADDON_PACKAGE].preferences


def get_save_dir():
    """Return the full materials output directory."""
    prefs = get_prefs()
    return prefs.subgmod_path + "materials/" + prefs.material_prefix + "/"


def get_bin_dir():
    """Return the GarrysMod bin/ directory."""
    return get_prefs().gmod_path + "bin/"
