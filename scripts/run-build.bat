@echo off
setlocal

if "%~1"=="" goto usage
if "%~2"=="" goto usage

rem Resolve user-provided paths before changing directory.
for %%I in ("%~1") do set "INPUT_AWJ=%%~fI"
for %%O in ("%~2") do set "OUTPUT_DIR=%%~fO"
set "CONFIG=%~3"
if not "%CONFIG%"=="" (
  for %%C in ("%CONFIG%") do set "CONFIG=%%~fC"
)

rem Move to repository root so `python -m awe_gui_builder` can import the local package
rem even when this .bat is launched from another working directory.
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." || exit /b 1

if "%CONFIG%"=="" (
  python -m awe_gui_builder build --input "%INPUT_AWJ%" --output "%OUTPUT_DIR%"
) else (
  python -m awe_gui_builder build --config "%CONFIG%" --input "%INPUT_AWJ%" --output "%OUTPUT_DIR%"
)
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%

:usage
echo Usage: scripts\run-build.bat C:\work\test.awj C:\work\awe_build [configs\sample.local.json]
exit /b 2
