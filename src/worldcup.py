from typing import Dict, List
from group import GroupStage
from knockout import KnockoutStage
from models import Teams, _team_name_match

class WorldCup:
    def __init__(
        self,
        rosters: dict | None = None,
        groups: dict | None = None,
        csv_path: str | None = None,
    ):
        self.rosters = rosters
        self.groups = groups
        self.csv_path = csv_path

        self.group_stage: GroupStage | None = None
        self.knockout = KnockoutStage()

        # step-mode state
        self.follow = None
        self.bracket = None
        self.knockout_round_order = [
            ("Round of 32", 32),
            ("Round of 16", 16),
            ("Quarterfinals", 8),
            ("Semifinals", 4),
            ("Final", 2),
        ]
        self.current_knockout_index = 0

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    def _init_group_stage(self) -> None:
        if self.group_stage is None:
            self.group_stage = GroupStage(
                rosters=self.rosters,
                groups=self.groups,
                csv_path=self.csv_path,
            )

    def _find_team_object(self, name: str) -> Teams | None:
        if not self.rosters:
            return None
        for grp in self.rosters.values():
            for _, tobj in grp.items():
                if _team_name_match(tobj.name, name):
                    return tobj
        return None

    def _collect_top2(self) -> list:
        assert self.group_stage is not None
        qualifiers = []
        for _, gt in self.group_stage.group_tables.items():
            q = gt.qualified(2)
            for name in q:
                obj = gt.teams_objs.get(name) or self._find_team_object(name)
                qualifiers.append(obj if obj is not None else name)
        return qualifiers

    def _collect_best_thirds(self, needed: int) -> list:
        assert self.group_stage is not None
        thirds = []
        for _, gt in self.group_stage.group_tables.items():
            st = gt.standings()
            if len(st) >= 3:
                name, stats = st[2]
                obj = gt.teams_objs.get(name) or self._find_team_object(name)
                thirds.append((obj if obj is not None else name, stats))

        thirds.sort(
            key=lambda it: (
                -it[1]["pts"],
                -((it[1]["gf"]) - (it[1]["ga"])),
                -it[1]["gf"],
            )
        )
        return [t for t, _ in thirds[:needed]]

    def build_round_of_32(self) -> list:
        top2 = self._collect_top2()
        need = 32 - len(top2)
        best_thirds = self._collect_best_thirds(need)
        return top2 + best_thirds

    # ---------------------------------------------------------
    # TERMINAL MODE (unchanged)
    # ---------------------------------------------------------

    def run(self, interactive_group_stage: bool = True, follow: str | None = None) -> dict:
        self._init_group_stage()

        if interactive_group_stage:
            print("Running interactive group stage (press Enter each round)...")
            self.group_stage.run_all(follow=follow)
        else:
            print("Running non-interactive full group stage...")
            self.group_stage.run_all(follow=follow, interactive=False)

        bracket = self.build_round_of_32()
        if len(bracket) != 32:
            print(f"Warning: expected 32-team bracket but got {len(bracket)} teams")

        current = bracket
        rounds = [
            ("Round of 32", 32),
            ("Round of 16", 16),
            ("Quarterfinals", 8),
            ("Semifinals", 4),
        ]
        winners_map = {}

        for name, _size in rounds:
            if len(current) < 2:
                break
            current = self.knockout.run_round(current, name)
            winners_map[name] = [t.name if isinstance(t, Teams) else t for t in current]

        if len(current) == 2:
            final_winners = self.knockout.run_round(current, "Final")
            champion_obj = final_winners[0]
            champion = champion_obj.name if isinstance(champion_obj, Teams) else champion_obj
        else:
            champion = None

        return {"rounds": self.knockout.rounds, "champion": champion}

    # ---------------------------------------------------------
    # STEP MODE (FLASK)
    # ---------------------------------------------------------

    def init_group_stage_step_mode(self, follow=None):
        self.follow = follow
        self._init_group_stage()
        self.group_stage.init_step_mode()

    def group_stage_step(self):
        """Simulate ONE group-stage round."""
        return self.group_stage.step(follow=self.follow)

    def init_knockout_step_mode(self):
        """Prepare knockout rounds after group stage is finished."""
        self.bracket = self.build_round_of_32()
        self.current_knockout_index = 0

        round_name, _size = self.knockout_round_order[self.current_knockout_index]
        self.knockout.init_step_mode(self.bracket, round_name)

    def knockout_step(self):
        """Simulate ONE knockout match or return final champion."""
        result = self.knockout.step()

        # If current round is not finished, just return this match
        if not result["done"]:
            return result

        # Current round finished → move to next knockout round
        self.current_knockout_index += 1

        # Tournament finished
        if self.current_knockout_index >= len(self.knockout_round_order):
            return {"done": True, "champion": result["winners"][0]}

        # Prepare next round
        winners = result["winners"]
        round_name, _size = self.knockout_round_order[self.current_knockout_index]
        self.knockout.init_step_mode(winners, round_name)

        # ⭐ Immediately step into the next round and return its first match
        next_result = self.knockout.step()
        return next_result

