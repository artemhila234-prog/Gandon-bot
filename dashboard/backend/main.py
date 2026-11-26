import json
import logging
import base64
import binascii
import re
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
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://media.apps.bot-hosting.cloud/auth/callback")
# OAuth, членство, роли и доступ к панели всегда проверяются на первом сервере GastWorld (1492974397001171176).
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "1492974397001171176").strip() or "1492974397001171176"
# Dedicated Ticket Bot access role on the second GastWorld server.
TICKETBOT_SUPPORT_GUILD_ID = "1454858971084230822"
TICKETBOT_SUPPORT_ROLE_ID = "1519379551032184882"
TICKETBOT_ADMIN_GUILD_IDS = tuple(dict.fromkeys((GUILD_ID, TICKETBOT_SUPPORT_GUILD_ID)))
DISCORD_ADMINISTRATOR_PERMISSION = 1 << 3
PLAYER_LIST_ROLE_ID = "1493196315205566545"  # Роль «Команда медиа» для вкладки «Игроки»
AUDIT_LOG_CHANNEL_ID = os.getenv("AUDIT_LOG_CHANNEL_ID", "1573032052666663032")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
BOT_SYNC_SECRET = os.getenv("BOT_SYNC_SECRET", "")
BOT_API_URL = os.getenv("BOT_API_URL", "").rstrip("/")
TICKETBOT_API_URL = os.getenv("TICKETBOT_API_URL", "").rstrip("/")
TICKETBOT_API_KEY = os.getenv("TICKETBOT_API_KEY", "")
ticketbot_log = logging.getLogger("gastworld.ticketbot")
BOT_DATA_API_SECRET = os.getenv("BOT_DATA_API_SECRET", "")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://media.apps.bot-hosting.cloud/tiktok/callback")
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
            palette TEXT NOT NULL DEFAULT '["#8b5cf6","#ec4899","#38bdf8"]',
            compact_mode INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        preference_columns = {row[1] for row in db.execute("PRAGMA table_info(user_preferences)").fetchall()}
        if "palette" not in preference_columns:
            db.execute("""ALTER TABLE user_preferences ADD COLUMN palette TEXT NOT NULL DEFAULT '["#8b5cf6","#ec4899","#38bdf8"]'""")
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
            "SELECT theme, accent, compact_mode, palette FROM user_preferences WHERE user_id = ?",
            (str(user_id),)
        ).fetchone()
    if not row:
        return {"theme": "system", "accent": "purple", "palette": ["#8b5cf6", "#ec4899", "#38bdf8"], "compact_mode": False}
    try:
        palette = json.loads(row[3] or '["#8b5cf6","#ec4899","#38bdf8"]')
    except (TypeError, json.JSONDecodeError):
        palette = ["#8b5cf6", "#ec4899", "#38bdf8"]
    if not isinstance(palette, list) or len(palette) != 3:
        palette = ["#8b5cf6", "#ec4899", "#38bdf8"]
    return {"theme": row[0], "accent": row[1], "palette": palette, "compact_mode": bool(row[2])}


def get_role_access_map() -> dict[str, str]:
    import sqlite3
    with sqlite3.connect(PANEL_DB_PATH) as db:
        rows = db.execute(
            "SELECT role_id, access_level FROM access_roles WHERE guild_id = ?",
            (GUILD_ID,)
        ).fetchall()
    return {str(role_id): level for role_id, level in rows}

app = FastAPI(title="GastWorld Control Panel API")
if not SESSION_SECRET:
    # Local-only fallback. Set a long random SESSION_SECRET before deployment.
    SESSION_SECRET = secrets.token_urlsafe(48)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="gastworld_panel_session",
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


async def optional_guild_member_and_roles(guild_id: str, user_id: str):
    """Returns (member, roles); a 404 means the user/bot is not present in that guild."""
    try:
        member, roles = await asyncio.gather(
            discord_get(f"/guilds/{guild_id}/members/{user_id}", BOT_TOKEN, bot=True),
            discord_get(f"/guilds/{guild_id}/roles", BOT_TOKEN, bot=True),
        )
        return member, roles
    except HTTPException as exc:
        if "404" in str(exc.detail):
            return None, None
        raise


def member_has_discord_administrator(member: dict[str, Any] | None, roles: list[dict[str, Any]] | None) -> bool:
    if not member:
        return False
    assigned = {str(role_id) for role_id in member.get("roles", [])}
    for role in roles or []:
        if str(role.get("id")) not in assigned:
            continue
        try:
            permissions = int(str(role.get("permissions") or "0"))
        except (TypeError, ValueError):
            permissions = 0
        if permissions & DISCORD_ADMINISTRATOR_PERMISSION:
            return True
    return False


async def refresh_session_user(request: Request) -> dict[str, Any] | None:
    """Re-check access on both GastWorld guilds on each request."""
    user = await current_user(request)
    if not user:
        return None
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Не настроен DISCORD_BOT_TOKEN для проверки доступа.")

    user_id = str(user.get("id", ""))
    primary_member, primary_roles = await optional_guild_member_and_roles(GUILD_ID, user_id)
    support_member, support_roles = await optional_guild_member_and_roles(TICKETBOT_SUPPORT_GUILD_ID, user_id)

    role_ids = [str(role_id) for role_id in (primary_member or {}).get("roles", [])]
    access = calculate_access(role_ids) if primary_member else "none"
    has_discord_admin = (
        member_has_discord_administrator(primary_member, primary_roles)
        or member_has_discord_administrator(support_member, support_roles)
    )
    if ACCESS_RANK.get(access, 0) >= ACCESS_RANK["adm"] or has_discord_admin:
        ticketbot_access = "admin"
    elif TICKETBOT_SUPPORT_ROLE_ID in {
        str(role_id) for role_id in (support_member or {}).get("roles", [])
    }:
        ticketbot_access = "support"
    else:
        ticketbot_access = "none"

    if access == "none" and ticketbot_access == "none":
        request.session.clear()
        return None

    role_names = {
        str(role["id"]): str(role.get("name") or "Без названия")
        for role in (primary_roles or [])
    }
    role_names.update({
        str(role["id"]): str(role.get("name") or "Без названия")
        for role in (support_roles or [])
    })
    visible_role_ids = list(dict.fromkeys(
        role_ids + [str(role_id) for role_id in (support_member or {}).get("roles", [])]
    ))
    user.update({
        "role_ids": role_ids,
        "role_names": [role_names.get(role_id, "Неизвестная роль") for role_id in visible_role_ids],
        "is_media": access != "none",
        "access_level": access,
        "ticketbot_access": ticketbot_access,
        "ticketbot_only": access == "none" and ticketbot_access != "none",
    })
    request.session["user"] = user
    return user


async def require_user(request: Request) -> dict[str, Any]:
    user = await refresh_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Нет доступа. Войди через Discord и проверь роль GastWorld.")
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

@app.get("/gastworld-logo.svg")
async def gastworld_logo():
    return FileResponse(os.path.join(BASE_DIR, "gastworld-logo.svg"), media_type="image/svg+xml")


@app.get("/style.css")
async def stylesheet():
    return FileResponse(os.path.join(BASE_DIR, "style.css"), media_type="text/css")


@app.get("/app.js")
async def frontend_script():
    return FileResponse(os.path.join(BASE_DIR, "app.js"), media_type="application/javascript")


@app.get("/ticketbot.js")
async def ticketbot_frontend_script():
    return FileResponse(os.path.join(BASE_DIR, "ticketbot.js"), media_type="application/javascript")

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

    # The panel normally uses the first guild, but the Ticket Bot support role
    # on the second guild is also a valid, restricted sign-in path.
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Не настроен DISCORD_BOT_TOKEN для проверки сервера.")

    request.session.clear()
    request.session["user"] = {
        "id": str(profile["id"]),
        "username": profile.get("global_name") or profile.get("username", "Discord user"),
        "discord_username": profile.get("username", ""),
        "avatar": profile.get("avatar"),
        "guild_id": GUILD_ID,
    }
    verified_user = await refresh_session_user(request)
    if not verified_user:
        raise HTTPException(
            status_code=403,
            detail="Нет роли доступа GastWorld. Для Ticket Bot нужна роль поддержки на втором сервере.",
        )
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


@app.get("/api/creator-profile")
async def api_creator_profile(request: Request):
    await require_user(request)
    try:
        return await get_dm_controller("creator_profile")("1479848906106863796")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)[:250])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить профиль создателя: {str(error)[:250]}")


@app.get("/api/allowed-guilds")
async def api_allowed_guilds(request: Request):
    """Список серверов, для которых Full разрешил выполнять команды GastWorld."""
    await require_access(request, "full")
    try:
        return await get_dm_controller("allowed_guilds_list")()
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить список разрешённых серверов: {str(error)[:250]}")


@app.post("/api/allowed-guilds")
async def api_allowed_guilds_add(request: Request):
    actor = await require_access(request, "full")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректные данные запроса.")
    guild_id = str(payload.get("guild_id") or "").strip() if isinstance(payload, dict) else ""
    if not guild_id.isdigit() or not 17 <= len(guild_id) <= 20:
        raise HTTPException(status_code=400, detail="Укажи Discord Server ID длиной 17–20 цифр.")
    try:
        return await get_dm_controller("allowed_guilds_add")(guild_id, str(actor.get("id", "")))
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:250])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:250])
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось разрешить сервер: {str(error)[:250]}")


@app.delete("/api/allowed-guilds/{guild_id}")
async def api_allowed_guilds_remove(guild_id: str, request: Request):
    await require_access(request, "full")
    if not guild_id.isdigit() or not 17 <= len(guild_id) <= 20:
        raise HTTPException(status_code=400, detail="Некорректный Discord Server ID.")
    try:
        return await get_dm_controller("allowed_guilds_remove")(guild_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:250])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:250])
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось отключить сервер: {str(error)[:250]}")


@app.get("/api/allowed-guilds/{guild_id}/commands")
async def api_allowed_guild_commands(guild_id: str, request: Request):
    await require_access(request, "full")
    if not guild_id.isdigit() or not 17 <= len(guild_id) <= 20:
        raise HTTPException(status_code=400, detail="Некорректный Discord Server ID.")
    try:
        return await get_dm_controller("allowed_guild_commands")(guild_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:250])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:250])
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить команды сервера: {str(error)[:250]}")


@app.post("/api/allowed-guilds/{guild_id}/commands")
async def api_allowed_guild_command_update(guild_id: str, request: Request):
    actor = await require_access(request, "full")
    if not guild_id.isdigit() or not 17 <= len(guild_id) <= 20:
        raise HTTPException(status_code=400, detail="Некорректный Discord Server ID.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректные данные запроса.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ожидается объект с настройками команды.")

    command_type = str(payload.get("command_type") or "").strip().lower()
    command_name = str(payload.get("command_name") or "").strip()
    disabled = payload.get("disabled")
    if command_type not in {"slash", "prefix"}:
        raise HTTPException(status_code=400, detail="Тип команды должен быть slash или prefix.")
    if not command_name or len(command_name) > 100:
        raise HTTPException(status_code=400, detail="Укажи корректное имя команды.")
    if not isinstance(disabled, bool):
        raise HTTPException(status_code=400, detail="Параметр disabled должен быть true или false.")

    try:
        return await get_dm_controller("allowed_guild_command_update")(
            guild_id, command_type, command_name, disabled, str(actor.get("id", ""))
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:250])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:250])
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось изменить доступ команды: {str(error)[:250]}")



