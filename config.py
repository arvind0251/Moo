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

# Store settings
STORE_ITEMS = {
    'dollar': {'price': 30, 'name': '💰 Dollar'},
    'diamond': {'price': 5, 'name': '💎 Diamond'},
    'protection': {'price': 50, 'name': '🛡️ Protection'},
    'killer_protection': {'price': 75, 'name': '🔴 Killer Protection'},
    'vote_shield': {'price': 60, 'name': '⚖️ Vote Shield'},
    'rifle': {'price': 100, 'name': '🔫 Rifle'},
    'mask': {'price': 40, 'name': '🎭 Mask'},
    'documents': {'price': 80, 'name': '📄 Documents'},
}
