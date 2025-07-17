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
        
        # Кэш для цен
        self._price_cache = {}
        self._cache_duration = 5  # секунды
        
        self.logger.info(f"✅ Bybit API инициализирован (testnet: {testnet})")
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Получить текущую цену"""
        try:
            # Проверяем кэш
            if symbol in self._price_cache:
                cached_price, timestamp = self._price_cache[symbol]
                if time.time() - timestamp < self._cache_duration:
                    return cached_price
            
            # Получаем цену с API
            result = self.session.get_tickers(category="linear", symbol=symbol)
            ticker_list = result.get('result', {}).get('list', [])
            
            if ticker_list and 'lastPrice' in ticker_list[0]:
                price = float(ticker_list[0]['lastPrice'])
                # Сохраняем в кэш
                self._price_cache[symbol] = (price, time.time())
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
            result = self.session.get_positions(category="linear")
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
    
    def open_order_with_tp_sl(self, params: Dict) -> Dict:
        """Открыть ордер с TP/SL"""
        try:
            symbol = params['symbol']
            side = params['side']
            size = params['size']
            leverage = params['leverage']
            take_profit = params['take_profit']
            stop_loss = params['stop_loss']
            
            # Устанавливаем плечо
            self.session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
            
            # Открываем позицию
            order_result = self.session.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=str(size),
                timeInForce="GTC"
            )
            
            if order_result.get('retCode') == 0:
                # Устанавливаем TP/SL
                self._set_take_profit_stop_loss(symbol, side, size, take_profit, stop_loss)
                
                self.logger.info(f"✅ Ордер открыт: {symbol} {side} {size}")
                return order_result
            else:
                self.logger.error(f"❌ Ошибка открытия ордера: {order_result}")
                return order_result
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка открытия ордера: {e}")
            return {'retCode': 1, 'retMsg': str(e)}
    
    def _set_take_profit_stop_loss(self, symbol: str, side: str, size: str, tp: float, sl: float):
        """Установить TP/SL"""
        try:
            # Take Profit
            if tp > 0:
                tp_side = "Sell" if side == "Buy" else "Buy"
                self.session.place_order(
                    category="linear",
                    symbol=symbol,
                    side=tp_side,
                    orderType="Limit",
                    qty=size,
                    price=str(tp),
                    timeInForce="GTC",
                    takeProfit=str(tp)
                )
            
            # Stop Loss
            if sl > 0:
                sl_side = "Sell" if side == "Buy" else "Buy"
                self.session.place_order(
                    category="linear",
                    symbol=symbol,
                    side=sl_side,
                    orderType="Stop",
                    qty=size,
                    price=str(sl),
                    stopPrice=str(sl),
                    timeInForce="GTC",
                    stopLoss=str(sl)
                )
            
            self.logger.info(f"✅ TP/SL установлены для {symbol}: TP={tp}, SL={sl}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка установки TP/SL: {e}")
    
    def close_position(self, symbol: str, side: str = None) -> Dict:
        """Закрыть позицию"""
        try:
            positions = self.get_positions(symbol)
            
            for pos in positions:
                if pos.get('symbol') == symbol:
                    pos_side = pos.get('side')
                    pos_size = pos.get('size')
                    
                    if side is None or pos_side == side:
                        close_side = "Sell" if pos_side == "Buy" else "Buy"
                        
                        result = self.session.place_order(
                            category="linear",
                            symbol=symbol,
                            side=close_side,
                            orderType="Market",
                            qty=pos_size,
                            timeInForce="GTC",
                            reduceOnly=True
                        )
                        
                        self.logger.info(f"✅ Позиция закрыта: {symbol}")
                        return result
            
            return {'retCode': 1, 'retMsg': 'Position not found'}
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка закрытия позиции: {e}")
            return {'retCode': 1, 'retMsg': str(e)}
    
    def get_min_qty(self, symbol: str) -> float:
        """Получить минимальный размер лота"""
        try:
            info = self.session.get_instruments_info(category='linear', symbol=symbol)
            if info and info.get('result') and info['result'].get('list'):
                lot_info = info['result']['list'][0].get('lotSizeFilter', {})
                min_qty = float(lot_info.get('minOrderQty', 0.001))
                return min_qty
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения min_qty: {e}")
        
        # Fallback значения
        fallback_min_qty = {
            'BTCUSDT': 0.001, 'ETHUSDT': 0.01, 'SOLUSDT': 0.1,
            'LINKUSDT': 0.1, 'DOGEUSDT': 1.0, 'XRPUSDT': 1.0,
            'BNBUSDT': 0.01, 'ADAUSDT': 1.0, 'AVAXUSDT': 0.1
        }
        return fallback_min_qty.get(symbol, 0.01) 