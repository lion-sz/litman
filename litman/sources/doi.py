import bibtexparser
import urllib3

from box import Box

from litman.entries.entry import Entry
from litman.db_connector import DB
from litman.sources.bibtex import parse_entry


DOI_URL = "https://doi.org/"


def load_doi(config: Box, db: DB, doi: str) -> Entry:
    res = urllib3.request(
        "GET", DOI_URL + doi, headers={"Accept": "application/x-bibtex"}
    )
    if res.status != 200:
        raise ValueError(f"Bad response status from doi.org: '{res.status}'.")
    bib_string = res.data.decode("utf8")
    lib = bibtexparser.parse_string(bib_string)
    if len(lib.entries) != 1:
        raise ValueError(f"Bad number of entries received: '{len(lib.entries)}'.")
    entry = parse_entry(config, db, lib.entries[0], None)
    if entry is None:
        raise ValueError("Parsing Failed")
    return entry
