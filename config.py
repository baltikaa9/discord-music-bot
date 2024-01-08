from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('TOKEN')

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'simulate': 'True',
    'key': 'FFmpegExtractAudio',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}
