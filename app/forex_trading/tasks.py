"""
Celery tasks for forex trading bot operations.
Handles background processing for trading, data collection, and monitoring.
"""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import List, Dict

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Avg
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    CurrencyPair, MarketData, TradingBot, Trade, 
    TradingAccount, TechnicalIndicator
)
from market_data.collectors import data_manager, initialize_data_collectors
from trading_bot.strategies import StrategyManager
from trading_bot.execution import create_trading_executor

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


@shared_task(bind=True, max_retries=3)
def collect_market_data(self):
    """Collect real-time market data from various providers"""
    try:
        # Get active currency pairs
        active_pairs = list(CurrencyPair.objects.filter(
            is_active=True
        ).values_list('symbol', flat=True))
        
        if not active_pairs:
            logger.warning("No active currency pairs found")
            return
        
        # Initialize data collectors if not already done
        initialize_data_collectors()
        
        # Start data collection for active pairs
        data_manager.start_collection(active_pairs)
        
        logger.info(f"Market data collection started for {len(active_pairs)} pairs")
        
    except Exception as exc:
        logger.error(f"Error collecting market data: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def update_technical_indicators(self):
    """Update technical indicators for all active currency pairs"""
    try:
        from trading_bot.strategies import calculate_technical_indicators
        
        active_pairs = CurrencyPair.objects.filter(is_active=True)
        
        for pair in active_pairs:
            try:
                indicator = calculate_technical_indicators(pair)
                if indicator:
                    indicator.save()
                    logger.debug(f"Updated indicators for {pair.symbol}")
            except Exception as e:
                logger.error(f"Error updating indicators for {pair.symbol}: {e}")
        
        logger.info(f"Technical indicators updated for {active_pairs.count()} pairs")
        
    except Exception as exc:
        logger.error(f"Error updating technical indicators: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def check_trading_signals(self):
    """Check for trading signals from active bots"""
    try:
        active_bots = TradingBot.objects.filter(is_active=True)
        
        for bot in active_bots:
            try:
                check_bot_signals.delay(bot.id)
            except Exception as e:
                logger.error(f"Error scheduling signal check for bot {bot.name}: {e}")
        
        logger.debug(f"Scheduled signal checks for {active_bots.count()} bots")
        
    except Exception as exc:
        logger.error(f"Error checking trading signals: {exc}")
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3)
def check_bot_signals(self, bot_id: int):
    """Check trading signals for a specific bot"""
    try:
        bot = TradingBot.objects.get(id=bot_id, is_active=True)
        strategy_manager = StrategyManager()
        
        # Get strategy instance
        strategy = strategy_manager.get_strategy(bot.strategy_name)
        if not strategy:
            logger.warning(f"Strategy {bot.strategy_name} not found for bot {bot.name}")
            return
        
        # Check signals for each currency pair
        for pair_symbol in bot.currency_pairs:
            try:
                pair = CurrencyPair.objects.get(symbol=pair_symbol)
                
                # Get recent market data
                market_data = MarketData.objects.filter(
                    currency_pair=pair
                ).order_by('-timestamp')[:100]
                
                if len(market_data) < 20:  # Need enough data for analysis
                    continue
                
                # Get technical indicators
                indicators = TechnicalIndicator.objects.filter(
                    currency_pair=pair
                ).order_by('-timestamp')[:10]
                
                # Generate signal
                signal = strategy.generate_signal(
                    list(market_data), 
                    list(indicators)
                )
                
                if signal and signal['action'] in ['buy', 'sell']:
                    # Execute trade signal
                    execute_trade_signal.delay(bot.id, signal)
                    
            except CurrencyPair.DoesNotExist:
                logger.warning(f"Currency pair {pair_symbol} not found")
            except Exception as e:
                logger.error(f"Error checking signals for {pair_symbol}: {e}")
        
    except TradingBot.DoesNotExist:
        logger.warning(f"Trading bot {bot_id} not found")
    except Exception as exc:
        logger.error(f"Error checking bot signals: {exc}")
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3)
def execute_trade_signal(self, bot_id: int, signal: Dict):
    """Execute a trading signal"""
    try:
        bot = TradingBot.objects.get(id=bot_id, is_active=True)
        
        # Check if bot can execute more trades
        open_trades = Trade.objects.filter(
            trading_bot=bot,
            status='open'
        ).count()
        
        if open_trades >= bot.max_trades:
            logger.info(f"Bot {bot.name} has reached maximum trades limit")
            return
        
        # Get trading executor
        executor = create_trading_executor(bot.user)
        if not executor:
            logger.error(f"Could not create trading executor for bot {bot.name}")
            return
        
        # Prepare trade signal data
        trade_signal = {
            'currency_pair': signal['currency_pair'],
            'trade_type': signal['action'],
            'entry_price': signal['price'],
            'stop_loss': signal.get('stop_loss'),
            'take_profit': signal.get('take_profit'),
            'strategy_name': bot.strategy_name,
            'order_type': 'market'
        }
        
        # Execute trade
        result = executor.execute_trade_signal(trade_signal)
        
        if result['success']:
            # Update trade with bot reference
            trade = Trade.objects.get(id=result['trade_id'])
            trade.trading_bot = bot
            trade.save()
            
            # Send real-time notification
            send_trade_notification.delay(trade.id, 'opened')
            
            logger.info(f"Trade executed successfully for bot {bot.name}: {result['trade_id']}")
        else:
            logger.warning(f"Trade execution failed for bot {bot.name}: {result['error']}")
        
    except TradingBot.DoesNotExist:
        logger.warning(f"Trading bot {bot_id} not found")
    except Exception as exc:
        logger.error(f"Error executing trade signal: {exc}")
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3)
def execute_stop_loss_take_profit(self):
    """Check and execute stop loss and take profit orders"""
    try:
        open_trades = Trade.objects.filter(status='open')
        
        for trade in open_trades:
            try:
                executor = create_trading_executor(trade.user)
                if executor:
                    executor.check_stop_loss_take_profit()
            except Exception as e:
                logger.error(f"Error checking SL/TP for trade {trade.id}: {e}")
        
        logger.debug(f"Checked SL/TP for {open_trades.count()} open trades")
        
    except Exception as exc:
        logger.error(f"Error executing stop loss/take profit: {exc}")
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3)
def update_bot_performance(self):
    """Update performance metrics for all trading bots"""
    try:
        bots = TradingBot.objects.all()
        
        for bot in bots:
            try:
                # Calculate performance metrics
                trades = Trade.objects.filter(trading_bot=bot, status='closed')
                
                if trades.exists():
                    total_trades = trades.count()
                    profitable_trades = trades.filter(pnl__gt=0).count()
                    total_pnl = trades.aggregate(Sum('pnl'))['pnl__sum'] or Decimal('0')
                    win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
                    
                    # Calculate average trade duration
                    completed_trades = trades.exclude(exit_timestamp__isnull=True)
                    if completed_trades.exists():
                        durations = []
                        for trade in completed_trades:
                            duration = trade.exit_timestamp - trade.entry_timestamp
                            durations.append(duration.total_seconds() / 3600)  # hours
                        avg_duration = sum(durations) / len(durations)
                    else:
                        avg_duration = 0
                    
                    # Update bot performance
                    bot.performance = {
                        'total_trades': total_trades,
                        'profitable_trades': profitable_trades,
                        'total_pnl': float(total_pnl),
                        'win_rate': win_rate,
                        'avg_trade_duration': avg_duration
                    }
                    bot.save()
                    
            except Exception as e:
                logger.error(f"Error updating performance for bot {bot.name}: {e}")
        
        logger.info(f"Updated performance for {bots.count()} bots")
        
    except Exception as exc:
        logger.error(f"Error updating bot performance: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_trade_notification(self, trade_id: int, action: str):
    """Send real-time trade notification"""
    try:
        trade = Trade.objects.get(id=trade_id)
        
        # Prepare notification data
        notification_data = {
            'type': 'trade_notification',
            'action': action,
            'trade': {
                'id': str(trade.id),
                'currency_pair': trade.currency_pair.symbol,
                'trade_type': trade.trade_type,
                'volume': float(trade.volume),
                'entry_price': float(trade.entry_price) if trade.entry_price else None,
                'exit_price': float(trade.exit_price) if trade.exit_price else None,
                'pnl': float(trade.pnl) if trade.pnl else None,
                'status': trade.status,
                'timestamp': trade.entry_timestamp.isoformat()
            }
        }
        
        # Send to user's notification channel
        user_group = f"user_{trade.user.id}_notifications"
        async_to_sync(channel_layer.group_send)(
            user_group,
            {
                'type': 'trade_notification',
                'message': notification_data
            }
        )
        
        logger.debug(f"Sent trade notification for trade {trade_id}")
        
    except Trade.DoesNotExist:
        logger.warning(f"Trade {trade_id} not found for notification")
    except Exception as exc:
        logger.error(f"Error sending trade notification: {exc}")


@shared_task(bind=True, max_retries=3)
def cleanup_old_market_data(self):
    """Clean up old market data to save storage space"""
    try:
        # Keep only last 30 days of market data
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_count = MarketData.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old market data records")
        
        # Keep only last 7 days of technical indicators
        cutoff_date = timezone.now() - timedelta(days=7)
        
        deleted_indicators = TechnicalIndicator.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_indicators} old technical indicator records")
        
    except Exception as exc:
        logger.error(f"Error cleaning up old data: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def send_daily_reports(self):
    """Send daily trading reports to users"""
    try:
        users = User.objects.filter(is_active=True)
        
        for user in users:
            try:
                # Get user's trading activity for today
                today = timezone.now().date()
                
                trades_today = Trade.objects.filter(
                    user=user,
                    entry_timestamp__date=today
                )
                
                if trades_today.exists():
                    send_user_daily_report.delay(user.id)
                    
            except Exception as e:
                logger.error(f"Error preparing daily report for user {user.id}: {e}")
        
        logger.info(f"Scheduled daily reports for {users.count()} users")
        
    except Exception as exc:
        logger.error(f"Error sending daily reports: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def send_user_daily_report(self, user_id: int):
    """Send daily report to a specific user"""
    try:
        user = User.objects.get(id=user_id)
        today = timezone.now().date()
        
        # Get today's trading statistics
        trades_today = Trade.objects.filter(
            user=user,
            entry_timestamp__date=today
        )
        
        closed_trades = trades_today.filter(status='closed')
        total_pnl = closed_trades.aggregate(Sum('pnl'))['pnl__sum'] or Decimal('0')
        profitable_trades = closed_trades.filter(pnl__gt=0).count()
        total_trades = closed_trades.count()
        
        # Get account balance
        account = TradingAccount.objects.filter(user=user, is_active=True).first()
        current_balance = account.balance if account else Decimal('0')
        
        # Prepare email content
        subject = f"Daily Trading Report - {today}"
        message = f"""
        Dear {user.first_name or user.username},
        
        Here's your trading summary for {today}:
        
        • Total Trades: {total_trades}
        • Profitable Trades: {profitable_trades}
        • Total P&L: ${total_pnl:.2f}
        • Win Rate: {(profitable_trades/total_trades*100):.1f}% if total_trades > 0 else 0%
        • Current Balance: ${current_balance:.2f}
        
        Active Bots: {TradingBot.objects.filter(user=user, is_active=True).count()}
        Open Trades: {Trade.objects.filter(user=user, status='open').count()}
        
        Best regards,
        Forex Trading Bot Team
        """
        
        # Send email
        if user.email:
            send_mail(
                subject,
                message,
                'noreply@forextradingbot.com',
                [user.email],
                fail_silently=False,
            )
            
            logger.info(f"Daily report sent to user {user.email}")
        
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for daily report")
    except Exception as exc:
        logger.error(f"Error sending daily report to user {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def process_market_data_batch(self, market_data_batch: List[Dict]):
    """Process a batch of market data updates"""
    try:
        for data in market_data_batch:
            try:
                currency_pair = CurrencyPair.objects.get(symbol=data['symbol'])
                
                MarketData.objects.create(
                    currency_pair=currency_pair,
                    timestamp=data['timestamp'],
                    bid=Decimal(str(data['bid'])),
                    ask=Decimal(str(data['ask']))
                )
                
                # Send real-time update via WebSocket
                async_to_sync(channel_layer.group_send)(
                    "market_data",
                    {
                        'type': 'market_data_update',
                        'message': data
                    }
                )
                
            except CurrencyPair.DoesNotExist:
                logger.warning(f"Currency pair {data['symbol']} not found")
            except Exception as e:
                logger.error(f"Error processing market data for {data['symbol']}: {e}")
        
        logger.debug(f"Processed batch of {len(market_data_batch)} market data updates")
        
    except Exception as exc:
        logger.error(f"Error processing market data batch: {exc}")
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3)
def monitor_system_health(self):
    """Monitor system health and send alerts if needed"""
    try:
        # Check data freshness
        latest_data = MarketData.objects.order_by('-timestamp').first()
        if latest_data:
            data_age = timezone.now() - latest_data.timestamp
            if data_age.total_seconds() > 300:  # 5 minutes
                logger.warning(f"Market data is stale: {data_age.total_seconds()} seconds old")
        
        # Check for stuck trades
        stuck_trades = Trade.objects.filter(
            status='open',
            entry_timestamp__lt=timezone.now() - timedelta(hours=24)
        )
        
        if stuck_trades.exists():
            logger.warning(f"Found {stuck_trades.count()} trades open for more than 24 hours")
        
        # Check bot performance
        active_bots = TradingBot.objects.filter(is_active=True)
        for bot in active_bots:
            recent_trades = Trade.objects.filter(
                trading_bot=bot,
                entry_timestamp__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if recent_trades == 0 and bot.is_active:
                logger.info(f"Bot {bot.name} has not made any trades in the last hour")
        
        logger.debug("System health check completed")
        
    except Exception as exc:
        logger.error(f"Error monitoring system health: {exc}")
        raise self.retry(exc=exc, countdown=300)