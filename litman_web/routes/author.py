import uuid
from flask import render_template, request

from litman_cli.globals import get_globals
from litman_web.app import app

from litman.author import Author


@app.route("/author")
def list_authors():
    config, db = get_globals()
    query = request.args.get("query", "")
    if query != "":
        authors = db.cursor.execute(
            f"SELECT {", ".join(Author.names)} FROM author WHERE last_name LIKE ?",
            (f"%{query}%",),
        ).fetchall()
    else:
        authors = db.cursor.execute(
            f"SELECT {", ".join(Author.names)} FROM author"
        ).fetchall()
    authors = [Author(*a) for a in authors]
    authors = sorted(authors, key=lambda a: a.last_name)
    return render_template("author/list.html", authors=authors)


@app.route("/author/<uuid:author_id>")
def show_author(author_id: uuid.UUID):
    config, db = get_globals()
    author = Author.load_id(db, author_id)
    entries = db.cursor.execute(
        "SELECT id, key, title FROM entry WHERE id IN "
        "(SELECT entry_id FROM author_link WHERE author_id = ?)",
        (author_id,),
    )
    kwargs = {"author": author, "entries": entries}
    if request.headers.get("HX-Request"):
        return render_template("author/author.html", **kwargs)
    else:
        return render_template(
            "base.html",
            include_template="True",
            template="author/author.html",
            **kwargs,
        )
