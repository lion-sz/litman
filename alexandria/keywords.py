import logging
from typing import Any, Optional

import bibtexparser.model

from alexandria import entries
from alexandria.db_connector import DB
from alexandria.file import File

logger = logging.getLogger(__name__)


class Keyword:

    id: int
    name: str

    _insert_keyword = "INSERT INTO keywords (name) VALUES (?)"
    _list_keywords = "SELECT id, name FROM keywords"
    _fetch_name = "SELECT id, name FROM keywords WHERE name = ?"
    _load_id = "SELECT id, name FROM keywords WHERE id = ?"
    _search = "SELECT id, name FROM keywords WHERE name LIKE ?"
    _fetch_all = "SELECT id, name FROM keywords"

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

    def list_keywords(self, db: DB):
        keywords = db.cursor.execute(self._list_keywords).fetchall()
        return [Keyword(*k) for k in keywords]

    @classmethod
    def create(cls, db: DB, name: str):
        db.cursor.execute(cls._insert_keyword, (name,))
        id = db.cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
        return cls(id, name)

    @classmethod
    def from_name(cls, db: DB, name: str):
        """Return a keyword with a given name.

        If this does not exist, create it.
        """
        res = db.cursor.execute(cls._fetch_name, (name,)).fetchone()
        # Does not exist, save and commit.
        if res is None:
            keyword = cls.create(db, name)
            db.connection.commit()
            return keyword
        return cls(*res)

    @classmethod
    def load_id(cls, db: DB, id: int):
        res = db.cursor.execute(cls._load_id, (id,)).fetchone()
        return cls(*res)

    def __eq__(self, other):
        if isinstance(other, Keyword):
            return self.id == other.id
        elif isinstance(other, int):
            return self.id == other
        else:
            raise Exception(f"Tried comparing Keyword to '{type(other)}'")

    @classmethod
    def search_keywords(cls, db: DB, search_term: str) -> list:
        if search_term == "":
            results = db.cursor.execute(cls._fetch_all).fetchall()
        else:
            results = db.cursor.execute(cls._search, (f"%{search_term}%",)).fetchall()
        return [Keyword(*k) for k in results]
