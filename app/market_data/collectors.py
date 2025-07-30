"""
Market data collectors for various forex data providers.
This module handles real-time and historical data collection.
"""

import requests
import json
import websocket
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Callable
from django.conf import settings
from django.utils import timezone
import logging

from forex_trading.models import CurrencyPair, MarketData, TechnicalIndicator
from trading_bot.strategies import calculate_technical_indicators

logger = logging.getLogger(__name__)


class BaseDataCollector:
    """Base class for market data collectors"""
    
    def __init__(self):
        self.is_running = False
        self.callbacks = []
    
    def add_callback(self, callback: Callable):
        """Add callback function for data updates"""
        self.callbacks.append(callback)
    
    def notify_callbacks(self, data: Dict):
        """Notify all registered callbacks with new data"""
        for callback in self.callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def start(self):
        """Start data collection"""
        self.is_running = True
    
    def stop(self):
        """Stop data collection"""
        self.is_running = False


class TraderMadeCollector(BaseDataCollector):
    """Collects real-time forex data from TraderMade API"""
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://marketdata.tradermade.com"
        self.ws_url = "wss://marketdata.tradermade.com/feedadv"
        self.ws = None
        self.subscribed_pairs = []
    
    def get_latest_rates(self, symbols: List[str]) -> Dict:
        """Get latest rates via REST API"""
        try:
            symbols_str = ','.join(symbols)
            url = f"{self.base_url}/api/v1/live"
            params = {
                'currency': symbols_str,
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._process_rest_data(data)
            
        except Exception as e:
            logger.error(f"Error fetching TraderMade data: {e}")
            return {}
    
    def start_websocket(self, symbols: List[str]):
        """Start WebSocket connection for real-time data"""
        self.subscribed_pairs = symbols
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                processed_data = self._process_websocket_data(data)
                if processed_data:
                    self.notify_callbacks(processed_data)
                    self._save_to_database(processed_data)
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket connection closed")
            if self.is_running:
                # Reconnect after 5 seconds
                time.sleep(5)
                self.start_websocket(symbols)
        
        def on_open(ws):
            logger.info("WebSocket connection opened")
            # Subscribe to symbols
            subscribe_message = {
                "userKey": self.api_key,
                "symbol": ','.join(symbols)
            }
            ws.send(json.dumps(subscribe_message))
        
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Start WebSocket in a separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
    
    def _process_rest_data(self, data: Dict) -> Dict:
        """Process REST API response data"""
        processed = {}
        
        if 'quotes' in data:
            for quote in data['quotes']:
                symbol = quote.get('currency', '').replace('/', '')
                if symbol:
                    processed[symbol] = {
                        'symbol': symbol,
                        'bid': Decimal(str(quote.get('bid', 0))),
                        'ask': Decimal(str(quote.get('ask', 0))),
                        'timestamp': timezone.now()
                    }
        
        return processed
    
    def _process_websocket_data(self, data: Dict) -> Optional[Dict]:
        """Process WebSocket data"""
        if 'symbol' in data and 'bid' in data and 'ask' in data:
            return {
                'symbol': data['symbol'].replace('/', ''),
                'bid': Decimal(str(data['bid'])),
                'ask': Decimal(str(data['ask'])),
                'timestamp': timezone.now()
            }
        return None
    
    def _save_to_database(self, data: Dict):
        """Save market data to database"""
        try:
            symbol = data['symbol']
            currency_pair = CurrencyPair.objects.filter(
                symbol__iexact=symbol.replace('', '/')
            ).first()
            
            if currency_pair:
                MarketData.objects.create(
                    currency_pair=currency_pair,
                    timestamp=data['timestamp'],
                    bid=data['bid'],
                    ask=data['ask']
                )
                
                # Calculate and save technical indicators periodically
                self._update_technical_indicators(currency_pair)
                
        except Exception as e:
            logger.error(f"Error saving market data: {e}")
    
    def _update_technical_indicators(self, currency_pair: CurrencyPair):
        """Update technical indicators for currency pair"""
        try:
            # Only update indicators every 5 minutes to avoid excessive calculations
            latest_indicator = TechnicalIndicator.objects.filter(
                currency_pair=currency_pair
            ).first()
            
            if (not latest_indicator or 
                timezone.now() - latest_indicator.timestamp > timedelta(minutes=5)):
                
                indicator = calculate_technical_indicators(currency_pair)
                if indicator:
                    indicator.save()
                    
        except Exception as e:
            logger.error(f"Error updating technical indicators: {e}")


class TwelveDataCollector(BaseDataCollector):
    """Collects forex data from Twelve Data API"""
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://api.twelvedata.com"
        self.ws_url = "wss://ws.twelvedata.com/v1/quotes/price"
    
    def get_latest_rates(self, symbols: List[str]) -> Dict:
        """Get latest rates via REST API"""
        try:
            processed = {}
            
            for symbol in symbols:
                url = f"{self.base_url}/quote"
                params = {
                    'symbol': symbol,
                    'apikey': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if 'close' in data:
                    processed[symbol] = {
                        'symbol': symbol,
                        'bid': Decimal(str(data['close'])) * Decimal('0.9999'),  # Simulate bid
                        'ask': Decimal(str(data['close'])) * Decimal('1.0001'),  # Simulate ask
                        'timestamp': timezone.now()
                    }
            
            return processed
            
        except Exception as e:
            logger.error(f"Error fetching Twelve Data: {e}")
            return {}
    
    def start_websocket(self, symbols: List[str]):
        """Start WebSocket connection"""
        # Implementation similar to TraderMade but adapted for Twelve Data format
        pass


class SimulatedDataCollector(BaseDataCollector):
    """Simulates forex data for testing and development"""
    
    def __init__(self):
        super().__init__()
        self.update_interval = 1  # seconds
        self.price_data = {}
        self._initialize_prices()
    
    def _initialize_prices(self):
        """Initialize starting prices for major currency pairs"""
        self.price_data = {
            'EURUSD': {'price': Decimal('1.0850'), 'volatility': Decimal('0.0001')},
            'GBPUSD': {'price': Decimal('1.2650'), 'volatility': Decimal('0.0002')},
            'USDJPY': {'price': Decimal('149.50'), 'volatility': Decimal('0.01')},
            'AUDUSD': {'price': Decimal('0.6750'), 'volatility': Decimal('0.0001')},
            'USDCHF': {'price': Decimal('0.8950'), 'volatility': Decimal('0.0001')},
            'USDCAD': {'price': Decimal('1.3550'), 'volatility': Decimal('0.0001')},
        }
    
    def start(self):
        """Start simulated data generation"""
        super().start()
        
        def generate_data():
            while self.is_running:
                for symbol, data in self.price_data.items():
                    # Simulate price movement
                    price_change = (Decimal(str(np.random.randn())) * 
                                  data['volatility'])
                    new_price = data['price'] + price_change
                    
                    # Ensure price doesn't go negative
                    if new_price > 0:
                        data['price'] = new_price
                    
                    # Create market data
                    spread = data['volatility'] * 2
                    market_data = {
                        'symbol': symbol,
                        'bid': new_price - spread,
                        'ask': new_price + spread,
                        'timestamp': timezone.now()
                    }
                    
                    self.notify_callbacks(market_data)
                    self._save_to_database(market_data)
                
                time.sleep(self.update_interval)
        
        # Start data generation in a separate thread
        data_thread = threading.Thread(target=generate_data)
        data_thread.daemon = True
        data_thread.start()
    
    def _save_to_database(self, data: Dict):
        """Save simulated data to database"""
        try:
            symbol = data['symbol']
            # Convert symbol format (EURUSD -> EUR/USD)
            formatted_symbol = f"{symbol[:3]}/{symbol[3:]}"
            
            currency_pair = CurrencyPair.objects.filter(
                symbol=formatted_symbol
            ).first()
            
            if currency_pair:
                MarketData.objects.create(
                    currency_pair=currency_pair,
                    timestamp=data['timestamp'],
                    bid=data['bid'],
                    ask=data['ask']
                )
        except Exception as e:
            logger.error(f"Error saving simulated data: {e}")


class DataCollectorManager:
    """Manages multiple data collectors"""
    
    def __init__(self):
        self.collectors = {}
        self.active_pairs = []
    
    def add_collector(self, name: str, collector: BaseDataCollector):
        """Add a data collector"""
        self.collectors[name] = collector
    
    def start_collection(self, pairs: List[str]):
        """Start data collection for specified currency pairs"""
        self.active_pairs = pairs
        
        # Start all collectors
        for name, collector in self.collectors.items():
            try:
                if hasattr(collector, 'start_websocket'):
                    collector.start_websocket(pairs)
                else:
                    collector.start()
                logger.info(f"Started collector: {name}")
            except Exception as e:
                logger.error(f"Error starting collector {name}: {e}")
    
    def stop_collection(self):
        """Stop all data collection"""
        for name, collector in self.collectors.items():
            try:
                collector.stop()
                logger.info(f"Stopped collector: {name}")
            except Exception as e:
                logger.error(f"Error stopping collector {name}: {e}")
    
    def get_latest_data(self, symbols: List[str]) -> Dict:
        """Get latest data from all collectors"""
        all_data = {}
        
        for name, collector in self.collectors.items():
            if hasattr(collector, 'get_latest_rates'):
                try:
                    data = collector.get_latest_rates(symbols)
                    all_data[name] = data
                except Exception as e:
                    logger.error(f"Error getting data from {name}: {e}")
        
        return all_data


# Global data collector instance
data_manager = DataCollectorManager()


def initialize_data_collectors():
    """Initialize all available data collectors"""
    forex_settings = getattr(settings, 'FOREX_API_SETTINGS', {})
    
    # TraderMade collector
    tradermade_key = forex_settings.get('TRADERMADE_API_KEY')
    if tradermade_key:
        data_manager.add_collector('tradermade', TraderMadeCollector(tradermade_key))
    
    # Twelve Data collector
    twelve_data_key = forex_settings.get('TWELVE_DATA_API_KEY')
    if twelve_data_key:
        data_manager.add_collector('twelve_data', TwelveDataCollector(twelve_data_key))
    
    # Always add simulated collector for development
    data_manager.add_collector('simulated', SimulatedDataCollector())
    
    logger.info("Data collectors initialized")


def start_data_collection(currency_pairs: List[str]):
    """Start collecting data for specified currency pairs"""
    initialize_data_collectors()
    data_manager.start_collection(currency_pairs)


def stop_data_collection():
    """Stop all data collection"""
    data_manager.stop_collection()


# Import numpy for random number generation
try:
    import numpy as np
except ImportError:
    # Fallback to random module if numpy is not available
    import random
    class np:
        @staticmethod
        def random():
            return random.random()
        
        @staticmethod
        def randn():
            return random.gauss(0, 1)