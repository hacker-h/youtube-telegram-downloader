from dotenv import load_dotenv
load_dotenv(dotenv_path='./bot.env')
from backends import overcast_storage

backend = overcast_storage.OvercastStorage()
backend.upload("s1.mp3")
