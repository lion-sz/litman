import sqlite3
import pathlib
import logging


logger = logging.getLogger(__name__)
_tables = ["entries", "articles", "files", "file_cw"]


class DB:

    db_file: pathlib.Path
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    def __init__(self, db_file: pathlib.Path):
        self.db_file = db_file
        if self.db_file.exists():
            self.connection = sqlite3.connect(self.db_file)
        else:
            self.connection = self._build_database()
        self.cursor = self.connection.cursor()

    def _build_database(self):
        logger.info(f"Building database at {self.db_file}")
        connection = sqlite3.connect(self.db_file)
        cursor = connection.cursor()
        scripts_path = pathlib.Path("./scripts/build")
        for table in _tables:
            with open(scripts_path / f"{table}.sql") as f:
                cursor.executescript(f.read())
        connection.commit()
        return connection


