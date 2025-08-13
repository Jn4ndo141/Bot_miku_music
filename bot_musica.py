import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import time
from dotenv import load_dotenv
from discord.ui import View, Button, Select
from typing import List, Optional, Dict

class MusicControlView(View):
    def __init__(self, player):
        super().__init__(timeout=None)
        self.player = player
        
        # Criamos os botões diretamente com os callbacks
        pause_button = Button(style=discord.ButtonStyle.primary, label="⏯️ Pausar/Continuar", custom_id="pause_resume_btn")
        stop_button = Button(style=discord.ButtonStyle.danger, label="⏹️ Parar", custom_id="stop_btn")
        skip_button = Button(style=discord.ButtonStyle.secondary, label="⏭️ Próxima", custom_id="skip_btn")
        loop_button = Button(style=discord.ButtonStyle.success, label="🔄 Loop", custom_id="loop_btn")
        
        # Definimos os callbacks para cada botão
        pause_button.callback = self.pause_resume_callback
        stop_button.callback = self.stop_callback
        skip_button.callback = self.skip_callback
        loop_button.callback = self.loop_callback
        
        # Adicionamos os botões à view
        self.add_item(pause_button)
        self.add_item(stop_button)
        self.add_item(skip_button)
        self.add_item(loop_button)
        
    async def interaction_check(self, interaction):
        # Verifica se o usuário está no mesmo canal de voz que o bot
        if not interaction.user.voice or (interaction.guild.voice_client and 
                                         interaction.user.voice.channel != interaction.guild.voice_client.channel):
            await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que o bot!", ephemeral=True)
            return False
        return True
        
    async def pause_resume_callback(self, interaction):
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ Música pausada!", ephemeral=True)
            self.player.paused = True
        else:
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("▶️ Música continuando!", ephemeral=True)
            self.player.paused = False
        await self.player.update_control_interface()
        
    async def stop_callback(self, interaction):
        self.player.loop = False
        self.player.queue = asyncio.Queue()
        self.player.queue_list = []
        
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.guild.voice_client.disconnect()
        
        await interaction.response.send_message("⏹️ Reprodução parada e fila limpa!", ephemeral=True)
        await self.player.update_control_interface()
        
    async def skip_callback(self, interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            self.player.skip_requested = True
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Pulando para a próxima música!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Não há música tocando para pular!", ephemeral=True)
            
    async def loop_callback(self, interaction):
        self.player.loop = not self.player.loop
        await interaction.response.send_message(
            f"🔄 Loop {'ativado' if self.player.loop else 'desativado'}!", 
            ephemeral=True
        )
        await self.player.update_control_interface()

load_dotenv()

intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options = {
    'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extract_flat': 'in_playlist',
    'prefer_ffmpeg': True,
    'keepvideo': False,
    'socket_timeout': 30
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -bufsize 512k -maxrate 128k',
    'executable': 'C:\\ffmpeg\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5, requester=None):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.requester = requester
        self.added_at = time.time()

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, requester=None, max_retries=3):
        loop = loop or asyncio.get_event_loop()
        
        # Implementa mecanismo de retry para lidar com oscilações de internet
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # Extrai informações do vídeo
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
                
                if 'entries' in data:
                    # Pega o primeiro item se for uma playlist
                    data = data['entries'][0]

                # Verifica se conseguiu extrair a URL do áudio
                if not data.get('url'):
                    raise Exception("Não foi possível extrair a URL do áudio")

                filename = data['url'] if stream else ytdl.prepare_filename(data)
                
                # Tenta criar o source com FFmpeg
                try:
                    audio_source = discord.FFmpegPCMAudio(filename, **ffmpeg_options)
                    source = cls(audio_source, data=data)
                    source.requester = requester
                    return source
                except Exception as ffmpeg_error:
                    # Se falhar com FFmpeg, tenta sem as opções extras
                    print(f"Erro com FFmpeg configurado, tentando versão simplificada: {ffmpeg_error}")
                    simple_options = {'options': '-vn'}
                    audio_source = discord.FFmpegPCMAudio(filename, **simple_options)
                    source = cls(audio_source, data=data)
                    source.requester = requester
                    return source
                    
            except Exception as e:
                retry_count += 1
                last_error = e
                # Espera com backoff exponencial
                wait_time = 1 * (2 ** (retry_count-1))  # 1, 2, 4 segundos...
                print(f"Erro ao processar URL (tentativa {retry_count}/{max_retries}): {e}. Tentando novamente em {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        # Se chegou aqui, todas as tentativas falharam
        raise last_error or Exception("Falha ao processar a URL após várias tentativas")

class MusicPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.queue_history = []
        self.queue_list = []

        self.np = None
        self.volume = 0.5
        self.current = None
        self.loop = True
        self.max_duration = 7200
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.last_position = 0
        self.skip_requested = False
        self.paused = False
        self.last_activity = time.time()
        
        # Interface de controle
        self.control_message = None
        self.control_view = None

        ctx.bot.loop.create_task(self.player_loop())
        ctx.bot.loop.create_task(self.connection_check())

    async def connection_check(self):
        """Verifica periodicamente a conexão e tenta reconectar em caso de problemas"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            await asyncio.sleep(15)  # Verifica a cada 15 segundos
            
            # Verifica se o bot está em um canal de voz
            if self.guild.voice_client and self.current:
                # Verifica se o áudio está realmente tocando
                if not self.guild.voice_client.is_playing() and not self.paused:
                    print(f"Detectada interrupção na reprodução. Tentando recuperar...")
                    self.reconnect_attempts += 1
                    
                    if self.reconnect_attempts <= self.max_reconnect_attempts:
                        try:
                            # Tenta reproduzir a música atual novamente
                            await self.channel.send(f"🔄 Reconectando... Tentativa {self.reconnect_attempts}/{self.max_reconnect_attempts}")
                            
                            # Reconecta ao canal de voz se necessário
                            if not self.guild.voice_client.is_connected():
                                voice_channel = self.guild.voice_client.channel
                                await voice_channel.connect()
                            
                            # Tenta reproduzir a música novamente
                            if self.current:
                                try:
                                    # Tenta obter a música novamente
                                    source = await YTDLSource.from_url(
                                        self.current.webpage_url, 
                                        loop=self.bot.loop, 
                                        stream=True,
                                        requester=self.current.requester
                                    )
                                    
                                    self.guild.voice_client.play(
                                        source, 
                                        after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set)
                                    )
                                    await self.channel.send(f"✅ Reprodução recuperada: **{source.title}**")
                                    self.current = source
                                    self.reconnect_attempts = 0  # Reseta o contador de tentativas
                                    
                                    # Atualiza a interface de controle
                                    await self.update_control_interface()
                                except Exception as e:
                                    await self.channel.send(f"❌ Erro ao recuperar a música: {str(e)}")
                        except Exception as e:
                            await self.channel.send(f"❌ Erro ao reconectar: {str(e)}")
                    else:
                        await self.channel.send("❌ Número máximo de tentativas de reconexão atingido. Use !tocar para tentar novamente.")
                        self.reconnect_attempts = 0
                        self.next.set()  # Avança para a próxima música, se houver
            else:
                self.reconnect_attempts = 0  # Reseta o contador quando não há reprodução ativa

    async def add_to_queue(self, source):
        """Adiciona uma música à fila e atualiza a lista de músicas"""
        await self.queue.put(source)
        self.queue_list.append(source)
        await self.update_control_interface()
        
    async def remove_from_queue(self, index):
        """Remove uma música da fila pelo índice"""
        if 0 <= index < len(self.queue_list):
            # Não podemos remover diretamente da asyncio.Queue, então recriamos
            removed_item = self.queue_list.pop(index)
            
            # Recria a fila sem o item removido
            old_queue = self.queue_list.copy()
            self.queue = asyncio.Queue()
            self.queue_list = []
            
            for item in old_queue:
                await self.add_to_queue(item)
                
            return removed_item
        return None

    async def update_control_interface(self):
        """Atualiza a interface de controle no chat"""
        if self.control_message:
            try:
                await self.control_message.delete()
            except:
                pass
        
        # Cria uma nova view com botões de controle
        view = MusicControlView(self)
        
        # Cria uma embed com informações da fila
        embed = discord.Embed(title="🎵 Controle de Música", color=0x00ff00)
        
        # Adiciona informações da música atual
        if self.current:
            embed.add_field(
                name="🔊 Tocando Agora", 
                value=f"**{self.current.title}**\n" +
                      f"Duração: {self.format_duration(self.current.duration)}\n" +
                      f"Solicitado por: {self.current.requester.mention if self.current.requester else 'Desconhecido'}", 
                inline=False
            )
            
            if self.current.thumbnail:
                embed.set_thumbnail(url=self.current.thumbnail)
        else:
            embed.add_field(name="🔊 Tocando Agora", value="Nada tocando no momento", inline=False)
        
        # Adiciona informações da fila
        queue_text = ""
        for i, song in enumerate(self.queue_list[:5]):
            requester = song.requester.mention if song.requester else "Desconhecido"
            queue_text += f"`{i+1}.` **{song.title}** ({self.format_duration(song.duration)}) - {requester}\n"
        
        if not queue_text:
            queue_text = "Nenhuma música na fila"
        elif len(self.queue_list) > 5:
            queue_text += f"\n... e mais {len(self.queue_list) - 5} músicas"
            
        embed.add_field(name="📋 Próximas na Fila", value=queue_text, inline=False)
        
        # Adiciona status do player
        status_text = f"🔄 Loop: {'Ativado' if self.loop else 'Desativado'}\n"
        status_text += f"🔊 Volume: {int(self.volume * 100)}%\n"
        status_text += f"⏱️ Limite de duração: {self.format_duration(self.max_duration)}"
        
        embed.add_field(name="⚙️ Configurações", value=status_text, inline=False)
        
        # Envia a mensagem com a interface de controle
        self.control_message = await self.channel.send(embed=embed, view=view)
        self.control_view = view

    def format_duration(self, duration):
        """Formata a duração em segundos para formato legível"""
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(minutes)}m {int(seconds)}s"

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()
            self.skip_requested = False

            try:
                # Timeout reduzido para permitir verificações mais frequentes
                source = await asyncio.wait_for(self.queue.get(), timeout=180)
            except asyncio.TimeoutError:
                # Verifica se há atividade recente antes de desconectar
                if time.time() - self.last_activity > 300:  # 5 minutos sem atividade
                    await self.channel.send("⏰ Desconectando por inatividade...")
                    return self.destroy(self.guild)
                continue

            if not isinstance(source, YTDLSource):
                continue

            if source.duration > self.max_duration:
                await self.channel.send(f"❌ Música muito longa! Máximo permitido: {self.format_duration(self.max_duration)}. Esta música tem {self.format_duration(source.duration)}")
                continue

            self.current = source
            self.last_activity = time.time()

            # Verifica e conecta ao canal de voz se necessário
            if not self.guild.voice_client or not self.guild.voice_client.is_connected():
                await self.channel.send("🔌 Conectando ao canal de voz...")
                try:
                    # Tenta encontrar o canal de voz do solicitante
                    if source.requester and source.requester.voice and source.requester.voice.channel:
                        await source.requester.voice.channel.connect()
                    else:
                        # Tenta encontrar qualquer canal de voz com membros
                        for vc in self.guild.voice_channels:
                            if len(vc.members) > 0:
                                await vc.connect()
                                break
                except Exception as e:
                    await self.channel.send(f"❌ Não foi possível conectar ao canal de voz: {str(e)}")
                    continue

            # Reproduz a música
            try:
                self.guild.voice_client.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next_song, e))
                self.np = await self.channel.send(f"🎵 Tocando agora: **{source.title}**")
                
                # Atualiza a interface de controle
                await self.update_control_interface()
                
                # Aguarda o término da música ou skip
                await self.next.wait()
                
                # Adiciona à fila novamente se o loop estiver ativado e não for um skip
                if self.loop and self.current and not self.skip_requested:
                    # Cria uma nova instância para evitar problemas com o stream
                    try:
                        looped_source = await YTDLSource.from_url(
                            self.current.webpage_url, 
                            loop=self.bot.loop, 
                            stream=True,
                            requester=self.current.requester
                        )
                        await self.queue.put(looped_source)
                        self.queue_list.append(looped_source)
                        await self.channel.send(f"🔄 Adicionado novamente à fila: **{self.current.title}**")
                    except Exception as e:
                        await self.channel.send(f"❌ Erro ao adicionar música em loop: {str(e)}")
                
                # Adiciona à história de reprodução
                if self.current:
                    self.queue_history.append(self.current)
                    # Limita o histórico a 10 músicas
                    if len(self.queue_history) > 10:
                        self.queue_history.pop(0)
            except Exception as e:
                await self.channel.send(f"❌ Erro durante a reprodução: {str(e)}")

    def play_next_song(self, error=None):
        """Callback chamado após o término de uma música"""
        if error:
            print(f"Erro na reprodução: {error}")
        
        # Remove a música atual da lista de fila se ela estiver lá
        if self.current in self.queue_list:
            self.queue_list.remove(self.current)
            
        self.next.set()

    def destroy(self, guild):
        """Limpa recursos e desconecta"""
        return self.bot.loop.create_task(self.cog.cleanup(guild))

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        return player

    @commands.command(name='tocar', aliases=['play', 'p'])
    async def play(self, ctx, *, url):
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return

        async with ctx.typing():
            try:
                data = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
                
                if 'entries' in data:
                    data = data['entries'][0]

                source = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True, requester=ctx.author)
                
                player = self.get_player(ctx)
                player.last_activity = time.time()  # Atualiza o timestamp de atividade
                await player.add_to_queue(source)
                
                await ctx.send(f"✅ **{source.title}** adicionada à fila! 🎵")
                
                if not ctx.guild.voice_client:
                    try:
                        await ctx.author.voice.channel.connect()
                        await ctx.send(f"🔌 Conectado automaticamente ao canal **{ctx.author.voice.channel.name}**!")
                    except Exception as e:
                        await ctx.send(f"❌ Erro ao conectar: {str(e)}")
                        return
                
            except Exception as e:
                await ctx.send(f"❌ Erro ao processar a música: {str(e)}")

    @commands.command(name='parar', aliases=['stop', 's'])
    async def stop(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return

        if ctx.guild.id in self.players:
            player = self.players[ctx.guild.id]
            player.loop = False
            player.queue = asyncio.Queue()
            player.queue_list = []
            
            if ctx.guild.voice_client:
                ctx.guild.voice_client.stop()
                await ctx.guild.voice_client.disconnect()
                
                # Limpa a interface de controle se existir
                if player.control_message:
                    try:
                        await player.control_message.delete()
                    except:
                        pass
            
            await ctx.send("⏹️ Reprodução parada e fila limpa!")

    @commands.command(name='pausar', aliases=['pause'])
    async def pause(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return

        if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
            player = self.get_player(ctx)
            ctx.guild.voice_client.pause()
            player.paused = True
            await ctx.send("⏸️ Música pausada!")
            await player.update_control_interface()

    @commands.command(name='continuar', aliases=['resume'])
    async def resume(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return

        if ctx.guild.voice_client and ctx.guild.voice_client.is_paused():
            player = self.get_player(ctx)
            ctx.guild.voice_client.resume()
            player.paused = False
            await ctx.send("▶️ Música continuando!")
            await player.update_control_interface()

    @commands.command(name='pular', aliases=['skip'])
    async def skip(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return
            
        if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
            player = self.get_player(ctx)
            player.skip_requested = True
            ctx.guild.voice_client.stop()
            await ctx.send("⏭️ Pulando para a próxima música!")
        else:
            await ctx.send("❌ Não há música tocando para pular!")

    @commands.command(name='volume')
    async def volume(self, ctx, volume: int):
        """Ajusta o volume (0-100)"""
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return

        if not 0 <= volume <= 100:
            await ctx.send("❌ Volume deve estar entre 0 e 100!")
            return

        if ctx.guild.id in self.players:
            player = self.players[ctx.guild.id]
            player.volume = volume / 100
            
            if ctx.guild.voice_client and ctx.guild.voice_client.source:
                ctx.guild.voice_client.source.volume = player.volume
            
            await ctx.send(f"🔊 Volume ajustado para {volume}%!")
            await player.update_control_interface()

    @commands.command(name='loop')
    async def loop(self, ctx):
        """Ativa ou desativa o loop da música atual"""
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return
            
        player = self.get_player(ctx)
        player.loop = not player.loop
        
        await ctx.send(f"🔄 Loop {'ativado' if player.loop else 'desativado'}!")
        await player.update_control_interface()

    @commands.command(name='fila', aliases=['queue', 'q'])
    async def queue(self, ctx):
        """Mostra a fila de músicas"""
        player = self.get_player(ctx)
        await player.update_control_interface()
        await ctx.send("📋 Painel de controle atualizado!")

    @commands.command(name='remover', aliases=['remove', 'r'])
    async def remove(self, ctx, index: int):
        """Remove uma música da fila pelo índice"""
        player = self.get_player(ctx)
        
        if index <= 0 or index > len(player.queue_list):
            await ctx.send(f"❌ Índice inválido! A fila tem {len(player.queue_list)} músicas.")
            return
            
        removed = await player.remove_from_queue(index - 1)  # Ajusta para índice base-0
        if removed:
            await ctx.send(f"🗑️ Removido da fila: **{removed.title}**")
            await player.update_control_interface()
        else:
            await ctx.send("❌ Não foi possível remover a música.")

    @commands.command(name='limpar', aliases=['clear'])
    async def clear(self, ctx):
        """Limpa toda a fila de músicas"""
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return
            
        player = self.get_player(ctx)
        player.queue = asyncio.Queue()
        player.queue_list = []
        
        await ctx.send("🧹 Fila limpa!")
        await player.update_control_interface()

    @commands.command(name='status')
    async def status(self, ctx):
        """Mostra o status atual do player"""
        if ctx.guild.id not in self.players:
            await ctx.send("❌ Nenhuma música tocando!")
            return

        player = self.players[ctx.guild.id]
        await player.update_control_interface()
        await ctx.send("📊 Painel de status atualizado!")

    @commands.command(name='conectar', aliases=['join', 'j'])
    async def join(self, ctx):
        """Conecta o bot ao canal de voz atual"""
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return
        
        if ctx.guild.voice_client:
            await ctx.send(f"✅ Já estou conectado ao canal **{ctx.guild.voice_client.channel.name}**!")
            return
        
        try:
            voice_channel = ctx.author.voice.channel
            await voice_channel.connect()
            await ctx.send(f"🎧 Conectado ao canal **{voice_channel.name}**!")
        except Exception as e:
            await ctx.send(f"❌ Erro ao conectar: {str(e)}")

    @commands.command(name='historico', aliases=['history', 'h'])
    async def history(self, ctx):
        """Mostra o histórico de músicas reproduzidas"""
        if not ctx.guild.id in self.players:
            await ctx.send("❌ Não há histórico disponível!")
            return
            
        player = self.players[ctx.guild.id]
        
        if not player.queue_history:
            await ctx.send("❌ Não há histórico disponível!")
            return
            
        embed = discord.Embed(title="📜 Histórico de Reprodução", color=0x9370DB)
        
        for i, song in enumerate(reversed(player.queue_history)):
            requester = song.requester.mention if song.requester else "Desconhecido"
            embed.add_field(
                name=f"{i+1}. {song.title}", 
                value=f"Duração: {player.format_duration(song.duration)} | Solicitado por: {requester}", 
                inline=False
            )
            
        await ctx.send(embed=embed)

    async def cleanup(self, guild):
        """Limpa o player quando o bot sai do servidor"""
        try:
            # Limpa a interface de controle se existir
            if guild.id in self.players and self.players[guild.id].control_message:
                try:
                    await self.players[guild.id].control_message.delete()
                except:
                    pass
                    
            await guild.voice_client.disconnect()
        except:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

@bot.event
async def on_ready():
    print(f'🎵 Bot de Música conectado como {bot.user.name}')
    print(f'🆔 ID: {bot.user.id}')
    print(f'📡 Conectado a {len(bot.guilds)} servidores')
    print(f'🔧 Intents habilitados: {bot.intents}')
    print('=' * 50)
    
    # Adiciona o cog de música quando o bot estiver pronto
    await bot.add_cog(Music(bot))
    print('✅ Cog de música carregado com sucesso!')

@bot.event
async def on_message(message):
    # Debug: mostrar todas as mensagens recebidas
    print(f'📨 Mensagem recebida: {message.content} de {message.author}')
    
    # Processar comandos
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    """Detecta mudanças no estado de voz dos membros"""
    
    # Se você entrou em um canal de voz
    if member.id == bot.user.id:
        return  # Ignora mudanças do próprio bot
    
    # Se você entrou em um canal de voz
    if before.channel is None and after.channel is not None:
        print(f'🎧 {member.name} entrou no canal de voz: {after.channel.name}')
        
        # Conecta o bot automaticamente ao mesmo canal
        try:
            voice_channel = after.channel
            if voice_channel.guild.voice_client is None:
                await voice_channel.connect()
                print(f'✅ Bot conectado automaticamente ao canal: {voice_channel.name}')
                
                # Envia mensagem de confirmação
                text_channel = voice_channel.guild.text_channels[0]  # Primeiro canal de texto
                await text_channel.send(f'🎧 Conectado automaticamente ao canal de voz **{voice_channel.name}**! Use `!tocar <música>` para começar.')
                
        except Exception as e:
            print(f'❌ Erro ao conectar automaticamente: {e}')
    
    # Se você saiu do canal de voz
    elif before.channel is not None and after.channel is None:
        print(f'🚪 {member.name} saiu do canal de voz: {before.channel.name}')
        
        # Se o bot está sozinho no canal, desconecta após 30 segundos
        if before.channel.guild.voice_client and len(before.channel.members) == 1:
            print(f'⏰ Bot sozinho no canal, desconectando em 30 segundos...')
            await asyncio.sleep(30)
            
            if before.channel.guild.voice_client and len(before.channel.members) == 1:
                await before.channel.guild.voice_client.disconnect()
                print(f'✅ Bot desconectado do canal vazio: {before.channel.name}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Comando não encontrado! Use `!ajuda` para ver os comandos disponíveis.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Argumento obrigatório faltando! Verifique a sintaxe do comando.")

@bot.command(name='ajuda')
async def help_command(ctx):
    """Mostra todos os comandos disponíveis"""
    help_embed = discord.Embed(
        title="🎵 Bot de Música - Comandos",
        description="Lista de todos os comandos disponíveis:",
        color=0x00ff00
    )
    
    commands_list = [
            ("!tocar <url/nome>", "Toca uma música do YouTube"),
            ("!parar", "Para a reprodução e limpa a fila"),
            ("!pausar", "Pausa a música atual"),
            ("!continuar", "Continua a música pausada"),
            ("!pular", "Pula para a próxima música na fila"),
            ("!volume <0-100>", "Ajusta o volume do player"),
            ("!loop", "Ativa/desativa o loop da música atual"),
            ("!fila", "Mostra o painel de controle com a fila atual"),
            ("!remover <número>", "Remove uma música da fila pelo número"),
            ("!limpar", "Limpa toda a fila de músicas"),
            ("!historico", "Mostra as últimas músicas tocadas"),
            ("!conectar", "Conecta o bot ao seu canal de voz"),
            ("!status", "Mostra o status atual do player"),
            ("!ajuda", "Mostra esta mensagem de ajuda")
        ]
    
    for cmd, desc in commands_list:
        help_embed.add_field(name=cmd, value=desc, inline=False)
    
    help_embed.set_footer(text="O bot reproduz músicas em loop por até 2 horas automaticamente!")
    
    await ctx.send(embed=help_embed)

# Executa o bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
