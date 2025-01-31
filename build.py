import os
import sys
import shutil
import subprocess
import customtkinter
import site
from pathlib import Path
import base64

def copy_customtkinter_assets():
    """Copy customtkinter assets to a temporary directory"""
    ctk_path = Path(customtkinter.__file__).parent
    assets_path = ctk_path / 'assets'
    temp_assets = Path('temp_assets')
    
    # Create temp directory
    if temp_assets.exists():
        shutil.rmtree(temp_assets)
    temp_assets.mkdir()
    
    # Copy assets
    if assets_path.exists():
        shutil.copytree(assets_path, temp_assets / 'customtkinter' / 'assets', dirs_exist_ok=True)
    
    return str(temp_assets)

def create_icon():
    """Create an icon file if it doesn't exist"""
    if os.path.exists('icon.ico'):
        return
        
    # Base64 encoded minimal TV icon (you can replace this with your own icon)
    icon_data = '''
    AAABAAEAICAAAAEAIACoEAAAFgAAACgAAAAgAAAAQAAAAAEAIAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABsbGwAa2trAGtra0Bra2uga2tr4Gtr
    a+Bra2uga2trQGtraQBra2kAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGxsbABra2sAa2trQGtra6Bra2vga2tr/2tra/9ra2v/a2tr
    /2tra+Bra2uga2trQGtraQBraWkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAABsbGwAa2trAGtra0Bra2uga2tr4Gtra/9ra2v/a2tr/2tra/9ra2v/a2tr/2tr
    a/9ra2vga2troGtraz9raWkAa2lpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAGxsbABra2sAa2trQGtra6Bra2vga2tr/2tra/9ra2v/a2tr/2tra/9ra2v/a2tr/2tra/9ra2v/a2tr
    /2tra+Bra2uga2trP2tpaQBraWkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAbGxs
    AGtrawBra2tAa2troGtra+Bra2v/a2tr/2tra/9ra2v/a2tr/2tra/9ra2v/a2tr/2tra/9ra2v/a2tr/2tra/9ra2v/
    a2tr4Gtra6Bra2s/a2lpAGtpaQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABra2sAa2trQGtra6Bra2vga2tr/2tra/9ra2v/a2tr4Gtr
    a6Bra2tAa2trAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGtra0Bra2uga2tr4Gtra/9ra2v/a2tr/2tra+Bra2uga2tr
    QGtraQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABra2tAa2troGtra+Bra2v/a2tr/2tra/9ra2v/a2tr/2tra+Bra2uga2tr
    P2tpaQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAGtra6Bra2vga2tr/2tra/9ra2v/a2tr/2tra/9ra2v/a2tr/2tra+Bra2uga2tr
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAABra2vga2tr/2tra/9ra2v/a2tr/2tra/9ra2v/a2tr/2tra/9ra2v/a2tr4Gtra0AA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAGtra+Bra2v/a2tr/2tra/9ra2v/a2tr/2tra/9ra2v/a2tr/2tra/9ra2vga2trQAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAABra2uga2tr4Gtra/9ra2v/a2tr/2tra/9ra2v/a2tr/2tra/9ra2vga2troGtrawAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAGtra0Bra2uga2tr4Gtra/9ra2v/a2tr/2tra/9ra2vga2troGtra0AAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//
    /wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////
    AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wA=
    '''
    
    # Write icon file
    with open('icon.ico', 'wb') as f:
        f.write(base64.b64decode(icon_data.replace('\n', '').strip()))

def build_exe():
    try:
        # Clean previous build
        for path in ['build', 'dist', 'temp_assets']:
            if os.path.exists(path):
                shutil.rmtree(path)
        
        # Create icon
        create_icon()
        
        # Copy assets to temp directory
        temp_path = copy_customtkinter_assets()
        
        # Create spec file content
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# Optimization settings
strip = True
upx = False  # Disable UPX for faster startup
debug = False

a = Analysis(
    ['iptv_player.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('lib/*', 'lib'),
        ('{temp_path}/*', '.'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'customtkinter',
        'cryptography',
        'multiprocessing',
        '_socket',
        'select',
        'tkinter',
        '_tkinter',
        'tkinter.ttk',
    ],
    hookspath=['.'],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'notebook', 'scipy', 'pandas', 'numpy',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
        'test', 'tests', 'testing', '_pytest',
        '_decimal', '_bz2', '_lzma', '_hashlib',
        'unittest', 'pdb', 'difflib', 'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary binary dependencies
a.binaries = [x for x in a.binaries if not x[0].startswith('mfc')]
a.binaries = [x for x in a.binaries if not x[0].startswith('api-ms-win')]
a.binaries = [x for x in a.binaries if not x[0].startswith('opengl32sw')]

# Keep only necessary data files
a.datas = [x for x in a.datas if not x[0].startswith('tk/demos')]
a.datas = [x for x in a.datas if not x[0].startswith('tk/images')]
a.datas = [x for x in a.datas if not x[0].startswith('tk/msgs')]
a.datas = [x for x in a.datas if not x[0].startswith('tcl/encoding')]
a.datas = [x for x in a.datas if not x[0].startswith('tcl/msgs')]
a.datas = [x for x in a.datas if not x[0].startswith('tcl/tzdata')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IPTV_Player',
    debug=debug,
    bootloader_ignore_signals=False,
    strip=strip,
    upx=upx,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    uac_admin=False,
    optimize=2
)
'''

        # Write spec file
        with open('iptv_player.spec', 'w') as f:
            f.write(spec_content)

        # Build command
        build_cmd = [
            'pyinstaller',
            '--clean',
            '--noconfirm',
            'iptv_player.spec'
        ]

        # Execute build
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("Build failed with error:")
            print(result.stdout)
            print(result.stderr)
            return

        # Copy MPV files if on Windows
        if sys.platform == 'win32':
            mpv_files = ['mpv-2.dll']
            dist_lib = os.path.join('dist', 'IPTV_Player', 'lib')
            os.makedirs(dist_lib, exist_ok=True)
            
            for file in mpv_files:
                src = os.path.join('lib', file)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(dist_lib, file))

        print("Build completed! Executable is in the 'dist' folder.")

    except Exception as e:
        print(f"Error during build: {str(e)}")
    finally:
        # Clean up temp directory
        if os.path.exists('temp_assets'):
            shutil.rmtree('temp_assets')

if __name__ == '__main__':
    build_exe() 