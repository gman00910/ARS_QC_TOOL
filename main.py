from asyncio import log
import ctypes
import subprocess
import sys
import os 
from flask import Flask, render_template, request, redirect, url_for, jsonify
import webbrowser
from threading import Timer, Thread
import main_script 
import logging
from logging.config import dictConfig
import win32gui
import win32con
import sys
import ctypes
from datetime import datetime
import tempfile
from colorama import Fore, Style
import time
import logging
import traceback
from datetime import datetime
import psutil
import logging
from datetime import datetime
import os
import json

class ProcessTracker:
    def __init__(self):
        # Set up logging
        self.log_dir = 'process_logs'
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.log_file = os.path.join(
            self.log_dir, 
            f'process_tracker_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        
        # Configure logging
        self.logger = logging.getLogger('ProcessTracker')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # Track initial state
        self.initial_processes = self.get_current_processes()
        self.log_process_state("Initial process state")

    def get_current_processes(self):
        processes = {}
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):  # Removed 'parent'
            try:
                pinfo = proc.as_dict(['pid', 'name', 'cmdline', 'create_time'])
                try:
                    pinfo['parent'] = proc.parent().pid if proc.parent() else None
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pinfo['parent'] = None
                processes[proc.pid] = pinfo
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def log_process_state(self, event_type="Process Check"):
        current_processes = self.get_current_processes()
        
        # Look for new processes
        for pid, proc_info in current_processes.items():
            if pid not in self.initial_processes:
                if any(term in proc_info['name'].lower() for term in ['python', 'powershell', 'cmd', 'shell']):
                    self.logger.info(f"""
New Process Detected:
Event: {event_type}
PID: {pid}
Name: {proc_info['name']}
Command: {' '.join(proc_info['cmdline']) if proc_info['cmdline'] else 'N/A'}
Parent PID: {proc_info['parent']}
Creation Time: {datetime.fromtimestamp(proc_info['create_time']).strftime('%Y-%m-%d %H:%M:%S.%f')}
""")

        # Look for terminated processes
        for pid, proc_info in self.initial_processes.items():
            if pid not in current_processes:
                if any(term in proc_info['name'].lower() for term in ['python', 'powershell', 'cmd', 'shell']):
                    self.logger.info(f"""
Process Terminated:
Event: {event_type}
PID: {pid}
Name: {proc_info['name']}
Command: {' '.join(proc_info['cmdline']) if proc_info['cmdline'] else 'N/A'}
""")

        # Update initial state
        self.initial_processes = current_processes

    def log_subprocess_call(self, command, cwd=None):
        self.logger.info(f"""
Subprocess Call:
Command: {command}
Working Directory: {cwd or 'Default'}
Current Process ID: {os.getpid()}
""")
        self.log_process_state("Subprocess Call")

# Create a global instance
process_tracker = ProcessTracker()








# Set up logging
log_filename = f'app_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # This will print to console as well
    ]
)
logger = logging.getLogger(__name__)

# Add this function to track subprocess calls
def log_subprocess_execution(cmd, cwd=None):
    logger.debug(f"""
Subprocess Execution:
Command: {cmd}
Working Directory: {cwd or 'Default'}
Process ID: {os.getpid()}
Python Executable: {sys.executable}
Arguments: {sys.argv}
""")
    

def get_subprocess_flags():
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {
            'startupinfo': startupinfo,
            'creationflags': subprocess.CREATE_NO_WINDOW,
            'shell': False
        }
    return {'shell': False}

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    if sys.platform == 'win32':
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            f'"{sys.argv[0]}"', None, 1
        )
        sys.exit(0)

def run_as_admin():
    if not is_admin():
        if sys.platform == 'win32':
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                f'"{sys.argv[0]}"',
                None,
                1
            )
            sys.exit(0)
    return True

app = Flask(__name__, 
           static_url_path='/static',
           static_folder='static',
           template_folder='templates')
    
