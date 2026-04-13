# orch_launcher.ps1
# Orchestrator Control Panel — PowerShell 7 TUI
# Pattern: mma-launcher_v8.ps1 (New-MenuItem + Read-ArrowMenu + Build-*Menu + dispatch)
# Keys: Up/Down select - Enter/Right confirm - Esc cancel/back - Left back

param(
    [switch]$DryRun,
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

# -----------------------------
# CONFIG LOADING
# -----------------------------
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
# Default: launcher lives at dispatcher/orchestrator/bin/, project root is 3 levels up
$DEFAULT_PROJECT_ROOT = (Resolve-Path (Join-Path $SCRIPT_DIR "..\..\..")).Path

# State file: remembers last-used project
$STATE_FILE = Join-Path $env:USERPROFILE ".orchestrator_launcher_state.json"

function Get-LastProjectRoot {
    if (Test-Path $STATE_FILE) {
        try {
            $state = Get-Content $STATE_FILE -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($state.project_root -and (Test-Path $state.project_root)) {
                return $state.project_root
            }
        } catch {}
    }
    return $DEFAULT_PROJECT_ROOT
}

function Save-ProjectRoot([string]$Root) {
    @{ project_root = $Root; updated = (Get-Date -Format "o") } |
        ConvertTo-Json | Set-Content $STATE_FILE -Encoding UTF8
}

# Apply -ProjectRoot parameter or use last-used/default
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Get-LastProjectRoot
} else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

$OrcDir      = Join-Path $ProjectRoot ".orchestrator"
$ConfigPath  = Join-Path $OrcDir "config.json"
$DispatchDir = Join-Path $ProjectRoot "dispatch"

function Load-Config {
    if (-not (Test-Path $ConfigPath)) {
        Write-Host "WARNING: No config at $ConfigPath" -ForegroundColor Yellow
        return $null
    }
    return Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
}

$Config = Load-Config

function Get-AgentNames {
    if (-not $Config -or -not $Config.agents) { return @() }
    return @($Config.agents | ForEach-Object { $_["name"] })
}

function Get-SessionPrefix {
    if ($Config -and $Config.session -and $Config.session.session_prefix) {
        return $Config.session.session_prefix
    }
    return "gate-"
}

function Resolve-OrcPath([string]$Key) {
    if (-not $Config -or -not $Config.paths -or -not $Config.paths[$Key]) { return $null }
    return Join-Path $ProjectRoot $Config.paths[$Key]
}

# Paths derived from config
$LogsDir         = Resolve-OrcPath "logs_dir"
$RuntimeDir      = Resolve-OrcPath "runtime_dir"
$TasksFile       = Resolve-OrcPath "tasks_file"
$CurrentTaskFile = Resolve-OrcPath "current_task_file"
$PlanFile        = Resolve-OrcPath "plan_file"
$ApprovalsDir    = Resolve-OrcPath "approvals_dir"
$DiffsDir        = Resolve-OrcPath "diffs_dir"

# Fixed paths (not in config)
$HaltsDir          = Join-Path $OrcDir "halts"
$RuntimeFlagsDir   = Join-Path $OrcDir "runtime_flags"
$MergedVerdictsDir = Join-Path $OrcDir "merged_verdicts"
$TrackersFile      = Join-Path $OrcDir "trackers.json"
$SprintProfilesDir = Join-Path $OrcDir "sprint_profiles"
$AuditLogPath      = if ($LogsDir) { Join-Path $LogsDir "audit.log" } else { $null }
$DecisionTracePath = if ($LogsDir) { Join-Path $LogsDir "decision_trace.log" } else { $null }

$RolesJsonPath     = Join-Path $env:USERPROFILE ".claude\hooks\roles.json"
$SettingsLocalPath = Join-Path $ProjectRoot ".claude\settings.local.json"

# Python
$PYTHON_EXE = if ($env:PYTHON) { $env:PYTHON } else { "python" }

# -----------------------------
# THEMES
# -----------------------------
$THEMES = @{
    default = @{
        Accent    = [ConsoleColor]::Cyan
        Title     = [ConsoleColor]::Cyan
        Highlight = [ConsoleColor]::White
        Divider   = [ConsoleColor]::DarkGray
    }
    sprint = @{
        Accent    = [ConsoleColor]::Green
        Title     = [ConsoleColor]::Green
        Highlight = [ConsoleColor]::White
        Divider   = [ConsoleColor]::DarkGreen
    }
}

function Get-Theme {
    $sprintActive = $false
    if ((Test-Path $RolesJsonPath)) {
        try {
            $rc = Get-Content $RolesJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
            $sprintActive = $rc["hooks_config"]["sprint_active"] -eq $true
        } catch {}
    }
    if ($sprintActive) { return $THEMES.sprint }
    return $THEMES.default
}

# -----------------------------
# UI FRAMEWORK (from mma-launcher_v8.ps1)
# -----------------------------
function Write-Box {
    param(
        [Parameter(Mandatory=$true)][string]$Title,
        [string[]]$Lines = @(),
        [ConsoleColor]$TitleColor = [ConsoleColor]::Cyan,
        [ConsoleColor]$DividerColor = [ConsoleColor]::DarkGray
    )
    $all = @($Title) + $Lines
    $w = ($all | Measure-Object -Property Length -Maximum).Maximum
    if (-not $w) { $w = 10 } else { $w = [Math]::Max($w, 10) }
    $top = [string][char]0x250C + ([string][char]0x2500 * ($w + 2)) + [string][char]0x2510
    $mid = [string][char]0x251C + ([string][char]0x2500 * ($w + 2)) + [string][char]0x2524
    $bot = [string][char]0x2514 + ([string][char]0x2500 * ($w + 2)) + [string][char]0x2518

    Write-Host $top -ForegroundColor $DividerColor
    Write-Host ("| " + $Title.PadRight($w) + " |") -ForegroundColor $TitleColor
    if ($Lines.Count -gt 0) {
        Write-Host $mid -ForegroundColor $DividerColor
        foreach ($l in $Lines) {
            Write-Host ("| " + $l.PadRight($w) + " |") -ForegroundColor DarkGray
        }
    }
    Write-Host $bot -ForegroundColor $DividerColor
}

function New-MenuItem {
    param(
        [Parameter(Mandatory=$true)][AllowEmptyString()][string]$Label,
        [AllowNull()]$Value,
        [bool]$Selectable = $true
    )
    [pscustomobject]@{ Label=$Label; Value=$Value; Selectable=$Selectable }
}

function Read-ArrowMenu {
    param(
        [Parameter(Mandatory=$true)][string]$Header,
        [Parameter(Mandatory=$true)][string]$Hint,
        [Parameter(Mandatory=$true)][array]$Items,
        [string]$Breadcrumb = "",
        [string]$Status = "",
        [ConsoleColor]$AccentColor = [ConsoleColor]::Cyan,
        [ConsoleColor]$TitleColor  = [ConsoleColor]::Cyan,
        [ConsoleColor]$DividerColor = [ConsoleColor]::DarkGray,
        [int]$InitialPos = 0
    )
    $selectables = @()
    for ($i=0; $i -lt $Items.Count; $i++) { if ($Items[$i].Selectable) { $selectables += $i } }
    if ($selectables.Count -eq 0) { return @{ action="cancel"; item=$null } }

    $selPos = if ($InitialPos -ge 0 -and $InitialPos -lt $selectables.Count) { $InitialPos } else { 0 }

    function Render {
        Clear-Host
        $lines = @()
        if (-not [string]::IsNullOrWhiteSpace($Breadcrumb)) { $lines += $Breadcrumb }
        if (-not [string]::IsNullOrWhiteSpace($Status))     { $lines += $Status }
        $lines += ([string][char]0x2501 * 39)
        $lines += $Hint
        $lines += "Up/Down select  -  Enter confirm  -  Esc back"

        Write-Box -Title $Header -Lines $lines -TitleColor $TitleColor -DividerColor $DividerColor
        Write-Host ""

        for ($i=0; $i -lt $Items.Count; $i++) {
            $it = $Items[$i]
            if (-not $it.Selectable) { Write-Host ("   " + $it.Label) -ForegroundColor $DividerColor; continue }
            $isSelected = ($selectables[$selPos] -eq $i)
            if ($isSelected) { Write-Host ("> " + $it.Label) -ForegroundColor $AccentColor -BackgroundColor Black }
            else             { Write-Host ("   " + $it.Label) -ForegroundColor White }
        }
    }

    Render
    while ($true) {
        $k = [Console]::ReadKey($true)
        switch ($k.Key) {
            'UpArrow'    { $selPos--; if ($selPos -lt 0) { $selPos = $selectables.Count - 1 }; Render }
            'DownArrow'  { $selPos++; if ($selPos -ge $selectables.Count) { $selPos = 0 }; Render }
            'Enter'      { return @{ action="select"; item=$Items[$selectables[$selPos]] } }
            'RightArrow' { return @{ action="select"; item=$Items[$selectables[$selPos]] } }
            'Escape'     { return @{ action="cancel"; item=$null } }
            'LeftArrow'  { return @{ action="back"; item=$null } }
            default      { }
        }
    }
}

function Read-CheckboxMenu {
    param(
        [Parameter(Mandatory=$true)][string]$Header,
        [Parameter(Mandatory=$true)][string]$Hint,
        [Parameter(Mandatory=$true)][string[]]$Items,
        [hashtable]$Checked = @{},
        [ConsoleColor]$AccentColor  = [ConsoleColor]::Cyan,
        [ConsoleColor]$TitleColor   = [ConsoleColor]::Cyan,
        [ConsoleColor]$DividerColor = [ConsoleColor]::DarkGray
    )

    # Default all items to checked if not specified
    foreach ($item in $Items) {
        if (-not $Checked.ContainsKey($item)) { $Checked[$item] = $true }
    }

    $selPos = 0

    function RenderCheckbox {
        Clear-Host
        $lines = @(
            ([string][char]0x2501 * 39),
            $Hint,
            "Up/Down select  -  Space toggle  -  Enter confirm"
        )
        Write-Box -Title $Header -Lines $lines -TitleColor $TitleColor -DividerColor $DividerColor
        Write-Host ""
        for ($i = 0; $i -lt $Items.Count; $i++) {
            $name = $Items[$i]
            $mark = if ($Checked[$name]) { "[+]" } else { "[ ]" }
            if ($i -eq $selPos) {
                Write-Host ("> $mark $name") -ForegroundColor $AccentColor -BackgroundColor Black
            } else {
                Write-Host ("   $mark $name") -ForegroundColor White
            }
        }
    }

    RenderCheckbox
    while ($true) {
        $k = [Console]::ReadKey($true)
        switch ($k.Key) {
            'UpArrow'   { $selPos--; if ($selPos -lt 0) { $selPos = $Items.Count - 1 }; RenderCheckbox }
            'DownArrow' { $selPos++; if ($selPos -ge $Items.Count) { $selPos = 0 }; RenderCheckbox }
            'Spacebar'  { $Checked[$Items[$selPos]] = -not $Checked[$Items[$selPos]]; RenderCheckbox }
            'Enter'     { return @($Items | Where-Object { $Checked[$_] }) }
            'Escape'    { return $null }
            default     { }
        }
    }
}

function Pause-Notice([string]$Message) {
    Write-Host ""
    if (-not [string]::IsNullOrWhiteSpace($Message)) {
        Write-Host $Message -ForegroundColor Yellow
    }
    Write-Host "Press any key to continue..." -ForegroundColor DarkGray
    [void][Console]::ReadKey($true)
}

