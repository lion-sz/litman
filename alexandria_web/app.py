import secrets

from cachelib import SimpleCache
from flask import Flask, render_template, session
from flask_session import Session

app = Flask(__name__)

SESSION_TYPE = "cachelib"
SESSION_SERIALIZATION_FORMAT = "json"
SESSION_CACHELIB = SimpleCache()
app.config.from_object(__name__)
Session(app)


@app.route("/")
def index():
    return render_template("base.html")
