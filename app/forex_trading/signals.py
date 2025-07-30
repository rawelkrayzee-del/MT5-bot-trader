from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from django.utils import timezone

from .models import Trade, TradingBot, MarketData


@receiver(post_save, sender=Trade)
def trade_notification(sender, instance, created, **kwargs):
    """Send real-time notification when a trade is created or updated"""
    channel_layer = get_channel_layer()
    
    # Prepare notification data
    notification_data = {
        'trade_id': str(instance.id),
        'user_id': instance.user.id,
        'currency_pair': instance.currency_pair.symbol,
        'trade_type': instance.trade_type,
        'status': instance.status,
        'entry_price': str(instance.entry_price) if instance.entry_price else None,
        'exit_price': str(instance.exit_price) if instance.exit_price else None,
        'quantity': str(instance.quantity),
        'profit_loss': str(instance.profit_loss),
        'created_at': instance.created_at.isoformat(),
        'is_new': created
    }
    
    # Send to user-specific notification group
    group_name = f"notifications_{instance.user.id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'trade_notification',
            'data': notification_data
        }
    )
    
    # If trade is closed, calculate and update bot statistics
    if instance.status == 'closed' and not created:
        update_bot_statistics(instance)


@receiver(post_save, sender=TradingBot)
def bot_status_notification(sender, instance, created, **kwargs):
    """Send real-time notification when a bot status changes"""
    channel_layer = get_channel_layer()
    
    # Prepare bot status data
    bot_data = {
        'bot_id': instance.id,
        'user_id': instance.user.id,
        'name': instance.name,
        'status': instance.status,
        'total_trades': instance.total_trades,
        'winning_trades': instance.winning_trades,
        'losing_trades': instance.losing_trades,
        'total_profit_loss': str(instance.total_profit_loss),
        'win_rate': instance.win_rate,
        'error_message': instance.error_message,
        'last_signal_at': instance.last_signal_at.isoformat() if instance.last_signal_at else None,
        'is_new': created
    }
    
    # Send to user-specific notification group
    user_group = f"notifications_{instance.user.id}"
    async_to_sync(channel_layer.group_send)(
        user_group,
        {
            'type': 'bot_notification',
            'data': bot_data
        }
    )
    
    # Send to bot-specific group
    bot_group = f"bot_{instance.id}"
    async_to_sync(channel_layer.group_send)(
        bot_group,
        {
            'type': 'bot_status_update',
            'data': bot_data
        }
    )


@receiver(post_save, sender=MarketData)
def market_data_notification(sender, instance, created, **kwargs):
    """Send real-time market data updates"""
    if not created:
        return
    
    channel_layer = get_channel_layer()
    
    # Prepare market data
    market_data = {
        'symbol': instance.currency_pair.symbol,
        'bid': str(instance.bid),
        'ask': str(instance.ask),
        'high': str(instance.high) if instance.high else None,
        'low': str(instance.low) if instance.low else None,
        'volume': instance.volume,
        'spread': str(instance.spread) if instance.spread else None,
        'timestamp': instance.timestamp.isoformat()
    }
    
    # Send to general market data group
    async_to_sync(channel_layer.group_send)(
        "market_data",
        {
            'type': 'market_data_update',
            'data': market_data
        }
    )
    
    # Send to symbol-specific group
    symbol_group = f"market_data_{instance.currency_pair.symbol}"
    async_to_sync(channel_layer.group_send)(
        symbol_group,
        {
            'type': 'market_data_update',
            'data': market_data
        }
    )


def update_bot_statistics(trade):
    """Update bot statistics when a trade is closed"""
    if not trade.strategy:
        return
    
    # Find bots using this strategy
    bots = TradingBot.objects.filter(
        user=trade.user,
        strategy=trade.strategy
    )
    
    for bot in bots:
        # Recalculate statistics
        user_trades = Trade.objects.filter(
            user=trade.user,
            strategy=trade.strategy,
            status='closed'
        )
        
        total_trades = user_trades.count()
        winning_trades = user_trades.filter(profit_loss__gt=0).count()
        losing_trades = user_trades.filter(profit_loss__lt=0).count()
        total_profit_loss = sum(t.profit_loss for t in user_trades)
        
        # Update bot statistics
        bot.total_trades = total_trades
        bot.winning_trades = winning_trades
        bot.losing_trades = losing_trades
        bot.total_profit_loss = total_profit_loss
        bot.save()


@receiver(pre_save, sender=Trade)
def trade_status_change_notification(sender, instance, **kwargs):
    """Send notification when trade status changes"""
    if instance.pk:  # Only for existing trades
        try:
            old_trade = Trade.objects.get(pk=instance.pk)
            if old_trade.status != instance.status:
                # Status changed, send alert
                channel_layer = get_channel_layer()
                
                alert_data = {
                    'type': 'trade_status_change',
                    'trade_id': str(instance.id),
                    'currency_pair': instance.currency_pair.symbol,
                    'old_status': old_trade.status,
                    'new_status': instance.status,
                    'profit_loss': str(instance.profit_loss) if instance.status == 'closed' else None,
                    'timestamp': instance.updated_at.isoformat() if hasattr(instance, 'updated_at') else None
                }
                
                group_name = f"notifications_{instance.user.id}"
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'alert_notification',
                        'data': alert_data
                    }
                )
        except Trade.DoesNotExist:
            pass


def send_trading_signal(user_id, bot_id, signal_data):
    """
    Utility function to send trading signals
    This can be called from trading algorithms
    """
    channel_layer = get_channel_layer()
    
    # Send to bot-specific group
    bot_group = f"bot_{bot_id}"
    async_to_sync(channel_layer.group_send)(
        bot_group,
        {
            'type': 'bot_trade_signal',
            'data': signal_data
        }
    )
    
    # Send to user notifications
    user_group = f"notifications_{user_id}"
    async_to_sync(channel_layer.group_send)(
        user_group,
        {
            'type': 'alert_notification',
            'data': {
                'type': 'trading_signal',
                'bot_id': bot_id,
                **signal_data
            }
        }
    )


def send_price_alert(user_id, currency_pair, price, alert_type):
    """
    Utility function to send price alerts
    """
    channel_layer = get_channel_layer()
    
    alert_data = {
        'type': 'price_alert',
        'currency_pair': currency_pair,
        'price': str(price),
        'alert_type': alert_type,  # 'above', 'below', 'target_reached'
        'timestamp': timezone.now().isoformat()
    }
    
    group_name = f"notifications_{user_id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'alert_notification',
            'data': alert_data
        }
    )