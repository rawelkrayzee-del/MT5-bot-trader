from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'currency-pairs', views.CurrencyPairViewSet)
router.register(r'market-data', views.MarketDataViewSet)
router.register(r'strategies', views.TradingStrategyViewSet, basename='strategy')
router.register(r'trades', views.TradeViewSet, basename='trade')
router.register(r'accounts', views.TradingAccountViewSet, basename='account')
router.register(r'bots', views.TradingBotViewSet, basename='bot')
router.register(r'indicators', views.TechnicalIndicatorViewSet, basename='indicator')

# The API URLs are now determined automatically by the router
app_name = 'forex_trading'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Dashboard and analytics endpoints
    path('api/dashboard/', views.DashboardAPIView.as_view(), name='dashboard'),
    path('api/portfolio/', views.PortfolioAPIView.as_view(), name='portfolio'),
    path('api/analysis/', views.MarketAnalysisAPIView.as_view(), name='analysis'),
]