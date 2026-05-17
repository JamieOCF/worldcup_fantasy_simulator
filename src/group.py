from typing import Dict, List
import itertools
import random
import json
from pathlib import Path
from models import (
    Teams,
    create_teams_from_rosters,
    sgroups_2026,
    _normalize_key,
    _team_name_match,
)
from match import Match


class GroupTable:
    def __init__(self, teams: list):
        self.teams_objs: dict[str, Teams] = {}
        names: list[str] = []

        for t in teams:
            if isinstance(t, Teams):
                # reset stats for fresh group stage
                t.pts = 0
                t.gf = 0
                t.ga = 0
                self.teams_objs[t.name] = t
                names.append(t.name)
            else:
                names.append(t)

        self.teams = names
        self.table: dict[str, dict] = {
            team: {"pts": 0, "gf": 0, "ga": 0, "gd": 0} for team in self.teams
        }
        self.fixtures: list[tuple[str, str]] = []
        self.matches: list[dict] = []

    def generate_fixtures(self, shuffle: bool = False) -> list:
        fixtures: list[tuple[str, str]] = []
        for a, b in itertools.combinations(self.teams, 2):
            fixtures.append((a, b))
        if shuffle:
            random.shuffle(fixtures)
        self.fixtures = fixtures
        return fixtures

    def simulate_match(self, home_name: str, away_name: str) -> dict:
        home_team = self.teams_objs.get(home_name) or Teams(name=home_name)
        away_team = self.teams_objs.get(away_name) or Teams(name=away_name)

        m = Match(home_team, away_team, knockout=False)
        res = m.simulate()

        score = res.get("score", {})
        home_goals = int(score.get(home_name, 0))
        away_goals = int(score.get(away_name, 0))

        # update table
        self.table[home_name]["gf"] += home_goals
        self.table[home_name]["ga"] += away_goals
        self.table[home_name]["gd"] = (
            self.table[home_name]["gf"] - self.table[home_name]["ga"]
        )

        self.table[away_name]["gf"] += away_goals
        self.table[away_name]["ga"] += home_goals
        self.table[away_name]["gd"] = (
            self.table[away_name]["gf"] - self.table[away_name]["ga"]
        )

        if home_goals > away_goals:
            self.table[home_name]["pts"] += 3
        elif home_goals < away_goals:
            self.table[away_name]["pts"] += 3
        else:
            self.table[home_name]["pts"] += 1
            self.table[away_name]["pts"] += 1

        if isinstance(home_team, Teams):
            home_team.record_match(home_goals, away_goals)
        if isinstance(away_team, Teams):
            away_team.record_match(away_goals, home_goals)

        self.matches.append(
            {
                "home": home_name,
                "away": away_name,
                "score": f"{home_goals}-{away_goals}",
                "timeline": res.get("timeline", []),
            }
        )
        return res

    def simulate_all(self, shuffle_fixtures: bool = False) -> None:
        if not self.fixtures:
            self.generate_fixtures(shuffle=shuffle_fixtures)
        for home, away in self.fixtures:
            self.simulate_match(home, away)

    def standings(self) -> list:
        def sort_key(item):
            name, st = item
            return (-st["pts"], -st["gd"], -st["gf"], name.lower())

        return sorted(self.table.items(), key=sort_key)

    def qualified(self, n: int = 2) -> list:
        s = self.standings()
        return [name for name, _ in s[:n]]

    def __str__(self) -> str:
        rows = [
            "{:<25}{:>4}{:>4}{:>4}{:>4}".format("Team", "Pts", "GF", "GA", "GD")
        ]
        for name, st in self.standings():
            rows.append(
                f"{name:<25}{st['pts']:>4}{st['gf']:>4}{st['ga']:>4}{st['gd']:>4}"
            )
        return "\n".join(rows)


