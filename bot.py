import re
import discord
import asyncio
import aiohttp
import sys
import threading
import uvicorn
from discord import app_commands
from discord.ext import commands
import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta

# ================== КОНФИГ ==================
TOKEN = os.getenv("DISCORD_TOKEN")
# --- Каналы и категории ---
REPORT_CHANNEL_ID = 1231958902474678364
JOIN_CHANNEL_ID = 1551952140929601576
CATEGORY_ID = 1551950227865608292
SHOP_CHANNEL_ID = 1564188124844662814  # ID канала для логов покупок
AUDIT_LOG_CHANNEL_ID = 1567159721398370457  # Канал полного журнала действий
LOGS_DIR = "logs"
LATEST_LOG_FILE = os.path.join(LOGS_DIR, "latest.log")
POVIXA_CHANNEL_ID = 1564557395907186798  # ID канала, где должна работать команда /povixa

# Настройка московского времени (UTC+3)
MSK = timezone(timedelta(hours=3))

# ================== МАГАЗИН ==================
SHOP_ITEMS = {
    "PVP": {"price": 1000, "type": "kit"},
    "CYBER": {"price": 1500, "type": "kit"},
    "RICH": {"price": 2000, "type": "kit"},
    "TOPER": {"price": 2500, "type": "kit"},
    "D.OWNER": {"price": 2300, "type": "kit"},
    "DADMIN": {"price": 1000, "type": "kit"},
    "D.GLMODER": {"price": 900, "type": "kit"},
    "D.STMODER": {"price": 750, "type": "kit"},
    "D.MODER": {"price": 500, "type": "kit"},
    "WHITE": {"price": 5000, "type": "донат"},
    "RABBIT": {"price": 4500, "type": "донат"},
    "DHELPER": {"price": 4500, "type": "донат"},
    "GOD": {"price": 4000, "type": "донат"},
    "ENDER": {"price": 4000, "type": "донат"},
    "DRACULA": {"price": 3500, "type": "донат"},
    "BERSERK": {"price": 3500, "type": "донат"},
    "COBRA": {"price": 3000, "type": "донат"},
    "Кейс «Всё или ничего»": {"price": 6000, "type": "кейс"},
    "Кейс с Супер Донатом": {"price": 4500, "type": "кейс"},
    "Кейс с Супер Риллами": {"price": 3000, "type": "кейс"},
    "Снятие 1 выговора": {"price": 400, "type": "услуга"},
}

# ================== РОЛИ ==================
MOD_ROLE_IDS = [1546125576136560660, 1546125509442674778]
WARN_1_ROLE_ID = 1546125538198823033
WARN_2_ROLE_ID = 1546125541571043398
WARN_3_ROLE_ID = 1546125544888729761

PROTECTED_ROLE_IDS = [
    1546125455633944598, 1546125498340614195, 1546125488496451686,
    1546125469093732372, 1546125465482174484, 1547654044263252038,
    1546125472897961984, 1546125480321749053, 1550200782177968178,
]

PLAYER_ROLE_ID = 1539269779267915827
APPROVER_ROLE_ID = 1535261711450378330
PENDING_APPLICATION_ROLE_ID = 1567152429093363782  # Роль ожидания одобрения заявки
APPROVER_POINTS_ROLE_IDS = [
    1546125455633944598, 1546125498340614195
]

POVIXA_ROLE_IDS = [
    1546125455633944598, 1546125498340614195
]

ROLES_TO_GIVE = [1546125522675962027, 1546125519240564797]
STAFF_ROLES = [
    1546125455633944598, 1546125498340614195, 1547654044263252038,
    1546125465482174484, 1546125449594282118
]

ALLOWED_GUILDS = [1546125037545988207]

