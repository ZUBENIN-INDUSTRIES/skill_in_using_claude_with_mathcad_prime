"""measure.py - real heights of top-level regions as computed by Mathcad.

Mathcad renumbers region ids on save, so heights are matched to the ORIGINAL file by order.
usage: python measure.py <original_or_edited.mcdx> <saved_by_mathcad.mcdx> <heights.json>
The json maps original region id -> actualHeight; pass it to Mcdx.relayout(heights).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcdx import Mcdx  # noqa: E402

a = Mcdx.load(sys.argv[1]).top_level()
b = Mcdx.load(sys.argv[2]).top_level()
assert [k for _, k, _, _ in a] == [k for _, k, _, _ in b], ('region kinds differ', [k for _, k, _, _ in a], [k for _, k, _, _ in b])
heights = {str(ra): hb for (ra, ka, _, _), (_, _, _, hb) in zip(a, b) if ka == 'text'}
json.dump(heights, open(sys.argv[3], 'w'), indent=1)
for (ra, ka, ta, ha), (_, _, tb, hb) in zip(a, b):
    print('%5d %-8s top %8.1f -> %8.1f   height %7.1f -> %7.1f%s' % (ra, ka, ta, tb, ha, hb, '   <-- changed' if abs(ha - hb) > 1 else ''))
