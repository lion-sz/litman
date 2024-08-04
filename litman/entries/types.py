import logging
import typing
from typing import Optional, Any

import bibtexparser.model

from litman.entries.entry import Entry

logger = logging.getLogger(__name__)


class Article(Entry):
    _type_table = "article"
    _type_names = ["journal", "volume", "number", "pages", "month"]

    journal: str
    volume: Optional[str]
    number: Optional[str]
    pages: Optional[str]
    month: Optional[str]

    def __init__(
        self,
        entry_args: tuple | list,
        journal: str,
        volume: Optional[str],
        number: Optional[str],
        pages: Optional[str],
        month: Optional[str],
    ):
        super().__init__(*entry_args)
        self.journal = journal
        self.volume = volume
        self.number = number
        self.pages = pages
        self.month = month

    @classmethod
    def _parse_bibtex(cls, entry_data: tuple, bib: bibtexparser.model.Entry):
        journal = bib["journaltitle"] if "journaltitle" in bib else None
        volume = bib["volume"] if "volume" in bib else None
        number = bib["number"] if "number" in bib else None
        pages = bib["pages"] if "pages" in bib else None
        month = bib["month"] if "month" in bib else None
        return cls(entry_data, journal, volume, number, pages, month)

    @classmethod
    def _parse_crossref(cls, entry_data: tuple, entry: dict):
        journal = entry.get("container-title", [None])[0]
        volume = entry.get("volume", None)
        page = entry.get("page", None)
        return cls(entry_data, journal, volume, page)


class Book(Entry):
    _type_table = "book"
    _type_names = ["publisher", "address", "edition"]

    publisher: Optional[str]
    address: Optional[str]
    edition: Optional[str]

    def __init__(
        self,
        entry_args: tuple[Any],
        publisher: Optional[str] = None,
        address: Optional[str] = None,
        edition: Optional[str] = None,
    ):
        super().__init__(*entry_args)
        self.publisher = publisher
        self.address = address
        self.edition = edition

    @classmethod
    def _parse_bibtex(cls, entry_data: tuple, bib: bibtexparser.model.Entry):
        publisher = bib["publisher"] if "publisher" in bib else None
        address = bib["address"] if "address" in bib else None
        edition = bib["edition"] if "edition" in bib else None
        return cls(entry_data, publisher, address, edition)

    @classmethod
    def _parse_crossref(cls, entry_data: tuple, entry: dict) -> typing.Self:
        raise NotImplementedError("parse crossref not implemented for Books.")


class InProceedings(Entry):
    _type_table = "inProceedings"
    _type_names = [
        "booktitle",
        "editor",
        "volume",
        "number",
        "series",
        "pages",
        "address",
        "month",
        "organization",
        "publisher",
    ]

    booktitle: str | None
    editor: str | None
    volume: str | None
    number: str | None
    series: str | None
    pages: str | None
    address: str | None
    month: int | None
    organization: str | None
    publisher: str | None

    def __init__(
        self,
        entry_args: tuple | list,
        booktitle: str | None,
        editor: str | None,
        volume: str | None,
        number: str | None,
        series: str | None,
        pages: str | None,
        address: str | None,
        month: int | str | None,
        organization: str | None,
        publisher: str | None,
    ):
        super().__init__(*entry_args)
        self.booktitle = booktitle
        self.editor = editor
        self.number = number
        self.volume = volume
        self.series = series
        self.pages = pages
        self.address = address
        if isinstance(month, str):
            self.month = int(month)
        else:
            self.month = month
        self.organization = organization
        self.publisher = publisher

    @classmethod
    def _parse_bibtex(cls, entry_data: tuple, bib: bibtexparser.model.Entry):
        data = list(bib[k] if k in bib else None for k in cls._type_names)
        return cls(entry_data, *data)

    @classmethod
    def _parse_crossref(cls, entry_data: tuple, entry: dict):
        raise NotImplementedError("parse crossref not implemented for InProceedings.")
