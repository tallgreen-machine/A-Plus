
// FIX: Import enums and types from the dedicated types file.
import {
    TradeDirection,
    BotStatusState,
    PatternStatus,
    TrainingPhase,
    ExchangeConnectionStatus,
} from '../types';
import type {
    PortfolioResponse,
    Trade,
    PerformanceMetrics,
    BotStatus,
    PatternPerformance,
    ActiveTrade,
    TrainedAsset,
    TrainedAssetDetails,
    AssetRanking,
    TrainingStatus,
    TrainingResults,
    RegimePerformance,
    ExchangePerformance,
    PatternParameters,
    PatternImplementation,
    ExchangeConnection,
    TimeframeData,
    Strategy,
    TrainedConfiguration,
} from '../types';

// FIX: Hoisted helper functions to prevent "used before declaration" error.
const generateRandomFloat = (min: number, max: number, decimals: number = 2) => {
    return parseFloat((Math.random() * (max - min) + min).toFixed(decimals));
};

const generateRandomInt = (min: number, max: number) => {
    return Math.floor(Math.random() * (max - min + 1)) + min;
};

const delay = (ms: number) => new Promise(res => setTimeout(res, ms));


// --- MOCK DATA STORE ---

const users = ['user1', 'user2'];
const exchanges = ['Binance', 'Coinbase', 'Bybit', 'Kraken', 'OKX', 'KuCoin'];
const regimes = ['Bull Market', 'Bear Market', 'Sideways'] as const;

// NEW: Global server latency simulation
let serverLatency = generateRandomInt(40, 120);

// MODIFIED: Start with empty, dynamic stores
let mockTrainedConfigurations: TrainedConfiguration[] = [];
let mockActiveTrades: ActiveTrade[] = [];


const mockData: { [userId: string]: any } = {};

const generatePatternParameters = (patternName: string): PatternParameters => {
    const primaryTimeframe = (['15m', '1h'] as const)[generateRandomInt(0,1)];
    const macroTimeframe = (['4h', '1d'] as const)[generateRandomInt(0,1)];

    let primarySignal: PatternParameters['primarySignal'] = {};
    if (patternName.includes('Reversal')) {
        primarySignal = {
            rsiPeriod: generateRandomInt(12, 18),
            overbought: generateRandomInt(70, 80),
            oversold: generateRandomInt(20, 30),
        }
    } else {
        primarySignal = {
            lookback: generateRandomInt(20, 50),
            threshold: generateRandomFloat(1.5, 2.5),
        }
    }

    return {
        primaryTimeframe,
        macroTimeframe,
        primarySignal,
        macroConfirmation: {
            trendFilter: (['EMA_200', 'MACD_Cross', 'ADX'] as const)[generateRandomInt(0, 2)],
            requiredState: (['Above', 'Positive', 'Trending'] as const)[generateRandomInt(0, 2)],
        },
        riskManagement: {
            riskRewardRatio: generateRandomFloat(1.5, 3.0),
            stopLossType: (['ATR', 'Percentage'] as const)[generateRandomInt(0, 1)],
            stopLossValue: generateRandomFloat(1, 3),
        }
    }
}

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

// --- MOCK DATA INITIALIZATION ---
const initializeUserMockData = (userId: string) => {
    let lastEquity = generateRandomFloat(95000, 105000);
    const portfolioHistory = Array.from({ length: 30 }, (_, i) => {
        const change = generateRandomFloat(-0.02, 0.02);
        lastEquity *= (1 + change);
        return {
            timestamp: new Date(Date.now() - (30 - i) * 24 * 60 * 60 * 1000).toISOString(),
            equity: lastEquity,
            cash: lastEquity * 0.4
        };
    });

    mockData[userId] = {
        portfolioHistory,
        trades: Array.from({ length: 200 }, (_, i) => {
            const direction = Math.random() > 0.5 ? TradeDirection.BUY : TradeDirection.SELL;
            const entryPrice = generateRandomFloat(20000, 70000);
            const quantity = generateRandomFloat(0.01, 0.5);
            const pnl = generateRandomFloat(-500, 1000);
            return {
                id: i,
                timestamp: new Date(Date.now() - generateRandomInt(10000, 1000 * 60 * 60 * 24 * 7)).toISOString(),
                symbol: 'BTC/USDT',
                direction,
                quantity,
                price: entryPrice,
                fill_cost: entryPrice * quantity,
                pnl: pnl,
                configId: `cfg-${generateRandomInt(1, 10)}`,
                strategyName: ['MeanReversion', 'TrendFollow', 'Breakout'][generateRandomInt(0, 2)],
            };
        }),
        logs: ["INFO: Bot initialized.", "DEBUG: Loading strategies.", "WARN: High market volatility detected."],
        performance: {
            totalPL: { value: 2345.67, percentage: 0.0234 },
            sharpeRatio: 1.87,
            maxDrawdown: 0.08,
            winLossRatio: 1.5,
            avgProfit: 350.21,
            avgLoss: -233.45,
            totalTrades: 200,
        },
        patterns: [],
        exchangeConnections: [],
        strategies: [],
    };
};

users.forEach(initializeUserMockData);

// Active configs for simulation
let activeConfigIds = new Set<string>();

