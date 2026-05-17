import json
import os
from flask import session

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLAYERS_FILE  = os.path.join(BASE_DIR, "data", "players.json")
SAVE_FILE     = os.path.join(BASE_DIR, "data", "save.json")

_SAVE_DEFAULTS = {
    "save_state": 0,
    "team_name": "—",
    "points": 0,
    "round": "—",
    "eliminated": "No",
    "budget": 135,

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


def _write_save(data: dict) -> None:
    os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
 
 
def _clear_creation() -> None:
    """Wipe the in-progress creation session — called on exit or completion."""
    session.pop("creation", None)
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(_SAVE_DEFAULTS, f, indent=4, ensure_ascii=False)
 
 
def _creation_step() -> int:
    """Return the furthest completed step (0 if nothing started)."""
    return session.get("creation", {}).get("step", 0)




# ── Formation definitions ─────────────────────────────────────────────────────
# Key: label shown in UI
# Value: (def, mid, fwd) for starters; bench splits follow same order
FORMATIONS = {
    "5-4-1": {"def": 5, "mid": 4, "fwd": 1, "bench": {"def": 3, "mid": 5, "fwd": 4}},
    "5-3-2": {"def": 5, "mid": 3, "fwd": 2, "bench": {"def": 3, "mid": 6, "fwd": 3}},
    "4-5-1": {"def": 4, "mid": 5, "fwd": 1, "bench": {"def": 4, "mid": 4, "fwd": 4}},
    "4-4-2": {"def": 4, "mid": 4, "fwd": 2, "bench": {"def": 4, "mid": 5, "fwd": 3}},
    "4-3-3": {"def": 4, "mid": 3, "fwd": 3, "bench": {"def": 4, "mid": 6, "fwd": 2}},
    "3-5-2": {"def": 3, "mid": 5, "fwd": 2, "bench": {"def": 5, "mid": 4, "fwd": 3}},
    "3-4-3": {"def": 3, "mid": 4, "fwd": 3, "bench": {"def": 5, "mid": 5, "fwd": 2}},
}
 
TOTAL_SQUAD = 25  # 1 GK starter + 10 outfield starters + 2 GK bench + 12 outfield bench

POSITION_MAP = {
    "LB":  "DEF", "CB":  "DEF", "RB":  "DEF",
    "LM":  "MID", "LW":  "MID", "RM":  "MID", "RW":  "MID",
    "CAM": "MID", "CM":  "MID", "CDM": "MID",
    "ST":  "FW",
    "GK":  "GK",
}
 
 
def _load_players() -> list:
    if not os.path.exists(PLAYERS_FILE):
        return []
    with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
 
 
def _load_save() -> dict:
    if not os.path.exists(SAVE_FILE):
        return {"budget": 175.0}
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
 
 
def _save_to_file(data: dict) -> None:
    os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


GROUPS_FILE  = os.path.join(BASE_DIR, "data", "worldCupGroups.json")
 
 
def _load_groups() -> dict:
    if not os.path.exists(GROUPS_FILE):
        return {}
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)