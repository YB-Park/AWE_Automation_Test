@echo off
setlocal

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 -m venv .venv
) else (
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m awe_gui_builder --help
