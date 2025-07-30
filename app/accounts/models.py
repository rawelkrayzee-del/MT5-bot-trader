"""
User Account Models for MT5 Trading Bot

This module contains all user-related models including custom user model,
trading account configurations, user preferences, and trading profiles.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser with trading-specific fields.
    """
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Trading Profile
    is_verified_trader = models.BooleanField(default=False)
    experience_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('professional', 'Professional'),
        ],
        default='beginner'
    )
    
    # Account Status
    is_premium = models.BooleanField(default=False)
    premium_expires_at = models.DateTimeField(null=True, blank=True)
    max_strategies = models.PositiveIntegerField(default=3)
    max_accounts = models.PositiveIntegerField(default=1)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Email as username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    @property
    def is_premium_active(self):
        """Check if premium subscription is active."""
        if not self.is_premium:
            return False
        if self.premium_expires_at:
            return timezone.now() < self.premium_expires_at
        return True
    
    def get_full_name(self):
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}".strip() or self.username


class TradingAccount(models.Model):
    """
    Model representing MT5 trading account configurations.
    """
    
    ACCOUNT_TYPES = [
        ('demo', 'Demo Account'),
        ('real', 'Real Account'),
        ('contest', 'Contest Account'),
    ]
    
    ACCOUNT_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trading_accounts')
    
    # MT5 Account Details
    account_number = models.CharField(max_length=50, unique=True)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='demo')
    server = models.CharField(max_length=100)
    broker = models.CharField(max_length=100, blank=True)
    
    # Credentials (encrypted)
    password_hash = models.CharField(max_length=255, help_text="Encrypted password")
    investor_password_hash = models.CharField(max_length=255, blank=True, help_text="Encrypted investor password")
    
    # Account Configuration
    currency = models.CharField(max_length=10, default='USD')
    leverage = models.PositiveIntegerField(default=100)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    equity = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    margin = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    free_margin = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Status and Settings
    status = models.CharField(max_length=10, choices=ACCOUNT_STATUS, default='active')
    is_default = models.BooleanField(default=False)
    is_connected = models.BooleanField(default=False)
    last_connection = models.DateTimeField(null=True, blank=True)
    
    # Trading Settings
    enable_trading = models.BooleanField(default=False)
    enable_live_trading = models.BooleanField(default=False)
    max_risk_per_trade = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('1.00'),
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)]
    )
    max_daily_loss = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('5.00'),
        validators=[MinValueValidator(0.1), MaxValueValidator(20.0)]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_accounts'
        verbose_name = 'Trading Account'
        verbose_name_plural = 'Trading Accounts'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_account_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.account_name} ({self.account_number}) - {self.user.email}"
    
    def clean(self):
        """Validate the model data."""
        super().clean()
        
        # Ensure only one default account per user
        if self.is_default:
            existing_default = TradingAccount.objects.filter(
                user=self.user, 
                is_default=True
            ).exclude(id=self.id)
            if existing_default.exists():
                raise ValidationError("User can only have one default trading account.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def profit_loss(self):
        """Calculate current profit/loss."""
        return self.equity - self.balance
    
    @property
    def margin_level(self):
        """Calculate margin level percentage."""
        if self.margin > 0:
            return (self.equity / self.margin) * 100
        return 0


class UserPreferences(models.Model):
    """
    Model for storing user preferences and settings.
    """
    
    THEMES = [
        ('light', 'Light Theme'),
        ('dark', 'Dark Theme'),
        ('auto', 'Auto (System)'),
    ]
    
    LANGUAGES = [
        ('en', 'English'),
        ('id', 'Indonesian'),
        ('zh', 'Chinese'),
        ('ja', 'Japanese'),
        ('ko', 'Korean'),
    ]
    
    TIMEZONES = [
        ('UTC', 'UTC'),
        ('Asia/Jakarta', 'Asia/Jakarta'),
        ('Asia/Singapore', 'Asia/Singapore'),
        ('Asia/Tokyo', 'Asia/Tokyo'),
        ('Europe/London', 'Europe/London'),
        ('America/New_York', 'America/New_York'),
    ]
    
    # User Reference
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # UI Preferences
    theme = models.CharField(max_length=10, choices=THEMES, default='dark')
    language = models.CharField(max_length=10, choices=LANGUAGES, default='en')
    timezone = models.CharField(max_length=50, choices=TIMEZONES, default='UTC')
    
    # Dashboard Settings
    default_timeframe = models.CharField(max_length=10, default='H1')
    show_news = models.BooleanField(default=True)
    show_economic_calendar = models.BooleanField(default=True)
    auto_refresh_interval = models.PositiveIntegerField(default=5)  # seconds
    
    # Chart Preferences
    chart_type = models.CharField(
        max_length=20,
        choices=[
            ('candlestick', 'Candlestick'),
            ('line', 'Line'),
            ('bar', 'Bar'),
            ('area', 'Area'),
        ],
        default='candlestick'
    )
    show_volume = models.BooleanField(default=True)
    show_grid = models.BooleanField(default=True)
    
    # Notification Settings
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    trade_notifications = models.BooleanField(default=True)
    news_notifications = models.BooleanField(default=False)
    
    # Trading Preferences
    confirm_trades = models.BooleanField(default=True)
    show_unrealized_pnl = models.BooleanField(default=True)
    auto_close_profits = models.BooleanField(default=False)
    sound_alerts = models.BooleanField(default=True)
    
    # Risk Management Defaults
    default_risk_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('1.00'),
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)]
    )
    default_sl_pips = models.PositiveIntegerField(default=20)
    default_tp_ratio = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=Decimal('2.00'),
        validators=[MinValueValidator(0.5), MaxValueValidator(10.0)]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
        verbose_name = 'User Preferences'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.email}"


