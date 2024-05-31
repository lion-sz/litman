import pathlib
import logging
import shutil
from typing import Optional

from box import Box

from alexandria.db_connector import DB

logger = logging.getLogger(__name__)


class File:

    file_id: int | None
    path: pathlib.Path

    _insert_file = "INSERT INTO files (path) VALUES (?)"

    def __init__(self, file_id: Optional[int], path: pathlib.Path):
        self.file_id = file_id
        self.path = path

    def save(self, config: Box, db: DB) -> int:
        if self.file_id is not None:
            logger.error(f"File {self.path} already saved")
            return
        # Copy the file to the library.
        target_path = config.files.file_storage_path / self.path.name
        shutil.copy(self.path, target_path)
        self.path = target_path
        db.cursor.execute(self._insert_file, (str(self.path),))
        self.file_id = db.cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
        return self.file_id

    @classmethod
    def from_db(cls, file):
        return cls(*file)