async def ticketbot_api_request(method: str, path: str, *, payload: Any = None, params: dict[str, Any] | None = None):
    if not TICKETBOT_API_URL or not TICKETBOT_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Ticket Bot API не подключён. Настрой TICKETBOT_API_URL и TICKETBOT_API_KEY на backend GastWorld."
        )
    url = f"{TICKETBOT_API_URL}/api/v1/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=8.0)) as client:
            response = await client.request(
                method.upper(), url, json=payload, params=params,
                headers={"X-TicketBot-Key": TICKETBOT_API_KEY, "Accept": "application/json"},
            )
    except httpx.RequestError as error:
        raise HTTPException(status_code=503, detail=f"Ticket Bot сейчас недоступен: {type(error).__name__}.")
    if response.status_code == 401:
        raise HTTPException(status_code=502, detail="Ticket Bot отклонил внутренний ключ API. Проверь ключи на обоих хостингах.")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Объект Ticket Bot не найден.")
    if response.status_code == 400:
        try: detail = response.json().get("detail", "Некорректные данные.")
        except Exception: detail = "Некорректные данные."
        raise HTTPException(status_code=400, detail=str(detail)[:350])
    if response.status_code == 403:
        raise HTTPException(status_code=403, detail="Ticket Bot отклонил действие по правам доступа.")
    if response.status_code >= 500:
        ticketbot_log.error(
            "Ticket Bot upstream failure: %s %s returned HTTP %s",
            method.upper(), f"/api/v1/{path.lstrip('/')}", response.status_code,
        )
        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = str(body.get("detail") or "").strip()
        except (ValueError, TypeError):
            pass
        if detail and detail.lower() not in {"internal server error", "internal error"}:
            message = f"Ticket Bot API: {detail[:300]}"
        else:
            message = (
                f"Ticket Bot API вернул HTTP {response.status_code} "
                f"на запрос {method.upper()} /api/v1/{path.lstrip('/')}. "
                "Проверь консоль Ticket Bot — там будет traceback."
            )
        raise HTTPException(status_code=502, detail=message)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Ticket Bot API request failed.")
    try:
        return response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Ticket Bot вернул некорректный JSON.")


def ticketbot_actor_payload(request: Request, payload: Any) -> dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {}
    user = request.session.get("user") or {}
    data["actor_id"] = str(user.get("id", ""))
    return data


async def require_ticketbot_access(
    request: Request, minimum: str = "support", guild_id: str | None = None
) -> dict[str, Any]:
    user = await require_user(request)
    current = str(user.get("ticketbot_access") or "none")
    if minimum == "admin" and current != "admin":
        raise HTTPException(status_code=403, detail="Для этого раздела нужны права ADM Ticket Bot.")
    if minimum == "support" and current not in {"support", "admin"}:
        raise HTTPException(status_code=403, detail="Нет роли поддержки Ticket Bot.")
    if guild_id and current == "support" and str(guild_id) != TICKETBOT_SUPPORT_GUILD_ID:
        raise HTTPException(status_code=403, detail="Роль поддержки действует только на втором сервере GastWorld.")
    return user


async def require_ticketbot_admin(request: Request):
    return await require_ticketbot_access(request, "admin")


@app.get("/api/ticketbot/profile")
async def api_ticketbot_profile(request: Request):
    await require_ticketbot_admin(request)
    return await ticketbot_api_request("GET", "profile")


@app.patch("/api/ticketbot/profile")
async def api_ticketbot_profile_update(request: Request):
    await require_ticketbot_admin(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "PATCH", "profile", payload=ticketbot_actor_payload(request, payload)
    )


@app.get("/api/ticketbot/guilds")
async def api_ticketbot_guilds(request: Request):
    user = await require_ticketbot_access(request, "support")
    data = await ticketbot_api_request("GET", "guilds")
    if user.get("ticketbot_access") == "support":
        data["guilds"] = [
            guild for guild in data.get("guilds", [])
            if str(guild.get("id") or guild.get("guild_id") or "") == TICKETBOT_SUPPORT_GUILD_ID
        ]
    return data


@app.get("/api/ticketbot/guilds/{guild_id}/overview")
async def api_ticketbot_overview(guild_id: str, request: Request):
    user = await require_ticketbot_access(request, "support", guild_id)
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный Discord Server ID.")
    data = await ticketbot_api_request("GET", f"guilds/{guild_id}/overview")
    if user.get("ticketbot_access") == "support":
        settings = data.get("settings") or {}
        return {
            "guild": data.get("guild") or {},
            "settings": {
                "language": settings.get("language", "en"),
                "timezone": settings.get("timezone", "UTC"),
            },
            "tickets": data.get("tickets") or {},
            "panels_count": len(data.get("panels") or []),
            "staff_count": len(data.get("staff") or []),
        }
    return data


