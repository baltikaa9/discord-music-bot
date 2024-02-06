import asyncio
from dataclasses import dataclass, field
from typing import Literal

import disnake.ui
from disnake import VoiceClient, Message, ApplicationCommandInteraction, AudioSource, Embed, Color, FFmpegPCMAudio, \
    VoiceChannel, TextChannel
from disnake.ext.commands import Bot
from disnake.ui import Button
from yt_dlp import YoutubeDL, DownloadError

from config import FFMPEG_OPTIONS, YDL_OPTIONS


@dataclass
class MusicInfo:
    title: str
    author: str
    url: str

    def __repr__(self):
        return f'`{self.title}` by `{self.author}`'


@dataclass
class DsServer:
    music_queue: list[MusicInfo] = field(default_factory=lambda: [])
    vc: VoiceClient | None = None
    player_message: Message | None = None


class MusicService:
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

        # self.ds_servers: dict[int, DsServer] = {}

        self.music_queue: list[MusicInfo] = []
        self.vc: VoiceClient | None = None
        self.player_message: Message | None = None

    async def add_music_to_queue_and_play(
            self, inter: ApplicationCommandInteraction,
            query: str, queue_pos: Literal['top', 'bottom'],
    ) -> None:
        # if inter.guild_id not in self.ds_servers:
        #     self.ds_servers[inter.guild_id] = DsServer()

        if not inter.author.voice:
            await inter.send(f'{inter.author.mention}, connect to a voice channel', ephemeral=True)
            return

        await inter.response.defer()
        music = self.ydl_search(query)

        if music is None:
            await inter.edit_original_response('Music not found. Try a different url')
            return

        await inter.edit_original_response(
            f'{inter.author.mention} | Added `{music.title}` by `{music.author}` in queue')

        connected_to_voice_channel = await self.connect_to_voice_channel(inter.author.voice.channel)

        if not connected_to_voice_channel:
            await inter.edit_original_response("Couldn't connect to the voice channel")
            return

        match queue_pos:
            case 'top':
                self.music_queue.insert(0, music)
            case 'bottom':
                self.music_queue.append(music)

        if not self.vc.is_playing():
            await self.play_music(inter.channel)

    async def play_music(self, text_channel: lambda: TextChannel) -> None:
        if self.player_message:
            await self.player_message.delete()
            self.player_message = None

        if self.music_queue:
            music = self.music_queue.pop(0)

            audio_src: AudioSource = FFmpegPCMAudio(
                source=music.url,
                executable='ffmpeg/ffmpeg.exe',
                **FFMPEG_OPTIONS,
            )

            embed, buttons = await self.create_player(music)
            self.player_message = await text_channel.send(embed=embed, components=buttons)

            self.vc.play(
                audio_src,
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_music(text_channel), self.bot.loop)
            )

    @staticmethod
    async def create_player(music: MusicInfo) -> tuple[Embed, list[Button]]:
        embed = Embed(
            title='Now playing', description=f'`{music.title}` by `{music.author}`',
            color=Color.purple()
        )
        buttons = [
            Button(label="Pause", style=disnake.ButtonStyle.blurple,
                   emoji=disnake.PartialEmoji(name='pause', id=1059394116439515136), custom_id='pause'),
            Button(label="Stop", style=disnake.ButtonStyle.red,
                   emoji=disnake.PartialEmoji(name='stop', id=1053672684820631612), custom_id='stop'),
            Button(label="Skip", style=disnake.ButtonStyle.green,
                   emoji=disnake.PartialEmoji(name='skip', id=1053664978298740776), custom_id='skip'),
            Button(label="Shuffle", style=disnake.ButtonStyle.green,
                   emoji=disnake.PartialEmoji(name='shuffle', id=1065366332108976238), custom_id='shuffle'),
            Button(label="Queue", style=disnake.ButtonStyle.grey,
                   emoji='📃', custom_id='queue'),
        ]
        return embed, buttons

    async def connect_to_voice_channel(self, author_voice_channel: VoiceChannel) -> bool:
        if not self.vc or not self.vc.is_connected():
            self.vc: VoiceClient = await author_voice_channel.connect()

            if not self.vc:
                return False
        elif self.vc.channel != author_voice_channel:
            await self.vc.move_to(author_voice_channel)
        return True

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

    # TODO: make addition to my music as vk (use MongoDB - {<guild_id>: list[<music_name>/MusicInfo])
