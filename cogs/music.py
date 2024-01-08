import asyncio
from dataclasses import dataclass

import disnake
from disnake.ext import commands
from disnake import ApplicationCommandInteraction, VoiceClient, AudioSource, Member, VoiceState
from yt_dlp import YoutubeDL, DownloadError

from config import YDL_OPTIONS, FFMPEG_OPTIONS


@dataclass
class MusicInfo:
    title: str
    author: str
    url: str

    def __repr__(self):
        return f'`{self.title}` by `{self.author}`'


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

        # self.is_playing: bool = False
        # self.is_paused: bool = False

        self.music_queue: list[MusicInfo] = []
        self.vc: VoiceClient | None = None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if self.vc and before.channel and before.channel.id == self.vc.channel.id and len(before.channel.members) == 1:
            self.music_queue = []
            await self.vc.disconnect()
            # self.is_playing = False
            # self.is_paused = False

    @commands.slash_command(description='Add a song from URL or search to queue')
    async def play(self, inter: ApplicationCommandInteraction,
                   query: str = commands.Param(description='The query to search')):
        music = await self._play_prepare(inter, query)

        if music:
            self.music_queue.append(music)

            if not self.vc.is_playing():
                await self.play_music(inter)

    @commands.slash_command(description='Add a song from URL or search to the top on queue')
    async def playnext(self, inter: ApplicationCommandInteraction,
                       query: str = commands.Param(description='The query to search')):
        music = await self._play_prepare(inter, query)

        if music:
            self.music_queue.insert(0, music)

            if not self.vc.is_playing():
                await self.play_music(inter)

    async def _play_prepare(self, inter: ApplicationCommandInteraction, query: str) -> MusicInfo | None:
        if not inter.author.voice:
            await inter.send(f'{inter.author.mention}, connect to a voice channel', ephemeral=True)
            return
        # elif self.vc and self.vc.is_paused():
        #     self.vc.resume()
        # self.is_paused = False

        await inter.response.defer()

        music = self.ydl_search(query)
        if music is None:
            await inter.edit_original_response('Music not found. Try a different url')
            return
        # self.music_queue.append(music)

        await inter.edit_original_response(
            f'{inter.author.mention} | Added `{music.title}` by `{music.author}` in queue')

        await self.connect_to_voice_channel(inter)
        return music

    @commands.slash_command(description='Pause/resume the currently playing song')
    async def pause(self, inter: ApplicationCommandInteraction):
        # if self.vc and self.vc.is_playing():
        if not self.vc:
            await inter.send("There's no music currently playing, add some music with the `/play` command",
                             ephemeral=True)
            return

        if not self.vc.is_paused():
            self.vc.pause()
            # self.is_paused = True
            await inter.send('Current music has been paused')
        else:
            self.vc.resume()
            # self.is_paused = False
            await inter.send('Current music has been resumed')
        # else:
        #     await inter.send("There's no music currently playing, add some music with the `/play` command",
        #                      ephemeral=True)

    @commands.slash_command(description='Stop the currently playing song')
    async def stop(self, inter: ApplicationCommandInteraction):
        if self.vc:
            self.music_queue = []
            await self.vc.disconnect()
            # self.is_playing = False
            # self.is_paused = False
            await inter.send('Bot has been disconnected', ephemeral=True)
        else:
            await inter.send('Bot already disconnected', ephemeral=True)

    @commands.slash_command(description='Skip the currently playing song')
    async def skip(self, inter: ApplicationCommandInteraction):
        if self.vc and self.vc.is_playing():
            self.vc.stop()
            if self.music_queue:
                await inter.send('Current music has been skipped. '
                                 f'Now playing `{self.music_queue[0].title}` by `{self.music_queue[0].author}`')
            else:
                await inter.send('Current music has been skipped. Queue is empty')
        else:
            await inter.send("There's no music currently playing, add some music with the `/play` command",
                             ephemeral=True)

    @commands.slash_command(name='queue', description='Show a music queue')
    async def get_queue(self, inter: ApplicationCommandInteraction):
        if len(self.music_queue):
            queue = [str(music) for music in self.music_queue]
            message = '\n'.join(queue)
            await inter.send(f'Music queue:\n{message}')
        else:
            await inter.send('Queue is empty')

    async def play_music(self, inter: ApplicationCommandInteraction) -> None:
        if self.music_queue:
            music = self.music_queue.pop(0)

            audio_src: AudioSource = disnake.FFmpegPCMAudio(
                executable='ffmpeg/ffmpeg.exe',
                source=music.url,
                **FFMPEG_OPTIONS,
            )

            embed = disnake.Embed(title='Now playing', description=f'`{music.title}` by `{music.author}`', color=disnake.Color.purple())
            await inter.send(embed=embed)

            self.vc.play(audio_src, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_music(inter), self.bot.loop))

        #     self.is_playing = True
        # else:
        #     self.is_playing = False

    async def connect_to_voice_channel(self, inter: ApplicationCommandInteraction) -> None:
        if not self.vc or not self.vc.is_connected():
            self.vc: VoiceClient = await inter.author.voice.channel.connect()

            if not self.vc:
                await inter.send("Couldn't connect to the voice channel", ephemeral=True)
                return
        elif self.vc.channel != inter.author.voice.channel:
            await self.vc.move_to(inter.author.voice.channel)
        else:
            return

    # def play_next(self, error=None):
    #     if self.music_queue:
    #         audio_src: AudioSource = disnake.FFmpegPCMAudio(
    #             executable='ffmpeg/ffmpeg.exe',
    #             source=self.music_queue.pop(0).url,
    #             **FFMPEGOPTIONS,
    #         )
    #
    #         self.vc.play(audio_src, after=self.play_next)
    #     self.is_playing = True
    # else:
    #     self.is_playing = False

    @staticmethod
    def ydl_search(query: str) -> MusicInfo | None:
        with YoutubeDL(YDL_OPTIONS) as ydl:
            if query.startswith('https://'):
                try:
                    info = ydl.extract_info(query, download=False)
                except DownloadError:
                    info = None
            else:
                info = ydl.extract_info(f'ytsearch:{query}', download=False)['entries'][0]

        if info:
            return MusicInfo(title=info['title'], author=info['channel'], url=info['url'])
        else:
            return
