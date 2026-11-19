"""Google Sheets sync for the GastWorld media staff roster.

Credentials are supplied only through the host environment:
  GOOGLE_SERVICE_ACCOUNT_JSON  - complete service-account JSON (never commit it)
  GASTWORLD_SHEETS_ID          - spreadsheet ID
  GASTWORLD_SHEETS_WORKSHEET   - worksheet title (default: Таблица КП)

Only the lower "Состав Медии" table is touched (rows 16+, columns B:H).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


FIRST_STAFF_ROW = 16
DISCORD_ID_COLUMN = 7  # G
STAFF_WORKSHEET = "Таблица КП"


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
    spreadsheet_id = os.getenv("GASTWORLD_SHEETS_ID", "").strip()
    worksheet_name = os.getenv("GASTWORLD_SHEETS_WORKSHEET", STAFF_WORKSHEET).strip()

    if not raw_credentials or not spreadsheet_id:
        raise SheetsConfigError(
            "Не заданы GOOGLE_SERVICE_ACCOUNT_JSON и/или GASTWORLD_SHEETS_ID."
        )

    try:
        credentials_info = json.loads(raw_credentials)
    except json.JSONDecodeError as exc:
        raise SheetsConfigError(
            "GOOGLE_SERVICE_ACCOUNT_JSON должен содержать корректный JSON service account."
        ) from exc

    client = gspread.service_account_from_dict(credentials_info)
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(worksheet_name)


def _cell_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def sync_staff_row(
    *,
    nickname: str,
    channel_url: str,
    position: str,
    warns: int,
    discord_id: int | str,
    points: int,
) -> int:
    """Insert/update one staff row and return its sheet row number.

    Layout: B nickname (hyperlink), C position, D channel URL,
    E warnings, F leave (untouched/blank), G Discord ID, H points.
    """
    nickname = _cell_text(nickname)
    channel_url = _cell_text(channel_url)
    position = _cell_text(position)
    discord_id = _cell_text(discord_id)

    if not nickname or not channel_url or not position or not discord_id:
        raise ValueError("Для записи нужны nickname, channel_url, position и discord_id.")
    if not channel_url.startswith(("https://", "http://")):
        raise ValueError("Ссылка на канал должна начинаться с http:// или https://")

    worksheet = _worksheet()
    discord_values = worksheet.col_values(DISCORD_ID_COLUMN)
    target_row = None

    for row_number in range(FIRST_STAFF_ROW, len(discord_values) + 1):
        if _cell_text(discord_values[row_number - 1]) == discord_id:
            target_row = row_number
            break

    if target_row is None:
        target_row = FIRST_STAFF_ROW
        while target_row <= len(discord_values) and _cell_text(discord_values[target_row - 1]):
            target_row += 1

    safe_name = nickname.replace('"', '""')
    safe_url = channel_url.replace('"', '""')
    nickname_formula = f'=HYPERLINK("{safe_url}","{safe_name}")'

    # B:H. F (Отпуск) stays empty until that feature is defined.
    worksheet.update(
        range_name=f"B{target_row}:H{target_row}",
        values=[[
            nickname_formula,
            position,
            channel_url,
            int(warns),
            "",
            discord_id,
            int(points),
        ]],
        value_input_option="USER_ENTERED",
    )
    return target_row


def clear_client_cache() -> None:
    """Drop cached worksheet/client after changing credentials or spreadsheet settings."""
    _worksheet.cache_clear()