class UserSession(models.Model):
    """
    Model for tracking user sessions and activity.
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Geographic Information
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Session Data
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_sessions'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.email} - {self.ip_address} ({self.created_at})"


class APIKey(models.Model):
    """
    Model for managing user API keys for external services.
    """
    
    SERVICE_CHOICES = [
        ('alpha_vantage', 'Alpha Vantage'),
        ('financial_modeling_prep', 'Financial Modeling Prep'),
        ('twelve_data', 'Twelve Data'),
        ('tradingview', 'TradingView'),
        ('telegram', 'Telegram Bot'),
        ('discord', 'Discord Webhook'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    key_name = models.CharField(max_length=100)
    key_value = models.CharField(max_length=500)  # Encrypted
    
    # Configuration
    is_active = models.BooleanField(default=True)
    rate_limit = models.PositiveIntegerField(default=100)  # requests per hour
    
    # Usage Tracking
    requests_today = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        unique_together = ['user', 'service', 'key_name']
    
    def __str__(self):
        return f"{self.user.email} - {self.service} ({self.key_name})"


class TradingProfile(models.Model):
    """
    Model for storing detailed trading profile and statistics.
    """
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trading_profile')
    
    # Trading Statistics
    total_trades = models.PositiveIntegerField(default=0)
    winning_trades = models.PositiveIntegerField(default=0)
    losing_trades = models.PositiveIntegerField(default=0)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Performance Metrics
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    profit_factor = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.00'))
    sharpe_ratio = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.00'))
    max_drawdown = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.00'))
    
    # Risk Metrics
    average_risk_per_trade = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    largest_win = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    largest_loss = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Trading Behavior
    favorite_pairs = models.JSONField(default=list)
    trading_hours = models.JSONField(default=dict)
    avg_trade_duration = models.DurationField(null=True, blank=True)
    
    # Achievements
    achievements = models.JSONField(default=list)
    badges = models.JSONField(default=list)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_profiles'
        verbose_name = 'Trading Profile'
        verbose_name_plural = 'Trading Profiles'
    
    def __str__(self):
        return f"Trading Profile for {self.user.email}"
    
    def update_statistics(self):
        """Update trading statistics from recent trades."""
        # This method will be implemented to calculate stats from Trade model
        pass
    
    @property
    def win_rate_percentage(self):
        """Calculate win rate as percentage."""
        if self.total_trades > 0:
            return (self.winning_trades / self.total_trades) * 100
        return 0