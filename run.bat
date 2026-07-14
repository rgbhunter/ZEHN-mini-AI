@echo off
chcp 65001 > nul
title ZEHN mini - Bot Launcher
echo =======================================================
echo      ZEHN mini botini ishga tushirish...
echo =======================================================
echo.
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Xatolik yuz berdi! Dastur kutilmaganda to'xtadi.
    pause
)
