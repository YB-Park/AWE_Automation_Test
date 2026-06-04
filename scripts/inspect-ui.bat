@echo off
setlocal

set "CONFIG=%~1"
if not "%CONFIG%"=="" (
  for %%C in ("%CONFIG%") do set "CONFIG=%%~fC"
)

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." || exit /b 1

if "%CONFIG%"=="" (
  python -m awe_gui_builder inspect --verbose
) else (
  python -m awe_gui_builder inspect --config "%CONFIG%" --verbose
)
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%
