from pathlib import Path
import sys
p = Path(__file__).parent / 'src'
if str(p) not in sys.path:
    sys.path.insert(0, str(p))

from group import GroupStage

if __name__ == '__main__':
    gs = GroupStage()
    gs.run_all(interactive=False)
    #print('Done. Check groupStage.json in repository root and src/')
