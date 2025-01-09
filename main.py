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

# Cache configuration
cache = {}
CACHE_DURATION = 30  # seconds
EXCLUDED_PATHS = {'/change_ip', '/change/<setting>'} 



def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    if sys.platform == 'win32':
        subprocess.Popen(["powershell", 
                         "Start-Process", 
                         "python", 
                         f'"{sys.argv[0]}"', 
                         "-Verb", 
                         "RunAs"], 
                        creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(0)

app = Flask(__name__, 
           static_url_path='/static',
           static_folder='static',
           template_folder='templates')
    


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



@app.route('/')
@cache_control(max_age=30)
def index():
    dhcp_info = main_script.check_dhcp_status()
    network_profiles = main_script.get_network_profile()
    # task_scheduler_data = main_script.check_task_scheduler_status()
    # print("Debug - Raw task data:", task_scheduler_data)  # Debug print
    task_scheduler_data = main_script.check_task_scheduler_status()
    
    
    ### FOR DEBUGGING PURPOSES ONLY ####
    
    #try:
        #dhcp_info = main_script.check_dhcp_status()
        #app.logger.debug(f"DHCP info: {dhcp_info}")
        
        #network_profiles = main_script.get_network_profile()
        #app.logger.debug(f"Network profiles: {network_profiles}")
        
        # Add debugging before formatting
        #app.logger.debug(f"Task scheduler data type: {type(task_scheduler_data)}")
        
        #formatted_tasks = main_script.format_task_scheduler_for_web(task_scheduler_data)
        #app.logger.debug(f"Formatted task data: {formatted_tasks}")
        
    #except Exception as e:
     #   app.logger.error(f"Error in index route: {str(e)}", exc_info=True)
     #   return f"Error: {str(e)}", 500
        
        
    #2nd task scheduler debugger - maybe delete???
    #if task_scheduler_data is None:
    #    print("Debug - No task scheduler data returned")
    #    task_scheduler_formatted = ['<div class="task-error">Error retrieving task scheduler data</div>']
    #else:
    #    task_scheduler_formatted = main_script.format_task_scheduler_for_web(task_scheduler_data)
        
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
            'Windows Notifications': main_script.check_notification_settings()
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
                # Return JSON response instead of redirecting
                return jsonify({'success': True, 'message': result})
        
        if setting == 'time_zone':
            timezones = main_script.get_available_timezones()
            return render_template('change_setting.html', setting=setting, timezones=timezones)
        
        return "Setting not supported for changes", 400
        
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
                subprocess.Popen([path], creationflags=subprocess.CREATE_NEW_CONSOLE)
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
        
        result = main_script.change_ip_configuration(
            interface_name, use_dhcp, ip_address, subnet_mask, gateway
        )
        
        # Clear cache after IP change
        cache.clear()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'result': result, 'success': 'Failed' not in result})
        
        return redirect(url_for('index'))
    
    interfaces = main_script.check_dhcp_status()
    return render_template('change_ip.html', interfaces=interfaces)


@app.route('/open_command_prompt')
def open_command_prompt():
   try:
       script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
       
       batch_content = f'''@echo off
title SHOTOVER Systems - Drive Summary Details
color 0A
cd /d "{os.path.dirname(script_path)}"
"{sys.executable}" "{script_path}"
echo.
pause >nul
'''
       
       batch_file = os.path.join(os.environ['TEMP'], 'shotover_summary.bat')
       with open(batch_file, 'w') as f:
           f.write(batch_content)
       
       # Launch with elevated privileges 
       ctypes.windll.shell32.ShellExecuteW(
           None,
           "runas",
           "cmd.exe",
           f"/c {batch_file}",
           None,
           1
       )
       
       return "", 204
   except Exception as e:
       print(f"Error in open_command_prompt: {str(e)}")
       return str(e), 500

@app.route('/Openshell')
def Openshell():
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
        
        # Fixed PowerShell script
        powershell_content = f'''
$pshost = Get-Host
$pswindow = $pshost.UI.RawUI
$pswindow.WindowTitle = "SHOTOVER Systems - Drive Summary Details"
Set-Location '{os.path.dirname(script_path)}'
& "{sys.executable}" "{script_path}"
Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
'''
        
        batch_file = os.path.join(os.environ['TEMP'], 'shotover_summary.ps1')
        with open(batch_file, 'w') as f:
            f.write(powershell_content)
        
        # Launch with elevated privileges
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "powershell.exe",
            f"-NoProfile -ExecutionPolicy Bypass -File {batch_file}",
            None,
            1
        )
        
        return "", 204
    except Exception as e:
        print(f"Error in Openshell: {str(e)}")
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
        
        # Try cmd first
        for path in cmd_paths:
            if os.path.exists(path):
                start_dir = os.path.dirname(path)
                subprocess.Popen(
                    [path],
                    cwd=start_dir,
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                return jsonify({"success": True})
                
        # Fall back to exe if cmd not found
        for path in exe_paths:
            if os.path.exists(path):
                subprocess.Popen(
                    [path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                return jsonify({"success": True})
                
        return jsonify({"success": False, "error": "ARS executable not found"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
def open_browser():
    url = 'http://127.0.0.1:5000'
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        # Add any other potential Chrome paths here
    ]

    def try_chrome():
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    browser = webbrowser.get(f'"{chrome_path}" --start-maximized %s')
                    browser.open(url, new=2)
                    return True
                except:
                    continue
        return False

    try:
        # First, try to use Chrome directly if it's the default
        if 'chrome' in webbrowser.get().name.lower():
            webbrowser.get().open(url, new=2)
            return

        # If Chrome isn't default, try to find and use Chrome specifically
        if try_chrome():
            return

        # If Chrome attempts fail, try using the system default browser
        webbrowser.open(url, new=2)

    except Exception as e:
        print(f"Error opening browser: {e}")
        # Final fallback: try basic browser open
        try:
            webbrowser.open_new(url)
        except:
            print("Failed to open browser. Please navigate to http://127.0.0.1:5000 manually")


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
    if is_admin():
        # Pre-load data to avoid multiple subprocess calls
        #app.config['task_data'] = main_script.check_task_scheduler_status()
        
        # Start browser after data is loaded
        Timer(0.1, open_browser).start()
        Timer(0.1, minimize_console).start()
        
        #webbrowser.open('http://127.0.0.1:5000')
        app.run(host='127.0.0.1', port=5000)



