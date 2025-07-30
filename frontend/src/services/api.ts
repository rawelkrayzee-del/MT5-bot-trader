/**
 * API Service for Forex Trading Bot
 * Handles all HTTP requests with proper error handling and authentication
 */

import axios, { AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { toast } from 'react-toastify';

// Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  errors?: Record<string, string[]>;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface MarketData {
  id: string;
  currency_pair: string;
  timestamp: string;
  bid: number;
  ask: number;
  spread: number;
  change_24h: number;
  change_percentage: number;
}

export interface Trade {
  id: string;
  currency_pair: string;
  trade_type: 'buy' | 'sell';
  volume: number;
  entry_price: number;
  exit_price?: number;
  stop_loss?: number;
  take_profit?: number;
  status: 'open' | 'closed' | 'pending';
  pnl?: number;
  entry_timestamp: string;
  exit_timestamp?: string;
  strategy_name: string;
  close_reason?: string;
}

export interface TradingBot {
  id: string;
  name: string;
  strategy: string;
  is_active: boolean;
  currency_pairs: string[];
  risk_level: 'low' | 'medium' | 'high';
  max_trades: number;
  created_at: string;
  performance: {
    total_trades: number;
    profitable_trades: number;
    total_pnl: number;
    win_rate: number;
    avg_trade_duration: number;
  };
}

export interface TradingAccount {
  id: string;
  name: string;
  balance: number;
  equity: number;
  margin_used: number;
  margin_available: number;
  currency: string;
  leverage: number;
  is_active: boolean;
}

export interface CurrencyPair {
  id: string;
  symbol: string;
  base_currency: string;
  quote_currency: string;
  pip_size: number;
  is_active: boolean;
}

export interface TradingStrategy {
  id: string;
  name: string;
  description: string;
  parameters: Record<string, any>;
  risk_level: 'low' | 'medium' | 'high';
  is_active: boolean;
  performance: {
    total_trades: number;
    win_rate: number;
    avg_pnl: number;
    max_drawdown: number;
  };
}

export interface DashboardStats {
  total_balance: number;
  total_equity: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  open_trades: number;
  active_bots: number;
  total_trades_today: number;
  win_rate: number;
}

