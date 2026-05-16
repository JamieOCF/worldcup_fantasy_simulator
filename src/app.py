from flask import Flask, render_template, redirect, url_for
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from history_manager import load_history, ROUND_ORDER
from save_manager import load_save

app = Flask(__name__)
app.config["SECRET_KEY"] = 'x' # dont change
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
def home_page():
    return render_template("home_page.html", style="home.css")

@app.route("/fantasy")
def fantasy():
    save = load_save()
    return render_template("fantasy.html", save_state = save["save_state"], save=save, style="fantasy.css")

@app.route("/history")
def history():
    history = load_history()          # already sorted best-first
 
    # Attach rank labels (1st, 2nd, 3rd…) — ties share the same rank
    ranked = []
    prev_key = None
    prev_rank = 0
    for i, entry in enumerate(history):
        key = (ROUND_ORDER.index(entry["furthest_round"])
               if entry["furthest_round"] in ROUND_ORDER else -1,
               entry["total_points"])
        if key != prev_key:
            prev_rank = i + 1
            prev_key  = key
        ranked.append({**entry, "rank": prev_rank})
 
    best_round  = history[0]["furthest_round"]  if history else "—"
    best_points = history[0]["total_points"]    if history else 0
    total_runs  = len(history)
 
    return render_template(
        "history.html",
        style = "history.css",
        history     = ranked,
        best_round  = best_round,
        best_points = best_points,
        total_runs  = total_runs,
    )

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/news")
def news():
    return render_template("news.html")

@app.route("/new_game")
def new_game():
    return render_template("new_game.html")

@app.route("/play")
def play():
    return render_template("play.html")