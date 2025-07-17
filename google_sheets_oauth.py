import logging
import os
import pickle
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleSheetsOAuthAPI:
    def __init__(self, spreadsheet_id: str, credentials_file: str = 'credentials.json'):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_file = credentials_file
        self.service = None
        self.logger = logging.getLogger(__name__)
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self._initialize_service()

    def _initialize_service(self):
        try:
            creds = None
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        self.logger.error(f"Файл {self.credentials_file} не найден!")
                        raise Exception("Файл credentials.json не найден")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            self.service = build('sheets', 'v4', credentials=creds)
            self.logger.info("Google Sheets API инициализирован с OAuth2")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Google Sheets API: {e}")
            raise

    def read_signals(self, range_name: str = "A:E") -> List[Dict]:
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            values = result.get('values', [])
            if not values:
                self.logger.warning("Таблица пуста")
                return []
            signals = []
            for i, row in enumerate(values[1:], start=2):
                try:
                    if len(row) >= 5:
                        signal = {
                            'row': i,
                            'symbol': row[0].strip().upper(),
                            'entry_price': float(row[1]),
                            'take_profit': float(row[2]),
                            'stop_loss': float(row[3]),
                            'direction': row[4].strip().upper(),
                            'status': 'new'
                        }
                        if self._validate_signal(signal):
                            signals.append(signal)
                        else:
                            self.logger.warning(f"Невалидный сигнал в строке {i}: {row}")
                    else:
                        self.logger.warning(f"Неполная строка {i}: {row}")
                except (ValueError, IndexError) as e:
                    self.logger.error(f"Ошибка обработки строки {i}: {e}")
                    continue
            self.logger.info(f"Прочитано {len(signals)} сигналов из Google таблицы")
            return signals
        except HttpError as e:
            self.logger.error(f"Ошибка Google Sheets API: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка: {e}")
            return []

    def _validate_signal(self, signal: Dict) -> bool:
        try:
            if not signal['symbol'] or len(signal['symbol']) < 3:
                return False
            if signal['entry_price'] <= 0:
                return False
            if signal['take_profit'] <= 0:
                return False
            if signal['stop_loss'] <= 0:
                return False
            if signal['direction'] not in ['LONG', 'SHORT']:
                return False
            if signal['direction'] == 'LONG':
                if signal['take_profit'] <= signal['entry_price']:
                    return False
                if signal['stop_loss'] >= signal['entry_price']:
                    return False
            else:
                if signal['take_profit'] >= signal['entry_price']:
                    return False
                if signal['stop_loss'] <= signal['entry_price']:
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Ошибка валидации сигнала: {e}")
            return False

    def mark_signal_processed(self, row: int, status: str = "processed"):
        try:
            range_name = f"F{row}"
            values = [[status]]
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': values}
            ).execute()
            self.logger.info(f"Сигнал в строке {row} отмечен как {status}")
        except Exception as e:
            self.logger.error(f"Ошибка отметки сигнала: {e}")

    def get_last_update_time(self) -> Optional[str]:
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id,
                ranges=[],
                includeGridData=False
            ).execute()
            return result.get('properties', {}).get('modifiedTime')
        except Exception as e:
            self.logger.error(f"Ошибка получения времени обновления: {e}")
            return None 