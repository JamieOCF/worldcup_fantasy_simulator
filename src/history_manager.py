"""
history_manager.py
──────────────────
Utility functions for the History / Leaderboard feature.

Expected shape of your run-state JSON (run_state.json or equivalent):
{
    "team_name": "FC Rocket",
    "players": [
        { "name": "Player Name", "position": "FW", "points": 42 },
        ...
    ],
    "rounds": [
        { "round": "Group Stage",    "eliminated": false },
        { "round": "Round of 16",    "eliminated": false },
        { "round": "Quarter-Final",  "eliminated": true  }
    ]
}

Round ordering (furthest = higher index = better):
    Group Stage → Round of 16 → Quarter-Final →
    Semi-Final  → Third Place → Final → Winner

history.json stores a list of entries, best-first.
Each entry:
{
    "team_name":     "FC Rocket",
    "furthest_round": "Quarter-Final",
    "total_points":  187,
    "top_scorer":    { "name": "Player Name", "points": 42 },
    "run_id":        "2026-07-12T14:32:00"   // ISO timestamp, used as unique key
}
"""

import json
import os
from datetime import datetime, timezone

# ── Paths (adjust if your project structure differs) ────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "data", "history.json")
RUN_FILE     = os.path.join(BASE_DIR, "data", "save.json")

# ── Round ordering ───────────────────────────────────────────────────────────
ROUND_ORDER = [
    "Group Stage",
    "Round of 16",
    "Quarter-Final",
    "Semi-Final",
    "Third Place",
    "Final",
    "Winner",
]

def _round_rank(round_name: str) -> int:
    """Return a sortable integer for a round name. Unknown rounds → -1."""
    try:
        return ROUND_ORDER.index(round_name)
    except ValueError:
        return -1


# ── History I/O ──────────────────────────────────────────────────────────────

def load_history() -> list[dict]:
    """Return the full history list, sorted best-first."""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _sort_history(data)


def save_history(history: list[dict]) -> None:
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def _sort_history(history: list[dict]) -> list[dict]:
    """
    Sort priority:
      1. Furthest round reached (higher = better)
      2. Total points (higher = better)
    """
    return sorted(
        history,
        key=lambda e: (_round_rank(e["furthest_round"]), e["total_points"]),
        reverse=True,
    )


# ── Extracting a completed run ───────────────────────────────────────────────

def _furthest_round(rounds: list[dict]) -> str:
    """
    Return the last round the team was NOT eliminated in.
    If they won the whole thing, return 'Winner'.
    """
    reached = "Group Stage"
    for r in rounds:
        if _round_rank(r["round"]) > _round_rank(reached):
            reached = r["round"]
        if r.get("eliminated"):
            break   # stop advancing once knocked out
    return reached


def _top_scorer(players: list[dict]) -> dict:
    if not players:
        return {"name": "—", "points": 0}
    best = max(players, key=lambda p: p.get("points", 0))
    return {"name": best["name"], "points": best.get("points", 0)}


def build_history_entry(run_state: dict) -> dict:
    """Convert a completed run_state dict into a history entry dict."""
    players = run_state.get("players", [])
    rounds  = run_state.get("rounds",  [])

    return {
        "team_name":      run_state.get("team_name", "Unknown"),
        "furthest_round": _furthest_round(rounds),
        "total_points":   sum(p.get("points", 0) for p in players),
        "top_scorer":     _top_scorer(players),
        "run_id":         datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ── Public API ───────────────────────────────────────────────────────────────

def record_completed_run(run_state: dict) -> list[dict]:
    """
    Call this at the end of every run.
    Reads existing history, appends the new entry, re-sorts, saves, and
    returns the updated history list.
    """
    entry   = build_history_entry(run_state)
    history = load_history()
    history.append(entry)
    history = _sort_history(history)
    save_history(history)
    return history


def record_run_from_file(run_file: str = RUN_FILE) -> list[dict]:
    """
    Convenience wrapper: load run state from a JSON file, then record it.
    """
    with open(run_file, "r", encoding="utf-8") as f:
        run_state = json.load(f)
    return record_completed_run(run_state)