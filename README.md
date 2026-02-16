# Unreal to Source Exporter (UTS)

Blender add-on for exporting Unreal Engine assets to the Source 1 engine (Garry's Mod).

## Features

- **Texture export** — Convert UE materials (BaseColor, Normal, Roughness, Metallic, AO) to Source VTF/VMT files with automatic power-of-two resizing
- **Model export** — Export meshes as SMD, generate QC files, and compile MDL via studiomdl with automatic LOD generation
- **VMF generation** — Create a Valve Map Format file with `prop_static` entities matching the Blender scene layout
- **Collision generation** — Automatic convex decomposition via CoACD or oriented bounding box (OBB) computation
- **Shader options** — Configure VertexLitGeneric / LightMappedGeneric, phong, envmap per-project via addon preferences

## Requirements

- **Blender 4.0+**
- **Python packages**: `Pillow`, `imageio`, `numpy`, `srctools`, `vmflib`
- **Blender add-on**: `io_scene_valvesource` (Blender Source Tools)
- **Source SDK**: `studiomdl.exe` (Source SDK Base 2013 Multiplayer)
- **CoACD**: `coacd.exe` (bundled in the add-on directory)

## Installation

1. Download or clone this repository.
2. Copy the `unreal_to_source_exporter/` folder into your Blender addons directory:
   ```
   %APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\
   ```
3. Open Blender, go to **Edit > Preferences > Add-ons**, search for **"Unreal to Source Exporter"** and enable it.
4. Configure paths in the add-on preferences (GarrysMod, VTex, CoACD, temp directories).

## Configuration

Open **Edit > Preferences > Add-ons > Unreal to Source Exporter (UTS)**:

| Setting | Description |
|---------|-------------|
| **Chemin GarrysMod** | Root GarrysMod folder (contains `bin/`, `garrysmod/`) |
| **Chemin garrysmod/** | The `garrysmod/` subfolder (contains `materials/`, `models/`) |
| **Chemin VTex** | Path to `vtex.exe` from Source SDK |
| **Chemin CoACD** | Path to `coacd.exe` for collision generation |
| **Dossier temporaire** | Temp folder for QC, SMD, VMF files |
| **Prefixe materiaux** | Relative path under `materials/` (e.g. `sanji/bbr`) |
| **Prefixe modeles** | Relative path under `models/` (e.g. `sanji/bbr`) |
| **Shader** | `VertexLitGeneric` (props) or `LightMappedGeneric` (maps) |
| **$phong / $envmap** | Toggle phong shading and environment map reflections |

## Usage

The add-on adds a **"UTS Export"** panel in the 3D Viewport sidebar (N-panel):

### Export Chain
Full pipeline: prepare scene, export textures, export models, generate VMF. Opens a dialog to select which steps to run.

### UE Textures -> Source
Export materials from the current scene. Automatically detects BaseColor, Normal, emissive textures by naming convention (`_basecolor`, `_bc`, `_n`, `_normal`, etc.).

### GTA Textures -> Source
Stub for GTA texture workflow (baking not yet implemented).

### Create Collisions
Generate collision meshes using CoACD convex decomposition. Configure resolution, MCTS parameters, and max convex hulls.

### OOB (Oriented Bounding Box)
Compute a tight oriented bounding box as a collision mesh for the active object.

## Architecture

```
unreal_to_source_exporter/
├── __init__.py              # bl_info, ADDON_PACKAGE, register/unregister
├── preferences.py           # UTS_Prefs (addon preferences)
├── utils.py                 # PILToVTF, clearCollections, clearMaterialsNames, copyOrigin
├── core/
│   ├── __init__.py
│   ├── helpers.py           # get_prefs(), get_save_dir(), get_bin_dir()
│   ├── texture.py           # create_texture(), texture cache
│   ├── material.py          # detect_nocull_materials(), rename_textures()
│   ├── model.py             # run_process() (studiomdl)
│   └── vmf.py               # create_prop_entity()
├── operators/
│   ├── __init__.py           # operator_classes list
│   ├── export_chain.py       # UTS_OT_ExportChain
│   ├── texture_export.py     # UTS_OT_UETextureExport, UTS_OT_GTATextureExport
│   └── collision.py          # UTS_OT_CreateCollisions, UTS_OT_CreateOOB
├── ui/
│   ├── __init__.py           # ui_classes list
│   └── panel.py              # UTS_PT_MainPanel, UTS_OT_OpenPreferences
├── coacd.exe                 # CoACD binary
└── temp/                     # Temporary files directory
```

## License

This project is provided as-is for personal and commercial use.
