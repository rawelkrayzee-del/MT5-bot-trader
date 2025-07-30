from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    CurrencyPair, MarketData, TradingStrategy, Trade, 
    TradingAccount, TradingBot, TechnicalIndicator
)


@admin.register(CurrencyPair)
class CurrencyPairAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'base_currency', 'quote_currency', 'pip_size', 'is_active', 'created_at']
    list_filter = ['is_active', 'base_currency', 'quote_currency']
    search_fields = ['symbol', 'base_currency', 'quote_currency']
    ordering = ['symbol']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MarketData)
class MarketDataAdmin(admin.ModelAdmin):
    list_display = ['currency_pair', 'timestamp', 'bid', 'ask', 'spread', 'volume']
    list_filter = ['currency_pair', 'timestamp']
    search_fields = ['currency_pair__symbol']
    ordering = ['-timestamp']
    readonly_fields = ['spread']
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('currency_pair')


@admin.register(TradingStrategy)
class TradingStrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy_type', 'created_by', 'is_active', 'created_at']
    list_filter = ['strategy_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = []
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = [
        'trade_id_short', 'user', 'currency_pair', 'trade_type', 'status', 
        'entry_price', 'exit_price', 'profit_loss_colored', 'created_at'
    ]
    list_filter = ['trade_type', 'status', 'currency_pair', 'created_at']
    search_fields = ['user__username', 'currency_pair__symbol', 'broker_trade_id']
    readonly_fields = ['id', 'profit_loss', 'created_at', 'opened_at', 'closed_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'currency_pair', 'strategy', 'trade_type', 'status')
        }),
        ('Position Details', {
            'fields': ('entry_price', 'exit_price', 'quantity')
        }),
        ('Risk Management', {
            'fields': ('stop_loss', 'take_profit')
        }),
        ('Financial', {
            'fields': ('profit_loss', 'commission', 'swap')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'opened_at', 'closed_at')
        }),
        ('External', {
            'fields': ('broker_trade_id',)
        }),
    )
    
    def trade_id_short(self, obj):
        return str(obj.id)[:8]
    trade_id_short.short_description = 'Trade ID'
    
    def profit_loss_colored(self, obj):
        color = 'green' if obj.profit_loss > 0 else 'red' if obj.profit_loss < 0 else 'gray'
        return format_html(
            '<span style="color: {};">${:.2f}</span>',
            color,
            obj.profit_loss
        )
    profit_loss_colored.short_description = 'P&L'
    profit_loss_colored.admin_order_field = 'profit_loss'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'currency_pair', 'strategy')


@admin.register(TradingAccount)
class TradingAccountAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'broker', 'account_type', 'balance', 'equity', 
        'margin_used', 'leverage', 'is_active', 'created_at'
    ]
    list_filter = ['account_type', 'broker', 'is_active', 'leverage']
    search_fields = ['user__username', 'account_id', 'broker']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'account_type', 'broker', 'account_id')
        }),
        ('Financial Details', {
            'fields': ('balance', 'equity', 'margin_used', 'margin_available', 'leverage', 'currency')
        }),
        ('API Configuration', {
            'fields': ('api_key', 'api_secret'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(TradingBot)
class TradingBotAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'status', 'strategy', 'total_trades', 
        'win_rate_display', 'total_profit_loss_colored', 'last_signal_at'
    ]
    list_filter = ['status', 'strategy__strategy_type', 'created_at']
    search_fields = ['name', 'user__username', 'strategy__name']
    readonly_fields = ['total_trades', 'winning_trades', 'losing_trades', 'total_profit_loss', 'created_at', 'updated_at']
    filter_horizontal = ['currency_pairs']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Bot Information', {
            'fields': ('name', 'user', 'trading_account', 'strategy')
        }),
        ('Configuration', {
            'fields': ('currency_pairs', 'max_concurrent_trades', 'risk_percentage')
        }),
        ('Status', {
            'fields': ('status', 'last_signal_at', 'error_message')
        }),
        ('Statistics', {
            'fields': ('total_trades', 'winning_trades', 'losing_trades', 'total_profit_loss'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def win_rate_display(self, obj):
        rate = obj.win_rate
        color = 'green' if rate >= 60 else 'orange' if rate >= 40 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            rate
        )
    win_rate_display.short_description = 'Win Rate'
    
    def total_profit_loss_colored(self, obj):
        color = 'green' if obj.total_profit_loss > 0 else 'red' if obj.total_profit_loss < 0 else 'gray'
        return format_html(
            '<span style="color: {};">${:.2f}</span>',
            color,
            obj.total_profit_loss
        )
    total_profit_loss_colored.short_description = 'Total P&L'
    total_profit_loss_colored.admin_order_field = 'total_profit_loss'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'trading_account', 'strategy')


@admin.register(TechnicalIndicator)
class TechnicalIndicatorAdmin(admin.ModelAdmin):
    list_display = [
        'currency_pair', 'timeframe', 'timestamp', 'rsi', 
        'sma_20', 'sma_50', 'macd'
    ]
    list_filter = ['currency_pair', 'timeframe', 'timestamp']
    search_fields = ['currency_pair__symbol']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('currency_pair', 'timeframe', 'timestamp')
        }),
        ('Moving Averages', {
            'fields': ('sma_20', 'sma_50', 'sma_200', 'ema_20')
        }),
        ('Oscillators', {
            'fields': ('rsi', 'macd', 'macd_signal', 'macd_histogram')
        }),
        ('Bollinger Bands', {
            'fields': ('bb_upper', 'bb_middle', 'bb_lower')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('currency_pair')


# Customize the admin site header and title
admin.site.site_header = "Forex Trading Bot Administration"
admin.site.site_title = "Forex Trading Bot Admin"
admin.site.index_title = "Welcome to Forex Trading Bot Administration"