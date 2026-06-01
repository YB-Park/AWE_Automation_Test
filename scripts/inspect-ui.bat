@echo off
setlocal

set CONFIG=%~1
if "%CONFIG%"=="" set CONFIG=configs\sample.local.json

python -m awe_gui_builder inspect --config "%CONFIG%"
exit /b %ERRORLEVEL%
