@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%results" mkdir "%ROOT%results"
set "PYTHONPATH=%ROOT%src"
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\creative-output.txt" -- py -3 -u -m yue2_music_director.creative_core --repo "%ROOT%." %*
exit /b %ERRORLEVEL%
