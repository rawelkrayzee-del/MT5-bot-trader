"""
Trading execution engine for automated forex trading.
Handles order execution, risk management, and broker integration.
"""

import time
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

from forex_trading.models import (
    Trade, TradingAccount, CurrencyPair, MarketData, TradingBot
)

logger = logging.getLogger(__name__)


class OrderType:
    """Order type constants"""
    MARKET = 'market'
    LIMIT = 'limit'
    STOP = 'stop'
    STOP_LOSS = 'stop_loss'
    TAKE_PROFIT = 'take_profit'


class RiskManager:
    """Risk management system for trading operations"""
    
    def __init__(self, account: TradingAccount):
        self.account = account
        self.max_risk_per_trade = Decimal('0.02')  # 2% per trade
        self.max_total_risk = Decimal('0.10')  # 10% total portfolio risk
        self.max_drawdown = Decimal('0.15')  # 15% maximum drawdown
        self.correlation_limit = Decimal('0.7')  # Maximum correlation between trades
    
    def calculate_position_size(self, currency_pair: CurrencyPair, 
                              entry_price: Decimal, stop_loss: Decimal) -> Decimal:
        """Calculate position size based on risk parameters"""
        try:
            # Calculate risk per pip
            pip_value = currency_pair.pip_size
            risk_in_pips = abs(entry_price - stop_loss) / pip_value
            
            # Maximum risk amount
            max_risk_amount = self.account.balance * self.max_risk_per_trade
            
            # Calculate position size
            position_size = max_risk_amount / (risk_in_pips * pip_value)
            
            # Apply maximum position limits
            max_position = self.account.balance * Decimal('0.1')  # 10% of balance
            position_size = min(position_size, max_position)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return Decimal('0')
    
    def validate_trade(self, trade_signal: Dict) -> Tuple[bool, str]:
        """Validate trade against risk management rules"""
        try:
            # Check account balance
            if self.account.balance <= 0:
                return False, "Insufficient account balance"
            
            # Check maximum number of open trades
            open_trades = Trade.objects.filter(
                user=self.account.user,
                status='open'
            ).count()
            
            if open_trades >= 10:  # Maximum 10 open trades
                return False, "Maximum number of open trades reached"
            
            # Check total risk exposure
            total_risk = self._calculate_total_risk()
            if total_risk > self.max_total_risk:
                return False, "Total risk exposure exceeds limit"
            
            # Check correlation with existing trades
            if self._check_correlation(trade_signal['currency_pair']):
                return False, "High correlation with existing trades"
            
            # Check drawdown
            current_drawdown = self._calculate_drawdown()
            if current_drawdown > self.max_drawdown:
                return False, "Maximum drawdown exceeded"
            
            return True, "Trade validated"
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return False, f"Validation error: {e}"
    
    def _calculate_total_risk(self) -> Decimal:
        """Calculate total risk exposure across all open trades"""
        open_trades = Trade.objects.filter(
            user=self.account.user,
            status='open'
        )
        
        total_risk = Decimal('0')
        for trade in open_trades:
            if trade.stop_loss and trade.entry_price:
                trade_risk = abs(trade.entry_price - trade.stop_loss) * trade.volume
                total_risk += trade_risk
        
        return total_risk / self.account.balance if self.account.balance > 0 else Decimal('1')
    
    def _check_correlation(self, currency_pair: str) -> bool:
        """Check if new trade is highly correlated with existing trades"""
        # Simplified correlation check - in production, use actual correlation data
        open_trades = Trade.objects.filter(
            user=self.account.user,
            status='open'
        )
        
        same_base_currency = 0
        for trade in open_trades:
            if (currency_pair[:3] == trade.currency_pair.symbol[:3] or
                currency_pair[4:] == trade.currency_pair.symbol[4:]):
                same_base_currency += 1
        
        return same_base_currency >= 3  # Max 3 trades with same base currency
    
    def _calculate_drawdown(self) -> Decimal:
        """Calculate current account drawdown"""
        initial_balance = self.account.initial_balance or self.account.balance
        current_equity = self.account.balance + self._calculate_unrealized_pnl()
        
        drawdown = (initial_balance - current_equity) / initial_balance
        return max(drawdown, Decimal('0'))
    
    def _calculate_unrealized_pnl(self) -> Decimal:
        """Calculate unrealized P&L from open trades"""
        open_trades = Trade.objects.filter(
            user=self.account.user,
            status='open'
        )
        
        total_pnl = Decimal('0')
        for trade in open_trades:
            # Get current market price
            latest_data = MarketData.objects.filter(
                currency_pair=trade.currency_pair
            ).order_by('-timestamp').first()
            
            if latest_data and trade.entry_price:
                if trade.trade_type == 'buy':
                    current_price = latest_data.bid
                    pnl = (current_price - trade.entry_price) * trade.volume
                else:
                    current_price = latest_data.ask
                    pnl = (trade.entry_price - current_price) * trade.volume
                
                total_pnl += pnl
        
        return total_pnl


