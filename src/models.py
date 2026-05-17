from pathlib import Path
import json
import random
from dataclasses import dataclass, field
from typing import Optional, Dict, List


teams_2026 = [
    # Group A
    "Mexico", "South Africa", "South Korea", "Czech Republic",
    # Group B
    "Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland",
    # Group C
    "Brazil", "Morocco", "Haiti", "Scotland",
    # Group D
    "United States", "Paraguay", "Australia", "Turkey",
    # Group E
    "Germany", "Curaçao", "Ivory Coast", "Ecuador",
    # Group F
    "Netherlands", "Japan", "Sweden", "Tunisia",
    # Group G
    "Belgium", "Egypt", "Iran", "New Zealand",
    # Group H
    "Spain", "Cape Verde", "Saudi Arabia", "Uruguay",
    # Group I
    "France", "Senegal", "Iraq", "Norway",
    # Group J
    "Argentina", "Algeria", "Austria", "Jordan",
    # Group K
    "Portugal", "DR Congo", "Uzbekistan", "Colombia",
    # Group L
    "England", "Croatia", "Ghana", "Panama"
]


sgroups_2026 = {
    "GroupA": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "GroupB": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "GroupC": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "GroupD": ["United States", "Paraguay", "Australia", "Turkey"],
    "GroupE": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "GroupF": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "GroupG": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "GroupH": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "GroupI": ["France", "Senegal", "Iraq", "Norway"],
    "GroupJ": ["Argentina", "Algeria", "Austria", "Jordan"],
    "GroupK": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "GroupL": ["England", "Croatia", "Ghana", "Panama"]
}


# Load rosters JSON
_rosters_path = Path(__file__).parent / "data" / "worldCupGroups.json"
if _rosters_path.exists():
    try:
        with open(_rosters_path, encoding="utf-8") as _fh:
            world_cup_2026_rosters = json.load(_fh)
            print(f"Loaded rosters from {_rosters_path}")
    except Exception as _e:
        print(f"Failed to load {_rosters_path}: {_e}")
        world_cup_2026_rosters = {}
else:
    print(f"Roster JSON not found at {_rosters_path}; using empty rosters")
    world_cup_2026_rosters = {}


@dataclass
class Player:
    short_name: str
    long_name: str
    positions: list[str]
    overall: int
    potential: int
    age: int
    nationality: str
    pace: Optional[int]
    shooting: Optional[int]
    passing: Optional[int]
    dribbling: Optional[int]
    defending: Optional[int]
    physic: Optional[int]
    aggression: Optional[int]
    mentality_penalties: Optional[int]
    # tournament points for fantasy / tracking
    points: int = 0
    # market value in millions (float)
    cost: float = 0.0
    # goalkeeping attributes (when applicable)
    gk_diving: Optional[int] = None
    gk_reflexes: Optional[int] = None
    gk_positioning: Optional[int] = None
    hasYellow: bool = False
    hasRed: bool = False
    isInjured: bool = False


def _safe_int(value: str) -> Optional[int]:
    try:
        return int(float(value)) if value.strip() else None
    except (ValueError, AttributeError):
        return None


def _normalise(name: str) -> str:
    return name.strip().lower()


def price_for_overall(overall: int) -> float:
    """Return approximate market value in millions for a given overall."""
    if overall >= 90:
        return 13.0
    if overall >= 85:
        return 9.0
    if overall >= 80:
        return 6.5
    if overall >= 75:
        return 4.0
    if overall >= 70:
        return 2.5
    if overall >= 65:
        return 1.2
    return 0.5


