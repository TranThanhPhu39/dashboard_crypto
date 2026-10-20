param([ValidateSet('Plan','Install','Status','RunNow','RunMonitor','Pause','Resume','Uninstall')][string]$Action='Status',[string]$PythonExecutable)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$configPath=Join-Path $projectRoot 'config\automation_20261020.json'
$cfg=Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$outputDir=Join-Path $projectRoot 'outputs\automation_20261020'
$null=New-Item -ItemType Directory -Path $outputDir -Force
$utf8=[Text.UTF8Encoding]::new($false)
function Save-JsonAtomic([string]$File,[object]$Value) {
    $temporary=$File+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
    [IO.File]::WriteAllText($temporary,($Value | ConvertTo-Json -Depth 15),$utf8)
    if (Test-Path -LiteralPath $File) {
        $backup=$temporary+'.backup'
        [IO.File]::Replace($temporary,$File,$backup)
        if ([IO.File]::Exists($backup)) { [IO.File]::Delete($backup) }
    }
    else { [IO.File]::Move($temporary,$File) }
}
$installationFile=Join-Path $outputDir 'installation.json'
$installation=$null
if (Test-Path -LiteralPath $installationFile) { $installation=Get-Content -LiteralPath $installationFile -Raw -Encoding UTF8 | ConvertFrom-Json }
$runner=Join-Path $projectRoot 'run_automation.py'
if (-not $PythonExecutable -and $installation) { $PythonExecutable=$installation.python_executable }
if (-not $PythonExecutable -and $Action -in @('Plan','Install')) {
    $PythonExecutable=(& py -3.11 -c 'import sys; print(sys.executable)').Trim()
}
function Verify-OwnTask([object]$Task,[string]$Stage,[string]$PythonWindowless) {
    $expected='"'+$runner+'" '+$Stage
    return $Task.Actions.Count -eq 1 -and $Task.Actions[0].Execute -eq $PythonWindowless -and $Task.Actions[0].Arguments -eq $expected -and $Task.Actions[0].WorkingDirectory -eq $projectRoot
}
if ($Action -in @('Plan','Install')) {
    if ((Get-TimeZone).Id -ne $cfg.windows_timezone) { throw 'Windows timezone differs from the declared schedule; no timezone was changed.' }
    if (-not (Test-Path -LiteralPath $PythonExecutable)) { throw 'Python 3.11 executable not found.' }
    $pythonWindowless=Join-Path (Split-Path -Parent $PythonExecutable) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonWindowless)) { throw 'pythonw.exe not found.' }
    $account=[Security.Principal.WindowsIdentity]::GetCurrent().Name
    if ($account -like '*CodexSandbox*') { throw 'Run installation in the user context, not a sandbox account.' }
    $principal=New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
    $endLocal=[DateTimeOffset]::Parse($cfg.stop_after_utc).ToLocalTime().ToString('yyyy-MM-ddTHH:mm:sszzz')
    $definitions=@()
    foreach ($item in @(@{Name=$cfg.pipeline_task;Stage='run';Minute=$cfg.pipeline_minute;Role='pipeline'},@{Name=$cfg.monitor_task;Stage='monitor';Minute=$cfg.monitor_minute;Role='monitor'})) {
        $clock=Get-Date
        $start=$clock.Date.AddHours($clock.Hour).AddMinutes([int]$item.Minute)
        if ($start -le $clock) { $start=$start.AddHours(1) }
        $periodic=New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes ([int]$cfg.repeat_minutes))
        $periodic.EndBoundary=$endLocal
        $logon=New-ScheduledTaskTrigger -AtLogOn -User $account
        $logon.Delay=if ($item.Role -eq 'pipeline') { 'PT2M' } else { 'PT5M' }
        $logon.EndBoundary=$endLocal
        $taskAction=New-ScheduledTaskAction -Execute $pythonWindowless -Argument ('"'+$runner+'" '+$item.Stage) -WorkingDirectory $projectRoot
        $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -Hidden -ExecutionTimeLimit (New-TimeSpan -Minutes ([int]$cfg.task_execution_limit_minutes)) -RestartCount ([int]$cfg.scheduler_restart_count) -RestartInterval (New-TimeSpan -Minutes ([int]$cfg.scheduler_restart_minutes))
        $definition=New-ScheduledTask -Action $taskAction -Trigger @($periodic,$logon) -Settings $settings -Principal $principal -Description ('Topic09 authorized automation; '+$item.Role+'; workspace '+$projectRoot+'; no model refits or early OOS scoring.')
        $definitions+=@{Item=$item;Definition=$definition}
    }
    if ($Action -eq 'Plan') {
        [pscustomobject]@{Account=$account;Python=$PythonExecutable;Root=$projectRoot;PipelineMinute=$cfg.pipeline_minute;MonitorMinute=$cfg.monitor_minute;EndLocal=$endLocal;LogonType='Interactive';PasswordStored=$false;TaskNames=@($cfg.pipeline_task,$cfg.monitor_task)} | ConvertTo-Json -Depth 5
        exit 0
    }
    foreach ($entry in $definitions) {
        $existing=Get-ScheduledTask -TaskName $entry.Item.Name -ErrorAction SilentlyContinue
        if ($existing -and -not (Verify-OwnTask $existing $entry.Item.Stage $pythonWindowless)) { throw ('Task name collision: '+$entry.Item.Name) }
    }
    foreach ($entry in $definitions) {
        $registered=Register-ScheduledTask -TaskName $entry.Item.Name -InputObject $entry.Definition -Force
        $xml=(Export-ScheduledTask -TaskName $entry.Item.Name) -replace 'encoding="UTF-16"','encoding="utf-8"'
        [IO.File]::WriteAllText((Join-Path $outputDir ($entry.Item.Role+'_task.xml')),$xml,$utf8)
    }
    $app=Get-StartApps | Where-Object { $_.Name -eq 'Windows PowerShell' } | Select-Object -First 1
    $record=[ordered]@{registered=$true;installed_at_utc=[DateTimeOffset]::UtcNow.ToString('o');account=$account;project_root=$projectRoot;python_executable=$PythonExecutable;python_windowless=$pythonWindowless;desktop_notifications=[bool]$cfg.desktop_notifications;toast_app_id=$app.AppID;config_sha256=(Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLower();authorization=$cfg.authorization;logon_type='Interactive';password_stored=$false;end_local=$endLocal}
    Save-JsonAtomic $installationFile $record
    $installation=[pscustomobject]$record
}
if ($Action -in @('Pause','Resume')) {
    if (-not $installation.registered) { throw 'No owned installation to pause/resume.' }
    foreach ($item in @(@{Name=$cfg.pipeline_task;Stage='run'},@{Name=$cfg.monitor_task;Stage='monitor'})) {
        $task=Get-ScheduledTask -TaskName $item.Name
        if (-not (Verify-OwnTask $task $item.Stage $installation.python_windowless)) { throw ('Task identity differs: '+$item.Name) }
    }
    foreach ($name in @($cfg.pipeline_task,$cfg.monitor_task)) {
        if ($Action -eq 'Pause') { $null=Disable-ScheduledTask -TaskName $name }
        else { $null=Enable-ScheduledTask -TaskName $name }
    }
    # Do not terminate an in-flight collector. The handoff script takes all
    # three OS locks before capturing the final authoritative local state.
}
if ($Action -eq 'Uninstall') {
    if (-not $installation) { throw 'No owned installation record; refusing task removal.' }
    foreach ($item in @(@{Name=$cfg.pipeline_task;Stage='run'},@{Name=$cfg.monitor_task;Stage='monitor'})) {
        $task=Get-ScheduledTask -TaskName $item.Name -ErrorAction SilentlyContinue
        if ($task) {
            if (-not (Verify-OwnTask $task $item.Stage $installation.python_windowless)) { throw ('Task identity differs: '+$item.Name) }
            Stop-ScheduledTask -TaskName $item.Name -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $item.Name -Confirm:$false
        }
    }
    $installation.registered=$false
    Save-JsonAtomic $installationFile $installation
}
if ($Action -in @('RunNow','RunMonitor')) {
    if (-not $installation.registered) { throw 'Automation is not installed.' }
    $name=if ($Action -eq 'RunNow') { $cfg.pipeline_task } else { $cfg.monitor_task }
    $stage=if ($Action -eq 'RunNow') { 'run' } else { 'monitor' }
    $task=Get-ScheduledTask -TaskName $name
    if (-not (Verify-OwnTask $task $stage $installation.python_windowless)) { throw 'Scheduled task identity differs.' }
    Start-ScheduledTask -TaskName $name
}
$rows=@()
foreach ($item in @(@{Name=$cfg.pipeline_task;Stage='run';Role='pipeline'},@{Name=$cfg.monitor_task;Stage='monitor';Role='monitor'})) {
    $task=Get-ScheduledTask -TaskName $item.Name -ErrorAction SilentlyContinue
    if ($task) {
        $info=Get-ScheduledTaskInfo -TaskName $item.Name
        $currentXml=(Export-ScheduledTask -TaskName $item.Name) -replace 'encoding="UTF-16"','encoding="utf-8"'
        [IO.File]::WriteAllText((Join-Path $outputDir ($item.Role+'_task.xml')),$currentXml,$utf8)
        $rows+=@{name=$item.Name;role=$item.Role;enabled=[bool]$task.Settings.Enabled;state=$task.State.ToString();action_matches=[bool]($installation -and (Verify-OwnTask $task $item.Stage $installation.python_windowless));next_run_local=([DateTimeOffset]$info.NextRunTime).ToString('o');last_run_local=([DateTimeOffset]$info.LastRunTime).ToString('o');last_task_result=$info.LastTaskResult;execute=$task.Actions[0].Execute;arguments=$task.Actions[0].Arguments;start_when_available=$task.Settings.StartWhenAvailable;wake_to_run=$task.Settings.WakeToRun;multiple_instances=$task.Settings.MultipleInstances.ToString();run_level=$task.Principal.RunLevel.ToString();logon_type=$task.Principal.LogonType.ToString()}
    }
}
$verified=$rows.Count -eq 2 -and @($rows | Where-Object { -not $_.enabled -or -not $_.action_matches }).Count -eq 0
$status=[ordered]@{checked_at_utc=[DateTimeOffset]::UtcNow.ToString('o');verified=[bool]$verified;tasks=@($rows);timezone=(Get-TimeZone).Id}
Save-JsonAtomic (Join-Path $outputDir 'scheduler_status.json') $status
$status | ConvertTo-Json -Depth 10
