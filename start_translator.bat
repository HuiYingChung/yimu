@echo off
rem Double-click launcher for 譯幕 (Yimu): runs without a console window.
rem Errors still surface in the subtitle window / message boxes.
cd /d "%~dp0"
start "Yimu" pythonw main.py
