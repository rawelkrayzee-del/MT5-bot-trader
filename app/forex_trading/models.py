from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class CurrencyPair(models.Model):
    """Model for forex currency pairs"""
    symbol = models.CharField(max_length=10, unique=True, help_text="e.g., EUR/USD, GBP/JPY")
    base_currency = models.CharField(max_length=3, help_text="Base currency code")
    quote_currency = models.CharField(max_length=3, help_text="Quote currency code")
    pip_size = models.DecimalField(max_digits=10, decimal_places=8, default=Decimal('0.0001'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'forex_currency_pairs'
        verbose_name = 'Currency Pair'
        verbose_name_plural = 'Currency Pairs'

    def __str__(self):
        return self.symbol


class MarketData(models.Model):
    """Model for storing real-time market data"""
    currency_pair = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name='market_data')
    timestamp = models.DateTimeField()
    bid = models.DecimalField(max_digits=12, decimal_places=6)
    ask = models.DecimalField(max_digits=12, decimal_places=6)
    high = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    low = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    volume = models.BigIntegerField(default=0)
    spread = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    
    class Meta:
        db_table = 'forex_market_data'
        unique_together = ['currency_pair', 'timestamp']
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['currency_pair', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def save(self, *args, **kwargs):
        if self.bid and self.ask:
            self.spread = self.ask - self.bid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.currency_pair.symbol} - {self.timestamp}"


class TradingStrategy(models.Model):
    """Model for trading strategies"""
    STRATEGY_TYPES = [
        ('sma_crossover', 'SMA Crossover'),
        ('rsi_oversold', 'RSI Oversold/Overbought'),
        ('bollinger_bands', 'Bollinger Bands'),
        ('macd', 'MACD'),
        ('fibonacci', 'Fibonacci Retracement'),
        ('custom', 'Custom Strategy'),
    ]
    
    name = models.CharField(max_length=100)
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_TYPES)
    description = models.TextField(blank=True)
    parameters = models.JSONField(default=dict, help_text="Strategy parameters in JSON format")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='strategies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'forex_trading_strategies'
        verbose_name = 'Trading Strategy'
        verbose_name_plural = 'Trading Strategies'

    def __str__(self):
        return f"{self.name} ({self.get_strategy_type_display()})"


class Trade(models.Model):
    """Model for individual trades"""
    TRADE_TYPES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]
    
    TRADE_STATUS = [
        ('pending', 'Pending'),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    currency_pair = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name='trades')
    strategy = models.ForeignKey(TradingStrategy, on_delete=models.SET_NULL, null=True, blank=True, related_name='trades')
    
    trade_type = models.CharField(max_length=4, choices=TRADE_TYPES)
    status = models.CharField(max_length=10, choices=TRADE_STATUS, default='pending')
    
    # Position details
    entry_price = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    exit_price = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Risk management
    stop_loss = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    
    # P&L
    profit_loss = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    swap = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # External broker trade ID
    broker_trade_id = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        db_table = 'forex_trades'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['currency_pair', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def calculate_profit_loss(self):
        """Calculate profit/loss for the trade"""
        if self.entry_price and self.exit_price:
            if self.trade_type == 'buy':
                pnl = (self.exit_price - self.entry_price) * self.quantity
            else:
                pnl = (self.entry_price - self.exit_price) * self.quantity
            
            self.profit_loss = pnl - self.commission - self.swap
            return self.profit_loss
        return Decimal('0.00')

    def __str__(self):
        return f"{self.trade_type.upper()} {self.currency_pair.symbol} - {self.status}"


class TradingAccount(models.Model):
    """Model for user trading accounts"""
    ACCOUNT_TYPES = [
        ('demo', 'Demo Account'),
        ('live', 'Live Account'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trading_accounts')
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES)
    broker = models.CharField(max_length=50, default='OANDA')
    account_id = models.CharField(max_length=100)
    
    # Account details
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('10000.00'))
    equity = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('10000.00'))
    margin_used = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    margin_available = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('10000.00'))
    
    # Trading settings
    leverage = models.IntegerField(default=100, validators=[MinValueValidator(1), MaxValueValidator(500)])
    currency = models.CharField(max_length=3, default='USD')
    
    # API credentials (encrypted)
    api_key = models.TextField(blank=True)
    api_secret = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'forex_trading_accounts'
        unique_together = ['user', 'account_id']

    def __str__(self):
        return f"{self.user.username} - {self.broker} ({self.account_type})"


class TradingBot(models.Model):
    """Model for automated trading bots"""
    BOT_STATUS = [
        ('stopped', 'Stopped'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('error', 'Error'),
    ]
    
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trading_bots')
    trading_account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='bots')
    strategy = models.ForeignKey(TradingStrategy, on_delete=models.CASCADE, related_name='bots')
    
    # Bot configuration
    currency_pairs = models.ManyToManyField(CurrencyPair, related_name='bots')
    max_concurrent_trades = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(20)])
    risk_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('2.00'))
    
    # Bot status
    status = models.CharField(max_length=10, choices=BOT_STATUS, default='stopped')
    last_signal_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Statistics
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    total_profit_loss = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'forex_trading_bots'
        ordering = ['-created_at']

    @property
    def win_rate(self):
        if self.total_trades > 0:
            return (self.winning_trades / self.total_trades) * 100
        return 0

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"


class TechnicalIndicator(models.Model):
    """Model for storing calculated technical indicators"""
    currency_pair = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name='indicators')
    timeframe = models.CharField(max_length=10, default='1H')  # 1M, 5M, 15M, 1H, 4H, 1D
    timestamp = models.DateTimeField()
    
    # Moving Averages
    sma_20 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    sma_50 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    sma_200 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    ema_20 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    
    # Oscillators
    rsi = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    macd = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    macd_signal = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    macd_histogram = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    
    # Bollinger Bands
    bb_upper = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    bb_middle = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    bb_lower = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    
    class Meta:
        db_table = 'forex_technical_indicators'
        unique_together = ['currency_pair', 'timeframe', 'timestamp']
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['currency_pair', 'timeframe', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.currency_pair.symbol} {self.timeframe} - {self.timestamp}"