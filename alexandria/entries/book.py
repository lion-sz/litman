import logging
from typing import Any, Optional

import bibtexparser.model

from alexandria.db_connector import DB
from alexandria.entries.entry import Entry

logger = logging.getLogger(__name__)


class Book(Entry):

    _type_field_names = ["publisher", "version"]

    publisher: Optional[str]
    version: Optional[str]

    _insert_type = "INSERT INTO books (entry_id, publisher, version) VALUES (?, ?, ?)"
    _update_type = "UPDATE books SET publisher = ?, version = ? WHERE entry_id = ?"
    _load_type = "SELECT publisher, version FROM books WHERE entry_id = ?"

    def __init__(
        self,
        entry_args: tuple[Any],
        publisher: Optional[str] = None,
        version: Optional[str] = None,
    ):
        super().__init__(*entry_args)
        self.publisher = publisher
        self.version = version

    @classmethod
    def _parse_bibtex(cls, entry_data: tuple, bib: bibtexparser.model.Entry):
        publisher = bib["publisher"] if "publisher" in bib else None
        version = bib["version"] if "version" in bib else None
        return cls(entry_data, publisher, version)
