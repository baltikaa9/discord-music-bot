from disnake import ApplicationCommandInteraction, Member, VoiceState
from disnake.ext import commands

from services.music import MusicService


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

        self.music_service: MusicService = MusicService(bot)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if (self.music_service.vc and before.channel
                and before.channel.id == self.music_service.vc.channel.id and len(before.channel.members) == 1):
            self.music_service.music_queue = []
            await self.music_service.vc.disconnect()

    @commands.slash_command(description='Add a song from URL or search to queue')
    async def play(
            self, inter: ApplicationCommandInteraction,
            query: str = commands.Param(description='The query to search')
    ):
        await self.music_service.add_music_to_queue_and_play(inter, query, 'bottom')

    @commands.slash_command(description='Add a song from URL or search to the top on queue')
    async def playnext(
            self, inter: ApplicationCommandInteraction,
            query: str = commands.Param(description='The query to search')
    ):
        await self.music_service.add_music_to_queue_and_play(inter, query, 'top')

    @commands.slash_command(description='Pause/resume the currently playing song')
    async def pause(self, inter: ApplicationCommandInteraction):
        if not self.music_service.vc:
            await inter.send(
                content="There's no music currently playing, add some music with the `/play` command",
                ephemeral=True
            )
            return

        if not self.music_service.vc.is_paused():
            self.music_service.vc.pause()
            await inter.send('Current music has been paused')
        else:
            self.music_service.vc.resume()
            await inter.send('Current music has been resumed')

    @commands.slash_command(description='Stop the currently playing song')
    async def stop(self, inter: ApplicationCommandInteraction):
        if self.music_service.vc:
            self.music_service.music_queue = []
            await self.music_service.vc.disconnect()
            await inter.send('Bot has been disconnected', ephemeral=True)
        else:
            await inter.send('Bot already disconnected', ephemeral=True)

    @commands.slash_command(description='Skip the currently playing song')
    async def skip(self, inter: ApplicationCommandInteraction):
        if self.music_service.vc and self.music_service.vc.is_playing():
            self.music_service.vc.stop()

            if self.music_service.music_queue:
                await inter.send('Current music has been skipped')
            else:
                await inter.send('Current music has been skipped. Queue is empty')
        else:
            await inter.send(
                content="There's no music currently playing, add some music with the `/play` command",
                ephemeral=True
            )

    @commands.slash_command(name='queue', description='Show a music queue')
    async def get_queue(self, inter: ApplicationCommandInteraction):
        if self.music_service.music_queue:
            queue = [str(music) for music in self.music_service.music_queue]
            message = '\n'.join(queue)
            await inter.send(f'Music queue:\n{message}')
        else:
            await inter.send('Queue is empty')
