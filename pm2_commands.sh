#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Создание директории для логов
create_logs_dir() {
    if [ ! -d "logs" ]; then
        mkdir -p logs
        print_success "Создана директория logs"
    fi
}

# Проверка установки PM2
check_pm2() {
    if ! command -v pm2 &> /dev/null; then
        print_error "PM2 не установлен"
        print_status "Установите PM2:"
        echo "npm install -g pm2"
        exit 1
    fi
    print_success "PM2 найден"
}

# Проверка Python зависимостей
check_python_deps() {
    if [ ! -f "requirements.txt" ]; then
        print_error "Файл requirements.txt не найден"
        exit 1
    fi
    
    print_status "Проверка Python зависимостей..."
    pip3 install -r requirements.txt
}

# Основные команды PM2
case "$1" in
    "start")
        print_status "Запуск торгового бота через PM2..."
        check_pm2
        create_logs_dir
        check_python_deps
        pm2 start ecosystem.config.js
        print_success "Бот запущен!"
        echo
        print_status "Полезные команды:"
        echo "pm2 status          - статус процессов"
        echo "pm2 logs tabletrader-bot - просмотр логов"
        echo "pm2 restart tabletrader-bot - перезапуск"
        echo "pm2 stop tabletrader-bot - остановка"
        ;;
    "stop")
        print_status "Остановка торгового бота..."
        pm2 stop tabletrader-bot
        print_success "Бот остановлен!"
        ;;
    "restart")
        print_status "Перезапуск торгового бота..."
        pm2 restart tabletrader-bot
        print_success "Бот перезапущен!"
        ;;
    "status")
        print_status "Статус процессов PM2:"
        pm2 status
        ;;
    "logs")
        print_status "Просмотр логов бота:"
        pm2 logs tabletrader-bot
        ;;
    "monit")
        print_status "Мониторинг процессов PM2:"
        pm2 monit
        ;;
    "delete")
        print_status "Удаление процесса из PM2..."
        pm2 delete tabletrader-bot
        print_success "Процесс удален из PM2!"
        ;;
    "save")
        print_status "Сохранение конфигурации PM2..."
        pm2 save
        print_success "Конфигурация сохранена!"
        ;;
    "startup")
        print_status "Настройка автозапуска PM2 при загрузке системы..."
        pm2 startup
        pm2 save
        print_success "Автозапуск настроен!"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|monit|delete|save|startup}"
        echo
        echo "Команды:"
        echo "  start    - запустить бота"
        echo "  stop     - остановить бота"
        echo "  restart  - перезапустить бота"
        echo "  status   - показать статус"
        echo "  logs     - показать логи"
        echo "  monit    - мониторинг процессов"
        echo "  delete   - удалить процесс из PM2"
        echo "  save     - сохранить конфигурацию"
        echo "  startup  - настроить автозапуск"
        echo
        print_status "Примеры:"
        echo "  $0 start     # Запустить бота"
        echo "  $0 logs      # Просмотр логов"
        echo "  $0 status    # Статус процессов"
        ;;
esac 