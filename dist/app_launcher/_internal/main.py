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


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

app = Flask(__name__, 
           static_url_path='/static',
           static_folder=resource_path('static'),
           template_folder=resource_path('templates'))

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    if sys.platform == 'win32':
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)
    
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
            return render_template('result.html', result=result)
    
   
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
        
        result = main_script.change_ip_configuration(interface_name, use_dhcp, ip_address, subnet_mask, gateway)
        return render_template('result.html', result=result)
    
   
    interfaces = main_script.check_dhcp_status()
    return render_template('change_ip.html', interfaces=interfaces)

@app.route('/open_command_prompt')
def open_command_prompt():
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
        
        batch_content = '@echo off\n'
        batch_content += 'title SHOTOVER Systems - Drive Summary Details\n'
        batch_content += 'color 0A\n'
        batch_content += f'python "{script_path}"\n'
        batch_content += 'echo.\n'
        batch_content += 'pause >nul'
        
        batch_file = os.path.join(os.environ['TEMP'], 'shotover_summary.bat')
        with open(batch_file, 'w') as f:
            f.write(batch_content)
        
        # Use ShellExecute to run as admin
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",  # Run as administrator
            "cmd.exe",
            f"/c start {batch_file}",
            None,
            1  # Normal window
        )
        
        return "", 204
    except Exception as e:
        print(f"Error in open_command_prompt: {str(e)}")
        return str(e), 500

@app.route('/Openshell')
def Openshell():
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
        
        # PowerShell specific script
        powershell_content = f'''
$Host.UI.RawUI.WindowTitle = "SHOTOVER Systems - Drive Summary Details"
python "{script_path}"
pause
'''
        
        batch_file = os.path.join(os.environ['TEMP'], 'shotover_summary.ps1')
        with open(batch_file, 'w') as f:
            f.write(powershell_content)
        
        # Use ShellExecute to run PowerShell as admin
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "powershell.exe",
            f"-ExecutionPolicy Bypass -File {batch_file}",
            None,
            1  # Normal window
        )
        
        return "", 204
    except Exception as e:
        print(f"Error in Openshell: {str(e)}")
        return str(e), 500

# @app.route('/printt')
# def printt():
#     try:
#         # Get the current date/time
#         current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
#         # Run the script and capture output
#         script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
#         result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
#         output = result.stdout

#         # Render the template with the output
#         return render_template('print_view.html', 
#                              output=output, 
#                              current_time=current_time)
#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)})
    
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

if __name__ == '__main__':
    if is_admin():
        Timer(0.3, open_browser).start()
        Timer(0.5, minimize_console).start()
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)



