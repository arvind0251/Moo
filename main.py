import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random
from datetime import datetime
import json
import os

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

class PlayerStats:
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name
        self.dollar = 0
        self.brilliant = 0
        self.protection = 0
        self.killer_protection = 0
        self.vote_shield = 0
        self.rifle = 0
        self.mask = 0
        self.documents = 0
        self.winning_score = 0
        self.total_games = 0
        self.next_role = None
        self.wins = 0
        
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'dollar': self.dollar,
            'brilliant': self.brilliant,
            'protection': self.protection,
            'killer_protection': self.killer_protection,
            'vote_shield': self.vote_shield,
            'rifle': self.rifle,
            'mask': self.mask,
            'documents': self.documents,
            'winning_score': self.winning_score,
            'total_games': self.total_games,
            'next_role': self.next_role,
            'wins': self.wins,
        }
    
    @staticmethod
    def from_dict(data):
        stats = PlayerStats(data['user_id'], data['name'])
        stats.dollar = data.get('dollar', 0)
        stats.brilliant = data.get('brilliant', 0)
        stats.protection = data.get('protection', 0)
        stats.killer_protection = data.get('killer_protection', 0)
        stats.vote_shield = data.get('vote_shield', 0)
        stats.rifle = data.get('rifle', 0)
        stats.mask = data.get('mask', 0)
        stats.documents = data.get('documents', 0)
        stats.winning_score = data.get('winning_score', 0)
        stats.total_games = data.get('total_games', 0)
        stats.next_role = data.get('next_role', None)
        stats.wins = data.get('wins', 0)
        return stats

class MafiaGame:
    def __init__(self, group_id):
        self.group_id = group_id
        self.state = GAME_WAITING
        self.players = {}
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

# Global storage
games = {}
player_stats = {}

def load_player_stats():
    """Load player stats from file"""
    global player_stats
    if os.path.exists('player_stats.json'):
        try:
            with open('player_stats.json', 'r') as f:
                data = json.load(f)
                player_stats = {int(k): PlayerStats.from_dict(v) for k, v in data.items()}
        except:
            player_stats = {}
    else:
        player_stats = {}

def save_player_stats():
    """Save player stats to file"""
    with open('player_stats.json', 'w') as f:
        data = {str(k): v.to_dict() for k, v in player_stats.items()}
        json.dump(data, f, indent=2)

