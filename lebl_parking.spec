# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['LEBL Parking.pyw'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('data/aircraft_wingspans.json',   'data'),
        ('data/cargo_airlines.json',       'data'),
        ('data/prefix_data.json',          'data'),
        ('airports/LEBL/config.json',      'airports/LEBL'),
        ('airports/LEBL/airlines.json',    'airports/LEBL'),
        ('airports/LEBL/parkings.json',    'airports/LEBL'),
        ('airports/LEPA/config.json',      'airports/LEPA'),
        ('airports/LEPA/airlines.json',    'airports/LEPA'),
        ('airports/LEPA/parkings.json',    'airports/LEPA'),
        ('assets/splash.png',              'assets'),
    ],
    hiddenimports=[],
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

splash = Splash(
    'assets/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    splash,
    splash.binaries,
    [],
    name='LEBL Parking',
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
    entitlements_file=None
)
