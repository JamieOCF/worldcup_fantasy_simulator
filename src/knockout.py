from typing import List, Dict
from models import Teams
from match import Match


class KnockoutStage:
    def __init__(self):
        self.rounds: Dict[str, list] = {}

        # step-mode state
        self.current_round_name = None
        self.current_pairs = []
        self.current_index = 0
        self.current_winners = []

    # ---------------------------------------------------------
    # PAIRING
    # ---------------------------------------------------------

    def pair_teams(self, teams: list) -> list[tuple[str, str]]:
        pairs = []
        left = 0
        right = len(teams) - 1
        while left < right:
            pairs.append((teams[left], teams[right]))
            left += 1
            right -= 1
        return pairs

    # ---------------------------------------------------------
    # NORMAL TERMINAL MODE
    # ---------------------------------------------------------

    def run_round(self, teams: list, round_name: str) -> list:
        print(f"\n--- Knockout: {round_name} ({len(teams)} teams) ---")
        pairs = self.pair_teams(teams)
        winners = []
        results = []

        for a, b in pairs:
            home = a if isinstance(a, Teams) else Teams(name=a)
            away = b if isinstance(b, Teams) else Teams(name=b)

            print(f"{home.name} vs {away.name}")
            m = Match(home, away, knockout=True)
            res = m.simulate()

            for line in res.get("messages", []):
                print(line)

            score = res.get("score", {})
            if int(score.get(home.name, 0)) > int(score.get(away.name, 0)):
                winners.append(home)
            else:
                winners.append(away)

            results.append({
                "home": home.name,
                "away": away.name,
                "score": res.get("score")
            })

        self.rounds[round_name] = results
        return winners

    # ---------------------------------------------------------
    # STEP MODE (FLASK)
    # ---------------------------------------------------------

    def init_step_mode(self, teams: list, round_name: str):
        """Prepare knockout round for step-by-step simulation."""
        self.current_round_name = round_name
        self.current_pairs = self.pair_teams(teams)
        self.current_index = 0
        self.current_winners = []
        self.rounds[round_name] = []  # prepare storage

    def step(self):
        """Simulate exactly ONE knockout match."""
        if self.current_index >= len(self.current_pairs):
            return {
                "done": True,
                "message": f"{self.current_round_name} complete",
                "winners": [t.name if isinstance(t, Teams) else t for t in self.current_winners]
            }

        a, b = self.current_pairs[self.current_index]
        self.current_index += 1

        home = a if isinstance(a, Teams) else Teams(name=a)
        away = b if isinstance(b, Teams) else Teams(name=b)

        m = Match(home, away, knockout=True)
        res = m.simulate()

        score = res.get("score", {})
        winner = home if int(score.get(home.name, 0)) > int(score.get(away.name, 0)) else away
        self.current_winners.append(winner)

        match_info = {
            "round": self.current_round_name,
            "match_number": self.current_index,
            "home": home.name,
            "away": away.name,
            "score": score,
            "timeline": res.get("timeline", []),
            "messages": res.get("messages", [])
        }

        # store result
        self.rounds[self.current_round_name].append(match_info)

        return {
            "done": False,
            "match": match_info
        }
