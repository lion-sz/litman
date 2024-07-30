from flask import render_template, request

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


@app.route("/keyword/add_keyword/<entry>", methods=["POST"])
def add_keyword(entry: int):
    keyword = request.form["keyword"]
    print(f"Attaching {keyword} to paper {id}.")
    config, db = get_globals()
    # Load the entry
    entry = Entry.load_id(db, entry, barebones=True)
    keyword = Keyword.from_name(db, keyword)
    if keyword in entry.keywords(db):
        return "Keyword already assigned to entry."
    else:
        entry.add_keyword(db, keyword)
        db.connection.commit()
    return "Success"


@app.route("/keyword/delete_keyword/<entry_id>/<keyword_id>", methods=["DELETE"])
def delete_keyword(entry_id: int, keyword_id: int):
    try:
        entry_id = int(entry_id)
    except:
        raise ValueError(f"entry id '{entry_id}' is not valid.'")
    try:
        keyword_id = int(keyword_id)
    except:
        raise ValueError(f"keyword id '{keyword_id}' is not valid.")
    config, db = get_globals()
    entry = Entry.load_id(db, entry_id, barebones=True)
    if keyword_id not in entry.keywords(db):
        return f"Keyword id '{keyword_id}' not found for '{entry.key}'."
    entry.delete_keyword(db, keyword_id)
