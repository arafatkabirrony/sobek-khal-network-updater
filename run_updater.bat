@echo off
title SOBEK Khal Network Updater - Developed by Arafat Kabir
cd /d "%~dp0"

set "CONDA_ENV=gis_env"
set "REPO_URL=https://github.com/arafatkabirrony/sobek-khal-network-updater"

if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat" "%CONDA_ENV%"
) else if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\miniconda3\Scripts\activate.bat" "%CONDA_ENV%"
) else (
    where conda >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Conda not found in PATH or default Anaconda/Miniconda folders.
        echo Repository: %REPO_URL%
        pause
        exit /b 1
    )
    call conda activate "%CONDA_ENV%"
)

if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate conda environment: %CONDA_ENV%
    echo Repository: %REPO_URL%
    pause
    exit /b 1
)

python "SOBEK_Khal_Network_Updater_Visual.py"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with an error.
    echo Repository: %REPO_URL%
    pause
)