def minimize_console():
    def enum_windows(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            if "python.exe" in window_title.lower():
                windows.append(hwnd)
    
    windows = []
    win32gui.EnumWindows(enum_windows, windows)
    
    for hwnd in windows:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    
@app.route('/')
def index():
    dhcp_info = main_script.check_dhcp_status()
    network_profiles = main_script.get_network_profile()
    # task_scheduler_data = main_script.check_task_scheduler_status()
    # print("Debug - Raw task data:", task_scheduler_data)  # Debug print
    task_scheduler_data = main_script.check_task_scheduler_status()
    try:
        dhcp_info = main_script.check_dhcp_status()
        app.logger.debug(f"DHCP info: {dhcp_info}")
        
        network_profiles = main_script.get_network_profile()
        app.logger.debug(f"Network profiles: {network_profiles}")
        
        # Add debugging before formatting
        app.logger.debug(f"Task scheduler data type: {type(task_scheduler_data)}")
        
        #formatted_tasks = main_script.format_task_scheduler_for_web(task_scheduler_data)
        #app.logger.debug(f"Formatted task data: {formatted_tasks}")
        
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500
        
    #2nd task scheduler debugger - maybe delete???
    if task_scheduler_data is None:
        print("Debug - No task scheduler data returned")
        task_scheduler_formatted = ['<div class="task-error">Error retrieving task scheduler data</div>']
    else:
        task_scheduler_formatted = main_script.format_task_scheduler_for_web(task_scheduler_data)
        
    # Merge network profile info into DHCP info
    if isinstance(dhcp_info, dict) and isinstance(network_profiles, dict):
        for interface_name, interface_info in dhcp_info.items():
            # Find matching interface in network_profiles
            for profile_name, category in network_profiles.items():
                if profile_name in interface_name:
                    # Add category to Type
                    interface_info['Type'] = f"{interface_info['Type']} (Category: {category})"
    try:
        result = {
            'Computer Name': main_script.get_computer_name(),
            'Windows Activation': main_script.check_windows_activation(),
            'Task Scheduler Status': main_script.format_task_scheduler_for_web(task_scheduler_data),
            'IP Configuration': main_script.check_dhcp_status(), 
            'Time Zone': main_script.get_time_zone(),
            'Display Info': main_script.get_display_info(),
            'ARS Version': main_script.get_ars_version(),
            'Boot Drive Version': main_script.get_boot_drive_version(),
            'COM Ports': main_script.get_com_ports(),
            'ARS Shortcut': main_script.check_ars_shortcut(),
            'VIB Version': main_script.get_vib_version(),
            'FX3 Version': main_script.get_fx3_version(),
            'Computer Metrics': main_script.computer_metrics(),
            'Windows Defender Status': main_script.windows_defender_status(),
            'Firewall Status': main_script.check_firewall_status(),
            'Defrag Status': main_script.check_defrag_settings(),
            'Drive Health': main_script.quick_drive_check(),
            'Network Profile': main_script.get_network_profile(),
            'Windows Update': main_script.is_windows_update_enabled(),
            }
        print("Debug - Formatted task data:", result['Task Scheduler Status'])  # Debug print
        return render_template('index.html', result=result)
    except Exception as e:
        print(f"Error in route: {str(e)}")
        return "Error loading page", 500

@app.route('/change/<setting>', methods=['GET', 'POST'])
def change_setting(setting):
    if request.method == 'POST':
        if setting == 'time_zone':
            new_timezone = request.form.get('new_value')
            result = main_script.change_time_zone(new_timezone)
            # Return to main page immediately after change
            return redirect(url_for('index'))
    
    if setting == 'time_zone':
        timezones = main_script.get_available_timezones()
        return render_template('change_setting.html', setting=setting, timezones=timezones)
    
    else:
        result = "Setting not supported for changes"
        
    return render_template('result.html', result=result)

@app.route('/run_viblib', methods=['POST'])
def run_viblib_route():
    try:
        preset_paths = [
            r"C:\maintenance\vib_lib\viblib_test.exe",
            r"C:\ARS\vib_lib\viblib_test.exe",
            r"C:\maintenance\testing\vib_production_test\viblib_test.exe",
            r"C:\ion\ion_v4.4.39\viblib_test.exe",
            r"C:\ARS\atom_tools\viblib\viblib_test.exe",
            r"D:\maintenance\vib_lib\viblib_test.exe",
            r"D:\ARS\vib_lib\viblib_test.exe",
            r"D:\maintenance\testing\vib_production_test\viblib_test.exe",
            r"D:\ion\ion_v4.4.39\viblib_test.exe",
            r"D:\ARS\atom_tools\viblib\viblib_test.exe"
        ]
        
        for path in preset_paths:
            if os.path.exists(path):
                subprocess.Popen([path], **get_subprocess_flags())
                return jsonify({"success": True})
                
        return jsonify({"success": False, "error": "VibLib executable not found"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/change_ip', methods=['GET', 'POST'])
def change_ip():
    if request.method == 'POST':
        interface_name = request.form.get('interface_name')
        use_dhcp = request.form.get('use_dhcp') == 'true'
        ip_address = request.form.get('ip_address')
        subnet_mask = request.form.get('subnet_mask')
        gateway = request.form.get('gateway')
        
        result = main_script.change_ip_configuration(interface_name, use_dhcp, ip_address, subnet_mask, gateway)
        
        # Return JSON for AJAX handling
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'result': result, 'success': 'Failed' not in result})
            
        return redirect(url_for('index'))
    
    interfaces = main_script.check_dhcp_status()
    return render_template('change_ip.html', interfaces=interfaces)

@app.route('/open_command_prompt')
def open_command_prompt():
    try:
        process_tracker.logger.info("open_command_prompt route called")
        process_tracker.log_process_state("Before Command Prompt Open")
        logger.debug("Starting open_command_prompt route")
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
        logger.debug(f"Script path: {script_path}")
        
        batch_content = f'''@echo off
title SHOTOVER Systems - Drive Summary Details
color 0A
cd /d "{os.path.dirname(script_path)}"
"{sys.executable}" "{script_path}" --cli-only
echo.
pause >nul
'''
        batch_file = os.path.join(os.environ['TEMP'], 'shotover_summary.bat')
        logger.debug(f"Creating batch file at: {batch_file}")
        
        with open(batch_file, 'w') as f:
            f.write(batch_content)
        
        logger.debug("Attempting to execute batch file")
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            f"/c {batch_file}",
            None,
            1
        )

        logger.debug("Batch file execution completed")
        process_tracker.log_process_state("After Command Prompt Open")
        return "", 204
    except Exception as e:
        process_tracker.logger.error(f"Error in open_command_prompt: {str(e)}")
        return str(e), 500
    

