#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Sheets API для чтения торговых сигналов
"""

import logging
from typing import List, Dict, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
from utils import get_bybit_symbol

class GoogleSheetsAPI:
    def __init__(self, credentials_file: str, spreadsheet_id: str, bybit_api=None):
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.bybit_api = bybit_api
        self.service = None
        self.logger = logging.getLogger(__name__)
        
        # Области доступа для Google Sheets
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        self._initialize_service()
    
    def _initialize_service(self):
        """Инициализация Google Sheets API"""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_file, scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            self.logger.info("✅ Google Sheets API инициализирован")
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Google Sheets API: {e}")
            raise
    
    def read_signals(self, range_name: str = "Trades!A:Q") -> List[Dict]:
        """
        Читать сигналы из Google таблицы
        
        Ожидаемые колонки:
        A - Монета (BTCUSDT)
        B - Цена входа (50000)
        C - Take Profit (52000)
        D - Stop Loss (48000)
        E - Направление (LONG/SHORT)
        """
        try:
            self.logger.info(f"📊 Читаем диапазон: {range_name}")
            self.logger.info(f"📊 ID таблицы: {self.spreadsheet_id}")
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            self.logger.info(f"🔍 СЫРЫЕ ДАННЫЕ ОТ GOOGLE: {result}")
            
            values = result.get('values', [])
            
            self.logger.info(f"🔍 ВСЕ СТРОКИ: {values}")
            self.logger.info(f"🔍 КОЛИЧЕСТВО СТРОК: {len(values)}")
            
            if not values:
                self.logger.warning("⚠️ Таблица пуста")
                return []
            
            signals = []
            self.logger.info(f"🔍 Обрабатываем {len(values)} строк из таблицы")
            for i, row in enumerate(values, start=1):  # Начинаем с 1 строки
                self.logger.info(f"🔍 Строка {i}: {row} (колонок: {len(row)})")
                try:
                    self.logger.info(f"🔍 Обрабатываем строку {i}: {row}")
                    self.logger.info(f"🔍 Проверяем условие len(row) >= 7: {len(row)} >= 7 = {len(row) >= 7}")
                    if len(row) >= 7:  # Минимум 7 колонок (A:G)
                        # Пропускаем пустые строки и заголовки
                        if (not row[1] or row[1].strip() == '' or 
                            row[1].strip().lower() in ['монета', 'дата входа', 'дата', 'символ', 'направление'] or
                            row[1].strip().isdigit() == False and len(row[1].strip()) < 3):
                            self.logger.info(f"🔍 Пропускаем строку {i} - заголовок или пустая")
                            continue
                            
                        self.logger.info(f"🔍 Создаем сигнал для строки {i}")
                        signal = {
                            'row': i,
                            'entry_date': row[1].strip() if len(row) > 1 and row[1] else '',
                            'symbol': row[2].strip().upper() if len(row) > 2 and row[2] else '',
                            'entry_price': float(row[3].replace(',', '.')) if len(row) > 3 and row[3] else 0,
                            'direction': row[4].strip().upper() if len(row) > 4 and row[4] else '',
                            'exit_price': float(row[5].replace(',', '.')) if len(row) > 5 and row[5] else 0,
                            'stop_loss': float(row[7].replace(',', '.')) if len(row) > 7 and row[7] else 0,
                            'status': 'new'
                        }
                        
                        # Определяем статус сделки
                        if signal['exit_price'] > 0:
                            signal['status'] = 'closed'
                            signal['profit_loss'] = self._calculate_pnl(signal)
                            self.logger.info(f"🔍 Закрытая сделка: {signal['symbol']} {signal['direction']} - выход: {signal['exit_price']}, P&L: {signal['profit_loss']}")
                        else:
                            signal['status'] = 'open'
                            self.logger.info(f"🔍 ОТКРЫТАЯ сделка: {signal['symbol']} {signal['direction']} - вход: {signal['entry_price']}")
                        
                        # Отладочная информация
                        self.logger.info(f"🔍 Строка {i}: {signal}")
                        
                        # Валидация сигнала
                        if self._validate_signal(signal):
                            # Преобразуем тикер для Bybit
                            bybit_symbol = get_bybit_symbol(signal['symbol'])
                            if not bybit_symbol:
                                self.logger.error(f"❌ Нет соответствия для тикера {signal['symbol']} — сигнал пропущен")
                                continue
                            signal['bybit_symbol'] = bybit_symbol
                            signals.append(signal)
                            self.logger.info(f"✅ Валидный сигнал добавлен: {signal['symbol']} {signal['direction']}")
                        else:
                            self.logger.warning(f"⚠️ Невалидный сигнал в строке {i}: {signal}")
                    else:
                        self.logger.warning(f"⚠️ Неполная строка {i} (колонок: {len(row)}): {row}")
                        self.logger.warning(f"⚠️ Строка {i} не прошла проверку len(row) >= 7")
                        # Отладочная информация для строк с данными
                        if len(row) >= 3 and row[1] and not row[1].strip().isdigit():
                            self.logger.info(f"🔍 Строка с данными {i}: {row}")
                        
                except (ValueError, IndexError) as e:
                    self.logger.error(f"❌ Ошибка обработки строки {i}: {e}")
                    continue
            
            self.logger.info(f"📊 Прочитано {len(signals)} сигналов из Google таблицы")
            return signals
            
        except HttpError as e:
            self.logger.error(f"❌ Ошибка Google Sheets API: {e}")
            return []
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка: {e}")
            return []
    
    def _validate_signal(self, signal: Dict) -> bool:
        """Валидация торгового сигнала"""
        try:
            # Проверка символа
            if not signal['symbol'] or len(signal['symbol']) < 3:
                return False
            
            # Проверка цены входа
            if signal['entry_price'] <= 0:
                return False
            
            # Проверка направления
            if signal['direction'] not in ['LONG', 'SHORT']:
                return False
            
            # Принимаем все сделки (открытые и закрытые)
            # if signal['status'] == 'closed':
            #     return False
            
            # Проверка стоп-лосса
            if signal['stop_loss'] <= 0:
                return False
            
            # Проверка логики стоп-лосса
            if signal['direction'] == 'LONG':
                if signal['stop_loss'] >= signal['entry_price']:
                    return False
            else:  # SHORT
                if signal['stop_loss'] <= signal['entry_price']:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации сигнала: {e}")
            return False
    
    def mark_signal_processed(self, row: int, status: str = "processed"):
        """Отметить сигнал как обработанный (опционально)"""
        try:
            # Здесь можно добавить логику для отметки обработанных сигналов
            # Например, записать в отдельную колонку или лист
            self.logger.info(f"✅ Сигнал в строке {row} отмечен как {status}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка отметки сигнала: {e}")
    
    def _calculate_pnl(self, signal: Dict) -> float:
        """Расчет прибыли/убытка по сделке"""
        try:
            entry_price = signal['entry_price']
            exit_price = signal['exit_price']
            direction = signal['direction']
            
            if direction == 'LONG':
                return ((exit_price - entry_price) / entry_price) * 100
            else:  # SHORT
                return ((entry_price - exit_price) / entry_price) * 100
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета P&L: {e}")
            return 0.0
    
    def get_current_price(self, signal: Dict) -> float:
        """Получить текущую цену через Bybit API"""
        try:
            symbol = signal.get('bybit_symbol', signal.get('symbol'))
            if self.bybit_api:
                price = self.bybit_api.get_last_price(symbol)
                return float(price) if price else 0.0
            return 0.0
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения цены {symbol}: {e}")
            return 0.0
    
    def backtest_signal(self, signal: Dict) -> Dict:
        """Бэктест сигнала с текущими ценами"""
        try:
            current_price = self.get_current_price(signal)
            if current_price == 0:
                return {'success': False, 'error': 'Не удалось получить текущую цену'}
            
            # Расчет текущего P&L для открытых сделок
            if signal['status'] == 'open':
                entry_price = signal['entry_price']
                direction = signal['direction']
                
                if direction == 'LONG':
                    current_pnl = ((current_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    current_pnl = ((entry_price - current_price) / entry_price) * 100
                
                signal['current_price'] = current_price
                signal['current_pnl'] = current_pnl
            
            return {'success': True, 'signal': signal}
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка бэктеста: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_last_update_time(self) -> Optional[str]:
        """Получить время последнего обновления таблицы"""
        try:
            # Здесь можно добавить логику для получения времени последнего обновления
            # Например, читать из отдельной ячейки или использовать метаданные
            return None
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения времени обновления: {e}")
            return None
    
    def get_next_row_number(self) -> int:
        """Получить следующий номер строки для добавления сделки"""
        try:
            # Читаем последние строки таблицы для определения следующего номера
            range_name = "Trades!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            # Ищем последний номер в колонке A
            last_number = 0
            for row in values:
                if row and row[0].strip().isdigit():
                    try:
                        number = int(row[0])
                        if number > last_number:
                            last_number = number
                    except ValueError:
                        continue
            
            return last_number + 1
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения следующего номера строки: {e}")
            return 1
    
    def add_trade_row(self, row_data: List[str]) -> bool:
        """Добавить новую строку с сделкой в таблицу"""
        try:
            # Находим следующую пустую строку в таблице
            range_name = "Trades!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            next_row = len(values) + 1
            
            # Формируем диапазон для записи
            write_range = f"Trades!A{next_row}:K{next_row}"
            
            # Записываем данные
            body = {
                'values': [row_data]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=write_range,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            self.logger.info(f"✅ Сделка добавлена в строку {next_row}: {row_data}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка добавления сделки: {e}")
            return False
    
    def update_trade_status(self, row: int, status: str, pnl: str = "") -> bool:
        """Обновить статус сделки и P&L"""
        try:
            # Обновляем статус в колонке J (P&L)
            range_name = f"Trades!J{row}"
            
            body = {
                'values': [[pnl]]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            self.logger.info(f"✅ Статус сделки в строке {row} обновлен: {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления статуса сделки: {e}")
            return False
    
    def get_trade_by_row(self, row: int) -> Optional[Dict]:
        """Получить данные сделки по номеру строки"""
        try:
            range_name = f"Trades!A{row}:K{row}"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values or not values[0]:
                return None
            
            row_data = values[0]
            
            # Формируем словарь с данными сделки
            trade = {
                'row': row,
                'number': row_data[0] if len(row_data) > 0 else '',
                'entry_date': row_data[1] if len(row_data) > 1 else '',
                'symbol': row_data[2] if len(row_data) > 2 else '',
                'entry_price': float(row_data[3].replace(',', '.')) if len(row_data) > 3 and row_data[3] else 0,
                'direction': row_data[4] if len(row_data) > 4 else '',
                'exit_price': float(row_data[5].replace(',', '.')) if len(row_data) > 5 and row_data[5] else 0,
                'leverage': row_data[6] if len(row_data) > 6 else '',
                'stop_loss': float(row_data[7].replace(',', '.')) if len(row_data) > 7 and row_data[7] else 0,
                'position_size': row_data[8] if len(row_data) > 8 else '',
                'pnl': row_data[9] if len(row_data) > 9 else '',
                'exit_date': row_data[10] if len(row_data) > 10 else ''
            }
            
            return trade
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения сделки из строки {row}: {e}")
            return None 