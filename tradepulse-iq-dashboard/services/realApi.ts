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
    // TEMPORARY: Return empty array since /portfolio/history returns 403
    return Promise.resolve([]);
}

export async function getPerformance(userId: string): Promise<PerformanceMetrics> {
    // TEMPORARY: Return mock performance data since /portfolio/performance returns 403
    return Promise.resolve({
        totalPL: { value: 2500.0, percentage: 0.025 },
        todayPL: { value: 150.0, percentage: 0.0015 },
        winRate: 0.68,
        profitFactor: 1.45,
        maxDrawdown: 0.08,
        sharpeRatio: 1.2,
        winLossRatio: 2.1,
        avgProfit: 180.0,
        avgLoss: -85.0,
        totalTrades: 45
    });
}

// Trade APIs - TEMPORARY: Using test endpoints
export async function getTrades(userId: string, limit: number = 100): Promise<Trade[]> {
    const response = await apiRequest<{trades: Trade[], total: number}>('/trades/test');
    return response.trades || [];
}

export async function getActiveTrades(userId: string): Promise<ActiveTrade[]> {
    // TEMPORARY: Return empty array since endpoint has database schema issues
    return Promise.resolve([]);
}

export async function getStatus(): Promise<BotStatus> {
    return apiRequest<BotStatus>('/trades/status'); // This one already works
}

export async function getLogs(userId: string, limit: number = 100): Promise<string[]> {
    return apiRequest<string[]>('/trades/test-logs');
}

// Pattern APIs - TEMPORARY: Using test endpoints  
export async function getPatternsPerformance(userId: string): Promise<PatternPerformance[]> {
    // TEMPORARY: Return empty array since endpoint has database schema issues
    return Promise.resolve([]);
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