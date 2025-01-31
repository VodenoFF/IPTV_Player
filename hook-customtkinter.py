from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all submodules
hiddenimports = collect_submodules('customtkinter')

# Collect all data files
datas = collect_data_files('customtkinter', include_py_files=True) 