@echo off
setlocal
if not exist "%~dp0outputs\research\evidence_20261019\report_view.html" (
  echo Cannot find report_view.html. Extract the complete fix package into the dashboard_crypto root folder.
  pause
  exit /b 1
)
start "" "%~dp0outputs\research\evidence_20261019\report_view.html"
endlocal
