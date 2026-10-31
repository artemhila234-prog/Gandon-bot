# Исправление сохранения заявок Discord-бота

В исходном коде `pending_apps` и `pending_points` — обычные словари Python. Они очищаются при каждом перезапуске процесса. Ниже — точечные изменения для сохранения заявок в существующей SQLite-базе `bot_data.db`.

> Перед заменой сделай копию `main.py` и `bot_data.db`. Не удаляй старую базу.

## 1. Добавь импорт

В начало файла рядом с `import sqlite3` добавь:

```python
import json
```

## 2. Добавь таблицу заявок

Сразу после создания таблицы `purchases` и до `conn.commit()` добавь:

```python
cursor.execute("""
CREATE TABLE IF NOT EXISTS pending_requests (
    request_type TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (request_type, user_id)
)
""")
```

После этого оставь существующий `conn.commit()`.

## 3. Добавь функции сохранения

После `get_msk_time_str()` (или рядом с остальными функциями базы данных) добавь:

```python
def save_pending_request(request_type, user_id, data):
    """Сохраняет или обновляет ожидающую заявку пользователя."""
    cursor.execute(
        """
        INSERT INTO pending_requests (request_type, user_id, data)
        VALUES (?, ?, ?)
        ON CONFLICT(request_type, user_id)
        DO UPDATE SET data = excluded.data,
                      created_at = CURRENT_TIMESTAMP
        """,
        (request_type, user_id, json.dumps(data, ensure_ascii=False))
    )
    conn.commit()


def load_pending_requests(request_type):
    """Загружает ожидающие заявки указанного типа."""
    cursor.execute(
        "SELECT user_id, data FROM pending_requests WHERE request_type = ?",
        (request_type,)
    )
    result = {}
    for user_id, data in cursor.fetchall():
        try:
            result[user_id] = json.loads(data)
        except (TypeError, json.JSONDecodeError):
            print(f"⚠️ Не удалось прочитать заявку {request_type} пользователя {user_id}")
    return result


def delete_pending_request(request_type, user_id):
    """Удаляет заявку после успешной обработки."""
    cursor.execute(
        "DELETE FROM pending_requests WHERE request_type = ? AND user_id = ?",
        (request_type, user_id)
    )
    conn.commit()


def complete_points_request(user_id, points):
    """
    Начисляет баллы и удаляет заявку одной транзакцией.
    Это защищает от повторного начисления, если процесс упадёт
    между начислением и удалением заявки.
    Возвращает новый баланс или None, если заявка уже обработана.
    """
    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            SELECT 1 FROM pending_requests
            WHERE request_type = 'points' AND user_id = ?
            """,
            (user_id,)
        )
        if cursor.fetchone() is None:
            conn.rollback()
            return None

        cursor.execute(
            """
            INSERT INTO users (user_id, balance, warns, personal_channel_id)
            VALUES (?, ?, 0, NULL)
            ON CONFLICT(user_id)
            DO UPDATE SET balance = balance + excluded.balance
            """,
            (user_id, points)
        )

        cursor.execute(
            """
            DELETE FROM pending_requests
            WHERE request_type = 'points' AND user_id = ?
            """,
            (user_id,)
        )

        cursor.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user_id,)
        )
        new_balance = cursor.fetchone()[0]
        conn.commit()
        return new_balance

    except Exception:
        conn.rollback()
        raise
```

## 4. Замени создание словарей

Было:

```python
pending_apps = {}
pending_points = {}
```

Станет:

```python
# При запуске восстанавливаем заявки из SQLite.
pending_apps = load_pending_requests("join")
pending_points = load_pending_requests("points")

print(
    f"📦 Загружено заявок: вступление — {len(pending_apps)}, "
    f"начисление баллов — {len(pending_points)}"
)
```

Важно: таблица и функции из шагов 2–3 должны быть объявлены выше этого блока.

## 5. Сохраняй заявки на баллы

В `on_message`, в блоке `ЗАЯВКА НА БАЛЛЫ`, замени:

```python
pending_points[message.author.id] = {
    'nick': nick,
    'points': points,
    'link': link
}
```

на:

```python
request_data = {
    'nick': nick,
    'points': points,
    'link': link
}
pending_points[message.author.id] = request_data
save_pending_request("points", message.author.id, request_data)
```

## 6. Сохраняй заявки на вступление

В `on_message`, в блоке `ЗАЯВКИ НА ВСТУПЛЕНИЕ`, замени:

```python
pending_apps[message.author.id] = {
    'nick': nick,
    'position': position,
    'age': age
}
```

на:

```python
request_data = {
    'nick': nick,
    'position': position,
    'age': age
}
pending_apps[message.author.id] = request_data
save_pending_request("join", message.author.id, request_data)
```

## 7. Измени обработчик `!принят`

В обработчике `accept(ctx)` найди:

```python
del pending_apps[member.id]
```

Удали эту строку. Заявку нельзя удалять до успешного завершения принятия.

В начале обработчика есть проверка, не поставлена ли уже реакция `✅`, а сама реакция добавляется до создания канала. Чтобы сбой не оставлял заявку заблокированной, перенеси эти две строки:

```python
await original_msg.clear_reaction('🕐')
await original_msg.add_reaction('✅')
```

из ранней части обработчика в конец успешного блока — после создания личного канала и отправки приветственного сообщения.

Сразу после них добавь:

```python
delete_pending_request("join", member.id)
pending_apps.pop(member.id, None)
```

Если обработчик завершился ошибкой до этого места, запись в SQLite останется. Так её можно будет обработать повторно.

## 8. Измени обработчик `!принято`

В обработчике `accept_points(ctx)` найди:

```python
points = app_data['points']
del pending_points[member.id]
```

Замени на:

```python
points = app_data['points']
```

Сразу после получения `points` выполни атомарное начисление:

```python
points = app_data['points']

new_balance = complete_points_request(member.id, points)
if new_balance is None:
    await ctx.send(
        "⚠️ Эта заявка уже обработана или больше не найдена.",
        delete_after=10
    )
    return

pending_points.pop(member.id, None)
```

Этот блок должен идти **до** `await original_msg.add_reaction('✅')`. Затем оставь очистку реакции `🕐` и добавление `✅` на месте.

Удали старое начисление:

```python
update_balance(member.id, points)
new_balance = get_user_data(member.id)['balance']
```

Не вызывай `update_balance` повторно для этой заявки: баллы уже начислены внутри `complete_points_request`. Транзакция одновременно начисляет баллы и удаляет заявку, поэтому повторная команда не начислит их второй раз.

## 9. Важное условие для Bot-Hosting

SQLite сохранит данные между перезапусками только в том случае, если файл `bot_data.db` находится на постоянном диске/persistent storage хостинга.

- Не клади базу во временную папку, которая очищается при перезапуске или пересоздании контейнера.
- Не удаляй `bot_data.db` при обновлении бота.
- Если хостинг запускает бота из другой рабочей папки, укажи постоянный путь к базе и используй его при каждом запуске.

## Что после исправления будет сохраняться

| Данные | Где хранятся |
|---|---|
| Баланс и предупреждения | `users` |
| ID личного канала | `users` |
| Отчёты и статус одобрения | `reports` |
| История покупок | `purchases` |
| Ожидающие заявки на вступление | `pending_requests` (`join`) |
| Ожидающие заявки на баллы | `pending_requests` (`points`) |

Старые записи в `users`, `reports` и `purchases` не удаляются. Новая таблица создаётся автоматически при запуске.

## Проверка после внесения изменений

1. Запусти бота и отправь тестовую заявку на вступление.
2. Перезапусти процесс бота.
3. Выполни `!принят` ответом на исходную заявку — данные должны восстановиться.
4. Повтори проверку с заявкой на баллы и `!принято`.
5. Убедись, что баллы начислились ровно один раз.

**Ограничение:** это точечный патч для сохранения двух видов ожидающих заявок. Он не переписывает остальные части бота и не исправляет другие найденные ранее проблемы.
