from django.apps import AppConfig


class ForexTradingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'forex_trading'
    verbose_name = 'Forex Trading'

    def ready(self):
        import forex_trading.signals