@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%results" mkdir "%ROOT%results"
if not defined YUE2_MCP_URL set "YUE2_MCP_URL=http://127.0.0.1:8791/mcp"
set "PYTHONPATH=%ROOT%src"
if /I "%~1"=="--styles" goto styles
if /I "%~1"=="--knowledge" goto knowledge
if /I "%~1"=="--artist-memory" goto artistmemory
if /I "%~1"=="--ready" goto ready
if /I "%~1"=="--setup" goto setup
if /I "%~1"=="--check-provider" goto check
if /I "%~1"=="--inspect-ending" goto ending
if /I "%~1"=="--review-plan" goto reviewplan
if /I "%~1"=="--cover" goto cover
if /I "%~1"=="--export" goto exportrelease
if /I "%~1"=="--feedback" goto feedback
if /I "%~1"=="--inspect-lock" goto lockstatus
if /I "%~1"=="--recover-lock" goto lockstatus
if /I "%~1"=="--release" goto releaseworkflow
if /I "%~1"=="--release-delivery" goto delivery
if /I "%~1"=="--assemble-release" goto assemble
if /I "%~1"=="--finish" goto finishaudio
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\music-output.txt" -- py -3 -u -m yue2_music_director.autonomous --repo "%ROOT%." --url "%YUE2_MCP_URL%" %*
exit /b %ERRORLEVEL%

:styles
py -3 -u -m yue2_music_director.style_library --repo "%ROOT%." %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%

:knowledge
py -3 -u -m yue2_music_director.knowledge_bank --repo "%ROOT%." %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%

:artistmemory
if /I "%~2"=="--help" goto artistmemoryhelp
py -3 -u -m yue2_music_director.artist_memory --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:artistmemoryhelp
py -3 -u -m yue2_music_director.artist_memory --help
exit /b %ERRORLEVEL%

:ready
py -3 -u -m yue2_music_director.readiness --repo "%ROOT%." --url "%YUE2_MCP_URL%" %*
exit /b %ERRORLEVEL%

:setup
py -3 -u -m yue2_music_director.provider_setup --repo "%ROOT%." --setup
exit /b %ERRORLEVEL%

:check
py -3 -u -m yue2_music_director.provider_setup --repo "%ROOT%." --check
exit /b %ERRORLEVEL%

:ending
if /I "%~2"=="--help" goto endinghelp
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\ending-output.txt" -- py -3 -u -m yue2_music_director.ending_audit --repo "%ROOT%." --job "%~2" --url "%YUE2_MCP_URL%"
exit /b %ERRORLEVEL%

:reviewplan
if /I "%~2"=="--help" goto reviewplanhelp
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\plan-review-output.txt" -- py -3 -u -m yue2_music_director.retained_plan_review --repo "%ROOT%." --job "%~2"
exit /b %ERRORLEVEL%

:cover
if /I "%~2"=="--help" goto coverhelp
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\cover-output.txt" -- py -3 -u -m yue2_music_director.cover_art --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:exportrelease
if /I "%~2"=="--help" goto exportreleasehelp
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\export-output.txt" -- py -3 -u -m yue2_music_director.release_export --repo "%ROOT%." --url "%YUE2_MCP_URL%" %*
exit /b %ERRORLEVEL%

:feedback
if /I "%~2"=="--help" goto feedbackhelp
py -3 -u -m yue2_music_director.human_feedback --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:finishaudio
if /I "%~2"=="--help" goto finishhelp
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\finishing-output.txt" -- py -3 -u -m yue2_music_director.audio_finishing --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:finishhelp
py -3 -u -m yue2_music_director.audio_finishing --help
exit /b %ERRORLEVEL%

:lockstatus
if /I "%~2"=="--help" goto lockstatushelp
py -3 -u -m yue2_music_director.lock_status --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:assemble
if /I "%~2"=="--help" goto assemblehelp
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\assembly-output.txt" -- py -3 -u -m yue2_music_director.release_assembly --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:delivery
if /I "%~2"=="--help" goto deliveryhelp
py -3 -u -m yue2_music_director.release_delivery --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:releaseworkflow
if /I "%~2"=="--help" goto releaseworkflowhelp
py -3 -u -m yue2_music_director.logged_command --log "%ROOT%results\release-output.txt" -- py -3 -u -m yue2_music_director.release_workflow --repo "%ROOT%." %*
exit /b %ERRORLEVEL%

:endinghelp
py -3 -u -m yue2_music_director.ending_audit --help
exit /b %ERRORLEVEL%

:reviewplanhelp
py -3 -u -m yue2_music_director.retained_plan_review --help
exit /b %ERRORLEVEL%

:coverhelp
py -3 -u -m yue2_music_director.cover_art --help
exit /b %ERRORLEVEL%

:exportreleasehelp
py -3 -u -m yue2_music_director.release_export --help
exit /b %ERRORLEVEL%

:feedbackhelp
py -3 -u -m yue2_music_director.human_feedback --help
exit /b %ERRORLEVEL%

:lockstatushelp
py -3 -u -m yue2_music_director.lock_status --help
exit /b %ERRORLEVEL%

:assemblehelp
py -3 -u -m yue2_music_director.release_assembly --help
exit /b %ERRORLEVEL%

:deliveryhelp
py -3 -u -m yue2_music_director.release_delivery --help
exit /b %ERRORLEVEL%

:releaseworkflowhelp
py -3 -u -m yue2_music_director.release_workflow --help
exit /b %ERRORLEVEL%
