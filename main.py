import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random
from datetime import datetime
import json
import os
import asyncio

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
        self.timer_task = None
        self.join_time_started = False
        
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
    with open('player_stats.json', 'w') as f:
        data = {str(k): v.to_dict() for k, v in player_stats.items()}
        json.dump(data, f, indent=2)

def get_or_create_stats(user_id, name):
    if user_id not in player_stats:
        player_stats[user_id] = PlayerStats(user_id, name)
    return player_stats[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Only works in group"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            "❌ This bot only works in groups!\n\n"
            "Please add me to a group and use /newgame there."
        )
        return
    
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        f"🎮 Welcome to the Mafia Game Bot!\n\n"
        f"Use /newgame to start a game in this group.",
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

async def auto_start_game(context: ContextTypes.DEFAULT_TYPE, group_id, game):
    """Auto start game after 10 seconds"""
    await asyncio.sleep(10)
    
    if group_id in games and games[group_id].state == GAME_WAITING:
        game = games[group_id]
        
        if len(game.players) < 4:
            await context.bot.send_message(
                group_id,
                f"❌ Not enough players! Only {len(game.players)} joined.\n"
                f"Game cancelled. Use /newgame to try again."
            )
            del games[group_id]
            return
        
        # Start the game
        if game.start_game():
            await context.bot.send_message(
                group_id,
                "🎮 <b>GAME STARTED!</b>\n\n"
                "🌙 Night has fallen...\n"
                "Roles are being assigned...\n\n"
                "Check your private messages!",
                parse_mode='HTML'
            )
            
            # Send roles to each player in private
            for user_id, player in game.players.items():
                role = player['role']
                role_description = get_role_description(role)
                stats = get_or_create_stats(user_id, player['name'])
                stats.next_role = role
                stats.total_games += 1
                
                try:
                    await context.bot.send_message(
                        user_id,
                        f"🎭 <b>YOUR ROLE: {role}</b>\n\n"
                        f"{role_description}\n\n"
                        f"Group में voting के लिए private में vote करो!",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Could not send message to {user_id}: {e}")
            
            save_player_stats()

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new game in the group"""
    # Only work in groups
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            "❌ /newgame only works in groups!\n"
            "Please add me to a group first."
        )
        return
    
    group_id = update.effective_chat.id
    
    if group_id in games and games[group_id].state == GAME_WAITING:
        await update.message.reply_text("⏳ A game is already waiting for players!")
        return
    
    if group_id in games and games[group_id].state != GAME_ENDED:
        await update.message.reply_text("❌ A game is already running in this group!")
        return
    
    games[group_id] = MafiaGame(group_id)
    game = games[group_id]
    
    keyboard = [
        [InlineKeyboardButton("✅ Join Game", callback_data='join_game')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 <b>New Mafia Game!</b>\n\n"
        "⏱️ <b>10 seconds to join!</b>\n\n"
        "Click the button below to join.\n"
        "Minimum 4 players required.\n\n"
        "Game will auto-start after 10 seconds!",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    # Start auto-start timer
    game.join_time_started = True
    context.application.create_task(auto_start_game(context, group_id, game))

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join the game"""
    group_id = update.effective_chat.id
    user = update.effective_user
    query = update.callback_query
    
    if group_id not in games:
        await query.answer("❌ No game found!")
        return
    
    game = games[group_id]
    
    if game.state != GAME_WAITING:
        await query.answer("❌ Game has already started!")
        return
    
    stats = get_or_create_stats(user.id, user.first_name)
    
    if game.add_player(user.id, user.first_name):
        player_count = len(game.players)
        await query.answer(f"✅ Joined! ({player_count} players)")
        await context.bot.send_message(
            group_id,
            f"✅ {user.first_name} joined the game!\n"
            f"<b>Players: {player_count}/∞</b>\n\n"
            f"⏱️ Game starts in 10 seconds...",
            parse_mode='HTML'
        )
    else:
        await query.answer("⚠️ You already joined!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show game status"""
    # Only work in groups
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Use /status in group only!")
        return
    
    group_id = update.effective_chat.id
    
    if group_id not in games:
        await update.message.reply_text("❌ No game found!")
        return
    
    game = games[group_id]
    
    status_text = f"📊 <b>Game Status</b>\n\n"
    status_text += f"<b>State:</b> {game.state}\n"
    status_text += f"<b>Day:</b> {game.day_count}, <b>Night:</b> {game.night_count}\n\n"
    status_text += f"👥 <b>Players ({len(game.players)}):</b>\n"
    
    for user_id, player in game.players.items():
        status_emoji = "✅" if player['alive'] else "💀"
        role_text = f" - {player['role']}" if game.state == GAME_ENDED else ""
        status_text += f"{status_emoji} {player['name']}{role_text}\n"
    
    await update.message.reply_text(status_text, parse_mode='HTML')

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
        'Detective': '🕵️ <b>Detective</b> - Find and vote out Mafia members.',
        'Sergeant': '👮 <b>Sergeant</b> - Help Detective. Replace if Detective dies.',
        'Mayor': '🎖️ <b>Mayor</b> - Your vote counts as 2 votes.',
        'Doctor': '👨‍⚕️ <b>Doctor</b> - Protect players at night. Can protect yourself once.',
        'Mafia': '🤵 <b>Mafia</b> - Kill players at night with Don.',
        'Don': '🤵 <b>Don</b> - Mafia leader. Decide who to kill at night.',
        'Lawyer': '👨‍💼 <b>Lawyer</b> - Protect Mafia. Make Detective see false roles.',
        'Killer': '🕴️ <b>Killer</b> - Mafia\'s assassin. Kill at night.',
        'Maniac': '🔪 <b>Maniac</b> - Kill everyone. Win alone.',
        'Werewolf': '🐺 <b>Werewolf</b> - Conditional roles.',
        'Arsonist': '🧟 <b>Arsonist</b> - Kill 3+ players to win.',
        'Mage': '🧙 <b>Mage</b> - Kill or forgive attackers.',
        'Crook': '🤹 <b>Crook</b> - Use others\' names in voting.',
        'Snitch': '🤓 <b>Snitch</b> - Match Detective to reveal roles.',
        'Hooker': '💃 <b>Hooker</b> - Block Killer at night.',
        'Hobo': '🧙 <b>Hobo</b> - Witness murders at night.',
        'Citizen': '👨 <b>Citizen</b> - Regular player.',
        'Lucky': '🤞 <b>Lucky</b> - 50% survive assassination.',
        'Suicide': '🤦 <b>Suicide</b> - Win if voted out in day.',
        'Kamikaze': '💣 <b>Kamikaze</b> - Take enemy with you.',
        'Journalist': '👩‍💻 <b>Journalist</b> - Mafia\'s spy. Find threats.',
    }
    return descriptions.get(role, 'Unknown role')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "📖 <b>Mafia Game Bot - Commands</b>\n\n"
        "<b>Group Commands:</b>\n"
        "/newgame - Create new game (10 sec to join)\n"
        "/status - Check game status\n\n"
        "<b>Private Commands:</b>\n"
        "/start - Start bot\n"
        "/profile - View your stats\n"
        "/store - Buy items\n\n"
        "<b>How to Play:</b>\n"
        "1. /newgame in group\n"
        "2. Click 'Join Game' (10 seconds)\n"
        "3. Game auto-starts\n"
        "4. Receive role in private\n"
        "5. Vote in private, game in group!"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

def main():
    """Start the bot"""
    from dotenv import load_dotenv
    
    load_dotenv()
    TOKEN = os.getenv('BOT_TOKEN')
    
    # Load player stats
    load_player_stats()
    
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("store", store))
    application.add_handler(CommandHandler("newgame", newgame))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(join_game, pattern='join_game'))
    application.add_handler(CallbackQueryHandler(handle_store_callback, pattern='^(buy_|item_)'))
    
    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
