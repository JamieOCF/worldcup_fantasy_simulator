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

# Load rosters from JSON file instead of embedding the large dict in source.
from pathlib import Path
import json

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



import csv
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import math
import random
from collections import defaultdict


@dataclass
class Player:
    # Identity
    short_name: str
    long_name: str
    positions: list[str]

    # Overall
    overall: int
    potential: int
    age: int
    nationality: str

    # Basic stats
    pace: Optional[int]
    shooting: Optional[int]
    passing: Optional[int]
    dribbling: Optional[int]
    defending: Optional[int]
    physic: Optional[int]

    # Mentality
    aggression: Optional[int]
    mentality_penalties: Optional[int]

    #play status
    # play status
    hasYellow: bool = False
    hasRed: bool = False
    isInjured: bool = False

    def __str__(self) -> str:
        lines = [
            f"{'='*40}",
            f"  {self.long_name} ({self.short_name})",
            f"  {self.nationality} | Age: {self.age}",
            f"  Positions: {', '.join(self.positions)}",
            f"  Overall: {self.overall}  |  Potential: {self.potential}",
            f"{'─'*40}",
            f"  Pace:      {self.pace or 'N/A':>3}   Shooting:  {self.shooting or 'N/A':>3}",
            f"  Passing:   {self.passing or 'N/A':>3}   Dribbling: {self.dribbling or 'N/A':>3}",
            f"  Defending: {self.defending or 'N/A':>3}   Physic:    {self.physic or 'N/A':>3}",
            f"{'─'*40}",
            f"  Aggression:  {self.aggression or 'N/A':>3}   Penalties: {self.mentality_penalties or 'N/A':>3}",
            f"{'='*40}",
        ]
        return "\n".join(lines)


def _safe_int(value: str) -> Optional[int]:
    """Convert a string to int, returning None if blank or non-numeric."""
    try:
        return int(float(value)) if value.strip() else None
    except (ValueError, AttributeError):
        return None


def _normalise(name: str) -> str:
    """Lowercase + strip for loose name matching."""
    return name.strip().lower()


def find_players(csv_path: str, player_names: list[str]) -> list[Player]:
    """
    Read *csv_path* and return a Player for every row whose short_name or
    long_name matches one of the names in *player_names* (case-insensitive).

    Only the most-recent FIFA version is kept when a player appears more than
    once (highest fifa_version → highest fifa_update).

    Parameters
    ----------
    csv_path     : path to the FIFA players CSV file
    player_names : list of player names to look up

    Returns
    -------
    List of Player objects, one per unique matched player name.
    """
    targets = {_normalise(n) for n in player_names}

    # key → best row seen so far  (key = normalised short_name)
    best: dict[str, dict] = {}

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            short = _normalise(row.get("short_name", ""))
            long  = _normalise(row.get("long_name", ""))

            if short not in targets and long not in targets:
                continue

            match_key = short if short in targets else long

            # Keep the row with the highest FIFA version / update
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
        players.append(Player(
            short_name          = row.get("short_name", "").strip(),
            long_name           = row.get("long_name",  "").strip(),
            positions           = positions,
            overall             = _safe_int(row.get("overall",   "")) or 0,
            potential           = _safe_int(row.get("potential", "")) or 0,
            age                 = _safe_int(row.get("age",       "")) or 0,
            nationality         = row.get("nationality_name", "").strip(),
            pace                = _safe_int(row.get("pace",      "")),
            shooting            = _safe_int(row.get("shooting",  "")),
            passing             = _safe_int(row.get("passing",   "")),
            dribbling           = _safe_int(row.get("dribbling", "")),
            defending           = _safe_int(row.get("defending", "")),
            physic              = _safe_int(row.get("physic",    "")),
            aggression          = _safe_int(row.get("mentality_aggression",  "")),
            mentality_penalties = _safe_int(row.get("mentality_penalties",   "")),
        ))

    return players


