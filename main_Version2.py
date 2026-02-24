import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Game states
GAME_WAITING = 'waiting'
GAME_RUNNING = 'running'
GAME_NIGHT = 'night'
GAME_DAY = 'day'
GAME_ENDED = 'ended'

# Roles
CIVILIAN_ROLES = ['Detective', 'Sergeant', 'Mayor', 'Doctor', 'Hooker', 'Hobo', 'Citizen', 'Lucky', 'Suicide', 'Kamikaze']
MAFIA_ROLES = ['Don', 'Mafia', 'Lawyer', 'Killer', 'Journalist']
INDIVIDUAL_ROLES = ['Maniac', 'Werewolf', 'Arsonist', 'Mage', 'Crook', 'Snitch']

ALL_ROLES = CIVILIAN_ROLES + MAFIA_ROLES + INDIVIDUAL_ROLES

class MafiaGame:
    def __init__(self, group_id):
        self.group_id = group_id
        self.state = GAME_WAITING
        self.players = {}  # {user_id: {'name': str, 'role': str, 'alive': bool}}
        self.mafia_players = []
        self.day_count = 0
        self.night_count = 0
        self.voted_out = None
        self.killed_at_night = None
        
    def add_player(self, user_id, name):
        if user_id not in self.players:
            self.players[user_id] = {
                'name': name,
                'role': None,
                'alive': True,
                'user_id': user_id
            }
            return True
        return False
    
    def remove_player(self, user_id):
        if user_id in self.players:
            del self.players[user_id]
            return True
        return False
    
    def assign_roles(self):
        """Assign random roles to all players"""
        if len(self.players) < 4:
            return False
        
        available_roles = ALL_ROLES.copy()
        random.shuffle(available_roles)
        
        for i, (user_id, player) in enumerate(self.players.items()):
            if i < len(available_roles):
                player['role'] = available_roles[i]
                if player['role'] in MAFIA_ROLES:
                    self.mafia_players.append(user_id)
        
        return True
    
    def get_alive_players(self):
        return {uid: p for uid, p in self.players.items() if p['alive']}
    
    def get_alive_mafia(self):
        return [uid for uid in self.mafia_players if self.players[uid]['alive']]
    
    def get_alive_civilians(self):
        alive = self.get_alive_players()
        return {uid: p for uid, p in alive.items() if uid not in self.mafia_players}
    
    def start_game(self):
        if self.assign_roles():
            self.state = GAME_NIGHT
            self.night_count = 1
            return True
        return False
    
    def end_game(self):
        self.state = GAME_ENDED
        return True

# Global games storage
games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        f"🎮 Welcome to the Mafia Game Bot!\n\n"
        f"Create a new group, add me to it, and use /newgame to start.",
        parse_mode='HTML'
    )

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new game in the group"""
    group_id = update.effective_chat.id
    
    if group_id in games:
        await update.message.reply_text("❌ A game is already running in this group!")
        return
    
    games[group_id] = MafiaGame(group_id)
    
    keyboard = [
        [InlineKeyboardButton("✅ Join Game", callback_data='join_game')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 New Mafia Game Started!\n\n"
        "Players, click the button below to join.\n"
        "Minimum 4 players required.\n\n"
        "Once all players join, use /startgame to begin.",
        reply_markup=reply_markup
    )

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join the game"""
    group_id = update.effective_chat.id
    user = update.effective_user
    
    if group_id not in games:
        await update.callback_query.answer("❌ No game found!")
        return
    
    game = games[group_id]
    
    if game.state != GAME_WAITING:
        await update.callback_query.answer("❌ Game has already started!")
        return
    
    if game.add_player(user.id, user.first_name):
        player_count = len(game.players)
        await update.callback_query.answer(f"✅ Joined the game! ({player_count} players)")
        await context.bot.send_message(
            group_id,
            f"✅ {user.first_name} joined the game!\n"
            f"Total players: {player_count}"
        )
    else:
        await update.callback_query.answer("⚠️ You have already joined!")

