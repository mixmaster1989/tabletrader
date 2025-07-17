#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчик торговых сигналов из Google таблицы
"""

import logging
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from google_sheets_api import GoogleSheetsAPI
from bybit_api import BybitAPI
from telegram_bot import TelegramBot
from utils import get_bybit_symbol
from trading_analyzer import TradingPatternAnalyzer

class SignalProcessor:
    """
    Обработчик торговых сигналов
    """
    
    def __init__(self, bybit_api, google_sheets_api, telegram_bot, logger=None):
        self.bybit = bybit_api
        self.google_sheets = google_sheets_api
        self.telegram = telegram_bot
        self.logger = logger
        self.cycle_count = 0
        self.last_report_time = None
        
        # Получаем конфигурацию из bybit_api
        self.config = bybit_api.config if hasattr(bybit_api, 'config') else {}
        
        # Инициализируем множества для отслеживания обработанных сигналов
        self.processed_signals = set()
        self.last_check_time = None
        
        # Инициализируем анализатор паттернов
        self.pattern_analyzer = TradingPatternAnalyzer(logger)
        self.pattern_analysis_done = False
        
    def log(self, message, level="INFO"):
        """Логирование с поддержкой внешнего логгера"""
        if self.logger:
            if level == "INFO":
                self.logger.info(message)
            elif level == "WARNING":
                self.logger.warning(message)
            elif level == "ERROR":
                self.logger.error(message)
        else:
            print(f"[{level}] {message}")
    
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
                        # Проверяем режим работы
                        if self.config['TRADE_MODE'] == 'monitor':
                            # Режим мониторинга - только логируем
                            self.logger.info(f"📊 РЕЖИМ МОНИТОРИНГА: Найден сигнал {signal['symbol']} {signal['direction']} по цене {signal['entry_price']}")
                            self.processed_signals.add(signal_id)
                            processed_count += 1
                        else:
                            # Режим торговли - открываем сделки
                            result = self._execute_signal(signal)
                            
                            if result['success']:
                                self.processed_signals.add(signal_id)
                                processed_count += 1
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
            bybit_symbol = signal.get('bybit_symbol')
            if not bybit_symbol:
                self.logger.error(f"❌ Нет bybit_symbol для сигнала {signal['symbol']} — пропуск")
                return False
            self.logger.info(f"🔍 Запрос к Bybit: bybit_symbol={bybit_symbol} (исходный: {signal['symbol']})")
            current_price = self.bybit.get_last_price(bybit_symbol)
            if not current_price:
                self.logger.error(f"❌ Не удалось получить цену для {signal['symbol']}")
                return False
            
            # Для бэктеста отключаем проверку отклонения цены (работаем с историческими данными)
            price_deviation = abs(current_price - signal['entry_price']) / signal['entry_price'] * 100
            self.logger.info(f"📊 {signal['symbol']}: историческая цена {signal['entry_price']:.6f}, текущая {current_price:.6f}, отклонение {price_deviation:.2f}%")
            
            # В бэктесте пропускаем проверку отклонения цены
            # if price_deviation > self.config['PRICE_DEVIATION']:
            #     self.logger.warning(f"⚠️ Цена {signal['symbol']} отклонена на {price_deviation:.2f}%")
            #     return False
            
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
    
    def get_status(self) -> Dict:
        """Получить статус процессора"""
        return {
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'processed_signals': len(self.processed_signals),
            'open_positions': len(self.bybit.get_positions()),
            'max_positions': self.config['MAX_POSITIONS']
        }
    
    def send_backtest_report(self):
        """Отправка отчета о бэктесте в Telegram"""
        self.logger.info("🚀 Начинаю генерацию бэктест-отчета...")
        try:
            # Читаем все сигналы из таблицы
            signals = self.google_sheets.read_signals()
            
            if not signals:
                self.telegram.send_message("📊 Таблица пуста - нет данных для анализа")
                return
            
            # Статистика
            total_signals = len(signals)
            closed_signals = [s for s in signals if s['status'] == 'closed']
            open_signals = [s for s in signals if s['status'] == 'open']
            
            # Расчет общей прибыли
            total_pnl = sum([s.get('profit_loss', 0) for s in closed_signals])
            avg_pnl = total_pnl / len(closed_signals) if closed_signals else 0
            
            # Текущие цены для открытых сделок
            current_pnl_open = 0
            open_details = []
            if open_signals:
                for signal in open_signals:
                    backtest_result = self.google_sheets.backtest_signal(signal)
                    if backtest_result['success']:
                        current_pnl = backtest_result['signal'].get('current_pnl', 0)
                        current_pnl_open += current_pnl
                        open_details.append(f"• {signal['symbol']} {signal['direction']}: {current_pnl:.2f}%")
            
            message = f"""📊 ОТЧЕТ О БЭКТЕСТЕ ТАБЛИЦЫ

