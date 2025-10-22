/**
 * Real API service for TradePulse IQ Dashboard
 * Replaces mockApi with actual backend calls
 */

import { 
    PortfolioResponse, 
    Trade, 
    EquityPoint, 
    PerformanceMetrics,
    BotStatus,
    PatternPerformance,
    ActiveTrade,
    TrainedAsset,
    TrainedAssetDetails,
    AssetRanking,
    TrainingStatus,
    TrainingResults,
    ExchangeConnection
} from '../types';

const API_BASE_URL = process.env.NODE_ENV === 'production' 
    ? '/api'  // Production: served by FastAPI
    : 'http://localhost:8000/api';  // Development: separate FastAPI server

// Authentication token storage - TEMPORARILY DISABLED
let authToken: string | null = null; // Disabled: localStorage.getItem('auth_token');

// API request helper - TEMPORARILY WITHOUT AUTH
async function apiRequest<T>(
    endpoint: string, 
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    try {
        const response = await fetch(url, {
            method: options.method || 'GET',
            ...options,
        });
        
        if (!response.ok) {
            console.error(`API request failed: ${response.status} ${response.statusText} for ${url}`);
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }
        
        return response.json();
        
    } catch (error) {
        console.error(`API request error for ${url}:`, error);
        throw error;
    }
}

// Authentication
export async function loginUser(username: string, password: string) {
    const response = await apiRequest<{
        access_token: string;
        token_type: string;
        expires_in: number;
        user: any;
    }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
    
    authToken = response.access_token;
    localStorage.setItem('auth_token', authToken);
    
    return response;
}

export async function logoutUser() {
    await apiRequest('/auth/logout', { method: 'POST' });
    authToken = null;
    localStorage.removeItem('auth_token');
}

export async function getUsers() {
    return apiRequest<{ id: number; username: string; display_name: string }[]>('/auth/users');
}

// Portfolio APIs - TEMPORARY: Using test endpoints
export async function getPortfolio(userId: string): Promise<PortfolioResponse> {
    return apiRequest<PortfolioResponse>('/portfolio/test');
}

export async function getPortfolioHistory(userId: string, days: number = 30): Promise<EquityPoint[]> {
    try {
        return await apiRequest<EquityPoint[]>(`/portfolio/history?days=${days}`);
    } catch (error) {
        console.error('Failed to fetch portfolio history:', error);
        return [];
    }
}

export async function getPerformance(userId: string): Promise<PerformanceMetrics> {
    try {
        return await apiRequest<PerformanceMetrics>('/portfolio/test-performance');
    } catch (error) {
        console.error('Failed to fetch performance metrics:', error);
        // Return zeros instead of fake data
        return Promise.resolve({
            totalPL: { value: 0, percentage: 0 },
            todayPL: { value: 0, percentage: 0 },
            winRate: 0,
            profitFactor: 0,
            maxDrawdown: 0,
            sharpeRatio: 0,
            winLossRatio: 0,
            avgProfit: 0,
            avgLoss: 0,
            totalTrades: 0
        });
    }
}

export async function getTrades(userId: string, limit: number = 100): Promise<Trade[]> {
    try {
        const response = await apiRequest<{trades: Trade[], total: number}>('/trades/test');
        return response.trades || [];
    } catch (error) {
        console.error('Failed to fetch trades:', error);
        return [];
    }
}

export async function getActiveTrades(userId: string): Promise<ActiveTrade[]> {
    try {
        return await apiRequest<ActiveTrade[]>('/trades/test-active');
    } catch (error) {
        console.error('Failed to fetch active trades:', error);
        return [];
    }
}

export async function getStatus(): Promise<BotStatus> {
    return apiRequest<BotStatus>('/trades/status'); // This one already works
}

export async function getLogs(userId: string, limit: number = 100): Promise<string[]> {
    return apiRequest<string[]>('/trades/test-logs');
}

export async function getPatternsPerformance(userId: string): Promise<PatternPerformance[]> {
    try {
        return await apiRequest<PatternPerformance[]>('/patterns/performance');
    } catch (error) {
        console.error('Failed to fetch pattern performance:', error);
        return [];
    }
}

export async function getTrainedAssets(userId: string): Promise<TrainedAsset[]> {
    return apiRequest<TrainedAsset[]>('/patterns/test-trained-assets');
}

export async function getAssetDetails(userId: string, symbol: string): Promise<TrainedAssetDetails> {
    return apiRequest<TrainedAssetDetails>(`/analytics/assets/${symbol}/details`);
}

// Training APIs
export async function getAssetRankings(userId: string): Promise<AssetRanking[]> {
    return apiRequest<AssetRanking[]>('/training/asset-rankings');
}

export async function startTraining(
    userId: string, 
    symbols: string[], 
    patterns: string[]
): Promise<{ jobId: string; message: string }> {
    return apiRequest<{ jobId: string; message: string }>('/training/start', {
        method: 'POST',
        body: JSON.stringify({
            symbols,
            patterns,
            timeframes: ['1h', '4h'],
            optimizationMethod: 'bayesian'
        }),
    });
}

export async function getTrainingStatus(userId: string, jobId: string): Promise<TrainingStatus> {
    return apiRequest<TrainingStatus>(`/training/status/${jobId}`);
}

export async function getTrainingJobs(userId: string): Promise<TrainingStatus[]> {
    return apiRequest<TrainingStatus[]>('/training/jobs');
}

export async function getTrainingResults(userId: string, jobId: string): Promise<TrainingResults> {
    return apiRequest<TrainingResults>(`/training/results/${jobId}`);
}

// Exchange APIs
export async function getExchangeConnections(userId: string): Promise<ExchangeConnection[]> {
    return apiRequest<ExchangeConnection[]>('/exchanges/connections');
}

export async function createExchangeConnection(userId: string, connection: ExchangeConnection): Promise<ExchangeConnection> {
    return apiRequest<ExchangeConnection>('/exchanges/connections', {
        method: 'POST',
        body: JSON.stringify(connection),
    });
}

export async function updateExchangeConnection(userId: string, connectionId: number, connection: ExchangeConnection): Promise<ExchangeConnection> {
    return apiRequest<ExchangeConnection>(`/exchanges/connections/${connectionId}`, {
        method: 'PUT',
        body: JSON.stringify(connection),
    });
}

export async function deleteExchangeConnection(userId: string, connectionId: number): Promise<{ message: string }> {
    return apiRequest<{ message: string }>(`/exchanges/connections/${connectionId}`, {
        method: 'DELETE',
    });
}

export async function testExchangeConnection(connection: ExchangeConnection): Promise<{ status: string; message: string }> {
    return apiRequest<{ status: string; message: string }>('/exchanges/test-connection', {
        method: 'POST',
        body: JSON.stringify(connection),
    });
}

// Analytics APIs
export async function getAssetAnalytics(userId: string, symbol: string) {
    return apiRequest(`/analytics/assets/${symbol}`);
}

export async function getWalkForwardResults(userId: string, symbol: string) {
    return apiRequest(`/analytics/walk-forward/${symbol}`);
}

export async function getMarketOverview(userId: string) {
    return apiRequest('/analytics/market-overview');
}

export async function getCorrelationMatrix(userId: string) {
    return apiRequest('/analytics/correlation-matrix');
}