@echo off
setlocal

set CONFIG=%~1

if "%CONFIG%"=="" (
  python -m awe_gui_builder inspect --verbose
) else (
  python -m awe_gui_builder inspect --config "%CONFIG%" --verbose
)
exit /b %ERRORLEVEL%
