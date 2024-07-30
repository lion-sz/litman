from typing import Optional

import bibtexparser

from alexandria.db_connector import DB
from alexandria.entries.entry import Entry


class Collection:
    id: int | None

    _field_names = ["name", "description"]

    name: str
    description: str | None

    _q_load_id = "SELECT id, name, description FROM collections WHERE id = ?"
    _q_load_name = "SELECT id, name, description FROM collections WHERE name = ?"
    _q_load_papers = "SELECT entry_id FROM collection_cw where collection_id = ?"
    _q_insert = """INSERT INTO collections
        (name, description, created_ts, modified_ts)
        VALUES (?, ?, unixepoch(), unixepoch())"""
    _q_update = """UPDATE collections SET
        name = ?, description = ?, modified_ts = unixepoch() WHERE id = ?"""
    _q_attach_entry = (
        "INSERT INTO collection_cw (entry_id, collection_id) VALUES (?, ?)"
    )
    _delete_collection = "DELETE FROM collections WHERE id = ?"
    _delete_links = "DELETE FROM collection_cw WHERE collection_id = ?"
    _count_entries = "SELECT COUNT(*) FROM collection_cw WHERE collection_id = ?"
    _check_entry_attached = (
        "SELECT COUNT(*) FROM collection_cw WHERE collection_id = ? AND entry_id = ?"
    )

    def __init__(self, id: int | None, name: str, description: str | None):
        self.id = id
        self.name = name
        self.description = description
        self._paper_ids = None

    @classmethod
    def load(cls, db: DB, id: Optional[int] = None, name: Optional[str] = None):
        if id is not None:
            res = db.cursor.execute(cls._q_load_id, (id,)).fetchone()
        elif name is not None:
            res = db.cursor.execute(cls._q_load_name, (name,)).fetchone()
        else:
            raise ValueError("Either id or name must be provided.")
        if res is None:
            return None
        else:
            return cls(*res)

    def save(self, db: DB):
        if self.id is None:
            db.cursor.execute(self._q_insert, (self.name, self.description))
            self.id = db.cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            db.cursor.execute(self._q_update, (self.name, self.description, self.id))
        return self.id

    def delete(self, db: DB):
        db.cursor.execute(self._delete_collection, (self.id,))
        db.cursor.execute(self._delete_links, (self.id,))

    def papers(self, db: DB) -> list[int]:
        papers = db.cursor.execute(self._q_load_papers, (self.id,)).fetchall()
        return [paper[0] for paper in papers]

    def attach_paper(self, db: DB, entry: Entry) -> Optional[int]:
        count = db.cursor.execute(
            self._check_entry_attached, (self.id, entry.entry_id)
        ).fetchone()
        if count[0] > 0:
            return -1
        db.cursor.execute(self._q_attach_entry, (entry.entry_id, self.id))
        return None

    def count_papers(self, db: DB) -> int:
        count = db.cursor.execute(self._count_entries, (self.id,)).fetchone()
        return count[0]

    def export_bibtex(self, db: DB) -> bibtexparser.Library:
        entries = self.papers(db)
        entries = [Entry.load_id(db, id) for id in entries]
        library = bibtexparser.Library([entry.export_bibtex() for entry in entries])
        return library
