import logging
import uuid
import typing
import warnings
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
    id: uuid.UUID
    type: EntryTypes

    _names = ["key", "doi", "title", "year", "url"]
    _type_names: list[str]  # This must be defined in the subclass
    _type_table: str

    key: str
    doi: Optional[str]
    title: str
    author: Optional[str]
    year: int

    _saved: bool  # Specifies if this entry is already saved.
    _files: Optional[list[File]]

    @property
    def _q_names(self) -> str:
        return ", ".join(self._names)

    @property
    def _q_inserts(self) -> str:
        return ", ".join(self._names)

    _fetch_id = "SELECT id, type, key, doi, title, year, url from entries WHERE id = ?"
    _attach_file = "INSERT INTO file_cw (entry_id, file_id) VALUES (?, ?)"
    _load_file_key = (
        "SELECT id, type, key, doi, title, year, url FROM entries WHERE key = ?"
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
    _add_abstract_q = "INSERT INTO abstract (entry_id, abstract) VALUES (?, ?)"

    # These must be defined by each class.
    _insert_type: str
    _update_type: str
    _load_type: str

    _insert_type_q: str
    _update_type_q: str
    _load_type_q: str

    def __init__(
        self,
        id: Optional[uuid.UUID],
        entry_type: int,
        key: str,
        doi: Optional[str],
        title: str,
        year: int,
        url: str | None,
    ):
        if id is not None:
            self.id = id
            self._saved = True
        else:
            self.id = uuid.uuid4()
            self._saved = False
        self.type = EntryTypes(entry_type)
        self.key = key
        self.doi = doi
        self.title = title
        self.year = year
        self.url = url
        self._files = None

    @property
    def entry_fields(self) -> tuple[Any]:
        return tuple(getattr(self, f) for f in self._names)

    @property
    def entry_field_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self._names}

    @property
    def _type_fields(self):
        return tuple(getattr(self, f) for f in self._type_names)

    @property
    def _type_field_dict(self):
        return {f: getattr(self, f) for f in self._type_names}

    @property
    def fields(self) -> tuple[Any]:
        return self.entry_fields + self._type_fields

    @property
    def field_dict(self) -> dict[str, Any]:
        return self.entry_field_dict | self._type_field_dict

    @classmethod
    def from_db(cls, entry: tuple[Any]):
        return cls(*entry)

    ###
    ### Load and Save Methods
    ###

    @classmethod
    def key_exists(cls, db: DB, key: str) -> uuid.UUID | None:
        q = "SELECT id FROM entry WHERE key = ?"
        res = db.cursor.execute(q, (key,)).fetchone()
        if res is None:
            return None
        else:
            return res[0]

    @classmethod
    def load_id(cls, db: DB, id: uuid.UUID, barebones: bool = False) -> typing.Self:
        """Load an entry based on the ID."""
        q = f"SELECT id, type, {', '.join(cls._names)} FROM entry WHERE id = ?"
        entry_data = db.cursor.execute(q, (id,)).fetchone()
        if entry_data is None:
            return None
        if barebones:
            entry = cls(*entry_data)
        else:
            entry_type = entries.entry_dispatch_int[entry_data[1]]
            entry = entry_type._type_load(db, *entry_data)
        return entry

    @classmethod
    def load_key(cls, db: DB, key: str, barebones: bool = False) -> typing.Self | None:
        q = "SELECT id FROM entry WHERE key = ?"
        id = db.cursor.execute(q, (key,)).fetchone()
        if id is None:
            return None
        return cls.load_id(db, id[0], barebones=barebones)

    @classmethod
    def load(cls, *args, **kwargs):
        warnings.deprecated("bare load method is depreceated.")
        return cls.load_key(*args, **kwargs)

    @classmethod
    def _type_load(cls, db, entry_id, *entry_data):
        type_q = (
            f"SELECT {', '.join(cls._type_names)} FROM {cls._type_table} WHERE id = ?"
        )
        type_data = db.cursor.execute(type_q, (entry_id,)).fetchone()
        if type_data is None:
            raise ValueError("No type data found.")
        return cls((entry_id,) + entry_data, *type_data)

    def save(self, db: DB, overwrite_existing_key: bool = True) -> None:
        insert_q = f"""INSERT INTO entry (id, type, {", ".join(self._names)})
            VALUES (?, ?, {", ".join(["?"] * len(self._names))})"""
        type_insert_q = f"""INSERT INTO {self._type_table} (id, {", ".join(self._type_names)})
            VALUES (?, {", ".join(["?"] * len(self._type_names))})"""
        update_q = f"""UPDATE entry SET {", ".join(f"{n} = ?" for n in self._names)}
            WHERE id = ?"""
        type_update_q = f"""UPDATE {self._type_table} SET {", ".join(f"{n} = ?" for n in self._type_names)}
            WHERE id = ?"""
        # Check if an id already exists.
        update = False
        if self._saved:
            update = True
        else:
            existing_id = self.key_exists(db, self.key)
            if existing_id is not None:
                if not overwrite_existing_key:
                    raise ValueError(f"Key '{self.key} exists already.")
                update = True
                self.id = existing_id
        if update:
            db.cursor.execute(update_q, self.entry_fields + (self.id,))
            db.cursor.execute(type_update_q, self._type_fields + (self.id,))
        else:
            db.cursor.execute(insert_q, (self.id, self.type.value) + self.entry_fields)
            db.cursor.execute(type_insert_q, (self.id,) + self._type_fields)
        return None

    ###
    ### Authors
    ###

    def authors(self, db: DB) -> list[Author]:
        q = "SELECT author_id FROM author_link WHERE entry_id = ?"
        author_ids = db.cursor.execute(q, (self.id,)).fetchall()
        authors = [Author.load_id(db, a[0]) for a in author_ids]
        return authors

    def attach_author(self, db: DB, author: Author) -> None:
        q = "INSERT INTO author_link (author_id, entry_id) VALUES (?, ?)"
        db.cursor.execute(q, (author.id, self.id))
        return

    def detach_author(self, db: DB, author: Author) -> None:
        q = "DELETE FROM author_link WHERE author_id = ? AND entry_id = ?"
        db.cursor.execute(q, (author.id, self.id))
        return

    ###
    ### Keywords
    ###

    def keywords(self, db: DB) -> list[str]:
        q = (
            "SELECT id, name FROM keyword WHERE id IN "
            "(SELECT keyword_id FROM keyword_link WHERE entry_id = ?)"
        )
        keywords = db.cursor.execute(q, (self.id,)).fetchall()
        return [Keyword(*k) for k in keywords]

    def add_keyword(self, db: DB, keyword) -> None:
        q = "INSERT INTO keyword_link (keyword_id, entry_id) VALUES (?, ?)"
        db.cursor.execute(q, (keyword.id, self.id))
        return

    def remove_keyword(self, db: DB, keyword: Keyword | uuid.UUID) -> None:
        if isinstance(keyword, Keyword):
            keyword_id = keyword.id
        elif isinstance(keyword, uuid.UUID):
            keyword_id = keyword
        else:
            raise ValueError("keyword must be a keyword or a keyword id.")
        q = "DELETE FROM keyword_link WHERE keyword_id = ? AND entry_id = ?"
        db.cursor.execute(q, (keyword_id, self.id))
        return

    ###
    ### Files / Abstract
    ###

    def files(self, db: DB) -> list[File]:
        if self._files is None:
            q = "SELECT file_id FROM file_link WHERE entry_id = ?"
            file_ids = db.cursor.execute(q, (self.id,)).fetchall()
            self._files = [File.load(db, f[0]) for f in file_ids]
        return self._files

    def attach_file(self, db: DB, file: File) -> None:
        q = "INSERT INTO file_link (file_id, entry_id) VALUES (?, ?)"
        db.cursor.execute(q, (file.id, self.id))
        return None

    def add_abstract(self, db: DB, abstract: str):
        q = "INSERT INTO abstract VALUES (?, ?)"
        db.cursor.execute(q, (self.id, abstract))
        return

    ###
    ### Parsing / Exporting
    ###

    @staticmethod
    def parse_bibtex(bib_entry: bibtexparser.model.Entry):
        """Parse the global bibtex fields."""
        key = bib_entry.key
        title = bib_entry["title"]
        # Parse the year
        year = None
        if "year" in bib_entry:
            year = bib_entry["year"]
            if isinstance(year, str):
                year = int(year)
        elif "date" in bib_entry:
            date = bib_entry["date"]
            if isinstance(date, int):
                year = date
            elif isinstance(date, str):
                year = int(date.split("-")[0])
            else:
                logger.error(f"Failed to parse date '{date}' for paper '{key}'.")
        else:
            logger.error(f"Failed to find year for paper '{key}'.")
        if "doi" in bib_entry:
            doi = bib_entry["doi"]
        else:
            doi = None
        if "url" in bib_entry:
            url = bib_entry["url"]
        else:
            url = None
        # Get the type.
        entry_type = entries.bibtex_mapping.get(bib_entry.entry_type, None)
        if entry_type is None:
            raise ValueError("Entry type not supported")
        entry = entries.entry_dispatch[entry_type]._parse_bibtex(
            (None, entry_type.value, key, doi, title, year, url),
            bib_entry,
        )
        return entry

    def export_bibtex(self, db: DB) -> bibtexparser.model.Entry:
        fields = [
            bibtexparser.model.Field(k, v)
            for k, v in self.field_dict.items()
            if k != "key"
        ]
        authors = " AND ".join([str(a) for a in self.authors(db)])
        fields.append(bibtexparser.model.Field("author", authors))
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