function Prompt-TextValue {
    param(
        [Parameter(Mandatory=$true)][string]$Prompt,
        [string]$Default = "",
        [bool]$AllowEmpty = $false
    )
    while ($true) {
        if ([string]::IsNullOrWhiteSpace($Default)) {
            $value = Read-Host $Prompt
        } else {
            $value = Read-Host "$Prompt [$Default]"
            if ([string]::IsNullOrWhiteSpace($value)) { $value = $Default }
        }
        if ($AllowEmpty -or -not [string]::IsNullOrWhiteSpace($value)) { return $value }
        Write-Host "Value cannot be empty." -ForegroundColor Red
    }
}

function Prompt-YesNo {
    param(
        [Parameter(Mandatory=$true)][string]$Prompt,
        [bool]$DefaultYes = $true
    )
    $suffix = if ($DefaultYes) { "[Y/n]" } else { "[y/N]" }
    while ($true) {
        $answer = Read-Host "$Prompt $suffix"
        if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
        switch ($answer.Trim().ToLowerInvariant()) {
            "y" { return $true }  "yes" { return $true }
            "n" { return $false } "no"  { return $false }
            default { Write-Host "Please answer y or n." -ForegroundColor Red }
        }
    }
}

function Escape-PSString([string]$Value) {
    if ($null -eq $Value) { return "" }
    return $Value.Replace("'", "''")
}

# -----------------------------
# NAV STACKS (from mma-launcher_v8.ps1)
# -----------------------------
$BackStack    = New-Object System.Collections.Generic.Stack[hashtable]
$ForwardStack = New-Object System.Collections.Generic.Stack[hashtable]

function Push-State([hashtable]$s) { $BackStack.Push($s); $ForwardStack.Clear() }
function Go-Back {
    if ($BackStack.Count -le 1) { return }
    $cur = $BackStack.Pop()
    $ForwardStack.Push($cur)
}
function Cur { if ($BackStack.Count -eq 0) { return $null } $BackStack.Peek() }

function Reset-ToHome {
    while ((Cur).id -ne "main" -and $BackStack.Count -gt 1) { Go-Back }
}

function Get-Breadcrumbs {
    $arr = $BackStack.ToArray()
    [Array]::Reverse($arr)
    $crumbs = @()
    foreach ($s in $arr) {
        if ($null -ne $s.crumb -and -not [string]::IsNullOrWhiteSpace($s.crumb)) { $crumbs += $s.crumb }
    }
    return ($crumbs -join "  >  ")
}

function Get-StatusLine {
    $projName = if ($Config -and $Config.project) { $Config.project } else { "unknown" }
    $parts = @("Project=$projName")
    $parts += "Root=$(Split-Path $ProjectRoot -Leaf)"
    return ($parts -join " | ")
}

# -----------------------------
# UTILITY: Backup-File, FolderBrowserDialog
# -----------------------------
function Show-FolderBrowserDialog([string]$Description, [string]$StartPath) {
    Add-Type -AssemblyName System.Windows.Forms
    $fb = New-Object System.Windows.Forms.FolderBrowserDialog
    $fb.Description = $Description
    if ($StartPath -and (Test-Path $StartPath)) { $fb.SelectedPath = $StartPath }
    if ($fb.ShowDialog() -eq "OK") { return $fb.SelectedPath }
    return $null
}

function Backup-File([string]$FilePath) {
    if (-not (Test-Path $FilePath)) { return }
    $dir = Split-Path $FilePath -Parent
    $name = Split-Path $FilePath -Leaf
    $backupDir = Join-Path $dir "backups"
    if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

    $stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backupName = "$name.bak.$stamp"
    Copy-Item $FilePath (Join-Path $backupDir $backupName)

    # Keep last 5
    $backups = Get-ChildItem -LiteralPath $backupDir -Filter "$name.bak.*" -File |
        Sort-Object LastWriteTime -Descending
    if ($backups.Count -gt 5) {
        $backups | Select-Object -Skip 5 | Remove-Item -Force
    }
    Write-Host "    Backed up: $backupName" -ForegroundColor DarkGray
}

# -----------------------------
# LIVE STATUS DASHBOARD
# -----------------------------
function Get-WatcherStatus {
    $pidFile = Join-Path $RuntimeFlagsDir "watcher.pid"
    if (-not (Test-Path $pidFile)) { return @{ running=$false; text="Not running" } }
    $watcherPid = (Get-Content $pidFile -Raw).Trim()
    try {
        $proc = Get-Process -Id $watcherPid -ErrorAction Stop
        $uptime = (Get-Date) - $proc.StartTime
        $uptimeStr = "{0}h {1}m" -f [int]$uptime.TotalHours, $uptime.Minutes
        return @{ running=$true; text="Running (PID $watcherPid) | uptime $uptimeStr" }
    } catch {
        return @{ running=$false; text="Stale PID $watcherPid (not running)" }
    }
}

function Get-AgentReadiness {
    $agents = Get-AgentNames
    $results = @()
    foreach ($a in $agents) {
        $readyFile = Join-Path $DispatchDir "$a\ready"
        $ready = Test-Path $readyFile
        $tag = if ($ready) { [char]0x2713 } else { [char]0x2717 }
        $results += @{ name=$a; ready=$ready; tag="[$a $tag]" }
    }
    $readyCount = ($results | Where-Object { $_.ready }).Count
    $total = $results.Count
    $tags = ($results | ForEach-Object { $_.tag }) -join " "
    return @{ summary="$readyCount/$total ready"; tags=$tags }
}

function Get-CurrentTaskInfo {
    if (-not $CurrentTaskFile -or -not (Test-Path $CurrentTaskFile)) {
        return "No active task"
    }
    try {
        $task = Get-Content $CurrentTaskFile -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
        $id = if ($task["id"]) { $task["id"] } else { "?" }
        $title = if ($task["title"]) { $task["title"] } else { "untitled" }
        return "$id - `"$title`""
    } catch { return "Error reading task" }
}

function Get-GateStatus {
    if (-not (Test-Path $MergedVerdictsDir)) { return "No verdicts" }
    $verdicts = Get-ChildItem -LiteralPath $MergedVerdictsDir -File -ErrorAction SilentlyContinue
    if ($verdicts.Count -eq 0) { return "No verdicts" }
    $latest = $verdicts | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    try {
        $v = Get-Content $latest.FullName -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
        $who = if ($v["agent"]) { $v["agent"] } else { "unknown" }
        $verdict = if ($v["verdict"]) { $v["verdict"] } else { "?" }
        $age = [math]::Round(((Get-Date) - $latest.LastWriteTime).TotalMinutes)
        return "$who`: $verdict (${age}m ago)"
    } catch { return "Verdict parse error" }
}

function Get-LastAuditEvent {
    if (-not $AuditLogPath -or -not (Test-Path $AuditLogPath)) { return "No audit log" }
    try {
        $lastLine = Get-Content $AuditLogPath -Tail 1 -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($lastLine)) { return "Empty log" }
        if ($lastLine.Length -gt 60) { $lastLine = $lastLine.Substring(0, 57) + "..." }
        return $lastLine
    } catch { return "Error reading log" }
}

function Get-DashboardLines {
    $configExists = Test-Path $ConfigPath
    $watcher = Get-WatcherStatus
    $agents = Get-AgentReadiness
    $task = Get-CurrentTaskInfo
    $gate = Get-GateStatus
    $lastEvent = Get-LastAuditEvent

    return @(
        "  Project:    $(if ($Config) { $Config.project } else { 'N/A' }) ($ProjectRoot)",
        "  Config:     .orchestrator/config.json $(if ($configExists) { '+' } else { 'MISSING' })",
        "  Watcher:    $($watcher.text)",
        "  Agents:     $($agents.summary)  $($agents.tags)",
        "  Task:       $task",
        "  Gate:       $gate",
        "  Last event: $lastEvent"
    )
}

# -----------------------------
# MONITORING
# -----------------------------
function Show-StatusDashboard {
    Clear-Host
    $lines = Get-DashboardLines
    Write-Host ""
    Write-Host "  === LIVE STATUS ===" -ForegroundColor Cyan
    foreach ($l in $lines) { Write-Host $l -ForegroundColor White }
    Write-Host ""
}

function Show-SprintStatusFull {
    Clear-Host
    Write-Host ""
    Write-Host "  === SPRINT STATUS (FULL) ===" -ForegroundColor Cyan
    Write-Host ""

    $fmt = "  {0,-18} {1,-12} {2,-8} {3,-10} {4,-10} {5}"
    Write-Host ($fmt -f "Agent", "Task", "Inbox", "Fan-In", "Verdict", "Last Activity") -ForegroundColor White
    Write-Host ("  " + ("-" * 75)) -ForegroundColor DarkGray

    $agents = Get-AgentNames
    foreach ($a in $agents) {
        # Task
        $taskInfo = "-"
        if ($CurrentTaskFile -and (Test-Path $CurrentTaskFile)) {
            try {
                $ct = Get-Content $CurrentTaskFile -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
                if ($ct["assigned_to"] -eq $a) { $taskInfo = $ct["id"] }
            } catch {}
        }

        # Inbox depth
        $inboxPath = Join-Path $DispatchDir "$a\inbox"
        $inboxCount = 0
        if (Test-Path $inboxPath) {
            $inboxCount = (Get-ChildItem -LiteralPath $inboxPath -File -ErrorAction SilentlyContinue).Count
        }

        # Fan-in state
        $fanIn = "-"
        if (Test-Path $TrackersFile) {
            try {
                $trackers = Get-Content $TrackersFile -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
                foreach ($key in $trackers.Keys) {
                    $t = $trackers[$key]
                    if ($t["received"] -and $t["received"].ContainsKey($a)) {
                        $received = $t["received"].Count
                        $required = if ($t["required"]) { $t["required"].Count } else { "?" }
                        $fanIn = "$received/$required"
                    }
                }
            } catch {}
        }

        # Verdict
        $verdict = "-"
        $verdictFiles = @()
        if (Test-Path $MergedVerdictsDir) {
            $verdictFiles = Get-ChildItem -LiteralPath $MergedVerdictsDir -Filter "*$a*" -File -ErrorAction SilentlyContinue
        }
        if ($verdictFiles.Count -gt 0) {
            $latestV = $verdictFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            try {
                $vd = Get-Content $latestV.FullName -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
                $verdict = if ($vd["verdict"]) { $vd["verdict"] } else { "?" }
            } catch {}
        }

        # Last activity
        $lastActivity = "-"
        $agentDir = Join-Path $DispatchDir $a
        if (Test-Path $agentDir) {
            $latestFile = Get-ChildItem -LiteralPath $agentDir -File -Recurse -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($latestFile) {
                $age = [math]::Round(((Get-Date) - $latestFile.LastWriteTime).TotalMinutes)
                $lastActivity = "${age}m ago"
            }
        }

        # Halt check
        $halted = Test-Path (Join-Path $HaltsDir "$a.halt")
        $haltTag = if ($halted) { " [HALTED]" } else { "" }

        Write-Host ($fmt -f "$a$haltTag", $taskInfo, $inboxCount, $fanIn, $verdict, $lastActivity) -ForegroundColor $(if ($halted) { "Yellow" } else { "White" })
    }
    Write-Host ""
}

