@echo off
echo Cleaning up old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Installing required packages...
python -m pip install --upgrade pip
pip install --upgrade -r requirements.txt
pip install --upgrade pyinstaller

echo Building executable...
pyinstaller --clean shotover_qc_tool.spec

echo Done!
pause