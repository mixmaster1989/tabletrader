#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram контроллер для управления торговым ботом
"""

import logging
import json
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from signal_processor import SignalProcessor, OrderStatus

class TelegramController:
    def __init__(self, bot_token: str, chat_id: str, signal_processor: SignalProcessor):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.signal_processor = signal_processor
        self.logger = logging.getLogger(__name__)
        
        # Инициализация бота
        self.updater = Updater(bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Регистрация обработчиков
        self._register_handlers()
        
        self.logger.info("✅ Telegram Controller инициализирован")
    
    def _register_handlers(self):
        """Регистрация обработчиков команд и кнопок"""
        # Команды
        self.dispatcher.add_handler(CommandHandler("start", self._start_command))
        self.dispatcher.add_handler(CommandHandler("menu", self._show_main_menu))
        self.dispatcher.add_handler(CommandHandler("status", self._show_status))
        
        # Обработчик кнопок
        self.dispatcher.add_handler(CallbackQueryHandler(self._button_callback))
    
    def _start_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /start"""
        self._show_main_menu(update, context)
    
    def _show_main_menu(self, update: Update, context: CallbackContext):
        """Показать главное меню"""
        keyboard = [
            [
                InlineKeyboardButton("🟢 Включить бота", callback_data="start_bot"),
                InlineKeyboardButton("🔴 Выключить бота", callback_data="stop_bot")
            ],
            [
                InlineKeyboardButton("🛑 Выключить + отменить все ордера", callback_data="stop_cancel_all")
            ],
            [
                InlineKeyboardButton("📊 Статус", callback_data="show_status"),
                InlineKeyboardButton("📋 Активные ордера", callback_data="show_orders")
            ],
            [
                InlineKeyboardButton("🔄 Обновить", callback_data="refresh")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = """
🤖 **Панель управления торговым ботом**

Выберите действие:
• 🟢 **Включить** - запустить бота
• 🔴 **Выключить** - остановить бота
• 🛑 **Выключить + отменить** - остановить и отменить все ордера
• 📊 **Статус** - показать текущее состояние
• 📋 **Активные ордера** - список ордеров для отмены
        """
        
        if update.callback_query:
            update.callback_query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    def _show_status(self, update: Update, context: CallbackContext):
        """Показать статус бота"""
        try:
            status = self.signal_processor.get_status()
            
            # Получаем активные ордера
            active_orders = []
            for signal_id, signal_data in self.signal_processor.processed_signals.items():
                if signal_data.get('status') == OrderStatus.PLACED.value:
                    active_orders.append({
                        'id': signal_id,
                        'symbol': signal_data['symbol'],
                        'direction': signal_data['direction'],
                        'entry_price': signal_data['entry_price'],
                        'order_id': signal_data.get('order_id', 'N/A')
                    })
            
            message_text = f"""
📊 **Статус бота**

🕒 Последняя проверка: {status.get('last_check', 'Неизвестно')}
📈 Обработано сигналов: {status.get('processed_signals', 0)}
📊 Открытых позиций: {status.get('open_positions', 0)}
📋 Активных ордеров: {len(active_orders)}

{'🔴 **Активные ордера:**' if active_orders else '✅ Активных ордеров нет'}
"""
            
            if active_orders:
                for order in active_orders:
                    message_text += f"""
• {order['symbol']} {order['direction']} @ {order['entry_price']}
  ID: {order['order_id']}
"""
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                update.callback_query.edit_message_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                update.message.reply_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статуса: {e}")
            self._send_error_message(update, "Ошибка получения статуса")
    
    def _show_orders_menu(self, update: Update, context: CallbackContext):
        """Показать меню активных ордеров"""
        try:
            active_orders = []
            for signal_id, signal_data in self.signal_processor.processed_signals.items():
                if signal_data.get('status') == OrderStatus.PLACED.value:
                    active_orders.append({
                        'id': signal_id,
                        'symbol': signal_data['symbol'],
                        'direction': signal_data['direction'],
                        'entry_price': signal_data['entry_price'],
                        'order_id': signal_data.get('order_id', 'N/A')
                    })
            
            if not active_orders:
                message_text = "✅ Активных ордеров нет"
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            else:
                message_text = f"📋 **Активные ордера ({len(active_orders)}):**\n\nВыберите ордер для отмены:"
                keyboard = []
                
                for order in active_orders:
                    button_text = f"❌ {order['symbol']} {order['direction']} @ {order['entry_price']}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"cancel_order:{order['id']}")])
                
                keyboard.append([InlineKeyboardButton("❌ Отменить все", callback_data="cancel_all_orders")])
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                update.callback_query.edit_message_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                update.message.reply_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения ордеров: {e}")
            self._send_error_message(update, "Ошибка получения ордеров")
    
    def _button_callback(self, update: Update, context: CallbackContext):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        query.answer()
        
        data = query.data
        
        try:
            if data == "start_bot":
                self._handle_start_bot(query)
            elif data == "stop_bot":
                self._handle_stop_bot(query)
            elif data == "stop_cancel_all":
                self._handle_stop_cancel_all(query)
            elif data == "show_status":
                self._show_status(update, context)
            elif data == "show_orders":
                self._show_orders_menu(update, context)
            elif data == "cancel_all_orders":
                self._handle_cancel_all_orders(query)
            elif data.startswith("cancel_order:"):
                order_id = data.split(":")[1]
                self._handle_cancel_single_order(query, order_id)
            elif data == "back_to_menu":
                self._show_main_menu(update, context)
            elif data == "refresh":
                self._show_main_menu(update, context)
            else:
                query.edit_message_text("❌ Неизвестная команда")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки кнопки {data}: {e}")
            self._send_error_message(update, f"Ошибка обработки команды: {e}")
    
    def _handle_start_bot(self, query):
        """Обработчик включения бота"""
        try:
            query.edit_message_text(
                "🟢 **Бот включен!**\n\nБот начал работу и будет обрабатывать сигналы.",
                parse_mode='Markdown'
            )
            self.logger.info("🟢 Бот включен через Telegram")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка включения бота: {e}")
            self._send_error_message(query, "Ошибка включения бота")
    
    def _handle_stop_bot(self, query):
        """Обработчик выключения бота"""
        try:
            query.edit_message_text(
                "🔴 **Бот выключен!**\n\nБот остановлен. Новые сигналы обрабатываться не будут.",
                parse_mode='Markdown'
            )
            self.logger.info("🔴 Бот выключен через Telegram")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка выключения бота: {e}")
            self._send_error_message(query, "Ошибка выключения бота")
    
    def _handle_stop_cancel_all(self, query):
        """Обработчик выключения бота с отменой всех ордеров"""
        try:
            # Отменяем все активные ордера
            cancelled_count = 0
            for signal_id, signal_data in self.signal_processor.processed_signals.items():
                if signal_data.get('status') == OrderStatus.PLACED.value:
                    if self.signal_processor.exchange.cancel_order(
                        signal_data['order_id'], 
                        signal_data['symbol']
                    ):
                        self.signal_processor.processed_signals[signal_id]['status'] = OrderStatus.CLOSED.value
                        cancelled_count += 1
            
            self.signal_processor._save_processed_signals()
            
            query.edit_message_text(
                f"🛑 **Бот выключен и все ордера отменены!**\n\n"
                f"Отменено ордеров: {cancelled_count}\n"
                f"Бот остановлен.",
                parse_mode='Markdown'
            )
            self.logger.info(f"🛑 Бот выключен и отменено {cancelled_count} ордеров через Telegram")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка выключения бота с отменой ордеров: {e}")
            self._send_error_message(query, "Ошибка выключения бота с отменой ордеров")
    
    def _handle_cancel_all_orders(self, query):
        """Обработчик отмены всех ордеров"""
        try:
            cancelled_count = 0
            failed_count = 0
            
            for signal_id, signal_data in self.signal_processor.processed_signals.items():
                if signal_data.get('status') == OrderStatus.PLACED.value:
                    if self.signal_processor.exchange.cancel_order(
                        signal_data['order_id'], 
                        signal_data['symbol']
                    ):
                        self.signal_processor.processed_signals[signal_id]['status'] = OrderStatus.CLOSED.value
                        cancelled_count += 1
                    else:
                        failed_count += 1
            
            self.signal_processor._save_processed_signals()
            
            message_text = f"❌ **Отмена ордеров завершена!**\n\n"
            message_text += f"✅ Успешно отменено: {cancelled_count}\n"
            if failed_count > 0:
                message_text += f"❌ Ошибок отмены: {failed_count}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            self.logger.info(f"❌ Отменено {cancelled_count} ордеров через Telegram")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отмены всех ордеров: {e}")
            self._send_error_message(query, "Ошибка отмены ордеров")
    
    def _handle_cancel_single_order(self, query, order_id):
        """Обработчик отмены одного ордера"""
        try:
            if order_id in self.signal_processor.processed_signals:
                signal_data = self.signal_processor.processed_signals[order_id]
                
                if signal_data.get('status') == OrderStatus.PLACED.value:
                    if self.signal_processor.exchange.cancel_order(
                        signal_data['order_id'], 
                        signal_data['symbol']
                    ):
                        self.signal_processor.processed_signals[order_id]['status'] = OrderStatus.CLOSED.value
                        self.signal_processor._save_processed_signals()
                        
                        query.edit_message_text(
                            f"✅ **Ордер отменен!**\n\n"
                            f"Символ: {signal_data['symbol']}\n"
                            f"Направление: {signal_data['direction']}\n"
                            f"Цена входа: {signal_data['entry_price']}",
                            parse_mode='Markdown'
                        )
                        
                        self.logger.info(f"✅ Ордер {order_id} отменен через Telegram")
                    else:
                        query.edit_message_text(
                            f"❌ **Ошибка отмены ордера!**\n\n"
                            f"Не удалось отменить ордер {order_id}.\n"
                            f"Проверьте статус вручную на бирже.",
                            parse_mode='Markdown'
                        )
                else:
                    query.edit_message_text(
                        f"⚠️ **Ордер уже не активен!**\n\n"
                        f"Статус: {signal_data.get('status', 'Неизвестно')}",
                        parse_mode='Markdown'
                    )
            else:
                query.edit_message_text(
                    "❌ **Ордер не найден!**",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка отмены ордера {order_id}: {e}")
            self._send_error_message(query, f"Ошибка отмены ордера: {e}")
    
    def _send_error_message(self, update, error_text: str):
        """Отправить сообщение об ошибке"""
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'edit_message_text'):
            update.edit_message_text(
                f"❌ **Ошибка!**\n\n{error_text}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text(
                f"❌ **Ошибка!**\n\n{error_text}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    def start(self):
        """Запустить бота"""
        self.updater.start_polling()
    
    def stop(self):
        """Остановить бота"""
        self.updater.stop() 