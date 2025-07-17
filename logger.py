#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Логирование для Google Signals Bot
"""

import logging
import os
from datetime import datetime
from typing import Optional

class BotLogger:
    def __init__(self, name: str, log_file: str = "google_signals_bot.log", level: str = "INFO"):
        self.name = name
        self.log_file = log_file
        self.level = level
        
        # Создаем логгер
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Очищаем существующие обработчики
        self.logger.handlers.clear()
        
        # Создаем форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Обработчик для файла
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Обработчик для консоли
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        """Информационное сообщение"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Предупреждение"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Ошибка"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """Отладочное сообщение"""
        self.logger.debug(message)
    
    def critical(self, message: str):
        """Критическая ошибка"""
        self.logger.critical(message)
    
    def log_signal(self, signal_data: dict):
        """Логирование сигнала"""
        message = f"📊 Сигнал: {signal_data.get('symbol', 'N/A')} {signal_data.get('direction', 'N/A')} @ {signal_data.get('entry_price', 'N/A')}"
        self.info(message)
    
    def log_trade(self, trade_data: dict):
        """Логирование сделки"""
        message = f"💰 Сделка: {trade_data.get('symbol', 'N/A')} {trade_data.get('side', 'N/A')} {trade_data.get('size', 'N/A')} @ {trade_data.get('price', 'N/A')}"
        self.info(message)
    
    def log_error(self, error: Exception, context: str = ""):
        """Логирование ошибки с контекстом"""
        message = f"❌ Ошибка в {context}: {str(error)}"
        self.error(message)
    
    def log_status(self, status_data: dict):
        """Логирование статуса"""
        message = f"📈 Статус: {status_data.get('processed_signals', 0)} сигналов, {status_data.get('open_positions', 0)} позиций"
        self.info(message)

def setup_logging(log_file: str = "google_signals_bot.log", level: str = "INFO"):
    """Настройка глобального логирования"""
    # Создаем директорию для логов если её нет
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Настраиваем корневой логгер
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Отключаем логи от сторонних библиотек
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING) 