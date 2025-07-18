#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для восстановления файла .env
"""

import shutil
import os

def restore_env_file():
    """Восстановить файл .env из example.env"""
    try:
        if os.path.exists('example.env'):
            shutil.copy('example.env', '.env')
            print("✅ Файл .env успешно создан из example.env")
            print("📝 Теперь отредактируйте .env файл и заполните своими данными:")
            print("   - BYBIT_API_KEY")
            print("   - BYBIT_API_SECRET") 
            print("   - GOOGLE_SHEETS_ID")
            print("   - TELEGRAM_BOT_TOKEN")
            print("   - TELEGRAM_CHAT_ID")
        else:
            print("❌ Файл example.env не найден!")
            return False
    except Exception as e:
        print(f"❌ Ошибка при создании .env файла: {e}")
        return False
    
    return True

def check_missing_files():
    """Проверить отсутствующие файлы"""
    missing_files = []
    
    if not os.path.exists('.env'):
        missing_files.append('.env')
    
    if not os.path.exists('credentials.json'):
        missing_files.append('credentials.json')
    
    if not os.path.exists('token.pickle'):
        missing_files.append('token.pickle')
    
    return missing_files

if __name__ == "__main__":
    print("🔍 Проверка отсутствующих файлов...")
    missing = check_missing_files()
    
    if missing:
        print(f"❌ Отсутствуют файлы: {', '.join(missing)}")
        
        if '.env' in missing:
            print("\n🔄 Восстановление файла .env...")
            restore_env_file()
        
        if 'credentials.json' in missing:
            print("\n⚠️  Файл credentials.json отсутствует!")
            print("   Создайте его в Google Cloud Console:")
            print("   1. Перейдите в https://console.cloud.google.com/")
            print("   2. Выберите проект")
            print("   3. APIs & Services > Credentials")
            print("   4. Создайте Service Account")
            print("   5. Скачайте JSON и переименуйте в credentials.json")
        
        if 'token.pickle' in missing:
            print("\nℹ️  Файл token.pickle будет создан автоматически при первом запуске")
    else:
        print("✅ Все файлы авторизации присутствуют!") 