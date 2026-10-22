@echo off
setlocal
pushd "%~dp0"
if not exist "dashboard\index.html" (
  echo Cannot find dashboard\index.html. Put this launcher in the dashboard_crypto root folder.
  pause
  popd
  exit /b 1
)
for %%D in (evidence_20261019 pit_nested_20261020 release_20261025) do (
  if not exist "outputs\research\%%D\dashboard.html" (
    if not exist "outputs\research\%%D" mkdir "outputs\research\%%D"
    >"outputs\research\%%D\dashboard.html" echo ^<!doctype html^>^<meta charset="utf-8"^>^<meta http-equiv="refresh" content="0;url=../../../dashboard/index.html"^>^<a href="../../../dashboard/index.html"^>Open Orbit dashboard^</a^>
  )
)
start "" "%~dp0dashboard\index.html"
popd
endlocal
