#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot для Google Signals Bot
"""

import logging
import requests
from typing import Optional

class TelegramBot:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("✅ Telegram Bot инициализирован")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Отправить сообщение в Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("✅ Сообщение отправлено в Telegram")
                return True
            else:
                self.logger.error(f"❌ Ошибка отправки в Telegram: {response.status_code} {response.text}")
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
📈 Открытых позиций: {status_data.get('open_positions', 0)}
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