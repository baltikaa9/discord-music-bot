import random

from disnake import ApplicationCommandInteraction, Member, VoiceState, MessageInteraction
from disnake.ext import commands

from config import BOT_DS_ID
from services.music import MusicService


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

        self.music_services: dict[int, MusicService] = {}

        # self.music_service: MusicService = MusicService(bot)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if member.guild.id not in self.music_services:
            self.music_services[member.guild.id] = MusicService(self.bot)
        if (self.music_services[member.guild.id].vc and before.channel
                and before.channel.id == self.music_services[member.guild.id].vc.channel.id and len(before.channel.members) == 1):
            self.music_services[member.guild.id].music_queue = []
            await self.music_services[member.guild.id].vc.disconnect()

        if member.id == BOT_DS_ID and before.channel and not after.channel:
            self.music_services[member.guild.id].music_queue = []
            await self.music_services[member.guild.id].vc.disconnect(force=True)

    @commands.Cog.listener()
    async def on_button_click(self, inter: MessageInteraction):
        match inter.component.custom_id:
            case 'pause':
                await self.pause(inter)
            case 'stop':
                await self.stop(inter)
            case 'skip':
                await self.skip(inter)
            case 'shuffle':
                await self.shuffle_queue(inter)
            case 'queue':
                await self.get_queue(inter)
            case _:
                return

    @commands.slash_command(description='Add a song from URL or search to queue')
    async def play(
            self, inter: ApplicationCommandInteraction,
            query: str = commands.Param(description='The query to search')
    ):
        if inter.guild_id not in self.music_services:
            self.music_services[inter.guild_id] = MusicService(self.bot)
        await self.music_services[inter.guild_id].add_music_to_queue_and_play(inter, query, 'bottom')

    @commands.slash_command(description='Add a song from URL or search to the top on queue')
    async def playnext(
            self, inter: ApplicationCommandInteraction,
            query: str = commands.Param(description='The query to search')
    ):
        if inter.guild_id not in self.music_services:
            self.music_services[inter.guild_id] = MusicService(self.bot)
        await self.music_services[inter.guild_id].add_music_to_queue_and_play(inter, query, 'top')

    @commands.slash_command(description='Pause/resume the currently playing song')
    async def pause(self, inter: ApplicationCommandInteraction | MessageInteraction):
        if inter.guild_id not in self.music_services:
            self.music_services[inter.guild_id] = MusicService(self.bot)
        if not self.music_services[inter.guild_id].vc:
            await inter.send(
                content="There's no music currently playing, add some music with the `/play` command",
                ephemeral=True
            )
            return

        if not self.music_services[inter.guild_id].vc.is_paused():
            self.music_services[inter.guild_id].vc.pause()
            await inter.send('Current music has been paused')
        else:
            self.music_services[inter.guild_id].vc.resume()
            await inter.send('Current music has been resumed')

    @commands.slash_command(description='Stop the currently playing song')
    async def stop(self, inter: ApplicationCommandInteraction | MessageInteraction):
        if inter.guild_id not in self.music_services:
            self.music_services[inter.guild_id] = MusicService(self.bot)
        if self.music_services[inter.guild_id].vc:
            self.music_services[inter.guild_id].music_queue = []
            await self.music_services[inter.guild_id].vc.disconnect()
            await inter.send('Bot has been disconnected', ephemeral=True)
        else:
            await inter.send('Bot already disconnected', ephemeral=True)

    @commands.slash_command(description='Skip the currently playing song')
    async def skip(self, inter: ApplicationCommandInteraction | MessageInteraction):
        if inter.guild_id not in self.music_services:
            self.music_services[inter.guild_id] = MusicService(self.bot)
        if self.music_services[inter.guild_id].vc and self.music_services[inter.guild_id].vc.is_playing():
            self.music_services[inter.guild_id].vc.stop()

            if self.music_services[inter.guild_id].music_queue:
                await inter.send('Current music has been skipped')
            else:
                await inter.send('Current music has been skipped. Queue is empty')
                await self.music_services[inter.guild_id].vc.disconnect()
        else:
            await inter.send(
                content="There's no music currently playing, add some music with the `/play` command",
                ephemeral=True
            )

    @commands.slash_command(name='queue', description='Show a music queue')
    async def get_queue(self, inter: ApplicationCommandInteraction):
        if inter.guild_id not in self.music_services:
            self.music_services[inter.guild_id] = MusicService(self.bot)
        if self.music_services[inter.guild_id].music_queue:
            queue = [str(music) for music in self.music_services[inter.guild_id].music_queue]
            message = '\n'.join(queue)
            await inter.send(f'Music queue:\n{message}')
        else:
            await inter.send('Queue is empty')

    @commands.slash_command(name='shuffle', description='Shuffle the music queue')
    async def shuffle_queue(self, inter: ApplicationCommandInteraction | MessageInteraction):
        if inter.guild_id not in self.music_services:
            self.music_services[inter.guild_id] = MusicService(self.bot)
        random.shuffle(self.music_services[inter.guild_id].music_queue)
        await inter.send(f'The music queue has been shuffled')


    @commands.command()
    async def ping(self, inter):
        if inter.guild_id not in self.music_services:
            self.music_services[inter.guild_id] = MusicService(self.bot)
        if self.music_services[inter.guild_id].vc:
            await inter.send(f'connected: {self.music_services[inter.guild_id].vc.is_connected()}')
