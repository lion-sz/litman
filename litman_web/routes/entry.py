import bibtexparser
import json
import uuid
from flask import render_template, request, send_file, Response

from litman import sources
from litman.entries.entry import Entry
from litman.entries import bibtex_mapping
from litman.author import Author
from litman.enums import FileType, EntryTypes
from litman.file import File
from litman.search import Search
from litman_cli.globals import get_globals
from litman_web.app import app

TYPE_INCLUDES = {
    EntryTypes.Article: "/entry/type/article.html",
    EntryTypes.Book: "/entry/type/book.html",
    EntryTypes.InProceedings: "/entry/type/inproceedings.html",
}


@app.route("/entry")
def list_entries():
    """List entries.

    This accepts a 'query' filter.
    """
    config, db = get_globals()
    query = request.args.get("query", "")
    entry_types = request.args.getlist("entry_type")
    q = []
    args = []
    if len(entry_types) > 0:
        types = [bibtex_mapping[t].value for t in entry_types]
        q.append(f"type IN ({', '.join('?' for _ in types)})")
        args.extend(types)
    if len(query):
        q.append("key LIKE ?")
        args.append(f"%{query}%")
    if len(q) > 0:
        q = "SELECT id, key, title FROM entry WHERE " + " AND ".join(q)
        entries = db.cursor.execute(q, args).fetchall()
    else:
        entries = db.cursor.execute("SELECT id, key, title FROM entry").fetchall()
    return render_template("entry/key_list.html", entries=entries)


@app.route("/entry/<uuid:id>")
def view_entry(id: uuid.UUID):
    config, db = get_globals()
    try:
        entry = Entry.load_id(db, id, barebones=False)
    except Exception as err:
        return f"Error loading entry: {err}"
    if entry is None:
        return f"Entry '{id}' was not found."
    files = entry.files(db)
    file_types = [(ft.name, ft.value) for ft in FileType]
    entry_kwargs = {
        "entry": entry,
        "type_include": TYPE_INCLUDES[entry.type],
        "authors": entry.authors(db),
        "files_loaded": True,
        "files": files,
        "file_types": file_types,
        "keywords": entry.keywords(db),
        "show_keywords": True,
    }
    if request.headers.get("HX-Request"):
        return render_template("entry/entry.html", **entry_kwargs)
    else:
        return render_template("base.html", template="entry/entry.html", **entry_kwargs)


@app.route("/entry/<uuid:id>/short")
def view_entry_short(id: uuid.UUID):
    config, db = get_globals()
    try:
        entry = Entry.load_id(db, id, barebones=True)
    except Exception as err:
        return f"Error loading entry: {err}"
    if entry is None:
        return f"Entry '{id}' was not found."
    entry_kwargs = {
        "entry": entry,
        "type_include": None,
        "authors": entry.authors(db),
        "files_loaded": False,
        "show_keywords": False,
    }
    return render_template("entry/entry.html", **entry_kwargs)


@app.route("/entry/edit/<uuid:id>", methods=["GET", "POST"])
def edit_entry(id: uuid.UUID):
    config, db = get_globals()
    entry = Entry.load_id(db, id)
    if request.method == "GET":
        library = bibtexparser.Library()
        library.add(entry.export_bibtex(db))
        bibtex_string = bibtexparser.write_string(library)
        return render_template(
            "entry/edit.html", entry=entry, bibtex_string=bibtex_string
        )
    # Attempt the edit.
    form_data = request.form.get("bibtex", "")
    parsed = bibtexparser.parse_string(form_data)
    if len(parsed.entries) != 1:
        msg = {
            "toastMessage": {
                "header": "Update Failed",
                "body": f"Unexpected amount of entries parsed: {len(parsed.entries)}.",
                "style": "bg-danger",
            }
        }
        return Response(status=204, headers={"HX-Trigger": json.dumps(msg)})
    bib_entry = parsed.entries[0]
    try:
        new_entry = Entry.parse_bibtex(bib_entry)
        entry.update_entry(new_entry)
        # Check if the authors changed.
        old_authors = entry.authors(db)
        new_authors = Author.parse_authors(bib_entry["author"], db)
        removed_authors = [a for a in old_authors if a not in new_authors]
        added_authors = [a for a in new_authors if a not in old_authors]
        for author in removed_authors:
            entry.detach_author(db, author)
            author.delete(db)
        for author in added_authors:
            author.save(db)
            entry.attach_author(db, author)
        entry.save(db)
        db.connection.commit()
    except Exception as err:
        msg = {
            "toastMessage": {
                "header": "Update Failed",
                "body": f"Parsing failed with {err}.",
                "style": "bg-danger",
            }
        }
        return Response(status=204, headers={"HX-Trigger": json.dumps(msg)})
    msg = {
        "toastMessage": {
            "header": "Update Succeeded",
            "body": f"Updated entry '{entry.key}'.",
            "style": "bg-success",
        },
        "reloadEntry": {"data": "blank"},
    }
    return Response(
        status=204,
        headers={
            # "HX-Redirect": f"/entry/{entry.id}",
            # "HX-Retarget": "#main",
            "HX-Trigger": json.dumps(msg),
        },
    )


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
        return render_template("entry/full_list.html", entries=entries)


