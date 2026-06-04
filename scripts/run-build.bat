@echo off
setlocal

if "%~1"=="" goto usage
if "%~2"=="" goto usage

set INPUT_AWJ=%~1
set OUTPUT_DIR=%~2
set CONFIG=%~3

if "%CONFIG%"=="" (
  python -m awe_gui_builder build --input "%INPUT_AWJ%" --output "%OUTPUT_DIR%"
) else (
  python -m awe_gui_builder build --config "%CONFIG%" --input "%INPUT_AWJ%" --output "%OUTPUT_DIR%"
)
exit /b %ERRORLEVEL%

:usage
echo Usage: scripts\run-build.bat C:\work\test.awj C:\work\awe_build [configs\sample.local.json]
exit /b 2
