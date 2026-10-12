# Installs the "mathcad-prime" skill for Claude Code.
#   irm https://raw.githubusercontent.com/ZUBENIN-INDUSTRIES/skill_in_using_claude_with_mathcad_prime/main/install.ps1 | iex
# Optional overrides via environment variables before running:
#   $env:MATHCAD_SKILL_PROJECT = '1'   -> install into .\.claude\skills of the current folder instead of the user profile
#   $env:MATHCAD_SKILL_BRANCH  = 'main'
$Owner = 'ZUBENIN-INDUSTRIES'
$Repo = 'skill_in_using_claude_with_mathcad_prime'
$Branch = if ($env:MATHCAD_SKILL_BRANCH) { $env:MATHCAD_SKILL_BRANCH } else { 'main' }
$Project = $env:MATHCAD_SKILL_PROJECT -eq '1'
$ErrorActionPreference = 'Stop'
$root = if ($Project) { Join-Path (Get-Location) '.claude\skills' } else { Join-Path $HOME '.claude\skills' }
$dest = Join-Path $root 'mathcad-prime'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('mathcad-skill-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $tmp, $root | Out-Null
try {
    $zip = Join-Path $tmp 'repo.zip'
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$Owner/$Repo/archive/refs/heads/$Branch.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem -Path $tmp -Directory -Recurse -Filter 'mathcad-prime' | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') } | Select-Object -First 1
    if (-not $src) { throw 'mathcad-prime/SKILL.md not found in the downloaded archive' }
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
    Copy-Item -Recurse -Path $src.FullName -Destination $dest
    Write-Host "Installed to $dest"
    if (Get-Command python -ErrorAction SilentlyContinue) {
        python -m pip install --quiet --disable-pip-version-check pymupdf
        Write-Host 'Python package pymupdf installed (used for PDF checks).'
    } else {
        Write-Host 'Python 3 not found: install it from https://www.python.org/ and run  python -m pip install pymupdf'
    }
    Write-Host 'Restart Claude Code (or start a new session) to load the skill.'
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
