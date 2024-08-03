from typing import Optional
import typing
import uuid

import bibtexparser

from alexandria.db_connector import DB
from alexandria.entries.entry import Entry


class Collection:
    id: uuid.UUID | None

    _field_names = ["name", "description"]

    name: str
    description: str | None

    _q_load_id = "SELECT id, name, description FROM collection WHERE id = ?"
    _q_load_name = "SELECT id, name, description FROM collection WHERE name = ?"
    _q_load_papers = "SELECT entry_id FROM collection_link where collection_id = ?"
    _q_insert = "INSERT INTO collection (id, name, description) VALUES (?, ?, ?)"
    _q_update = "UPDATE collection SET name = ?, description = ? WHERE id = ?"
    _q_attach_entry = (
        "INSERT INTO collection_link (entry_id, collection_id) VALUES (?, ?)"
    )
    _delete_collection = "DELETE FROM collection WHERE id = ?"
    _delete_links = "DELETE FROM collection_link WHERE collection_id = ?"
    _count_entries = "SELECT COUNT(*) FROM collection_link WHERE collection_id = ?"
    _check_entry_attached = (
        "SELECT COUNT(*) FROM collection_link WHERE collection_id = ? AND entry_id = ?"
    )

    def __init__(self, id: uuid.UUID | None, name: str, description: str | None):
        self.id = id
        self.name = name
        self.description = description
        self._paper_ids = None

    @classmethod
    def load(cls, db: DB, id: Optional[uuid.UUID] = None, name: Optional[str] = None):
        if id is not None:
            return cls.load_id(db, id)
        elif name is not None:
            res = db.cursor.execute(cls._q_load_name, (name,)).fetchone()
        else:
            raise ValueError("Either id or name must be provided.")
        if res is None:
            return None
        else:
            return cls(*res)

    @classmethod
    def load_id(cls, db: DB, id: uuid.UUID) -> typing.Self:
        res = db.cursor.execute(cls._q_load_id, (id,)).fetchone()
        if res is None:
            raise ValueError("Collection not found.")
        return cls(*res)

    def save(self, db: DB):
        if self.id is None:
            self.id = uuid.uuid4()
            db.cursor.execute(self._q_insert, (self.id, self.name, self.description))
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
            self._check_entry_attached, (self.id, entry.id)
        ).fetchone()
        if count[0] > 0:
            return -1
        db.cursor.execute(self._q_attach_entry, (entry.id, self.id))
        return None

    def count_papers(self, db: DB) -> int:
        count = db.cursor.execute(self._count_entries, (self.id,)).fetchone()
        return count[0]

    def export_bibtex(self, db: DB) -> bibtexparser.Library:
        entries = self.papers(db)
        entries = [Entry.load_id(db, id) for id in entries]
        library = bibtexparser.Library([entry.export_bibtex(db) for entry in entries])
        return library