@app.route("/entry/files/<uuid:entry_id>")
def get_files(entry_id: uuid.UUID):
    config, db = get_globals()
    try:
        entry = Entry.load_id(db, entry_id)
        files = entry.files(db)
    except Exception:
        return f"No file found for for entry '{entry_id}'"
    return render_template("entry/files.html", entry=entry, files=files)


@app.route("/entry/files/<uuid:entry_id>", methods=["POST"])
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
        message = {
            "toastMessage": {
                "header": "File Upload Succeeded",
                "body": "",
                "style": "bg-success",
            }
        }
    except Exception as err:
        db.connection.rollback()
        message = {
            "toastMessage": {
                "header": "File Upload Failed",
                "body": str(err),
                "style": "bg-danger",
            }
        }
    return Response(
        render_template("entry/files.html", entry=entry, files=entry.files(db)),
        headers={"HX-Trigger": json.dumps(message)},
    )


@app.route("/entry/file/<uuid:file_id>")
def get_file(file_id: uuid.UUID):
    config, db = get_globals()
    try:
        file = File.load(db, file_id)
    except Exception:
        return f"No file found for file '{file_id}'"
    print(file.path)
    return send_file(config.files.file_storage_path / file.path)


@app.route("/entry/create", methods=["GET"])
def create_entry():
    if request.headers.get("HX-Request"):
        return render_template("entry/create.html")
    else:
        return render_template("base.html", template="entry/create.html")


@app.route("/entry/create/bibtex", methods=["POST"])
def create_entry_bibtex():
    config, db = get_globals()
    msg = None
    form_data = request.form["bibtex"]
    if len(form_data) == 0:
        msg = {
            "toastMessage": {
                "header": "Creation Failed",
                "body": "No BibTeX data was provided.",
                "style": "bg-danger",
            }
        }
        return Response(status=204, headers={"HX-Trigger": json.dumps(msg)})
    try:
        entries = sources.import_library(config, db, None, bib_string=form_data)
        if len(entries) != 1:
            msg = {
                "toastMessage": {
                    "header": "Creation Failed",
                    "body": f"Bad number of entries found: '{len(entries)}'.",
                    "style": "bg-danger",
                }
            }
            return Response(status=204, headers={"HX-Trigger": json.dumps(msg)})
        entry = entries[0]
    except Exception as err:
        msg = {
            "toastMessage": {
                "header": "Creation Failed",
                "body": f"Import Error: '{err}'",
                "style": "bg-danger",
            }
        }
        return Response(status=204, headers={"HX-Trigger": json.dumps(msg)})
    return Response(headers={"HX-Redirect": f"/entry/{entry.id}"})


@app.route("/entry/create/crossref", methods=["POST"])
def create_entry_crossref():
    config, db = get_globals()
    # Check if the provided values are valid.
    key = request.form.get("key", "")
    doi = request.form.get("doi", "")
    doi_err = None
    key_err = None
    if key == "":
        key_err = "No Citation Key Provided"
    else:
        if Entry.load_key(db, key, barebones=True) is not None:
            key_err = f"Citation Key '{key}' already exists."
    if doi == "":
        doi_err = "No DOI Provided"

    # Check if there was an error in form validation.
    if key_err or doi_err:
        return render_template(
            "entry/create_crossref.html",
            doi=doi,
            key=key,
            doi_err=doi_err,
            key_err=key_err,
        )
    # Try the import.
    try:
        entry = sources.load_doi(db, key, doi)
        if entry is None:
            msg = "Unspecified error."
        else:
            db.connection.commit()
    except Exception as err:
        db.connection.rollback()
        msg = str(err)
        trigger_data = {
            "toastMessage": {
                "header": "Import Failed",
                "body": f"Imported failed: {msg}",
                "style": "bg-danger",
            }
        }
        return Response(status=204, headers={"HX-Trigger": json.dumps(trigger_data)})
    return Response(headers={"HX-Redirect": f"/entry/{entry.id}"})


@app.route("/entry/create/doi", methods=["POST"])
def load_doi():
    config, db = get_globals()
    doi = request.form.get("doi", "")
    if doi == "":
        return "DOI Empty"
    try:
        entry = sources.load_doi(config, db, doi)
        db.connection.commit()
    except Exception as err:
        msg = {
            "HX-Trigger": {
                "header": "Import Failed",
                "body": str(err),
                "style": "bg-danger",
            }
        }
        return Response(status=204, headers={"HX-Trigger": json.dumps(msg)})
    return Response(headers={"HX-Redirect": f"/entry/{entry.id}"})
