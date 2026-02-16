import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty


class UTS_Prefs(AddonPreferences):
    bl_idname = __package__

    # --- Chemins ---

    gmod_path: StringProperty(
        name='Chemin GarrysMod',
        description='Dossier racine de Garry\'s Mod (contient bin/, garrysmod/, etc.)',
        default='C:\\Program Files (x86)\\Steam\\steamapps\\common\\GarrysMod\\',
        subtype='DIR_PATH'
    )

    subgmod_path: StringProperty(
        name='Chemin garrysmod/',
        description='Sous-dossier garrysmod/ (contient materials/, models/, etc.)',
        default='C:\\Program Files (x86)\\Steam\\steamapps\\common\\GarrysMod\\garrysmod\\',
        subtype='DIR_PATH'
    )

    vtex_path: StringProperty(
        name='Chemin VTex',
        description='Chemin vers vtex.exe du Source SDK',
        default='C:\\Program Files (x86)\\Steam\\steamapps\\common\\Source SDK Base 2013 Multiplayer\\bin\\vtex.exe',
        subtype='FILE_PATH'
    )

    coacd_path: StringProperty(
        name='Chemin CoACD',
        description='Chemin vers coacd.exe pour la generation de collisions',
        default='',
        subtype='FILE_PATH'
    )

    temp_path: StringProperty(
        name='Dossier temporaire',
        description='Dossier pour les fichiers temporaires d\'export (QC, SMD, VMF)',
        default='C:\\uts_temp\\',
        subtype='DIR_PATH'
    )

    temp_path_models: StringProperty(
        name='Dossier temporaire modeles',
        description='Dossier pour les modeles compiles temporaires (SMD)',
        default='C:\\uts_temp\\compiled_models\\',
        subtype='DIR_PATH'
    )

    # --- Prefixes materiaux / modeles ---

    material_prefix: StringProperty(
        name='Prefixe materiaux',
        description='Chemin relatif dans materials/ (ex: sanji/bbr -> materials/sanji/bbr/)',
        default='sanji/bbr'
    )

    model_prefix: StringProperty(
        name='Prefixe modeles',
        description='Chemin relatif dans models/ (ex: sanji/bbr -> models/sanji/bbr/)',
        default='sanji/bbr'
    )

    # --- Options shader ---

    shader_type: EnumProperty(
        name='Shader',
        description='Type de shader Source dans les fichiers VMT',
        items=[
            ('VertexLitGeneric', 'VertexLitGeneric', 'Shader standard pour les modeles (props)'),
            ('LightMappedGeneric', 'LightMappedGeneric', 'Shader pour les brushs/maps (lightmaps)'),
        ],
        default='VertexLitGeneric'
    )

    enable_phong: BoolProperty(
        name='$phong',
        description='Activer le phong shading (reflets speculaires)',
        default=False
    )

    phong_exponent: FloatProperty(
        name='$phongexponent',
        description='Intensite du reflet phong (plus eleve = plus serre)',
        default=30.0,
        min=1.0,
        max=255.0
    )

    phong_boost: FloatProperty(
        name='$phongboost',
        description='Multiplicateur de luminosite du phong',
        default=1.0,
        min=0.0,
        max=10.0
    )

    enable_envmap: BoolProperty(
        name='$envmap',
        description='Activer les reflets environnementaux (cubemap)',
        default=False
    )

    envmap_tint: FloatProperty(
        name='$envmaptint',
        description='Intensite des reflets envmap (0 = aucun, 1 = max)',
        default=0.3,
        min=0.0,
        max=1.0
    )

    def draw(self, context):
        layout = self.layout

        # -- Section : Chemins --
        box = layout.box()
        row = box.row()
        row.label(text="Chemins", icon='FILE_FOLDER')
        col = box.column(align=True)
        col.prop(self, "gmod_path")
        col.prop(self, "subgmod_path")
        col.separator()
        col.prop(self, "vtex_path")
        col.prop(self, "coacd_path")
        col.separator()
        col.prop(self, "temp_path")
        col.prop(self, "temp_path_models")

        layout.separator()

        # -- Section : Prefixes --
        box = layout.box()
        row = box.row()
        row.label(text="Prefixes de sortie", icon='OUTLINER')
        col = box.column(align=True)
        col.prop(self, "material_prefix")
        col.prop(self, "model_prefix")

        layout.separator()

        # -- Section : Shader --
        box = layout.box()
        row = box.row()
        row.label(text="Options Shader", icon='SHADING_RENDERED')
        col = box.column(align=True)
        col.prop(self, "shader_type")

        col.separator()
        row = col.row()
        row.prop(self, "enable_phong")
        sub = row.row()
        sub.enabled = self.enable_phong
        sub.prop(self, "phong_exponent")
        sub = row.row()
        sub.enabled = self.enable_phong
        sub.prop(self, "phong_boost")

        col.separator()
        row = col.row()
        row.prop(self, "enable_envmap")
        sub = row.row()
        sub.enabled = self.enable_envmap
        sub.prop(self, "envmap_tint")
