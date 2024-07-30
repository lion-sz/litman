from datetime import date

import bibtexparser
from flask import redirect, render_template, request, send_file

from alexandria.collection import Collection
from alexandria.entries.entry import Entry
from alexandria_cli.globals import get_globals
from alexandria_web._utils import err_msg, success_msg
from alexandria_web.app import app


@app.route("/collection")
def list_collections():
    """List Collections

    This route accepts a query parameter for searching collections.
    """
    config, db = get_globals()
    query = request.args.get("query", "")
    if query != "":
        collections = db.cursor.execute(
            "SELECT id, name FROM collections WHERE name LIKE ?", (f"%{query}%",)
        )
    else:
        collections = db.cursor.execute(
            "SELECT id, name FROM collections ORDER BY id"
        ).fetchall()
    return render_template("collection/name_list.html", collections=collections)


@app.route("/collection/show/<int:id>")
def show_collection(id: int):
    config, db = get_globals()
    collection = Collection.load(db, id=id)
    count = collection.count_papers(db)
    print(count)
    return render_template(
        "collection/collection.html", collection=collection, count=count
    )


@app.route("/collection/entries/<int:id>")
def list_attached_entries(id: int):
    config, db = get_globals()
    entries = db.cursor.execute(
        """
        SELECT id, key, title FROM entries WHERE id IN (
            SELECT entry_id FROM collection_cw WHERE collection_id = ?
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
    return redirect(f"/collection/show/{collection.id}")


@app.route("/collection/delete/<int:id>", methods=["DELETE"])
def delete_collection(id: str):
    config, db = get_globals()
    collection = Collection.load(db, id=id)
    collection.delete(db)
    db.connection.commit()
    return f"Collection '{collection.name}' deleted."


@app.route("/collection/attach/<int:id>", methods=["POST"])
def attach_paper(id: int):
    config, db = get_globals()
    collection = Collection.load(db, id=id)
    entry_key = request.form["key"]
    entry = Entry.load_key(db, entry_key, barebones=True)
    if entry is None:
        return err_msg("Entry not found!")
    status = collection.attach_paper(db, entry)
    if status == -1:
        return err_msg("Paper already attached!")
    db.connection.commit()
    return success_msg("Done")


@app.route("/collection/export/<int:id>")
def export_bibtex(id: int):
    # Export the library.
    config, db = get_globals()
    collection = Collection.load(db, id=id)
    library = collection.export_bibtex(db)
    # Dump the library to an export file.
    libfile_name = f"export_{collection.name}_{str(date.today())}.bib"
    libfile = config.files.tmp_storage / libfile_name
    with open(libfile, "w") as f:
        bibtexparser.write_file(f, library)
    return send_file(libfile)
