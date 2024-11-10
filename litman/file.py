import logging
import typing
import uuid
import pathlib
import shutil
from typing import Optional

from box import Box

from litman.db_connector import DB
from litman.enums import FileType

logger = logging.getLogger(__name__)


def _map_to_file_type(filetype: str) -> FileType:
    try:
        return FileType[filetype]
    except KeyError:
        pass
    if filetype == "pdf":
        return FileType.PDF
    raise KeyError(f"FileType {filetype} not known.")


class File:
    id: uuid.UUID | None
    path: pathlib.Path
    type: FileType
    default_open: bool

    _saved: bool
    _load_id = "SELECT id, path, type, default_open FROM file WHERE id = ?"
    _insert_file = "INSERT INTO file (id, path, type, default_open) VALUES (?, ?, ?, ?)"
    _delete_file = "DELETE FROM file WHERE id = ?"
    _delete_file_ln = "DELETE FROM file_link where file_id = ?"

    def __init__(
        self,
        id: Optional[uuid.UUID] | None,
        path: pathlib.Path | str,
        filetype: str | int | FileType,
        default_open: bool | int,
    ):
        self._saved = id is not None
        self.id = id if id is not None else uuid.uuid4()
        self.path = path if isinstance(path, pathlib.Path) else pathlib.Path(path)

        if isinstance(filetype, str):
            filetype = _map_to_file_type(filetype)
        elif isinstance(filetype, int):
            filetype = FileType(filetype)
        self.type = filetype
        self.default_open = bool(default_open)

    @classmethod
    def load(cls, db: DB, file_id: uuid.UUID) -> typing.Self:
        file_data = db.cursor.execute(cls._load_id, (file_id,)).fetchone()
        if len(file_data) == 0:
            raise Exception(f"File with id '{file_id}' not found")
        return cls(*file_data)

    def save(self, config: Box, db: DB) -> None:
        if self._saved:
            logger.error(f"File {self.path} already saved")
            return
        # Copy the file to the library.
        if self.path.parent != config.files.file_storage_path:
            target_path = config.files.file_storage_path / self.path.name
            shutil.copy(self.path, target_path)

        db.cursor.execute(
            self._insert_file,
            (self.id, str(self.path.name), self.type.value, int(self.default_open)),
        )
        return None

    def delete(self, config: Box, db: DB) -> None:
        db.cursor.execute(self._delete_file, (self.id,))
        db.cursor.execute(self._delete_file_ln, (self.id,))
        filepath = config.files.file_storage_path / self.path.name
        filepath.unlink()
        return

    @classmethod
    def from_db(cls, file):
        return cls(*file)

    @property
    def name(self):
        return self.path.name
