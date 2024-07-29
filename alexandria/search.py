from typing import Optional

from alexandria.db_connector import DB
from alexandria.entries.entry import Entry


class Search:

    db: DB
    query: str
    result: list

    _key_exact = (
        "SELECT id, type, key, doi, title, author, year FROM entries WHERE key = ?"
    )
    _key_like = (
        "SELECT id, type, key, doi, title, author, year FROM entries WHERE key LIKE ?"
    )
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
        results = self.db.cursor.execute(
            self._key_like, (f"%{self.query}%",)
        ).fetchall()
        return [Entry.from_db(result) for result in results]

    def _search_title(self):
        results = self.db.cursor.execute(self._title, (self.query,)).fetchall()
        return [Entry.from_db(result) for result in results]


class AdvancedSearch:
    """This class implements an advanced search with multiple filters.

    Implemented filters are:
        * Title: Token search (sqlite FTS)
        * Author: Token search (sqlite FTS)
        * Keywords: Must belong to all keywords
    """

    is_valid: bool
    _title: str | None
    _author: str | None
    _keywords: list[int] | None

    def __init__(
        self,
        title: str | None = None,
        author: str | None = None,
        keywords: list[int] | None = None,
    ):
        self._title = title
        self._author = author
        self._keywords = keywords
        # Check that there is at least one filter.
        self.is_valid = title or author or keywords

    def search(self, db: DB):
        """Search the database."""
        if not self.is_valid:
            raise ValueError("Search is not valid")
        query, args = self._build_search_query()
        print(query, args)
        results = db.cursor.execute(query, args).fetchall()
        return results

    def _build_search_query(self) -> str:
        """This function builds the search query used.

        There are fundamentally two different kind of queries:
        1. If I need full text search
        2. If I filter only on keywords.
        """
        # Build the keyword filter.
        if len(self._keywords) == 1:
            kw_query = "SELECT entry_id FROM keywords_cw WHERE keyword_id == ?"
            kw_args = [self._keywords[0].id]
        elif len(self._keywords) > 1:
            kw_query = "SELECT entry_id FROM keywords_cw GROUP BY entry_id HAVING SUM(keyword_id in ?)"
            kw_args = [[k.id for k in self._keywords]]
        else:
            kw_query = None
            kw_args = []

        # Check for fts search:
        fts_query = []
        fts_args = []
        if self._title:
            fts_query = ["title MATCH ?"]
            fts_args = [self._title]
        if self._author:
            fts_query = fts_query + ["author MATCH ?"]
            fts_args = fts_args + [self._author]

        query = "SELECT id, key, title FROM entries WHERE "
        args = []
        # If I use either fts or keywords, I need to filter based on an external table.
        # This external filtering is done were.
        if fts_query or kw_query:
            if fts_query:
                foreign_q = (
                    f"SELECT rowid FROM entries_fts WHERE {' AND '.join(fts_query)}"
                )
                foreign_q_args = fts_args
                if kw_query:
                    # If I use both fts and keywords, I need a three-level query.
                    foreign_q = foreign_q + f" AND rowid IN ({kw_query})"
                    foreign_q_args += kw_args
            else:
                foreign_q = kw_query
                foreign_q_args = kw_args
            query += f"id IN ({foreign_q})"
            args += foreign_q_args
        # Other filters are not yet implemented.
        return query, args
