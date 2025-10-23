/**
 * Real API Service Layer for TradePulse V2 Dashboard
 * Connects to the FastAPI backend instead of using mock data
 * 
 * Maps frontend API calls to backend REST endpoints:
 * - GET /api/portfolio/* → Portfolio data
 * - GET /api/trades/* → Trade history & active trades
 * - GET /api/strategies/* → Strategy performance & configurations
 * - GET /api/training/configurations/* → Trained configurations
 * - GET /api/exchanges/* → Exchange connections
 */

import type {
  PortfolioResponse,
  Trade,
  PerformanceMetrics,
  BotStatus,
  StrategyPerformance,
  ActiveTrade,
  TrainedConfiguration,
  Strategy,
  ExchangeConnection,
} from '../types';

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const DEFAULT_USER_ID = 'user_1'; // TODO: Replace with actual auth system

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `API error: ${response.status} ${response.statusText}`
      );
    }

    return await response.json();
  } catch (error) {
    console.error(`API request failed: ${endpoint}`, error);
    throw error;
  }
}

/**
 * Convert snake_case backend keys to camelCase frontend keys
 */
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Recursively convert all object keys from snake_case to camelCase
 */
function convertKeysToCamelCase<T>(obj: any): T {
  if (obj === null || obj === undefined) return obj;
  
  if (Array.isArray(obj)) {
    return obj.map(item => convertKeysToCamelCase(item)) as any;
  }
  
  if (typeof obj === 'object' && obj.constructor === Object) {
    return Object.keys(obj).reduce((acc, key) => {
      const camelKey = toCamelCase(key);
      acc[camelKey] = convertKeysToCamelCase(obj[key]);
      return acc;
    }, {} as any);
  }
  
  return obj;
}

/**
 * Simulate delay for consistency with mock API (optional, can be removed)
 */
async function delay(ms: number = 100): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================================
// Portfolio APIs
// ============================================================================

export const getPortfolio = async (userId: string = DEFAULT_USER_ID): Promise<PortfolioResponse> => {
  const data = await apiFetch<any>('/api/portfolio');
  return convertKeysToCamelCase<PortfolioResponse>(data);
};

// ============================================================================
// Trades APIs
// ============================================================================

export const getTrades = async (userId: string = DEFAULT_USER_ID): Promise<Trade[]> => {
  const data = await apiFetch<any[]>('/api/trades');
  return convertKeysToCamelCase<Trade[]>(data);
};

export const getActiveTrades = async (userId: string = DEFAULT_USER_ID): Promise<ActiveTrade[]> => {
  const data = await apiFetch<any[]>('/api/trades/active');
  return convertKeysToCamelCase<ActiveTrade[]>(data);
};

export const getLogs = async (userId: string = DEFAULT_USER_ID): Promise<string[]> => {
  return await apiFetch<string[]>('/api/trades/logs');
};

export const getStatus = async (): Promise<BotStatus> => {
  const data = await apiFetch<any>('/api/trades/status');
  return convertKeysToCamelCase<BotStatus>(data);
};

// ============================================================================
// Performance APIs
// ============================================================================

export const getPerformance = async (userId: string = DEFAULT_USER_ID): Promise<PerformanceMetrics> => {
  const data = await apiFetch<any>('/api/portfolio/performance');
  return convertKeysToCamelCase<PerformanceMetrics>(data);
};

// ============================================================================
// Strategy Performance APIs (V2: "Strategy" not "Pattern")
// ============================================================================

/**
 * Get strategy performance metrics
 * Maps to backend's strategy performance endpoint
 */
export const getStrategiesPerformance = async (userId: string = DEFAULT_USER_ID): Promise<StrategyPerformance[]> => {
  const data = await apiFetch<any[]>('/api/strategies/performance');
  return convertKeysToCamelCase<StrategyPerformance[]>(data);
};

// Alias for backward compatibility (if getPatternsPerformance is used anywhere)
export const getPatternsPerformance = getStrategiesPerformance;

// ============================================================================
// Trained Configurations APIs (V2: replaces "Trained Assets")
// ============================================================================

/**
 * Get all trained configurations from the database
 * This is the V2 endpoint - uses trained_configurations table
 */
