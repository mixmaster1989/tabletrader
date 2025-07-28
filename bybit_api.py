#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Упрощенный Bybit API для Google Signals Bot
"""

import logging
import time
from pybit.unified_trading import HTTP
from typing import Dict, List, Optional

class BybitAPI:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.logger = logging.getLogger(__name__)
        
        # Инициализация сессии
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )
        
        self.logger.info(f"✅ Bybit API инициализирован (testnet: {testnet})")
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Получить текущую цену"""
        try:
            result = self.session.get_tickers(category="linear", symbol=symbol + 'USDT')
            ticker_list = result.get('result', {}).get('list', [])
            
            if ticker_list and 'lastPrice' in ticker_list[0]:
                price = float(ticker_list[0]['lastPrice'])
                return price
            else:
                self.logger.error(f"❌ Не удалось получить цену для {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения цены для {symbol}: {e}")
            return None
    
    def get_positions(self, symbol: str = None) -> List[Dict]:
        """Получить открытые позиции"""
        try:
            result = self.session.get_positions(category="linear", settleCoin="USDT")
            positions = result.get('result', {}).get('list', [])
            
            # Фильтруем только открытые позиции
            open_positions = []
            for pos in positions:
                if float(pos.get('size', 0)) > 0:
                    if symbol is None or pos.get('symbol') == symbol:
                        open_positions.append(pos)
            
            return open_positions
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения позиций: {e}")
            return []
    
    def get_balance(self) -> Dict:
        """Получить баланс"""
        try:
            result = self.session.get_wallet_balance(accountType='UNIFIED')
            balances = result.get('result', {}).get('list', [])
            return balances[0] if balances else {}
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения баланса: {e}")
            return {}

    def modify_trading_stop(self, params: Dict) -> Dict:
        """Изменить TP/SL для существующей позиции"""
        try:
            symbol = params['symbol'] + 'USDT'
            take_profit = params['take_profit']
            stop_loss = params['stop_loss']

            self.logger.info(f"🛠️ Изменение TP/SL для {symbol}: TP={take_profit}, SL={stop_loss}")
            
            result = self.session.set_trading_stop(
                category="linear",
                symbol=symbol,
                takeProfit=str(take_profit),
                stopLoss=str(stop_loss),
                positionIdx=0  # 0 для одностороннего режима
            )
            
            if result.get('retCode') == 0:
                self.logger.info(f"✅ TP/SL для {symbol} успешно изменен.")
                return {"success": True, "result": result}
            else:
                self.logger.error(f"❌ Ошибка изменения TP/SL для {symbol}: {result.get('retMsg')}")
                return {"success": False, "error": result.get('retMsg')}

        except Exception as e:
            self.logger.error(f"❌ Исключение при изменении TP/SL для {symbol}: {e}")
            return {"success": False, "error": str(e)}
    
    def open_order_with_tp_sl(self, params: Dict) -> Dict:
        """Открыть ордер с TP/SL"""
        try:
            bybitSide = "Buy" if params['side'] == "LONG" else "Sell"
            symbol = params['symbol'] + 'USDT'
            size = params['size']
            leverage = params['leverage']
            take_profit = params['take_profit']
            stop_loss = params['stop_loss']
            # Устанавливаем плечо
            try:
                self.session.set_leverage(
                    category="linear",
                    symbol=symbol,
                    buyLeverage=str(leverage),
                    sellLeverage=str(leverage)
                )
            except Exception as e:
                self.logger.error(f"❌ Ошибка установки плеча: {e}")
            
            # Открываем позицию
            order_result = self.session.place_order(
                category="linear",
                symbol=symbol,
                side=bybitSide,
                orderType="Market",
                qty=str(size),
                takeProfit=str(take_profit),
                stopLoss=str(stop_loss),
                timeInForce="IOC"
            )
            
            if order_result.get('retCode') == 0:
                # tp_sl_result = self._set_take_profit_stop_loss(symbol, bybitSide, size, take_profit, stop_loss)
                
                self.logger.info(f"✅ Ордер открыт: {symbol} {bybitSide} {size}")
                return {"orderId": order_result.get('result', {}).get('orderId'), 'success': True, 'tpOrderId': None, 'slOrderId': None, 'avgPrice': order_result.get('result', {}).get('avgPrice')}
            else:
                self.logger.error(f"❌ Ошибка открытия ордера: {order_result}")
                return {"orderId": None, 'success': False, 'tpOrderId': None, 'slOrderId': None, 'error': order_result.get('retMsg', 'Unknown error')}
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка открытия ордера: {e}")
            return {'retCode': 1, 'retMsg': str(e)}

    def calculate_position_size(self, symbol: str, usdtSize: float,lastPrice: float) -> float:
        try:
            info = self.session.get_instruments_info(category='linear', symbol=symbol + 'USDT')
            if info and info.get('result') and info['result'].get('list'):
                lot_size_filter = info['result']['list'][0]['lotSizeFilter']
                min_order_qty = float(lot_size_filter['minOrderQty'])
                qty_step = float(lot_size_filter['qtyStep'])
                min_notional_value = float(lot_size_filter['minNotionalValue'])
    
                if usdtSize < min_notional_value:
                    raise ValueError(f"Сумма {usdtSize} USDT меньше минимальной {min_notional_value} USDT")
    
                btc_amount = usdtSize / lastPrice
    
                step_decimal_places = len(str(qty_step).split('.')[-1]) if '.' in str(qty_step) else 0
                btc_amount_rounded = round(btc_amount, step_decimal_places)
    
                step_multiplier = round(btc_amount_rounded / qty_step)
                final_amount = step_multiplier * qty_step
    
                if final_amount < min_order_qty:
                    raise ValueError(f"Сумма {final_amount} меньше минимальной {min_order_qty}")
    

                self.logger.info(f"✅ Размер позиции для {symbol}: final_amount: {final_amount} {symbol} usdtSize: {usdtSize}USDT lastPrice: {lastPrice}USDT qty_step: {qty_step} min_order_qty: {min_order_qty}")
                return round(final_amount, 8)
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета размера позиции: {e}")
            return 0
        