@dataclass
class Teams:
    """Representation of a national team with players split by position groups.

    The structure for `players` mirrors the `starting_xi` dict in
    `world_cup_2026_rosters`: keys are exactly `Goalkeeper`, `Defenders`,
    `Midfielders`, `Forwards` and values are lists of `Player` objects.
    """
    name: str
    players: Dict[str, List[Player]] = field(default_factory=lambda: {
        "Goalkeeper": [],
        "Defenders": [],
        "Midfielders": [],
        "Forwards": [],
    })
    bench: List[Player] = field(default_factory=list)

    def all_players(self) -> List[Player]:
        """Return a flat list of all players (starting + bench)."""
        out = []
        for grp in ("Goalkeeper", "Defenders", "Midfielders", "Forwards"):
            out.extend(self.players.get(grp, []))
        out.extend(self.bench)
        return out


def create_teams_from_rosters(rosters: dict = world_cup_2026_rosters, csv_path: str | None = None) -> dict:
    """Build Teams objects from the nested `rosters` dict.

    If `csv_path` is provided the function will attempt to resolve each
    player's FIFA attributes via `find_players`. Missing players are
    created as lightweight `Player` objects with minimal defaults.

    Returns a nested dict with the same grouping as `rosters` but where
    each team value is a `Teams` instance.
    """
    # gather all names to try and resolve via CSV
    all_names = []
    for group in rosters.values():
        for team_name, team_data in group.items():
            sx = team_data.get("starting_xi", {})
            # goalkeeper may be a single string
            gk = sx.get("Goalkeeper")
            if gk:
                all_names.append(gk)
            for grp in ("Defenders", "Midfielders", "Forwards"):
                all_names.extend(sx.get(grp, []))
            # bench
            all_names.extend(team_data.get("bench", []))

    resolved: List[Player] = []
    name_map: Dict[str, Player] = {}
    # If a csv_path isn't provided, try to locate a suitable FC26 CSV in src/data
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
            print(f"Found player in CSV: {name}")
            return name_map[key]
        # create a lightweight placeholder
        print(f"Player not found in CSV: {name} — creating placeholder with random stats")
        # randomized reasonable stats for placeholder players
        overall = random.randint(50, 86)
        # derive other stats around overall with some variance
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
            # goalkeeper
            gk = sx.get("Goalkeeper")
            if gk:
                t.players["Goalkeeper"].append(_lookup_or_make(gk, "GK"))

            for grp in ("Defenders", "Midfielders", "Forwards"):
                for nm in sx.get(grp, []):
                    t.players[grp].append(_lookup_or_make(nm, grp[:-1] if grp.endswith('s') else grp))

            # bench
            for nm in team_data.get("bench", []):
                t.bench.append(_lookup_or_make(nm, "Bench"))

            out[group_key][team_name] = t

    return out


def _poisson(lam: float) -> int:
    """Sample a Poisson-distributed integer with mean `lam` (Knuth)."""
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1


def _weighted_choice(items: List, weights: List[float]):
    total = sum(weights)
    if total <= 0:
        return random.choice(items)
    r = random.random() * total
    upto = 0.0
    for it, w in zip(items, weights):
        upto += w
        if r <= upto:
            return it
    return items[-1]