function Open-TailView {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [string]$Title = "Log Viewer"
    )

    if (-not (Test-Path $FilePath)) {
        Write-Host "  File not found: $FilePath" -ForegroundColor Red
        Pause-Notice ""
        return
    }

    $escapedPath = $FilePath -replace "'", "''"
    $escapedTitle = $Title -replace "'", "''"

    Start-Process pwsh -ArgumentList @(
        '-NoExit',
        '-Command',
        "`$Host.UI.RawUI.WindowTitle = '$escapedTitle'; Get-Content -Wait -Tail 50 '$escapedPath'"
    ) | Out-Null

    Write-Host "  Opened $Title in new window." -ForegroundColor Green
    Pause-Notice ""
}

# -----------------------------
# AGENT CONTROL
# -----------------------------
function Build-AgentPickMenu([string]$ActionType) {
    $items = @()
    $agents = Get-AgentNames
    $i = 1
    foreach ($a in $agents) {
        $sessionStatus = "No session"
        try {
            & psmux has-session -t $a 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { $sessionStatus = "Running" }
        } catch {}

        $items += New-MenuItem -Label "$i. $a  --  status: $sessionStatus" -Value @{ type=$ActionType; agent=$a }
        $i++
    }
    return $items
}

function Open-AgentTerminal([string]$AgentName) {
    $modeItems = @(
        (New-MenuItem -Label "1. Bare terminal (psmux only, no AI)" -Value @{ type="launch_agent"; agent=$AgentName; mode="bare" }),
        (New-MenuItem -Label "2. Claude Code (claude)" -Value @{ type="launch_agent"; agent=$AgentName; mode="claude" }),
        (New-MenuItem -Label "3. Claude Code resume (claude --resume)" -Value @{ type="launch_agent"; agent=$AgentName; mode="claude_resume" }),
        (New-MenuItem -Label "4. Claude Code with model..." -Value @{ type="launch_agent"; agent=$AgentName; mode="claude_model" }),
        (New-MenuItem -Label "5. Custom command..." -Value @{ type="launch_agent"; agent=$AgentName; mode="custom" }),
        (New-MenuItem -Label "6. Skip (session exists)" -Value @{ type="launch_agent"; agent=$AgentName; mode="skip" })
    )
    $pick = Read-ArrowMenu -Header "Launch mode for $AgentName" -Hint "Pick how to start the agent" -Items $modeItems
    if ($pick.action -ne "select") { return }

    Launch-AgentWithMode $AgentName $pick.item.Value.mode
}

function Launch-AgentWithMode([string]$AgentName, [string]$Mode) {
    $session = $AgentName

    if ($Mode -eq "skip") {
        Write-Host "  Skipping $AgentName (assuming session exists)" -ForegroundColor DarkGray
        Pause-Notice ""
        return
    }

    # Check if session exists
    $exists = $false
    try {
        & psmux has-session -t $session 2>$null | Out-Null
        $exists = ($LASTEXITCODE -eq 0)
    } catch {}

    if ($exists) {
        $choice = Prompt-YesNo -Prompt "  Session '$session' exists. Kill and recreate?" -DefaultYes:$false
        if ($choice) {
            & psmux kill-session -t $session 2>$null
        } else {
            Write-Host "  Attaching to existing session." -ForegroundColor DarkGray
            Start-Process pwsh -ArgumentList @('-NoExit', '-Command', "psmux a -t '$session'")
            Pause-Notice "Attached."
            return
        }
    }

    # Create new session with GATE_AGENT_NAME set to the full config name (e.g. gate-ralph)
    & psmux new-session -d -s $session -c $ProjectRoot
    & psmux send-keys -t $session "`$env:GATE_AGENT_NAME = '$AgentName'" Enter

    switch ($Mode) {
        "bare"          { }
        "claude"        { & psmux send-keys -t $session "claude" Enter }
        "claude_resume" { & psmux send-keys -t $session "claude --resume" Enter }
        "claude_model"  {
            $model = Prompt-TextValue -Prompt "  Model" -Default "opus"
            & psmux send-keys -t $session "claude --model $model" Enter
        }
        "custom" {
            $cmd = Prompt-TextValue -Prompt "  Command" -AllowEmpty:$false
            & psmux send-keys -t $session $cmd Enter
        }
    }

    # Open attach window
    $escapedSession = Escape-PSString $session
    $escapedAgent = Escape-PSString $AgentName
    Start-Process pwsh -ArgumentList @('-NoExit', '-Command', "`$Host.UI.RawUI.WindowTitle = 'Agent: $escapedAgent'; psmux a -t '$escapedSession'")
    Write-Host "  Launched $AgentName (mode=$Mode, session=$session, GATE_AGENT_NAME=$AgentName)" -ForegroundColor Green
    Pause-Notice ""
}

