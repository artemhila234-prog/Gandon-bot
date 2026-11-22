import re
import discord
import asyncio
import aiohttp
import sys
import threading
from collections import deque
import uvicorn
from discord import app_commands
from discord.ext import commands
from aaaa.gastworld_sheets import sync_staff_row, remove_staff_row
import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta

# ================== КОНФИГ ==================
TOKEN = os.getenv("DISCORD_TOKEN")
# --- Каналы и категории ---
REPORT_CHANNEL_ID = 1231958902474678364
JOIN_CHANNEL_ID = 1563918554829422704
CATEGORY_ID = 1573332011739779164  # Категория личных каналов медиа на первом сервере
VERIFICATION_GUILD_ID = 1492974397001171176
SECONDARY_ROLE_GUILD_ID = 1454858971084230822
VERIFICATION_REVIEW_ROLE_ID = 1493607029053587647
VERIFICATION_COMMON_ROLE_ID = 1573415226186010795
VERIFICATION_TT_ROLE_ID = 1573415527932629173
VERIFICATION_YT_ROLE_ID = 1556575041657774100
SHOP_CHANNEL_ID = 1573032052666663032  # Единый канал логов GastWorld
AUDIT_LOG_CHANNEL_ID = 1573032052666663032  # Единый канал логов GastWorld
ROLE_ANNOUNCEMENT_CHANNEL_ID = 1532858494657495201  # Уведомления о выданных ролях
LOGS_DIR = "logs"
LATEST_LOG_FILE = os.path.join(LOGS_DIR, "latest.log")
WARN_COMMAND_CHANNEL_ID = 1546125784026972262  # Канал, где разрешено выполнять команды управления варнами
WARN_LOG_CHANNEL_ID = 1573032052666663032  # Единый канал логов GastWorld
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
MEDIA_TEAM_ROLE_ID = 1493196315205566545
MEDIA_TEAM_AUTO_ROLE_ID = 1573343622986862602
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

ALLOWED_GUILDS = [1492974397001171176]
# Роли доступа сайта всегда создаются и синхронизируются на первом сервере.
ACCESS_ROLES_GUILD_ID = 1492974397001171176

# Тикет-система работает исключительно на первом сервере.
TICKET_ALLOWED_GUILDS = [1492974397001171176]

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

