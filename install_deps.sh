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

# Проверка Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 не установлен"
        print_status "Установите Python3:"
        echo "sudo apt update && sudo apt install python3 python3-pip"
        exit 1
    fi
    print_success "Python3 найден: $(python3 --version)"
}

# Проверка pip
check_pip() {
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 не установлен"
        print_status "Установите pip3:"
        echo "sudo apt install python3-pip"
        exit 1
    fi
    print_success "pip3 найден: $(pip3 --version)"
}

# Обновление pip
update_pip() {
    print_status "Обновление pip..."
    pip3 install --upgrade pip
    print_success "pip обновлен"
}

# Установка зависимостей
install_dependencies() {
    print_status "Установка зависимостей..."
    
    # Удаляем старые установки Google модулей
    print_status "Очистка старых Google модулей..."
    pip3 uninstall -y google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client google-oauth2-tool 2>/dev/null || true
    
    # Устанавливаем зависимости по порядку
    print_status "Установка основных зависимостей..."
    pip3 install python-dotenv==1.0.0
    pip3 install requests==2.31.0
    
    print_status "Установка Bybit API..."
    pip3 install pybit==5.7.0
    
    print_status "Установка Google API модулей..."
    pip3 install google-auth==2.23.4
    pip3 install google-auth-oauthlib==1.1.0
    pip3 install google-auth-httplib2==0.1.1
    pip3 install google-api-python-client==2.108.0
    
    print_status "Установка утилит..."
    pip3 install colorama==0.4.6
    
    print_success "Все зависимости установлены"
}

# Проверка установки
verify_installation() {
    print_status "Проверка установки модулей..."
    
    python3 -c "import google.oauth2.service_account; print('✓ google.oauth2.service_account')" 2>/dev/null && print_success "Google OAuth2 установлен" || print_error "Google OAuth2 не установлен"
    
    python3 -c "import pybit; print('✓ pybit')" 2>/dev/null && print_success "PyBit установлен" || print_error "PyBit не установлен"
    
    python3 -c "import dotenv; print('✓ python-dotenv')" 2>/dev/null && print_success "python-dotenv установлен" || print_error "python-dotenv не установлен"
    
    python3 -c "import requests; print('✓ requests')" 2>/dev/null && print_success "requests установлен" || print_error "requests не установлен"
}

# Основная функция
main() {
    echo "=========================================="
    echo "Установка зависимостей TableTrader Bot"
    echo "=========================================="
    echo
    
    check_python
    check_pip
    update_pip
    install_dependencies
    verify_installation
    
    echo
    echo "=========================================="
    print_success "Установка завершена!"
    echo "=========================================="
    echo
    print_status "Теперь можно запускать бота:"
    echo "python3 main.py"
    echo "или"
    echo "./pm2_commands.sh start"
    echo
}

# Запуск основной функции
main "$@" 