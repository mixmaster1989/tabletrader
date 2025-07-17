#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Вспомогательные функции для Google Signals Bot
"""

import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

def generate_signal_id(signal_data: Dict) -> str:
    """Генерация уникального ID для сигнала"""
    signal_str = f"{signal_data.get('symbol', '')}_{signal_data.get('entry_price', '')}_{signal_data.get('direction', '')}"
    return hashlib.md5(signal_str.encode()).hexdigest()[:8]

def validate_price_deviation(current_price: float, signal_price: float, max_deviation: float) -> bool:
    """Проверка отклонения цены от сигнала"""
    if signal_price <= 0:
        return False
    
    deviation = abs(current_price - signal_price) / signal_price * 100
    return deviation <= max_deviation

def format_price(price: float, symbol: str = "") -> str:
    """Форматирование цены"""
    if symbol in ['BTCUSDT', 'ETHUSDT']:
        return f"{price:.2f}"
    elif symbol in ['SOLUSDT', 'LINKUSDT', 'AVAXUSDT']:
        return f"{price:.4f}"
    else:
        return f"{price:.6f}"

def calculate_roi(entry_price: float, current_price: float, direction: str) -> float:
    """Расчет ROI"""
    if direction == 'LONG':
        return ((current_price - entry_price) / entry_price) * 100
    elif direction == 'SHORT':
        return ((entry_price - current_price) / entry_price) * 100
    else:
        return 0.0

def is_market_open() -> bool:
    """Проверка, открыт ли рынок (криптовалюты торгуются 24/7)"""
    return True

def get_time_until_next_check(check_interval: int) -> int:
    """Получить время до следующей проверки"""
    current_second = datetime.now().second
    return check_interval - (current_second % check_interval)

def format_duration(seconds: int) -> str:
    """Форматирование длительности"""
    if seconds < 60:
        return f"{seconds}с"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}м {seconds % 60}с"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}ч {minutes}м"

def safe_float(value, default: float = 0.0) -> float:
    """Безопасное преобразование в float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default: int = 0) -> int:
    """Безопасное преобразование в int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def validate_symbol(symbol: str) -> bool:
    """Валидация торгового символа"""
    if not symbol or len(symbol) < 3:
        return False
    
    # Проверяем формат XXXUSDT
    if not symbol.endswith('USDT'):
        return False
    
    # Проверяем, что символ содержит только буквы и цифры
    base_symbol = symbol[:-4]  # Убираем USDT
    return base_symbol.isalnum()

def get_symbol_info(symbol: str) -> Dict:
    """Получить информацию о символе"""
    # Fallback информация о популярных символах
    symbol_info = {
        'BTCUSDT': {'min_qty': 0.001, 'price_precision': 2, 'qty_precision': 3},
        'ETHUSDT': {'min_qty': 0.01, 'price_precision': 2, 'qty_precision': 3},
        'SOLUSDT': {'min_qty': 0.1, 'price_precision': 4, 'qty_precision': 1},
        'LINKUSDT': {'min_qty': 0.1, 'price_precision': 4, 'qty_precision': 1},
        'DOGEUSDT': {'min_qty': 1.0, 'price_precision': 6, 'qty_precision': 0},
        'XRPUSDT': {'min_qty': 1.0, 'price_precision': 4, 'qty_precision': 0},
        'BNBUSDT': {'min_qty': 0.01, 'price_precision': 2, 'qty_precision': 3},
        'ADAUSDT': {'min_qty': 1.0, 'price_precision': 4, 'qty_precision': 0},
        'AVAXUSDT': {'min_qty': 0.1, 'price_precision': 4, 'qty_precision': 1},
    }
    
    return symbol_info.get(symbol, {'min_qty': 0.01, 'price_precision': 4, 'qty_precision': 2})

def round_to_precision(value: float, precision: int) -> float:
    """Округление до заданной точности"""
    return round(value, precision)

def is_valid_tp_sl(entry_price: float, take_profit: float, stop_loss: float, direction: str) -> bool:
    """Проверка корректности TP/SL"""
    if direction == 'LONG':
        return take_profit > entry_price and stop_loss < entry_price
    elif direction == 'SHORT':
        return take_profit < entry_price and stop_loss > entry_price
    else:
        return False

def calculate_position_value(price: float, size: float, leverage: int) -> float:
    """Расчет стоимости позиции"""
    return (price * size) / leverage

def format_currency(amount: float, currency: str = "USDT") -> str:
    """Форматирование валюты"""
    if amount >= 1000:
        return f"{amount/1000:.1f}k {currency}"
    else:
        return f"{amount:.2f} {currency}"

def get_current_timestamp() -> int:
    """Получить текущий timestamp"""
    return int(time.time())

def is_recent_signal(signal_timestamp: int, max_age_hours: int = 24) -> bool:
    """Проверка, не устарел ли сигнал"""
    current_time = get_current_timestamp()
    signal_age = current_time - signal_timestamp
    max_age_seconds = max_age_hours * 3600
    
    return signal_age <= max_age_seconds 