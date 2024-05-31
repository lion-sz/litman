import pathlib
import shutil
import subprocess
from typing import Optional

from box import Box
import typer

from alexandria.db_connector import DB
from alexandria import bibtex
from alexandria.search import Search
from alexandria.file import File
from alexandria.entries.entry import Entry
from alexandria.global_state import STATE

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


@app.command()
def view(query: str):
    # Search and display results.
    config: Box = STATE["config"]
    db: DB = STATE["db"]
    paper = select_paper(db, query)
    if paper is None:
        return
    file_path = pathlib.Path(paper.files(db)[0].path)
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
        ["xdg-open", f"https://doi.org/{paper.doi}"], start_new_session=True
    )

@app.command()
def new():
    config = STATE["config"]
    new_path = config.files.tmp_storage / "alexandria_new.bib"
    new_path.unlink(missing_ok=True)
    subprocess.call([config.general.editor, new_path])
    import_bibtex(new_path)

@app.command()
def attach(key: str, file_path: pathlib.Path):
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
        file = File(None, path=file_path)
        file.save(config, db)
        entry.attach_file(db, file)
        db.connection.commit()
    except Exception as err:
        print(f"Failed to attach file '{file_path}' to entry '{key}'.")
        print(err)
        return 1

