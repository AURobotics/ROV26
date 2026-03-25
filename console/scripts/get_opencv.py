from pathlib import Path
import shutil
import subprocess
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
import json
import hashlib

REPO = "AURobotics/ROV26"
RELEASE_TAG = "opencv-build"

project_root = Path(__file__).parent.parent.resolve()
wheels_dir = (project_root / "wheels").resolve()

if not wheels_dir.exists():
    wheels_dir.mkdir()

if shutil.which("gh") is None:
    print("Github CLI is not installed")
    exit(1)

releases_response: list = json.loads(
    subprocess.run(
        ["gh", "api", f"repos/{REPO}/releases"], check=True, capture_output=True
    ).stdout
)
releases: list[dict] = []
for release in releases_response:
    release: dict
    tag_name: str = release["tag_name"]
    if tag_name.startswith(RELEASE_TAG):
        releases.append(release)


if len(releases) == 0:
    print("Could not find any releases.")
    exit(1)


release = sorted(releases, key=lambda x: x["published_at"], reverse=True)[0]
wheels: dict[str, str] = {asset["name"]: asset["digest"].split(":")[1] for asset in release["assets"]}

supported_tags = set(sys_tags())
compatible_wheel = None
for wheel in wheels.keys():
    file_tags = parse_wheel_filename(wheel)[3]
    if any(tag in supported_tags for tag in file_tags):
        compatible_wheel = wheel
        break


if compatible_wheel is None:
    print("No opencv wheel was found for your system.")
    exit(1)

hash = wheels[compatible_wheel]
existing_wheel = (wheels_dir / compatible_wheel).resolve()
to_remove_existing = False
if existing_wheel.exists():
    hasher = hashlib.sha256()
    file_bytes = existing_wheel.read_bytes()
    digest = hashlib.sha256(file_bytes).hexdigest()
    if digest == wheels[compatible_wheel]:
        print("The most up-to-date wheel already exists.")
        exit(0)
    else:
        to_remove_existing = True

subprocess.run(
    [
        "gh",
        "release",
        "download",
        f"{release['tag_name']}",
        "--repo",
        f"{REPO}",
        "--pattern",
        f"{compatible_wheel}",
        "--dir",
        f"{wheels_dir}",
    ],
    check=True,
)

if to_remove_existing:
    existing_wheel.unlink()