@app.route('/Openshell')
def Openshell():
    try:
        process_tracker.logger.info("Openshell route called")
        process_tracker.log_process_state("Before PowerShell Open")
        logger.debug("Starting Openshell route")
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
        logger.debug(f"Script path: {script_path}")
        
        powershell_content = f'''
$Host.UI.RawUI.WindowTitle = "SHOTOVER Systems - Drive Summary Details"
Set-Location '{os.path.dirname(script_path)}'
& "{sys.executable}" "{script_path}" --cli-only
Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
'''
        batch_file = os.path.join(os.environ['TEMP'], 'shotover_summary.ps1')
        logger.debug(f"Creating PowerShell script at: {batch_file}")
        
        with open(batch_file, 'w') as f:
            f.write(powershell_content)
        
        logger.debug("Attempting to execute PowerShell script")
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "powershell.exe",
            f"-NoProfile -ExecutionPolicy Bypass -File {batch_file}",
            None,
            1
        )
        logger.debug("PowerShell script execution completed")
        process_tracker.log_process_state("After PowerShell Open")
        return "", 204
    except Exception as e:
        process_tracker.logger.error(f"Error in Openshell: {str(e)}")
        return str(e), 500


@app.route('/printt')
def printt():
    try:
        # Get the current date/time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Run the script and capture output
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        output = result.stdout

        # Convert ANSI color codes to HTML classes
        output = (output
            .replace(f"{Fore.CYAN}", '<span class="cyan">')
            .replace(f"{Fore.GREEN}", '<span class="green">')
            .replace(f"{Fore.RED}", '<span class="red">')
            .replace(f"{Fore.YELLOW}", '<span class="yellow">')
            .replace(f"{Style.RESET_ALL}", '</span>')
        )

        # Render the template with the colored output
        return render_template('print_view.html', 
                             output=output, 
                             current_time=current_time)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/run_ars', methods=['POST'])
