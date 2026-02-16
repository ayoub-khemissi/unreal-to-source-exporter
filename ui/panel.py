import os

import bpy

from ..core.helpers import get_prefs


class UTS_PT_MainPanel(bpy.types.Panel):
    bl_label = "UTS Export"
    bl_idname = "UTS_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UTS Export'

    def draw(self, context):
        layout = self.layout
        prefs = get_prefs()

        # -- Section : Info chemins --
        box = layout.box()
        row = box.row()
        row.label(text="Chemins de sortie", icon='FILE_FOLDER')
        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text=f"Materiaux: materials/{prefs.material_prefix}/")
        col.label(text=f"Modeles: models/{prefs.model_prefix}/")
        col.label(text=f"Shader: {prefs.shader_type}")

        row = box.row()
        row.operator("uts.open_preferences", text="Ouvrir les preferences", icon='PREFERENCES')

        layout.separator()

        # -- Section : Preview materiaux --
        box = layout.box()
        row = box.row()
        row.label(text="Materiaux dans la scene", icon='MATERIAL')

        total_mats = 0
        with_base = 0
        with_normal = 0
        without_tex = 0

        for mat in bpy.data.materials:
            if not mat or not mat.node_tree:
                continue
            total_mats += 1
            has_base = False
            has_normal = False

            for node in mat.node_tree.nodes:
                if type(node).__name__ != "ShaderNodeTexImage" or not node.image:
                    continue
                img_name = node.image.name.lower()
                img_path = ""
                if node.image.filepath:
                    img_path = os.path.basename(node.image.filepath).lower()

                if "basecolor" in img_name or "basecolor" in img_path or "diffuse" in img_name or "diffuse" in img_path:
                    has_base = True
                elif "normal" in img_name or "normal" in img_path:
                    has_normal = True

            if has_base:
                with_base += 1
            if has_normal:
                with_normal += 1
            if not has_base and not has_normal:
                without_tex += 1

        col = box.column(align=True)
        col.label(text=f"{total_mats} materiaux detectes")
        col.label(text=f"  {with_base} avec BaseColor", icon='CHECKMARK')
        col.label(text=f"  {with_normal} avec Normal", icon='CHECKMARK')
        if without_tex > 0:
            col.label(text=f"  {without_tex} sans texture", icon='ERROR')

        layout.separator()

        # -- Section : Options shader rapides --
        box = layout.box()
        row = box.row()
        row.label(text="Options Shader", icon='SHADING_RENDERED')
        col = box.column(align=True)
        col.prop(prefs, "shader_type", text="")
        row = col.row(align=True)
        row.prop(prefs, "enable_phong", toggle=True)
        row.prop(prefs, "enable_envmap", toggle=True)

        layout.separator()

        # -- Section : Export rapides --
        box = layout.box()
        row = box.row()
        row.label(text="Export", icon='EXPORT')
        col = box.column(align=True)
        col.scale_y = 1.4
        col.operator("uts.export_chain", text="Export Chain", icon='PLAY')
        col.separator()
        col.operator("uts.ue_texture_export", text="UE Textures -> Source", icon='TEXTURE')
        col.operator("uts.gta_texture_export", text="GTA Textures -> Source", icon='TEXTURE')
        col.separator()
        col.operator("uts.create_collisions", text="Creer Collisions", icon='MESH_ICOSPHERE')
        col.operator("uts.create_oob", text="OOB", icon='CUBE')


class UTS_OT_OpenPreferences(bpy.types.Operator):
    bl_idname = "uts.open_preferences"
    bl_label = "Ouvrir les preferences UTS"
    bl_description = "Ouvre les preferences de l'addon UTS"

    def execute(self, context):
        bpy.ops.preferences.addon_show(module=__package__.rsplit('.', 1)[0])
        return {'FINISHED'}
