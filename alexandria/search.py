from typing import Optional
import itertools
import uuid

from alexandria.db_connector import DB
from alexandria.entries.entry import Entry
from alexandria.keywords import Keyword


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
        * Keywords: Must belong to any of the keywords
    """

    is_valid: bool
    _title: str | None
    _author: str | None
    _keywords: list[Keyword] | None

    def __init__(
        self,
        title: str | None = None,
        author: str | None = None,
        keywords: list[Keyword] | None = None,
    ):
        self._title = title
        self._author = author
        self._keywords = keywords
        # Check that there is at least one filter.
        self.is_valid = title or author or keywords

    def _search_authors(self, db: DB) -> list[uuid.UUID]:
        """Search for authors matching the name provided."""
        authors = self._author.split(",")
        q = "SELECT id FROM author WHERE " + " OR ".join(
            ["last_name LIKE ?"] * len(authors)
        )
        ids = db.cursor.execute(q, [f"%{a.strip()}%" for a in authors]).fetchall()
        ids = list(itertools.chain.from_iterable(ids))
        return ids

    def search(self, db: DB) -> list[tuple]:
        """This function executes the search.

        There are fundamentally two different kind of queries:
        1. If I need full text search
        2. If I filter only on keywords.

        Returns:
            tuples of id, key, and title for each entry found.
        """
        if not self.is_valid:
            raise ValueError("Search is not valid")
        # I have a number of conditions that come from link tables. These are:
        #   title (entry_fts)
        #   author (author_link)
        #   keyword (keyword_link)
        # For these I can build the subqueries and then later merge them.
        foreign_queries = []
        foreign_args = []
        if self._title:
            q = "rowid IN (SELECT rowid FROM entry_fts WHERE title MATCH ?)"
            foreign_queries.append(q)
            foreign_args.append(self._title)
        if self._author:
            author_ids = self._search_authors(db)
            q = "id IN (SELECT DISTINCT entry_id FROM author_link WHERE author_id IN ({}))".format(
                ", ".join("?" for _ in author_ids)
            )
            foreign_queries.append(q)
            foreign_args.extend(author_ids)
        if self._keywords:
            q = "id IN (SELECT DISTINCT entry_id FROM keyword_link WHERE keyword_id IN ({}))".format(
                ", ".join("?" for _ in self._keywords)
            )
            foreign_queries.append(q)
            foreign_args.extend([k.id for k in self._keywords])

        query = "SELECT id, key, title FROM entry WHERE " + " AND ".join(
            foreign_queries
        )
        args = foreign_args
        print(query, args)
        results = db.cursor.execute(query, args).fetchall()
        return results
