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
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)


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


def get_script_path():
    """Get the correct path for main_script.py in both PyInstaller and normal environments"""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        return os.path.join(sys._MEIPASS, 'main_script.py')
    else:
        # Running in normal Python environment
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')


def run_command_safely(cmd, **kwargs):
    from subprocess import CREATE_NO_WINDOW, CREATE_NEW_CONSOLE
    
    default_flags = CREATE_NO_WINDOW
    if kwargs.pop('new_console', False):
        default_flags = CREATE_NEW_CONSOLE
        
    kwargs['creationflags'] = kwargs.get('creationflags', default_flags)
    return subprocess.Popen(cmd, **kwargs)


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# First, update the script path function to be more robust
def get_script_and_python():
    """Get the correct paths for both the script and Python executable"""
    if getattr(sys, 'frozen', False):
        # Running from PyInstaller bundle
        base_path = sys._MEIPASS
        python_exe = os.path.join(base_path, 'python.exe')
        script_path = os.path.join(base_path, 'main_script.py')
    else:
        # Running in development
        base_path = os.path.dirname(os.path.abspath(__file__))
        python_exe = sys.executable
        script_path = os.path.join(base_path, 'main_script.py')
        
    return script_path, python_exe, base_path


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
    dhcp_info = main_script.check_dhcp_status()
    network_profiles = main_script.get_network_profile()
    
    # Merge network profile info into DHCP info
    if isinstance(dhcp_info, dict) and isinstance(network_profiles, dict):
        for interface_name, interface_info in dhcp_info.items():
            for profile_name, category in network_profiles.items():
                if profile_name in interface_name:
                    interface_info['Type'] = f"{interface_info['Type']} (Category: {category})"
    return {
        'Computer Name': main_script.get_computer_name(),
        'Windows Activation': main_script.check_windows_activation(),
        'Task Scheduler Status': main_script.format_task_scheduler_for_web(task_scheduler_data),
        'IP Configuration': dhcp_info,
        'Network Profile': network_profiles,
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
        'Time Zone': main_script.get_time_zone(),
        'Drive Health': main_script.quick_drive_check(),
        'Windows Update': main_script.is_windows_update_enabled(),
        'Windows Notifications': main_script.check_notification_settings()
    }

def clear_system_info_cache():
    """Clear all caches"""
    get_cached_system_info.cache_clear()
    # Clear Flask cache
    current_time = time.time()
    for key in list(cache.keys()):
        cache_entry = cache[key]
        if current_time - cache_entry.get('timestamp', 0) > CACHE_DURATION:
            del cache[key]
    
    
@app.route('/')
@cache_control(max_age=30)
def index():
    try:
        # Clear specific cache entries
        # cache_key = f"/:{request.query_string}"
        # if cache_key in cache:
        #     del cache[cache_key]
        
        # Get fresh timezone data
       # current_timezone = main_script.get_time_zone()
        
        # Get cached data
        cached_info = get_cached_system_info()
        
        # Create result using cached data but with fresh timezone
        result = {
            **cached_info,
            'Computer Name': cached_info['Computer Name'],
            'Windows Activation': cached_info['Windows Activation'],
            'Task Scheduler Status': cached_info['Task Scheduler Status'],
            'IP Configuration': cached_info['IP Configuration'],
            'Time Zone': cached_info['Time Zone'], 
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
            'Network Profile': cached_info['Network Profile'],
            'Windows Update': cached_info['Windows Update'],
            'Windows Notifications': cached_info['Windows Notifications']
        }
        
        return render_template('index.html', result=result)
        
    except Exception as e:
        print(f"Error in route: {str(e)}")
        return "Error loading page", 500



# @app.route('/change/<setting>', methods=['GET', 'POST'])
# def change_setting(setting):
#     try:
#         if request.method == 'POST':
#             if setting == 'time_zone':
#                 new_timezone = request.form.get('new_value')
#                 result = main_script.change_time_zone(new_timezone)
                
