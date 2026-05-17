import os
from pathlib import Path
from models import create_teams_from_rosters
from worldcup import WorldCup

if __name__ == "__main__":
    # 1. Clear out any old web logs from timeline.txt so you have a clean slate
    if os.path.exists("timeline.txt"):
        os.remove("timeline.txt")
        print("🧹 Cleaned old timeline.txt file for a fresh terminal run.")

    # Locate CSV automatically
    data_dir = Path(__file__).parent / "data"
    csv_candidates = list(data_dir.glob("FC26*.csv"))
    csv_path = str(csv_candidates[0]) if csv_candidates else None

    print("\n=== Teams builder test ===")
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

    # Run full WorldCup simulation 
    try:
        print("\n🚀 Running full WorldCup simulation in Terminal...")
        wc = WorldCup(rosters=teams, csv_path=csv_path)
        
        # Set interactive to False so it runs automatically in the background
        res = wc.run(interactive_group_stage=False, follow=None)
        
        print("\n========================================")
        print(f"🏆 TOURNAMENT CHAMPION: {res.get('champion')}")
        print("========================================")
        
        # 2. Verify that the file writing logic in your Match class worked
        if os.path.exists("timeline.txt"):
            print("\n✅ Verification Success: Match logs successfully appended to 'timeline.txt'.")
            with open("timeline.txt", "r", encoding="utf-8") as fh:
                line_count = len(fh.readlines())
            print(f"   The log file contains {line_count} lines of live game data.")
        else:
            print("\n❌ Warning: Simulation completed, but 'timeline.txt' was not generated.")
            
    except Exception as e:
        print("\n💥 WorldCup run failed:", e)