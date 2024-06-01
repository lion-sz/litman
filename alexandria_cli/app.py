import pathlib
import shutil
import subprocess
from typing import Optional

import bibtexparser
import typer
from box import Box

from alexandria import bibtex
from alexandria.db_connector import DB
from alexandria.entries.entry import Entry
from alexandria.file import File
from alexandria.global_state import STATE
from alexandria_cli.app_utils import select_paper

app = typer.Typer()


@app.callback()
def setup(
    config_path: pathlib.Path = "~/.config/alexandria.toml",
    clean: bool = False,
    base_path: Optional[pathlib.Path] = None,
):
    config_path = config_path.expanduser().absolute()
    # Load the config
    config = Box.from_toml(config_path.read_text())
    STATE["config"] = config
    for key, value in config.files.items():
        config.files[key] = pathlib.Path(value).expanduser().absolute()
    # Set up the file path.
    if clean:
        if config.files.file_storage_path.exists():
            for f in config.files.file_storage_path.glob("*"):
                f.unlink()
            config.files.file_storage_path.rmdir()
    config.files.file_storage_path.mkdir(exist_ok=True)
    # Load the database
    db_file = config.files.database_file
    if clean:
        db_file.unlink(missing_ok=True)
    db = DB(db_file=db_file)
    STATE["db"] = db
    # Set the base path
    if base_path is not None:
        STATE["base_path"] = base_path.expanduser().absolute()


@app.command()
def import_bibtex(bibfile: pathlib.Path, library_root: Optional[pathlib.Path] = None):
    if "base_path" in STATE and not bibfile.is_absolute():
        bibfile = STATE["base_path"] / bibfile
    print(bibfile)
    if not bibfile.exists():
        print(f"{bibfile} does not exist")
        return 1
    if library_root is None:
        library_root = bibfile.parent
    bibtex.import_bibtex(bibfile, library_root)


@app.command()
def view(query: str):
    # Search and display results.
    config: Box = STATE["config"]
    db: DB = STATE["db"]
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
    db: DB = STATE["db"]
    paper = select_paper(db, query)
    if paper is None:
        return
    subprocess.Popen(
        ["xdg-open", f"https://doi.org/{paper.doi}"],
        start_new_session=True,
    )


@app.command()
def new(file: Optional[pathlib.Path] = None):
    config = STATE["config"]
    db = STATE["db"]
    new_path = config.files.tmp_storage / "alexandria_new.bib"
    new_path.unlink(missing_ok=True)
    subprocess.call([config.general.editor, new_path])
    entries = bibtex.import_bibtex(new_path)
    if len(entries) != 0:
        print(f"Import failed")
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
    config: Box = STATE["config"]
    db: DB = STATE["db"]
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
    db = STATE["db"]
    result = bibtex.export_bibtex(db, [key])
    if len(result.strip()) == 0:
        return 1
    if target is None:
        print(result)
    else:
        target.write_text(result)


@app.command()
def edit(key: str):
    config = STATE["config"]
    db = STATE["db"]
    entry = Entry.load(db, key)
    result = bibtex.export_bibtex(db, [key])
    if len(result.strip()) == 0:
        return 1
    tmp_file = config.files.tmp_storage / f"{key}.bib"
    tmp_file.write_text(result)
    subprocess.call([config.general.editor, tmp_file])
    try:
        parsed = Entry.parse_bibtex(bibtexparser.parse_file(tmp_file).entries[0])
    except Exception as err:
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
