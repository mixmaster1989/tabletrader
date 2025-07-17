#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot для Google Signals Bot с возможностью добавления сделок
"""

import logging
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime
import re
import time

class TelegramBot:
    def __init__(self, bot_token: str, chat_id: str, google_sheets_api=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.logger = logging.getLogger(__name__)
        self.google_sheets_api = google_sheets_api
        
        # Состояние пользователей для добавления сделок
        self.user_states = {}
        
        self.logger.info("✅ Telegram Bot инициализирован")
    
    def send_message(self, message: str, parse_mode: str = "HTML", reply_markup: dict = None) -> bool:
        """Отправить сообщение в Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("✅ Сообщение отправлено в Telegram")
                return True
            else:
                self.logger.error(f"❌ Ошибка отправки в Telegram: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            return False
    
    def send_error(self, error_message: str) -> bool:
        """Отправить сообщение об ошибке"""
        message = f"❌ ОШИБКА БОТА:\n\n{error_message}"
        return self.send_message(message)
    
    def send_status(self, status_data: dict) -> bool:
        """Отправить статус бота"""
        try:
            message = f"""🤖 СТАТУС БОТА

📊 Обработано сигналов: {status_data.get('processed_signals', 0)}
📈 Открытых позиций: {status_data.get('open_positions', 0)}/{status_data.get('max_positions', 0)}
🕐 Последняя проверка: {status_data.get('last_check', 'N/A')}

✅ Бот работает"""
            
            return self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки статуса: {e}")
            return False
    
    def send_position_update(self, position_data: dict) -> bool:
        """Отправить обновление по позиции"""
        try:
            message = f"""📊 ОБНОВЛЕНИЕ ПОЗИЦИИ

🪙 Монета: {position_data.get('symbol', 'N/A')}
📈 Направление: {position_data.get('side', 'N/A')}
💰 Размер: {position_data.get('size', 'N/A')}
💵 PnL: {position_data.get('pnl', 'N/A')}
📊 ROI: {position_data.get('roi', 'N/A')}%"""
            
            return self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки обновления позиции: {e}")
            return False
    
    def send_add_trade_menu(self) -> bool:
        """Отправить меню добавления сделки"""
        message = """📝 ДОБАВИТЬ НОВУЮ СДЕЛКУ

Выберите действие:"""
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "➕ Добавить сделку", "callback_data": "add_trade"}],
                [{"text": "📊 Посмотреть статус", "callback_data": "status"}],
                [{"text": "❌ Отмена", "callback_data": "cancel"}]
            ]
        }
        
        return self.send_message(message, reply_markup=keyboard)
    
    def send_symbol_selection(self, user_id: str) -> bool:
        """Отправить выбор символа"""
        message = """🪙 ВЫБЕРИТЕ СИМВОЛ

Выберите криптовалюту для сделки:"""
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "ADA", "callback_data": f"symbol_ADA"}, {"text": "SOL", "callback_data": f"symbol_SOL"}],
                [{"text": "BNB", "callback_data": f"symbol_BNB"}, {"text": "DOGE", "callback_data": f"symbol_DOGE"}],
                [{"text": "NEAR", "callback_data": f"symbol_NEAR"}, {"text": "PEOPLE", "callback_data": f"symbol_PEOPLE"}],
                [{"text": "TON", "callback_data": f"symbol_TON"}, {"text": "HMSRT", "callback_data": f"symbol_HMSRT"}],
                [{"text": "❌ Отмена", "callback_data": "cancel"}]
            ]
        }
        
        # Сохраняем состояние пользователя
        self.user_states[user_id] = {"state": "selecting_symbol"}
        
        return self.send_message(message, reply_markup=keyboard)
    
    def send_direction_selection(self, user_id: str, symbol: str) -> bool:
        """Отправить выбор направления сделки"""
        message = f"""📈 ВЫБЕРИТЕ НАПРАВЛЕНИЕ ДЛЯ {symbol}

Выберите тип сделки:"""
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📈 LONG (Покупка)", "callback_data": f"direction_LONG"}],
                [{"text": "📉 SHORT (Продажа)", "callback_data": f"direction_SHORT"}],
                [{"text": "❌ Отмена", "callback_data": "cancel"}]
            ]
        }
        
        # Обновляем состояние пользователя
        if user_id in self.user_states:
            self.user_states[user_id]["symbol"] = symbol
            self.user_states[user_id]["state"] = "selecting_direction"
        
        return self.send_message(message, reply_markup=keyboard)
    
    def send_price_input(self, user_id: str, symbol: str, direction: str) -> bool:
        """Отправить запрос на ввод цены входа"""
        message = f"""💰 ВВЕДИТЕ ЦЕНУ ВХОДА

🪙 Символ: {symbol}
📈 Направление: {direction}

Введите цену входа (например: 0.33591):"""
        
        # Обновляем состояние пользователя
        if user_id in self.user_states:
            self.user_states[user_id]["direction"] = direction
            self.user_states[user_id]["state"] = "entering_entry_price"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "❌ Отмена", "callback_data": "cancel"}]
            ]
        }
        
        return self.send_message(message, reply_markup=keyboard)
    
    def send_exit_price_input(self, user_id: str, symbol: str, direction: str, entry_price: str) -> bool:
        """Отправить запрос на ввод цены выхода"""
        message = f"""💰 ВВЕДИТЕ ЦЕНУ ВЫХОДА

🪙 Символ: {symbol}
📈 Направление: {direction}
💵 Цена входа: {entry_price}

Введите цену выхода (например: 0.34001):"""
        
        # Обновляем состояние пользователя
        if user_id in self.user_states:
            self.user_states[user_id]["entry_price"] = entry_price
            self.user_states[user_id]["state"] = "entering_exit_price"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "❌ Отмена", "callback_data": "cancel"}]
            ]
        }
        
        return self.send_message(message, reply_markup=keyboard)
    
    def send_stop_loss_input(self, user_id: str, symbol: str, direction: str, entry_price: str, exit_price: str) -> bool:
        """Отправить запрос на ввод стоп-лосса"""
        message = f"""🛑 ВВЕДИТЕ СТОП-ЛОСС

🪙 Символ: {symbol}
📈 Направление: {direction}
💵 Цена входа: {entry_price}
💰 Цена выхода: {exit_price}

Введите стоп-лосс (например: 0.33181):"""
        
        # Обновляем состояние пользователя
        if user_id in self.user_states:
            self.user_states[user_id]["exit_price"] = exit_price
            self.user_states[user_id]["state"] = "entering_stop_loss"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "❌ Отмена", "callback_data": "cancel"}]
            ]
        }
        
        return self.send_message(message, reply_markup=keyboard)
    
    def send_trade_confirmation(self, user_id: str, trade_data: dict) -> bool:
        """Отправить подтверждение сделки"""
        # Рассчитываем P&L
        entry_price = float(trade_data["entry_price"])
        exit_price = float(trade_data["exit_price"])
        
        if trade_data["direction"] == "LONG":
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        message = f"""✅ ПОДТВЕРЖДЕНИЕ СДЕЛКИ

🪙 Символ: {trade_data['symbol']}
📈 Направление: {trade_data['direction']}
💵 Цена входа: {trade_data['entry_price']}
💰 Цена выхода: {trade_data['exit_price']}
🛑 Стоп-лосс: {trade_data['stop_loss']}
📊 P&L: {pnl_percent:.2f}%

Подтвердите добавление сделки:"""
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Подтвердить", "callback_data": "confirm_trade"}],
                [{"text": "❌ Отмена", "callback_data": "cancel"}]
            ]
        }
        
        # Сохраняем данные сделки
        if user_id in self.user_states:
            self.user_states[user_id]["trade_data"] = trade_data
            self.user_states[user_id]["state"] = "confirming_trade"
        
        return self.send_message(message, reply_markup=keyboard)
    
    def add_trade_to_sheet(self, trade_data: dict) -> bool:
        """Добавить сделку в Google таблицу"""
        try:
            if not self.google_sheets_api:
                self.logger.error("❌ Google Sheets API не инициализирован")
                return False
            
            # Формируем данные для добавления
            current_date = datetime.now().strftime("%d.%m.%Y %H:%M")
            
            # Получаем следующий номер строки
            next_row = self.google_sheets_api.get_next_row_number()
            
            # Формируем строку для добавления
            row_data = [
                str(next_row),  # Номер
                current_date,   # Дата входа
                trade_data["symbol"],  # Символ
                trade_data["entry_price"],  # Цена входа
                trade_data["direction"],  # Направление
                trade_data["exit_price"],  # Цена выхода
                "X10",  # Плечо (по умолчанию)
                trade_data["stop_loss"],  # Стоп-лосс
                "$1 000,00",  # Размер позиции (по умолчанию)
                "",  # P&L (будет рассчитан автоматически)
                current_date  # Дата выхода
            ]
            
            # Добавляем строку в таблицу
            success = self.google_sheets_api.add_trade_row(row_data)
            
            if success:
                self.logger.info(f"✅ Сделка добавлена в таблицу: {trade_data['symbol']} {trade_data['direction']}")
                return True
            else:
                self.logger.error("❌ Ошибка добавления сделки в таблицу")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка добавления сделки: {e}")
            return False
    
    def handle_callback_query(self, callback_data: str, user_id: str) -> bool:
        """Обработать callback query от кнопок"""
        try:
            if callback_data == "add_trade":
                return self.send_symbol_selection(user_id)
            
            elif callback_data == "status":
                # Отправляем статус бота
                status_data = {
                    "processed_signals": 0,
                    "open_positions": 0,
                    "max_positions": 5,
                    "last_check": datetime.now().strftime("%H:%M:%S")
                }
                return self.send_status(status_data)
            
            elif callback_data.startswith("symbol_"):
                symbol = callback_data.replace("symbol_", "")
                return self.send_direction_selection(user_id, symbol)
            
            elif callback_data.startswith("direction_"):
                direction = callback_data.replace("direction_", "")
                if user_id in self.user_states:
                    symbol = self.user_states[user_id].get("symbol", "")
                    return self.send_price_input(user_id, symbol, direction)
            
            elif callback_data == "confirm_trade":
                if user_id in self.user_states and "trade_data" in self.user_states[user_id]:
                    trade_data = self.user_states[user_id]["trade_data"]
                    success = self.add_trade_to_sheet(trade_data)
                    
                    if success:
                        message = f"""✅ СДЕЛКА ДОБАВЛЕНА!

🪙 Символ: {trade_data['symbol']}
📈 Направление: {trade_data['direction']}
💵 Цена входа: {trade_data['entry_price']}
💰 Цена выхода: {trade_data['exit_price']}
🛑 Стоп-лосс: {trade_data['stop_loss']}

Сделка успешно добавлена в Google таблицу!"""
                    else:
                        message = "❌ Ошибка добавления сделки в таблицу"
                    
                    # Очищаем состояние пользователя
                    if user_id in self.user_states:
                        del self.user_states[user_id]
                    
                    return self.send_message(message)
            
            elif callback_data == "cancel":
                # Очищаем состояние пользователя
                if user_id in self.user_states:
                    del self.user_states[user_id]
                
                return self.send_message("❌ Операция отменена")
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки callback: {e}")
            return False
    
    def handle_text_message(self, text: str, user_id: str) -> bool:
        """Обработать текстовое сообщение"""
        try:
            if user_id not in self.user_states:
                # Если пользователь не в процессе добавления сделки
                if text.lower() in ["/start", "/add", "добавить", "сделка"]:
                    return self.send_add_trade_menu()
                elif text.lower() in ["/status", "статус"]:
                    status_data = {
                        "processed_signals": 0,
                        "open_positions": 0,
                        "max_positions": 5,
                        "last_check": datetime.now().strftime("%H:%M:%S")
                    }
                    return self.send_status(status_data)
                else:
                    return self.send_message("Используйте /add для добавления сделки или /status для просмотра статуса")
            
            # Обработка ввода данных для сделки
            state = self.user_states[user_id].get("state", "")
            
            if state == "entering_entry_price":
                # Проверяем, что введена корректная цена
                if self.is_valid_price(text):
                    symbol = self.user_states[user_id].get("symbol", "")
                    direction = self.user_states[user_id].get("direction", "")
                    return self.send_exit_price_input(user_id, symbol, direction, text)
                else:
                    return self.send_message("❌ Неверный формат цены. Введите число (например: 0.33591)")
            
            elif state == "entering_exit_price":
                if self.is_valid_price(text):
                    symbol = self.user_states[user_id].get("symbol", "")
                    direction = self.user_states[user_id].get("direction", "")
                    entry_price = self.user_states[user_id].get("entry_price", "")
                    return self.send_stop_loss_input(user_id, symbol, direction, entry_price, text)
                else:
                    return self.send_message("❌ Неверный формат цены. Введите число (например: 0.34001)")
            
            elif state == "entering_stop_loss":
                if self.is_valid_price(text):
                    symbol = self.user_states[user_id].get("symbol", "")
                    direction = self.user_states[user_id].get("direction", "")
                    entry_price = self.user_states[user_id].get("entry_price", "")
                    exit_price = self.user_states[user_id].get("exit_price", "")
                    
                    trade_data = {
                        "symbol": symbol,
                        "direction": direction,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "stop_loss": text
                    }
                    
                    return self.send_trade_confirmation(user_id, trade_data)
                else:
                    return self.send_message("❌ Неверный формат цены. Введите число (например: 0.33181)")
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки текстового сообщения: {e}")
            return False
    
    def is_valid_price(self, price_str: str) -> bool:
        """Проверить, является ли строка корректной ценой"""
        try:
            price = float(price_str.replace(",", "."))
            return price > 0
        except:
            return False
    
    def test_connection(self) -> bool:
        """Проверить подключение к Telegram"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                self.logger.info(f"✅ Telegram Bot подключен: {bot_info.get('result', {}).get('username', 'Unknown')}")
                return True
            else:
                self.logger.error(f"❌ Ошибка подключения к Telegram: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка тестирования Telegram: {e}")
            return False 

    def get_updates(self, offset=0, timeout=10):
        """Получить новые сообщения через getUpdates"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {'timeout': timeout, 'offset': offset}
            response = requests.get(url, params=params, timeout=timeout+5)
            if response.status_code == 200:
                return response.json().get('result', [])
            else:
                self.logger.error(f"❌ Ошибка getUpdates: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"❌ Ошибка getUpdates: {e}")
            return []

    def run_polling(self, poll_interval=1):
        """Запустить polling-цикл для обработки сообщений Telegram"""
        self.logger.info("🚦 Запуск polling Telegram...")
        offset = 0
        while True:
            updates = self.get_updates(offset)
            for update in updates:
                offset = update['update_id'] + 1
                if 'message' in update:
                    user_id = str(update['message']['from']['id'])
                    text = update['message'].get('text', '')
                    if text:
                        self.handle_text_message(text, user_id)
                elif 'callback_query' in update:
                    user_id = str(update['callback_query']['from']['id'])
                    data = update['callback_query']['data']
                    self.handle_callback_query(data, user_id)
            time.sleep(poll_interval) 