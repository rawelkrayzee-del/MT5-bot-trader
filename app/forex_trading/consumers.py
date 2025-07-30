import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import MarketData, CurrencyPair, Trade, TradingBot


class MarketDataConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time market data"""
    
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Join market data group
        self.group_name = "market_data"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial market data
        await self.send_latest_market_data()
    
    async def disconnect(self, close_code):
        # Leave market data group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'subscribe':
                currency_pairs = data.get('currency_pairs', [])
                await self.subscribe_to_pairs(currency_pairs)
            elif action == 'unsubscribe':
                currency_pairs = data.get('currency_pairs', [])
                await self.unsubscribe_from_pairs(currency_pairs)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
    
    async def subscribe_to_pairs(self, currency_pairs):
        """Subscribe to specific currency pairs"""
        for pair in currency_pairs:
            group_name = f"market_data_{pair}"
            await self.channel_layer.group_add(
                group_name,
                self.channel_name
            )
        
        await self.send(text_data=json.dumps({
            'type': 'subscription_confirmed',
            'currency_pairs': currency_pairs
        }))
    
    async def unsubscribe_from_pairs(self, currency_pairs):
        """Unsubscribe from specific currency pairs"""
        for pair in currency_pairs:
            group_name = f"market_data_{pair}"
            await self.channel_layer.group_discard(
                group_name,
                self.channel_name
            )
    
    async def send_latest_market_data(self):
        """Send latest market data for all active currency pairs"""
        market_data = await self.get_latest_market_data()
        
        await self.send(text_data=json.dumps({
            'type': 'market_data',
            'data': market_data
        }))
    
    @database_sync_to_async
    def get_latest_market_data(self):
        """Get latest market data from database"""
        data = []
        for pair in CurrencyPair.objects.filter(is_active=True):
            latest = MarketData.objects.filter(currency_pair=pair).first()
            if latest:
                data.append({
                    'symbol': pair.symbol,
                    'bid': str(latest.bid),
                    'ask': str(latest.ask),
                    'spread': str(latest.spread) if latest.spread else None,
                    'timestamp': latest.timestamp.isoformat()
                })
        return data
    
    # Message handlers
    async def market_data_update(self, event):
        """Send market data update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'market_data_update',
            'data': event['data']
        }))


class TradingNotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for trading notifications and alerts"""
    
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Join user-specific notification group
        self.group_name = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to trading notifications'
        }))
    
    async def disconnect(self, close_code):
        # Leave notification group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'get_recent_trades':
                await self.send_recent_trades()
            elif action == 'get_bot_status':
                await self.send_bot_status()
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
    
    async def send_recent_trades(self):
        """Send recent trades for the user"""
        trades = await self.get_recent_trades()
        
        await self.send(text_data=json.dumps({
            'type': 'recent_trades',
            'data': trades
        }))
    
    async def send_bot_status(self):
        """Send current bot status"""
        bots = await self.get_user_bots()
        
        await self.send(text_data=json.dumps({
            'type': 'bot_status',
            'data': bots
        }))
    
    @database_sync_to_async
    def get_recent_trades(self):
        """Get recent trades for the user"""
        trades = Trade.objects.filter(user=self.user).order_by('-created_at')[:10]
        return [
            {
                'id': str(trade.id),
                'currency_pair': trade.currency_pair.symbol,
                'trade_type': trade.trade_type,
                'status': trade.status,
                'entry_price': str(trade.entry_price) if trade.entry_price else None,
                'quantity': str(trade.quantity),
                'profit_loss': str(trade.profit_loss),
                'created_at': trade.created_at.isoformat()
            }
            for trade in trades
        ]
    
    @database_sync_to_async
    def get_user_bots(self):
        """Get user's trading bots status"""
        bots = TradingBot.objects.filter(user=self.user)
        return [
            {
                'id': bot.id,
                'name': bot.name,
                'status': bot.status,
                'total_trades': bot.total_trades,
                'total_profit_loss': str(bot.total_profit_loss)
            }
            for bot in bots
        ]
    
    # Message handlers
    async def trade_notification(self, event):
        """Send trade notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'trade_notification',
            'data': event['data']
        }))
    
    async def bot_notification(self, event):
        """Send bot notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'bot_notification',
            'data': event['data']
        }))
    
    async def alert_notification(self, event):
        """Send alert notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'data': event['data']
        }))


class TradingBotConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time trading bot monitoring"""
    
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.bot_id = self.scope['url_route']['kwargs']['bot_id']
        
        # Verify bot ownership
        bot_exists = await self.verify_bot_ownership()
        if not bot_exists:
            await self.close()
            return
        
        # Join bot-specific group
        self.group_name = f"bot_{self.bot_id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial bot status
        await self.send_bot_status()
    
    async def disconnect(self, close_code):
        # Leave bot group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'get_status':
                await self.send_bot_status()
            elif action == 'get_performance':
                await self.send_bot_performance()
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
    
    @database_sync_to_async
    def verify_bot_ownership(self):
        """Verify that the user owns the bot"""
        try:
            bot = TradingBot.objects.get(id=self.bot_id, user=self.user)
            return True
        except TradingBot.DoesNotExist:
            return False
    
    async def send_bot_status(self):
        """Send current bot status"""
        bot_data = await self.get_bot_data()
        
        await self.send(text_data=json.dumps({
            'type': 'bot_status',
            'data': bot_data
        }))
    
    async def send_bot_performance(self):
        """Send bot performance metrics"""
        performance = await self.get_bot_performance()
        
        await self.send(text_data=json.dumps({
            'type': 'bot_performance',
            'data': performance
        }))
    
    @database_sync_to_async
    def get_bot_data(self):
        """Get bot data from database"""
        try:
            bot = TradingBot.objects.get(id=self.bot_id)
            return {
                'id': bot.id,
                'name': bot.name,
                'status': bot.status,
                'total_trades': bot.total_trades,
                'winning_trades': bot.winning_trades,
                'losing_trades': bot.losing_trades,
                'total_profit_loss': str(bot.total_profit_loss),
                'win_rate': bot.win_rate,
                'last_signal_at': bot.last_signal_at.isoformat() if bot.last_signal_at else None,
                'error_message': bot.error_message
            }
        except TradingBot.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_bot_performance(self):
        """Get detailed bot performance metrics"""
        try:
            bot = TradingBot.objects.get(id=self.bot_id)
            trades = Trade.objects.filter(user=self.user, strategy=bot.strategy)
            
            recent_trades = trades.order_by('-created_at')[:20]
            
            return {
                'recent_trades': [
                    {
                        'id': str(trade.id),
                        'currency_pair': trade.currency_pair.symbol,
                        'trade_type': trade.trade_type,
                        'status': trade.status,
                        'profit_loss': str(trade.profit_loss),
                        'created_at': trade.created_at.isoformat()
                    }
                    for trade in recent_trades
                ],
                'total_profit_loss': str(bot.total_profit_loss),
                'win_rate': bot.win_rate
            }
        except TradingBot.DoesNotExist:
            return None
    
    # Message handlers
    async def bot_status_update(self, event):
        """Send bot status update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'bot_status_update',
            'data': event['data']
        }))
    
    async def bot_trade_signal(self, event):
        """Send bot trade signal to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'trade_signal',
            'data': event['data']
        }))