# ================== БАЗА ДАННЫХ ==================
# База хранится рядом с bot.py; путь можно задать через BOT_DB_PATH.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("BOT_DB_PATH", os.path.join(BASE_DIR, "bot_data.db"))
conn = sqlite3.connect(DB_PATH, timeout=30)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=FULL")
conn.execute("PRAGMA busy_timeout=30000")
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    warns INTEGER DEFAULT 0,
    personal_channel_id INTEGER
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
    message_id INTEGER PRIMARY KEY,
    author_id INTEGER,
    ban_number INTEGER,
    mute_number INTEGER,
    proof TEXT,
    approved BOOLEAN DEFAULT 0
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    item TEXT,
    price INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)''')

# Заявки сохраняются отдельно, чтобы не терялись после перезапуска бота.
cursor.execute('''CREATE TABLE IF NOT EXISTS pending_requests (
    request_type TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    message_id INTEGER,
    data TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (request_type, user_id)
)''')

# Автоматическая миграция существующей базы: CREATE TABLE IF NOT EXISTS
# не добавляет столбцы в уже созданную таблицу.
cursor.execute("PRAGMA table_info(pending_requests)")
pending_request_columns = {row[1] for row in cursor.fetchall()}
if "message_id" not in pending_request_columns:
    cursor.execute("ALTER TABLE pending_requests ADD COLUMN message_id INTEGER")
conn.commit()

# ================== БОТ ==================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ================== ФУНКЦИИ ==================
def get_user_data(user_id):
    # Создаём строку пользователя заранее, чтобы любые изменения сохранялись.
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, balance, warns, personal_channel_id) VALUES (?, 0, 0, NULL)",
        (user_id,)
    )
    cursor.execute(
        'SELECT balance, warns, personal_channel_id FROM users WHERE user_id = ?',
        (user_id,)
    )
    row = cursor.fetchone()
    conn.commit()
    return {'balance': row[0], 'warns': row[1], 'personal_channel_id': row[2]}

def update_warns(user_id, new_warns):
    # UPSERT исправляет случай /snyat: пользователь мог ещё отсутствовать в users.
    cursor.execute(
        """INSERT INTO users (user_id, balance, warns, personal_channel_id)
           VALUES (?, 0, ?, NULL)
           ON CONFLICT(user_id) DO UPDATE SET warns = excluded.warns""",
        (user_id, new_warns)
    )
    conn.commit()

def update_balance(user_id, amount):
    # Атомарное изменение баланса без перезаписи варнов и личного канала.
    cursor.execute(
        """INSERT INTO users (user_id, balance, warns, personal_channel_id)
           VALUES (?, ?, 0, NULL)
           ON CONFLICT(user_id) DO UPDATE SET balance = users.balance + excluded.balance""",
        (user_id, amount)
    )
    conn.commit()

def add_purchase(user_id, item, price):
    cursor.execute('INSERT INTO purchases (user_id, item, price) VALUES (?, ?, ?)', (user_id, item, price))
    conn.commit()

def set_personal_channel(user_id, channel_id):
    cursor.execute('UPDATE users SET personal_channel_id = ? WHERE user_id = ?', (channel_id, user_id))
    conn.commit()

def get_personal_channel(user_id):
    cursor.execute('SELECT personal_channel_id FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def add_report(message_id, author_id, ban_number, mute_number, proof):
    cursor.execute('INSERT INTO reports (message_id, author_id, ban_number, mute_number, proof) VALUES (?, ?, ?, ?, ?)',
                   (message_id, author_id, ban_number, mute_number, proof))
    conn.commit()

def get_report(message_id):
    cursor.execute('SELECT author_id, ban_number, mute_number, approved FROM reports WHERE message_id = ?', (message_id,))
    return cursor.fetchone()

def approve_report(message_id):
    cursor.execute('UPDATE reports SET approved = 1 WHERE message_id = ?', (message_id,))
    conn.commit()

def is_personal_channel(channel):
    if channel is None: return False
    if channel.id == REPORT_CHANNEL_ID: return True
    cursor.execute('SELECT 1 FROM users WHERE personal_channel_id = ? LIMIT 1', (channel.id,))
    if cursor.fetchone() is not None: return True
    if CATEGORY_ID and getattr(channel, 'category_id', None) == CATEGORY_ID: return True
    return False

def has_protected_role(member):
    return any(role.id in PROTECTED_ROLE_IDS for role in member.roles)

def is_moderator(member):
    if member.guild_permissions.kick_members: return True
    return any(role.id in MOD_ROLE_IDS for role in member.roles)

def has_verification_role(member):
    # Роль 1546125576136560660 также может принимать заявки на вступление.
    return any(role.id == APPROVER_ROLE_ID or role.id in MOD_ROLE_IDS for role in member.roles)

def has_points_role(member):
    if not APPROVER_POINTS_ROLE_IDS: return False
    return any(role.id in APPROVER_POINTS_ROLE_IDS for role in member.roles)

def has_povixa_role(member):
    if not POVIXA_ROLE_IDS: return False
    return any(role.id in POVIXA_ROLE_IDS for role in member.roles)

def get_msk_time_str():
    return datetime.now(MSK).strftime('%d.%m.%Y %H:%M')

pending_apps = {}
pending_points = {}

def save_pending_request(request_type, user_id, message_id, data):
    """Сохраняет или обновляет заявку пользователя в SQLite."""
    conn.execute(
        '''INSERT INTO pending_requests (request_type, user_id, message_id, data)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(request_type, user_id) DO UPDATE SET
               message_id = excluded.message_id,
               data = excluded.data,
               created_at = CURRENT_TIMESTAMP''',
        (request_type, user_id, message_id, json.dumps(data, ensure_ascii=False))
    )
    conn.commit()

def delete_pending_request(request_type, user_id):
    conn.execute(
        "DELETE FROM pending_requests WHERE request_type = ? AND user_id = ?",
        (request_type, user_id)
    )
    conn.commit()

def load_pending_requests():
    """Восстанавливает ожидающие заявки после запуска."""
    rows = conn.execute(
        "SELECT request_type, user_id, data FROM pending_requests"
    ).fetchall()
    for request_type, user_id, raw_data in rows:
        try:
            data = json.loads(raw_data)
        except (TypeError, json.JSONDecodeError):
            continue
        if request_type == "join":
            pending_apps[user_id] = data
        elif request_type == "points":
            pending_points[user_id] = data

load_pending_requests()

# ================== ВЫДАЧА PLAYER ПРИ ВХОДЕ ==================
@bot.event
async def on_member_join(member):
    if member.guild.id not in ALLOWED_GUILDS: return
    role = member.guild.get_role(PLAYER_ROLE_ID)
    if role:
        try:
            await member.add_roles(role, reason="Автовыдача PLAYER")
            print(f"✅ {member.name} получил {role.name}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

# ================== КОМАНДЫ ==================
def is_allowed_guild(interaction):
    return interaction.guild is not None and interaction.guild.id in ALLOWED_GUILDS

# -------- /shop --------
@bot.tree.command(name="shop", description="Магазин баллов сервера")
async def shop(interaction: discord.Interaction):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Этот бот не настроен для этого сервера.", ephemeral=True)
        return

    shop_text = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "⭐ **МАГАЗИН БАЛЛОВ**\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━╯\n"
        "🎬 Зарабатывай баллы за просмотры, покупай игровые наборы и донаты и получай награды за свою активность!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎥・**КАК ЗАРАБОТАТЬ БАЛЛЫ?**\n"
        "📊 5 просмотров = 1 балл\n"
        "▫️ 500 просмотров — 100 баллов\n"
        "▫️ 1 000 просмотров — 200 баллов\n"
        "▫️ 5 000 просмотров — 1 000 баллов\n"
        "▫️ 10 000 просмотров — 2 000 баллов\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎒・**КИТЫ И НАБОРЫ**\n"
        "⚔️ PVP — 1 000 баллов\n"
        "💻 CYBER — 1 500 баллов\n"
        "💰 RICH — 2 000 баллов\n"
        "👑 TOPER — 2 500 баллов\n\n"
        "🔧 D.OWNER — 2 300 баллов\n"
        "⚙️ DADMIN — 1 000 баллов\n"
        "🛡️ D.GLMODER — 900 баллов\n"
        "💠 D.STMODER — 750 баллов\n"
        "🔹 D.MODER — 500 баллов\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👑・**ДОНАТЫ**\n"
        "🤍 WHITE — 5 000 баллов\n"
        "🐰 RABBIT — 4 500 баллов\n"
        "🎬 DHELPER — 4 500 баллов\n"
        "😇 GOD — 4 000 баллов\n"
        "🔥 ENDER — 4 000 баллов\n"
        "🦇 DRACULA — 3 500 баллов\n"
        "⚡ BERSERK — 3 500 баллов\n"
        "🐍 COBRA — 3 000 баллов\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎁・**КЕЙСЫ**\n"
        "🎲 Кейс «Всё или ничего» — 6 000 баллов\n"
        "💎 Кейс с Супер Донатом — 4 500 баллов\n"
        "🎁 Кейс с Супер Риллами — 3 000 баллов\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📜・**УСЛУГИ**\n"
        "📝 Снятие 1 выговора — 400 баллов\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📜・**ПРАВИЛА МАГАЗИНА**\n"
        "🔹 За каждые 5 просмотров начисляется 1 балл.\n"
        "🔹 Накрутка просмотров запрещена.\n"
        "🔹 Для покупки обратись к администрации или куратору медиа.\n"
        "🔹 После покупки баллы списываются с баланса.\n"
        "🔹 Перед покупкой убедись, что у тебя достаточно баллов.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🌟 **СНИМАЙ • КОПИ • ПОКУПАЙ**\n"
        "🎬 Твои просмотры — твой прогресс!"
    )

    embed = discord.Embed(description=shop_text, color=0x9B59B6)
    embed.set_footer(text="Для покупки используй /kit, /донат, /case или /услуга")
    await interaction.response.send_message(embed=embed)

# -------- /kit --------
@bot.tree.command(name="kit", description="Купить кит за баллы")
@app_commands.describe(name="Какой кит ты хочешь купить")
@app_commands.choices(name=[
    app_commands.Choice(name="PVP — 1000 баллов", value="PVP"),
    app_commands.Choice(name="CYBER — 1500 баллов", value="CYBER"),
    app_commands.Choice(name="RICH — 2000 баллов", value="RICH"),
    app_commands.Choice(name="TOPER — 2500 баллов", value="TOPER"),
    app_commands.Choice(name="D.OWNER — 2300 баллов", value="D.OWNER"),
    app_commands.Choice(name="DADMIN — 1000 баллов", value="DADMIN"),
    app_commands.Choice(name="D.GLMODER — 900 баллов", value="D.GLMODER"),
    app_commands.Choice(name="D.STMODER — 750 баллов", value="D.STMODER"),
    app_commands.Choice(name="D.MODER — 500 баллов", value="D.MODER"),
])
async def kit(interaction: discord.Interaction, name: app_commands.Choice[str]):
    await process_purchase(interaction, name.value)

# -------- /донат --------
@bot.tree.command(name="донат", description="Купить донат-привилегию за баллы")
@app_commands.describe(name="Какой донат ты хочешь купить")
@app_commands.choices(name=[
    app_commands.Choice(name="WHITE — 5000 баллов", value="WHITE"),
    app_commands.Choice(name="RABBIT — 4500 баллов", value="RABBIT"),
    app_commands.Choice(name="DHELPER — 4500 баллов", value="DHELPER"),
    app_commands.Choice(name="GOD — 4000 баллов", value="GOD"),
    app_commands.Choice(name="ENDER — 4000 баллов", value="ENDER"),
    app_commands.Choice(name="DRACULA — 3500 баллов", value="DRACULA"),
    app_commands.Choice(name="BERSERK — 3500 баллов", value="BERSERK"),
    app_commands.Choice(name="COBRA — 3000 баллов", value="COBRA"),
])
async def donat(interaction: discord.Interaction, name: str):
    # Нормализуем старые значения команд, которые Discord может ещё отправлять из кэша.
    normalized_name = name.strip().upper()
    await process_purchase(interaction, normalized_name)

# -------- /case --------
@bot.tree.command(name="case", description="Купить кейс за баллы")
@app_commands.describe(name="Какой кейс ты хочешь купить")
@app_commands.choices(name=[
    app_commands.Choice(name="Кейс «Всё или ничего» — 6000 баллов", value="Кейс «Всё или ничего»"),
    app_commands.Choice(name="Кейс с Супер Донатом — 4500 баллов", value="Кейс с Супер Донатом"),
    app_commands.Choice(name="Кейс с Супер Риллами — 3000 баллов", value="Кейс с Супер Риллами"),
])
async def case_cmd(interaction: discord.Interaction, name: app_commands.Choice[str]):
    await process_purchase(interaction, name.value)

# -------- /услуга --------
@bot.tree.command(name="услуга", description="Купить услугу за баллы")
@app_commands.describe(name="Какую услугу ты хочешь купить")
@app_commands.choices(name=[
    app_commands.Choice(name="Снятие 1 выговора — 400 баллов", value="Снятие 1 выговора"),
])
async def usluga_cmd(interaction: discord.Interaction, name: app_commands.Choice[str]):
    await process_purchase(interaction, name.value)

# -------- Общая функция покупки --------
async def process_purchase(interaction: discord.Interaction, item_key: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Этот бот не настроен для этого сервера.", ephemeral=True)
        return

    item = SHOP_ITEMS.get(item_key)
    if not item:
        await interaction.response.send_message("❌ Товар не найден.", ephemeral=True)
        return

    price = item["price"]
    data = get_user_data(interaction.user.id)
    balance = data['balance']
    time_str = get_msk_time_str()

    if balance < price:
        embed = discord.Embed(
            title="❌ Не оплачено!",
            color=0xE74C3C,
            description=f"У вас не хватает баллов на покупку данного товара.\n\n"
                        f"**Товар:** `{item_key}`\n"
                        f"**Цена:** {price} баллов\n"
                        f"**Ваш баланс:** {balance} баллов\n"
                        f"**Не хватает:** {price - balance} баллов",
            timestamp=datetime.now(MSK)
        )
        embed.set_footer(text=f"Действие зафиксировано | {time_str} МСК")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    update_balance(interaction.user.id, -price)
    add_purchase(interaction.user.id, item_key, price)

    embed = discord.Embed(
        title="✅ Успешно!",
        color=0x2ECC71,
        description=f"Товар будет выдан администрацией.\n\n"
                    f"**Товар:** `{item_key}`\n"
                    f"**Цена:** {price} баллов\n"
                    f"**Остаток:** {balance - price} баллов",
        timestamp=datetime.now(MSK)
    )
    embed.set_footer(text=f"Действие зафиксировано | {time_str} МСК")
    await interaction.response.send_message(embed=embed)

    try:
        shop_channel = interaction.guild.get_channel(SHOP_CHANNEL_ID)
        if shop_channel:
            log = discord.Embed(
                title="🧾 Новая покупка",
                color=0x3498DB,
                description=f"**Игрок:** {interaction.user.mention}\n"
                            f"**Товар:** `{item_key}`\n"
                            f"**Цена:** {price} баллов",
                timestamp=datetime.now(MSK)
            )
            log.set_footer(text=f"{time_str} МСК")
            await shop_channel.send(embed=log)
    except:
        pass

# -------- /balance --------
@bot.tree.command(name="balance", description="Показать баланс и статистику игрока")
@app_commands.describe(игрок="Игрок, чью статистику показать (необязательно)")
async def balance(interaction: discord.Interaction, игрок: discord.Member = None):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Этот бот не настроен для этого сервера.", ephemeral=True)
        return

    target = игрок if игрок else interaction.user
    cursor.execute('SELECT SUM(ban_number), SUM(mute_number) FROM reports WHERE author_id = ? AND approved = 1', (target.id,))
    row = cursor.fetchone()
    total_bans = row[0] if row[0] else 0
    total_mutes = row[1] if row[1] else 0
    total_points = total_bans * 10 + total_mutes * 5
    user_data = get_user_data(target.id)

    embed = discord.Embed(
        title=f"📊 Статистика игрока {target.display_name}",
        color=discord.Color.green(),
        description=f"**Общее количество баллов:** {total_points}\n"
                    f"**Текущий баланс:** {user_data['balance']} баллов"
    )
    await interaction.response.send_message(embed=embed)

# -------- /povixa --------
@bot.tree.command(name="povixa", description="Поздравить игрока с повышением")
@app_commands.describe(игрок="Игрок, которого повысили", роль="Новая роль игрока")
async def povixa(interaction: discord.Interaction, игрок: discord.Member, роль: discord.Role):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Этот бот не настроен для этого сервера.", ephemeral=True)
        return

    if interaction.channel.id != POVIXA_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{POVIXA_CHANNEL_ID}>!", ephemeral=True)
        return

    if not has_povixa_role(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для использования этой команды.", ephemeral=True)
        return

    try:
        await игрок.add_roles(роль, reason=f"Повышение от {interaction.user.display_name}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ У меня недостаточно прав, чтобы выдать эту роль. Проверьте иерархию ролей.", ephemeral=True)
        return
    except discord.HTTPException:
        await interaction.response.send_message("❌ Произошла ошибка при выдаче роли.", ephemeral=True)
        return

    time_str = get_msk_time_str()
    embed = discord.Embed(
        color=0x2ECC71,
        description=f"Поздравляем с повышением!\n{игрок.mention}\nПовышен до: {роль.mention}\nУдачной работы!",
        timestamp=datetime.now(MSK)
    )
    embed.set_footer(text=f"Действие зафиксировано | {time_str} МСК")
    await interaction.response.send_message(embed=embed)

# -------- /warn --------
@bot.tree.command(name="warn", description="Выдать предупреждение игроку (до 2-х)")
@app_commands.describe(игрок="Игрок, которому выдаётся предупреждение", причина="Причина предупреждения")
async def warn(interaction: discord.Interaction, игрок: discord.Member, причина: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Этот бот не настроен для этого сервера.", ephemeral=True)
        return
    if not is_moderator(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав.", ephemeral=True)
        return
    if игрок == interaction.user:
        await interaction.response.send_message("❌ Нельзя выдать предупреждение самому себе.", ephemeral=True)
        return
    if has_protected_role(игрок):
        await interaction.response.send_message("❌ Ошибка: вы не можете выдать варн администрации сервера.", ephemeral=True)
        return

    data = get_user_data(игрок.id)
    current_warns = data['warns']
    if current_warns >= 2:
        await interaction.response.send_message(f"❌ У {игрок.display_name} уже {current_warns} предупреждения. Третий – через /snyat.", ephemeral=True)
        return

    new_warns = current_warns + 1
    update_warns(игрок.id, new_warns)

    role1 = interaction.guild.get_role(WARN_1_ROLE_ID)
    role2 = interaction.guild.get_role(WARN_2_ROLE_ID)
    role3 = interaction.guild.get_role(WARN_3_ROLE_ID)

    try:
        if new_warns == 1:
            if role1: await игрок.add_roles(role1, reason=f"Варн #{new_warns}")
            if role2 and role2 in игрок.roles: await игрок.remove_roles(role2)
            if role3 and role3 in игрок.roles: await игрок.remove_roles(role3)
        elif new_warns == 2:
            if role1 and role1 in игрок.roles: await игрок.remove_roles(role1)
            if role2: await игрок.add_roles(role2, reason=f"Варн #{new_warns}")
    except discord.Forbidden:
        await interaction.response.send_message("⚠️ Варн записан в БД, но бот **не смог выдать роль** (проверьте иерархию ролей бота).", ephemeral=True)

    time_str = get_msk_time_str()
    embed = discord.Embed(
        title="⚠️ Выдан варн!",
        color=0xFFA500,
        description=f"Игроку {игрок.mention} выдан варн!\n**Причина:** {причина}\n**Выдан варн:** Warn {new_warns}/3",
        timestamp=datetime.now(MSK)
    )
    embed.set_footer(text=f"Действие зафиксировано | {time_str} МСК")
    await interaction.response.send_message(embed=embed)

# -------- /unwarn --------
@bot.tree.command(name="unwarn", description="Снять одно предупреждение с игрока")
@app_commands.describe(игрок="Игрок, у которого снимается предупреждение", причина="Причина снятия")
async def unwarn(interaction: discord.Interaction, игрок: discord.Member, причина: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Этот бот не настроен для этого сервера.", ephemeral=True)
        return
    if not is_moderator(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав.", ephemeral=True)
        return

    data = get_user_data(игрок.id)
    current_warns = data['warns']
    if current_warns <= 0:
        await interaction.response.send_message(f"❌ У игрока **{игрок.display_name}** нет предупреждений.", ephemeral=True)
        return

    new_warns = current_warns - 1
    update_warns(игрок.id, new_warns)

    role1 = interaction.guild.get_role(WARN_1_ROLE_ID)
    role2 = interaction.guild.get_role(WARN_2_ROLE_ID)
    role3 = interaction.guild.get_role(WARN_3_ROLE_ID)

    # Пытаемся снять роли и выводим ошибку, если не хватает прав
    try:
        if role1 and role1 in игрок.roles: await игрок.remove_roles(role1)
        if role2 and role2 in игрок.roles: await игрок.remove_roles(role2)
        if role3 and role3 in игрок.roles: await игрок.remove_roles(role3)

        if new_warns == 1:
            if role1: await игрок.add_roles(role1, reason="Снят варн, осталось 1")
        elif new_warns == 2:
            if role2: await игрок.add_roles(role2, reason="Снят варн, осталось 2")
    except discord.Forbidden:
        await interaction.response.send_message("⚠️ Варн снят в БД, но бот **не смог изменить роли** (проверьте, что роль бота стоит ВЫШЕ ролей Warn).", ephemeral=True)
        return

    time_str = get_msk_time_str()
    embed = discord.Embed(
        title="✅ Снят варн!",
        color=0x2ECC71,
        description=f"Игроку {игрок.mention} снят варн!\n**Причина:** {причина}",
        timestamp=datetime.now(MSK)
    )
    embed.set_footer(text=f"Действие зафиксировано | {time_str} МСК")
    await interaction.response.send_message(embed=embed)

# -------- /snyat --------
@bot.tree.command(name="snyat", description="Снять игрока (Warn 3/3 + кик + удаление личного канала)")
@app_commands.describe(игрок="Игрок, которого нужно снять", причина="Причина снятия")
async def snyat(interaction: discord.Interaction, игрок: discord.Member, причина: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Этот бот не настроен для этого сервера.", ephemeral=True)
        return
    if not is_moderator(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав.", ephemeral=True)
        return
    if игрок == interaction.user:
        await interaction.response.send_message("❌ Нельзя снять самого себя.", ephemeral=True)
        return
    if игрок == interaction.guild.owner:
        await interaction.response.send_message("❌ Нельзя снять владельца сервера.", ephemeral=True)
        return
    if has_protected_role(игрок):
        await interaction.response.send_message("❌ Ошибка: вы не можете выдать варн администрации сервера.", ephemeral=True)
        return

    update_warns(игрок.id, 3)

    role1 = interaction.guild.get_role(WARN_1_ROLE_ID)
    role2 = interaction.guild.get_role(WARN_2_ROLE_ID)
    role3 = interaction.guild.get_role(WARN_3_ROLE_ID)
    
    try:
        if role1 and role1 in игрок.roles: await игрок.remove_roles(role1)
        if role2 and role2 in игрок.roles: await игрок.remove_roles(role2)
        if role3: await игрок.add_roles(role3, reason=f"Снят через /snyat: {причина}")
    except discord.Forbidden:
        await interaction.response.send_message("⚠️ Пользователь снят в БД, но бот **не смог изменить роли** (проверьте иерархию).", ephemeral=True)

    channel_id = get_personal_channel(игрок.id)
    if channel_id:
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            try: await channel.delete(reason=f"Удаление личного канала {игрок.display_name}")
            except: pass
        cursor.execute('UPDATE users SET personal_channel_id = NULL WHERE user_id = ?', (игрок.id,))
        conn.commit()

    try:
        await игрок.kick(reason=f"Снят через /snyat от {interaction.user.display_name}: {причина}")
        time_str = get_msk_time_str()
        embed = discord.Embed(
            title="🚫 Снят с Команды Проекта!",
            color=0xE74C3C,
            description=f"Игрок {игрок.mention} снят с Команды Проекта!\n**Причина:** {причина}",
            timestamp=datetime.now(MSK)
        )
        embed.set_footer(text=f"Действие зафиксировано | {time_str} МСК")
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ У меня недостаточно прав для кика.", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("❌ Ошибка при кике.", ephemeral=True)

# ================== !принят (верификация) ==================
@bot.command(name='принят')
async def accept(ctx):
    if not ctx.message.reference:
        await ctx.send("❌ Вы должны ответить на сообщение игрока с заявкой.", delete_after=10)
        await ctx.message.delete(delay=10)
        return
    try:
        original_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except:
        await ctx.send("❌ Не удалось найти исходное сообщение.", delete_after=10)
        await ctx.message.delete(delay=10)
        return
    if ctx.channel.id != JOIN_CHANNEL_ID:
        await ctx.send("❌ Эта команда работает только в канале вступления.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    author = ctx.author
    if not has_verification_role(author):
        await ctx.send("❌ У вас нет прав принимать заявки на вступление.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    # Разрешаем подтверждать собственную заявку только участникам с ролью MOD_ROLE_IDS.
    can_approve_own_application = any(role.id in MOD_ROLE_IDS for role in author.roles)
    if original_msg.author.bot or (original_msg.author == author and not can_approve_own_application):
        await ctx.send("❌ Нельзя принять сообщение от бота или самого себя.", delete_after=10)
        await ctx.message.delete(delay=10)
        return
    for reaction in original_msg.reactions:
        if str(reaction.emoji) == '✅':
            await ctx.send("❌ Этот игрок уже принят.", delete_after=10)
            await ctx.message.delete(delay=10)
            return

    member = original_msg.author
    app_data = pending_apps.get(member.id)
    if not app_data:
        await ctx.send("⚠️ Данные заявки не найдены.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    nick = app_data['nick']
    position = app_data['position']

    new_nick = f"{nick} | {position}"
    if len(new_nick) > 32: new_nick = new_nick[:32]
    try:
        await member.edit(nick=new_nick, reason=f"Принят от {author.display_name}")
    except Exception as e:
        await ctx.send(f"⚠️ Не удалось изменить никнейм: {e}", delete_after=10)

    roles_to_add = [ctx.guild.get_role(rid) for rid in ROLES_TO_GIVE if ctx.guild.get_role(rid)]
    # После одобрения заявки автоматически выдаём базовый класс доступа Media.
    media_role = discord.utils.get(ctx.guild.roles, name="Media")
    if media_role is None:
        legacy_media_role = discord.utils.get(ctx.guild.roles, name="Media » уровень доступа")
        if legacy_media_role is not None:
            media_role = legacy_media_role
            try:
                await media_role.edit(name="Media", reason="Миграция роли доступа WhiteGrief")
            except discord.Forbidden:
                pass
    if media_role is None:
        try:
            media_role = await ctx.guild.create_role(
                name="Media",
                colour=discord.Colour(0x8B5CF6),
                permissions=discord.Permissions.none(),
                hoist=True,
                reason="Базовая роль доступа WhiteGrief Control Panel",
            )
            print(f"✅ Создана роль Media (ID: {media_role.id})")
        except discord.Forbidden:
            await ctx.send("❌ Не удалось создать роль Media. Проверь право Manage Roles и положение роли бота.")
            return
    if media_role not in member.roles and media_role not in roles_to_add:
        roles_to_add.append(media_role)

    if roles_to_add:
        try:
            await member.add_roles(*roles_to_add, reason=f"Заявка одобрена: {author.display_name}")
        except discord.Forbidden:
            await ctx.send("❌ Недостаточно прав для выдачи ролей (проверьте иерархию).")
            return

    # После одобрения снимаем временную роль ожидания.
    pending_role = ctx.guild.get_role(PENDING_APPLICATION_ROLE_ID)
    if pending_role and pending_role in member.roles:
        try:
            await member.remove_roles(pending_role, reason=f"Заявка одобрена пользователем {author}")
        except discord.Forbidden:
            await ctx.send("⚠️ Заявка одобряется, но не удалось снять роль ожидания. Проверь права и иерархию ролей.")
        except discord.HTTPException as error:
            await ctx.send(f"⚠️ Не удалось снять роль ожидания: {error}")

    category = ctx.guild.get_channel(CATEGORY_ID) if CATEGORY_ID else None
    channel_name = nick.lower()

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }
    for role_id in STAFF_ROLES:
        role = ctx.guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    try:
        channel = await ctx.guild.create_text_channel(channel_name, category=category, overwrites=overwrites,
                                                     reason=f"Личный канал для {member.display_name}")
        set_personal_channel(member.id, channel.id)

        # Приветственная Embed-панель для нового участника Медиа.
        welcome_embed = discord.Embed(
            title="🎬 WHITEGRIEF MEDIA",
            description=(
                f"**Добро пожаловать в команду Медиа, {member.mention}!**\n"
                "Рады видеть тебя среди нас. Здесь собрана важная информация о работе, баллах и покупках."
            ),
            color=discord.Color.from_rgb(151, 112, 210)
        )
        welcome_embed.add_field(
            name="🎥 ТВОЯ РАБОТА",
            value="• Оставляй еженедельную норму.\n• Публикуй видеоролики, чтобы получать баллы.\n• Следи за активностью и не пропускай отчётную неделю.",
            inline=False
        )
        welcome_embed.add_field(
            name="💎 ПОЛЕЗНЫЕ КОМАНДЫ",
            value="**/balance** — проверить баланс.\n**/shop** — посмотреть магазин.\n**/kit** — приобрести наборы.\n**/донат** — приобрести донат-привилегии.\n**/case** — приобрести кейсы.\n**/услуга** — приобрести услуги.",
            inline=False
        )
        welcome_embed.add_field(
            name="📊 1. НЕДЕЛЬНАЯ НОРМА",
            value="**1.** Твой никнейм: `(твой игровой никнейм)`\n**2.** Ссылки на ролики, которые ты сделал: `(ссылки)`",
            inline=False
        )
        welcome_embed.add_field(
            name="💰 2. ПОЛУЧЕНИЕ БАЛЛОВ",
            value="**1.** Твой никнейм: `(твой ник в игре)`\n**2.** Сколько хочешь получить баллов: `(количество)`\n**3.** Ссылка на ролик: `(ссылка)`",
            inline=False
        )
        welcome_embed.add_field(
            name="🛒 3. ПОКУПКА ЗА БАЛЛЫ",
            value="**1.** Твой никнейм: `(твой ник в игре)`\n**2.** Что хочешь купить: `(название товара)`",
            inline=False
        )
        welcome_embed.add_field(
            name="⭐ НЕСКОЛЬКО ВАЖНЫХ СОВЕТОВ",
            value="• Проверяй ссылки перед отправкой.\n• Указывай точное количество баллов.\n• Перед покупкой проверяй баланс.\n• Сохраняй ссылки на опубликованные ролики.",
            inline=False
        )
        welcome_embed.add_field(
            name="🔥 СНИМАЙ • ПУБЛИКУЙ • ЗАРАБАТЫВАЙ",
            value="**Твои ролики — твой вклад в развитие WhiteGrief Media!**",
            inline=False
        )
        welcome_embed.set_footer(text="WHITEGRIEF MEDIA • Удачной работы!")
        await channel.send(content=f"Привет, {member.mention}! Ты попал в команду Медиа.", embed=welcome_embed)
        await original_msg.clear_reaction('🕐')
        await original_msg.add_reaction('✅')
        pending_apps.pop(member.id, None)
        delete_pending_request("join", member.id)
        accepted_embed = discord.Embed(
            title="✅ ЗАЯВКА ОДОБРЕНА",
            description=f"{member.mention} успешно принят в команду **WhiteGrief Media**!",
            color=discord.Color.from_rgb(0, 255, 0),
            timestamp=discord.utils.utcnow()
        )
        accepted_embed.add_field(name="🎮 Игровой ник", value=nick, inline=True)
        accepted_embed.add_field(name="🛡️ Должность", value=position, inline=True)
        accepted_embed.add_field(name="📁 Личный канал", value=channel.mention, inline=False)
        accepted_embed.add_field(
            name="🚀 Следующий шаг",
            value="Загляни в личный канал, ознакомься с инструкциями и приступай к работе!",
            inline=False
        )
        accepted_embed.set_footer(text=f"WHITEGRIEF MEDIA • Принял: {author.display_name}")
        await ctx.send(embed=accepted_embed)
    except discord.Forbidden:
        await ctx.send("❌ У меня недостаточно прав для создания каналов.")
        return
    except Exception as e:
        await ctx.send(f"❌ Ошибка при создании канала: {e}")
        return

    await ctx.message.delete()

# ================== !принято (заявки на баллы) ==================
@bot.command(name='принято')
async def accept_points(ctx):
    if not ctx.message.reference:
        await ctx.send("❌ Вы должны ответить на сообщение с заявкой на баллы.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    try:
        original_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except:
        await ctx.send("❌ Не удалось найти исходное сообщение.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    if not is_personal_channel(ctx.channel):
        await ctx.send("❌ Эта команда работает только в личных каналах игроков.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    author = ctx.author
    if not has_points_role(author):
        await ctx.send("❌ У вас нет прав принимать заявки на баллы.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    if original_msg.author.bot or original_msg.author == author:
        await ctx.send("❌ Нельзя принять сообщение от бота или самого себя.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    for reaction in original_msg.reactions:
        if str(reaction.emoji) == '✅':
            await ctx.send("❌ Эта заявка уже одобрена.", delete_after=10)
            await ctx.message.delete(delay=10)
            return

    member = original_msg.author
    app_data = pending_points.get(member.id)
    if not app_data:
        await ctx.send("⚠️ Данные заявки не найдены.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    points = app_data['points']

    update_balance(member.id, points)
    pending_points.pop(member.id, None)
    delete_pending_request("points", member.id)
    try:
        await original_msg.clear_reaction('🕐')
    except:
        pass
    await original_msg.add_reaction('✅')
    new_balance = get_user_data(member.id)['balance']
    time_str = get_msk_time_str()

    embed = discord.Embed(
        title="✅ Заявка одобрена!",
        color=0x2ECC71,
        description=f"Игроку {member.mention} начислено **{points}** баллов.\n"
                    f"**Текущий баланс:** {new_balance} баллов.\n"
                    f"**Одобрил:** {author.mention}",
        timestamp=datetime.now(MSK)
    )
    embed.set_footer(text=f"Действие зафиксировано | {time_str} МСК")
    await ctx.send(embed=embed)
    await ctx.message.delete()

# ================== ON_MESSAGE ==================
@bot.event
async def on_message(message):
    # Красивый потоковый просмотр обычных текстовых сообщений в консоли Bot-Hosting.
    # Embed-панели и сообщения без текста/вложений в монитор не выводим.
    if (
        message.guild is not None
        and message.guild.id in ALLOWED_GUILDS
        and not message.author.bot
        and not message.embeds
        and (message.content.strip() or message.attachments)
    ):
        reset = "\033[0m"
        cyan = "\033[96m"
        purple = "\033[95m"
        green = "\033[92m"
        gray = "\033[90m"
        channel_name = getattr(message.channel, "name", "unknown-channel")
        author_name = getattr(message.author, "display_name", message.author.name)
        author_type = "БОТ" if message.author.bot else "ИГРОК"
        author_color = green if message.author.bot else purple
        timestamp = message.created_at.astimezone(MSK).strftime("%H:%M:%S")
        content = message.content.strip()
        border = "╔" + "═" * 68 + "╗"
        bottom = "╚" + "═" * 68 + "╝"
        print(f"\\n{cyan}{border}{reset}", flush=True)
        print(f"{cyan}║{reset} {purple}WHITEGRIEF • LIVE CHAT{reset} {gray}{timestamp}{reset}", flush=True)
        print(f"{cyan}╠" + "═" * 68 + f"╣{reset}", flush=True)
        print(f"{cyan}║{reset} Канал: {green}#{channel_name}{reset} <#{message.channel.id}>  {gray}(ID: {message.channel.id}){reset}", flush=True)
        print(f"{cyan}║{reset} {author_type}: {author_color}{author_name}{reset} <@{message.author.id}>  {gray}(ID: {message.author.id}){reset}", flush=True)
        print(f"{cyan}╟" + "─" * 68 + f"╢{reset}", flush=True)
        if content:
            for line in content.splitlines():
                print(f"{cyan}║{reset} {line}", flush=True)
        for attachment in message.attachments:
            print(f"{cyan}║{reset} 📎 {attachment.filename}: {attachment.url}", flush=True)
        print(f"{cyan}{bottom}{reset}", flush=True)

    if message.author.bot:
        return
    if message.guild is None or message.guild.id not in ALLOWED_GUILDS:
        return

    # ---------- ЛИЧНЫЕ КАНАЛЫ ----------
    if is_personal_channel(message.channel):
        if message.content.startswith('!'):
            await bot.process_commands(message)
            return

        lines = message.content.split('\n')
        ban_number = None
        mute_number = None
        proof = None
        nick = None
        points = None
        link = None

        for line in lines:
            line = line.strip()
            if not line:
                continue
            low = line.lower()

            if low.startswith('номер бана:'):
                try: ban_number = int(line.split(':', 1)[1].strip())
                except: pass
            elif low.startswith('номер мута:'):
                try: mute_number = int(line.split(':', 1)[1].strip())
                except: pass
            elif low.startswith('доказательства:'):
                proof = line.split(':', 1)[1].strip()

            if low.startswith('1. твой никнейм:') or low.startswith('твой никнейм:') \
               or low.startswith('1. ник:') or low.startswith('ник:'):
                nick = line.split(':', 1)[1].strip()
            elif (low.startswith('2. сколько ты хочешь получить балов:') or
                  low.startswith('сколько ты хочешь получить балов:') or
                  low.startswith('2. сколько ты хочешь получить баллов:') or
                  low.startswith('сколько ты хочешь получить баллов:')):
                try:
                    points = int(line.split(':', 1)[1].strip())
                except:
                    points = None
            elif (low.startswith('3. ссылка на ролик:') or
                  low.startswith('ссылка на ролик:') or
                  low.startswith('3. ссылка:') or
                  low.startswith('ссылка:')):
                link = line.split(':', 1)[1].strip()

        # ---- ОТЧЁТ ----
        if ban_number is not None and mute_number is not None and proof:
            embed = discord.Embed(
                title="📋 Новый отчёт",
                color=discord.Color.blue(),
                description=f"**Автор:** {message.author.mention}\n"
                            f"**Номер бана:** {ban_number}\n"
                            f"**Номер мута:** {mute_number}\n"
                            f"**Доказательства:** {proof}"
            )
            embed.set_footer(text="Нажмите ✅ для одобрения или ❌ для отклонения")
            msg = await message.channel.send(embed=embed)
            await msg.add_reaction('✅')
            await msg.add_reaction('❌')
            add_report(msg.id, message.author.id, ban_number, mute_number, proof)
            await message.delete()
            await message.channel.send(f"✅ Отчёт от {message.author.mention} принят!", delete_after=5)
            return

        # ---- ЗАЯВКА НА БАЛЛЫ ----
        if nick and points is not None and link:
            app_data = {'nick': nick, 'points': points, 'link': link}
            pending_points[message.author.id] = app_data
            save_pending_request("points", message.author.id, message.id, app_data)
            await message.add_reaction('🕐')

            mentions = []
            for role_id in APPROVER_POINTS_ROLE_IDS:
                role = message.guild.get_role(role_id)
                if role:
                    mentions.append(role.mention)

            if mentions:
                roles_text = " ".join(mentions)
                await message.channel.send(
                    f"{roles_text}, игрок {message.author.mention} подал заявку на **{points}** баллов.\n"
                    f"Напиши **!принято** ответом на его сообщение, чтобы начислить баллы."
                )
            else:
                await message.channel.send(
                    f"⚠️ Роли для заявок на баллы не найдены.\n"
                    f"Игрок {message.author.mention} ждёт одобрения. Напиши **!принято**."
                )
            return

        return

    # ---------- ЗАЯВКИ НА ВСТУПЛЕНИЕ ----------
    if message.channel.id == JOIN_CHANNEL_ID:
        if message.content.startswith('!'):
            await bot.process_commands(message)
            return

        lines = message.content.split('\n')
        nick = None
        position = None
        age = None

        for line in lines:
            line = line.strip()
            if not line or line.lower().startswith('форма заявки'):
                continue
            if line.lower().startswith('1. ник:') or line.lower().startswith('ник:'):
                nick = line.split(':', 1)[1].strip()
            elif line.lower().startswith('2. должность:') or line.lower().startswith('должность:'):
                position = line.split(':', 1)[1].strip()
            elif line.lower().startswith('3. возраст:') or line.lower().startswith('возраст:'):
                age = line.split(':', 1)[1].strip()

        if nick and position and age:
            app_data = {'nick': nick, 'position': position, 'age': age}
            pending_apps[message.author.id] = app_data
            save_pending_request("join", message.author.id, message.id, app_data)

            # Выдаём роль ожидания, пока заявка не одобрена.
            pending_role = message.guild.get_role(PENDING_APPLICATION_ROLE_ID)
            if pending_role and pending_role not in message.author.roles:
                try:
                    await message.author.add_roles(pending_role, reason="Заявка на вступление ожидает одобрения")
                except discord.Forbidden:
                    print(f"[WARN] Не удалось выдать роль ожидания {PENDING_APPLICATION_ROLE_ID}: проверь права и иерархию ролей.", flush=True)
                except discord.HTTPException as error:
                    print(f"[WARN] Ошибка выдачи роли ожидания: {error}", flush=True)
            elif pending_role is None:
                print(f"[WARN] Роль ожидания {PENDING_APPLICATION_ROLE_ID} не найдена на сервере.", flush=True)

            await message.add_reaction('🕐')
            approver_role = message.guild.get_role(APPROVER_ROLE_ID)
            application_embed = discord.Embed(
                title="📩 НОВАЯ ЗАЯВКА В WHITEGRIEF MEDIA",
                description=(
                    f"Игрок {message.author.mention} отправил заявку и ожидает рассмотрения.\n"
                    "Пожалуйста, проверьте данные и примите решение."
                ),
                color=discord.Color.from_rgb(255, 210, 0),
                timestamp=discord.utils.utcnow()
            )
            application_embed.add_field(name="🎮 Игровой ник", value=nick, inline=True)
            application_embed.add_field(name="🛡️ Должность", value=position, inline=True)
            application_embed.add_field(name="🎂 Возраст", value=age, inline=True)
            application_embed.add_field(
                name="📝 Как одобрить",
                value="Ответьте на исходное сообщение игрока командой **!принят**.",
                inline=False
            )
            application_embed.set_footer(text="WHITEGRIEF MEDIA • Заявки на вступление")
            content = approver_role.mention if approver_role else None
            await message.channel.send(content=content, embed=application_embed)
        else:
            await message.channel.send(
                "❌ Неверный формат заявки. Используйте:\n"
                "`1. Ник: ...`\n`2. Должность: ...`\n`3. Возраст: ...`",
                delete_after=10
            )
            await message.delete(delay=10)
        return

    await bot.process_commands(message)

# ================== РЕАКЦИИ ==================
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    report = get_report(payload.message_id)
    if not report:
        return
    author_id, ban_number, mute_number, approved = report
    if approved:
        return
    if not is_personal_channel(payload.channel_id):
        return
    emoji = str(payload.emoji)
    if emoji not in ('✅', '❌'):
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    member = guild.get_member(payload.user_id)
    if not member: return
    if not is_moderator(member): return

    channel = guild.get_channel(payload.channel_id)
    if not channel: return
    try:
        msg = await channel.fetch_message(payload.message_id)
    except: return

    embed = msg.embeds[0] if msg.embeds else discord.Embed()
    embed.color = discord.Color.green() if emoji == '✅' else discord.Color.red()

    if emoji == '✅':
        points = 0
        if ban_number > 0: points += 10
        if mute_number > 0: points += 5
        if points > 0:
            update_balance(author_id, points)
            approve_report(payload.message_id)
            embed.add_field(name="✅ Статус", value=f"Одобрено {member.mention}\nНачислено {points} баллов.", inline=False)
        else:
            approve_report(payload.message_id)
            embed.add_field(name="✅ Статус", value=f"Одобрено {member.mention} (без баллов)", inline=False)
    else:
        embed.add_field(name="❌ Статус", value=f"Отклонено {member.mention}", inline=False)

    await msg.edit(embed=embed)
    await msg.clear_reactions()

# ================== КОНСОЛЬ BOT-HOSTING ==================
_console_reader_started = False

async def console_input_loop():
    """Читает команды из stdin панели Bot-Hosting, не регистрируя их в Discord."""
    print("🖥️ Консольное управление включено. Введите /help для списка команд.", flush=True)

    while not bot.is_closed():
        try:
            raw = await asyncio.to_thread(sys.stdin.readline)
            if not raw:
                await asyncio.sleep(1)
                continue

            line = raw.strip()
            if not line:
                continue

            parts = line.split(maxsplit=2)
            command = parts[0].lower()

            if command == "/help":
                print(
                    "Команды консоли:\n"
                    "/text <ID канала> <сообщение> — отправить сообщение\n"
                    "/channels — список текстовых каналов и их ID\n"
                    "/help — показать эту подсказку",
                    flush=True
                )

            elif command == "/text":
                if len(parts) < 3:
                    print("❌ Формат: /text <ID канала> <сообщение>", flush=True)
                    continue
                try:
                    channel_id = int(parts[1])
                except ValueError:
                    print("❌ ID канала должен состоять из цифр.", flush=True)
                    continue

                channel = bot.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await bot.fetch_channel(channel_id)
                    except discord.NotFound:
                        print("❌ Канал с таким ID не найден.", flush=True)
                        continue
                    except discord.Forbidden:
                        print("❌ У бота нет доступа к этому каналу.", flush=True)
                        continue

                if not hasattr(channel, "send"):
                    print("❌ В этот тип канала нельзя отправить обычное сообщение.", flush=True)
                    continue

                try:
                    await channel.send(parts[2])
                    print(f"✅ Сообщение отправлено в #{getattr(channel, 'name', 'канал')} ({channel_id}).", flush=True)
                except discord.Forbidden:
                    print("❌ Нет прав на отправку сообщений в этот канал.", flush=True)
                except discord.HTTPException as error:
                    print(f"❌ Discord не принял сообщение: {error}", flush=True)

            elif command == "/channels":
                print("📚 Текстовые каналы доступных серверов:", flush=True)
                found = False
                for guild_id in ALLOWED_GUILDS:
                    guild = bot.get_guild(guild_id)
                    if guild is None:
                        continue
                    for channel in guild.text_channels:
                        print(f"#{channel.name} — ID: {channel.id}", flush=True)
                        found = True
                if not found:
                    print("Каналы пока не найдены. Проверь подключение бота и права.", flush=True)

            else:
                print("❓ Неизвестная команда. Введите /help.", flush=True)

        except Exception as error:
            print(f"❌ Ошибка консольного обработчика: {error}", flush=True)


# ================== ЗАПУСК ==================
@bot.event
async def on_ready():
    global _console_reader_started
    print(f'Бот {bot.user} запущен!')
    if not _console_reader_started:
        _console_reader_started = True
        asyncio.create_task(console_input_loop())

    # Автоматически создаём роли доступа и синхронизируем их ID с сайтом.
    for access_guild_id in ALLOWED_GUILDS:
        access_guild = bot.get_guild(access_guild_id)
        if access_guild:
            await ensure_control_panel_roles(access_guild)

    # Регистрируем команды только как серверные (guild commands).
    # Старые глобальные команды удаляем ниже, чтобы Discord не показывал
    # две версии каждой slash-команды одновременно.
    for guild_id in ALLOWED_GUILDS:
        guild = bot.get_guild(guild_id)
        if guild:
            try:
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)

                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                print(f'✅ Обновлено {len(synced)} серверных slash-команд на сервере {guild.name}')
            except Exception as e:
                print(f'❌ Ошибка синхронизации на {guild_id}: {e}')

    # Удаляем прежние глобальные регистрации. Серверные копии выше остаются.
    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        print('✅ Старые глобальные slash-команды удалены — дубликатов больше не будет.')
    except Exception as e:
        print(f'❌ Ошибка удаления глобальных команд: {e}')

    await bot.change_presence(activity=discord.Game(name='/shop | модерация'))



# ================== РОЛИ ДОСТУПА WHITEGRIEF CONTROL PANEL ==================
CONTROL_PANEL_SYNC_URL = os.getenv("CONTROL_PANEL_SYNC_URL", "").strip()
CONTROL_PANEL_SYNC_SECRET = os.getenv("CONTROL_PANEL_SYNC_SECRET", "").strip()

ACCESS_ROLE_DEFINITIONS = [
    # От минимального доступа к максимальному: фиолетовый -> красный.
    ("media", "Media » уровень доступа", 0x8B5CF6),
    ("co_adm", "Co.Adm » уровень доступа", 0xC026D3),
    ("adm", "Adm » уровень доступа", 0xF97316),
    ("full", "Full » уровень доступа", 0xEF4444),
]

async def ensure_control_panel_roles(guild: discord.Guild) -> None:
    """Создаёт недостающие роли доступа и передаёт их ID веб-панели."""
    role_payload = {}
    for access_level, role_name, color in ACCESS_ROLE_DEFINITIONS:
        role = discord.utils.get(guild.roles, name=role_name)
        # Миграция: сохраняем существующую роль Media и возвращаем ей полное название.
        if role is None and access_level == "media":
            old_role = discord.utils.get(guild.roles, name="Media")
            if old_role is not None:
                try:
                    role = await old_role.edit(
                        name=role_name,
                        reason="Приведение названия роли доступа WhiteGrief к стандарту",
                    )
                    print(f"✅ Переименована роль доступа: {role.name} (ID: {role.id})")
                except discord.Forbidden:
                    print("⚠️ Не удалось переименовать роль Media; проверь права Manage Roles и иерархию.")
        if role is None:
            try:
                role = await guild.create_role(
                    name=role_name,
                    colour=discord.Colour(color),
                    permissions=discord.Permissions.none(),
                    hoist=True,
                    mentionable=False,
                    reason="Настройка уровней доступа WhiteGrief Control Panel",
                )
                print(f"✅ Создана роль доступа: {role.name} (ID: {role.id})")
            except discord.Forbidden:
                print(f"❌ Не удалось создать роль {role_name}: у бота нет права Manage Roles или роль бота стоит ниже.")
                continue
            except Exception as error:
                print(f"❌ Ошибка создания роли {role_name}: {error}")
                continue
        role_payload[str(role.id)] = {
            "access_level": access_level,
            "name": role.name,
        }

    if len(role_payload) != len(ACCESS_ROLE_DEFINITIONS):
        print("⚠️ Не все роли доступа найдены/созданы; синхронизация с сайтом пропущена.")
        return

    print("🔐 Роли доступа WhiteGrief:")
    for role_id, info in role_payload.items():
        print(f"   {info['name']} — {role_id} [{info['access_level']}]")

    if not CONTROL_PANEL_SYNC_URL or not CONTROL_PANEL_SYNC_SECRET:
        print("⚠️ CONTROL_PANEL_SYNC_URL/CONTROL_PANEL_SYNC_SECRET не настроены. Роли созданы, но сайт пока не получил их ID.")
        return

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                CONTROL_PANEL_SYNC_URL,
                json={"guild_id": str(guild.id), "roles": role_payload},
                headers={"X-Bot-Sync-Secret": CONTROL_PANEL_SYNC_SECRET},
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ ID ролей переданы WhiteGrief Control Panel ({result.get('synced', 0)} ролей).")
                else:
                    detail = (await response.text())[:300]
                    print(f"❌ Сайт не принял ID ролей: HTTP {response.status}: {detail}")
    except Exception as error:
        print(f"❌ Не удалось связаться с Control Panel: {error}")


# ================== ПОЛНЫЙ АУДИТ СЕРВЕРА ==================
def write_audit_log(title, details, guild_id=None):
    """Отправляет аккуратный Embed в Discord; подробности уже сохраняются в latest.log."""
    safe_details = str(details)

    # Сохраняем аудит в latest.log, но не дублируем его в видимой консоли хостинга.
    timestamp = datetime.now(MSK).strftime("%Y-%m-%d %H:%M:%S")
    console_stream = sys.stdout
    if hasattr(console_stream, "log_file"):
        log_line = f"[AUDIT] {title} {safe_details}"
        lock = getattr(console_stream, "lock", None)
        if lock:
            with lock:
                for line in log_line.splitlines() or [log_line]:
                    console_stream.log_file.write(f"[{timestamp}] {line}\n")
                console_stream.log_file.flush()
        else:
            for line in log_line.splitlines() or [log_line]:
                console_stream.log_file.write(f"[{timestamp}] {line}\n")
            console_stream.log_file.flush()

    if bot.user is None:
        return
    channel = bot.get_channel(AUDIT_LOG_CHANNEL_ID)
    if channel is None:
        return

    async def send_audit():
        try:
            normalized_title = title.upper()
            if "УДАЛ" in normalized_title or "БАН" in normalized_title:
                color = discord.Color.from_rgb(237, 66, 69)
            elif "ИЗМЕН" in normalized_title or "ОБНОВ" in normalized_title:
                color = discord.Color.from_rgb(250, 166, 26)
            elif "ЗАШЁЛ" in normalized_title or "СОЗДАН" in normalized_title:
                color = discord.Color.from_rgb(46, 204, 113)
            else:
                color = discord.Color.from_rgb(88, 166, 255)

            embed = discord.Embed(
                title=f"📋  {title}",
                color=color,
                timestamp=datetime.now(timezone.utc)
            )

            if title == "НОВОЕ СООБЩЕНИЕ":
                channel_match = re.search(r"Канал: <#(\d+)> • #(.+?) \(ID: \d+\)", safe_details)
                author_match = re.search(r"Автор: <@(\d+)> • (.+?) \(ID: \d+\)", safe_details)
                message_match = re.search(r"Сообщение ID: (\d+)", safe_details)
                text_match = re.search(r"Текст:\n([\s\S]*?)(?=\nВложение:|\nEmbed:|$)", safe_details)

                if channel_match:
                    channel_id, channel_name = channel_match.groups()
                    embed.add_field(name="📍 Канал", value=f"<#{channel_id}>\n#{channel_name}", inline=True)
                if author_match:
                    author_id, author_name = author_match.groups()
                    embed.add_field(name="👤 Автор", value=f"<@{author_id}>\n{author_name}", inline=True)
                if message_match:
                    embed.add_field(name="🆔 ID сообщения", value=message_match.group(1), inline=False)

                message_text = text_match.group(1).strip() if text_match else ""
                if message_text:
                    if len(message_text) > 1000:
                        message_text = message_text[:997] + "..."
                    embed.add_field(name="💬 Содержание", value=message_text[:1024], inline=False)

                extras = re.findall(r"(Вложение: .+|Embed: .+)", safe_details)
                if extras:
                    embed.add_field(name="📎 Дополнительно", value="\n".join(extras)[:1024], inline=False)
            else:
                embed.description = safe_details[:4000] or "—"

            guild = bot.get_guild(guild_id) if guild_id else None
            if guild and guild.icon:
                embed.set_author(name=guild.name, icon_url=guild.icon.url)
            else:
                embed.set_author(name="WHITEGRIEF • SERVER AUDIT")
            embed.set_footer(text="WHITEGRIEF AUDIT")
            await channel.send(embed=embed)
        except Exception as error:
            print(f"[AUDIT DISCORD ERROR] {error}", flush=True)

    asyncio.create_task(send_audit())

def audit_member_label(member):
    return f"{member} (ID: {member.id})"


@bot.listen("on_message")
async def audit_message_create(message):
    if message.guild is None or message.guild.id not in ALLOWED_GUILDS:
        return
    # Сообщения самого WhiteGrief и остальных ботов не засоряют аудит и live-консоль.
    if message.author.bot:
        return
    if not message.content.strip() and not message.attachments and not message.embeds:
        return
    channel_name = getattr(message.channel, "name", "unknown")
    details = (
        f"Канал: <#{message.channel.id}> • #{channel_name} (ID: {message.channel.id})\n"
        f"Автор: <@{message.author.id}> • {message.author} (ID: {message.author.id})\n"
        f"Сообщение ID: {message.id}\n"
        f"Текст:\n{message.content[:2500] or '[нет текстового содержимого]'}"
    )
    for attachment in message.attachments:
        details += f"\nВложение: {attachment.filename} — {attachment.url}"
    for embed in message.embeds[:3]:
        details += f"\nEmbed: {(embed.title or '')} {(embed.description or '')[:500]}"
    write_audit_log("НОВОЕ СООБЩЕНИЕ", details, message.guild.id)


@bot.listen("on_message_edit")
async def audit_message_edit(before, after):
    if after.guild is None or after.guild.id not in ALLOWED_GUILDS:
        return
    if after.author.bot:
        return
    if before.content == after.content and before.attachments == after.attachments:
        return
    details = (
        f"Канал: #{getattr(after.channel, 'name', 'unknown')} (ID: {after.channel.id})\n"
        f"Автор: {after.author} (ID: {after.author.id})\n"
        f"Сообщение ID: {after.id}\n"
        f"Было:\n{before.content[:1500] or '[пусто]'}\n"
        f"Стало:\n{after.content[:1500] or '[пусто]'}"
    )
    write_audit_log("ИЗМЕНЕНО СООБЩЕНИЕ", details, after.guild.id)


@bot.listen("on_raw_message_delete")
async def audit_message_delete(payload):
    guild = bot.get_guild(payload.guild_id) if payload.guild_id else None
    if guild is None or guild.id not in ALLOWED_GUILDS:
        return
    cached = payload.cached_message
    if cached and cached.author.bot:
        return
    channel = guild.get_channel(payload.channel_id)
    channel_name = getattr(channel, "name", "unknown")
    if cached:
        details = (
            f"Канал: #{channel_name} (ID: {payload.channel_id})\n"
            f"Автор удалённого сообщения: {cached.author} (ID: {cached.author.id})\n"
            f"Сообщение ID: {payload.message_id}\n"
            f"Содержимое:\n{cached.content[:2500] or '[нет текста]'}"
        )
        for attachment in cached.attachments:
            details += f"\nВложение: {attachment.filename} — {attachment.url}"
    else:
        details = (
            f"Канал: #{channel_name} (ID: {payload.channel_id})\n"
            f"Сообщение ID: {payload.message_id}\n"
            "Содержимое недоступно: сообщения не было в кэше бота."
        )
    details += "\nКто именно удалил сообщение: Discord не передаёт это событие боту напрямую."
    write_audit_log("УДАЛЕНО СООБЩЕНИЕ", details, guild.id)


@bot.listen("on_raw_bulk_message_delete")
async def audit_bulk_message_delete(payload):
    guild = bot.get_guild(payload.guild_id) if payload.guild_id else None
    if guild is None or guild.id not in ALLOWED_GUILDS:
        return
    channel = guild.get_channel(payload.channel_id)
    details = (
        f"Канал: #{getattr(channel, 'name', 'unknown')} (ID: {payload.channel_id})\n"
        f"Количество удалённых сообщений: {len(payload.message_ids)}\n"
        f"ID сообщений: {', '.join(map(str, list(payload.message_ids)[:100]))}\n"
        "Кто именно выполнил массовое удаление: событие Discord не указывает исполнителя."
    )
    write_audit_log("МАССОВОЕ УДАЛЕНИЕ СООБЩЕНИЙ", details, guild.id)


@bot.listen("on_member_join")
async def audit_member_join(member):
    if member.guild.id in ALLOWED_GUILDS:
        write_audit_log("ИГРОК ЗАШЁЛ НА СЕРВЕР", audit_member_label(member), member.guild.id)


@bot.listen("on_member_remove")
async def audit_member_remove(member):
    if member.guild.id in ALLOWED_GUILDS:
        write_audit_log("ИГРОК ПОКИНУЛ СЕРВЕР", audit_member_label(member), member.guild.id)


@bot.listen("on_member_update")
async def audit_member_update(before, after):
    if after.guild.id not in ALLOWED_GUILDS:
        return
    changes = []
    if before.nick != after.nick:
        changes.append(f"Ник: {before.nick or before.name} → {after.nick or after.name}")
    before_roles = {r.id: r for r in before.roles}
    after_roles = {r.id: r for r in after.roles}
    added = [r for rid, r in after_roles.items() if rid not in before_roles]
    removed = [r for rid, r in before_roles.items() if rid not in after_roles]
    if added:
        changes.append("Выданы роли: " + ", ".join(f"{r.name} ({r.id})" for r in added))
    if removed:
        changes.append("Сняты роли: " + ", ".join(f"{r.name} ({r.id})" for r in removed))
    if changes:
        write_audit_log("ИЗМЕНЕНИЕ УЧАСТНИКА", audit_member_label(after) + "\n" + "\n".join(changes), after.guild.id)


@bot.listen("on_guild_channel_create")
async def audit_channel_create(channel):
    if channel.guild.id in ALLOWED_GUILDS:
        write_audit_log("СОЗДАН КАНАЛ", f"#{channel.name} (ID: {channel.id}, тип: {channel.type})", channel.guild.id)


@bot.listen("on_guild_channel_delete")
async def audit_channel_delete(channel):
    if channel.guild.id in ALLOWED_GUILDS:
        write_audit_log("УДАЛЁН КАНАЛ", f"#{channel.name} (ID: {channel.id}, тип: {channel.type})", channel.guild.id)


@bot.listen("on_guild_channel_update")
async def audit_channel_update(before, after):
    if after.guild.id not in ALLOWED_GUILDS:
        return
    changes = []
    if before.name != after.name:
        changes.append(f"Название: {before.name} → {after.name}")
    if getattr(before, "topic", None) != getattr(after, "topic", None):
        changes.append(f"Описание: {getattr(before, 'topic', None)} → {getattr(after, 'topic', None)}")
    if changes:
        write_audit_log("ИЗМЕНЁН КАНАЛ", f"Канал ID: {after.id}\n" + "\n".join(changes), after.guild.id)


@bot.listen("on_guild_role_create")
async def audit_role_create(role):
    if role.guild.id in ALLOWED_GUILDS:
        write_audit_log("СОЗДАНА РОЛЬ", f"{role.name} (ID: {role.id})", role.guild.id)


@bot.listen("on_guild_role_delete")
async def audit_role_delete(role):
    if role.guild.id in ALLOWED_GUILDS:
        write_audit_log("УДАЛЕНА РОЛЬ", f"{role.name} (ID: {role.id})", role.guild.id)


@bot.listen("on_guild_role_update")
async def audit_role_update(before, after):
    if after.guild.id not in ALLOWED_GUILDS:
        return
    changes = []
    if before.name != after.name:
        changes.append(f"Название: {before.name} → {after.name}")
    if before.permissions != after.permissions:
        changes.append("Изменены разрешения роли")
    if before.color != after.color:
        changes.append(f"Изменён цвет: {before.color} → {after.color}")
    if before.hoist != after.hoist:
        changes.append(f"Отображение отдельно: {before.hoist} → {after.hoist}")
    if changes:
        write_audit_log("ИЗМЕНЕНА РОЛЬ", f"{after.name} (ID: {after.id})\n" + "\n".join(changes), after.guild.id)


@bot.listen("on_member_ban")
async def audit_member_ban(guild, user):
    if guild.id in ALLOWED_GUILDS:
        write_audit_log("БАН УЧАСТНИКА", f"{user} (ID: {user.id})", guild.id)


@bot.listen("on_member_unban")
async def audit_member_unban(guild, user):
    if guild.id in ALLOWED_GUILDS:
        write_audit_log("РАЗБАН УЧАСТНИКА", f"{user} (ID: {user.id})", guild.id)


@bot.listen("on_voice_state_update")
async def audit_voice_state(member, before, after):
    if member.guild.id not in ALLOWED_GUILDS:
        return
    if before.channel != after.channel:
        old_name = before.channel.name if before.channel else "не в голосовом"
        new_name = after.channel.name if after.channel else "не в голосовом"
        write_audit_log("ИЗМЕНЕНИЕ ГОЛОСОВОГО КАНАЛА", f"{audit_member_label(member)}\n{old_name} → {new_name}", member.guild.id)


class TimestampedTee:
    """Пишет одновременно в консоль Bot-Hosting и в logs/latest.log, добавляя дату и время."""
    def __init__(self, console_stream, log_file, lock):
        self.console_stream = console_stream
        self.log_file = log_file
        self.lock = lock
        self.buffer = ""

    def write(self, text):
        if not isinstance(text, str):
            text = str(text)
        self.console_stream.write(text)
        with self.lock:
            self.buffer += text
            while "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                stamp = datetime.now(MSK).strftime("%Y-%m-%d %H:%M:%S")
                self.log_file.write(f"[{stamp}] {line}\n")
            self.log_file.flush()
        return len(text)

    def flush(self):
        self.console_stream.flush()
        with self.lock:
            if self.buffer:
                stamp = datetime.now(MSK).strftime("%Y-%m-%d %H:%M:%S")
                self.log_file.write(f"[{stamp}] {self.buffer}\n")
                self.buffer = ""
            self.log_file.flush()

    def isatty(self):
        return self.console_stream.isatty() if hasattr(self.console_stream, "isatty") else False

    def fileno(self):
        return self.console_stream.fileno()

    @property
    def encoding(self):
        return getattr(self.console_stream, "encoding", "utf-8")


def setup_session_logs():
    """Архивирует прошлый latest.log и начинает новый лог текущего запуска."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    if os.path.exists(LATEST_LOG_FILE) and os.path.getsize(LATEST_LOG_FILE) > 0:
        stamp = datetime.now(MSK).strftime("%Y-%m-%d-%H-%M-%S")
        archive_path = os.path.join(LOGS_DIR, f"{stamp}.log")
        suffix = 1
        while os.path.exists(archive_path):
            archive_path = os.path.join(LOGS_DIR, f"{stamp}-{suffix}.log")
            suffix += 1
        os.replace(LATEST_LOG_FILE, archive_path)

    log_file = open(LATEST_LOG_FILE, "w", encoding="utf-8", buffering=1)
    lock = threading.Lock()
    # Один потокобезопасный замок защищает общий файл stdout и stderr.
    sys.stdout = TimestampedTee(sys.__stdout__, log_file, lock)
    sys.stderr = TimestampedTee(sys.__stderr__, log_file, lock)
    print("========== WHITEGRIEF BOT SESSION STARTED ==========", flush=True)


if not TOKEN:
    raise RuntimeError("Не задан DISCORD_TOKEN. Добавь токен в переменные окружения Bot-Hosting.")

async def run_services():
    """Запускает Discord-бота и FastAPI в одном процессе Bot-Hosting."""
    from dashboard.backend.main import app as panel_app

    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(
        panel_app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    web_server = uvicorn.Server(config)

    print(f"🌐 Запускаю WhiteGrief Control Panel на порту {port}...", flush=True)
    bot_task = asyncio.create_task(bot.start(TOKEN), name="discord-bot")
    web_task = asyncio.create_task(web_server.serve(), name="control-panel")

    done, pending = await asyncio.wait(
        {bot_task, web_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
    web_server.should_exit = True
    await asyncio.gather(*pending, return_exceptions=True)

    for task in done:
        error = task.exception()
        if error:
            raise error


setup_session_logs()
asyncio.run(run_services())
