import logging
import enum
from typing import Optional, Any

import bibtexparser.model

from alexandria.file import File
from alexandria.db_connector import DB
from alexandria.global_state import STATE

logger = logging.getLogger(__name__)


class Entry:
    entry_id: str | None
    type: int
    key: str
    doi: Optional[str]
    title: str
    author: Optional[str]
    year: int

    _files: Optional[list[File]]

    _insert_entries = "INSERT INTO entries (type, key, doi, title, author, year) VALUES (?, ?, ?, ?, ?, ?)"
    _attach_file = "INSERT INTO file_cw (entry_id, file_id) VALUES (?, ?)"
    _load_file_key = (
        "SELECT id, type, key, doi, title, author, year FROM entries WHERE key = ?"
    )
    _load_files = """
        SELECT file_id, path from files where file_id in (
            SELECT file_id FROM file_cw WHERE entry_id = ?
        )"""

    def __init__(
        self,
        entry_id: Optional[int],
        entry_type: int,
        key: str,
        doi: Optional[str],
        title: str,
        author: Optional[str],
        year: int,
    ):
        self.entry_id = entry_id
        self.type = entry_type
        self.key = key
        self.doi = doi
        self.title = title
        self.author = author
        self.year = year
        self._files = None

    @classmethod
    def from_db(cls, entry: tuple[Any]):
        return cls(*entry)

    @classmethod
    def load(cls, key: str):
        db = STATE["db"]
        entry = db.cursor.execute(cls._load_file_key, (key,)).fetchone()
        if entry is None:
            return None
        return cls.from_db(entry)

    @staticmethod
    def _parse_bibtex(entry: bibtexparser.model.Entry):
        """Parse the global bibtex fields."""
        key = entry.key
        title = entry["title"]
        author = entry["author"]
        # Parse the year
        year = None
        if "year" in entry:
            year = entry["year"]
        elif "date" in entry:
            date = entry["date"]
            if isinstance(date, int):
                year = date
            elif isinstance(date, str):
                year = date.split("-")[0]
            else:
                logger.error(f"Failed to parse date '{date}' for paper '{key}'.")
        else:
            logger.error(f"Failed to find year for paper '{key}'.")
        if "doi" in entry:
            doi = entry["doi"]
        else:
            doi = None
        return {"key": key, "title": title, "author": author, "year": year, "doi": doi}

    @classmethod
    def load_bibtex(cls, entry):
        raise NotImplementedError("This is not allowed for the base class.")

    def save_entry(self, db: DB) -> int:
        if self.entry_id is not None:
            logger.error(f"Entry {self.key} already saved")
            return
        db.cursor.execute(
            self._insert_entries,
            (self.type, self.key, self.doi, self.title, self.author, self.year),
        )
        self.entry_id: int = db.cursor.execute("SELECT last_insert_rowid()").fetchone()[
            0
        ]
        return self.entry_id

    def attach_file(self, db: DB, file: File):
        db.cursor.execute(self._attach_file, (self.entry_id, file.file_id))

    def files(self, db: DB):
        if self._files is None:
            files = db.cursor.execute(self._load_files, (self.entry_id,)).fetchall()
            self._files = [File.from_db(f) for f in files]
        return self._files
