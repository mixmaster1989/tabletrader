#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конфигурация для Google Signals Bot
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def load_config():
    """Загрузить конфигурацию"""
    return {
        # Bybit API
        'BYBIT_API_KEY': os.getenv('BYBIT_API_KEY', ''),
        'BYBIT_API_SECRET': os.getenv('BYBIT_API_SECRET', ''),
        'BYBIT_TESTNET': os.getenv('BYBIT_TESTNET', 'false').lower() == 'true',
        
        # Google Sheets
        'GOOGLE_SHEETS_ID': os.getenv('GOOGLE_SHEETS_ID', ''),  # Используем то же название, что и в валидации
        'GOOGLE_SPREADSHEET_ID': os.getenv('GOOGLE_SHEETS_ID', ''),  # Дублируем для совместимости
        'GOOGLE_SHEET_NAME': os.getenv('GOOGLE_SHEET_NAME', 'Trades'),  # Добавляем имя листа
        'GOOGLE_CREDENTIALS_FILE': os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json'),
        
        # Telegram
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID', ''),
        
        # Настройки торговли
        'DEFAULT_LEVERAGE': int(os.getenv('DEFAULT_LEVERAGE', '20')),
        'DEFAULT_POSITION_SIZE': float(os.getenv('DEFAULT_POSITION_SIZE', '0.01')),
        'MAX_POSITIONS': int(os.getenv('MAX_POSITIONS', '3')),
        'TRADE_MODE': os.getenv('TRADE_MODE', 'monitor').lower(),  # 'monitor' или 'trade'
        
        # Настройки мониторинга
        'CHECK_INTERVAL': int(os.getenv('CHECK_INTERVAL', '30')),  # секунды
        'PRICE_DEVIATION': float(os.getenv('PRICE_DEVIATION', '0.5')),  # % от цены входа
        
        # Логирование
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'LOG_FILE': os.getenv('LOG_FILE', './google_signals_bot.log'),
    }

def validate_config(config):
    """Проверить конфигурацию"""
    required_keys = [
        'BYBIT_API_KEY', 'BYBIT_API_SECRET', 'GOOGLE_SHEETS_ID',
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'
    ]
    
    missing_keys = []
    for key in required_keys:
        if not config.get(key):
            missing_keys.append(key)
    
    if missing_keys:
        raise ValueError(f"Отсутствуют обязательные параметры: {', '.join(missing_keys)}")
    
    return True 