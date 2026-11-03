# WhiteGrief Control Panel

Веб-панель для управления Discord-ботом WhiteGrief. Фронтенд и backend размещаются отдельно от Bot-Hosting, где работает сам бот.

## Текущая стадия

- Тёмный адаптивный интерфейс.
- Discord OAuth2 вход.
- Проверка, что пользователь состоит на Discord-сервере WhiteGrief.
- Получение ролей пользователя через Discord API на серверной стороне.
- Проверка роли Media через `MEDIA_ROLE_ID`.
- Классы доступа: `owner`, `admin`, `manager`, `media`, `viewer`, `none`.
- Привязка Discord role ID к классу доступа через `ROLE_ACCESS_MAP`.

Управляющие действия (выдача баллов, снятие варнов, одобрение заявок, управление магазином и ботом) пока не подключены. Следующий этап — защищённые API endpoints для каждого действия.

## Запуск локально

Требуется Python 3.11+.

1. Создай Discord Application в Discord Developer Portal.
2. В разделе OAuth2 добавь Redirect URL: `http://localhost:8000/auth/callback`.
3. Убедись, что бот WhiteGrief находится на сервере и может просматривать участников и роли.
4. Скопируй `.env.example` в `dashboard/backend/.env` (или создай этот файл вручную) и заполни настройки. Не загружай настоящий `.env` в GitHub.
5. Установи зависимости и запусти backend:

```bash
cd dashboard/backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Открой `http://localhost:8000`.

## Переменные окружения

- `DISCORD_CLIENT_ID` — Application ID Discord-приложения.
- `DISCORD_CLIENT_SECRET` — OAuth2 Client Secret.
- `DISCORD_BOT_TOKEN` — токен бота, только на backend-хостинге.
- `DISCORD_GUILD_ID` — ID Discord-сервера WhiteGrief.
- `DISCORD_REDIRECT_URI` — полный адрес callback, он должен совпадать с Discord Developer Portal.
- `SESSION_SECRET` — случайный длинный секрет для подписи cookie.
- `COOKIE_HTTPS_ONLY=true` — включать в production за HTTPS.
- `MEDIA_ROLE_ID` — ID роли Media, будет добавлен после того, как владелец пришлёт точный ID.
- `ROLE_ACCESS_MAP` — JSON-словарь role ID → access class.
- `OWNER_USER_IDS` — Discord user IDs владельцев, разделённые запятыми.

Пример конфигурации ролей (замени примеры настоящими ID):

```env
MEDIA_ROLE_ID=123456789012345678
ROLE_ACCESS_MAP={"123456789012345678":"media","234567890123456789":"admin"}
OWNER_USER_IDS=345678901234567890
```

Класс доступа выбирается по самой высокой из ролей пользователя. Пока ID ролей не заданы, участник сервера сможет войти и увидеть свой профиль, но получит класс `none`.

## Важно по безопасности

Не помещай Discord bot token, Client Secret или SESSION_SECRET в HTML/JavaScript. Храни их только в переменных окружения сайта. Используй HTTPS, приватный доступ к переменным окружения и отдельный секрет сессии. В production не включай debug-режим.