def get_or_create_stats(user_id, name):
    """Get or create player stats"""
    if user_id not in player_stats:
        player_stats[user_id] = PlayerStats(user_id, name)
    return player_stats[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        f"🎮 Welcome to the Mafia Game Bot!\n\n"
        f"Create a new group, add me to it, and use /newgame to start.",
        parse_mode='HTML'
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show player profile and stats"""
    user = update.effective_user
    stats = get_or_create_stats(user.id, user.first_name)
    
    profile_text = (
        f"👤 <b>Profile: {stats.name}</b>\n\n"
        f"⭐ ID: {stats.user_id}\n\n"
        f"💰 Dollar: {stats.dollar}\n"
        f"💎 Brilliant: {stats.brilliant}\n\n"
        f"🛡️ Protection: {stats.protection}\n"
        f"🔴 Killer protection: {stats.killer_protection}\n"
        f"⚖️ Vote shield: {stats.vote_shield}\n"
        f"🔫 Rifle: {stats.rifle}\n\n"
        f"🎭 Mask: {stats.mask}\n"
        f"📄 Documents: {stats.documents}\n\n"
        f"🎯 Your role in next game: {stats.next_role or '-'}\n\n"
        f"🏆 Winning score: {stats.winning_score}\n"
        f"🎲 Total games: {stats.total_games}\n"
        f"✅ Wins: {stats.wins}"
    )
    
    await update.message.reply_text(profile_text, parse_mode='HTML')

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
    
    stats = get_or_create_stats(user.id, user.first_name)
    
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
        
        for user_id, player in game.players.items():
            role = player['role']
            role_description = get_role_description(role)
            stats = get_or_create_stats(user_id, player['name'])
            stats.next_role = role
            
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

async def buy_diamond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buy diamond"""
    user = update.effective_user
    stats = get_or_create_stats(user.id, user.first_name)
    
    await update.message.reply_text(
        "💎 <b>Buy Diamond</b>\n\n"
        "Choose amount:",
        parse_mode='HTML'
    )

async def store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open store"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("💰 Buy Dollar", callback_data='buy_dollar'),
         InlineKeyboardButton("💎 Buy Diamond", callback_data='buy_diamond')],
        [InlineKeyboardButton("🛡️ Protection", callback_data='item_protection')],
        [InlineKeyboardButton("🔴 Killer Protection", callback_data='item_killer_protection')],
        [InlineKeyboardButton("⚖️ Vote Shield", callback_data='item_vote_shield')],
        [InlineKeyboardButton("🔫 Rifle", callback_data='item_rifle')],
        [InlineKeyboardButton("🎭 Mask", callback_data='item_mask')],
        [InlineKeyboardButton("📄 Documents", callback_data='item_documents')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏪 <b>Store</b>\n\n"
        "Choose what to buy:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_store_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle store callbacks"""
    user = update.effective_user
    stats = get_or_create_stats(user.id, user.first_name)
    query = update.callback_query
    
    if query.data == 'buy_dollar':
        stats.dollar += 30
        await query.answer("✅ Bought $30!")
    elif query.data == 'buy_diamond':
        stats.brilliant += 5
        await query.answer("✅ Bought 5 Diamonds!")
    elif query.data == 'item_protection':
        if stats.dollar >= 50:
            stats.dollar -= 50
            stats.protection += 1
            await query.answer("✅ Bought Protection!")
        else:
            await query.answer("❌ Not enough dollars!")
    elif query.data == 'item_killer_protection':
        if stats.dollar >= 75:
            stats.dollar -= 75
            stats.killer_protection += 1
            await query.answer("✅ Bought Killer Protection!")
        else:
            await query.answer("❌ Not enough dollars!")
    elif query.data == 'item_vote_shield':
        if stats.dollar >= 60:
            stats.dollar -= 60
            stats.vote_shield += 1
            await query.answer("✅ Bought Vote Shield!")
        else:
            await query.answer("❌ Not enough dollars!")
    elif query.data == 'item_rifle':
        if stats.dollar >= 100:
            stats.dollar -= 100
            stats.rifle += 1
            await query.answer("✅ Bought Rifle!")
        else:
            await query.answer("❌ Not enough dollars!")
    elif query.data == 'item_mask':
        if stats.dollar >= 40:
            stats.dollar -= 40
            stats.mask += 1
            await query.answer("✅ Bought Mask!")
        else:
            await query.answer("❌ Not enough dollars!")
    elif query.data == 'item_documents':
        if stats.dollar >= 80:
            stats.dollar -= 80
            stats.documents += 1
            await query.answer("✅ Bought Documents!")
        else:
            await query.answer("❌ Not enough dollars!")
    
    save_player_stats()

def get_role_description(role):
    """Get role description"""
    descriptions = {
        'Detective': '🕵️ Detective - The city\'s main protector. Find and eliminate Mafia members.',
        'Sergeant': '👮 Sergeant - Help the Detective. If Detective dies, take their place.',
        'Mayor': '🎖️ Mayor - You are the Mayor! Your vote equals 2 votes.',
        'Doctor': '👨‍⚕️ Doctor - Protect the Detective. Can heal yourself once.',
        'Mafia': '🤵 Mafia - Mafia group member. Decide who to kill at night.',
        'Don': '🤵 Don - Mafia group leader. Lead your group to victory.',
        'Lawyer': '👨‍💼 Lawyer - Protect Mafia. Make Detective see false information.',
        'Killer': '🕴️ Killer - Mafia\'s assassin. Kill anyone you choose.',
        'Maniac': '🔪 Maniac - Kill everyone around.',
        'Werewolf': '🐺 Werewolf - Play by your own rules.',
        'Arsonist': '🧟 Arsonist - Set fires. Kill 3+ players to win.',
        'Mage': '🧙 Mage - Live by your own laws.',
        'Crook': '🤹 Crook - Free role. Use others\' names.',
        'Snitch': '🤓 Snitch - Check same player as Detective.',
        'Hooker': '💃 Hooker - Block the Killer at night.',
        'Hobo': '🧙 Hobo - Get a bottle and witness murders.',
        'Citizen': '👨 Citizen - Regular civilian.',
        'Lucky': '🤞 Lucky - 50% chance to survive.',
        'Suicide': '🤦 Suicide - Win if lynched in day.',
        'Kamikaze': '💣 Kamikaze - Take enemy with you.',
        'Journalist': '👩‍💻 Journalist - Mafia\'s spy.',
    }
    return descriptions.get(role, 'Unknown role')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "📖 <b>Mafia Game Bot - Commands</b>\n\n"
        "/start - Start the bot\n"
        "/profile - Show your profile and stats\n"
        "/store - Buy items and upgrades\n"
        "/newgame - Create new game\n"
        "/startgame - Start game (4+ players)\n"
        "/status - Check game status\n"
        "/help - Show this message\n\n"
        "<b>How to Play:</b>\n"
        "1. Use /newgame\n"
        "2. Click 'Join Game'\n"
        "3. Use /startgame\n"
        "4. Play according to your role!"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

def main():
    """Start the bot"""
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # Load player stats
    load_player_stats()
    
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("store", store))
    application.add_handler(CommandHandler("newgame", newgame))
    application.add_handler(CommandHandler("startgame", startgame))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(join_game, pattern='join_game'))
    application.add_handler(CallbackQueryHandler(handle_store_callback, pattern='^(buy_|item_)'))
    
    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