function Attach-AgentSession([string]$AgentName) {
    $session = $AgentName
    $exists = $false
    try {
        & psmux has-session -t $session 2>$null | Out-Null
        $exists = ($LASTEXITCODE -eq 0)
    } catch {}

    if (-not $exists) {
        Write-Host "  No psmux session found for $AgentName" -ForegroundColor Red
        Pause-Notice ""
        return
    }

    $escapedSession = Escape-PSString $session
    $escapedAgent = Escape-PSString $AgentName
    Start-Process pwsh -ArgumentList @('-NoExit', '-Command', "`$Host.UI.RawUI.WindowTitle = 'Agent: $escapedAgent'; psmux a -t '$escapedSession'")
    Write-Host "  Attached to $AgentName" -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-ResumeStuckTask {
    Write-Host ""
    Write-Host "  Resume Stuck Task" -ForegroundColor Cyan

    $orchCtl = Join-Path $ProjectRoot "dispatcher\orchestrator\scripts\orchestratorctl.py"
    if (-not (Test-Path $orchCtl)) {
        Write-Host "  orchestratorctl.py not found" -ForegroundColor Red
        Pause-Notice ""
        return
    }

    & $PYTHON_EXE $orchCtl status 2>&1 | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    $taskId = Prompt-TextValue -Prompt "  Task ID to resume" -AllowEmpty:$false
    & $PYTHON_EXE $orchCtl resume $taskId 2>&1 | ForEach-Object { Write-Host "  $_" }
    Pause-Notice ""
}

function Invoke-OverrideVerdict {
    Write-Host ""
    Write-Host "  Override Verdict" -ForegroundColor Cyan

    $orchCtl = Join-Path $ProjectRoot "dispatcher\orchestrator\scripts\orchestratorctl.py"
    if (-not (Test-Path $orchCtl)) {
        Write-Host "  orchestratorctl.py not found" -ForegroundColor Red
        Pause-Notice ""
        return
    }

    $taskId = Prompt-TextValue -Prompt "  Task ID to force-approve" -AllowEmpty:$false
    & $PYTHON_EXE $orchCtl override $taskId 2>&1 | ForEach-Object { Write-Host "  $_" }
    Write-Host "  Verdict overridden. Audit logged." -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-ClearHaltFlags {
    Write-Host ""
    if (-not (Test-Path $HaltsDir)) {
        Write-Host "  No halts directory found." -ForegroundColor DarkGray
        Pause-Notice ""
        return
    }

    $halts = Get-ChildItem -LiteralPath $HaltsDir -Filter "*.halt" -File -ErrorAction SilentlyContinue
    if ($halts.Count -eq 0) {
        Write-Host "  No halt flags found." -ForegroundColor DarkGray
    } else {
        $halts | Remove-Item -Force
        Write-Host "  Cleared $($halts.Count) halt flag(s)." -ForegroundColor Green
    }
    Pause-Notice ""
}

# -----------------------------
# HOOK CONTROL
# -----------------------------
$ORCHESTRATOR_HOOKS = @(
    "dispatch_gate",
    "inbox_access_guard",
    "monitor_ingest",
    "check_gate",
    "commit_tag_enforcer",
    "diff_capture"
)

function Get-HookFlagDir {
    $dir = Join-Path $OrcDir "hook_flags"
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    return $dir
}

function Invoke-ToggleHook {
    $flagDir = Get-HookFlagDir
    $items = @()
    $i = 1
    foreach ($h in $ORCHESTRATOR_HOOKS) {
        $disabled = Test-Path (Join-Path $flagDir "$h.disabled")
        $status = if ($disabled) { "DISABLED" } else { "enabled" }
        $items += New-MenuItem -Label "$i. $h  [$status]" -Value @{ type="toggle_one_hook"; hook=$h }
        $i++
    }
    $pick = Read-ArrowMenu -Header "Toggle Hook" -Hint "Select a hook to toggle" -Items $items
    if ($pick.action -ne "select") { return }

    $hook = $pick.item.Value.hook
    $flagFile = Join-Path $flagDir "$hook.disabled"
    if (Test-Path $flagFile) {
        Remove-Item $flagFile -Force
        Write-Host "  $hook`: ENABLED" -ForegroundColor Green
    } else {
        "disabled by launcher" | Set-Content $flagFile -Encoding UTF8
        Write-Host "  $hook`: DISABLED" -ForegroundColor Red
    }
    Pause-Notice ""
}

function Show-HookStatus {
    Clear-Host
    $flagDir = Get-HookFlagDir
    Write-Host ""
    Write-Host "  === HOOK STATUS ===" -ForegroundColor Cyan
    Write-Host ""
    $fmt = "  {0,-25} {1}"
    Write-Host ($fmt -f "Hook", "Status") -ForegroundColor White
    Write-Host ("  " + ("-" * 40)) -ForegroundColor DarkGray

    foreach ($h in $ORCHESTRATOR_HOOKS) {
        $disabled = Test-Path (Join-Path $flagDir "$h.disabled")
        $status = if ($disabled) { "DISABLED" } else { "enabled" }
        $color = if ($disabled) { "Red" } else { "Green" }
        Write-Host ($fmt -f $h, $status) -ForegroundColor $color
    }
    Write-Host ""
}

function Set-AllHooks([bool]$Enable) {
    $flagDir = Get-HookFlagDir
    foreach ($h in $ORCHESTRATOR_HOOKS) {
        $flagFile = Join-Path $flagDir "$h.disabled"
        if ($Enable) {
            if (Test-Path $flagFile) { Remove-Item $flagFile -Force }
        } else {
            "disabled by launcher" | Set-Content $flagFile -Encoding UTF8
        }
    }
    if ($Enable) {
        Write-Host "  All orchestrator hooks ENABLED." -ForegroundColor Green
    } else {
        Write-Host "  All orchestrator hooks DISABLED (emergency kill)." -ForegroundColor Red
    }
}

function Set-SprintMode([bool]$On) {
    $profileName = if ($On) { "sprint_on.json" } else { "sprint_off.json" }
    $profilePath = Join-Path $SprintProfilesDir $profileName

    if (-not (Test-Path $profilePath)) {
        Write-Host "  Profile not found: $profilePath" -ForegroundColor Red
        Pause-Notice ""
        return
    }

    if (-not (Test-Path $RolesJsonPath)) {
        Write-Host "  roles.json not found: $RolesJsonPath" -ForegroundColor Red
        Pause-Notice ""
        return
    }

    # Backup first
    Backup-File $RolesJsonPath

    # Read both files
    $roles = Get-Content $RolesJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    $profile = Get-Content $profilePath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable

    # Patch roles: for each role key in profile, replace in live file
    if ($profile.ContainsKey("roles")) {
        if (-not $roles.ContainsKey("roles")) { $roles["roles"] = @{} }
        foreach ($key in $profile["roles"].Keys) {
            $roles["roles"][$key] = $profile["roles"][$key]
        }
    }

    # Patch hooks_config flags
    if ($profile.ContainsKey("hooks_config")) {
        if (-not $roles.ContainsKey("hooks_config")) { $roles["hooks_config"] = @{} }
        foreach ($key in $profile["hooks_config"].Keys) {
            $roles["hooks_config"][$key] = $profile["hooks_config"][$key]
        }
    }

    # Atomic write: tmp + rename
    $tmpFile = "$RolesJsonPath.tmp"
    $roles | ConvertTo-Json -Depth 10 | Set-Content $tmpFile -Encoding UTF8
    Move-Item -Path $tmpFile -Destination $RolesJsonPath -Force

    $tag = if ($On) { "ON" } else { "OFF" }
    Write-Host "  Sprint mode: $tag (patched from $profileName)" -ForegroundColor $(if ($On) { "Green" } else { "DarkGray" })
    Pause-Notice ""
}

function Invoke-FolderUnlock {
    if (-not (Test-Path $RolesJsonPath)) {
        Write-Host "  roles.json not found." -ForegroundColor Red
        Pause-Notice ""
        return
    }

    $rolesConfig = Get-Content $RolesJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    $hc = $rolesConfig["hooks_config"]
    if (-not $hc) { $hc = @{}; $rolesConfig["hooks_config"] = $hc }
    if (-not $hc.ContainsKey("folder_overrides")) {
        $hc["folder_overrides"] = @{ enabled = $false; paths = @(".claude/", "secrets/") }
    }
    $fo = $hc["folder_overrides"]
    $current = $fo["enabled"] -eq $true
    $paths = if ($fo.ContainsKey("paths")) { $fo["paths"] -join ", " } else { "(none)" }

    Write-Host ""
    Write-Host "  Folder Override: $(if ($current) { 'ENABLED' } else { 'DISABLED' })" -ForegroundColor $(if ($current) { "Yellow" } else { "DarkGray" })
    Write-Host "  Unlocked paths: $paths" -ForegroundColor DarkGray

    $toggleItems = @(
        (New-MenuItem -Label "Toggle $(if ($current) { 'OFF' } else { 'ON' })" -Value "toggle"),
        (New-MenuItem -Label "Edit unlocked paths" -Value "edit_paths"),
        (New-MenuItem -Label "Done" -Value "done")
    )
    $pick = Read-ArrowMenu -Header "Folder Override" -Hint "Temporarily bypass write blocks" -Items $toggleItems
    if ($pick.action -ne "select") { return }

    switch ($pick.item.Value) {
        "toggle" {
            Backup-File $RolesJsonPath
            $fo["enabled"] = -not $current
            # Atomic write
            $tmpFile = "$RolesJsonPath.tmp"
            $rolesConfig | ConvertTo-Json -Depth 10 | Set-Content $tmpFile -Encoding UTF8
            Move-Item -Path $tmpFile -Destination $RolesJsonPath -Force
            Write-Host "  Override: $(if ($fo['enabled']) { 'ENABLED' } else { 'DISABLED' })" -ForegroundColor $(if ($fo["enabled"]) { "Yellow" } else { "Green" })
        }
        "edit_paths" {
            $currentPaths = if ($fo.ContainsKey("paths")) { $fo["paths"] -join ", " } else { ".claude/, secrets/" }
            $newPaths = Prompt-TextValue -Prompt "Paths (comma-separated)" -Default $currentPaths
            $fo["paths"] = ($newPaths -split ",") | ForEach-Object { $_.Trim() }
            Backup-File $RolesJsonPath
            $tmpFile = "$RolesJsonPath.tmp"
            $rolesConfig | ConvertTo-Json -Depth 10 | Set-Content $tmpFile -Encoding UTF8
            Move-Item -Path $tmpFile -Destination $RolesJsonPath -Force
            Write-Host "  Paths updated." -ForegroundColor Green
        }
    }
    Pause-Notice ""
}

# -----------------------------
# INSTALL OPTIONS
# -----------------------------
function Build-InstallMenu {
    @(
        (New-MenuItem -Label "21. Deploy to Project..."       -Value @{ type="deploy_to_project" }),
        (New-MenuItem -Label "22. Deploy Engine..."           -Value @{ type="deploy_engine" }),
        (New-MenuItem -Label "23. Delete from Project..."     -Value @{ type="delete_from_project" }),
        (New-MenuItem -Label "24. Delete Engine..."           -Value @{ type="delete_engine" }),
        (New-MenuItem -Label " " -Value $null -Selectable:$false),
        (New-MenuItem -Label "25. Backup Settings"            -Value @{ type="backup_settings" }),
        (New-MenuItem -Label "26. Restore Settings"           -Value @{ type="restore_settings" })
    )
}

function Invoke-DeployToProject {
    $target = Show-FolderBrowserDialog -Description "Select project root to deploy orchestrator to" -StartPath $ProjectRoot
    if (-not $target) { return }

    Write-Host ""
    Write-Host "  Deploying orchestrator to: $target" -ForegroundColor Cyan

    $orchTarget = Join-Path $target ".orchestrator"
    $dispatchTarget = Join-Path $target "dispatch"
    $created = 0
    $skipped = 0

    # 1. Config template
    $configTarget = Join-Path $orchTarget "config.json"
    if (-not (Test-Path $configTarget)) {
        if (-not (Test-Path $orchTarget)) { New-Item -ItemType Directory -Path $orchTarget -Force | Out-Null }
        if (Test-Path $ConfigPath) {
            Copy-Item $ConfigPath $configTarget
            Write-Host "    + config.json (copied from current project)" -ForegroundColor Green
        } else {
            @{ project = (Split-Path $target -Leaf); agents = @() } |
                ConvertTo-Json -Depth 5 | Set-Content $configTarget -Encoding UTF8
            Write-Host "    + config.json (minimal template)" -ForegroundColor Green
        }
        $created++
    } else {
        Write-Host "    ~ config.json (exists, skipped)" -ForegroundColor DarkGray
        $skipped++
    }

    # 2. Create .orchestrator/ subdirs
    $orchSubdirs = @("plans", "tasks", "diffs", "merged_verdicts", "halts", "runtime_flags", "logs", "approvals", "hook_flags")
    foreach ($sub in $orchSubdirs) {
        $dir = Join-Path $orchTarget $sub
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "    + .orchestrator/$sub/" -ForegroundColor Green
            $created++
        } else {
            $skipped++
        }
    }

    # 3. Create dispatch/<agent>/ structure
    $agents = @()
    if (Test-Path $configTarget) {
        try {
            $targetConfig = Get-Content $configTarget -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
            $agents = @($targetConfig.agents | ForEach-Object { $_["name"] })
        } catch {}
    }
    if ($agents.Count -eq 0) { $agents = Get-AgentNames }

    foreach ($a in $agents) {
        foreach ($sub in @("inbox", "outbox", "reports", "done", "archive")) {
            $dir = Join-Path $dispatchTarget "$a\$sub"
            if (-not (Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                $created++
            } else { $skipped++ }
        }
        Write-Host "    + dispatch/$a/{inbox,outbox,reports,done,archive}" -ForegroundColor Green
    }

    # 4. Sprint profiles
    $spDir = Join-Path $orchTarget "sprint_profiles"
    if (-not (Test-Path $spDir)) { New-Item -ItemType Directory -Path $spDir -Force | Out-Null }
    foreach ($profileFile in @("sprint_on.json", "sprint_off.json")) {
        $pf = Join-Path $spDir $profileFile
        if (-not (Test-Path $pf)) {
            @{
                roles = @{}
                hooks_config = @{
                    sprint_active = ($profileFile -eq "sprint_on.json")
                    auto_approve_mode = if ($profileFile -eq "sprint_on.json") { "sprint" } else { "disabled" }
                }
            } | ConvertTo-Json -Depth 5 | Set-Content $pf -Encoding UTF8
            Write-Host "    + sprint_profiles/$profileFile (template)" -ForegroundColor Green
            $created++
        } else { $skipped++ }
    }

    # 5. Backup existing settings.local.json
    $settingsLocal = Join-Path $target ".claude\settings.local.json"
    if (Test-Path $settingsLocal) {
        Backup-File $settingsLocal
    }

    # 6. Merge hook entries into settings.local.json via install_hooks.py
    $claudeDir = Join-Path $target ".claude"
    if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null }

    $engineRoot = $null
    if ($Config -and $Config.shared_roots) {
        if (Test-Path $Config.shared_roots.orchestrator_primary) {
            $engineRoot = $Config.shared_roots.orchestrator_primary
        } elseif (Test-Path $Config.shared_roots.orchestrator_fallback) {
            $engineRoot = $Config.shared_roots.orchestrator_fallback
        }
    }

    # Backup roles.json before hooks are installed
    $rolesPath = Join-Path $env:USERPROFILE ".claude\hooks\roles.json"
    if (Test-Path $rolesPath) { Backup-File $rolesPath }

    if ($engineRoot) {
        $installScript = Join-Path $engineRoot "scripts\install_hooks.py"
        if (Test-Path $installScript) {
            Write-Host "    Running install_hooks.py (merge mode)..." -ForegroundColor DarkGray
            & $PYTHON_EXE $installScript --project $target --merge 2>&1 | ForEach-Object { Write-Host "    $_" }
        } else {
            Write-Host "    ! install_hooks.py not found at $installScript" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    ! No engine root found -- hooks not installed. Deploy engine first." -ForegroundColor Yellow
    }

    # 7. Summary
    Write-Host ""
    Write-Host "  Deploy complete: $created created, $skipped skipped (already existed)" -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-DeployEngine {
    $defaultTarget = $null
    if ($Config -and $Config.shared_roots) {
        if (Test-Path (Split-Path $Config.shared_roots.orchestrator_primary -Parent)) {
            $defaultTarget = $Config.shared_roots.orchestrator_primary
        } else {
            $defaultTarget = $Config.shared_roots.orchestrator_fallback
        }
    }

    $target = Show-FolderBrowserDialog -Description "Select target for engine deployment (NAS or D:\)" -StartPath $defaultTarget
    if (-not $target) { return }

    $engineSource = Join-Path $ProjectRoot "dispatcher\orchestrator"

    Write-Host ""
    Write-Host "  Deploying engine to: $target" -ForegroundColor Cyan

    $copyDirs = @("hooks", "lib", "scripts", "schemas", "bin", "tests", "mcp-server")
    $copyFiles = @("VERSION")

    $copied = 0
    foreach ($dir in $copyDirs) {
        $src = Join-Path $engineSource $dir
        $dst = Join-Path $target $dir
        if (Test-Path $src) {
            Copy-Item -Path $src -Destination $dst -Recurse -Force
            Write-Host "    + $dir/" -ForegroundColor Green
            $copied++
        } else {
            Write-Host "    ~ $dir/ (not found in source, skipped)" -ForegroundColor DarkGray
        }
    }

    # Copy agent profiles
    $agentProfilesSrc = Join-Path $ProjectRoot "dispatcher\agents\profiles"
    $agentProtocolsSrc = Join-Path $ProjectRoot "dispatcher\agents\protocols"
    foreach ($ap in @(@{s=$agentProfilesSrc;d="agents/profiles"}, @{s=$agentProtocolsSrc;d="agents/protocols"})) {
        if (Test-Path $ap.s) {
            $dst = Join-Path $target $ap.d
            Copy-Item -Path $ap.s -Destination $dst -Recurse -Force
            Write-Host "    + $($ap.d)/" -ForegroundColor Green
            $copied++
        }
    }

    # Copy standalone files
    foreach ($f in $copyFiles) {
        $src = Join-Path $engineSource $f
        if (Test-Path $src) {
            Copy-Item $src (Join-Path $target $f) -Force
            Write-Host "    + $f" -ForegroundColor Green
            $copied++
        }
    }

    # Verify: py_compile all .py files
    Write-Host ""
    Write-Host "  Verifying .py files..." -ForegroundColor DarkGray
    $pyFiles = Get-ChildItem -LiteralPath $target -Filter "*.py" -Recurse -File -ErrorAction SilentlyContinue
    $compileErrors = 0
    foreach ($py in $pyFiles) {
        $result = & $PYTHON_EXE -m py_compile $py.FullName 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    FAIL: $($py.FullName)" -ForegroundColor Red
            $compileErrors++
        }
    }
    if ($compileErrors -eq 0) {
        Write-Host "    All $($pyFiles.Count) .py files compile OK" -ForegroundColor Green
    } else {
        Write-Host "    $compileErrors compile error(s) found" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "  Engine deployed: $copied items copied to $target" -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-DeleteFromProject {
    $target = Show-FolderBrowserDialog -Description "Select project to remove orchestrator from" -StartPath $ProjectRoot
    if (-not $target) { return }

    $orchTarget = Join-Path $target ".orchestrator"
    $dispatchTarget = Join-Path $target "dispatch"

    if (-not (Test-Path $orchTarget) -and -not (Test-Path $dispatchTarget)) {
        Write-Host "  No orchestrator found at $target" -ForegroundColor Yellow
        Pause-Notice ""
        return
    }

    Write-Host ""
    Write-Host "  This will remove orchestrator from: $target" -ForegroundColor Red
    Write-Host "  Dispatch messages and logs will be deleted." -ForegroundColor Red
    $confirm = Prompt-YesNo -Prompt "  Continue?" -DefaultYes:$false
    if (-not $confirm) { return }

    if (Test-Path $orchTarget)     { Remove-Item $orchTarget -Recurse -Force; Write-Host "    Removed .orchestrator/" -ForegroundColor DarkGray }
    if (Test-Path $dispatchTarget) { Remove-Item $dispatchTarget -Recurse -Force; Write-Host "    Removed dispatch/" -ForegroundColor DarkGray }

    # Remove orchestrator hook entries from settings.local.json
    $settingsLocal = Join-Path $target ".claude\settings.local.json"
    if (Test-Path $settingsLocal) {
        try {
            $settings = Get-Content $settingsLocal -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
            if ($settings.ContainsKey("hooks")) {
                foreach ($event in @($settings["hooks"].Keys)) {
                    $entries = $settings["hooks"][$event]
                    if ($entries -is [array]) {
                        $filtered = @($entries | Where-Object {
                            $cmd = ""
                            if ($_ -is [hashtable] -and $_.ContainsKey("hooks")) {
                                foreach ($h in $_["hooks"]) {
                                    if ($h.ContainsKey("command")) { $cmd += $h["command"] }
                                }
                            }
                            $cmd -notmatch "orchestrator|dispatch_gate|inbox_access_guard|monitor_ingest|check_gate"
                        })
                        if ($filtered.Count -eq 0) {
                            $settings["hooks"].Remove($event)
                        } else {
                            $settings["hooks"][$event] = $filtered
                        }
                    }
                }
                $tmpFile = "$settingsLocal.tmp"
                $settings | ConvertTo-Json -Depth 10 | Set-Content $tmpFile -Encoding UTF8
                Move-Item $tmpFile $settingsLocal -Force
                Write-Host "    Cleaned orchestrator hooks from settings.local.json" -ForegroundColor DarkGray
            }
        } catch {
            Write-Host "    Warning: could not clean settings.local.json: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "  Orchestrator removed from $target" -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-DeleteEngine {
    $defaultTarget = $null
    if ($Config -and $Config.shared_roots) {
        $defaultTarget = $Config.shared_roots.orchestrator_primary
    }

    $target = Show-FolderBrowserDialog -Description "Select deployed engine location to delete" -StartPath $defaultTarget
    if (-not $target) { return }

    Write-Host ""
    Write-Host "  This will delete the deployed engine at: $target" -ForegroundColor Red
    $confirm = Prompt-YesNo -Prompt "  Continue?" -DefaultYes:$false
    if (-not $confirm) { return }

    $engineDirs = @("hooks", "lib", "scripts", "schemas", "bin", "tests", "mcp-server")
    $engineFiles = @("VERSION")

    foreach ($dir in $engineDirs) {
        $path = Join-Path $target $dir
        if (Test-Path $path) { Remove-Item $path -Recurse -Force; Write-Host "    Removed $dir/" -ForegroundColor DarkGray }
    }
    foreach ($f in $engineFiles) {
        $path = Join-Path $target $f
        if (Test-Path $path) { Remove-Item $path -Force; Write-Host "    Removed $f" -ForegroundColor DarkGray }
    }

    # Leave agents/ (shared across projects)
    Write-Host "    agents/ left intact (shared across projects)" -ForegroundColor DarkGray

    Write-Host ""
    Write-Host "  Engine deleted from $target" -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-BackupSettings {
    Write-Host ""
    Write-Host "  Backing up settings..." -ForegroundColor Cyan

    if (Test-Path $RolesJsonPath)     { Backup-File $RolesJsonPath }
    if (Test-Path $SettingsLocalPath) { Backup-File $SettingsLocalPath }

    Write-Host "  Backup complete." -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-RestoreSettings {
    Write-Host ""
    Write-Host "  Available backups:" -ForegroundColor Cyan

    $allBackups = @()

    # roles.json backups
    $rolesBackupDir = Join-Path (Split-Path $RolesJsonPath -Parent) "backups"
    if (Test-Path $rolesBackupDir) {
        $allBackups += Get-ChildItem -LiteralPath $rolesBackupDir -Filter "roles.json.bak.*" -File |
            Sort-Object LastWriteTime -Descending |
            ForEach-Object { @{ file=$_; label="roles.json  $($_.Name)  $('{0:yyyy-MM-dd HH:mm}' -f $_.LastWriteTime)"; target=$RolesJsonPath } }
    }

    # settings.local.json backups
    $settingsBackupDir = Join-Path (Split-Path $SettingsLocalPath -Parent) "backups"
    if (Test-Path $settingsBackupDir) {
        $allBackups += Get-ChildItem -LiteralPath $settingsBackupDir -Filter "settings.local.json.bak.*" -File |
            Sort-Object LastWriteTime -Descending |
            ForEach-Object { @{ file=$_; label="settings.local.json  $($_.Name)  $('{0:yyyy-MM-dd HH:mm}' -f $_.LastWriteTime)"; target=$SettingsLocalPath } }
    }

    if ($allBackups.Count -eq 0) {
        Write-Host "  No backups found." -ForegroundColor DarkGray
        Pause-Notice ""
        return
    }

    $items = @()
    $i = 1
    foreach ($b in $allBackups) {
        $items += New-MenuItem -Label "$i. $($b.label)" -Value $b
        $i++
    }
    $pick = Read-ArrowMenu -Header "Restore Settings" -Hint "Select a backup to restore" -Items $items
    if ($pick.action -ne "select") { return }

    $backup = $pick.item.Value
    Copy-Item $backup.file.FullName $backup.target -Force
    Write-Host "  Restored: $($backup.file.Name) -> $($backup.target)" -ForegroundColor Green
    Pause-Notice ""
}

# -----------------------------
# CONFIGURATION
# -----------------------------
function Invoke-ChangeProject {
    $target = Show-FolderBrowserDialog -Description "Select project root directory" -StartPath $ProjectRoot
    if (-not $target) { return }

    $testConfig = Join-Path $target ".orchestrator\config.json"
    if (-not (Test-Path $testConfig)) {
        Write-Host "  No .orchestrator/config.json found at $target" -ForegroundColor Red
        $proceed = Prompt-YesNo -Prompt "  Use this directory anyway?" -DefaultYes:$false
        if (-not $proceed) { return }
    }

    # Update globals
    $script:ProjectRoot = $target
    $script:OrcDir = Join-Path $target ".orchestrator"
    $script:ConfigPath = Join-Path $script:OrcDir "config.json"
    $script:DispatchDir = Join-Path $target "dispatch"
    $script:Config = Load-Config

    # Re-derive all paths
    $script:LogsDir = Resolve-OrcPath "logs_dir"
    $script:RuntimeDir = Resolve-OrcPath "runtime_dir"
    $script:TasksFile = Resolve-OrcPath "tasks_file"
    $script:CurrentTaskFile = Resolve-OrcPath "current_task_file"
    $script:PlanFile = Resolve-OrcPath "plan_file"
    $script:ApprovalsDir = Resolve-OrcPath "approvals_dir"
    $script:DiffsDir = Resolve-OrcPath "diffs_dir"
    $script:HaltsDir = Join-Path $script:OrcDir "halts"
    $script:RuntimeFlagsDir = Join-Path $script:OrcDir "runtime_flags"
    $script:MergedVerdictsDir = Join-Path $script:OrcDir "merged_verdicts"
    $script:TrackersFile = Join-Path $script:OrcDir "trackers.json"
    $script:SprintProfilesDir = Join-Path $script:OrcDir "sprint_profiles"
    $script:AuditLogPath = if ($script:LogsDir) { Join-Path $script:LogsDir "audit.log" } else { $null }
    $script:DecisionTracePath = if ($script:LogsDir) { Join-Path $script:LogsDir "decision_trace.log" } else { $null }
    $script:SettingsLocalPath = Join-Path $target ".claude\settings.local.json"

    Save-ProjectRoot $target

    Write-Host "  Project changed to: $target" -ForegroundColor Green
    (Cur).items = Build-MainMenu
    Pause-Notice ""
}

function Invoke-ValidateConfig {
    Write-Host ""
    Write-Host "  Validating config..." -ForegroundColor Cyan

    $validateScript = Join-Path $ProjectRoot "dispatcher\orchestrator\scripts\validate.py"
    if (Test-Path $validateScript) {
        & $PYTHON_EXE $validateScript 2>&1 | ForEach-Object { Write-Host "  $_" }
    } else {
        # Manual validation
        $checks = @()
        $checks += @{ name="config.json exists"; ok=(Test-Path $ConfigPath) }
        $checks += @{ name="dispatch/ exists"; ok=(Test-Path $DispatchDir) }
        $checks += @{ name="logs/ exists"; ok=($LogsDir -and (Test-Path $LogsDir)) }
        $checks += @{ name="runtime_flags/ exists"; ok=(Test-Path $RuntimeFlagsDir) }
        $checks += @{ name="roles.json exists"; ok=(Test-Path $RolesJsonPath) }

        $agents = Get-AgentNames
        foreach ($a in $agents) {
            $inbox = Join-Path $DispatchDir "$a\inbox"
            $checks += @{ name="dispatch/$a/inbox exists"; ok=(Test-Path $inbox) }
        }

        $fmt = "  {0,-40} {1}"
        foreach ($c in $checks) {
            $status = if ($c.ok) { "OK" } else { "FAIL" }
            $color = if ($c.ok) { "Green" } else { "Red" }
            Write-Host ($fmt -f $c.name, $status) -ForegroundColor $color
        }
    }
    Pause-Notice ""
}

function Invoke-Doctor {
    Clear-Host
    Write-Host ""
    Write-Host "  === DOCTOR -- Pre-Flight Checks ===" -ForegroundColor Cyan
    Write-Host ""

    $checks = @(
        @{ name="PowerShell 7+"; ok=($PSVersionTable.PSVersion.Major -ge 7) },
        @{ name="psmux available"; ok=($null -ne (Get-Command psmux -ErrorAction SilentlyContinue)) },
        @{ name="Python available"; ok=($null -ne (Get-Command $PYTHON_EXE -ErrorAction SilentlyContinue)) },
        @{ name="Project root exists"; ok=(Test-Path $ProjectRoot) },
        @{ name="config.json exists"; ok=(Test-Path $ConfigPath) },
        @{ name=".orchestrator/ exists"; ok=(Test-Path $OrcDir) },
        @{ name="dispatch/ exists"; ok=(Test-Path $DispatchDir) },
        @{ name="roles.json exists"; ok=(Test-Path $RolesJsonPath) },
        @{ name="Watcher script exists"; ok=(Test-Path (Join-Path $ProjectRoot "dispatcher\orchestrator\scripts\watcher.py")) },
        @{ name="orchestratorctl.py exists"; ok=(Test-Path (Join-Path $ProjectRoot "dispatcher\orchestrator\scripts\orchestratorctl.py")) }
    )

    # Check agents
    $agents = Get-AgentNames
    foreach ($a in $agents) {
        $inbox = Join-Path $DispatchDir "$a\inbox"
        $checks += @{ name="Agent $a inbox"; ok=(Test-Path $inbox) }
    }

    # Check engine locations
    if ($Config -and $Config.shared_roots) {
        $checks += @{ name="Engine (primary) $($Config.shared_roots.orchestrator_primary)"; ok=(Test-Path $Config.shared_roots.orchestrator_primary) }
        $checks += @{ name="Engine (fallback) $($Config.shared_roots.orchestrator_fallback)"; ok=(Test-Path $Config.shared_roots.orchestrator_fallback) }
    }

    $fmt = "  {0,-55} {1}"
    $passCount = 0
    $failCount = 0
    foreach ($c in $checks) {
        $status = if ($c.ok) { "OK" } else { "FAIL" }
        $color = if ($c.ok) { "Green" } else { "Red" }
        Write-Host ($fmt -f $c.name, $status) -ForegroundColor $color
        if ($c.ok) { $passCount++ } else { $failCount++ }
    }

    Write-Host ""
    Write-Host "  $passCount passed, $failCount failed" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Yellow" })
    Pause-Notice ""
}

function Invoke-ResetWatcher {
    Write-Host ""
    Write-Host "  Resetting watcher state..." -ForegroundColor Yellow

    if (Test-Path $TrackersFile) {
        Remove-Item $TrackersFile -Force
        Write-Host "    Removed trackers.json" -ForegroundColor DarkGray
    }

    if (Test-Path $MergedVerdictsDir) {
        Get-ChildItem -LiteralPath $MergedVerdictsDir -File -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host "    Cleared merged_verdicts/" -ForegroundColor DarkGray
    }

    # Kill watcher if running, then restart
    Invoke-KillWatcher
    Start-WatcherWithSupervisor
    Write-Host "  Watcher state reset and restarted." -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-KillWatcher {
    # Write STOP flag first so supervisor exits after child dies
    if (Test-Path $RuntimeFlagsDir) {
        $stopFile = Join-Path $RuntimeFlagsDir "STOP"
        "force-kill" | Set-Content $stopFile -Encoding UTF8
        Write-Host "    STOP flag written (supervisor will not restart)" -ForegroundColor DarkGray
    }

    # Kill supervisor if PID file exists
    $supervisorPidFile = Join-Path $RuntimeFlagsDir "supervisor.pid"
    if (Test-Path $supervisorPidFile) {
        $supervisorPid = (Get-Content $supervisorPidFile -Raw).Trim()
        try {
            Stop-Process -Id $supervisorPid -Force -ErrorAction Stop
            Write-Host "    Killed supervisor (PID $supervisorPid)" -ForegroundColor DarkGray
        } catch {
            Write-Host "    Supervisor PID $supervisorPid not running" -ForegroundColor DarkGray
        }
        Remove-Item $supervisorPidFile -Force -ErrorAction SilentlyContinue
    }

    $pidFile = Join-Path $RuntimeFlagsDir "watcher.pid"
    if (Test-Path $pidFile) {
        $watcherPid = (Get-Content $pidFile -Raw).Trim()
        try {
            Stop-Process -Id $watcherPid -Force -ErrorAction Stop
            Write-Host "    Killed watcher (PID $watcherPid)" -ForegroundColor DarkGray
        } catch {
            Write-Host "    Watcher PID $watcherPid not running" -ForegroundColor DarkGray
        }
        Remove-Item $pidFile -Force
    } else {
        # Try finding by process name
        $procs = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
            try { $_.CommandLine -match "watcher\.py" } catch { $false }
        }
        if ($procs) {
            $procs | Stop-Process -Force
            Write-Host "    Killed watcher process(es)" -ForegroundColor DarkGray
        } else {
            Write-Host "    No watcher process found" -ForegroundColor DarkGray
        }
    }
}

# -----------------------------
# QUICK ACCESS
# -----------------------------
function Build-AgentInboxMenu {
    $items = @()
    $agents = Get-AgentNames
    $i = 1
    foreach ($a in $agents) {
        $inboxPath = Join-Path $DispatchDir "$a\inbox"
        $count = 0
        if (Test-Path $inboxPath) {
            $count = (Get-ChildItem -LiteralPath $inboxPath -File -ErrorAction SilentlyContinue).Count
        }
        $items += New-MenuItem -Label "$i. $a  ($count messages)" -Value @{ type="open_agent_inbox"; agent=$a }
        $i++
    }
    return $items
}

# -----------------------------
# SPRINT CONTROL
# -----------------------------
function Start-WatcherWithSupervisor {
    $watcherScript = Join-Path $ProjectRoot "dispatcher\orchestrator\scripts\watcher.py"
    if (-not (Test-Path $watcherScript)) {
        Write-Host "  WARNING: watcher.py not found at $watcherScript" -ForegroundColor Yellow
        return
    }

    # Write PID file for the supervisor wrapper, then launch as detached process
    $runtimeFlagsPath = $RuntimeFlagsDir
    if (-not (Test-Path $runtimeFlagsPath)) { New-Item -ItemType Directory -Path $runtimeFlagsPath -Force | Out-Null }

    $pidFile = Join-Path $runtimeFlagsPath "watcher.pid"
    $supervisorPidFile = Join-Path $runtimeFlagsPath "supervisor.pid"
    $pythonExe = $PYTHON_EXE
    $escapedScript = $watcherScript -replace "'", "''"
    $escapedFlags = $runtimeFlagsPath -replace "'", "''"
    $escapedPid = $pidFile -replace "'", "''"
    $escapedSupervisorPid = $supervisorPidFile -replace "'", "''"

    # Launch detached supervisor process
    $supervisorBlock = @"
`$ErrorActionPreference = 'Stop'
`$pidFile = '$escapedPid'
`$supervisorPidFile = '$escapedSupervisorPid'
`$flagsDir = '$escapedFlags'
`$watcherScript = '$escapedScript'
`$python = '$pythonExe'

# Write supervisor PID so Invoke-KillWatcher can terminate it
`$PID | Set-Content `$supervisorPidFile -Encoding UTF8

while (-not (Test-Path (Join-Path `$flagsDir 'STOP'))) {
    `$proc = Start-Process `$python -ArgumentList `$watcherScript -PassThru -NoNewWindow
    `$proc.Id | Set-Content `$pidFile -Encoding UTF8
    `$proc.WaitForExit()
    if (`$proc.ExitCode -eq 0) { break }
    if (Test-Path (Join-Path `$flagsDir 'STOP')) { break }
    Write-Host "Watcher crashed (exit `$(`$proc.ExitCode)), restarting in 5s..."
    Start-Sleep 5
}
if (Test-Path `$pidFile) { Remove-Item `$pidFile -Force }
if (Test-Path `$supervisorPidFile) { Remove-Item `$supervisorPidFile -Force }
"@

    Start-Process pwsh -ArgumentList @('-NoProfile', '-Command', $supervisorBlock) -WindowStyle Hidden
    Write-Host "  Watcher supervisor started (detached)." -ForegroundColor Green
}

function Invoke-SprintWizard {
    # Step 1: Select agents
    $agents = Get-AgentNames
    if ($agents.Count -eq 0) {
        Write-Host "  No agents configured." -ForegroundColor Red
        Pause-Notice ""
        return
    }

    $checkedState = @{}
    foreach ($a in $agents) { $checkedState[$a] = $true }

    $selectedAgents = Read-CheckboxMenu `
        -Header "Sprint Wizard - Step 1: Agents" `
        -Hint "Space to toggle  -  Enter to confirm" `
        -Items $agents `
        -Checked $checkedState

    if ($null -eq $selectedAgents -or $selectedAgents.Count -eq 0) { return }
    $selectedAgents = @($selectedAgents)

    # Step 2: Launch mode per agent (collect mode + model/cmd here, not at launch time)
    $launchModes = @{}
    $modeOptions = @(
        @{ label="Bare terminal (psmux session only, no AI)"; mode="bare" },
        @{ label="Claude Code (claude)"; mode="claude" },
        @{ label="Claude Code resume (claude --resume)"; mode="claude_resume" },
        @{ label="Claude Code with model..."; mode="claude_model" },
        @{ label="Custom command..."; mode="custom" },
        @{ label="Skip (session exists)"; mode="skip" }
    )

    Write-Host ""
    Write-Host "  Step 2/4 - Launch mode per agent:" -ForegroundColor Cyan

    $firstEntry = $null
    foreach ($a in $selectedAgents) {
        if ($launchModes.ContainsKey($a)) { continue }

        $modeItems = @()
        $i = 1
        foreach ($opt in $modeOptions) {
            $modeItems += New-MenuItem -Label "$i. $($opt.label)" -Value @{ type="mode_pick"; mode=$opt.mode }
            $i++
        }

        $modePick = Read-ArrowMenu -Header "Launch mode for $a" -Hint "Pick how to launch this agent" -Items $modeItems
        if ($modePick.action -ne "select") { return }

        $pickedMode = $modePick.item.Value.mode
        $entry = @{ mode=$pickedMode; model=$null; cmd=$null }

        # Collect model/cmd immediately in the wizard
        if ($pickedMode -eq "claude_model") {
            $entry.model = Prompt-TextValue -Prompt "  Model for $a" -Default "opus"
        } elseif ($pickedMode -eq "custom") {
            $entry.cmd = Prompt-TextValue -Prompt "  Command for $a" -AllowEmpty:$false
        }

        $launchModes[$a] = $entry

        if ($null -eq $firstEntry) {
            $firstEntry = $entry
            if ($selectedAgents.Count -gt 1) {
                $applyAll = Prompt-YesNo -Prompt "  Apply '$pickedMode' to all remaining agents?" -DefaultYes:$true
                if ($applyAll) {
                    foreach ($remaining in $selectedAgents) {
                        if (-not $launchModes.ContainsKey($remaining)) {
                            $remainEntry = @{ mode=$pickedMode; model=$entry.model; cmd=$entry.cmd }
                            if ($pickedMode -eq "claude_model") {
                                $remainEntry.model = Prompt-TextValue -Prompt "  Model for $remaining" -Default "opus"
                            } elseif ($pickedMode -eq "custom") {
                                $remainEntry.cmd = Prompt-TextValue -Prompt "  Command for $remaining" -AllowEmpty:$false
                            }
                            $launchModes[$remaining] = $remainEntry
                        }
                    }
                    break
                }
            }
        }
    }

    # Step 3: Session names
    Write-Host ""
    Write-Host "  Step 3/4 - Session names (Enter to keep defaults):" -ForegroundColor Cyan
    $sessionNames = @{}
    foreach ($a in $selectedAgents) {
        $default = $a
        $name = Prompt-TextValue -Prompt "  Session for $a" -Default $default -AllowEmpty:$false
        $sessionNames[$a] = $name
    }

    # Step 4: Confirm and launch
    Write-Host ""
    Write-Host "  Step 4/4 - Sprint configuration:" -ForegroundColor Cyan
    foreach ($a in $selectedAgents) {
        $entry = $launchModes[$a]
        $modeStr = $entry.mode
        if ($entry.model) { $modeStr += " (model=$($entry.model))" }
        if ($entry.cmd)   { $modeStr += " (cmd=$($entry.cmd))" }
        Write-Host "    $a -> mode=$modeStr, session=$($sessionNames[$a])" -ForegroundColor White
    }

    $planExists = $PlanFile -and (Test-Path $PlanFile)
    if ($planExists) {
        Write-Host "    Plan: $PlanFile" -ForegroundColor White
    }
    Write-Host ""

    $confirm = Prompt-YesNo -Prompt "  Launch sprint?" -DefaultYes:$true
    if (-not $confirm) { return }

    # Execute launch
    Write-Host ""
    Write-Host "  Launching sprint..." -ForegroundColor Green

    # 1. Validate config
    Write-Host "  [1/5] Validating config..." -ForegroundColor DarkGray

    # 2. Ensure dispatch folders
    Write-Host "  [2/5] Ensuring dispatch folders..." -ForegroundColor DarkGray
    foreach ($a in $selectedAgents) {
        foreach ($sub in @("inbox", "outbox", "reports", "done", "archive")) {
            $dir = Join-Path $DispatchDir "$a\$sub"
            if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        }
    }

    # 3. Start watcher
    Write-Host "  [3/5] Starting watcher..." -ForegroundColor DarkGray
    Start-WatcherWithSupervisor

    # 4. Launch agent sessions
    Write-Host "  [4/5] Launching agent sessions..." -ForegroundColor DarkGray
    foreach ($a in $selectedAgents) {
        $session = $sessionNames[$a]
        $entry = $launchModes[$a]
        $mode = $entry.mode

        # Create psmux session with GATE_AGENT_NAME (full config name, e.g. gate-ralph)
        & psmux new-session -d -s $session -c $ProjectRoot 2>$null
        & psmux send-keys -t $session "`$env:GATE_AGENT_NAME = '$a'" Enter

        switch ($mode) {
            "bare"          { }
            "claude"        { & psmux send-keys -t $session "claude" Enter }
            "claude_resume" { & psmux send-keys -t $session "claude --resume" Enter }
            "claude_model"  {
                $model = if ($entry.model) { $entry.model } else { "opus" }
                & psmux send-keys -t $session "claude --model $model" Enter
            }
            "custom" {
                $cmd = $entry.cmd
                & psmux send-keys -t $session $cmd Enter
            }
            "skip" { Write-Host "    Skipping $a (existing session)" -ForegroundColor DarkGray }
        }
        Write-Host "    Launched $a in session $session (mode=$mode)" -ForegroundColor Green
    }

    # 5. Wait for ready files (optional)
    if ($Config.session.require_ready_files) {
        Write-Host "  [5/5] Waiting for ready files..." -ForegroundColor DarkGray
        $timeout = 60
        $start = Get-Date
        while (((Get-Date) - $start).TotalSeconds -lt $timeout) {
            $allReady = $true
            foreach ($a in $selectedAgents) {
                if (-not (Test-Path (Join-Path $DispatchDir "$a\ready"))) { $allReady = $false; break }
            }
            if ($allReady) { break }
            Start-Sleep 2
            Write-Host "." -NoNewline
        }
        Write-Host ""
    } else {
        Write-Host "  [5/5] Ready files not required (skipping)" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "  Sprint launched successfully." -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-SprintPause {
    Write-Host ""
    Write-Host "  Pausing sprint..." -ForegroundColor Yellow
    $agents = Get-AgentNames
    foreach ($a in $agents) {
        $agentCfg = $Config.agents | Where-Object { $_["name"] -eq $a }
        if ($agentCfg.executor) {
            $haltFile = Join-Path $HaltsDir "$a.halt"
            if (-not (Test-Path $HaltsDir)) { New-Item -ItemType Directory -Path $HaltsDir -Force | Out-Null }
            "sprint paused" | Set-Content $haltFile -Encoding UTF8
            Write-Host "    Halted: $a" -ForegroundColor DarkGray
        }
    }
    Write-Host "  Sprint paused. Watcher still running." -ForegroundColor Yellow
    Pause-Notice ""
}

function Invoke-SprintResume {
    Write-Host ""
    Write-Host "  Resuming sprint..." -ForegroundColor Green
    if (Test-Path $HaltsDir) {
        Get-ChildItem -LiteralPath $HaltsDir -Filter "*.halt" -File -ErrorAction SilentlyContinue |
            Remove-Item -Force
        Write-Host "    All halt flags cleared." -ForegroundColor Green
    }

    # Re-wake agents
    $agents = Get-AgentNames
    foreach ($a in $agents) {
        $wakeDir = Join-Path $DispatchDir "$a\inbox"
        if (-not (Test-Path $wakeDir)) { New-Item -ItemType Directory -Path $wakeDir -Force | Out-Null }
        $wakeFile = Join-Path $wakeDir "WAKE"
        "resume" | Set-Content $wakeFile -Encoding UTF8
        Write-Host "    Woke: $a" -ForegroundColor DarkGray
    }
    Write-Host "  Sprint resumed." -ForegroundColor Green
    Pause-Notice ""
}

function Invoke-SprintStop {
    Write-Host ""
    Write-Host "  Stopping sprint..." -ForegroundColor Red

    # Write STOP flag
    if (-not (Test-Path $RuntimeFlagsDir)) { New-Item -ItemType Directory -Path $RuntimeFlagsDir -Force | Out-Null }
    $stopFile = Join-Path $RuntimeFlagsDir "STOP"
    "stopped by launcher" | Set-Content $stopFile -Encoding UTF8
    Write-Host "    STOP flag written." -ForegroundColor DarkGray

    # Print summary
    $task = Get-CurrentTaskInfo
    Write-Host ""
    Write-Host "  Sprint summary:" -ForegroundColor Cyan
    Write-Host "    Current task: $task"
    Write-Host "    Audit log: $AuditLogPath"

    # Optionally close terminals
    $close = Prompt-YesNo -Prompt "  Close agent terminals?" -DefaultYes:$false
    if ($close) {
        $agents = Get-AgentNames
        foreach ($a in $agents) {
            try { & psmux kill-session -t $a 2>$null } catch {}
        }
        Write-Host "    Sessions killed." -ForegroundColor DarkGray
    }

    Write-Host "  Sprint stopped." -ForegroundColor Red
    Pause-Notice ""
}

# -----------------------------
# MAIN MENU
# -----------------------------
function Build-MainMenu {
    $dashboard = Get-DashboardLines
    $items = @()

    # Dashboard status (non-selectable)
    $items += New-MenuItem -Label "===== ORCHESTRATOR CONTROL PANEL =====" -Value $null -Selectable:$false
    foreach ($line in $dashboard) {
        $items += New-MenuItem -Label $line -Value $null -Selectable:$false
    }
    $items += New-MenuItem -Label "======================================" -Value $null -Selectable:$false
    $items += New-MenuItem -Label " " -Value $null -Selectable:$false

    # Sprint Control
    $items += New-MenuItem -Label "───── Sprint Control ─────" -Value $null -Selectable:$false
    $items += New-MenuItem -Label " 1. Launch Sprint..."          -Value @{ type="sprint_wizard" }
    $items += New-MenuItem -Label " 2. Pause Sprint"              -Value @{ type="sprint_pause" }
    $items += New-MenuItem -Label " 3. Resume Sprint"             -Value @{ type="sprint_resume" }
    $items += New-MenuItem -Label " 4. Stop Sprint"               -Value @{ type="sprint_stop" }
    $items += New-MenuItem -Label " " -Value $null -Selectable:$false

    # Monitoring
    $items += New-MenuItem -Label "───── Monitoring ─────" -Value $null -Selectable:$false
    $items += New-MenuItem -Label " 5. Status Dashboard"          -Value @{ type="status_dashboard" }
    $items += New-MenuItem -Label " 6. Sprint Status (full)"      -Value @{ type="sprint_status_full" }
    $items += New-MenuItem -Label " 7. View Decision Trace"       -Value @{ type="view_decision_trace" }
    $items += New-MenuItem -Label " 8. View Audit Log"            -Value @{ type="view_audit_log" }
    $items += New-MenuItem -Label " " -Value $null -Selectable:$false

    # Agent Control
    $items += New-MenuItem -Label "───── Agent Control ─────" -Value $null -Selectable:$false
    $items += New-MenuItem -Label " 9. Open Agent Terminal..."    -Value @{ type="agent_terminal_menu" }
    $items += New-MenuItem -Label "10. Attach to Session"         -Value @{ type="attach_session_menu" }
    $items += New-MenuItem -Label "11. Resume Stuck Task..."      -Value @{ type="resume_stuck_task" }
    $items += New-MenuItem -Label "12. Override Verdict..."       -Value @{ type="override_verdict" }
    $items += New-MenuItem -Label "13. Clear Halt Flags"          -Value @{ type="clear_halt_flags" }
    $items += New-MenuItem -Label " " -Value $null -Selectable:$false

    # Hook Control
    $items += New-MenuItem -Label "───── Hook Control ─────" -Value $null -Selectable:$false
    $items += New-MenuItem -Label "14. Toggle Hook..."            -Value @{ type="toggle_hook" }
    $items += New-MenuItem -Label "15. Hook Status"               -Value @{ type="hook_status" }
    $items += New-MenuItem -Label "16. Enable ALL Hooks"          -Value @{ type="hooks_enable_all" }
    $items += New-MenuItem -Label "17. Disable ALL Hooks"         -Value @{ type="hooks_disable_all" }
    $items += New-MenuItem -Label "18. Sprint Mode ON"            -Value @{ type="sprint_mode_on" }
    $items += New-MenuItem -Label "19. Sprint Mode OFF"           -Value @{ type="sprint_mode_off" }
    $items += New-MenuItem -Label "20. Folder Unlock..."          -Value @{ type="folder_unlock" }
    $items += New-MenuItem -Label " " -Value $null -Selectable:$false

    # Install Options (submenu)
    $items += New-MenuItem -Label "───── Install Options ─────" -Value $null -Selectable:$false
    $items += New-MenuItem -Label "21. Install Options..."        -Value @{ type="install_menu" }
    $items += New-MenuItem -Label " " -Value $null -Selectable:$false

    # Configuration
    $items += New-MenuItem -Label "───── Configuration ─────" -Value $null -Selectable:$false
    $items += New-MenuItem -Label "27. Change Project Directory"  -Value @{ type="change_project" }
    $items += New-MenuItem -Label "28. Validate Config"           -Value @{ type="validate_config" }
    $items += New-MenuItem -Label "29. Doctor"                    -Value @{ type="doctor" }
    $items += New-MenuItem -Label "30. Reset Watcher State"       -Value @{ type="reset_watcher" }
    $items += New-MenuItem -Label "31. Force Kill Watcher"        -Value @{ type="kill_watcher" }
    $items += New-MenuItem -Label " " -Value $null -Selectable:$false

    # Quick Access
    $items += New-MenuItem -Label "───── Quick Access ─────" -Value $null -Selectable:$false
    $items += New-MenuItem -Label "32. Audit Log (folder)"        -Value @{ type="open_folder"; path=$LogsDir }
    $items += New-MenuItem -Label "33. Dispatch Folders"           -Value @{ type="open_folder"; path=$DispatchDir }
    $items += New-MenuItem -Label "34. Agent Inboxes..."           -Value @{ type="agent_inboxes_menu" }
    $items += New-MenuItem -Label "35. Config File"                -Value @{ type="open_file"; path=$ConfigPath }
    $items += New-MenuItem -Label "36. Spec & Plans"               -Value @{ type="open_folder"; path=(Join-Path $ProjectRoot "dispatcher\docs") }
    $items += New-MenuItem -Label "37. Open Project Folder"        -Value @{ type="open_folder"; path=$ProjectRoot }
    $items += New-MenuItem -Label " " -Value $null -Selectable:$false
    $items += New-MenuItem -Label "38. Quit"                       -Value @{ type="quit" }

    return $items
}

# -----------------------------
# DRYRUN VERIFICATION
# -----------------------------
if ($DryRun) {
    Write-Host "=== DryRun Verification ===" -ForegroundColor Cyan
    Write-Host "  ProjectRoot: $ProjectRoot" -ForegroundColor DarkGray
    Write-Host "  ConfigPath:  $ConfigPath" -ForegroundColor DarkGray
    Write-Host ""

    $requiredFunctions = @(
        "Load-Config", "Get-AgentNames", "Get-SessionPrefix", "Resolve-OrcPath",
        "Get-Theme", "Write-Box", "New-MenuItem", "Read-ArrowMenu", "Read-CheckboxMenu",
        "Pause-Notice", "Prompt-TextValue", "Prompt-YesNo", "Escape-PSString",
        "Push-State", "Go-Back", "Cur", "Reset-ToHome", "Get-Breadcrumbs", "Get-StatusLine",
        "Backup-File", "Show-FolderBrowserDialog",
        "Get-WatcherStatus", "Get-AgentReadiness", "Get-CurrentTaskInfo",
        "Get-GateStatus", "Get-LastAuditEvent", "Get-DashboardLines",
        "Show-StatusDashboard", "Show-SprintStatusFull", "Open-TailView",
        "Build-AgentPickMenu", "Open-AgentTerminal", "Attach-AgentSession",
        "Launch-AgentWithMode", "Invoke-ResumeStuckTask", "Invoke-OverrideVerdict",
        "Invoke-ClearHaltFlags",
        "Invoke-ToggleHook", "Show-HookStatus", "Set-AllHooks",
        "Set-SprintMode", "Invoke-FolderUnlock",
        "Build-InstallMenu", "Invoke-DeployToProject", "Invoke-DeployEngine",
        "Invoke-DeleteFromProject", "Invoke-DeleteEngine",
        "Invoke-BackupSettings", "Invoke-RestoreSettings",
        "Invoke-ChangeProject", "Invoke-ValidateConfig", "Invoke-Doctor",
        "Invoke-ResetWatcher", "Invoke-KillWatcher",
        "Build-AgentInboxMenu",
        "Invoke-SprintWizard", "Invoke-SprintPause", "Invoke-SprintResume",
        "Invoke-SprintStop", "Start-WatcherWithSupervisor",
        "Build-MainMenu"
    )

    $missing = @()
    foreach ($fn in $requiredFunctions) {
        if (-not (Get-Command $fn -ErrorAction SilentlyContinue)) { $missing += $fn }
    }

    if ($missing.Count -eq 0) {
        Write-Host "  All $($requiredFunctions.Count) functions defined." -ForegroundColor Green
    } else {
        Write-Host "  MISSING $($missing.Count) functions:" -ForegroundColor Red
        $missing | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    }

    # Verify menu builds
    try {
        $menu = Build-MainMenu
        Write-Host "  Build-MainMenu: $($menu.Count) items" -ForegroundColor Green

        # Print all selectable items
        Write-Host ""
        Write-Host "  Menu items:" -ForegroundColor Cyan
        foreach ($item in $menu) {
            if ($item.Selectable -and $item.Value) {
                Write-Host "    $($item.Label)  -> $($item.Value.type)" -ForegroundColor White
            } elseif (-not $item.Selectable) {
                Write-Host "    $($item.Label)" -ForegroundColor DarkGray
            }
        }
    } catch {
        Write-Host "  Build-MainMenu FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }

    try {
        $install = Build-InstallMenu
        Write-Host "  Build-InstallMenu: $($install.Count) items" -ForegroundColor Green
    } catch {
        Write-Host "  Build-InstallMenu FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "DryRun complete." -ForegroundColor Cyan
    exit 0
}

# -----------------------------
# MAIN LOOP
# -----------------------------
Push-State @{
    id="main"
    crumb="Home"
    header="ORCHESTRATOR CONTROL PANEL"
    hint="Arrow keys to navigate, Enter to select, Esc to quit."
    items=(Build-MainMenu)
    ctx=@{}
}

:MAIN while ($true) {
    $s = Cur
    if (-not $s) { break }

    $theme = Get-Theme
    $r = Read-ArrowMenu -Header $s.header -Hint $s.hint -Items $s.items `
        -Breadcrumb (Get-Breadcrumbs) -Status (Get-StatusLine) `
        -AccentColor $theme.Accent -TitleColor $theme.Title -DividerColor $theme.Divider

    if ($r.action -eq "back")   { Go-Back; continue }
    if ($r.action -eq "cancel") { if ($s.id -eq "main") { break MAIN } else { Go-Back; continue } }

    $item = $r.item
    if (-not $item) { continue }
    $v = $item.Value
    if (-not $v) { continue }

    try {
        switch ($v.type) {

            "quit" { break MAIN }

            # --- Sprint Control ---
            "sprint_wizard"  { Invoke-SprintWizard; (Cur).items = Build-MainMenu; continue }
            "sprint_pause"   { Invoke-SprintPause;  (Cur).items = Build-MainMenu; continue }
            "sprint_resume"  { Invoke-SprintResume; (Cur).items = Build-MainMenu; continue }
            "sprint_stop"    { Invoke-SprintStop;   (Cur).items = Build-MainMenu; continue }

            # --- Monitoring ---
            "status_dashboard"    { Show-StatusDashboard; Pause-Notice ""; (Cur).items = Build-MainMenu; continue }
            "sprint_status_full"  { Show-SprintStatusFull; Pause-Notice ""; continue }
            "view_decision_trace" { Open-TailView $DecisionTracePath "Decision Trace"; continue }
            "view_audit_log"      { Open-TailView $AuditLogPath "Audit Log"; continue }

            # --- Agent Control ---
            "agent_terminal_menu" {
                Push-State @{
                    id="agent_terminal"
                    crumb="Agent Terminal"
                    header="Open Agent Terminal"
                    hint="Pick an agent, then a launch mode."
                    items=(Build-AgentPickMenu "open_agent")
                    ctx=@{}
                }
                continue
            }
            "attach_session_menu" {
                Push-State @{
                    id="attach_session"
                    crumb="Attach Session"
                    header="Attach to Session"
                    hint="Pick an agent to attach to its psmux session."
                    items=(Build-AgentPickMenu "attach_agent")
                    ctx=@{}
                }
                continue
            }
            "open_agent"      { Open-AgentTerminal $v.agent; Reset-ToHome; continue }
            "attach_agent"    { Attach-AgentSession $v.agent; Reset-ToHome; continue }
            "launch_agent"    { Launch-AgentWithMode $v.agent $v.mode; Reset-ToHome; continue }
            "resume_stuck_task"  { Invoke-ResumeStuckTask; continue }
            "override_verdict"   { Invoke-OverrideVerdict; continue }
            "clear_halt_flags"   { Invoke-ClearHaltFlags; (Cur).items = Build-MainMenu; continue }

            # --- Hook Control ---
            "toggle_hook"      { Invoke-ToggleHook; continue }
            "hook_status"      { Show-HookStatus; Pause-Notice ""; continue }
            "hooks_enable_all" { Set-AllHooks $true;  Pause-Notice "All hooks enabled."; continue }
            "hooks_disable_all"{ Set-AllHooks $false; Pause-Notice "All hooks disabled."; continue }
            "sprint_mode_on"   { Set-SprintMode $true;  (Cur).items = Build-MainMenu; continue }
            "sprint_mode_off"  { Set-SprintMode $false; (Cur).items = Build-MainMenu; continue }
            "folder_unlock"    { Invoke-FolderUnlock; (Cur).items = Build-MainMenu; continue }

            # --- Install Options (submenu) ---
            "install_menu" {
                Push-State @{
                    id="install"
                    crumb="Install Options"
                    header="Install Options"
                    hint="Deploy, delete, backup, or restore orchestrator components."
                    items=(Build-InstallMenu)
                    ctx=@{}
                }
                continue
            }
            "deploy_to_project"    { Invoke-DeployToProject; continue }
            "deploy_engine"        { Invoke-DeployEngine; continue }
            "delete_from_project"  { Invoke-DeleteFromProject; continue }
            "delete_engine"        { Invoke-DeleteEngine; continue }
            "backup_settings"      { Invoke-BackupSettings; continue }
            "restore_settings"     { Invoke-RestoreSettings; continue }

            # --- Configuration ---
            "change_project"   { Invoke-ChangeProject; continue }
            "validate_config"  { Invoke-ValidateConfig; continue }
            "doctor"           { Invoke-Doctor; continue }
            "reset_watcher"    { Invoke-ResetWatcher; (Cur).items = Build-MainMenu; continue }
            "kill_watcher"     { Invoke-KillWatcher;  (Cur).items = Build-MainMenu; continue }

            # --- Quick Access ---
            "open_folder" {
                if ($v.path -and (Test-Path $v.path)) {
                    Start-Process explorer.exe $v.path
                } else {
                    Write-Host "  Path not found: $($v.path)" -ForegroundColor Red
                }
                Pause-Notice ""
                continue
            }
            "open_file" {
                if ($v.path -and (Test-Path $v.path)) {
                    Start-Process $v.path
                } else {
                    Write-Host "  File not found: $($v.path)" -ForegroundColor Red
                }
                Pause-Notice ""
                continue
            }
            "agent_inboxes_menu" {
                Push-State @{
                    id="agent_inboxes"
                    crumb="Agent Inboxes"
                    header="Pick Agent Inbox"
                    hint="Opens the agent's inbox folder in Explorer."
                    items=(Build-AgentInboxMenu)
                    ctx=@{}
                }
                continue
            }
            "open_agent_inbox" {
                $inboxPath = Join-Path $DispatchDir "$($v.agent)\inbox"
                if (Test-Path $inboxPath) { Start-Process explorer.exe $inboxPath }
                else { Write-Host "  Inbox not found: $inboxPath" -ForegroundColor Red }
                Pause-Notice ""
                continue
            }

            default {
                Write-Host "  Unknown action: $($v.type)" -ForegroundColor Red
                Pause-Notice ""
                continue
            }
        }
    }
    catch {
        Write-Host ""
        Write-Host ("ERROR: " + $_.Exception.Message) -ForegroundColor Red
        Write-Host "Press any key to return..." -ForegroundColor DarkGray
        [void][Console]::ReadKey($true)
        continue
    }
}
