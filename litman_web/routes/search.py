import uuid

from flask import (
    Response,
    render_template,
    request,
    session,
)

from litman.keywords import Keyword
from litman.search import AdvancedSearch
from litman_cli.globals import get_globals
from litman_web.app import app


@app.route("/search/advanced", methods=["GET"])
def search_advanced_get():
    session["search_keywords"] = []
    return render_template("search/advanced_search.html", selected_keywords=[])


@app.route("/search/advanced", methods=["POST"])
def search_advanced_post():
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
    print(len(results))
    return render_template("entry/title_list.html", entries=results)


@app.route("/search/advanced/keywords", methods=["POST"])
def search_add_keyword_post():
    config, db = get_globals()
    keyword = request.form["keywords"]
    keyword = Keyword.from_name(db, keyword)
    session["search_keywords"] = session.get("search_keywords", []) + [keyword]
    return render_template(
        "search/keyword_group.html",
        keywords=session["search_keywords"],
    )


@app.route("/search/advanced/keywords/<uuid:keyword_id>", methods=["DELETE"])
def search_add_keyword(keyword_id: uuid.UUID):
    config, db = get_globals()
    print("Session Keywords: ", session.get("search_keywords", []))
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
