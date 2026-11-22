"""Google Sheets sync for the GastWorld media staff roster.

Credentials are supplied only through the host environment:
  GOOGLE_SERVICE_ACCOUNT_FILE - path to uploaded service-account JSON (recommended)
  GOOGLE_SERVICE_ACCOUNT_JSON - complete service-account JSON (alternative)
  GASTWORLD_SHEETS_ID          - spreadsheet ID
  GASTWORLD_SHEETS_WORKSHEET   - worksheet title (default: Таблица Медия)

Only the lower "Состав Медии" table is touched (rows 16+, columns B:H).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


FIRST_STAFF_ROW = 16
DISCORD_ID_COLUMN = 7  # G
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
    points: int,
    preserve_stats: bool = False,
) -> int:
    """Keep TikTok staff above YouTube staff, preserving the full row on moves."""
    nickname = _cell_text(nickname)
    personal_channel_url = _cell_text(personal_channel_url)
    profile_url = _cell_text(profile_url)
    position = _cell_text(position).upper()
    discord_id = _cell_text(discord_id)
    if not nickname or not personal_channel_url or not profile_url or position not in {"TT", "YT"} or not discord_id:
        raise ValueError("Для записи нужны ник, ссылки, должность TT/YT и Discord ID.")
    if not personal_channel_url.startswith(("https://", "http://")) or not profile_url.startswith(("https://", "http://")):
        raise ValueError("Ссылки должны начинаться с http:// или https://")
    if position == "TT" and "tiktok.com/@" not in profile_url.lower():
        raise ValueError("Для TT нужна ссылка на TikTok-профиль.")
    if position == "YT" and "youtube.com/" not in profile_url.lower():
        raise ValueError("Для YT нужна ссылка на YouTube-профиль.")

    worksheet = _worksheet()
    ids = worksheet.col_values(DISCORD_ID_COLUMN)
    positions = worksheet.col_values(3)
    existing_row = next((r for r in range(FIRST_STAFF_ROW, len(ids) + 1) if _cell_text(ids[r - 1]) == discord_id), None)

    row_was_existing = existing_row is not None
    preserved_row = None
    if existing_row is not None and _cell_text(positions[existing_row - 1]).upper() != position:
        preserved_row = worksheet.get(
            "A{}:H{}".format(existing_row, existing_row), value_render_option="FORMULA"
        )
        preserved_row = (preserved_row[0] if preserved_row else [])[:8]
        preserved_row += [""] * (8 - len(preserved_row))
        worksheet.delete_rows(existing_row)
        ids = worksheet.col_values(DISCORD_ID_COLUMN)
        positions = worksheet.col_values(3)
        existing_row = None

    if existing_row is not None:
        target_row = existing_row
    elif position == "TT":
        first_yt = next((r for r in range(FIRST_STAFF_ROW, len(ids) + 1)
                         if _cell_text(ids[r - 1]) and _cell_text(positions[r - 1]).upper() == "YT"), None)
        if first_yt is not None:
            worksheet.insert_row(
                preserved_row or ["", "", "", "", "", "", "", ""],
                index=first_yt,
                value_input_option="USER_ENTERED" if preserved_row else "RAW",
            )
            target_row = first_yt
        else:
            target_row = max(FIRST_STAFF_ROW, len(ids) + 1)
            while target_row <= len(ids) and _cell_text(ids[target_row - 1]):
                target_row += 1
            if preserved_row:
                worksheet.insert_row(preserved_row, index=target_row, value_input_option="USER_ENTERED")
    else:
        target_row = max(FIRST_STAFF_ROW, len(ids) + 1)
        while target_row <= len(ids) and _cell_text(ids[target_row - 1]):
            target_row += 1
        if preserved_row:
            worksheet.insert_row(preserved_row, index=target_row, value_input_option="USER_ENTERED")

    safe_name = nickname.replace('"', '""')
    safe_url = personal_channel_url.replace('"', '""')
    nickname_formula = f'=HYPERLINK("{safe_url}","{safe_name}")'
    if preserve_stats and row_was_existing:
        worksheet.update(range_name=f"B{target_row}:D{target_row}",
                         values=[[nickname_formula, position, profile_url]],
                         value_input_option="USER_ENTERED")
        worksheet.update(range_name=f"G{target_row}",
                         values=[[discord_id]],
                         value_input_option="USER_ENTERED")
    else:
        worksheet.update(range_name=f"B{target_row}:E{target_row}",
                         values=[[nickname_formula, position, profile_url, int(warns)]],
                         value_input_option="USER_ENTERED")
        worksheet.update(range_name=f"G{target_row}:H{target_row}",
                         values=[[discord_id, int(points)]],
                         value_input_option="USER_ENTERED")
    return target_row


def remove_staff_row(discord_id: int | str) -> bool:
    worksheet = _worksheet()
    wanted = _cell_text(discord_id)
    ids = worksheet.col_values(DISCORD_ID_COLUMN)
    for row_number in range(FIRST_STAFF_ROW, len(ids) + 1):
        if _cell_text(ids[row_number - 1]) == wanted:
            worksheet.delete_rows(row_number)
            return True
    return False


def clear_client_cache() -> None:
    """Drop cached worksheet/client after changing credentials or spreadsheet settings."""
    _worksheet.cache_clear()
