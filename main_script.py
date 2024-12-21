import json
import subprocess
import os
import socket
from datetime import datetime
from tzlocal import get_localzone
import re
import win32api
import ctypes
from pathlib import Path
import time
import psutil
from colorama import init, Fore, Style
import pythoncom
from pathlib import Path
import winshell
import winreg
######################## Misc. #########################################################

# Function to get the current date in the format MMDDYYYY for backup naming
def get_current_date():
    return datetime.now().strftime("%m%d%Y")

####################### Drive Summary Functions ##########################
# Option 0: Name of the computer
def get_computer_name():
    return socket.gethostname()

# Option 1: Check if Windows is activated
def check_windows_activation():
    try:
        result = subprocess.check_output("cscript %windir%\\system32\\slmgr.vbs /xpr", shell=True).decode()
        if "The machine is permanently activated" in result:
            return "Windows is activated."
        else:
            return "Windows is NOT activated. Sorry, best of luck with that."
    except Exception as e:
        print(f"Couldn't check activation status: {str(e)}")
        return "Couldn't check activation status. Please check the command prompt for details."

def check_dhcp_status():
    try:
        ip_config = subprocess.check_output("ipconfig /all", shell=True).decode()
        interfaces = {}
        current_interface = None
        
        for line in ip_config.splitlines():
            line = line.strip()
            
            # Start of new interface
            if "adapter" in line and ":" in line:
                current_interface = line.split(":")[0].strip()
                # Determine Type (Ethernet or Wi-Fi)
                connection_type = "Wi-Fi" if "Wi-Fi" in current_interface else "Ethernet"
                
                interfaces[current_interface] = {
                    "Status": "Connected",
                    "Type": connection_type, 
                    "DNS Suffix": "",
                    "DHCP": "Unknown",
                    "IP": "",
                    "Subnet Mask": "",  # Changed from "Subnet" to "Subnet Mask"
                    "Gateway": ""
                }
            
            # Skip if no current interface
            if not current_interface:
                continue
                
            # Check for disconnected state
            if "Media State" in line and "disconnected" in line:
                interfaces[current_interface]["Status"] = "Disconnected"
                
            # Parse other information
            if ": " in line:
                key, value = line.split(": ", 1)
                key = key.strip()
                value = value.strip()
                
                if "DNS Suffix" in key:
                    interfaces[current_interface]["DNS Suffix"] = value
                elif "DHCP Enabled" in key:
                    interfaces[current_interface]["DHCP"] = "Enabled" if value.lower() == "yes" else "Disabled"
                elif "IPv4 Address" in key:
                    if '(' in value:
                        value = value.split('(')[0]
                    interfaces[current_interface]["IP"] = value
                elif "Subnet Mask" in key:
                    interfaces[current_interface]["Subnet Mask"] = value  # Changed key name here too
                elif "Default Gateway" in key and value:
                    interfaces[current_interface]["Gateway"] = value
        
        # Filter out non-network adapters and disconnected interfaces
        active_interfaces = {
            name: info for name, info in interfaces.items()
            if (("Ethernet" in name or "Wi-Fi" in name) and 
                "Bluetooth" not in name and
                info["Status"] == "Connected" and
                info["IP"])
        }
        
        return active_interfaces if active_interfaces else {"No active interfaces": {
            "Status": "No active network connections found",
            "Type": "None",
            "DHCP": "Unknown",
            "IP": "None",
            "Subnet Mask": "None",  # Changed here too
            "Gateway": "None"
        }}
        
    except Exception as e:
        return {"Error": f"Failed to retrieve network status: {str(e)}"}

# Option 4: Get the current time zone abbreviation
def get_time_zone():
    try:
        local_tz = get_localzone()  # Get the system's local time zone
        local_time = datetime.now(local_tz)
        return local_time.strftime('%Z')
    except Exception as e:
        print(f"Couldn't get time zone: {str(e)}")  # Print error to command prompt
        return "Couldn't get time zone. Please check the command prompt for details."

