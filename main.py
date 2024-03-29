import disnake
from disnake.ext import commands

from cogs.music import MusicCog
from config import TOKEN

bot = commands.Bot(command_prefix='/', activity=disnake.Game(name='попе пальчиком'), help_command=None, intents=disnake.Intents.all(), reload=True)

bot.add_cog(MusicCog(bot))


@bot.event
async def on_ready():
    print(f'bot {bot.user} is ready')


if __name__ == '__main__':
    bot.run(TOKEN)
