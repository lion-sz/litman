import logging
import pathlib
import shutil
from typing import Optional

from box import Box

from alexandria.db_connector import DB
from alexandria.enums import FileType

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

    file_id: int | None
    path: pathlib.Path
    type: FileType
    default_open: bool

    _load_id = """SELECT path, type, default_open FROM files WHERE file_id = ?"""
    _insert_file = """INSERT INTO files
        (path, type, default_open, created_ts, modified_ts)
        VALUES (?, ?, ?, unixepoch(), unixepoch())"""

    def __init__(
        self,
        file_id: Optional[int],
        path: pathlib.Path | str,
        filetype: str | int | FileType,
        default_open: bool | int,
    ):
        self.file_id = file_id
        self.path = path if isinstance(path, pathlib.Path) else pathlib.Path(path)
        if isinstance(filetype, str):
            filetype = _map_to_file_type(filetype)
        elif isinstance(filetype, int):
            filetype = FileType(filetype)
        self.type = filetype
        self.default_open = bool(default_open)

    @classmethod
    def load(cls, db: DB, file_id: int) -> "File":
        file_data = db.cursor.execute(cls._load_id, (file_id,)).fetchone()
        if len(file_data) == 0:
            raise Exception(f"File with id '{file_id}' not found")
        return cls(file_id, *file_data)

    def save(self, config: Box, db: DB) -> int:
        if self.file_id is not None:
            logger.error(f"File {self.path} already saved")
            return
        # Copy the file to the library.
        if self.path.parent != config.files.file_storage_path:
            target_path = config.files.file_storage_path / self.path.name
            shutil.copy(self.path, target_path)
            self.path = target_path
        db.cursor.execute(
            self._insert_file, (str(self.path), self.type.value, int(self.default_open))
        )
        self.file_id = db.cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
        return self.file_id

    @classmethod
    def from_db(cls, file):
        return cls(*file)

    @property
    def name(self):
        return self.path.name
