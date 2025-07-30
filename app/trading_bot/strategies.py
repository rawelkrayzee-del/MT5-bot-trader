"""
Comprehensive trading strategies for the forex trading bot.
This module contains various algorithmic trading strategies.
"""

import pandas as pd
import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import talib
from django.utils import timezone
from datetime import timedelta

from forex_trading.models import MarketData, TechnicalIndicator, CurrencyPair


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, parameters: Dict):
        self.parameters = parameters
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signal(self, market_data: List[MarketData], 
                       indicators: List[TechnicalIndicator]) -> Dict:
        """
        Generate trading signal based on market data and indicators
        Returns: {
            'action': 'buy' | 'sell' | 'hold',
            'confidence': float (0-1),
            'stop_loss': float,
            'take_profit': float,
            'reason': str
        }
        """
        pass
    
    def calculate_position_size(self, account_balance: Decimal, 
                              risk_percentage: Decimal, 
                              stop_loss_pips: int) -> Decimal:
        """Calculate position size based on risk management"""
        risk_amount = account_balance * (risk_percentage / 100)
        pip_value = Decimal('10')  # Simplified - should be calculated based on currency pair
        position_size = risk_amount / (stop_loss_pips * pip_value)
        return max(position_size, Decimal('0.01'))  # Minimum position size


class SMAStrateg(BaseStrategy):
    """Simple Moving Average Crossover Strategy"""
    
    def __init__(self, parameters: Dict = None):
        default_params = {
            'fast_period': 20,
            'slow_period': 50,
            'stop_loss_pips': 20,
            'take_profit_pips': 40
        }
        if parameters:
            default_params.update(parameters)
        super().__init__(default_params)
    
    def generate_signal(self, market_data: List[MarketData], 
                       indicators: List[TechnicalIndicator]) -> Dict:
        if len(indicators) < 2:
            return {'action': 'hold', 'confidence': 0, 'reason': 'Insufficient data'}
        
        latest = indicators[0]
        previous = indicators[1]
        
        if not (latest.sma_20 and latest.sma_50 and previous.sma_20 and previous.sma_50):
            return {'action': 'hold', 'confidence': 0, 'reason': 'Missing SMA data'}
        
        # Golden Cross (fast SMA crosses above slow SMA)
        if (latest.sma_20 > latest.sma_50 and previous.sma_20 <= previous.sma_50):
            return {
                'action': 'buy',
                'confidence': 0.8,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': 'Golden Cross - Fast SMA crossed above Slow SMA'
            }
        
        # Death Cross (fast SMA crosses below slow SMA)
        elif (latest.sma_20 < latest.sma_50 and previous.sma_20 >= previous.sma_50):
            return {
                'action': 'sell',
                'confidence': 0.8,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': 'Death Cross - Fast SMA crossed below Slow SMA'
            }
        
        return {'action': 'hold', 'confidence': 0, 'reason': 'No crossover signal'}


class RSIStrategy(BaseStrategy):
    """RSI Oversold/Overbought Strategy"""
    
    def __init__(self, parameters: Dict = None):
        default_params = {
            'oversold_threshold': 30,
            'overbought_threshold': 70,
            'rsi_period': 14,
            'stop_loss_pips': 15,
            'take_profit_pips': 30
        }
        if parameters:
            default_params.update(parameters)
        super().__init__(default_params)
    
    def generate_signal(self, market_data: List[MarketData], 
                       indicators: List[TechnicalIndicator]) -> Dict:
        if not indicators:
            return {'action': 'hold', 'confidence': 0, 'reason': 'No indicator data'}
        
        latest = indicators[0]
        
        if not latest.rsi:
            return {'action': 'hold', 'confidence': 0, 'reason': 'Missing RSI data'}
        
        rsi_value = float(latest.rsi)
        
        # Oversold condition
        if rsi_value < self.parameters['oversold_threshold']:
            confidence = min((self.parameters['oversold_threshold'] - rsi_value) / 10, 1.0)
            return {
                'action': 'buy',
                'confidence': confidence,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': f'RSI Oversold: {rsi_value:.2f}'
            }
        
        # Overbought condition
        elif rsi_value > self.parameters['overbought_threshold']:
            confidence = min((rsi_value - self.parameters['overbought_threshold']) / 10, 1.0)
            return {
                'action': 'sell',
                'confidence': confidence,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': f'RSI Overbought: {rsi_value:.2f}'
            }
        
        return {'action': 'hold', 'confidence': 0, 'reason': f'RSI Neutral: {rsi_value:.2f}'}


