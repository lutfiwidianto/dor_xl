@echo off
setlocal
set ROOT=%~dp0

echo [1/4] Create virtual environment
py -3 -m venv "%ROOT%venv"

echo [2/4] Activate virtual environment
call "%ROOT%venv\Scripts\activate.bat"

echo [3/4] Install Python dependencies
pip install -r "%ROOT%requirements.txt"

echo [4/4] Create dor.cmd launcher
set DORCMD=%ROOT%dor.cmd
echo @echo off> "%DORCMD%"
echo call "%ROOT%venv\Scripts\activate.bat">> "%DORCMD%"
echo py "%ROOT%main.py">> "%DORCMD%"

echo.
echo Done. Run: dor
echo If "dor" is not found, run it via:
echo "%ROOT%dor.cmd"
endlocal
