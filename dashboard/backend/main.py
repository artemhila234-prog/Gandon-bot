import json
import base64
import binascii
from datetime import datetime, timezone
import os
import asyncio
import secrets
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISCORD_API = "https://discord.com/api/v10"
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/auth/callback")
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "1546125037545988207")
PLAYER_LIST_ROLE_ID = "1546125522675962027"
AUDIT_LOG_CHANNEL_ID = os.getenv("AUDIT_LOG_CHANNEL_ID", "1546125784026972262")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
BOT_SYNC_SECRET = os.getenv("BOT_SYNC_SECRET", "")
BOT_API_URL = os.getenv("BOT_API_URL", "").rstrip("/")
BOT_DATA_API_SECRET = os.getenv("BOT_DATA_API_SECRET", "")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://med1a.apps.bot-hosting.cloud/tiktok/callback")
TIKTOK_TOKEN_ENCRYPTION_KEY = os.getenv("TIKTOK_TOKEN_ENCRYPTION_KEY", "")
TIKTOK_SCOPES = "user.info.basic,user.info.profile,video.list"
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
        db.execute("""CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            theme TEXT NOT NULL DEFAULT 'system',
            accent TEXT NOT NULL DEFAULT 'purple',
            compact_mode INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS panel_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.executemany(
            "INSERT OR IGNORE INTO panel_settings (setting_key, setting_value) VALUES (?, ?)",
            [("announcement_enabled", "false"), ("announcement_text", ""), ("default_theme", "dark")]
        )
        db.commit()

init_panel_db()


def get_global_panel_settings() -> dict[str, Any]:
    import sqlite3
    defaults = {"announcement_enabled": False, "announcement_text": "", "default_theme": "dark"}
    with sqlite3.connect(PANEL_DB_PATH) as db:
        rows = db.execute("SELECT setting_key, setting_value FROM panel_settings").fetchall()
    values = {str(key): str(value) for key, value in rows}
    return {
        "announcement_enabled": values.get("announcement_enabled", "false").lower() == "true",
        "announcement_text": values.get("announcement_text", defaults["announcement_text"]),
        "default_theme": values.get("default_theme", defaults["default_theme"]),
    }


def get_user_panel_preferences(user_id: str) -> dict[str, Any]:
    import sqlite3
    with sqlite3.connect(PANEL_DB_PATH) as db:
        row = db.execute(
            "SELECT theme, accent, compact_mode FROM user_preferences WHERE user_id = ?",
            (str(user_id),)
        ).fetchone()
    if not row:
        return {"theme": "system", "accent": "purple", "compact_mode": False}
    return {"theme": row[0], "accent": row[1], "compact_mode": bool(row[2])}


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
        "bot_api": bool(BOT_API_URL and BOT_DATA_API_SECRET),
        "tiktok_oauth": bool(TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET and TIKTOK_REDIRECT_URI),
        "tiktok_encryption": bool(TIKTOK_TOKEN_ENCRYPTION_KEY),
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


@app.get("/terms")
@app.get("/terms/")
async def terms_page():
    return FileResponse(os.path.join(BASE_DIR, "terms.html"), media_type="text/html; charset=utf-8")

@app.get("/privacy")
@app.get("/privacy/")
async def privacy_page():
    return FileResponse(os.path.join(BASE_DIR, "privacy.html"), media_type="text/html; charset=utf-8")

@app.get("/style.css")
async def stylesheet():
    return FileResponse(os.path.join(BASE_DIR, "style.css"), media_type="text/css")


@app.get("/app.js")
async def frontend_script():
    return FileResponse(os.path.join(BASE_DIR, "app.js"), media_type="application/javascript")

@app.get("/tiktokm5Y1iWvDkXPyhVbml4Yb7W3NE8WSScOd.txt")
async def tiktok_site_verification():
    verification_file = os.path.join(BASE_DIR, "tiktokm5Y1iWvDkXPyhVbml4Yb7W3NE8WSScOd.txt")
    return FileResponse(verification_file, media_type="text/plain")


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
        if "/members/" in path:
            raise HTTPException(status_code=404, detail=f"Discord не нашёл участника {path.rsplit('/', 1)[-1]} на сервере {GUILD_ID}. Проверь, что пользователь состоит на этом сервере и что DISCORD_GUILD_ID на первом хостинге указан верно.")
        raise HTTPException(status_code=404, detail="Объект не найден в Discord. Проверь ID канала, сообщения или сервера.")
    if response.status_code == 403:
        raise HTTPException(status_code=502, detail="Боту не хватает прав или его роль ниже роли участника.")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Ошибка Discord API ({response.status_code}).")
    return response.json() if response.content else None


@app.get("/api/access/members")
async def api_access_members(request: Request):
    """Полный список участников сервера для вкладки «Доступ» (только Adm/Full)."""
    await require_access(request, "adm")
    roles = await discord_request("GET", f"/guilds/{GUILD_ID}/roles")
    role_by_id = {
        str(role.get("id")): {
            "id": str(role.get("id")),
            "name": str(role.get("name") or "Без названия"),
            "color": int(role.get("color") or 0),
            "position": int(role.get("position") or 0),
            "managed": bool(role.get("managed")),
        }
        for role in roles if isinstance(role, dict) and role.get("id")
    }

    members = []
    after = "0"
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            response = await client.get(
                f"{DISCORD_API}/guilds/{GUILD_ID}/members",
                params={"limit": 1000, "after": after},
                headers={"Authorization": f"Bot {BOT_TOKEN}"},
            )
            if response.status_code == 429:
                try:
                    retry_after = min(float(response.json().get("retry_after", 1)), 10)
                except Exception:
                    retry_after = 1
                await asyncio.sleep(max(0.5, retry_after))
                continue
            if response.status_code == 403:
                raise HTTPException(status_code=502, detail="Discord запретил чтение списка участников. Проверь включённый Server Members Intent и права бота.")
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Не удалось загрузить участников Discord (HTTP {response.status_code}).")
            batch = response.json()
            if not isinstance(batch, list):
                raise HTTPException(status_code=502, detail="Discord вернул некорректный список участников.")
            for member in batch:
                user = member.get("user") or {}
                user_id = str(user.get("id") or "")
                if not user_id:
                    continue
                member_role_ids = [str(role_id) for role_id in member.get("roles", [])]
                members.append({
                    "id": user_id,
                    "username": str(user.get("username") or "unknown"),
                    "display_name": str(member.get("nick") or user.get("global_name") or user.get("username") or "Игрок"),
                    "global_name": str(user.get("global_name") or ""),
                    "avatar": (
                        f"https://cdn.discordapp.com/avatars/{user_id}/{user.get('avatar')}.png?size=64"
                        if user.get("avatar") else ""
                    ),
                    "bot": bool(user.get("bot")),
                    "role_ids": member_role_ids,
                    "roles": [
                        {"id": rid, "name": role_by_id[rid]["name"], "color": role_by_id[rid]["color"]}
                        for rid in member_role_ids if rid in role_by_id
                    ],
                })
            if len(batch) < 1000:
                break
            next_after = str((batch[-1].get("user") or {}).get("id") or "")
            if not next_after or next_after == after:
                break
            after = next_after

    members.sort(key=lambda item: (item["display_name"].casefold(), item["username"].casefold()))
    role_items = sorted(role_by_id.values(), key=lambda role: (role["position"], role["name"].casefold()), reverse=True)
    return {
        "members": members,
        "roles": role_items,
        "total_members": len(members),
        "total_roles": len(role_items),
        "guild_name": "WhiteGrief",
        "guild_id": GUILD_ID,
    }


@app.get("/api/settings")
async def api_settings(request: Request):
    user = await require_user(request)
    is_admin = ACCESS_RANK.get(user.get("access_level", "none"), 0) >= ACCESS_RANK["adm"]
    result: dict[str, Any] = {
        "is_admin": is_admin,
        "current_access_level": user.get("access_level", "none"),
        "preferences": get_user_panel_preferences(str(user["id"])),
        "global_settings": get_global_panel_settings(),
        "configuration": configuration_status() if is_admin else None,
        "guild_id": GUILD_ID if is_admin else None,
        "guild_name": "WhiteGrief" if is_admin else None,
        "discord_connected": False,
        "roles": [],
        "channels": [],
        "channels_error": "",
    }
    if not is_admin:
        return result

    role_map = get_role_access_map()
    try:
        roles = await discord_request("GET", f"/guilds/{GUILD_ID}/roles")
        channels = await discord_request("GET", f"/guilds/{GUILD_ID}/channels")
        result["discord_connected"] = True
        result["roles"] = [
            {
                "id": str(role.get("id", "")),
                "name": str(role.get("name", "Без названия")),
                "access_level": role_map.get(str(role.get("id", "")), "none"),
                "access_label": {
                    "full": "Full", "adm": "Adm", "co_adm": "Co.Adm",
                    "media": "Media", "none": "Без доступа",
                }.get(role_map.get(str(role.get("id", "")), "none"), "Без доступа"),
                "position": int(role.get("position", 0)),
            }
            for role in roles if str(role.get("id", "")) != GUILD_ID and not role.get("managed", False)
        ]
        result["roles"].sort(key=lambda item: item["position"], reverse=True)
        result["channels"] = [
            {"id": str(channel.get("id", "")), "name": str(channel.get("name", ""))}
            for channel in channels
            if channel.get("type") in (0, 5) and str(channel.get("guild_id", GUILD_ID)) == GUILD_ID
        ]
        result["channels"].sort(key=lambda item: item["name"].casefold())
    except HTTPException as exc:
        result["channels_error"] = str(exc.detail)
    return result


@app.get("/api/settings/live")
async def api_settings_live(request: Request):
    # Polling endpoint uses the already-authenticated session cookie and avoids
    # repeated Discord member/role lookups every few seconds.
    user = await current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Сначала войди через Discord.")
    return {
        "global_settings": get_global_panel_settings(),
        "preferences": get_user_panel_preferences(str(user["id"])),
    }


@app.post("/api/settings/preferences")
async def api_save_preferences(request: Request):
    user = await require_user(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ожидался объект настроек.")
    theme = payload.get("theme", "system")
    accent = payload.get("accent", "purple")
    compact_mode = payload.get("compact_mode", False)
    if not isinstance(theme, str) or theme not in {"system", "dark", "light"}:
        raise HTTPException(status_code=400, detail="Неизвестная тема оформления.")
    if not isinstance(accent, str) or accent not in {"purple", "blue", "green", "red"}:
        raise HTTPException(status_code=400, detail="Неизвестный цвет акцента.")
    if not isinstance(compact_mode, bool):
        raise HTTPException(status_code=400, detail="compact_mode должен быть true или false.")
    import sqlite3
    with sqlite3.connect(PANEL_DB_PATH) as db:
        db.execute(
            """INSERT INTO user_preferences (user_id, theme, accent, compact_mode, updated_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id) DO UPDATE SET
               theme=excluded.theme, accent=excluded.accent,
               compact_mode=excluded.compact_mode, updated_at=CURRENT_TIMESTAMP""",
            (str(user["id"]), theme, accent, int(compact_mode)),
        )
        db.commit()
    return {"ok": True, "preferences": get_user_panel_preferences(str(user["id"]))}


@app.post("/api/settings/access-roles")
async def api_save_access_roles(request: Request):
    actor = await require_access(request, "adm")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON.")
    submitted = payload.get("roles") if isinstance(payload, dict) else None
    if not isinstance(submitted, list) or not submitted:
        raise HTTPException(status_code=400, detail="Передай список ролей и уровней доступа.")

    try:
        discord_roles = await discord_request("GET", f"/guilds/{GUILD_ID}/roles")
    except HTTPException as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось получить актуальные роли Discord: {exc.detail}")
    actual = {
        str(role.get("id")): str(role.get("name", "Без названия"))[:100]
        for role in discord_roles
        if str(role.get("id", "")) != GUILD_ID and not role.get("managed", False)
    }
    normalized = {}
    allowed = {"none", "media", "co_adm", "adm", "full"}
    for item in submitted:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Некорректная запись роли.")
        role_id = str(item.get("id", ""))
        level = str(item.get("access_level", ""))
        if role_id not in actual or level not in allowed:
            raise HTTPException(status_code=400, detail="В списке есть неизвестная роль или уровень доступа.")
        if role_id in normalized:
            raise HTTPException(status_code=400, detail="Одна и та же роль указана несколько раз.")
        normalized[role_id] = level
    if set(normalized) != set(actual):
        raise HTTPException(status_code=400, detail="Список ролей устарел. Обнови настройки и попробуй снова.")

    old_map = get_role_access_map()
    actor_is_full = actor.get("access_level") == "full"
    if not actor_is_full:
        for role_id, level in normalized.items():
            if level == "full":
                raise HTTPException(status_code=403, detail="Назначать уровень Full может только пользователь Full.")
            if old_map.get(role_id) == "full" and level != "full":
                raise HTTPException(status_code=403, detail="Изменять или снимать уровень Full может только пользователь Full.")

    if not any(level == "full" for level in normalized.values()):
        raise HTTPException(status_code=400, detail="Нельзя убрать последний уровень Full: должен остаться хотя бы один владелец панели.")

    actor_level = max(
        (level for role_id, level in normalized.items() if role_id in set(map(str, actor.get("role_ids", [])))),
        key=lambda level: ACCESS_RANK.get(level, 0),
        default="none",
    )
    if ACCESS_RANK.get(actor_level, 0) < ACCESS_RANK["adm"]:
        raise HTTPException(status_code=400, detail="Нельзя снять собственный доступ Adm/Full во время этой сессии.")

    import sqlite3
    rows = [(GUILD_ID, role_id, level, actual[role_id]) for role_id, level in normalized.items()]
    with sqlite3.connect(PANEL_DB_PATH) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM access_roles WHERE guild_id = ?", (GUILD_ID,))
        db.executemany(
            "INSERT INTO access_roles (guild_id, role_id, access_level, role_name, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            rows,
        )
        db.commit()
    return {"ok": True, "saved": len(rows), "roles": [
        {"id": role_id, "name": actual[role_id], "access_level": normalized[role_id]}
        for role_id in sorted(normalized, key=lambda rid: next((int(r.get("position", 0)) for r in discord_roles if str(r.get("id")) == rid), 0), reverse=True)
    ]}


@app.post("/api/settings/admin")
async def api_save_admin_settings(request: Request):
    await require_access(request, "adm")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ожидался объект настроек.")
    announcement_enabled = payload.get("announcement_enabled", False)
    announcement_text = payload.get("announcement_text", "")
    default_theme = payload.get("default_theme", "dark")
    if not isinstance(announcement_enabled, bool):
        raise HTTPException(status_code=400, detail="announcement_enabled должен быть true или false.")
    if not isinstance(announcement_text, str) or len(announcement_text) > 350:
        raise HTTPException(status_code=400, detail="Текст уведомления должен быть не длиннее 350 символов.")
    if not isinstance(default_theme, str) or default_theme not in {"dark", "light"}:
        raise HTTPException(status_code=400, detail="Неизвестная тема по умолчанию.")
    values = {
        "announcement_enabled": "true" if announcement_enabled else "false",
        "announcement_text": announcement_text.strip(),
        "default_theme": default_theme,
    }
    import sqlite3
    with sqlite3.connect(PANEL_DB_PATH) as db:
        db.executemany(
            """INSERT INTO panel_settings (setting_key, setting_value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(setting_key) DO UPDATE SET
               setting_value=excluded.setting_value, updated_at=CURRENT_TIMESTAMP""",
            list(values.items()),
        )
        db.commit()
    return {"ok": True, "global_settings": get_global_panel_settings()}


async def bot_api_request(method: str, path: str, *, payload: dict[str, Any] | None = None) -> Any:
    if not BOT_API_URL or not BOT_DATA_API_SECRET:
        raise HTTPException(status_code=503, detail="Связь с сервером бота не настроена.")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method, f"{BOT_API_URL}{path}",
                headers={"X-Bot-Data-Secret": BOT_DATA_API_SECRET},
                json=payload,
            )
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", "Ошибка API сервера бота.")
            except Exception:
                detail = "Ошибка API сервера бота."
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json() if response.content else None
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Не удалось связаться с сервером Discord-бота.")


async def change_warns(request: Request, user_id: str, delta: int, reason: str) -> dict[str, Any]:
    user = await require_access(request, "co_adm")
    if not user_id.isdigit() or not reason.strip():
        raise HTTPException(status_code=400, detail="Укажи корректный Discord ID и причину.")
    actor_name = str(user.get("global_name") or user.get("username") or user.get("discord_username") or "Участник")[:80]
    return await bot_api_request(
        "POST", f"/api/internal/data/players/{user_id}/warn",
        payload={
            "delta": delta,
            "reason": reason.strip(),
            "actor_id": str(user.get("id", "")),
            "actor_name": actor_name,
        },
    )

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
    result = await bot_api_request("GET", "/api/internal/data/requests")
    # Discord snowflake IDs exceed JavaScript's safe integer range.
    # Convert them to strings before returning JSON to the browser.
    for item in result.get("requests", []):
        if item.get("user_id") is not None:
            item["user_id"] = str(item["user_id"])
        if item.get("message_id") is not None:
            item["message_id"] = str(item["message_id"])
    return result

@app.post("/api/requests/{user_id}/approve")
async def api_approve_request(user_id: str, request: Request):
    actor = await require_access(request, "co_adm")
    if not user_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный Discord ID.")
    return await bot_api_request(
        "POST", f"/api/internal/data/requests/{user_id}/approve",
        payload={"actor_id": str(actor.get("id", "")),
                 "actor_name": str(actor.get("global_name") or actor.get("username") or "Модератор")[:80]},
    )

@app.post("/api/requests/{user_id}/reject")
async def api_reject_request(user_id: str, request: Request):
    actor = await require_access(request, "co_adm")
    if not user_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный Discord ID.")
    return await bot_api_request(
        "POST", f"/api/internal/data/requests/{user_id}/reject",
        payload={"actor_id": str(actor.get("id", "")),
                 "actor_name": str(actor.get("global_name") or actor.get("username") or "Модератор")[:80]},
    )

@app.get("/api/shop")
async def api_shop(request: Request):
    await require_access(request, "media")
    return {"items": SHOP_ITEMS_PANEL}


@app.get("/api/messages/channels")
async def api_message_channels(request: Request):
    user = await require_access(request, "adm")
    channels = await discord_request("GET", f"/guilds/{GUILD_ID}/channels")
    items = []
    for channel in channels if isinstance(channels, list) else []:
        if channel.get("type") in (0, 5) and str(channel.get("guild_id", GUILD_ID)) == GUILD_ID:
            items.append({
                "id": str(channel.get("id", "")),
                "name": str(channel.get("name", "")),
                "parent_name": str(channel.get("parent_name") or ""),
            })
    items.sort(key=lambda item: (item["parent_name"].casefold(), item["name"].casefold()))
    return {"channels": items, "sender": {"username": user.get("username", "Администратор"), "discord_username": user.get("discord_username", "")}}


@app.get("/api/messages/history")
async def api_message_history(request: Request, channel_id: str):
    await require_access(request, "adm")
    channel_id = str(channel_id).strip()
    if not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID канала.")
    channel = await discord_request("GET", f"/channels/{channel_id}")
    if str(channel.get("guild_id", "")) != GUILD_ID:
        raise HTTPException(status_code=403, detail="Этот канал не принадлежит серверу WhiteGrief.")
    raw_messages = await discord_request("GET", f"/channels/{channel_id}/messages?limit=50")
    channel_names = {}
    try:
        guild_channels = await discord_request("GET", f"/guilds/{GUILD_ID}/channels")
        if isinstance(guild_channels, list):
            channel_names = {str(c.get("id")): str(c.get("name") or "канал") for c in guild_channels}
    except Exception:
        pass

    def compact_message(message):
        if not isinstance(message, dict):
            return None
        author = message.get("author") or {}
        member = message.get("member") or {}
        return {
            "id": str(message.get("id", "")),
            "author": str(member.get("nick") or author.get("global_name") or author.get("username") or "Игрок"),
            "content": str(message.get("content") or "")[:350],
            "timestamp": str(message.get("timestamp") or ""),
        }

    items = []
    for message in raw_messages if isinstance(raw_messages, list) else []:
        author = message.get("author") or {}
        member = message.get("member") or {}
        avatar_hash = author.get("avatar")
        author_id = str(author.get("id") or "")
        avatar = (
            f"https://cdn.discordapp.com/avatars/{author_id}/{avatar_hash}.png"
            if avatar_hash and author_id else
            f"https://cdn.discordapp.com/embed/avatars/{int(author.get('discriminator') or '0') % 5}.png"
            if str(author.get("discriminator") or "").isdigit() else ""
        )
        attachments = [
            {"name": str(a.get("filename") or "Файл"), "url": str(a.get("url") or ""), "content_type": str(a.get("content_type") or "")}
            for a in message.get("attachments", []) if a.get("url")
        ]
        embeds = [
            {"title": str(e.get("title") or ""), "description": str(e.get("description") or "")[:1200]}
            for e in message.get("embeds", [])[:3]
            if e.get("title") or e.get("description")
        ]
        reference = message.get("referenced_message")
        message_reference = message.get("message_reference") or {}
        reply = compact_message(reference) if reference else None
        forwarded = []
        snapshots = message.get("message_snapshots") or []
        for snapshot in snapshots[:3]:
            snap_message = snapshot.get("message") if isinstance(snapshot, dict) else None
            snap = compact_message(snap_message)
            if snap:
                snap["channel_name"] = channel_names.get(str(message_reference.get("channel_id") or ""), "другого канала")
                forwarded.append(snap)
        items.append({
            "id": str(message.get("id", "")),
            "author_id": author_id,
            "author": str(member.get("nick") or author.get("global_name") or author.get("username") or "Игрок"),
            "avatar": avatar,
            "content": str(message.get("content") or ""),
            "timestamp": str(message.get("timestamp") or ""),
            "attachments": attachments,
            "embeds": embeds,
            "reply": reply,
            "forwarded": forwarded,
        })
    return {"messages": items}


@app.post("/api/messages/send")
async def api_send_message(request: Request):
    user = await require_access(request, "adm")
    form = None
    content_type = (request.headers.get("content-type") or "").lower()
    if "multipart/form-data" in content_type:
        try:
            # Ограничиваем количество частей на уровне парсера; размер файлов
            # дополнительно проверяется ниже до отправки в Discord.
            form = await request.form(max_files=10, max_fields=10)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Не удалось разобрать загрузку файлов ({type(exc).__name__}). Обнови страницу и попробуй ещё раз."
            )
        payload_field = form.get("payload_json")
        if not isinstance(payload_field, str):
            raise HTTPException(status_code=400, detail="В запросе отсутствует корректное описание сообщения (payload_json). Обнови страницу панели.")
        try:
            data = json.loads(payload_field)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Не удалось прочитать данные сообщения. Обнови страницу панели и попробуй ещё раз.")
    else:
        # Совместимость со старой вкладкой/кешированной версией frontend без файлов.
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Некорректные данные сообщения. Обнови страницу панели.")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Данные сообщения должны быть объектом JSON.")

    channel_id = str(data.get("channel_id", "")).strip()
    content = str(data.get("content", "")).strip()
    embed_data = data.get("embed")
    if not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Выбери текстовый канал Discord.")

    sender_name = str(user.get("global_name") or user.get("username") or user.get("discord_username") or "Администратор").strip()
    sender_id = str(user.get("id") or "").strip()
    if not sender_id.isdigit():
        raise HTTPException(status_code=400, detail="Не удалось определить Discord ID отправителя. Перезайди в панель.")
    sender_mention = f"<@{sender_id}>"
    attribution = f"-# Отправитель: {sender_mention} · WhiteGrief Control Panel"
    has_embed = isinstance(embed_data, dict) and bool(str(embed_data.get("title", "")).strip() or str(embed_data.get("description", "")).strip())
    if has_embed:
        embed_description = str(embed_data.get("description", "")).strip()
        final_description = (embed_description + "\n\n" if embed_description else "") + attribution
        if len(final_description) > 4096:
            raise HTTPException(status_code=400, detail="Описание Embed слишком длинное вместе с подписью отправителя.")
        embed_data = {**embed_data, "description": final_description}
    else:
        if content and len(content) + len(attribution) + 2 > 2000:
            raise HTTPException(status_code=400, detail="Слишком длинный текст: оставь место для подписи отправителя (лимит Discord — 2000 символов).")
        content = (content + "\n\n" if content else "") + attribution

    payload: dict[str, Any] = {"allowed_mentions": {"parse": []}}
    if content:
        payload["content"] = content
    if embed_data is not None:
        if not isinstance(embed_data, dict):
            raise HTTPException(status_code=400, detail="Некорректный Embed.")
        title = str(embed_data.get("title", "")).strip()
        description = str(embed_data.get("description", "")).strip()
        if len(title) > 256 or len(description) > 4096:
            raise HTTPException(status_code=400, detail="Embed превышает допустимую длину.")
        if title or description:
            try:
                color = int(str(embed_data.get("color", "#8b6bd6")).lstrip("#"), 16)
                if not 0 <= color <= 0xFFFFFF:
                    raise ValueError()
            except ValueError:
                raise HTTPException(status_code=400, detail="Некорректный цвет Embed.")
            payload["embeds"] = [{"title": title or None, "description": description or None, "color": color}]

    uploads = [item for item in form.getlist("files") if hasattr(item, "read")] if form is not None else []
    if len(uploads) > 10:
        raise HTTPException(status_code=400, detail="За одно сообщение можно прикрепить не больше 10 файлов.")
    discord_files = []
    total_size = 0
    for upload in uploads:
        raw_name = str(getattr(upload, "filename", "") or "file").replace("\\", "/").split("/")[-1]
        filename = raw_name.strip()[:100] or "file"
        file_bytes = await upload.read()
        if not file_bytes:
            continue
        if len(file_bytes) > 8 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"Файл «{filename}» больше 8 МБ.")
        total_size += len(file_bytes)
        if total_size > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Общий размер вложений не должен превышать 25 МБ.")
        mime = str(getattr(upload, "content_type", "") or "application/octet-stream")[:120]
        discord_files.append((filename, file_bytes, mime))

    if not content and not payload.get("embeds") and not discord_files:
        raise HTTPException(status_code=400, detail="Добавь текст, Embed или хотя бы один файл.")
    channel = await discord_request("GET", f"/channels/{channel_id}")
    if str(channel.get("guild_id", "")) != GUILD_ID or channel.get("type") not in (0, 5):
        raise HTTPException(status_code=400, detail="Можно отправлять только в текстовые каналы WhiteGrief.")

    if discord_files:
        files_payload = {f"files[{index}]": item for index, item in enumerate(discord_files)}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{DISCORD_API}/channels/{channel_id}/messages",
                headers={"Authorization": f"Bot {BOT_TOKEN}"},
                data={"payload_json": json.dumps(payload, ensure_ascii=False)},
                files=files_payload,
            )
        if response.status_code >= 400:
            detail = "Discord не принял вложения (HTTP " + str(response.status_code) + "). Проверь лимит размера и права бота."
            try:
                detail += " " + str(response.json().get("message", ""))[:250]
            except Exception:
                pass
            raise HTTPException(status_code=502, detail=detail)
        sent = response.json()
    else:
        sent = await discord_request("POST", f"/channels/{channel_id}/messages", payload=payload)
    return {"ok": True, "message_id": str(sent.get("id", "")), "attachments": len(discord_files)}

SHOP_ITEMS_PANEL = [
    {"name": "PVP", "price": 1000, "type": "kit"}, {"name": "CYBER", "price": 1500, "type": "kit"},
    {"name": "RICH", "price": 2000, "type": "kit"}, {"name": "TOPER", "price": 2500, "type": "kit"},
    {"name": "D.OWNER", "price": 2300, "type": "kit"}, {"name": "DADMIN", "price": 1000, "type": "kit"},
    {"name": "D.GLMODER", "price": 900, "type": "kit"}, {"name": "D.STMODER", "price": 750, "type": "kit"},
    {"name": "D.MODER", "price": 500, "type": "kit"}, {"name": "WHITE", "price": 5000, "type": "донат"},
    {"name": "RABBIT", "price": 4500, "type": "донат"}, {"name": "DHELPER", "price": 4500, "type": "донат"},
    {"name": "GOD", "price": 4000, "type": "донат"}, {"name": "ENDER", "price": 4000, "type": "донат"},
    {"name": "DRACULA", "price": 3500, "type": "донат"}, {"name": "BERSERK", "price": 3500, "type": "донат"},
    {"name": "COBRA", "price": 3000, "type": "донат"},
    {"name": "Кейс «Всё или ничего»", "price": 6000, "type": "кейс"},
    {"name": "Кейс с Супер Донатом", "price": 4500, "type": "кейс"},
    {"name": "Кейс с Супер Риликами", "price": 3000, "type": "кейс"},
    {"name": "Снятие 1 выговора", "price": 400, "type": "услуга"}
]
@app.get("/api/me/balance")
async def api_my_balance(request: Request):
    user = await require_access(request, "media")
    return await bot_api_request("GET", f"/api/internal/data/balance/{user['id']}")


@app.get("/api/logs")
async def api_logs(request: Request):
    await require_access(request, "adm")
    from urllib.parse import urlencode
    kind = (request.query_params.get("kind") or "system").lower()
    level = (request.query_params.get("level") or "all").lower()
    query = (request.query_params.get("q") or "")[:200]
    limit = request.query_params.get("limit", "250")
    if kind not in {"system", "audit"}:
        raise HTTPException(status_code=400, detail="Неизвестный тип журнала.")
    params = urlencode({"kind": kind, "level": level, "q": query, "limit": limit})
    return await bot_api_request("GET", f"/api/internal/data/logs?{params}")


@app.get("/api/log-files")
async def api_log_files(request: Request):
    await require_access(request, "adm")
    return await bot_api_request("GET", "/api/internal/data/log-files")


@app.get("/api/log-file")
async def api_log_file(request: Request):
    await require_access(request, "adm")
    from urllib.parse import urlencode
    name = (request.query_params.get("name") or "").strip()
    return await bot_api_request("GET", "/api/internal/data/log-file?" + urlencode({"name": name}))


@app.get("/api/console")
async def api_console(request: Request):
    await require_access(request, "adm")
    return await bot_api_request("GET", "/api/internal/console")


@app.get("/api/console/output")
async def api_console_output(request: Request):
    await require_access(request, "adm")
    from urllib.parse import urlencode
    try:
        after_id = max(0, int(request.query_params.get("after_id", "0")))
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректный курсор консоли.")
    return await bot_api_request("GET", "/api/internal/console/output?" + urlencode({"after_id": after_id}))


@app.post("/api/console/action")
async def api_console_action(request: Request):
    # Adm может выполнять только заранее определённые действия, включая рестарт.
    # Произвольный ввод команд ниже остаётся доступен исключительно Full.
    await require_access(request, "adm")
    payload = await request.json()
    action = str(payload.get("action", "")).strip()
    if action not in {"sync_commands", "sync_roles", "refresh_presence", "restart"}:
        raise HTTPException(status_code=400, detail="Неизвестное действие консоли.")
    return await bot_api_request("POST", "/api/internal/console/action", payload={"action": action})


@app.post("/api/console/command")
async def api_console_command(request: Request):
    await require_access(request, "full")
    payload = await request.json()
    command = str(payload.get("command", ""))
    if not command.strip() or len(command) > 2000:
        raise HTTPException(status_code=400, detail="Введи команду длиной до 2000 символов.")
    return await bot_api_request("POST", "/api/internal/console/command", payload={"command": command})

@app.post("/api/console/app-command")
async def api_console_app_command(request: Request):
    await require_access(request, "full")
    payload = await request.json()
    command = str(payload.get("command", ""))
    if not command.strip() or len(command) > 2000:
        raise HTTPException(status_code=400, detail="Введи ввод длиной до 2000 символов.")
    return await bot_api_request(
        "POST",
        "/api/internal/console/app-command",
        payload={"command": command},
    )


@app.get("/api/players")
async def api_players(request: Request):
    await require_access(request, "media")
    result = await bot_api_request("GET", "/api/internal/data/players")
    db_players = {
        str(player["user_id"]): player
        for player in result.get("players", [])
    }

    try:
        # Получаем всех участников сервера постранично, затем оставляем только нужную роль.
        members = []
        after = "0"
        while True:
            page = await discord_request(
                "GET",
                f"/guilds/{GUILD_ID}/members?limit=1000&after={after}"
            )
            if not isinstance(page, list) or not page:
                break
            members.extend(page)
            if len(page) < 1000:
                break
            last_user_id = str(page[-1].get("user", {}).get("id", ""))
            if not last_user_id or last_user_id == after:
                break
            after = last_user_id

        players = []
        for member in members:
            member_user = member.get("user", {})
            player_id = str(member_user.get("id", ""))
            role_ids = {str(role_id) for role_id in member.get("roles", [])}
            if not player_id or PLAYER_LIST_ROLE_ID not in role_ids:
                continue

            # Сохраняем реальные значения из БД; для новых участников используем нули.
            player = dict(db_players.get(player_id, {}))
            player["user_id"] = player_id
            player.setdefault("balance", 0)
            player.setdefault("warns", 0)
            player["username"] = member_user.get("global_name") or member_user.get("username") or "Участник"
            player["discord_username"] = member_user.get("username") or ""
            avatar_hash = member_user.get("avatar")
            player["avatar_url"] = (
                f"https://cdn.discordapp.com/avatars/{player_id}/{avatar_hash}.png?size=64"
                if avatar_hash else None
            )
            players.append(player)

        players.sort(key=lambda item: item["username"].casefold())
        return {"players": players, "count": len(players)}

    except (HTTPException, TypeError, AttributeError):
        # Не выдаём неполный список за полный при ошибке Discord API.
        raise HTTPException(status_code=502, detail="Не удалось получить полный список участников Discord. Проверь права бота и Server Members Intent.")


@app.get("/health")
async def health():
    return {"ok": True, "service": "whitegrief-control-panel"}



# ================== ЗАЩИЩЁННЫЙ API ДЛЯ ПАНЕЛИ ==================
def require_bot_data_secret(request: Request) -> None:
    supplied = request.headers.get("X-Bot-Data-Secret", "")
    expected = os.getenv("BOT_DATA_API_SECRET", "")
    if not expected or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="Недействительный ключ доступа к данным бота.")


@app.get("/api/internal/data/logs")
async def internal_data_logs(request: Request):
    require_bot_data_secret(request)
    from pathlib import Path
    from datetime import datetime
    import re

    kind = (request.query_params.get("kind") or "system").lower()
    level_filter = (request.query_params.get("level") or "all").upper()
    query = (request.query_params.get("q") or "").strip().casefold()[:200]
    try:
        limit = max(1, min(500, int(request.query_params.get("limit", "250"))))
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректный лимит логов.")
    if kind not in {"system", "audit"}:
        raise HTTPException(status_code=400, detail="Неизвестный тип журнала.")
    logs_dir = Path(os.path.dirname(BASE_DIR)) / "logs"
    if not logs_dir.is_dir():
        return {"entries": [], "count": 0, "available": False, "files": []}

    files = sorted(
        [path for path in logs_dir.glob("*.log") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    entries = []
    timestamp_pattern = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*(.*)$")
    for file_path in files:
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as log_file:
                for line_number, raw_line in enumerate(log_file, 1):
                    line = raw_line.rstrip("\r\n")
                    if not line.strip():
                        continue
                    match = timestamp_pattern.match(line)
                    timestamp = match.group(1) if match else ""
                    message = match.group(2) if match else line
                    is_audit = "[AUDIT]" in message.upper()
                    if (kind == "audit") != is_audit:
                        continue
                    upper = message.upper()
                    if "ERROR" in upper or "TRACEBACK" in upper or "EXCEPTION" in upper or "ОШИБКА" in upper:
                        level = "ERROR"
                    elif "WARNING" in upper or "WARN" in upper or "ПРЕДУПРЕЖД" in upper:
                        level = "WARNING"
                    elif is_audit:
                        level = "AUDIT"
                    else:
                        level = "INFO"
                    if level_filter != "ALL" and level != level_filter:
                        continue
                    if query and query not in message.casefold() and query not in file_path.name.casefold():
                        continue
                    entries.append({
                        "timestamp": timestamp,
                        "level": level,
                        "message": message[:4000],
                        "file": file_path.name,
                        "line": line_number,
                    })
        except OSError:
            continue
    entries.sort(key=lambda item: item["timestamp"], reverse=True)
    return {
        "entries": entries[:limit],
        "count": min(len(entries), limit),
        "total": len(entries),
        "available": True,
        "files": [path.name for path in files[:30]],
    }


@app.get("/api/internal/data/log-files")
async def internal_data_log_files(request: Request):
    require_bot_data_secret(request)
    from pathlib import Path
    from datetime import datetime
    logs_dir = Path(os.path.dirname(BASE_DIR)) / "logs"
    if not logs_dir.is_dir():
        return {"available": False, "files": []}
    files = []
    for path in sorted((p for p in logs_dir.iterdir() if p.is_file() and p.suffix.lower() == ".log"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            stat = path.stat()
            files.append({
                "name": path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
        except OSError:
            continue
    return {"available": True, "directory": "logs/", "files": files}


@app.get("/api/internal/data/log-file")
async def internal_data_log_file(request: Request):
    require_bot_data_secret(request)
    from pathlib import Path
    from datetime import datetime
    filename = (request.query_params.get("name") or "").strip()
    if not filename or Path(filename).name != filename or not filename.lower().endswith(".log"):
        raise HTTPException(status_code=400, detail="Некорректное имя файла.")
    logs_dir = Path(os.path.dirname(BASE_DIR)) / "logs"
    path = logs_dir / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Файл лога не найден.")
    try:
        with path.open("r", encoding="utf-8", errors="replace") as log_file:
            lines = log_file.readlines()
        max_lines = 5000
        truncated = len(lines) > max_lines
        selected = lines[-max_lines:]
        return {
            "name": path.name,
            "lines": [line.rstrip("\r\n") for line in selected],
            "total_lines": len(lines),
            "shown_lines": len(selected),
            "truncated": truncated,
            "size": path.stat().st_size,
            "modified": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        }
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось прочитать лог: {exc}")


@app.get("/api/internal/console")
async def internal_console(request: Request):
    require_bot_data_secret(request)
    controller = getattr(app.state, "bot_controller", None)
    if not controller:
        return {"status": {"online": False, "bot_name": "WhiteGrief", "guild_name": "Нет подключения к процессу бота", "guild_count": 0, "latency_ms": None}, "available": False}
    try:
        status = await controller["status"]()
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Не удалось получить статус бота: {error}")
    return {"status": status, "available": True, "updated_at": datetime.now(timezone.utc).isoformat()}


@app.get("/api/internal/console/output")
async def internal_console_output(request: Request):
    require_bot_data_secret(request)
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("output"):
        raise HTTPException(status_code=503, detail="Буфер вывода консоли не подключён.")
    try:
        after_id = max(0, int(request.query_params.get("after_id", "0")))
        return await controller["output"](after_id=after_id, limit=500)
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректный курсор консоли.")


@app.post("/api/internal/console/action")
async def internal_console_action(request: Request):
    require_bot_data_secret(request)
    controller = getattr(app.state, "bot_controller", None)
    if not controller:
        raise HTTPException(status_code=503, detail="Управление доступно только на хостинге Discord-бота.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный запрос.")
    action = str(payload.get("action", "")).strip()
    handler = controller.get("actions", {}).get(action)
    if handler is None:
        raise HTTPException(status_code=400, detail="Неизвестное действие консоли.")
    try:
        result = await handler()
        return {"ok": True, **(result if isinstance(result, dict) else {"message": "Готово."})}
    except Exception as error:
        print(f"❌ [ПАНЕЛЬ] Ошибка действия {action}: {error}", flush=True)
        raise HTTPException(status_code=500, detail=f"Действие не выполнено: {error}")

@app.post("/api/internal/console/command")
async def internal_console_command(request: Request):
    require_bot_data_secret(request)
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("command"):
        raise HTTPException(status_code=503, detail="Терминал не подключён к процессу бота.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный запрос.")
    command = str(payload.get("command", ""))
    try:
        return await controller["command"](command)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/api/internal/console/app-command")
async def internal_console_app_command(request: Request):
    require_bot_data_secret(request)
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("app_command"):
        raise HTTPException(status_code=503, detail="Ввод в приложение не подключён к процессу бота.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный запрос.")
    command = str(payload.get("command", ""))
    try:
        return await controller["app_command"](command)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/api/internal/data/players")
async def internal_data_players(request: Request):
    require_bot_data_secret(request)
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена на сервере бота.")
    try:
        with sqlite3.connect(path, timeout=10) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT user_id, balance, warns FROM users WHERE warns < 3 ORDER BY user_id"
            ).fetchall()
        return {"players": [dict(row) for row in rows], "count": len(rows)}
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Не удалось прочитать базу данных игроков.")


@app.get("/api/internal/data/requests")
async def internal_data_requests(request: Request):
    require_bot_data_secret(request)
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена на сервере бота.")
    try:
        with sqlite3.connect(path, timeout=10) as db:
            rows = db.execute(
                "SELECT request_type, user_id, message_id, data, created_at FROM pending_requests ORDER BY created_at"
            ).fetchall()
        return {"requests": [
            {"type": row[0], "user_id": row[1], "message_id": row[2],
             "data": json.loads(row[3]), "created_at": row[4]}
            for row in rows
        ]}
    except (sqlite3.Error, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Не удалось прочитать заявки из базы бота.")


@app.post("/api/internal/data/requests/{user_id}/approve")
async def internal_approve_request(user_id: str, request: Request):
    require_bot_data_secret(request)
    payload = await request.json()
    actor_id = str(payload.get("actor_id", "")).strip()
    actor_name = str(payload.get("actor_name", "Модератор")).strip()[:80]
    if not user_id.isdigit() or not actor_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректные данные одобрения заявки.")
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена.")
    try:
        with sqlite3.connect(path, timeout=10) as db:
            row = db.execute(
                "SELECT request_type, message_id, data FROM pending_requests WHERE CAST(user_id AS TEXT) = ? AND request_type = 'join'",
                (str(user_id),)
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Заявка не найдена в базе бота. Обнови список заявок: возможно, она уже обработана или была отправлена с другого Discord ID.")
        request_type, message_id, raw_data = row
        app_data = json.loads(raw_data)
        nick = str(app_data.get("nick", "")).strip()
        position = str(app_data.get("position", "")).strip()
        if not nick or not position or not message_id:
            raise HTTPException(status_code=409, detail="В заявке отсутствуют ник, должность или ID сообщения.")
        member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{user_id}")
        target_user = member.get("user", {})
        target_name = member.get("nick") or target_user.get("global_name") or target_user.get("username") or user_id
        roles = {str(x) for x in member.get("roles", [])}
        new_nick = f"{nick} | {position}"[:32]
        await discord_request("PATCH", f"/guilds/{GUILD_ID}/members/{user_id}", payload={"nick": new_nick})
        roles.update({
            "1546125522675962027",  # Команда медиа
            "1546125519240564797",  # 🔮» Media
            "1567181453479903405",  # Media » уровень доступа
        })
        roles.discard("1567152429093363782")  # Снять ожидание верификации
        await discord_request("PATCH", f"/guilds/{GUILD_ID}/members/{user_id}", payload={"roles": sorted(roles)})
        channel_payload = {
            "name": nick.lower().replace(" ", "-")[:90],
            "type": 0,
            "parent_id": "1551950227865608292",
            "permission_overwrites": [
                {"id": GUILD_ID, "type": 0, "deny": "1024"},
                {"id": user_id, "type": 1, "allow": "68608"},
                {"id": actor_id, "type": 1, "allow": "68608"},
            ],
        }
        channel = await discord_request("POST", f"/guilds/{GUILD_ID}/channels", payload=channel_payload)
        channel_id = str(channel["id"])
        with sqlite3.connect(path, timeout=10) as db:
            db.execute("INSERT INTO users (user_id, balance, warns, personal_channel_id) VALUES (?, 0, 0, ?) ON CONFLICT(user_id) DO UPDATE SET personal_channel_id = excluded.personal_channel_id", (int(user_id), int(channel_id)))
            db.execute("DELETE FROM pending_requests WHERE request_type = 'join' AND user_id = ?", (int(user_id),))
            db.commit()
        await discord_request("PUT", f"/channels/1551952140929601576/messages/{message_id}/reactions/%E2%9C%85/@me")
        accepted = {
            "embeds": [{
                "title": "✅ ЗАЯВКА ОДОБРЕНА",
                "description": f"<@{user_id}> успешно принят в команду **WhiteGrief Media**!",
                "color": 65280,
                "fields": [
                    {"name": "🎮 Игровой ник", "value": nick, "inline": True},
                    {"name": "🛡️ Должность", "value": position, "inline": True},
                    {"name": "📁 Личный канал", "value": f"<#{channel_id}>", "inline": False},
                    {"name": "🚀 Следующий шаг", "value": "Загляни в личный канал, ознакомься с инструкциями и приступай к работе!", "inline": False},
                    {"name": "Одобрил", "value": f"{actor_name} (<@{actor_id}>)", "inline": False},
                ],
                "footer": {"text": f"WHITEGRIEF MEDIA • Принял: {actor_name}"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
            "allowed_mentions": {"parse": [], "users": []},
        }
        await discord_request("POST", f"/channels/1551952140929601576/messages", payload=accepted)
        welcome = {
            "content": f"Привет, <@{user_id}>! Ты попал в команду Медиа.",
            "embeds": [{
                "title": "🎬 WHITEGRIEF MEDIA",
                "description": (
                    f"**Добро пожаловать в команду Медиа, <@{user_id}>!**\n"
                    "Рады видеть тебя среди нас. Здесь собрана важная информация о работе, баллах и покупках."
                ),
                "color": 0x9770D2,
                "fields": [
                    {"name": "🎥 ТВОЯ РАБОТА", "value": "• Оставляй еженедельную норму.\n• Публикуй видеоролики, чтобы получать баллы.\n• Следи за активностью и не пропускай отчётную неделю.", "inline": False},
                    {"name": "💎 ПОЛЕЗНЫЕ КОМАНДЫ", "value": "**/balance** — проверить баланс.\n**/shop** — посмотреть магазин.\n**/kit** — приобрести наборы.\n**/донат** — приобрести донат-привилегии.\n**/case** — приобрести кейсы.\n**/услуга** — приобрести услуги.", "inline": False},
                    {"name": "📊 1. НЕДЕЛЬНАЯ НОРМА", "value": "**1.** Твой никнейм: `(твой игровой никнейм)`\n**2.** Ссылки на ролики, которые ты сделал: `(ссылки)`", "inline": False},
                    {"name": "💰 2. ПОЛУЧЕНИЕ БАЛЛОВ", "value": "**1.** Твой никнейм: `(твой ник в игре)`\n**2.** Сколько хочешь получить баллов: `(количество)`\n**3.** Ссылка на ролик: `(ссылка)`", "inline": False},
                    {"name": "🛒 3. ПОКУПКА ЗА БАЛЛЫ", "value": "**1.** Твой никнейм: `(твой ник в игре)`\n**2.** Что хочешь купить: `(название товара)`", "inline": False},
                    {"name": "⭐ НЕСКОЛЬКО ВАЖНЫХ СОВЕТОВ", "value": "• Проверяй ссылки перед отправкой.\n• Указывай точное количество баллов.\n• Перед покупкой проверяй баланс.\n• Сохраняй ссылки на опубликованные ролики.", "inline": False},
                    {"name": "🔥 СНИМАЙ • ПУБЛИКУЙ • ЗАРАБАТЫВАЙ", "value": "**Твои ролики — твой вклад в развитие WhiteGrief Media!**", "inline": False},
                ],
                "footer": {"text": "WHITEGRIEF MEDIA • Удачной работы!"},
            }],
            "allowed_mentions": {"parse": [], "users": [user_id]},
        }
        await discord_request("POST", f"/channels/{channel_id}/messages", payload=welcome)
        return {"ok": True, "user_id": user_id, "username": target_name, "actor_name": actor_name}
    except HTTPException:
        raise
    except (sqlite3.Error, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось обработать заявку: {exc}")

@app.post("/api/internal/data/requests/{user_id}/reject")
async def internal_reject_request(user_id: str, request: Request):
    require_bot_data_secret(request)
    payload = await request.json()
    actor_id = str(payload.get("actor_id", "")).strip()
    actor_name = str(payload.get("actor_name", "Модератор")).strip()[:80]
    if not user_id.isdigit() or not actor_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректные данные отклонения заявки.")
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена.")
    try:
        with sqlite3.connect(path, timeout=10) as db:
            row = db.execute(
                "SELECT message_id, data FROM pending_requests WHERE CAST(user_id AS TEXT) = ? AND request_type = 'join'",
                (str(user_id),)
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ожидающая заявка не найдена.")
        message_id, raw_data = row
        app_data = json.loads(raw_data)
        member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{user_id}")
        roles = {str(role_id) for role_id in member.get("roles", [])}
        pending_role_id = "1567152429093363782"
        had_pending_role = pending_role_id in roles
        roles.discard(pending_role_id)
        if had_pending_role:
            await discord_request("PATCH", f"/guilds/{GUILD_ID}/members/{user_id}", payload={"roles": sorted(roles)})
        with sqlite3.connect(path, timeout=10) as db:
            db.execute("DELETE FROM pending_requests WHERE request_type = 'join' AND user_id = ?", (int(user_id),))
            db.commit()
        if message_id:
            rejected = {
                "embeds": [{
                    "title": "❌ ЗАЯВКА ОТКЛОНЕНА",
                    "description": f"<@{user_id}> — заявка отклонена. Роль ожидания верификации снята.",
                    "color": 14495300,
                    "fields": [
                        {"name": "Игровой ник", "value": str(app_data.get("nick", "Не указан"))[:100], "inline": True},
                        {"name": "Должность", "value": str(app_data.get("position", "Не указана"))[:100], "inline": True},
                        {"name": "Отклонил", "value": f"{actor_name} (<@{actor_id}>)", "inline": False},
                    ],
                    "footer": {"text": "WHITEGRIEF MEDIA • Заявки на вступление"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }],
                "allowed_mentions": {"parse": [], "users": []},
            }
            try:
                await discord_request("PATCH", f"/channels/1551952140929601576/messages/{message_id}", payload=rejected)
            except HTTPException:
                pass
        dm_sent = False
        try:
            dm_channel = await discord_request(
                "POST", "/users/@me/channels",
                payload={"recipient_id": user_id},
            )
            dm_channel_id = str(dm_channel["id"])
            dm_message = {
                "embeds": [{
                    "title": "❌ Заявка в WhiteGrief Media отклонена",
                    "description": (
                        "К сожалению, по итогам рассмотрения твоя заявка **не была одобрена**.\n\n"
                        "Спасибо за интерес к команде **WhiteGrief Media** и за потраченное время. "
                        "Не расстраивайся: это не повод останавливаться. "
                        "Если хочешь узнать подробности решения или получить рекомендации, "
                        "можешь обратиться к администрации проекта.\n\n"
                        "Желаем удачи!"
                    ),
                    "color": 14495300,
                    "footer": {"text": "WHITEGRIEF MEDIA • Уведомление по заявке"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }]
            }
            await discord_request("POST", f"/channels/{dm_channel_id}/messages", payload=dm_message)
            dm_sent = True
        except (HTTPException, KeyError, TypeError):
            # Личные сообщения могут быть закрыты — это не должно отменять отклонение заявки.
            pass
        return {"ok": True, "user_id": user_id, "role_removed": had_pending_role, "kicked": False, "dm_sent": dm_sent}
    except HTTPException:
        raise
    except (sqlite3.Error, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось отклонить заявку: {exc}")

@app.get("/api/internal/data/balance/{user_id}")
async def internal_data_balance(user_id: str, request: Request):
    require_bot_data_secret(request)
    if not user_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный Discord ID.")
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена на сервере бота.")
    with sqlite3.connect(path, timeout=10) as db:
        row = db.execute("SELECT balance FROM users WHERE user_id = ?", (int(user_id),)).fetchone()
    return {"user_id": user_id, "balance": int(row[0]) if row else 0}


@app.post("/api/internal/data/players/{user_id}/warn")
async def internal_data_change_warns(user_id: str, request: Request):
    require_bot_data_secret(request)
    payload = await request.json()
    delta = int(payload.get("delta", 0))
    reason = str(payload.get("reason", "")).strip()
    actor_id = str(payload.get("actor_id", "")).strip()
    actor_name = str(payload.get("actor_name", "Модератор сайта")).strip()[:80]
    if not user_id.isdigit() or delta not in (-1, 1) or not reason or not actor_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректные данные изменения варна.")
    member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{user_id}")
    role_ids = {str(x) for x in member.get("roles", [])}
    if role_ids & PROTECTED_ROLE_IDS:
        raise HTTPException(status_code=403, detail="Нельзя менять варны участнику с защищённой ролью администрации.")
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена на сервере бота.")
    try:
        with sqlite3.connect(path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT warns FROM users WHERE user_id = ?", (int(user_id),)).fetchone()
            current = int(row[0]) if row else 0
            updated = max(0, min(2, current + delta))
            if updated == current:
                raise HTTPException(status_code=409, detail="Количество варнов уже на этом уровне.")
            new_roles = role_ids - set(WARN_ROLE_IDS.values())
            if updated:
                new_roles.add(WARN_ROLE_IDS[updated])
            await discord_request("PATCH", f"/guilds/{GUILD_ID}/members/{user_id}", payload={"roles": sorted(new_roles)})
            db.execute(
                "INSERT INTO users (user_id, balance, warns, personal_channel_id) VALUES (?, 0, ?, NULL) "
                "ON CONFLICT(user_id) DO UPDATE SET warns = excluded.warns",
                (int(user_id), updated),
            )
            db.commit()
    except HTTPException:
        raise
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Ошибка базы данных бота.")

    target_user = member.get("user", {})
    target_name = member.get("nick") or target_user.get("global_name") or target_user.get("username") or user_id
    action_text = "ВЫДАН" if delta == 1 else "СНЯТ"
    color = 0xE05265 if delta == 1 else 0x55C995
    embed = {
        "title": f"⚠️ Варн {action_text}" if delta == 1 else "✅ Варн снят",
        "color": color,
        "fields": [
            {"name": "Игрок", "value": f"{target_name} (<@{user_id}>)", "inline": False},
            {"name": "Действие выполнил", "value": f"{actor_name} (<@{actor_id}>)", "inline": False},
            {"name": "Количество варнов", "value": f"{current} → {updated}", "inline": True},
            {"name": "Причина", "value": reason[:1000], "inline": False},
            {"name": "Источник", "value": "WhiteGrief Control Panel", "inline": True},
        ],
        "footer": {"text": "WhiteGrief • Журнал модерации"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await discord_request("POST", f"/channels/{AUDIT_LOG_CHANNEL_ID}/messages", payload={"embeds": [embed], "allowed_mentions": {"parse": [], "users": []}})
    except HTTPException:
        print("Не удалось отправить лог изменения варна в Discord.", flush=True)
    return {"ok": True, "user_id": user_id, "warns": updated, "reason": reason, "actor_name": actor_name}


# ================== TIKTOK OAUTH + BOT-SIDE TOKEN STORAGE ==================
@app.get("/tiktok/login")
async def tiktok_login(state: str = ""):
    if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET or not TIKTOK_REDIRECT_URI:
        raise HTTPException(status_code=503, detail="TikTok OAuth не настроен: проверь TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET и TIKTOK_REDIRECT_URI.")
    if not state or len(state) < 24:
        raise HTTPException(status_code=400, detail="Некорректный код привязки.")
    pending = await bot_api_request("GET", f"/api/internal/tiktok/pending/{state}")
    from urllib.parse import urlencode
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "response_type": "code",
        "scope": TIKTOK_SCOPES,
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": state,
        "disable_auto_auth": "1",
    }
    return RedirectResponse("https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params))

@app.get("/tiktok/callback")
async def tiktok_callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    if error:
        return HTMLResponse("<h2>Подключение TikTok отменено</h2><p>Вернись в Discord и попробуй ещё раз.</p>", status_code=400)
    if not code or not state:
        raise HTTPException(status_code=400, detail="TikTok не вернул код авторизации или state.")
    pending = await bot_api_request("GET", f"/api/internal/tiktok/pending/{state}")
    if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET or not TIKTOK_TOKEN_ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="Не настроены TikTok credentials или ключ шифрования на сайте.")
    async with httpx.AsyncClient(timeout=25) as client:
        token_response = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": TIKTOK_CLIENT_KEY, "client_secret": TIKTOK_CLIENT_SECRET,
                "code": code, "grant_type": "authorization_code", "redirect_uri": TIKTOK_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_data = token_response.json()
        if token_response.status_code != 200 or not token_data.get("access_token"):
            raise HTTPException(status_code=502, detail="TikTok не выдал токен. Проверь Login Kit, redirect URI и разрешения приложения.")
        profile_response = await client.get(
            "https://open.tiktokapis.com/v2/user/info/?fields=open_id,username,bio_description,profile_deep_link",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        profile_data = profile_response.json()
    if profile_response.status_code != 200 or profile_data.get("error", {}).get("code") not in (None, "ok", 0):
        raise HTTPException(status_code=502, detail="Не удалось получить профиль TikTok. Проверь разрешение user.info.profile.")
    profile = profile_data.get("data", {}).get("user", {})
    username = str(profile.get("username") or "").lstrip("@")
    open_id = str(profile.get("open_id") or "")
    expected_username = str(pending.get("expected_username") or "").lstrip("@")
    if not username or not open_id:
        raise HTTPException(status_code=502, detail="TikTok не вернул username или open_id.")
    if username.casefold() != expected_username.casefold():
        raise HTTPException(status_code=400, detail=f"Ты авторизовал @{username}, а в команде указан @{expected_username}. Запусти /привязать_аккаунт заново.")
    now = int(datetime.now(timezone.utc).timestamp())
    token_bundle = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "access_token_expires_at": now + int(token_data.get("expires_in", 86400)),
        "refresh_token_expires_at": now + int(token_data.get("refresh_expires_in", 31536000)),
        "scope": token_data.get("scope", ""),
        "open_id": open_id,
    }
    try:
        from cryptography.fernet import Fernet
        encrypted = Fernet(TIKTOK_TOKEN_ENCRYPTION_KEY.encode("utf-8")).encrypt(json.dumps(token_bundle).encode("utf-8")).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=503, detail="Ключ TIKTOK_TOKEN_ENCRYPTION_KEY некорректен. Используй ключ Fernet и одинаковое значение на обоих хостингах.")
    profile_url = str(profile.get("profile_deep_link") or f"https://www.tiktok.com/@{username}")
    await bot_api_request("POST", "/api/internal/tiktok/complete", payload={
        "state": state, "open_id": open_id, "username": username,
        "profile_url": profile_url, "token_cipher": encrypted,
    })
    return HTMLResponse(
        "<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>WhiteGrief — TikTok</title><body style='background:#101018;color:#f4f1ff;font:16px Arial;display:grid;place-items:center;min-height:90vh'>"
        "<main style='max-width:520px;padding:32px;border:1px solid #38304f;border-radius:18px;background:#191624'>"
        "<h2>✅ TikTok подключён</h2><p>Аккаунт @" + username + " авторизован. Вернись в Discord и нажми кнопку «Проверить», "
        "чтобы подтвердить код в BIO.</p><p>Это окно можно закрыть.</p></main></body></html>"
    )

@app.get("/api/internal/tiktok/pending/{state}")
async def internal_tiktok_pending(state: str, request: Request):
    require_bot_data_secret(request)
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена.")
    with sqlite3.connect(path, timeout=10) as db:
        row = db.execute(
            "SELECT user_id, expected_username, expires_at FROM tiktok_pending WHERE oauth_state = ?", (state,)
        ).fetchone()
    if not row or row[2] <= datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=404, detail="Заявка на привязку не найдена или истекла. Запусти команду заново.")
    return {"user_id": str(row[0]), "expected_username": row[1], "expires_at": row[2]}

@app.post("/api/internal/tiktok/complete")
async def internal_tiktok_complete(request: Request):
    require_bot_data_secret(request)
    payload = await request.json()
    state = str(payload.get("state", ""))
    open_id = str(payload.get("open_id", ""))
    username = str(payload.get("username", "")).lstrip("@")
    profile_url = str(payload.get("profile_url", ""))[:500]
    token_cipher = str(payload.get("token_cipher", ""))
    if not state or not open_id or not username or not token_cipher or not profile_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="TikTok вернул неполные данные профиля.")
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена.")
    try:
        with sqlite3.connect(path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT user_id, expected_username, expires_at FROM tiktok_pending WHERE oauth_state = ?", (state,)
            ).fetchone()
            if not row or row[2] <= datetime.now(timezone.utc).isoformat():
                raise HTTPException(status_code=404, detail="Заявка на привязку истекла. Запусти команду заново.")
            if username.casefold() != str(row[1]).casefold():
                raise HTTPException(status_code=400, detail="Авторизованный TikTok-профиль не совпадает с указанным.")
            owner = db.execute("SELECT user_id FROM tiktok_accounts WHERE open_id = ?", (open_id,)).fetchone()
            if owner and int(owner[0]) != int(row[0]):
                raise HTTPException(status_code=409, detail="Этот TikTok-аккаунт уже привязан к другому Discord-пользователю.")
            db.execute(
                "UPDATE tiktok_pending SET token_cipher=?, open_id=?, username=?, profile_url=? WHERE user_id=? AND oauth_state=?",
                (token_cipher, open_id, username, profile_url, int(row[0]), state)
            )
            db.commit()
    except HTTPException:
        raise
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Не удалось сохранить TikTok-привязку в базе бота.")
    return {"ok": True, "username": username}


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
        # На старте бота обновляем системные роли, но не перезаписываем
        # уровни, вручную назначенные администрацией через Dashboard.
        db.executemany(
            """INSERT INTO access_roles (guild_id, role_id, access_level, role_name)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(guild_id, role_id) DO UPDATE SET
               role_name=excluded.role_name, updated_at=CURRENT_TIMESTAMP""",
            normalized,
        )
        db.commit()
    return {"ok": True, "synced": len(normalized)}
