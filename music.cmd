@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%results" mkdir "%ROOT%results"
if not defined YUE2_MCP_URL set "YUE2_MCP_URL=http://127.0.0.1:8791/mcp"
set "PYTHONPATH=%ROOT%src"
if /I "%~1"=="--setup" goto setup
if /I "%~1"=="--check-provider" goto check
if /I "%~1"=="--inspect-ending" goto ending
if /I "%~1"=="--review-plan" goto reviewplan
if /I "%~1"=="--cover" goto cover
if /I "%~1"=="--export" goto exportrelease
if /I "%~1"=="--feedback" goto feedback
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\music-output.txt" -- py -3 -u -m yue2_music_director.autonomous --repo "%ROOT%." --url "%YUE2_MCP_URL%" %*
exit /b %ERRORLEVEL%

:setup
py -3 -u -m yue2_music_director.provider_setup --repo "%ROOT%." --setup
exit /b %ERRORLEVEL%

:check
py -3 -u -m yue2_music_director.provider_setup --repo "%ROOT%." --check
exit /b %ERRORLEVEL%

:ending
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\ending-output.txt" -- py -3 -u -m yue2_music_director.ending_audit --repo "%ROOT%." --job "%~2" --url "%YUE2_MCP_URL%"
exit /b %ERRORLEVEL%

:reviewplan
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\plan-review-output.txt" -- py -3 -u -m yue2_music_director.retained_plan_review --repo "%ROOT%." --job "%~2"
exit /b %ERRORLEVEL%

:cover
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\cover-output.txt" -- py -3 -u -m yue2_music_director.cover_art --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:exportrelease
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\export-output.txt" -- py -3 -u -m yue2_music_director.release_export --repo "%ROOT%." --url "%YUE2_MCP_URL%" %*
exit /b %ERRORLEVEL%

:feedback
py -3 -u -m yue2_music_director.human_feedback --repo "%ROOT%." %*
exit /b %ERRORLEVEL%