#                 # Force clear all caches
#                 clear_system_info_cache()
#                 get_cached_system_info.cache_clear()
                
#                 # Clear Flask cache
#                 for key in list(cache.keys()):
#                     del cache[key]
                
#                 # Get fresh timezone
#                 current_timezone = main_script.get_time_zone()
                
#                 return jsonify({
#                     'success': True,
#                     'message': result,
#                     'newTimezone': current_timezone
#                 })
        
#         if setting == 'time_zone':
#             timezones = main_script.get_available_timezones()
#             return render_template('change_setting.html', setting=setting, timezones=timezones)
        
#         return jsonify({'success': False, 'error': 'Setting not supported'}), 400
        
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
                print(f"Found VibLib at: {path}")  # Debug logging
                subprocess.Popen(
                    [path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                return jsonify({"success": True, "path": path})
                
        return jsonify({"success": False, "error": "VibLib executable not found", "searched_paths": preset_paths})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


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
            
            # Clear the cache after IP change
            clear_system_info_cache()
            
            return jsonify({
                'success': 'Failed' not in result,
                'message': result
            })
    
    interfaces = main_script.check_dhcp_status()
    if isinstance(interfaces, dict):
        interfaces = {'IP Configuration': interfaces}
    return render_template('change_ip.html', interfaces=interfaces)

# Add route to force refresh IP data
@app.route('/refresh_ip', methods=['POST'])
def refresh_ip():
    try:
        clear_system_info_cache()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    try:
        # Clear all caches
        clear_system_info_cache()
        get_cached_system_info.cache_clear()
        
        # Clear specific cache entries
        for key in list(cache.keys()):
            del cache[key]
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
    
    
    
# @app.route('/Openshell')
# def Openshell():
#     try:
#         if getattr(sys, 'frozen', False):
#             base_path = sys._MEIPASS
#             ps_content = '''
# $Host.UI.RawUI.WindowTitle = "SHOTOVER Systems - Drive Summary Details"
# python -c "import sys; sys.path.insert(0, r'{}'); import main_script; main_script.print_summary()"
# Write-Host "`nPress any key to continue..."
# $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
# '''.format(base_path)
#         else:
#             ps_content = '''
# $Host.UI.RawUI.WindowTitle = "SHOTOVER Systems - Drive Summary Details"
# & "{}" -c "import main_script; main_script.print_summary()"
# Write-Host "`nPress any key to continue..."
# $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
# '''.format(sys.executable)

#         ps_file = os.path.join(os.environ['TEMP'], 'shotover_summary.ps1')
#         with open(ps_file, 'w') as f:
#             f.write(ps_content)
        
#         subprocess.Popen(
#             ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps_file],
#             creationflags=subprocess.CREATE_NEW_CONSOLE
#         )
#         return "", 204
#     except Exception as e:
#         print(f"Error in Openshell: {str(e)}")
#         return str(e), 500
    
@app.route('/Openshell')
def Openshell():
    try:
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            base_path = sys._MEIPASS
            ps_content = '''
$Host.UI.RawUI.WindowTitle = "SHOTOVER Systems - Drive Summary Details"
python -c "import sys; sys.path.insert(0, r'{}'); import main_script; main_script.print_summary()"
Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
'''.format(base_path)
        else:
            # Running in normal Python environment
            ps_content = '''
$Host.UI.RawUI.WindowTitle = "SHOTOVER Systems - Drive Summary Details"
& "{}" -c "import main_script; main_script.print_summary()"
Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
'''.format(sys.executable)

        # Create and write the PowerShell script
        ps_file = os.path.join(os.environ['TEMP'], 'shotover_summary.ps1')
        with open(ps_file, 'w') as f:
            f.write(ps_content)
        
        # Run it in a new window
        subprocess.Popen(
            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps_file],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return "", 204
    except Exception as e:
        print(f"Error in Openshell: {str(e)}")
        return str(e), 500
    
# @app.route('/Openshell')
# def Openshell():
#     try:
#         subprocess.Popen([sys.executable, '-c', 'import main_script; main_script.print_summary()'],
#                         creationflags=subprocess.CREATE_NEW_CONSOLE)
#         return "", 204
#     except Exception as e:
#         print(f"Error in Openshell: {str(e)}")
#         return str(e), 500

@app.route('/printt')
def printt():
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Use the existing cached data from the index route
        cached_info = get_cached_system_info()
        
        # Format the cached data for printing
        output_str = format_system_info_for_print(cached_info)

        return render_template('print_view.html', 
                             output=output_str, 
                             current_time=current_time)
    except Exception as e:
        print(f"Error in printt route: {str(e)}")
        return jsonify({"success": False, "error": str(e)})



def format_system_info_for_print(cached_info):
    """Format cached system info for print view"""
    output = []
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Time Header
    output.append(f"\n\n{Fore.CYAN}Time: {current_time}{Style.RESET_ALL}")
    
    # System Information
    output.append(f"\n{Fore.GREEN}{'='*20} SYSTEM INFORMATION {'='*20}{Style.RESET_ALL}\n")
    output.append(f"{Fore.CYAN}Computer Name:{Style.RESET_ALL} {cached_info['Computer Name']}")
    output.append(f"{Fore.CYAN}Windows Activation:{Style.RESET_ALL} {cached_info['Windows Activation']}")
    output.append(f"{Fore.CYAN}Time Zone:{Style.RESET_ALL} {cached_info.get('Time Zone', 'N/A')}")
    
    # Display Info
    display_info = cached_info['Display Info']
    display_lines = display_info.split('\n') if isinstance(display_info, str) else []
    for line in display_lines:
        if any(key in line for key in ['Display Info:', 'Name:', 'Resolution:', 'Refresh rate:']):
            label = line.split(':')[0] + ':'
            value = ':'.join(line.split(':')[1:])
            output.append(f"{Fore.CYAN}{label}{Style.RESET_ALL}{value}")
        else:
            output.append(line)

    # Network Configuration
    output.append(f"\n{Fore.GREEN}{'='*20} NETWORK CONFIGURATION {'='*20}{Style.RESET_ALL}")
    dhcp_status = cached_info['IP Configuration']
    network_profiles = cached_info['Network Profile']

    if isinstance(dhcp_status, dict):
        for interface, info in dhcp_status.items():
            output.append(f"\n{Fore.CYAN}{interface}:{Style.RESET_ALL}")
            type_str = info.get('Type', 'N/A')
            if isinstance(network_profiles, dict):
                for profile_name, category in network_profiles.items():
                    if profile_name in interface:
                        type_str += f" (Category: {category})"
            output.append(f"  {Fore.CYAN}Type:{Style.RESET_ALL} {type_str}")
            output.append(f"  {Fore.CYAN}DNS Suffix:{Style.RESET_ALL} {info.get('DNS Suffix', 'N/A')}")
            output.append(f"  {Fore.CYAN}DHCP:{Style.RESET_ALL} {info.get('DHCP', 'N/A')}")
            output.append(f"  {Fore.CYAN}IP:{Style.RESET_ALL} {info.get('IP', 'N/A')}")
            output.append(f"  {Fore.CYAN}Subnet Mask:{Style.RESET_ALL} {info.get('Subnet Mask', 'N/A')}")
            output.append(f"  {Fore.CYAN}Gateway:{Style.RESET_ALL} {info.get('Gateway', 'N/A')}")

    # Versions
    output.append(f"\n{Fore.GREEN}{'='*20} VERSIONS {'='*20}{Style.RESET_ALL}\n")
    output.append(f"{Fore.CYAN}ARS Version:{Style.RESET_ALL} {cached_info['ARS Version']}")
    output.append(f"{Fore.CYAN}ARS Shortcut:{Style.RESET_ALL} {cached_info['ARS Shortcut']}")
    output.append(f"{Fore.CYAN}Boot Version:{Style.RESET_ALL} {cached_info['Boot Drive Version']}")
    output.append(f"{Fore.CYAN}VIB Version:{Style.RESET_ALL} {cached_info['VIB Version']}")
    output.append(f"{Fore.CYAN}FX3 Version:{Style.RESET_ALL} {cached_info['FX3 Version']}")

    # System Status
    output.append(f"\n{Fore.GREEN}{'='*20} SYSTEM STATUS {'='*20}{Style.RESET_ALL}\n")

    # Computer Metrics
    metrics = cached_info['Computer Metrics']
    output.append(f"{Fore.CYAN}Computer Metrics:{Style.RESET_ALL}")
    output.append(f"    CPU: {metrics['CPU']}")
    output.append(f"    RAM: {metrics['RAM']}")
    output.append(f"    Physical Memory: {metrics['Physical Memory']}")
    output.append(f"    Virtual Memory: {metrics['Virtual Memory']}")

    # Windows Defender
    defender = cached_info['Windows Defender Status']
    output.append(f"\n{Fore.CYAN}Windows Defender:{Style.RESET_ALL}")
    for key, value in defender.items():
        color = Fore.GREEN if value == 'ON' else Fore.RED
        output.append(f"    {key}: {color}{value}{Style.RESET_ALL}")

    # Firewall Status
    firewall = cached_info['Firewall Status']
    output.append(f"\n{Fore.CYAN}Firewall Status:{Style.RESET_ALL}")
    for profile, status in firewall.items():
        color = Fore.GREEN if status == 'ON' else Fore.RED
        output.append(f"    {profile}: {color}{status}{Style.RESET_ALL}")

    # Defrag Status
    defrag = cached_info['Defrag Status']
    output.append(f"\n{Fore.CYAN}Defrag Status:{Style.RESET_ALL}")
    output.append(f"    C Drive: {Fore.GREEN if defrag['C_Drive'] == 'Enabled' else Fore.RED}{defrag['C_Drive']}{Style.RESET_ALL}")
    output.append(f"    D Drive: {Fore.GREEN if defrag['D_Drive'] == 'Enabled' else Fore.RED}{defrag['D_Drive']}{Style.RESET_ALL}")

    # Drive Health
    drives = cached_info['Drive Health']
    output.append(f"\n{Fore.CYAN}Drive Health:{Style.RESET_ALL}")
    for drive, info in drives.items():
        output.append(f"    {Fore.CYAN}{drive}:{Style.RESET_ALL}")
        color = Fore.GREEN if info['Status'] == 'Healthy' else Fore.RED
        output.append(f"       Status: {color}{info['Status']}{Style.RESET_ALL}")
        output.append(f"       Usage: {info['Usage']}")
        output.append(f"       Space: {info['Space']}")

    # Windows Update and Notifications
    update_status = cached_info['Windows Update']
    output.append(f"\n  {Fore.CYAN}Windows Update:{Style.RESET_ALL} {Fore.GREEN if update_status == 'Enabled' else Fore.RED}{update_status}{Style.RESET_ALL}")
    
    notif_status = cached_info['Windows Notifications']
    output.append(f"\n  {Fore.CYAN}Windows Notifications:{Style.RESET_ALL} {Fore.GREEN if notif_status == 'Enabled' else Fore.RED}{notif_status}{Style.RESET_ALL}")

    # Task Scheduler
    output.append(f"\n{Fore.GREEN}{'='*20} TASK SCHEDULER {'='*20}{Style.RESET_ALL}")
    tasks = cached_info['Task Scheduler Status']
    if tasks:
        for task in tasks:
            if ':' in task:
                output.append(f"{Fore.CYAN}{task}{Style.RESET_ALL}")
            else:
                output.append(task)

    # COM Ports
    output.append(f"\n{Fore.GREEN}{'='*20} COM PORTS {'='*20}{Style.RESET_ALL}")
    output.append(f"{Fore.CYAN}Name                     Status   Service{Style.RESET_ALL}")
    output.append("----                     ------   -------")
    output.append(cached_info['COM Ports'])

    # SHOTOVER Logo
    output.append(f"{Fore.CYAN}")
    output.append(r"""
 ____    _    _    ___    _____     ___   __     __  _____   ____   
/ ___|  | |  | |  / _ \  |_   _|   / _ \  \ \   / / | ____| |  _ \  
\___ \  | |__| | | | | |   | |    | | | |  \ \ / /  |  _|   | |_) | 
 ___) | |  __  | | |_| |   | |    | |_| |   \ V /   | |___  |  _ <  
|____/  |_|  |_|  \___/    |_|     \___/     \_/    |_____| |_| \_\ 

                                                              """.strip())
    output.append(f"{Style.RESET_ALL}\n")

    # Join all lines and apply HTML color formatting
    output_str = "\n".join(output)
    return (output_str
        .replace(f"{Fore.CYAN}", '<span class="cyan">')
        .replace(f"{Fore.GREEN}", '<span class="green">')
        .replace(f"{Fore.RED}", '<span class="red">')
        .replace(f"{Fore.YELLOW}", '<span class="yellow">')
        .replace(f"{Style.RESET_ALL}", '</span>')
    )

    
    
@app.route('/run_ars', methods=['POST'])
def run_ars_route():
    try:
        paths = [
            r"D:\ARS\bin\loader\runloader.cmd",
            r"C:\ARS\bin\loader\runloader.cmd",
            r"E:\ARS\bin\loader\runloader.cmd",
            r"D:\ARS\loader\runloader.cmd",
            r"C:\ARS\loader\runloader.cmd",
            r"E:\ARS\loader\runloader.cmd",
            r"D:\ARS\bin\ars.exe",
            r"C:\ARS\bin\ars.exe",
            r"D:\ARS\ars.exe",
            r"C:\ARS\ars.exe"
        ]
        
        for path in paths:
            if os.path.exists(path):
                print(f"Found ARS at: {path}")  # Debug logging
                if path.endswith('.cmd'):
                    subprocess.Popen(
                        [path],
                        cwd=os.path.dirname(path),
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    subprocess.Popen(
                        [path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                return jsonify({"success": True, "path": path})
                
        return jsonify({"success": False, "error": "ARS executable not found", "searched_paths": paths})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
    
    
def open_browser():
    url = 'http://127.0.0.1:5000'
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    ]

    def try_chrome():
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    # Position on left side of screen and make taller
                    browser = webbrowser.get(
                        f'"{chrome_path}" --window-position=0,0 '
                        f'--window-size=960,1080 '
                        f'--window-state=normal %s'
                    )
                    browser.open(url, new=2)
                    return True
                except:
                    continue
        return False

    try:
        if try_chrome():
            return
        webbrowser.open(url, new=2)
    except Exception as e:
        print(f"Error opening browser: {e}")


def minimize_console():
    try:
        def enum_windows(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                # Look specifically for the admin window
                if "administrator:" in title.lower():
                    windows.append(hwnd)
        
        windows = []
        win32gui.EnumWindows(enum_windows, windows)
        
        for hwnd in windows:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            
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
        if len(sys.argv) > 1 and sys.argv[1] == '--standalone':
            # Run main_script directly when called with --standalone
            import main_script
            main_script.main()
            sys.exit(0)
            
        if is_admin():
            Timer(0.1, open_browser).start()
            Timer(0.1, minimize_console).start()
            app.run(host='127.0.0.1', port=5000)
    except Exception as e:
        print(f"Startup Error: {str(e)}")
        input("Press Enter to exit...")
        