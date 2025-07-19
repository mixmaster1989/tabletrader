#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Анализатор рынка для генерации торговых сигналов
"""

import logging
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from bybit_api import BybitAPI

@dataclass
class TradingSignal:
    symbol: str
    direction: str  # 'LONG' или 'SHORT'
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float  # 0.0 - 1.0
    strategy: str
    reasoning: str
    risk_reward_ratio: float

class MarketAnalyzer:
    def __init__(self, bybit_api: BybitAPI):
        self.bybit_api = bybit_api
        self.logger = logging.getLogger(__name__)
        
    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
        """Получить исторические данные"""
        try:
            # Получаем данные через Bybit API
            result = self.bybit_api.session.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            if result.get('retCode') == 0:
                klines = result.get('result', {}).get('list', [])
                
                # Преобразуем в DataFrame
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
                ])
                
                # Конвертируем типы
                for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                return df
            else:
                self.logger.error(f"❌ Ошибка получения данных: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения klines для {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Рассчитать технические индикаторы"""
        try:
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'], period=14)
            
            # MACD
            df['ema12'] = df['close'].ewm(span=12).mean()
            df['ema26'] = df['close'].ewm(span=26).mean()
            df['macd'] = df['ema12'] - df['ema26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # Stochastic
            df['stoch_k'] = self._calculate_stochastic(df, period=14)
            df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
            
            # ATR (Average True Range)
            df['atr'] = self._calculate_atr(df, period=14)
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета индикаторов: {e}")
            return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Рассчитать RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_stochastic(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Рассчитать Stochastic"""
        lowest_low = df['low'].rolling(window=period).min()
        highest_high = df['high'].rolling(window=period).max()
        k = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        return k
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Рассчитать ATR"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def analyze_symbol(self, symbol: str) -> List[TradingSignal]:
        """Анализировать символ и генерировать сигналы"""
        try:
            self.logger.info(f"🔍 Анализируем {symbol}...")
            
            # Получаем данные
            df = self.get_klines(symbol, interval="1h", limit=100)
            if df is None or df.empty:
                return []
            
            # Рассчитываем индикаторы
            df = self.calculate_indicators(df)
            
            # Получаем текущую цену
            current_price = self.bybit_api.get_last_price(symbol)
            if current_price is None:
                return []
            
            signals = []
            
            # Стратегия 1: RSI + MACD
            signal1 = self._rsi_macd_strategy(df, symbol, current_price)
            if signal1:
                signals.append(signal1)
            
            # Стратегия 2: Bollinger Bands + Volume
            signal2 = self._bollinger_volume_strategy(df, symbol, current_price)
            if signal2:
                signals.append(signal2)
            
            # Стратегия 3: Stochastic + ATR
            signal3 = self._stochastic_atr_strategy(df, symbol, current_price)
            if signal3:
                signals.append(signal3)
            
            # Сортируем по уверенности
            signals.sort(key=lambda x: x.confidence, reverse=True)
            
            self.logger.info(f"✅ Сгенерировано {len(signals)} сигналов для {symbol}")
            return signals[:3]  # Возвращаем топ-3
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа {symbol}: {e}")
            return []
    
    def _rsi_macd_strategy(self, df: pd.DataFrame, symbol: str, current_price: float) -> Optional[TradingSignal]:
        """Стратегия на основе RSI и MACD"""
        try:
            if len(df) < 30:
                return None
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Условия для LONG
            rsi_oversold = latest['rsi'] < 30 and prev['rsi'] >= 30
            macd_bullish = latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']
            
            # Условия для SHORT
            rsi_overbought = latest['rsi'] > 70 and prev['rsi'] <= 70
            macd_bearish = latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']
            
            if rsi_oversold and macd_bullish:
                # LONG сигнал
                atr = latest['atr']
                entry_price = current_price
                take_profit = entry_price + (atr * 2)
                stop_loss = entry_price - (atr * 1.5)
                confidence = min(0.8, (30 - latest['rsi']) / 30 * 0.8)
                
                return TradingSignal(
                    symbol=symbol,
                    direction='LONG',
                    entry_price=entry_price,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    confidence=confidence,
                    strategy='RSI + MACD',
                    reasoning=f"RSI oversold ({latest['rsi']:.1f}), MACD bullish crossover",
                    risk_reward_ratio=(take_profit - entry_price) / (entry_price - stop_loss)
                )
            
            elif rsi_overbought and macd_bearish:
                # SHORT сигнал
                atr = latest['atr']
                entry_price = current_price
                take_profit = entry_price - (atr * 2)
                stop_loss = entry_price + (atr * 1.5)
                confidence = min(0.8, (latest['rsi'] - 70) / 30 * 0.8)
                
                return TradingSignal(
                    symbol=symbol,
                    direction='SHORT',
                    entry_price=entry_price,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    confidence=confidence,
                    strategy='RSI + MACD',
                    reasoning=f"RSI overbought ({latest['rsi']:.1f}), MACD bearish crossover",
                    risk_reward_ratio=(entry_price - take_profit) / (stop_loss - entry_price)
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка RSI+MACD стратегии: {e}")
            return None
    
    def _bollinger_volume_strategy(self, df: pd.DataFrame, symbol: str, current_price: float) -> Optional[TradingSignal]:
        """Стратегия на основе Bollinger Bands и объема"""
        try:
            if len(df) < 20:
                return None
            
            latest = df.iloc[-1]
            
            # Проверяем объем
            volume_spike = latest['volume_ratio'] > 1.5
            
            if volume_spike:
                # LONG если цена близко к нижней полосе
                if current_price <= latest['bb_lower'] * 1.01:
                    atr = latest['atr']
                    entry_price = current_price
                    take_profit = latest['bb_middle']  # Цель - средняя линия
                    stop_loss = entry_price - (atr * 1.2)
                    confidence = min(0.7, latest['volume_ratio'] / 3 * 0.7)
                    
                    return TradingSignal(
                        symbol=symbol,
                        direction='LONG',
                        entry_price=entry_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                        confidence=confidence,
                        strategy='Bollinger + Volume',
                        reasoning=f"Price at BB lower band, volume spike ({latest['volume_ratio']:.1f}x)",
                        risk_reward_ratio=(take_profit - entry_price) / (entry_price - stop_loss)
                    )
                
                # SHORT если цена близко к верхней полосе
                elif current_price >= latest['bb_upper'] * 0.99:
                    atr = latest['atr']
                    entry_price = current_price
                    take_profit = latest['bb_middle']  # Цель - средняя линия
                    stop_loss = entry_price + (atr * 1.2)
                    confidence = min(0.7, latest['volume_ratio'] / 3 * 0.7)
                    
                    return TradingSignal(
                        symbol=symbol,
                        direction='SHORT',
                        entry_price=entry_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                        confidence=confidence,
                        strategy='Bollinger + Volume',
                        reasoning=f"Price at BB upper band, volume spike ({latest['volume_ratio']:.1f}x)",
                        risk_reward_ratio=(entry_price - take_profit) / (stop_loss - entry_price)
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка Bollinger+Volume стратегии: {e}")
            return None
    
    def _stochastic_atr_strategy(self, df: pd.DataFrame, symbol: str, current_price: float) -> Optional[TradingSignal]:
        """Стратегия на основе Stochastic и ATR"""
        try:
            if len(df) < 20:
                return None
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Условия для LONG
            stoch_oversold = latest['stoch_k'] < 20 and latest['stoch_d'] < 20
            stoch_bullish = latest['stoch_k'] > latest['stoch_d'] and prev['stoch_k'] <= prev['stoch_d']
            
            # Условия для SHORT
            stoch_overbought = latest['stoch_k'] > 80 and latest['stoch_d'] > 80
            stoch_bearish = latest['stoch_k'] < latest['stoch_d'] and prev['stoch_k'] >= prev['stoch_d']
            
            if stoch_oversold and stoch_bullish:
                # LONG сигнал
                atr = latest['atr']
                entry_price = current_price
                take_profit = entry_price + (atr * 2.5)
                stop_loss = entry_price - (atr * 1.8)
                confidence = min(0.6, (20 - latest['stoch_k']) / 20 * 0.6)
                
                return TradingSignal(
                    symbol=symbol,
                    direction='LONG',
                    entry_price=entry_price,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    confidence=confidence,
                    strategy='Stochastic + ATR',
                    reasoning=f"Stochastic oversold ({latest['stoch_k']:.1f}), bullish crossover",
                    risk_reward_ratio=(take_profit - entry_price) / (entry_price - stop_loss)
                )
            
            elif stoch_overbought and stoch_bearish:
                # SHORT сигнал
                atr = latest['atr']
                entry_price = current_price
                take_profit = entry_price - (atr * 2.5)
                stop_loss = entry_price + (atr * 1.8)
                confidence = min(0.6, (latest['stoch_k'] - 80) / 20 * 0.6)
                
                return TradingSignal(
                    symbol=symbol,
                    direction='SHORT',
                    entry_price=entry_price,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    confidence=confidence,
                    strategy='Stochastic + ATR',
                    reasoning=f"Stochastic overbought ({latest['stoch_k']:.1f}), bearish crossover",
                    risk_reward_ratio=(entry_price - take_profit) / (stop_loss - entry_price)
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка Stochastic+ATR стратегии: {e}")
            return None
    
    def get_popular_symbols(self) -> List[str]:
        """Получить список популярных символов для анализа"""
        return [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'XRPUSDT',
            'BNBUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOGEUSDT', 'NEARUSDT',
            'PEOPLEUSDT', 'MATICUSDT', 'DOTUSDT', 'LTCUSDT', 'BCHUSDT'
        ]
    
    def analyze_all_symbols(self) -> Dict[str, List[TradingSignal]]:
        """Анализировать все популярные символы"""
        results = {}
        symbols = self.get_popular_symbols()
        
        for symbol in symbols:
            try:
                signals = self.analyze_symbol(symbol)
                if signals:
                    results[symbol] = signals
                time.sleep(0.5)  # Небольшая задержка между запросами
            except Exception as e:
                self.logger.error(f"❌ Ошибка анализа {symbol}: {e}")
                continue
        
        return results 