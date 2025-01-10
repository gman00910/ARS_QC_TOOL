from asyncio import log
import ctypes
import subprocess
import sys
import os 
from flask import Flask, render_template, request, redirect, url_for, jsonify
import webbrowser
from threading import Timer
import main_script 
from logging.config import dictConfig
import win32gui
import win32con
import sys
import ctypes
from datetime import datetime
from colorama import Fore, Style
from flask import make_response
from functools import wraps
import time
from main_script import check_dhcp_status
from functools import lru_cache
from datetime import datetime, timedelta

# Cache configuration
cache = {}
EXCLUDED_PATHS = {'/change_ip', '/change/<setting>'} 


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

CACHE_DURATION = 300

def cache_control(max_age=30):
    def decorator(view_function):
        @wraps(view_function)
        def wrapped_function(*args, **kwargs):
            # Don't cache AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response = make_response(view_function(*args, **kwargs))
                response.headers['Cache-Control'] = 'no-store'
                return response

            # Don't cache excluded paths
            if request.path in EXCLUDED_PATHS:
                response = make_response(view_function(*args, **kwargs))
                response.headers['Cache-Control'] = 'no-store'
                return response

            cache_key = f"{request.path}:{request.query_string}"
            cached_data = cache.get(cache_key)
            
            if cached_data and time.time() - cached_data['timestamp'] < CACHE_DURATION:
                return cached_data['response']

            response = make_response(view_function(*args, **kwargs))
            cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }

            response.headers['Cache-Control'] = f'public, max-age={max_age}'
            return response
        return wrapped_function
    return decorator

@lru_cache(maxsize=1)
def get_cached_system_info():
    task_scheduler_data = main_script.check_task_scheduler_status() 
    return {
        'Computer Name': main_script.get_computer_name(),
        'Windows Activation': main_script.check_windows_activation(),
        'Task Scheduler Status': main_script.format_task_scheduler_for_web(task_scheduler_data),
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
        'Windows Notifications': main_script.check_notification_settings()
    }



# def clear_cache():
#     get_cached_system_info.cache_clear()

# @app.before_first_request
# def setup_cache_clearing():
#     from apscheduler.schedulers.background import BackgroundScheduler
#     scheduler = BackgroundScheduler()
#     scheduler.add_job(func=clear_cache, trigger="interval", seconds=CACHE_DURATION)
#     scheduler.start()


@app.route('/')
@cache_control(max_age=30)
def index():
    try:
        # Get cached data
        cached_info = get_cached_system_info()
        
        # Get real-time data that shouldn't be cached
        dhcp_info = main_script.check_dhcp_status()
        network_profiles = main_script.get_network_profile()
        task_scheduler_data = main_script.check_task_scheduler_status()  
            
        # Merge network profile info into DHCP info
        if isinstance(dhcp_info, dict) and isinstance(network_profiles, dict):
            for interface_name, interface_info in dhcp_info.items():
                for profile_name, category in network_profiles.items():
                    if profile_name in interface_name:
                        interface_info['Type'] = f"{interface_info['Type']} (Category: {category})"

        # Create result using ALL the original data points but use cached where possible
        result = {
            'Computer Name': cached_info['Computer Name'],
            'Windows Activation': cached_info['Windows Activation'],
            'Task Scheduler Status': main_script.format_task_scheduler_for_web(task_scheduler_data),
            'IP Configuration': dhcp_info, 
            'Time Zone': main_script.get_time_zone(),
            'Display Info': cached_info['Display Info'],
            'ARS Version': cached_info['ARS Version'],
            'Boot Drive Version': cached_info['Boot Drive Version'],
            'COM Ports': cached_info['COM Ports'],
            'ARS Shortcut': cached_info['ARS Shortcut'],
            'VIB Version': cached_info['VIB Version'],
            'FX3 Version': cached_info['FX3 Version'],
            'Computer Metrics': cached_info['Computer Metrics'],
            'Windows Defender Status': cached_info['Windows Defender Status'],
            'Firewall Status': cached_info['Firewall Status'], 
            'Defrag Status': cached_info['Defrag Status'],
            'Drive Health': cached_info['Drive Health'],
            'Network Profile': network_profiles,
            'Windows Update': cached_info['Windows Update'],
            'Windows Notifications': cached_info['Windows Notifications']
        }
        
        return render_template('index.html', result=result)
        
    except Exception as e:
        print(f"Error in route: {str(e)}")
        return "Error loading page", 500

@app.route('/change/<setting>', methods=['GET', 'POST'])
def change_setting(setting):
    try:
        if request.method == 'POST':
            if setting == 'time_zone':
                new_timezone = request.form.get('new_value')
                result = main_script.change_time_zone(new_timezone)
                # Instead of redirecting, return JSON
                return jsonify({
                    'success': True,
                    'message': result,
                    'newTimezone': new_timezone
                })
        
        if setting == 'time_zone':
            timezones = main_script.get_available_timezones()
            return render_template('change_setting.html', setting=setting, timezones=timezones)
        
        return jsonify({'success': False, 'error': 'Setting not supported'}), 400
        
    except Exception as e:
        print(f"Error in change_setting route: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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




# @app.route('/change_ip', methods=['GET', 'POST'])
# def change_ip():
#     if request.method == 'POST':
#         interface_name = request.form.get('interface_name')
#         use_dhcp = request.form.get('use_dhcp') == 'true'
#         ip_address = request.form.get('ip_address')
#         subnet_mask = request.form.get('subnet_mask')
#         gateway = request.form.get('gateway')
        
#         result = main_script.change_ip_configuration(
#             interface_name, use_dhcp, ip_address, subnet_mask, gateway
#         )
        
#         return jsonify({
#             'success': 'Failed' not in result,
#             'message': result
#         })
    
#     interfaces = main_script.check_dhcp_status()
#     return render_template('change_ip.html', interfaces=interfaces)
@app.route('/change_ip', methods=['GET', 'POST'])
def change_ip():
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            interface_name = request.form.get('interface_name')
            use_dhcp = request.form.get('use_dhcp') == 'true'
            ip_address = request.form.get('ip_address')
            subnet_mask = request.form.get('subnet_mask')
            gateway = request.form.get('gateway')
            
            result = main_script.change_ip_configuration(
                interface_name, use_dhcp, ip_address, subnet_mask, gateway
            )
            
            return jsonify({
                'success': 'Failed' not in result,
                'message': result
            })
    
    # GET request - make sure we have interfaces data
    interfaces = main_script.check_dhcp_status()
    if isinstance(interfaces, dict):
        interfaces = {'IP Configuration': interfaces}  # Match the structure expected by the template
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


@app.route('/check_network')
def check_network():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        result = check_dhcp_status()  # Your existing function
        return render_template('network_section.html', result=result)

@app.route('/check_timezone')
def check_timezone():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        timezone = main_script.get_time_zone()  # Use your existing get_time_zone function
        return render_template('timezone_section.html', result={'Time Zone': timezone})
    return '', 400


if __name__ == '__main__':
    try:
        if is_admin():
            # Pre-load data to avoid multiple subprocess calls
            #app.config['task_data'] = main_script.check_task_scheduler_status()
            
            # Start browser after data is loaded
            Timer(0.1, open_browser).start()
            Timer(0.1, minimize_console).start()
            
            #webbrowser.open('http://127.0.0.1:5000')
            app.run(host='127.0.0.1', port=5000)

    except Exception as e:
        print(f"Startup Error: {str(e)}")
        input("Press Enter to exit...")  # This will keep the window open

