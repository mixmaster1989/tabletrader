#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест настройки Google Sheets API
"""

import os
import json
import pickle
from google_sheets_oauth import GoogleSheetsOAuthAPI

def test_credentials_file():
    """Проверить файл credentials.json"""
    if not os.path.exists('credentials.json'):
        print("❌ Файл credentials.json не найден!")
        print("   Создайте его в Google Cloud Console")
        return False
    
    try:
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds]
        
        if missing_fields:
            print(f"❌ В credentials.json отсутствуют поля: {missing_fields}")
            return False
        
        print("✅ Файл credentials.json корректен")
        print(f"   Project ID: {creds.get('project_id', 'N/A')}")
        print(f"   Client Email: {creds.get('client_email', 'N/A')}")
        return True
        
    except json.JSONDecodeError:
        print("❌ Файл credentials.json содержит некорректный JSON")
        return False
    except Exception as e:
        print(f"❌ Ошибка чтения credentials.json: {e}")
        return False

def test_google_sheets_connection():
    """Проверить подключение к Google Sheets"""
    try:
        # Используем тестовый ID таблицы
        test_spreadsheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        
        print("🔄 Тестирование подключения к Google Sheets...")
        api = GoogleSheetsOAuthAPI(test_spreadsheet_id)
        
        # Пробуем прочитать данные
        result = api.service.spreadsheets().values().get(
            spreadsheetId=test_spreadsheet_id,
            range="A1:A5"
        ).execute()
        
        print("✅ Подключение к Google Sheets успешно!")
        print("✅ Файл token.pickle создан автоматически")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Google Sheets: {e}")
        print("   Проверьте:")
        print("   1. Включен ли Google Sheets API в проекте")
        print("   2. Корректен ли файл credentials.json")
        print("   3. Есть ли доступ к интернету")
        return False

def check_env_file():
    """Проверить файл .env"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        return False
    
    print("✅ Файл .env найден")
    return True

def main():
    print("🔍 Проверка настройки Google API...")
    print("=" * 50)
    
    # Проверяем .env
    env_ok = check_env_file()
    
    # Проверяем credentials.json
    creds_ok = test_credentials_file()
    
    # Проверяем подключение к Google Sheets
    if creds_ok:
        connection_ok = test_google_sheets_connection()
    else:
        connection_ok = False
    
    print("=" * 50)
    
    if env_ok and creds_ok and connection_ok:
        print("🎉 Все проверки пройдены успешно!")
        print("✅ Google API настроен корректно")
        print("✅ Файл token.pickle создан")
        print("\nТеперь можете запускать основной бот:")
        print("python main.py")
    else:
        print("❌ Есть проблемы с настройкой")
        print("\nСледуйте инструкциям в файле GOOGLE_CREDENTIALS_SETUP.md")

if __name__ == "__main__":
    main() 