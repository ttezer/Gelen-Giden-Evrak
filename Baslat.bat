@echo off
setlocal
cd /d "%~dp0"
set PYTHON_EXE=.venv\Scripts\python.exe

if "%1"=="build" (
    echo "[1/2] Program Tasinabilir Tek Dosya (EXE) olarak paketleniyor..."
    %PYTHON_EXE% -m pip install pyinstaller
    %PYTHON_EXE% -m PyInstaller --noconfirm --onefile --windowed --name "Belge_Arsiv_Sistemi" --add-data "logo.png;." main.py
    echo "[2/2] Islem tamamlandi. dist/Belge_Arsiv_Sistemi.exe dosyasina bakin."
    pause
    exit /b
)

if not exist .venv (
    echo [!] Sanal ortam bulunamadi. Yukleniyor...
    python -m venv .venv
    %PYTHON_EXE% -m pip install -r requirements.txt
)

echo [OK] Uygulama baslatiliyor...
%PYTHON_EXE% main.py
if %ERRORLEVEL% neq 0 (
    echo [HATA] Uygulama beklenmedik sekilde kapandi. Yukaridaki hatayi kontrol edin.
    pause
)
exit