def run_ars_route():
    try:
        # Search for runloader.cmd first
        cmd_paths = [
            r"D:\ARS\bin\loader\runloader.cmd",
            r"C:\ARS\bin\loader\runloader.cmd",
            r"E:\ARS\bin\loader\runloader.cmd",
            r"D:\ARS\loader\runloader.cmd",
            r"C:\ARS\loader\runloader.cmd",
            r"E:\ARS\loader\runloader.cmd"
        ]
        
        # Search for ars.exe as fallback
        exe_paths = [
            r"D:\ARS\bin\ars.exe",
            r"C:\ARS\bin\ars.exe",
            r"D:\ARS\ars.exe",
            r"C:\ARS\ars.exe"
        ]
        
        for path in cmd_paths:
            if os.path.exists(path):
                start_dir = os.path.dirname(path)
                subprocess.Popen(
                    [path],
                    cwd=start_dir,
                    **get_subprocess_flags()
                )
                return jsonify({"success": True})
                
        for path in exe_paths:
            if os.path.exists(path):
                subprocess.Popen(
                    [path],
                    **get_subprocess_flags()
                )
                return jsonify({"success": True})
                
        return jsonify({"success": False, "error": "ARS executable not found"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
def open_browser():
    url = 'http://127.0.0.1:5000'
    try:
        # Use a simpler browser opening approach
        webbrowser.get('windows-default').open(url, new=2, autoraise=True)
    except Exception as e:
        print(f"Error opening browser: {e}")

if __name__ == '__main__':
    process_tracker.logger.info("Application Starting")
    process_tracker.log_process_state("Application Start")

    if is_admin():
        process_tracker.logger.info("Running with admin privileges")
        
        # Start Flask without threading
        app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
        
        # Open browser after Flask starts
        Timer(1.5, open_browser).start()
    else:
        process_tracker.logger.warning("Not running with admin privileges")
        # Handle non-admin case


def minimize_console():
    try:
        def enum_windows(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                # Only minimize the main Python/Flask window
                if ("python" in title.lower() or "flask" in title.lower()) and "summary" not in title.lower():
                    windows.append(hwnd)
        
        windows = []
        win32gui.EnumWindows(enum_windows, windows)
        
        # Only minimize the main console window
        if windows:
            win32gui.ShowWindow(windows[0], win32con.SW_MINIMIZE)
            
    except Exception as e:
        print(f"Error minimizing console: {str(e)}")

# @app.after_request
# def add_cache_headers(response):
#     response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
#     return response

if __name__ == '__main__':
    process_tracker.logger.info("Application Starting")
    process_tracker.log_process_state("Application Start")

    if is_admin():
        process_tracker.logger.info("Running with admin privileges")
        
        def delayed_browser_open():
            process_tracker.log_process_state("Before Browser Open")
            open_browser()
            process_tracker.log_process_state("After Browser Open")

        def delayed_console_minimize():
            process_tracker.log_process_state("Before Console Minimize")
            minimize_console()
            process_tracker.log_process_state("After Console Minimize")

        Timer(0.3, delayed_browser_open).start()
        Timer(0.5, delayed_console_minimize).start()
        
        process_tracker.logger.info("Starting Flask server")
        app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
    else:
        process_tracker.logger.warning("Not running with admin privileges")