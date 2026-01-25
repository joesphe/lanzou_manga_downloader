# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['source_code/lanzou_simple_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 添加必要的数据文件
        ('source_code', 'source_code'),
    ],
    hiddenimports=[
        'DrissionPage',
        'tqdm',
        'json',
        'logging',
        'concurrent.futures',
        'requests',
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'threading',
        're',
        'datetime',
        'os',
        'sys',
        'time',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='蓝奏云漫画下载器_精简版',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False以创建GUI应用（无控制台窗口）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标文件的话
)
