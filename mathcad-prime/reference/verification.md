# Verification

## Contents
- Results
- PDF
- Measuring alignment from the PDF
- Before reporting

## Results
```powershell
python "${CLAUDE_SKILL_DIR}/scripts/check.py" C:\work\file_calc.mcdx C:\work\file_calc.pdf C:\work
```
- Prints input definitions (`in  … := value`, read from the worksheet — confirm your edits there), each evaluated region with its computed value(s), and every region with an error or non-synchronized status; `problems: 0` is required.
- Values are in SI base units (m, kg, s, N, Pa, rad…) regardless of the display unit.
- Compare with your independent calculation (numpy, `cmath`) to at least 4 significant digits. A mismatch means a wrong formula or sign — fix and rerun, do not adjust the expectation.
- Region ids in the saved file differ from your edited file (renumbered); match by order or by the printed formula.

## PDF
- `check.py` renders every page to PNG — open and look at each one.
- Same page count as `ref.pdf` exported from the untouched copy in step 1b (an extra, almost empty page = overflow).
- No overlaps, no line wrapped by your change, plots fully on one page, pictures not distorted.

## Measuring alignment from the PDF
The exported PDF has a text layer; positions are reliable even when `actualWidth/Height` in the file are stale:
```python
import pymupdf
page = pymupdf.open(r"C:/work/file_calc.pdf")[1]
for x0, y0, x1, y1, word, *_ in page.get_text("words"):
    print(round(x0), round((y0 + y1) / 2), word)
```
Use it to align labels with matrix rows, find where a block really ends, etc. PDF units are pt (1 pt = 96/72 px).

## Before reporting
Tell the user: what was changed, the key results, anything you could not verify, and any error you found in their original worksheet (fixed only in the new copy).
