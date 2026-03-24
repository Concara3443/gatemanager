# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Incluir automáticamente todos los aeropuertos en airports/
airports_datas = []
airports_dir = os.path.join(os.path.dirname(os.path.abspath(SPEC)), 'airports')
for icao in os.listdir(airports_dir):
    icao_path = os.path.join(airports_dir, icao)
    if not os.path.isdir(icao_path):
        continue
    for fname in os.listdir(icao_path):
        if fname.endswith('.json'):
            airports_datas.append(
                (os.path.join(icao_path, fname), f'airports/{icao}')
            )

a = Analysis(
    ['LEBL Parking.pyw'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('data/aircraft_wingspans.json',   'data'),
        ('data/cargo_airlines.json',       'data'),
        ('data/prefix_data.json',          'data'),
        ('assets/splash.png',              'assets'),
        ('assets/icon.png',                'assets'),
    ] + airports_datas,
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
    name='GateManager',
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
    icon='assets/icon.ico'
)
