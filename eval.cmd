@echo off
setlocal
set "ROOT=%~dp0"
for %%I in ("%ROOT%..\yue2-eval-cpu") do set "EVALROOT=%%~fI"
set "PYTHON=%EVALROOT%\venv\Scripts\python.exe"
if not exist "%ROOT%results" mkdir "%ROOT%results"
if not exist "%PYTHON%" (
    echo ERROR: Existing isolated evaluator environment not found. > "%ROOT%results\eval-output.txt"
    type "%ROOT%results\eval-output.txt"
    exit /b 2
)
if not defined YUE2_MCP_URL set "YUE2_MCP_URL=http://127.0.0.1:8791/mcp"
set "PYTHONPATH=%ROOT%src"
set "HF_HUB_OFFLINE=1"
"%PYTHON%" -u -m yue2_music_director.logged_command --log "%ROOT%results\eval-output.txt" -- "%PYTHON%" -u -m yue2_music_director.retained_evaluation --repo "%ROOT%." --weights "%EVALROOT%\model.safetensors" --url "%YUE2_MCP_URL%"
exit /b %ERRORLEVEL%
