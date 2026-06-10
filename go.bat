@echo off
setlocal enabledelayedexpansion

set "VENV_DIR=.venv"
set "ACTIVATE=%VENV_DIR%\Scripts\activate.bat"
set "DEPS_MARKER=%VENV_DIR%\.deps_installed"

REM Check if uv is installed
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 'uv' is not installed. Please install it from https://github.com/astral-sh/uv
    exit /b 1
)

REM Ensure venv exists
if not exist "%ACTIVATE%" (
    echo [SETUP] Creating virtual environment with uv...
    uv venv %VENV_DIR% --python 3.12
)

REM Activate venv
call "%ACTIVATE%"

REM Install Python deps if needed
if exist "%DEPS_MARKER%" goto RUN_APP

echo [SETUP] Detecting Hardware...

set TORCH_INDEX_URL=
set CUDA_VERSION_LABEL=CPU

REM Detect NVIDIA GPU driver presence
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [SETUP] Detected NVIDIA GPU
    set TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121
    set CUDA_VERSION_LABEL=cu126
) else (
    echo [SETUP] No NVIDIA GPU detected. Using CPU.
    set TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
    set CUDA_VERSION_LABEL=cpu
)

echo [SETUP] Installing PyTorch !CUDA_VERSION_LABEL! using uv...
uv pip install torch torchvision torchaudio --index-url !TORCH_INDEX_URL!

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install PyTorch.
    exit /b !ERRORLEVEL!
)

echo [SETUP] Installing remaining backend dependencies with uv...
uv pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install Python dependencies.
    exit /b !ERRORLEVEL!
)
echo Installed > "%DEPS_MARKER%"

:RUN_APP
REM Ensure Node deps exist
if not exist "node_modules" (
    echo [SETUP] Installing Node dependencies...
    npm install
)

REM Run modes
if "%1"=="cmd" (
    echo [INFO] Opening virtualenv shell...
    cmd /k
) else if "%1"=="backend" (
    echo [RUN] Starting backend only...
    npm run backend
) else if "%1"=="frontend" (
    echo [RUN] Starting frontend only...
    npm run frontend
) else if "%1"=="b" (
    echo [RUN] Building frontend...
    npm run build
) else (
    echo [RUN] Starting both backend and frontend...
    npm run start
)

endlocal