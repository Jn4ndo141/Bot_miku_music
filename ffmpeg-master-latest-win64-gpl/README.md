# FFmpeg para o Bot de Música Discord

## Arquivos Binários Necessários

Este diretório deve conter os binários do FFmpeg necessários para o funcionamento do bot de música. Devido ao tamanho dos arquivos, eles não são incluídos no repositório Git.

## Como Obter os Arquivos

1. Baixe o FFmpeg para Windows em: https://ffmpeg.org/download.html#build-windows
   - Recomendamos a versão "FFmpeg Git Full".

2. Extraia o conteúdo do arquivo baixado.

3. Copie os seguintes arquivos para o diretório `bin/`:
   - `ffmpeg.exe`
   - `ffplay.exe`
   - `ffprobe.exe`

## Estrutura Esperada

```
ffmpeg-master-latest-win64-gpl/
├── bin/
│   ├── ffmpeg.exe
│   ├── ffplay.exe
│   └── ffprobe.exe
└── README.md (este arquivo)
```

## Verificação

Para verificar se os arquivos estão corretamente instalados, execute o script `executar_bot.bat` na raiz do projeto. Ele deve configurar o PATH para incluir estes binários automaticamente.