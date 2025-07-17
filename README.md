# Google Signals Bot 🤖

Автоматический торговый бот для выполнения сигналов из Google таблиц на Bybit.

## 🚀 Возможности

- 📊 Чтение торговых сигналов из Google таблиц
- 💰 Автоматическое открытие позиций на Bybit
- 🎯 Автоматическая установка Take Profit и Stop Loss
- 📱 Уведомления в Telegram
- 🔄 Мониторинг новых сигналов в реальном времени
- 🛡️ Защита от дублирования сигналов
- ⚙️ Гибкая настройка параметров

## 📋 Структура Google таблицы

Бот ожидает следующую структуру таблицы:

| Колонка | Описание | Пример |
|---------|----------|--------|
| A | Символ монеты | BTCUSDT |
| B | Цена входа | 50000 |
| C | Take Profit | 52000 |
| D | Stop Loss | 48000 |
| E | Направление | LONG/SHORT |

## ⚙️ Установка

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd google_signals_bot
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте Google Sheets API:**
   - Создайте проект в Google Cloud Console
   - Включите Google Sheets API
   - Создайте Service Account
   - Скачайте credentials.json
   - Разрешите доступ к таблице для service account email

4. **Создайте .env файл:**
```env
# Bybit API
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret
BYBIT_TESTNET=false

# Google Sheets
GOOGLE_SHEETS_ID=your_google_sheets_id
GOOGLE_CREDENTIALS_FILE=credentials.json

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Настройки торговли
DEFAULT_LEVERAGE=20
DEFAULT_POSITION_SIZE=0.01
MAX_POSITIONS=3

# Настройки мониторинга
CHECK_INTERVAL=30
PRICE_DEVIATION=0.5

# Логирование
LOG_LEVEL=INFO
LOG_FILE=google_signals_bot.log
```

## 🚀 Запуск

```bash
python main.py
```

## 📊 Мониторинг

Бот отправляет уведомления в Telegram:
- 🚀 При запуске/остановке
- 📊 При открытии новых позиций
- ❌ При ошибках
- 📈 Статус каждые 10 циклов

## ⚠️ Важные моменты

1. **Безопасность:** Храните API ключи в безопасном месте
2. **Тестирование:** Сначала протестируйте на testnet
3. **Мониторинг:** Следите за логами и уведомлениями
4. **Риск-менеджмент:** Настройте разумные размеры позиций

## 🔧 Настройка

### Параметры торговли:
- `DEFAULT_LEVERAGE` - плечо по умолчанию
- `DEFAULT_POSITION_SIZE` - размер позиции
- `MAX_POSITIONS` - максимальное количество открытых позиций
- `PRICE_DEVIATION` - допустимое отклонение цены от сигнала (%)

### Параметры мониторинга:
- `CHECK_INTERVAL` - интервал проверки новых сигналов (секунды)

## 📝 Логи

Логи сохраняются в файл `google_signals_bot.log` и выводятся в консоль.

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи
2. Убедитесь в правильности настроек
3. Проверьте подключение к интернету
4. Убедитесь в корректности структуры Google таблицы

## ⚖️ Отказ от ответственности

Этот бот предназначен для образовательных целей. Торговля криптовалютами связана с высокими рисками. Используйте на свой страх и риск. 