class MACDStrategy(BaseStrategy):
    """MACD Signal Strategy"""
    
    def __init__(self, parameters: Dict = None):
        default_params = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'stop_loss_pips': 25,
            'take_profit_pips': 50
        }
        if parameters:
            default_params.update(parameters)
        super().__init__(default_params)
    
    def generate_signal(self, market_data: List[MarketData], 
                       indicators: List[TechnicalIndicator]) -> Dict:
        if len(indicators) < 2:
            return {'action': 'hold', 'confidence': 0, 'reason': 'Insufficient data'}
        
        latest = indicators[0]
        previous = indicators[1]
        
        if not (latest.macd and latest.macd_signal and 
                previous.macd and previous.macd_signal):
            return {'action': 'hold', 'confidence': 0, 'reason': 'Missing MACD data'}
        
        # MACD bullish signal (MACD crosses above signal line)
        if (latest.macd > latest.macd_signal and 
            previous.macd <= previous.macd_signal):
            histogram = latest.macd - latest.macd_signal
            confidence = min(abs(float(histogram)) * 1000, 1.0)  # Scale histogram for confidence
            return {
                'action': 'buy',
                'confidence': confidence,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': 'MACD Bullish Crossover'
            }
        
        # MACD bearish signal (MACD crosses below signal line)
        elif (latest.macd < latest.macd_signal and 
              previous.macd >= previous.macd_signal):
            histogram = latest.macd_signal - latest.macd
            confidence = min(abs(float(histogram)) * 1000, 1.0)
            return {
                'action': 'sell',
                'confidence': confidence,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': 'MACD Bearish Crossover'
            }
        
        return {'action': 'hold', 'confidence': 0, 'reason': 'No MACD crossover'}