def get_display_info():
    try:
        # Get display adapters
        adapter_result = subprocess.check_output("wmic path Win32_VideoController get Name", shell=True).decode()
        adapter_lines = adapter_result.strip().split("\n")[1:]  # Skip header
        adapters = [line.strip() for line in adapter_lines if line.strip()]

        # Get resolution and refresh rates for each adapter
        resolution_result = subprocess.check_output("wmic path Win32_VideoController get VideoModeDescription,Name", shell=True).decode()
        resolution_lines = resolution_result.strip().split("\n")[1:]  # Skip header
        
        display_info = []
        #display_info.append("Display Info:")

        # Process each display
        for i, adapter in enumerate(adapters, 1):
            display_info.append(f"\nDisplay {i}:")
            display_info.append(f"      Name: {adapter}")
            
            # Get resolution for this adapter
            resolution_line = next((line for line in resolution_lines if adapter in line), "")
            resolution_match = re.search(r'(\d{3,4} x \d{3,4})', resolution_line)
            resolution = resolution_match.group(1) if resolution_match else "Unknown"
            display_info.append(f"      Resolution: {resolution}")
            
            # Get refresh rate using a different method
            try:
                refresh_rate_result = subprocess.check_output([
                    "powershell",
                    "-Command",
                    f"Get-WmiObject -Query \"SELECT CurrentRefreshRate FROM Win32_VideoController WHERE Name = '{adapter}'\" | Select-Object -ExpandProperty CurrentRefreshRate"
                ], text=True).strip()
                
                if refresh_rate_result and refresh_rate_result != "":
                    refresh_rate_float = float(refresh_rate_result)
                    # Round to nearest common refresh rate
                    if abs(refresh_rate_float - 60.0) < 0.2:
                        refresh_rate = "60.0"
                    elif abs(refresh_rate_float - 59.9) < 0.2:
                        refresh_rate = "59.9"
                    else:
                        refresh_rate = f"{refresh_rate_float:.1f}"
                else:
                    refresh_rate = "Unknown"
            except:
                refresh_rate = "Unknown"
                
            display_info.append(f"      Refresh rate: {refresh_rate} Hz")

        return "\n".join(display_info)

    except Exception as e:
        return f"Failed to get display info: {str(e)}"


# Option 7: Search for any text document containing "boot" in its name in Documents folders
def get_boot_drive_version():
    root_dir = r"C:\Users"
    filename = "boot drive version.txt"

    try:
        for user_folder in os.listdir(root_dir):
            user_docs_path = os.path.join(root_dir, user_folder, "Documents")
            if os.path.isdir(user_docs_path):
                for root, dirs, files in os.walk(user_docs_path):
                    for file in files:
                        if file.lower() == filename:
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r') as f:
                                    version = f.read().strip()
                                    return f"{version}"
                            except Exception as e:
                                print(f"Error reading file: {str(e)}")  # Print error to command prompt
                                return "Error reading file. Please check the command prompt for details."
        return "Boot Drive Version file not found in C:\\Users."
    except Exception as e:
        print(f"Couldn't search for Boot Drive Version file: {str(e)}")  # Print error to command prompt
        return "Couldn't search for Boot Drive Version file. Please check the command prompt for details."

# Option 8: Check if ars.exe shortcut exists on the desktop
def check_ars_shortcut():
    try:
        shortcut_path = r"C:\ARS\loader.hta"  # Path to the ARS.exe shortcut
        if os.path.exists(shortcut_path):
            return "ARS.exe shortcut found."
        else:
            return "ARS.exe shortcut not found."
    except Exception as e:
        print(f"Couldn't check for ARS.exe shortcut: {str(e)}")  # Print error to command prompt
        return "Couldn't check for ARS.exe shortcut. Please check the command prompt for details."
    
###########
def get_latest_version(files, prefix):
    version_pattern = re.compile(rf"{prefix}_v_(\d+_\d+_\d+)\.bin")
    versions = []
    for file in files:
        match = version_pattern.match(file)
        if match:
            versions.append(match.group(1))
    if versions:
        return sorted(versions, key=lambda s: list(map(int, s.split('_'))))[-1]
    return None

def get_vib_version():
    vib_dir = r"C:\ARS\atom_tools"
    if os.path.exists(vib_dir):
        files = os.listdir(vib_dir)
        latest_version = get_latest_version(files, "vib")
        if latest_version:
            return f"VIB version: {latest_version.replace('_', '.')}"
    return "VIB version not found."

def get_fx3_version():
    fx3_dir = r"C:\ARS\atom_tools"
    if os.path.exists(fx3_dir):
        files = os.listdir(fx3_dir)
        version_pattern = re.compile(r"fx3_v_(\d+_\d+_\d+)\.img")
        versions = []
        for file in files:
            match = version_pattern.match(file)
            if match:
                versions.append(match.group(1))
        if versions:
            latest_version = sorted(versions, key=lambda s: list(map(int, s.split('_'))))[-1]
            return f"FX3 version: {latest_version.replace('_', '.')}"
    return "FX3 version not found."

def get_latest_version(files, prefix):
    version_pattern = re.compile(rf"{prefix}_v_(\d+_\d+_\d+)\.bin")
    versions = []
    for file in files:
        match = version_pattern.match(file)
        if match:
            versions.append(match.group(1))
    if versions:
        return sorted(versions, key=lambda s: list(map(int, s.split('_'))))[-1]
    return None
############

####################### Change Settings Functions ########################

