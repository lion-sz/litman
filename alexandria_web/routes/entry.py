import pathlib
import shutil
import subprocess
from typing import Optional

import bibtexparser
from box import Box

from alexandria import bibtex
from alexandria.db_connector import DB
from alexandria.entries.entry import Entry
from alexandria.file import File
from alexandria.search import Search
from alexandria_cli.globals import get_globals
from alexandria_cli.app_utils import select_paper


from flask import Flask, render_template, request, send_file, redirect

from alexandria_web.app import app

@app.route("/entry/<key>")
def view_entry(key: str):
    config, db = get_globals()
    try:
        entry = Entry.load(db, key, barebones=True)
    except Exception as err:
        return f"Error loading entry: {err}"
    files = entry.files(db)
    entries = [(entry, files)]
    return render_template("entry/entry.html", entry=entry, files=files)


@app.route("/entry/search", methods=["POST"])
def search():
    query = request.form.get("search", "")
    if len(query) == 0:
        return "No Query provided"
    config, db = get_globals()
    search = Search(db, query)
    if len(search.result) == 1:
        return render_template("entry/entry.html", entry=search.result[0])
    else:
        entries = [(entry, None) for entry in search.result]
        return render_template("entry/entry_list.html", entries=entries)


@app.route("/entry/list")
def list_entries():
    config, db = get_globals()
    entries = db.cursor.execute("SELECT key, title FROM entries").fetchall()
    return render_template("entry/entry_short_list.html", entries=entries)


@app.route("/entry/get_files/<entry_id>")
def get_files(entry_id: str):
    config, db = get_globals()
    try:
        entry = Entry.load(db, entry_id)
        files = entry.files(db)
    except Exception as err:
        return f"No file found for for entry '{entry_id}'"
    return render_template("file_list.html", files=files)


@app.route("/entry/file/<file_id>")
def get_file(file_id: str):
    config, db = get_globals()
    try:
        file = File.load(db, file_id)
    except Exception as err:
        return f"No file found for file '{file_id}'"
    return send_file(file.path)


@app.route("/entry/create", methods=["GET", "POST"])
def create_entry():
    if request.method == "GET":
        return render_template("entry/create.html", show_msg=False)
    elif request.method == "POST":
        config, db = get_globals()
        err_msg = None
        form_data = request.form["bibtex"]
        if len(form_data) == 0:
            err_msg = "No Bibtex Data provided."
        else:
            try:
                entries = bibtex.import_bibtex(config, db, None, bib_string=form_data)
                if len(entries) == 0:
                    err_msg = "No entries found."
                else:
                    return redirect(f"/entry/{entries[0].key}")
            except Exception as err:
                err_msg = str(err)
        if err_msg is None:
            return "Success!"
        else:
            return render_template("entry/create.html", show_msg=True, msg=err_msg)
    else:
        return "Unallowed Method"


@app.route("/entry/attach_file/<key>", methods=["POST"])
def attach_file(key: str):
    # if request.method == "GET":
    #     return "get"
    if request.method != "POST":
        raise ValueError(f"Unexpected Method {request.method}")
    config, db = get_globals()
    print(f"Attaching file for paper {key}.")
    if "file" not in request.files:
        return "No File Provided"
    file_obj = request.files["file"]
    if "type" not in request.form:
        return "No Type Provided"
    # Attach the file to the entry.
    entry = Entry.load(db, key)
    if entry is None:
        return f"Entry {key} Found"
    default_file = len(entry.files(db)) == 0
    file_path = config.files.file_storage_path / file_obj.filename
    file = File(None, file_path, request.form["type"], default_file)
    try:
        file.save(config, db)
        entry.attach_file(db, file)
        db.connection.commit()
    except Exception as err:
        return str(err)
    file_obj.save(file_path)
    return "done"
