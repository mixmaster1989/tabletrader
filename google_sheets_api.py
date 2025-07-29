#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Sheets API для чтения торговых сигналов
"""

from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
import json

class GoogleSheetsAPI:
    def __init__(self, credentials_file: str, spreadsheet_id: str, pos_size: float, leverage: int):
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self.logger = logging.getLogger(__name__)
        
        # Области доступа для Google Sheets
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        
        self._initialize_service()
        self.pos_size = pos_size
        self.leverage = leverage    
    
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
    
    def read_signals(self, range_name: str = "'Trades'!B:M") -> List[Dict]:
        """
        Читать сигналы из Google таблицы
        
        Ожидаемые колонки:
        B - Время входа
        C - Символ
        D - Цена входа
        E - Сторона
        F - Цена выхода
        G - Плечо
        H - Цена стоп лоса
        I - Размер
        J - Прибыль
        K - Дата выхода
        L - Тейк в процентах
        M - Стоп в процентах
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            try:
                with open('google_sheets_data.json', 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
                self.logger.info("💾 Результат чтения таблицы сохранен в google_sheets_data.json")
            except Exception as e:
                self.logger.error(f"❌ Не удалось сохранить результат в файл: {e}")
            
            values = result.get('values', [])
            
            if not values:
                self.logger.warning("⚠️ Таблица пуста")
                return []
            
            signals = []
            for i, row in enumerate(values[1:], start=2):  # Пропускаем заголовок
                try:
                    if len(row) >= 8:
                        date_format = "%d.%m.%Y %H:%M"
                        parsed_date = datetime.strptime(row[0].strip(), date_format)

                        signal = {
                            'row': i,
                            'date': parsed_date,
                            'symbol': row[1].strip().upper(),
                            'entry_price': float(row[2].replace(',', '.').split('/')[0].strip()),
                            'direction': row[3].strip().upper(),
                            'take_profit': float(row[4].replace(',', '.').split('/')[0].strip()),
                            'leverage': int(row[5].replace('X', '').strip()),
                            'stop_loss': float(row[6].replace(',', '.').split('/')[0].strip()),
                            'size': float(row[7].replace(',', '.').split('/')[0].strip()),
                            'status': 'new'  # Статус для отслеживания
                        }
                        
                        # Валидация сигнала
                        error = self._validate_signal(signal)

                        if error == "":
                            signals.append(signal)
                        else:
                            self.logger.warning(f"⚠️ Невалидный сигнал в строке {i}: signal: {signal} raw: {row}")
                            self.logger.warning(f"⚠️ Ошибка валидации сигнала: {error}")
                    else:
                        self.logger.warning(f"⚠️ Неполная строка {i}: raw: {row}")
                        
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
    
    def _validate_signal(self, signal: Dict) -> str:
        """
        Валидация торгового сигнала
        
        :param signal: Словарь с данными сигнала
        {
            'row': int,
            'date': datetime,
            'symbol': str,
            'entry_price': float,
            'direction': str,
            'take_profit': float,
            'leverage': int,
            'stop_loss': float,
            'size': float,
            'status': str
        }
        """
        try:
            # Проверка символа
            if type(signal['row']) != int:
                return "Номер строки должен быть целым числом"

            if type(signal['date']) != datetime:
                return "Дата входа должна быть datetime"

            if type(signal['symbol']) != str:
                return "Символ должен быть строкой"
            if len(signal['symbol']) < 3:
                return "Символ должен быть не менее 3 символов"

            if type(signal['entry_price']) != float:
                return "Цена входа должна быть числом"
            if signal['entry_price'] <= 0:
                return "Цена входа должна быть больше 0"

            if signal['direction'] not in ['LONG', 'SHORT']:
                return "Направление должно быть LONG или SHORT"

            if type(signal['take_profit']) != float:
                return "Take Profit должна быть числом"
            if signal['take_profit'] <= 0:
                return "Take Profit должна быть больше 0"

            if type(signal['leverage']) != int:
                return "Плечо должно быть целым числом"
            if signal['leverage'] <= 0:
                return "Плечо должно быть больше 0"

            if type(signal['stop_loss']) != float:
                return "Stop Loss должна быть числом"
            if signal['stop_loss'] <= 0:
                return "Stop Loss должна быть больше 0"

            if type(signal['size']) != float:
                return "Размер должен быть числом"
            if signal['size'] <= 0:
                return "Размер должен быть больше 0"

            return ""
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации сигнала: {e}")
            return "Ошибка валидации сигнала"
    
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