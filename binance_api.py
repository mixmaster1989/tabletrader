#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Упрощенный Binance Futures API для Google Signals Bot
"""

import logging
import time
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Union

from binance.client import Client
from binance.exceptions import BinanceAPIException

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceAPI:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.logger = logging.getLogger(__name__)

        # Инициализация клиента Binance
        self.client = Client(api_key=api_key, api_secret=api_secret, testnet=testnet)
        try:
            self.client.futures_change_position_mode(dualSidePosition=False)
        except BinanceAPIException as e:
            if e.code != -4059:
                self.logger.warning(f"Не удалось установить режим позиции: {e}")
        self.logger.info(f"✅ Binance API инициализирован (testnet: {testnet})")

    def _get_symbol_for_request(self, symbol: str) -> str:
        """Преобразует символ в формат, используемый Binance (e.g., BTC -> BTCUSDT)"""
        if not symbol.endswith('USDT'):
             return f"{symbol}USDT"
        return symbol

    def get_last_price(self, symbol: str) -> Optional[float]:
        """Получить текущую цену фьючерса"""
        try:
            symbol_for_request = self._get_symbol_for_request(symbol)
            ticker = self.client.futures_symbol_ticker(symbol=symbol_for_request)
            price = float(ticker['price'])
            self.logger.debug(f"Получена цена для {symbol_for_request}: {price}")
            return price
        except BinanceAPIException as e:
            self.logger.error(f"❌ Ошибка получения цены для {symbol_for_request}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка получения цены для {symbol}: {e}")
            return None

    def get_positions(self, symbol: str = None) -> List[Dict]:
        """Получить открытые фьючерсные позиции"""
        try:
            all_positions = self.client.futures_position_information()
            open_positions = []

            for pos in all_positions:
                # Проверяем, что позиция по USDT-Margined Futures и размер не нулевой
                if pos['symbol'].endswith('USDT') and float(pos['positionAmt']) != 0:
                    if symbol is None or pos['symbol'] == self._get_symbol_for_request(symbol):
                        # Форматируем данные позиции для совместимости
                        formatted_pos = {
                            'symbol': pos['symbol'],
                            'size': abs(float(pos['positionAmt'])), # Абсолютный размер
                            'side': 'Buy' if float(pos['positionAmt']) > 0 else 'Sell',
                            'entryPrice': float(pos['entryPrice']),
                            'unrealizedPnl': float(pos['unRealizedProfit']),
                        }
                        open_positions.append(formatted_pos)

            self.logger.debug(f"Получено {len(open_positions)} открытых позиций")
            return open_positions

        except BinanceAPIException as e:
            self.logger.error(f"❌ Ошибка получения позиций: {e}")
            return []
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка получения позиций: {e}")
            return []

    def get_balance(self) -> Dict:
        """Получить баланс фьючерсного кошелька USDT"""
        try:
            # Получаем список балансов
            account_info = self.client.futures_account()
            balances = account_info.get('assets', [])
            
            # Ищем баланс USDT
            for asset in balances:
                if asset['asset'] == 'USDT':
                     # Форматируем для совместимости (примерная структура)
                    formatted_balance = {
                        'coin': asset['asset'],
                        'walletBalance': float(asset['walletBalance']),
                        'unrealizedPnl': float(asset['unrealizedProfit']),
                        # Добавьте другие поля при необходимости
                    }
                    self.logger.debug(f"Получен баланс USDT: {formatted_balance}")
                    return formatted_balance

            self.logger.warning("Баланс USDT не найден")
            return {}
        except BinanceAPIException as e:
            self.logger.error(f"❌ Ошибка получения баланса: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка получения баланса: {e}")
            return {}

    def modify_trading_stop(self, params: Dict) -> Dict:
        """
        Изменить TP/SL для существующей позиции.
        Binance обычно требует отмены старых TP/SL и установки новых.
        """
        try:
            symbol_for_request = self._get_symbol_for_request(params['symbol'])
            take_profit = params.get('take_profit')
            stop_loss = params.get('stop_loss')

            # 1. Получить текущую позицию для определения стороны
            positions = self.get_positions(params['symbol'])
            if not positions:
                 self.logger.error(f"❌ Позиция для {symbol_for_request} не найдена для установки TP/SL")
                 return {"success": False, "error": "Позиция не найдена"}

            position = positions[0] # Предполагаем одну активную позицию
            side = position['side'] # 'Buy' или 'Sell'

            # 2. Определяем стороны для TP и SL ордеров
            # TP для Long - Sell, для Short - Buy
            # SL для Long - Sell, для Short - Buy
            # Но тип ордера определяет поведение
            tp_side = 'SELL' if side == 'Buy' else 'BUY'
            sl_side = 'SELL' if side == 'Buy' else 'BUY'

            # 3. Отменить существующие TP/SL ордера для этой позиции
            open_orders = self.client.futures_get_open_orders(symbol=symbol_for_request)
            tp_sl_order_ids = [o['orderId'] for o in open_orders if o['type'] in ['TAKE_PROFIT_MARKET', 'STOP_MARKET']]

            for order_id in tp_sl_order_ids:
                try:
                    self.client.futures_cancel_order(symbol=symbol_for_request, orderId=order_id)
                    self.logger.debug(f"Отменен TP/SL ордер {order_id} для {symbol_for_request}")
                except BinanceAPIException as e:
                     # Может быть ошибка, если ордер уже исполнен или отменен, продолжаем
                     self.logger.warning(f"Не удалось отменить ордер {order_id}: {e}")

            # 4. Установить новые TP/SL
            orders_to_place = []
            if take_profit:
                orders_to_place.append({
                    'symbol': symbol_for_request,
                    'side': tp_side,
                    'type': 'TAKE_PROFIT_MARKET',
                    'stopPrice': str(take_profit),
                    'closePosition': True, # Закрыть всю позицию
                     'workingType': 'MARK_PRICE' # Или 'CONTRACT_PRICE'
                })
            if stop_loss:
                 orders_to_place.append({
                    'symbol': symbol_for_request,
                    'side': sl_side,
                    'type': 'STOP_MARKET',
                    'stopPrice': str(stop_loss),
                    'closePosition': True,
                    'workingType': 'MARK_PRICE'
                })

            placed_orders = []
            for order_params in orders_to_place:
                try:
                    result = self.client.futures_create_order(**order_params)
                    placed_orders.append(result)
                    self.logger.info(f"✅ Установлен TP/SL ордер: {result}")
                except BinanceAPIException as e:
                    self.logger.error(f"❌ Ошибка размещения TP/SL ордера {order_params}: {e}")
                    # Возвращаем ошибку, если не удалось разместить один из ордеров?
                    # Или продолжаем и возвращаем частичный успех?
                    return {"success": False, "error": f"Ошибка размещения ордера: {e}"}

            self.logger.info(f"✅ TP/SL для {symbol_for_request} успешно изменены/установлены.")
            return {"success": True, "result": placed_orders}

        except BinanceAPIException as e:
            self.logger.error(f"❌ Ошибка изменения TP/SL для {params.get('symbol', 'UNKNOWN')}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            self.logger.error(f"❌ Исключение при изменении TP/SL для {params.get('symbol', 'UNKNOWN')}: {e}")
            return {"success": False, "error": str(e)}

    def prepare_for_new_entry(self, symbol: str):
        """Отменяет все активные ордера по символу перед новым входом"""
        symbol_for_request = self._get_symbol_for_request(symbol)
        try:
            # Получаем список активных ордеров
            open_orders = self.client.futures_get_open_orders(symbol=symbol_for_request)
        
            if open_orders:
                # Отменяем все
                self.client.futures_cancel_all_open_orders(symbol=symbol_for_request)
                self.logger.info(f"🧹 Отменено {len(open_orders)} активных ордеров по {symbol_for_request}")
            else:
                self.logger.debug(f"🟢 Нет активных ордеров по {symbol_for_request}")

        except BinanceAPIException as e:
            self.logger.error(f"❌ Ошибка при отмене ордеров для {symbol_for_request}: {e}")
            raise e
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка при отмене ордеров для {symbol_for_request}: {e}")
            raise e

    def open_order_with_tp_sl(self, params: Dict) -> Dict:
        """Открыть фьючерсный ордер с TP/SL"""
        try:
            self.prepare_for_new_entry(params['symbol'])
            
            symbol_for_request = self._get_symbol_for_request(params['symbol'])
            side_map = {"LONG": "BUY", "SHORT": "SELL"}
            binance_side = side_map.get(params['side'], params['side'].upper())
            size = params['size']
            leverage = int(params['leverage'])
            take_profit = params.get('take_profit')
            stop_loss = params.get('stop_loss')
    
            self.logger.info(f"🛠️ Открытие ордера: {symbol_for_request}, {binance_side}, Размер: {size}, Плечо: {leverage}")
    
            # 1. Установка плеча
            try:
                self.client.futures_change_leverage(symbol=symbol_for_request, leverage=leverage)
                self.logger.debug(f"Установлено плечо {leverage} для {symbol_for_request}")
            except BinanceAPIException as e:
                if e.code != -4053:  # Уже установлено
                    self.logger.warning(f"Ошибка при установке плеча: {e}")
    
            # 2. Установка маржинального типа (ISOLATED)
            try:
                self.client.futures_change_margin_type(symbol=symbol_for_request, marginType='ISOLATED')
            except BinanceAPIException as e:
                if e.code != -4046:  # "No need to change margin type"
                    self.logger.warning(f"Ошибка при установке ISOLATED: {e}")
    
            # 3. Открытие рыночной позиции
            order_params = {
                'symbol': symbol_for_request,
                'side': binance_side,
                'type': 'MARKET',
                'quantity': str(size),
                'timestamp': int(time.time() * 1000)
            }
    
            order_result = self.client.futures_create_order(**order_params)
            order_id = order_result['orderId']
            avg_price = float(order_result.get('avgPrice', 0))
            executed_qty = str(size)

            self.logger.info(f"✅ Ордер открыт: {symbol_for_request} {binance_side} {executed_qty} по средней цене {avg_price}. Order ID: {order_id}")
    
            tp_order_id = None
            sl_order_id = None
    
            # 4. Установка Take Profit (TAKE_PROFIT_MARKET)
            if take_profit:
                try:
                    tp_params = {
                        'symbol': symbol_for_request,
                        'side': 'SELL' if binance_side == 'BUY' else 'BUY',
                        'type': 'TAKE_PROFIT_MARKET',
                        'quantity': str(executed_qty),
                        'stopPrice': str(take_profit),
                        'reduceOnly': 'true',
                        'workingType': 'MARK_PRICE',  # Рекомендуется
                        'timestamp': int(time.time() * 1000)
                    }
                    tp_result = self.client.futures_create_order(**tp_params)
                    tp_order_id = tp_result['orderId']
                    self.logger.info(f"✅ TP установлен: {take_profit} (Order ID: {tp_order_id})")
                except BinanceAPIException as e:
                    self.logger.error(f"❌ Ошибка при установке TP: {e}")
                    # Не прерываем, продолжаем
    
            # 5. Установка Stop Loss (STOP_MARKET)
            if stop_loss:
                try:
                    sl_params = {
                        'symbol': symbol_for_request,
                        'side': 'SELL' if binance_side == 'BUY' else 'BUY',
                        'type': 'STOP_MARKET',
                        'quantity': str(executed_qty),
                        'stopPrice': str(stop_loss),
                        'reduceOnly': 'true',
                        'workingType': 'MARK_PRICE',  # Рекомендуется
                        'timestamp': int(time.time() * 1000)
                    }
                    sl_result = self.client.futures_create_order(**sl_params)
                    sl_order_id = sl_result['orderId']
                    self.logger.info(f"✅ SL установлен: {stop_loss} (Order ID: {sl_order_id})")
                except BinanceAPIException as e:
                    self.logger.error(f"❌ Ошибка при установке SL: {e}")
    
            return {
                "success": True,
                "orderId": order_id,
                "tpOrderId": tp_order_id,
                "slOrderId": sl_order_id,
                "avgPrice": avg_price,
                "executedQty": executed_qty
            }
    
        except BinanceAPIException as e:
            self.logger.error(f"❌ Ошибка Binance API: {e}")
            return {"success": False, "retCode": e.code, "retMsg": e.message}
        except Exception as e:
            self.logger.error(f"❌ Неизвестная ошибка: {e}")
            return {"success": False, "retCode": 1, "retMsg": str(e)}

    def calculate_position_size(self, symbol: str, usdt_size: float, last_price: float) -> float:
        try:
            symbol_for_request = self._get_symbol_for_request(symbol)
    
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol_for_request), None)
    
            if not symbol_info:
                raise ValueError(f"Информация о символе {symbol_for_request} не найдена")
    
            filters = {f['filterType']: f for f in symbol_info['filters']}
            lot_size_filter = filters.get('LOT_SIZE')
            min_notional_filter = filters.get('MIN_NOTIONAL')
    
            if not lot_size_filter:
                raise ValueError(f"Фильтр LOT_SIZE не найден для {symbol_for_request}")
    
            # Используем строки из API для точности
            step_size_str = lot_size_filter['stepSize']
            min_qty_str = lot_size_filter['minQty']
            contract_size_str = symbol_info.get('contractSize', '1')
    
            step_size_dec = Decimal(step_size_str).normalize()
            min_qty_dec = Decimal(min_qty_str).normalize()
            contract_size_dec = Decimal(contract_size_str).normalize()
    
            # Конвертируем входы в Decimal
            usdt_size_dec = Decimal(str(usdt_size))
            last_price_dec = Decimal(str(last_price))
    
            # Расчёт
            quantity = usdt_size_dec / (last_price_dec * contract_size_dec)
            quantity_rounded = quantity.quantize(step_size_dec, rounding=ROUND_DOWN)
            final_quantity = float(quantity_rounded)
    
            # 🔴 Проверка: не обнулился ли объём?
            if final_quantity < float(step_size_dec):
                min_usdt_for_step = float(step_size_dec) * last_price * float(contract_size_dec)
                if usdt_size < min_usdt_for_step:
                    raise ValueError(
                        f"Сумма {usdt_size} USDT слишком мала: нужно минимум ~{min_usdt_for_step:.2f} USDT "
                        f"для минимального шага {step_size_dec} контрактов при цене {last_price}"
                    )
    
            # Проверка minQty
            if final_quantity < float(min_qty_dec):
                min_usdt_for_min_qty = float(min_qty_dec) * last_price * float(contract_size_dec)
                if usdt_size < min_usdt_for_min_qty:
                    raise ValueError(
                        f"Сумма {usdt_size} USDT слишком мала: нужно минимум {min_usdt_for_min_qty:.2f} USDT "
                        f"для минимального объёма {min_qty_dec} контрактов"
                    )
                else:
                    self.logger.warning(
                        f"Размер {final_quantity} < minQty {min_qty_dec}, используем minQty."
                    )
                    final_quantity = float(min_qty_dec)
    
            # Проверка MIN_NOTIONAL
            if min_notional_filter:
                min_notional = float(min_notional_filter['notional'])
                notional_value = final_quantity * last_price * float(contract_size_dec)
                if notional_value < min_notional:
                    raise ValueError(
                        f"Стоимость позиции {notional_value:.2f} USDT < минимальной {min_notional} USDT"
                    )
    
            self.logger.info(
                f"✅ Размер позиции для {symbol_for_request}: {final_quantity} контрактов "
                f"(~{usdt_size} USDT при цене {last_price})"
            )
            return final_quantity
    
        except BinanceAPIException as e:
            self.logger.error(f"❌ Ошибка Binance при расчете размера позиции для {symbol}: {e}")
            return 0.0
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета размера позиции для {symbol}: {e}")
            return 0.0