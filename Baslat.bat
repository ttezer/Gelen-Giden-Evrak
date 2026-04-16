@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PYTHON_EXE=.venv\Scripts\python.exe

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_FULL=py -3.14
) else (
    set PYTHON_FULL=python
)

if "%1"=="build" (
    echo "[1/2] Program Tasinabilir Tek Dosya (EXE) olarak paketleniyor..."
    %PYTHON_EXE% -m pip install pyinstaller
    %PYTHON_EXE% -m PyInstaller --noconfirm --onefile --windowed --name "Belge_Arsiv_Sistemi" --add-data "logo.png;." main.py
    echo "[2/2] Islem tamamlandi. dist/Belge_Arsiv_Sistemi.exe dosyasina bakin."
    pause
    exit /b
)

if not exist .venv (
    echo [!] Sanal ortam bulunamadi. Olusturuluyor...
    %PYTHON_FULL% -m venv .venv
    %PYTHON_EXE% -m pip install -r requirements.txt
) else (
    %PYTHON_EXE% --version >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [!] Sanal ortam bozuk. Yeniden olusturuluyor...
        rmdir /s /q .venv
        %PYTHON_FULL% -m venv .venv
        %PYTHON_EXE% -m pip install -r requirements.txt
    )
)

echo [OK] Uygulama baslatiliyor...
%PYTHON_EXE% main.py
if !ERRORLEVEL! neq 0 (
    echo [HATA] Uygulama beklenmedik sekilde kapandi. Yukaridaki hatayi kontrol edin.
    pause
)
exit
