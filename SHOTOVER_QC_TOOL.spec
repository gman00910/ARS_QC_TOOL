# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
    ('main_script.py', '.'),
    ('templates', 'templates'),
    ('static', 'static')
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('main_script.py', '.'),
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[
        'flask',
        'tzlocal',
        'win32api',
        'win32gui',
        'win32con',
        'winshell',
        'colorama',
        'psutil',
        'pythoncom',
        'win32com.shell',
        'win32com.client',
        'subprocess',
        'webbrowser',
        'main_script',
        'sys',  
        'os',
        'datetime',
        'threading'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SHOTOVER_QC_TOOL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True
)