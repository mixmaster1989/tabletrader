#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для переключения между тестовым и реальным режимом торговли
"""

import os
import sys
import shutil
from datetime import datetime

def backup_env():
    """Создать резервную копию .env файла"""
    if os.path.exists('.env'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'.env.backup_{timestamp}'
        shutil.copy2('.env', backup_name)
        print(f"✅ Резервная копия создана: {backup_name}")
        return backup_name
    return None

def switch_to_testnet():
    """Переключиться в тестовый режим"""
    print("🎯 Переключение в ТЕСТОВЫЙ РЕЖИМ...")
    
    # Создаем резервную копию
    backup_env()
    
    # Создаем новый .env файл для тестовой сети
    env_content = """# Bybit API (ТЕСТОВАЯ СЕТЬ)
BYBIT_API_KEY=your_testnet_api_key_here
BYBIT_API_SECRET=your_testnet_api_secret_here
BYBIT_TESTNET=true

# Google Sheets
GOOGLE_SHEETS_ID=1Vg-Za-flAc7kI77Emh6Rft-8gZT2spIqnzPoFniedZI
GOOGLE_SHEET_NAME=Trades
GOOGLE_CREDENTIALS_FILE=credentials.json

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Настройки торговли (ДЕМО-СЧЕТ)
TRADE_MODE=trade
DEFAULT_LEVERAGE=10
DEFAULT_POSITION_SIZE=0.01
MAX_POSITIONS=3
PRICE_DEVIATION=0.5

# Настройки мониторинга
CHECK_INTERVAL=30

# Логирование
LOG_LEVEL=INFO
LOG_FILE=./google_signals_bot.log
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ Переключение в тестовый режим завершено!")
        print("💰 Теперь торговля будет осуществляться на демо-счете")
        print("📝 Не забудьте обновить API ключи в .env файле")
    except Exception as e:
        print(f"❌ Ошибка при переключении: {e}")

def switch_to_mainnet():
    """Переключиться в реальный режим"""
    print("⚠️ Переключение в РЕАЛЬНЫЙ РЕЖИМ...")
    print("💸 ВНИМАНИЕ: Торговля будет осуществляться на реальном счете!")
    
    confirm = input("Вы уверены? (yes/no): ").lower()
    if confirm != 'yes':
        print("❌ Переключение отменено")
        return
    
    # Создаем резервную копию
    backup_env()
    
    # Создаем новый .env файл для реальной сети
    env_content = """# Bybit API (РЕАЛЬНАЯ СЕТЬ)
BYBIT_API_KEY=your_mainnet_api_key_here
BYBIT_API_SECRET=your_mainnet_api_secret_here
BYBIT_TESTNET=false

# Google Sheets
GOOGLE_SHEETS_ID=1Vg-Za-flAc7kI77Emh6Rft-8gZT2spIqnzPoFniedZI
GOOGLE_SHEET_NAME=Trades
GOOGLE_CREDENTIALS_FILE=credentials.json

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Настройки торговли (РЕАЛЬНЫЙ СЧЕТ)
TRADE_MODE=trade
DEFAULT_LEVERAGE=5
DEFAULT_POSITION_SIZE=0.005
MAX_POSITIONS=2
PRICE_DEVIATION=0.3

# Настройки мониторинга
CHECK_INTERVAL=30

# Логирование
LOG_LEVEL=INFO
LOG_FILE=./google_signals_bot.log
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ Переключение в реальный режим завершено!")
        print("💸 Теперь торговля будет осуществляться на реальном счете")
        print("📝 Не забудьте обновить API ключи в .env файле")
        print("⚠️ Будьте осторожны с реальными деньгами!")
    except Exception as e:
        print(f"❌ Ошибка при переключении: {e}")

def show_current_mode():
    """Показать текущий режим"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден")
        return
    
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'BYBIT_TESTNET=true' in content:
            print("🎯 Текущий режим: ТЕСТОВАЯ СЕТЬ")
            print("💰 Торговля на демо-счете")
        elif 'BYBIT_TESTNET=false' in content:
            print("⚠️ Текущий режим: РЕАЛЬНАЯ СЕТЬ")
            print("💸 Торговля на реальном счете")
        else:
            print("❓ Режим не определен")
    except Exception as e:
        print(f"❌ Ошибка при чтении .env: {e}")

def main():
    """Главная функция"""
    print("🔄 Переключатель режимов Google Signals Bot")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python switch_mode.py testnet  - переключиться в тестовый режим")
        print("  python switch_mode.py mainnet  - переключиться в реальный режим")
        print("  python switch_mode.py status   - показать текущий режим")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'testnet':
        switch_to_testnet()
    elif command == 'mainnet':
        switch_to_mainnet()
    elif command == 'status':
        show_current_mode()
    else:
        print(f"❌ Неизвестная команда: {command}")

if __name__ == "__main__":
    main() 