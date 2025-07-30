from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    CurrencyPair, MarketData, TradingStrategy, Trade, 
    TradingAccount, TradingBot, TechnicalIndicator
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class CurrencyPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPair
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class MarketDataSerializer(serializers.ModelSerializer):
    currency_pair_symbol = serializers.CharField(source='currency_pair.symbol', read_only=True)
    
    class Meta:
        model = MarketData
        fields = [
            'id', 'currency_pair', 'currency_pair_symbol', 'timestamp', 
            'bid', 'ask', 'high', 'low', 'volume', 'spread'
        ]
        read_only_fields = ['spread']


class MarketDataCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketData
        fields = ['currency_pair', 'timestamp', 'bid', 'ask', 'high', 'low', 'volume']


class TradingStrategySerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = TradingStrategy
        fields = [
            'id', 'name', 'strategy_type', 'description', 'parameters', 
            'is_active', 'created_by', 'created_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TradeSerializer(serializers.ModelSerializer):
    currency_pair_symbol = serializers.CharField(source='currency_pair.symbol', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Trade
        fields = [
            'id', 'user', 'user_username', 'currency_pair', 'currency_pair_symbol',
            'strategy', 'strategy_name', 'trade_type', 'status', 'entry_price',
            'exit_price', 'quantity', 'stop_loss', 'take_profit', 'profit_loss',
            'commission', 'swap', 'created_at', 'opened_at', 'closed_at', 'broker_trade_id'
        ]
        read_only_fields = [
            'id', 'profit_loss', 'created_at', 'opened_at', 'closed_at'
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TradeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = [
            'currency_pair', 'strategy', 'trade_type', 'quantity', 
            'stop_loss', 'take_profit'
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TradingAccountSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = TradingAccount
        fields = [
            'id', 'user', 'user_username', 'account_type', 'broker', 'account_id',
            'balance', 'equity', 'margin_used', 'margin_available', 'leverage',
            'currency', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'api_secret': {'write_only': True},
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TradingBotSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    trading_account_broker = serializers.CharField(source='trading_account.broker', read_only=True)
    currency_pairs_symbols = serializers.StringRelatedField(source='currency_pairs', many=True, read_only=True)
    win_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = TradingBot
        fields = [
            'id', 'name', 'user', 'user_username', 'trading_account',
            'trading_account_broker', 'strategy', 'strategy_name', 'currency_pairs',
            'currency_pairs_symbols', 'max_concurrent_trades', 'risk_percentage',
            'status', 'last_signal_at', 'error_message', 'total_trades',
            'winning_trades', 'losing_trades', 'total_profit_loss', 'win_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'total_trades', 'winning_trades', 'losing_trades', 'total_profit_loss',
            'last_signal_at', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        currency_pairs = validated_data.pop('currency_pairs', [])
        validated_data['user'] = self.context['request'].user
        bot = super().create(validated_data)
        bot.currency_pairs.set(currency_pairs)
        return bot


class TradingBotStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingBot
        fields = ['status', 'error_message']


class TechnicalIndicatorSerializer(serializers.ModelSerializer):
    currency_pair_symbol = serializers.CharField(source='currency_pair.symbol', read_only=True)
    
    class Meta:
        model = TechnicalIndicator
        fields = [
            'id', 'currency_pair', 'currency_pair_symbol', 'timeframe', 'timestamp',
            'sma_20', 'sma_50', 'sma_200', 'ema_20', 'rsi', 'macd', 'macd_signal',
            'macd_histogram', 'bb_upper', 'bb_middle', 'bb_lower'
        ]


class TechnicalIndicatorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicalIndicator
        fields = [
            'currency_pair', 'timeframe', 'timestamp', 'sma_20', 'sma_50',
            'sma_200', 'ema_20', 'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower'
        ]


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_equity = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_profit_loss = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_trades = serializers.IntegerField()
    active_bots = serializers.IntegerField()
    total_trades_today = serializers.IntegerField()
    win_rate = serializers.FloatField()


class PortfolioSerializer(serializers.Serializer):
    """Serializer for portfolio overview"""
    currency_pair = serializers.CharField()
    total_quantity = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_entry_price = serializers.DecimalField(max_digits=12, decimal_places=6)
    current_price = serializers.DecimalField(max_digits=12, decimal_places=6)
    unrealized_pnl = serializers.DecimalField(max_digits=15, decimal_places=2)
    trade_count = serializers.IntegerField()