def find_players(csv_path: str, player_names: list[str]) -> list[Player]:
    import csv
    targets = {_normalise(n) for n in player_names}
    best: dict[str, dict] = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            short = _normalise(row.get("short_name", ""))
            long = _normalise(row.get("long_name", ""))
            if short not in targets and long not in targets:
                continue
            match_key = short if short in targets else long
            prev = best.get(match_key)
            if prev is None:
                best[match_key] = row
            else:
                prev_ver = (_safe_int(prev.get("fifa_version", "0")) or 0,
                            _safe_int(prev.get("fifa_update",  "0")) or 0)
                curr_ver = (_safe_int(row.get("fifa_version",  "0")) or 0,
                            _safe_int(row.get("fifa_update",   "0")) or 0)
                if curr_ver > prev_ver:
                    best[match_key] = row



    players = []
    for row in best.values():
        positions = [p.strip() for p in row.get("player_positions", "").split(",") if p.strip()]
        overall_val = _safe_int(row.get("overall",   "")) or 0
        # helper to generate reasonable stats when CSV fields are missing
        def rnd_stat(center: int, spread: int = 12):
            return max(1, min(99, center + random.randint(-spread, spread)))

        pace_val = _safe_int(row.get("pace", "")) or rnd_stat(overall_val, 16)
        shooting_val = _safe_int(row.get("shooting", "")) or rnd_stat(overall_val, 18)
        passing_val = _safe_int(row.get("passing", "")) or rnd_stat(overall_val, 16)
        dribbling_val = _safe_int(row.get("dribbling", "")) or rnd_stat(overall_val, 16)
        defending_val = _safe_int(row.get("defending", "")) or rnd_stat(max(1, overall_val - 5), 18)
        physic_val = _safe_int(row.get("physic", "")) or rnd_stat(max(1, overall_val - 2), 16)
        aggression_val = _safe_int(row.get("mentality_aggression", "")) or rnd_stat(50, 30)
        mentality_penalties_val = _safe_int(row.get("mentality_penalties", "")) or rnd_stat(50, 30)
        gk_div = _safe_int(row.get("goalkeeping_diving", "")) or (None if not positions or not any(p.upper().startswith("G") for p in positions) else rnd_stat(max(60, overall_val - 5), 18))
        gk_ref = _safe_int(row.get("goalkeeping_reflexes", "")) or (None if not positions or not any(p.upper().startswith("G") for p in positions) else rnd_stat(max(60, overall_val - 3), 18))
        gk_pos = _safe_int(row.get("goalkeeping_positioning", "")) or (None if not positions or not any(p.upper().startswith("G") for p in positions) else rnd_stat(max(60, overall_val - 4), 18))
        # compute GK bonus if goalkeeper stats present
        gk_vals = [v for v in (gk_div, gk_ref, gk_pos) if v is not None]
        gk_bonus = 0.0
        if gk_vals:
            avg_gk = sum(gk_vals) / len(gk_vals)
            gk_bonus = max(0.0, (avg_gk - 70) * 0.12)  # ~2.4M extra for avg 90
        base_price = price_for_overall(overall_val)
        # add small random variance to market value (+/- ~12%)
        raw_price = base_price + gk_bonus
        variance = random.uniform(-0.12, 0.12)
        final_price = round(max(0.1, raw_price * (1.0 + variance)), 2)
        players.append(Player(
            short_name=row.get("short_name", "").strip(),
            long_name=row.get("long_name",  "").strip(),
            positions=positions,
            overall=overall_val,
            potential=_safe_int(row.get("potential", "")) or 0,
            age=_safe_int(row.get("age",       "")) or 0,
            nationality=row.get("nationality_name", "").strip(),
            pace=pace_val,
            shooting=shooting_val,
            passing=passing_val,
            dribbling=dribbling_val,
            defending=defending_val,
            physic=physic_val,
            aggression=aggression_val,
            mentality_penalties=mentality_penalties_val,
            gk_diving=gk_div,
            gk_reflexes=gk_ref,
            gk_positioning=gk_pos,
            cost=final_price,
        ))

    return players


@dataclass
class Teams:
    name: str
    players: Dict[str, List[Player]] = field(default_factory=lambda: {
        "Goalkeeper": [],
        "Defenders": [],
        "Midfielders": [],
        "Forwards": [],
    })
    bench: List[Player] = field(default_factory=list)
    pts: int = 0
    gf: int = 0
    ga: int = 0

    def record_match(self, goals_for: int, goals_against: int) -> None:
        self.gf += int(goals_for)
        self.ga += int(goals_against)
        if goals_for > goals_against:
            self.pts += 3
        elif goals_for == goals_against:
            self.pts += 1

    def all_players(self) -> List[Player]:
        out = []
        for grp in ("Goalkeeper", "Defenders", "Midfielders", "Forwards"):
            out.extend(self.players.get(grp, []))
        out.extend(self.bench)
        return out


