param(
    [Parameter(Position=0)] [string]$Command = "paths",
    [Parameter(Position=1)] [string]$Arg1 = "",
    [Parameter(Position=2)] [string]$Arg2 = ""
)

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ConfigPath = Join-Path $ProjectRoot ".orchestrator\config.json"
if (!(Test-Path $ConfigPath)) {
    Write-Error "Missing $ConfigPath"
    exit 1
}

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$primary = $config.shared_roots.orchestrator_primary
$fallback = $config.shared_roots.orchestrator_fallback
$orchRoot = if (Test-Path $primary) { $primary } elseif (Test-Path $fallback) { $fallback } else { $primary }

$ctl = Join-Path $orchRoot "scripts\orchestratorctl.py"
$watcher = Join-Path $orchRoot "scripts\watcher.py"

switch ($Command) {
    "paths"    { python $ctl paths $ProjectRoot; break }
    "doctor"   { python $ctl doctor $ProjectRoot; break }
    "validate" { python $ctl validate $ProjectRoot; break }
    "smoke"    { python $ctl smoke $ProjectRoot; break }
    "watcher"  { python $watcher $ProjectRoot; break }
    "stop"     { "stop" | Set-Content (Join-Path $ProjectRoot ".orchestrator\runtime\STOP"); break }
    "send"     { python $ctl send $ProjectRoot $Arg1 $Arg2; break }
    "hooks"    { 
        $agent = $Arg1 -replace '^gate-',''
        python (Join-Path $orchRoot "scripts\install_hooks.py") --project $ProjectRoot --agent $agent --settings-file $Arg2
        break 
    }
    "mcp"      { python $ctl render-mcp $ProjectRoot --agent $Arg1; break }
    default    { Write-Error "Unknown command: $Command"; exit 1 }
}
