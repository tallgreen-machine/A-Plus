// FIX: Removed self-import which was causing declaration conflicts. This file should define and export types, not import them from itself.
// FIX: Define and export all types used across the application.

export interface Portfolio {
    timestamp: string;
    equity: number;
    cash: number;
}

export interface PortfolioResponse {
    portfolio: Portfolio;
    holdings: any[]; // Define properly if needed
}

export enum TradeDirection {
    BUY = 'BUY',
    SELL = 'SELL',
}

export interface Trade {
    id: number;
    timestamp: string;
    symbol: string;
    direction: TradeDirection;
    quantity: number;
    price: number;
    fill_cost: number;
    pnl?: number;
    strategyName?: string;
    configId?: string;
}

export interface PerformanceMetrics {
    totalPL: { value: number; percentage: number };
    sharpeRatio: number;
    maxDrawdown: number;
    winLossRatio: number;
    avgProfit: number;
    avgLoss: number;
    totalTrades: number;
}

export enum BotStatusState {
    RUNNING = 'RUNNING',
    STOPPED = 'STOPPED',
    FAILED = 'FAILED',
}

export interface BotStatus {
    status: BotStatusState;
}

export enum StrategyStatus {
    ACTIVE = 'ACTIVE',
    PAUSED = 'PAUSED',
    PAPER_TRADING = 'PAPER_TRADING',
}

export interface StrategyPerformance {
    id: string;
    name: string;
    status: StrategyStatus;
    totalPL: number;
    winLossRatio: number;
    totalTrades: number;
    parameters: {
        [key: string]: any;
    };
}

export interface ActiveTrade {
    id: string;
    pair: string; // Renamed from symbol
    exchange: string;
    timeframe: string;
    strategyName: string; // Renamed from patternName
    configId: string;
    direction: TradeDirection;
    entryPrice: number;
    quantity: number;
    currentPL: number;
    takeProfit: number;
    stopLoss: number;
    startTimestamp: string;
    currentPrice?: number;
}

export type TimeframeData = {
    '24h': number;
    '7d': number;
    '30d': number;
    lifetime: number;
};

export interface TrainedAsset {
    symbol: string;
    strategies: {
        strategyId: string;
        initials: string;
        status: StrategyStatus;
        plByTimeframe: TimeframeData;
        plByRegime: {
            'Bull Market': TimeframeData,
            'Bear Market': TimeframeData,
            'Sideways': TimeframeData,
        }
    }[];
    activeCombinations: number;
    totalCombinations: number;
}

export interface ExchangePerformance {
    exchange: string;
    status: StrategyStatus;
    winRate: number;
    avgProfit: number;
    avgLoss: number;
    totalTrades: number;
    totalPL: number;
    avgSlippage: number; // as percentage
    avgFees: number; // as percentage
    avgLatencyMs: number;
}

export interface RegimePerformance {
    regime: 'Bull Market' | 'Bear Market' | 'Sideways';
    status: StrategyStatus; // Master switch for this regime
    exchangePerformance: ExchangePerformance[];
}

export interface StrategyParameters {
    primaryTimeframe: '15m' | '1h' | '4h';
    macroTimeframe: '4h' | '1d';
    primarySignal: {
        lookback?: number;
        threshold?: number;
        rsiPeriod?: number;
        overbought?: number;
        oversold?: number;
    };
    macroConfirmation: {
        trendFilter: 'EMA_200' | 'MACD_Cross' | 'ADX';
        requiredState: 'Above' | 'Positive' | 'Trending';
    };
    riskManagement: {
        riskRewardRatio: number;
        stopLossType: 'ATR' | 'Percentage';
        stopLossValue: number;
    };
}


export interface TrainedAssetDetails {
    symbol: string;
    strategies: {
        id: string;
        name: string;
        status: StrategyStatus;
        parameters: StrategyParameters;
        trainedHistory: string;
        analytics: {
            winRate: number;
            avgProfit: number;
            avgLoss: number;
        };
        regimePerformance: RegimePerformance[];
        recentTrades: Trade[];
    }[];
}

export interface AssetRanking {
    symbol: string;
    suitabilityScore: number;
    volatilityIndex: number;
    liquidityIndex: number;
    dataAvailability: 'Excellent' | 'Good' | 'Fair';
    reason: string;
    estimatedTime: string;
    riskLevel: 'Low' | 'Medium' | 'High';
}

