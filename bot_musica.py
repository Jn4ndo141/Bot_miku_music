import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
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
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration', 0)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None
        self.volume = 0.5
        self.current = None
        self.loop = True
        self.max_duration = 7200

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                source = await asyncio.wait_for(self.queue.get(), timeout=300)
            except asyncio.TimeoutError:
                return self.destroy(self.guild)

            if not isinstance(source, YTDLSource):
                continue

            if source.duration > self.max_duration:
                await self.channel.send(f"❌ Música muito longa! Máximo permitido: 2 horas. Esta música tem {source.duration//3600}h {(source.duration%3600)//60}m")
                continue

            self.current = source

            if not self.guild.voice_client:
                await self.channel.send("🔌 Conectando ao canal de voz...")
                try:
                    await self.channel.author.voice.channel.connect()
                except:
                    await self.channel.send("❌ Não foi possível conectar ao canal de voz!")
                    return

            self.guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self.channel.send(f"🎵 Tocando agora: **{source.title}**")

            await self.next.wait()

            if self.loop and self.current:
                await self.queue.put(self.current)
                await self.channel.send(f"🔄 Reproduzindo novamente: **{self.current.title}**")

    def destroy(self, guild):
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

                source = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                
                player = self.get_player(ctx)
                await player.queue.put(source)
                
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
            
            if ctx.guild.voice_client:
                ctx.guild.voice_client.stop()
                await ctx.guild.voice_client.disconnect()
            
            await ctx.send("⏹️ Reprodução parada e fila limpa!")

    @commands.command(name='pausar', aliases=['pause'])
    async def pause(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return

        if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
            ctx.guild.voice_client.pause()
            await ctx.send("⏸️ Música pausada!")

    @commands.command(name='continuar', aliases=['resume'])
    async def resume(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return

        if ctx.guild.voice_client and ctx.guild.voice_client.is_paused():
            ctx.guild.voice_client.resume()
            await ctx.send("▶️ Música continuando!")

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

    @commands.command(name='status')
    async def status(self, ctx):
        """Mostra o status atual do player"""
        if ctx.guild.id not in self.players:
            await ctx.send("❌ Nenhuma música tocando!")
            return

        player = self.players[ctx.guild.id]
        status_msg = f"📊 **Status do Player:**\n"
        status_msg += f"🎵 **Música atual:** {player.current.title if player.current else 'Nenhuma'}\n"
        status_msg += f"🔄 **Loop:** {'Ativado' if player.loop else 'Desativado'}\n"
        status_msg += f"🔊 **Volume:** {int(player.volume * 100)}%\n"
        status_msg += f"📺 **Canal:** {ctx.guild.voice_client.channel.name if ctx.guild.voice_client else 'Desconectado'}"
        
        await ctx.send(status_msg)

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

    async def cleanup(self, guild):
        """Limpa o player quando o bot sai do servidor"""
        try:
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
        ("!tocar <URL/termo>", "Toca uma música do YouTube ou busca por termo"),
        ("!conectar", "Conecta o bot ao canal de voz atual"),
        ("!parar", "Para a reprodução e limpa a fila"),
        ("!pausar", "Pausa a música atual"),
        ("!continuar", "Continua a música pausada"),
        ("!volume <0-100>", "Ajusta o volume do player"),
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
