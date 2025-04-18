@echo off
set ext=%~x1
if [%ext%] == [.bin] (
    python "%~dp0/python/BBCF_Script_Parser.py" "--no-0" "%~f1"
) else if [%ext%] == [.py] (
    python "%~dp0/python/BBCF_Script_Rebuilder.py" "%~f1"
) else (
    echo Wrong file!
)
pause
