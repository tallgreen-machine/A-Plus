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
}

export interface EquityPoint {
    timestamp: string;
    equity: number;
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

export enum PatternStatus {
    ACTIVE = 'ACTIVE',
    PAUSED = 'PAUSED',
    PAPER_TRADING = 'PAPER_TRADING',
}

export interface PatternPerformance {
    id: string;
    name: string;
    status: PatternStatus;
    totalPL: number;
    winLossRatio: number;
    totalTrades: number;
    parameters: {
        [key: string]: any;
    };
}

export interface ActiveTrade {
    id: string;
    symbol: string;
    direction: TradeDirection;
    entryPrice: number;
    quantity: number;
    currentPL: number;
    takeProfit: number;
    stopLoss: number;
    patternName: string;
    startTimestamp: string;
    currentPrice?: number;
}

export interface TrainedAsset {
    symbol: string;
    patterns: {
        patternId: string;
        initials: string;
        totalPL: number;
        status: PatternStatus;
    }[];
}

export interface ExchangePerformance {
    exchange: string;
    status: PatternStatus;
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
    status: PatternStatus; // Master switch for this regime
    exchangePerformance: ExchangePerformance[];
}

export interface PatternParameters {
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
    patterns: {
        id: string;
        name: string;
        status: PatternStatus;
        parameters: PatternParameters;
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

export interface PatternViability {
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
    patternAnalysis?: PatternViability[];
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

export interface PatternImplementation {
    pattern: string;
    parameters: PatternParameters;
    regimes: RegimeImplementation[];
}

export interface TrainingResults {
    jobId: string;
    assetSymbol: string;
    confidenceScore: number;
    recommendation: 'HIGH' | 'MEDIUM' | 'LOW' | 'REJECT';
    patternViabilitySummary: {
        pattern: string;
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
    implementationPlan: PatternImplementation[];
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