import uuid
import json
from datetime import date

import bibtexparser
from flask import render_template, request, send_file, Response

from litman.collection import Collection
from litman.entries.entry import Entry
from litman_cli.globals import get_globals
from litman_web.app import app


@app.route("/collection")
def list_collections():
    """List Collections

    This route accepts a query parameter for searching collections.
    """
    config, db = get_globals()
    query = request.args.get("query", "")
    if query != "":
        collections = db.cursor.execute(
            "SELECT id, name FROM collection WHERE name LIKE ?", (f"%{query}%",)
        )
    else:
        collections = db.cursor.execute(
            "SELECT id, name FROM collection ORDER BY id"
        ).fetchall()
    return render_template("collection/name_list.html", collections=collections)


@app.route("/collection/<uuid:id>")
def show_collection(id: uuid.UUID):
    config, db = get_globals()
    collection = Collection.load_id(db, id)
    kwargs = {"collection": collection, "count": collection.count_papers(db)}
    if request.headers.get("HX-Request"):
        return render_template("collection/collection.html", **kwargs)
    else:
        return render_template(
            "base.html",
            template="collection/collection.html",
            **kwargs,
        )


@app.route("/collection/entries/<uuid:id>")
def list_attached_entries(id: uuid.UUID):
    config, db = get_globals()
    entries = db.cursor.execute(
        """
        SELECT id, key, title FROM entry WHERE id IN (
            SELECT entry_id FROM collection_link WHERE collection_id = ?
        )""",
        (id,),
    ).fetchall()
    return render_template("entry/title_list.html", entries=entries)


@app.route("/collection/create", methods=["GET", "POST"])
def create_collection():
    if request.method == "GET":
        return render_template("collection/create.html")
    assert request.method == "POST", f"Unallowed method '{request.method}'"
    config, db = get_globals()
    form = request.form
    collection = Collection(None, form["name"], form["description"])
    collection.save(db)
    db.connection.commit()
    return Response(
        headers={
            "HX-Redirect": f"/collection/{collection.id}",
            "HX-Push-Url": f"collection/{str(collection.id)}",
        },
    )


@app.route("/collection/delete/<uuid:id>", methods=["DELETE"])
def delete_collection(id: uuid.UUID):
    config, db = get_globals()
    collection = Collection.load_id(db, id)
    collection.delete(db)
    db.connection.commit()
    msg = {
        "toastMessage": {
            "header": "Collection Deleted",
            "body": f"Collection '{collection.name}' deleted.",
            "style": "bg-success",
        }
    }
    return Response(
        status=304,
        headers={"HX-Redirect": "/", "HX-Trigger": json.dumps(msg)},
    )


@app.route("/collection/attach/<uuid:id>", methods=["POST"])
def attach_paper(id: uuid.UUID):
    config, db = get_globals()
    collection = Collection.load(db, id=id)
    entry_key = request.form["key"]
    entry = Entry.load_key(db, entry_key, barebones=True)
    msg = None
    if entry is None:
        msg = {
            "toastMessage": {
                "header": "Failed Attaching Entry",
                "body": f"No entry found for key '{entry_key}'.",
                "style": "bg-danger",
            }
        }
        return Response(status=204, headers={"HX-Trigger": json.dumps(msg)})
    status = collection.attach_paper(db, entry)
    if status == -1:
        msg = {
            "toastMessage": {
                "header": "Failed Attaching Entry",
                "body": f"Entry '{entry_key}' is already attached.",
                "style": "bg-danger",
            }
        }
        return Response(status=204, headers={"HX-Trigger": json.dumps(msg)})
    db.connection.commit()
    msg = {
        "toastMessage": {
            "header": "Attached Entry",
            "body": f"Attached entry '{entry_key}'.",
            "style": "bg-success",
        }
    }
    body = render_template(
        "collection/collection.html",
        collection=collection,
        count=collection.count_papers(db),
    )
    return Response(body, status=200, headers={"HX-Trigger": json.dumps(msg)})


@app.route("/collection/export/<uuid:id>")
def export_bibtex(id: uuid.UUID):
    # Export the library.
    config, db = get_globals()
    collection = Collection.load_id(db, id)
    library = collection.export_bibtex(db)
    # Dump the library to an export file.
    libfile_name = f"export_{collection.name}_{str(date.today())}.bib"
    libfile = config.files.tmp_storage / libfile_name
    with open(libfile, "w") as f:
        bibtexparser.write_file(f, library)
    return send_file(libfile)
