from pathlib import Path
import shutil
import subprocess
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename

BRANCH = "opencv-build"

project_root = Path(__file__).parent.parent.resolve()
repo_root = project_root.parent.resolve()
wheels_dir = (project_root / "wheels").resolve()
tmp_dir = (project_root / ".tmp").resolve()
wheels_src = "console/wheels/"

if not wheels_dir.exists():
    wheels_dir.mkdir()

if not tmp_dir.exists():
    tmp_dir.mkdir()

if shutil.which("git") is None:
    print("Git is not installed")
    exit(1)

git_lfs_exists = subprocess.run(["git", "lfs", "--version"]).returncode == 0

if not git_lfs_exists:
    print("Git lfs is not installed")
    exit(1)

subprocess.run(["git", "fetch", "origin", f"{BRANCH}:{BRANCH}"], check=True)
wheels = [
    wheel.split(" - ")[1].split("/")[-1]
    for wheel in subprocess.check_output(
        ["git", "lfs", "ls-files", f"origin/{BRANCH}", "-I", f"{wheels_src}"],
        text=True,
    ).splitlines()
    if wheel.endswith(".whl")
]

supported_tags = set(sys_tags())
compatible_wheel = None
for wheel in wheels:
    file_tags = parse_wheel_filename(wheel)[3]
    if any(tag in supported_tags for tag in file_tags):
        compatible_wheel = wheel
        break


if compatible_wheel is None:
    print("No opencv wheel was found for your system.")
    exit(1)

subprocess.run(
    [
        "git",
        "lfs",
        "fetch",
        "origin",
        BRANCH,
        f'--include="console/wheels/{compatible_wheel}"',
        '--exclude="*"',
    ],
    check=True,
)
subprocess.run(
    [
        "git",
        "archive",
        BRANCH,
        f"console/wheels/{compatible_wheel}",
        "-o",
        f"{project_root}/.tmp/opencv.tar",
    ],
    check=True,
    cwd=repo_root,
)
subprocess.run(
    [
        "tar",
        "-xf",
        f"{project_root / '.tmp' / 'opencv.tar'}",
        "-C",
        f"{wheels_dir}",
        "--strip-components=2",
    ],
    check=True,
)
shutil.rmtree(tmp_dir)
wheel = (wheels_dir / compatible_wheel).resolve()
