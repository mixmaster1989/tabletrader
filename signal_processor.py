#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчик торговых сигналов из Google таблицы
"""

import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
from binance_api import BinanceAPI
from google_sheets_api import GoogleSheetsAPI
from telegram_bot import TelegramBot

class SignalProcessor:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Инициализация компонентов
        self.google_sheets = GoogleSheetsAPI(
            config['GOOGLE_CREDENTIALS_FILE'],
            config['GOOGLE_SHEETS_ID'],
            float(config["DEFAULT_POSITION_SIZE"]),
            int(config["DEFAULT_LEVERAGE"]),
        )
        
        self.exchange = BinanceAPI(
            config['BINANCE_API_KEY'],
            config['BINANCE_API_SECRET'],
            config['BINANCE_TESTNET']
        )
        
        self.telegram = TelegramBot(
            config['TELEGRAM_BOT_TOKEN'],
            config['TELEGRAM_CHAT_ID']
        )
        
        # Отслеживание обработанных сигналов
        self.processed_signals = dict()
        self.last_check_time = None
        
        self.logger.info("✅ SignalProcessor инициализирован")
    
    def process_signals(self) -> Dict:
        """Основной метод обработки сигналов"""
        try:
            positions = self.exchange.get_positions()
            if positions:
                self.logger.info(f"📊 Открыто {len(positions)} позиций")

            for pos in positions:
                self.logger.info(f"📊 Позиция: {pos['symbol']} {pos['side']} {pos['size']} USDT")

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
                    if signal_id in self.processed_signals and self.processed_signals[signal_id]['processed']:
                        # processed_signal = self.processed_signals[signal_id]
                        # Проверяем, изменились ли TP или SL
                        # if signal['take_profit'] != processed_signal['take_profit'] or \
                        #    signal['stop_loss'] != processed_signal['stop_loss']:
                        #     try:
                        #         self.logger.info(f"📝 Обнаружено изменение TP/SL для {signal['symbol']}. Обновление ордера...")
                        #         update_params = {
                        #             'symbol': signal['symbol'],
                        #             'take_profit': signal['take_profit'],
                        #             'stop_loss': signal['stop_loss']
                        #         }
                        #         update_result = self.exchange.modify_trading_stop(update_params)
                        #         if update_result['success']:
                        #             # Обновляем сохраненные данные
                        #             self.processed_signals[signal_id]['take_profit'] = signal['take_profit']
                        #             self.processed_signals[signal_id]['stop_loss'] = signal['stop_loss']
                        #             self.logger.info(f"✅ TP/SL для {signal['symbol']} успешно обновлен.")
                        #         else:
                        #             self.logger.error(f"❌ Ошибка обновления TP/SL для {signal['symbol']}: {update_result['error']}")
                        #     except Exception as e:
                        #         self.logger.error(f"❌ Ошибка обновления TP/SL для {signal['symbol']}: {e}")
                        continue

                    usdtSize = signal['size']

                    current_price = self.exchange.get_last_price(signal['symbol'])

                    posSize = self.exchange.calculate_position_size(signal['symbol'], usdtSize,current_price)
                    
                    # Проверяем возможность входа
                    if self._can_enter_position(signal):
                        print(signal)
                        # Выполняем вход в позицию
                        result = self._execute_signal(signal, posSize)
                        
                        if result['success']:
                            self.processed_signals[signal_id] = {
                                "processed": True,
                                "order_id": result.get('order_id'),
                                "tp_order_id": result.get('tp_order_id'),
                                "sl_order_id": result.get('sl_order_id'),
                                "take_profit": signal['take_profit'],
                                "stop_loss": signal['stop_loss'],
                            }
                            processed_count += 1
                            
                            # Отправляем уведомление
                            self._send_notification(signal, {**result, 'usdt': usdtSize})
                            
                            # Отмечаем как обработанный
                            # self.google_sheets.mark_signal_processed(signal['row'])
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
            positions = self.exchange.get_positions()
            print(positions)
            # Проверяем, нет ли уже позиции по этой монете
            for pos in positions:
                if pos.get('symbol') == signal['symbol'] + 'USDT':
                    self.logger.info(f"⏸️ Позиция по {signal['symbol']} уже открыта")
                    return False
            
            # Проверяем цену входа
            current_price = self.exchange.get_last_price(signal['symbol'])
            if not current_price:
                self.logger.error(f"❌ Не удалось получить цену для {signal['symbol']}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки возможности входа: {e}")
            return False
    
    def _execute_signal(self, signal: Dict, posSize: float) -> Dict:
        """Выполнение торгового сигнала"""
        try:
            order_params = {
                'symbol': signal['symbol'],
                'side': signal['direction'],
                'size': posSize,
                'leverage': signal['leverage'],
                'take_profit': signal['take_profit'],
                'stop_loss': signal['stop_loss']
            }
            
            # Открываем позицию
            result = self.exchange.open_order_with_tp_sl(order_params)
            
            if result.get('success'):
                return {
                    'success': True,
                    'order_id': result.get('orderId'),
                    'tp_order_id': result.get('tpOrderId'),
                    'sl_order_id': result.get('slOrderId'),
                    'price': result.get('avgPrice'),
                    'size': order_params['size']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
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
💰 Цена входа: {signal['entry_price']}$
📏 Размер: {result['size']}
📏 Размер (USDT): {result['usdt']}$
🎯 Take Profit: {signal['take_profit']}$
🛑 Stop Loss: {signal['stop_loss']}$

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
            'open_positions': len(self.exchange.get_positions()),
            'max_positions': self.config['MAX_POSITIONS']
        } 