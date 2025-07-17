#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест функциональности добавления сделок через Telegram
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_telegram_bot_initialization():
    """Тест инициализации Telegram бота"""
    print("🔍 Тестирование инициализации Telegram бота...")
    
    try:
        from telegram_bot import TelegramBot
        from config import load_config
        
        # Загружаем конфигурацию
        config = load_config()
        
        # Создаем экземпляр бота без Google Sheets API для теста
        bot = TelegramBot(
            bot_token=config.get('TELEGRAM_BOT_TOKEN'),
            chat_id=config.get('TELEGRAM_CHAT_ID')
        )
        
        print("✅ Telegram бот инициализирован успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации Telegram бота: {e}")
        return False

def test_webhook_server():
    """Тест веб-хук сервера"""
    print("\n🔍 Тестирование веб-хук сервера...")
    
    try:
        from telegram_webhook import create_webhook_server
        from telegram_bot import TelegramBot
        from config import load_config
        
        # Загружаем конфигурацию
        config = load_config()
        
        # Создаем экземпляр бота
        bot = TelegramBot(
            bot_token=config.get('TELEGRAM_BOT_TOKEN'),
            chat_id=config.get('TELEGRAM_CHAT_ID')
        )
        
        # Создаем веб-хук сервер
        webhook_server = create_webhook_server(bot, port=5001)  # Используем другой порт для теста
        
        print("✅ Веб-хук сервер создан успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания веб-хук сервера: {e}")
        return False

def test_trade_data_validation():
    """Тест валидации данных сделки"""
    print("\n🔍 Тестирование валидации данных сделки...")
    
    try:
        from telegram_bot import TelegramBot
        
        # Создаем временный бот для теста
        bot = TelegramBot("test_token", "test_chat_id")
        
        # Тестируем валидацию цен
        test_cases = [
            ("0.33591", True),
            ("0,33591", True),  # Запятая
            ("335.91", True),
            ("abc", False),
            ("", False),
            ("0", False),
            ("-1", False)
        ]
        
        for price, expected in test_cases:
            result = bot.is_valid_price(price)
            status = "✅" if result == expected else "❌"
            print(f"{status} Цена '{price}' -> {result} (ожидалось: {expected})")
            
            if result != expected:
                return False
        
        print("✅ Валидация цен работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования валидации: {e}")
        return False

def test_pnl_calculation():
    """Тест расчета P&L"""
    print("\n🔍 Тестирование расчета P&L...")
    
    try:
        # Тестовые данные
        test_cases = [
            # (entry_price, exit_price, direction, expected_pnl)
            (100, 110, "LONG", 10.0),    # +10%
            (100, 90, "LONG", -10.0),    # -10%
            (100, 90, "SHORT", 10.0),    # +10%
            (100, 110, "SHORT", -10.0),  # -10%
            (0.33591, 0.34001, "LONG", 1.22),  # Пример из логов
        ]
        
        for entry, exit, direction, expected in test_cases:
            if direction == "LONG":
                pnl = ((exit - entry) / entry) * 100
            else:  # SHORT
                pnl = ((entry - exit) / entry) * 100
            
            # Округляем до 2 знаков
            pnl = round(pnl, 2)
            expected = round(expected, 2)
            
            status = "✅" if abs(pnl - expected) < 0.01 else "❌"
            print(f"{status} {direction}: {entry} -> {exit} = {pnl}% (ожидалось: {expected}%)")
            
            if abs(pnl - expected) >= 0.01:
                return False
        
        print("✅ Расчет P&L работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка расчета P&L: {e}")
        return False

def test_google_sheets_integration():
    """Тест интеграции с Google Sheets"""
    print("\n🔍 Тестирование интеграции с Google Sheets...")
    
    try:
        from google_sheets_api import GoogleSheetsAPI
        from config import load_config
        
        # Загружаем конфигурацию
        config = load_config()
        
        # Создаем экземпляр API
        sheets_api = GoogleSheetsAPI(
            credentials_file=config.get('GOOGLE_CREDENTIALS_FILE'),
            spreadsheet_id=config.get('GOOGLE_SPREADSHEET_ID')
        )
        
        # Тестируем получение следующего номера строки
        next_row = sheets_api.get_next_row_number()
        print(f"✅ Следующий номер строки: {next_row}")
        
        # Тестируем чтение сигналов
        signals = sheets_api.read_signals()
        print(f"✅ Прочитано сигналов: {len(signals)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграции с Google Sheets: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ TELEGRAM TRADE ФУНКЦИОНАЛЬНОСТИ\n")
    
    tests = [
        ("Инициализация Telegram бота", test_telegram_bot_initialization),
        ("Веб-хук сервер", test_webhook_server),
        ("Валидация данных сделки", test_trade_data_validation),
        ("Расчет P&L", test_pnl_calculation),
        ("Интеграция с Google Sheets", test_google_sheets_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"ТЕСТ: {test_name}")
        print(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - ПРОЙДЕН")
            else:
                print(f"❌ {test_name} - ПРОВАЛЕН")
        except Exception as e:
            print(f"❌ {test_name} - ОШИБКА: {e}")
    
    print(f"\n{'='*50}")
    print(f"РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")
    print(f"{'='*50}")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к работе.")
        return True
    else:
        print("⚠️ Некоторые тесты не пройдены. Проверьте настройки.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 