const updateData = () => {
    // Update server latency
    serverLatency = Math.max(20, Math.min(250, serverLatency + generateRandomInt(-15, 15)));

    // Update portfolio for all users
    users.forEach(userId => {
        const user = mockData[userId];
        const last = user.portfolioHistory[user.portfolioHistory.length - 1];
        const newEquity = last.equity * (1 + generateRandomFloat(-0.005, 0.005));
        user.portfolioHistory.push({
            timestamp: new Date().toISOString(),
            equity: newEquity,
            cash: newEquity * 0.4
        });
        if (user.portfolioHistory.length > 100) user.portfolioHistory.shift();

        user.performance.totalPL.value += (newEquity - last.equity);
    });

    // Update active trades (IMMUTABLE UPDATE)
    mockActiveTrades = mockActiveTrades.map(trade => {
        const priceChange = generateRandomFloat(-0.001, 0.001);
        const newCurrentPrice = (trade.currentPrice ?? trade.entryPrice) * (1 + priceChange);
        const pnlDirection = trade.direction === TradeDirection.BUY ? 1 : -1;
        const newCurrentPL = (newCurrentPrice - trade.entryPrice) * trade.quantity * pnlDirection;

        return {
            ...trade,
            currentPrice: newCurrentPrice,
            currentPL: newCurrentPL,
        };
    });

    // Chance to close an existing trade
    if (mockActiveTrades.length > 0 && Math.random() < 0.05) { // 5% chance
        const tradeToClose = mockActiveTrades.shift()!;
        const closedTrade: Trade = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            symbol: tradeToClose.pair,
            direction: tradeToClose.direction,
            quantity: tradeToClose.quantity,
            price: tradeToClose.currentPrice ?? tradeToClose.entryPrice,
            fill_cost: tradeToClose.entryPrice * tradeToClose.quantity,
            pnl: tradeToClose.currentPL,
            configId: tradeToClose.configId,
            strategyName: tradeToClose.strategyName,
        };
        mockData['user1'].trades.unshift(closedTrade);
    }
    
    // Chance to open a new trade
    const tradableConfigs = mockTrainedConfigurations.filter(c =>
        activeConfigIds.has(c.id) &&
        ['MATURE', 'VALIDATION', 'DECAY'].includes(c.lifecycle_stage)
    );
    if (tradableConfigs.length > 0 && Math.random() < 0.5) { // 50% chance
        const config = tradableConfigs[generateRandomInt(0, tradableConfigs.length - 1)];
        const entryPrice = generateRandomFloat(3000, 4000);
        const stopLoss = entryPrice * (1 - generateRandomFloat(0.01, 0.03));
        const takeProfit = entryPrice * (1 + generateRandomFloat(0.02, 0.05));

        const newTrade: ActiveTrade = {
            id: `trade-${Date.now()}`,
            pair: config.pair,
            exchange: config.exchange,
            timeframe: config.timeframe,
            strategyName: config.strategy_name,
            configId: config.id,
            direction: Math.random() > 0.5 ? TradeDirection.BUY : TradeDirection.SELL,
            entryPrice,
            quantity: generateRandomFloat(0.1, 2),
            currentPL: 0,
            takeProfit,
            stopLoss,
            startTimestamp: new Date().toISOString(),
            currentPrice: entryPrice,
        };
        mockActiveTrades.push(newTrade);
    }

    // Chance to update a config's metrics
    if (mockTrainedConfigurations.length > 0 && Math.random() < 0.2) {
        const configToUpdate = mockTrainedConfigurations[generateRandomInt(0, mockTrainedConfigurations.length - 1)];
        configToUpdate.performance.net_profit += generateRandomFloat(-0.001, 0.001);
        configToUpdate.performance.gross_win_rate += generateRandomFloat(-0.0005, 0.0005);
        configToUpdate.validation.sharpe_ratio += generateRandomFloat(-0.01, 0.01);
    }
};

setInterval(updateData, 1000);

// --- API FUNCTIONS ---
export const getPortfolio = async (userId: string): Promise<PortfolioResponse> => {
    await delay(generateRandomInt(50, 200));
    const history = mockData[userId].portfolioHistory;
    return { portfolio: history[history.length - 1], holdings: [] };
};

export const getTrades = async (userId: string): Promise<Trade[]> => {
    await delay(generateRandomInt(50, 200));
    return [...mockData[userId].trades].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
};

export const getLogs = async (userId: string): Promise<string[]> => {
    await delay(generateRandomInt(50, 100));
    return mockData[userId].logs;
};

export const getPerformance = async (userId: string): Promise<PerformanceMetrics> => {
    await delay(generateRandomInt(50, 150));
    return mockData[userId].performance;
};

export const getStatus = async (): Promise<BotStatus> => {
    await delay(50);
    return { status: BotStatusState.RUNNING };
};

export const getPatternsPerformance = async (userId: string): Promise<PatternPerformance[]> => {
    await delay(generateRandomInt(100, 300));
    return mockData[userId].patterns;
};

export const getActiveTrades = async (userId: string): Promise<ActiveTrade[]> => {
    await delay(generateRandomInt(50, 150));
    return [...mockActiveTrades];
};

export const getTrainedConfigurations = async (userId: string): Promise<TrainedConfiguration[]> => {
    await delay(generateRandomInt(200, 500));
    return [...mockTrainedConfigurations];
};

export const getServerLatency = async (): Promise<number> => {
    await delay(generateRandomInt(10, 50));
    return serverLatency;
};

