import logging
from typing import Any, Optional

import bibtexparser.model

from alexandria.db_connector import DB
from alexandria.entries.entry import Entry

logger = logging.getLogger(__name__)


class Article(Entry):

    _type_field_names = ["journal", "volume", "pages"]

    journal: str
    volume: Optional[str]
    pages: Optional[str]

    _insert_articles = (
        "INSERT INTO articles (entry_id, journal, volume, pages) VALUES (?, ?, ?, ?)"
    )
    _update_articles = (
        "UPDATE articles SET journal = ?, volume = ?, pages = ? WHERE entry_id = ?"
    )
    _load_article = "SELECT journal, volume, pages FROM articles WHERE entry_id = ?"

    def __init__(
        self,
        entry_args: dict[str, Any],
        journal: str,
        volume: Optional[str],
        pages: Optional[str],
    ):
        super().__init__(*entry_args)
        self.journal = journal
        self.volume = volume
        self.pages = pages

    @property
    def _type_fields(self):
        return tuple(getattr(self, f) for f in self._type_field_names)

    @property
    def _type_field_dict(self):
        return {f: getattr(self, f) for f in self._type_field_names}

    @classmethod
    def _load(cls, db, entry_data: tuple):
        entry_id = entry_data[0]
        article_data = db.cursor.execute(cls._load_article, (entry_id,)).fetchone()
        return cls(entry_data, *article_data)

    def _save(self, db: DB, update: bool = False):
        if update:
            db.cursor.execute(self._update_articles, self._type_fields + self.entry_id)
        else:
            db.cursor.execute(
                self._insert_articles, (self.entry_id,) + self._type_fields
            )
        return self.entry_id

    @classmethod
    def _parse_bibtex(cls, entry_data: tuple, bib: bibtexparser.model.Entry):
        journal = bib["journaltitle"] if "journaltitle" in bib else None
        volume = bib["volume"] if "volume" in bib else None
        pages = bib["pages"] if "pages" in bib else None
        return cls(entry_data, journal, volume, pages)