# Change PC name
def set_pc_name(new_name):
    try:
        commands = [
            f'reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\ComputerName\\ComputerName" /v ComputerName /t REG_SZ /d "{new_name}" /f',
            f'reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\ComputerName\\ActiveComputerName" /v ComputerName /t REG_SZ /d "{new_name}" /f',
            f'reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v Hostname /t REG_SZ /d "{new_name}" /f',
            f'reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v "NV Hostname" /t REG_SZ /d "{new_name}" /f'
        ]
        
        for cmd in commands:
            subprocess.run(cmd, shell=True, capture_output=True, check=False)
            
        return f"PC name changed to {new_name}. Please restart for changes to take effect."
    except Exception as e:
        return f"Error changing PC name: {str(e)}"


# Change IP configuration
def change_ip_configuration(interface_name, use_dhcp=True, ip_address=None, subnet_mask=None, gateway=None):
    try:
        if use_dhcp:
            print(f"Debug: Changing IP configuration to DHCP for {interface_name}")
            subprocess.call(f"netsh interface ip set address name=\"{interface_name}\" source=dhcp", shell=True)
            subprocess.call(f"netsh interface ip set dns name=\"{interface_name}\" source=dhcp", shell=True)
            print(f"Debug: IP configuration changed to DHCP for {interface_name}")
            return "IP configuration changed to DHCP."
        else:
            if not ip_address:
                return "IP address is required for static IP configuration."

            # Automatically determine the subnet mask if not provided
            if not subnet_mask:
                first_octet = int(ip_address.split('.')[0])
                # Class A: 1-126
                if first_octet >= 1 and first_octet <= 126:
                    subnet_mask = "255.0.0.0"
                # Class B: 128-191
                elif first_octet >= 128 and first_octet <= 191:
                    subnet_mask = "255.255.0.0"
                # Class C: 192-223
                elif first_octet >= 192 and first_octet <= 223:
                    subnet_mask = "255.255.255.0"
                # Special cases
                elif first_octet == 127:  # Loopback
                    subnet_mask = "255.0.0.0"
                else:
                    subnet_mask = "255.255.255.0"  # Default to Class C if unclear

            print(f"Debug: Using subnet mask: {subnet_mask}")

            # Release current IP configuration
            print(f"Debug: Releasing current IP configuration for {interface_name}")
            subprocess.call(f"netsh interface ip set address name=\"{interface_name}\" source=dhcp", shell=True)
            subprocess.call(f"netsh interface ip set dns name=\"{interface_name}\" source=dhcp", shell=True)
            subprocess.call(f"netsh interface ip delete address name=\"{interface_name}\" addr=all", shell=True)
            time.sleep(2)  # Small delay to ensure the command is applied

            # Set new static IP configuration
            print(f"Debug: Changing IP configuration to static IP {ip_address} for {interface_name}")
            if gateway:
                command = f"netsh interface ip set address name=\"{interface_name}\" static {ip_address} {subnet_mask} {gateway}"
            else:
                command = f"netsh interface ip set address name=\"{interface_name}\" static {ip_address} {subnet_mask}"
            
            print(f"Debug: Executing command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                return f"Failed to change IP configuration: {result.stderr}"
            
            print(f"Debug: IP configuration changed to static IP {ip_address} for {interface_name}")
            return f"IP configuration changed to static IP: {ip_address}"
    except Exception as e:
        print(f"Failed to change IP configuration: {str(e)}")
        return "Failed to change IP configuration. Please check the command prompt for details."

def get_available_timezones():
    try:
        # Common time zones to appear at the top
        common_zones = [
            'Eastern Standard Time',      # US East
            'Central Standard Time',      # US Central
            'Mountain Standard Time',     # US Mountain
            'Pacific Standard Time',      # US Pacific
            'GMT Standard Time',          # UK
            'AUS Eastern Standard Time',  # Sydney/Melbourne
            'Tokyo Standard Time',        # Japan
            'China Standard Time',        # China
            'India Standard Time',        # India
            'W. Europe Standard Time'     # Western Europe
        ]
        
        result = subprocess.run(['tzutil', '/l'], capture_output=True, text=True)
        zones = result.stdout.split('\n')
        
        # Get all valid timezone IDs
        all_zones = [zone.strip() for zone in zones if zone.strip() and 'UTC' not in zone and 'Time' in zone]
        
        # Remove common zones from all_zones to avoid duplicates
        other_zones = [zone for zone in all_zones if zone not in common_zones]
        
        # Return common zones first, then all others alphabetically
        return common_zones + sorted(other_zones)
    except Exception:
        return []
    
# Change Time Zone
def change_time_zone(new_time_zone):
    try:
        print(f"Attempting to change to timezone: {new_time_zone}")  # Debug print
        result = subprocess.run(['tzutil', '/l'], capture_output=True, text=True)
        available_zones = result.stdout.split('\n')
        print(f"Available zones: {available_zones}")  # Debug print
        
        if new_time_zone not in available_zones:
            return f"Invalid time zone ID. Use 'tzutil /l' to list valid time zones."
            
        subprocess.run(['tzutil', '/s', new_time_zone], 
                      check=True, 
                      capture_output=True)
        return f"Time zone changed to {new_time_zone}"
    except subprocess.CalledProcessError as e:
        return f"Failed to change time zone: {e.stderr.decode()}"
    

#F*&^%&* FINDING VIB_LIB
def run_viblib():
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
        r"D:\ARS\atom_tools\viblib\viblib_test.exe"]
    
    for path in preset_paths:
        if os.path.exists(path):
            try:
                subprocess.run([path], check=True)
                return f"viblib_test.exe executed successfully from {path}."
            except subprocess.CalledProcessError as e:
                print(f"Error executing viblib_test.exe: {str(e)}")  # Print error to command prompt
                return "Error executing viblib_test.exe. Please check the command prompt for details."
    
    return "viblib_test.exe not found in any of the specified paths."


