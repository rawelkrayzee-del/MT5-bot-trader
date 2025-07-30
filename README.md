# MT5 Trading Bot - Full Stack Platform

## 🚀 Proyek Trading Bot MT5 Lengkap dan Siap Pakai

Platform trading bot MetaTrader 5 yang lengkap dengan antarmuka web modern, analisis real-time, dan sistem manajemen risiko otomatis. Dibangun dengan teknologi full-stack terkini untuk memberikan pengalaman trading yang profesional dan efisien.

## ✨ Fitur Utama

### 🎯 Trading & Execution
- **Koneksi MT5 Real-time**: Integrasi langsung dengan MetaTrader 5 menggunakan Python API
- **Eksekusi Order Otomatis**: Market orders, pending orders, dan stop limit orders
- **Multi-Strategy Support**: Mendukung berbagai strategi trading algoritmik
- **Risk Management**: Position sizing otomatis dan stop loss/take profit dinamis
- **Portfolio Management**: Manajemen portfolio multi-instrument

### 📊 Dashboard & Analytics
- **Real-time Dashboard**: Monitoring performa trading secara real-time
- **Interactive Charts**: Chart trading dengan indikator teknikal terintegrasi
- **Performance Analytics**: Analisis detail performa trading dan statistik
- **Trade History**: Riwayat trading lengkap dengan filtering dan ekspor
- **Risk Metrics**: Kalkulasi risiko real-time dan exposure analysis

### 🧠 Strategy Builder
- **Visual Strategy Builder**: Pembuat strategi visual drag-and-drop
- **Backtesting Engine**: Uji strategi dengan data historis
- **Strategy Optimization**: Optimasi parameter strategi otomatis
- **Signal Generation**: Generator sinyal trading dengan multiple indicators
- **Custom Indicators**: Support untuk indikator teknikal custom

### 🔒 Security & Management
- **User Authentication**: Sistem autentikasi yang aman
- **Account Management**: Manajemen multiple trading accounts
- **API Security**: Enkripsi dan keamanan API keys
- **Audit Logs**: Logging lengkap untuk semua aktivitas trading
- **Backup & Recovery**: Sistem backup otomatis

### 📱 Modern Interface
- **Responsive Design**: Antarmuka yang responsif untuk semua device
- **Dark/Light Mode**: Tema gelap dan terang
- **Real-time Updates**: Update data real-time via WebSocket
- **Mobile Optimized**: Optimasi untuk trading mobile
- **Customizable Layout**: Layout dashboard yang dapat dikustomisasi

## 🏗️ Arsitektur Teknologi

### Backend (Django)
- **Framework**: Django 5.0+ dengan Django REST Framework
- **Database**: PostgreSQL dengan Redis untuk caching
- **API Integration**: MetaTrader 5 Python API
- **WebSocket**: Django Channels untuk real-time communication
- **Task Queue**: Celery dengan Redis broker
- **Authentication**: JWT dengan refresh tokens

### Frontend (React)
- **Framework**: React 18+ dengan TypeScript
- **State Management**: Redux Toolkit dengan RTK Query
- **UI Library**: Material-UI (MUI) dengan custom themes
- **Charts**: TradingView Charting Library
- **Real-time**: Socket.IO client untuk WebSocket
- **Build Tool**: Vite untuk development dan build yang cepat

### Infrastructure
- **Containerization**: Docker dan Docker Compose
- **Deployment**: Docker Swarm atau Kubernetes
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Load Balancer**: Nginx dengan SSL termination

## 📋 Struktur Proyek

```
mt5-trading-bot/
├── backend/                    # Django backend
│   ├── core/                  # Core Django settings
│   ├── accounts/              # User management
│   ├── trading/               # Trading models dan logic
│   ├── strategies/            # Strategy management
│   ├── analytics/             # Analytics dan reporting
│   ├── mt5_integration/       # MT5 API integration
│   └── websocket/             # WebSocket handlers
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/        # Reusable components
│   │   ├── pages/             # Page components
│   │   ├── store/             # Redux store
│   │   ├── services/          # API services
│   │   └── utils/             # Utility functions
│   └── public/
├── docker/                    # Docker configurations
├── docs/                      # Documentation
└── scripts/                   # Deployment scripts
```

## 🚦 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- MetaTrader 5 Terminal

### Installation

1. **Clone Repository**
```bash
git clone <repository-url>
cd mt5-trading-bot
```

2. **Setup Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

3. **Setup Frontend**
```bash
cd frontend
npm install
npm run dev
```

4. **Setup MT5 Connection**
```bash
# Install MT5 Python package
pip install MetaTrader5

# Configure MT5 credentials in backend/.env
MT5_LOGIN=your_login
MT5_PASSWORD=your_password
MT5_SERVER=your_server
MT5_PATH=/path/to/mt5/terminal
```

5. **Run Development Servers**
```bash
# Backend (Terminal 1)
cd backend
python manage.py runserver

# Frontend (Terminal 2)
cd frontend
npm run dev

# Celery Worker (Terminal 3)
cd backend
celery -A core worker -l info

# Redis (Terminal 4)
redis-server
```

