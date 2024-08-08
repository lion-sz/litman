import pathlib
import logging
import pickle

import urllib3
from box import Box

from litman.db_connector import DB

logger = logging.getLogger(__name__)


def bootstrap_db(config: Box, db: DB):
    """This function pulls an existing database and replaces the current one."""
    if config.general.mode != "client":
        raise ValueError("Only allowed in client mode.")
    main = config.client.main
    response = urllib3.request("GET", f"{main}/admin/get_dump")
    tempfile = pathlib.Path(config.files.tmp_storage) / "bootstrap_import.sql"
    with tempfile.open("wb") as ofile:
        ofile.write(response.data)
    db.bootstrap(tempfile)
    # Load all files that are not present on the client.
    files = db.cursor.execute("SELECT id, path FROM file").fetchall()
    for id, file_name in files:
        file_path = config.files.file_storage_path / file_name
        if file_path.exists():
            continue
        logger.info(f"Fetching file {file_name}.")
        response = urllib3.request("GET", f"{main}/entry/file/{str(id)}")
        with file_path.open("wb") as ofile:
            ofile.write(response.data)


def sync_client(config: Box, db: DB):
    """Push updates to a remote server."""
    main = config.client.main
    export = db.export_transactions()
    payload = pickle.dumps(export)
    response = urllib3.request("POST", f"{main}/admin/sync", body=payload)
    if response.status == 500:
        raise ValueError("Server error.")
    body = response.data
    data = pickle.loads(body)
    db.import_transactions(data)
    db.cursor.execute("INSERT INTO sync_log (date) VALUES (unixepoch())")
    db.connection.commit()
    return


def sync_server(config: Box, db: DB, payload):
    export = pickle.loads(payload)
    # Get the local changes before inserting remote changes.
    last_sync = export["last_sync"]
    local_export = db.export_transactions(last_sync)
    # Import remote changes.
    db.import_transactions(export)
    response_body = pickle.dumps(local_export)
    return response_body