export const runTrainingSimulation = async (
    pair: string,
    strategies: Strategy[],
    onProgress: (result: TrainedConfiguration) => void
): Promise<TrainedConfiguration[]> => {
    const results: TrainedConfiguration[] = [];
    const timeframes = ['5m', '15m', '1h', '4h'];

    for (const strategy of strategies) {
        for (const exchange of exchanges.slice(0, generateRandomInt(2, 4))) {
            for (const timeframe of timeframes) {
                await delay(generateRandomInt(50, 150)); // Simulate work
                const sampleSize = generateRandomInt(50, 500);
                const grossWinRate = generateRandomFloat(30, 75);
                const netProfit = (grossWinRate / 100) - (1 - grossWinRate / 100) - generateRandomFloat(0.05, 0.15); // WR - LR - fees/slippage
                
                const newConfig: TrainedConfiguration = {
                    id: `cfg-${pair}-${exchange}-${timeframe}-${strategy.id}-${Date.now()}`,
                    pair,
                    exchange,
                    timeframe,
                    lifecycle_stage: (['DISCOVERY', 'VALIDATION', 'MATURE'] as const)[generateRandomInt(0, 2)],
                    strategy_name: strategy.name,
                    totalPL: generateRandomFloat(500, 25000) * (netProfit > 0 ? 1 : -1),
                    parameters: {
                        stop_distance: generateRandomFloat(1, 3),
                        target_multiple: generateRandomFloat(1.5, 4),
                    },
                    performance: {
                        gross_win_rate: grossWinRate,
                        avg_win: generateRandomFloat(100, 500),
                        avg_loss: generateRandomFloat(-80, -400),
                        exchange_fees: 0.001,
                        est_slippage: 0.0005,
                        actual_slippage: 0.0006,
                        net_profit: netProfit,
                        sample_size: Math.random() < 0.1 ? 0 : sampleSize, // 10% chance for 0 trades
                    },
                    validation: {
                        sharpe_ratio: generateRandomFloat(0.5, 2.5),
                        calmar_ratio: generateRandomFloat(0.8, 3.0),
                        p_value: generateRandomFloat(0.01, 0.1),
                        z_score: generateRandomFloat(-3, 3),
                        stability_score: generateRandomFloat(60, 95),
                    },
                    regime: {
                        current_state: 'Ranging',
                        regime_probabilities: {
                            trending: generateRandomFloat(0.1, 0.8),
                            ranging: generateRandomFloat(0.1, 0.8),
                            volatile: generateRandomFloat(0.1, 0.8),
                        },
                    },
                };
                onProgress(newConfig);
                if (newConfig.performance.net_profit > -0.2) { // Allow slightly negative to pass
                    results.push(newConfig);
                }
            }
        }
    }
    mockTrainedConfigurations.push(...results);
    return results;
};

export const updateActiveConfigs = (configIds: string[]) => {
    activeConfigIds = new Set(configIds);
    console.log("Backend active configs updated:", activeConfigIds);
};

// --- SETTINGS APIS ---

