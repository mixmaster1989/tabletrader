#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Упрощенный OKX API для Google Signals Bot
"""

import logging
import okx.Trade as Trade
import okx.Account as Account
import okx.PublicData as PublicData
from typing import Dict, List, Optional

class OKXAPI:
    def __init__(self, api_key: str, api_secret: str, passphrase: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.testnet = testnet
        print(api_key)
        print(api_secret)
        print(passphrase)
        self.logger = logging.getLogger(__name__)
        
        # Инициализация API клиентов
        self.account_api = Account.AccountAPI(api_key=api_key, api_secret_key=api_secret, passphrase=passphrase,flag='0')
        self.trade_api = Trade.TradeAPI(api_key=api_key, api_secret_key=api_secret, passphrase=passphrase,flag='0')
        self.public_api = PublicData.PublicAPI()

        self.logger.info(f"✅ OKX API инициализирован (testnet: {testnet})")

    def get_last_price(self, symbol: str) -> Optional[float]:
        """Получить текущую цену для SWAP инструмента"""
        try:
            instrument_id = f"{symbol}-USDT-SWAP"
            result = self.public_api.get_mark_price(instType='SWAP', instId=instrument_id)
            
            if result and result.get('code') == '0':
                data = result.get('data', [])
                if data:
                    price = float(data[0]['markPx'])
                    return price
            
            self.logger.error(f"❌ Не удалось получить цену для {instrument_id}. Ответ API: {result}")
            return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения цены для {symbol}: {e}")
            return None

    def get_positions(self, symbol: str = None) -> List[Dict]:
        """Получить открытые позиции по SWAP"""
        try:
            instrument_id = f"{symbol}-USDT-SWAP" if symbol else None
            result = self.account_api.get_positions(instType='SWAP', instId=instrument_id)
            
            if result and result.get('code') == '0':
                positions = result.get('data', [])
                open_positions = [p for p in positions if float(p.get('pos', '0')) != 0]
                return open_positions
            else:
                self.logger.error(f"❌ Ошибка получения позиций: {result.get('msg', 'Нет данных')}")
                return []
            
        except Exception as e:
            self.logger.error(f"❌ Исключение при получении позиций: {e}")
            return []

    def get_balance(self) -> Dict:
        """Получить баланс торгового аккаунта"""
        try:
            result = self.account_api.get_account_balance()
            
            if result and result.get('code') == '0':
                balance_data = result.get('data', [{}])[0]
                return balance_data
            else:
                self.logger.error(f"❌ Ошибка получения баланса: {result.get('msg', 'Нет данных')}")
                return {}
                
        except Exception as e:
            self.logger.error(f"❌ Исключение при получении баланса: {e}")
            return {}

    def modify_trading_stop(self, params: Dict) -> Dict:
        """Изменить TP/SL для существующей позиции"""
        try:
            instrument_id = f"{params['symbol']}-USDT-SWAP"
            
            self.logger.info(f"🛠️ Изменение TP/SL для {instrument_id}: TP={params['take_profit']}, SL={params['stop_loss']}")

            result = self.trade_api.amend_algo_order(
                instId=instrument_id,
                algoId=params['algo_id'],
                newTpTriggerPx=str(params['take_profit']),
                newSlTriggerPx=str(params['stop_loss'])
            )

            if result.get('code') == '0':
                self.logger.info(f"✅ TP/SL для {instrument_id} успешно изменен.")
                return {"success": True, "result": result.get('data', [{}])[0]}
            else:
                self.logger.error(f"❌ Ошибка изменения TP/SL для {instrument_id}: {result.get('msg')}")
                return {"success": False, "error": result.get('msg')}

        except Exception as e:
            self.logger.error(f"❌ Исключение при изменении TP/SL для {params['symbol']}: {e}")
            return {"success": False, "error": str(e)}

    def open_order_with_tp_sl(self, params: Dict) -> Dict:
        """Открыть ордер с TP/SL"""
        try:
            side = 'buy' if params['side'] == 'LONG' else 'sell'
            instrument_id = f"{params['symbol']}-USDT-SWAP"
            size = params['size']
            leverage = params['leverage']
            take_profit = params['take_profit']
            stop_loss = params['stop_loss']

            # 1. Установить плечо
            self.account_api.set_leverage(
                instId=instrument_id,
                lever=str(leverage),
                mgnMode='isolated'
            )
            self.logger.info(f"✅ Плечо {leverage}x для {instrument_id} установлено.")

            # 2. Открыть рыночный ордер
            order_result = self.trade_api.place_order(
                instId=instrument_id,
                tdMode='isolated',
                side=side,
                ordType='market',
                sz=str(size),
                tpTriggerPx=str(take_profit),
                slTriggerPx=str(stop_loss)
            )

            if order_result.get('code') == '0':
                order_data = order_result.get('data', [{}])[0]
                self.logger.info(f"✅ Ордер открыт: {instrument_id} {side} {size}")
                return {"orderId": order_data.get('ordId'), 'success': True}
            else:
                self.logger.error(f"❌ Ошибка открытия ордера: {order_result.get('msg')}")
                return {"orderId": None, 'success': False, 'error': order_result.get('msg')}

        except Exception as e:
            self.logger.error(f"❌ Ошибка открытия ордера: {e}")
            return {'success': False, 'error': str(e)}

    def calculate_position_size(self, symbol: str, usdt_size: float, last_price: float) -> Optional[float]:
        """Рассчитать размер позиции в контрактах (для SWAP)"""
        try:
            instrument_id = f"{symbol}-USDT-SWAP"
            # Получаем информацию об инструменте
            result = self.public_api.get_instruments(instType='SWAP', instId=instrument_id)
            if not (result and result.get('code') == '0' and result.get('data')):
                self.logger.error(f"Не удалось получить информацию для {instrument_id}")
                return None

            instrument_info = result['data'][0]
            ct_val = float(instrument_info['ctVal'])  # Стоимость одного контракта в USD
            min_sz = float(instrument_info['minSz'])    # Минимальный размер ордера в контрактах
            lot_sz = float(instrument_info['lotSz'])    # Шаг лота в контрактах

            # Рассчитываем количество контрактов
            num_contracts = usdt_size / (ct_val * last_price)
            
            # Округляем до ближайшего шага лота
            final_quantity = round(num_contracts / lot_sz) * lot_sz

            # Проверяем минимальный размер
            if final_quantity < min_sz:
                self.logger.warning(f"Рассчитанный размер {final_quantity} меньше minSz {min_sz}, устанавливаю minSz.")
                final_quantity = min_sz

            self.logger.info(f"✅ Размер позиции для {instrument_id}: {final_quantity} контрактов (на сумму ~{usdt_size} USDT)")
            return round(final_quantity, 8)

        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета размера позиции для {symbol}: {e}")
            return None
