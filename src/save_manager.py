import json
import os

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE     = os.path.join(BASE_DIR, "data", "save.json")

_SAVE_DEFAULTS = {
    "save_state": 0,
    "team_name": "—",
    "points": 0,
    "round": "—",
    "eliminated": "No",

    "highest_score_player": {"name": "—", "points": 0},
    "lowest_score_player": {"name": "—", "points": 0},

    "players": [],
    "rounds": []
}
 
def load_save() -> dict:
    if not os.path.exists(SAVE_FILE):
        return dict(_SAVE_DEFAULTS)
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # fill any missing keys with defaults
    return {**_SAVE_DEFAULTS, **data}

def check_state():
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["save_state"]