from os import environ
import pathlib
from typing import Optional

from box import Box

from litman.db_connector import DB
from litman_cli import globals
from litman_web.app import app as app
from litman_web import routes  # noqa: F401

config_path: pathlib.Path = pathlib.Path(environ.get("LITMAN_CONFIG", "./litman.toml"))
clean: bool = False
base_path: Optional[pathlib.Path] = None

config_path = config_path.expanduser().absolute()
# Load the config
config = Box.from_toml(config_path.read_text())
globals.STATE["config"] = config
print(config.files.database_file, config.files.file_storage_path)
if "LITMAN_MODE" in environ:
    print("Overwriting litman mode")
    config.general.mode = environ["LITMAN_MODE"]
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
globals.STATE["db"] = db
# Set the base path
if base_path is not None:
    globals.STATE["base_path"] = base_path.expanduser().absolute()