export const getTrainedConfigurations = async (
  userId: string = DEFAULT_USER_ID,
  filters?: {
    strategy?: string;
    exchange?: string;
    pair?: string;
    status?: string;
    is_active?: boolean;
  }
): Promise<TrainedConfiguration[]> => {
  // Build query parameters
  const params = new URLSearchParams();
  if (filters?.strategy) params.append('strategy', filters.strategy);
  if (filters?.exchange) params.append('exchange', filters.exchange);
  if (filters?.pair) params.append('pair', filters.pair);
  if (filters?.status) params.append('status', filters.status);
  if (filters?.is_active !== undefined) params.append('is_active', String(filters.is_active));

  const queryString = params.toString();
  const endpoint = `/api/training/configurations${queryString ? `?${queryString}` : ''}`;
  
  const data = await apiFetch<any[]>(endpoint);
  return convertKeysToCamelCase<TrainedConfiguration[]>(data);
};

/**
 * Get single trained configuration by ID
 */
export const getTrainedConfiguration = async (configurationId: string): Promise<TrainedConfiguration> => {
  const data = await apiFetch<any>(`/api/training/configurations/${configurationId}`);
  return convertKeysToCamelCase<TrainedConfiguration>(data);
};

/**
 * Activate a trained configuration
 */
export const activateConfiguration = async (configurationId: string): Promise<void> => {
  await apiFetch(`/api/training/configurations/${configurationId}/activate`, {
    method: 'POST',
  });
};

/**
 * Deactivate a trained configuration
 */
export const deactivateConfiguration = async (configurationId: string): Promise<void> => {
  await apiFetch(`/api/training/configurations/${configurationId}/deactivate`, {
    method: 'POST',
  });
};

/**
 * Get configurations summary statistics
 */
export const getConfigurationsSummary = async (): Promise<{
  total: number;
  active: number;
  byStatus: Record<string, number>;
  byStrategy: Record<string, number>;
}> => {
  const data = await apiFetch<any>('/api/training/configurations/stats/summary');
  return convertKeysToCamelCase(data);
};

// ============================================================================
// Server Monitoring
// ============================================================================

export const getServerLatency = async (): Promise<number> => {
  const startTime = performance.now();
  await apiFetch('/health');
  const endTime = performance.now();
  return Math.round(endTime - startTime);
};

// ============================================================================
// Training Simulation (placeholder - needs backend implementation)
// ============================================================================

// Mock data for trading pairs - used by StrategyStudio component
export const mockTrainedAssetsList = [
  // TIER 1
  'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT',
  'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'NEAR/USDT', 'TRX/USDT', 'ARB/USDT', 'OP/USDT', 'INJ/USDT', 'TIA/USDT', 'SUI/USDT',
  'ETH/BTC', 'SOL/BTC', 'BNB/BTC', 'ADA/BTC', 'LINK/ETH',
  // TIER 2
  'DOGE/USDT', 'SHIB/USDT', 'TON/USDT', 'APT/USDT', 'STX/USDT', 'FIL/USDT', 'IMX/USDT', 'VET/USDT', 'HBAR/USDT', 'AAVE/USDT',
  'MKR/USDT', 'GRT/USDT', 'ALGO/USDT', 'ICP/USDT', 'ETC/USDT', 'XLM/USDT', 'RUNE/USDT', 'FTM/USDT', 'SAND/USDT', 'MANA/USDT',
  'AXS/USDT', 'CRV/USDT', 'SNX/USDT', 'LDO/USDT', 'THETA/USDT', 'EOS/USDT', 'EGLD/USDT', 'KCS/USDT', 'XMR/USDT', 'FLOW/USDT',
  'APE/USDT', 'CHZ/USDT', 'GMT/USDT', 'QNT/USDT', 'KAVA/USDT', 'ZIL/USDT', 'ENJ/USDT', '1INCH/USDT', 'BAT/USDT',
];

