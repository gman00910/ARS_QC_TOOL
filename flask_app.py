from asyncio import log
import ctypes
import subprocess
import sys
import os 
from flask import Flask, render_template, request, redirect, url_for
import webbrowser
from threading import Timer, Thread
import main_script 
import logging
from logging.config import dictConfig

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

app = Flask(__name__, 
           static_url_path='/static',
           static_folder=resource_path('static'),
           template_folder=resource_path('templates'))

def run_as_admin():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            print("Requesting admin privileges...")
            script = os.path.abspath(sys.argv[0])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, script, None, 1)
            return False
        return True
    except Exception as e:
        print(f"Error requesting admin privileges: {str(e)}")
        return False
    
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

@app.route('/run_viblib')
def run_viblib_route():
    result = main_script.run_viblib()
    return render_template('result.html', result=result)

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
        batch_content = f'@echo off\npython "{script_path}"\npause'
        
       
        batch_file_path = os.path.join(os.path.expanduser('~'), 'run_summary.bat')
        with open(batch_file_path, 'w') as f:
            f.write(batch_content)
        
       
        subprocess.Popen(['cmd', '/k', batch_file_path], shell=True)
        return "Command prompt opened successfully"
    except Exception as e:
        return f"Error opening command prompt: {str(e)}"

@app.route('/Openshell')
def Openshell():
    try:
       
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
        
       
        batch_content = '@echo off\n'
        batch_content += 'title SHOTOVER Systems - Drive Summary Details\n'
        batch_content += 'color 0A\n'
        batch_content += f'python "{script_path}"\n'
        batch_content += 'echo.\n'
        batch_content += 'echo Press any key to close this window...\n'
        batch_content += 'pause >nul'
        
       
        batch_file = os.path.join(os.environ['TEMP'], 'shotover_summary.bat')
        with open(batch_file, 'w') as f:
            f.write(batch_content)
        
       
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = subprocess.SW_MAXIMIZE 
        
        process = subprocess.Popen(['cmd', '/c', 'start', '/MAX', batch_file], 
                                 startupinfo=startup_info,
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        return render_template('result.html', result="Shell opened successfully")
    except Exception as e:
        return render_template('result.html', result=f"Error opening shell: {str(e)}")

@app.route('/printt')
def printt():
    try:
       
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_script.py')
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        output = result.stdout
        
       
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>SHOTOVER Systems - Drive Summary</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                .header { text-align: center; margin-bottom: 30px; }
                .content { white-space: pre-wrap; }
                @media print {
                    body { margin: 0.5in; }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>SHOTOVER Systems - Drive Summary</h1>
                <p>Generated on {date}</p>
            </div>
            <div class="content">{content}</div>
            <script>
                window.onload = function() { window.print(); window.close(); }
            </script>
        </body>
        </html>
        '''.format(date=result.stdout.split('\n')[0], content=output)
        
       
        temp_html = os.path.join(os.environ['TEMP'], 'shotover_summary_print.html')
        with open(temp_html, 'w') as f:
            f.write(html_content)
            
       
        webbrowser.open('file://' + temp_html)
        
        return render_template('result.html', result="Print dialog opened")
    except Exception as e:
        return render_template('result.html', result=f"Error printing: {str(e)}")
    
@app.route('/run_ars')
def run_ars_route():
    result = main_script.run_ars()
    return redirect('/')  # Redirect back to home page

def open_browser():
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    if run_as_admin():
        Timer(0.3, open_browser).start()
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)