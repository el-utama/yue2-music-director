@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%results" mkdir "%ROOT%results"
if not defined YUE2_MCP_URL set "YUE2_MCP_URL=http://127.0.0.1:8791/mcp"
set "PYTHONPATH=%ROOT%src"
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\music-output.txt" -- py -3 -u -m yue2_music_director.autonomous --repo "%ROOT%." --url "%YUE2_MCP_URL%" %*
exit /b %ERRORLEVEL%
