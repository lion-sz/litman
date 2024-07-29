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

    _insert_type = (
        "INSERT INTO articles (entry_id, journal, volume, pages) VALUES (?, ?, ?, ?)"
    )
    _update_type = (
        "UPDATE articles SET journal = ?, volume = ?, pages = ? WHERE entry_id = ?"
    )
    _load_type = "SELECT journal, volume, pages FROM articles WHERE entry_id = ?"

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

    @classmethod
    def _parse_bibtex(cls, entry_data: tuple, bib: bibtexparser.model.Entry):
        journal = bib["journaltitle"] if "journaltitle" in bib else None
        volume = bib["volume"] if "volume" in bib else None
        pages = bib["pages"] if "pages" in bib else None
        return cls(entry_data, journal, volume, pages)