def run_ars():
    preset_paths = [
        r"D:\ARS\bin\loader\runloader.cmd",
        r"C:\ARS\bin\loader\runloader.cmd",
        r"E:\ARS\bin\loader\runloader.cmd"
        r"D:\ARS\loader\runloader.cmd",
        r"C:\ARS\loader\runloader.cmd",
        r"E:\ARS\loader\runloader.cmd",
        r"D:\ARS\bin\ars.exe",
        r"C:\ARS\bin\ars.exe",
        r"E:\ARS\bin\ars.exe"]   
    
    for path in preset_paths:
        if os.path.exists(path):
            try:
                # Get the directory containing runloader.cmd
                start_dir = os.path.dirname(path)
                
                # Run with specific working directory and arguments
                subprocess.Popen(
                    [path, "-d"],
                    cwd=start_dir,
                    shell=True,  # Required for .cmd files
                    creationflags=subprocess.CREATE_NEW_CONSOLE  # Create new window
                )
                return f"ARS Loader executed successfully from {path}."
            except subprocess.CalledProcessError as e:
                print(f"Error executing ARS Loader: {str(e)}")
                return "Error executing ARS Loader. Please check the command prompt for details."
            except Exception as e:
                print(f"Unexpected error running ARS Loader: {str(e)}")
                return f"Unexpected error: {str(e)}"
    
    return "ARS Loader (runloader.cmd) not found in any of the specified paths."

def get_com_ports():
    try:
        ps_command = """
        Get-WmiObject Win32_PnPEntity |
        Where-Object {$_.DeviceID -like "*USB*"} |
        Select-Object Name, Status, Service |
        Where-Object {$_.Name -like "*Hub*" -or $_.Name -like "*Root*"} |
        Format-Table -AutoSize | Out-String
        """
        
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True)
            
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                # Split into lines and filter out empty lines
                lines = [line for line in output.splitlines() if line.strip()]
                if len(lines) > 2:  # Has header and separator and data
                    formatted_lines = []
                    # Add data lines, skipping the duplicate headers
                    for line in lines[2:]:
                        if not (line.startswith('Name') or line.startswith('----')):
                            formatted_lines.append(line)
                    return "\n".join(formatted_lines)
            return "No USB devices detected"
            
    except Exception as e:
        print(f"Debug - Error: {str(e)}")
        return "Error detecting USB devices"

def computer_metrics():
    try:
        cpu_percent = psutil.cpu_percent()
        memory_info = psutil.virtual_memory()
        used_ram_percent = memory_info.percent
        available_memory_gb = memory_info.available / (1024 ** 3)

        return {
            'CPU': str(cpu_percent) + '%',
            'RAM': str(used_ram_percent) + '%',
            'Available Memory': str(round(available_memory_gb, 2)) + ' GB'
        }
    except Exception as e:
        print(f"Error getting computer metrics: {str(e)}")
        return {
            'CPU': 'Error',
            'RAM': 'Error',
            'Available Memory': 'Error'
        }
