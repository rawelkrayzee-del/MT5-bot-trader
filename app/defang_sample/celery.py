"""
Celery configuration for forex trading bot.
Handles background tasks like data collection, trading, and notifications.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defang_sample.settings')

app = Celery('forex_trading_bot')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.TIME_ZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    beat_schedule={
        'collect-market-data': {
            'task': 'forex_trading.tasks.collect_market_data',
            'schedule': 5.0,  # Every 5 seconds
        },
        'update-technical-indicators': {
            'task': 'forex_trading.tasks.update_technical_indicators',
            'schedule': 60.0,  # Every minute
        },
        'check-trading-signals': {
            'task': 'forex_trading.tasks.check_trading_signals',
            'schedule': 10.0,  # Every 10 seconds
        },
        'execute-stop-loss-take-profit': {
            'task': 'forex_trading.tasks.execute_stop_loss_take_profit',
            'schedule': 5.0,  # Every 5 seconds
        },
        'update-bot-performance': {
            'task': 'forex_trading.tasks.update_bot_performance',
            'schedule': 300.0,  # Every 5 minutes
        },
        'cleanup-old-market-data': {
            'task': 'forex_trading.tasks.cleanup_old_market_data',
            'schedule': 3600.0,  # Every hour
        },
        'send-daily-reports': {
            'task': 'forex_trading.tasks.send_daily_reports',
            'schedule': 86400.0,  # Every day
        },
    },
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')