"""This module handles synchronization between the client and server.

There are two ways to synchronize:
1. sharing transactions,
2. Bootstrapping the client from the server.

The transactions based approach is a bit more complicated.

1. The client collects local transactions and posts them to the server
    (`server/push_transactions`).
2. The server collects local transactions and decides what to write
    (curently not implemented, so all).
    It responds with the transactions since the clients last sync
    and a list of the requested files.
3. The client loads these transactions and posts the files to the server.
4. The client posts a list of the files that it requires from the server.

The bootstrapping simply clones the remote db to the local db.
"""

import pathlib
import logging
import pickle

import urllib3
from box import Box

from litman.db_connector import DB

logger = logging.getLogger(__name__)


def _find_missing_files(config, db):
    """Scan all local files and flag missing files."""
    file_path = pathlib.Path(config.files.file_storage_path)
    present = list(file_path.glob("*"))
    present = [f.name for f in present]
    expected = db.cursor.execute("SELECT path FROM files").fetchall()
    missing = [f for f in expected if f in present]
    return missing


def bootstrap_db(config: Box, db: DB):
    """This function pulls an existing database and replaces the current one."""
    if config.general.mode != "client":
        raise ValueError("Only allowed in client mode.")
    auth_headers = urllib3.make_headers(
        basic_auth="{}:{}".format(config.client.user, config.client.password),
    )
    main = config.client.main
    response = urllib3.request("GET", f"{main}/admin/get_dump", headers=auth_headers)
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
    auth_headers = urllib3.make_headers(
        basic_auth="{}:{}".format(config.client.user, config.client.password),
    )
    response = urllib3.request(
        "POST",
        f"{main}/admin/sync",
        body=payload,
        headers=auth_headers,
    )
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
