from pathlib import Path
import os
from typing import cast

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel
from PySide6.QtWidgets import QFileSystemModel


def get_base_path() -> Path:
    return Path(__file__).parent.parent.parent.parent.absolute()


def resolve(path: str | os.PathLike) -> Path:
    path = Path(path)
    if not path.is_absolute():
        base = get_base_path()
        return Path(base / path)
    else:
        return Path(path)


def temp() -> Path:
    path = resolve("./.tmp")
    if not path.exists():
        path.mkdir()
    return path


class ExecutableFilterProxy(QSortFilterProxyModel):
    def filterAcceptsRow(
        self,
        source_row: int,
        source_parent: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        model = self.sourceModel()
        if not isinstance(model, QFileSystemModel):
            return False
        index = model.index(source_row, 0, source_parent)
        if model.isDir(index):
            return True
        return model.fileInfo(index).isExecutable()