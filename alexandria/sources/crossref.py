"""Loading an entry from Crossref

The crossref documentation can be found here:
https://api.crossref.org/swagger-ui/index.html
"""

import urllib3
import json

from alexandria.db_connector import DB
from alexandria.entries import Entry
from alexandria.author import Author

base_url = "https://api.crossref.org/works/"
doi = "10.1257/mac.20200320"


def load_doi(db: DB, key: str, doi: str):
    req_url = base_url + doi
    print(f"Calling url '{req_url}")
    res = urllib3.request("GET", req_url)
    if res.status != 200:
        raise ValueError(f"DOI {doi} was not found.")

    parsed = json.loads(res.data.decode("utf-8"))["message"]
    if parsed == "":
        raise ValueError("parsed empty.")
    # Parse the entry
    entry = Entry.parse_crossref(key, parsed)
    entry.save(db)
    # Add authors
    for parsed_author in parsed["author"]:
        author = Author(
            None,
            parsed_author.get("given", None),
            parsed_author.get("suffix", None),
            parsed_author.get("family"),
        )
        author.save(db)
        entry.attach_author(db, author)
    # Check for an abstract.
    if "abstract" in parsed and parsed["abstract"] != "":
        entry.add_abstract(db, parsed["abstract"])
    return entry
