from typing import Optional


from alexandria.db_connector import DB
from alexandria.entries.entry import Entry


class Search:

    db: DB
    query: str
    result: list

    _key_exact = "SELECT id, type, key, doi, title, author, year FROM entries WHERE key = ?"
    _key_like = "SELECT id, type, key, doi, title, author, year FROM entries WHERE key LIKE ?"
    _title = """SELECT id, type, key, doi, title, author, year FROM entries WHERE id IN (
            SELECT rowid FROM entries_fts WHERE title MATCH ? ORDER BY rank
        )"""

    def __init__(self, db: DB, query: str):
        self.db = db
        self.query = query
        self.result = self.search()

    def search(self):
        # Key based searches
        key_exact = self._search_key_exact()
        if key_exact is not None:
            return [key_exact]
        key_like = self._search_key_like()
        if len(key_like) > 0:
            return key_like
        title = self._search_title()
        if len(title) > 0:
            return title
        return []

    def _search_key_exact(self) -> Optional[Entry]:
        results = self.db.cursor.execute(self._key_exact, (self.query,)).fetchall()
        if len(results) == 1:
            return Entry.from_db(results[0])
        else:
            return None

    def _search_key_like(self) -> list[Entry]:
        results = self.db.cursor.execute(self._key_like, (f"%{self.query}%",)).fetchall()
        return [Entry.from_db(result) for result in results]

    def _search_title(self):
        results = self.db.cursor.execute(self._title, (self.query,)).fetchall()
        return [Entry.from_db(result) for result in results]
