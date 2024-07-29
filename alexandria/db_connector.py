import logging
import pathlib
import sqlite3

logger = logging.getLogger(__name__)
_build_scripts = ["entries", "entry_types", "files", "collections", "keywords"]


class DB:

    db_file: pathlib.Path
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    def __init__(self, db_file: pathlib.Path):
        self.db_file = db_file
        if self.db_file.exists():
            self.connection = sqlite3.connect(self.db_file, check_same_thread=False)
        else:
            self.connection = self._build_database()
        self.cursor = self.connection.cursor()

    def _build_database(self):
        logger.info(f"Building database at {self.db_file}")
        connection = sqlite3.connect(self.db_file)
        cursor = connection.cursor()
        scripts_path = pathlib.Path("./scripts/build")
        for script in _build_scripts:
            with open(scripts_path / f"{script}.sql") as f:
                cursor.executescript(f.read())
        connection.commit()
        return connection