def check_task_scheduler_status():
    try:
        ps_command = r'''
        $tasks = @{
            'Root' = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' };
            'Sledgehammer' = Get-ScheduledTask | Where-Object { $_.TaskName -in ('LockFiles', 'WDU', 'Wub_task') };
            'WindowsUpdate' = Get-ScheduledTask | Where-Object { $_.TaskPath -like '*WindowsUpdate*' };
            'Defender' = Get-ScheduledTask | Where-Object { $_.TaskPath -like '*Windows Defender*' }
        }
        
        $formattedTasks = @{}
        foreach ($category in $tasks.Keys) {
            $formattedTasks[$category] = $tasks[$category] | ForEach-Object {
                @{
                    'Name' = $_.TaskName;
                    'State' = $(
                        if ($_.State -eq 'Ready') { '3 (Enabled)' }
                        elseif ($_.State -eq 'Disabled') { '1 (Disabled)' }
                        else { $_.State }
                    )
                }
            }
        }
        $formattedTasks | ConvertTo-Json -Depth 3
        '''
        result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            formatted_tasks = []
            
            def format_task_line(name, state):
                # Add consistent indentation for task lines
                if len(name) > 37:
                    name = name[:37] + "..."
                return f"    {name:<40}{state}"  # Added 4 spaces indentation

            formatted_tasks = []
            
            # Root tasks
            formatted_tasks.append("Startup Tasks:")# Single blank line after header
            if 'Root' in data and isinstance(data['Root'], list):
                for task in sorted(data['Root'], key=lambda x: x['Name']):
                    formatted_tasks.append(format_task_line(task['Name'], task['State']))
            
            # Sledgehammer tasks
            formatted_tasks.append("Sledgehammer Tasks:") # Single blank line after header
            if not data.get('Sledgehammer') or (isinstance(data['Sledgehammer'], dict) and not data['Sledgehammer']):
                formatted_tasks.append("    No Sledgehammer tasks found")

            formatted_tasks.append("Windows Update:")  # No indentation for header
            if 'WindowsUpdate' in data:
                windows_update_tasks = data['WindowsUpdate']
                if not isinstance(windows_update_tasks, list):
                    windows_update_tasks = [windows_update_tasks]
                for task in sorted(windows_update_tasks, key=lambda x: x['Name']):
                    formatted_tasks.append(format_task_line(task['Name'], task['State']))
           
            formatted_tasks.append("Defender:")  # No indentation for header
            if 'Defender' in data and isinstance(data['Defender'], list):
                for task in sorted(data['Defender'], key=lambda x: x['Name']):
                    formatted_tasks.append(format_task_line(task['Name'], task['State']))

            return formatted_tasks
            
    except Exception as e:
        print(f"Debug - Error details: {str(e)}")
        return ["Error retrieving scheduled tasks"]
    

def format_task_scheduler_for_web(tasks_data):
    if not tasks_data:
        return ["No task scheduler data available"]
    
    try:
        formatted_tasks = []
        
        for item in tasks_data:
            # Remove ANSI color codes
            item = re.sub(r'\x1b\[\d+m', '', item)
            item = re.sub(r'\x1b\[0m', '', item)
            
            # Skip empty lines
            if not item.strip():
                continue
            
            # Format headers (items with "Tasks:")
            if "Tasks:" in item:
                formatted_tasks.append(f"{item.strip()}")
            else:
                # Check if it's a status line (contains 3 (Enabled))
                if "(Enabled)" in item:
                    # Split task name and status
                    parts = item.split("3 (Enabled)")
                    task_name = parts[0].strip()
                    # Pad with spaces to align status
                    formatted_tasks.append(f"    {task_name:<40} 3 (Enabled)")
                elif "No Sledgehammer tasks found" in item:
                    formatted_tasks.append(f"    {item.strip()}")
                else:
                    formatted_tasks.append(f"    {item.strip()}")
        
        return formatted_tasks
        
    except Exception as e:
        print(f"Error formatting task scheduler: {str(e)}")
        return ["Error formatting task scheduler data"]

    
def windows_defender_status():
    try:
        ps_command = """
        $status = Get-MpComputerStatus | Select-Object -Property AMServiceEnabled,
            RealTimeProtectionEnabled,
            IoavProtectionEnabled,
            AntispywareEnabled,
            BehaviorMonitorEnabled
        $status | ConvertTo-Json
        """
        process = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True)
        
        if process.returncode == 0:
            status = json.loads(process.stdout)
            return {
                'Real-time Protection': 'ON' if status['RealTimeProtectionEnabled'] else 'OFF',
                'Antispyware': 'ON' if status['AntispywareEnabled'] else 'OFF',
                'Behavior Monitor': 'ON' if status['BehaviorMonitorEnabled'] else 'OFF'
            }
        return {'Error': 'Unable to get status'}
    except Exception as e:
        return {'Error': str(e)}

def check_firewall_status():
    try:
        ps_command = "Get-NetFirewallProfile | Select-Object Name, Enabled | ConvertTo-Json"
        result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True)
        
        if result.returncode == 0:
            profiles = json.loads(result.stdout)
            if isinstance(profiles, dict):
                profiles = [profiles]
            
            status_dict = {}
            for profile in profiles:
                status_dict[profile['Name']] = 'ON' if profile['Enabled'] else 'OFF'
            return status_dict
    except Exception as e:
        return {'Error': str(e)}

