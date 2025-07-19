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
from bybit_api import BybitAPI
from google_sheets_api import GoogleSheetsAPI
from market_analyzer import MarketAnalyzer
# from telegram_webhook import create_webhook_server  # Удалено
import threading

class GoogleSignalsBot:
    def __init__(self):
        self.config = None
        self.signal_processor = None
        self.telegram = None
        self.bybit_api = None
        self.google_sheets_api = None
        self.market_analyzer = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        self.polling_thread = None
        
    def _setup_logging(self):
        """Настройка логирования"""
        if not self.config:
            return
            
        log_level = getattr(logging, self.config.get('LOG_LEVEL', 'INFO'))
        log_file = self.config.get('LOG_FILE', './google_signals_bot.log')
        
        # Создаем директорию для логов если нужно
        import os
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def initialize(self):
        """Инициализация бота"""
        try:
            self.logger.info("🚀 Инициализация Google Signals Bot...")
            
            # Загружаем конфигурацию
            self.config = load_config()
            
            # Логируем настройки сразу после загрузки
            self.logger.info(f"🔧 Настройки Bybit из конфига:")
            self.logger.info(f"   - API Key: {self.config.get('BYBIT_API_KEY', 'НЕ УСТАНОВЛЕН')[:10] if self.config.get('BYBIT_API_KEY') else 'НЕ УСТАНОВЛЕН'}...")
            self.logger.info(f"   - Testnet: {self.config.get('BYBIT_TESTNET', 'НЕ УСТАНОВЛЕН')}")
            self.logger.info(f"   - Google Sheets ID: {self.config.get('GOOGLE_SHEETS_ID', 'НЕ УСТАНОВЛЕН')}")
            
            validate_config(self.config)
            
            # Пересоздаем логирование с правильной конфигурацией
            self._setup_logging()
            
            # Инициализируем компоненты в правильном порядке
            testnet_mode = self.config.get('BYBIT_TESTNET', True)  # По умолчанию тестовая сеть
            
            self.logger.info(f"🔧 Настройки Bybit:")
            self.logger.info(f"   - API Key: {self.config['BYBIT_API_KEY'][:10]}...")
            self.logger.info(f"   - Testnet: {testnet_mode}")
            
            if testnet_mode:
                self.logger.info("🎯 РЕЖИМ ТЕСТОВОЙ СЕТИ АКТИВИРОВАН")
                self.logger.info("💰 Торговля будет осуществляться на демо-счете")
            else:
                self.logger.info("⚠️ РЕАЛЬНЫЙ РЕЖИМ - БУДЬТЕ ОСТОРОЖНЫ!")
            
            self.bybit_api = BybitAPI(
                api_key=self.config['BYBIT_API_KEY'],
                api_secret=self.config['BYBIT_API_SECRET'],
                testnet=testnet_mode
            )
            
            self.google_sheets_api = GoogleSheetsAPI(
                credentials_file=self.config['GOOGLE_CREDENTIALS_FILE'],
                spreadsheet_id=self.config['GOOGLE_SHEETS_ID'],
                bybit_api=self.bybit_api
            )
            
            self.telegram = TelegramBot(
                self.config['TELEGRAM_BOT_TOKEN'],
                self.config['TELEGRAM_CHAT_ID'],
                google_sheets_api=self.google_sheets_api  # Передаем для добавления сделок
            )
            
            self.signal_processor = SignalProcessor(
                bybit_api=self.bybit_api,
                google_sheets_api=self.google_sheets_api,
                telegram_bot=self.telegram,
                logger=self.logger
            )
            
            # Передаем signal_processor в Telegram бот для доступа к функциям тестовой сети
            self.telegram.signal_processor = self.signal_processor
            
            # Передаем конфигурацию в signal_processor
            self.signal_processor.config = self.config
            
            # Инициализируем анализатор рынка
            self.market_analyzer = MarketAnalyzer(self.bybit_api)
            
            # Передаем анализатор рынка в Telegram бот
            self.telegram.market_analyzer = self.market_analyzer
            
            # Инициализируем веб-хук сервер для Telegram
            # self.webhook_server = create_webhook_server(self.telegram, port=5000) # Удалено
            
            # Сразу отправляем сводку по бэктесту
            self.signal_processor.send_backtest_report()

            # Запуск анализа паттернов при старте
            self.signal_processor.analyze_trading_patterns()
            
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
            balance = self.bybit_api.get_balance()
            if balance:
                if self.config.get('BYBIT_TESTNET', True):
                    self.logger.info("✅ Bybit Testnet API подключен")
                    self.logger.info(f"💰 Тестовый баланс: {balance.get('totalWalletBalance', 'N/A')} USDT")
                    
                    # Получаем информацию об аккаунте
                    account_info = self.bybit_api.get_account_info()
                    if account_info:
                        self.logger.info(f"🏦 Тип аккаунта: {account_info.get('accountType', 'N/A')}")
                else:
                    self.logger.info("✅ Bybit Mainnet API подключен")
            else:
                raise Exception("Не удалось получить баланс Bybit")
        except Exception as e:
            raise Exception(f"Ошибка подключения к Bybit: {e}")
        
        # Тест Google Sheets
        try:
            signals = self.google_sheets_api.read_signals()
            self.logger.info(f"✅ Google Sheets API подключен (найдено сигналов: {len(signals)})")
        except Exception as e:
            raise Exception(f"Ошибка подключения к Google Sheets: {e}")
    
    def start(self):
        """Запуск бота"""
        try:
            self.logger.info("🚀 Запуск Google Signals Bot...")
            
            # Отправляем сообщение о запуске с информацией о режиме
            if self.config.get('BYBIT_TESTNET', True):
                startup_message = "🚀 Google Signals Bot запущен в ТЕСТОВОМ РЕЖИМЕ! 🎯\n💰 Торговля на демо-счете Bybit"
            else:
                startup_message = "🚀 Google Signals Bot запущен в РЕАЛЬНОМ РЕЖИМЕ! ⚠️\n💸 Торговля на реальном счете Bybit"
            
            self.telegram.send_message(startup_message)

            # Запускаем polling-цикл Telegram в отдельном потоке
            self.polling_thread = threading.Thread(target=self.telegram.run_polling, daemon=True)
            self.polling_thread.start()
            self.logger.info("✅ Polling Telegram запущен")

            self.running = True
            
            # Основной цикл работы бота
            while True:
                try:
                    # Обрабатываем сигналы
                    result = self.signal_processor.process_signals()
                    
                    # Увеличиваем счетчик циклов
                    self.signal_processor.cycle_count += 1
                    
                    # Отправляем отчет о бэктесте каждые 10 циклов
                    if self.signal_processor.cycle_count % 10 == 0:
                        self.signal_processor.send_backtest_report()
                    
                    # Анализируем паттерны каждые 20 циклов
                    if self.signal_processor.cycle_count % 20 == 0:
                        self.signal_processor.analyze_trading_patterns()
                    
                    # Мониторим позиции каждые 5 циклов
                    if self.signal_processor.cycle_count % 5 == 0:
                        self.signal_processor.monitor_positions()
                    
                    # Отправляем статус тестовой сети каждые 30 циклов
                    if self.signal_processor.cycle_count % 30 == 0:
                        self.signal_processor.send_testnet_status()
                    
                    # Логируем статус
                    self.logger.info(f"🔄 Цикл {self.signal_processor.cycle_count} завершен")
                    
                    # Пауза между циклами
                    time.sleep(self.config['CHECK_INTERVAL'])
                    
                except KeyboardInterrupt:
                    self.logger.info("🛑 Получен сигнал остановки")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Ошибка в основном цикле: {e}")
                    self.telegram.send_error(f"Ошибка в основном цикле: {e}")
                    time.sleep(self.config['CHECK_INTERVAL'])
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка: {e}")
            self.telegram.send_error(f"Критическая ошибка: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка бота"""
        self.logger.info("🛑 Остановка Google Signals Bot...")
        self.running = False
        
        # Останавливаем веб-хук сервер # Удалено
        # if self.webhook_server: # Удалено
        #     self.webhook_server.stop() # Удалено
        #     self.logger.info("🛑 Веб-хук сервер остановлен") # Удалено
        
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