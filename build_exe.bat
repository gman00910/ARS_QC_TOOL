@echo off
echo Cleaning up old builds...
rmdir /s /q build
rmdir /s /q dist
del /f /q *.spec

echo Installing required packages...
pip install -r requirements.txt
pip install pyinstaller

echo Building executable...
pyinstaller --clean main.spec

echo Done!
pause