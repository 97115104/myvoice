@echo off
REM My Voice Setup Script for Windows
REM Installs dependencies and sets up the environment

echo =======================================
echo          My Voice Setup
echo    Voice Cloning ^& Text-to-Speech
echo =======================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python detected

REM Create virtual environment
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
pip install --upgrade pip

REM Check for CUDA
echo.
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo CUDA detected, installing PyTorch with CUDA support...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
) else (
    echo No CUDA detected, installing CPU-only PyTorch...
    pip install torch torchaudio
)

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

REM Download XTTS model
echo.
echo Pre-downloading XTTS v2 model...
echo (This may take a few minutes, the model is ~2GB)
python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')"

echo.
echo =======================================
echo          Setup Complete!
echo =======================================
echo.
echo To start the server, run:
echo   venv\Scripts\activate.bat
echo   python server.py
echo.
echo Then open http://localhost:5000 in your browser
echo.
pause
