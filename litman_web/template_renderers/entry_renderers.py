import uuid

from flask import render_template, redirect

from litman.db_connector import DB


def title_list(db: DB, entry_ids: list[uuid.UUID], allow_redirect: bool = True) -> str:
    """Render a title list.

    If ``allow_redirect`` is true, return a redirect if there is just one entry.
    """
    if allow_redirect and len(entry_ids) == 1:
        return redirect(f"/entry/{entry_ids[0]}")
    data = [
        db.cursor.execute(
            "select id, key, title from entry WHERE id = ?",
            (id,),
        ).fetchone()
        for id in entry_ids
    ]
    print(data)
    return render_template("entry/title_list.html", entries=data)
