# recalc.ps1 - open a worksheet in Mathcad Prime, recalculate, save as .mcdx and/or export .pdf
# usage: powershell -ExecutionPolicy Bypass -File recalc.ps1 -In <file.mcdx> [-OutMcdx <x.mcdx>] [-OutPdf <x.pdf>]
# Paths must be full and must NOT contain 8.3 short names (C:\Users\ABCD~1\...): SaveAs then fails with E_ABORT.
param(
    [Parameter(Mandatory = $true)][string]$In,
    [string]$OutMcdx,
    [string]$OutPdf,
    [int]$WaitSeconds = 5
)
$ErrorActionPreference = 'Stop'
foreach ($p in @($In, $OutMcdx, $OutPdf)) { if ($p -and $p.Contains('~')) { throw "8.3 short path not allowed: $p" } }
if (-not (Test-Path -LiteralPath $In)) { throw "not found: $In" }
foreach ($p in @($OutMcdx, $OutPdf)) { if ($p -and (Test-Path -LiteralPath $p)) { throw "target exists (delete or choose another name first): $p" } }

$wasRunning = [bool](Get-Process -Name MathcadPrime -ErrorAction SilentlyContinue)
$app = New-Object -ComObject MathcadPrime.Application      # attaches to a running instance if there is one
$app.Visible = $true
$ws = $app.Open((Resolve-Path -LiteralPath $In).Path)
Start-Sleep -Seconds $WaitSeconds
$ws.Synchronize()                                            # full recalculation
if ($OutMcdx) { $ws.SaveAs($OutMcdx) }                       # SaveAs refreshes cached results; Save of an unmodified doc does not
if ($OutPdf) { $ws.SaveAs($OutPdf) }                         # format chosen by extension
$ws.Close(0)                                                 # 0 = do not save again
if (-not $wasRunning) { $app.Quit(0) }                       # never quit the user's own Mathcad session
"ok"