async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the game"""
    group_id = update.effective_chat.id
    
    if group_id not in games:
        await update.message.reply_text("❌ No game found!")
        return
    
    game = games[group_id]
    
    if len(game.players) < 4:
        await update.message.reply_text(
            f"❌ Minimum 4 players required!\n"
            f"Current players: {len(game.players)}"
        )
        return
    
    if game.start_game():
        await context.bot.send_message(
            group_id,
            "🎮 Game Started!\n\n"
            "🌙 Night has fallen - Mafia will choose their target...\n"
            "Role messages are being sent to all players."
        )
        
        # Send roles to each player
        for user_id, player in game.players.items():
            role = player['role']
            role_description = get_role_description(role)
            try:
                await context.bot.send_message(
                    user_id,
                    f"🎭 Your Role: <b>{role}</b>\n\n"
                    f"{role_description}",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Could not send message to {user_id}: {e}")
    else:
        await update.message.reply_text("❌ Could not start game!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show game status"""
    group_id = update.effective_chat.id
    
    if group_id not in games:
        await update.message.reply_text("❌ No game found!")
        return
    
    game = games[group_id]
    
    status_text = f"📊 Game Status\n\n"
    status_text += f"State: {game.state}\n"
    status_text += f"Day: {game.day_count}, Night: {game.night_count}\n\n"
    status_text += f"👥 Players ({len(game.players)}):\n"
    
    for user_id, player in game.players.items():
        status_emoji = "✅" if player['alive'] else "💀"
        role_text = f" - {player['role']}" if game.state == GAME_ENDED else ""
        status_text += f"{status_emoji} {player['name']}{role_text}\n"
    
    await update.message.reply_text(status_text)

def get_role_description(role):
    """Get role description"""
    descriptions = {
        'Detective': '🕵️ Detective - The city\'s main protector. Find and eliminate Mafia members during voting.',
        'Sergeant': '👮 Sergeant - Help the Detective. If Detective dies, take their place.',
        'Mayor': '🎖️ Mayor - You are the Mayor! Your vote equals 2 votes during day voting.',
        'Doctor': '👨‍⚕️ Doctor - Protect the Detective when they declare themselves. Can heal yourself once.',
        'Mafia': '🤵 Mafia - Mafia group member. Decide who to eliminate at night.',
        'Don': '🤵 Don - Mafia group leader. Lead your group to victory.',
        'Lawyer': '👨‍💼 Lawyer - Protect the Mafia. Make Detective see false information.',
        'Killer': '🕴️ Killer - Mafia\'s assassin. Kill anyone you choose each night.',
        'Maniac': '🔪 Maniac - Kill everyone around. Win by eliminating all others.',
        'Werewolf': '🐺 Werewolf - Play by your own rules. Become Mafia if killed by Don, Sergeant if killed by Detective.',
        'Arsonist': '🧟 Arsonist - Set fires. Kill 3+ players to win.',
        'Mage': '🧙 Mage - Live by your own laws. Kill or forgive those who try to kill you.',
        'Crook': '🤹 Crook - Free role. Use others\' names in day voting. Survive to win.',
        'Snitch': '🤓 Snitch - Check the same player as Detective on same night. Reveal their role to win.',
        'Hooker': '💃 Hooker - Block the Killer at night. Don\'t visit the Detective intentionally.',
        'Hobo': '🧙 Hobo - Get a bottle and witness murders.',
        'Citizen': '👨 Citizen - Regular civilian. Find and lynch Mafia members.',
        'Lucky': '🤞 Lucky - 50% chance to survive assassination. Win with civilians.',
        'Suicide': '🤦 Suicide - Win if lynched during day. Lose if killed at night.',
        'Kamikaze': '💣 Kamikaze - Take Maniac or Mafia with you. Choose your companion when leaving.',
        'Journalist': '👩‍💻 Journalist - Mafia\'s spy. Find threats to Mafia like Doctor, Hobo, Hooker.',
    }
    return descriptions.get(role, 'Unknown role')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "📖 <b>Mafia Game Bot - Commands</b>\n\n"
        "/start - Start the bot\n"
        "/newgame - Create new game\n"
        "/startgame - Start game (4+ players required)\n"
        "/status - Check game status\n"
        "/help - Show this message\n\n"
        "<b>How to Play:</b>\n"
        "1. Use /newgame\n"
        "2. Let players join with 'Join Game' button\n"
        "3. Use /startgame when ready\n"
        "4. Play according to your role!"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

def main():
    """Start the bot"""
    # Replace with your actual token
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newgame", newgame))
    application.add_handler(CommandHandler("startgame", startgame))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(join_game, pattern='join_game'))
    
    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()