export const runTrainingSimulation = async (
  params: {
    strategy: string;
    exchange: string;
    pair: string;
    timeframe: string;
    startDate: string;
    endDate: string;
  }
): Promise<{
  id: string;
  status: 'running' | 'completed' | 'failed';
  progress: number;
  results?: any;
}> => {
  // TODO: Implement backend endpoint for training simulations
  // For now, return a placeholder
  console.warn('runTrainingSimulation: Backend endpoint not yet implemented');
  
  return {
    id: `sim_${Date.now()}`,
    status: 'running',
    progress: 0,
  };
};

// ============================================================================
// Configuration Management
// ============================================================================

/**
 * Update active configurations
 * This sets which configurations should be actively trading
 */
export const updateActiveConfigs = async (configIds: string[]): Promise<void> => {
  // First deactivate all, then activate selected ones
  // TODO: This should be a single atomic backend endpoint
  console.warn('updateActiveConfigs: Implementing as sequential activate/deactivate calls');
  
  // Get all configurations
  const allConfigs = await getTrainedConfigurations();
  
  // Deactivate all that are not in configIds
  const deactivatePromises = allConfigs
    .filter(config => config.isActive && !configIds.includes(config.id))
    .map(config => deactivateConfiguration(config.id));
  
  // Activate all in configIds
  const activatePromises = configIds.map(id => activateConfiguration(id));
  
  await Promise.all([...deactivatePromises, ...activatePromises]);
};

// ============================================================================
// Strategy Management (V2: "Strategy" configuration, not trading strategy)
// ============================================================================

/**
 * Get user's strategy configurations (from strategies table, not trained_configurations)
 * Note: This is for strategy definitions/templates, not trained configurations
 */
export const getStrategies = async (userId: string = DEFAULT_USER_ID): Promise<Strategy[]> => {
  // TODO: Backend endpoint needed - strategies table CRUD
  // For now, return empty array
  console.warn('getStrategies: Backend endpoint not yet implemented for strategies table');
  return [];
};

/**
 * Save strategy configuration
 */
export const saveStrategy = async (
  userId: string,
  strategy: Omit<Strategy, 'id'> & { id?: string }
): Promise<Strategy> => {
  // TODO: Backend endpoint needed
  console.warn('saveStrategy: Backend endpoint not yet implemented');
  throw new Error('saveStrategy endpoint not implemented');
};

/**
 * Delete strategy configuration
 */
export const deleteStrategy = async (userId: string, strategyId: string): Promise<void> => {
  // TODO: Backend endpoint needed
  console.warn('deleteStrategy: Backend endpoint not yet implemented');
  throw new Error('deleteStrategy endpoint not implemented');
};

// ============================================================================
// Exchange Connection APIs
// ============================================================================

export const getExchangeConnections = async (userId: string = DEFAULT_USER_ID): Promise<ExchangeConnection[]> => {
  const data = await apiFetch<any[]>('/api/exchanges/connections');
  return convertKeysToCamelCase<ExchangeConnection[]>(data);
};

export const saveExchangeConnection = async (
  userId: string,
  connection: Omit<ExchangeConnection, 'id' | 'status'> & { id?: string }
): Promise<ExchangeConnection> => {
  const endpoint = connection.id 
    ? `/api/exchanges/connections/${connection.id}`
    : '/api/exchanges/connections';
  
  const method = connection.id ? 'PUT' : 'POST';
  
  // Convert camelCase to snake_case for backend
  const snakeCaseData = {
    exchange_name: connection.exchangeName,
    nickname: connection.nickname,
    api_key: connection.apiKey,
    api_secret: connection.apiSecret,
    ...(connection.id && { id: connection.id }),
  };
  
  const data = await apiFetch<any>(endpoint, {
    method,
    body: JSON.stringify(snakeCaseData),
  });
  
  return convertKeysToCamelCase<ExchangeConnection>(data);
};

export const deleteExchangeConnection = async (
  userId: string,
  connectionId: string
): Promise<void> => {
  await apiFetch(`/api/exchanges/connections/${connectionId}`, {
    method: 'DELETE',
  });
};

/**
 * Test exchange connection
 */
export const testExchangeConnection = async (connectionId: string): Promise<{
  success: boolean;
  message: string;
  balance?: Record<string, number>;
}> => {
  const data = await apiFetch<any>(`/api/exchanges/connections/${connectionId}/test-connection`, {
    method: 'POST',
  });
  return convertKeysToCamelCase(data);
};
