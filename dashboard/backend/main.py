import json
import os
import secrets
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISCORD_API = "https://discord.com/api/v10"
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/auth/callback")
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "1546125037545988207")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
BOT_SYNC_SECRET = os.getenv("BOT_SYNC_SECRET", "")
PANEL_DB_PATH = os.getenv("PANEL_DB_PATH", os.path.join(os.path.dirname(__file__), "panel.db"))
ACCESS_RANK = {"none": 0, "media": 1, "co_adm": 2, "adm": 3, "full": 4}

def init_panel_db() -> None:
    import sqlite3
    with sqlite3.connect(PANEL_DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS access_roles (
            guild_id TEXT NOT NULL,
            role_id TEXT NOT NULL,
            access_level TEXT NOT NULL,
            role_name TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, role_id)
        )""")
        db.commit()

init_panel_db()

def get_role_access_map() -> dict[str, str]:
    import sqlite3
    with sqlite3.connect(PANEL_DB_PATH) as db:
        rows = db.execute(
            "SELECT role_id, access_level FROM access_roles WHERE guild_id = ?",
            (GUILD_ID,)
        ).fetchall()
    return {str(role_id): level for role_id, level in rows}

app = FastAPI(title="WhiteGrief Control Panel API")
if not SESSION_SECRET:
    # Local-only fallback. Set a long random SESSION_SECRET before deployment.
    SESSION_SECRET = secrets.token_urlsafe(48)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="wg_panel_session",
    same_site="lax",
    https_only=os.getenv("COOKIE_HTTPS_ONLY", "false").lower() == "true",
    max_age=60 * 60 * 8,
)



def configuration_status() -> dict[str, bool]:
    return {
        "oauth": bool(CLIENT_ID and CLIENT_SECRET),
        "bot": bool(BOT_TOKEN),
        "session_secret": bool(os.getenv("SESSION_SECRET")),
        "redirect_uri": bool(REDIRECT_URI),
        "bot_sync": bool(BOT_SYNC_SECRET),
        "access_roles": bool(get_role_access_map()),
    }


async def discord_get(path: str, token: str, *, bot: bool = False) -> Any:
    headers = {"Authorization": f"Bot {token}" if bot else f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get(f"{DISCORD_API}{path}", headers=headers)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Discord API error ({response.status_code})")
    return response.json()


async def current_user(request: Request) -> dict[str, Any] | None:
    user = request.session.get("user")
    return user if isinstance(user, dict) else None


async def refresh_session_user(request: Request) -> dict[str, Any] | None:
    """Повторно проверяет членство и роли в Discord, чтобы снятая роль сразу закрывала доступ."""
    user = await current_user(request)
    if not user:
        return None
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Не настроен DISCORD_BOT_TOKEN для проверки доступа.")

    try:
        member = await discord_get(f"/guilds/{GUILD_ID}/members/{user['id']}", BOT_TOKEN, bot=True)
        guild_roles = await discord_get(f"/guilds/{GUILD_ID}/roles", BOT_TOKEN, bot=True)
    except HTTPException as exc:
        if "404" in str(exc.detail):
            request.session.clear()
            return None
        raise

    role_ids = [str(role_id) for role_id in member.get("roles", [])]
    access = calculate_access(role_ids)
    if access == "none":
        request.session.clear()
        return None

    role_names = {str(role["id"]): role["name"] for role in guild_roles}
    user.update({
        "role_ids": role_ids,
        "role_names": [role_names.get(role_id, "Неизвестная роль") for role_id in role_ids],
        "is_media": access != "none",
        "access_level": access,
    })
    request.session["user"] = user
    return user


async def require_user(request: Request) -> dict[str, Any]:
    user = await refresh_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Нет доступа. Войди через Discord и проверь роль WhiteGrief.")
    return user


async def require_access(request: Request, minimum: str) -> dict[str, Any]:
    user = await require_user(request)
    if ACCESS_RANK.get(user.get("access_level", "none"), 0) < ACCESS_RANK[minimum]:
        raise HTTPException(status_code=403, detail="Недостаточно прав для этого действия.")
    return user


def calculate_access(role_ids: list[str]) -> str:
    role_map = get_role_access_map()
    levels = [role_map.get(role_id, "none") for role_id in role_ids]
    valid = [level for level in levels if level in ACCESS_RANK]
    return max(valid, key=lambda level: ACCESS_RANK[level], default="none")


@app.get("/")
async def index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/style.css")
async def stylesheet():
    return FileResponse(os.path.join(BASE_DIR, "style.css"), media_type="text/css")


@app.get("/app.js")
async def frontend_script():
    return FileResponse(os.path.join(BASE_DIR, "app.js"), media_type="application/javascript")


@app.get("/auth/login")
async def auth_login(request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="OAuth2 ещё не настроен. Заполните DISCORD_CLIENT_ID и DISCORD_CLIENT_SECRET.")
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "consent",
    }
    from urllib.parse import urlencode
    return RedirectResponse(f"https://discord.com/oauth2/authorize?{urlencode(params)}")


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = "", state: str = ""):
    expected_state = request.session.pop("oauth_state", None)
    if not code or not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="OAuth state не прошёл проверку. Попробуйте войти ещё раз.")

    token_payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            f"{DISCORD_API}/oauth2/token",
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Не удалось завершить вход через Discord.")
        token_data = token_response.json()
        profile_response = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        if profile_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Discord не вернул профиль пользователя.")
        profile = profile_response.json()

    # Membership and roles are checked server-side using the bot token.
    # The bot must be in the configured server and have access to view its members.
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Не настроен DISCORD_BOT_TOKEN для проверки сервера.")
    try:
        member = await discord_get(f"/guilds/{GUILD_ID}/members/{profile['id']}", BOT_TOKEN, bot=True)
        guild_roles = await discord_get(f"/guilds/{GUILD_ID}/roles", BOT_TOKEN, bot=True)
    except HTTPException as exc:
        if "404" in str(exc.detail):
            raise HTTPException(status_code=403, detail="Ты не состоишь на Discord-сервере WhiteGrief.")
        raise

    member_role_ids = [str(role_id) for role_id in member.get("roles", [])]
    role_names = {str(role["id"]): role["name"] for role in guild_roles}
    access = calculate_access(member_role_ids)
    if access == "none":
        raise HTTPException(status_code=403, detail="У тебя нет роли доступа WhiteGrief Control Panel. Обратись к администрации Media.")

    request.session.clear()
    request.session["user"] = {
        "id": str(profile["id"]),
        "username": profile.get("global_name") or profile.get("username", "Discord user"),
        "discord_username": profile.get("username", ""),
        "avatar": profile.get("avatar"),
        "guild_id": GUILD_ID,
        "role_ids": member_role_ids,
        "role_names": [role_names.get(role_id, "Неизвестная роль") for role_id in member_role_ids],
        "is_media": access != "none",
        "access_level": access,
    }
    return RedirectResponse("/", status_code=303)


@app.get("/api/me")
async def api_me(request: Request):
    user = await refresh_session_user(request)
    return {
        "authenticated": bool(user),
        "user": user,
        "configuration": configuration_status(),
        "access_levels": list(ACCESS_RANK.keys()),
    }


@app.post("/auth/logout")
async def auth_logout(request: Request):
    request.session.clear()
    return {"ok": True}


WARN_ROLE_IDS = {1: "1546125538198823033", 2: "1546125541571043398", 3: "1546125544888729761"}
PROTECTED_ROLE_IDS = {"1546125455633944598", "1546125498340614195", "1546125488496451686", "1546125469093732372", "1546125465482174484", "1547654044263252038", "1546125472897961984", "1546125480321749053", "1550200782177968178"}

def bot_database_path() -> str:
    return os.getenv("BOT_DB_PATH", os.path.join(os.path.dirname(BASE_DIR), "bot_data.db"))

async def discord_request(method: str, path: str, *, payload: dict[str, Any] | None = None) -> Any:
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Не настроен DISCORD_BOT_TOKEN.")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.request(method, f"{DISCORD_API}{path}", headers={"Authorization": f"Bot {BOT_TOKEN}"}, json=payload)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Участник не найден на Discord-сервере.")
    if response.status_code == 403:
        raise HTTPException(status_code=502, detail="Боту не хватает прав или его роль ниже роли участника.")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Ошибка Discord API ({response.status_code}).")
    return response.json() if response.content else None

async def change_warns(request: Request, user_id: str, delta: int, reason: str) -> dict[str, Any]:
    await require_access(request, "co_adm")
    if not user_id.isdigit() or not reason.strip():
        raise HTTPException(status_code=400, detail="Укажи корректный Discord ID и причину.")
    member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{user_id}")
    role_ids = {str(x) for x in member.get("roles", [])}
    if role_ids & PROTECTED_ROLE_IDS:
        raise HTTPException(status_code=403, detail="Нельзя менять варны участнику с защищённой ролью администрации.")
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена.")
    try:
        with sqlite3.connect(path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT warns FROM users WHERE user_id = ?", (int(user_id),)).fetchone()
            current = int(row[0]) if row else 0
            updated = max(0, min(3, current + delta))
            if updated == current:
                raise HTTPException(status_code=409, detail="Количество варнов уже на этом уровне.")
            new_roles = role_ids - set(WARN_ROLE_IDS.values())
            if updated:
                new_roles.add(WARN_ROLE_IDS[updated])
            await discord_request("PATCH", f"/guilds/{GUILD_ID}/members/{user_id}", payload={"roles": sorted(new_roles)})
            db.execute("INSERT INTO users (user_id, balance, warns, personal_channel_id) VALUES (?, 0, ?, NULL) ON CONFLICT(user_id) DO UPDATE SET warns = excluded.warns", (int(user_id), updated))
            db.commit()
    except HTTPException:
        raise
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Ошибка базы данных бота.")
    return {"ok": True, "user_id": user_id, "warns": updated, "reason": reason.strip()}

@app.post("/api/players/{user_id}/warn")
async def api_add_warn(user_id: str, request: Request):
    payload = await request.json()
    return await change_warns(request, user_id, 1, str(payload.get("reason", "")))

@app.post("/api/players/{user_id}/remove-warn")
async def api_remove_warn(user_id: str, request: Request):
    payload = await request.json()
    return await change_warns(request, user_id, -1, str(payload.get("reason", "")))

@app.get("/api/requests")
async def api_requests(request: Request):
    await require_access(request, "co_adm")
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена.")
    try:
        with sqlite3.connect(path, timeout=10) as db:
            rows = db.execute("SELECT request_type, user_id, message_id, data, created_at FROM pending_requests ORDER BY created_at").fetchall()
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Не удалось прочитать заявки.")
    return {"requests": [{"type": row[0], "user_id": row[1], "message_id": row[2], "data": json.loads(row[3]), "created_at": row[4]} for row in rows]}

@app.get("/api/shop")
async def api_shop(request: Request):
    await require_access(request, "media")
    return {"items": SHOP_ITEMS_PANEL}

SHOP_ITEMS_PANEL = [
    {"name": "PVP", "price": 1000, "type": "kit"}, {"name": "CYBER", "price": 1500, "type": "kit"},
    {"name": "RICH", "price": 2000, "type": "kit"}, {"name": "TOPER", "price": 2500, "type": "kit"},
    {"name": "D.OWNER", "price": 2300, "type": "kit"}, {"name": "DADMIN", "price": 1000, "type": "kit"},
    {"name": "D.GLMODER", "price": 900, "type": "kit"}, {"name": "D.STMODER", "price": 750, "type": "kit"},
    {"name": "D.MODER", "price": 500, "type": "kit"}, {"name": "WHITE", "price": 5000, "type": "donat"},
    {"name": "RABBIT", "price": 4500, "type": "donat"}, {"name": "DHELPER", "price": 4500, "type": "donat"},
    {"name": "GOD", "price": 4000, "type": "donat"}, {"name": "ENDER", "price": 4000, "type": "donat"},
    {"name": "DRACULA", "price": 3500, "type": "donat"}, {"name": "BERSERK", "price": 3500, "type": "donat"},
    {"name": "COBRA", "price": 3000, "type": "donat"},
    {"name": "Кейс «Всё или ничего»", "price": 6000, "type": "кейс"},
    {"name": "Кейс с Супер Донатом", "price": 4500, "type": "кейс"},
    {"name": "Кейс с Супер Риллами", "price": 3000, "type": "кейс"},
    {"name": "Снятие 1 выговора", "price": 400, "type": "услуга"}
]
@app.get("/api/players")
async def api_players(request: Request):
    await require_access(request, "media")
    import sqlite3
    bot_db_path = os.getenv("BOT_DB_PATH", os.path.join(os.path.dirname(BASE_DIR), "bot_data.db"))
    if not os.path.isfile(bot_db_path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена. Проверь BOT_DB_PATH.")
    try:
        with sqlite3.connect(bot_db_path, timeout=10) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT user_id, balance, warns FROM users ORDER BY user_id"
            ).fetchall()
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Не удалось прочитать базу данных игроков.")
    return {"players": [dict(row) for row in rows], "count": len(rows)}


@app.get("/health")
async def health():
    return {"ok": True, "service": "whitegrief-control-panel"}


@app.post("/api/internal/sync-roles")
async def sync_access_roles(request: Request):
    supplied_secret = request.headers.get("X-Bot-Sync-Secret", "")
    if not BOT_SYNC_SECRET or not secrets.compare_digest(supplied_secret, BOT_SYNC_SECRET):
        raise HTTPException(status_code=403, detail="Недействительный ключ синхронизации")
    payload = await request.json()
    guild_id = str(payload.get("guild_id", ""))
    roles = payload.get("roles", {})
    if guild_id != GUILD_ID or not isinstance(roles, dict):
        raise HTTPException(status_code=400, detail="Некорректный сервер или список ролей")
    allowed = {"full", "adm", "co_adm", "media"}
    normalized = []
    for role_id, info in roles.items():
        if not isinstance(info, dict):
            continue
        level = str(info.get("access_level", ""))
        role_name = str(info.get("name", ""))[:100]
        if level not in allowed or not str(role_id).isdigit() or not role_name:
            continue
        normalized.append((guild_id, str(role_id), level, role_name))
    if len(normalized) != 4:
        raise HTTPException(status_code=400, detail="Ожидались все четыре роли доступа")
    import sqlite3
    with sqlite3.connect(PANEL_DB_PATH) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM access_roles WHERE guild_id = ?", (guild_id,))
        db.executemany(
            "INSERT INTO access_roles (guild_id, role_id, access_level, role_name) VALUES (?, ?, ?, ?)",
            normalized,
        )
        db.commit()
    return {"ok": True, "synced": len(normalized)}