class OANDABroker:
    """OANDA broker integration for live trading"""
    
    def __init__(self, api_key: str, account_id: str, environment: str = 'practice'):
        self.api_key = api_key
        self.account_id = account_id
        self.environment = environment
        
        if environment == 'live':
            self.base_url = "https://api-fxtrade.oanda.com"
        else:
            self.base_url = "https://api-fxpractice.oanda.com"
        
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def place_order(self, order_data: Dict) -> Dict:
        """Place an order through OANDA API"""
        try:
            import requests
            
            url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
            
            # Convert order data to OANDA format
            oanda_order = self._convert_to_oanda_format(order_data)
            
            response = requests.post(
                url, 
                headers=self.headers,
                json={'order': oanda_order},
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': True,
                'order_id': result.get('orderCreateTransaction', {}).get('id'),
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def close_position(self, trade_id: str) -> Dict:
        """Close a position through OANDA API"""
        try:
            import requests
            
            url = f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/close"
            
            response = requests.put(
                url,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_account_info(self) -> Dict:
        """Get account information from OANDA"""
        try:
            import requests
            
            url = f"{self.base_url}/v3/accounts/{self.account_id}"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def _convert_to_oanda_format(self, order_data: Dict) -> Dict:
        """Convert internal order format to OANDA format"""
        oanda_order = {
            'type': order_data.get('type', 'MARKET').upper(),
            'instrument': order_data['symbol'].replace('/', '_'),
            'units': str(int(order_data['volume'])),
        }
        
        # Add price for limit orders
        if order_data.get('type') == 'limit':
            oanda_order['price'] = str(order_data['price'])
        
        # Add stop loss and take profit
        if order_data.get('stop_loss'):
            oanda_order['stopLossOnFill'] = {
                'price': str(order_data['stop_loss'])
            }
        
        if order_data.get('take_profit'):
            oanda_order['takeProfitOnFill'] = {
                'price': str(order_data['take_profit'])
            }
        
        return oanda_order


class SimulatedBroker:
    """Simulated broker for testing and development"""
    
    def __init__(self):
        self.orders = {}
        self.next_order_id = 1
        self.slippage = Decimal('0.0001')  # 1 pip slippage
    
    def place_order(self, order_data: Dict) -> Dict:
        """Simulate order placement"""
        try:
            order_id = str(self.next_order_id)
            self.next_order_id += 1
            
            # Simulate execution with slight slippage
            execution_price = order_data.get('price', 0)
            if order_data.get('type') == 'market':
                # Add slippage for market orders
                if order_data.get('side') == 'buy':
                    execution_price = Decimal(str(execution_price)) + self.slippage
                else:
                    execution_price = Decimal(str(execution_price)) - self.slippage
            
            self.orders[order_id] = {
                **order_data,
                'order_id': order_id,
                'execution_price': execution_price,
                'status': 'filled',
                'timestamp': timezone.now()
            }
            
            return {
                'success': True,
                'order_id': order_id,
                'execution_price': execution_price
            }
            
        except Exception as e:
            logger.error(f"Error in simulated order: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def close_position(self, trade_id: str) -> Dict:
        """Simulate position closing"""
        return {
            'success': True,
            'trade_id': trade_id,
            'timestamp': timezone.now()
        }


class TradingExecutor:
    """Main trading execution engine"""
    
    def __init__(self, account: TradingAccount):
        self.account = account
        self.risk_manager = RiskManager(account)
        
        # Initialize broker based on configuration
        if hasattr(settings, 'OANDA_API_KEY') and settings.OANDA_API_KEY:
            self.broker = OANDABroker(
                api_key=settings.OANDA_API_KEY,
                account_id=getattr(settings, 'OANDA_ACCOUNT_ID', ''),
                environment=getattr(settings, 'OANDA_ENVIRONMENT', 'practice')
            )
        else:
            self.broker = SimulatedBroker()
    
    def execute_trade_signal(self, trade_signal: Dict) -> Dict:
        """Execute a trade signal"""
        try:
            # Validate trade signal
            is_valid, message = self.risk_manager.validate_trade(trade_signal)
            if not is_valid:
                return {
                    'success': False,
                    'error': f"Trade validation failed: {message}"
                }
            
            # Get currency pair
            currency_pair = CurrencyPair.objects.filter(
                symbol=trade_signal['currency_pair']
            ).first()
            
            if not currency_pair:
                return {
                    'success': False,
                    'error': "Currency pair not found"
                }
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                currency_pair,
                trade_signal['entry_price'],
                trade_signal.get('stop_loss', trade_signal['entry_price'])
            )
            
            if position_size <= 0:
                return {
                    'success': False,
                    'error': "Invalid position size calculated"
                }
            
            # Prepare order data
            order_data = {
                'symbol': trade_signal['currency_pair'],
                'type': trade_signal.get('order_type', OrderType.MARKET),
                'side': trade_signal['trade_type'],  # 'buy' or 'sell'
                'volume': position_size,
                'price': trade_signal['entry_price'],
                'stop_loss': trade_signal.get('stop_loss'),
                'take_profit': trade_signal.get('take_profit')
            }
            
            # Execute order through broker
            result = self.broker.place_order(order_data)
            
            if result['success']:
                # Create trade record
                trade = Trade.objects.create(
                    user=self.account.user,
                    currency_pair=currency_pair,
                    trade_type=trade_signal['trade_type'],
                    volume=position_size,
                    entry_price=result.get('execution_price', trade_signal['entry_price']),
                    stop_loss=trade_signal.get('stop_loss'),
                    take_profit=trade_signal.get('take_profit'),
                    status='open',
                    broker_trade_id=result.get('order_id'),
                    strategy_name=trade_signal.get('strategy_name', 'Unknown')
                )
                
                # Update account balance (for simulated trading)
                if isinstance(self.broker, SimulatedBroker):
                    self._update_simulated_balance(trade)
                
                logger.info(f"Trade executed successfully: {trade.id}")
                
                return {
                    'success': True,
                    'trade_id': trade.id,
                    'message': "Trade executed successfully"
                }
            else:
                return {
                    'success': False,
                    'error': f"Order execution failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                'success': False,
                'error': f"Execution error: {e}"
            }
    
    def close_trade(self, trade: Trade, reason: str = 'Manual') -> Dict:
        """Close an existing trade"""
        try:
            if trade.status != 'open':
                return {
                    'success': False,
                    'error': "Trade is not open"
                }
            
            # Get current market price
            latest_data = MarketData.objects.filter(
                currency_pair=trade.currency_pair
            ).order_by('-timestamp').first()
            
            if not latest_data:
                return {
                    'success': False,
                    'error': "No market data available"
                }
            
            # Determine exit price based on trade type
            if trade.trade_type == 'buy':
                exit_price = latest_data.bid
            else:
                exit_price = latest_data.ask
            
            # Close position through broker
            if trade.broker_trade_id:
                result = self.broker.close_position(trade.broker_trade_id)
                if not result['success']:
                    logger.warning(f"Broker close failed: {result.get('error')}")
            
            # Calculate P&L
            if trade.trade_type == 'buy':
                pnl = (exit_price - trade.entry_price) * trade.volume
            else:
                pnl = (trade.entry_price - exit_price) * trade.volume
            
            # Update trade record
            trade.exit_price = exit_price
            trade.exit_timestamp = timezone.now()
            trade.pnl = pnl
            trade.status = 'closed'
            trade.close_reason = reason
            trade.save()
            
            # Update account balance
            self.account.balance += pnl
            self.account.save()
            
            logger.info(f"Trade closed: {trade.id}, P&L: {pnl}")
            
            return {
                'success': True,
                'trade_id': trade.id,
                'pnl': pnl,
                'message': "Trade closed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            return {
                'success': False,
                'error': f"Close error: {e}"
            }
    
    def check_stop_loss_take_profit(self):
        """Check and execute stop loss and take profit orders"""
        try:
            open_trades = Trade.objects.filter(
                user=self.account.user,
                status='open'
            )
            
            for trade in open_trades:
                # Get current market price
                latest_data = MarketData.objects.filter(
                    currency_pair=trade.currency_pair
                ).order_by('-timestamp').first()
                
                if not latest_data:
                    continue
                
                current_price = latest_data.bid if trade.trade_type == 'buy' else latest_data.ask
                
                # Check stop loss
                if trade.stop_loss:
                    if ((trade.trade_type == 'buy' and current_price <= trade.stop_loss) or
                        (trade.trade_type == 'sell' and current_price >= trade.stop_loss)):
                        
                        self.close_trade(trade, 'Stop Loss')
                        continue
                
                # Check take profit
                if trade.take_profit:
                    if ((trade.trade_type == 'buy' and current_price >= trade.take_profit) or
                        (trade.trade_type == 'sell' and current_price <= trade.take_profit)):
                        
                        self.close_trade(trade, 'Take Profit')
                        continue
                        
        except Exception as e:
            logger.error(f"Error checking stop loss/take profit: {e}")
    
    def _update_simulated_balance(self, trade: Trade):
        """Update account balance for simulated trading"""
        # Deduct small commission for simulated trading
        commission = trade.volume * Decimal('0.00002')  # 0.2 pips commission
        self.account.balance -= commission
        self.account.save()


def create_trading_executor(user) -> Optional[TradingExecutor]:
    """Create a trading executor for a user"""
    try:
        account = TradingAccount.objects.filter(user=user, is_active=True).first()
        if account:
            return TradingExecutor(account)
        return None
    except Exception as e:
        logger.error(f"Error creating trading executor: {e}")
        return None