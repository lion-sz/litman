import pathlib
import shutil
import subprocess
from typing import Optional

import bibtexparser
import typer

from alexandria.sources import import_library, export_library
from alexandria.entries.entry import Entry
from alexandria.file import File
from alexandria_cli.globals import get_globals
from alexandria_cli.app_utils import select_paper

app = typer.Typer()


@app.command()
def import_bibtex(bibfile: pathlib.Path, library_root: Optional[pathlib.Path] = None):
    config, db = get_globals()
    bibfile = bibfile.expanduser()
    if not bibfile.exists():
        print(f"{bibfile} does not exist")
        return 1
    if library_root is None:
        library_root = bibfile.parent
    import_library(config, db, library_root, bib_file=bibfile)


@app.command()
def view(query: str):
    # Search and display results.
    config, db = get_globals()
    paper = select_paper(db, query)
    if paper is None:
        return
    files = [f for f in paper.files(db) if f.default_open]
    if len(files) == 0:
        print(f"No file found for paper '{paper.key}'")
        return 1
    file_path = files[0].path
    target_path = config.files.tmp_storage / file_path.name
    shutil.copy(file_path, target_path)
    subprocess.Popen(["xdg-open", target_path], start_new_session=True)


@app.command()
def web(query: str):
    # Search and display results.
    config, db = get_globals()
    paper = select_paper(db, query)
    if paper is None:
        return
    subprocess.Popen(
        ["xdg-open", f"https://doi.org/{paper.doi}"],
        start_new_session=True,
    )


@app.command()
def new(file: Optional[pathlib.Path] = None):
    config, db = get_globals()
    new_path = config.files.tmp_storage / "alexandria_new.bib"
    new_path.unlink(missing_ok=True)
    subprocess.call([config.general.editor, new_path])
    entries = import_library(new_path)
    if len(entries) != 0:
        print("Import failed")
        return 1
    entry = entries[0]
    if file is not None:
        try:
            f = File(None, file, "Main", True)
            f.save(config, db)
            entry.attach_file(db, f)
            db.connection.commit()
        except Exception as err:
            print(f"Failed to attach file '{file}' to entry '{entry.key}'.")
            print(err)
            return 1


@app.command()
def attach(
    key: str,
    file_path: pathlib.Path,
    type: str = "Main",
    default_open: bool = True,
):
    config, db = get_globals()
    entry = Entry.load(key=key)
    if entry is None:
        print(f"No entry found with key '{key}'.")
        return 1
    if not file_path.exists():
        print(f"File '{file_path}' does not exist.")
        return 1
    try:
        file = File(None, file_path, type, default_open)
        file.save(config, db)
        entry.attach_file(db, file)
        db.connection.commit()
    except Exception as err:
        print(f"Failed to attach file '{file_path}' to entry '{key}'.")
        print(err)
        return 1


@app.command()
def export(key: str, target: pathlib.Path = None):
    config, db = get_globals()
    result = export_library(db, [key])
    if len(result.strip()) == 0:
        return 1
    if target is None:
        print(result)
    else:
        target.write_text(result)


@app.command()
def edit(key: str):
    config, db = get_globals()
    entry = Entry.load(db, key)
    result = export_library(db, [key])
    if len(result.strip()) == 0:
        return 1
    tmp_file = config.files.tmp_storage / f"{key}.bib"
    tmp_file.write_text(result)
    subprocess.call([config.general.editor, tmp_file])
    try:
        parsed = Entry.parse_bibtex(bibtexparser.parse_file(tmp_file).entries[0])
    except Exception:
        print("Failed parsing results")
    if parsed.type != entry.type:
        print("Entry type cannot changed.")
        return 1
    try:
        parsed.save(db)
        db.connection.commit()
    except Exception as err:
        print("Failed to update entry.")
        raise err
    return 0
