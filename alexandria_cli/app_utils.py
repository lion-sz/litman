from typing import Optional

from alexandria.db_connector import DB
from alexandria.entries.entry import Entry
from alexandria.search import Search


def select_paper(db: DB, query: str) -> Optional[Entry]:
    search = Search(db, query)
    if len(search.result) == 0:
        print("No results found.")
        return
    if len(search.result) > 1:
        for i, result in enumerate(search.result):
            print(f"{str(i + 1).ljust(2)}: {result.key.ljust(20)} - {result.title}")
        print(f"1-{len(search.result)} to select a paper")
        selection = int(input())
        paper = search.result[selection - 1]
    else:
        paper = search.result[0]
    return paper
