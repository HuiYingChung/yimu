@echo off
rem Double-click launcher: runs the translator without a console window.
rem Errors still surface in the subtitle window / message boxes.
cd /d "%~dp0"
start "" pythonw main.py
