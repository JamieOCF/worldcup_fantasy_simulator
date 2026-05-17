from pathlib import Path
from models import create_teams_from_rosters
from worldcup import WorldCup

if __name__ == "__main__":
    # locate CSV automatically if possible
    data_dir = Path(__file__).parent / "data"
    csv_candidates = list(data_dir.glob("FC26*.csv"))
    csv_path = str(csv_candidates[0]) if csv_candidates else None

    print("=== Teams builder test ===")
    teams = create_teams_from_rosters(csv_path=csv_path)

    any_team = None
    for group in teams.values():
        for t in group.values():
            any_team = t
            break
        if any_team:
            break

    if any_team:
        print(f"Found team: {any_team.name}")
    else:
        print("No roster-backed teams found; placeholders will be used.")

    # run full WorldCup demo
    try:
        print("\nRunning full WorldCup ...")
        wc = WorldCup(rosters=teams, csv_path=csv_path)
        res = wc.run(interactive_group_stage=True, follow=None)
        print("\nChampion:", res.get("champion"))
    except Exception as e:
        print("WorldCup run failed:", e)