# ARS_QC_TOOL
This application provides both a web interface and command-line interface for system administrators to view and manage various system health metrics for ARS Mission Computers.



Local --> C:\Users\garrett.smith\Documents\GitHub\ARS_QC_TOOL

CD C:\Users\garrett.smith\Documents\GitHub\ARS_QC_TOOL


![msedge_XsKD8vze9D](https://github.com/user-attachments/assets/03cba02a-a636-4d81-ac51-0761f529524d)


run shell as admin
cd "C:\Users\14106\Documents\GitHub\ARS_QC_TOOL"              --> home laptop
PS C:\Users\garrett.smith\Documents\github\ARS_QC_tool>       --> Work laptop

python -m PyInstaller main.py
pyinstaller --onefile --console --add-data "templates;templates" --add-data "static;static" main.py
