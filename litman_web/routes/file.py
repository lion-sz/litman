import json
import uuid
from flask import render_template, request, Response, send_file

from litman.entries.entry import Entry
from litman.file import File
from litman_cli.globals import get_globals
from litman_web.app import app


@app.route("/entry/<uuid:entry_id>/file")
def get_files(entry_id: uuid.UUID):
    config, db = get_globals()
    try:
        entry = Entry.load_id(db, entry_id)
        files = entry.files(db)
    except Exception:
        return f"No file found for for entry '{entry_id}'"
    if len(files) == 0:
        return "No files found for this entry."
    return render_template("entry/files.html", entry=entry, files=files)


@app.route("/entry/<uuid:entry_id>/file", methods=["POST"])
def attach_file(entry_id: uuid.UUID):
    config, db = get_globals()
    try:
        if "file" not in request.files:
            raise ValueError("No File Provided")
        file_obj = request.files["file"]
        if "type" not in request.form:
            raise ValueError("No Type Provided")
        # Attach the file to the entry.
        entry = Entry.load_id(db, entry_id)
        if entry is None:
            raise ValueError(f"Entry {entry_id} Found")
        default_file = len(entry.files(db)) == 0
        file_path = config.files.file_storage_path / file_obj.filename
        file = File(None, file_path, int(request.form["type"]), default_file)
        file.save(config, db)
        entry.attach_file(db, file)
        file_obj.save(file_path)
        db.connection.commit()
        return Response(headers={"HX-Refresh": "true"})
    except Exception as err:
        db.connection.rollback()
        message = {
            "toastMessage": {
                "header": "File Upload Failed",
                "body": str(err),
                "style": "bg-danger",
            },
        }
        return Response(status=402, headers={"HX-Trigger": json.dumps(message)})


@app.route("/entry/<uuid:entry_id>/file/<uuid:file_id>", methods=["GET"])
def get_file(entry_id: uuid.UUID, file_id: uuid.UUID):
    config, db = get_globals()
    try:
        file = File.load(db, file_id)
    except Exception:
        return f"No file found for file '{file_id}'"
    print(file.path)
    return send_file(config.files.file_storage_path / file.path)


@app.route("/entry/<uuid:entry_id>/file/<uuid:file_id>", methods=["DELETE"])
def delete_file(entry_id: uuid.UUID, file_id: uuid.UUID):
    config, db = get_globals()
    try:
        file = File.load(db, file_id)
        file.delete(config, db)
    except Exception:
        return "Deleting File did not work."
    try:
        entry = Entry.load_id(db, entry_id)
        files = entry.files(db)
    except Exception:
        return f"No file found for for entry '{entry_id}'"
    return render_template("entry/files.html", entry=entry, files=files)


@app.route("/entry/<uuid:entry_id>/file/<uuid:file_id>/make_default", methods=["GET"])
def make_default(entry_id: uuid.UUID, file_id: uuid.UUID):
    config, db = get_globals()
    entry = Entry.load_id(db, entry_id)
    old_default = entry.default_file(db)
    db.cursor.execute(
        "UPDATE file SET default_open = 0 WHERE id = ?", (old_default.id,)
    )
    db.cursor.execute("UPDATE file SET default_open = 1 WHERE id = ?", (file_id,))
    try:
        entry = Entry.load_id(db, entry_id)
        files = entry.files(db)
    except Exception:
        return f"No file found for for entry '{entry_id}'"
    return render_template("entry/files.html", entry=entry, files=files)
