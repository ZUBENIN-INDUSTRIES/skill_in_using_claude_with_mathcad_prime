"""check.py - verify a worksheet SAVED BY MATHCAD (after recalc.ps1) and its PDF.

usage: python check.py <saved.mcdx> [<exported.pdf> <png_out_dir>]
Prints: every evaluated region with its numeric result, calculation errors / non-synchronized results,
and (if a PDF is given) the page count and one PNG per page (needs: pip install pymupdf).
"""
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcdx import Mcdx, readable  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
mc = sys.argv[1]
doc = Mcdx.load(mc)
res = zipfile.ZipFile(mc).read('mathcad/result.xml').decode('utf-8')
data = {}
for m in re.finditer(r'<resultData result-id="(\d+)"([^>]*?)(/>|>(.*?)</resultData>)', res, re.S):
    status = re.search(r'calculation-status="(\w+)"', m.group(2))
    data[int(m.group(1))] = (status.group(1) if status else '', m.group(4) or '')
bad = 0
for m in re.finditer(r'<region region-id="(\d+)"[^>]*><math resultRef="(\d+)">(.*?)</math>', doc.ws, re.S):
    rid, ref, body = int(m.group(1)), int(m.group(2)), m.group(3)
    st, payload = data.get(ref, ('missing', ''))
    err = re.search(r'<(?:\w+:)?error[^>]*>|error-?\w*="[^"]+"', payload)
    vals = re.findall(r'<ml:real>([^<]*)</ml:real>', payload) + re.findall(r'<ml:imag[^>]*>([^<]*)</ml:imag>', payload)
    if err or st not in ('Synchronized', ''):
        bad += 1
        print('!! region %d status=%s %s :: %s' % (rid, st, err.group(0) if err else '', readable(body)[:120]))
    elif '<ml:define>' in body and '<ml:eval>' not in body and '<ml:real>' in body:
        print('   in  %d :: %s' % (rid, readable(body)[:100]))
    elif '<ml:eval>' in body and vals:
        print('   region %d = %s :: %s' % (rid, ' '.join(v[:10] for v in vals[:6]), readable(body)[:100]))
print('problems:', bad)
if len(sys.argv) > 3:
    import pymupdf
    pdf, outdir = sys.argv[2], sys.argv[3]
    d = pymupdf.open(pdf)
    print('pdf pages:', d.page_count)
    base = os.path.splitext(os.path.basename(pdf))[0]
    for i in range(d.page_count):
        d[i].get_pixmap(dpi=70).save(os.path.join(outdir, '%s_p%d.png' % (base, i + 1)))
