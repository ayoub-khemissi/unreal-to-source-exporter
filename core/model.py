import os
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

    print(f"[UTS] Running: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        stdout, stderr = process.communicate(timeout=300)
        output = stdout + stderr
        print(f"[UTS] studiomdl exit code: {process.returncode}")
        print(f"[UTS] studiomdl output: {output[:500]}")

        return output
    except Exception as e:
        print(f"[UTS] Exception for {obName}: {e}")
        return str(e)
