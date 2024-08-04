import logging
import pathlib
import sqlite3
import uuid

logger = logging.getLogger(__name__)
_build_scripts = [
    "entries",
    "entry_types",
    "files",
    "collections",
    "keywords",
    "author",
]


def conv(b):
    print("converter: ", b, type(b))
    return uuid.UUID(bytes=b)


sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes)
sqlite3.register_converter("uuid", lambda b: uuid.UUID(bytes=b))
# sqlite3.register_converter("uuid", conv)


class DB:
    db_file: pathlib.Path
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    def __init__(self, db_file: pathlib.Path):
        self.db_file = db_file
        build = not self.db_file.exists()
        self.connection = sqlite3.connect(
            self.db_file,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self.cursor = self.connection.cursor()
        if build:
            self._build_database()

    def _build_database(self):
        logger.info(f"Building database at {self.db_file}")
        scripts_path = pathlib.Path("./scripts/build")
        for script in _build_scripts:
            with open(scripts_path / f"{script}.sql") as f:
                self.cursor.executescript(f.read())
        self.connection.commit()
        return