## 🔧 Konfigurasi

### Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/mt5_trading
REDIS_URL=redis://localhost:6379

# MT5 Configuration
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=MetaQuotes-Demo
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
CORS_ALLOWED_ORIGINS=http://localhost:3000

# External APIs
ALPHA_VANTAGE_API_KEY=your_key
FINANCIAL_MODELING_PREP_API_KEY=your_key
```

### Trading Configuration
```python
# Trading settings
TRADING_SETTINGS = {
    'DEFAULT_RISK_PERCENT': 1.0,
    'MAX_RISK_PERCENT': 5.0,
    'DEFAULT_SLIPPAGE': 3,
    'MAX_SPREAD': 5,
    'TRADING_HOURS': {
        'start': '09:00',
        'end': '17:00',
        'timezone': 'UTC'
    }
}
```

## 📖 Panduan Penggunaan

### 1. Setup Trading Account
1. Login ke dashboard web
2. Tambahkan MT5 account credentials
3. Verifikasi koneksi MT5
4. Konfigurasi trading settings

### 2. Membuat Strategy
1. Akses Strategy Builder
2. Pilih indikator teknikal
3. Set entry/exit conditions
4. Konfigurasi risk management
5. Backtest strategy

### 3. Deploy Trading Bot
1. Activate strategy
2. Set position sizing
3. Monitor real-time performance
4. Adjust parameters sesuai kebutuhan

### 4. Monitoring & Analytics
1. Dashboard real-time monitoring
2. Review trade history
3. Analyze performance metrics
4. Export trading reports

## 🛡️ Risk Management

### Position Sizing
- **Fixed Percent**: Risiko tetap per trade
- **Kelly Criterion**: Optimal position sizing
- **ATR-based**: Position sizing berdasarkan volatilitas
- **Equity Curve**: Adaptive sizing berdasarkan performa

### Stop Loss & Take Profit
- **Static Levels**: Level tetap berdasarkan pips
- **ATR-based**: Dynamic levels berdasarkan volatilitas
- **Support/Resistance**: Levels berdasarkan S/R
- **Trailing Stops**: Stop loss yang mengikuti harga

## 📊 Trading Strategies

### Trend Following
- **Moving Average Crossover**
- **MACD Signal**
- **ADX Trend Strength**
- **Parabolic SAR**

### Mean Reversion
- **RSI Overbought/Oversold**
- **Bollinger Bands**
- **Stochastic Oscillator**
- **Williams %R**

### Breakout Strategies
- **Support/Resistance Breakout**
- **Channel Breakout**
- **Volume Breakout**
- **News-based Breakout**

### Advanced Strategies
- **Machine Learning Models**
- **Sentiment Analysis**
- **Multi-timeframe Analysis**
- **Portfolio Optimization**

## 🔍 Monitoring & Logging

### Real-time Monitoring
- Trade execution status
- Account balance dan equity
- Open positions
- Risk exposure
- Market conditions

### Performance Analytics
- Win rate dan profit factor
- Sharpe ratio
- Maximum drawdown
- Risk-adjusted returns
- Monthly/yearly performance

### Error Handling
- Connection monitoring
- Trade execution errors
- Strategy validation
- Risk limit breaches
- Emergency stops

## 🚀 Deployment

### Docker Production Setup
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale web=3

# Monitor logs
docker-compose logs -f
```

### Kubernetes Deployment
```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check status
kubectl get pods
kubectl get services
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
python manage.py test
pytest
coverage run -m pytest
coverage report
```

### Frontend Tests
```bash
cd frontend
npm test
npm run test:coverage
npm run test:e2e
```

### Integration Tests
```bash
# Test MT5 connection
python manage.py test_mt5_connection

# Test trading workflow
python manage.py test_trading_workflow
```

## 📚 API Documentation

### Trading API Endpoints
- `POST /api/trading/orders/` - Create new order
- `GET /api/trading/positions/` - Get open positions
- `DELETE /api/trading/positions/{id}/` - Close position
- `GET /api/trading/history/` - Get trade history
- `POST /api/trading/strategies/` - Create strategy

### Market Data API
- `GET /api/market/symbols/` - Available symbols
- `GET /api/market/prices/{symbol}/` - Real-time prices
- `GET /api/market/history/{symbol}/` - Historical data
- `GET /api/market/indicators/{symbol}/` - Technical indicators

### Account API
- `GET /api/account/info/` - Account information
- `GET /api/account/balance/` - Account balance
- `GET /api/account/performance/` - Performance metrics
- `POST /api/account/settings/` - Update settings

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

Trading foreign exchange and CFDs on margin carries a high level of risk and may not be suitable for all investors. The high degree of leverage can work against you as well as for you. Before deciding to trade foreign exchange you should carefully consider your investment objectives, level of experience, and risk appetite.

## 🆘 Support

- 📧 Email: support@mt5tradingbot.com
- 💬 Discord: [Join our community](https://discord.gg/mt5trading)
- 📖 Documentation: [docs.mt5tradingbot.com](https://docs.mt5tradingbot.com)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)

---

**Built with ❤️ for the trading community**