class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands Mean Reversion Strategy"""
    
    def __init__(self, parameters: Dict = None):
        default_params = {
            'period': 20,
            'std_dev': 2.0,
            'stop_loss_pips': 20,
            'take_profit_pips': 30
        }
        if parameters:
            default_params.update(parameters)
        super().__init__(default_params)
    
    def generate_signal(self, market_data: List[MarketData], 
                       indicators: List[TechnicalIndicator]) -> Dict:
        if not indicators:
            return {'action': 'hold', 'confidence': 0, 'reason': 'No indicator data'}
        
        latest = indicators[0]
        
        if not (latest.bb_upper and latest.bb_lower and latest.bb_middle):
            return {'action': 'hold', 'confidence': 0, 'reason': 'Missing Bollinger Bands data'}
        
        if not market_data:
            return {'action': 'hold', 'confidence': 0, 'reason': 'No market data'}
        
        current_price = (market_data[0].bid + market_data[0].ask) / 2
        
        bb_upper = float(latest.bb_upper)
        bb_lower = float(latest.bb_lower)
        bb_middle = float(latest.bb_middle)
        
        # Price touches or crosses below lower band (oversold)
        if float(current_price) <= bb_lower:
            # Calculate distance from lower band for confidence
            distance = (bb_middle - float(current_price)) / (bb_middle - bb_lower)
            confidence = min(distance, 1.0)
            return {
                'action': 'buy',
                'confidence': confidence,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': 'Price at Lower Bollinger Band'
            }
        
        # Price touches or crosses above upper band (overbought)
        elif float(current_price) >= bb_upper:
            distance = (float(current_price) - bb_middle) / (bb_upper - bb_middle)
            confidence = min(distance, 1.0)
            return {
                'action': 'sell',
                'confidence': confidence,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': 'Price at Upper Bollinger Band'
            }
        
        return {'action': 'hold', 'confidence': 0, 'reason': 'Price within Bollinger Bands'}


class ComboStrategy(BaseStrategy):
    """Combined strategy using multiple indicators"""
    
    def __init__(self, parameters: Dict = None):
        default_params = {
            'rsi_weight': 0.3,
            'macd_weight': 0.4,
            'sma_weight': 0.3,
            'min_confidence': 0.6,
            'stop_loss_pips': 20,
            'take_profit_pips': 40
        }
        if parameters:
            default_params.update(parameters)
        super().__init__(default_params)
        
        # Initialize individual strategies
        self.rsi_strategy = RSIStrategy()
        self.macd_strategy = MACDStrategy()
        self.sma_strategy = SMAStrateg()
    
    def generate_signal(self, market_data: List[MarketData], 
                       indicators: List[TechnicalIndicator]) -> Dict:
        # Get signals from individual strategies
        rsi_signal = self.rsi_strategy.generate_signal(market_data, indicators)
        macd_signal = self.macd_strategy.generate_signal(market_data, indicators)
        sma_signal = self.sma_strategy.generate_signal(market_data, indicators)
        
        # Calculate weighted scores
        buy_score = 0
        sell_score = 0
        reasons = []
        
        # RSI contribution
        if rsi_signal['action'] == 'buy':
            buy_score += rsi_signal['confidence'] * self.parameters['rsi_weight']
            reasons.append(f"RSI: {rsi_signal['reason']}")
        elif rsi_signal['action'] == 'sell':
            sell_score += rsi_signal['confidence'] * self.parameters['rsi_weight']
            reasons.append(f"RSI: {rsi_signal['reason']}")
        
        # MACD contribution
        if macd_signal['action'] == 'buy':
            buy_score += macd_signal['confidence'] * self.parameters['macd_weight']
            reasons.append(f"MACD: {macd_signal['reason']}")
        elif macd_signal['action'] == 'sell':
            sell_score += macd_signal['confidence'] * self.parameters['macd_weight']
            reasons.append(f"MACD: {macd_signal['reason']}")
        
        # SMA contribution
        if sma_signal['action'] == 'buy':
            buy_score += sma_signal['confidence'] * self.parameters['sma_weight']
            reasons.append(f"SMA: {sma_signal['reason']}")
        elif sma_signal['action'] == 'sell':
            sell_score += sma_signal['confidence'] * self.parameters['sma_weight']
            reasons.append(f"SMA: {sma_signal['reason']}")
        
        # Determine final signal
        max_score = max(buy_score, sell_score)
        
        if max_score < self.parameters['min_confidence']:
            return {
                'action': 'hold',
                'confidence': 0,
                'reason': f'Combined confidence too low: {max_score:.2f}'
            }
        
        if buy_score > sell_score:
            return {
                'action': 'buy',
                'confidence': buy_score,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': f'Combined Buy Signal: {"; ".join(reasons)}'
            }
        else:
            return {
                'action': 'sell',
                'confidence': sell_score,
                'stop_loss_pips': self.parameters['stop_loss_pips'],
                'take_profit_pips': self.parameters['take_profit_pips'],
                'reason': f'Combined Sell Signal: {"; ".join(reasons)}'
            }


# Strategy factory
STRATEGY_CLASSES = {
    'sma_crossover': SMAStrateg,
    'rsi_oversold': RSIStrategy,
    'macd': MACDStrategy,
    'bollinger_bands': BollingerBandsStrategy,
    'combo': ComboStrategy,
}


def get_strategy(strategy_type: str, parameters: Dict = None) -> BaseStrategy:
    """Factory function to create strategy instances"""
    if strategy_type not in STRATEGY_CLASSES:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    return STRATEGY_CLASSES[strategy_type](parameters)


def calculate_technical_indicators(currency_pair: CurrencyPair, 
                                 timeframe: str = '1H', 
                                 periods: int = 100) -> TechnicalIndicator:
    """
    Calculate technical indicators for a currency pair
    """
    # Get market data
    end_time = timezone.now()
    start_time = end_time - timedelta(hours=periods)
    
    market_data = MarketData.objects.filter(
        currency_pair=currency_pair,
        timestamp__range=[start_time, end_time]
    ).order_by('timestamp')
    
    if len(market_data) < 50:  # Minimum required for calculations
        return None
    
    # Convert to pandas DataFrame
    df = pd.DataFrame([
        {
            'timestamp': data.timestamp,
            'open': float((data.bid + data.ask) / 2),
            'high': float(data.high) if data.high else float((data.bid + data.ask) / 2),
            'low': float(data.low) if data.low else float((data.bid + data.ask) / 2),
            'close': float((data.bid + data.ask) / 2),
            'volume': data.volume
        }
        for data in market_data
    ])
    
    df.set_index('timestamp', inplace=True)
    
    # Calculate indicators using TA-Lib
    close_prices = df['close'].values
    
    try:
        # Moving Averages
        sma_20 = talib.SMA(close_prices, timeperiod=20)[-1]
        sma_50 = talib.SMA(close_prices, timeperiod=50)[-1]
        sma_200 = talib.SMA(close_prices, timeperiod=200)[-1] if len(close_prices) >= 200 else None
        ema_20 = talib.EMA(close_prices, timeperiod=20)[-1]
        
        # RSI
        rsi = talib.RSI(close_prices, timeperiod=14)[-1]
        
        # MACD
        macd_line, macd_signal, macd_histogram = talib.MACD(close_prices)
        macd = macd_line[-1]
        macd_signal_val = macd_signal[-1]
        macd_hist = macd_histogram[-1]
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close_prices, timeperiod=20)
        
        # Create TechnicalIndicator instance
        indicator = TechnicalIndicator(
            currency_pair=currency_pair,
            timeframe=timeframe,
            timestamp=end_time,
            sma_20=Decimal(str(sma_20)) if not np.isnan(sma_20) else None,
            sma_50=Decimal(str(sma_50)) if not np.isnan(sma_50) else None,
            sma_200=Decimal(str(sma_200)) if sma_200 and not np.isnan(sma_200) else None,
            ema_20=Decimal(str(ema_20)) if not np.isnan(ema_20) else None,
            rsi=Decimal(str(rsi)) if not np.isnan(rsi) else None,
            macd=Decimal(str(macd)) if not np.isnan(macd) else None,
            macd_signal=Decimal(str(macd_signal_val)) if not np.isnan(macd_signal_val) else None,
            macd_histogram=Decimal(str(macd_hist)) if not np.isnan(macd_hist) else None,
            bb_upper=Decimal(str(bb_upper[-1])) if not np.isnan(bb_upper[-1]) else None,
            bb_middle=Decimal(str(bb_middle[-1])) if not np.isnan(bb_middle[-1]) else None,
            bb_lower=Decimal(str(bb_lower[-1])) if not np.isnan(bb_lower[-1]) else None,
        )
        
        return indicator
        
    except Exception as e:
        print(f"Error calculating indicators: {e}")
        return None