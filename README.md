# 🎵 Discord Music Bot

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.3.2-7289da.svg)](https://discordpy.readthedocs.io/en/stable/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Um bot de música avançado para Discord com reprodução contínua e controles intuitivos**

</div>

## 📋 Visão Geral

Este bot de música para Discord oferece uma experiência de áudio de alta qualidade com recursos avançados como reprodução automática em loop, controle de volume e gerenciamento de fila. Desenvolvido com Discord.py e yt-dlp, o bot é capaz de reproduzir músicas do YouTube com excelente qualidade de áudio.

## ✨ Funcionalidades

- 🎵 **Reprodução de alta qualidade** - Streaming de áudio do YouTube com qualidade otimizada
- 🔄 **Loop automático** - Reprodução contínua da mesma música
- ⏱️ **Limite de duração configurável** - Padrão de 2 horas por música
- 🔊 **Controle de volume dinâmico** - Ajuste o volume durante a reprodução
- ⏸️ **Controles de reprodução** - Pausar, continuar e parar a qualquer momento
- 📊 **Status em tempo real** - Informações detalhadas sobre a música em reprodução
- 🔍 **Pesquisa integrada** - Encontre músicas por nome sem precisar de URL

## 🛠️ Requisitos Técnicos

- Python 3.8 ou superior
- FFmpeg (instruções de instalação abaixo)
- Conexão com internet estável
- Token de bot do Discord
- Permissões adequadas no servidor Discord

## 🚀 Guia de Instalação

### Pré-requisitos

- [Python 3.8+](https://www.python.org/downloads/) instalado no seu sistema
- [Git](https://git-scm.com/downloads) (opcional, para clonar o repositório)
- [FFmpeg](https://ffmpeg.org/download.html) (necessário para processamento de áudio)
- Token de bot do Discord válido

### Instalação Passo a Passo

1. **Clone ou baixe este repositório**

2. **Instale as dependências**
   ```bash
   py -m pip install -r requirements.txt
   ```

3. **Configure o FFmpeg**
   - Baixe o FFmpeg para Windows em: https://ffmpeg.org/download.html#build-windows
   - Extraia os arquivos e coloque os executáveis (`ffmpeg.exe`, `ffplay.exe`, `ffprobe.exe`) na pasta `ffmpeg-master-latest-win64-gpl/bin/`
   - Consulte o arquivo `ffmpeg-master-latest-win64-gpl/README.md` para mais detalhes

4. **Configure o token do bot**
   - Renomeie o arquivo `.env_example` para `.env`
   - Substitua `seu_token_aqui` pelo seu token real do Discord
   ```
   DISCORD_TOKEN=seu_token_aqui
   ```

5. **Execute o bot**
   ```bash
   # Opção 1: Direto pelo Python
   py bot_musica.py

   # Opção 2: Pelo script batch (Windows)
   executar_bot.bat
   ```

## 🔧 Configuração do Bot no Discord

### 1. Criar uma Aplicação no Discord

1. Acesse o [Portal de Desenvolvedores do Discord](https://discord.com/developers/applications)
2. Clique em "New Application" e dê um nome para seu bot
3. Navegue até a seção "Bot" no menu lateral
4. Clique em "Add Bot" e confirme

### 2. Configurar Permissões do Bot

1. Na seção "Privileged Gateway Intents", ative:
   - ✅ PRESENCE INTENT
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT

2. Em "OAuth2" → "URL Generator":
   - Em **Scopes**: selecione `bot`
   - Em **Bot Permissions**: selecione
     - Send Messages
     - Use Slash Commands
     - Connect
     - Speak
     - Use Voice Activity

3. Copie o URL gerado e abra-o em seu navegador para adicionar o bot ao seu servidor

## 🎮 Comandos Disponíveis

| Comando | Aliases | Descrição |
|---------|---------|------------|
| `!tocar <URL/termo>` | `!play`, `!p` | Reproduz uma música do YouTube |
| `!parar` | `!stop`, `!s` | Interrompe a reprodução atual |
| `!pausar` | `!pause` | Pausa a música em reprodução |
| `!continuar` | `!resume` | Retoma a reprodução pausada |
| `!volume <0-100>` | - | Ajusta o volume de reprodução |
| `!status` | - | Exibe informações sobre a música atual |
| `!ajuda` | `!help` | Lista todos os comandos disponíveis |

## 📖 Guia de Uso

1. **Conecte-se a um canal de voz** - Entre em um canal de voz no Discord
2. **Inicie a reprodução** - Digite `!tocar <URL do YouTube>` ou `!tocar <nome da música>`
3. **Controle a reprodução** - Use os comandos para pausar, continuar ou ajustar o volume
4. **Encerre a reprodução** - Use `!parar` quando quiser interromper a música

## ⚙️ Personalização

### Limite de Duração
O bot está configurado para aceitar músicas com até 2 horas (7200 segundos). Para alterar este limite, modifique a seguinte linha no arquivo `bot_musica.py`:

```python
self.max_duration = 7200  # 2 horas em segundos
```

### Reprodução em Loop
Por padrão, o bot reproduz músicas em loop automaticamente. Para desativar esta função, altere:

```python
self.loop = False  # Desativa o loop automático
```

## 🔍 Solução de Problemas

- **O bot não reproduz áudio**: Verifique se o FFmpeg está corretamente configurado
- **Erros de conexão**: Certifique-se de que o bot tem permissões adequadas no servidor
- **Problemas com URLs**: Alguns vídeos podem ter restrições de reprodução; tente outro vídeo
- **Bot não responde**: Verifique se os intents estão corretamente configurados no Portal do Desenvolvedor
- **Erro ao fazer push para GitHub**: Os arquivos FFmpeg são muito grandes para o GitHub. Use o `.gitignore` fornecido para excluí-los do repositório

## 📦 Dependências

- [discord.py[voice]](https://discordpy.readthedocs.io/) - Framework para interação com a API do Discord
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Biblioteca para download e extração de informações do YouTube
- [PyNaCl](https://pypi.org/project/PyNaCl/) - Biblioteca para criptografia (necessária para áudio)
- [python-dotenv](https://pypi.org/project/python-dotenv/) - Gerenciamento de variáveis de ambiente
- [ffmpeg-python](https://pypi.org/project/ffmpeg-python/) - Interface Python para FFmpeg

## 📜 Licença

Este projeto está licenciado sob a [Licença MIT](https://opensource.org/licenses/MIT) - veja o arquivo LICENSE para detalhes.

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests com melhorias.

### Nota sobre arquivos grandes

Os executáveis do FFmpeg excedem o limite de tamanho de arquivo do GitHub (100MB). Por isso:
1. Eles estão incluídos no `.gitignore`
2. Você precisará baixá-los separadamente seguindo as instruções acima
3. Consulte o arquivo `ffmpeg-master-latest-win64-gpl/README.md` para mais detalhes

---

<div align="center">

Aproveite

</div>
