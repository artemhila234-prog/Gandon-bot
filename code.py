import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from datetime import datetime, timezone, timedelta

# ================== КОНФИГ ==================
TOKEN = os.getenv("DISCORD_TOKEN")
# --- Каналы и категории ---
REPORT_CHANNEL_ID = 1231958902474678364
JOIN_CHANNEL_ID = 1551952140929601576
CATEGORY_ID = 1551950227865608292
SHOP_CHANNEL_ID = 1564188124844662814  # ID канала для логов покупок
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
MOD_ROLE_IDS = [1546125576136560660]
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
    del pending_apps[member.id]

    await original_msg.clear_reaction('🕐')
    await original_msg.add_reaction('✅')

    new_nick = f"{nick} | {position}"
    if len(new_nick) > 32: new_nick = new_nick[:32]
    try:
        await member.edit(nick=new_nick, reason=f"Принят от {author.display_name}")
    except Exception as e:
        await ctx.send(f"⚠️ Не удалось изменить никнейм: {e}", delete_after=10)

    roles_to_add = [ctx.guild.get_role(rid) for rid in ROLES_TO_GIVE if ctx.guild.get_role(rid)]
    if roles_to_add:
        try:
            await member.add_roles(*roles_to_add, reason=f"Принят от {author.display_name}")
        except discord.Forbidden:
            await ctx.send("❌ Недостаточно прав для выдачи ролей (проверьте иерархию).")
            return

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
        await ctx.send(f"✅ {member.mention} принят! Создан личный канал {channel.mention}.")
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
    del pending_points[member.id]

    try:
        await original_msg.clear_reaction('🕐')
    except:
        pass
    await original_msg.add_reaction('✅')

    update_balance(member.id, points)
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
            pending_points[message.author.id] = {'nick': nick, 'points': points, 'link': link}
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
            pending_apps[message.author.id] = {'nick': nick, 'position': position, 'age': age}
            await message.add_reaction('🕐')
            approver_role = message.guild.get_role(APPROVER_ROLE_ID)
            if approver_role:
                await message.channel.send(
                    f"{approver_role.mention}, игрок {message.author.mention} ждёт твоего одобрения.\n"
                    f"Напиши **!принят** ответом на его сообщение."
                )
            else:
                await message.channel.send(
                    f"⚠️ Роль для верификации не найдена.\nИгрок {message.author.mention} ждёт одобрения. Напиши **!принят**."
                )
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

# ================== ЗАПУСК ==================
@bot.event
async def on_ready():
    print(f'Бот {bot.user} запущен!')

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

if not TOKEN:
    raise RuntimeError("Не задан DISCORD_TOKEN. Добавь токен в переменные окружения Bot-Hosting.")

bot.run(TOKEN)
