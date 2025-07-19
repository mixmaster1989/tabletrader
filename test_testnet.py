#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для проверки подключения к тестовой сети Bybit
"""

import os
import sys
from dotenv import load_dotenv
from bybit_api import BybitAPI

def test_testnet_connection():
    """Проверить подключение к тестовой сети"""
    print("🎯 Проверка подключения к тестовой сети Bybit...")
    print("=" * 50)
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем настройки
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    testnet = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'
    
    if not api_key or not api_secret:
        print("❌ API ключи не найдены в .env файле")
        print("📝 Убедитесь, что вы добавили BYBIT_API_KEY и BYBIT_API_SECRET")
        return False
    
    if not testnet:
        print("⚠️ ВНИМАНИЕ: BYBIT_TESTNET=false - вы подключены к реальной сети!")
        confirm = input("Продолжить? (yes/no): ").lower()
        if confirm != 'yes':
            return False
    
    try:
        # Создаем подключение к API
        print("🔄 Создание подключения к Bybit API...")
        bybit_api = BybitAPI(api_key, api_secret, testnet=testnet)
        
        # Проверяем баланс
        print("\n💰 Проверка баланса...")
        balance = bybit_api.get_balance()
        if balance:
            print(f"✅ Баланс получен успешно!")
            print(f"   Общий баланс: {balance.get('totalWalletBalance', 'N/A')} USDT")
            print(f"   Доступно: {balance.get('availableToWithdraw', 'N/A')} USDT")
            print(f"   Закреплено: {balance.get('totalPnl', 'N/A')} USDT")
        else:
            print("❌ Не удалось получить баланс")
            return False
        
        # Получаем информацию об аккаунте
        print("\n🏦 Информация об аккаунте...")
        account_info = bybit_api.get_account_info()
        if account_info:
            print(f"✅ Информация об аккаунте получена!")
            print(f"   Тип аккаунта: {account_info.get('accountType', 'N/A')}")
            print(f"   Уровень риска: {account_info.get('riskLevel', 'N/A')}")
        else:
            print("⚠️ Не удалось получить информацию об аккаунте")
        
        # Проверяем получение цены
        print("\n📊 Проверка получения рыночных данных...")
        test_symbol = "BTCUSDT"
        price = bybit_api.get_last_price(test_symbol)
        if price:
            print(f"✅ Цена {test_symbol}: {price}")
        else:
            print(f"❌ Не удалось получить цену {test_symbol}")
            return False
        
        # Проверяем позиции
        print("\n📈 Проверка позиций...")
        positions = bybit_api.get_positions()
        if positions:
            print(f"✅ Найдено позиций: {len(positions)}")
            for pos in positions:
                symbol = pos.get('symbol', 'N/A')
                size = pos.get('size', '0')
                side = pos.get('side', 'N/A')
                print(f"   {symbol}: {side} {size}")
        else:
            print("✅ Открытых позиций нет")
        
        print("\n" + "=" * 50)
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print("🎯 Тестовая сеть Bybit работает корректно")
        
        if testnet:
            print("💰 Вы готовы к тестовой торговле на демо-счете")
        else:
            print("⚠️ ВНИМАНИЕ: Вы подключены к реальной сети!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при проверке подключения: {e}")
        print("\n🔧 Возможные решения:")
        print("1. Проверьте правильность API ключей")
        print("2. Убедитесь, что ключи созданы для тестовой сети")
        print("3. Проверьте разрешения API ключей (Read, Trade)")
        print("4. Убедитесь в стабильности интернет-соединения")
        return False

def main():
    """Главная функция"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Использование: python test_testnet.py")
        print("Проверяет подключение к тестовой сети Bybit")
        return
    
    success = test_testnet_connection()
    
    if success:
        print("\n🚀 Теперь можно запускать бота: python main.py")
    else:
        print("\n❌ Исправьте ошибки перед запуском бота")
        sys.exit(1)

if __name__ == "__main__":
    main() 