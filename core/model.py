import subprocess

import bpy

from .helpers import get_bin_dir, get_prefs


def run_process(obName):
    """Run studiomdl.exe process and capture output."""
    prefs = get_prefs()
    cmd = [
        f"{get_bin_dir()}studiomdl.exe",
        "-game", prefs.subgmod_path,
        "-nop4", "-quiet",
        f"{prefs.temp_path_models}\\{obName}.qc"
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=300)
        return stdout + stderr
    except Exception as e:
        print(f"[UTS] Exception occurred while running process for {obName}")
        return str(e)
