import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

MIN_PLAYERS = 4
MAX_PLAYERS = 20
NIGHT_DURATION = 60
DAY_DURATION = 120

ROLE_CONFIG = {
    'civilian_ratio': 0.6,
    'mafia_ratio': 0.25,
    'individual_ratio': 0.15,
}
