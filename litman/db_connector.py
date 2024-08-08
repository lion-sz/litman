import logging
import subprocess
import pathlib
import sqlite3
import uuid

logger = logging.getLogger(__name__)
_build_scripts = [
    "transaction_log",
    "entries",
    "entry_types",
    "files",
    "collections",
    "keywords",
    "author",
]

sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes)
sqlite3.register_converter("uuid", lambda b: uuid.UUID(bytes=b))


class DB:
    db_file: pathlib.Path
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    _tables = [
        "entry",
        "article",
        "book",
        "inProceedings",
        "author",
        "collection",
        "file",
        "keyword",
    ]
    _link_tables = {
        "author_link": ("author_id", "entry_id"),
        "file_link": ("file_id", "entry_id"),
        "collection_link": ("entry_id", "collection_id"),
        "keyword_link": ("keyword_id", "entry_id"),
    }
    _schema: dict

    def __init__(self, db_file: pathlib.Path):
        self.db_file = db_file
        build = not self.db_file.exists()
        self.connection = sqlite3.connect(
            self.db_file,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self.cursor = self.connection.cursor()
        if build:
            self._build_database()
        self._load_schema()

    def _load_schema(self):
        # Load the schemas from the list of tables
        self._schema = {}
        for table in self._tables:
            dat = self.cursor.execute(f"PRAGMA TABLE_INFO({table})").fetchall()
            self._schema[table] = [d[1] for d in dat]

    def _build_database(self):
        logger.info(f"Building database at {self.db_file}")
        scripts_path = pathlib.Path("./scripts/build")
        for script in _build_scripts:
            with open(scripts_path / f"{script}.sql") as f:
                self.cursor.executescript(f.read())
        self.connection.commit()
        # Build the triggers.
        with open(scripts_path / "trigger_template.sql") as f:
            trigger_template = f.read()
        trigger_script = "\n".join(
            trigger_template.format(table=table) for table in self._tables
        )
        trigger_script += "\n"
        with open(scripts_path / "link_trigger_template.sql") as f:
            link_template = f.read()
        trigger_script += "\n".join(
            link_template.format(table=t, id_a=s[0], id_b=s[1])
            for t, s in self._link_tables.items()
        )
        self.cursor.executescript(trigger_script)
        self.connection.commit()
        return

    def _clear_transaction_logs(self):
        """This function clears the transaction log tables."""
        self.cursor.execute("DELETE FROM transaction_log")
        self.cursor.execute("DELETE FROM transaction_log_link")
        self.connection.commit()

    def export_transactions(self, last_sync: int = None):
        if last_sync is None:
            last_sync = self.cursor.execute("SELECT max(date) FROM sync_log").fetchone()
            if last_sync is None:
                raise ValueError("No last sync log found.")
            last_sync = last_sync[0]
        export = {}
        for table in self._tables:
            transactions = self.cursor.execute(
                "SELECT * FROM transaction_log WHERE source == ? AND date >= ?",
                (table, last_sync),
            ).fetchall()
            insert_ids = [e[0] for e in transactions if e[3] == 1]
            if insert_ids:
                inserts = self.cursor.execute(
                    f"SELECT * FROM {table} WHERE id IN ({', '.join('?' for _ in insert_ids)})",
                    insert_ids,
                ).fetchall()
            else:
                inserts = []
            update_ids = [e[0] for e in transactions if e[3] == 2]
            if update_ids:
                updates = self.cursor.execute(
                    f"SELECT * FROM {table} WHERE id IN ({', '.join('?' for _ in update_ids)})",
                    update_ids,
                ).fetchall()
            else:
                updates = []
            delete_ids = [e[0] for e in transactions if e[3] == 3]
            export[table] = {
                "transactions": transactions,
                "insert_ids": insert_ids,
                "update_ids": update_ids,
                "delete_ids": delete_ids,
                "inserts": inserts,
                "updates": updates,
            }
        ln_q = (
            "SELECT id_left, id_right, source FROM "
            "transaction_log_link WHERE type = ? AND date >= ?"
        )
        ln_inserts = self.cursor.execute(ln_q, (1, last_sync)).fetchall()
        ln_deletes = self.cursor.execute(ln_q, (3, last_sync)).fetchall()
        result = {
            "last_sync": last_sync,
            "tables": export,
            "links": {"inserts": ln_inserts, "deletes": ln_deletes},
        }
        return result

    def import_transactions(self, export: dict):
        """This function imports transactions without checks.

        It is meant to run on clients and trusts that the server knows what
        it is doing...
        """
        try:
            for table, data in export["tables"].items():
                inserts = data["inserts"]
                if len(inserts) > 0:
                    logger.info(f"inserting into {table}: {len(inserts)}")
                    insert_q = f"INSERT INTO {table}({', '.join(self._schema[table])}) VALUES ({', '.join('?' for _ in self._schema[table])})"
                    self.cursor.executemany(insert_q, data["inserts"])
                updates = data["updates"]
                if len(updates) > 0:
                    logger.info(f"updating into {table}: {len(updates)}")
                    update_q = f"UPDATE {table} SET {', '.join(f'{n} = ?' for n in self._schema[table][1:])} WHERE id = ?"
                    self.cursor.executemany(
                        update_q, [x[1:] + (x[0],) for x in updates]
                    )
                deletes = data["delete_ids"]
                if len(deletes) > 0:
                    logger.info(f"Deleting into {table}: {len(updates)}")
                    self.cursor.executemany(
                        f"DELETE FROM {table} WHERE id = ?", deletes
                    )
            links = export["links"]
            for id_a, id_b, table in links["inserts"]:
                name_a, name_b = self._link_tables[table]
                q = f"INSERT INTO {table} ({name_a}, {name_b}) VALUES (?, ?)"
                self.cursor.execute(q, (id_a, id_b))
            for id_a, id_b, table in links["deletes"]:
                name_a, name_b = self._link_tables[table]
                q = f"DELETE FROM {table} WHERE {name_a} == ? AND {name_b} == ?"
                self.cursor.execute(q, (id_a, id_b))
            self.connection.commit()
        except Exception as err:
            self.connection.rollback()
            raise err
        return

    def import_master(self, export: dict):
        """This function imports transactions as the master database.

        It SHOULD check for conflicts but this is not yet implemented."""
        raise ValueError("Not Yet Implemented.")

    def dump(self, out_file: pathlib.Path):
        with open("/tmp/dump_script.sql", "w") as f:
            f.write(f".output {out_file}\n")
            f.write(".dump")
        subprocess.call(["sqlite3", str(self.db_file), ".read /tmp/dump_script.sql"])
        return

    def bootstrap(self, in_file: pathlib.Path):
        self.connection.close()
        self.db_file.unlink(missing_ok=True)
        subprocess.call(["sqlite3", str(self.db_file), f".read {in_file}"])
        self.connection = sqlite3.connect(
            self.db_file,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self.cursor = self.connection.cursor()
        self.cursor.execute("INSERT INTO sync_log(date) VALUES (unixepoch())")
        self.connection.commit()
        self._load_schema()
        return
