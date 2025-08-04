#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчик торговых сигналов из Google таблицы
"""

import logging
import time
import json
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from enum import Enum
from binance_api import BinanceAPI
from google_sheets_api import GoogleSheetsAPI
from telegram_bot import TelegramBot

class OrderStatus(Enum):
    PLACED = "размещен"
    FILLED = "исполнен"
    CLOSED = "закрыт"
    ERROR = "ошибка"

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
        self.processed_signals_file = 'processed_signals.json'
        self.processed_signals = self._load_processed_signals()
        self.last_check_time = None
        
        self.logger.info("✅ SignalProcessor инициализирован")

    def _load_processed_signals(self) -> Dict:
        """Загружает обработанные сигналы из файла."""
        try:
            with open(self.processed_signals_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_processed_signals(self):
        """Сохраняет обработанные сигналы в файл."""
        try:
            with open(self.processed_signals_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_signals, f, ensure_ascii=False, indent=4)
            self.logger.info(f"💾 Обработанные сигналы сохранены в {self.processed_signals_file}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения обработанных сигналов: {e}")
    
    def get_status(self) -> Dict:
        """Получить статус бота"""
        try:
            # Получаем количество открытых позиций
            positions = self.exchange.get_positions()
            open_positions = len([p for p in positions if float(p.get('positionAmt', 0)) != 0])
            
            # Получаем количество обработанных сигналов
            processed_signals = len(self.processed_signals)
            
            return {
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'processed_signals': processed_signals,
                'open_positions': open_positions
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статуса: {e}")
            return {
                'last_check': 'Ошибка',
                'processed_signals': 0,
                'open_positions': 0
            }
    
    def process_signals(self) -> Dict:
        """Основной метод обработки сигналов"""
        try:
            # 1. Проверка статуса размещенных ордеров (PLACED)
            for signal_id, signal_data in list(self.processed_signals.items()):
                if signal_data.get('status') == OrderStatus.PLACED.value:
                    # Проверяем условия отмены ордера
                    if self._check_order_cancellation_conditions(signal_id, signal_data):
                        # Отменяем ордер
                        if self.exchange.cancel_order(signal_data['order_id'], signal_data['symbol']):
                            self.processed_signals[signal_id]['status'] = OrderStatus.CLOSED.value
                            self.telegram.send_message(f"❌ Ордер {signal_id} отменен по условиям (таймаут или достижение TP)")
                            self._save_processed_signals()
                            continue
                        else:
                            # Если отмена не удалась, отмечаем как ошибку и отправляем уведомление
                            self.processed_signals[signal_id]['status'] = OrderStatus.ERROR.value
                            self.telegram.send_message(f"⚠️ ВНИМАНИЕ! Не удалось отменить ордер {signal_id} автоматически!\n\n"
                                                      f"🔍 Проверьте вручную на бирже:\n"
                                                      f"• Если ордер уже отменен - все хорошо\n"
                                                      f"• Если ордер активен - отмените вручную\n\n"
                                                      f"📊 Детали ордера:\n"
                                                      f"• Символ: {signal_data['symbol']}\n"
                                                      f"• Order ID: {signal_data['order_id']}\n"
                                                      f"• Направление: {signal_data['direction']}\n"
                                                      f"• Цена входа: {signal_data['entry_price']}")
                            self._save_processed_signals()
                            continue
                    
                    order_status = self.exchange.check_order_status(signal_data['order_id'], signal_data['symbol'])
                    if order_status == 'NOT_FOUND':
                        self.logger.info(f"❌ Ордер {signal_id} не найден!")
                        self.processed_signals[signal_id]['status'] = OrderStatus.ERROR.value
                        self.telegram.send_message(f"⚠️ Ордер {signal_id} не найден!")
                        continue
                    if order_status == None:
                        self.logger.info(f"⚠️ Ошибка получения статуса ордера {signal_id}!")
                        self.processed_signals[signal_id]['status'] = OrderStatus.ERROR.value
                        self.telegram.send_message(f"⚠️ Ошибка получения статуса ордера {signal_id}!")
                        continue
                    if order_status == 'FILLED':
                        self.logger.info(f"✅ Ордер {signal_id} исполнен!")
                        self.processed_signals[signal_id]['status'] = OrderStatus.FILLED.value
                        self._send_notification(self.processed_signals[signal_id], status=OrderStatus.FILLED)

                        # Устанавливаем TP/SL для новой позиции
                        tp_sl_params = {
                            'symbol': signal_data['symbol'],
                            'direction': signal_data['direction'],
                            'size': signal_data['size'],
                            'take_profit': signal_data['take_profit'],
                            'stop_loss': signal_data['stop_loss']
                        }
                        tp_sl_result = self.exchange.place_tp_sl_for_position(tp_sl_params)
                        if tp_sl_result.get('success'):
                            self.logger.info(f"✅ TP/SL для {signal_id} успешно установлены. TP: {signal_data['take_profit']}, SL: {signal_data['stop_loss']}")
                            self.processed_signals[signal_id].update(tp_sl_result.get('orders', {}))
                            self.telegram.send_message(f"✅ TP/SL для {signal_id} успешно установлены. TP: {signal_data['take_profit']}, SL: {signal_data['stop_loss']}")
                        else:
                            self.logger.error(f"❌ Не удалось установить TP/SL для {signal_id}. Ошибка: {tp_sl_result.get('error')}")
                            
                            self.telegram.send_error(f"❌ Ошибка установки TP/SL для {signal_id}, Попробуйте другие значения")
                    elif order_status in ['CANCELED', 'EXPIRED']:
                        self.logger.warning(f"❌ Ордер {signal_id} отменен или истек.")
                        self.processed_signals[signal_id]['status'] = OrderStatus.CLOSED.value
                        self.telegram.send_message(f"❌ Ордер {signal_id} отменен или истек.")

            # 2. Синхронизация закрытых позиций (FILLED -> CLOSED)
            positions = self.exchange.get_positions()
            open_position_symbols = {p['symbol'] for p in positions}
            for signal_id, signal_data in list(self.processed_signals.items()):
                if signal_data.get('status') == OrderStatus.FILLED.value:
                    position_symbol = signal_data['symbol'] + 'USDT'
                    if position_symbol not in open_position_symbols:
                        self.logger.info(f"🔄 Позиция по сигналу {signal_id} закрыта на бирже.")
                        self.processed_signals[signal_id]['status'] = OrderStatus.CLOSED.value
                        self.telegram.send_message(f"✅ Позиция по сигналу {signal_id} закрыта.")

            # Читаем сигналы из Google таблицы
            signals = self.google_sheets.read_signals()
            
            if not signals:
                self.logger.info("📊 Сигналов нет")
                return {'processed': 0, 'errors': 0}
            
            processed_count = 0
            error_count = 0

            for signal in signals:
                try:
                    signal_id = f"{signal['symbol']}_{signal['id']}"
                    # Пропускаем, если сигнал уже в работе (не в статусе ERROR)
                    if signal_id in self.processed_signals and \
                       self.processed_signals[signal_id].get('status') not in [OrderStatus.ERROR.value]:
                        # Логика обновления entry_price для еще не исполненных ордеров
                        if self.processed_signals[signal_id].get('status') == OrderStatus.PLACED.value and \
                           (signal['entry_price'] != self.processed_signals[signal_id]['entry_price']):
                            self._set_new_entry_price(signal_id, signal)
                        # Логика обновления TP/SL для уже исполненных ордеров
                        if self.processed_signals[signal_id].get('status') == OrderStatus.FILLED.value and \
                           (signal['take_profit'] != self.processed_signals[signal_id]['take_profit'] or \
                            signal['stop_loss'] != self.processed_signals[signal_id]['stop_loss']):
                            self._update_tp_sl(signal, signal_id)
                        continue

                    # Пропускаем, если другой сигнал по этой же монете уже в работе
                    
                    is_signal_in_work = False
                    
                    for processed_signal_id, processed_signal in self.processed_signals.items():
                        if processed_signal['symbol'] == signal['symbol'] and \
                           processed_signal.get('status') not in [OrderStatus.ERROR.value, OrderStatus.CLOSED.value]:
                            is_signal_in_work = True
                            break

                    if is_signal_in_work:
                        continue

                    signal_time = signal['date']
                    end_active = signal_time + timedelta(minutes=20)
                    now = datetime.now()

                    if now < signal_time:
                        self.logger.info(f"🕒 Сигнал в строке {signal['id']} ещё не наступил (до времени: {(signal_time - now).total_seconds() / 60:.1f} мин)")
                        continue
                    elif now > end_active:
                        continue
                    
                    balance = self.exchange.get_balance() * 0.95 
                    if balance < signal['size']:
                        self.logger.warning(f"⚠️ Недостаточно средств на балансе для сигнала {signal['symbol']} в строке {signal['id']}")
                        signal['size'] = balance

                    posSize = self.exchange.calculate_position_size(signal['symbol'], signal['size'] * signal['leverage'],signal['entry_price'])
                    
                    # Вход в позицию (выставление лимитного ордера)
                    if self._can_enter_position(signal):
                        self.logger.info(f"🚀 Выполнение сигнала {signal_id}")
                        result = self._execute_signal(signal, posSize)
                        
                        if result['success']:
                            self.processed_signals[signal_id] = {
                                'status': OrderStatus.PLACED.value,
                                'id': signal['id'],
                                'order_id': result.get('order_id'),
                                'symbol': signal['symbol'],
                                'direction': signal['direction'],
                                'entry_price': signal['entry_price'],
                                'take_profit': signal['take_profit'],
                                'stop_loss': signal['stop_loss'],
                                'size': posSize,
                                'order_time': datetime.now().isoformat() # Время размещения ордера
                            }
                            processed_count += 1
                            self._send_notification(self.processed_signals[signal_id], status=OrderStatus.PLACED)
                            break # Выходим после успешного размещения одного ордера
                        else:
                            error_count += 1
                            self.logger.error(f"❌ Ошибка выполнения сигнала {signal.get('symbol', 'Unknown')} в строке {signal['id']}: {result['error']}")
                    else:
                        self.logger.info(f"⏸️ Сигнал {signal['symbol']} пропущен - условия не подходят")
                        
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"❌ Ошибка обработки сигнала {signal.get('symbol', 'Unknown')} в строке {signal['id']}: {e}")
            
            self._save_processed_signals() # Сохраняем состояние после цикла
            self.last_check_time = datetime.now()
            
            return {
                'processed': processed_count,
                'errors': error_count,
                'total_signals': len(signals)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки сигналов: {e}")
            self._save_processed_signals() # Сохраняем состояние даже если была ошибка
            return {'processed': 0, 'errors': 1}

    def _update_tp_sl(self, signal: Dict, signal_id: str):
        """Обновляет Take Profit и Stop Loss для активной позиции."""
        try:
            self.logger.info(f"📝 Обнаружено изменение TP/SL для {signal['symbol']}. Обновление TP/SL...")
            update_params = {
                'symbol': signal['symbol'],
                'take_profit': signal['take_profit'],
                'stop_loss': signal['stop_loss']
            }
            update_result = self.exchange.modify_trading_stop(update_params)
            if update_result['success']:
                self.processed_signals[signal_id]['take_profit'] = signal['take_profit']
                self.processed_signals[signal_id]['stop_loss'] = signal['stop_loss']
                self._save_processed_signals()
                self.logger.info(f"✅ TP/SL для {signal_id} успешно обновлен. TP: {signal['take_profit']}, SL: {signal['stop_loss']}")
                self.telegram.send_message(f"✅ TP/SL для {signal_id} успешно обновлен. TP: {signal['take_profit']}, SL: {signal['stop_loss']}")
            else:
                error_msg = update_result.get('error', 'Неизвестная ошибка')
                self.processed_signals[signal_id]['status'] = OrderStatus.ERROR.value
                self.logger.error(f"❌ Ошибка обновления TP/SL для {signal_id}: {error_msg}")
                self.telegram.send_error(f"❌ Ошибка обновления TP/SL для {signal_id}: {error_msg}")
        except Exception as e:
            self.processed_signals[signal_id]['status'] = OrderStatus.ERROR.value
            self.logger.error(f"❌ Исключение при обновлении TP/SL для {signal_id}: {e}")
            self.telegram.send_error(f"❌ Исключение при обновлении TP/SL для {signal_id}")
    
    def _can_enter_position(self, signal: Dict) -> bool:
        """Проверка возможности входа в позицию"""
        try:
            positions = self.exchange.get_positions()
            # Проверяем, нет ли уже позиции по этой монете
            for pos in positions:
                if pos.get('symbol') == signal['symbol'] + 'USDT':
                    self.logger.info(f"⏸️ Позиция по {signal['symbol']} уже открыта")
                    return False

            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки возможности входа: {e}")
            return False

    def _set_new_entry_price(self, signal_id: str, signal: Dict):
        try:
            posSize = self.exchange.calculate_position_size(signal['symbol'], signal['size'] * signal['leverage'],signal['entry_price'])
            result = self._execute_signal(signal, posSize)
            if result['success']:
                self.logger.info(f"✅ Цена входа успешно изменена для {signal_id}")
                self.telegram.send_message(f"✅ Цена входа успешно изменена для {signal_id}")
                self.processed_signals[signal_id]['entry_price'] = signal['entry_price']
                self.processed_signals[signal_id]['order_id'] = result.get('order_id')
                self.processed_signals[signal_id]['order_time'] = datetime.now().isoformat()
                self._save_processed_signals()
            else:
                self.processed_signals[signal_id]['status'] = OrderStatus.ERROR.value
                self.logger.error(f"❌ Ошибка при изменении цены входа {signal_id}: {result['error']}")
                self.telegram.send_error(f"❌ Ошибка при изменении цены входа {signal_id}")

        except Exception as e:
            self.processed_signals[signal_id]['status'] = OrderStatus.ERROR.value
            self.logger.error(f"❌ Ошибка при изменении цены входа {signal_id}: {e}")
    
    def _execute_signal(self, signal: Dict, posSize: float) -> Dict:
        """Выполнение торгового сигнала"""
        try:
            order_params = {
                'symbol': signal['symbol'],
                'side': signal['direction'],
                'size': posSize,
                'leverage': signal['leverage'],
                'price': signal['entry_price']
            }
            
            # Выставляем лимитный ордер
            result = self.exchange.place_limit_order(order_params)

            if result.get('success'):
                return {
                    'success': True,
                    'order_id': result.get('orderId'),
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
    
    def _check_order_cancellation_conditions(self, signal_id: str, signal_data: Dict) -> bool:
        """
        Проверяет условия для отмены ордера:
        1. Прошло 20 минут с размещения
        2. Цена достигла тейк-профита без исполнения ордера
        """
        try:
            # Проверяем, есть ли время размещения ордера
            if 'order_time' not in signal_data:
                return False
            
            order_time = datetime.fromisoformat(signal_data['order_time'])
            current_time = datetime.now()
            
            # Правило 1: Таймаут 20 минут
            time_diff = current_time - order_time
            if time_diff.total_seconds() > 20 * 60:  # 20 минут в секундах
                self.logger.warning(f"⏰ Ордер {signal_id} не исполнен в течение 20 минут")
                return True
            
            # Правило 2: Проверка достижения тейк-профита
            current_price = self.exchange.get_last_price(signal_data['symbol'])
            if current_price is None:
                return False
            
            take_profit = signal_data['take_profit']
            direction = signal_data['direction']
            
            # Для LONG: если цена >= TP, но ордер не исполнен
            if direction == 'LONG' and current_price >= take_profit:
                self.logger.warning(f"🎯 Ордер {signal_id}: цена {current_price} достигла TP {take_profit}")
                return True
            
            # Для SHORT: если цена <= TP, но ордер не исполнен
            if direction == 'SHORT' and current_price <= take_profit:
                self.logger.warning(f"🎯 Ордер {signal_id}: цена {current_price} достигла TP {take_profit}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки условий отмены ордера {signal_id}: {e}")
            return False

    def _send_notification(self, signal_data: Dict, status: OrderStatus):
        """Отправка уведомления о сделке в зависимости от статуса."""
        try:
            if status == OrderStatus.PLACED:
                message = f"""🔵 ОРДЕР РАЗМЕЩЕН

📊 ID: {signal_data['symbol']}_{signal_data['id']}
📈 Направление: {signal_data['direction']}
💰 Цена входа: {signal_data['entry_price']}$
🎯 Take Profit: {signal_data['take_profit']}$
🛑 Stop Loss: {signal_data['stop_loss']}$

🆔 Order ID: {signal_data.get('order_id', 'N/A')}
⏰ {datetime.now().strftime('%H:%M:%S UTC')}"""
            elif status == OrderStatus.FILLED:
                message = f"""✅ ОРДЕР ИСПОЛНЕН

📊 ID: {signal_data['symbol']}_{signal_data['id']}
📈 Направление: {signal_data['direction']}
💰 Цена входа: {signal_data['entry_price']}$

✅ Позиция открыта!
🆔 Order ID: {signal_data.get('order_id', 'N/A')}
⏰ {datetime.now().strftime('%H:%M:%S UTC')}"""
            else:
                return

            self.telegram.send_message(message)

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки уведомления: {e}")
    
    def get_status(self) -> Dict:
        """Получить статус процессора"""
        return {
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'processed_signals': len(self.processed_signals),
            'open_positions': len(self.exchange.get_positions()),
        } 