export const getStrategies = async (userId: string): Promise<Strategy[]> => {
    if (!mockData[userId].strategies || mockData[userId].strategies.length === 0) {
        mockData[userId].strategies = [
            { 
                id: 'strat-1', 
                name: 'LIQUIDITY SWEEP - FULL DISCOVERY V3', 
                prompt: `Objective: Execute a full-stack, combinatorial discovery task to identify all profitable configurations for the "LIQUIDITY SWEEP V3" trading pattern based on the provided runtime inputs.

Runtime Inputs: Target Pairs: [USER_PROVIDED_PAIRS_FROM_INPUT] Target Exchanges: [DYNAMICALLY_FETCH_CONNECTED_EXCHANGES]

Core Iteration Matrix: You must iterate through every possible combination of the following variables: Exchanges: Use the provided [Target Exchanges] list. Trading Pairs: Use the provided [Target Pairs] list. Regimes: Use the output from the [ENSEMBLE CLASSIFIER - multiple timeframes]. Timeframes: 1m, 5m, 15m, 1h, 4h, 1d

Data & Optimization Mandate: For each unique combination (e.g., Binance, BTC/USDT, 1h), you must connect to that exchange's API (Binance) and pull the necessary historical market data (OHLCV) for that pair and timeframe (BTC/USDT, 1h). This data, combined with alternative data streams, is the required input for the discovery task.

Discovery Task (Per Combination): Using the historical data pulled for the combination, run an optimization (testing the specified ranges) to discover the ideal parameters that maximize NET_PROFIT.

Parameters to Discover: pierce_depth (test 0.05% to 0.5%) rejection_candles (test 1 to 5) volume_spike_threshold (test 1.5x to 5x) reversal_candle_size (test 0.5 to 2.0 ATR) key_level_lookback (test 20 to 200 periods) stop_distance (test 0.5 to 2.0 ATR) target_multiple (test 1.5:1 to 4:1) min_stop_density_score (test 0.5 to 1.0) max_spread_tolerance (test 1 to 10 bps)

Validation, Governance, & Lifecycle: For each configuration, calculate all metrics and assign a status based on the "Lifecycle Stage Rules". Continuously monitor all configurations and apply "Aggressive Decay Rules" and "Circuit Breakers" as defined.

Lifecycle Stage Rules:

DISCOVERY: sample < 30, position = 0.25x, latency_priority = low

VALIDATION: sample 30-100, position = 0.5x, p_value < 0.05

MATURE: sample > 100, position = 1.0x, sharpe > 1.5, adverse_selection < 0.3

DECAY: performance_degradation > -20% OR death_signal triggered

PAPER: NET_PROFIT < 0 OR sharpe < 0.5 OR fill_rate < 0.7

Aggressive Decay Rules:

if rolling_30d_sharpe < 0.5 * lifetime_sharpe: -> IMMEDIATE move to PAPER

if adverse_selection_score > 0.6: -> REDUCE position 50%

if death_signals_count >= 2: -> DECAY status

if fill_rate < 0.7: -> PAUSE trading

Circuit Breakers:

max_daily_loss: X

max_correlation_spike: X

unusual_market_threshold: X

latency_threshold_ms: X

consecutive_losses_limit: N

max_adverse_selection: X

regime_break_threshold: X

Output Requirement: For every discovered configuration (all statuses), generate and output a single JSON object. This object must precisely follow the "V3 Universal Discovery Template" below, with all placeholders [...] populated with the actual discovered parameters, calculated metrics, and metadata.

Required JSON Output Template (LIQUIDITY SWEEP V3) {"pair":"[TRADING_PAIR]","pattern":"LIQUIDITY SWEEP V3","configurations":[{"id":"[DYNAMICALLY_GENERATED_ID]","status":"[DISCOVERY/VALIDATION/MATURE/DECAY/PAPER]","metadata":{"model_version":"[MODEL_VERSION]","discovery_date":"[DISCOVERY_TIMESTAMP]","engine_hash":"[ENGINE_HASH]","runtime_env":"[RUNTIME_ENVIRONMENT]"},"context":{"pair":"[TRADING_PAIR]","exchange":"[EXCHANGE_NAME]","timeframe":"[TIMEFRAME_VALUE]"},"parameters":{"pierce_depth":"[val]","rejection_candles":"[val]","volume_spike_threshold":"[val]","reversal_candle_size":"[val]","key_level_lookback":"[val]","stop_distance":"[val]","target_multiple":"[val]","min_stop_density_score":"[val]","max_spread_tolerance":"[val]"},"performance":{"gross_WR":"[val]","avg_win":"[val]","avg_loss":"[val]","exchange_fees":"[val]","est_slippage":"[val]","actual_slippage":"[val]","NET_PROFIT":"[val]","sample_size":"[val]"},"statistical_validation":{"sharpe_ratio":"[val]","calmar_ratio":"[val]","sortino_ratio":"[val]","p_value":"[val]","z_score":"[val]","monte_carlo_var":"[val]","stability_score":"[val]","drawdown_duration":"[val]","trade_clustering":"[val]","rolling_30d_sharpe":"[val]","lifetime_sharpe_ratio":"[val]"},"execution_metrics":{"fill_rate":"[val]","partial_fill_rate":"[val]","time_to_fill_ms":"[val]","slippage_vs_mid_bps":"[val]","adverse_selection_score":"[val]","post_trade_drift_1m":"[val]","post_trade_drift_5m":"[val]","rejection_rate":"[val]"},"ensemble_regime_classification":{"regime_models":{"model_1h":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_4h":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_1d":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_volatility":{"type":"[val]","weight":"[val]","prediction":"[val]"}},"final_regime_probability":{"trending":"[val]","ranging":"[val]","volatile":"[val]"},"regime_transition_probability":"[val]","regime_stability_score":"[val]"},"alternative_data_signals":{"order_flow_imbalance":"[val]","options_flow":{"put_call_ratio":"[val]","gamma_exposure":"[val]","dealer_positioning":"[val]"},"funding_rate":"[val]","perpetual_basis":"[val]","social_sentiment":{"twitter_score":"[val]","reddit_mentions":"[val]","sentiment_velocity":"[val]"},"whale_activity_score":"[val]","exchange_inflow_outflow":"[val]"},"adversarial_analysis":{"adversarial_score":"[val]","trap_probability":"[val]","smart_money_alignment":"[val]","similar_patterns_detected":"[val]","competitor_activity_level":"[val]","unusual_mm_behavior":"[val]","spoofing_detected":"[val]"},"risk_allocation":{"kelly_fraction":"[val]","correlation_adjusted_weight":"[val]","regime_adjusted_size":"[val]","max_position_size":"[val]","current_allocation":"[val]","var_95":"[val]","cvar_95":"[val]"},"market_microstructure":{"avg_spread_bps":"[val]","book_depth_ratio":"[val]","book_imbalance":"[val]","tick_size_impact":"[val]","maker_rebate":"[val]","taker_fee":"[val]","level2_depth_score":"[val]","microstructure_noise":"[val]"},"pattern_health":{"months_since_discovery":"[val]","performance_degradation":"[val]","degradation_velocity":"[val]","death_signals":{"volume_profile_changed":"[val]","new_algo_detected":"[val]","correlation_spike":"[val]","sharpe_below_50pct":"[val]","unusual_fill_pattern":"[val]","regime_break":"[val]"},"death_signal_count":"[val]","resurrection_score":"[val]","correlation_to_other_patterns":{"[pattern_name]":"[val]"}},"circuit_breakers":{"max_daily_loss":"[val]","max_correlation_spike":"[val]","unusual_market_threshold":"[val]","latency_threshold_ms":"[val]","consecutive_losses_limit":"[val]","max_adverse_selection":"[val]","regime_break_threshold":"[val]"},"meta_learning_outputs":{"pattern_failure_predictors":"[list]","optimal_market_conditions":"[desc]","edge_expiration_estimate":"[val]","recommended_alternatives":"[list]"}}]}` 
            },
            { 
                id: 'strat-2', 
                name: 'CAPITULATION REVERSAL - FULL DISCOVERY V3', 
                prompt: `Objective: Execute a full-stack, combinatorial discovery task to identify all profitable configurations for the "CAPITULATION REVERSAL V3" trading pattern based on the provided runtime inputs.

Runtime Inputs: Target Pairs: [USER_PROVIDED_PAIRS_FROM_INPUT] Target Exchanges: [DYNAMICALLY_FETCH_CONNECTED_EXCHANGES]

Core Iteration Matrix: You must iterate through every possible combination of the following variables: Exchanges: Use the provided [Target Exchanges] list. Trading Pairs: Use the provided [Target Pairs] list. Regimes: Use the output from the [ENSEMBLE CLASSIFIER - multiple timeframes]. Timeframes: 1m, 5m, 15m, 1h, 4h, 1d

Data & Optimization Mandate: For each unique combination (e.g., Kraken, ETH/USDT, 5m), you must connect to that exchange's API (Kraken) and pull the necessary historical market data (OHLCV) for that pair and timeframe (ETH/USDT, 5m). This data, combined with alternative data streams, is the required input for the discovery task.

Discovery Task (Per Combination): Using the historical data pulled for the combination, run an optimization (testing the specified ranges) to discover the ideal parameters that maximize NET_PROFIT.

Parameters to Discover: volume_explosion_threshold (test 3x to 10x avg) price_move_speed (test 2% to 10% per candle) sentiment_extreme_threshold (test RSI <20 or >80) exhaustion_wick_ratio (test 1.5 to 4.0) reversal_confirmation_candles (test 1 to 3) stop_distance (test 1.0 to 3.0 ATR) target_multiple (test 2:1 to 5:1) panic_score_minimum (test 0.6 to 0.9) smart_money_divergence (test 0.4 to 0.8)

Validation, Governance, & Lifecycle: For each configuration, calculate all metrics and assign a status based on the "Lifecycle Stage Rules". Continuously monitor all configurations and apply "Aggressive Decay Rules" and "Circuit Breakers" as defined.

Lifecycle Stage Rules:

DISCOVERY: sample < 30, position = 0.25x, latency_priority = low

VALIDATION: sample 30-100, position = 0.5x, p_value < 0.05

MATURE: sample > 100, position = 1.0x, sharpe > 1.5, adverse_selection < 0.3

DECAY: performance_degradation > -20% OR death_signal triggered

PAPER: NET_PROFIT < 0 OR sharpe < 0.5 OR fill_rate < 0.7

Aggressive Decay Rules:

if rolling_30d_sharpe < 0.5 * lifetime_sharpe: -> IMMEDIATE move to PAPER

if adverse_selection_score > 0.6: -> REDUCE position 50%

if death_signals_count >= 2: -> DECAY status

if fill_rate < 0.7: -> PAUSE trading

Circuit Breakers:

max_daily_loss: X

max_correlation_spike: X

unusual_market_threshold: X

latency_threshold_ms: X

consecutive_losses_limit: N

max_adverse_selection: X

regime_break_threshold: X

Output Requirement: For every discovered configuration (all statuses), generate and output a single JSON object. This object must precisely follow the "V3 Universal Discovery Template" below, with all placeholders [...] populated with the actual discovered parameters, calculated metrics, and metadata.

Required JSON Output Template (CAPITULATION REVERSAL V3) {"pair":"[TRADING_PAIR]","pattern":"CAPITULATION REVERSAL V3","configurations":[{"id":"[DYNAMICALLY_GENERATED_ID]","status":"[DISCOVERY/VALIDATION/MATURE/DECAY/PAPER]","metadata":{"model_version":"[MODEL_VERSION]","discovery_date":"[DISCOVERY_TIMESTAMP]","engine_hash":"[ENGINE_HASH]","runtime_env":"[RUNTIME_ENVIRONMENT]"},"context":{"pair":"[TRADING_PAIR]","exchange":"[EXCHANGE_NAME]","timeframe":"[TIMEFRAME_VALUE]"},"parameters":{"volume_explosion_threshold":"[val]","price_move_speed":"[val]","sentiment_extreme_threshold":"[val]","exhaustion_wick_ratio":"[val]","reversal_confirmation_candles":"[val]","stop_distance":"[val]","target_multiple":"[val]","panic_score_minimum":"[val]","smart_money_divergence":"[val]"},"performance":{"gross_WR":"[val]","avg_win":"[val]","avg_loss":"[val]","exchange_fees":"[val]","est_slippage":"[val]","actual_slippage":"[val]","NET_PROFIT":"[val]","sample_size":"[val]"},"statistical_validation":{"sharpe_ratio":"[val]","calmar_ratio":"[val]","sortino_ratio":"[val]","p_value":"[val]","z_score":"[val]","monte_carlo_var":"[val]","stability_score":"[val]","drawdown_duration":"[val]","trade_clustering":"[val]","rolling_30d_sharpe":"[val]","lifetime_sharpe_ratio":"[val]"},"execution_metrics":{"fill_rate":"[val]","partial_fill_rate":"[val]","time_to_fill_ms":"[val]","slippage_vs_mid_bps":"[val]","adverse_selection_score":"[val]","post_trade_drift_1m":"[val]","post_trade_drift_5m":"[val]","rejection_rate":"[val]"},"ensemble_regime_classification":{"regime_models":{"model_1h":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_4h":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_1d":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_volatility":{"type":"[val]","weight":"[val]","prediction":"[val]"}},"final_regime_probability":{"trending":"[val]","ranging":"[val]","volatile":"[val]"},"regime_transition_probability":"[val]","regime_stability_score":"[val]"},"alternative_data_signals":{"order_flow_imbalance":"[val]","options_flow":{"put_call_ratio":"[val]","gamma_exposure":"[val]","dealer_positioning":"[val]","vix_term_structure":"[val]"},"funding_rate":"[val]","perpetual_basis":"[val]","social_sentiment":{"fear_greed_index":"[val]","panic_words_frequency":"[val]","capitulation_mentions":"[val]"},"long_liquidations_24h":"[val]","short_liquidations_24h":"[val]"},"adversarial_analysis":{"adversarial_score":"[val]","fake_capitulation_probability":"[val]","smart_money_accumulation":"[val]","institutional_buying_detected":"[val]","wash_trading_score":"[val]","manipulation_indicators":"[val]"},"risk_allocation":{"kelly_fraction":"[val]","correlation_adjusted_weight":"[val]","regime_adjusted_size":"[val]","max_position_size":"[val]","current_allocation":"[val]","var_95":"[val]","cvar_95":"[val]"},"market_microstructure":{"avg_spread_bps":"[val]","book_depth_ratio":"[val]","book_imbalance":"[val]","tick_size_impact":"[val]","maker_rebate":"[val]","taker_fee":"[val]","level2_depth_score":"[val]","microstructure_noise":"[val]"},"pattern_health":{"months_since_discovery":"[val]","performance_degradation":"[val]","degradation_velocity":"[val]","death_signals":{"volume_profile_changed":"[val]","new_algo_detected":"[val]","correlation_spike":"[val]","sharpe_below_50pct":"[val]","unusual_fill_pattern":"[val]","regime_break":"[val]"},"death_signal_count":"[val]","resurrection_score":"[val]","correlation_to_other_patterns":{"[pattern_name]":"[val]"}},"circuit_breakers":{"max_daily_loss":"[val]","max_correlation_spike":"[val]","unusual_market_threshold":"[val]","latency_threshold_ms":"[val]","consecutive_losses_limit":"[val]","max_adverse_selection":"[val]","regime_break_threshold":"[val]"},"meta_learning_outputs":{"pattern_failure_predictors":"[list]","optimal_market_conditions":"[desc]","edge_expiration_estimate":"[val]","recommended_alternatives":"[list]"}}]}` 
            },
            { 
                id: 'strat-3', 
                name: 'FAILED BREAKDOWN (SPRING) - FULL DISCOVERY V3', 
                prompt: `Objective: Execute a full-stack, combinatorial discovery task to identify all profitable configurations for the "FAILED BREAKDOWN (SPRING) V3" trading pattern based on the provided runtime inputs.

Runtime Inputs: Target Pairs: [USER_PROVIDED_PAIRS_FROM_INPUT] Target Exchanges: [DYNAMICALLY_FETCH_CONNECTED_EXCHANGES]

Core Iteration Matrix: You must iterate through every possible combination of the following variables: Exchanges: Use the provided [Target Exchanges] list. Trading Pairs: Use the provided [Target Pairs] list. Regimes: Use the output from the [ENSEMBLE CLASSIFIER - multiple timeframes]. Timeframes: 1m, 5m, 15m, 1h, 4h, 1d

Data & Optimization Mandate: For each unique combination (e.g., Coinbase, SOL/USDC, 4h), you must connect to that exchange's API (Coinbase) and pull the necessary historical market data (OHLCV) for that pair and timeframe (SOL/USDC, 4h). This data, combined with alternative data streams, is the required input for the discovery task.

Discovery Task (Per Combination): Using the historical data pulled for the combination, run an optimization (testing the specified ranges) to discover the ideal parameters that maximize NET_PROFIT.

Parameters to Discover: range_lookback_periods (test 20 to 200) breakdown_depth (test 0.5% to 2% below support) volume_decline_threshold (test 0.3x to 0.7x avg) recovery_speed (test 1 to 5 candles) spring_confirmation_volume (test 1.5x to 4x) stop_distance (test below spring low) target_multiple (test to range high) accumulation_score_min (test 0.6 to 0.9) wyckoff_phase_alignment (test phase C/D detection)

Validation, Governance, & Lifecycle: For each configuration, calculate all metrics and assign a status based on the "Lifecycle Stage Rules". Continuously monitor all configurations and apply "Aggressive Decay Rules" and "Circuit Breakers" as defined.

Lifecycle Stage Rules:

DISCOVERY: sample < 30, position = 0.25x, latency_priority = low

VALIDATION: sample 30-100, position = 0.5x, p_value < 0.05

MATURE: sample > 100, position = 1.0x, sharpe > 1.5, adverse_selection < 0.3

DECAY: performance_degradation > -20% OR death_signal triggered

PAPER: NET_PROFIT < 0 OR sharpe < 0.5 OR fill_rate < 0.7

Aggressive Decay Rules:

if rolling_30d_sharpe < 0.5 * lifetime_sharpe: -> IMMEDIATE move to PAPER

if adverse_selection_score > 0.6: -> REDUCE position 50%

if death_signals_count >= 2: -> DECAY status

if fill_rate < 0.7: -> PAUSE trading

Circuit Breakers:

max_daily_loss: X

max_correlation_spike: X

unusual_market_threshold: X

latency_threshold_ms: X

consecutive_losses_limit: N

max_adverse_selection: X

regime_break_threshold: X

Output Requirement: For every discovered configuration (all statuses), generate and output a single JSON object. This object must precisely follow the "V3 Universal Discovery Template" below, with all placeholders [...] populated with the actual discovered parameters, calculated metrics, and metadata.

Required JSON Output Template (FAILED BREAKDOWN V3) {"pair":"[TRADING_PAIR]","pattern":"FAILED BREAKDOWN (SPRING) V3","configurations":[{"id":"[DYNAMICALLY_GENERATED_ID]","status":"[DISCOVERY/VALIDATION/MATURE/DECAY/PAPER]","metadata":{"model_version":"[MODEL_VERSION]","discovery_date":"[DISCOVERY_TIMESTAMP]","engine_hash":"[ENGINE_HASH]","runtime_env":"[RUNTIME_ENVIRONMENT]"},"context":{"pair":"[TRADING_PAIR]","exchange":"[EXCHANGE_NAME]","timeframe":"[TIMEFRAME_VALUE]"},"parameters":{"range_lookback_periods":"[val]","breakdown_depth":"[val]","volume_decline_threshold":"[val]","recovery_speed":"[val]","spring_confirmation_volume":"[val]","stop_distance":"[val]","target_multiple":"[val]","accumulation_score_min":"[val]","wyckoff_phase_alignment":"[val]"},"performance":{"gross_WR":"[val]","avg_win":"[val]","avg_loss":"[val]","exchange_fees":"[val]","est_slippage":"[val]","actual_slippage":"[val]","NET_PROFIT":"[val]","sample_size":"[val]"},"statistical_validation":{"sharpe_ratio":"[val]","calmar_ratio":"[val]","sortino_ratio":"[val]","p_value":"[val]","z_score":"[val]","monte_carlo_var":"[val]","stability_score":"[val]","drawdown_duration":"[val]","trade_clustering":"[val]","rolling_30d_sharpe":"[val]","lifetime_sharpe_ratio":"[val]"},"execution_metrics":{"fill_rate":"[val]","partial_fill_rate":"[val]","time_to_fill_ms":"[val]","slippage_vs_mid_bps":"[val]","adverse_selection_score":"[val]","post_trade_drift_1m":"[val]","post_trade_drift_5m":"[val]","rejection_rate":"[val]"},"ensemble_regime_classification":{"regime_models":{"model_1h":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_4h":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_1d":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_volatility":{"type":"[val]","weight":"[val]","prediction":"[val]"}},"final_regime_probability":{"trending":"[val]","ranging":"[val]","volatile":"[val]"},"regime_transition_probability":"[val]","regime_stability_score":"[val]"},"alternative_data_signals":{"order_flow_imbalance":"[val]","options_flow":{"put_call_ratio":"[val]","gamma_exposure":"[val]","dealer_positioning":"[val]"},"funding_rate":"[val]","on_chain_accumulation":"[val]","exchange_balance_change":"[val]","dormant_coins_moved":"[val]","miner_distribution":"[val]"},"adversarial_analysis":{"adversarial_score":"[val]","false_breakdown_trap":"[val]","smart_money_positioning":"[val]","composite_operator_score":"[val]","distribution_detected":"[val]","accumulation_confirmed":"[val]"},"risk_allocation":{"kelly_fraction":"[val]","correlation_adjusted_weight":"[val]","regime_adjusted_size":"[val]","max_position_size":"[val]","current_allocation":"[val]","var_95":"[val]","cvar_95":"[val]"},"market_microstructure":{"avg_spread_bps":"[val]","book_depth_ratio":"[val]","book_imbalance":"[val]","tick_size_impact":"[val]","maker_rebate":"[val]","taker_fee":"[val]","level2_depth_score":"[val]","microstructure_noise":"[val]"},"pattern_health":{"months_since_discovery":"[val]","performance_degradation":"[val]","degradation_velocity":"[val]","death_signals":{"volume_profile_changed":"[val]","new_algo_detected":"[val]","correlation_spike":"[val]","sharpe_below_50pct":"[val]","unusual_fill_pattern":"[val]","regime_break":"[val]"},"death_signal_count":"[val]","resurrection_score":"[val]","correlation_to_other_patterns":{"[pattern_name]":"[val]"}},"circuit_breakers":{"max_daily_loss":"[val]","max_correlation_spike":"[val]","unusual_market_threshold":"[val]","latency_threshold_ms":"[val]","consecutive_losses_limit":"[val]","max_adverse_selection":"[val]","regime_break_threshold":"[val]"},"meta_learning_outputs":{"pattern_failure_predictors":"[list]","optimal_market_conditions":"[desc]","edge_expiration_estimate":"[val]","recommended_alternatives":"[list]"}}]}` 
            },
            { 
                id: 'strat-4', 
                name: 'SUPPLY SHOCK (MACRO) - FULL DISCOVERY V3', 
                prompt: `Objective: Execute a full-stack, combinatorial discovery task to identify all profitable configurations for the "SUPPLY SHOCK (MACRO) V3" trading pattern based on the provided runtime inputs.

Runtime Inputs: Target Pairs: [USER_PROVIDED_PAIRS_FROM_INPUT] Target Exchanges: [DYNAMICALLY_FETCH_CONNECTED_EXCHANGES]

Core Iteration Matrix: You must iterate through every possible combination of the following variables: Exchanges: Use the provided [Target Exchanges] list. Trading Pairs: Use the provided [Target Pairs] list. Regimes: Use the output from the [ENSEMBLE CLASSIFIER - multiple timeframes]. Timeframes: 1m, 5m, 15m, 1h, 4h, 1d

Data & Optimization Mandate: For each unique combination (e.g., Bybit, ADA/USDT, 1d), you must connect to that exchange's API (Bybit) and pull the necessary historical market data (OHLCV) for that pair and timeframe (ADA/USDT, 1d). This data, combined with alternative data streams, is the required input for the discovery task.

Discovery Task (Per Combination): Using the historical data pulled for the combination, run an optimization (testing the specified ranges) to discover the ideal parameters that maximize NET_PROFIT.

Parameters to Discover: gap_threshold (test 1% to 5% from previous close) volume_surge_multiplier (test 5x to 20x) momentum_persistence (test 3 to 10 consecutive candles) news_sentiment_score (test -1 to +1) no_retracement_periods (test 5 to 20) trail_stop_activation (test 1.5 to 3.0 ATR) position_hold_maximum (test 5 to 30 candles) catalyst_strength_minimum (test 0.6 to 0.9) continuation_probability (test 0.6 to 0.9)

Validation, Governance, & Lifecycle: For each configuration, calculate all metrics and assign a status based on the "Lifecycle Stage Rules". Continuously monitor all configurations and apply "Aggressive Decay Rules" and "Circuit Breakers" as defined.

Lifecycle Stage Rules:

DISCOVERY: sample < 30, position = 0.25x, latency_priority = low

VALIDATION: sample 30-100, position = 0.5x, p_value < 0.05

MATURE: sample > 100, position = 1.0x, sharpe > 1.5, adverse_selection < 0.3

DECAY: performance_degradation > -20% OR death_signal triggered

PAPER: NET_PROFIT < 0 OR sharpe < 0.5 OR fill_rate < 0.7

Aggressive Decay Rules:

if rolling_30d_sharpe < 0.5 * lifetime_sharpe: -> IMMEDIATE move to PAPER

if adverse_selection_score > 0.6: -> REDUCE position 50%

if death_signals_count >= 2: -> DECAY status

if fill_rate < 0.7: -> PAUSE trading

Circuit Breakers:

max_daily_loss: X

max_correlation_spike: X

unusual_market_threshold: X

latency_threshold_ms: X

consecutive_losses_limit: N

max_adverse_selection: X

regime_break_threshold: X

Output Requirement: For every discovered configuration (all statuses), generate and output a single JSON object. This object must precisely follow the "V3 Universal Discovery Template" below, with all placeholders [...] populated with the actual discovered parameters, calculated metrics, and metadata.

Required JSON Output Template (SUPPLY SHOCK V3) {"pair":"[TRADING_PAIR]","pattern":"SUPPLY SHOCK (MACRO) V3","configurations":[{"id":"[DYNAMICALLY_GENERATED_ID]","status":"[DISCOVERY/VALIDATION/MATURE/DECAY/PAPER]","metadata":{"model_version":"[MODEL_VERSION]","discovery_date":"[DISCOVERY_TIMESTAMP]","engine_hash":"[ENGINE_HASH]","runtime_env":"[RUNTIME_ENVIRONMENT]"},"context":{"pair":"[TRADING_PAIR]","exchange":"[EXCHANGE_NAME]","timeframe":"[TIMEFRAME_VALUE]"},"parameters":{"gap_threshold":"[val]","volume_surge_multiplier":"[val]","momentum_persistence":"[val]","news_sentiment_score":"[val]","no_retracement_periods":"[val]","trail_stop_activation":"[val]","position_hold_maximum":"[val]","catalyst_strength_minimum":"[val]","continuation_probability":"[val]"},"performance":{"gross_WR":"[val]","avg_win":"[val]","avg_loss":"[val]","exchange_fees":"[val]","est_slippage":"[val]","actual_slippage":"[val]","NET_PROFIT":"[val]","sample_size":"[val]"},"statistical_validation":{"sharpe_ratio":"[val]","calmar_ratio":"[val]","sortino_ratio":"[val]","p_value":"[val]","z_score":"[val]","monte_carlo_var":"[val]","stability_score":"[val]","drawdown_duration":"[val]","trade_clustering":"[val]","rolling_30d_sharpe":"[val]","lifetime_sharpe_ratio":"[val]"},"execution_metrics":{"fill_rate":"[val]","partial_fill_rate":"[val]","time_to_fill_ms":"[val]","slippage_vs_mid_bps":"[val]","adverse_selection_score":"[val]","post_trade_drift_1m":"[val]","post_trade_drift_5m":"[val]","rejection_rate":"[val]"},"ensemble_regime_classification":{"regime_models":{"model_1h":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_4h":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_1d":{"timeframe":"[val]","weight":"[val]","prediction":"[val]"},"model_volatility":{"type":"[val]","weight":"[val]","prediction":"[val]"}},"final_regime_probability":{"trending":"[val]","ranging":"[val]","volatile":"[val]"},"regime_transition_probability":"[val]","regime_stability_score":"[val]"},"alternative_data_signals":{"order_flow_imbalance":"[val]","options_flow":{"put_call_ratio":"[val]","gamma_exposure":"[val]","dealer_positioning":"[val]","unusual_options_activity":"[val]"},"funding_rate":"[val]","perpetual_basis":"[val]","macro_indicators":{"dxy_correlation":"[val]","spy_correlation":"[val]","vix_level":"[val]","bond_yield_direction":"[val]"},"news_analytics":{"headline_count":"[val]","sentiment_score":"[val]","source_credibility":"[val]","event_magnitude":"[val]"}},"adversarial_analysis":{"adversarial_score":"[val]","fake_news_probability":"[val]","insider_trading_signals":"[val]","pump_dump_indicators":"[val]","coordinated_manipulation":"[val]","front_running_detected":"[val]"},"risk_allocation":{"kelly_fraction":"[val]","correlation_adjusted_weight":"[val]","regime_adjusted_size":"[val]","max_position_size":"[val]","current_allocation":"[val]","var_95":"[val]","cvar_service_95":"[val]"},"market_microstructure":{"avg_spread_bps":"[val]","book_depth_ratio":"[val]","book_imbalance":"[val]","tick_size_impact":"[val]","maker_rebate":"[val]","taker_fee":"[val]","level2_depth_score":"[val]","microstructure_noise":"[val]"},"pattern_health":{"months_since_discovery":"[val]","performance_degradation":"[val]","degradation_velocity":"[val]","death_signals":{"volume_profile_changed":"[val]","new_algo_detected":"[val]","correlation_spike":"[val]","sharpe_below_50pct":"[val]","unusual_fill_pattern":"[val]","regime_break":"[val]"},"death_signal_count":"[val]","resurrection_score":"[val]","correlation_to_other_patterns":{"[pattern_name]":"[val]"}},"circuit_breakers":{"max_daily_loss":"[val]","max_correlation_spike":"[val]","unusual_market_threshold":"[val]","latency_threshold_ms":"[val]","consecutive_losses_limit":"[val]","max_adverse_selection":"[val]","regime_break_threshold":"[val]"},"meta_learning_outputs":{"pattern_failure_predictors":"[list]","optimal_market_conditions":"[desc]","edge_expiration_estimate":"[val]","recommended_alternatives":"[list]"}}]}` 
            },
        ];
    }
    return mockData[userId].strategies;
};

