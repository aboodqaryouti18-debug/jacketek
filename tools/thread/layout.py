"""One coordinate system for the six-post composition: the profile grid (Instagram shows
the centre 3:4 of each 4:5 post; the panels tile edge to edge).
  G = (column offset + (x - ox), row * 1350 + y)   in output px of the 1080x1350 posts
Top row 01 02 03, bottom row 04 05 06 (as in profile_grid_01-06.jpg)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
import compose as C
S = C.S
PW = {"POST_01": 667, "POST_02": 666, "POST_03": 667, "POST_04": 667, "POST_05": 666, "POST_06": 667}
POS = {"POST_01": (0, 0), "POST_02": (1, 0), "POST_03": (2, 0), "POST_04": (0, 1), "POST_05": (1, 1), "POST_06": (2, 1)}
STYLE = {"POST_01": "navy", "POST_02": "beige", "POST_03": "navy", "POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}
COL_X = [0, 667 * S, (667 + 666) * S]          # column offsets in G
GW, GH = 2000 * S, 2 * 1350

def ox(post):
    return (1080 - PW[post] * S) / 2

def offset(post):
    """output px (x, y) of this post -> G: add (dx, dy)"""
    c, r = POS[post]
    return COL_X[c] - ox(post), r * 1350
