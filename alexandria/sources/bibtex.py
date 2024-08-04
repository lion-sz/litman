import logging
import pathlib
from typing import Optional

import bibtexparser
from box import Box

from alexandria.db_connector import DB
from alexandria.entries import Entry, bibtex_mapping
from alexandria.file import File
from alexandria.author import Author


logger = logging.getLogger(__name__)


def parse_entry(
    config: Box,
    db: DB,
    bib_entry: bibtexparser.model.Entry,
    import_root: pathlib.Path,
) -> Optional[Entry]:
    entry_type = bibtex_mapping.get(bib_entry["ENTRYTYPE"], None)
    if entry_type is None:
        logger.warning(
            f"Bibtex type '{bib_entry.entry_type}' of entry '{bib_entry.key}' not supported",
        )
        return None
    try:
        parsed = Entry.parse_bibtex(bib_entry)
        # Check if the entry already exists
        if Entry.key_exists(db, parsed.key) is not None:
            logger.info(f"Entry '{parsed.key}' already exists. Skipping")
            return None
        else:
            parsed.save(db)
        # Parse the authors
        if "author" in bib_entry:
            authors = Author.parse_authors(bib_entry["author"])
            for author in authors:
                author.save(db)
                parsed.attach_author(db, author)
        if "file" in bib_entry:
            if import_root is None:
                raise Exception("Cannot import file without a library root.")
            # The first files is assumed to be the main file.
            # This block might be jabref specific.
            for i, file_str in enumerate(bib_entry["file"].split(";")):
                desc, path, type = file_str.split(":", 2)
                file = File(
                    None,
                    path=import_root / path,
                    filetype=type.lower(),
                    default_open=i == 0,
                )
                file.save(config, db)
                parsed.attach_file(db, file)
        if "abstract" in bib_entry:
            parsed.add_abstract(db, bib_entry["abstract"])
        db.connection.commit()
        logger.debug(f"Saved paper '{parsed.key}'.")
        return parsed
    except Exception as err:
        logger.error(f"Insertion failed for paper '{bib_entry.key}'.")
        logger.exception(err)
        return None


def import_library(
    config: Box,
    db: DB,
    library_root: pathlib.Path | None,
    bib_file: pathlib.Path = None,
    bib_string: str = None,
) -> list[Entry]:
    if int(bib_file is None) + int(bib_string is None) != 1:
        logger.error("Exactly one of bibfile or bibstring must be provided")
        raise Exception("Exactly one of bibfile or bibstring must be provided")
    if bib_file:
        library = bibtexparser.parse_file(bib_file)
    else:
        library = bibtexparser.parse_string(bib_string)
    entries = []
    for entry in library.entries:
        parsed = parse_entry(config, db, entry, library_root)
        if parsed is not None:
            entries.append(parsed)
    return entries


def export_library(db: DB, keys: list[str]) -> str:
    library = bibtexparser.Library()
    for key in keys:
        entry = Entry.load(db, key)
        if entry is None:
            logger.warning(f"Entry '{key}' not found.")
            continue
        bib_entry = entry.to_bibtex_entry()
        library.add(bib_entry)
    return bibtexparser.write_string(library)
