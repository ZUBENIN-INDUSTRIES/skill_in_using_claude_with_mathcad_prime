---
name: mathcad-prime
description: Reads, edits and recalculates PTC Mathcad Prime worksheets (.mcdx) and exports them to PDF — changes values, formulas, text and pictures by patching the file's XML, then lets Mathcad recalculate through its COM API and verifies the results and layout. Use when the user mentions Mathcad / Маткад / Mathcad Prime or a .mcdx file and wants to change, fill in, copy for another set of input data, recalculate, check, or export a worksheet to PDF.
---

# Mathcad Prime worksheets

## Contents
- What works and what does not
- Setup check
- Workflow (checklist)
- Rules that prevent the usual mistakes
- Script reference
- Reference files

## What works and what does not
- **Works:** reading any .mcdx; changing numbers, units, formulas, matrices, ranges, user functions, solve-block equations; editing text blocks (incl. inline math); adding / deleting inline regions; replacing pictures; moving regions; recalculation, Save As .mcdx and PDF export through Mathcad; verifying results.
- **Does not:** Mathcad has no API for inserting regions or reading values that are not designated worksheet outputs — all structural edits are done in the file, Mathcad is only used to calculate and export. Build new documents from an existing worksheet (the user's file or a blank one saved by Mathcad), never from nothing.
- Mathcad Prime runs on Windows only; the COM part needs Mathcad installed on this machine.

## Setup check
Run once per session (PowerShell):
```powershell
Test-Path Registry::HKEY_CLASSES_ROOT\MathcadPrime.Application   # True = COM automation available
python --version                                                  # Python 3.8+
python -m pip install pymupdf                                     # only for PDF checks
```

## Workflow (checklist)
`${CLAUDE_SKILL_DIR}` below = the folder containing this SKILL.md. Inside Python/PowerShell code it is NOT expanded automatically if you copy it into a script: write the real path.

Copy into your answer and tick the steps. Do not skip or reorder.
```
- [ ] 1. Located the file; worksheet not open with unsaved edits (see rule 1); work on a copy
- [ ] 1b. Exported a reference PDF of the untouched copy (recalc.ps1 -In copy -OutPdf ref.pdf) to compare against later
- [ ] 2. Dumped regions and texts (mcdx.py dump / texts), mapped what to change by region id
- [ ] 3. Computed the expected results independently (e.g. numpy) BEFORE editing
- [ ] 4. Wrote an edit script using mcdx.py (no hand edits of XML); every replacement asserted
- [ ] 5. recalc.ps1 -> saved copy + PDF in a temp folder with a plain (non-8.3) path
- [ ] 6. check.py: 0 problems, values equal the expected ones
- [ ] 7. Looked at every PDF page: no overlaps, no wrapped lines, page count = ref.pdf
- [ ] 8. If heights changed: measure.py -> relayout -> repeat 5-7
- [ ] 9. Final SaveAs to the destination (never overwrite without asking); report what changed
```

Minimal edit script:
```python
import sys; sys.path.insert(0, r"${CLAUDE_SKILL_DIR}/scripts")
from mcdx import *
doc = Mcdx.load(r"C:/work/in.mcdx")
doc.set_value(doc.find_define("L_1"), 4.5)                         # L_1 := 4.5 m
doc.set_define(31, "A", ap("mult", ident("b"), ident("h")))        # A := b·h = …  (keeps '=' if region had it)
doc.replace_text(0, ">Case 1.<", ">Case 2.<")                      # text inside a text block
doc.save(r"C:/work/out.mcdx")
```
```powershell
powershell -ExecutionPolicy Bypass -File "${CLAUDE_SKILL_DIR}/scripts/recalc.ps1" -In C:\work\out.mcdx -OutMcdx C:\work\out_calc.mcdx -OutPdf C:\work\out_calc.pdf
python "${CLAUDE_SKILL_DIR}/scripts/check.py" C:\work\out_calc.mcdx C:\work\out_calc.pdf C:\work
```

## Rules that prevent the usual mistakes
1. **Open documents.** `Get-Process MathcadPrime | Select MainWindowTitle` — if the user has the file open, ask them to save and close it first; otherwise their unsaved edits and yours overwrite each other.
2. **Never hand-edit XML, never regex-replace globally.** Use `Mcdx` methods; each one asserts it matched exactly once. Snapshot a region string only after all attribute changes on it (string replace of a stale snapshot silently does nothing).
3. **Text blocks hold inline math anchored by character position** (`text-caret-position`). Any text change that alters length shifts them. Edit text only via `replace_text` / `edit_xaml` / `clone_inline` / `delete` — they recompute positions. Details: [reference/text-blocks.md](reference/text-blocks.md).
4. **Names are structured**, not plain strings: `L_1` = L with literal subscript 1. Build math with `ident`, `num`, `qty`, `ap`, `fn`, `par`, `chain`, `matrix`. Element catalog: [reference/math-xml.md](reference/math-xml.md).
5. **Check ORIGIN** (`doc.settings()['array-origin']`) before writing indices.
6. **Mathcad recalculates only on open/SaveAs.** `result.xml` in an edited file is stale; read results only from the copy saved by `recalc.ps1`. Values cannot be read through COM unless regions are designated outputs (they return NaN) — use `check.py`.
7. **Layout is your job.** Region ids are renumbered on save; top-level `top` snaps to an 18.9 px grid; a grown text block does not push regions below it — they overlap. Prefer edits that keep heights (put an extra formula on the same line, fit pictures into the old box); otherwise do the measured second pass. Details: [reference/layout.md](reference/layout.md).
8. **COM etiquette.** `New-Object -ComObject MathcadPrime.Application` attaches to the user's running Mathcad: only `Close(0)` your worksheet, `Quit` only if you started Mathcad (recalc.ps1 does this). Paths with `~` (8.3 short names) make SaveAs fail with E_ABORT. Details: [reference/automation.md](reference/automation.md).
9. **Verify like a reviewer.** Results vs independent calculation, then every PDF page; an extra page or a wrapped line means something moved. Details: [reference/verification.md](reference/verification.md).
10. **Keep the user's content.** Change only what was asked. If something in the worksheet looks wrong, you usually lack the source it was built from (drawing, spec, textbook): report it as a question with your reasoning, do not fix it unasked. Fix only errors you can prove from the worksheet itself (e.g. an index pointing at the wrong vector element), only in new copies, and say exactly what and why.
11. **PowerShell mangles inline `python -c` code** containing `[ ]`, quotes or `$` — put Python into .py files.

## Script reference
| Script | Purpose |
|---|---|
| `${CLAUDE_SKILL_DIR}/scripts/mcdx.py` | library + CLI `dump` / `texts` / `region <id>` (raw XML of one region) — stdlib only |
| `${CLAUDE_SKILL_DIR}/scripts/recalc.ps1` | open in Mathcad, recalc, SaveAs .mcdx / .pdf |
| `${CLAUDE_SKILL_DIR}/scripts/check.py` | input definitions, computed results, calculation errors, PDF pages → PNG |
| `${CLAUDE_SKILL_DIR}/scripts/measure.py` | real heights after a Mathcad save → json for `relayout` |

`Mcdx` methods: `load/save`, `get(rid)` (raw XML), `settings`, `get/put/delete`, `find_define`, `set_value`, `set_define`, `set_eval`, `set_math`, `attr/set_attr`, `top_level`, `text`, `replace_text`, `edit_xaml`, `clone_inline(src, where='after'|'before'|'paragraph', anchor_rid)`, `host_block`, `replace_picture(rid, png, fit='box'|'width')`, `relayout(heights)`.

## Reference files
- [reference/file-format.md](reference/file-format.md) — package layout, worksheet.xml, result.xml, settings, pictures, plots, solve blocks
- [reference/math-xml.md](reference/math-xml.md) — how definitions, operators, units, matrices, functions are written
- [reference/text-blocks.md](reference/text-blocks.md) — XAML text, inline regions, caret positions, adding/removing inline math
- [reference/layout.md](reference/layout.md) — coordinates, grid, page breaks, pictures, two-pass relayout
- [reference/automation.md](reference/automation.md) — COM API, what it can and cannot do, errors
- [reference/verification.md](reference/verification.md) — reading results, PDF checks, alignment by text layer
