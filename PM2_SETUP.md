# Настройка PM2 для TableTrader Bot

## Установка PM2

```bash
# Установка Node.js (если не установлен)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Установка PM2
sudo npm install -g pm2
```

## Быстрый старт

```bash
# Сделать скрипт исполняемым
chmod +x pm2_commands.sh

# Запустить бота
./pm2_commands.sh start

# Просмотр статуса
./pm2_commands.sh status

# Просмотр логов
./pm2_commands.sh logs
```

## Основные команды PM2

### Запуск бота
```bash
# Через скрипт
./pm2_commands.sh start

# Или напрямую
pm2 start ecosystem.config.js
```

### Управление процессом
```bash
# Остановка
./pm2_commands.sh stop
# или
pm2 stop tabletrader-bot

# Перезапуск
./pm2_commands.sh restart
# или
pm2 restart tabletrader-bot

# Удаление из PM2
./pm2_commands.sh delete
# или
pm2 delete tabletrader-bot
```

### Мониторинг
```bash
# Статус процессов
./pm2_commands.sh status
# или
pm2 status

# Просмотр логов
./pm2_commands.sh logs
# или
pm2 logs tabletrader-bot

# Интерактивный мониторинг
./pm2_commands.sh monit
# или
pm2 monit
```

### Автозапуск при загрузке системы
```bash
# Настройка автозапуска
./pm2_commands.sh startup

# Сохранение текущей конфигурации
./pm2_commands.sh save
```

## Конфигурация PM2

Файл `ecosystem.config.js` содержит настройки:

- **name**: `tabletrader-bot` - имя процесса
- **script**: `main.py` - основной файл бота
- **interpreter**: `python3` - интерпретатор Python
- **autorestart**: `true` - автоматический перезапуск при сбоях
- **max_memory_restart**: `1G` - перезапуск при превышении памяти
- **watch**: отслеживание изменений файлов
- **logs**: сохранение логов в директорию `logs/`

## Логи

Логи сохраняются в директории `logs/`:
- `out.log` - стандартный вывод
- `err.log` - ошибки
- `combined.log` - все логи

## Полезные команды

```bash
# Просмотр всех процессов PM2
pm2 list

# Просмотр информации о процессе
pm2 show tabletrader-bot

# Очистка логов
pm2 flush

# Перезагрузка всех процессов
pm2 reload all

# Остановка всех процессов
pm2 stop all

# Удаление всех процессов
pm2 delete all
```

## Решение проблем

### Бот не запускается
```bash
# Проверка логов
pm2 logs tabletrader-bot

# Проверка статуса
pm2 status

# Перезапуск с очисткой
pm2 delete tabletrader-bot
pm2 start ecosystem.config.js
```

### Проблемы с зависимостями
```bash
# Установка зависимостей
pip3 install -r requirements.txt

# Проверка Python
python3 --version
```

### Проблемы с правами доступа
```bash
# Создание директории логов
mkdir -p logs

# Установка прав
chmod 755 logs/
```

## Автозапуск при перезагрузке сервера

```bash
# Настройка автозапуска
pm2 startup

# Сохранение текущих процессов
pm2 save

# Проверка автозапуска
pm2 resurrect
```

## Мониторинг производительности

```bash
# Интерактивный мониторинг
pm2 monit

# Просмотр статистики
pm2 show tabletrader-bot

# Просмотр использования ресурсов
pm2 status
```

## Безопасность

- Убедитесь, что файл `.env` не отслеживается PM2
- Регулярно проверяйте логи на подозрительную активность
- Используйте отдельного пользователя для запуска бота
- Ограничьте доступ к директории с ботом 