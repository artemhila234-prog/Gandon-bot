"""Google Sheets sync for the GastWorld media staff roster.

Credentials are supplied only through the host environment:
  GOOGLE_SERVICE_ACCOUNT_FILE - path to uploaded service-account JSON (recommended)
  GOOGLE_SERVICE_ACCOUNT_JSON - complete service-account JSON (alternative)
  GASTWORLD_SHEETS_ID          - spreadsheet ID
  GASTWORLD_SHEETS_WORKSHEET   - worksheet title (default: Таблица Медия)

Only the lower "Состав Медии" table is touched (rows 16+, columns B:I).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


FIRST_STAFF_ROW = 16
DISCORD_ID_COLUMN = 9  # I (technical ID; G displays Discord username)
STAFF_WORKSHEET = "Таблица Медия"


class SheetsConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _worksheet():
    try:
        import gspread
    except ImportError as exc:
        raise SheetsConfigError(
            "Не установлен gspread. Установи зависимости из aaaa/requirements.txt."
        ) from exc

    raw_credentials = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    credentials_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    spreadsheet_id = os.getenv("GASTWORLD_SHEETS_ID", "").strip()
    worksheet_name = os.getenv("GASTWORLD_SHEETS_WORKSHEET", STAFF_WORKSHEET).strip()

    if not raw_credentials and not credentials_file:
        raise SheetsConfigError(
            "Задай GOOGLE_SERVICE_ACCOUNT_FILE (путь к JSON-файлу) "
            "или GOOGLE_SERVICE_ACCOUNT_JSON."
        )
    if not spreadsheet_id:
        raise SheetsConfigError("Не задан GASTWORLD_SHEETS_ID.")

    try:
        if credentials_file:
            client = gspread.service_account(filename=credentials_file)
        else:
            credentials_info = json.loads(raw_credentials)
            client = gspread.service_account_from_dict(credentials_info)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        raise SheetsConfigError(
            "Не удалось прочитать JSON-ключ Google Service Account."
        ) from exc
    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        return spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound as exc:
        available = ", ".join(ws.title for ws in spreadsheet.worksheets()) or "(нет доступных листов)"
        raise SheetsConfigError(
            f'Лист Google Sheets "{worksheet_name}" не найден в указанной таблице. '
            f'Доступные листы: {available}. Проверь GASTWORLD_SHEETS_ID '
            f'и точное значение GASTWORLD_SHEETS_WORKSHEET.'
        ) from exc


def _cell_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def sync_staff_row(
    *,
    nickname: str,
    personal_channel_url: str,
    profile_url: str,
    position: str,
    warns: int,
    discord_id: int | str,
    discord_username: str,
    points: int,
    preserve_stats: bool = False,
) -> int:
    """Keep TikTok staff above YouTube staff and preserve existing statistics."""
    nickname = _cell_text(nickname)
    personal_channel_url = _cell_text(personal_channel_url)
    profile_url = _cell_text(profile_url)
    position = _cell_text(position)
    discord_id = _cell_text(discord_id)
    discord_username = _cell_text(discord_username)
    allowed_positions = {"YouTube", "YouTube+", "TikTok", "TikTok+", "Media Adm"}
    if not nickname or not personal_channel_url or not profile_url or position not in allowed_positions or not discord_id or not discord_username:
        raise ValueError("Для записи нужны ник, ссылки, одна из должностей YouTube/YouTube+/TikTok/TikTok+/Media Adm, Discord username и ID.")
    if not personal_channel_url.startswith(("https://", "http://")) or not profile_url.startswith(("https://", "http://")):
        raise ValueError("Ссылки должны начинаться с http:// или https://")
    profile_lower = profile_url.lower()
    is_tiktok_profile = "tiktok.com/@" in profile_lower
    is_youtube_profile = any(host in profile_lower for host in ("youtube.com/", "youtu.be/"))
    if position in {"TikTok", "TikTok+"} and not is_tiktok_profile:
        raise ValueError("Для должности TikTok/TikTok+ нужна ссылка на TikTok-профиль.")
    if position in {"YouTube", "YouTube+"} and not is_youtube_profile:
        raise ValueError("Для должности YouTube/YouTube+ нужна ссылка на YouTube-профиль.")
    if position == "Media Adm" and not (is_tiktok_profile or is_youtube_profile):
        raise ValueError("Для Media Adm нужна ссылка на TikTok или YouTube-профиль.")
    platform_group = "TT" if is_tiktok_profile else "YT"

    worksheet = _worksheet()
    ids = worksheet.col_values(DISCORD_ID_COLUMN)
    legacy_ids = worksheet.col_values(7)  # Older rows stored Discord ID in G
    positions = worksheet.col_values(3)
    last_row = max(len(ids), len(legacy_ids), len(positions))
    existing_row = next(
        (r for r in range(FIRST_STAFF_ROW, last_row + 1)
         if (r <= len(ids) and _cell_text(ids[r - 1]) == discord_id)
         or (r <= len(legacy_ids) and _cell_text(legacy_ids[r - 1]) == discord_id)),
        None,
    )

    row_was_existing = existing_row is not None
    preserved_row = None
    if existing_row is not None and _cell_text(positions[existing_row - 1]) != position:
        preserved_row = worksheet.get(
            "A{}:I{}".format(existing_row, existing_row), value_render_option="FORMULA"
        )
        preserved_row = (preserved_row[0] if preserved_row else [])[:9]
        preserved_row += [""] * (9 - len(preserved_row))
        worksheet.delete_rows(existing_row)
        ids = worksheet.col_values(DISCORD_ID_COLUMN)
        legacy_ids = worksheet.col_values(7)
        positions = worksheet.col_values(3)
        last_row = max(len(ids), len(legacy_ids), len(positions))
        existing_row = None

    if existing_row is not None:
        target_row = existing_row
    elif platform_group == "TT":
        first_yt = next(
            (r for r in range(FIRST_STAFF_ROW, last_row + 1)
             if ((r <= len(ids) and _cell_text(ids[r - 1]))
                 or (r <= len(legacy_ids) and _cell_text(legacy_ids[r - 1])))
             and r <= len(positions)
             and _cell_text(positions[r - 1]) in {"YouTube", "YouTube+"}),
            None,
        )
        if first_yt is not None:
            worksheet.insert_row(
                preserved_row or ["", "", "", "", "", "", "", "", ""],
                index=first_yt,
                value_input_option="USER_ENTERED" if preserved_row else "RAW",
            )
            target_row = first_yt
        else:
            target_row = max(FIRST_STAFF_ROW, last_row + 1)
            if preserved_row:
                worksheet.insert_row(preserved_row, index=target_row, value_input_option="USER_ENTERED")
    else:
        target_row = max(FIRST_STAFF_ROW, last_row + 1)
        if preserved_row:
            worksheet.insert_row(preserved_row, index=target_row, value_input_option="USER_ENTERED")

    safe_name = nickname.replace('"', '""')
    safe_channel_url = personal_channel_url.replace('"', '""')
    safe_profile_url = profile_url.replace('"', '""')
    nickname_formula = f'=HYPERLINK("{safe_channel_url}";"{safe_name}")'
    profile_formula = f'=HYPERLINK("{safe_profile_url}";"КАНАЛ")'
    if preserve_stats and row_was_existing:
        worksheet.update(
            range_name=f"B{target_row}:D{target_row}",
            values=[[nickname_formula, position, profile_formula]],
            value_input_option="USER_ENTERED",
        )
        worksheet.update(
            range_name=f"F{target_row}:G{target_row}",
            values=[["Нету", discord_username]],
            value_input_option="USER_ENTERED",
        )
        worksheet.update(
            range_name=f"I{target_row}",
            values=[[discord_id]],
            value_input_option="USER_ENTERED",
        )
    else:
        worksheet.update(
            range_name=f"B{target_row}:F{target_row}",
            values=[[nickname_formula, position, profile_formula, f"{min(max(int(warns), 0), 3)}/3", "Нету"]],
            value_input_option="USER_ENTERED",
        )
        worksheet.update(
            range_name=f"G{target_row}:I{target_row}",
            values=[[discord_username, int(points), discord_id]],
            value_input_option="USER_ENTERED",
        )
    # Единое оформление строки состава: центрирование, жирный шрифт, 14 pt.
    worksheet.format(
        f"B{target_row}:I{target_row}",
        {
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
            "textFormat": {
                "bold": True,
                "fontSize": 14,
                "foregroundColor": {"red": 0, "green": 0, "blue": 0},
                "fontFamily": "Montserrat",
            },
        },
    )
    return target_row

def remove_staff_row(discord_id: int | str) -> bool:
    """Remove a staff row by technical Discord ID (I), with legacy G fallback."""
    worksheet = _worksheet()
    wanted = _cell_text(discord_id)
    ids = worksheet.col_values(DISCORD_ID_COLUMN)
    legacy_ids = worksheet.col_values(7)  # Older sheet layout stored the ID in G.
    last_row = max(len(ids), len(legacy_ids))
    for row_number in range(FIRST_STAFF_ROW, last_row + 1):
        current_id = _cell_text(ids[row_number - 1]) if row_number <= len(ids) else ""
        legacy_id = _cell_text(legacy_ids[row_number - 1]) if row_number <= len(legacy_ids) else ""
        if current_id == wanted or legacy_id == wanted:
            worksheet.delete_rows(row_number)
            return True
    return False


def clear_client_cache() -> None:
    """Drop cached worksheet/client after changing credentials or spreadsheet settings."""
    _worksheet.cache_clear()
