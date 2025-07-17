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

class GoogleSheetsAPI:
    def __init__(self, credentials_file: str, spreadsheet_id: str):
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self.logger = logging.getLogger(__name__)
        
        # Области доступа для Google Sheets
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        
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
    
    def read_signals(self, range_name: str = "A:E") -> List[Dict]:
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
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                self.logger.warning("⚠️ Таблица пуста")
                return []
            
            signals = []
            for i, row in enumerate(values[1:], start=2):  # Пропускаем заголовок
                try:
                    if len(row) >= 5:  # Минимум 5 колонок
                        signal = {
                            'row': i,
                            'symbol': row[0].strip().upper(),
                            'entry_price': float(row[1]),
                            'take_profit': float(row[2]),
                            'stop_loss': float(row[3]),
                            'direction': row[4].strip().upper(),
                            'status': 'new'  # Статус для отслеживания
                        }
                        
                        # Валидация сигнала
                        if self._validate_signal(signal):
                            signals.append(signal)
                        else:
                            self.logger.warning(f"⚠️ Невалидный сигнал в строке {i}: {row}")
                    else:
                        self.logger.warning(f"⚠️ Неполная строка {i}: {row}")
                        
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
            
            # Проверка цен
            if signal['entry_price'] <= 0:
                return False
            if signal['take_profit'] <= 0:
                return False
            if signal['stop_loss'] <= 0:
                return False
            
            # Проверка направления
            if signal['direction'] not in ['LONG', 'SHORT']:
                return False
            
            # Проверка логики TP/SL
            if signal['direction'] == 'LONG':
                if signal['take_profit'] <= signal['entry_price']:
                    return False
                if signal['stop_loss'] >= signal['entry_price']:
                    return False
            else:  # SHORT
                if signal['take_profit'] >= signal['entry_price']:
                    return False
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
    
    def get_last_update_time(self) -> Optional[str]:
        """Получить время последнего обновления таблицы"""
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id,
                ranges=[],
                includeGridData=False
            ).execute()
            
            return result.get('properties', {}).get('modifiedTime')
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения времени обновления: {e}")
            return None 