# 🚀 Forex Trading Bot - Full Stack Application

A comprehensive, production-ready forex trading bot platform built with Django, React, and modern DevOps practices. This application provides automated trading capabilities, real-time market analysis, portfolio management, and a professional trading dashboard.

![Forex Trading Bot](https://img.shields.io/badge/Version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.11-green)
![Django](https://img.shields.io/badge/Django-5.0.4-darkgreen)
![React](https://img.shields.io/badge/React-18.2.0-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Detailed Setup](#-detailed-setup)
- [API Documentation](#-api-documentation)
- [Trading Strategies](#-trading-strategies)
- [Monitoring](#-monitoring)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### 🎯 Core Trading Features
- **Automated Trading Bots** - Multiple strategy support with risk management
- **Real-time Market Data** - Live forex price feeds from multiple providers
- **Technical Analysis** - 20+ technical indicators (SMA, RSI, MACD, Bollinger Bands, etc.)
- **Risk Management** - Advanced position sizing and portfolio protection
- **Multiple Brokers** - OANDA integration with simulated trading support
- **Strategy Backtesting** - Historical performance analysis

### 📊 Professional Dashboard
- **Real-time Charts** - Interactive TradingView-style charts
- **Portfolio Analytics** - Comprehensive performance metrics
- **Trade Management** - Open/close positions with stop-loss/take-profit
- **Bot Management** - Create, configure, and monitor trading bots
- **Market Analysis** - Live market data and technical indicators
- **Notifications** - Real-time alerts via WebSocket

### 🔧 Technical Features
- **RESTful API** - Complete Django REST Framework implementation
- **WebSocket Support** - Real-time data streaming
- **Background Tasks** - Celery for async processing
- **Database** - PostgreSQL with optimized queries
- **Caching** - Redis for performance optimization
- **Monitoring** - Prometheus + Grafana integration
- **Security** - JWT authentication, CORS, and data validation

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │  Django Backend │    │   PostgreSQL    │
│   (Port 3000)   │◄──►│   (Port 8000)   │◄──►│   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Celery Worker  │◄──►│      Redis      │
                       │  (Background)   │    │   (Port 6379)   │
                       └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   External APIs │
                       │ TraderMade/OANDA│
                       └─────────────────┘
```

### Tech Stack

**Backend:**
- Django 5.0.4 with Django REST Framework
- PostgreSQL 15 (Database)
- Redis 7 (Caching & Message Broker)
- Celery (Background Tasks)
- Channels (WebSocket Support)

**Frontend:**
- React 18.2.0 with TypeScript
- Material-UI (MUI) 5.x
- TradingView Charts
- WebSocket Integration
- React Query for State Management

**Infrastructure:**
- Docker & Docker Compose
- Nginx (Reverse Proxy)
- Prometheus (Metrics)
- Grafana (Monitoring)
- Let's Encrypt (SSL)

## 📋 Prerequisites

- **Docker** 20.10+ and Docker Compose 2.0+
- **Git** for version control
- **8GB RAM** minimum (16GB recommended)
- **10GB** free disk space

### Optional API Keys (for live data)
- **TraderMade API** - Free tier available
- **Twelve Data API** - Free tier available  
- **OANDA API** - Practice account free

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/forex-trading-bot.git
cd forex-trading-bot
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys (optional for demo)
nano .env
```

### 3. Launch Application
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 4. Access the Application

- **Frontend Dashboard:** http://localhost:3000
- **Backend API:** http://localhost:8000/api
- **Admin Panel:** http://localhost:8000/admin
- **Celery Monitor:** http://localhost:5555
- **Email Testing:** http://localhost:8025
- **Grafana:** http://localhost:3001

### 5. Create Admin User
```bash
# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Load sample data
docker-compose exec backend python manage.py loaddata initial_data.json
```

## 🔧 Detailed Setup

### Environment Variables

Create `.env` file with your configuration:

```bash
# API Keys (Optional - app works with simulated data)
TRADERMADE_API_KEY=your_tradermade_key
TWELVE_DATA_API_KEY=your_twelve_data_key
OANDA_API_KEY=your_oanda_key
OANDA_ACCOUNT_ID=your_account_id
OANDA_ENVIRONMENT=practice

# Database (automatically configured in Docker)
DATABASE_URL=postgresql://forex_user:forex_password123@postgres:5432/forex_trading_db

# Redis (automatically configured in Docker)
REDIS_URL=redis://:redis_password123@redis:6379/0

# Email (using MailHog for development)
EMAIL_HOST=mailhog
EMAIL_PORT=1025
EMAIL_USE_TLS=False

# Security (change in production)
SECRET_KEY=your-secret-key-here
DEBUG=False
```

### Manual Installation (Alternative)

If you prefer running without Docker:

#### Backend Setup
```bash
cd app
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup database
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

#### Required Services
- PostgreSQL running on port 5432
- Redis running on port 6379

## 📚 API Documentation

### Authentication Endpoints
```
POST /api/auth/login/          # User login
POST /api/auth/register/       # User registration  
POST /api/auth/logout/         # User logout
GET  /api/auth/user/           # Current user info
```

### Trading Endpoints
```
GET    /api/forex/trades/           # List trades
POST   /api/forex/trades/           # Create trade
POST   /api/forex/trades/{id}/close/ # Close trade
GET    /api/forex/market-data/      # Market data
GET    /api/forex/currency-pairs/   # Available pairs
```

### Bot Management
```
GET    /api/forex/bots/             # List bots
POST   /api/forex/bots/             # Create bot
PATCH  /api/forex/bots/{id}/        # Update bot
POST   /api/forex/bots/{id}/start/  # Start bot
POST   /api/forex/bots/{id}/stop/   # Stop bot
DELETE /api/forex/bots/{id}/        # Delete bot
```

### Analytics
```
GET /api/forex/analytics/portfolio/  # Portfolio metrics
GET /api/forex/analytics/trades/     # Trade analytics
GET /api/forex/dashboard/stats/      # Dashboard stats
```

### WebSocket Endpoints
```
ws://localhost:8000/ws/market-data/     # Real-time prices
ws://localhost:8000/ws/notifications/   # Trade alerts
ws://localhost:8000/ws/bot/{id}/        # Bot updates
```

## 🧠 Trading Strategies

The platform includes several built-in strategies:

### 1. SMA Crossover Strategy
- **Logic:** Buy when short SMA crosses above long SMA
- **Parameters:** Short period (10), Long period (20)
- **Risk Level:** Low to Medium

### 2. RSI Mean Reversion
- **Logic:** Buy oversold (RSI < 30), Sell overbought (RSI > 70)
- **Parameters:** RSI period (14), Oversold (30), Overbought (70)
- **Risk Level:** Medium

### 3. MACD Momentum
- **Logic:** Trade based on MACD signal line crossovers
- **Parameters:** Fast (12), Slow (26), Signal (9)
- **Risk Level:** Medium to High

### 4. Bollinger Bands
- **Logic:** Mean reversion using price vs. bands
- **Parameters:** Period (20), Standard deviations (2)
- **Risk Level:** Low to Medium

### Creating Custom Strategies

```python
from trading_bot.strategies import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self, parameters):
        super().__init__(parameters)
        self.name = "My Custom Strategy"
    
    def generate_signal(self, market_data, indicators):
        # Your strategy logic here
        if should_buy():
            return {
                'action': 'buy',
                'currency_pair': 'EUR/USD',
                'price': current_price,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'confidence': 0.85
            }
        return None
```

## 📊 Monitoring

### Application Metrics

Access Grafana at http://localhost:3001 (admin/admin123):

- **System Metrics:** CPU, Memory, Disk usage
- **Trading Metrics:** Trades per hour, P&L, Win rate
- **API Metrics:** Request rate, Response time, Error rate
- **Bot Performance:** Active bots, Success rate, Portfolio value

### Celery Monitoring

Flower dashboard at http://localhost:5555:

- **Worker Status:** Active/offline workers
- **Task Monitoring:** Completed/failed tasks
- **Queue Status:** Task queue lengths
- **Resource Usage:** Worker memory/CPU

### Log Management

```bash
# View application logs
docker-compose logs -f backend

# View specific service logs
docker-compose logs -f celery_worker
docker-compose logs -f postgres

# View trading activity
docker-compose exec backend python manage.py shell
>>> from forex_trading.models import Trade
>>> Trade.objects.filter(status='open').count()
```

## 🚢 Deployment

### Production Deployment

1. **Update Environment Variables**
```bash
# Set production values
DEBUG=False
SECRET_KEY=your-secure-secret-key
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:pass@prod-db:5432/forex_db
```

2. **SSL Configuration**
```bash
# Generate SSL certificates
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem
```

3. **Deploy with Docker Compose**
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale workers based on load
docker-compose up -d --scale celery_worker=4
```

### Cloud Deployment Options

- **AWS:** ECS/Fargate with RDS and ElastiCache
- **Google Cloud:** Cloud Run with Cloud SQL
- **Azure:** Container Instances with Azure Database
- **DigitalOcean:** App Platform with Managed Database

### Performance Optimization

- **Database:** Connection pooling, query optimization
- **Caching:** Redis for session storage and API caching
- **CDN:** Static file delivery via CloudFlare/AWS CloudFront
- **Load Balancing:** Multiple backend instances behind Nginx

## 🛠️ Development

### Running Tests
```bash
# Backend tests
docker-compose exec backend python manage.py test

# Frontend tests  
docker-compose exec frontend npm test

# Integration tests
docker-compose exec backend python manage.py test forex_trading.tests.integration
```

### Code Quality
```bash
# Python linting
docker-compose exec backend flake8 .
docker-compose exec backend black .

# JavaScript linting
docker-compose exec frontend npm run lint
docker-compose exec frontend npm run lint:fix
```

### Database Migrations
```bash
# Create new migration
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate

# Show migration status
docker-compose exec backend python manage.py showmigrations
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use ESLint/Prettier for JavaScript/TypeScript
- Write tests for new features
- Update documentation for API changes
- Ensure Docker builds work correctly

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and demonstration purposes only. Forex trading involves substantial risk and may not be suitable for all investors. Past performance does not guarantee future results. Please consult with a financial advisor before making any investment decisions.

## 📞 Support

- **Documentation:** [Wiki](https://github.com/yourusername/forex-trading-bot/wiki)
- **Issues:** [GitHub Issues](https://github.com/yourusername/forex-trading-bot/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/forex-trading-bot/discussions)

## 🔮 Roadmap

- [ ] Machine Learning-based strategies
- [ ] Mobile app (React Native)
- [ ] Additional broker integrations
- [ ] Social trading features
- [ ] Advanced backtesting engine
- [ ] Multi-timeframe analysis
- [ ] Portfolio optimization algorithms

---

**Built with ❤️ for the trading community**
