import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def launch_flask():
    try:
        # Get the directory containing the executable
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        # Set Flask environment variables
        os.environ['FLASK_APP'] = 'main.py'  # Change this to your actual Flask app filename
        os.environ['FLASK_ENV'] = 'production'
        
        # Path to Flask app
        flask_app = Path(application_path) / "main.py"  # Change this to your actual Flask app filename
        
        # Launch Flask without console
        process = subprocess.Popen(
            [sys.executable, str(flask_app)],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=application_path
        )
        
        # Wait for Flask to start
        time.sleep(2)
        
        # Open browser (prioritize Chrome)
        try:
            chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
            browser = webbrowser.get(chrome_path)
        except:
            browser = webbrowser.get()
        browser.open('http://127.0.0.1:5000')
        
        return process
        
    except Exception as e:
        error_log = Path(application_path) / 'error_log.txt'
        with open(error_log, 'w') as f:
            f.write(f"Error: {str(e)}")

if __name__ == '__main__':
    flask_process = launch_flask()
    try:
        flask_process.wait()
    except KeyboardInterrupt:
        flask_process.terminate()