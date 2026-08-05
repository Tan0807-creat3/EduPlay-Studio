# -*- mode: python ; coding: utf-8 -*-
# EduPlay Studio — PyInstaller onedir spec
# Python source is obfuscated before PyInstaller packs it.

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SPEC_FILE = globals().get("__file__", os.path.join(os.getcwd(), "EduPlayStudio.spec"))
PROJECT_ROOT = os.path.abspath(os.path.dirname(SPEC_FILE))
SOURCE_ROOT = os.path.abspath(os.environ.get("EDUPLAY_OBF_ROOT", PROJECT_ROOT))
ENTRY_SCRIPT = os.path.join(SOURCE_ROOT, "app.py")

block_cipher = None


def add_data_dir(rel_source, rel_target=None):
    source = os.path.join(PROJECT_ROOT, rel_source)
    if not os.path.exists(source):
        return []
    return [(source, rel_target or rel_source)]


def add_data_file(rel_source, rel_target_dir):
    source = os.path.join(PROJECT_ROOT, rel_source)
    if not os.path.isfile(source):
        return []
    return [(source, rel_target_dir)]

# ── Collect Qt WebEngine resources (required at runtime) ──────────────────────
qtweb_datas = collect_data_files('PySide6', includes=['*.pak', '*.dat', '*.bin', '*.json'])
selected_datas = []
selected_datas += add_data_dir(os.path.join('eduplay', 'resources', 'icons'), os.path.join('eduplay', 'resources', 'icons'))
selected_datas += add_data_dir(os.path.join('eduplay', 'resources', 'styles'), os.path.join('eduplay', 'resources', 'styles'))
selected_datas += add_data_dir(os.path.join('eduplay', 'resources', 'fonts'), os.path.join('eduplay', 'resources', 'fonts'))
selected_datas += add_data_dir(os.path.join('eduplay', 'resources', 'i18n'), os.path.join('eduplay', 'resources', 'i18n'))
selected_datas += add_data_dir(os.path.join('eduplay', 'resources', 'vsto_addin'), os.path.join('eduplay', 'resources', 'vsto_addin'))
selected_datas += add_data_dir(os.path.join('assets_bundle', 'kenney_platformer-kit'), os.path.join('assets_bundle', 'kenney_platformer-kit'))
selected_datas += add_data_dir(os.path.join('assets_bundle', 'millionaire'), os.path.join('assets_bundle', 'millionaire'))
selected_datas += add_data_dir(os.path.join('assets_bundle', 'sound'), os.path.join('assets_bundle', 'sound'))
selected_datas += add_data_dir(os.path.join('assets_bundle', 'templates_fish'), os.path.join('assets_bundle', 'templates_fish'))
selected_datas += add_data_dir(os.path.join('assets_bundle', 'millionaire_ngdat'), os.path.join('assets_bundle', 'millionaire_ngdat'))
selected_datas += add_data_dir(os.path.join('assets_bundle', 'millionaire_exam'), os.path.join('assets_bundle', 'millionaire_exam'))
selected_datas += add_data_dir(os.path.join('assets_bundle', 'templates'), os.path.join('assets_bundle', 'templates'))
selected_datas += add_data_file(os.path.join('assets_bundle', 'game_config.json'), 'assets_bundle')

a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[SOURCE_ROOT, PROJECT_ROOT],
    binaries=[],
    datas=[
        *selected_datas,
        # Qt WebEngine helper process
        *qtweb_datas,
    ],
    hiddenimports=[
        *collect_submodules('eduplay'),
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtMultimedia',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtPrintSupport',
        'groq',
        'jinja2',
        'jinja2.ext',
        'PIL',
        'PIL.Image',
        'pkg_resources.py2_warn',
        'charset_normalizer',
        'cryptography',
    ],
    hookspath=[PROJECT_ROOT],
    hooksconfig={},
    runtime_hooks=['runtime_hook_distutils.py'],
    excludes=[
        # Dev / test artifacts — never shipped
        'tests',
        'pytest',
        # Fix distutils conflict in Python 3.12 - exclude setuptools._vendor
        'distutils',
        'setuptools._vendor',
        'setuptools._distutils',
        'unittest',
        'setuptools',
        'pip',
        'wheel',
        'distutils',
        'doctest',
        'pdb',
        'profile',
        'pstats',
        'cProfile',
        'xml.etree.ElementTree',  # not used at runtime
        'tkinter',
        'turtle',
        'curses',
        'idlelib',
        'lib2to3',
        'multiprocessing.pool',
        # Heavy unused scientific libs
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'sklearn',
        'IPython',
        'jupyter',
        'notebook',
        'black',
        'pylint',
        'mypy',
        'flake8',
        'hypothesis',
    ],
    noarchive=False,
    optimize=2,          # Compile to .pyc with -OO (strip docstrings + asserts)
)

pyz = PYZ(
    a.pure,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EduPlayStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,          # Strip debug symbols from EXE
    upx=True,            # UPX compress the EXE
    console=False,       # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'eduplay', 'resources', 'icons', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,          # Strip debug symbols from all binaries
    upx=True,            # UPX compress DLLs
    upx_exclude=[
        # Qt DLLs that break with UPX
        'Qt6WebEngineCore.dll',
        'Qt6WebEngineWidgets.dll',
        'Qt6Core.dll',
        'Qt6Gui.dll',
        'Qt6Widgets.dll',
        'Qt6Network.dll',
        'qwindows.dll',
        'qtwebengine_devtools_resources.pak',
    ],
    name='EduPlayStudio',
)
