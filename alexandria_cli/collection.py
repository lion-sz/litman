import pathlib
import shutil
import subprocess
from typing import Optional

import bibtexparser
import typer
from box import Box

from alexandria.collection import Collection
from alexandria import bibtex
from alexandria.db_connector import DB
from alexandria.entries.entry import Entry
from alexandria.file import File
from alexandria_cli.globals import get_globals
from alexandria_cli.app_utils import select_paper

app = typer.Typer()

@app.command()
def new(name: str, description: Optional[str] = None):
    config, db = get_globals()
    collection = Collection(None, name, description)
    try:
        collection.save(db)
        db.connection.commit()
    except Exception as err:
        print(f"Failed to create collection '{name}'")
        print(err)
        return 1
    print(f"Created collection '{collection.name}'")

@app.command()
def new(collection: str, key: str):
    config, db = get_globals()
    collection = Collection.load(db, name=collection)
    if collection is None:
        print(f"Collection '{collection}' not found")
        raise typer.Abort()
    entry = Entry.load(db, key)
    if entry is None:
        print(f"Entry '{key}' not found")
        raise typer.Abort()
    try:
        collection.attach_paper(db, entry)
        db.connection.commit()
    except Exception as err:
        print(f"Failed to attach '{key}' to '{collection}'")
        raise err