export enum TrainingPhase {
    DATA_COLLECTION = 'Data Collection',
    VIABILITY_ASSESSMENT = 'Viability Assessment',
    TIMEFRAME_TESTING = 'Multi-Timeframe Testing',
    OPTIMIZATION = 'Bayesian Optimization',
    VALIDATION = 'Walk-Forward Validation',
    ROBUSTNESS = 'Robustness & Stress Testing',
    SCORING = 'Final Confidence Scoring',
    COMPLETE = 'Complete',
}

export interface StrategyViability {
    name: string;
    winRate: number;
    signals: number;
    status: 'Viable' | 'Marginal' | 'Not Viable';
}

export interface TrainingStatus {
    jobId: string;
    assetSymbol: string;
    phase: TrainingPhase;
    progress: number;
    message: string;
    eta: string;
    strategyAnalysis?: StrategyViability[];
    currentBest?: {
        winRate: number;
        rr: number;
        score: number;
    };
}

export interface WalkForwardResult {
    window: number;
    trainingPeriod: string;
    validationPeriod: string;
    trainWR: number;
    valWR: number;
    deviation: string;
    status: 'Pass' | 'Fail';
}

// NEW: Nested structure for implementation plan
export interface ExchangeImplementation {
    exchange: string;
    winRate: number;
    signals: number;
    totalPL: number;
    status: 'ACTIVE' | 'PAPER_TRADING';
}

export interface RegimeImplementation {
    regime: 'Bull Market' | 'Bear Market' | 'Sideways';
    exchanges: ExchangeImplementation[];
}

export interface StrategyImplementation {
    strategy: string;
    parameters: StrategyParameters;
    regimes: RegimeImplementation[];
}

export interface TrainingResults {
    jobId: string;
    assetSymbol: string;
    confidenceScore: number;
    recommendation: 'HIGH' | 'MEDIUM' | 'LOW' | 'REJECT';
    strategyViabilitySummary: {
        strategy: string;
        status: 'Enabled' | 'Disabled';
        winRate: number;
        signalsPerYear: number;
        primaryTimeframe: string;
    }[];
    performance: {
        winRate: number;
        avgRR: number;
        signalsPerMonth: number;
        expectedReturn: string;
        maxDrawdown: number;
    };
    aiSummaryReport: string;
    walkForwardValidation: {
        results: WalkForwardResult[];
        stabilityScore: number;
    };
    robustnessTesting: {
        monteCarlo: {
            winRateCI: [number, number];
            avgRR_CI: [number, number];
            interpretation: string;
        };
        regimePerformance: {
            regime: 'Bull Market' | 'Bear Market' | 'Sideways';
            winRate: number;
            signals: number;
        }[];
    };
    implementationPlan: StrategyImplementation[];
    fullReportUrl: string;
    equityCurveUrl: string;
}

// --- NEW: Exchange Onboarding/Settings ---
export enum ExchangeConnectionStatus {
    CONNECTED = 'CONNECTED',
    ERROR = 'ERROR',
}

export interface ExchangeConnection {
    id: string;
    exchangeName: 'Binance' | 'Coinbase' | 'Bybit' | 'Kraken' | 'OKX' | 'KuCoin';
    nickname: string;
    apiKey: string;
    apiSecret: string;
    status: ExchangeConnectionStatus;
}

// --- NEW: Strategy Studio ---
export interface Strategy {
    id: string;
    name: string;
    prompt: string;
}

// --- NEW: Trained Assets from Strategy Studio ---
export interface TrainedConfiguration {
  id: string;
  pair: string;
  exchange: string;
  timeframe: string;
  lifecycle_stage: 'DISCOVERY' | 'VALIDATION' | 'MATURE' | 'DECAY' | 'PAPER';
  strategy_name: string;
  totalPL: number; // Represents historical/backtest P/L
  parameters: {
    pierce_depth?: number;
    rejection_candles?: number;
    volume_spike_threshold?: number;
    reversal_candle_size?: number;
    key_level_lookback?: number;
    stop_distance?: number;
    target_multiple?: number;
  };
  performance: {
    gross_win_rate: number;
    avg_win: number;
    avg_loss: number;
    exchange_fees: number;
    est_slippage: number;
    actual_slippage: number;
    net_profit: number;
    sample_size: number;
  };
  validation: {
    sharpe_ratio: number;
    calmar_ratio: number;
    p_value: number;
    z_score: number;
    stability_score: number;
  };
  regime: {
    current_state: any; // Simplified for now
    regime_probabilities: {
      trending: number;
      ranging: number;
      volatile: number;
    };
  };
  created_at?: string; // ISO timestamp
  job_id?: number; // Training job ID that created this configuration
  training_settings?: {
    optimizer: string;
    n_iterations?: number;
    lookback_days?: number;
    model_version?: string;
    engine_hash?: string;
  };
  isActive?: boolean;
}