# Layout

## Contents
- Coordinates
- Why things overlap
- Avoiding height changes
- Two-pass relayout
- Pictures
- Page breaks

## Coordinates
- Units are WPF px (1/96 in). A4 page content width ≈ 642.5 px (17 cm).
- Top-level `top` is snapped by Mathcad to a grid of 18.8976 px (0.5 cm) — you can place a region only on grid lines; sub-grid alignment is impossible (Margin/LineHeight are ignored).
- `actualWidth/actualHeight` in the file are what Mathcad computed last time; for edited regions they are stale until Mathcad saves the file. Some math regions keep stale sizes even then — measure from the PDF.

## Why things overlap
Mathcad does not move regions when a text block grows; the block simply runs into the next region. Typical causes: an extra paragraph, a wrapped long line, a taller matrix, a bigger picture.

## Avoiding height changes
1. Put an added formula on an existing line (`clone_inline(..., where='after'|'before')`).
2. Keep sentences short enough not to wrap; widen a narrow text block instead (`set_attr(rid, 'width', 560)` and `actualWidth`).
3. Fit a new picture into the old box (`replace_picture(rid, png, fit='box')`).
4. Long equations that wrap: widen their text regions (solve-block constraints too).

## Two-pass relayout
```text
edit -> save edited.mcdx -> recalc.ps1 (OutMcdx pass1.mcdx)
python measure.py edited.mcdx pass1.mcdx heights.json     # real heights, matched by order
doc = Mcdx.load('edited.mcdx'); doc.relayout({int(k): v for k, v in json.load(open('heights.json')).items()}); doc.save(...)
recalc.ps1 again -> check PDF
```
`relayout` keeps the original vertical gaps between consecutive top-level regions and snaps to the grid.
Do the edits again from the original template in pass 2 (scripts are idempotent that way), not on top of pass 1.

## Pictures
- `fit='box'` keeps the old height and centres the narrower/wider image in the old box — no layout change.
- `fit='width'` (with `width=`) keeps width and lets height follow — use with relayout.
- Draw replacement images with the same aspect ratio as the old box when possible.

## Page breaks
Content that crosses a page bottom is pushed to the next page in the PDF and can land on the next region. After any change compare the PDF page count with the original and look at the top of every page.
