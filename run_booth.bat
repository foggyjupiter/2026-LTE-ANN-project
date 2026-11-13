@echo off
rem Sogaeting booth launcher for Windows. Double-click this file.
rem It only finds Python and hands over to run_booth.py in the same folder,
rem which starts the server and the Ren'Py game. Options are passed along,
rem for example: run_booth.bat --fake
rem
rem Korean guide: renpy\README.md
rem
rem This file is plain ASCII on purpose. cmd.exe reads .bat files in the system
rem code page (cp949 on Korean Windows), so Korean text saved as UTF-8 can break
rem the script. Every Korean message comes from run_booth.py instead.
rem
rem The last command builds the path of run_booth.py from the path of this file
rem (argument zero). Explorer passes that path in double quotes, so spaces and
rem Korean letters in folder names are safe. Do not add quotes around it.
rem There are no labels and no parenthesized blocks, so the script does not
rem depend on line endings or on parentheses in folder names.
setlocal
set "PY="
py -3 -c "pass" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "pass" >nul 2>nul && set "PY=python"
if not defined PY echo Python was not found. Python 3.10 or newer is needed.
if not defined PY echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
if not defined PY pause
if not defined PY exit /b 1
%PY% %0\..\run_booth.py %*
if errorlevel 1 pause
