import bibtexparser
from flask import (
    Flask,
    Response,
    redirect,
    render_template,
    request,
    send_file,
    session,
)

from alexandria import bibtex
from alexandria.collection import Collection
from alexandria.db_connector import DB
from alexandria.entries.entry import Entry
from alexandria.enums import FileType
from alexandria.file import File
from alexandria.keywords import Keyword
from alexandria.search import AdvancedSearch, Search
from alexandria_cli.app_utils import select_paper
from alexandria_cli.globals import get_globals
from alexandria_web._utils import err_msg, parse_int, success_msg
from alexandria_web.app import app


@app.route("/search/advanced", methods=["GET", "POST"])
def search_advanced():
    if request.method == "GET":
        session["search_keywords"] = []
        return render_template("search/advanced_search.html", selected_keywords=[])
    assert request.method == "POST", f"Method '{request.method}' not supported"
    print(request.form)
    search = AdvancedSearch(
        title=request.form.get("title", None),
        author=request.form.get("author", None),
        keywords=session.get("search_keywords", []),
    )
    if not search.is_valid:
        return Response(status=204)
    config, db = get_globals()
    results = search.search(db)
    return render_template("entry/title_list.html", entries=results)


@app.route("/search/advanced/keywords", methods=["POST"])
@app.route("/search/advanced/keywords/<int:keyword_id>", methods=["DELETE"])
def search_add_keyword(keyword_id: int = None):
    config, db = get_globals()
    print("Session Keywords: ", session.get("search_keywords", []))
    if request.method == "POST":
        keyword = request.form["keywords"]
        keyword = Keyword.from_name(db, keyword)
        session["search_keywords"] = session.get("search_keywords", []) + [keyword]
    else:
        session["search_keywords"] = [
            k for k in session["search_keywords"] if k.id != keyword_id
        ]
    return render_template(
        "search/keyword_group.html",
        keywords=session["search_keywords"],
    )


@app.route("/search/advanced/list_keywords", methods=["GET"])
def search_list_keywords():
    search = request.args.get("keywords", "")
    if search == "":
        return ""
    config, db = get_globals()
    keywords = Keyword.search_keywords(db, search)
    return render_template("search/search_keyword_list.html", keywords=keywords)