def get_ars_version():
    try:
        pythoncom.CoInitialize()   # Initialize COM at the start
        paths = [
            r"D:\ARS\bin\ars.exe",
            r"C:\ARS\bin\ars.exe",
            r"C:\ARS\ars.exe",
            r"C:\ARS\ars.exe"]

        try:   # Check desktop shortcuts
            desktop = winshell.desktop()
            shortcuts = Path(desktop).glob("*.lnk")
            
            for shortcut in shortcuts:
                if "ars" in shortcut.name.lower():
                    shell = winshell.shortcut(str(shortcut))
                    target_path = shell.path
                    if os.path.exists(target_path):
                        info = win32api.GetFileVersionInfo(target_path, '\\')
                        version = f"{info['FileVersionMS'] >> 16}.{info['FileVersionMS'] & 0xFFFF}"
                        return f"ARS Version (from shortcut): {version}\n --> Path: {target_path}"
        except Exception as e:
            print(f"Shortcut check error: {str(e)}")

        for path in paths:   # Check direct file paths
            if os.path.exists(path):
                try:
                    info = win32api.GetFileVersionInfo(path, '\\')
                    version = f"{info['FileVersionMS'] >> 16}.{info['FileVersionMS'] & 0xFFFF}"
                    return f"ARS Version: {version}\nPath: {path}"
                except Exception as e:
                    print(f"Error getting version from {path}: {str(e)}")
                finally:
                    pythoncom.CoUninitialize()

        return "ARS.exe not found in standard locations. Please check manually."

    except Exception as e:
        return f"Error checking ARS version: {str(e)}"
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

def quick_drive_check():
    try:
        ps_command = """
        $result = @()
        'C', 'D' | ForEach-Object {
            $drive = Get-Volume $($_+ ':') | Select-Object DriveLetter, HealthStatus, 
                @{Name='UsedSpace';Expression={($_.Size - $_.SizeRemaining) / 1GB}},
                @{Name='TotalSize';Expression={$_.Size / 1GB}},
                @{Name='UsedPercent';Expression={[math]::Round((($_.Size - $_.SizeRemaining) / $_.Size) * 100, 1)}} 
            if ($drive) {
                $result += [PSCustomObject]@{
                    DriveLetter = $drive.DriveLetter
                    HealthStatus = $drive.HealthStatus
                    UsedSpace = [math]::Round($drive.UsedSpace, 2)
                    TotalSize = [math]::Round($drive.TotalSize, 2)
                    UsedPercent = $drive.UsedPercent
                }
            }
        }
        $result | ConvertTo-Json
        """
        result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True)
        
        if result.returncode == 0:
            drives = json.loads(result.stdout)
            if isinstance(drives, dict):
                drives = [drives]
            
            drive_status = {}
            for drive in drives:
                drive_letter = f"Drive {drive['DriveLetter']}"
                drive_status[drive_letter] = {
                    'Status': 'Healthy' if drive['HealthStatus'] == "Healthy" else 'Unhealthy',
                    'Usage': f"{drive['UsedPercent']}%",
                    'Space': f"{drive['UsedSpace']}/{drive['TotalSize']} GB"
                }
            
            return drive_status
                    
    except Exception as e:
        return {'Error': f"Error checking drive status: {str(e)}"}

def check_defrag_settings():
    try:
        ps_command = """
        Get-ScheduledTask | Where-Object {$_.TaskName -eq 'ScheduledDefrag'} | 
        Select-Object State | ConvertTo-Json
        """
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            task_state = json.loads(result.stdout)
            is_enabled = task_state.get('State') == 'Ready'
            
            return {
                'C_Drive': 'Enabled' if is_enabled else 'Disabled',
                'D_Drive': 'Enabled' if is_enabled else 'Disabled'
            }
                
    except Exception as e:
        print("Error checking defrag settings")
        return {'Error': 'Error checking defrag settings'}

def get_network_profile():
    try:
        ps_command = """
        Get-NetConnectionProfile | Select-Object InterfaceAlias, NetworkCategory | ConvertTo-Json
        """
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            profiles = json.loads(result.stdout)
            if isinstance(profiles, dict):  # Single profile
                profiles = [profiles]
                
            network_info = {}
            for profile in profiles:
                interface = profile['InterfaceAlias']
                category = profile['NetworkCategory']
                network_info[interface] = category
                
            return network_info
    except Exception as e:
        return {"Error": f"Failed to get network profile: {str(e)}"}

