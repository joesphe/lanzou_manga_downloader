# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['d:\\lanzou_manga_downloader\\source_code_prod\\lanzoub_downloader_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 添加可能需要的数据文件
        ('source_code_prod/*', 'source_code_prod'),
    ],
    hiddenimports=[
        'DrissionPage',
        'tkinter',
        'json',
        'hashlib',
        'requests',
        'threading',
        're',
        'base64',
        'os',
        'sys',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='lanzou_downloader_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
