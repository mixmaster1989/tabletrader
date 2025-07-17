#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Главный файл Google Signals Bot
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from config import load_config, validate_config
from signal_processor import SignalProcessor
from telegram_bot import TelegramBot

class GoogleSignalsBot:
    def __init__(self):
        self.config = None
        self.signal_processor = None
        self.telegram = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Настройка логирования
        self._setup_logging()
        
    def _setup_logging(self):
        """Настройка логирования"""
        log_level = getattr(logging, self.config.get('LOG_LEVEL', 'INFO') if self.config else 'INFO')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.get('LOG_FILE', 'google_signals_bot.log') if self.config else 'google_signals_bot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def initialize(self):
        """Инициализация бота"""
        try:
            self.logger.info("🚀 Инициализация Google Signals Bot...")
            
            # Загружаем конфигурацию
            self.config = load_config()
            validate_config(self.config)
            
            # Пересоздаем логирование с правильной конфигурацией
            self._setup_logging()
            
            # Инициализируем компоненты
            self.telegram = TelegramBot(
                self.config['TELEGRAM_BOT_TOKEN'],
                self.config['TELEGRAM_CHAT_ID']
            )
            
            self.signal_processor = SignalProcessor(self.config)
            
            # Тестируем подключения
            self._test_connections()
            
            self.logger.info("✅ Google Signals Bot инициализирован")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации: {e}")
            if self.telegram:
                self.telegram.send_error(f"Ошибка инициализации: {e}")
            return False
    
    def _test_connections(self):
        """Тестирование подключений"""
        self.logger.info("🔍 Тестирование подключений...")
        
        # Тест Telegram
        if not self.telegram.test_connection():
            raise Exception("Не удалось подключиться к Telegram")
        
        # Тест Bybit
        try:
            balance = self.signal_processor.bybit.get_balance()
            if balance:
                self.logger.info("✅ Bybit API подключен")
            else:
                raise Exception("Не удалось получить баланс Bybit")
        except Exception as e:
            raise Exception(f"Ошибка подключения к Bybit: {e}")
        
        # Тест Google Sheets
        try:
            signals = self.signal_processor.google_sheets.read_signals()
            self.logger.info(f"✅ Google Sheets API подключен (найдено сигналов: {len(signals)})")
        except Exception as e:
            raise Exception(f"Ошибка подключения к Google Sheets: {e}")
    
    def start(self):
        """Запуск бота"""
        try:
            self.logger.info("🚀 Запуск Google Signals Bot...")
            self.telegram.send_message("🚀 Google Signals Bot запущен!")
            
            self.running = True
            
            # Основной цикл
            while self.running:
                try:
                    # Обрабатываем сигналы
                    result = self.signal_processor.process_signals()
                    
                    # Логируем результат
                    if result['processed'] > 0:
                        self.logger.info(f"✅ Обработано {result['processed']} сигналов")
                    
                    if result['errors'] > 0:
                        self.logger.warning(f"⚠️ {result['errors']} ошибок при обработке")
                    
                    # Отправляем статус каждые 10 циклов
                    if hasattr(self, '_cycle_count'):
                        self._cycle_count += 1
                    else:
                        self._cycle_count = 1
                    
                    if self._cycle_count % 10 == 0:
                        status = self.signal_processor.get_status()
                        self.telegram.send_status(status)
                    
                    # Ждем следующей проверки
                    time.sleep(self.config['CHECK_INTERVAL'])
                    
                except KeyboardInterrupt:
                    self.logger.info("🛑 Получен сигнал остановки")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Ошибка в основном цикле: {e}")
                    self.telegram.send_error(f"Ошибка в основном цикле: {e}")
                    time.sleep(30)  # Ждем 30 секунд перед повтором
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка: {e}")
            self.telegram.send_error(f"Критическая ошибка: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка бота"""
        self.logger.info("🛑 Остановка Google Signals Bot...")
        self.running = False
        
        if self.telegram:
            self.telegram.send_message("🛑 Google Signals Bot остановлен")
        
        self.logger.info("✅ Google Signals Bot остановлен")

def signal_handler(signum, frame):
    """Обработчик сигналов для корректной остановки"""
    print("\n🛑 Получен сигнал остановки...")
    if hasattr(signal_handler, 'bot'):
        signal_handler.bot.stop()

def main():
    """Главная функция"""
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Создаем и запускаем бота
    bot = GoogleSignalsBot()
    signal_handler.bot = bot  # Сохраняем ссылку для обработчика сигналов
    
    if bot.initialize():
        bot.start()
    else:
        print("❌ Не удалось инициализировать бота")
        sys.exit(1)

if __name__ == "__main__":
    main() 