def is_windows_update_enabled():
    ps_command = "Get-Service -Name wuauserv | Select-Object -ExpandProperty Status"
    result = subprocess.run(
        ["powershell", "-Command", ps_command],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        status = result.stdout.strip()
        if status == "Running":
            return "Enabled"
        elif status == "Stopped":
            return "Disabled"
        else:
            return f"Unknown status: {status}"
    else:
        return f"Error checking Windows Update status: {result.stderr}"
    
def check_notification_settings():
    try:
        # Try to open the Windows App Runtime registry key for notifications
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        
        try:
            # Try to get EnableNotificationCenter value
            value, _ = winreg.QueryValueEx(key, "EnableNotificationCenter")
            return "Notifications are " + ("enabled" if value == 1 else "disabled")
        except WindowsError:
            # If that specific value isn't found, try alternate method
            subprocess.run(['powershell', '-Command', 'Get-ItemProperty -Path "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"'], capture_output=True)
            return "Could not determine exact status - please check Windows Settings"
    except Exception as e:
        return f"Error accessing notification settings: {str(e)}"
################## PRINT SUMMARY ##################################
def print_summary():
    """Print a formatted summary of all system checks"""
    init()  # Initialize colorama
    
    try:
        print(f"\n\n{Fore.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")

        print(f"{Fore.GREEN}{'='*20} SYSTEM INFORMATION {'='*20}{Style.RESET_ALL}\n")
        print(f"{Fore.CYAN}Computer Name:{Style.RESET_ALL} {get_computer_name()}")
        print(f"{Fore.CYAN}Windows Activation:{Style.RESET_ALL} {check_windows_activation()}")
        print(f"{Fore.CYAN}Time Zone:{Style.RESET_ALL} {get_time_zone()}")
       
        # Get display info and split it into components
        display_info = get_display_info()
        display_lines = display_info.split('\n')
        for line in display_lines:
            if any(key in line for key in ['Display Info:', 'Name:', 'Resolution:', 'Refresh rate:']):
                label = line.split(':')[0] + ':'
                value = ':'.join(line.split(':')[1:])
                print(f"{Fore.CYAN}{label}{Style.RESET_ALL}{value}")
            else:
                print(line)

        print(f"\n{Fore.GREEN}{'='*20} NETWORK CONFIGURATION {'='*20}{Style.RESET_ALL}")
        dhcp_status = check_dhcp_status()

        if isinstance(dhcp_status, dict):
            if "Error" in dhcp_status:
                print(f"{Style.YELLOW}Error:{Style.RESET_ALL} {dhcp_status['Error']}")
            else:
                network_profiles = get_network_profile()
                
                for interface, info in dhcp_status.items():
                    print(f"\n{Style.BRIGHT}{interface}:{Style.RESET_ALL}")
                    type_str = info.get('Type', 'N/A')
                    if isinstance(network_profiles, dict):
                        for profile_name, category in network_profiles.items():
                            if profile_name in interface:
                                type_str += f" (Category: {category})"
                    print(f"  {Fore.CYAN}Type:{Style.RESET_ALL} {type_str}")
                    
                    if info.get('DNS Suffix'):
                        print(f"  {Fore.CYAN}DNS Suffix:{Style.RESET_ALL} {info['DNS Suffix']}")
                    else:
                        print(f"  {Fore.CYAN}DNS Suffix:{Style.RESET_ALL} N/A")
                    print(f"  {Fore.CYAN}DHCP:{Style.RESET_ALL} {info.get('DHCP', 'N/A')}")
                    print(f"  {Fore.CYAN}IP:{Style.RESET_ALL} {info.get('IP', 'N/A')}")
                    print(f"  {Fore.CYAN}Subnet Mask:{Style.RESET_ALL} {info.get('Subnet Mask', 'N/A')}")
                    print(f"  {Fore.CYAN}Gateway:{Style.RESET_ALL} {info.get('Gateway', 'N/A')}")

        print(f"\n{Fore.GREEN}{'='*20} VERSIONS {'='*20}{Style.RESET_ALL}\n") 
        print(f"{Fore.CYAN}ARS Version:{Style.RESET_ALL} {get_ars_version()}")
        print(f"{Fore.CYAN}ARS Shortcut:{Style.RESET_ALL} {check_ars_shortcut()}")
        print(f"{Fore.CYAN}Boot Version:{Style.RESET_ALL} {get_boot_drive_version()}")
        print(f"{Fore.CYAN}VIB Version:{Style.RESET_ALL} {get_vib_version()}")
        print(f"{Fore.CYAN}FX3 Version:{Style.RESET_ALL} {get_fx3_version()}")
        
        print(f"\n{Fore.GREEN}{'='*20} SYSTEM STATUS {'='*20}{Style.RESET_ALL}\n")

        # Computer Metrics
        metrics = computer_metrics()
        print(f"{Fore.CYAN}Computer Metrics:{Style.RESET_ALL}")
        print(f"    CPU: {metrics['CPU']}")
        print(f"    RAM: {metrics['RAM']}")
        print(f"    Available Memory: {metrics['Available Memory']}")

        # Windows Defender
        defender = windows_defender_status()
        print(f"\n{Fore.CYAN}Windows Defender:{Style.RESET_ALL}")
        print(f"    Real-time Protection: {Fore.GREEN if defender['Real-time Protection'] == 'ON' else Fore.RED}{defender['Real-time Protection']}{Style.RESET_ALL}")
        print(f"    Antispyware: {Fore.GREEN if defender['Antispyware'] == 'ON' else Fore.RED}{defender['Antispyware']}{Style.RESET_ALL}")
        print(f"    Behavior Monitor: {Fore.GREEN if defender['Behavior Monitor'] == 'ON' else Fore.RED}{defender['Behavior Monitor']}{Style.RESET_ALL}")

        # Firewall Status
        firewall = check_firewall_status()
        print(f"\n{Fore.CYAN}Firewall Status:{Style.RESET_ALL}")
        for profile, status in firewall.items():
            print(f"    {profile}: {Fore.GREEN if status == 'ON' else Fore.RED}{status}{Style.RESET_ALL}")

        # Defrag Status
        defrag = check_defrag_settings()
        print(f"\n{Fore.CYAN}Defrag Status:{Style.RESET_ALL}")
        print(f"    C Drive: {Fore.GREEN if defrag['C_Drive'] == 'Enabled' else Fore.RED}{defrag['C_Drive']}{Style.RESET_ALL}")
        print(f"    D Drive: {Fore.GREEN if defrag['D_Drive'] == 'Enabled' else Fore.RED}{defrag['D_Drive']}{Style.RESET_ALL}")

        # Drive Health
        drives = quick_drive_check()
        print(f"\n{Fore.CYAN}Drive Health:{Style.RESET_ALL}")
        for drive, info in drives.items():
            print(f"    {Style.BRIGHT}{drive}:{Style.RESET_ALL}")
            print(f"       Status: {Fore.GREEN if info['Status'] == 'Healthy' else Fore.RED}{info['Status']}{Style.RESET_ALL}")
            print(f"       Usage: {info['Usage']}")
            print(f"       Space: {info['Space']}")
        
        # Windows Update
       # update_status = is_windows_update_enabled()
       # if update_status == "ENABLED":
       #     print(f"\n {Fore.CYAN}Windows Update:{Style.RESET_ALL} {Fore.GREEN}ENABLED{Style.RESET_ALL}")
       #     print(f"\n     Windows Update: {Fore.GREEN if update_status == 'ENABLED' else Fore.RED if update_status == 'DISABLED' else Fore.YELLOW}{update_status}{Style.RESET_ALL}")
       # elif update_status == "DISABLED":
      #      print(f"\n {Fore.CYAN}Windows Update:{Style.RESET_ALL} {Fore.RED}DISABLED{Style.RESET_ALL}")
       # else:
       #     print(f"\n {Fore.CYAN}Windows Update:{Style.RESET_ALL} {Fore.YELLOW}{update_status}{Style.RESET_ALL}")

        print(f"\n     Windows Update: {Fore.GREEN if update_status == 'ENABLED' else Fore.RED if update_status == 'DISABLED' else Fore.YELLOW}{update_status}{Style.RESET_ALL}")

        # TASK SCHEDULER
        print(f"\n{Fore.GREEN}{'='*20} TASK SCHEDULER {'='*20}{Style.RESET_ALL}")
        tasks = check_task_scheduler_status()
        if tasks:
            for task in tasks:
                if ':' in task:  # Category header
                    print(f"{Style.BRIGHT}{task}{Style.RESET_ALL}")
                else:
                    print(task)

        # COM PORTS
        print(f"\n{Fore.GREEN}{'='*20} COM PORTS {'='*20}{Style.RESET_ALL}")
        print(f"{Style.BRIGHT}Name                     Status   Service{Style.RESET_ALL}")
        print("----                     ------   -------")
        com_ports = get_com_ports()
        print(com_ports)

        print(f"{Fore.CYAN}")
        print(r"""
             ____    _    _    ___    _____     ___   __     __  _____   ____   
            / ___|  | |  | |  / _ \  |_   _|   / _ \  \ \   / / | ____| |  _ \  
            \___ \  | |__| | | | | |   | |    | | | |  \ \ / /  |  _|   | |_) | 
             ___) | |  __  | | |_| |   | |    | |_| |   \ V /   | |___  |  _ <  
            |____/  |_|  |_|  \___/    |_|     \___/     \_/    |_____| |_| \_\ 

                               ///////////             ///////////           
                             //////////////          //////////////         
                                /////////               ////////            

                    ////                                             //// 
                        ////                                        ////    
                        ////                                   ////       
                            ////                             ////          
                                ////                       ////             
                                    ////               ////                 
                                    ////////////////                     
        """.strip())
        print(f"{Style.RESET_ALL}")
        print("\n")

    except Exception as e:
        print(f"\n{Fore.RED}Error during system check: {str(e)}{Style.RESET_ALL}")
    finally:
        print(f"\n{Style.RESET_ALL}")

# Update your main() function to use the new summary printer:
def main():
    print_summary()

if __name__ == "__main__":
    main()

#----------THIS IS WHAT PULL REQUEST DOES --------------
#git add .
#git commit -m "Your commit message"
#git push origin your-branch-name

#----------THIS IS WHAT PULL REQUEST DOES --------------
# Switch to main/trunk branch
#git checkout main  # or master, depending on your default branch name

# Pull latest changes from main
#git pull origin main

# Merge your branch into main
#git merge your-branch-name

# Push changes to remote main
#git push origin main