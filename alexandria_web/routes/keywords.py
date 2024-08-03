import json
import uuid

from flask import render_template, request, Response

from alexandria.entries.entry import Entry
from alexandria.keywords import Keyword
from alexandria_cli.globals import get_globals
from alexandria_web.app import app


@app.route("/keyword", methods=["GET"])
def list_keywords():
    """List Keywords

    This method accepts a 'query' url query.
    """
    config, db = get_globals()
    query = request.args.get("query", "")
    keywords = Keyword.search_keywords(db, query)
    return render_template("keyword/list.html", keywords=keywords)


@app.route("/keyword/<uuid:keyword_id>", methods=["GET"])
def show_keyword(keyword_id: uuid.UUID):
    config, db = get_globals()
    keyword = Keyword.load_id(db, keyword_id)
    q = (
        "SELECT id, key, title FROM entry WHERE id IN "
        + "(SELECT entry_id FROM keyword_link WHERE keyword_id = ?)"
    )
    entries = db.cursor.execute(q, (keyword_id,)).fetchall()
    kwargs = {"keyword": keyword, "entries": entries}
    if request.headers.get("HX-Request"):
        return render_template("keyword/keyword.html", **kwargs)
    else:
        return render_template("base.html", template="keyword/keyword.html", **kwargs)


@app.route("/keyword/add_keyword/<uuid:entry_id>", methods=["POST"])
def add_keyword(entry_id: uuid.UUID):
    keyword = request.form["keyword"]
    config, db = get_globals()
    # Load the entry
    entry = Entry.load_id(db, entry_id, barebones=True)
    keyword = Keyword.from_name(db, keyword)
    if keyword in entry.keywords(db):
        msg = {
            "header": "Adding Keyword Failed",
            "body": "Keyword already assigned to entry.",
            "style": "bg-danger",
        }
    else:
        entry.add_keyword(db, keyword)
        db.connection.commit()
        msg = {
            "header": "Success",
            "body": f"Assigned '{keyword.name}' to entry.",
            "style": "bg-success",
        }
    return Response(
        render_template(
            "keyword/keyword_elem.html",
            entry=entry,
            keywords=entry.keywords(db),
        ),
        headers={"HX-Trigger": json.dumps({"toastMessage": msg})},
    )


@app.route(
    "/keyword/delete_keyword/<uuid:entry_id>/<uuid:keyword_id>", methods=["DELETE"]
)
def delete_keyword(entry_id: uuid.UUID, keyword_id: uuid.UUID):
    config, db = get_globals()
    entry = Entry.load_id(db, entry_id, barebones=True)
    if keyword_id not in entry.keywords(db):
        return f"Keyword id '{keyword_id}' not found for '{entry.key}'."
    entry.remove_keyword(db, keyword_id)
    return render_template(
        "keyword/keyword_elem.html",
        entry=entry,
        keywords=entry.keywords(db),
    )
