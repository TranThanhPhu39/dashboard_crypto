param([Parameter(Mandatory=$true)][string]$Title,[Parameter(Mandatory=$true)][string]$Message,[Parameter(Mandatory=$true)][string]$AppId)
$ErrorActionPreference = 'Stop'
try {
    $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    $null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $safeTitle = [Security.SecurityElement]::Escape($Title)
    $safeMessage = [Security.SecurityElement]::Escape($Message)
    $xml.LoadXml('<toast><visual><binding template="ToastGeneric"><text>' + $safeTitle + '</text><text>' + $safeMessage + '</text></binding></visual></toast>')
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    $toast.Tag = 'Topic09'; $toast.Group = 'Topic09Automation'
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId)
    # Some Windows PowerShell WinRT projections expose this enum as null.
    # Submit via Show without claiming that the user saw the notification.
    if ($null -ne $notifier.Setting -and $notifier.Setting.ToString() -ne 'Enabled') { throw ('Notifications setting: ' + $notifier.Setting.ToString()) }
    $notifier.Show($toast)
    Write-Output 'Submitted to Windows notification center; display depends on notification settings.'
    exit 0
} catch {
    Write-Output $_.ScriptStackTrace
    Write-Error $_
    exit 1
}
