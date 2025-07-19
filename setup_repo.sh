#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода цветного текста
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

# Проверка наличия SSH
check_ssh() {
    if ! command -v ssh-keygen &> /dev/null; then
        print_error "SSH не установлен. Установите openssh-client:"
        echo "sudo apt update && sudo apt install openssh-client"
        exit 1
    fi
    print_success "SSH найден"
}

# Создание SSH ключа
create_ssh_key() {
    print_status "Создание SSH ключа для GitHub..."
    
    # Проверяем, существует ли уже ключ
    if [ -f ~/.ssh/id_rsa ]; then
        print_warning "SSH ключ уже существует"
        read -p "Перезаписать существующий ключ? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Используем существующий ключ"
            return
        fi
    fi
    
    # Создаем новый ключ
    ssh-keygen -t rsa -b 4096 -C "github-deploy-key" -f ~/.ssh/id_rsa -N ""
    
    if [ $? -eq 0 ]; then
        print_success "SSH ключ создан"
    else
        print_error "Ошибка создания SSH ключа"
        exit 1
    fi
}

# Показ публичного ключа
show_public_key() {
    print_status "Публичный ключ для добавления в GitHub:"
    echo
    echo "=========================================="
    cat ~/.ssh/id_rsa.pub
    echo "=========================================="
    echo
    
    print_warning "Скопируйте этот ключ и добавьте его в настройки репозитория GitHub:"
    echo "1. Перейдите в репозиторий: https://github.com/mixmaster1989/tabletrader"
    echo "2. Settings -> Deploy keys -> Add deploy key"
    echo "3. Вставьте ключ выше"
    echo "4. Поставьте галочку 'Allow write access'"
    echo "5. Нажмите 'Add key'"
    echo
}

# Ожидание подтверждения
wait_for_deployment() {
    while true; do
        read -p "Ключ добавлен в репозиторий? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            break
        fi
        print_warning "Пожалуйста, добавьте ключ в репозиторий и повторите"
    done
}

# Загрузка SSH агента
setup_ssh_agent() {
    print_status "Настройка SSH агента..."
    
    # Запускаем ssh-agent
    eval "$(ssh-agent -s)"
    
    # Добавляем ключ в агент
    ssh-add ~/.ssh/id_rsa
    
    if [ $? -eq 0 ]; then
        print_success "SSH ключ добавлен в агент"
    else
        print_error "Ошибка добавления ключа в SSH агент"
        exit 1
    fi
}

# Проверка подключения к GitHub
test_github_connection() {
    print_status "Проверка подключения к GitHub..."
    
    # Тестируем подключение
    ssh -T git@github.com
    
    if [ $? -eq 1 ]; then
        print_success "Подключение к GitHub успешно"
    else
        print_error "Ошибка подключения к GitHub"
        print_warning "Убедитесь, что ключ правильно добавлен в репозиторий"
        exit 1
    fi
}

# Клонирование репозитория
clone_repository() {
    print_status "Клонирование репозитория..."
    
    # Проверяем, существует ли директория
    if [ -d "tabletrader" ]; then
        print_warning "Директория tabletrader уже существует"
        read -p "Удалить существующую директорию? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf tabletrader
            print_status "Директория удалена"
        else
            print_status "Используем существующую директорию"
            return
        fi
    fi
    
    # Клонируем репозиторий
    git clone git@github.com:mixmaster1989/tabletrader.git
    
    if [ $? -eq 0 ]; then
        print_success "Репозиторий успешно клонирован"
    else
        print_error "Ошибка клонирования репозитория"
        exit 1
    fi
}

# Настройка Git
setup_git() {
    print_status "Настройка Git..."
    
    cd tabletrader
    
    # Настраиваем пользователя Git (если не настроен)
    if [ -z "$(git config --global user.name)" ]; then
        print_warning "Git пользователь не настроен"
        read -p "Введите ваше имя для Git: " git_name
        git config --global user.name "$git_name"
    fi
    
    if [ -z "$(git config --global user.email)" ]; then
        print_warning "Git email не настроен"
        read -p "Введите ваш email для Git: " git_email
        git config --global user.email "$git_email"
    fi
    
    print_success "Git настроен"
}

# Установка зависимостей
install_dependencies() {
    print_status "Проверка зависимостей..."
    
    # Проверяем Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 не установлен"
        print_status "Установите Python3: sudo apt install python3 python3-pip"
        exit 1
    fi
    
    # Проверяем pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 не установлен"
        print_status "Установите pip3: sudo apt install python3-pip"
        exit 1
    fi
    
    # Устанавливаем зависимости
    if [ -f "requirements.txt" ]; then
        print_status "Установка Python зависимостей..."
        pip3 install -r requirements.txt
        
        if [ $? -eq 0 ]; then
            print_success "Зависимости установлены"
        else
            print_warning "Ошибка установки зависимостей"
        fi
    else
        print_warning "Файл requirements.txt не найден"
    fi
}

# Основная функция
main() {
    echo "=========================================="
    echo "Настройка репозитория tabletrader"
    echo "=========================================="
    echo
    
    # Проверяем SSH
    check_ssh
    
    # Создаем SSH ключ
    create_ssh_key
    
    # Показываем публичный ключ
    show_public_key
    
    # Ждем подтверждения
    wait_for_deployment
    
    # Настраиваем SSH агент
    setup_ssh_agent
    
    # Тестируем подключение
    test_github_connection
    
    # Клонируем репозиторий
    clone_repository
    
    # Настраиваем Git
    setup_git
    
    # Устанавливаем зависимости
    install_dependencies
    
    echo
    echo "=========================================="
    print_success "Настройка завершена успешно!"
    echo "=========================================="
    echo
    print_status "Результат:"
    echo "- SSH ключ создан и добавлен в агент"
    echo "- Репозиторий клонирован в директорию 'tabletrader'"
    echo "- Git настроен"
    echo "- Зависимости установлены"
    echo
    print_status "Следующие шаги:"
    echo "1. cd tabletrader"
    echo "2. Создайте .env файл с вашими настройками"
    echo "3. python3 main.py"
    echo
}

# Запуск основной функции
main "$@" 