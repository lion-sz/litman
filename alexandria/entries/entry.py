import logging
import typing
from typing import Any, Optional

import bibtexparser.model

from alexandria import entries
from alexandria.db_connector import DB
from alexandria.enums import EntryTypes
from alexandria.file import File
from alexandria.keywords import Keyword
from alexandria.author import Author

logger = logging.getLogger(__name__)


class Entry:
    entry_id: int | None
    type: EntryTypes

    _field_names = ["key", "doi", "title", "author", "year"]
    _type_field_names: list[str]  # This must be defined in the subclass

    key: str
    doi: Optional[str]
    title: str
    author: Optional[str]
    year: int

    _files: Optional[list[File]]

    _insert_entries = """INSERT INTO entries
        (type, key, doi, title, author, year, created_ts, modified_ts)
        VALUES (?, ?, ?, ?, ?, ?, unixepoch(), unixepoch())"""
    _update_entries = """UPDATE entries SET
        key = ?, doi = ?, title = ?, author = ?, year = ?, modified_ts = unixepoch()
        WHERE id = ?"""
    _fetch_id = (
        "SELECT id, type, key, doi, title, author, year from entries WHERE id = ?"
    )
    _attach_file = "INSERT INTO file_cw (entry_id, file_id) VALUES (?, ?)"
    _load_file_key = (
        "SELECT id, type, key, doi, title, author, year FROM entries WHERE key = ?"
    )
    _load_files = """
        SELECT file_id, path, type, default_open from files where file_id in (
            SELECT file_id FROM file_cw WHERE entry_id = ?
        )"""
    _load_id = "SELECT id FROM entries WHERE key = ?"
    _load_keywords = """
        SELECT id, name FROM keywords WHERE id IN (
            SELECT keyword_id FROM keywords_cw WHERE entry_id = ?
        )"""
    _attach_keyword = "INSERT INTO keywords_cw (keyword_id, entry_id) VALUES (?, ?)"
    _delete_keyword = "DELETE FROM keywords_cw WHERE entry_id = ? AND keyword_id = ?"
    _list_authors = "SELECT author_id FROM author_link WHERE entry_id = ?"
    _attach_author = "INSERT INTO author_link (author_id, entry_id) VALUES (?, ?)"
    _detach_author = "DELETE FROM author_link WHERE author_id = ? AND entry_id = ?"

    # These must be defined by each class.
    _insert_type: str
    _update_type: str
    _load_type: str

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
        self.type = EntryTypes(entry_type)
        self.key = key
        self.doi = doi
        self.title = title
        self.author = author
        self.year = year
        self._files = None

    @property
    def entry_fields(self) -> tuple[Any]:
        return tuple(getattr(self, f) for f in self._field_names)

    @property
    def entry_field_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self._field_names}

    @property
    def _type_fields(self):
        return tuple(getattr(self, f) for f in self._type_field_names)

    @property
    def _type_field_dict(self):
        return {f: getattr(self, f) for f in self._type_field_names}

    @classmethod
    def _type_load(cls, db, entry_data: tuple):
        entry_id = entry_data[0]
        article_data = db.cursor.execute(cls._load_type, (entry_id,)).fetchone()
        return cls(entry_data, *article_data)

    @property
    def fields(self) -> tuple[Any]:
        return self.entry_fields + self._type_fields

    @property
    def field_dict(self) -> dict[str, Any]:
        return self.entry_field_dict | self._type_field_dict

    @classmethod
    def from_db(cls, entry: tuple[Any]):
        return cls(*entry)

    @classmethod
    def load(cls, *args, **kwargs):
        return cls.load_key(*args, **kwargs)

    @classmethod
    def load_key(cls, db: DB, key: str, barebones: bool = False):
        entry_data = db.cursor.execute(cls._load_file_key, (key,)).fetchone()
        if entry_data is None:
            return None
        entry_type = entries.entry_dispatch_int[entry_data[1]]
        if barebones:
            entry = Entry(*entry_data)
        else:
            entry = entry_type._type_load(db, entry_data)
        return entry

    @classmethod
    def load_id(cls, db: DB, id: int, barebones: bool = False):
        entry_data = db.cursor.execute(cls._fetch_id, (id,)).fetchone()
        if entry_data is None:
            return None
        entry_type = entries.entry_dispatch_int[entry_data[1]]
        if barebones:
            entry = Entry(*entry_data)
        else:
            entry = entry_type._type_load(db, entry_data)
        return entry

    def save(self, db: DB) -> int:
        # Check if an id already exists.
        if self.entry_id is None:
            self.entry_id = db.cursor.execute(self._load_id, (self.key,)).fetchone()
        if self.entry_id is not None:
            db.cursor.execute(
                self._update_entries,
                self.entry_fields + (self.entry_id,),
            )
            db.cursor.execute(self._update_type, self._type_fields + (self.entry_id,))
        else:
            db.cursor.execute(
                self._insert_entries, (self.type.value,) + self.entry_fields
            )
            self.entry_id = db.cursor.lastrowid
            db.cursor.execute(self._insert_type, (self.entry_id,) + self._type_fields)
        return self.entry_id

    @classmethod
    def exists(cls, db: DB, key: str):
        return db.cursor.execute(cls._load_id, (key,)).fetchone() is not None

    def attach_file(self, db: DB, file: File):
        db.cursor.execute(self._attach_file, (self.entry_id, file.file_id))

    def files(self, db: DB) -> list[File]:
        if self._files is None:
            files = db.cursor.execute(self._load_files, (self.entry_id,)).fetchall()
            self._files = [File.from_db(f) for f in files]
        return self._files

    def keywords(self, db: DB) -> list[str]:
        keywords = db.cursor.execute(self._load_keywords, (self.entry_id,)).fetchall()
        return [Keyword(*k) for k in keywords]

    def add_keyword(self, db: DB, keyword):
        db.cursor.execute(self._attach_keyword, (keyword.id, self.entry_id))

    def delete_keyword(self, db: DB, keyword: Keyword | int):
        if isinstance(keyword, Keyword):
            keyword_id = keyword.id
        elif isinstance(keyword, int):
            keyword_id = keyword
        else:
            raise ValueError("keyword must be a keyword or a keyword id.")
        db.cursor.execute(self._delete_keyword, (self.entry_id, keyword_id))

    def authors(self, db: DB) -> list[Author]:
        author_ids = db.cursor.execute(self._list_authors, (self.entry_id,)).fetchall()
        authors = [Author.load_id(db, a[0]) for a in author_ids]
        return authors

    def attach_author(self, db: DB, author: Author) -> None:
        db.cursor.execute(self._attach_author, (author.id, self.entry_id))
        return

    def detach_author(self, db: DB, author: Author) -> None:
        db.cursor.execute(self._detach_author, (author.id, self.entry_id))
        return

    @staticmethod
    def parse_bibtex(bib_entry: bibtexparser.model.Entry):
        """Parse the global bibtex fields."""
        key = bib_entry.key
        title = bib_entry["title"]
        author = bib_entry["author"]
        # Parse the year
        year = None
        if "year" in bib_entry:
            year = bib_entry["year"]
        elif "date" in bib_entry:
            date = bib_entry["date"]
            if isinstance(date, int):
                year = date
            elif isinstance(date, str):
                year = date.split("-")[0]
            else:
                logger.error(f"Failed to parse date '{date}' for paper '{key}'.")
        else:
            logger.error(f"Failed to find year for paper '{key}'.")
        if "doi" in bib_entry:
            doi = bib_entry["doi"]
        else:
            doi = None
        # Get the type.
        entry_type = entries.bibtex_mapping.get(bib_entry.entry_type, None)
        if entry_type is None:
            raise ValueError("Entry type not supported")
        entry = entries.entry_dispatch[entry_type]._parse_bibtex(
            (None, entry_type.value, key, doi, title, author, year),
            bib_entry,
        )
        return entry

    def export_bibtex(self) -> bibtexparser.model.Entry:
        fields = [bibtexparser.model.Field(k, v) for k, v in self.field_dict.items()]
        entry = bibtexparser.model.Entry(
            entries.rev_bibtex_mapping[self.type],
            self.key,
            fields,
        )
        return entry

    def update_entry(self, new_entry: typing.Self) -> None:
        """Update an existing entry with values from a new entry.

        Files, keywords and collections are kept as is.
        The authors string is updated, but handling the author objects
        is left to the calling function.
        """
        if self.type != new_entry.type:
            raise ValueError("Cannot update entry with different type.")
        for field, value in new_entry.field_dict.items():
            setattr(self, field, value)
        return
