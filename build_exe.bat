@echo off
echo Checking current directory...
cd /d "%~dp0"

echo Cleaning Python cache...
del /s /q *.pyc >nul 2>&1
del /s /q __pycache__ >nul 2>&1

echo Cleaning up old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Setting up clean environment...
if exist venv (
    echo Using existing venv...
    call venv\Scripts\activate
) else (
    echo Creating new venv...
    python -m venv venv
    call venv\Scripts\activate
)

echo Installing required packages...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo Building executable...
pyinstaller --clean shotover_qc_tool.spec

echo Done!
if exist dist (
    echo Build successful! Executable is in the dist folder.
) else (
    echo Build may have failed. Check the output above.
)

pause