export const saveStrategy = async (userId: string, strategy: Omit<Strategy, 'id'> & { id?: string }): Promise<Strategy> => {
    const strategies = mockData[userId].strategies as Strategy[];
    if (strategy.id) {
        const index = strategies.findIndex(s => s.id === strategy.id);
        if (index !== -1) {
            strategies[index] = { ...strategies[index], ...strategy };
            return strategies[index];
        }
    }
    const newStrategy = { ...strategy, id: strategy.id || `strat-${Date.now()}` };
    strategies.push(newStrategy);
    return newStrategy;
};

export const deleteStrategy = async (userId: string, strategyId: string): Promise<void> => {
    mockData[userId].strategies = mockData[userId].strategies.filter((s: Strategy) => s.id !== strategyId);
};

export const getExchangeConnections = async (userId: string): Promise<ExchangeConnection[]> => {
     if (!mockData[userId].exchangeConnections || mockData[userId].exchangeConnections.length === 0) {
        mockData[userId].exchangeConnections = [
            { id: 'conn-1', exchangeName: 'Binance', nickname: 'Main Binance Acct', apiKey: 'binance-key-123', apiSecret: 'secret', status: ExchangeConnectionStatus.CONNECTED },
            { id: 'conn-2', exchangeName: 'Coinbase', nickname: 'Coinbase Pro', apiKey: 'coinbase-key-456', apiSecret: 'secret', status: ExchangeConnectionStatus.ERROR },
        ];
    }
    return mockData[userId].exchangeConnections;
};

export const saveExchangeConnection = async (userId: string, connection: Omit<ExchangeConnection, 'id' | 'status'> & { id?: string }): Promise<ExchangeConnection> => {
    const connections = mockData[userId].exchangeConnections as ExchangeConnection[];
    await delay(1000); // Simulate API test
    const status = Math.random() > 0.1 ? ExchangeConnectionStatus.CONNECTED : ExchangeConnectionStatus.ERROR;
     if (connection.id) {
        const index = connections.findIndex(c => c.id === connection.id);
        if (index !== -1) {
            connections[index] = { ...connections[index], ...connection, status };
            return connections[index];
        }
    }
    const newConnection: ExchangeConnection = { ...connection, id: connection.id || `conn-${Date.now()}`, status };
    connections.push(newConnection);
    return newConnection;
};

export const deleteExchangeConnection = async (userId: string, connectionId: string): Promise<void> => {
    mockData[userId].exchangeConnections = mockData[userId].exchangeConnections.filter((c: ExchangeConnection) => c.id !== connectionId);
};
