import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

# In app_launcher.py
def launch_flask():
    try:
        # Get directory path
        application_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

        flask_app = Path(application_path) / "main.py"
        
        # Launch Flask as a single process
        process = subprocess.Popen(
            [sys.executable, str(flask_app)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=application_path
        )
        
        # Wait for Flask to fully start
        time.sleep(3)  # Increased from 2 to 3 seconds
        
        # Single browser launch attempt
        try:
            chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe %s'
            webbrowser.get(chrome_path).open('http://127.0.0.1:5000')
        except:
            webbrowser.open('http://127.0.0.1:5000')
        
        return process

    except Exception as e:
        with open(Path(application_path) / 'error_log.txt', 'w') as f:
            f.write(f"Error: {str(e)}")
            
if __name__ == '__main__':
    flask_process = launch_flask()
    try:
        flask_process.wait()
    except KeyboardInterrupt:
        flask_process.terminate()