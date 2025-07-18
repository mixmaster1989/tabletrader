# Инструкции по восстановлению файлов авторизации

## Потерянные файлы:
1. `.env` - файл с переменными окружения
2. `credentials.json` - файл с учетными данными Google API
3. `token.pickle` - файл с токеном авторизации Google

## Восстановление:

### 1. Создание файла .env
```bash
# Скопируйте example.env в .env
cp example.env .env
```

Затем отредактируйте `.env` файл и заполните своими данными:
- `BYBIT_API_KEY` - ваш API ключ Bybit
- `BYBIT_API_SECRET` - ваш секретный ключ Bybit
- `GOOGLE_SHEETS_ID` - ID вашей Google таблицы
- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота
- `TELEGRAM_CHAT_ID` - ID вашего чата

### 2. Восстановление credentials.json
Вам нужно заново создать файл `credentials.json`:

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Выберите ваш проект
3. Перейдите в "APIs & Services" > "Credentials"
4. Создайте новый "Service Account" или используйте существующий
5. Скачайте JSON файл с ключами
6. Переименуйте его в `credentials.json` и поместите в корневую папку проекта

### 3. Восстановление token.pickle
Файл `token.pickle` будет создан автоматически при первом запуске программы с правильными `credentials.json`.

## Проверка восстановления:
```bash
python test_google_setup.py
```

## Важные замечания:
- Файл `.env` содержит секретные данные и не должен попадать в git
- Файл `credentials.json` также содержит секретные данные
- Файл `token.pickle` создается автоматически и может быть пересоздан 