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

        # Binance API
        'BINANCE_API_KEY': os.getenv('BINANCE_API_KEY', ''),
        'BINANCE_API_SECRET': os.getenv('BINANCE_API_SECRET', ''),
        'BINANCE_TESTNET': os.getenv('BINANCE_TESTNET', 'false').lower() == 'true',

        # OKX API
        'OKX_API_KEY': os.getenv('OKX_API_KEY', ''),
        'OKX_API_SECRET': os.getenv('OKX_API_SECRET', ''),
        'OKX_PASSPHRASE': os.getenv('OKX_PASSPHRASE', ''),
        'OKX_TESTNET': os.getenv('OKX_TESTNET', 'false').lower() == 'true',
        
        # Google Sheets
        'GOOGLE_SHEETS_ID': os.getenv('GOOGLE_SHEETS_ID', ''),
        'GOOGLE_CREDENTIALS_FILE': os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json'),
        
        # Telegram
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID', ''),
        
        # Настройки торговли
        'DEFAULT_LEVERAGE': int(os.getenv('DEFAULT_LEVERAGE', '20')),
        'DEFAULT_POSITION_SIZE': float(os.getenv('DEFAULT_POSITION_SIZE', '1')),
        'MAX_POSITIONS': int(os.getenv('MAX_POSITIONS', '3')),
        
        # Настройки мониторинга
        'CHECK_INTERVAL': int(os.getenv('CHECK_INTERVAL', '30')),  # секунды
        'PRICE_DEVIATION': float(os.getenv('PRICE_DEVIATION', '0.5')),  # % от цены входа
        
        # Логирование
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'LOG_FILE': os.getenv('LOG_FILE', 'google_signals_bot.log'),
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