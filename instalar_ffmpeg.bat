@echo off
echo ========================================
echo    Instalador do FFmpeg para Bot Discord
echo ========================================
echo.

echo Verificando se o Chocolatey esta instalado...
choco --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Chocolatey nao encontrado. Instalando Chocolatey...
    echo.
    powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    if %errorlevel% neq 0 (
        echo Erro ao instalar Chocolatey. Tente instalar manualmente.
        pause
        exit /b 1
    )
    echo Chocolatey instalado com sucesso!
    echo.
)

echo Instalando FFmpeg...
choco install ffmpeg -y
if %errorlevel% neq 0 (
    echo Erro ao instalar FFmpeg via Chocolatey.
    echo Tentando metodo alternativo...
    echo.
    echo Baixando FFmpeg manualmente...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg.zip'"
    powershell -Command "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'C:\ffmpeg' -Force"
    echo Adicionando FFmpeg ao PATH...
    setx PATH "%PATH%;C:\ffmpeg\bin" /M
    del ffmpeg.zip
    echo FFmpeg instalado em C:\ffmpeg
) else (
    echo FFmpeg instalado com sucesso via Chocolatey!
)

echo.
echo Verificando instalacao do FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo AVISO: FFmpeg pode nao estar no PATH. Reinicie o terminal.
) else (
    echo FFmpeg instalado e funcionando corretamente!
)

echo.
echo ========================================
echo Instalacao concluida!
echo Reinicie o terminal e execute o bot novamente.
echo ========================================
pause