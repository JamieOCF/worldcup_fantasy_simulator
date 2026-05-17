from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_session import Session
from history_manager import load_history, ROUND_ORDER
from save_manager import load_save, _creation_step, _clear_creation, _write_save,\
_load_save, _load_players, _save_to_file, _load_groups
from save_manager import FORMATIONS, POSITION_MAP, TOTAL_SQUAD
from functools import wraps
import os
from flask_wtf.csrf import CSRFProtect


import json
# Look for your existing models import and add it there:
from models import Teams, _team_name_match, create_teams_from_rosters
from worldcup import WorldCup
import traceback

app = Flask(__name__)
print("RUNNING APP FROM:", __file__)
app.config["SECRET_KEY"] = 'x' # dont change
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

CURRENT_WC = None


csrf = CSRFProtect(app)


@app.errorhandler(Exception)
def handle_exception(e):
    traceback.print_exc()          # full traceback in your terminal
    return jsonify({"error": str(e)}), 500


def requires_creation_step(minimum_step: int):
    """
    Decorator that enforces step ordering.
    If the user hasn't reached `minimum_step - 1` yet, they are sent back to
    the start of the flow (which also wipes the partial session).
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if _creation_step() < minimum_step - 1:
                _clear_creation()
                flash("Please start the process from the beginning.", "warning")
                return redirect(url_for("new_save"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

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
        "history.html", style = "history.css",
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

@app.route("/new_save", methods=["GET", "POST"])
def new_save():
    """
    Always clears any previous partial creation first.
    Shows the overwrite warning if a save already exists,
    then the team name input.
    """
    _clear_creation()                # wipe any abandoned attempt
    save = load_save()
    return render_template(
        "new_save.html", style="new_save.css", 
        # script="name.js",
        save_state     = save.get("save_state", 0),
        save_team_name = save.get("team_name", ""),
    )

@app.route("/team-name", methods=["POST"])
def team_name():
    team_name = request.form.get("team_name", "").strip()
 
    if not team_name:
        # Re-render with error; keep save context for the warning modal
        save = load_save()
        flash("Team name cannot be empty.", "error")
        return render_template(
            "new_save.html",
            save_state     = save.get("save_state", 0),
            save_team_name = save.get("team_name", ""),
            name_error     = True,
        ), 422
 
    if len(team_name) > 40:
        team_name = team_name[:40]
 
    # Initialise creation session at step 1
    session["creation"] = {
        "step":      1,
        "team_name": team_name,
        "squad":     [],
        "opponent":  None,
    }
    session.modified = True
    return redirect(url_for("choose_team"))


## step 3 --- create your squad of players

@app.route("/api/players")
def api_players():
    """Return all players sorted by cost desc, optionally filtered by position."""
    position = request.args.get("position", "").upper()
    players  = _load_players()
 
    def normalise(p):
        raw = p.get("positions", [""])[0].upper()
        return POSITION_MAP.get(raw, raw)

    if position:
        players = [p for p in players if normalise(p) == position]

    players.sort(key=lambda p: p.get("cost", 0), reverse=True)

    return jsonify([
        {
            "id":          p.get("id", ""),
            "short_name":  p.get("short_name", ""),
            "position":    normalise(p),   # ← send the normalised position
            "nationality": p.get("nationality", "—"),
            "cost":        p.get("cost", 0),
        }
        for p in players
    ])

@app.route("/choose-team")
@requires_creation_step(minimum_step=2)   # must have completed step 1
def choose_team():
    """
    Render the squad-builder page you will create separately.
    The session already holds team_name; the page should POST to /new-save/choose-team.
    """
    creation = session.get("creation", {})
    if creation.get("step", 0) < 1:
        flash("Please start from the beginning.", "warning")
        return redirect(url_for("new_save"))
 
    save    = _load_save()
    budget  = save.get("budget", 135.0)

    return render_template(
        "choose_team.html", style="choose_team.css",
        team_name = creation.get("team_name"),
        budget     = budget,
        formations = list(FORMATIONS.keys()),
    )
 
@app.route("/choose-team", methods=["POST"])
def submit_squad():
    creation = session.get("creation", {})
    if creation.get("step", 0) < 1:
        return redirect(url_for("new_save"))
 
    raw_squad = request.form.get("squad_json", "[]")
    formation = request.form.get("formation", "4-3-3")
 
    try:
        squad = json.loads(raw_squad)
    except (ValueError, TypeError):
        flash("Invalid squad data.", "error")
        return redirect(url_for("choose_team"))
 
    # Basic validation: must have exactly 25 players
    if len(squad) != TOTAL_SQUAD:
        flash(f"Squad must contain exactly {TOTAL_SQUAD} players.", "error")
        return redirect(url_for("choose_team"))
 
    # Deduct final budget from save
    save       = _load_save()
    total_cost = sum(p.get("cost", 0) for p in squad)
    save["budget"] = round(save.get("budget", 135.0) - total_cost, 1)
    _save_to_file(save)
 
    creation["squad"]     = squad
    creation["formation"] = formation
    creation["step"]      = 2
    session.modified      = True

    # with open("logger.txt", "w") as l:
    #     l.write(str(squad))
    #     l.close()
 
    return redirect(url_for("replace"))
 
 
# ── Step 4 — Choose opponent (which WC team to replace) ──────────────────────
 
@app.route("/replace", methods=["GET"])
def replace():
    creation = session.get("creation", {})
    if creation.get("step", 0) < 2:
        flash("Please complete the previous steps first.", "warning")
        # print("oooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooops")
        return redirect(url_for("new_save"))
 
    groups = _load_groups()
 
    return render_template(
        "replace.html", style="replace.css",
        team_name   = creation.get("team_name", ""),
        groups      = groups,
        groups_json = json.dumps(groups),
    )
 
 
@app.route("/replacer", methods=["POST"])
def replace_helper():
    creation = session.get("creation", {})
    if creation.get("step", 0) < 2:
        return redirect(url_for("new_save"))
 
    opponent       = request.form.get("opponent", "").strip()
    opponent_group = request.form.get("opponent_group", "").strip()
 
    if not opponent or not opponent_group:
        flash("Please select a team to replace.", "warning")
        return redirect(url_for("replace"))
 
    # Validate the team actually exists in the group
    groups = _load_groups()
    group_teams = groups.get(opponent_group, {})
    if opponent not in group_teams:
        flash("Invalid team selection.", "error")
        return redirect(url_for("replace"))
 
    creation["replacement"]       = opponent
    creation["replacement_group"] = opponent_group
    creation["step"]           = 3
    session.modified           = True
 
    return redirect(url_for("finalise"))
 
 
# ── Step 5 — Finalise: write save.json and clean up ──────────────────────────
 
@app.route("/finalise", methods=["GET"])
@requires_creation_step(minimum_step=4)   # must have completed step 3
def finalise():
    """
    All three steps are done. Write the new save and clear the creation session.
    """
    creation = session.get("creation", {})
 
    new_save = {
        "save_state":  1,                          # 1 = active run
        "team_name":   creation["team_name"],
        "replacement":    creation["replacement"],
        "round":       "Group Stage",
        "points":      0,
        "eliminated":  False,
        "players":       creation["squad"],
        "highest_score_player": {"name": "—", "points": 0},
        "lowest_score_player":  {"name": "—", "points": 0},
    }

    BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
    SQUAD_FILE    = os.path.join(BASE_DIR, "data", "playerTeam.json")

    defs = []
    mids = []
    fwds = []
    gk = None
    bench = []
    squad = creation["squad"]
    for p in squad:
        pos = p["slot_id"].split("-")[0]
        match pos:
            case "def":
                defs.append(p["short_name"])
            case "mid":
                mids.append(p["short_name"])
            case "fwd":
                fwds.append(p["short_name"])
            case "gk":
                gk = p["short_name"]
            case "bench":
                bench.append(p["short_name"])

    squad_data = {
        creation["team_name"]: {
            "replacing": creation["replacement"],
            "starting_xi": {
                "Goalkeeper": gk,
                "Defenders": defs,
                "Midfielders": mids,
                "Forwards": fwds
            },
            "bench": bench
        }
    }
    # with open("logger.txt", "w") as l:
    #     l.write(squad_data)
    #     l.close()
    with open("data/playerTeam.json", "w") as f:
        json.dump(squad_data, f, indent=4)
 
    _write_save(new_save)
    _clear_creation()                              # clean up session
 
    flash(f"Save created! Welcome, {new_save['team_name']}.", "success")
    return redirect(url_for("play"))          # ← redirect to your game start
 
 
# ── Cancel / back-button safety ──────────────────────────────────────────────
 
@app.route("/cancel", methods=["GET"])
def cancel():
    """
    Explicit cancel link (optional — the session is also wiped on next /new-save visit).
    """
    _clear_creation()
    return redirect(url_for("fantasy"))

@app.route("/play", methods=["GET","POST"])
def play():
    return render_template("play.html")





# ---------------------------------------------------------
# GROUP STAGE
# ---------------------------------------------------------

TEAMS_DATA = create_teams_from_rosters(csv_path="data/FC26_Rosters.csv")

@app.route("/start_group_stage", methods=["GET", "POST"])
def start_group_stage():
    global CURRENT_WC
    print("--- DEBUG: START_GROUP_STAGE ROUTE HIT ---")

    follow = None
    
    # Bypass automatic parsing to completely eliminate HTTP 400 errors
    try:
        import json
        # Read the raw unparsed string data directly from the incoming stream
        raw_data = request.get_data(as_text=True)
        print(f"DEBUG: Raw data received is: '{raw_data}'")
        
        if raw_data:
            data = json.loads(raw_data)
            if isinstance(data, dict):
                follow = data.get("follow")
    except Exception as e:
        print(f"DEBUG: Parsing failed, but continuing safely. Error: {e}")

    # Initialize your class safely
    try:
        CURRENT_WC = WorldCup(rosters=TEAMS_DATA, csv_path="data/FC26_Rosters.csv")
        CURRENT_WC.init_group_stage_step_mode(follow=follow)
    except Exception as e:
        traceback.print_exc()          # prints exactly where it died
        return jsonify({"error": str(e)}), 400
    

    return jsonify({"message": f"Group stage started. Following: {follow}"})

@app.route("/next_group_round", methods=["GET","POST"])
def next_group_round():
    global CURRENT_WC

    if CURRENT_WC is None:
        return jsonify({"error": "Tournament not started"}), 400

    result = CURRENT_WC.group_stage_step()
    return jsonify(result)


# ---------------------------------------------------------
# KNOCKOUT STAGE
# ---------------------------------------------------------

@app.route("/start_knockout", methods=["POST"])
def start_knockout():
    global CURRENT_WC

    if CURRENT_WC is None:
        return jsonify({"error": "Tournament not started"}), 400

    CURRENT_WC.init_knockout_step_mode()
    return jsonify({"message": "Knockout stage started"})


@app.route("/next_knockout_match", methods=["GET"])
def next_knockout_match():
    global CURRENT_WC

    if CURRENT_WC is None:
        return jsonify({"error": "Tournament not started"}), 400

    result = CURRENT_WC.knockout_step()
    return jsonify(result)
