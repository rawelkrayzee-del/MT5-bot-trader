from django.shortcuts import render
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal

from .models import (
    CurrencyPair, MarketData, TradingStrategy, Trade, 
    TradingAccount, TradingBot, TechnicalIndicator
)
from .serializers import (
    CurrencyPairSerializer, MarketDataSerializer, MarketDataCreateSerializer,
    TradingStrategySerializer, TradeSerializer, TradeCreateSerializer,
    TradingAccountSerializer, TradingBotSerializer, TradingBotStatusSerializer,
    TechnicalIndicatorSerializer, TechnicalIndicatorCreateSerializer,
    DashboardStatsSerializer, PortfolioSerializer
)


class CurrencyPairViewSet(viewsets.ModelViewSet):
    """ViewSet for currency pairs"""
    queryset = CurrencyPair.objects.filter(is_active=True)
    serializer_class = CurrencyPairSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(symbol__icontains=search) |
                Q(base_currency__icontains=search) |
                Q(quote_currency__icontains=search)
            )
        return queryset.order_by('symbol')


class MarketDataViewSet(viewsets.ModelViewSet):
    """ViewSet for market data"""
    queryset = MarketData.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MarketDataCreateSerializer
        return MarketDataSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        currency_pair = self.request.query_params.get('currency_pair', None)
        hours = self.request.query_params.get('hours', 24)
        
        if currency_pair:
            queryset = queryset.filter(currency_pair__symbol=currency_pair)
        
        # Filter by time range
        time_threshold = timezone.now() - timedelta(hours=int(hours))
        queryset = queryset.filter(timestamp__gte=time_threshold)
        
        return queryset.select_related('currency_pair').order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest market data for all currency pairs"""
        latest_data = []
        for pair in CurrencyPair.objects.filter(is_active=True):
            latest = MarketData.objects.filter(currency_pair=pair).first()
            if latest:
                latest_data.append(latest)
        
        serializer = self.get_serializer(latest_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def ohlc(self, request):
        """Get OHLC data for charting"""
        currency_pair = request.query_params.get('currency_pair')
        timeframe = request.query_params.get('timeframe', '1H')
        limit = int(request.query_params.get('limit', 100))
        
        if not currency_pair:
            return Response({'error': 'currency_pair parameter required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # This is a simplified OHLC - in production, you'd aggregate data properly
        data = MarketData.objects.filter(
            currency_pair__symbol=currency_pair
        ).order_by('-timestamp')[:limit]
        
        ohlc_data = []
        for item in reversed(data):
            mid_price = (item.bid + item.ask) / 2
            ohlc_data.append({
                'timestamp': item.timestamp,
                'open': float(mid_price),
                'high': float(item.high or mid_price),
                'low': float(item.low or mid_price),
                'close': float(mid_price),
                'volume': item.volume
            })
        
        return Response(ohlc_data)


class TradingStrategyViewSet(viewsets.ModelViewSet):
    """ViewSet for trading strategies"""
    serializer_class = TradingStrategySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TradingStrategy.objects.filter(
            Q(created_by=self.request.user) | Q(is_active=True)
        ).order_by('-created_at')


class TradeViewSet(viewsets.ModelViewSet):
    """ViewSet for trades"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TradeCreateSerializer
        return TradeSerializer
    
    def get_queryset(self):
        queryset = Trade.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get('status', None)
        currency_pair = self.request.query_params.get('currency_pair', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if currency_pair:
            queryset = queryset.filter(currency_pair__symbol=currency_pair)
            
        return queryset.select_related('currency_pair', 'strategy').order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a trade"""
        trade = self.get_object()
        exit_price = request.data.get('exit_price')
        
        if trade.status != 'open':
            return Response({'error': 'Trade is not open'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if not exit_price:
            return Response({'error': 'exit_price required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        trade.exit_price = Decimal(str(exit_price))
        trade.status = 'closed'
        trade.closed_at = timezone.now()
        trade.calculate_profit_loss()
        trade.save()
        
        serializer = self.get_serializer(trade)
        return Response(serializer.data)


class TradingAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for trading accounts"""
    serializer_class = TradingAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TradingAccount.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get account balance and equity"""
        account = self.get_object()
        return Response({
            'balance': account.balance,
            'equity': account.equity,
            'margin_used': account.margin_used,
            'margin_available': account.margin_available,
            'leverage': account.leverage
        })


class TradingBotViewSet(viewsets.ModelViewSet):
    """ViewSet for trading bots"""
    serializer_class = TradingBotSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TradingBot.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a trading bot"""
        bot = self.get_object()
        bot.status = 'running'
        bot.error_message = ''
        bot.save()
        
        # Here you would trigger the bot to start trading
        # For now, we'll just update the status
        
        serializer = TradingBotStatusSerializer(bot)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop a trading bot"""
        bot = self.get_object()
        bot.status = 'stopped'
        bot.save()
        
        serializer = TradingBotStatusSerializer(bot)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a trading bot"""
        bot = self.get_object()
        bot.status = 'paused'
        bot.save()
        
        serializer = TradingBotStatusSerializer(bot)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get bot performance statistics"""
        bot = self.get_object()
        trades = Trade.objects.filter(user=request.user, strategy=bot.strategy)
        
        total_trades = trades.count()
        winning_trades = trades.filter(profit_loss__gt=0).count()
        losing_trades = trades.filter(profit_loss__lt=0).count()
        total_profit = trades.aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
        
        return Response({
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'total_profit_loss': total_profit,
            'average_profit': trades.exclude(profit_loss=0).aggregate(avg=Avg('profit_loss'))['avg'] or Decimal('0')
        })


class TechnicalIndicatorViewSet(viewsets.ModelViewSet):
    """ViewSet for technical indicators"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TechnicalIndicatorCreateSerializer
        return TechnicalIndicatorSerializer
    
    def get_queryset(self):
        queryset = TechnicalIndicator.objects.all()
        currency_pair = self.request.query_params.get('currency_pair', None)
        timeframe = self.request.query_params.get('timeframe', None)
        hours = self.request.query_params.get('hours', 24)
        
        if currency_pair:
            queryset = queryset.filter(currency_pair__symbol=currency_pair)
        if timeframe:
            queryset = queryset.filter(timeframe=timeframe)
        
        # Filter by time range
        time_threshold = timezone.now() - timedelta(hours=int(hours))
        queryset = queryset.filter(timestamp__gte=time_threshold)
        
        return queryset.select_related('currency_pair').order_by('-timestamp')


class DashboardAPIView(APIView):
    """API view for dashboard statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get all trading accounts for the user
        accounts = TradingAccount.objects.filter(user=user, is_active=True)
        
        # Calculate totals
        total_balance = accounts.aggregate(total=Sum('balance'))['total'] or Decimal('0')
        total_equity = accounts.aggregate(total=Sum('equity'))['total'] or Decimal('0')
        
        # Get trades statistics
        today = timezone.now().date()
        user_trades = Trade.objects.filter(user=user)
        
        total_profit_loss = user_trades.filter(status='closed').aggregate(
            total=Sum('profit_loss'))['total'] or Decimal('0')
        
        active_trades = user_trades.filter(status='open').count()
        active_bots = TradingBot.objects.filter(user=user, status='running').count()
        
        trades_today = user_trades.filter(created_at__date=today).count()
        
        # Calculate win rate
        closed_trades = user_trades.filter(status='closed')
        winning_trades = closed_trades.filter(profit_loss__gt=0).count()
        total_closed = closed_trades.count()
        win_rate = (winning_trades / total_closed * 100) if total_closed > 0 else 0
        
        stats = {
            'total_balance': total_balance,
            'total_equity': total_equity,
            'total_profit_loss': total_profit_loss,
            'active_trades': active_trades,
            'active_bots': active_bots,
            'total_trades_today': trades_today,
            'win_rate': win_rate
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)


class PortfolioAPIView(APIView):
    """API view for portfolio overview"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get open trades grouped by currency pair
        open_trades = Trade.objects.filter(user=user, status='open').values(
            'currency_pair__symbol'
        ).annotate(
            total_quantity=Sum('quantity'),
            average_entry_price=Avg('entry_price'),
            trade_count=Count('id')
        )
        
        portfolio_data = []
        for trade_group in open_trades:
            symbol = trade_group['currency_pair__symbol']
            
            # Get current market price (latest market data)
            latest_data = MarketData.objects.filter(
                currency_pair__symbol=symbol
            ).first()
            
            current_price = Decimal('0')
            if latest_data:
                current_price = (latest_data.bid + latest_data.ask) / 2
            
            # Calculate unrealized P&L (simplified)
            avg_entry = trade_group['average_entry_price'] or Decimal('0')
            quantity = trade_group['total_quantity'] or Decimal('0')
            unrealized_pnl = (current_price - avg_entry) * quantity
            
            portfolio_data.append({
                'currency_pair': symbol,
                'total_quantity': trade_group['total_quantity'],
                'average_entry_price': trade_group['average_entry_price'],
                'current_price': current_price,
                'unrealized_pnl': unrealized_pnl,
                'trade_count': trade_group['trade_count']
            })
        
        serializer = PortfolioSerializer(portfolio_data, many=True)
        return Response(serializer.data)


class MarketAnalysisAPIView(APIView):
    """API view for market analysis and signals"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        currency_pair = request.query_params.get('currency_pair', 'EUR/USD')
        
        # Get latest technical indicators
        latest_indicators = TechnicalIndicator.objects.filter(
            currency_pair__symbol=currency_pair
        ).order_by('-timestamp').first()
        
        if not latest_indicators:
            return Response({'error': 'No indicators available'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Simple signal generation based on indicators
        signals = []
        
        # RSI signals
        if latest_indicators.rsi:
            if latest_indicators.rsi > 70:
                signals.append({'type': 'sell', 'indicator': 'RSI', 'strength': 'strong', 'value': latest_indicators.rsi})
            elif latest_indicators.rsi < 30:
                signals.append({'type': 'buy', 'indicator': 'RSI', 'strength': 'strong', 'value': latest_indicators.rsi})
        
        # SMA crossover signals
        if latest_indicators.sma_20 and latest_indicators.sma_50:
            if latest_indicators.sma_20 > latest_indicators.sma_50:
                signals.append({'type': 'buy', 'indicator': 'SMA Crossover', 'strength': 'medium'})
            else:
                signals.append({'type': 'sell', 'indicator': 'SMA Crossover', 'strength': 'medium'})
        
        # MACD signals
        if latest_indicators.macd and latest_indicators.macd_signal:
            if latest_indicators.macd > latest_indicators.macd_signal:
                signals.append({'type': 'buy', 'indicator': 'MACD', 'strength': 'medium'})
            else:
                signals.append({'type': 'sell', 'indicator': 'MACD', 'strength': 'medium'})
        
        return Response({
            'currency_pair': currency_pair,
            'timestamp': latest_indicators.timestamp,
            'indicators': TechnicalIndicatorSerializer(latest_indicators).data,
            'signals': signals,
            'overall_sentiment': self._calculate_overall_sentiment(signals)
        })
    
    def _calculate_overall_sentiment(self, signals):
        """Calculate overall market sentiment from signals"""
        if not signals:
            return 'neutral'
        
        buy_signals = len([s for s in signals if s['type'] == 'buy'])
        sell_signals = len([s for s in signals if s['type'] == 'sell'])
        
        if buy_signals > sell_signals:
            return 'bullish'
        elif sell_signals > buy_signals:
            return 'bearish'
        else:
            return 'neutral'