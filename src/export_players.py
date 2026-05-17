from pathlib import Path
import json
from dataclasses import asdict

from models import create_teams_from_rosters


def main():
    teams = create_teams_from_rosters()
    seen = set()
    players = []
    for group in teams.values():
        for team in group.values():
            for p in team.all_players():
                key = (p.short_name.strip().lower(), p.long_name.strip().lower())
                if key in seen:
                    continue
                seen.add(key)
                players.append(asdict(p))

    out_path = Path(__file__).parent / "data" / "players.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(players, fh, indent=2, ensure_ascii=False)

    print(f"Wrote {len(players)} players to {out_path}")


if __name__ == "__main__":
    main()
