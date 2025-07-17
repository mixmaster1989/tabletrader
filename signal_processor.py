#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчик торговых сигналов из Google таблицы
"""

import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
from google_sheets_api import GoogleSheetsAPI
from bybit_api import BybitAPI
from telegram_bot import TelegramBot

class SignalProcessor:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Инициализация компонентов
        self.google_sheets = GoogleSheetsAPI(
            config['GOOGLE_CREDENTIALS_FILE'],
            config['GOOGLE_SHEETS_ID']
        )
        
        self.bybit = BybitAPI(
            config['BYBIT_API_KEY'],
            config['BYBIT_API_SECRET'],
            config['BYBIT_TESTNET']
        )
        
        self.telegram = TelegramBot(
            config['TELEGRAM_BOT_TOKEN'],
            config['TELEGRAM_CHAT_ID']
        )
        
        # Отслеживание обработанных сигналов
        self.processed_signals = set()
        self.last_check_time = None
        
        self.logger.info("✅ SignalProcessor инициализирован")
    
    def process_signals(self) -> Dict:
        """Основной метод обработки сигналов"""
        try:
            # Читаем сигналы из Google таблицы
            signals = self.google_sheets.read_signals()
            
            if not signals:
                self.logger.info("📊 Новых сигналов нет")
                return {'processed': 0, 'errors': 0}
            
            processed_count = 0
            error_count = 0
            
            for signal in signals:
                try:
                    # Проверяем, не обработан ли уже сигнал
                    signal_id = f"{signal['symbol']}_{signal['row']}"
                    if signal_id in self.processed_signals:
                        continue
                    
                    # Проверяем возможность входа
                    if self._can_enter_position(signal):
                        # Выполняем вход в позицию
                        result = self._execute_signal(signal)
                        
                        if result['success']:
                            self.processed_signals.add(signal_id)
                            processed_count += 1
                            
                            # Отправляем уведомление
                            self._send_notification(signal, result)
                            
                            # Отмечаем как обработанный
                            self.google_sheets.mark_signal_processed(signal['row'])
                        else:
                            error_count += 1
                            self.logger.error(f"❌ Ошибка выполнения сигнала: {result['error']}")
                    else:
                        self.logger.info(f"⏸️ Сигнал {signal['symbol']} пропущен - условия не подходят")
                        
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"❌ Ошибка обработки сигнала {signal.get('symbol', 'Unknown')}: {e}")
            
            self.last_check_time = datetime.now()
            
            return {
                'processed': processed_count,
                'errors': error_count,
                'total_signals': len(signals)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки сигналов: {e}")
            return {'processed': 0, 'errors': 1}
    
    def _can_enter_position(self, signal: Dict) -> bool:
        """Проверка возможности входа в позицию"""
        try:
            # Проверяем количество открытых позиций
            positions = self.bybit.get_positions()
            if len(positions) >= self.config['MAX_POSITIONS']:
                self.logger.warning(f"⚠️ Достигнут лимит позиций ({self.config['MAX_POSITIONS']})")
                return False
            
            # Проверяем, нет ли уже позиции по этой монете
            for pos in positions:
                if pos.get('symbol') == signal['symbol']:
                    self.logger.info(f"⏸️ Позиция по {signal['symbol']} уже открыта")
                    return False
            
            # Проверяем цену входа
            current_price = self.bybit.get_last_price(signal['symbol'])
            if not current_price:
                self.logger.error(f"❌ Не удалось получить цену для {signal['symbol']}")
                return False
            
            # Проверяем отклонение цены от сигнала
            price_deviation = abs(current_price - signal['entry_price']) / signal['entry_price'] * 100
            if price_deviation > self.config['PRICE_DEVIATION']:
                self.logger.warning(f"⚠️ Цена {signal['symbol']} отклонена на {price_deviation:.2f}%")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки возможности входа: {e}")
            return False
    
    def _execute_signal(self, signal: Dict) -> Dict:
        """Выполнение торгового сигнала"""
        try:
            # Подготавливаем параметры ордера
            order_params = {
                'symbol': signal['symbol'],
                'side': signal['direction'],
                'size': self.config['DEFAULT_POSITION_SIZE'],
                'leverage': self.config['DEFAULT_LEVERAGE'],
                'take_profit': signal['take_profit'],
                'stop_loss': signal['stop_loss']
            }
            
            # Открываем позицию
            result = self.bybit.open_order_with_tp_sl(order_params)
            
            if result.get('retCode') == 0:
                return {
                    'success': True,
                    'order_id': result.get('result', {}).get('orderId'),
                    'price': result.get('result', {}).get('avgPrice'),
                    'size': order_params['size']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('retMsg', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_notification(self, signal: Dict, result: Dict):
        """Отправка уведомления о сделке"""
        try:
            message = f"""🚀 НОВАЯ СДЕЛКА ОТКРЫТА

📊 Монета: {signal['symbol']}
📈 Направление: {signal['direction']}
💰 Цена входа: {signal['entry_price']}
📏 Размер: {result['size']}
🎯 Take Profit: {signal['take_profit']}
🛑 Stop Loss: {signal['stop_loss']}

✅ Статус: Успешно
🆔 Order ID: {result.get('order_id', 'N/A')}

⏰ {datetime.now().strftime('%H:%M:%S UTC')}"""
            
            self.telegram.send_message(message)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки уведомления: {e}")
    
    def get_status(self) -> Dict:
        """Получить статус процессора"""
        return {
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'processed_signals': len(self.processed_signals),
            'open_positions': len(self.bybit.get_positions()),
            'max_positions': self.config['MAX_POSITIONS']
        } 