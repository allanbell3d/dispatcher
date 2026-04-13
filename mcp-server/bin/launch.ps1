# Gate Orchestration — Launch Script
# Creates psmux sessions + PowerShell windows for watcher + all agents.
#
# Usage:
#   pwsh -File D:\IA\orchestration\launch.ps1              # sessions only
#   pwsh -File D:\IA\orchestration\launch.ps1 --claude     # sessions + launch claude in each
#
# Stop:
#   New-Item "gate\STOP" -ItemType File

param(
    [switch]$claude
)

$ErrorActionPreference = "Stop"

$WORKTREE  = "E:\Business\Real Estate\Villa number 2 -60-62\Advert\.worktrees\v2-refactor-phase-d"
$GATE_DIR  = Join-Path $WORKTREE "gate"
$WATCHER   = "D:\IA\orchestration\scripts\watcher.py"
$PYTHON    = "C:\Users\Allan\AppData\Local\Programs\Python\Python312\python.exe"

$pwshCmd = Get-Command pwsh.exe -ErrorAction SilentlyContinue
$pwshExe = if ($pwshCmd) { $pwshCmd.Source } else { 'pwsh.exe' }

# ── Clean state ──────────────────────────────────────────────────────────
if (Test-Path "$GATE_DIR\STOP") { Remove-Item "$GATE_DIR\STOP" -Force }
Get-ChildItem "$GATE_DIR\mailbox\*.pending.md" -ErrorAction SilentlyContinue | ForEach-Object {
    Set-Content $_.FullName "" -NoNewline
}

# ── Helper: create psmux session if needed ───────────────────────────────
function Ensure-PsmuxSession {
    param([string]$Session, [string]$WorkDir)
    $exists = $false
    try {
        psmux has-session -t $Session 2>$null | Out-Null
        $exists = ($LASTEXITCODE -eq 0)
    } catch { $exists = $false }
    if (-not $exists) {
        psmux new-session -d -s $Session -c $WorkDir
        Write-Host "  Created psmux session: $Session" -ForegroundColor DarkGray
    } else {
        Write-Host "  Session exists: $Session" -ForegroundColor DarkGray
    }
}

# ── Helper: open PowerShell window attached to psmux session ─────────────
function Open-AttachedWindow {
    param(
        [string]$Session,
        [string]$WorkDir,
        [string]$Title,
        [string[]]$PreAttachCmds = @()
    )
    $sessionEsc = $Session -replace "'", "''"
    $titleEsc   = $Title -replace "'", "''"

    $bodyLines = @(
        '$ErrorActionPreference = ''Stop''',
        'Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force',
        "`$Host.UI.RawUI.WindowTitle = '$titleEsc'"
    )

    # Optional commands before attaching (e.g., start watcher)
    $bodyLines += $PreAttachCmds

    $bodyLines += @(
        "`$psmuxCmd = Get-Command psmux -ErrorAction Stop",
        "Write-Host 'Attaching to psmux session: $Session' -ForegroundColor Cyan",
        "& `$psmuxCmd.Source a -t '$sessionEsc'"
    )

    $command = '& { ' + ([string]::Join("; ", $bodyLines)) + ' }'
    Start-Process $pwshExe -WorkingDirectory $WorkDir -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-Command',
        $command
    ) | Out-Null
}

# ── Launch watcher ───────────────────────────────────────────────────────
$watcherSession = "gate-watcher"
Write-Host "Launching watcher..." -ForegroundColor Yellow
Ensure-PsmuxSession -Session $watcherSession -WorkDir $WORKTREE

# Send watcher command into the psmux session, then open window attached
psmux send-keys -t $watcherSession "$PYTHON `"$WATCHER`" `"$GATE_DIR`"" Enter

Open-AttachedWindow -Session $watcherSession -WorkDir $WORKTREE -Title "GATE • WATCHER"
Write-Host "  Watcher window opened" -ForegroundColor Green

# ── Agent definitions ────────────────────────────────────────────────────
$agents = @(
    @{ Name="gate-ralph";      Session="gate-ralph" }
    @{ Name="gate-architect";  Session="gate-architect" }
    @{ Name="gate-critic";     Session="gate-critic" }
    @{ Name="gate-playwright"; Session="gate-playwright" }
    @{ Name="gate-monitor";    Session="gate-monitor" }
)

# ── Launch agents ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Launching agents..." -ForegroundColor Yellow

foreach ($agent in $agents) {
    $name    = $agent.Name
    $session = $agent.Session

    Ensure-PsmuxSession -Session $session -WorkDir $WORKTREE
    Open-AttachedWindow -Session $session -WorkDir $WORKTREE -Title "GATE • $($name.ToUpper())"
    Write-Host "  $name window opened (session: $session)" -ForegroundColor Green

    # Launch claude in the session if --claude flag set
    if ($claude) {
        Start-Sleep -Milliseconds 500
        psmux send-keys -t $session "claude" Enter
        Write-Host "    claude started" -ForegroundColor DarkGray
    }

    Start-Sleep -Milliseconds 500
}

# ── Summary ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Gate orchestration launched:" -ForegroundColor Yellow
Write-Host "  gate-watcher    — mailbox distribution + agent wake" -ForegroundColor Cyan
Write-Host "  gate-ralph      — executor" -ForegroundColor Cyan
Write-Host "  gate-architect  — spec reviewer" -ForegroundColor Cyan
Write-Host "  gate-critic     — quality reviewer" -ForegroundColor Cyan
Write-Host "  gate-playwright — tester" -ForegroundColor Cyan
Write-Host "  gate-monitor    — observer" -ForegroundColor Cyan
Write-Host ""
Write-Host "Attach:  psmux a -t gate-ralph" -ForegroundColor DarkGray
Write-Host "Stop:    New-Item '$GATE_DIR\STOP' -ItemType File" -ForegroundColor DarkGray