// Base API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          });
          
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          
          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access}`;
          }
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    // Handle different error types
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          if (data.errors) {
            // Form validation errors
            Object.entries(data.errors).forEach(([field, messages]) => {
              if (Array.isArray(messages)) {
                messages.forEach(message => toast.error(`${field}: ${message}`));
              }
            });
          } else {
            toast.error(data.message || 'Bad request');
          }
          break;
        case 403:
          toast.error('Access denied');
          break;
        case 404:
          toast.error('Resource not found');
          break;
        case 429:
          toast.error('Too many requests. Please try again later.');
          break;
        case 500:
          toast.error('Server error. Please try again later.');
          break;
        default:
          toast.error(data.message || 'An unexpected error occurred');
      }
    } else if (error.request) {
      toast.error('Network error. Please check your connection.');
    } else {
      toast.error('An unexpected error occurred');
    }

    return Promise.reject(error);
  }
);

// API Service Class
class ApiService {
  // Authentication endpoints
  async login(email: string, password: string): Promise<ApiResponse<{ access: string; refresh: string; user: any }>> {
    const response = await api.post('/auth/login/', { email, password });
    return response.data;
  }

  async register(userData: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }): Promise<ApiResponse<any>> {
    const response = await api.post('/auth/register/', userData);
    return response.data;
  }

  async logout(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      await api.post('/auth/logout/', { refresh: refreshToken });
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  async getCurrentUser(): Promise<ApiResponse<any>> {
    const response = await api.get('/auth/user/');
    return response.data;
  }

  // Dashboard endpoints
  async getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
    const response = await api.get('/forex/dashboard/stats/');
    return response.data;
  }

  // Market data endpoints
  async getMarketData(symbols?: string[]): Promise<ApiResponse<MarketData[]>> {
    const params = symbols ? { symbols: symbols.join(',') } : {};
    const response = await api.get('/forex/market-data/', { params });
    return response.data;
  }

  async getHistoricalData(
    symbol: string,
    timeframe: string,
    start_date?: string,
    end_date?: string
  ): Promise<ApiResponse<any[]>> {
    const response = await api.get(`/forex/market-data/historical/`, {
      params: { symbol, timeframe, start_date, end_date }
    });
    return response.data;
  }

  // Currency pairs endpoints
  async getCurrencyPairs(): Promise<ApiResponse<CurrencyPair[]>> {
    const response = await api.get('/forex/currency-pairs/');
    return response.data;
  }

  // Trading endpoints
  async getTrades(params?: {
    status?: string;
    currency_pair?: string;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<PaginatedResponse<Trade>>> {
    const response = await api.get('/forex/trades/', { params });
    return response.data;
  }

  async createTrade(tradeData: {
    currency_pair: string;
    trade_type: 'buy' | 'sell';
    volume: number;
    stop_loss?: number;
    take_profit?: number;
    order_type?: 'market' | 'limit';
    limit_price?: number;
  }): Promise<ApiResponse<Trade>> {
    const response = await api.post('/forex/trades/', tradeData);
    return response.data;
  }

  async closeTrade(tradeId: string): Promise<ApiResponse<Trade>> {
    const response = await api.post(`/forex/trades/${tradeId}/close/`);
    return response.data;
  }

  // Trading account endpoints
  async getTradingAccounts(): Promise<ApiResponse<TradingAccount[]>> {
    const response = await api.get('/forex/accounts/');
    return response.data;
  }

  async createTradingAccount(accountData: {
    name: string;
    balance: number;
    currency: string;
    leverage: number;
  }): Promise<ApiResponse<TradingAccount>> {
    const response = await api.post('/forex/accounts/', accountData);
    return response.data;
  }

  // Trading bot endpoints
  async getTradingBots(): Promise<ApiResponse<TradingBot[]>> {
    const response = await api.get('/forex/bots/');
    return response.data;
  }

  async createTradingBot(botData: {
    name: string;
    strategy: string;
    currency_pairs: string[];
    risk_level: 'low' | 'medium' | 'high';
    max_trades: number;
    parameters: Record<string, any>;
  }): Promise<ApiResponse<TradingBot>> {
    const response = await api.post('/forex/bots/', botData);
    return response.data;
  }

  async updateTradingBot(botId: string, botData: Partial<TradingBot>): Promise<ApiResponse<TradingBot>> {
    const response = await api.patch(`/forex/bots/${botId}/`, botData);
    return response.data;
  }

  async startTradingBot(botId: string): Promise<ApiResponse<any>> {
    const response = await api.post(`/forex/bots/${botId}/start/`);
    return response.data;
  }

  async stopTradingBot(botId: string): Promise<ApiResponse<any>> {
    const response = await api.post(`/forex/bots/${botId}/stop/`);
    return response.data;
  }

  async deleteTradingBot(botId: string): Promise<ApiResponse<any>> {
    const response = await api.delete(`/forex/bots/${botId}/`);
    return response.data;
  }

  // Trading strategies endpoints
  async getTradingStrategies(): Promise<ApiResponse<TradingStrategy[]>> {
    const response = await api.get('/forex/strategies/');
    return response.data;
  }

  async createTradingStrategy(strategyData: {
    name: string;
    description: string;
    parameters: Record<string, any>;
    risk_level: 'low' | 'medium' | 'high';
  }): Promise<ApiResponse<TradingStrategy>> {
    const response = await api.post('/forex/strategies/', strategyData);
    return response.data;
  }

  async updateTradingStrategy(strategyId: string, strategyData: Partial<TradingStrategy>): Promise<ApiResponse<TradingStrategy>> {
    const response = await api.patch(`/forex/strategies/${strategyId}/`, strategyData);
    return response.data;
  }

  async backtestStrategy(strategyId: string, backtestData: {
    start_date: string;
    end_date: string;
    initial_balance: number;
    currency_pairs: string[];
  }): Promise<ApiResponse<any>> {
    const response = await api.post(`/forex/strategies/${strategyId}/backtest/`, backtestData);
    return response.data;
  }

  // Analytics endpoints
  async getPortfolioAnalytics(params?: {
    period?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<ApiResponse<any>> {
    const response = await api.get('/forex/analytics/portfolio/', { params });
    return response.data;
  }

  async getTradeAnalytics(params?: {
    period?: string;
    strategy?: string;
    currency_pair?: string;
  }): Promise<ApiResponse<any>> {
    const response = await api.get('/forex/analytics/trades/', { params });
    return response.data;
  }

  // Technical indicators endpoints
  async getTechnicalIndicators(symbol: string, timeframe?: string): Promise<ApiResponse<any>> {
    const response = await api.get(`/forex/indicators/`, {
      params: { symbol, timeframe }
    });
    return response.data;
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;