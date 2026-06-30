# Pipeline de Build

1. `build_app.bat` → PyInstaller (one-folder)
2. `cleanup_dlls.py` → Remove DLLs obsoletas
3. Inno Setup → Gera instalador
4. Teste automatizado (`--auto-test`)
