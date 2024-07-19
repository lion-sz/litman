from typing import Optional

from alexandria.db_connector import DB
from alexandria.entries.entry import Entry


class Collection:

    id: int | None

    _field_names = ["name", "description"]

    name: str
    description: str | None

    _paper_ids: list[int] | None

    _q_load_id = "SELECT id, name, description FROM collections WHERE id = ?"
    _q_load_name = "SELECT id, name, description FROM collections WHERE name = ?"
    _q_load_papers = "SELECT entry_id FROM collection_cw where collection_id = ?"
    _q_insert = """INSERT INTO collections
        (name, description, created_ts, modified_ts)
        VALUES (?, ?, unixepoch(), unixepoch())"""
    _q_update = """UPDATE collections SET
        name = ?, description = ?, modified_ts = unixepoch() WHERE id = ?"""
    _q_attach_entry = "INSERT INTO collection_cw (entry_id, collection_id) VALUES (?, ?)"

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

    def papers(self, db: DB):
        if self._paper_ids is None:
            papers = db.cursor.execute(self._q_load_papers, (self.id,)).fetchall()
            self._paper_ids = [paper[0] for paper in papers]
        return self._paper_ids

    def attach_paper(self, db: DB, entry: Entry):
        db.cursor.execute(self._q_attach_entry, (entry.id, self.id))
