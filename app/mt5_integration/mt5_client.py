"""
MetaTrader 5 Client for Trading Bot Integration

This module provides a comprehensive interface for connecting to and trading
with MetaTrader 5 terminal using the official Python API.
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import threading
import time
import json


logger = logging.getLogger(__name__)


class MT5ConnectionError(Exception):
    """Custom exception for MT5 connection errors."""
    pass


class MT5TradingError(Exception):
    """Custom exception for MT5 trading errors."""
    pass


class MT5Client:
    """
    Comprehensive MetaTrader 5 client for trading operations.
    
    This class handles connection management, data retrieval, order execution,
    and position management with proper error handling and logging.
    """
    
    def __init__(self, account_config: Optional[Dict] = None):
        """
        Initialize MT5 client with account configuration.
        
        Args:
            account_config: Dict containing MT5 account credentials
        """
        self.account_config = account_config or {}
        self.is_connected = False
        self.connection_lock = threading.Lock()
        self.last_error = None
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self) -> bool:
        """
        Initialize connection to MT5 terminal.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        with self.connection_lock:
            try:
                # Get MT5 settings from Django configuration
                mt5_settings = getattr(settings, 'MT5_SETTINGS', {})
                connection_config = mt5_settings.get('CONNECTION', {})
                
                # Override with account-specific config if provided
                if self.account_config:
                    connection_config.update(self.account_config)
                
                # Initialize MT5 connection
                if not mt5.initialize(
                    path=connection_config.get('PATH', ''),
                    login=int(connection_config.get('LOGIN', 0)) if connection_config.get('LOGIN') else None,
                    password=connection_config.get('PASSWORD', ''),
                    server=connection_config.get('SERVER', ''),
                    timeout=connection_config.get('TIMEOUT', 60000),
                    portable=connection_config.get('PORTABLE', False)
                ):
                    error_code = mt5.last_error()
                    self.last_error = f"MT5 initialization failed: {error_code}"
                    logger.error(self.last_error)
                    return False
                
                # Verify connection
                terminal_info = mt5.terminal_info()
                if not terminal_info:
                    self.last_error = "Failed to get terminal info"
                    logger.error(self.last_error)
                    return False
                
                account_info = mt5.account_info()
                if not account_info:
                    self.last_error = "Failed to get account info"
                    logger.error(self.last_error)
                    return False
                
                self.is_connected = True
                self.connection_attempts = 0
                
                logger.info(f"MT5 connected successfully to account {account_info.login}")
                logger.info(f"Terminal: {terminal_info.name} {terminal_info.build}")
                logger.info(f"Account: {account_info.name} ({account_info.server})")
                
                return True
                
            except Exception as e:
                self.last_error = f"Connection error: {str(e)}"
                logger.error(self.last_error, exc_info=True)
                return False
    
    def ensure_connection(self) -> bool:
        """
        Ensure MT5 connection is active, reconnect if needed.
        
        Returns:
            bool: True if connection is active, False otherwise
        """
        if not self.is_connected:
            self.connection_attempts += 1
            if self.connection_attempts <= self.max_connection_attempts:
                logger.warning(f"Attempting to reconnect to MT5 (attempt {self.connection_attempts})")
                return self._initialize_connection()
            else:
                logger.error("Max connection attempts reached")
                return False
        
        # Test connection with a simple call
        try:
            terminal_info = mt5.terminal_info()
            if not terminal_info:
                self.is_connected = False
                return self.ensure_connection()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            self.is_connected = False
            return self.ensure_connection()
    
    def disconnect(self):
        """Disconnect from MT5 terminal."""
        with self.connection_lock:
            if self.is_connected:
                mt5.shutdown()
                self.is_connected = False
                logger.info("MT5 disconnected")
    
    def get_account_info(self) -> Optional[Dict]:
        """
        Get account information.
        
        Returns:
            Dict with account information or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            account_info = mt5.account_info()
            if not account_info:
                return None
            
            return {
                'login': account_info.login,
                'name': account_info.name,
                'server': account_info.server,
                'currency': account_info.currency,
                'balance': float(account_info.balance),
                'equity': float(account_info.equity),
                'margin': float(account_info.margin),
                'free_margin': float(account_info.margin_free),
                'margin_level': float(account_info.margin_level),
                'leverage': account_info.leverage,
                'profit': float(account_info.profit),
                'credit': float(account_info.credit),
                'trade_allowed': account_info.trade_allowed,
                'trade_expert': account_info.trade_expert,
                'margin_so_mode': account_info.margin_so_mode,
                'margin_so_call': float(account_info.margin_so_call),
                'margin_so_so': float(account_info.margin_so_so),
            }
        
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_terminal_info(self) -> Optional[Dict]:
        """
        Get terminal information.
        
        Returns:
            Dict with terminal information or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            terminal_info = mt5.terminal_info()
            if not terminal_info:
                return None
            
            return {
                'community_account': terminal_info.community_account,
                'community_connection': terminal_info.community_connection,
                'connected': terminal_info.connected,
                'dlls_allowed': terminal_info.dlls_allowed,
                'trade_allowed': terminal_info.trade_allowed,
                'tradeapi_disabled': terminal_info.tradeapi_disabled,
                'email_enabled': terminal_info.email_enabled,
                'ftp_enabled': terminal_info.ftp_enabled,
                'notifications_enabled': terminal_info.notifications_enabled,
                'mqid': terminal_info.mqid,
                'build': terminal_info.build,
                'maxbars': terminal_info.maxbars,
                'codepage': terminal_info.codepage,
                'ping_last': terminal_info.ping_last,
                'community_balance': float(terminal_info.community_balance),
                'retransmission': terminal_info.retransmission,
                'company': terminal_info.company,
                'name': terminal_info.name,
                'language': terminal_info.language,
                'path': terminal_info.path,
                'data_path': terminal_info.data_path,
                'commondata_path': terminal_info.commondata_path,
            }
        
        except Exception as e:
            logger.error(f"Error getting terminal info: {e}")
            return None
    
    def get_symbols(self, group: str = "*") -> List[Dict]:
        """
        Get available symbols.
        
        Args:
            group: Symbol group filter (default: all symbols)
            
        Returns:
            List of symbol dictionaries
        """
        if not self.ensure_connection():
            return []
        
        try:
            symbols = mt5.symbols_get(group)
            if not symbols:
                return []
            
            symbol_list = []
            for symbol in symbols:
                symbol_dict = {
                    'name': symbol.name,
                    'description': symbol.description,
                    'path': symbol.path,
                    'currency_base': symbol.currency_base,
                    'currency_profit': symbol.currency_profit,
                    'currency_margin': symbol.currency_margin,
                    'digits': symbol.digits,
                    'point': float(symbol.point),
                    'spread': symbol.spread,
                    'stops_level': symbol.stops_level,
                    'freeze_level': symbol.freeze_level,
                    'trade_mode': symbol.trade_mode,
                    'trade_execution': symbol.trade_execution,
                    'swap_mode': symbol.swap_mode,
                    'swap_rollover3days': symbol.swap_rollover3days,
                    'margin_hedged_use_leg': symbol.margin_hedged_use_leg,
                    'expiration_mode': symbol.expiration_mode,
                    'filling_mode': symbol.filling_mode,
                    'order_mode': symbol.order_mode,
                    'order_gtc_mode': symbol.order_gtc_mode,
                    'option_mode': symbol.option_mode,
                    'option_right': symbol.option_right,
                    'bid': float(symbol.bid),
                    'bidhigh': float(symbol.bidhigh),
                    'bidlow': float(symbol.bidlow),
                    'ask': float(symbol.ask),
                    'askhigh': float(symbol.askhigh),
                    'asklow': float(symbol.asklow),
                    'last': float(symbol.last),
                    'lasthigh': float(symbol.lasthigh),
                    'lastlow': float(symbol.lastlow),
                    'volume_real': float(symbol.volume_real),
                    'volumehigh_real': float(symbol.volumehigh_real),
                    'volumelow_real': float(symbol.volumelow_real),
                    'option_strike': float(symbol.option_strike),
                    'point': float(symbol.point),
                    'trade_tick_value': float(symbol.trade_tick_value),
                    'trade_tick_value_profit': float(symbol.trade_tick_value_profit),
                    'trade_tick_value_loss': float(symbol.trade_tick_value_loss),
                    'trade_tick_size': float(symbol.trade_tick_size),
                    'trade_contract_size': float(symbol.trade_contract_size),
                    'trade_accrued_interest': float(symbol.trade_accrued_interest),
                    'trade_face_value': float(symbol.trade_face_value),
                    'trade_liquidity_rate': float(symbol.trade_liquidity_rate),
                    'volume_min': float(symbol.volume_min),
                    'volume_max': float(symbol.volume_max),
                    'volume_step': float(symbol.volume_step),
                    'volume_limit': float(symbol.volume_limit),
                    'swap_long': float(symbol.swap_long),
                    'swap_short': float(symbol.swap_short),
                    'margin_initial': float(symbol.margin_initial),
                    'margin_maintenance': float(symbol.margin_maintenance),
                    'session_volume': float(symbol.session_volume),
                    'session_turnover': float(symbol.session_turnover),
                    'session_interest': float(symbol.session_interest),
                    'session_buy_orders_volume': float(symbol.session_buy_orders_volume),
                    'session_sell_orders_volume': float(symbol.session_sell_orders_volume),
                    'session_open': float(symbol.session_open),
                    'session_close': float(symbol.session_close),
                    'session_aw': float(symbol.session_aw),
                    'session_price_settlement': float(symbol.session_price_settlement),
                    'session_price_limit_min': float(symbol.session_price_limit_min),
                    'session_price_limit_max': float(symbol.session_price_limit_max),
                    'margin_hedged': float(symbol.margin_hedged),
                    'price_change': float(symbol.price_change),
                    'price_volatility': float(symbol.price_volatility),
                    'time': symbol.time,
                    'start_time': symbol.start_time,
                    'expiration_time': symbol.expiration_time,
                    'visible': symbol.visible,
                    'select': symbol.select,
                    'custom': symbol.custom,
                }
                symbol_list.append(symbol_dict)
            
            return symbol_list
        
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed information for a specific symbol.
        
        Args:
            symbol: Symbol name
            
        Returns:
            Dict with symbol info or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return None
            
            return {
                'name': symbol_info.name,
                'description': symbol_info.description,
                'currency_base': symbol_info.currency_base,
                'currency_profit': symbol_info.currency_profit,
                'currency_margin': symbol_info.currency_margin,
                'digits': symbol_info.digits,
                'point': float(symbol_info.point),
                'spread': symbol_info.spread,
                'trade_contract_size': float(symbol_info.trade_contract_size),
                'volume_min': float(symbol_info.volume_min),
                'volume_max': float(symbol_info.volume_max),
                'volume_step': float(symbol_info.volume_step),
                'bid': float(symbol_info.bid),
                'ask': float(symbol_info.ask),
                'last': float(symbol_info.last),
                'swap_long': float(symbol_info.swap_long),
                'swap_short': float(symbol_info.swap_short),
            }
        
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def get_tick_data(self, symbol: str) -> Optional[Dict]:
        """
        Get latest tick data for a symbol.
        
        Args:
            symbol: Symbol name
            
        Returns:
            Dict with tick data or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return None
            
            return {
                'time': tick.time,
                'bid': float(tick.bid),
                'ask': float(tick.ask),
                'last': float(tick.last),
                'volume': int(tick.volume),
                'time_msc': tick.time_msc,
                'flags': tick.flags,
                'volume_real': float(tick.volume_real) if hasattr(tick, 'volume_real') else 0.0,
            }
        
        except Exception as e:
            logger.error(f"Error getting tick data for {symbol}: {e}")
            return None
    
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        start_date: datetime, 
        end_date: datetime = None, 
        count: int = None
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLC data.
        
        Args:
            symbol: Symbol name
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN1)
            start_date: Start date
            end_date: End date (optional if count is provided)
            count: Number of bars to retrieve (optional if end_date is provided)
            
        Returns:
            DataFrame with OHLC data or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            # Map timeframe strings to MT5 constants
            timeframe_map = {
                'M1': mt5.TIMEFRAME_M1,
                'M5': mt5.TIMEFRAME_M5,
                'M15': mt5.TIMEFRAME_M15,
                'M30': mt5.TIMEFRAME_M30,
                'H1': mt5.TIMEFRAME_H1,
                'H4': mt5.TIMEFRAME_H4,
                'D1': mt5.TIMEFRAME_D1,
                'W1': mt5.TIMEFRAME_W1,
                'MN1': mt5.TIMEFRAME_MN1,
            }
            
            mt5_timeframe = timeframe_map.get(timeframe)
            if not mt5_timeframe:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None
            
            # Select symbol
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Failed to select symbol {symbol}")
                return None
            
            # Get data
            if count:
                rates = mt5.copy_rates_from(symbol, mt5_timeframe, start_date, count)
            else:
                end_date = end_date or datetime.now()
                rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data received for {symbol} {timeframe}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'open': 'open_price',
                'high': 'high_price',
                'low': 'low_price',
                'close': 'close_price',
                'tick_volume': 'volume',
                'real_volume': 'real_volume'
            }, inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    def place_market_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        stop_loss: float = None,
        take_profit: float = None,
        deviation: int = 20,
        magic: int = 0,
        comment: str = ""
    ) -> Optional[Dict]:
        """
        Place a market order.
        
        Args:
            symbol: Symbol name
            order_type: 'buy' or 'sell'
            volume: Order volume
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            deviation: Maximum price deviation in points
            magic: Magic number
            comment: Order comment
            
        Returns:
            Dict with order result or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Symbol {symbol} not found")
                return None
            
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"Failed to select symbol {symbol}")
                    return None
            
            # Determine order type and price
            if order_type.lower() == 'buy':
                mt5_order_type = mt5.ORDER_TYPE_BUY
                price = symbol_info.ask
            elif order_type.lower() == 'sell':
                mt5_order_type = mt5.ORDER_TYPE_SELL
                price = symbol_info.bid
            else:
                logger.error(f"Invalid order type: {order_type}")
                return None
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": price,
                "deviation": deviation,
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add stop loss and take profit if provided
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Send order
            result = mt5.order_send(request)
            if not result:
                logger.error("Order send failed")
                return None
            
            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed: {result.retcode} - {result.comment}")
                return None
            
            logger.info(f"Market {order_type} order placed: {volume} {symbol} @ {price}")
            
            return {
                'retcode': result.retcode,
                'deal': result.deal,
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'bid': result.bid,
                'ask': result.ask,
                'comment': result.comment,
                'request_id': result.request_id,
            }
        
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    def place_pending_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: float,
        stop_loss: float = None,
        take_profit: float = None,
        expiration: datetime = None,
        magic: int = 0,
        comment: str = ""
    ) -> Optional[Dict]:
        """
        Place a pending order.
        
        Args:
            symbol: Symbol name
            order_type: 'buy_limit', 'sell_limit', 'buy_stop', 'sell_stop'
            volume: Order volume
            price: Order price
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            expiration: Order expiration time (optional)
            magic: Magic number
            comment: Order comment
            
        Returns:
            Dict with order result or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Symbol {symbol} not found")
                return None
            
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"Failed to select symbol {symbol}")
                    return None
            
            # Map order types
            order_type_map = {
                'buy_limit': mt5.ORDER_TYPE_BUY_LIMIT,
                'sell_limit': mt5.ORDER_TYPE_SELL_LIMIT,
                'buy_stop': mt5.ORDER_TYPE_BUY_STOP,
                'sell_stop': mt5.ORDER_TYPE_SELL_STOP,
            }
            
            mt5_order_type = order_type_map.get(order_type.lower())
            if mt5_order_type is None:
                logger.error(f"Invalid pending order type: {order_type}")
                return None
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": price,
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
            }
            
            # Add stop loss and take profit if provided
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Add expiration if provided
            if expiration:
                request["type_time"] = mt5.ORDER_TIME_SPECIFIED
                request["expiration"] = int(expiration.timestamp())
            
            # Send order
            result = mt5.order_send(request)
            if not result:
                logger.error("Pending order send failed")
                return None
            
            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Pending order failed: {result.retcode} - {result.comment}")
                return None
            
            logger.info(f"Pending {order_type} order placed: {volume} {symbol} @ {price}")
            
            return {
                'retcode': result.retcode,
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'comment': result.comment,
                'request_id': result.request_id,
            }
        
        except Exception as e:
            logger.error(f"Error placing pending order: {e}")
            return None
    
    def modify_order(
        self,
        order_ticket: int,
        price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        expiration: datetime = None
    ) -> Optional[Dict]:
        """
        Modify an existing order.
        
        Args:
            order_ticket: Order ticket number
            price: New order price (optional)
            stop_loss: New stop loss price (optional)
            take_profit: New take profit price (optional)
            expiration: New expiration time (optional)
            
        Returns:
            Dict with modification result or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            # Get current order info
            orders = mt5.orders_get(ticket=order_ticket)
            if not orders:
                logger.error(f"Order {order_ticket} not found")
                return None
            
            order = orders[0]
            
            # Prepare modification request
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": order_ticket,
                "volume": order.volume_current,
                "price": price if price is not None else order.price_open,
                "type_time": order.type_time,
            }
            
            # Add stop loss and take profit
            if stop_loss is not None:
                request["sl"] = stop_loss
            elif hasattr(order, 'sl') and order.sl:
                request["sl"] = order.sl
                
            if take_profit is not None:
                request["tp"] = take_profit
            elif hasattr(order, 'tp') and order.tp:
                request["tp"] = order.tp
            
            # Add expiration if provided
            if expiration:
                request["type_time"] = mt5.ORDER_TIME_SPECIFIED
                request["expiration"] = int(expiration.timestamp())
            
            # Send modification
            result = mt5.order_send(request)
            if not result:
                logger.error("Order modification failed")
                return None
            
            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order modification failed: {result.retcode} - {result.comment}")
                return None
            
            logger.info(f"Order {order_ticket} modified successfully")
            
            return {
                'retcode': result.retcode,
                'order': result.order,
                'comment': result.comment,
                'request_id': result.request_id,
            }
        
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            return None
    
    def cancel_order(self, order_ticket: int) -> Optional[Dict]:
        """
        Cancel a pending order.
        
        Args:
            order_ticket: Order ticket number
            
        Returns:
            Dict with cancellation result or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            # Prepare cancellation request
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order_ticket,
            }
            
            # Send cancellation
            result = mt5.order_send(request)
            if not result:
                logger.error("Order cancellation failed")
                return None
            
            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order cancellation failed: {result.retcode} - {result.comment}")
                return None
            
            logger.info(f"Order {order_ticket} cancelled successfully")
            
            return {
                'retcode': result.retcode,
                'order': result.order,
                'comment': result.comment,
                'request_id': result.request_id,
            }
        
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return None
    
    def close_position(
        self,
        position_ticket: int,
        volume: float = None,
        deviation: int = 20,
        comment: str = ""
    ) -> Optional[Dict]:
        """
        Close a position.
        
        Args:
            position_ticket: Position ticket number
            volume: Volume to close (None for full position)
            deviation: Maximum price deviation in points
            comment: Close comment
            
        Returns:
            Dict with close result or None if error
        """
        if not self.ensure_connection():
            return None
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=position_ticket)
            if not positions:
                logger.error(f"Position {position_ticket} not found")
                return None
            
            position = positions[0]
            
            # Determine close parameters
            close_volume = volume if volume is not None else position.volume
            
            if position.type == mt5.POSITION_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
                close_price = mt5.symbol_info_tick(position.symbol).bid
            else:
                close_type = mt5.ORDER_TYPE_BUY
                close_price = mt5.symbol_info_tick(position.symbol).ask
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": close_type,
                "position": position_ticket,
                "price": close_price,
                "deviation": deviation,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close order
            result = mt5.order_send(request)
            if not result:
                logger.error("Position close failed")
                return None
            
            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Position close failed: {result.retcode} - {result.comment}")
                return None
            
            logger.info(f"Position {position_ticket} closed successfully")
            
            return {
                'retcode': result.retcode,
                'deal': result.deal,
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'comment': result.comment,
                'request_id': result.request_id,
            }
        
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None
    
    def get_positions(self, symbol: str = None) -> List[Dict]:
        """
        Get open positions.
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of position dictionaries
        """
        if not self.ensure_connection():
            return []
        
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if not positions:
                return []
            
            position_list = []
            for position in positions:
                position_dict = {
                    'ticket': position.ticket,
                    'time': position.time,
                    'time_msc': position.time_msc,
                    'time_update': position.time_update,
                    'time_update_msc': position.time_update_msc,
                    'type': position.type,
                    'magic': position.magic,
                    'identifier': position.identifier,
                    'reason': position.reason,
                    'volume': float(position.volume),
                    'price_open': float(position.price_open),
                    'sl': float(position.sl) if position.sl else None,
                    'tp': float(position.tp) if position.tp else None,
                    'price_current': float(position.price_current),
                    'swap': float(position.swap),
                    'profit': float(position.profit),
                    'symbol': position.symbol,
                    'comment': position.comment,
                    'external_id': position.external_id,
                }
                position_list.append(position_dict)
            
            return position_list
        
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_orders(self, symbol: str = None) -> List[Dict]:
        """
        Get pending orders.
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of order dictionaries
        """
        if not self.ensure_connection():
            return []
        
        try:
            if symbol:
                orders = mt5.orders_get(symbol=symbol)
            else:
                orders = mt5.orders_get()
            
            if not orders:
                return []
            
            order_list = []
            for order in orders:
                order_dict = {
                    'ticket': order.ticket,
                    'time_setup': order.time_setup,
                    'time_setup_msc': order.time_setup_msc,
                    'time_done': order.time_done,
                    'time_done_msc': order.time_done_msc,
                    'time_expiration': order.time_expiration,
                    'type': order.type,
                    'type_time': order.type_time,
                    'type_filling': order.type_filling,
                    'state': order.state,
                    'magic': order.magic,
                    'position_id': order.position_id,
                    'position_by_id': order.position_by_id,
                    'reason': order.reason,
                    'volume_initial': float(order.volume_initial),
                    'volume_current': float(order.volume_current),
                    'price_open': float(order.price_open),
                    'sl': float(order.sl) if order.sl else None,
                    'tp': float(order.tp) if order.tp else None,
                    'price_current': float(order.price_current),
                    'price_stoplimit': float(order.price_stoplimit) if hasattr(order, 'price_stoplimit') else None,
                    'symbol': order.symbol,
                    'comment': order.comment,
                    'external_id': order.external_id,
                }
                order_list.append(order_dict)
            
            return order_list
        
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def __del__(self):
        """Cleanup on object destruction."""
        self.disconnect()