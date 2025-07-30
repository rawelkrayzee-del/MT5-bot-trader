"""
Trading Serializers for MT5 Trading Bot API

This module contains DRF serializers for all trading-related models
with proper validation, custom fields, and nested serialization.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import (
    Symbol, MarketData, OHLC, Order, Position, Trade, 
    TradingSession, OrderExecution
)
from accounts.models import TradingAccount

User = get_user_model()


class SymbolSerializer(serializers.ModelSerializer):
    """Serializer for Symbol model."""
    
    # Add computed fields
    current_price = serializers.SerializerMethodField()
    price_change_percent = serializers.SerializerMethodField()
    is_market_open = serializers.SerializerMethodField()
    
    class Meta:
        model = Symbol
        fields = [
            'id', 'symbol', 'description', 'symbol_type',
            'base_currency', 'quote_currency', 'contract_size',
            'tick_size', 'tick_value', 'min_volume', 'max_volume',
            'volume_step', 'digits', 'spread', 'swap_long', 'swap_short',
            'is_active', 'is_tradeable', 'created_at', 'updated_at',
            # Computed fields
            'current_price', 'price_change_percent', 'is_market_open'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_current_price(self, obj):
        """Get current market price for the symbol."""
        latest_data = obj.market_data.first()
        if latest_data:
            return {
                'bid': latest_data.bid,
                'ask': latest_data.ask,
                'mid': latest_data.mid_price,
                'timestamp': latest_data.timestamp
            }
        return None
    
    def get_price_change_percent(self, obj):
        """Calculate 24h price change percentage."""
        # This would require historical data calculation
        # Implementation depends on your specific requirements
        return 0.0
    
    def get_is_market_open(self, obj):
        """Check if market is currently open for this symbol."""
        # Implementation depends on your trading hours logic
        return True


class MarketDataSerializer(serializers.ModelSerializer):
    """Serializer for MarketData model."""
    
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)
    mid_price = serializers.SerializerMethodField()
    spread_pips = serializers.SerializerMethodField()
    
    class Meta:
        model = MarketData
        fields = [
            'id', 'symbol', 'symbol_name', 'bid', 'ask', 'last',
            'volume', 'spread', 'is_session_open', 'timestamp',
            'mid_price', 'spread_pips'
        ]
        read_only_fields = ['id', 'timestamp', 'symbol_name', 'mid_price', 'spread_pips']
    
    def get_mid_price(self, obj):
        """Get mid price."""
        return obj.mid_price
    
    def get_spread_pips(self, obj):
        """Get spread in pips."""
        return obj.spread_pips


class OHLCSerializer(serializers.ModelSerializer):
    """Serializer for OHLC data."""
    
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)
    price_change = serializers.SerializerMethodField()
    price_change_percent = serializers.SerializerMethodField()
    
    class Meta:
        model = OHLC
        fields = [
            'id', 'symbol', 'symbol_name', 'timeframe',
            'open_price', 'high_price', 'low_price', 'close_price',
            'tick_volume', 'real_volume', 'spread', 'timestamp',
            'price_change', 'price_change_percent'
        ]
        read_only_fields = ['id', 'symbol_name', 'price_change', 'price_change_percent']
    
    def get_price_change(self, obj):
        """Calculate price change from open to close."""
        return obj.close_price - obj.open_price
    
    def get_price_change_percent(self, obj):
        """Calculate price change percentage."""
        if obj.open_price > 0:
            return ((obj.close_price - obj.open_price) / obj.open_price) * 100
        return 0.0


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders."""
    
    class Meta:
        model = Order
        fields = [
            'account', 'symbol', 'order_type', 'volume', 'price',
            'stop_price', 'stop_loss', 'take_profit', 'deviation',
            'magic_number', 'comment', 'expires_at', 'risk_amount',
            'risk_percentage'
        ]
    
    def validate_volume(self, value):
        """Validate order volume."""
        if value <= 0:
            raise serializers.ValidationError("Volume must be positive.")
        return value
    
    def validate_price(self, value):
        """Validate order price."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Price must be positive.")
        return value
    
    def validate_risk_percentage(self, value):
        """Validate risk percentage."""
        if value is not None and (value <= 0 or value > 10):
            raise serializers.ValidationError("Risk percentage must be between 0 and 10.")
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        order_type = data.get('order_type')
        price = data.get('price')
        
        # Pending orders require price
        if order_type in ['limit_buy', 'limit_sell', 'stop_buy', 'stop_sell'] and not price:
            raise serializers.ValidationError("Pending orders require a price.")
        
        # Market orders should not have price
        if order_type in ['market_buy', 'market_sell'] and price:
            raise serializers.ValidationError("Market orders should not specify a price.")
        
        return data


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""
    
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    is_buy = serializers.BooleanField(read_only=True)
    is_sell = serializers.BooleanField(read_only=True)
    remaining_volume = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    fill_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'account', 'account_name', 'symbol', 'symbol_name',
            'order_type', 'status', 'volume', 'price', 'stop_price',
            'stop_loss', 'take_profit', 'filled_volume', 'avg_fill_price',
            'slippage', 'magic_number', 'comment', 'deviation',
            'risk_amount', 'risk_percentage', 'created_at', 'updated_at',
            'filled_at', 'expires_at', 'mt5_order_id', 'mt5_position_id',
            'is_buy', 'is_sell', 'remaining_volume', 'fill_percentage'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'filled_volume', 'avg_fill_price',
            'slippage', 'created_at', 'updated_at', 'filled_at',
            'mt5_order_id', 'mt5_position_id', 'symbol_name', 'account_name',
            'is_buy', 'is_sell', 'remaining_volume', 'fill_percentage'
        ]


class PositionSerializer(serializers.ModelSerializer):
    """Serializer for Position model."""
    
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    net_pnl = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    pnl_percent = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Position
        fields = [
            'id', 'user', 'account', 'account_name', 'symbol', 'symbol_name',
            'position_type', 'volume', 'open_price', 'current_price',
            'stop_loss', 'take_profit', 'unrealized_pnl', 'commission',
            'swap', 'magic_number', 'comment', 'opened_at', 'updated_at',
            'mt5_position_id', 'mt5_order_id', 'net_pnl', 'pnl_percent',
            'duration'
        ]
        read_only_fields = [
            'id', 'user', 'opened_at', 'updated_at', 'mt5_position_id',
            'mt5_order_id', 'symbol_name', 'account_name', 'net_pnl',
            'pnl_percent', 'duration'
        ]
    
    def get_pnl_percent(self, obj):
        """Calculate P&L percentage."""
        if obj.open_price > 0:
            return (obj.net_pnl / (obj.open_price * obj.volume)) * 100
        return 0.0
    
    def get_duration(self, obj):
        """Calculate position duration."""
        if obj.opened_at:
            duration = timezone.now() - obj.opened_at
            return duration.total_seconds()
        return 0


class TradeSerializer(serializers.ModelSerializer):
    """Serializer for Trade model."""
    
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    pips_gained = serializers.DecimalField(max_digits=10, decimal_places=4, read_only=True)
    is_winning_trade = serializers.BooleanField(read_only=True)
    return_on_risk = serializers.DecimalField(max_digits=8, decimal_places=4, read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = Trade
        fields = [
            'id', 'user', 'account', 'account_name', 'symbol', 'symbol_name',
            'trade_type', 'volume', 'open_price', 'close_price',
            'gross_pnl', 'commission', 'swap', 'net_pnl', 'stop_loss',
            'take_profit', 'risk_amount', 'risk_percentage', 'slippage',
            'magic_number', 'comment', 'opened_at', 'closed_at', 'duration',
            'mt5_position_id', 'mt5_order_open_id', 'mt5_order_close_id',
            'strategy_name', 'strategy_id', 'pips_gained', 'is_winning_trade',
            'return_on_risk', 'duration_seconds'
        ]
        read_only_fields = [
            'id', 'gross_pnl', 'net_pnl', 'duration', 'symbol_name',
            'account_name', 'pips_gained', 'is_winning_trade', 'return_on_risk',
            'duration_seconds'
        ]
    
    def get_duration_seconds(self, obj):
        """Get duration in seconds."""
        if obj.duration:
            return obj.duration.total_seconds()
        return 0


class TradingSessionSerializer(serializers.ModelSerializer):
    """Serializer for TradingSession model."""
    
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    session_duration = serializers.SerializerMethodField()
    average_trade_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = TradingSession
        fields = [
            'id', 'user', 'account', 'account_name', 'session_name',
            'total_trades', 'winning_trades', 'losing_trades', 'gross_pnl',
            'net_pnl', 'commission_paid', 'win_rate', 'profit_factor',
            'largest_win', 'largest_loss', 'max_drawdown', 'total_risk',
            'started_at', 'ended_at', 'created_at', 'session_duration',
            'average_trade_duration'
        ]
        read_only_fields = [
            'id', 'total_trades', 'winning_trades', 'losing_trades',
            'gross_pnl', 'net_pnl', 'commission_paid', 'win_rate',
            'profit_factor', 'largest_win', 'largest_loss', 'max_drawdown',
            'created_at', 'account_name', 'session_duration', 'average_trade_duration'
        ]
    
    def get_session_duration(self, obj):
        """Calculate session duration."""
        if obj.ended_at and obj.started_at:
            return (obj.ended_at - obj.started_at).total_seconds()
        elif obj.started_at:
            return (timezone.now() - obj.started_at).total_seconds()
        return 0
    
    def get_average_trade_duration(self, obj):
        """Calculate average trade duration."""
        if obj.total_trades > 0:
            # This would require calculating from related trades
            return 0
        return 0


class OrderExecutionSerializer(serializers.ModelSerializer):
    """Serializer for OrderExecution model."""
    
    order_symbol = serializers.CharField(source='order.symbol.symbol', read_only=True)
    execution_quality = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderExecution
        fields = [
            'id', 'order', 'order_symbol', 'executed_volume', 'execution_price',
            'commission', 'bid_price', 'ask_price', 'spread', 'slippage',
            'latency_ms', 'executed_at', 'mt5_deal_id', 'execution_quality'
        ]
        read_only_fields = [
            'id', 'executed_at', 'order_symbol', 'execution_quality'
        ]
    
    def get_execution_quality(self, obj):
        """Calculate execution quality score."""
        score = 100
        
        # Penalize for slippage
        if obj.slippage > 0:
            score -= min(obj.slippage * 10, 30)
        
        # Penalize for latency
        if obj.latency_ms > 100:
            score -= min((obj.latency_ms - 100) / 10, 20)
        
        # Penalize for wide spread
        if obj.spread > 5:
            score -= min((obj.spread - 5) * 2, 20)
        
        return max(score, 0)


class TradingStatsSerializer(serializers.Serializer):
    """Serializer for trading statistics."""
    
    total_trades = serializers.IntegerField()
    winning_trades = serializers.IntegerField()
    losing_trades = serializers.IntegerField()
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_pnl = serializers.DecimalField(max_digits=15, decimal_places=2)
    gross_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    gross_loss = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_factor = serializers.DecimalField(max_digits=8, decimal_places=4)
    largest_win = serializers.DecimalField(max_digits=15, decimal_places=2)
    largest_loss = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_win = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_loss = serializers.DecimalField(max_digits=15, decimal_places=2)
    max_consecutive_wins = serializers.IntegerField()
    max_consecutive_losses = serializers.IntegerField()
    max_drawdown = serializers.DecimalField(max_digits=8, decimal_places=4)
    sharpe_ratio = serializers.DecimalField(max_digits=8, decimal_places=4)
    total_commission = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_swap = serializers.DecimalField(max_digits=10, decimal_places=2)


class AccountSummarySerializer(serializers.Serializer):
    """Serializer for account summary."""
    
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    equity = serializers.DecimalField(max_digits=15, decimal_places=2)
    margin = serializers.DecimalField(max_digits=15, decimal_places=2)
    free_margin = serializers.DecimalField(max_digits=15, decimal_places=2)
    margin_level = serializers.DecimalField(max_digits=8, decimal_places=2)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    open_positions = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    daily_pnl = serializers.DecimalField(max_digits=15, decimal_places=2)
    weekly_pnl = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_pnl = serializers.DecimalField(max_digits=15, decimal_places=2)