class Match:
    """Simulate a match between two `Teams`.

    The simulation is intentionally simple and stochastic. Goals are
    generated from a Poisson process with mean 2.7 total expected goals
    per match; who scores depends on team attacking/defensive stats.
    Cards are drawn per-player using the player's aggression stat.
    """

    AVG_XG = 2.7

    def __init__(self, home: Teams, away: Teams, knockout: bool = False):
        self.home = home
        self.away = away
        self.knockout = knockout

        self.timeline: List[dict] = []
        self.score = {home.name: 0, away.name: 0}

    def _team_attack_value(self, team: Teams) -> float:
        # Average forward shooting + midfield passing weighted
        fwd = team.players.get("Forwards", [])
        mid = team.players.get("Midfielders", [])
        def avg(stat_getter, players):
            vals = [stat_getter(p) or 0 for p in players]
            return sum(vals) / len(vals) if vals else 0

        avg_fwd_shoot = avg(lambda p: p.shooting, fwd)
        avg_mid_pass = avg(lambda p: p.passing, mid)
        return 0.7 * avg_fwd_shoot + 0.3 * avg_mid_pass

    def _team_defense_value(self, team: Teams) -> float:
        defs = team.players.get("Defenders", [])
        # use defenders defending stat; fallback to average defending
        vals = [p.defending or 0 for p in defs]
        return sum(vals) / len(vals) if vals else 1.0

    def _choose_scorer(self, team: Teams):
        # Prefer Forwards by shooting, else midfielders by passing
        fwd = team.players.get("Forwards", [])
        mid = team.players.get("Midfielders", [])
        if fwd:
            items = fwd
            weights = [(p.shooting or 10) for p in fwd]
            return _weighted_choice(items, weights)
        if mid:
            items = mid
            weights = [(p.passing or 5) for p in mid]
            return _weighted_choice(items, weights)
        # fallback to any player
        allp = team.all_players()
        return random.choice(allp) if allp else None

    def _simulate_substitutions(self):
        """Substitute players—prioritise those on a yellow card.

        Simple rules:
        - Max 5 substitutions per team.
        - Players with `hasYellow` are considered first and have a high
          chance (70%) to be substituted if a bench player is available.
        - Bench players with `isInjured` or `hasRed` are not eligible.
        - Substitutions generate timeline events with a minute between 46-90.
        """
        for team in (self.home, self.away):
            max_subs = 5
            subs_done = 0

            # candidates: starting players with yellow and not red
            candidates = []
            for grp in ("Goalkeeper", "Defenders", "Midfielders", "Forwards"):
                for p in list(team.players.get(grp, [])):
                    if p.hasRed:
                        continue
                    if p.hasYellow:
                        candidates.append((grp, p))

            for grp, p in candidates:
                if subs_done >= max_subs:
                    break
                # 70% chance to sub a yellow-carded player
                if random.random() < 0.7 and team.bench:
                    # pick first eligible bench player
                    bench_choice = None
                    for b in team.bench:
                        if not b.isInjured and not b.hasRed:
                            bench_choice = b
                            break
                    if bench_choice is None:
                        continue

                    # perform substitution: remove bench_choice from bench, move p to bench,
                    # and add bench_choice to the same starting group
                    team.bench = [x for x in team.bench if x.long_name != bench_choice.long_name]
                    team.players[grp] = [x for x in team.players[grp] if x.long_name != p.long_name]
                    team.players[grp].append(bench_choice)
                    team.bench.append(p)
                    subs_done += 1
                    minute = random.randint(46, 90)
                    self.timeline.append({"minute": minute, "type": "sub", "team": team.name, "out": p.long_name, "in": bench_choice.long_name})


    def _starting_players(self, team: Teams) -> List[Player]:
        out = []
        for grp in ("Goalkeeper", "Defenders", "Midfielders", "Forwards"):
            out.extend(team.players.get(grp, []))
        return out

    def _simulate_goals_period(self, minutes_start: int, minutes_end: int, lam: float):
        """Simulate goals within a minute window [minutes_start, minutes_end]."""
        total_goals = _poisson(lam)
        minutes = sorted(random.randint(minutes_start, minutes_end) for _ in range(total_goals))

        home_attack = self._team_attack_value(self.home)
        away_attack = self._team_attack_value(self.away)
        home_def = self._team_defense_value(self.home)
        away_def = self._team_defense_value(self.away)

        home_score_weight = max(0.01, home_attack / (away_def or 1))
        away_score_weight = max(0.01, away_attack / (home_def or 1))

        for minute in minutes:
            t = _weighted_choice([self.home, self.away], [home_score_weight, away_score_weight])
            scorer = self._choose_scorer(t)
            if scorer is None:
                continue
            self.score[t.name] += 1
            ev = {"minute": minute, "type": "goal", "team": t.name, "scorer": scorer.long_name}
            self.timeline.append(ev)

    def _simulate_penalties(self) -> List[str]:
        """Run a penalty shootout. Returns message lines and updates score."""
        messages: List[str] = []

        def pick_pen_order(team: Teams) -> List[Player]:
            # prefer on-pitch players sorted by mentality_penalties
            starters = [p for p in self._starting_players(team) if not p.isInjured and not p.hasRed]
            bench_ok = [b for b in team.bench if not b.isInjured and not b.hasRed]
            candidates = starters + bench_ok
            def score(p: Player):
                return (p.mentality_penalties or 50) * 2 + (p.overall or 0)
            candidates.sort(key=score, reverse=True)
            # ensure unique takers for the first five kicks
            takers = []
            seen = set()
            for p in candidates:
                key = p.long_name.lower()
                if key in seen:
                    continue
                takers.append(p)
                seen.add(key)
                if len(takers) >= 5:
                    break
            return takers

        home_takers = pick_pen_order(self.home)
        away_takers = pick_pen_order(self.away)

        def keeper_overall(team: Teams) -> int:
            gk = team.players.get("Goalkeeper", [])
            if gk:
                return gk[0].overall or 50
            allp = team.all_players()
            return allp[0].overall if allp else 50

        # opponent keepers
        home_keeper = keeper_overall(self.away)
        away_keeper = keeper_overall(self.home)

        # penalty counters (do NOT add these goals to self.score yet)
        home_pen = 0
        away_pen = 0

        pen_events = []

        # initial 5 alternating kicks: home then away per round
        for i in range(5):
            minute_h = 121 + i * 2
            # home kick
            taker_h = home_takers[i] if i < len(home_takers) else (home_takers[i % len(home_takers)] if home_takers else None)
            if taker_h:
                prob = 0.75 + ((taker_h.mentality_penalties or 50) - 50) / 200.0 - ((home_keeper or 50) - 50) / 300.0
                prob = max(0.05, min(0.95, prob))
                scored_h = random.random() < prob
                if scored_h:
                    home_pen += 1
                pen_events.append((minute_h, self.home.name, taker_h.long_name, scored_h))

            minute_a = minute_h + 1
            taker_a = away_takers[i] if i < len(away_takers) else (away_takers[i % len(away_takers)] if away_takers else None)
            if taker_a:
                prob = 0.75 + ((taker_a.mentality_penalties or 50) - 50) / 200.0 - ((away_keeper or 50) - 50) / 300.0
                prob = max(0.05, min(0.95, prob))
                scored_a = random.random() < prob
                if scored_a:
                    away_pen += 1
                pen_events.append((minute_a, self.away.name, taker_a.long_name, scored_a))

            # early win check: if one team is uncatchable before all 5 kicks, we still record full sequence

        # append pen events to timeline
        for m, team_name, taker_name, scored in pen_events:
            self.timeline.append({"minute": m, "type": "pen", "team": team_name, "taker": taker_name, "scored": scored})

        # sudden death if tied after five each
        sd_index = 0
        while home_pen == away_pen:
            minute_h = 121 + 5 * 2 + sd_index * 2
            taker_h = home_takers[sd_index % len(home_takers)] if home_takers else None
            taker_a = away_takers[sd_index % len(away_takers)] if away_takers else None

            scored_h = False
            scored_a = False
            if taker_h:
                prob = 0.75 + ((taker_h.mentality_penalties or 50) - 50) / 200.0 - ((home_keeper or 50) - 50) / 300.0
                prob = max(0.05, min(0.95, prob))
                scored_h = random.random() < prob
                if scored_h:
                    home_pen += 1
                self.timeline.append({"minute": minute_h, "type": "pen", "team": self.home.name, "taker": taker_h.long_name, "scored": scored_h})

            minute_a = minute_h + 1
            if taker_a:
                prob = 0.75 + ((taker_a.mentality_penalties or 50) - 50) / 200.0 - ((away_keeper or 50) - 50) / 300.0
                prob = max(0.05, min(0.95, prob))
                scored_a = random.random() < prob
                if scored_a:
                    away_pen += 1
                self.timeline.append({"minute": minute_a, "type": "pen", "team": self.away.name, "taker": taker_a.long_name, "scored": scored_a})

            sd_index += 1
            # after both have taken, check if one leads
            if home_pen != away_pen:
                break

        # determine winner and award +1 goal to winner (penalty shootout goals don't count directly)
        if home_pen > away_pen:
            # home wins shootout
            self.score[self.home.name] += 1
            self.timeline.append({"minute": 999, "type": "penwin", "team": self.home.name, "detail": f"{home_pen}-{away_pen}"})
        else:
            self.score[self.away.name] += 1
            self.timeline.append({"minute": 999, "type": "penwin", "team": self.away.name, "detail": f"{away_pen}-{home_pen}"})

        return [ (e['minute'], e) for e in [ev for ev in self.timeline if ev.get('type')=='pen'] ]

    def _simulate_cards(self):
        # For each player, determine yellow/red based on aggression. If a player
        # receives a red card they are removed from their team's active lists.
        yellow_counts = defaultdict(int)

        def _remove_player(team: Teams, player: Player):
            # remove from starting groups
            for grp in list(team.players.keys()):
                team.players[grp] = [x for x in team.players[grp] if x.long_name != player.long_name]
            # remove from bench
            team.bench = [x for x in team.bench if x.long_name != player.long_name]
            player.hasRed = True
            # red card -> suspended for next match
            player.isInjured = True

        for team in (self.home, self.away):
            for p in list(team.all_players()):
                aggr = (p.aggression or 50) / 100.0
                # base probabilities (per player per match)
                yellow_prob = 0.02 * (0.5 + aggr)  # scale 0.01-0.06
                red_prob = 0.002 * (0.5 + aggr)    # scale 0.001-0.006

                # direct red
                if random.random() < red_prob:
                    minute = random.randint(1, 90)
                    self.timeline.append({"minute": minute, "type": "red", "team": team.name, "player": p.long_name})
                    _remove_player(team, p)
                    continue

                # yellow (may lead to second-yellow -> red)
                if random.random() < yellow_prob:
                    yellow_counts[(team.name, p.long_name)] += 1
                    minute = random.randint(1, 90)
                    self.timeline.append({"minute": minute, "type": "yellow", "team": team.name, "player": p.long_name})
                    if yellow_counts[(team.name, p.long_name)] >= 2:
                        # second yellow -> red and send-off
                        minute2 = random.randint(minute, 90)
                        self.timeline.append({"minute": minute2, "type": "red", "team": team.name, "player": p.long_name})
                        _remove_player(team, p)

    def simulate(self) -> dict:
        """Run the match simulation and return a result dict with timeline and score.

        Handles knockout matches with extra time and penalties.
        """
        self.timeline = []
        self.score = {self.home.name: 0, self.away.name: 0}

        # 90 minutes
        self._simulate_goals_period(1, 90, self.AVG_XG)
        # halftime event
        self.timeline.append({"minute": 45, "type": "halftime"})
        self._simulate_cards()
        self._simulate_substitutions()

        messages: List[str] = []

        # if knockout and draw -> extra time
        went_to_et = False
        penalties_messages: List[str] = []
        if self.knockout and self.score[self.home.name] == self.score[self.away.name]:
            went_to_et = True
            # extra time start event
            self.timeline.append({"minute": 91, "type": "et_start"})
            lam_et = self.AVG_XG * (30.0 / 90.0)
            self._simulate_goals_period(91, 120, lam_et)
            # extra time half-time
            self.timeline.append({"minute": 105, "type": "et_half"})
            # cards/subs in ET
            self._simulate_cards()
            self._simulate_substitutions()

            if self.score[self.home.name] == self.score[self.away.name]:
                # penalties start event
                self.timeline.append({"minute": 121, "type": "penalties"})
                pen_ev = self._simulate_penalties()

        # sort timeline and build messages
        self.timeline.sort(key=lambda e: e.get("minute", 0))
        for ev in self.timeline:
            if ev["type"] == "goal":
                messages.append(f"{ev['minute']}' - GOAL - {ev['team']}: {ev['scorer']}")
            elif ev["type"] == "yellow":
                messages.append(f"{ev['minute']}' - YELLOW - {ev['team']}: {ev['player']}")
            elif ev["type"] == "red":
                messages.append(f"{ev['minute']}' - RED - {ev['team']}: {ev['player']}")
            elif ev["type"] == "sub":
                messages.append(f"{ev['minute']}' - SUB - {ev['team']}: OUT {ev['out']} IN {ev['in']}")
            elif ev["type"] == "pen":
                scored = ev.get("scored")
                if scored:
                    messages.append(f"{ev['minute']}' - PENALTY - {ev['team']}: {ev.get('taker')} SCORES")
                else:
                    messages.append(f"{ev['minute']}' - PENALTY - {ev['team']}: {ev.get('taker')} MISSES")
            elif ev["type"] == "penwin":
                messages.append(f"{ev.get('team')} win penalty shootout {ev.get('detail')}")
            elif ev["type"] == "halftime":
                messages.append(f"{ev['minute']}' - HALFTIME")
            elif ev["type"] == "et_start":
                messages.append(f"{ev['minute']}' - EXTRA TIME START")
            elif ev["type"] == "et_half":
                messages.append(f"{ev['minute']}' - EXTRA TIME HALFTIME")
            elif ev["type"] == "penalties":
                messages.append(f"{ev['minute']}' - PENALTIES TO FOLLOW")

        # final score message
        if went_to_et and self.knockout and self.score[self.home.name] == self.score[self.away.name]:
            # penalties decided the winner; final score includes penalties
            score_msg = f"FT (pens) {self.home.name} {self.score[self.home.name]} - {self.score[self.away.name]} {self.away.name}"
        elif went_to_et:
            score_msg = f"AET {self.home.name} {self.score[self.home.name]} - {self.score[self.away.name]} {self.away.name}"
        else:
            score_msg = f"FT {self.home.name} {self.score[self.home.name]} - {self.score[self.away.name]} {self.away.name}"

        messages.append("\n" + score_msg)

        return {"timeline": self.timeline, "messages": messages, "score": self.score}

    def __str__(self) -> str:
        res = self.simulate()
        return "\n".join(res["messages"])


