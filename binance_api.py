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
                            'leverage': float(pos['leverage'])
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
            print(e)
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

    def open_order_with_tp_sl(self, params: Dict) -> Dict:
        """Открыть фьючерсный ордер с TP/SL"""
        try:
            symbol_for_request = self._get_symbol_for_request(params['symbol'])
            side_map = {"LONG": "BUY", "SHORT": "SELL"} # Сохраняем для совместимости с логикой Bybit
            binance_side = side_map.get(params['side'], params['side'].upper())
            size = params['size']
            leverage = int(params['leverage'])
            take_profit = params.get('take_profit') # Может быть None
            stop_loss = params.get('stop_loss')     # Может быть None

            self.logger.info(f"🛠️ Открытие ордера: {symbol_for_request}, {binance_side}, Размер: {size}, Плечо: {leverage}")

            # 1. Устанавливаем плечо
            try:
                self.client.futures_change_leverage(symbol=symbol_for_request, leverage=leverage)
                self.logger.debug(f"Установлено плечо {leverage} для {symbol_for_request}")
            except BinanceAPIException as e:
                 # Ошибка 4053 означает, что плечо уже такое
                if e.code != -4053: # -4053: "Leverage is already at the same level"
                    self.logger.warning(f"Предупреждение при установке плеча для {symbol_for_request}: {e}")

            # 2. Открываем рыночную позицию
            order_params = {
                'symbol': symbol_for_request,
                'side': binance_side,
                'type': 'MARKET',
                'quantity': str(size),
                'takeProfit': str(take_profit) if take_profit else None,
                'stopLoss': str(stop_loss) if stop_loss else None
            }

            order_result = self.client.futures_create_order(**order_params)

            if order_result and order_result.get('orderId'):
                order_id = order_result['orderId']
                avg_price = float(order_result.get('avgPrice', 0))
                executed_qty = float(order_result.get('executedQty', 0))

                self.logger.info(f"✅ Ордер открыт: {symbol_for_request} {binance_side} {executed_qty} по средней цене {avg_price}. Order ID: {order_id}")

                # # 3. Устанавливаем TP/SL отдельно (более надежный способ)
                # # Создаем временный params для modify_trading_stop
                # tp_sl_params = {
                #     'symbol': params['symbol'], # Передаем исходный символ
                #      'take_profit': take_profit,
                #      'stop_loss': stop_loss
                # }
                # tp_sl_result = self.modify_trading_stop(tp_sl_params)
                # if not tp_sl_result.get('success'):
                #      self.logger.warning(f"⚠️ Ошибка при установке TP/SL после открытия ордера: {tp_sl_result.get('error')}")

                return {
                    "orderId": order_id,
                    'success': True,
                    'tpOrderId': None,
                    'slOrderId': None,
                    'avgPrice': avg_price
                }
            else:
                error_msg = order_result.get('msg', 'Неизвестная ошибка при размещении ордера')
                self.logger.error(f"❌ Неудачная попытка открытия ордера: {error_msg}")
                return {"orderId": None, 'success': False, 'tpOrderId': None, 'slOrderId': None, 'error': error_msg}

        except BinanceAPIException as e:
            self.logger.error(f"❌ Ошибка Binance при открытии ордера для {params.get('symbol', 'UNKNOWN')}: {e}")
            return {'success': False, 'retCode': e.code, 'retMsg': e.message}
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка при открытии ордера для {params.get('symbol', 'UNKNOWN')}: {e}")
            return {'success': False, 'retCode': 1, 'retMsg': str(e)}

    def calculate_position_size(self, symbol: str, usdt_size: float, last_price: float) -> float:
        """Рассчитать размер позиции в контрактах на основе суммы USDT и цены"""
        try:
            symbol_for_request = self._get_symbol_for_request(symbol)
            
            # Получаем информацию о символе
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol_for_request), None)
    
            if not symbol_info:
                raise ValueError(f"Информация о символе {symbol_for_request} не найдена")
    
            filters = {f['filterType']: f for f in symbol_info['filters']}
            lot_size_filter = filters.get('LOT_SIZE')
            min_notional_filter = filters.get('MIN_NOTIONAL')
    
            if not lot_size_filter:
                raise ValueError(f"Фильтр LOT_SIZE не найден для {symbol_for_request}")
    
            step_size = float(lot_size_filter['stepSize'])
            min_qty = float(lot_size_filter['minQty'])
            contract_size = float(symbol_info.get('contractSize', 1.0))  # Важно!
    
            # Рассчитываем количество контрактов
            quantity = usdt_size / (last_price * contract_size)
    
            # Округляем вниз до step_size
            step_size_dec = Decimal(str(step_size))
            qty_dec = Decimal(str(quantity))
            quantity_rounded = qty_dec.quantize(step_size_dec, rounding=ROUND_DOWN)
            final_quantity = float(quantity_rounded)
    
            # Проверка minQty
            if final_quantity < min_qty:
                min_notional_required = min_qty * last_price * contract_size
                if usdt_size < min_notional_required:
                    raise ValueError(
                        f"Сумма {usdt_size} USDT слишком мала: нужно минимум {min_notional_required:.2f} USDT"
                    )
                else:
                    self.logger.warning(
                        f"Размер {final_quantity} < minQty {min_qty}, используем minQty."
                    )
                    final_quantity = min_qty
    
            # Проверка MIN_NOTIONAL
            if min_notional_filter:
                min_notional = float(min_notional_filter['notional'])
                notional_value = final_quantity * last_price * contract_size
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