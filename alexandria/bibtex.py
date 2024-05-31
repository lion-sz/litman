import sqlite3
import pathlib
import logging
from typing import Optional

from box import Box
import bibtexparser

from alexandria.entries import Entry, EntryTypes, entry_dispatch
from alexandria.file import File
from alexandria.db_connector import DB
from alexandria.global_state import STATE


logger = logging.getLogger(__name__)

_BIBTEX_ENTRY_MAPPING = {
    "article": EntryTypes.Article,
}


def parse_entry(entry: bibtexparser.model.Entry, import_root: pathlib.Path) -> Optional[Entry]:
    db: DB = STATE["db"]
    config: Box = STATE["config"]
    entry_type = _BIBTEX_ENTRY_MAPPING.get(entry["ENTRYTYPE"], None)
    if entry_type is None:
        logger.warning(
            f"Bibtex type '{entry.entry_type}' of entry '{entry.key}' not supported",
        )
        return
    try:
        parsed = entry_dispatch[entry_type].load_bibtex(entry)
        parsed.save(db)
        if "file" in entry:
            file_path = entry["file"].replace(":PDF", "")
            if file_path.startswith(":"):
                file_path = file_path[1:]
            file = File(None, path=import_root / file_path)
            file.save(config, db)
            parsed.attach_file(db, file)
        db.connection.commit()
        logger.debug(f"Saved paper '{parsed.key}'.")
        return parsed
    except Exception as err:
        logger.error(f"Insertion failed for paper '{entry.key}'.")
        logger.exception(err)
        return

def import_bibtex(bibfile: pathlib.Path, library_root: pathlib.Path):
    library = bibtexparser.parse_file(bibfile)
    for entry in library.entries:
        parse_entry(entry, library_root)