# ── quick demo + Teams test ──────────────────────────────────────────────────
if __name__ == "__main__":
    # small find_players demo
    NAMES_I_WANT = [
        "L. Messi",
        "Cristiano Ronaldo",
        "K. Mbappé",
        "Erling Haaland",
        "R. Alvarado",
    ]

    results = find_players("data/FC26.csv", NAMES_I_WANT)

    if not results:
        print("No players found — check that the names match short_name or long_name in the CSV.")
    else:
        for p in results:
            print(p)

    # Teams builder test
    print("\n=== Teams builder test ===")
    # locate CSV automatically if possible
    data_dir = Path(__file__).parent / "data"
    csv_candidates = list(data_dir.glob("FC26*.csv"))
    csv_path = str(csv_candidates[0]) if csv_candidates else None

    teams = create_teams_from_rosters(csv_path=csv_path)

    # helper to find a team by common name variants (robust to underscores/spaces)
    def _find_team(teams_dict, candidates: list[str]):
        cand_norm = [c.lower().replace('_', ' ').strip() for c in candidates]
        for gk, group in teams_dict.items():
            for tk, t in group.items():
                tk_norm = tk.lower().replace('_', ' ').strip()
                name_norm = t.name.lower().replace('_', ' ').strip()
                for c in cand_norm:
                    if c in tk_norm or c in name_norm:
                        return gk, tk, t
        return None, None, None

    # prefer South Korea vs Mexico if present, else pick first available two teams
    g1, k1, team = _find_team(teams, ["South Korea", "South_Korea", "Korea Republic"])
    g2, k2, team2 = _find_team(teams, ["Mexico"]) if team else (None, None, None)
    if not team or not team2:
        # fallback: pick first group and first two different teams
        team = None
        team2 = None
        for group in teams.values():
            keys = list(group.keys())
            if len(keys) >= 2:
                team = group[keys[0]]
                team2 = group[keys[1]]
                break

    if team:
        print(f"Team: {team.name}")
        for grp in ("Goalkeeper", "Defenders", "Midfielders", "Forwards"):
            print(f"\n{grp}:")
            for p in team.players.get(grp, []):
                print(f" - {p.long_name} ({p.short_name})")

        print("\nBench (first 10):")
        for p in team.bench[:10]:
            print(f" - {p.long_name}")
    else:
        print("No teams available in rosters to display.")

    # Match simulation test
    print("\n=== Match simulation test ===")
    if team and team2:
        home = team
        away = team2
        match = Match(home, away, knockout=True)
        result = match.simulate()
        for line in result["messages"]:
            print(line)


        # show remaining starting players after red cards
        '''
        print("\n=== Post-match remaining starting XI ===")
        for t in (home, away):
            print(f"\n{t.name}:")
            for grp in ("Goalkeeper", "Defenders", "Midfielders", "Forwards"):
                print(f" {grp}:")
                for p in t.players.get(grp, []):
                    print(f"  - {p.long_name}")
    else:
        print("Could not find test teams for match simulation.")'''