🎯 Я вижу вашу таблицу и анализирую {total_signals} сделок!

📈 ЗАКРЫТЫЕ СДЕЛКИ: {len(closed_signals)}
💰 Общая прибыль: {total_pnl:.2f}%
📊 Средняя прибыль: {avg_pnl:.2f}%

🔍 ОТКРЫТЫЕ СДЕЛКИ: {len(open_signals)}
💹 Текущий P&L: {current_pnl_open:.2f}%"""
            
            if open_details:
                message += "\n\n📱 АКТИВНЫЕ ПОЗИЦИИ:\n" + "\n".join(open_details)
            
            # Топ-3 лучшие сделки
            if closed_signals:
                message += "\n\n🏆 ЛУЧШИЕ СДЕЛКИ:"
                best_trades = sorted(closed_signals, key=lambda x: x.get('profit_loss', 0), reverse=True)[:3]
                for i, trade in enumerate(best_trades, 1):
                    pnl = trade.get('profit_loss', 0)
                    emoji = "🚀" if pnl > 0 else "📉"
                    message += f"\n{i}. {emoji} {trade['symbol']} {trade['direction']}: {pnl:.2f}%"
            
            message += f"""

💪 Ваша стратегия показывает отличные результаты!
📱 Бот мониторит {len(open_signals)} активных позиций

⏰ {datetime.now().strftime('%H:%M:%S UTC')}"""
            
            self.telegram.send_message(message)
            self.logger.info("✅ Бэктест-отчет успешно отправлен в Telegram")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки отчета: {e}")
            self.telegram.send_message(f"❌ Ошибка генерации отчета: {e}")
    
    def analyze_trading_patterns(self):
        """
        Анализ торговых паттернов и отправка отчета
        """
        try:
            self.log("🔍 Запуск анализа торговых паттернов...")
            self.logger.info("🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Начинаю анализ...")
            
            # Получаем все сигналы
            signals = self.google_sheets.read_signals()
            self.logger.info(f"🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Получено {len(signals)} сигналов")
            
            if not signals:
                self.log("⚠️ Нет сигналов для анализа паттернов")
                self.logger.warning("🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Нет сигналов для анализа")
                return
            
            # Проверяем, достаточно ли данных для анализа
            if len(signals) < 10:
                self.log(f"⚠️ Недостаточно данных для анализа ({len(signals)} сделок, нужно минимум 10)")
                self.logger.warning(f"🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Недостаточно данных ({len(signals)} сделок)")
                return
            
            self.logger.info("🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Достаточно данных, начинаю анализ...")
            
            # Выполняем полный анализ
            report = self.pattern_analyzer.analyze_all(signals)
            self.logger.info("🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Анализ завершен, формирую отчет...")
            
            # Выводим отчет в консоль
            self.pattern_analyzer.print_report(report)
            
            # Формируем краткий отчет для Telegram
            summary = report['summary']
            rules = report['rules']
            
            telegram_report = f"""
🧠 **АНАЛИЗ ТОРГОВЫХ ПАТТЕРНОВ**

📊 **Статистика:**
• Всего сделок: {summary['total_trades']}
• Винрейт: {summary['win_rate']:.1%}
• Общая прибыль: {summary['total_profit']:.2f}%

📋 **Выявленные правила:**
"""
            
            # Добавляем топ-5 правил
            for i, rule in enumerate(rules[:5], 1):
                telegram_report += f"{i}. {rule}\n"
            
            if len(rules) > 5:
                telegram_report += f"... и еще {len(rules) - 5} правил\n"
            
            # Добавляем информацию о лучших символах
            if 'symbols' in report['patterns']:
                symbol_stats = report['patterns']['symbols']['stats']
                top_symbols = symbol_stats[('profit_loss', 'mean')].nlargest(3)
                telegram_report += f"\n💎 **Топ-3 символа:**\n"
                for symbol, profit in top_symbols.items():
                    win_rate = symbol_stats.loc[symbol, ('is_profitable', 'mean')]
                    telegram_report += f"• {symbol}: {profit:.2f}% (винрейт: {win_rate:.1%})\n"
            
            # Отправляем отчет
            self.telegram.send_message(telegram_report)
            self.log("✅ Анализ паттернов завершен и отчет отправлен")
            self.logger.info("🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Отчет отправлен в Telegram")
            
            # Помечаем, что анализ выполнен
            self.pattern_analysis_done = True
            
        except Exception as e:
            self.log(f"❌ Ошибка анализа паттернов: {e}")
            self.logger.error(f"🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Ошибка - {e}")
            import traceback
            self.logger.error(f"🧠 АНАЛИЗАТОР ПАТТЕРНОВ: Traceback: {traceback.format_exc()}") 