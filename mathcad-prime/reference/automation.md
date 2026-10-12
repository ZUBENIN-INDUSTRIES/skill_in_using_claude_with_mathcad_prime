# Mathcad Prime COM automation

## Contents
- Availability
- The calls that matter
- What the API cannot do
- Errors and their causes

## Availability
`Test-Path Registry::HKEY_CLASSES_ROOT\MathcadPrime.Application` → True. Installed under `C:\Program Files\PTC\Mathcad Prime <ver>`.

## The calls that matter
```powershell
$app = New-Object -ComObject MathcadPrime.Application   # attaches to a running Mathcad if any
$app.Visible = $true                                     # recalculation is reliable with a visible window
$ws  = $app.Open("C:\work\file.mcdx")
Start-Sleep 5; $ws.Synchronize()                         # full recalculation
$ws.SaveAs("C:\work\file_calc.mcdx")                     # writes fresh result.xml
$ws.SaveAs("C:\work\file_calc.pdf")                      # format by extension
$ws.Close(0)                                             # close without saving
$app.Quit(0)                                             # only if you started Mathcad
```
`scripts/recalc.ps1` wraps exactly this, refuses 8.3 paths and existing targets, and quits only if Mathcad was not running before.

## What the API cannot do
- Insert, delete or move regions; edit formulas → do it in the file.
- Read arbitrary values: `OutputGetRealValue(name)` works only for regions designated as outputs in the worksheet (otherwise `NaN`, ErrorCode 1) → read `result.xml` of the saved copy (`check.py`).
- `$ws.Save()` on a document Mathcad thinks is unmodified writes nothing new → always `SaveAs` to a new path.

## Errors and their causes
| Symptom | Cause / fix |
|---|---|
| SaveAs throws `E_ABORT (0x80004004)` | path contains an 8.3 short name (`C:\Users\ABCD~1\…`) or is too long → use a plain path like `C:\Users\<name>\AppData\Local\Temp\work\` |
| Results unchanged after Open+Save | hidden window / Save instead of SaveAs → Visible, Synchronize, SaveAs |
| User's Mathcad closed by your script | you called Quit on an attached instance → check `Get-Process MathcadPrime` first |
| File opens with errors (red regions) | malformed math XML (wrong nesting, missing operand) → diff your region against a working one |
| Your edits lost / user's edits lost | the file was open in Mathcad while you wrote it → ask the user to save & close |
