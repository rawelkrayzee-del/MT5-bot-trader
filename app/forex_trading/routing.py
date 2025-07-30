from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/market-data/$', consumers.MarketDataConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.TradingNotificationConsumer.as_asgi()),
    re_path(r'ws/bot/(?P<bot_id>\d+)/$', consumers.TradingBotConsumer.as_asgi()),
]