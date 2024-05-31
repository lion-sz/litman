import logging
import sqlite3
from typing import Optional, Any

from alexandria.file import File
from alexandria.entries.entry import Entry
from alexandria.db_connector import DB

logger = logging.getLogger(__name__)


class Article(Entry):
    journal: str
    volume: Optional[str]
    pages: Optional[str]

    _insert_articles = "INSERT INTO articles (entry_id, journal, volume, pages) VALUES (?, ?, ?, ?)"

    def __init__(self, entry_args: dict[str, Any], journal: str, volume: Optional[str], pages: Optional[str]):
        super().__init__(None, 1, **entry_args)
        self.journal = journal
        self.volume = volume
        self.pages = pages

    @classmethod
    def load_bibtex(cls, bib):
        entry_args = Entry._parse_bibtex(bib)
        return cls(
            entry_args=entry_args,
            journal=bib["journaltitle"] if "journaltitle" in bib else None,
            volume=bib["volume"] if "volume" in bib else None,
            pages=bib["pages"] if "pages" in bib else None,
        )

    def save(self, db: DB) -> int:
        if self.entry_id is not None:
            logger.error(f"Entry {self.key} already saved")
            return
        self.save_entry(db)
        db.cursor.execute(self._insert_articles, (self.entry_id, self.journal, self.volume, self.pages))
        return self.entry_id
