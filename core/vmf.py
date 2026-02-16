import math

from vmflib import vmf
from vmflib.types import Origin
from mathutils import Euler

from .helpers import get_prefs


def create_prop_entity(obj, name_common):
    """Create a prop_static VMF entity from a Blender object."""
    cp_prop = vmf.Entity('prop_static')
    cp_prop.origin = Origin(obj.location.x, obj.location.y, obj.location.z)

    angCopy = obj.rotation_euler.copy()
    mat_blender = angCopy.to_matrix().to_4x4()

    ang = mat_blender.to_euler('YZX')
    ang.rotate(Euler((0, 0, math.radians(-90)), 'YZX'))

    cp_prop.properties['angles'] = f'{round(math.degrees(angCopy[1]), 3)} {round(math.degrees(angCopy[2]), 3)} {round(math.degrees(angCopy[0]), 3)}'
    cp_prop.properties['model'] = "models/" + get_prefs().model_prefix + "/" + name_common + ".mdl"

    return cp_prop
