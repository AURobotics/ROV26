import subprocess
import sys
import shutil
import argparse
import os
import re
from pathlib import Path
from wheel.wheelfile import WheelFile

# Regex to find auditwheel's mangled hash (e.g., -57ce35be)
MANGLE_REGEX = re.compile(r"-[0-9a-f]{8}\.")

EXTRA_DEPS = ['gstreamer-libs>=1.22.0 ; sys_platform != "linux"']


HOOK_CODE = """
import sys
import site
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

datas = []
binaries = []
hiddenimports = []

import cv2
cv2_root = Path(cv2.__file__).parent.resolve()

for config in cv2_root.glob("config*.py"):
    datas.append((str(config), "cv2"))

if sys.platform == "win32":
    sp_paths = site.getsitepackages()
    if site.getusersitepackages():
        sp_paths.append(site.getusersitepackages())

    GST_CORE_DEST = "gstreamer_libs"

    for sp in sp_paths:
        sp_path = Path(sp)
        for pkg_path in sp_path.glob("gstreamer_*"):
            if not pkg_path.is_dir():
                continue
                
            pkg_folder_name = pkg_path.name
            datas.append((str(pkg_path), pkg_folder_name))
            
            plugin_path = pkg_path / 'lib' / 'gstreamer-1.0'
            if plugin_path.exists():
                datas.append((str(plugin_path), f'{GST_CORE_DEST}/lib/gstreamer-1.0'))
                
            bin_path = pkg_path / 'bin'
            if bin_path.exists():
                for dll in bin_path.glob("*.dll"):
                    binaries.append((str(dll), '.'))

hiddenimports.extend(collect_submodules('cv2'))
"""

LOADER_CODE = """
# --- GSTREAMER LOADER (AUTO-PATCHED) ---
import sys
import os
import ctypes
from pathlib import Path
from importlib.util import find_spec

def get_hook_dirs():
    \"\"\"Used by PyInstaller entry point to locate hook-cv2.py\"\"\"
    return [os.path.dirname(__file__)]

def _setup_gst_env():
    if sys.platform == "win32":
        _gst_root = None
        _spec = find_spec("gstreamer_libs")
        
        if _spec and _spec.origin:
            _gst_root = Path(_spec.origin).parent.resolve()
        elif getattr(sys, 'frozen', False):
            _gst_root = Path(sys._MEIPASS) / "gstreamer_libs"

        if _gst_root and (_gst_root / "bin").exists():
            try:
                os.add_dll_directory(str(_gst_root / "bin"))
            except Exception: pass

_setup_gst_env()
# -------------------------------------------
"""



def patch_rpaths_and_mangle(target_file, bin_dir):
    """Fixes auditwheel mangling and sets RPATH for a given .so file"""
    try:
        needed = subprocess.check_output(
            ["patchelf", "--print-needed", str(target_file)], text=True
        ).splitlines()

        for lib in needed:
            if MANGLE_REGEX.search(lib):
                prefix = lib.split("-")[0]
                match = list(bin_dir.glob(f"{prefix}*"))
                target_name = match[0].name if match else MANGLE_REGEX.sub(".", lib)
                print(f"     -> Fixing mangle: {lib} to {target_name}")
                subprocess.run(
                    [
                        "patchelf",
                        "--replace-needed",
                        lib,
                        target_name,
                        str(target_file),
                    ],
                    check=True,
                )

        rel_path = os.path.relpath(bin_dir, target_file.parent)
        subprocess.run(
            ["patchelf", "--set-rpath", f"$ORIGIN/{rel_path}", str(target_file)],
            check=True,
        )
    except Exception as e:
        print(f"   ! Error patching {target_file.name}: {e}")


def patch_wheel(wheel_path, output_dir=None):
    wheel_path = Path(wheel_path)
    gst_src = Path(__file__).parent / "bin"
    if sys.platform == "linux":
        print("Linux wheels are not supported")
        exit(1)

    build_dir = (Path(__file__).parent / "build_temp").resolve()
    dist_dir = (
        Path(output_dir).resolve() if output_dir else (Path(__file__).parent / "wheels")
    )

    if build_dir.exists():
        shutil.rmtree(build_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    print(f"Unpacking {wheel_path.name}...")
    with WheelFile(str(wheel_path)) as wf:
        wf.extractall(str(build_dir))

    try:
        pkg_dir = next(build_dir.glob("cv2"), None)
        dist_info_dir = next(build_dir.glob("*.dist-info"), None)

        if not pkg_dir:
            raise RuntimeError("cv2 folder missing.")

        target_bin_dir = pkg_dir / "bin"
        if target_bin_dir.exists():
            shutil.rmtree(target_bin_dir)
        shutil.copytree(gst_src, target_bin_dir)

        hook_file = pkg_dir / "hook-cv2.py"
        hook_file.write_text(HOOK_CODE.strip(), encoding="utf-8")


        init_file = pkg_dir / "__init__.py"
        content = init_file.read_text(encoding="utf-8")
        loader_regex = re.compile(
            r"# --- GSTREAMER LOADER \(AUTO-PATCHED\) ---.*?# -------------------------------------------",
            re.DOTALL,
        )

        if loader_regex.search(content):
            new_init = loader_regex.sub(LOADER_CODE.strip(), content)
        else:
            new_init = LOADER_CODE.strip() + "\n" + content
        init_file.write_text(new_init, encoding="utf-8")

        # 5. Patch Metadata (Preserving EXTRA_DEPS)
        if dist_info_dir:
            meta_file = dist_info_dir / "METADATA"
            meta_content = meta_file.read_text(encoding="utf-8")
            for dep in EXTRA_DEPS:
                dep_str = f"Requires-Dist: {dep}"
                if dep_str not in meta_content:
                    meta_lines = meta_content.splitlines()
                    for i, line in enumerate(meta_lines):
                        if not line.strip() or line.startswith("Requires-Dist:"):
                            meta_lines.insert(i, dep_str)
                            break
                    meta_content = "\n".join(meta_lines)
            meta_file.write_text(meta_content, encoding="utf-8")

            # 6. Entry Points
            ep_file = dist_info_dir / "entry_points.txt"
            hook_entry = "hook-dirs = cv2:get_hook_dirs"
            if ep_file.exists():
                ep_content = ep_file.read_text()
                if hook_entry not in ep_content:
                    if "[pyinstaller40]" in ep_content:
                        ep_content = ep_content.replace(
                            "[pyinstaller40]", f"[pyinstaller40]\\n{hook_entry}"
                        )
                    else:
                        ep_content += f"\\n[pyinstaller40]\\n{hook_entry}\\n"
                ep_file.write_text(ep_content.replace("\\n", "\n"))
            else:
                ep_file.write_text(
                    f"[pyinstaller40]\\n{hook_entry}\\n".replace("\\n", "\n")
                )

    except Exception as e:
        print(f"FAILED: {e}")
        if build_dir.exists():
            shutil.rmtree(build_dir)
        sys.exit(1)

    print("Repacking wheel...")
    subprocess.run(
        [sys.executable, "-m", "wheel", "pack", str(build_dir), "-d", str(dist_dir)],
        check=True,
    )
    shutil.rmtree(build_dir)
    wheel_path.unlink()
    print(f"✅ Successfully patched wheel in: {dist_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", help="Path to the .whl file to patch")
    parser.add_argument("-o", "--output", help="Output directory for the patched wheel")
    args = parser.parse_args()
    patch_wheel(args.wheel, args.output)
