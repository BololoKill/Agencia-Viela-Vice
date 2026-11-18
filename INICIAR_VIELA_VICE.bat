@echo off
chcp 65001 >nul
title Agencia Viela Vice - Painel Executivo

:: Garante que o diretorio de execucao e a propria pasta do projeto
cd /d "%~dp0"

:: Verifica se o Python esta instalado e acessivel
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ====================================================================
    echo [ERRO] Python nao foi localizado no PATH do Windows!
    echo Instale o Python 3.10+ e marque a opcao "Add Python to PATH".
    echo ====================================================================
    pause
    exit /b 1
)

:: Executa o Launcher Interativo com UI/UX Vice City
python src\launcher.py

if %errorlevel% neq 0 (
    echo.
    echo Ocorreu uma interrupcao no sistema.
    pause
)
