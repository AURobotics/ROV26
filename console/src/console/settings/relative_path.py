import sys
from pathlib import Path
import os


def get_base_path() -> Path:
    return Path(__file__).parent.parent.parent.parent.absolute()


def resolve(path: str | os.PathLike) -> Path:
    pathstr = str(path)
    if pathstr.startswith("./"):
        base = get_base_path()
        return Path(base / pathstr[2:])
    else:
        return Path(path)
