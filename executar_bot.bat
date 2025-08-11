@echo off
echo ========================================
echo    Bot de Musica Discord
echo ========================================
echo.

echo Configurando FFmpeg...
set PATH=%CD%\ffmpeg-master-latest-win64-gpl\bin;%PATH%
echo FFmpeg configurado: %CD%\ffmpeg-master-latest-win64-gpl\bin

echo.
echo Executando bot...
py bot_musica.py

echo.
echo Bot parado. Pressione qualquer tecla para sair...
pause > nul
