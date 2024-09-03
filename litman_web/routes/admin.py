import pathlib
import logging

from flask import render_template, send_file, request, Response

from litman.synchronization import bootstrap_db, sync_client, sync_server
from litman_cli.globals import get_globals
from litman_web.app import app

logger = logging.getLogger(__name__)


@app.route("/admin")
def admin():
    if request.headers.get("HX-Request"):
        return render_template("admin/admin.html")
    else:
        return render_template("base.html", template="admin/admin.html")


@app.route("/admin/get_dump")
def get_dump():
    config, db = get_globals()
    out_file = pathlib.Path(config.files.tmp_storage / "litman_dump.sql")
    db.dump(out_file)
    return send_file(out_file)


@app.route("/admin/bootstrap")
def bootstrap():
    config, db = get_globals()
    bootstrap_db(config, db)
    return "Done"


@app.route("/admin/push")
def push_changes():
    config, db = get_globals()
    sync_client(config, db)
    return "HI"


@app.route("/admin/sync", methods=["POST"])
def get_changes():
    config, db = get_globals()
    body = request.get_data()
    try:
        response_body = sync_server(config, db, body)
    except Exception as err:
        logger.exception(err)
        return Response(status=500)
    return Response(response_body, status=200)
