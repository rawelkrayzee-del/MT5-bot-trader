"""
Trading Models for MT5 Trading Bot

This module contains all trading-related models including orders, positions, 
trades, symbols, and trading statistics.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from accounts.models import User, TradingAccount


class Symbol(models.Model):
    """
    Model representing trading symbols/instruments.
    """
    
    SYMBOL_TYPES = [
        ('forex', 'Forex'),
        ('stocks', 'Stocks'),
        ('indices', 'Indices'),
        ('commodities', 'Commodities'),
        ('crypto', 'Cryptocurrency'),
        ('bonds', 'Bonds'),
        ('futures', 'Futures'),
        ('options', 'Options'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=200)
    symbol_type = models.CharField(max_length=20, choices=SYMBOL_TYPES)
    
    # Contract Specifications
    base_currency = models.CharField(max_length=10, blank=True)
    quote_currency = models.CharField(max_length=10, blank=True)
    contract_size = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('100000'))
    tick_size = models.DecimalField(max_digits=10, decimal_places=8, default=Decimal('0.00001'))
    tick_value = models.DecimalField(max_digits=10, decimal_places=8, default=Decimal('1.0'))
    
    # Trading Information
    min_volume = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.01'))
    max_volume = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.0'))
    volume_step = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.01'))
    
    # Market Information
    digits = models.PositiveIntegerField(default=5)
    spread = models.PositiveIntegerField(default=0)  # in points
    swap_long = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0'))
    swap_short = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0'))
    
    # Status
    is_active = models.BooleanField(default=True)
    is_tradeable = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'symbols'
        verbose_name = 'Symbol'
        verbose_name_plural = 'Symbols'
        ordering = ['symbol']
    
    def __str__(self):
        return f"{self.symbol} - {self.description}"


class MarketData(models.Model):
    """
    Model for storing real-time market data.
    """
    
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='market_data')
    
    # Price Data
    bid = models.DecimalField(max_digits=15, decimal_places=8)
    ask = models.DecimalField(max_digits=15, decimal_places=8)
    last = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    
    # Volume and Spread
    volume = models.PositiveIntegerField(default=0)
    spread = models.PositiveIntegerField(default=0)
    
    # Market Status
    is_session_open = models.BooleanField(default=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'market_data'
        verbose_name = 'Market Data'
        verbose_name_plural = 'Market Data'
        ordering = ['-timestamp']
        unique_together = ['symbol', 'timestamp']
    
    def __str__(self):
        return f"{self.symbol.symbol} - {self.bid}/{self.ask} @ {self.timestamp}"
    
    @property
    def mid_price(self):
        """Calculate mid price."""
        return (self.bid + self.ask) / 2
    
    @property
    def spread_pips(self):
        """Calculate spread in pips."""
        return (self.ask - self.bid) / self.symbol.tick_size


class OHLC(models.Model):
    """
    Model for storing OHLC (candlestick) data.
    """
    
    TIMEFRAMES = [
        ('M1', '1 Minute'),
        ('M5', '5 Minutes'),
        ('M15', '15 Minutes'),
        ('M30', '30 Minutes'),
        ('H1', '1 Hour'),
        ('H4', '4 Hours'),
        ('D1', '1 Day'),
        ('W1', '1 Week'),
        ('MN1', '1 Month'),
    ]
    
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='ohlc_data')
    timeframe = models.CharField(max_length=10, choices=TIMEFRAMES)
    
    # OHLC Data
    open_price = models.DecimalField(max_digits=15, decimal_places=8)
    high_price = models.DecimalField(max_digits=15, decimal_places=8)
    low_price = models.DecimalField(max_digits=15, decimal_places=8)
    close_price = models.DecimalField(max_digits=15, decimal_places=8)
    
    # Volume and Spread
    tick_volume = models.PositiveIntegerField(default=0)
    real_volume = models.PositiveIntegerField(default=0)
    spread = models.PositiveIntegerField(default=0)
    
    # Timestamp
    timestamp = models.DateTimeField()
    
    class Meta:
        db_table = 'ohlc_data'
        verbose_name = 'OHLC Data'
        verbose_name_plural = 'OHLC Data'
        ordering = ['-timestamp']
        unique_together = ['symbol', 'timeframe', 'timestamp']
    
    def __str__(self):
        return f"{self.symbol.symbol} {self.timeframe} - {self.timestamp}"


class Order(models.Model):
    """
    Model representing trading orders.
    """
    
    ORDER_TYPES = [
        ('market_buy', 'Market Buy'),
        ('market_sell', 'Market Sell'),
        ('limit_buy', 'Buy Limit'),
        ('limit_sell', 'Sell Limit'),
        ('stop_buy', 'Buy Stop'),
        ('stop_sell', 'Sell Stop'),
        ('stop_limit_buy', 'Buy Stop Limit'),
        ('stop_limit_sell', 'Sell Stop Limit'),
    ]
    
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('filled', 'Filled'),
        ('partial', 'Partially Filled'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='orders')
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='orders')
    
    # Order Details
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES)
    status = models.CharField(max_length=15, choices=ORDER_STATUS, default='pending')
    
    # Order Parameters
    volume = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    stop_price = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    
    # Execution Details
    filled_volume = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    avg_fill_price = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    slippage = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0'))
    
    # Trading Parameters
    magic_number = models.PositiveIntegerField(default=0)
    comment = models.CharField(max_length=100, blank=True)
    deviation = models.PositiveIntegerField(default=3)
    
    # Risk Management
    risk_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    risk_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # MT5 Integration
    mt5_order_id = models.CharField(max_length=50, blank=True)
    mt5_position_id = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order_type} {self.volume} {self.symbol.symbol} @ {self.price or 'Market'}"
    
    @property
    def is_buy(self):
        """Check if order is a buy order."""
        return self.order_type in ['market_buy', 'limit_buy', 'stop_buy', 'stop_limit_buy']
    
    @property
    def is_sell(self):
        """Check if order is a sell order."""
        return not self.is_buy
    
    @property
    def remaining_volume(self):
        """Calculate remaining volume to be filled."""
        return self.volume - self.filled_volume
    
    @property
    def fill_percentage(self):
        """Calculate fill percentage."""
        if self.volume > 0:
            return (self.filled_volume / self.volume) * 100
        return 0


class Position(models.Model):
    """
    Model representing open trading positions.
    """
    
    POSITION_TYPES = [
        ('long', 'Long'),
        ('short', 'Short'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='positions')
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='positions')
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='positions')
    
    # Position Details
    position_type = models.CharField(max_length=10, choices=POSITION_TYPES)
    volume = models.DecimalField(max_digits=10, decimal_places=2)
    open_price = models.DecimalField(max_digits=15, decimal_places=8)
    current_price = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    
    # Risk Management
    stop_loss = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    
    # P&L Calculation
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    swap = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Trading Parameters
    magic_number = models.PositiveIntegerField(default=0)
    comment = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    opened_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # MT5 Integration
    mt5_position_id = models.CharField(max_length=50, unique=True, blank=True)
    mt5_order_id = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'positions'
        verbose_name = 'Position'
        verbose_name_plural = 'Positions'
        ordering = ['-opened_at']
    
    def __str__(self):
        return f"{self.position_type} {self.volume} {self.symbol.symbol} @ {self.open_price}"
    
    def update_pnl(self, current_price=None):
        """Update unrealized P&L based on current market price."""
        if current_price:
            self.current_price = current_price
            
        if self.current_price and self.open_price:
            price_diff = self.current_price - self.open_price
            if self.position_type == 'short':
                price_diff = -price_diff
            
            # Calculate P&L in account currency
            self.unrealized_pnl = price_diff * self.volume * self.symbol.contract_size
            self.save(update_fields=['current_price', 'unrealized_pnl', 'updated_at'])
    
    @property
    def net_pnl(self):
        """Calculate net P&L including commission and swap."""
        return self.unrealized_pnl - self.commission - self.swap


class Trade(models.Model):
    """
    Model representing completed trades.
    """
    
    TRADE_TYPES = [
        ('long', 'Long'),
        ('short', 'Short'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='trades')
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='trades')
    
    # Trade Details
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES)
    volume = models.DecimalField(max_digits=10, decimal_places=2)
    open_price = models.DecimalField(max_digits=15, decimal_places=8)
    close_price = models.DecimalField(max_digits=15, decimal_places=8)
    
    # P&L and Costs
    gross_pnl = models.DecimalField(max_digits=15, decimal_places=2)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    swap = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_pnl = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Risk Management
    stop_loss = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    risk_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    risk_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Trade Execution
    slippage = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0'))
    magic_number = models.PositiveIntegerField(default=0)
    comment = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField()
    duration = models.DurationField(null=True, blank=True)
    
    # MT5 Integration
    mt5_position_id = models.CharField(max_length=50, blank=True)
    mt5_order_open_id = models.CharField(max_length=50, blank=True)
    mt5_order_close_id = models.CharField(max_length=50, blank=True)
    
    # Strategy Information
    strategy_name = models.CharField(max_length=100, blank=True)
    strategy_id = models.UUIDField(null=True, blank=True)
    
    class Meta:
        db_table = 'trades'
        verbose_name = 'Trade'
        verbose_name_plural = 'Trades'
        ordering = ['-closed_at']
    
    def __str__(self):
        return f"{self.trade_type} {self.volume} {self.symbol.symbol} - P&L: {self.net_pnl}"
    
    def save(self, *args, **kwargs):
        """Calculate duration and P&L before saving."""
        if self.opened_at and self.closed_at:
            self.duration = self.closed_at - self.opened_at
        
        # Calculate gross P&L
        price_diff = self.close_price - self.open_price
        if self.trade_type == 'short':
            price_diff = -price_diff
        
        self.gross_pnl = price_diff * self.volume * self.symbol.contract_size
        self.net_pnl = self.gross_pnl - self.commission - self.swap
        
        super().save(*args, **kwargs)
    
    @property
    def pips_gained(self):
        """Calculate pips gained/lost in the trade."""
        price_diff = self.close_price - self.open_price
        if self.trade_type == 'short':
            price_diff = -price_diff
        return price_diff / self.symbol.tick_size
    
    @property
    def is_winning_trade(self):
        """Check if trade was profitable."""
        return self.net_pnl > 0
    
    @property
    def return_on_risk(self):
        """Calculate return on risk ratio."""
        if self.risk_amount and self.risk_amount > 0:
            return self.net_pnl / self.risk_amount
        return 0


class TradingSession(models.Model):
    """
    Model for tracking trading sessions and performance.
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trading_sessions')
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='sessions')
    
    # Session Information
    session_name = models.CharField(max_length=100, blank=True)
    
    # Session Statistics
    total_trades = models.PositiveIntegerField(default=0)
    winning_trades = models.PositiveIntegerField(default=0)
    losing_trades = models.PositiveIntegerField(default=0)
    gross_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    net_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    commission_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Session Metrics
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    profit_factor = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.00'))
    largest_win = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    largest_loss = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Risk Metrics
    max_drawdown = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.00'))
    total_risk = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'trading_sessions'
        verbose_name = 'Trading Session'
        verbose_name_plural = 'Trading Sessions'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Session {self.session_name or self.id} - {self.user.email}"
    
    def calculate_statistics(self):
        """Calculate session statistics from related trades."""
        trades = Trade.objects.filter(
            user=self.user,
            account=self.account,
            closed_at__gte=self.started_at
        )
        
        if self.ended_at:
            trades = trades.filter(closed_at__lte=self.ended_at)
        
        self.total_trades = trades.count()
        self.winning_trades = trades.filter(net_pnl__gt=0).count()
        self.losing_trades = trades.filter(net_pnl__lt=0).count()
        
        if self.total_trades > 0:
            self.gross_pnl = sum(trade.gross_pnl for trade in trades)
            self.net_pnl = sum(trade.net_pnl for trade in trades)
            self.commission_paid = sum(trade.commission for trade in trades)
            self.win_rate = (self.winning_trades / self.total_trades) * 100
            
            winning_trades_pnl = sum(trade.net_pnl for trade in trades if trade.net_pnl > 0)
            losing_trades_pnl = abs(sum(trade.net_pnl for trade in trades if trade.net_pnl < 0))
            
            if losing_trades_pnl > 0:
                self.profit_factor = winning_trades_pnl / losing_trades_pnl
            
            if trades:
                self.largest_win = max(trade.net_pnl for trade in trades)
                self.largest_loss = min(trade.net_pnl for trade in trades)
        
        self.save()


class OrderExecution(models.Model):
    """
    Model for tracking order execution details and fills.
    """
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='executions')
    
    # Execution Details
    executed_volume = models.DecimalField(max_digits=10, decimal_places=2)
    execution_price = models.DecimalField(max_digits=15, decimal_places=8)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Market Conditions
    bid_price = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    ask_price = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    spread = models.PositiveIntegerField(default=0)
    
    # Execution Quality
    slippage = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0'))
    latency_ms = models.PositiveIntegerField(default=0)
    
    # Timestamp
    executed_at = models.DateTimeField(auto_now_add=True)
    
    # MT5 Integration
    mt5_deal_id = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'order_executions'
        verbose_name = 'Order Execution'
        verbose_name_plural = 'Order Executions'
        ordering = ['-executed_at']
    
    def __str__(self):
        return f"Execution {self.executed_volume} @ {self.execution_price} for Order {self.order.id}"