@app.get("/api/ticketbot/guilds/{guild_id}/channels")
async def api_ticketbot_channels(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный Discord Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/channels")


@app.get("/api/ticketbot/guilds/{guild_id}/roles")
async def api_ticketbot_roles(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный Discord Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/roles")


@app.patch("/api/ticketbot/guilds/{guild_id}/settings")
async def api_ticketbot_settings(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный Discord Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "PATCH", f"guilds/{guild_id}/settings", payload=ticketbot_actor_payload(request, payload)
    )


@app.get("/api/ticketbot/guilds/{guild_id}/panels")
async def api_ticketbot_panels(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/panels")


@app.post("/api/ticketbot/guilds/{guild_id}/panels")
async def api_ticketbot_panel_save(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/panels", payload=ticketbot_actor_payload(request, payload)
    )


@app.post("/api/ticketbot/guilds/{guild_id}/panels/{panel_id}/publish")
async def api_ticketbot_panel_publish(guild_id: str, panel_id: int, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/panels/{panel_id}/publish",
        payload=ticketbot_actor_payload(request, {}),
    )


@app.delete("/api/ticketbot/guilds/{guild_id}/panels/{panel_id}")
async def api_ticketbot_panel_delete(guild_id: str, panel_id: int, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request(
        "DELETE", f"guilds/{guild_id}/panels/{panel_id}",
        payload=ticketbot_actor_payload(request, {}),
    )


@app.get("/api/ticketbot/guilds/{guild_id}/tickets")
async def api_ticketbot_tickets(guild_id: str, request: Request, status: str = "all",
                              limit: int = 100, before_id: int | None = None):
    await require_ticketbot_access(request, "support", guild_id)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    params = {"status": status, "limit": max(1, min(limit, 200))}
    if before_id is not None:
        params["before_id"] = max(1, int(before_id))
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/tickets", params=params)


@app.get("/api/ticketbot/guilds/{guild_id}/tickets/{ticket_id}")
async def api_ticketbot_ticket(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_access(request, "support", guild_id)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/tickets/{ticket_id}")


@app.post("/api/ticketbot/guilds/{guild_id}/tickets/{ticket_id}/reply")
async def api_ticketbot_ticket_reply(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_access(request, "support", guild_id)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/tickets/{ticket_id}/reply",
        payload=ticketbot_actor_payload(request, payload),
    )


@app.post("/api/ticketbot/guilds/{guild_id}/tickets/{ticket_id}/claim")
async def api_ticketbot_ticket_claim(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_access(request, "support", guild_id)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/tickets/{ticket_id}/claim",
        payload=ticketbot_actor_payload(request, {}),
    )


@app.post("/api/ticketbot/guilds/{guild_id}/tickets/{ticket_id}/close")
async def api_ticketbot_ticket_close(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_access(request, "support", guild_id)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: payload = {}
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/tickets/{ticket_id}/close",
        payload=ticketbot_actor_payload(request, payload),
    )


@app.post("/api/ticketbot/guilds/{guild_id}/tickets/{ticket_id}/reopen")
async def api_ticketbot_ticket_reopen(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_access(request, "support", guild_id)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/tickets/{ticket_id}/reopen",
        payload=ticketbot_actor_payload(request, {}),
    )


@app.post("/api/ticketbot/guilds/{guild_id}/tickets/{ticket_id}/members")
async def api_ticketbot_ticket_member(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/tickets/{ticket_id}/members",
        payload=ticketbot_actor_payload(request, payload),
    )


@app.get("/api/ticketbot/guilds/{guild_id}/tickets/{ticket_id}/tags")
async def api_ticketbot_ticket_tags(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/tickets/{ticket_id}/tags")


@app.post("/api/ticketbot/guilds/{guild_id}/tickets/{ticket_id}/tags")
async def api_ticketbot_ticket_tag_update(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/tickets/{ticket_id}/tags",
        payload=ticketbot_actor_payload(request, payload),
    )


@app.get("/api/ticketbot/guilds/{guild_id}/transcript/{ticket_id}")
async def api_ticketbot_transcript(guild_id: str, ticket_id: int, request: Request):
    await require_ticketbot_access(request, "support", guild_id)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    if not TICKETBOT_API_URL or not TICKETBOT_API_KEY:
        raise HTTPException(status_code=503, detail="Ticket Bot API не подключён.")
    url = f"{TICKETBOT_API_URL}/api/v1/guilds/{guild_id}/tickets/{ticket_id}/transcript"
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.get(url, headers={"X-TicketBot-Key": TICKETBOT_API_KEY})
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Ticket Bot сейчас недоступен.")
    if response.status_code == 404: raise HTTPException(status_code=404, detail="Транскрипт не найден.")
    if response.status_code != 200: raise HTTPException(status_code=502, detail="Не удалось получить транскрипт.")
    return HTMLResponse(response.text, headers={"Content-Disposition": f'inline; filename="ticket-{ticket_id}.html"'})


@app.get("/api/ticketbot/guilds/{guild_id}/staff")
async def api_ticketbot_staff(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/staff")


@app.post("/api/ticketbot/guilds/{guild_id}/staff")
async def api_ticketbot_staff_update(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/staff", payload=ticketbot_actor_payload(request, payload)
    )


@app.get("/api/ticketbot/guilds/{guild_id}/schedules")
async def api_ticketbot_schedules(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/schedules")


@app.post("/api/ticketbot/guilds/{guild_id}/schedules")
async def api_ticketbot_schedule_save(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/schedules", payload=ticketbot_actor_payload(request, payload)
    )


@app.delete("/api/ticketbot/guilds/{guild_id}/schedules/{schedule_id}")
async def api_ticketbot_schedule_delete(guild_id: str, schedule_id: int, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request(
        "DELETE", f"guilds/{guild_id}/schedules/{schedule_id}",
        payload=ticketbot_actor_payload(request, {}),
    )


@app.get("/api/ticketbot/guilds/{guild_id}/replies")
async def api_ticketbot_replies(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/replies")


@app.post("/api/ticketbot/guilds/{guild_id}/replies")
async def api_ticketbot_reply_save(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/replies", payload=ticketbot_actor_payload(request, payload)
    )


@app.delete("/api/ticketbot/guilds/{guild_id}/replies/{shortcut}")
async def api_ticketbot_reply_delete(guild_id: str, shortcut: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request(
        "DELETE", f"guilds/{guild_id}/replies/{shortcut}",
        payload=ticketbot_actor_payload(request, {}),
    )


@app.get("/api/ticketbot/guilds/{guild_id}/tags")
async def api_ticketbot_tags(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/tags")


@app.post("/api/ticketbot/guilds/{guild_id}/tags")
async def api_ticketbot_tag_save(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/tags", payload=ticketbot_actor_payload(request, payload)
    )


@app.delete("/api/ticketbot/guilds/{guild_id}/tags/{tag_id}")
async def api_ticketbot_tag_delete(guild_id: str, tag_id: int, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request(
        "DELETE", f"guilds/{guild_id}/tags/{tag_id}",
        payload=ticketbot_actor_payload(request, {}),
    )


@app.get("/api/ticketbot/guilds/{guild_id}/knowledge")
async def api_ticketbot_knowledge(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/knowledge")


@app.post("/api/ticketbot/guilds/{guild_id}/knowledge")
async def api_ticketbot_knowledge_save(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    try: payload = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Некорректный JSON.")
    return await ticketbot_api_request(
        "POST", f"guilds/{guild_id}/knowledge", payload=ticketbot_actor_payload(request, payload)
    )


@app.delete("/api/ticketbot/guilds/{guild_id}/knowledge/{article_id}")
async def api_ticketbot_knowledge_delete(guild_id: str, article_id: int, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request(
        "DELETE", f"guilds/{guild_id}/knowledge/{article_id}",
        payload=ticketbot_actor_payload(request, {}),
    )


@app.get("/api/ticketbot/guilds/{guild_id}/analytics")
async def api_ticketbot_analytics(guild_id: str, request: Request):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/analytics")


@app.get("/api/ticketbot/guilds/{guild_id}/audit")
async def api_ticketbot_audit(guild_id: str, request: Request, limit: int = 100):
    await require_ticketbot_admin(request)
    if not guild_id.isdigit(): raise HTTPException(status_code=400, detail="Некорректный Server ID.")
    return await ticketbot_api_request("GET", f"guilds/{guild_id}/audit", params={"limit": max(1,min(limit,500))})


@app.post("/auth/logout")
async def auth_logout(request: Request):
    request.session.clear()
    return {"ok": True}


WARN_ROLE_IDS = {1: "1546125538198823033", 2: "1546125541571043398", 3: "1546125544888729761"}
PROTECTED_ROLE_IDS = {"1546125455633944598", "1546125498340614195", "1546125488496451686", "1546125469093732372", "1546125465482174484", "1547654044263252038", "1546125472897961984", "1546125480321749053", "1550200782177968178"}

def bot_database_path() -> str:
    return os.getenv("BOT_DB_PATH", os.path.join(os.path.dirname(BASE_DIR), "aaaa", "bot_data.db"))

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
        try:
            error_data = response.json()
        except ValueError:
            error_data = {}
        discord_message = str(error_data.get("message") or response.text or "без описания")[:500]
        discord_code = error_data.get("code")
        code_suffix = f", код {discord_code}" if discord_code is not None else ""
        raise HTTPException(
            status_code=502,
            detail=f"Discord API отклонил запрос ({response.status_code}{code_suffix}) на {method} {path}: {discord_message}",
        )
    return response.json() if response.content else None


@app.get("/api/access/members")
async def api_access_members(request: Request):
    """Полный список участников сервера для вкладки «Доступ» (только Adm/Full)."""
    actor = await require_access(request, "adm")
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
    bot_user = await discord_request("GET", "/users/@me")
    bot_member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{bot_user.get('id')}")
    bot_role_ids = {str(item) for item in bot_member.get("roles", [])}
    bot_top_position = max(
        (int(role.get("position") or 0) for role in roles if str(role.get("id")) in bot_role_ids),
        default=0,
    )
    access_map = get_role_access_map()
    assignable_roles = [
        role for role in role_items
        if role["id"] != GUILD_ID
        and not role["managed"]
        and role["position"] < bot_top_position
        and not (
            access_map.get(role["id"], "none") == "full"
            and actor.get("access_level") != "full"
        )
    ]
    return {
        "members": members,
        "roles": role_items,
        "assignable_roles": assignable_roles,
        "total_members": len(members),
        "total_roles": len(role_items),
        "guild_name": "GastWorld",
        "guild_id": GUILD_ID,
    }


@app.post("/api/access/members/{user_id}/roles")
async def api_access_assign_role(user_id: str, request: Request):
    """Выдать участнику роль Discord из вкладки «Доступ»."""
    actor = await require_access(request, "adm")
    if not user_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный Discord ID участника.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректные данные запроса.")
    role_id = str(payload.get("role_id") or "") if isinstance(payload, dict) else ""
    if not role_id.isdigit() or role_id == GUILD_ID:
        raise HTTPException(status_code=400, detail="Выбери обычную роль сервера.")

    roles = await discord_request("GET", f"/guilds/{GUILD_ID}/roles")
    role = next((item for item in roles if str(item.get("id")) == role_id), None)
    if not role:
        raise HTTPException(status_code=404, detail="Эта роль больше не существует на сервере.")
    if role.get("managed"):
        raise HTTPException(status_code=400, detail="Роли интеграций и ботов нельзя выдавать вручную.")

    role_access = get_role_access_map().get(role_id, "none")
    if role_access == "full" and actor.get("access_level") != "full":
        raise HTTPException(status_code=403, detail="Только пользователь с уровнем Full может выдавать роль, открывающую доступ Full.")

    bot_user = await discord_request("GET", "/users/@me")
    bot_member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{bot_user.get('id')}")
    bot_role_ids = {str(item) for item in bot_member.get("roles", [])}
    bot_top_position = max(
        (int(item.get("position") or 0) for item in roles if str(item.get("id")) in bot_role_ids),
        default=0,
    )
    if int(role.get("position") or 0) >= bot_top_position:
        raise HTTPException(status_code=403, detail="Эта роль находится выше или на одном уровне с ролью бота. Подними роль бота в настройках Discord.")

    member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{user_id}")
    member_role_ids = {str(item) for item in member.get("roles", [])}
    if role_id in member_role_ids:
        return {
            "ok": True,
            "already_had_role": True,
            "message": "У участника уже есть эта роль.",
            "role": {"id": role_id, "name": role.get("name"), "color": int(role.get("color") or 0)},
        }

    await discord_request("PUT", f"/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}")
    return {
        "ok": True,
        "already_had_role": False,
        "message": f"Роль «{role.get('name') or 'Без названия'}» выдана участнику.",
        "role": {"id": role_id, "name": role.get("name"), "color": int(role.get("color") or 0)},
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
        "guild_name": "GastWorld" if is_admin else None,
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
    palette = payload.get("palette", ["#8b5cf6", "#ec4899", "#38bdf8"])
    compact_mode = payload.get("compact_mode", False)
    if not isinstance(theme, str) or theme not in {"system", "dark", "light"}:
        raise HTTPException(status_code=400, detail="Неизвестная тема оформления.")
    if not isinstance(accent, str) or accent not in {"purple", "blue", "green", "red"}:
        raise HTTPException(status_code=400, detail="Неизвестный цвет акцента.")
    if (not isinstance(palette, list) or len(palette) != 3
            or any(not isinstance(color, str) or len(color) != 7 or color[0] != "#"
                   or any(char not in "0123456789abcdefABCDEF" for char in color[1:]) for color in palette)):
        raise HTTPException(status_code=400, detail="Палитра должна содержать ровно три HEX-цвета.")
    if not isinstance(compact_mode, bool):
        raise HTTPException(status_code=400, detail="compact_mode должен быть true или false.")
    import sqlite3
    with sqlite3.connect(PANEL_DB_PATH) as db:
        db.execute(
            """INSERT INTO user_preferences (user_id, theme, accent, palette, compact_mode, updated_at)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id) DO UPDATE SET
               theme=excluded.theme, accent=excluded.accent, palette=excluded.palette,
               compact_mode=excluded.compact_mode, updated_at=CURRENT_TIMESTAMP""",
            (str(user["id"]), theme, accent, json.dumps(palette), int(compact_mode)),
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
        async with httpx.AsyncClient(timeout=60) as client:
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


@app.get("/api/tickets")
async def api_tickets(request: Request):
    await require_access(request, "adm")
    return await bot_api_request("GET", "/api/internal/tickets")


@app.get("/api/tickets/acceptance")
async def api_ticket_acceptance(request: Request):
    await require_access(request, "adm")
    return await bot_api_request("GET", "/api/internal/tickets/acceptance")


@app.post("/api/tickets/acceptance")
async def api_set_ticket_acceptance(request: Request):
    await require_access(request, "adm")
    payload = await request.json()
    if not isinstance(payload.get("accepting"), bool):
        raise HTTPException(status_code=400, detail="Ожидается логическое значение accepting.")
    return await bot_api_request("POST", "/api/internal/tickets/acceptance", payload={"accepting": payload["accepting"]})


@app.post("/api/tickets/{channel_id}/status")
async def api_ticket_status(channel_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID тикета.")
    payload = await request.json()
    status = str(payload.get("status", "")).strip().lower()
    if status not in {"open", "closed", "resolved"}:
        raise HTTPException(status_code=400, detail="Неизвестный статус тикета.")
    return await bot_api_request("POST", f"/api/internal/tickets/{channel_id}/status", payload={
        "status": status, "actor": str(actor.get("username") or actor.get("discord_username") or "Adm")
    })


MESSAGE_GUILDS = {
    "1492974397001171176": "Первый сервер · GastWorld MEDIA",
    "1454858971084230822": "Второй сервер · GastWorld",
}


@app.get("/api/messages/channels")
async def api_message_channels(request: Request, guild_id: str = "1492974397001171176"):
    user = await require_access(request, "adm")
    guild_id = str(guild_id).strip()
    if guild_id not in MESSAGE_GUILDS:
        raise HTTPException(status_code=400, detail="Выбран неизвестный Discord-сервер.")
    channels = await discord_request("GET", f"/guilds/{guild_id}/channels")
    bot_profile = {}
    try:
        bot_user = await discord_request("GET", "/users/@me")
        bot_id = str(bot_user.get("id", ""))
        bot_avatar = bot_user.get("avatar")
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{bot_id}/{bot_avatar}.png?size=128"
            if bot_id and bot_avatar else
            f"https://cdn.discordapp.com/embed/avatars/{(int(bot_id) >> 22) % 6}.png"
            if bot_id.isdigit() else ""
        )
        bot_profile = {"username": bot_user.get("global_name") or bot_user.get("username") or "GastWorld", "avatar_url": avatar_url}
    except Exception:
        pass
    items = []
    for channel in channels if isinstance(channels, list) else []:
        if channel.get("type") in (0, 5) and str(channel.get("guild_id", guild_id)) == guild_id:
            items.append({
                "id": str(channel.get("id", "")),
                "name": str(channel.get("name", "")),
                "parent_name": str(channel.get("parent_name") or ""),
            })
    items.sort(key=lambda item: (item["parent_name"].casefold(), item["name"].casefold()))
    return {
        "guild_id": guild_id,
        "guild_name": MESSAGE_GUILDS[guild_id],
        "servers": [{"id": key, "name": value} for key, value in MESSAGE_GUILDS.items()],
        "channels": items,
        "bot_profile": bot_profile,
        "sender": {"username": user.get("username", "Администратор"), "discord_username": user.get("discord_username", "")},
    }


@app.get("/api/messages/history")
async def api_message_history(request: Request, channel_id: str):
    await require_access(request, "adm")
    channel_id = str(channel_id).strip()
    if not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID канала.")
    channel = await discord_request("GET", f"/channels/{channel_id}")
    guild_id = str(channel.get("guild_id", ""))
    if guild_id not in MESSAGE_GUILDS:
        raise HTTPException(status_code=403, detail="История доступна только для двух серверов GastWorld.")
    raw_messages = await discord_request("GET", f"/channels/{channel_id}/messages?limit=50")
    channel_names = {}
    try:
        guild_channels = await discord_request("GET", f"/guilds/{guild_id}/channels")
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
    attribution = f"-# Отправитель: {sender_mention} · GastWorld Control Panel"
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
    if str(channel.get("guild_id", "")) not in MESSAGE_GUILDS or channel.get("type") not in (0, 5):
        raise HTTPException(status_code=400, detail="Можно отправлять только в текстовые каналы двух серверов GastWorld.")

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


# ================== DISCORD SERVER / CHANNEL CLIENT ==================
@app.get("/api/discord/bot-profile")
async def api_discord_bot_profile(request: Request):
    await require_access(request, "adm")
    try:
        return await get_dm_controller("bot_profile")()
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить профиль бота: {str(error)[:300]}")


@app.patch("/api/discord/bot-profile")
async def api_discord_bot_profile_update(request: Request):
    await require_access(request, "adm")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректные данные профиля.")
    try:
        return await get_dm_controller("bot_profile_update")(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось изменить профиль бота: {str(error)[:350]}")


@app.get("/api/discord/guilds")
async def api_discord_guilds(request: Request):
    await require_access(request, "adm")
    try:
        return await get_dm_controller("discord_guilds")()
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить серверы Discord: {str(error)[:300]}")

@app.get("/api/discord/guilds/{guild_id}/settings")
async def api_discord_guild_settings(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        return await get_dm_controller("discord_settings")(guild_id, str(actor.get("id", "")))
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить настройки сервера: {str(error)[:300]}")


@app.patch("/api/discord/guilds/{guild_id}/settings")
async def api_discord_guild_settings_update(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректные настройки сервера.")
    try:
        return await get_dm_controller("discord_settings_update")(
            guild_id, str(actor.get("id", "")), payload
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось сохранить настройки сервера: {str(error)[:300]}")


@app.get("/api/discord/guilds/{guild_id}/roles")
async def api_discord_guild_roles(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        return await get_dm_controller("discord_roles")(guild_id, str(actor.get("id", "")))
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить роли: {str(error)[:300]}")


@app.post("/api/discord/guilds/{guild_id}/roles")
async def api_discord_guild_role_create(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        payload = await request.json()
        return await get_dm_controller("discord_role_create")(guild_id, str(actor.get("id", "")), payload)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось создать роль: {str(error)[:300]}")


@app.patch("/api/discord/guilds/{guild_id}/roles/{role_id}")
async def api_discord_guild_role_update(guild_id: str, role_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not role_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или роли.")
    try:
        payload = await request.json()
        return await get_dm_controller("discord_role_update")(guild_id, str(actor.get("id", "")), role_id, payload)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось сохранить роль: {str(error)[:300]}")


@app.delete("/api/discord/guilds/{guild_id}/roles/{role_id}")
async def api_discord_guild_role_delete(guild_id: str, role_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not role_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или роли.")
    try:
        return await get_dm_controller("discord_role_delete")(guild_id, str(actor.get("id", "")), role_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось удалить роль: {str(error)[:300]}")


@app.get("/api/discord/guilds/{guild_id}/members")
async def api_discord_guild_members(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    after = str(request.query_params.get("after", "0") or "0")
    try:
        limit = int(request.query_params.get("limit", "500"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Некорректный размер страницы участников.")
    if not after.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный курсор списка участников.")
    limit = max(1, min(limit, 1000))
    try:
        return await get_dm_controller("discord_members")(
            guild_id, str(actor.get("id", "")), after, limit
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить участников сервера: {str(error)[:300]}")

@app.get("/api/discord/guilds/{guild_id}/presence")
async def api_discord_guild_presence(guild_id: str, request: Request):
    await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        return await get_dm_controller("discord_presence")(guild_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось обновить статусы участников: {str(error)[:300]}")

@app.get("/api/discord/guilds/{guild_id}/members/{member_id}")
async def api_discord_guild_member_profile(guild_id: str, member_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not member_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или участника.")
    try:
        return await get_dm_controller("discord_member_profile")(
            guild_id, member_id, str(actor.get("id", ""))
        )
    except PermissionError as error:
        raise HTTPException(status_code=404, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить профиль участника: {str(error)[:300]}")


@app.post("/api/discord/guilds/{guild_id}/members/{member_id}/roles")
async def api_discord_member_role(guild_id: str, member_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not member_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или участника.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный запрос роли.")
    role_id = str(payload.get("role_id", "")) if isinstance(payload, dict) else ""
    action = str(payload.get("action", "")) if isinstance(payload, dict) else ""
    if not role_id.isdigit() or action not in {"add", "remove"}:
        raise HTTPException(status_code=400, detail="Укажи роль и действие add/remove.")
    try:
        return await get_dm_controller("discord_member_role")(guild_id, member_id, role_id, action, str(actor.get("id", "")))
    except Exception as error:
        detail = str(error)[:300]
        if "403" in detail or "Forbidden" in detail:
            raise HTTPException(status_code=403, detail="Discord запретил изменение ролей. Проверь Manage Roles и иерархию ролей бота.")
        raise HTTPException(status_code=502, detail=f"Не удалось изменить роль: {detail}")

@app.get("/api/discord/guilds/{guild_id}/channels")
async def api_discord_guild_channels(guild_id: str, request: Request):
    await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        return await get_dm_controller("discord_channels")(guild_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить каналы: {str(error)[:300]}")

@app.get("/api/discord/guilds/{guild_id}/emojis")
async def api_discord_guild_emojis(guild_id: str, request: Request):
    await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        return await get_dm_controller("discord_emojis")(guild_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить эмодзи сервера: {str(error)[:300]}")



async def require_event_manage_permission(guild_id: str, actor: dict[str, Any], event: dict[str, Any]):
    try:
        return await get_dm_controller("settings_event_manage_permission")(
            guild_id,
            str(actor.get("id", "")),
            str(event.get("channel_id") or ""),
            int(event.get("entity_type") or 3),
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось проверить права на событие: {str(error)[:250]}")


async def require_guild_setting_permission(guild_id: str, actor: dict[str, Any], permission: str):
    try:
        return await get_dm_controller("settings_permission")(guild_id, str(actor.get("id", "")), permission)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось проверить серверные права: {str(error)[:250]}")


@app.get("/api/discord/guilds/{guild_id}/settings/{section}")
async def api_discord_server_settings_section(guild_id: str, section: str, request: Request, after: str = "0", limit: int = 500):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    if section == "channels":
        try:
            return await get_dm_controller("settings_guild_channels")(guild_id, str(actor.get("id", "")))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)[:300])
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)[:300])
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Не удалось загрузить каналы: {str(error)[:300]}")
    if section == "members":
        if not after.isdigit() or not 1 <= limit <= 1000:
            raise HTTPException(status_code=400, detail="Некорректные параметры списка участников.")
        try:
            return await get_dm_controller("discord_members")(guild_id, str(actor.get("id", "")), after, limit)
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Не удалось загрузить участников: {str(error)[:300]}")
    if section == "safety":
        settings = await get_dm_controller("discord_settings")(guild_id, str(actor.get("id", "")))
        guild_data = await discord_request("GET", f"/guilds/{guild_id}")
        return {
            **settings,
            "incidents": guild_data.get("incidents_data") or {},
            "mfa_level": guild_data.get("mfa_level", 0),
            "verification_level": guild_data.get("verification_level", settings.get("settings", {}).get("verification_level", 0)),
        }
    if section == "invites":
        await require_guild_setting_permission(guild_id, actor, "manage_guild|view_audit_log")
        return await discord_request("GET", f"/guilds/{guild_id}/invites")
    if section == "bans":
        await require_guild_setting_permission(guild_id, actor, "ban_members|view_audit_log")
        return await discord_request("GET", f"/guilds/{guild_id}/bans?limit=1000")
    if section == "audit":
        await require_guild_setting_permission(guild_id, actor, "view_audit_log")
        return await discord_request("GET", f"/guilds/{guild_id}/audit-logs?limit=100")
    if section == "automod":
        await require_guild_setting_permission(guild_id, actor, "manage_guild")
        return await discord_request("GET", f"/guilds/{guild_id}/auto-moderation/rules")
    if section == "integrations":
        await require_guild_setting_permission(guild_id, actor, "manage_guild")
        return await discord_request("GET", f"/guilds/{guild_id}/integrations")
    if section == "emoji":
        await require_guild_setting_permission(guild_id, actor, "manage_expressions|create_expressions")
        emojis = await discord_request("GET", f"/guilds/{guild_id}/emojis")
        stickers = await discord_request("GET", f"/guilds/{guild_id}/stickers")
        return {"emojis": emojis or [], "stickers": stickers or []}
    if section == "events":
        # Чтение событий разрешено участникам сервера; проверяем членство отдельно от права управления.
        await get_dm_controller("discord_settings")(guild_id, str(actor.get("id", "")))
        return await discord_request("GET", f"/guilds/{guild_id}/scheduled-events?with_user_count=true")
    raise HTTPException(status_code=404, detail="Неизвестный раздел настроек сервера.")


@app.post("/api/discord/guilds/{guild_id}/settings/channels")
async def api_discord_server_channel_create(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        payload = await request.json()
        return await get_dm_controller("settings_channel_create")(guild_id, str(actor.get("id", "")), payload)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось создать канал: {str(error)[:300]}")


@app.patch("/api/discord/guilds/{guild_id}/settings/channels/{channel_id}")
async def api_discord_server_channel_update(guild_id: str, channel_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или канала.")
    try:
        payload = await request.json()
        return await get_dm_controller("settings_channel_update")(guild_id, str(actor.get("id", "")), channel_id, payload)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось изменить канал: {str(error)[:300]}")


@app.delete("/api/discord/guilds/{guild_id}/settings/channels/{channel_id}")
async def api_discord_server_channel_delete(guild_id: str, channel_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или канала.")
    try:
        return await get_dm_controller("settings_channel_delete")(guild_id, str(actor.get("id", "")), channel_id)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось удалить канал: {str(error)[:300]}")


@app.get("/api/discord/guilds/{guild_id}/settings/channels/{channel_id}/permissions")
async def api_discord_server_channel_permissions(guild_id: str, channel_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или канала.")
    try:
        return await get_dm_controller("settings_channel_permissions")(guild_id, str(actor.get("id", "")), channel_id)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить права канала: {str(error)[:300]}")


@app.patch("/api/discord/guilds/{guild_id}/settings/channels/{channel_id}/permissions/{target_id}")
async def api_discord_server_channel_permission_update(guild_id: str, channel_id: str, target_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not all(value.isdigit() for value in (guild_id, channel_id, target_id)):
        raise HTTPException(status_code=400, detail="Некорректные ID.")
    try:
        payload = await request.json()
        return await get_dm_controller("settings_channel_permission_update")(
            guild_id, str(actor.get("id", "")), channel_id, target_id, payload
        )
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось сохранить права канала: {str(error)[:300]}")


@app.delete("/api/discord/guilds/{guild_id}/settings/channels/{channel_id}/permissions/{target_id}")
async def api_discord_server_channel_permission_delete(guild_id: str, channel_id: str, target_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not all(value.isdigit() for value in (guild_id, channel_id, target_id)):
        raise HTTPException(status_code=400, detail="Некорректные ID.")
    try:
        return await get_dm_controller("settings_channel_permission_delete")(
            guild_id, str(actor.get("id", "")), channel_id, target_id
        )
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось сбросить переопределение прав: {str(error)[:300]}")


@app.delete("/api/discord/guilds/{guild_id}/settings/bans/{user_id}")
async def api_discord_server_unban(guild_id: str, user_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not user_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или пользователя.")
    await require_guild_setting_permission(guild_id, actor, "ban_members")
    return await discord_request("DELETE", f"/guilds/{guild_id}/bans/{user_id}")


@app.post("/api/discord/guilds/{guild_id}/settings/members/{member_id}/action")
async def api_discord_server_member_action(guild_id: str, member_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not member_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или участника.")
    try:
        payload = await request.json()
        return await get_dm_controller("settings_member_action")(guild_id, str(actor.get("id", "")), member_id, payload)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось выполнить действие над участником: {str(error)[:300]}")


@app.patch("/api/discord/guilds/{guild_id}/settings/safety")
async def api_discord_server_safety_update(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректные настройки безопасности.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Некорректные настройки безопасности.")
    incident_payload = {}
    for key in ("invites_disabled_until", "dms_disabled_until"):
        if key in payload:
            value = payload[key]
            if value is not None:
                try:
                    target_time = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                    if target_time.tzinfo is None:
                        raise ValueError()
                    remaining = (target_time - datetime.now(timezone.utc)).total_seconds()
                    if remaining < 0 or remaining > 24 * 60 * 60:
                        raise ValueError()
                except (TypeError, ValueError):
                    raise HTTPException(status_code=400, detail="Временная защита от рейдов может быть включена максимум на следующие 24 часа.")
            incident_payload[key] = value
    regular = {key: value for key, value in payload.items() if key not in incident_payload}
    result = None
    if regular:
        try:
            result = await get_dm_controller("discord_settings_update")(guild_id, str(actor.get("id", "")), regular)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)[:300])
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)[:300])
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Не удалось сохранить общие параметры безопасности: {str(error)[:250]}")
    if incident_payload:
        await require_guild_setting_permission(guild_id, actor, "manage_guild")
        incidents = await discord_request("PUT", f"/guilds/{guild_id}/incident-actions", payload=incident_payload)
        if result is None:
            result = {"ok": True}
        result["incidents"] = incidents
    return result or {"ok": True}


@app.post("/api/discord/guilds/{guild_id}/settings/invites")
async def api_discord_server_invite_create(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    payload = await request.json()
    channel_id = str(payload.get("channel_id") or "")
    if not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Выбери текстовый канал для приглашения.")
    try:
        await get_dm_controller("settings_channel_action_permission")(
            guild_id, str(actor.get("id", "")), channel_id, "create_instant_invite"
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    try:
        max_age = int(payload.get("max_age", 86400))
        max_uses = int(payload.get("max_uses", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Срок и лимит приглашения должны быть числами.")
    if max_age not in {0, 3600, 21600, 86400, 604800} or not 0 <= max_uses <= 100:
        raise HTTPException(status_code=400, detail="Недопустимый срок или лимит использований приглашения.")
    body = {
        "max_age": max_age,
        "max_uses": max_uses,
        "temporary": bool(payload.get("temporary", False)),
        "unique": bool(payload.get("unique", True)),
    }
    return await discord_request("POST", f"/channels/{channel_id}/invites", payload=body)


@app.delete("/api/discord/guilds/{guild_id}/settings/invites/{code}")
async def api_discord_server_invite_delete(guild_id: str, code: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not code or len(code) > 100:
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или код приглашения.")
    await require_guild_setting_permission(guild_id, actor, "manage_guild")
    invite = await discord_request("GET", f"/invites/{code}")
    if str(invite.get("guild", {}).get("id") or "") != guild_id:
        raise HTTPException(status_code=404, detail="Приглашение не относится к выбранному серверу.")
    return await discord_request("DELETE", f"/invites/{code}")


@app.post("/api/discord/guilds/{guild_id}/settings/automod")
async def api_discord_server_automod_create(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    await require_guild_setting_permission(guild_id, actor, "manage_guild")
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Некорректное правило AutoMod.")
    trigger_type = int(payload.get("trigger_type") or 0)
    expected_event = 2 if trigger_type == 6 else 1
    if trigger_type not in {1, 3, 4, 5, 6} or int(payload.get("event_type") or 0) != expected_event:
        raise HTTPException(status_code=400, detail="Тип события AutoMod не соответствует выбранному триггеру.")
    actions = payload.get("actions")
    if not isinstance(actions, list) or not actions:
        raise HTTPException(status_code=400, detail="Добавь хотя бы одно действие AutoMod.")
    if any(not isinstance(item, dict) or int(item.get("type") or 0) not in {1, 2, 3, 4} for item in actions):
        raise HTTPException(status_code=400, detail="Неизвестное действие AutoMod.")
    if any(int(item.get("type") or 0) == 4 for item in actions) and trigger_type != 6:
        raise HTTPException(status_code=400, detail="Блокировка взаимодействий предназначена для фильтра профиля участника.")
    if any(int(item.get("type") or 0) == 3 for item in actions):
        if trigger_type not in {1, 5}:
            raise HTTPException(status_code=400, detail="Discord разрешает тайм-аут только для ключевых слов и массовых упоминаний.")
        await require_guild_setting_permission(guild_id, actor, "moderate_members")
    metadata = payload.get("trigger_metadata") or {}
    if trigger_type in {1, 6}:
        keywords = metadata.get("keyword_filter") if isinstance(metadata, dict) else None
        if not isinstance(keywords, list) or not keywords or any(not isinstance(word, str) or not word.strip() or len(word) > 60 for word in keywords) or len(keywords) > 1000:
            raise HTTPException(status_code=400, detail="Для выбранного правила укажи от 1 до 1000 ключевых слов длиной до 60 символов.")
    if trigger_type == 5:
        limit = int(metadata.get("mention_total_limit") or 0) if isinstance(metadata, dict) else 0
        if not 1 <= limit <= 50:
            raise HTTPException(status_code=400, detail="Лимит уникальных упоминаний должен быть от 1 до 50.")
    return await discord_request("POST", f"/guilds/{guild_id}/auto-moderation/rules", payload=payload)


@app.patch("/api/discord/guilds/{guild_id}/settings/automod/{rule_id}")
async def api_discord_server_automod_update(guild_id: str, rule_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not rule_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или правила AutoMod.")
    await require_guild_setting_permission(guild_id, actor, "manage_guild")
    payload = await request.json()
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="Некорректные изменения правила AutoMod.")
    if "actions" in payload:
        actions = payload.get("actions")
        if not isinstance(actions, list) or not actions or any(not isinstance(item, dict) or int(item.get("type") or 0) not in {1, 2, 3, 4} for item in actions):
            raise HTTPException(status_code=400, detail="Некорректный список действий AutoMod.")
        if any(int(item.get("type") or 0) == 3 for item in actions):
            current = await discord_request("GET", f"/guilds/{guild_id}/auto-moderation/rules/{rule_id}")
            if int(current.get("trigger_type") or 0) not in {1, 5}:
                raise HTTPException(status_code=400, detail="Discord разрешает тайм-аут только для ключевых слов и массовых упоминаний.")
            await require_guild_setting_permission(guild_id, actor, "moderate_members")
        if any(int(item.get("type") or 0) == 4 for item in actions):
            current = await discord_request("GET", f"/guilds/{guild_id}/auto-moderation/rules/{rule_id}")
            if int(current.get("trigger_type") or 0) != 6:
                raise HTTPException(status_code=400, detail="Блокировка взаимодействий предназначена для фильтра профиля участника.")
    return await discord_request("PATCH", f"/guilds/{guild_id}/auto-moderation/rules/{rule_id}", payload=payload)


@app.delete("/api/discord/guilds/{guild_id}/settings/automod/{rule_id}")
async def api_discord_server_automod_delete(guild_id: str, rule_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not rule_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера или правила AutoMod.")
    await require_guild_setting_permission(guild_id, actor, "manage_guild")
    return await discord_request("DELETE", f"/guilds/{guild_id}/auto-moderation/rules/{rule_id}")


@app.delete("/api/discord/guilds/{guild_id}/settings/integrations/{integration_id}")
async def api_discord_server_integration_delete(guild_id: str, integration_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not integration_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID интеграции.")
    await require_guild_setting_permission(guild_id, actor, "manage_guild")
    return await discord_request("DELETE", f"/guilds/{guild_id}/integrations/{integration_id}")


@app.post("/api/discord/guilds/{guild_id}/settings/emoji")
async def api_discord_server_emoji_create(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    await require_guild_setting_permission(guild_id, actor, "manage_expressions|create_expressions")
    payload = await request.json()
    name = str(payload.get("name") or "").strip()
    image = str(payload.get("image") or "")
    if not 2 <= len(name) <= 32 or not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise HTTPException(status_code=400, detail="Имя эмодзи: 2–32 символа, латинские буквы, цифры и _.")
    if not image.startswith("data:image/") or len(image) > 400000:
        raise HTTPException(status_code=400, detail="Загрузи изображение эмодзи размером не более 256 КБ.")
    return await discord_request("POST", f"/guilds/{guild_id}/emojis", payload={"name": name, "image": image, "roles": payload.get("roles") or []})


@app.patch("/api/discord/guilds/{guild_id}/settings/emoji/{emoji_id}")
async def api_discord_server_emoji_update(guild_id: str, emoji_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not emoji_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID эмодзи.")
    await require_guild_setting_permission(guild_id, actor, "manage_expressions|create_expressions")
    payload = await request.json()
    if not isinstance(payload, dict) or set(payload) - {"name", "roles"}:
        raise HTTPException(status_code=400, detail="Некорректные параметры эмодзи.")
    if "name" in payload and not re.fullmatch(r"[A-Za-z0-9_]{2,32}", str(payload["name"]).strip()):
        raise HTTPException(status_code=400, detail="Имя эмодзи: 2–32 символа, латинские буквы, цифры и _.")
    if "roles" in payload and (not isinstance(payload["roles"], list) or any(not str(role_id).isdigit() for role_id in payload["roles"])):
        raise HTTPException(status_code=400, detail="Список ролей для эмодзи некорректен.")
    return await discord_request("PATCH", f"/guilds/{guild_id}/emojis/{emoji_id}", payload=payload)


@app.delete("/api/discord/guilds/{guild_id}/settings/emoji/{emoji_id}")
async def api_discord_server_emoji_delete(guild_id: str, emoji_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not emoji_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID эмодзи.")
    await require_guild_setting_permission(guild_id, actor, "manage_expressions|create_expressions")
    return await discord_request("DELETE", f"/guilds/{guild_id}/emojis/{emoji_id}")


async def discord_multipart_request(path: str, *, data: dict[str, str], file_name: str, file_bytes: bytes, content_type: str = "application/octet-stream"):
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Не настроен DISCORD_BOT_TOKEN.")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{DISCORD_API}{path}",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
            data=data,
            files={"file": (file_name, file_bytes, content_type)},
        )
    if response.status_code >= 400:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {}
        detail = str(error_data.get("message") or response.text or "без описания")[:500]
        raise HTTPException(status_code=502, detail=f"Discord API отклонил загрузку файла (HTTP {response.status_code}): {detail}")
    return response.json() if response.content else None


@app.post("/api/discord/guilds/{guild_id}/settings/stickers")
async def api_discord_server_sticker_create(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    await require_guild_setting_permission(guild_id, actor, "manage_expressions|create_expressions")
    try:
        form = await request.form()
        upload = form.get("file")
        if not upload or not getattr(upload, "filename", ""):
            raise HTTPException(status_code=400, detail="Выбери файл стикера.")
        content = await upload.read()
        if len(content) > 512 * 1024:
            raise HTTPException(status_code=413, detail="Файл стикера не должен превышать 512 КБ.")
        name = str(form.get("name") or "").strip()
        tags = str(form.get("tags") or "").strip()
        description = str(form.get("description") or "").strip()
        if not 2 <= len(name) <= 30 or not 1 <= len(tags) <= 200 or (description and not 2 <= len(description) <= 100):
            raise HTTPException(status_code=400, detail="Проверь имя (2–30), Unicode-эмодзи тег (1–200) и описание (пустое или 2–100 символов).")
        return await discord_multipart_request(
            f"/guilds/{guild_id}/stickers",
            data={"name": name, "tags": tags, "description": description},
            file_name=str(upload.filename)[:255], file_bytes=content,
            content_type=str(getattr(upload, "content_type", "") or "application/octet-stream"),
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Не удалось прочитать файл стикера.")


@app.patch("/api/discord/guilds/{guild_id}/settings/stickers/{sticker_id}")
async def api_discord_server_sticker_update(guild_id: str, sticker_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not sticker_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID стикера.")
    await require_guild_setting_permission(guild_id, actor, "manage_expressions|create_expressions")
    payload = await request.json()
    if not isinstance(payload, dict) or set(payload) - {"name", "description", "tags"}:
        raise HTTPException(status_code=400, detail="Некорректные параметры стикера.")
    if "name" in payload and not 2 <= len(str(payload["name"]).strip()) <= 30:
        raise HTTPException(status_code=400, detail="Имя стикера должно содержать 2–30 символов.")
    if "description" in payload and len(str(payload["description"] or "")) not in (0,) and not 2 <= len(str(payload["description"])) <= 100:
        raise HTTPException(status_code=400, detail="Описание стикера должно быть пустым или содержать 2–100 символов.")
    if "tags" in payload and not 1 <= len(str(payload["tags"]).strip()) <= 200:
        raise HTTPException(status_code=400, detail="Тег стикера должен содержать от 1 до 200 символов.")
    return await discord_request("PATCH", f"/guilds/{guild_id}/stickers/{sticker_id}", payload=payload)


@app.delete("/api/discord/guilds/{guild_id}/settings/stickers/{sticker_id}")
async def api_discord_server_sticker_delete(guild_id: str, sticker_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not sticker_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID стикера.")
    await require_guild_setting_permission(guild_id, actor, "manage_expressions|create_expressions")
    return await discord_request("DELETE", f"/guilds/{guild_id}/stickers/{sticker_id}")


@app.post("/api/discord/guilds/{guild_id}/settings/events")
async def api_discord_server_event_create(guild_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID сервера.")
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Некорректные параметры события.")
    name = str(payload.get("name") or "").strip()
    if not 1 <= len(name) <= 100:
        raise HTTPException(status_code=400, detail="Название события должно содержать 1–100 символов.")
    try:
        entity_type = int(payload.get("entity_type") or 3)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Некорректный тип события.")
    if entity_type not in {1, 2, 3}:
        raise HTTPException(status_code=400, detail="Тип события должен быть внешним, голосовым или Stage.")
    body = {
        "name": name,
        "description": str(payload.get("description") or "")[:1000] or None,
        "privacy_level": 2,
        "entity_type": entity_type,
        "scheduled_start_time": payload.get("scheduled_start_time"),
    }
    if entity_type == 3:
        location = str((payload.get("entity_metadata") or {}).get("location") or "").strip()
        if not location or not payload.get("scheduled_end_time"):
            raise HTTPException(status_code=400, detail="Для внешнего события укажи место и время окончания.")
        body["channel_id"] = None
        body["entity_metadata"] = {"location": location[:100]}
        body["scheduled_end_time"] = payload["scheduled_end_time"]
        await get_dm_controller("settings_event_permission")(
            guild_id, str(actor.get("id", "")), None, entity_type
        )
    else:
        channel_id = str(payload.get("channel_id") or "")
        if not channel_id.isdigit():
            raise HTTPException(status_code=400, detail="Выбери голосовой или Stage-канал.")
        channel = await discord_request("GET", f"/channels/{channel_id}")
        expected_type = 13 if entity_type == 1 else 2
        if str(channel.get("guild_id") or "") != guild_id or int(channel.get("type") or 0) != expected_type:
            expected_label = "Stage" if entity_type == 1 else "голосовой"
            raise HTTPException(status_code=400, detail=f"Для выбранного типа события требуется {expected_label}-канал этого сервера.")
        await get_dm_controller("settings_event_permission")(
            guild_id, str(actor.get("id", "")), channel_id, entity_type
        )
        body["channel_id"] = channel_id
    if payload.get("scheduled_end_time") and entity_type != 3:
        body["scheduled_end_time"] = payload["scheduled_end_time"]
    return await discord_request("POST", f"/guilds/{guild_id}/scheduled-events", payload=body)


@app.patch("/api/discord/guilds/{guild_id}/settings/events/{event_id}")
async def api_discord_server_event_update(guild_id: str, event_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not event_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID события.")
    event = await discord_request("GET", f"/guilds/{guild_id}/scheduled-events/{event_id}")
    await require_event_manage_permission(guild_id, actor, event)
    payload = await request.json()
    allowed = {"name", "description", "scheduled_start_time", "scheduled_end_time", "status", "entity_metadata"}
    body = {key: payload[key] for key in allowed if key in payload}
    if not body:
        raise HTTPException(status_code=400, detail="Нет полей для изменения события.")
    if "name" in body and not 1 <= len(str(body["name"]).strip()) <= 100:
        raise HTTPException(status_code=400, detail="Название события должно содержать 1–100 символов.")
    if "description" in body and body["description"] is not None and len(str(body["description"])) > 1000:
        raise HTTPException(status_code=400, detail="Описание события не должно превышать 1000 символов.")
    if "entity_metadata" in body:
        location = str((body["entity_metadata"] or {}).get("location") or "").strip()
        if not location:
            raise HTTPException(status_code=400, detail="Для внешнего события укажи место проведения.")
        body["entity_metadata"] = {"location": location[:100]}
    return await discord_request("PATCH", f"/guilds/{guild_id}/scheduled-events/{event_id}", payload=body)


@app.delete("/api/discord/guilds/{guild_id}/settings/events/{event_id}")
async def api_discord_server_event_delete(guild_id: str, event_id: str, request: Request):
    actor = await require_access(request, "adm")
    if not guild_id.isdigit() or not event_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID события.")
    event = await discord_request("GET", f"/guilds/{guild_id}/scheduled-events/{event_id}")
    await require_event_manage_permission(guild_id, actor, event)
    return await discord_request("DELETE", f"/guilds/{guild_id}/scheduled-events/{event_id}")


@app.get("/api/discord/channels/{channel_id}/messages")
async def api_discord_channel_history(channel_id: str, request: Request):
    await require_access(request, "adm")
    if not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID канала.")
    try:
        return await get_dm_controller("discord_channel_history")(channel_id, 100)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось открыть канал: {str(error)[:300]}")

@app.post("/api/discord/channels/{channel_id}/messages")
async def api_discord_channel_send(channel_id: str, request: Request):
    await require_access(request, "adm")
    if not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID канала.")
    try:
        form = await request.form()
        content = str(form.get("content") or "").strip()
        reply_to = str(form.get("reply_to") or "").strip()
        uploads = form.getlist("files")
        if len(uploads) > 10:
            raise HTTPException(status_code=400, detail="Можно прикрепить не больше 10 файлов.")
        files, total = [], 0
        for upload in uploads:
            data = await upload.read()
            if len(data) > 8 * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"Файл «{upload.filename}» больше 8 МБ.")
            total += len(data)
            files.append((str(upload.filename or "file")[:255], data))
        if total > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Общий размер вложений не должен превышать 25 МБ.")
        if not content and not files:
            raise HTTPException(status_code=400, detail="Добавь текст или файл.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Не удалось прочитать отправляемые файлы.")
    try:
        return await get_dm_controller("discord_channel_send")(channel_id, content, files, reply_to or None)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось отправить сообщение: {str(error)[:300]}")


@app.patch("/api/discord/channels/{channel_id}/messages/{message_id}")
async def api_discord_message_edit(channel_id: str, message_id: str, request: Request):
    await require_access(request, "adm")
    if not channel_id.isdigit() or not message_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID канала или сообщения.")
    try:
        payload = await request.json()
        content = str(payload.get("content") or "")
        if len(content) > 2000:
            raise HTTPException(status_code=400, detail="Максимальная длина сообщения — 2000 символов.")
        return await get_dm_controller("discord_message_edit")(channel_id, message_id, content)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось изменить сообщение: {str(error)[:300]}")


@app.delete("/api/discord/channels/{channel_id}/messages/{message_id}")
async def api_discord_message_delete(channel_id: str, message_id: str, request: Request):
    await require_access(request, "adm")
    if not channel_id.isdigit() or not message_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID канала или сообщения.")
    try:
        return await get_dm_controller("discord_message_delete")(channel_id, message_id)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось удалить сообщение: {str(error)[:300]}")


@app.post("/api/discord/channels/{channel_id}/messages/{message_id}/reactions")
async def api_discord_message_react(channel_id: str, message_id: str, request: Request):
    await require_access(request, "adm")
    if not channel_id.isdigit() or not message_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID канала или сообщения.")
    try:
        payload = await request.json()
        emoji = str(payload.get("emoji") or "").strip()
        return await get_dm_controller("discord_message_react")(channel_id, message_id, emoji)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось добавить реакцию: {str(error)[:300]}")


@app.post("/api/discord/channels/{channel_id}/messages/{message_id}/pin")
async def api_discord_message_pin(channel_id: str, message_id: str, request: Request):
    await require_access(request, "adm")
    if not channel_id.isdigit() or not message_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID канала или сообщения.")
    try:
        payload = await request.json()
        pinned = payload.get("pinned")
        if not isinstance(pinned, bool):
            raise HTTPException(status_code=400, detail="Укажи состояние pinned true/false.")
        return await get_dm_controller("discord_message_pin")(channel_id, message_id, pinned)
    except HTTPException:
        raise
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)[:300])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)[:300])
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось закрепить сообщение: {str(error)[:300]}")


# ================== DISCORD BOT DIRECT MESSAGES ==================
def get_dm_controller(action: str):
    controller=getattr(app.state, 'bot_controller', None)
    callback=controller.get(action) if controller else None
    if not callback: raise HTTPException(status_code=503, detail='Discord DM-модуль не подключён к работающему процессу бота.')
    return callback

@app.get('/api/discord/dms')
async def api_discord_dm_list(request: Request):
    await require_access(request, 'adm')
    try: return await get_dm_controller('dm_list')()
    except Exception as error: raise HTTPException(status_code=502, detail=f'Не удалось загрузить личные диалоги: {str(error)[:300]}')

@app.get('/api/discord/dms/search')
async def api_discord_dm_search(request: Request, q: str = ''):
    await require_access(request, 'adm')
    query=str(q or '').strip()[:100]
    if len(query)<2: return {'users':[]}
    try: return await get_dm_controller('dm_search')(query)
    except Exception as error: raise HTTPException(status_code=502, detail=f'Поиск пользователей не выполнен: {str(error)[:300]}')

@app.get('/api/discord/dms/{user_id}/messages')
async def api_discord_dm_history(user_id: str, request: Request):
    await require_access(request, 'adm')
    if not user_id.isdigit(): raise HTTPException(status_code=400, detail='Некорректный Discord ID.')
    try: return await get_dm_controller('dm_history')(user_id, 60)
    except Exception as error:
        detail=str(error)[:350]
        if '403' in detail or 'Forbidden' in detail: detail='Discord не разрешил открыть личный диалог с этим пользователем. Возможно, действуют ограничения приватности.'
        raise HTTPException(status_code=502, detail=f'Не удалось открыть личные сообщения: {detail}')

DM_SEND_LAST_AT: dict[str, float] = {}

@app.post('/api/discord/dms/{user_id}/messages')
async def api_discord_dm_send(user_id: str, request: Request):
    actor=await require_access(request, 'adm')
    if not user_id.isdigit(): raise HTTPException(status_code=400, detail='Некорректный Discord ID.')
    try:
        form=await request.form()
        content=str(form.get('content') or '').strip()
        reply_to=str(form.get('reply_to') or '').strip()
        uploads=form.getlist('files')
        if len(uploads)>10: raise HTTPException(status_code=400, detail='Можно прикрепить не больше 10 файлов.')
        files=[];total=0
        for upload in uploads:
            data=await upload.read()
            if len(data)>8*1024*1024: raise HTTPException(status_code=413, detail=f'Файл «{upload.filename}» больше 8 МБ.')
            total+=len(data);files.append((str(upload.filename or 'file')[:255],data))
        if total>25*1024*1024: raise HTTPException(status_code=413, detail='Общий размер вложений не должен превышать 25 МБ.')
        if not content and not files: raise HTTPException(status_code=400, detail='Напиши сообщение или прикрепи файл.')
    except HTTPException: raise
    except Exception: raise HTTPException(status_code=400, detail='Не удалось прочитать отправляемые файлы.')
    if len(content)>2000: raise HTTPException(status_code=400, detail='Максимальная длина сообщения Discord — 2000 символов.')
    rate_key=f"{actor.get('id')}:{user_id}"
    now=datetime.now(timezone.utc).timestamp()
    last_sent=DM_SEND_LAST_AT.get(rate_key, 0.0)
    if now-last_sent < 2.0: raise HTTPException(status_code=429, detail='Подожди пару секунд перед следующим сообщением этому пользователю.')
    DM_SEND_LAST_AT[rate_key]=now
    try:
        result=await get_dm_controller('dm_send')(user_id, content, files, reply_to or None)
        print(f'[PANEL DM] Администратор {actor.get("id")} отправил DM пользователю {user_id}.', flush=True)
        return result
    except Exception as error:
        detail=str(error)[:350]
        if '403' in detail or 'Forbidden' in detail: detail='Discord запретил отправку этому пользователю. Он мог закрыть личные сообщения или ограничить взаимодействие с ботами.'
        raise HTTPException(status_code=502, detail=f'Не удалось отправить личное сообщение: {detail}')

SHOP_ITEMS_PANEL = [
    {"name": "PVP", "price": 1000, "type": "kit"}, {"name": "CYBER", "price": 1500, "type": "kit"},
    {"name": "RICH", "price": 2000, "type": "kit"}, {"name": "TOPER", "price": 2500, "type": "kit"},
    {"name": "D.OWNER", "price": 2300, "type": "донат"}, {"name": "DADMIN", "price": 1000, "type": "донат"},
    {"name": "D.GLMODER", "price": 900, "type": "донат"}, {"name": "D.STMODER", "price": 750, "type": "донат"},
    {"name": "D.MODER", "price": 500, "type": "донат"}, {"name": "WHITE", "price": 5000, "type": "донат"},
    {"name": "RABBIT", "price": 4500, "type": "донат"}, {"name": "DHELPER", "price": 4500, "type": "донат"},
    {"name": "GOD", "price": 4000, "type": "донат"}, {"name": "ENDER", "price": 4000, "type": "донат"},
    {"name": "DRACULA", "price": 3500, "type": "донат"}, {"name": "BERSERK", "price": 3500, "type": "донат"},
    {"name": "COBRA", "price": 3000, "type": "донат"},
    {"name": "Кейс «Всё или ничего»", "price": 6000, "type": "кейс"},
    {"name": "Кейс с Супер Донатом", "price": 4500, "type": "кейс"},
    {"name": "Кейс с Супер Риликами", "price": 3000, "type": "кейс"},
    {"name": "Снятие 1 выговора", "price": 400, "type": "услуга"}
]
@app.post("/api/shop/purchase")
async def api_shop_purchase(request: Request):
    user = await require_access(request, "media")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный запрос покупки.")
    item_name = str(payload.get("item", "")).strip()
    request_id = str(payload.get("request_id", "")).strip()
    item = next((entry for entry in SHOP_ITEMS_PANEL if entry["name"] == item_name), None)
    if not item:
        raise HTTPException(status_code=400, detail="Товар не найден в каталоге.")
    if not request_id or len(request_id) > 100:
        raise HTTPException(status_code=400, detail="Не удалось проверить запрос покупки.")
    return await bot_api_request(
        "POST", "/api/internal/data/shop/purchase",
        payload={"user_id": str(user["id"]), "item": item_name, "request_id": request_id,
             "minecraft_nick": str(payload.get("minecraft_nick", "")).strip()},
    )


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
        # Получаем всех участников первого сервера и оставляем только роль «Команда медиа».
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


@app.get("/api/sheets/staff-candidates")
async def api_sheets_staff_candidates(request: Request):
    await require_access(request, "co_adm")
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("sheets_candidates"):
        raise HTTPException(status_code=503, detail="Управление таблицей состава не подключено к боту.")
    try:
        return await controller["sheets_candidates"]()
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось получить состав Discord: {error}")


@app.post("/api/sheets/staff-add")
async def api_sheets_staff_add(request: Request):
    await require_access(request, "co_adm")
    payload = await request.json()
    required = ("user_id", "nickname", "position", "profile_url", "personal_channel_id")
    if any(not str(payload.get(key, "")).strip() for key in required):
        raise HTTPException(status_code=400, detail="Заполни никнейм, должность, ссылку на профиль и ID личного канала.")
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("sheets_add_staff"):
        raise HTTPException(status_code=503, detail="Добавление состава не подключено к боту.")
    try:
        return await controller["sheets_add_staff"](
            payload["user_id"], payload["nickname"], payload["position"],
            payload["profile_url"], payload["personal_channel_id"],
        )
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Не удалось добавить участника: {error}")


@app.get("/api/status")
async def api_status():
    """Проверяет именно API процесса Discord-бота, а не доступность самого Dashboard."""
    if not BOT_API_URL:
        return {"ok": False, "bot_api": False, "status": "not_configured", "message": "API бота не настроено"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BOT_API_URL}/health")
        if response.status_code != 200:
            return {"ok": True, "bot_api": False, "status": "offline", "message": f"Бот API ответил HTTP {response.status_code}"}
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            return {"ok": True, "bot_api": False, "status": "offline", "message": "Бот API не подтвердил готовность"}
        return {"ok": True, "bot_api": True, "status": "online", "message": "Бот подключён"}
    except (httpx.HTTPError, ValueError):
        return {"ok": True, "bot_api": False, "status": "offline", "message": "Нет соединения с API бота"}


async def probe_bot_api(base_url: str) -> dict[str, Any]:
    if not base_url:
        return {"online": False, "status": "not_configured"}
    try:
        async with httpx.AsyncClient(timeout=4.5) as client:
            response = await client.get(f"{base_url.rstrip('/')}/health")
        if response.status_code != 200:
            return {"online": False, "status": "offline"}
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            return {"online": False, "status": "offline"}
        return {
            "online": payload.get("discord_ready", True) is not False,
            "status": "online" if payload.get("discord_ready", True) is not False else "connecting",
            "discord_ready": payload.get("discord_ready"),
            "guild_count": payload.get("guild_count"),
        }
    except (httpx.HTTPError, ValueError):
        return {"online": False, "status": "offline"}


@app.get("/api/bots/status")
async def api_bots_status(request: Request):
    await require_access(request, "adm")
    gastworld, ticketbot = await asyncio.gather(
        probe_bot_api(BOT_API_URL),
        probe_bot_api(TICKETBOT_API_URL),
    )
    return {
        "bots": {
            "gastworld": {"name": "GastWorld", **gastworld},
            "ticketbot": {"name": "Ticket Bot", **ticketbot},
        }
    }


@app.get("/health")
async def health():
    return {"ok": True, "service": "gastworld-control-panel"}



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
        return {"status": {"online": False, "bot_name": "GastWorld", "guild_name": "Нет подключения к процессу бота", "guild_count": 0, "latency_ms": None}, "available": False}
    try:
        status = await controller["status"]()
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Не удалось получить статус бота: {error}")
    return {"status": status, "available": True, "updated_at": datetime.now(timezone.utc).isoformat()}


@app.get("/api/internal/tickets")
async def internal_tickets(request: Request):
    require_bot_data_secret(request)
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("tickets"):
        raise HTTPException(status_code=503, detail="Система тикетов не подключена к процессу бота.")
    return await controller["tickets"]()


@app.get("/api/internal/tickets/acceptance")
async def internal_ticket_acceptance(request: Request):
    require_bot_data_secret(request)
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("ticket_acceptance"):
        raise HTTPException(status_code=503, detail="Управление приёмом тикетов не подключено.")
    return await controller["ticket_acceptance"]()


@app.post("/api/internal/tickets/acceptance")
async def internal_set_ticket_acceptance(request: Request):
    require_bot_data_secret(request)
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("set_ticket_acceptance"):
        raise HTTPException(status_code=503, detail="Управление приёмом тикетов не подключено.")
    payload = await request.json()
    if not isinstance(payload.get("accepting"), bool):
        raise HTTPException(status_code=400, detail="Ожидается логическое значение accepting.")
    try:
        return await controller["set_ticket_acceptance"](payload["accepting"])
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/api/internal/tickets/{channel_id}/status")
async def internal_ticket_status(channel_id: str, request: Request):
    require_bot_data_secret(request)
    if not channel_id.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный ID тикета.")
    controller = getattr(app.state, "bot_controller", None)
    if not controller or not controller.get("ticket_status"):
        raise HTTPException(status_code=503, detail="Управление тикетами не подключено к процессу бота.")
    payload = await request.json()
    status = str(payload.get("status", "")).strip().lower()
    if status not in {"open", "closed", "resolved"}:
        raise HTTPException(status_code=400, detail="Неизвестный статус тикета.")
    try:
        return await controller["ticket_status"](channel_id, status, str(payload.get("actor", "Dashboard"))[:100])
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


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
        profile_url = str(app_data.get("profile_url", "")).strip()
        normalized_position = position.casefold().strip()
        if normalized_position in {"tt", "тт", "tiktok", "тикток"}:
            stored_position = "TT"
        elif normalized_position in {"yt", "ютуб", "youtube"}:
            stored_position = "YT"
        else:
            stored_position = ""
        if not nick or not stored_position or not profile_url.startswith(("https://", "http://")) or not message_id:
            raise HTTPException(status_code=409, detail="В заявке отсутствуют корректные ник, должность, ссылка на профиль или ID сообщения.")
        member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{user_id}")
        target_user = member.get("user", {})
        target_name = member.get("nick") or target_user.get("global_name") or target_user.get("username") or user_id
        roles = {str(x) for x in member.get("roles", [])}
        new_nick = f"{nick} | {position}"[:32]
        await discord_request("PATCH", f"/guilds/{GUILD_ID}/members/{user_id}", payload={"nick": new_nick})
        normalized_position = position.casefold().strip()
        if normalized_position in {"tt", "тт", "tiktok", "тикток"}:
            first_server_role_ids = (
                "1493615940741365881",
                "1573343622986862602",
                "1493196315205566545",
                "1492975006446260306",
            )
        elif normalized_position in {"yt", "ютуб", "youtube"}:
            first_server_role_ids = (
                "1493615940741365881",
                "1573343622986862602",
                "1493196315205566545",
                "1492975112985645166",
            )
        else:
            raise HTTPException(status_code=409, detail=f"Неизвестная должность в заявке: {position}")

        roles.update(first_server_role_ids)
        # После успешной верификации снимаем обе роли ожидания/предварительной проверки.
        roles.discard("1520158772067041314")
        roles.discard("1567152429093363782")
        await discord_request("PATCH", f"/guilds/{GUILD_ID}/members/{user_id}", payload={"roles": sorted(roles)})

        # На втором сервере выдаём общую роль и роль выбранной площадки.
        secondary_guild_id = "1454858971084230822"
        common_secondary_role_id = "1573415226186010795"
        platform_role_ids = {
            "tt": "1573415527932629173",
            "тт": "1573415527932629173",
            "tiktok": "1573415527932629173",
            "тикток": "1573415527932629173",
            "yt": "1556575041657774100",
            "ютуб": "1556575041657774100",
            "youtube": "1556575041657774100",
        }
        normalized_position = position.casefold().strip()
        platform_role_id = platform_role_ids.get(normalized_position)
        secondary_role_status = "not_applicable"
        if platform_role_id:
            try:
                await discord_request("GET", f"/guilds/{secondary_guild_id}/members/{user_id}")
                for role_id in (common_secondary_role_id, platform_role_id):
                    await discord_request(
                        "PUT",
                        f"/guilds/{secondary_guild_id}/members/{user_id}/roles/{role_id}",
                    )
                    print(f"✅ [ЗАЯВКИ] Выдана роль {role_id} на втором сервере пользователю {user_id}.", flush=True)
                secondary_role_status = "granted"
            except HTTPException as exc:
                secondary_role_status = f"failed: {exc.detail}"
                print(f"❌ [ЗАЯВКИ] Не удалось выдать комплект ролей TT/YT на сервере {secondary_guild_id} пользователю {user_id}: {exc.detail}", flush=True)
        else:
            secondary_role_status = f"unknown_position: {position}"
            print(f"⚠️ [ЗАЯВКИ] Неизвестная должность '{position}' у заявки {user_id}; роли второго сервера не выбраны.", flush=True)
        channel_payload = {
            "name": nick.lower().replace(" ", "-")[:90],
            "type": 0,
            "parent_id": "1573332011739779164",
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
            db.execute(
                """INSERT INTO media_staff_profiles (user_id, nickname, position, profile_url)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       nickname = excluded.nickname,
                       position = excluded.position,
                       profile_url = excluded.profile_url,
                       updated_at = CURRENT_TIMESTAMP""",
                (int(user_id), nick, stored_position, profile_url),
            )
            db.execute("DELETE FROM pending_requests WHERE request_type = 'join' AND user_id = ?", (int(user_id),))
            db.commit()
        await discord_request("PUT", f"/channels/1563918554829422704/messages/{message_id}/reactions/%E2%9C%85/@me")
        accepted = {
            "embeds": [{
                "title": "✅ ЗАЯВКА ОДОБРЕНА",
                "description": f"<@{user_id}> успешно принят в команду **GastWorld Media**!",
                "color": 65280,
                "fields": [
                    {"name": "🎮 Игровой ник", "value": nick, "inline": True},
                    {"name": "🛡️ Должность", "value": position, "inline": True},
                    {"name": "📁 Личный канал", "value": f"<#{channel_id}>", "inline": False},
                    {"name": "🚀 Следующий шаг", "value": "Загляни в личный канал, ознакомься с инструкциями и приступай к работе!", "inline": False},
                    {"name": "Одобрил", "value": f"{actor_name} (<@{actor_id}>)", "inline": False},
                ],
                "footer": {"text": f"GASTWORLD MEDIA • Принял: {actor_name}"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
            "allowed_mentions": {"parse": [], "users": []},
        }
        await discord_request("POST", f"/channels/1563918554829422704/messages", payload=accepted)
        welcome = {
            "content": f"Привет, <@{user_id}>! Ты попал в команду Медиа.",
            "embeds": [{
                "title": "🎬 GASTWORLD MEDIA",
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
                    {"name": "🔥 СНИМАЙ • ПУБЛИКУЙ • ЗАРАБАТЫВАЙ", "value": "**Твои ролики — твой вклад в развитие GastWorld Media!**", "inline": False},
                ],
                "footer": {"text": "GASTWORLD MEDIA • Удачной работы!"},
            }],
            "allowed_mentions": {"parse": [], "users": [user_id]},
        }
        await discord_request("POST", f"/channels/{channel_id}/messages", payload=welcome)
        return {"ok": True, "user_id": user_id, "username": target_name, "actor_name": actor_name, "secondary_role": secondary_role_status}
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
                    "footer": {"text": "GASTWORLD MEDIA • Заявки на вступление"},
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
                    "title": "❌ Заявка в GastWorld Media отклонена",
                    "description": (
                        "К сожалению, по итогам рассмотрения твоя заявка **не была одобрена**.\n\n"
                        "Спасибо за интерес к команде **GastWorld Media** и за потраченное время. "
                        "Не расстраивайся: это не повод останавливаться. "
                        "Если хочешь узнать подробности решения или получить рекомендации, "
                        "можешь обратиться к администрации проекта.\n\n"
                        "Желаем удачи!"
                    ),
                    "color": 14495300,
                    "footer": {"text": "GASTWORLD MEDIA • Уведомление по заявке"},
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


@app.post("/api/internal/data/shop/purchase")
async def internal_shop_purchase(request: Request):
    require_bot_data_secret(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный запрос покупки.")
    user_id = str(payload.get("user_id", "")).strip()
    item_name = str(payload.get("item", "")).strip()
    request_id = str(payload.get("request_id", "")).strip()
    minecraft_nick = str(payload.get("minecraft_nick", "")).strip()
    if not user_id.isdigit() or not request_id or len(request_id) > 100:
        raise HTTPException(status_code=400, detail="Некорректные данные покупки.")
    if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", minecraft_nick):
        raise HTTPException(status_code=400, detail="Введи корректный ник Minecraft: 3–16 символов, латиница, цифры и _.")
    item = next((entry for entry in SHOP_ITEMS_PANEL if entry["name"] == item_name), None)
    if not item:
        raise HTTPException(status_code=400, detail="Такого товара нет в магазине.")
    price = int(item["price"])
    import sqlite3
    path = bot_database_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="База данных бота не найдена.")
    # Make sure the account is still a member and the personal channel belongs to it.
    member = await discord_request("GET", f"/guilds/{GUILD_ID}/members/{user_id}")
    member_user = member.get("user") or {}
    display_name = str(member.get("nick") or member_user.get("global_name") or member_user.get("username") or user_id)
    order_id = None
    balance_after = None
    notification_sent = False
    try:
        with sqlite3.connect(path, timeout=15) as db:
            db.execute("PRAGMA busy_timeout=15000")
            db.execute("""CREATE TABLE IF NOT EXISTS web_shop_orders (
                request_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                price INTEGER NOT NULL,
                purchase_id INTEGER,
                balance_after INTEGER,
                notification_sent INTEGER NOT NULL DEFAULT 0,
                minecraft_nick TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            existing_columns = {column[1] for column in db.execute("PRAGMA table_info(web_shop_orders)").fetchall()}
            if "minecraft_nick" not in existing_columns:
                db.execute("ALTER TABLE web_shop_orders ADD COLUMN minecraft_nick TEXT NOT NULL DEFAULT ''")
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT user_id,item,price,purchase_id,balance_after,notification_sent,minecraft_nick FROM web_shop_orders WHERE request_id=?",
                (request_id,)
            ).fetchone()
            if prior:
                if int(prior[0]) != int(user_id) or str(prior[1]) != item_name or int(prior[2]) != price or str(prior[6] or "") != minecraft_nick:
                    raise HTTPException(status_code=409, detail="Идентификатор покупки уже использован для другого заказа.")
                order_id, balance_after, notification_sent = prior[3], prior[4], bool(prior[5])
            else:
                row = db.execute(
                    "SELECT balance, personal_channel_id FROM users WHERE user_id=?",
                    (int(user_id),)
                ).fetchone()
                if not row:
                    raise HTTPException(status_code=409, detail="У тебя пока нет личного канала GastWorld. Обратись к администрации.")
                balance, personal_channel_id = int(row[0] or 0), row[1]
                if not personal_channel_id:
                    raise HTTPException(status_code=409, detail="Личный Discord-канал не найден. Обратись к администрации.")
                if balance < price:
                    raise HTTPException(status_code=409, detail=f"Недостаточно баллов. Нужно {price}, у тебя {balance}.")
                channel = await discord_request("GET", f"/channels/{int(personal_channel_id)}")
                if str(channel.get("guild_id", "")) != GUILD_ID:
                    raise HTTPException(status_code=409, detail="Личный канал не принадлежит серверу GastWorld.")
                balance_after = balance - price
                db.execute("UPDATE users SET balance=? WHERE user_id=?", (balance_after, int(user_id)))
                cursor = db.execute(
                    "INSERT INTO purchases (user_id,item,price) VALUES (?,?,?)",
                    (int(user_id), item_name, price)
                )
                order_id = int(cursor.lastrowid)
                db.execute(
                    "INSERT INTO web_shop_orders (request_id,user_id,item,price,purchase_id,balance_after,notification_sent,minecraft_nick) VALUES (?,?,?,?,?,?,0,?)",
                    (request_id, int(user_id), item_name, price, order_id, balance_after, minecraft_nick)
                )
                db.commit()
        if not notification_sent:
            personal_channel_id = int(row[1]) if 'row' in locals() and row else None
            if not personal_channel_id:
                with sqlite3.connect(path, timeout=10) as db:
                    channel_row = db.execute("SELECT personal_channel_id FROM users WHERE user_id=?", (int(user_id),)).fetchone()
                    personal_channel_id = int(channel_row[0]) if channel_row and channel_row[0] else None
            if not personal_channel_id:
                return {"ok": True, "purchase_id": order_id, "balance": balance_after, "notification_sent": False,
                        "message": "Покупка сохранена, но личный канал не найден."}
            embed = {
                "title": "🛍️ Покупка через GastWorld Control Panel",
                "description": f"**{display_name}** совершил покупку на сайте.",
                "color": 0x8B5CF6,
                "fields": [
                    {"name": "Товар", "value": item_name, "inline": True},
                    {"name": "Ник Minecraft", "value": minecraft_nick, "inline": True},
                    {"name": "Цена", "value": f"{price:,} баллов".replace(",", " "), "inline": True},
                    {"name": "Остаток", "value": f"{int(balance_after or 0):,} баллов".replace(",", " "), "inline": True},
                    {"name": "Номер покупки", "value": f"#{order_id}", "inline": True},
                    {"name": "Статус", "value": "Ожидает выдачи администрацией", "inline": False},
                ],
                "footer": {"text": "GASTWORLD • Покупка с сайта"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            try:
                await discord_request("POST", f"/channels/{personal_channel_id}/messages", payload={
                    "content": f"<@{user_id}>",
                    "embeds": [embed],
                    "allowed_mentions": {"parse": [], "users": [user_id]},
                })
                with sqlite3.connect(path, timeout=10) as db:
                    db.execute("UPDATE web_shop_orders SET notification_sent=1 WHERE request_id=?", (request_id,))
                    db.commit()
                notification_sent = True
            except HTTPException:
                # The order and debit are durable; the same request_id can retry the notification safely.
                notification_sent = False
        return {
            "ok": True, "purchase_id": order_id, "item": item_name, "price": price,
            "balance": int(balance_after or 0), "notification_sent": notification_sent,
            "message": "Покупка оформлена." if notification_sent else "Покупка сохранена, но уведомление в личный канал не отправилось.",
        }
    except HTTPException:
        raise
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Не удалось сохранить покупку в базе данных.")


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
            {"name": "Источник", "value": "GastWorld Control Panel", "inline": True},
        ],
        "footer": {"text": "GastWorld • Журнал модерации"},
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
        "<title>GastWorld — TikTok</title><body style='background:#101018;color:#f4f1ff;font:16px Arial;display:grid;place-items:center;min-height:90vh'>"
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