class GroupStage:
    def __init__(
        self,
        rosters: dict | None = None,
        groups: dict | None = None,
        csv_path: str | None = None,
    ):
        # rosters: mapping group_key -> {team_key: Teams}
        if rosters is None:
            try:
                self.rosters = create_teams_from_rosters(csv_path=csv_path)
            except Exception:
                self.rosters = create_teams_from_rosters()
        else:
            self.rosters = rosters

        self.groups_def = sgroups_2026 if groups is None else groups
        self.group_tables: Dict[str, GroupTable] = {}

        # detect any user-supplied custom team names to follow by default
        self.custom_team_names: List[str] = []
        try:
            data_file = Path(__file__).parent / "data" / "playerTeam.json"
            if data_file.exists():
                with open(data_file, encoding="utf-8") as fh:
                    js = json.load(fh)
                    if isinstance(js, dict):
                        self.custom_team_names = list(js.keys())
        except Exception:
            self.custom_team_names = []

        # build GroupTable for each group
        for gk, names in self.groups_def.items():
            gk_norm = _normalize_key(gk)
            resolved = None
            for rk in self.rosters.keys():
                if _normalize_key(rk) == gk_norm:
                    resolved = rk
                    break

            if resolved and self.rosters.get(resolved):
                teams_objs = list(self.rosters[resolved].values())
                gt = GroupTable(teams_objs)
            else:
                gt = GroupTable(list(names))

            self.group_tables[gk] = gt

    # ---------------------------------------------------------
    # NORMAL MODE (terminal)
    # ---------------------------------------------------------

    def generate_all_fixtures(self, shuffle: bool = False) -> None:
        for gt in self.group_tables.values():
            gt.generate_fixtures(shuffle=shuffle)

    def _write_state(self, round_num: int) -> None:
        try:
            state = {"groups": {}}
            for gk3, gt3 in self.group_tables.items():
                state["groups"][gk3] = gt3.table

            out_path = Path(__file__).parent / "groupStage.json"
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2, ensure_ascii=False)

            try:
                cwd_copy = Path.cwd() / "groupStage.json"
                with open(cwd_copy, "w", encoding="utf-8") as fh2:
                    json.dump(state, fh2, indent=2, ensure_ascii=False)
                print(f"Wrote group stage tables to {out_path} and {cwd_copy}")
            except Exception:
                print(f"Wrote group stage tables to {out_path}")
        except Exception as _e:
            print(f"Failed to write group stage state: {_e}")

    def run_all(
        self,
        follow: str | None = None,
        shuffle: bool = False,
        interactive: bool = True,
    ) -> Dict[str, list]:
        # generate fixtures
        self.generate_all_fixtures(shuffle=shuffle)

        # if WorldCup didn't specify follow, fall back to first custom team if present
        if follow is None and self.custom_team_names:
            follow = self.custom_team_names[0]

        pointers: Dict[str, int] = {gk: 0 for gk in self.group_tables.keys()}
        total_remaining = sum(len(gt.fixtures) for gt in self.group_tables.values())
        round_num = 0

        # initial state
        try:
            self._write_state(round_num)
        except Exception:
            pass

        while total_remaining > 0:
            round_num += 1
            print(f"\n=== Round {round_num} — one match per group ===")

            for gk, gt in self.group_tables.items():
                idx = pointers[gk]
                if idx >= len(gt.fixtures):
                    continue

                home, away = gt.fixtures[idx]
                pointers[gk] += 1
                total_remaining -= 1

                res = gt.simulate_match(home, away)

                if follow and (
                    _team_name_match(follow, home)
                    or _team_name_match(follow, away)
                ):
                    print(f"\n>> Follow: {follow} involved in this match")
                    for m in res.get("messages", []):
                        print(m)

            print("\n=== Current Group Standings ===")
            for gk2, gt2 in self.group_tables.items():
                print(f"\n{gk2}:")
                print(gt2)

            try:
                self._write_state(round_num)
            except Exception:
                pass

            if interactive:
                try:
                    input(
                        "\nPress Enter to continue to the next round (or Ctrl+C to stop)..."
                    )
                except KeyboardInterrupt:
                    print("\nSimulation interrupted by user.")
                    break
                except EOFError:
                    print("\nNon-interactive stdin; continuing automatically.")
            else:
                continue

        final = {gk: gt.standings() for gk, gt in self.group_tables.items()}
        try:
            self._write_state(round_num)
        except Exception:
            pass
        return final

    # ---------------------------------------------------------
    # STEP MODE (Flask)
    # ---------------------------------------------------------

    def init_step_mode(self, shuffle=False):
        """Prepare the group stage for step-by-step simulation."""
        self.generate_all_fixtures(shuffle=shuffle)
        self.pointers = {gk: 0 for gk in self.group_tables.keys()}
        self.total_remaining = sum(len(gt.fixtures) for gt in self.group_tables.values())
        self.round_num = 0

    def step(self, follow=None):
        """Simulate exactly ONE round (one match per group)."""
        if self.total_remaining <= 0:
            return {"done": True, "message": "Group stage complete"}

        self.round_num += 1
        round_info = {"round": self.round_num, "matches": []}

        for gk, gt in self.group_tables.items():
            idx = self.pointers[gk]
            if idx >= len(gt.fixtures):
                continue

            home, away = gt.fixtures[idx]
            self.pointers[gk] += 1
            self.total_remaining -= 1

            res = gt.simulate_match(home, away)

            match_info = {
                "group": gk,
                "home": home,
                "away": away,
                "score": res["score"],
                "timeline": res.get("timeline", []),
            }

            if follow and (
                _team_name_match(follow, home)
                or _team_name_match(follow, away)
            ):
                match_info["follow_messages"] = res.get("messages", [])

            round_info["matches"].append(match_info)

        round_info["standings"] = {
            gk: gt.standings() for gk, gt in self.group_tables.items()
        }

        return round_info