def create_teams_from_rosters(rosters: dict = world_cup_2026_rosters, csv_path: str | None = None) -> dict:
    # allow a user-supplied team JSON to replace a squad in the rosters
    custom_path = Path(__file__).parent / "data" / "playerTeam.json"
    if custom_path.exists():
        try:
            with open(custom_path, encoding="utf-8") as _cf:
                custom = json.load(_cf)
            # custom is mapping new_team_name -> {replacing: <team>, starting_xi: {...}, bench: [...]}
            for new_name, info in custom.items():
                replacing = info.get("replacing")
                if not replacing:
                    continue
                replaced = False
                for gk, group in rosters.items():
                    for team_name in list(group.keys()):
                        try:
                            if _team_name_match(team_name, replacing):
                                # replace the team entry with the custom team data
                                group.pop(team_name, None)
                                group[new_name] = {
                                    "starting_xi": info.get("starting_xi", {}),
                                    "bench": info.get("bench", [])
                                }
                                replaced = True
                                break
                        except Exception:
                            continue
                    if replaced:
                        break
        except Exception:
            pass

    all_names = []
    for group in rosters.values():
        for team_name, team_data in group.items():
            sx = team_data.get("starting_xi", {})
            gk = sx.get("Goalkeeper")
            if gk:
                all_names.append(gk)
            for grp in ("Defenders", "Midfielders", "Forwards"):
                all_names.extend(sx.get(grp, []))
            all_names.extend(team_data.get("bench", []))

    resolved: List[Player] = []
    name_map: Dict[str, Player] = {}
    if csv_path is None:
        data_dir = Path(__file__).parent / "data"
        csv_candidates = list(data_dir.glob("FC26*.csv"))
        csv_path = str(csv_candidates[0]) if csv_candidates else None

    if csv_path:
        try:
            resolved = find_players(csv_path, all_names)
            for p in resolved:
                name_map[p.short_name.strip().lower()] = p
                name_map[p.long_name.strip().lower()] = p
        except FileNotFoundError:
            print(f"CSV not found at {csv_path}; proceeding with placeholders")

    def _lookup_or_make(name: str, pos_hint: str) -> Player:
        key = name.strip().lower()
        if key in name_map:
            return name_map[key]
        overall = random.randint(50, 86)
        def rnd_stat(center: int, spread: int = 12):
            return max(1, min(99, center + random.randint(-spread, spread)))
        shooting = rnd_stat(overall, 18)
        passing = rnd_stat(overall, 16)
        pace = rnd_stat(overall, 16)
        dribbling = rnd_stat(overall, 16)
        defending = rnd_stat(overall - 5, 18)
        physic = rnd_stat(overall - 2, 16)
        aggression = rnd_stat(50, 30)
        mentality_penalties = rnd_stat(50, 30)
        # if placeholder is a goalkeeper, generate GK stats and include bonus
        gk_div = None
        gk_ref = None
        gk_pos = None
        if pos_hint.upper().startswith("G"):
            gk_div = rnd_stat(max(60, overall - 5), 18)
            gk_ref = rnd_stat(max(60, overall - 3), 18)
            gk_pos = rnd_stat(max(60, overall - 4), 18)
            gk_bonus = max(0.0, ((gk_div + gk_ref + gk_pos) / 3 - 70) * 0.12)
        else:
            gk_bonus = 0.0
        base_price = price_for_overall(overall)
        raw_price = base_price + gk_bonus
        variance = random.uniform(-0.12, 0.12)
        final_price = round(max(0.1, raw_price * (1.0 + variance)), 2)

        return Player(
            short_name=name,
            long_name=name,
            positions=[pos_hint],
            overall=overall,
            potential=min(99, overall + random.randint(0, 6)),
            age=random.randint(20, 34),
            nationality="",
            pace=pace,
            shooting=shooting,
            passing=passing,
            dribbling=dribbling,
            defending=defending,
            physic=physic,
            aggression=aggression,
            mentality_penalties=mentality_penalties,
            gk_diving=gk_div,
            gk_reflexes=gk_ref,
            gk_positioning=gk_pos,
            cost=final_price,
            hasYellow=False,
            hasRed=False,
            isInjured=False,
        )

    out: Dict[str, Dict[str, Teams]] = {}
    for group_key, group in rosters.items():
        out[group_key] = {}
        for team_name, team_data in group.items():
            t = Teams(name=team_name)
            sx = team_data.get("starting_xi", {})
            gk = sx.get("Goalkeeper")
            if gk:
                t.players["Goalkeeper"].append(_lookup_or_make(gk, "GK"))
            for grp in ("Defenders", "Midfielders", "Forwards"):
                for nm in sx.get(grp, []):
                    t.players[grp].append(_lookup_or_make(nm, grp[:-1] if grp.endswith('s') else grp))
            for nm in team_data.get("bench", []):
                t.bench.append(_lookup_or_make(nm, "Bench"))
            out[group_key][team_name] = t

    return out


def _normalize_key(k: str) -> str:
    return ''.join(ch for ch in k.lower() if ch.isalnum())


def _team_name_match(a: str, b: str) -> bool:
    na = _normalize_key(a)
    nb = _normalize_key(b)
    return na == nb or na in nb or nb in na