cursor.execute('''CREATE TABLE IF NOT EXISTS media_staff_profiles (
    user_id INTEGER PRIMARY KEY,
    nickname TEXT NOT NULL,
    position TEXT NOT NULL,
    profile_url TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
cursor.execute('''CREATE TABLE IF NOT EXISTS verification_guide_config (
    channel_id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL
)''')

# Автоматическая миграция существующей базы: CREATE TABLE IF NOT EXISTS
# не добавляет столбцы в уже созданную таблицу.
cursor.execute("PRAGMA table_info(pending_requests)")
pending_request_columns = {row[1] for row in cursor.fetchall()}
if "message_id" not in pending_request_columns:
    cursor.execute("ALTER TABLE pending_requests ADD COLUMN message_id INTEGER")
conn.commit()

# TikTok reward rule: one point for every five video views (round down).
TIKTOK_VIEWS_PER_POINT = 5

# TikTok tables: pending links, linked accounts and one-time video rewards.
cursor.execute("""CREATE TABLE IF NOT EXISTS tiktok_pending (
    user_id INTEGER PRIMARY KEY, code TEXT NOT NULL, expected_username TEXT NOT NULL,
    oauth_state TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL, token_cipher TEXT,
    open_id TEXT, username TEXT, profile_url TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS tiktok_accounts (
    user_id INTEGER PRIMARY KEY, open_id TEXT NOT NULL UNIQUE, username TEXT NOT NULL,
    profile_url TEXT NOT NULL, token_cipher TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS tiktok_videos (
    video_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, views INTEGER NOT NULL,
    points INTEGER NOT NULL, rewarded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)""")
cursor.execute("DELETE FROM pending_requests WHERE request_type = 'points'")
cursor.execute("""CREATE TABLE IF NOT EXISTS support_tickets (channel_id TEXT PRIMARY KEY,guild_id TEXT NOT NULL,user_id TEXT NOT NULL,username TEXT NOT NULL,subject TEXT NOT NULL,description TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,closed_by TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS support_ticket_config (guild_id TEXT PRIMARY KEY,category_id TEXT,panel_channel_id TEXT,panel_message_id TEXT,accepting INTEGER NOT NULL DEFAULT 1)""")
try:
    cursor.execute("ALTER TABLE support_ticket_config ADD COLUMN accepting INTEGER NOT NULL DEFAULT 1")
except sqlite3.OperationalError:
    pass
conn.commit()

print(f"🗄️ База GastWorld: {os.path.abspath(DB_PATH)}", flush=True)

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
    cursor.execute(
        'INSERT INTO users (user_id, personal_channel_id) VALUES (?, ?) '
        'ON CONFLICT(user_id) DO UPDATE SET personal_channel_id = excluded.personal_channel_id',
        (int(user_id), int(channel_id))
    )
    conn.commit()

def get_personal_channel(user_id):
    cursor.execute('SELECT personal_channel_id FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

async def sync_staff_member_to_sheets(member, preserve_sheet_stats=None):
    if member is None:
        return "skip_member"
    try:
        profile = conn.execute("SELECT nickname, position, profile_url FROM media_staff_profiles WHERE user_id = ?", (int(member.id),)).fetchone()
        channel_id = get_personal_channel(member.id)
        if not profile:
            print(f"⚠️ [GOOGLE SHEETS] Не найден профиль участника {member.id} в media_staff_profiles.", flush=True)
            return "skip_profile"
        if not channel_id:
            print(f"⚠️ [GOOGLE SHEETS] Не найден личный канал участника {member.id} в users.", flush=True)
            return "skip_channel"
        nickname, position, profile_url = profile
        user_record_exists = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (int(member.id),)).fetchone() is not None
        if preserve_sheet_stats is None:
            preserve_sheet_stats = not user_record_exists
        data = get_user_data(member.id)
        personal_channel_url = f"https://discord.com/channels/{VERIFICATION_GUILD_ID}/{int(channel_id)}"
        role_ids = {role.id for role in member.roles}
        if 1493252228759290078 in role_ids:
            sheet_position = "Media Adm"
        elif 1493252086341566534 in role_ids:
            sheet_position = "TikTok+"
        elif 1493252439011365065 in role_ids:
            sheet_position = "YouTube+"
        else:
            sheet_position = "TikTok" if str(position).upper() == "TT" else "YouTube"
        row_number = await asyncio.to_thread(sync_staff_row, nickname=nickname, personal_channel_url=personal_channel_url, profile_url=profile_url, position=sheet_position, warns=data['warns'], discord_id=member.id, discord_username=member.name, points=data['balance'], preserve_stats=preserve_sheet_stats)
        print(f"📊 [GOOGLE SHEETS] Обновлена строка {row_number} для {member.id} ({position}).", flush=True)
        return "ok"
    except Exception as error:
        print(f"⚠️ [GOOGLE SHEETS] Не удалось обновить участника {member.id}: {error}", flush=True)
        return "error"

async def panel_sheets_candidates():
    guild = bot.get_guild(VERIFICATION_GUILD_ID)
    if guild is None:
        raise RuntimeError("Основной сервер Медиа не найден.")
    candidates = []
    async for member in guild.fetch_members(limit=None):
        if not any(role.id == MEDIA_TEAM_ROLE_ID for role in member.roles):
            continue
        profile = conn.execute("SELECT 1 FROM media_staff_profiles WHERE user_id = ?", (int(member.id),)).fetchone()
        if profile:
            continue
        channel_id = get_personal_channel(member.id)
        candidates.append({
            "user_id": str(member.id),
            "username": member.global_name or member.name,
            "discord_username": member.name,
            "personal_channel_id": str(channel_id) if channel_id else "",
        })
    candidates.sort(key=lambda item: item["username"].casefold())
    return {"candidates": candidates, "count": len(candidates), "role_id": str(MEDIA_TEAM_ROLE_ID)}


async def panel_sheets_add_staff(user_id, nickname, position, profile_url, personal_channel_id):
    guild = bot.get_guild(VERIFICATION_GUILD_ID)
    if guild is None:
        raise RuntimeError("Основной сервер Медиа не найден.")
    try:
        user_id = int(user_id)
        personal_channel_id = int(personal_channel_id)
    except (TypeError, ValueError):
        raise ValueError("Укажи корректные Discord ID участника и личного канала.")
    nickname = str(nickname or "").strip()[:100]
    position = str(position or "").strip().upper()
    profile_url = str(profile_url or "").strip()
    if not nickname:
        raise ValueError("Укажи никнейм участника.")
    if position not in {"TT", "YT"}:
        raise ValueError("Должность должна быть TT или YT.")
    if not profile_url.startswith(("https://", "http://")):
        raise ValueError("Укажи корректную ссылку на профиль.")
    if position == "TT" and "tiktok.com/@" not in profile_url.lower():
        raise ValueError("Для TT нужна ссылка на TikTok-профиль.")
    if position == "YT" and not any(host in profile_url.lower() for host in ("youtube.com/", "youtu.be/")):
        raise ValueError("Для YT нужна ссылка на YouTube-профиль.")
    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            raise ValueError("Участник не найден на основном сервере.")
    if not any(role.id == MEDIA_TEAM_ROLE_ID for role in member.roles):
        raise ValueError("У участника нет роли Команда медиа.")
    channel = guild.get_channel(personal_channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(personal_channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            raise ValueError("Личный канал не найден или бот не имеет к нему доступа.")
    if not isinstance(channel, discord.TextChannel) or channel.guild.id != VERIFICATION_GUILD_ID:
        raise ValueError("Выбранный личный канал должен быть текстовым каналом основного сервера Медиа.")

    conn.execute(
        """INSERT INTO media_staff_profiles (user_id, nickname, position, profile_url, updated_at)
           VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id) DO UPDATE SET
             nickname=excluded.nickname, position=excluded.position,
             profile_url=excluded.profile_url, updated_at=CURRENT_TIMESTAMP""",
        (user_id, nickname, position, profile_url),
    )
    had_user_record = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone() is not None
    conn.execute(
        """INSERT INTO users (user_id, balance, warns, personal_channel_id)
           VALUES (?, 0, 0, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             personal_channel_id=COALESCE(users.personal_channel_id, excluded.personal_channel_id)""",
        (user_id, personal_channel_id),
    )
    conn.commit()
    sync_result = await sync_staff_member_to_sheets(member, preserve_sheet_stats=not had_user_record)
    data = get_user_data(user_id)
    return {
        "user_id": str(user_id),
        "nickname": nickname,
        "position": position,
        "sheets_synced": sync_result == "ok",
        "sync_result": sync_result,
        "balance": data["balance"],
        "warns": data["warns"],
        "personal_channel_id": str(get_personal_channel(user_id) or ""),
    }


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
    # Только эта роль может принимать или отклонять заявки на первом сервере.
    return any(role.id == VERIFICATION_REVIEW_ROLE_ID for role in member.roles)

def has_points_role(member):
    if not APPROVER_POINTS_ROLE_IDS: return False
    return any(role.id in APPROVER_POINTS_ROLE_IDS for role in member.roles)

def has_povixa_role(member):
    if not POVIXA_ROLE_IDS: return False
    return any(role.id in POVIXA_ROLE_IDS for role in member.roles)

def get_msk_time_str():
    return datetime.now(MSK).strftime('%d.%m.%Y %H:%M')


# ================== TIKTOK ==================
TIKTOK_CONNECT_URL = os.getenv("TIKTOK_CONNECT_URL", "https://media.apps.bot-hosting.cloud/tiktok/login")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_VIDEO_RE = re.compile(r"https?://(?:(?:www|vm|vt)\.)?tiktok\.com/@[A-Za-z0-9._]+/video/(\d+)", re.I)
TIKTOK_PROFILE_RE = re.compile(r"^https?://(?:www\.)?tiktok\.com/@([A-Za-z0-9._]+)/?$", re.I)

def tiktok_fernet():
    from cryptography.fernet import Fernet
    key = os.getenv("TIKTOK_TOKEN_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError("Не задан TIKTOK_TOKEN_ENCRYPTION_KEY.")
    return Fernet(key.encode("utf-8"))

async def get_tiktok_tokens(user_id: int, *, pending: bool = False):
    table = "tiktok_pending" if pending else "tiktok_accounts"
    row = conn.execute(f"SELECT token_cipher FROM {table} WHERE user_id = ?", (int(user_id),)).fetchone()
    if not row or not row[0]:
        raise RuntimeError("TikTok не подключён. Сначала выполни /привязать_аккаунт.")
    try:
        payload = json.loads(tiktok_fernet().decrypt(row[0].encode("utf-8")).decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Не удалось расшифровать TikTok-токен. Проверь ключ шифрования на обоих хостингах.") from exc
    if int(payload.get("access_token_expires_at", 0)) <= int(datetime.now(timezone.utc).timestamp()) + 90:
        if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET or not payload.get("refresh_token"):
            raise RuntimeError("TikTok-токен истёк. Повтори привязку аккаунта.")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                data={"client_key": TIKTOK_CLIENT_KEY, "client_secret": TIKTOK_CLIENT_SECRET,
                      "grant_type": "refresh_token", "refresh_token": payload["refresh_token"]},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                refreshed = await response.json(content_type=None)
                if response.status != 200 or not refreshed.get("access_token"):
                    raise RuntimeError("TikTok не смог обновить доступ. Повтори привязку аккаунта.")
        now = int(datetime.now(timezone.utc).timestamp())
        payload["access_token"] = refreshed["access_token"]
        payload["refresh_token"] = refreshed.get("refresh_token", payload["refresh_token"])
        payload["access_token_expires_at"] = now + int(refreshed.get("expires_in", 86400))
        payload["refresh_token_expires_at"] = now + int(refreshed.get("refresh_expires_in", 31536000))
        encrypted = tiktok_fernet().encrypt(json.dumps(payload).encode("utf-8")).decode("utf-8")
        conn.execute(f"UPDATE {table} SET token_cipher = ? WHERE user_id = ?", (encrypted, int(user_id)))
        conn.commit()
    return payload

async def tiktok_get_user(access_token: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://open.tiktokapis.com/v2/user/info/?fields=open_id,username,bio_description,profile_deep_link",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as response:
            data = await response.json(content_type=None)
            if response.status != 200 or data.get("error", {}).get("code") not in (None, "ok", 0):
                raise RuntimeError("TikTok API не вернул профиль. Проверь разрешение user.info.profile.")
    return data.get("data", {}).get("user", {})

async def verify_tiktok_link(user_id: int):
    row = conn.execute(
        "SELECT code, expected_username, open_id, username, profile_url FROM tiktok_pending WHERE user_id = ? AND expires_at > ?",
        (int(user_id), datetime.now(timezone.utc).isoformat())
    ).fetchone()
    if not row:
        raise RuntimeError("Заявка на привязку истекла. Запусти /привязать_аккаунт ещё раз.")
    code, expected_username, saved_open_id, saved_username, saved_url = row
    tokens = await get_tiktok_tokens(user_id, pending=True)
    profile = await tiktok_get_user(tokens["access_token"])
    username = str(profile.get("username") or saved_username or "").lstrip("@")
    if not profile.get("open_id") or profile.get("open_id") != saved_open_id:
        raise RuntimeError("TikTok вернул другой аккаунт. Начни привязку заново.")
    if username.casefold() != expected_username.casefold():
        raise RuntimeError("Авторизован не тот TikTok-профиль, который был указан в команде.")
    if code.casefold() not in str(profile.get("bio_description") or "").casefold():
        return False, username, saved_url
    profile_url = str(profile.get("profile_deep_link") or saved_url or f"https://www.tiktok.com/@{username}")
    existing = conn.execute("SELECT user_id FROM tiktok_accounts WHERE open_id = ?", (profile["open_id"],)).fetchone()
    if existing and int(existing[0]) != int(user_id):
        raise RuntimeError("Этот TikTok-аккаунт уже привязан к другому Discord-пользователю.")
    conn.execute(
        """INSERT INTO tiktok_accounts (user_id, open_id, username, profile_url, token_cipher)
           SELECT user_id, open_id, username, ?, token_cipher FROM tiktok_pending WHERE user_id = ? AND 1=1
           ON CONFLICT(user_id) DO UPDATE SET open_id=excluded.open_id, username=excluded.username,
             profile_url=excluded.profile_url, token_cipher=excluded.token_cipher, updated_at=CURRENT_TIMESTAMP""",
        (profile_url, int(user_id))
    )
    conn.execute("DELETE FROM tiktok_pending WHERE user_id = ?", (int(user_id),))
    conn.commit()
    return True, username, profile_url

async def process_tiktok_video(message: discord.Message):
    match = TIKTOK_VIDEO_RE.search(message.content or "")
    if not match:
        await message.reply("❌ Нужна полная ссылка вида https://www.tiktok.com/@username/video/123...", mention_author=False)
        return
    video_id = match.group(1)
    account = conn.execute("SELECT username FROM tiktok_accounts WHERE user_id = ?", (message.author.id,)).fetchone()
    if not account:
        await message.reply("❌ TikTok ещё не привязан. Сначала выполни /привязать_аккаунт.", mention_author=False)
        return
    try:
        tokens = await get_tiktok_tokens(message.author.id)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://open.tiktokapis.com/v2/video/query/?fields=id,view_count,share_url",
                headers={"Authorization": f"Bearer {tokens['access_token']}", "Content-Type": "application/json"},
                json={"filters": {"video_ids": [video_id]}},
                timeout=aiohttp.ClientTimeout(total=25),
            ) as response:
                data = await response.json(content_type=None)
                if response.status != 200 or data.get("error", {}).get("code") not in (None, "ok", 0):
                    raise RuntimeError("TikTok API не смог проверить ролик. Возможно, видео приватное или доступ временно ограничен.")
        video = next((item for item in data.get("data", {}).get("videos", []) if str(item.get("id")) == video_id), None)
        if not video:
            await message.reply("❌ TikTok не подтвердил, что это видео принадлежит привязанному аккаунту.", mention_author=False)
            return
        views = max(0, int(video.get("view_count", 0)))
        points = views // TIKTOK_VIEWS_PER_POINT
        if points < 1:
            await message.reply(f"ℹ️ У ролика пока {views} просмотров. Для начисления нужен минимум {TIKTOK_VIEWS_PER_POINT}. Можешь отправить ссылку позже.", mention_author=False)
            return
        conn.execute("BEGIN IMMEDIATE")
        inserted = conn.execute(
            "INSERT OR IGNORE INTO tiktok_videos (video_id, user_id, views, points) VALUES (?, ?, ?, ?)",
            (video_id, message.author.id, views, points)
        ).rowcount
        if not inserted:
            conn.rollback()
            await message.reply("⚠️ Этот ролик уже отправлялся. Повторное начисление за него невозможно.", mention_author=False)
            return
        conn.execute(
            """INSERT INTO users (user_id, balance, warns, personal_channel_id)
               VALUES (?, ?, 0, NULL)
               ON CONFLICT(user_id) DO UPDATE SET balance = users.balance + excluded.balance""",
            (message.author.id, points)
        )
        conn.commit()
        balance = int(conn.execute("SELECT balance FROM users WHERE user_id = ?", (message.author.id,)).fetchone()[0])
        await sync_staff_member_to_sheets(message.author)
        embed = discord.Embed(title="🎉 Баллы за TikTok начислены",
            description=f"Видео принадлежит привязанному аккаунту **@{account[0]}**.", color=0x2ECC71)
        embed.add_field(name="Просмотры", value=f"{views:,}".replace(",", " "), inline=True)
        embed.add_field(name="Начислено", value=f"**{points:,}** баллов".replace(",", " "), inline=True)
        embed.add_field(name="Новый баланс", value=f"**{balance:,}** баллов".replace(",", " "), inline=True)
        embed.add_field(name="Правило", value=f"{TIKTOK_VIEWS_PER_POINT} просмотров = 1 балл. За один ролик начисление производится только один раз.", inline=False)
        embed.add_field(name="Видео", value=f"[Открыть ролик](https://www.tiktok.com/@{account[0]}/video/{video_id})", inline=False)
        await message.reply(embed=embed, mention_author=False)
    except Exception as exc:
        if conn.in_transaction:
            conn.rollback()
        await message.reply(f"❌ Не удалось проверить TikTok: {str(exc)[:350]}", mention_author=False)

class TikTokVerifyView(discord.ui.View):
    def __init__(self, user_id: int, connect_url: str):
        super().__init__(timeout=900)
        self.user_id = int(user_id)
        self.add_item(discord.ui.Button(label="Подключить TikTok", style=discord.ButtonStyle.link, url=connect_url))
        button = discord.ui.Button(label="Проверить", style=discord.ButtonStyle.success)
        button.callback = self.verify
        self.add_item(button)

    async def verify(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Эта кнопка предназначена не для тебя.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            success, username, profile_url = await verify_tiktok_link(self.user_id)
            if not success:
                await interaction.followup.send("Код пока не найден в BIO. Добавь его в описание TikTok-профиля и нажми Проверить ещё раз.", ephemeral=True)
                return
            for child in self.children:
                child.disabled = True
            try:
                await interaction.message.edit(view=self)
            except discord.HTTPException as edit_error:
                print(f"[TIKTOK] Не удалось отключить кнопку: {edit_error}", flush=True)

            await interaction.followup.send(
                f"✅ TikTok успешно привязан: [@{username}]({profile_url}). Теперь отправляй ссылки на свои ролики в личный канал.",
                ephemeral=True
            )
        except Exception as exc:
            await interaction.followup.send(f"❌ {str(exc)[:350]}", ephemeral=True)

@bot.tree.command(name="привязать_аккаунт", description="Привязать TikTok-профиль для начисления баллов")
@app_commands.describe(profile_url="Ссылка на твой TikTok-профиль")
async def tiktok_link_command(interaction: discord.Interaction, profile_url: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Команда доступна только на сервере GastWorld.", ephemeral=True)
        return
    match = TIKTOK_PROFILE_RE.match(profile_url.strip())
    if not match:
        await interaction.response.send_message("❌ Укажи ссылку в формате https://www.tiktok.com/@username.", ephemeral=True)
        return
    username = match.group(1).lstrip("@")
    import secrets as secrets_module
    code = "".join(secrets_module.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5))
    oauth_state = secrets_module.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    connect_url = f"{TIKTOK_CONNECT_URL}?state={oauth_state}"
    conn.execute(
        """INSERT INTO tiktok_pending (user_id, code, expected_username, oauth_state, expires_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET code=excluded.code, expected_username=excluded.expected_username,
             oauth_state=excluded.oauth_state, expires_at=excluded.expires_at,
             token_cipher=NULL, open_id=NULL, username=NULL, profile_url=NULL""",
        (interaction.user.id, code, username, oauth_state, expires_at)
    )
    conn.commit()
    await interaction.response.send_message(
        f"**Привязка TikTok — шаг 1 из 3**\n\n"
        f"1. Добавь этот код в BIO профиля **@{username}**:\n## {code}\n"
        "2. Нажми Подключить TikTok и разреши доступ приложению GastWorld.\n"
        "3. Вернись сюда и нажми Проверить.\n\nСсылка и код действуют 15 минут.",
        view=TikTokVerifyView(interaction.user.id, connect_url), ephemeral=True
    )



# ================== SUPPORT TICKETS ==================
TICKET_CATEGORY_NAME = "📌› бот"
TICKET_PANEL_CHANNEL_NAME = "❗・тикет-баги"
TICKET_PANEL_CUSTOM_ID = "gastworld:tickets:create"

def ticket_is_staff(member):
    ids = {r.id for r in getattr(member, "roles", [])}
    staff_ids = set(STAFF_ROLES) | set(MOD_ROLE_IDS) | {1546125455633944598,1546125498340614195,1546125469093732372,1546125465482174484,1547654044263252038,1546125472897961984,1546125480321749053,1550200782177968178,1567181454947917864,1567181456059535380,1567181457212833822}
    return bool(ids.intersection(staff_ids))

def ticket_accepting(guild_id):
    row = conn.execute("SELECT accepting FROM support_ticket_config WHERE guild_id=?", (str(guild_id),)).fetchone()
    return bool(row[0]) if row else True

def ticket_embed_panel(guild_id=None):
    guild_id = int(guild_id or TICKET_ALLOWED_GUILDS[0])
    accepting = ticket_accepting(guild_id)
    description = ("Нашёл баг или ошибку в Discord-боте либо на сайте GastWorld?\n\nНажми **«Создать тикет»** ниже и опиши проблему — команда поддержки увидит обращение и поможет разобраться.\n\nУкажи, что произошло и как повторить ошибку. При необходимости приложи скриншоты. Для каждой проблемы создавай отдельный тикет." if accepting else "Приём новых обращений временно закрыт.\n\nСуществующие тикеты продолжают работать. Попробуй отправить обращение позже.")
    embed = discord.Embed(title="❗ Поддержка GastWorld", description=description, color=0xFFFFFF)
    embed.set_footer(text="GastWorld • Служба поддержки")
    return embed

class TicketCreateModal(discord.ui.Modal, title="Новое обращение"):
    subject = discord.ui.TextInput(label="Кратко опиши проблему", placeholder="Например: ошибка при покупке", max_length=100, required=True)
    description = discord.ui.TextInput(label="Подробности", placeholder="Что произошло и как повторить ошибку?", style=discord.TextStyle.paragraph, max_length=1800, required=True)
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        if guild is None or guild.id not in TICKET_ALLOWED_GUILDS:
            await interaction.followup.send("Тикеты доступны только на сервере GastWorld.", ephemeral=True); return
        if not ticket_accepting(guild.id):
            await interaction.followup.send("🚫 Приём новых тикетов сейчас закрыт. Попробуй позже.", ephemeral=True); return
        old = conn.execute("SELECT channel_id FROM support_tickets WHERE guild_id=? AND user_id=? AND status='open'", (str(guild.id),str(interaction.user.id))).fetchone()
        if old:
            old_channel = guild.get_channel(int(old[0]))
            if old_channel:
                await interaction.followup.send(f"У тебя уже есть открытый тикет: {old_channel.mention}", ephemeral=True); return
            conn.execute("UPDATE support_tickets SET status='closed' WHERE channel_id=?", (str(old[0]),)); conn.commit()
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if category is None: category = await guild.create_category(TICKET_CATEGORY_NAME, reason="Категория тикетов GastWorld")
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False), interaction.user: discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True,attach_files=True,embed_links=True)}
        if guild.me: overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True,send_messages=True,manage_channels=True,read_message_history=True)
        for role_id in set(STAFF_ROLES)|set(MOD_ROLE_IDS)|{1567181454947917864,1567181456059535380,1567181457212833822}:
            role = guild.get_role(role_id)
            if role: overwrites[role] = discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True)
        slug = re.sub(r"[^a-z0-9-]+","-",interaction.user.name.lower()).strip("-")[:35] or "user"
        channel = await guild.create_text_channel(name=f"📌・тикет-{slug}",category=category,topic=f"GastWorld ticket | user_id={interaction.user.id} | status=open",overwrites=overwrites,reason=f"Тикет от {interaction.user}")
        conn.execute("INSERT INTO support_tickets(channel_id,guild_id,user_id,username,subject,description,status) VALUES(?,?,?,?,?,?,'open')",(str(channel.id),str(guild.id),str(interaction.user.id),str(interaction.user),str(self.subject.value),str(self.description.value))); conn.commit()
        embed = discord.Embed(title=f"🎫 {self.subject.value}",description=self.description.value,color=0x8B5CF6)
        embed.add_field(name="Автор",value=f"{interaction.user.mention}\nID: {interaction.user.id}",inline=True)
        embed.add_field(name="Статус",value="🟢 Открыт",inline=True)
        embed.set_footer(text="GastWorld • Тикет поддержки")
        await channel.send(content=f"{interaction.user.mention} · команда поддержки",embed=embed,view=TicketControlView())
        await interaction.followup.send(f"✅ Тикет создан: {channel.mention}",ephemeral=True)

class TicketPanelView(discord.ui.View):
    def __init__(self, guild_id=None):
        super().__init__(timeout=None)
        guild_id = int(guild_id or TICKET_ALLOWED_GUILDS[0])
        accepting = ticket_accepting(guild_id)
        button = discord.ui.Button(label="Создать тикет" if accepting else "Приём закрыт",style=discord.ButtonStyle.secondary,emoji="🎫",custom_id=TICKET_PANEL_CUSTOM_ID,disabled=not accepting)
        button.callback = self.create
        self.add_item(button)
    async def create(self, interaction): await interaction.response.send_modal(TicketCreateModal())

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for label,style,emoji,cid,status in (("Закрыть",discord.ButtonStyle.secondary,"🔒","gastworld:tickets:close","closed"),("Переоткрыть",discord.ButtonStyle.success,"🔓","gastworld:tickets:reopen","open"),("Решено",discord.ButtonStyle.primary,"✅","gastworld:tickets:resolve","resolved")):
            button=discord.ui.Button(label=label,style=style,emoji=emoji,custom_id=cid)
            button.callback=self.make_callback(status)
            self.add_item(button)
    def make_callback(self,status):
        async def callback(interaction):
            row=conn.execute("SELECT user_id FROM support_tickets WHERE channel_id=?",(str(interaction.channel_id),)).fetchone()
            if not row: await interaction.response.send_message("Тикет не найден.",ephemeral=True); return
            if str(interaction.user.id)!=str(row[0]) and not ticket_is_staff(interaction.user):
                await interaction.response.send_message("Недостаточно прав.",ephemeral=True); return
            await interaction.response.defer(ephemeral=True, thinking=True)
            try:
                await set_ticket_status(str(interaction.channel_id),status,str(interaction.user))
            except Exception as error:
                await interaction.followup.send(f"Ошибка изменения тикета: {str(error)[:300]}",ephemeral=True)
                return
            await interaction.followup.send({"open":"🟢 Тикет переоткрыт.","closed":"🔒 Тикет закрыт.","resolved":"✅ Отмечен как решённый."}[status],ephemeral=True)
        return callback

async def set_ticket_status(channel_id,status,actor="Dashboard"):
    if status not in {"open","closed","resolved"}: raise ValueError("Неизвестный статус.")
    row=conn.execute("SELECT guild_id,user_id,subject,description FROM support_tickets WHERE channel_id=?",(str(channel_id),)).fetchone()
    if not row: raise ValueError("Тикет не найден.")
    guild=bot.get_guild(int(row[0])); channel=guild.get_channel(int(channel_id)) if guild else None
    if channel is None: raise ValueError("Канал тикета не найден.")
    member=guild.get_member(int(row[1]))
    if member is None:
        try: member=await guild.fetch_member(int(row[1]))
        except (discord.NotFound,discord.Forbidden): member=None
    if member:
        await channel.set_permissions(member,view_channel=True,send_messages=(status=="open"),read_message_history=True,attach_files=(status=="open"))
    await channel.edit(topic=f"GastWorld ticket | user_id={row[1]} | status={status}")
    # Синхронизируем Embed в самом тикете, независимо от того, откуда нажали кнопку.
    status_labels={"open":"🟢 Открыт","closed":"🔒 Закрыт","resolved":"✅ Решено"}
    status_colors={"open":0xFFFFFF,"closed":0x777777,"resolved":0xBDBDBD}
    try:
        async for message in channel.history(limit=30,oldest_first=True):
            if message.author == bot.user and message.embeds and message.embeds[0].title == f"🎫 {row[2]}":
                embed=message.embeds[0].copy()
                embed.color=status_colors[status]
                for index,field in enumerate(embed.fields):
                    if field.name=="Статус":
                        embed.set_field_at(index,name="Статус",value=status_labels[status],inline=field.inline)
                        break
                else:
                    embed.add_field(name="Статус",value=status_labels[status],inline=True)
                await message.edit(embed=embed,view=TicketControlView())
                break
    except (discord.Forbidden,discord.HTTPException) as error:
        print(f"⚠️ [ТИКЕТЫ] Не удалось обновить Embed тикета {channel_id}: {error}",flush=True)
    conn.execute("UPDATE support_tickets SET status=?,updated_at=CURRENT_TIMESTAMP,closed_by=? WHERE channel_id=?",(status,None if status=="open" else str(actor)[:100],str(channel_id)))
    conn.commit()
    return {"channel_id":str(channel_id),"status":status}

async def ensure_ticket_system(guild):
    category=discord.utils.get(guild.categories,name=TICKET_CATEGORY_NAME)
    if category is None: category=await guild.create_category(TICKET_CATEGORY_NAME,reason="Категория тикетов GastWorld")
    overwrites={guild.default_role:discord.PermissionOverwrite(view_channel=True,send_messages=False,read_message_history=True)}
    if guild.me: overwrites[guild.me]=discord.PermissionOverwrite(view_channel=True,send_messages=True,manage_channels=True,read_message_history=True)
    panel=discord.utils.get(guild.text_channels,name=TICKET_PANEL_CHANNEL_NAME)
    if panel is None: panel=await guild.create_text_channel(TICKET_PANEL_CHANNEL_NAME,category=category,overwrites=overwrites,reason="Панель тикетов GastWorld")
    else:
        if panel.category_id!=category.id: await panel.edit(category=category)
        await panel.edit(overwrites=overwrites)
    conn.execute("INSERT INTO support_ticket_config(guild_id,category_id,panel_channel_id) VALUES(?,?,?) ON CONFLICT(guild_id) DO UPDATE SET category_id=excluded.category_id,panel_channel_id=excluded.panel_channel_id",(str(guild.id),str(category.id),str(panel.id))); conn.commit()
    saved=conn.execute("SELECT panel_message_id FROM support_ticket_config WHERE guild_id=?",(str(guild.id),)).fetchone()
    panel_message=None
    if saved and saved[0]:
        try: panel_message=await panel.fetch_message(int(saved[0]))
        except (discord.NotFound,ValueError): pass
    if panel_message is None:
        async for candidate in panel.history(limit=50):
            if candidate.author==bot.user and candidate.embeds and candidate.embeds[0].title=="❗ Поддержка GastWorld": panel_message=candidate; break
    if panel_message is None: panel_message=await panel.send(embed=ticket_embed_panel(guild.id),view=TicketPanelView(guild.id))
    else: await panel_message.edit(embed=ticket_embed_panel(guild.id),view=TicketPanelView(guild.id))
    conn.execute("UPDATE support_ticket_config SET panel_message_id=? WHERE guild_id=?",(str(panel_message.id),str(guild.id))); conn.commit()
    print(f"🎫 [ТИКЕТЫ] Панель готова: #{panel.name}; категория {category.name}",flush=True)


pending_apps = {}

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
    print(f"💾 Заявка сохранена: type={request_type}, user_id={user_id}, message_id={message_id}, db={DB_PATH}", flush=True)

def delete_pending_request(request_type, user_id):
    conn.execute(
        "DELETE FROM pending_requests WHERE request_type = ? AND user_id = ?",
        (request_type, user_id)
    )
    conn.commit()

def purge_user_data(user_id):
    """Полностью удаляет локальные данные пользователя из базы бота."""
    user_id = int(user_id)
    with conn:
        conn.execute("DELETE FROM purchases WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM reports WHERE author_id = ?", (user_id,))
        # Keep pending applications even if player data is purged.
        # Moderators must still be able to approve or reject the saved request.
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM media_staff_profiles WHERE user_id = ?", (user_id,))
    pending_apps.pop(user_id, None)

async def reconcile_server_players(guild):
    """Очищает данные ушедших игроков, сохраняя действующий состав Медиа."""
    kept_role_id = 1546125522675962027
    # Профили Медиа — отдельная категория пользователей: они могут не иметь
    # старую роль игрока, поэтому сохраняем их, пока они состоят на сервере.
    media_profile_ids = {
        int(row[0]) for row in conn.execute(
            "SELECT user_id FROM media_staff_profiles"
        ).fetchall()
    }
    present_with_role = set()
    async for member in guild.fetch_members(limit=None):
        has_legacy_player_role = any(role.id == kept_role_id for role in member.roles)
        has_saved_media_profile = member.id in media_profile_ids
        if has_legacy_player_role or has_saved_media_profile:
            present_with_role.add(member.id)

    db_ids = {
        int(row[0]) for row in conn.execute("SELECT user_id FROM users").fetchall()
    }
    # Участники с сохранённым профилем Медиа не удаляются из-за отсутствия
    # устаревшей роли игрока. Данные очищаются, если пользователь покинул сервер
    # или не относится ни к действующим игрокам, ни к сохранённому составу Медиа.
    to_purge = db_ids - present_with_role
    for user_id in to_purge:
        purge_user_data(user_id)
    pending_count = conn.execute("SELECT COUNT(*) FROM pending_requests").fetchone()[0]
    print(
        f"🧹 Очистка базы: сохранено {len(present_with_role & db_ids)} записей игроков/Медиа, "
        f"удалено {len(to_purge)}; профилей Медиа сохранено {len(media_profile_ids & present_with_role)}; "
        f"ожидающих заявок сохранено {pending_count}.",
        flush=True
    )

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
            # Старые заявки без Embed-панели не должны блокировать повторную подачу.
            if data.get("panel_message_id") and int(data.get("guild_id", 0)) == VERIFICATION_GUILD_ID:
                pending_apps[int(user_id)] = data
            else:
                conn.execute(
                    "DELETE FROM pending_requests WHERE request_type = 'join' AND user_id = ?",
                    (int(user_id),)
                )
                print(f"ℹ️ [ВЕРИФИКАЦИЯ] Старая заявка {user_id} сброшена: можно подать заново.", flush=True)
    conn.commit()

load_pending_requests()

# ================== АВТООЧИСТКА ДАННЫХ ИГРОКОВ ==================
@bot.event
async def on_member_remove(member):
    if member.guild.id == 1492974397001171176:
        try:
            await asyncio.to_thread(remove_staff_row, member.id)
        except Exception as error:
            print(f"⚠️ [GOOGLE SHEETS] Не удалось удалить строку {member.id}: {error}", flush=True)
        purge_user_data(member.id)
        print(f"🧹 Удалены данные ушедшего участника {member.id}")

@bot.event
async def on_member_update(before, after):
    if after.guild.id != VERIFICATION_GUILD_ID:
        return
    kept_role_id = 1546125522675962027
    had_role = any(role.id == kept_role_id for role in before.roles)
    has_role = any(role.id == kept_role_id for role in after.roles)
    if had_role and not has_role:
        # Снятие старой роли игрока не должно удалять данные действующего
        # сотрудника Медиа: состав теперь определяется сохранённым профилем.
        media_profile = conn.execute(
            "SELECT 1 FROM media_staff_profiles WHERE user_id = ?",
            (int(after.id),)
        ).fetchone()
        if media_profile:
            print(
                f"ℹ️ [ОЧИСТКА] У {after.id} снята старая роль игрока, "
                "но профиль Медиа сохранён; данные и строка таблицы не удаляются.",
                flush=True
            )
            return
        try:
            await asyncio.to_thread(remove_staff_row, after.id)
        except Exception as error:
            print(f"⚠️ [GOOGLE SHEETS] Не удалось удалить строку {after.id}: {error}", flush=True)
        purge_user_data(after.id)
        print(f"🧹 Удалены данные участника {after.id}: снята роль игрока", flush=True)

# ================== АВТОРОЛЬ ДЛЯ КОМАНДЫ МЕДИА ==================
async def sync_media_team_member_role(guild):
    team_role = guild.get_role(MEDIA_TEAM_ROLE_ID)
    required_role = guild.get_role(MEDIA_TEAM_AUTO_ROLE_ID)
    if team_role is None:
        print(f"⚠️ [ИГРОКИ] Не найдена роль Команда медиа {MEDIA_TEAM_ROLE_ID}.", flush=True)
        return
    if required_role is None:
        print(f"⚠️ [ИГРОКИ] Не найдена роль для автоматической выдачи {MEDIA_TEAM_AUTO_ROLE_ID}.", flush=True)
        return
    updated = 0
    async for member in guild.fetch_members(limit=None):
        if member.bot or team_role not in member.roles or required_role in member.roles:
            continue
        try:
            await member.add_roles(required_role, reason="Автовыдача роли участнику Команды медиа")
            updated += 1
            print(f"✅ [ИГРОКИ] Выдана роль {required_role.name} участнику {member} ({member.id}).", flush=True)
        except (discord.Forbidden, discord.HTTPException) as error:
            print(f"❌ [ИГРОКИ] Не удалось выдать роль {required_role.id} участнику {member.id}: {error}", flush=True)
    print(f"🔄 [ИГРОКИ] Проверка Команды медиа завершена. Выдано ролей: {updated}.", flush=True)


@bot.listen("on_member_update")
async def auto_assign_media_team_role(before, after):
    if after.guild.id != VERIFICATION_GUILD_ID:
        return
    had_team_role = any(role.id == MEDIA_TEAM_ROLE_ID for role in before.roles)
    has_team_role = any(role.id == MEDIA_TEAM_ROLE_ID for role in after.roles)
    has_required_role = any(role.id == MEDIA_TEAM_AUTO_ROLE_ID for role in after.roles)
    if has_team_role and not had_team_role and not has_required_role:
        role = after.guild.get_role(MEDIA_TEAM_AUTO_ROLE_ID)
        if role is None:
            print(f"⚠️ [ИГРОКИ] Не найдена роль для автоматической выдачи {MEDIA_TEAM_AUTO_ROLE_ID}.", flush=True)
            return
        try:
            await after.add_roles(role, reason="Автовыдача роли участнику Команды медиа")
            print(f"✅ [ИГРОКИ] Выдана роль {role.name} участнику {after} ({after.id}).", flush=True)
        except (discord.Forbidden, discord.HTTPException) as error:
            print(f"❌ [ИГРОКИ] Не удалось выдать роль {role.id} участнику {after.id}: {error}", flush=True)


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

# -------- /sheets_add_staff --------
@bot.tree.command(name="sheets_add_staff", description="Добавить участника с ролью Команда медиа в таблицу")
@app_commands.describe(
    member="Участник с ролью Команда медиа",
    nickname="Никнейм для таблицы",
    position="Платформа участника",
    profile_url="Ссылка на TikTok или YouTube профиль",
    personal_channel="Личный текстовый канал участника",
)
@app_commands.choices(position=[
    app_commands.Choice(name="TikTok (TT)", value="TT"),
    app_commands.Choice(name="YouTube (YT)", value="YT"),
])
async def sheets_add_staff(
    interaction: discord.Interaction,
    member: discord.Member,
    nickname: str,
    position: app_commands.Choice[str],
    profile_url: str,
    personal_channel: discord.TextChannel,
):
    if interaction.guild_id != VERIFICATION_GUILD_ID:
        await interaction.response.send_message("❌ Команда доступна только на основном сервере Медиа.", ephemeral=True)
        return
    if not (interaction.user.guild_permissions.administrator or has_verification_role(interaction.user)):
        await interaction.response.send_message("❌ Недостаточно прав. Нужна роль проверки заявок или Administrator.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        result = await panel_sheets_add_staff(
            member.id, nickname, position.value, profile_url, personal_channel.id
        )
    except (ValueError, RuntimeError) as error:
        await interaction.followup.send(f"❌ {error}", ephemeral=True)
        return
    status = "✅ Профиль добавлен в базу и Google Sheets." if result["sheets_synced"] else "⚠️ Профиль сохранён в базе, но запись в Google Sheets не удалась. Запусти /sheets_sync после проверки доступа Google."
    await interaction.followup.send(
        f"{status}\n👤 {discord.utils.escape_markdown(result['nickname'])} · **{result['position']}**\n"
        f"💰 Баланс сохранён: **{result['balance']}** · Выговоры сохранены: **{result['warns']}**",
        ephemeral=True,
    )


# -------- /unstaff --------
@bot.tree.command(name="unstaff", description="Убрать участника из таблицы состава Медиа")
@app_commands.describe(member="Участник, которого нужно убрать из состава и таблицы")
async def unstaff(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild_id != VERIFICATION_GUILD_ID:
        await interaction.response.send_message("❌ Команда доступна только на основном сервере Медиа.", ephemeral=True)
        return
    if not (interaction.user.guild_permissions.administrator or has_verification_role(interaction.user)):
        await interaction.response.send_message("❌ Недостаточно прав. Нужна роль проверки заявок или Administrator.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        row_removed = await asyncio.to_thread(remove_staff_row, member.id)
    except Exception as error:
        print(f"⚠️ [GOOGLE SHEETS] Не удалось убрать участника {member.id} из таблицы: {error}", flush=True)
        await interaction.followup.send(
            "❌ Не удалось изменить Google Sheets. Профиль в базе оставлен, чтобы /sheets_sync не добавил участника обратно. Проверь доступ Google и повтори команду.",
            ephemeral=True,
        )
        return

    # Удаляем профиль из источника /sheets_sync, но не трогаем баланс,
    # выговоры, покупки, личный канал и Discord-роли участника.
    conn.execute("DELETE FROM media_staff_profiles WHERE user_id = ?", (int(member.id),))
    conn.commit()

    if row_removed:
        message = f"✅ {member.mention} убран из таблицы Google Sheets и из сохранённого состава Медиа."
    else:
        message = f"ℹ️ Строка {member.mention} в Google Sheets не найдена; профиль удалён из сохранённого состава, чтобы /sheets_sync не добавил его обратно."
    await interaction.followup.send(message, ephemeral=True)


# -------- /sheets_sync --------
@bot.tree.command(name="sheets_sync", description="Синхронизировать действующий состав Медиа с Google Sheets")
async def sheets_sync(interaction: discord.Interaction):
    if interaction.guild_id != VERIFICATION_GUILD_ID:
        await interaction.response.send_message("❌ Команда доступна только на основном сервере Медиа.", ephemeral=True)
        return
    if not (interaction.user.guild_permissions.administrator or has_verification_role(interaction.user)):
        await interaction.response.send_message("❌ Недостаточно прав. Нужна роль проверки заявок или Administrator.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = bot.get_guild(VERIFICATION_GUILD_ID)
    if guild is None:
        await interaction.followup.send("❌ Основной сервер Медиа не найден ботом.", ephemeral=True)
        return

    profile_ids = [
        int(row[0]) for row in conn.execute(
            "SELECT user_id FROM media_staff_profiles ORDER BY CASE UPPER(position) WHEN 'TT' THEN 0 ELSE 1 END, nickname COLLATE NOCASE"
        ).fetchall()
    ]
    if not profile_ids:
        await interaction.followup.send("ℹ️ В базе пока нет сохранённых профилей состава Медиа.", ephemeral=True)
        return

    counts = {"ok": 0, "error": 0, "skip_member": 0, "skip_profile": 0, "skip_channel": 0}
    for user_id in profile_ids:
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                counts["skip_member"] += 1
                continue
        result = await sync_staff_member_to_sheets(member)
        counts[result if result in counts else "error"] += 1

    summary = (
        "📊 **Синхронизация Google Sheets завершена**\n"
        f"✅ Обновлено: **{counts['ok']}**\n"
        f"⚠️ Ошибок записи: **{counts['error']}**\n"
        f"⏭️ Пропущено (нет на сервере): **{counts['skip_member']}**\n"
        f"⏭️ Пропущено (нет профиля): **{counts['skip_profile']}**\n"
        f"⏭️ Пропущено (нет личного канала): **{counts['skip_channel']}**\n\n"
        "Верхний блок таблицы и столбец F «Отпуск» команда не изменяет."
    )
    await interaction.followup.send(summary, ephemeral=True)

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
        f"📊 {TIKTOK_VIEWS_PER_POINT} просмотров = 1 балл\n"
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
        "🎁 Кейс с Супер Риликами — 3 000 баллов\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📜・**УСЛУГИ**\n"
        "📝 Снятие 1 выговора — 400 баллов\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📜・**ПРАВИЛА МАГАЗИНА**\n"
        f"🔹 За каждые {TIKTOK_VIEWS_PER_POINT} просмотров начисляется 1 балл.\n"
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
    await sync_staff_member_to_sheets(interaction.user)

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
    if interaction.channel_id != WARN_COMMAND_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Команды управления варнами доступны только в канале <#{WARN_COMMAND_CHANNEL_ID}>.",
            ephemeral=True
        )
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
    await sync_staff_member_to_sheets(игрок)

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

    embed = discord.Embed(
        title="⚠️ ВАРН ВЫДАН",
        color=0xE05265,
        timestamp=datetime.now(MSK)
    )
    embed.add_field(name="Игрок", value=f"{игрок.display_name} ({игрок.mention})", inline=False)
    embed.add_field(name="Действие выполнил", value=f"{interaction.user.display_name} ({interaction.user.mention})", inline=False)
    embed.add_field(name="Количество варнов", value=f"{current_warns} → {new_warns}", inline=False)
    embed.add_field(name="Причина", value=причина[:1000], inline=False)
    embed.add_field(name="Источник", value="Discord-команда /warn", inline=False)
    embed.set_footer(text="GastWorld • Журнал модерации")
    await interaction.response.send_message("✅ Варн выдан и записан в единый журнал.", ephemeral=True)
    log_channel = interaction.guild.get_channel(WARN_LOG_CHANNEL_ID)
    if log_channel is None:
        log_channel = await interaction.guild.fetch_channel(WARN_LOG_CHANNEL_ID)
    await log_channel.send(embed=embed)

# -------- /unwarn --------
@bot.tree.command(name="unwarn", description="Снять одно предупреждение с игрока")
@app_commands.describe(игрок="Игрок, у которого снимается предупреждение", причина="Причина снятия")
async def unwarn(interaction: discord.Interaction, игрок: discord.Member, причина: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message("❌ Этот бот не настроен для этого сервера.", ephemeral=True)
        return
    if interaction.channel_id != WARN_COMMAND_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Команды управления варнами доступны только в канале <#{WARN_COMMAND_CHANNEL_ID}>.",
            ephemeral=True
        )
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
    await sync_staff_member_to_sheets(игрок)

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

    embed = discord.Embed(
        title="✅ ВАРН СНЯТ",
        color=0x55C995,
        timestamp=datetime.now(MSK)
    )
    embed.add_field(name="Игрок", value=f"{игрок.display_name} ({игрок.mention})", inline=False)
    embed.add_field(name="Действие выполнил", value=f"{interaction.user.display_name} ({interaction.user.mention})", inline=False)
    embed.add_field(name="Количество варнов", value=f"{current_warns} → {new_warns}", inline=False)
    embed.add_field(name="Причина", value=причина[:1000], inline=False)
    embed.add_field(name="Источник", value="Discord-команда /unwarn", inline=False)
    embed.set_footer(text="GastWorld • Журнал модерации")
    await interaction.response.send_message("✅ Варн снят и записан в единый журнал.", ephemeral=True)
    log_channel = interaction.guild.get_channel(WARN_LOG_CHANNEL_ID)
    if log_channel is None:
        log_channel = await interaction.guild.fetch_channel(WARN_LOG_CHANNEL_ID)
    await log_channel.send(embed=embed)

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
        try:
            await asyncio.to_thread(remove_staff_row, игрок.id)
        except Exception as error:
            print(f"⚠️ [GOOGLE SHEETS] Не удалось удалить строку {игрок.id}: {error}", flush=True)
        conn.execute("DELETE FROM media_staff_profiles WHERE user_id = ?", (int(игрок.id),))
        conn.commit()
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

# ================== EMBED-ПАНЕЛЬ ВЕРИФИКАЦИИ ==================
def normalize_media_position(value):
    normalized = re.sub(r"[^a-zа-яё]", "", str(value or "").casefold())
    if normalized in {"tt", "тт", "tiktok", "тикток", "тиктокер"}:
        return "TT"
    if normalized in {"yt", "ютуб", "youtube", "юутуб", "ютубер"}:
        return "YT"
    return None


def is_valid_media_profile_url(url, position):
    value = str(url or "").strip().lower()
    if position == "TT":
        return bool(re.match(r"^https?://(?:www\.)?tiktok\.com/@[a-z0-9._-]+/?(?:\?.*)?$", value))
    if position == "YT":
        return bool(re.match(r"^https?://(?:www\.)?youtube\.com/(?:@[a-z0-9._-]+|channel/[a-z0-9_-]+|c/[a-z0-9._-]+|user/[a-z0-9._-]+)/?(?:\?.*)?$", value))
    return False


def verification_guide_embed():
    embed = discord.Embed(
        title="📋 Как правильно оформить заявку на верификацию",
        description=(
            "Чтобы заявка попала на проверку, отправь **одно сообщение** строго по форме ниже. "
            "Заполни все три пункта и не меняй их названия."
        ),
        color=discord.Color.from_rgb(90, 110, 140)
    )
    embed.add_field(
        name="📝 Форма заявки",
        value="`1. Ник: Steve`\n`2. Должность: TT`\n`3. Ссылка на канал: https://www.tiktok.com/@username`",
        inline=False
    )
    embed.add_field(
        name="🎬 Должность",
        value="Укажи **TT** для TikTok или **YT** для YouTube.",
        inline=False
    )
    embed.add_field(
        name="⚠️ Важно",
        value=(
            "• Укажи правильный игровой ник.\n"
            "• Укажи ссылку на TikTok или YouTube профиль в зависимости от должности.\n"
            "• Не отправляй несколько заявок подряд.\n"
            "• Если заявку отклонили, исправь данные и отправь новую."
        ),
        inline=False
    )
    embed.set_footer(text="GASTWORLD_VERIFICATION_GUIDE_V1")
    return embed


async def ensure_verification_guide(guild):
    if guild.id != VERIFICATION_GUILD_ID:
        return
    channel = guild.get_channel(JOIN_CHANNEL_ID)
    if channel is None:
        try:
            channel = await guild.fetch_channel(JOIN_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as error:
            print(f"⚠️ [ВЕРИФИКАЦИЯ] Не найден канал заявок {JOIN_CHANNEL_ID}: {error}", flush=True)
            return

    row = conn.execute(
        "SELECT message_id FROM verification_guide_config WHERE channel_id = ?",
        (int(channel.id),)
    ).fetchone()
    guide_message = None
    if row:
        try:
            guide_message = await channel.fetch_message(int(row[0]))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
            guide_message = None

    def is_existing_guide(candidate):
        parts = [candidate.content or ""]
        for candidate_embed in candidate.embeds:
            parts.extend([candidate_embed.title or "", candidate_embed.description or ""])
            parts.extend(field.name + " " + field.value for field in candidate_embed.fields)
            if candidate_embed.footer and candidate_embed.footer.text == "GASTWORLD_VERIFICATION_GUIDE_V1":
                return True
        body = " ".join(parts).casefold()
        return "1. ник" in body and "2. должность" in body and "3. возраст" in body

    if guide_message is None:
        try:
            for candidate in await channel.pins():
                if is_existing_guide(candidate):
                    guide_message = candidate
                    break
            if guide_message is None:
                async for candidate in channel.history(limit=200):
                    if is_existing_guide(candidate):
                        guide_message = candidate
                        break
        except (discord.Forbidden, discord.HTTPException) as error:
            print(f"⚠️ [ВЕРИФИКАЦИЯ] Не удалось проверить закреплённые сообщения/историю: {error}", flush=True)

    if guide_message is None:
        guide_message = await channel.send(embed=verification_guide_embed())
        print(f"📌 [ВЕРИФИКАЦИЯ] Создана инструкция в #{channel.name}.", flush=True)
    else:
        await guide_message.edit(embed=verification_guide_embed())

    conn.execute(
        "INSERT INTO verification_guide_config(channel_id,message_id) VALUES(?,?) "
        "ON CONFLICT(channel_id) DO UPDATE SET message_id=excluded.message_id",
        (int(channel.id), int(guide_message.id))
    )
    conn.commit()

    if not guide_message.pinned:
        try:
            await guide_message.pin(reason="Закреплённая инструкция по подаче заявки GastWorld")
            print(f"📌 [ВЕРИФИКАЦИЯ] Инструкция закреплена в #{channel.name}.", flush=True)
        except (discord.Forbidden, discord.HTTPException) as error:
            print(f"⚠️ [ВЕРИФИКАЦИЯ] Не удалось закрепить инструкцию: {error}", flush=True)


class VerificationReviewView(discord.ui.View):
    def __init__(self, applicant_id):
        super().__init__(timeout=None)
        self.applicant_id = int(applicant_id)

        accept_button = discord.ui.Button(
            label="Принять",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"gastworld:verification:accept:{self.applicant_id}"
        )
        reject_button = discord.ui.Button(
            label="Отклонить",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            custom_id=f"gastworld:verification:reject:{self.applicant_id}"
        )
        accept_button.callback = self.accept
        reject_button.callback = self.reject
        self.add_item(accept_button)
        self.add_item(reject_button)

    async def accept(self, interaction):
        await process_verification_decision(interaction, self.applicant_id, accepted=True)

    async def reject(self, interaction):
        await process_verification_decision(interaction, self.applicant_id, accepted=False)


async def process_verification_decision(interaction, applicant_id, *, accepted):
    guild = interaction.guild
    if guild is None or guild.id != VERIFICATION_GUILD_ID or interaction.channel_id != JOIN_CHANNEL_ID:
        await interaction.response.send_message("Эта панель работает только в канале верификации первого сервера.", ephemeral=True)
        return
    if not has_verification_role(interaction.user):
        await interaction.response.send_message("У вас нет роли для рассмотрения заявок.", ephemeral=True)
        return
    if interaction.user.id == int(applicant_id):
        await interaction.response.send_message("Нельзя рассматривать собственную заявку.", ephemeral=True)
        return

    app_data = pending_apps.get(int(applicant_id))
    if not app_data:
        await interaction.response.send_message("Заявка уже обработана или больше не существует.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    panel_message = interaction.message
    if not accepted:
        embed = panel_message.embeds[0].copy() if panel_message.embeds else discord.Embed()
        embed.title = "❌ ЗАЯВКА ОТКЛОНЕНА"
        embed.color = discord.Color.red()
        embed.set_footer(text=f"GASTWORLD MEDIA • Отклонил: {interaction.user.display_name}")
        disabled_view = VerificationReviewView(applicant_id)
        for child in disabled_view.children:
            child.disabled = True
        await panel_message.edit(embed=embed, view=disabled_view)
        try:
            await panel_message.add_reaction("❌")
        except discord.HTTPException:
            pass

        applicant = guild.get_member(int(applicant_id))
        if applicant is None:
            try:
                applicant = await guild.fetch_member(int(applicant_id))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                applicant = None
        pending_role = guild.get_role(PENDING_APPLICATION_ROLE_ID)
        if applicant and pending_role and pending_role in applicant.roles:
            try:
                await applicant.remove_roles(pending_role, reason=f"Заявка отклонена: {interaction.user}")
            except discord.HTTPException as error:
                print(f"⚠️ [ВЕРИФИКАЦИЯ] Не удалось снять роль ожидания: {error}", flush=True)

        pending_apps.pop(int(applicant_id), None)
        delete_pending_request("join", int(applicant_id))
        print(f"❌ [ВЕРИФИКАЦИЯ] Заявка {applicant_id} отклонена пользователем {interaction.user.id}. Повторная подача разрешена.", flush=True)
        return

    applicant = guild.get_member(int(applicant_id))
    if applicant is None:
        try:
            applicant = await guild.fetch_member(int(applicant_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            await interaction.followup.send("Не удалось найти автора заявки на первом сервере.", ephemeral=True)
            return

    nick = str(app_data.get("nick", "")).strip()
    position = normalize_media_position(app_data.get("position"))
    profile_url = str(app_data.get("profile_url", "")).strip()
    if not nick or position is None or not is_valid_media_profile_url(profile_url, position):
        await interaction.followup.send("В заявке некорректный ник или должность. Отклоните её, чтобы человек мог подать исправленную.", ephemeral=True)
        return

    try:
        new_nick = f"{nick} | {position}"[:32]
        await applicant.edit(nick=new_nick, reason=f"Заявка одобрена {interaction.user}")
    except discord.Forbidden:
        print(f"⚠️ [ВЕРИФИКАЦИЯ] Не удалось изменить ник участника {applicant.id}.", flush=True)
    except discord.HTTPException as error:
        print(f"⚠️ [ВЕРИФИКАЦИЯ] Ошибка изменения ника: {error}", flush=True)

    # Комплект ролей выдаётся на первом сервере в зависимости от площадки.
    first_server_role_ids = (
        (1493615940741365881, 1573343622986862602, 1493196315205566545, 1492975006446260306)
        if position == "TT"
        else (1493615940741365881, 1573343622986862602, 1493196315205566545, 1492975112985645166)
    )
    roles_to_add = [
        role for role_id in first_server_role_ids
        if (role := guild.get_role(role_id)) is not None
    ]
    missing_roles = [
        role_id for role_id in first_server_role_ids
        if guild.get_role(role_id) is None
    ]
    if missing_roles:
        print(f"⚠️ [ВЕРИФИКАЦИЯ] На первом сервере не найдены роли: {missing_roles}", flush=True)
    try:
        if roles_to_add:
            await applicant.add_roles(*roles_to_add, reason=f"Заявка {position} одобрена: {interaction.user}")
    except discord.Forbidden:
        await interaction.followup.send("Не удалось выдать роли на первом сервере. Проверьте права и иерархию ролей бота.", ephemeral=True)
        return
    except discord.HTTPException as error:
        await interaction.followup.send(f"Ошибка выдачи ролей на первом сервере: {error}", ephemeral=True)
        return

    # После успешной верификации снимаем общую роль, указанную для обеих площадок.
    obsolete_role = guild.get_role(1520158772067041314)
    if obsolete_role and obsolete_role in applicant.roles:
        try:
            await applicant.remove_roles(obsolete_role, reason=f"Верификация {position} завершена: {interaction.user}")
        except discord.HTTPException as error:
            print(f"⚠️ [ВЕРИФИКАЦИЯ] Не удалось снять роль 1520158772067041314: {error}", flush=True)

    pending_role = guild.get_role(PENDING_APPLICATION_ROLE_ID)
    if pending_role and pending_role in applicant.roles:
        try:
            await applicant.remove_roles(pending_role, reason=f"Заявка одобрена: {interaction.user}")
        except discord.HTTPException as error:
            print(f"⚠️ [ВЕРИФИКАЦИЯ] Не удалось снять роль ожидания: {error}", flush=True)

    # На втором сервере выдаём общую роль и роль выбранной площадки.
    secondary_guild = bot.get_guild(SECONDARY_ROLE_GUILD_ID)
    if secondary_guild is None:
        print(f"❌ [ВЕРИФИКАЦИЯ] Второй сервер {SECONDARY_ROLE_GUILD_ID} недоступен; комплект ролей {position} не выдан.", flush=True)
    else:
        secondary_member = secondary_guild.get_member(int(applicant_id))
        if secondary_member is None:
            try:
                secondary_member = await secondary_guild.fetch_member(int(applicant_id))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                secondary_member = None
        platform_role_id = VERIFICATION_TT_ROLE_ID if position.strip().casefold() in {"tt", "тт", "tiktok", "тикток"} else VERIFICATION_YT_ROLE_ID
        role_ids = (VERIFICATION_COMMON_ROLE_ID, platform_role_id)
        if secondary_member is None:
            print(f"⚠️ [ВЕРИФИКАЦИЯ] Пользователь {applicant_id} не состоит на втором сервере; комплект ролей {position} не выдан.", flush=True)
        else:
            for role_id in role_ids:
                secondary_role = secondary_guild.get_role(role_id)
                if secondary_role is None:
                    print(f"⚠️ [ВЕРИФИКАЦИЯ] Роль {role_id} не найдена на втором сервере.", flush=True)
                    continue
                if secondary_role not in secondary_member.roles:
                    try:
                        await secondary_member.add_roles(secondary_role, reason=f"GastWorld Media: заявка одобрена на первом сервере ({position})")
                        print(f"✅ [ВЕРИФИКАЦИЯ] На втором сервере выдана роль {role_id} пользователю {applicant_id}.", flush=True)
                    except discord.HTTPException as error:
                        print(f"❌ [ВЕРИФИКАЦИЯ] Не удалось выдать роль {role_id} пользователю {applicant_id}: {error}", flush=True)

    category = guild.get_channel(CATEGORY_ID) if CATEGORY_ID else None
    if category is None and CATEGORY_ID:
        try:
            category = await guild.fetch_channel(CATEGORY_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as error:
            print(f"❌ [ВЕРИФИКАЦИЯ] Не удалось получить категорию личных каналов {CATEGORY_ID}: {error}", flush=True)
            await interaction.followup.send("Не удалось найти категорию для личного канала. Канал не создан, чтобы не разместить его вне категории.", ephemeral=True)
            return
    if not isinstance(category, discord.CategoryChannel) or category.guild.id != guild.id:
        print(f"❌ [ВЕРИФИКАЦИЯ] ID {CATEGORY_ID} не является категорией на первом сервере.", flush=True)
        await interaction.followup.send("Указанная категория личных каналов не найдена на этом сервере. Канал не создан.", ephemeral=True)
        return
    channel_name = re.sub(r"[^a-z0-9а-яё_-]+", "-", nick.casefold()).strip("-")[:90] or f"media-{applicant_id}"
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        applicant: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
    }
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    for role_id in STAFF_ROLES:
        staff_role = guild.get_role(role_id)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    try:
        personal_channel = await guild.create_text_channel(
            channel_name, category=category, overwrites=overwrites,
            reason=f"Личный канал для {applicant.display_name}"
        )
        set_personal_channel(applicant.id, personal_channel.id)
        welcome_embed = discord.Embed(
            title="🎬 GASTWORLD MEDIA",
            description=f"**Добро пожаловать в команду Медиа, {applicant.mention}!**\nРады видеть тебя среди нас. Здесь собрана важная информация о работе, баллах и покупках.",
            color=discord.Color.from_rgb(151, 112, 210)
        )
        welcome_embed.add_field(name="🎥 ТВОЯ РАБОТА", value="• Оставляй еженедельную норму.\n• Публикуй видеоролики, чтобы получать баллы.\n• Следи за активностью и не пропускай отчётную неделю.", inline=False)
        welcome_embed.add_field(name="💎 ПОЛЕЗНЫЕ КОМАНДЫ", value="**/balance** — проверить баланс.\n**/shop** — посмотреть магазин.\n**/kit** — приобрести наборы.\n**/донат** — приобрести донат-привилегии.\n**/case** — приобрести кейсы.\n**/услуга** — приобрести услуги.", inline=False)
        welcome_embed.add_field(name="📊 1. НЕДЕЛЬНАЯ НОРМА", value="**1.** Твой никнейм: `(твой игровой никнейм)`\n**2.** Ссылки на ролики, которые ты сделал: `(ссылки)`", inline=False)
        welcome_embed.add_field(name="💰 2. ПОЛУЧЕНИЕ БАЛЛОВ", value="**1.** Привяжи TikTok через /привязать_аккаунт.\n**2.** Добавь код из команды в BIO и подтверди привязку.\n**3.** Отправь ссылку на ролик в личный канал — бот проверит просмотры и начислит баллы автоматически.", inline=False)
        welcome_embed.add_field(name="🛒 3. ПОКУПКА ЗА БАЛЛЫ", value="**1.** Твой никнейм: `(твой ник в игре)`\n**2.** Что хочешь купить: `(название товара)`", inline=False)
        welcome_embed.add_field(name="⭐ НЕСКОЛЬКО ВАЖНЫХ СОВЕТОВ", value="• Проверяй ссылки перед отправкой.\n• Перед покупкой проверяй баланс.\n• Сохраняй ссылки на опубликованные ролики.", inline=False)
        welcome_embed.add_field(name="🔥 СНИМАЙ • ПУБЛИКУЙ • ЗАРАБАТЫВАЙ", value="**Твои ролики — твой вклад в развитие GastWorld Media!**", inline=False)
        welcome_embed.set_footer(text="GASTWORLD MEDIA • Удачной работы!")
        await personal_channel.send(content=f"Привет, {applicant.mention}! Ты попал в команду Медиа.", embed=welcome_embed)
        conn.execute("""INSERT INTO media_staff_profiles (user_id, nickname, position, profile_url) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET nickname=excluded.nickname, position=excluded.position, profile_url=excluded.profile_url, updated_at=CURRENT_TIMESTAMP""", (int(applicant.id), nick, position, profile_url))
        conn.commit()
        await sync_staff_member_to_sheets(applicant)
    except discord.Forbidden:
        await interaction.followup.send("Роли выданы, но не удалось создать личный канал. Проверь права Manage Channels.", ephemeral=True)
        return
    except discord.HTTPException as error:
        await interaction.followup.send(f"Ошибка создания личного канала: {str(error)[:250]}", ephemeral=True)
        return

    embed = panel_message.embeds[0].copy() if panel_message.embeds else discord.Embed()
    embed.title = "✅ ЗАЯВКА ОДОБРЕНА"
    embed.color = discord.Color.green()
    embed.set_footer(text=f"GASTWORLD MEDIA • Принял: {interaction.user.display_name}")
    disabled_view = VerificationReviewView(applicant_id)
    for child in disabled_view.children:
        child.disabled = True
    await panel_message.edit(embed=embed, view=disabled_view)
    try:
        await panel_message.add_reaction("✅")
    except discord.HTTPException:
        pass

    pending_apps.pop(int(applicant_id), None)
    delete_pending_request("join", int(applicant_id))
    print(f"✅ [ВЕРИФИКАЦИЯ] Заявка {applicant_id} одобрена {interaction.user.id}; first-server roles + second-server {position}.", flush=True)


async def register_pending_verification_views():
    if getattr(bot, "_verification_views_registered", False):
        return
    for user_id, data in list(pending_apps.items()):
        message_id = data.get("panel_message_id")
        guild_id = int(data.get("guild_id", VERIFICATION_GUILD_ID))
        if not message_id or guild_id != VERIFICATION_GUILD_ID:
            continue
        bot.add_view(VerificationReviewView(user_id), message_id=int(message_id))
    bot._verification_views_registered = True


# ================== ON_MESSAGE ==================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Глобальные текстовые пасхалки: работают на всех серверах,
    # включая сервер, для которого отключена основная функциональность.
    easter_eggs = {
        "иди нахуй": "**Сам пошёл нахуй сын хуйни**",
        "ты": "**Жопой нюхаешь цветы🧨**",
        "какашка": "**Ты какашка🧡**",
        "соси": "**Мне, нежно**",
        "нет": "**Дат**",
        "да": "**Нет**",
    }
    reply_text = easter_eggs.get((message.content or "").casefold())
    if reply_text is not None:
        await message.channel.send(reply_text)
        return

    # На этом сервере отключена основная функциональность бота.
    # Глобальные пасхалки выше продолжают работать.
    if message.guild is None or message.guild.id == 1454858971084230822:
        return

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
        print(f"\n{cyan}{border}{reset}", flush=True)
        print(f"{cyan}║{reset} {purple}GASTWORLD • LIVE CHAT{reset} {gray}{timestamp}{reset}", flush=True)
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

        # ---- АВТОМАТИЧЕСКОЕ НАЧИСЛЕНИЕ ЗА TIKTOK ----
        if "tiktok.com/" in (message.content or "").lower():
            await process_tiktok_video(message)
            return

        return

    # ---------- ЗАЯВКИ НА ВСТУПЛЕНИЕ ----------
    if message.guild.id == VERIFICATION_GUILD_ID and message.channel.id == JOIN_CHANNEL_ID:
        if message.content.startswith('!'):
            await bot.process_commands(message)
            return

        if message.author.id in pending_apps:
            await message.delete(delay=3)
            return

        lines = message.content.split('\n')
        nick = None
        position_raw = None
        profile_url = None
        for line in lines:
            line = line.strip()
            if not line or line.casefold().startswith('форма заявки'):
                continue
            low = line.casefold()
            if low.startswith('1. ник:') or low.startswith('ник:'):
                nick = line.split(':', 1)[1].strip()
            elif low.startswith('2. должность:') or low.startswith('должность:'):
                position_raw = line.split(':', 1)[1].strip()
            elif low.startswith('3. ссылка на канал:') or low.startswith('ссылка на канал:') or low.startswith('3. канал:'):
                profile_url = line.split(':', 1)[1].strip()

        position = normalize_media_position(position_raw)
        if nick and position and is_valid_media_profile_url(profile_url, position):
            pending_role = message.guild.get_role(PENDING_APPLICATION_ROLE_ID)
            if pending_role and pending_role not in message.author.roles:
                try:
                    await message.author.add_roles(pending_role, reason="Заявка на вступление ожидает одобрения")
                except discord.HTTPException as error:
                    print(f"[WARN] Не удалось выдать роль ожидания: {error}", flush=True)

            application_embed = discord.Embed(
                title="📩 НОВАЯ ЗАЯВКА В GASTWORLD MEDIA",
                description=f"Игрок {message.author.mention} отправил заявку и ожидает рассмотрения.",
                color=discord.Color.from_rgb(255, 210, 0),
                timestamp=discord.utils.utcnow()
            )
            application_embed.add_field(name="🎮 Игровой ник", value=nick[:1024], inline=True)
            application_embed.add_field(name="🛡️ Должность", value=position, inline=True)
            application_embed.add_field(name="🔗 Ссылка на канал", value=profile_url[:1024], inline=False)
            application_embed.add_field(name="👤 Автор заявки", value=f"{message.author.mention}\nID: {message.author.id}", inline=False)
            application_embed.set_footer(text="GASTWORLD MEDIA • Используйте кнопки для решения")
            reviewer_role = message.guild.get_role(VERIFICATION_REVIEW_ROLE_ID)
            panel_message = await message.channel.send(
                content=reviewer_role.mention if reviewer_role else None,
                embed=application_embed,
                view=VerificationReviewView(message.author.id)
            )
            app_data = {
                "nick": nick,
                "position": position,
                "profile_url": profile_url,
                "guild_id": message.guild.id,
                "panel_message_id": panel_message.id
            }
            pending_apps[message.author.id] = app_data
            save_pending_request("join", message.author.id, panel_message.id, app_data)
            try:
                await message.delete()
            except discord.HTTPException:
                pass
        else:
            await message.channel.send(
                "❌ Неверный формат. Укажи ник, должность TT или YT и ссылку на профиль соответствующей платформы по закреплённой форме.",
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
            report_author = guild.get_member(int(author_id))
            if report_author is None:
                try:
                    report_author = await guild.fetch_member(int(author_id))
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    report_author = None
            if report_author is not None:
                await sync_staff_member_to_sheets(report_author)
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

async def execute_application_console_command(raw: str) -> str:
    """Выполняет ввод именно как команду приложения GastWorld."""
    line = str(raw if raw is not None else "").strip()
    if not line:
        return "❌ Введи хотя бы один символ."
    if len(line) > 2000:
        return "❌ Команда слишком длинная (максимум 2000 символов)."

    parts = line.split(maxsplit=2)
    command = parts[0].lower()

    if command == "/help":
        return (
            "Команды приложения GastWorld:\n"
            "/text <ID канала> <сообщение> — отправить сообщение\n"
            "/channels — список текстовых каналов и их ID\n"
            "/delete pending_requests — удалить все ожидающие заявки\n"
            "/restart pending_requests — пересоздать таблицу заявок (удалит записи)\n"
            "/help — показать эту подсказку"
        )

    if command == "/text":
        if len(parts) < 3:
            return "❌ Формат: /text <ID канала> <сообщение>"
        try:
            channel_id = int(parts[1])
        except ValueError:
            return "❌ ID канала должен состоять из цифр."
        channel = bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except discord.NotFound:
                return "❌ Канал с таким ID не найден."
            except discord.Forbidden:
                return "❌ У бота нет доступа к этому каналу."
        if not hasattr(channel, "send"):
            return "❌ В этот тип канала нельзя отправить обычное сообщение."
        try:
            await channel.send(parts[2])
            return f"✅ Сообщение отправлено в #{getattr(channel, 'name', 'канал')} ({channel_id})."
        except discord.Forbidden:
            return "❌ Нет прав на отправку сообщений в этот канал."
        except discord.HTTPException as error:
            return f"❌ Discord не принял сообщение: {error}"

    if command == "/channels":
        lines = ["📚 Текстовые каналы доступных серверов:"]
        found = False
        for guild_id in ALLOWED_GUILDS:
            guild = bot.get_guild(guild_id)
            if guild is None:
                continue
            for channel in guild.text_channels:
                lines.append(f"#{channel.name} — ID: {channel.id}")
                found = True
        if not found:
            lines.append("Каналы пока не найдены. Проверь подключение бота и права.")
        return "\n".join(lines)

    if command == "/delete":
        if len(parts) != 2 or parts[1].lower() != "pending_requests":
            return "❌ Формат: /delete pending_requests"
        try:
            conn.execute("BEGIN IMMEDIATE")
            deleted_count = conn.execute("DELETE FROM pending_requests").rowcount
            conn.commit()
            return f"✅ Таблица pending_requests очищена. Удалено заявок: {deleted_count}. Остальные таблицы не затронуты."
        except sqlite3.Error as error:
            conn.rollback()
            return f"❌ Не удалось очистить pending_requests: {error}"

    if command == "/restart":
        if len(parts) != 2 or parts[1].lower() != "pending_requests":
            return "❌ Формат: /restart pending_requests"
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DROP TABLE IF EXISTS pending_requests")
            conn.execute("""CREATE TABLE pending_requests (
                request_type TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                message_id INTEGER,
                data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (request_type, user_id)
            )""")
            conn.commit()
            pending_apps.clear()
            return "✅ Таблица pending_requests пересоздана. Все ожидающие заявки удалены; остальные таблицы не затронуты."
        except sqlite3.Error as error:
            conn.rollback()
            return f"❌ Не удалось пересоздать pending_requests: {error}"

    return f"❓ Неизвестная команда приложения: {line}\nВведи /help для списка доступных команд."


async def panel_application_command(command: str):
    """Обрабатывает ввод из вкладки «Ввод в приложение»."""
    raw = str(command if command is not None else "")
    if not raw.strip():
        raise RuntimeError("Введи хотя бы один символ.")
    if len(raw) > 2000:
        raise RuntimeError("Команда слишком длинная (максимум 2000 символов).")
    print(f"[APP INPUT] {raw}", flush=True)
    output = await execute_application_console_command(raw)
    print(output, flush=True)
    return {
        "command": raw,
        "exit_code": 0 if not output.startswith(("❌", "❓")) else 1,
        "output": output[:20000],
    }


async def console_input_loop():
    """Читает stdin-хостинга и передаёт ввод в обработчик приложения."""
    print("🖥️ Консольное управление включено. Введите /help для списка команд.", flush=True)
    while not bot.is_closed():
        try:
            raw = await asyncio.to_thread(sys.stdin.readline)
            if not raw:
                await asyncio.sleep(1)
                continue
            if not raw.strip():
                continue
            output = await execute_application_console_command(raw)
            print(output, flush=True)
        except Exception as error:
            print(f"❌ Ошибка консольного обработчика: {error}", flush=True)


def audit_primary_guild_configuration(guild: discord.Guild) -> None:
    """Показывает устаревшие ID ролей/каналов после переноса на новый сервер."""
    role_ids = {
        *MOD_ROLE_IDS,
        WARN_1_ROLE_ID, WARN_2_ROLE_ID, WARN_3_ROLE_ID,
        *PROTECTED_ROLE_IDS,
        PLAYER_ROLE_ID, MEDIA_TEAM_ROLE_ID, MEDIA_TEAM_AUTO_ROLE_ID,
        APPROVER_ROLE_ID, PENDING_APPLICATION_ROLE_ID,
        *APPROVER_POINTS_ROLE_IDS, *POVIXA_ROLE_IDS,
        *ROLES_TO_GIVE, *STAFF_ROLES,
        VERIFICATION_REVIEW_ROLE_ID,
        1493615940741365881, 1492975006446260306, 1492975112985645166,
        1567181454947917864, 1567181456059535380, 1567181457212833822,
    }
    channel_ids = {
        REPORT_CHANNEL_ID, JOIN_CHANNEL_ID, CATEGORY_ID,
        SHOP_CHANNEL_ID, AUDIT_LOG_CHANNEL_ID, ROLE_ANNOUNCEMENT_CHANNEL_ID,
        WARN_COMMAND_CHANNEL_ID, WARN_LOG_CHANNEL_ID, POVIXA_CHANNEL_ID,
    }
    missing_roles = sorted(role_id for role_id in role_ids if guild.get_role(role_id) is None)
    missing_channels = sorted(channel_id for channel_id in channel_ids if guild.get_channel(channel_id) is None)
    print(
        f"🔎 [ПРОВЕРКА ПЕРЕНОСА] Сервер {guild.name} ({guild.id}): "
        f"ролей проверено {len(role_ids)}, отсутствует {len(missing_roles)}; "
        f"каналов/категорий проверено {len(channel_ids)}, отсутствует {len(missing_channels)}.",
        flush=True,
    )
    if missing_roles:
        print(f"⚠️ [ПРОВЕРКА ПЕРЕНОСА] Не найдены ID ролей: {missing_roles}", flush=True)
    if missing_channels:
        print(f"⚠️ [ПРОВЕРКА ПЕРЕНОСА] Не найдены ID каналов/категорий: {missing_channels}", flush=True)


# ================== ЗАПУСК ==================
@bot.event
async def on_ready():
    global _console_reader_started
    print(f'Бот {bot.user} запущен!')
    connected = ", ".join(f"{guild.name} ({guild.id})" for guild in bot.guilds) or "нет серверов"
    print(f"🌐 Discord-серверы, видимые боту: {connected}", flush=True)
    if not getattr(bot, "_primary_guild_config_audited", False):
        primary_guild = bot.get_guild(VERIFICATION_GUILD_ID)
        if primary_guild:
            audit_primary_guild_configuration(primary_guild)
        bot._primary_guild_config_audited = True
    if not getattr(bot, "_player_data_reconciled", False):
        for guild_id in ALLOWED_GUILDS:
            guild = bot.get_guild(guild_id)
            if guild:
                try:
                    await reconcile_server_players(guild)
                except Exception as e:
                    print(f"❌ Не удалось выполнить очистку данных игроков: {e}")
        bot._player_data_reconciled = True

    if not getattr(bot, "_media_team_roles_synced", False):
        media_guild = bot.get_guild(VERIFICATION_GUILD_ID)
        if media_guild:
            try:
                await sync_media_team_member_role(media_guild)
            except Exception as error:
                print(f"❌ [ИГРОКИ] Ошибка синхронизации ролей Команды медиа: {error}", flush=True)
        bot._media_team_roles_synced = True
    if not _console_reader_started:
        _console_reader_started = True
        asyncio.create_task(console_input_loop())

    if not getattr(bot, "_ticket_views_registered", False):
        for ticket_guild_id in TICKET_ALLOWED_GUILDS:
            bot.add_view(TicketPanelView(ticket_guild_id))
        bot.add_view(TicketControlView())
        bot._ticket_views_registered = True

    await register_pending_verification_views()
    verification_guild = bot.get_guild(VERIFICATION_GUILD_ID)
    if verification_guild:
        try:
            await ensure_verification_guide(verification_guild)
        except Exception as error:
            print(f"❌ [ВЕРИФИКАЦИЯ] Не удалось проверить закреплённую инструкцию: {error}", flush=True)
    else:
        print(f"⚠️ [ВЕРИФИКАЦИЯ] Первый сервер {VERIFICATION_GUILD_ID} не найден.", flush=True)

    # Роли доступа сайта обслуживаются только на первом сервере.
    access_guild = bot.get_guild(ACCESS_ROLES_GUILD_ID)
    if access_guild:
        await ensure_control_panel_roles(access_guild)
    else:
        print(f"❌ [РОЛИ САЙТА] Первый сервер {ACCESS_ROLES_GUILD_ID} не найден. Проверь, что бот добавлен на него.", flush=True)

    # Тикет-система имеет отдельный список серверов и не меняет ограничения остальных функций.
    for ticket_guild_id in TICKET_ALLOWED_GUILDS:
        ticket_guild = bot.get_guild(ticket_guild_id)
        if ticket_guild:
            try:
                await ensure_ticket_system(ticket_guild)
            except Exception as error:
                print(f"❌ [ТИКЕТЫ] Ошибка настройки на {ticket_guild_id}: {error}", flush=True)
        else:
            print(f"⚠️ [ТИКЕТЫ] Первый сервер {ticket_guild_id} не найден в подключении бота.", flush=True)

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



# ================== РОЛИ ДОСТУПА GASTWORLD CONTROL PANEL ==================
CONTROL_PANEL_SYNC_URL = os.getenv("CONTROL_PANEL_SYNC_URL", "").strip()
CONTROL_PANEL_SYNC_SECRET = os.getenv("CONTROL_PANEL_SYNC_SECRET", "").strip()

ACCESS_ROLE_DEFINITIONS = [
    # От минимального доступа к максимальному: фиолетовый -> красный.
    ("media", "Media", 0x8B5CF6),
    ("co_adm", "Co.Adm » уровень доступа", 0xC026D3),
    ("adm", "Adm » уровень доступа", 0xF97316),
    ("full", "Full » уровень доступа", 0xEF4444),
]

async def ensure_control_panel_roles(guild: discord.Guild) -> None:
    """Создаёт недостающие роли доступа и передаёт их ID веб-панели."""
    role_payload = {}
    for access_level, role_name, color in ACCESS_ROLE_DEFINITIONS:
        role = discord.utils.get(guild.roles, name=role_name)
        # Миграция ранее созданной роли Media со старым длинным названием.
        if role is None and access_level == "media":
            role = discord.utils.get(guild.roles, name="Media » уровень доступа")
            if role is not None:
                try:
                    await role.edit(name="Media", reason="Переименование роли доступа GastWorld")
                except discord.Forbidden:
                    print("⚠️ Не удалось переименовать старую роль Media; проверь иерархию ролей.")
        if role is None:
            try:
                role = await guild.create_role(
                    name=role_name,
                    colour=discord.Colour(color),
                    permissions=discord.Permissions.none(),
                    hoist=True,
                    mentionable=False,
                    reason="Настройка уровней доступа GastWorld Control Panel",
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

    print("🔐 Роли доступа GastWorld:")
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
                    print(f"✅ ID ролей переданы GastWorld Control Panel ({result.get('synced', 0)} ролей).")
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
            bot_avatar_url = bot.user.display_avatar.url if bot.user else None
            if guild:
                embed.set_author(name=guild.name, icon_url=bot_avatar_url)
            else:
                embed.set_author(
                    name="GASTWORLD • SERVER AUDIT",
                    icon_url=bot_avatar_url,
                )
            embed.set_footer(text="GASTWORLD AUDIT")
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
    # Сообщения самого GastWorld и остальных ботов не засоряют аудит и live-консоль.
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

    before_roles = {r.id: r for r in before.roles}
    after_roles = {r.id: r for r in after.roles}
    added = [r for rid, r in after_roles.items() if rid not in before_roles]
    removed = [r for rid, r in before_roles.items() if rid not in after_roles]

    changes = []
    if before.nick != after.nick:
        changes.append(f"Ник: {before.nick or before.name} → {after.nick or after.name}")
    if added:
        changes.append("Выданы роли: " + ", ".join(f"{r.name} ({r.id})" for r in added))
    if removed:
        changes.append("Сняты роли: " + ", ".join(f"{r.name} ({r.id})" for r in removed))

    if not changes:
        return

    issuer = None
    if added or removed:
        try:
            await asyncio.sleep(0.8)
            async for entry in after.guild.audit_logs(
                limit=10,
                action=discord.AuditLogAction.member_role_update
            ):
                if (
                    getattr(entry.target, "id", None) == after.id
                    and (datetime.now(timezone.utc) - entry.created_at).total_seconds() <= 15
                ):
                    issuer = entry.user
                    break
        except (discord.Forbidden, discord.HTTPException) as error:
            print(f"[ROLE AUDIT ERROR] Не удалось определить выдавшего роль: {error}", flush=True)

    issuer_text = f"<@{issuer.id}> (ID: {issuer.id})" if issuer else "Не удалось определить"
    details = audit_member_label(after) + "\n" + "\n".join(changes)
    if added or removed:
        details += f"\nКто изменил роли: {issuer_text}"
        write_audit_log("ИЗМЕНЕНИЕ РОЛЕЙ", details, after.guild.id)
    else:
        write_audit_log("ИЗМЕНЕНИЕ УЧАСТНИКА", details, after.guild.id)

    if added:
        channel = after.guild.get_channel(ROLE_ANNOUNCEMENT_CHANNEL_ID)
        if channel is None:
            channel = bot.get_channel(ROLE_ANNOUNCEMENT_CHANNEL_ID)
        if channel is not None:
            embed = discord.Embed(
                title="Изменение ролей",
                color=discord.Color.from_rgb(46, 204, 170),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Кто", value=after.mention, inline=False)
            embed.add_field(name="Выданы", value=", ".join(role.mention for role in added)[:1024], inline=False)
            embed.add_field(name="Изменил", value=issuer_text, inline=False)
            try:
                await channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException) as error:
                print(f"[ROLE ANNOUNCEMENT ERROR] Не удалось отправить уведомление: {error}", flush=True)


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


# Последние строки stdout/stderr первого хостинга для трансляции в Dashboard.
CONSOLE_OUTPUT_LINES = deque(maxlen=1800)
CONSOLE_OUTPUT_SEQ = 0
console_output_lock = threading.Lock()

def push_console_output(line):
    global CONSOLE_OUTPUT_SEQ
    with console_output_lock:
        CONSOLE_OUTPUT_SEQ += 1
        CONSOLE_OUTPUT_LINES.append({
            "id": CONSOLE_OUTPUT_SEQ,
            "text": f"[{datetime.now(MSK).strftime('%Y-%m-%d %H:%M:%S')}] {str(line)}",
        })


class TimestampedTee:
    """Дублирует stdout/stderr в Bot-Hosting, latest.log и буфер live-консоли сайта."""
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
                push_console_output(line)
            self.log_file.flush()
        return len(text)

    def flush(self):
        self.console_stream.flush()
        with self.lock:
            if self.buffer:
                stamp = datetime.now(MSK).strftime("%Y-%m-%d %H:%M:%S")
                self.log_file.write(f"[{stamp}] {self.buffer}\n")
                push_console_output(self.buffer)
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
    print("========== GASTWORLD BOT SESSION STARTED ==========", flush=True)


if not TOKEN:
    raise RuntimeError("Не задан DISCORD_TOKEN. Добавь токен в переменные окружения Bot-Hosting.")

BOT_PROCESS_STARTED_AT = datetime.now(timezone.utc).isoformat()

async def panel_console_status():
    guild = bot.get_guild(ALLOWED_GUILDS[0]) if ALLOWED_GUILDS else None
    return {
        "process_started_at": BOT_PROCESS_STARTED_AT,
        "process_id": os.getpid(),
        "online": bool(bot.is_ready() and not bot.is_closed()),
        "bot_name": str(bot.user) if bot.user else "GastWorld",
        "guild_name": guild.name if guild else "Сервер не найден",
        "guild_count": len(bot.guilds),
        "latency_ms": round(bot.latency * 1000) if bot.is_ready() else None,
    }

async def panel_sync_commands():
    if not bot.is_ready(): raise RuntimeError("Discord-бот ещё не подключён.")
    results = []
    for guild_id in ALLOWED_GUILDS:
        guild = bot.get_guild(guild_id)
        if guild is None: continue
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        results.append({"guild": guild.name, "count": len(synced)})
        print(f"🖥️ [ПАНЕЛЬ] Синхронизировано {len(synced)} slash-команд на сервере {guild.name}.", flush=True)
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    if not results: raise RuntimeError("Доступный Discord-сервер не найден.")
    return {"message": "Slash-команды синхронизированы.", "results": results}

async def panel_sync_roles():
    if not bot.is_ready(): raise RuntimeError("Discord-бот ещё не подключён.")
    for guild_id in ALLOWED_GUILDS:
        guild = bot.get_guild(guild_id)
        if guild is not None:
            await ensure_control_panel_roles(guild)
            print(f"🖥️ [ПАНЕЛЬ] Выполнена синхронизация ролей доступа: {guild.name}.", flush=True)
            return {"message": f"Роли доступа синхронизированы: {guild.name}."}
    raise RuntimeError("Доступный Discord-сервер не найден.")

async def panel_console_command(command: str):
    """Выполняет введённую Full-команду через shell на первом хостинге."""
    raw = str(command if command is not None else "")
    if not raw.strip():
        raise RuntimeError("Введи хотя бы один символ команды.")
    if len(raw) > 2000:
        raise RuntimeError("Команда слишком длинная (максимум 2000 символов).")
    print(f"container~ {raw}", flush=True)
    try:
        process = await asyncio.create_subprocess_shell(
            raw,
            cwd=BASE_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            output_bytes, _ = await asyncio.wait_for(process.communicate(), timeout=60)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise RuntimeError("Команда выполнялась дольше 60 секунд и была остановлена.")
    except FileNotFoundError:
        raise RuntimeError("Командная оболочка недоступна в окружении хостинга.")
    output = output_bytes.decode("utf-8", errors="replace").rstrip()
    if not output:
        output = "Команда выполнена без вывода." if process.returncode == 0 else "Команда завершилась с ошибкой."
    return {
        "command": raw,
        "exit_code": int(process.returncode or 0),
        "output": output[:20000],
    }


async def panel_console_output(after_id: int = 0, limit: int = 250):
    """Возвращает новые строки реальной stdout/stderr-консоли процесса."""
    with console_output_lock:
        lines = [item.copy() for item in CONSOLE_OUTPUT_LINES if item["id"] > max(0, int(after_id))]
        latest_id = CONSOLE_OUTPUT_SEQ
    return {"lines": lines[-max(1, min(int(limit), 500)):], "latest_id": latest_id}

async def panel_restart_bot():
    """Перезапускает текущий процесс тем же Python-интерпретатором и тем же startup-файлом."""
    script = os.path.abspath(sys.argv[0])
    if not os.path.isfile(script):
        raise RuntimeError(f"Не найден файл запуска для перезапуска: {script}")
    argv = [sys.executable, script, *sys.argv[1:]]
    print(
        f"♻️ [ПАНЕЛЬ] Перезапуск запрошен. PID={os.getpid()}, файл={script}, Python={sys.executable}",
        flush=True,
    )

    def replace_process():
        try:
            print("♻️ [ПАНЕЛЬ] Выполняю os.execv для повторного запуска GastWorld…", flush=True)
            os.execv(sys.executable, argv)
        except Exception as error:
            print(f"❌ [ПАНЕЛЬ] Не удалось перезапустить процесс: {type(error).__name__}: {error}", flush=True)

    # Даём FastAPI завершить HTTP-ответ, затем заменяем процесс.
    asyncio.get_running_loop().call_later(2.0, replace_process)
    return {
        "message": "Команда перезапуска принята. Ожидается перезапуск процесса и повторное подключение Discord."
    }
async def panel_refresh_presence():
    if not bot.is_ready(): raise RuntimeError("Discord-бот ещё не подключён.")
    await bot.change_presence(activity=discord.Game(name="/shop | модерация"))
    print("🖥️ [ПАНЕЛЬ] Активность бота обновлена.", flush=True)
    return {"message": "Активность бота обновлена."}

async def panel_tickets_list():
    rows=conn.execute("SELECT channel_id,user_id,username,subject,description,status,created_at,updated_at,closed_by FROM support_tickets ORDER BY created_at DESC LIMIT 250").fetchall()
    return {"tickets":[{"channel_id":r[0],"user_id":r[1],"username":r[2],"subject":r[3],"description":r[4],"status":r[5],"created_at":r[6],"updated_at":r[7],"closed_by":r[8]} for r in rows]}

async def panel_ticket_status(channel_id,status,actor):
    return await set_ticket_status(channel_id,status,actor)

async def panel_ticket_acceptance():
    return {"accepting": ticket_accepting(ALLOWED_GUILDS[0])}

async def panel_set_ticket_acceptance(enabled):
    guild_id = str(ALLOWED_GUILDS[0])
    conn.execute("INSERT OR IGNORE INTO support_ticket_config (guild_id,accepting) VALUES (?,1)", (guild_id,))
    conn.execute("UPDATE support_ticket_config SET accepting=? WHERE guild_id=?", (1 if enabled else 0, guild_id))
    conn.commit()
    guild = bot.get_guild(int(guild_id))
    row = conn.execute("SELECT panel_channel_id,panel_message_id FROM support_ticket_config WHERE guild_id=?", (guild_id,)).fetchone()
    if guild and row and row[0] and row[1]:
        channel = guild.get_channel(int(row[0]))
        if channel:
            try:
                message = await channel.fetch_message(int(row[1]))
                await message.edit(embed=ticket_embed_panel(), view=TicketPanelView())
            except discord.NotFound:
                pass
    return {"accepting": bool(enabled)}



async def panel_dm_user_payload(user):
    avatar = getattr(user, 'display_avatar', None)
    return {'id': str(user.id), 'username': str(getattr(user, 'name', 'Unknown')), 'global_name': str(getattr(user, 'global_name', None) or getattr(user, 'display_name', None) or getattr(user, 'name', 'Unknown')), 'avatar_url': str(avatar.url) if avatar else '', 'bot': bool(getattr(user, 'bot', False))}

async def panel_dm_list():
    if not bot.is_ready(): raise RuntimeError('Discord-бот ещё подключается.')
    items=[]; seen=set()
    for channel in bot.private_channels:
        if not isinstance(channel, discord.DMChannel): continue
        recipient=channel.recipient
        if not recipient or recipient.id in seen: continue
        seen.add(recipient.id)
        last=getattr(channel, 'last_message', None)
        if last is None:
            # DMChannel in some discord.py versions has no last_message_id attribute.
            # Prefer a cached message ID when available; otherwise read the newest
            # message from channel history without assuming that the attribute exists.
            last_message_id=getattr(channel, 'last_message_id', None)
            if last_message_id:
                try: last=await channel.fetch_message(last_message_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException): last=None
            if last is None:
                try:
                    async for candidate in channel.history(limit=1):
                        last=candidate
                        break
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    last=None
        items.append({'channel_id':str(channel.id),'user':await panel_dm_user_payload(recipient),'last_message':{'content':(last.content or '[Вложение/медиа]')[:180],'created_at':last.created_at.isoformat(),'author_id':str(last.author.id)} if last else None})
    items.sort(key=lambda x:x['last_message']['created_at'] if x['last_message'] else '', reverse=True)
    return {'conversations':items,'bot':await panel_dm_user_payload(bot.user) if bot.user else None}

async def panel_dm_search(query):
    if not bot.is_ready(): raise RuntimeError('Discord-бот ещё подключается.')
    query=str(query or '').strip()
    if len(query)<2: return {'users':[]}
    found={}
    if query.isdigit():
        try:
            user=await bot.fetch_user(int(query)); found[user.id]=await panel_dm_user_payload(user)
        except (discord.NotFound, discord.HTTPException): pass
    else:
        needle=query.casefold().lstrip('@')
        for member in bot.get_all_members():
            if needle in str(member.name or '').casefold() or needle in str(member.display_name or '').casefold() or needle in str(getattr(member,'global_name','') or '').casefold():
                found[member.id]=await panel_dm_user_payload(member)
                if len(found)>=25: break
    return {'users':list(found.values())[:25]}

async def panel_dm_history(user_id, limit=60):
    if not bot.is_ready(): raise RuntimeError('Discord-бот ещё подключается.')
    if not str(user_id).isdigit(): raise ValueError('Некорректный Discord ID.')
    user=await bot.fetch_user(int(user_id)); channel=await user.create_dm(); messages=[]
    async for message in channel.history(limit=max(1,min(int(limit),100))):
        messages.append({'id':str(message.id),'content':message.content or '', 'created_at':message.created_at.isoformat(), 'author':await panel_dm_user_payload(message.author), 'attachments':[{'filename':x.filename,'url':x.url} for x in message.attachments[:10]], 'embeds':[{'title':x.title,'description':(x.description or '')[:500]} for x in message.embeds[:3]]})
    messages.reverse()
    return {'user':await panel_dm_user_payload(user),'channel_id':str(channel.id),'messages':messages}

async def panel_dm_send(user_id, content):
    if not bot.is_ready(): raise RuntimeError('Discord-бот ещё подключается.')
    content=str(content or '').strip()
    if not content: raise ValueError('Сообщение не может быть пустым.')
    if len(content)>2000: raise ValueError('Discord ограничивает обычное сообщение 2000 символами.')
    if not str(user_id).isdigit(): raise ValueError('Некорректный Discord ID.')
    user=await bot.fetch_user(int(user_id)); channel=await user.create_dm()
    message=await channel.send(content, allowed_mentions=discord.AllowedMentions.none())
    return {'ok':True,'message':{'id':str(message.id),'content':message.content,'created_at':message.created_at.isoformat(),'author':await panel_dm_user_payload(message.author),'attachments':[],'embeds':[]}}

async def panel_guild_list():
    if not bot.is_ready():
        raise RuntimeError("Discord-бот ещё подключается.")
    guilds = []
    for guild in sorted(bot.guilds, key=lambda item: item.name.casefold()):
        me = guild.me or guild.get_member(bot.user.id)
        guilds.append({
            "id": str(guild.id), "name": guild.name,
            "icon_url": str(guild.icon.url) if guild.icon else "",
            "member_count": int(guild.member_count or 0),
        })
    return {"guilds": guilds, "bot": await panel_dm_user_payload(bot.user) if bot.user else None}


async def panel_guild_members(guild_id):
    if not bot.is_ready():
        raise RuntimeError("Discord-бот ещё подключается.")
    if not str(guild_id).isdigit():
        raise ValueError("Некорректный ID сервера.")
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        raise ValueError("Сервер не найден среди серверов, где состоит бот.")
    roles = [{
        "id": str(role.id),
        "name": role.name,
        "position": int(role.position),
        "hoist": bool(role.hoist),
        "color_hex": f"#{role.color.value:06x}" if role.color.value else "",
    } for role in sorted(guild.roles, key=lambda item: item.position, reverse=True) if role.id != guild.default_role.id]
    members = []
    try:
        async for member in guild.fetch_members(limit=None):
            members.append({
                **(await panel_dm_user_payload(member)),
                "global_name": str(member.nick or member.global_name or member.name),
                "bot": bool(member.bot),
                "role_ids": [str(role.id) for role in member.roles if role.id != guild.default_role.id],
            })
    except discord.Forbidden:
        raise RuntimeError("Discord не разрешил получить список участников. Проверь Server Members Intent в Discord Developer Portal и включи его в настройках бота.")
    members.sort(key=lambda item: (bool(item["bot"]), (item["global_name"] or item["username"]).casefold()))
    return {"guild": {"id": str(guild.id), "name": guild.name}, "members": members, "roles": roles, "count": len(members)}


async def panel_guild_channels(guild_id):
    if not bot.is_ready():
        raise RuntimeError("Discord-бот ещё подключается.")
    if not str(guild_id).isdigit():
        raise ValueError("Некорректный ID сервера.")
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        raise ValueError("Сервер не найден среди серверов, где состоит бот.")
    me = guild.me or guild.get_member(bot.user.id)
    if me is None:
        raise ValueError("Не удалось определить права бота на сервере.")
    categories = []
    channels = []
    for category in sorted(guild.categories, key=lambda item: (item.position, item.name.casefold())):
        categories.append({"id": str(category.id), "name": category.name, "position": category.position})
    for channel in sorted(guild.channels, key=lambda item: (getattr(item, "position", 0), item.name.casefold())):
        if not isinstance(channel, discord.TextChannel):
            continue
        permissions = channel.permissions_for(me)
        if not permissions.view_channel:
            continue
        channels.append({
            "id": str(channel.id), "name": channel.name,
            "category_id": str(channel.category_id) if channel.category_id else "",
            "category_name": channel.category.name if channel.category else "Без категории",
            "position": channel.position,
            "can_send": bool(permissions.send_messages),
            "can_history": bool(permissions.read_message_history),
            "type": "announcement" if getattr(channel, "is_news", lambda: False)() else "text",
        })
    return {"guild": {"id": str(guild.id), "name": guild.name, "icon_url": str(guild.icon.url) if guild.icon else ""}, "categories": categories, "channels": channels}


async def panel_channel_history(channel_id, limit=100):
    if not bot.is_ready():
        raise RuntimeError("Discord-бот ещё подключается.")
    if not str(channel_id).isdigit():
        raise ValueError("Некорректный ID канала.")
    channel = await bot.fetch_channel(int(channel_id))
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("Это не текстовый канал.")
    if not channel.permissions_for(channel.guild.me).view_channel or not channel.permissions_for(channel.guild.me).read_message_history:
        raise PermissionError("У бота нет прав просматривать историю этого канала.")
    messages = []
    async for message in channel.history(limit=max(1, min(int(limit), 100))):
        messages.append({
            "id": str(message.id), "content": message.content or "",
            "created_at": message.created_at.isoformat(),
            "author": await panel_dm_user_payload(message.author),
            "attachments": [{"filename": item.filename, "url": item.url} for item in message.attachments[:10]],
            "embeds": [{"title": item.title or "", "description": (item.description or "")[:500]} for item in message.embeds[:3]],
        })
    messages.reverse()
    return {"channel": {"id": str(channel.id), "name": channel.name, "guild_id": str(channel.guild.id)}, "messages": messages}


async def panel_channel_send(channel_id, content):
    if not bot.is_ready():
        raise RuntimeError("Discord-бот ещё подключается.")
    content = str(content or "").strip()
    if not content:
        raise ValueError("Сообщение не может быть пустым.")
    if len(content) > 2000:
        raise ValueError("Discord ограничивает сообщение 2000 символами.")
    if not str(channel_id).isdigit():
        raise ValueError("Некорректный ID канала.")
    channel = await bot.fetch_channel(int(channel_id))
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("Отправлять можно только в текстовые каналы.")
    permissions = channel.permissions_for(channel.guild.me)
    if not permissions.view_channel or not permissions.send_messages:
        raise PermissionError("У бота нет права отправлять сообщения в этот канал.")
    message = await channel.send(content, allowed_mentions=discord.AllowedMentions.none())
    return {"ok": True, "message": {"id": str(message.id), "content": message.content, "created_at": message.created_at.isoformat(), "author": await panel_dm_user_payload(message.author), "attachments": [], "embeds": []}}


async def run_services():
    """Запускает Discord-бота и FastAPI в одном процессе Bot-Hosting."""
    from dashboard.backend.main import app as panel_app

    panel_app.state.bot_controller = {
        "status": panel_console_status,
        "command": panel_console_command,
        "app_command": panel_application_command,
        "output": panel_console_output,
        "tickets": panel_tickets_list,
        "ticket_status": panel_ticket_status,
        "ticket_acceptance": panel_ticket_acceptance,
        "set_ticket_acceptance": panel_set_ticket_acceptance,
        "sheets_candidates": panel_sheets_candidates,
        "sheets_add_staff": panel_sheets_add_staff,
        "dm_list": panel_dm_list,
        "dm_search": panel_dm_search,
        "dm_history": panel_dm_history,
        "dm_send": panel_dm_send,
        "discord_guilds": panel_guild_list,
        "discord_members": panel_guild_members,
        "discord_channels": panel_guild_channels,
        "discord_channel_history": panel_channel_history,
        "discord_channel_send": panel_channel_send,
        "actions": {
            "sync_commands": panel_sync_commands,
            "sync_roles": panel_sync_roles,
            "refresh_presence": panel_refresh_presence,
            "restart": panel_restart_bot,
        },
    }

    port = int(os.getenv("SERVER_PORT") or os.getenv("PORT") or "25819")
    config = uvicorn.Config(
        panel_app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    web_server = uvicorn.Server(config)

    print(f"🌐 Запускаю GastWorld Control Panel на порту {port}...", flush=True)
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
