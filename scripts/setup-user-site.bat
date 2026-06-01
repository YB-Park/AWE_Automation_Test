@echo off
setlocal

python -m pip install --user -r requirements.txt
python -m awe_gui_builder --help
