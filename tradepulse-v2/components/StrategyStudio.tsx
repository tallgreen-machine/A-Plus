import React, { useState, useEffect, useCallback, FormEvent, useRef } from 'react';
import * as api from '../services/realApi';
import type { Strategy, TrainedConfiguration } from '../types';
import { Skeleton } from './Skeleton';
import { PlusIcon, TrashIcon, SparklesIcon, RocketIcon } from './icons';
import ResourceMonitor from './ResourceMonitor';
import TrainingQueue from './TrainingQueue';
import AnimatedProgress from './AnimatedProgress';

interface StrategyStudioProps {
    currentUser: string;
    onTrainingComplete: (results: TrainedConfiguration[]) => void;
}

interface LogEntry {
    timestamp: string;
    content: string;
    level: 'info' | 'success' | 'error' | 'progress';
}

interface TrainingJob {
    job_id: string;
    status: string;
    strategy: string;
    symbol: string;
    exchange: string;
    timeframe: string;
}

interface TrainingProgress {
    job_id: string;
    percentage: number;
    current_step: string;
    step_number: number;
    total_steps: number;
    step_percentage: number;
    current_iteration?: number;
    total_iterations?: number;
    current_candle?: number;  // NEW: Fine-grained progress
    total_candles?: number;   // NEW: Total candles in dataset
    best_score?: number;
    current_score?: number;
    best_params?: Record<string, any>;
    estimated_completion?: string;
    is_complete: boolean;
    error_message?: string;
}

// Hard-coded available strategies (will be dynamic later)
const AVAILABLE_STRATEGIES = [
    {
        id: 'LIQUIDITY_SWEEP',
        name: 'Liquidity Sweep V3',
        description: 'Identifies and trades liquidity sweeps at key levels with volume confirmation',
        riskReward: '2:1',
        stopLoss: '1.5 ATR',
        parameters: 9,
        effectiveness: '100%',
        dataRequired: 'OHLCV only',
        bestTimeframes: ['15m', '1h', '4h']
    },
    {
        id: 'CAPITULATION_REVERSAL',
        name: 'Capitulation Reversal V3',
        description: 'Detects panic selling/buying events through volume explosions and price velocity',
        riskReward: '2.5:1',
        stopLoss: '1.5 ATR',
        parameters: 13,
        effectiveness: '70-85%',
        dataRequired: 'OHLCV + optional L2',
        bestTimeframes: ['1h', '4h']
    },
    {
        id: 'FAILED_BREAKDOWN',
        name: 'Failed Breakdown (Spring) V3',
        description: 'Wyckoff-based detection of failed breakdowns with accumulation confirmation',
        riskReward: '2:1',
        stopLoss: '1.2 ATR',
        parameters: 15,
        effectiveness: '55-70%',
        dataRequired: 'OHLCV + optional L2/trades',
        bestTimeframes: ['4h', '1d']
    }
];

// Detailed technical specifications for each strategy
const STRATEGY_SPECS: Record<string, any> = {
    LIQUIDITY_SWEEP: {
        name: 'Liquidity Sweep V3',
        overview: 'Detects liquidity sweeps (stop hunts) where price pierces a key level, triggers stops, then reverses direction with volume confirmation.',
        entryLogic: [
            'Identify key support/resistance levels (100+ period lookback)',
            'Detect pierce through level (configurable depth)',
            'Confirm volume spike (2-5x average volume)',
            'Confirm reversal candles (rejection pattern)',
            'Enter on reversal confirmation'
        ],
        exitLogic: [
            'Take-profit: 2:1 risk/reward ratio',
            'Stop-loss: 1.5 ATR distance',
            'Max holding: 30 candles',
            'Exit on opposite signal'
        ],
        parameters: [
            { name: 'pierce_depth', range: '0.05% - 0.5%', default: '0.2%', description: 'How far price must pierce level' },
            { name: 'volume_spike_threshold', range: '1.5x - 5x', default: '2.5x', description: 'Volume multiplier vs average' },
            { name: 'reversal_candles', range: '1 - 5', default: '2', description: 'Required reversal candles' },
            { name: 'min_distance_from_level', range: '0.05% - 0.3%', default: '0.1%', description: 'Min distance to consider level valid' },
            { name: 'atr_multiplier_sl', range: '1.0 - 3.0', default: '1.5', description: 'Stop-loss distance (ATR multiplier)' },
            { name: 'risk_reward_ratio', range: '1.5:1 - 4:1', default: '2:1', description: 'Take-profit ratio' },
            { name: 'max_holding_periods', range: '10 - 100', default: '30', description: 'Maximum candles to hold' },
            { name: 'key_level_lookback', range: '50 - 200', default: '100', description: 'Periods to look back for key levels' },
            { name: 'min_level_touches', range: '2 - 5', default: '3', description: 'Min touches to qualify as key level' }
        ],
        dataRequirements: {
            minimum: ['OHLCV (open, high, low, close, volume)', 'ATR indicator'],
            optional: ['Order flow data', 'Spread data'],
            frequency: 'Per-candle basis'
        },
        performance: {
            effectiveness: '100%',
            bestMarkets: ['Trending', 'Range-bound'],
            bestTimeframes: ['15m', '1h', '4h'],
            bestAssets: ['BTC', 'ETH', 'Major altcoins']
        },
        notes: [
            'Works with FREE data only',
            'No external APIs required',
            'Best in liquid markets with clear levels'
        ]
    },
    CAPITULATION_REVERSAL: {
        name: 'Capitulation Reversal V3 (FREE DATA)',
        overview: 'Detects panic selling/buying events through price action and volume WITHOUT requiring external data feeds (liquidations, funding rates, sentiment). Modified to work with free data only.',
        entryLogic: [
            'Detect volume explosion (5x+ average = liquidation proxy)',
            'Detect extreme price velocity (3%+ per candle = panic)',
            'Detect ATR explosion (2.5x+ = volatility spike)',
            'Detect exhaustion wicks (wick 3x+ body size)',
            'Confirm RSI extremes (< 15 or > 85)',
            'Check for 3+ consecutive panic candles',
            'Optional: Verify order book imbalance (60%+ bid dominance)',
            'Enter on recovery candle with strong volume (2.5x+)'
        ],
        exitLogic: [
            'Take-profit: 2.5:1 risk/reward ratio',
            'Stop-loss: 1.5 ATR distance',
            'Max holding: 50 candles',
            'Exit on volume divergence'
        ],
        parameters: [
            { name: 'volume_explosion_threshold', range: '3x - 8x', default: '5x', description: 'Volume multiplier indicating panic' },
            { name: 'price_velocity_threshold', range: '2% - 5%', default: '3%', description: 'Price change per candle threshold' },
            { name: 'atr_explosion_threshold', range: '2x - 4x', default: '2.5x', description: 'ATR multiplier vs average' },
            { name: 'exhaustion_wick_ratio', range: '2:1 - 5:1', default: '3:1', description: 'Wick/body ratio for exhaustion' },
            { name: 'rsi_extreme_threshold', range: '10 - 20', default: '15', description: 'RSI extreme level (< X or > 100-X)' },
            { name: 'rsi_divergence_lookback', range: '10 - 30', default: '20', description: 'Periods for RSI divergence' },
            { name: 'orderbook_imbalance_threshold', range: '50% - 70%', default: '60%', description: 'Bid/ask imbalance threshold' },
            { name: 'consecutive_panic_candles', range: '2 - 5', default: '3', description: 'Min panic candles in a row' },
            { name: 'recovery_volume_threshold', range: '2x - 4x', default: '2.5x', description: 'Recovery volume multiplier' },
            { name: 'atr_multiplier_sl', range: '1.0 - 2.5', default: '1.5', description: 'Stop-loss distance' },
            { name: 'risk_reward_ratio', range: '2:1 - 4:1', default: '2.5:1', description: 'Take-profit ratio' },
            { name: 'max_holding_periods', range: '30 - 100', default: '50', description: 'Maximum candles to hold' },
            { name: 'lookback_periods', range: '50 - 150', default: '100', description: 'Periods to analyze for panic' }
        ],
        dataRequirements: {
            minimum: ['OHLCV', 'ATR', 'RSI (14-period)', 'Volume moving average'],
            optional: ['Order book L2 data (top 20 levels)', 'Bid/ask imbalance metrics'],
            frequency: 'Real-time per-candle + optional 5-min L2 snapshots'
        },
        performance: {
            effectiveness: '70-85% (vs 100% with paid liquidation data)',
            improvementWithL2: '+15% with order book data',
            bestMarkets: ['Volatile', 'Trending with pullbacks'],
            bestTimeframes: ['1h', '4h'],
            bestAssets: ['BTC', 'ETH', 'SOL', 'High-volume altcoins']
        },
        notes: [
            'Modified from original V3 spec to work WITHOUT paid data',
            'Uses volume explosions as proxy for liquidations',
            'Uses price velocity as proxy for funding rate stress',
            'Order book data optional but recommended (+15% effectiveness)',
            'Best during high volatility periods'
        ]
    },
    FAILED_BREAKDOWN: {
        name: 'Failed Breakdown (Spring) V3 (FREE DATA)',
        overview: 'Detects Wyckoff springs (failed breakdowns) using volume profile and price action WITHOUT requiring on-chain data. Modified to work with free exchange data only.',
        entryLogic: [
            'Detect range formation (100+ periods, <5% width, declining volume)',
            'Identify support level (3+ touches)',
            'Detect breakdown BELOW support (1% depth) with WEAK volume (<50% avg)',
            'Detect rapid recovery ABOVE support within 10 candles',
            'Confirm recovery with STRONG volume (3x+ average)',
            'Calculate accumulation score (must be ≥70%)',
            'Optional: Detect order book absorption (3x normal depth)',
            'Optional: Confirm smart money via large trade analysis (1.5:1 buy ratio)',
            'Enter on spring confirmation'
        ],
        exitLogic: [
            'Take-profit: 2:1 risk/reward ratio',
            'Stop-loss: 1.2 ATR below entry (tighter than other strategies)',
            'Max holding: 50 candles',
            'Trail stop after 1:1 achieved'
        ],
        parameters: [
            { name: 'range_lookback_periods', range: '50 - 200', default: '100', description: 'Periods to identify range' },
            { name: 'range_tightness_threshold', range: '3% - 8%', default: '5%', description: 'Max range width percentage' },
            { name: 'breakdown_depth', range: '0.5% - 2%', default: '1%', description: 'How far below support' },
            { name: 'breakdown_volume_threshold', range: '30% - 70%', default: '50%', description: 'WEAK volume = trap/fake breakdown' },
            { name: 'spring_max_duration', range: '5 - 20', default: '10', description: 'Max candles below support' },
            { name: 'recovery_volume_threshold', range: '2x - 5x', default: '3x', description: 'STRONG volume = smart money' },
            { name: 'recovery_speed', range: '3 - 10', default: '5', description: 'Max candles to reclaim support' },
            { name: 'orderbook_absorption_threshold', range: '2x - 5x', default: '3x', description: 'Hidden bid volume multiplier' },
            { name: 'orderbook_monitoring_depth', range: '10 - 30', default: '20', description: 'Order book levels to monitor' },
            { name: 'large_trade_multiplier', range: '3x - 8x', default: '5x', description: 'Large trade size vs median' },
            { name: 'smart_money_imbalance', range: '1.3:1 - 2:1', default: '1.5:1', description: 'Buy/sell ratio for smart money' },
            { name: 'accumulation_score_minimum', range: '60% - 80%', default: '70%', description: 'Min score to enter trade' },
            { name: 'atr_multiplier_sl', range: '1.0 - 2.0', default: '1.2', description: 'Stop-loss distance' },
            { name: 'risk_reward_ratio', range: '1.5:1 - 3:1', default: '2:1', description: 'Take-profit ratio' },
            { name: 'max_holding_periods', range: '30 - 100', default: '50', description: 'Maximum candles to hold' }
        ],
        dataRequirements: {
            minimum: ['OHLCV', 'ATR', 'Volume moving average', 'Support/resistance detection'],
            optional: [
                'Order book L2 data (top 20 levels) - adds +15% effectiveness',
                'Trade feed data (individual trades) - adds +10% effectiveness',
                'Large trade identification',
                'Bid/ask depth metrics'
            ],
            frequency: 'Real-time per-candle + optional 5-min L2 snapshots + optional trade stream'
        },
        performance: {
            effectiveness: '55-70% (vs 100% with paid on-chain data)',
            improvementWithL2: '+15% with order book data',
            improvementWithTrades: '+10% additional with trade feed',
            bestMarkets: ['Range-bound', 'Accumulation phases'],
            bestTimeframes: ['4h', '1d'],
            bestAssets: ['BTC', 'ETH', 'Established altcoins']
        },
        wyckoffPhases: [
            { phase: 'A', name: 'Preliminary Support', description: 'Initial sell-off and support' },
            { phase: 'B', name: 'Accumulation Range', description: 'Range formation with declining volume' },
            { phase: 'C', name: 'Spring (KEY)', description: 'Breakdown trap with weak volume - ENTRY SIGNAL' },
            { phase: 'D', name: 'Recovery', description: 'Strong volume reversal - ENTRY POINT' },
            { phase: 'E', name: 'Markup', description: 'Breakout and uptrend begins' }
        ],
        notes: [
            'Modified from original V3 spec to work WITHOUT on-chain data',
            'Based on Wyckoff methodology (1930s - no on-chain data existed!)',
            'Uses volume profile as proxy for accumulation',
            'Weak breakdown volume = lack of real selling (trap)',
            'Strong recovery volume = institutional buying',
            'L2 order book data highly recommended (+15% effectiveness)',
            'Trade feed data moderately recommended (+10% effectiveness)',
            'Best during consolidation/accumulation phases'
        ]
    }
};

const AVAILABLE_SYMBOLS = [
    'BTC/USDT',
    'ETH/USDT',
    'SOL/USDT',
    'ADA/USDT',
    'AVAX/USDT',
    'DOT/USDT',
    'MATIC/USDT'
];

const AVAILABLE_EXCHANGES = ['binanceus', 'cryptocom', 'coinbase', 'bitstamp'];
const AVAILABLE_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d'];
const AVAILABLE_REGIMES = ['bull', 'bear', 'sideways'];

const API_BASE = 'http://138.68.245.159:8000';

export const StrategyStudio: React.FC<StrategyStudioProps> = ({ currentUser, onTrainingComplete }) => {
    // Strategy selection
    const [selectedStrategies, setSelectedStrategies] = useState<string[]>(['LIQUIDITY_SWEEP']);
    const [strategyDetailsModal, setStrategyDetailsModal] = useState<string | null>(null);
    
    // Training config
    const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC/USDT');
    const [selectedExchange, setSelectedExchange] = useState<string>('binanceus');
    const [selectedTimeframe, setSelectedTimeframe] = useState<string>('5m');
    const [selectedRegime, setSelectedRegime] = useState<string>('sideways');
    const [optimizer, setOptimizer] = useState<string>('random'); // Changed to 'random' for faster, more predictable training
    const [lookbackCandles, setLookbackCandles] = useState<number>(10000); // Changed from lookbackDays to lookbackCandles
    const [nIterations, setNIterations] = useState<number>(20);
    
    // Data Quality Filtering config (NEW)
    const [enableFiltering, setEnableFiltering] = useState<boolean>(true);
    const [minVolumeThreshold, setMinVolumeThreshold] = useState<number>(0.1);
    const [minPriceMovement, setMinPriceMovement] = useState<number>(0.01);
    const [filterFlatCandles, setFilterFlatCandles] = useState<boolean>(true);
    
    // Training state
    const [isTraining, setIsTraining] = useState(false);
    const [currentJob, setCurrentJob] = useState<TrainingJob | null>(null);
    const [trainingLog, setTrainingLog] = useState<LogEntry[]>([]);
    const [allTrainingLogs, setAllTrainingLogs] = useState<LogEntry[]>([]);
    const [currentProgress, setCurrentProgress] = useState<any>(null);
    const logContainerRef = useRef<HTMLDivElement>(null);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Fetch all training logs on mount
    useEffect(() => {
        const fetchAllLogs = async () => {
            try {
                const response = await fetch('/api/training/logs/recent?limit=100');
                const data = await response.json();
                // Transform API response to LogEntry format
                const transformedLogs = data.map((log: any) => ({
                    timestamp: new Date(log.timestamp).toLocaleTimeString(),
                    message: log.message,
                    progress: log.progress,
                    jobId: log.job_id,
                    level: log.log_level || 'info',
                }));
                setAllTrainingLogs(transformedLogs);
            } catch (error) {
                console.error('Failed to fetch training logs:', error);
            }
        };
        fetchAllLogs();
    }, []);

    // Connect to SSE for active training job
    useEffect(() => {
        let eventSource: EventSource | null = null;
        let pollingInterval: NodeJS.Timeout | null = null;

        const connectToActiveJob = async () => {
            try {
                // Find if there's a running job
                const response = await fetch('/api/training/queue');
                const jobs = await response.json();
                const runningJob = jobs.find((j: any) => j.status === 'running');

                if (runningJob) {
                    // Close existing connection if any
                    if (eventSource) {
                        eventSource.close();
                    }

                    // Connect to SSE stream
                    eventSource = new EventSource(`/api/training/${runningJob.id}/stream`);
                    
                    // Listen for log events
                    eventSource.addEventListener('log', (event: any) => {
                        try {
                            const data = JSON.parse(event.data);
                            if (data.message) {
                                // Append new log to accumulated logs
                                setAllTrainingLogs(prev => [...prev, {
                                    timestamp: new Date(data.timestamp).toLocaleTimeString(),
                                    message: data.message,
                                    progress: data.progress || 0,
                                    jobId: parseInt(runningJob.id),
                                    level: data.log_level || 'info',
                                }]);
                            }
                        } catch (error) {
                            console.error('Error parsing SSE log event:', error);
                        }
                    });
                    
                    // Listen for progress events (optional - for progress bar updates)
                    eventSource.addEventListener('progress', (event: any) => {
                        try {
                            const data = JSON.parse(event.data);
                            // Update progress state for display with job metadata
                            setCurrentProgress({
                                progress: data.progress || 0,
                                current_episode: data.current_episode,
                                total_episodes: data.total_episodes,
                                current_candle: data.current_candle,  // NEW: Candle-level progress
                                total_candles: data.total_candles,    // NEW: Total candles
                                current_reward: data.current_reward,
                                current_loss: data.current_loss,
                                stage: data.stage,
                                status: data.status,
                                // Include job metadata for display
                                jobId: runningJob.id,
                                strategy_name: runningJob.strategy_name,
                                pair: runningJob.pair,
                                exchange: runningJob.exchange,
                                timeframe: runningJob.timeframe,
                                regime: runningJob.regime
                            });
                        } catch (error) {
                            console.error('Error parsing SSE progress event:', error);
                        }
                    });

                    eventSource.onerror = () => {
                        console.log('SSE connection closed or error occurred');
                        if (eventSource) {
                            eventSource.close();
                            eventSource = null;
                        }
                    };
                } else if (eventSource) {
                    // No running job, close connection
                    eventSource.close();
                    eventSource = null;
                    setCurrentProgress(null); // Clear progress when no job running
                }
            } catch (error) {
                console.error('Failed to check for active job:', error);
            }
        };

        // Check immediately
        connectToActiveJob();

        // Poll for new running jobs every 5 seconds
        pollingInterval = setInterval(connectToActiveJob, 5000);

        return () => {
            if (eventSource) {
                eventSource.close();
            }
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
        };
    }, []);

    // Auto-scroll log to bottom
    useEffect(() => {
        if (logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [trainingLog]);

    // Cleanup polling interval on unmount
    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
        };
    }, []);

    const addLog = (content: string, level: LogEntry['level'] = 'info') => {
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setTrainingLog(prev => [...prev, { timestamp, content, level }]);
    };

    const handleTrain = async () => {
        if (selectedStrategies.length === 0) {
            addLog('Please select at least one strategy', 'error');
            return;
        }

        setTrainingLog([]);
        setIsTraining(true);
        setCurrentJob(null);

        // Clear any existing polling interval
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
        }

        try {
            addLog(`Submitting training job for ${selectedSymbol} on ${selectedExchange} (${selectedTimeframe})`, 'info');
            
            // Submit training job to queue
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch(`${API_BASE}/api/training/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy_name: selectedStrategies[0], // First selected strategy
                    pair: selectedSymbol,
                    exchange: selectedExchange,
                    timeframe: selectedTimeframe,
                    regime: selectedRegime,
                    optimizer: optimizer,
                    lookback_candles: lookbackCandles,  // Changed from lookback_days
                    n_iterations: nIterations,
                    data_filter_config: {  // NEW: Data quality filtering settings
                        enable_filtering: enableFiltering,
                        min_volume_threshold: minVolumeThreshold,
                        min_price_movement_pct: minPriceMovement,
                        filter_flat_candles: filterFlatCandles,
                        preserve_high_volume_single_price: true
                    }
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to submit training job');
            }

            const job = await response.json();
            setCurrentJob(job);
            addLog(`✓ Training job submitted: ${job.id}`, 'success');
            addLog(`Job added to queue. Watch progress in the log column.`, 'info');
            
            setIsTraining(false); // No longer blocking, job is in queue

        } catch (error) {
            if (error instanceof Error) {
                if (error.name === 'AbortError') {
                    addLog(`✗ Request timeout - server may be slow or unavailable`, 'error');
                } else {
                    addLog(`✗ Error: ${error.message}`, 'error');
                }
            } else {
                addLog(`✗ Unknown error occurred`, 'error');
            }
            setIsTraining(false);
        }
    };

    const selectStrategy = (strategyId: string) => {
        setSelectedStrategies([strategyId]); // Only one strategy at a time
    };
    
    const renderStrategySidebar = () => {
        return (
            <div className="flex flex-col h-full">
                <div className="p-4 border-b border-brand-border shrink-0">
                    <h3 className="text-lg font-bold text-brand-text-primary mb-1">Available Strategies</h3>
                    <p className="text-xs text-brand-text-secondary">Select a strategy to train</p>
                </div>
                <nav className="flex-1 overflow-y-auto p-2 space-y-2">
                    {AVAILABLE_STRATEGIES.map(strategy => {
                        const isSelected = selectedStrategies.includes(strategy.id);
                        return (
                            <div
                                key={strategy.id}
                                className={`w-full text-left px-3 py-3 rounded-md text-sm transition-colors border-2 ${
                                    isSelected
                                        ? 'bg-brand-primary/20 border-brand-primary'
                                        : 'border-brand-border hover:bg-brand-surface'
                                }`}
                            >
                                <div className="flex items-start justify-between">
                                    <button
                                        onClick={() => selectStrategy(strategy.id)}
                                        className="flex-1 text-left"
                                    >
                                        <div className={`font-semibold ${isSelected ? 'text-brand-primary' : 'text-brand-text-primary'}`}>
                                            {strategy.name}
                                        </div>
                                        <div className="text-xs text-brand-text-secondary mt-1">{strategy.description}</div>
                                        <div className="flex gap-2 mt-2 text-xs text-brand-text-secondary">
                                            <span className="bg-brand-surface px-2 py-0.5 rounded">R/R: {strategy.riskReward}</span>
                                            <span className="bg-brand-surface px-2 py-0.5 rounded">{strategy.parameters} params</span>
                                            <span className="bg-brand-surface px-2 py-0.5 rounded">{strategy.effectiveness}</span>
                                        </div>
                                    </button>
                                    {isSelected && (
                                        <div className="ml-2 text-brand-primary text-lg">●</div>
                                    )}
                                </div>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setStrategyDetailsModal(strategy.id);
                                    }}
                                    className="mt-2 text-brand-text-secondary hover:text-brand-primary transition-colors text-xs px-2 py-1 border border-brand-border rounded hover:border-brand-primary"
                                    title="View technical specifications"
                                >
                                    Details
                                </button>
                            </div>
                        );
                    })}
                </nav>
            </div>
        );
    };

    const renderConfigPanel = () => {
        return (
            <div className="flex flex-col h-full p-6 space-y-4">
                <h2 className="text-2xl font-bold text-brand-text-primary">Training Configuration</h2>
                
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-brand-text-secondary mb-1.5">
                            Symbol
                        </label>
                        <select
                            value={selectedSymbol}
                            onChange={(e) => setSelectedSymbol(e.target.value)}
                            className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                        >
                            {AVAILABLE_SYMBOLS.map(symbol => (
                                <option key={symbol} value={symbol}>{symbol}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-brand-text-secondary mb-1.5">
                            Exchange
                        </label>
                        <select
                            value={selectedExchange}
                            onChange={(e) => setSelectedExchange(e.target.value)}
                            className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                        >
                            {AVAILABLE_EXCHANGES.map(exchange => (
                                <option key={exchange} value={exchange}>
                                    {exchange === 'cryptocom' ? 'Crypto.com' : 
                                     exchange === 'binanceus' ? 'BinanceUS' : 
                                     exchange === 'coinbase' ? 'Coinbase' : 
                                     exchange === 'bitstamp' ? 'Bitstamp' : exchange}
                                </option>
                            ))}
                        </select>
                        <p className="text-xs text-brand-text-secondary mt-1">Multi-exchange training enabled</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-brand-text-secondary mb-1.5">
                            Timeframe
                        </label>
                        <select
                            value={selectedTimeframe}
                            onChange={(e) => setSelectedTimeframe(e.target.value)}
                            className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                        >
                            {AVAILABLE_TIMEFRAMES.map(tf => (
                                <option key={tf} value={tf}>{tf}</option>
                            ))}
                        </select>
                    </div>

                    {/* Market Regime dropdown - commented out for now, may re-enable later
                    <div>
                        <label className="block text-sm font-medium text-brand-text-secondary mb-1.5">
                            Market Regime
                        </label>
                        <select
                            value={selectedRegime}
                            onChange={(e) => setSelectedRegime(e.target.value)}
                            className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                        >
                            {AVAILABLE_REGIMES.map(regime => (
                                <option key={regime} value={regime}>
                                    {regime.charAt(0).toUpperCase() + regime.slice(1)}
                                </option>
                            ))}
                        </select>
                        <p className="text-xs text-brand-text-secondary mt-1">
                            Optimize parameters for this market condition
                        </p>
                    </div>
                    */}

                    <div>
                        <label className="block text-sm font-medium text-brand-text-secondary mb-1.5">
                            Optimizer Algorithm
                        </label>
                        <select
                            value={optimizer}
                            onChange={(e) => setOptimizer(e.target.value)}
                            className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                        >
                            <option value="bayesian">Bayesian Optimization (Recommended)</option>
                            <option value="random">Random Search</option>
                        </select>
                        <p className="text-xs text-brand-text-secondary mt-1">
                            {optimizer === 'bayesian' && 'Smart search using probability models - fastest convergence'}
                            {optimizer === 'random' && 'Random parameter exploration - good for broad search'}
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-brand-text-secondary mb-1.5">
                                Training Candles
                            </label>
                            <input
                                type="number"
                                value={lookbackCandles}
                                onChange={(e) => setLookbackCandles(Number(e.target.value))}
                                min="1000"
                                max="50000"
                                step="1000"
                                className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                            />
                            <div className="flex gap-2 mt-2 flex-wrap">
                                {[5000, 10000, 15000, 20000].map(count => (
                                    <button
                                        key={count}
                                        onClick={() => setLookbackCandles(count)}
                                        className={`text-xs px-2 py-1 rounded ${
                                            lookbackCandles === count 
                                                ? 'bg-brand-primary text-white' 
                                                : 'bg-brand-bg-secondary text-brand-text-secondary hover:bg-brand-bg-tertiary'
                                        }`}
                                    >
                                        {(count / 1000).toFixed(0)}k
                                    </button>
                                ))}
                            </div>
                            <p className="text-xs text-brand-text-secondary mt-1">
                                {lookbackCandles >= 10000 
                                    ? '~35 days @ 5m, 417 days @ 1h (recommended)' 
                                    : '~17 days @ 5m, 208 days @ 1h (quick test)'}
                            </p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-brand-text-secondary mb-1.5">
                                Iterations
                            </label>
                            <input
                                type="number"
                                value={nIterations}
                                onChange={(e) => setNIterations(Number(e.target.value))}
                                min="10"
                                max="200"
                                className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                            />
                            <p className="text-xs text-brand-text-secondary mt-1">Optimization attempts</p>
                        </div>
                    </div>

                    {/* Data Quality Filtering Section */}
                    <div className="pt-4 border-t border-brand-border">
                        <div className="mb-3">
                            <label className="flex items-center gap-2 text-sm font-medium text-brand-text-secondary cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={enableFiltering}
                                    onChange={(e) => setEnableFiltering(e.target.checked)}
                                    className="w-4 h-4 text-brand-primary bg-brand-bg border-brand-border rounded focus:ring-brand-primary focus:ring-2"
                                />
                                <span>Enable Data Quality Filtering</span>
                                <span className="ml-auto px-2 py-0.5 text-xs bg-green-500/10 text-green-400 rounded">Recommended</span>
                            </label>
                            <p className="text-xs text-brand-text-secondary mt-1 ml-6">
                                Remove invalid candles (zero volume, flat prices) that degrade training quality
                            </p>
                        </div>

                        {enableFiltering && (
                            <div className="ml-6 space-y-3 pb-3">
                                <div>
                                    <label className="flex items-center justify-between text-xs font-medium text-brand-text-secondary mb-1">
                                        <span>Min Volume Threshold</span>
                                        <span className="font-mono text-brand-primary">{minVolumeThreshold}</span>
                                    </label>
                                    <input
                                        type="range"
                                        min="0"
                                        max="1"
                                        step="0.05"
                                        value={minVolumeThreshold}
                                        onChange={(e) => setMinVolumeThreshold(Number(e.target.value))}
                                        className="w-full h-2 bg-brand-bg-secondary rounded-lg appearance-none cursor-pointer"
                                    />
                                    <div className="flex justify-between text-xs text-brand-text-secondary mt-1">
                                        <span>0 (off)</span>
                                        <span>0.5</span>
                                        <span>1.0 (strict)</span>
                                    </div>
                                </div>

                                <div>
                                    <label className="flex items-center justify-between text-xs font-medium text-brand-text-secondary mb-1">
                                        <span>Min Price Movement %</span>
                                        <span className="font-mono text-brand-primary">{(minPriceMovement * 100).toFixed(2)}%</span>
                                    </label>
                                    <input
                                        type="range"
                                        min="0"
                                        max="0.1"
                                        step="0.005"
                                        value={minPriceMovement}
                                        onChange={(e) => setMinPriceMovement(Number(e.target.value))}
                                        className="w-full h-2 bg-brand-bg-secondary rounded-lg appearance-none cursor-pointer"
                                    />
                                    <div className="flex justify-between text-xs text-brand-text-secondary mt-1">
                                        <span>0% (off)</span>
                                        <span>0.05%</span>
                                        <span>0.10%</span>
                                    </div>
                                </div>

                                <div>
                                    <label className="flex items-center gap-2 text-xs text-brand-text-secondary cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={filterFlatCandles}
                                            onChange={(e) => setFilterFlatCandles(e.target.checked)}
                                            className="w-3 h-3 text-brand-primary bg-brand-bg border-brand-border rounded focus:ring-brand-primary"
                                        />
                                        <span>Filter flat candles (O=H=L=C)</span>
                                    </label>
                                    <p className="text-xs text-brand-text-secondary mt-0.5 ml-5">
                                        Preserves high-volume single-price trades
                                    </p>
                                </div>

                                <div className="bg-blue-500/5 border border-blue-500/20 rounded-md p-2 mt-2">
                                    <p className="text-xs text-blue-400">
                                        <strong>Tip:</strong> Start with defaults (0.1 vol, 0.01% move). If win rate &lt; 30%, try stricter settings (0.5 vol, 0.05% move).
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="pt-4 border-t border-brand-border">
                        <button
                            onClick={handleTrain}
                            disabled={isTraining || selectedStrategies.length === 0}
                            className="w-full flex items-center justify-center gap-2 bg-brand-primary text-white font-semibold px-4 py-3 rounded-lg hover:bg-brand-primary/80 transition-colors disabled:bg-brand-border disabled:text-brand-text-secondary disabled:cursor-not-allowed"
                        >
                            {isTraining ? (
                                <>
                                    <SparklesIcon className="w-5 h-5 animate-spin" />
                                    <span>Training in Progress...</span>
                                </>
                            ) : (
                                <>
                                    <RocketIcon className="w-5 h-5" />
                                    <span>Start Training</span>
                                </>
                            )}
                        </button>
                        {selectedStrategies.length === 0 && (
                            <p className="text-xs text-brand-negative mt-2 text-center">
                                Please select at least one strategy from the left panel
                            </p>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    const renderTrainingSidebar = () => {
        return (
            <div className="flex flex-col h-full bg-brand-surface/50">
                <div className="p-4 border-b border-brand-border shrink-0">
                    <h3 className="text-lg font-bold text-brand-text-primary">Training Log</h3>
                    <p className="text-xs text-brand-text-secondary mt-1">Real-time training progress</p>
                </div>
                
                <div className="flex-1 flex flex-col p-4 min-h-0">
                    <div ref={logContainerRef} className="flex-1 overflow-y-auto bg-black/20 p-3 rounded-md">
                        {trainingLog.length > 0 ? (
                            <pre className="text-xs whitespace-pre-wrap font-mono space-y-1">
                                {trainingLog.map((log, index) => {
                                    let colorClass = 'text-brand-text-secondary';
                                    if (log.level === 'success') colorClass = 'text-green-400';
                                    else if (log.level === 'error') colorClass = 'text-red-400';
                                    else if (log.level === 'progress') colorClass = 'text-blue-400';

                                    return (
                                        <div key={index}>
                                            <span className="text-gray-500">[{log.timestamp}] </span>
                                            <span className={colorClass}>{log.content}</span>
                                        </div>
                                    );
                                })}
                            </pre>
                        ) : (
                            <div className="flex items-center justify-center h-full text-center text-sm text-brand-text-secondary/50 p-4">
                                Training logs will appear here when you start training
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };
    
    const renderStrategyDetailsModal = () => {
        if (!strategyDetailsModal) return null;
        
        const specs = STRATEGY_SPECS[strategyDetailsModal];
        if (!specs) return null;
        
        return (
            <div 
                className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                onClick={() => setStrategyDetailsModal(null)}
            >
                <div 
                    className="bg-brand-surface rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Modal Header */}
                    <div className="sticky top-0 bg-brand-surface border-b border-brand-border p-6 flex justify-between items-start">
                        <div>
                            <h2 className="text-2xl font-bold text-brand-text-primary">{specs.name}</h2>
                            <p className="text-sm text-brand-text-secondary mt-1">{specs.overview}</p>
                        </div>
                        <button
                            onClick={() => setStrategyDetailsModal(null)}
                            className="text-brand-text-secondary hover:text-brand-text-primary text-2xl leading-none"
                        >
                            ×
                        </button>
                    </div>
                    
                    {/* Modal Content */}
                    <div className="p-6 space-y-6">
                        {/* Entry Logic */}
                        <section>
                            <h3 className="text-lg font-semibold text-brand-text-primary mb-3">Entry Logic</h3>
                            <ol className="space-y-2">
                                {specs.entryLogic.map((step: string, idx: number) => (
                                    <li key={idx} className="flex gap-3 text-sm">
                                        <span className="text-brand-primary font-semibold shrink-0">{idx + 1}.</span>
                                        <span className="text-brand-text-secondary">{step}</span>
                                    </li>
                                ))}
                            </ol>
                        </section>
                        
                        {/* Exit Logic */}
                        <section>
                            <h3 className="text-lg font-semibold text-brand-text-primary mb-3">Exit Logic</h3>
                            <ul className="space-y-2">
                                {specs.exitLogic.map((item: string, idx: number) => (
                                    <li key={idx} className="flex gap-3 text-sm">
                                        <span className="text-brand-primary">•</span>
                                        <span className="text-brand-text-secondary">{item}</span>
                                    </li>
                                ))}
                            </ul>
                        </section>
                        
                        {/* Wyckoff Phases (only for Failed Breakdown) */}
                        {specs.wyckoffPhases && (
                            <section>
                                <h3 className="text-lg font-semibold text-brand-text-primary mb-3">Wyckoff Phases</h3>
                                <div className="grid gap-2">
                                    {specs.wyckoffPhases.map((phase: any, idx: number) => (
                                        <div key={idx} className="flex gap-3 text-sm bg-brand-bg rounded p-3">
                                            <span className="text-brand-primary font-bold shrink-0">Phase {phase.phase}:</span>
                                            <div>
                                                <div className="font-semibold text-brand-text-primary">{phase.name}</div>
                                                <div className="text-brand-text-secondary text-xs mt-1">{phase.description}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}
                        
                        {/* ML Parameters */}
                        <section>
                            <h3 className="text-lg font-semibold text-brand-text-primary mb-3">
                                ML-Optimizable Parameters ({specs.parameters.length})
                            </h3>
                            <div className="grid gap-3">
                                {specs.parameters.map((param: any, idx: number) => (
                                    <div key={idx} className="bg-brand-bg rounded p-3">
                                        <div className="flex justify-between items-start gap-4 mb-1">
                                            <span className="font-mono text-sm text-brand-primary">{param.name}</span>
                                            <div className="text-right shrink-0">
                                                <div className="text-xs text-brand-text-secondary">Range: {param.range}</div>
                                                <div className="text-xs text-brand-text-primary">Default: {param.default}</div>
                                            </div>
                                        </div>
                                        <p className="text-xs text-brand-text-secondary">{param.description}</p>
                                    </div>
                                ))}
                            </div>
                        </section>
                        
                        {/* Data Requirements */}
                        <section>
                            <h3 className="text-lg font-semibold text-brand-text-primary mb-3">Data Requirements</h3>
                            <div className="space-y-3">
                                <div>
                                    <h4 className="text-sm font-semibold text-brand-text-primary mb-2">Minimum (Required)</h4>
                                    <ul className="space-y-1">
                                        {specs.dataRequirements.minimum.map((item: string, idx: number) => (
                                            <li key={idx} className="flex gap-2 text-sm">
                                                <span className="text-green-500">✓</span>
                                                <span className="text-brand-text-secondary">{item}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                {specs.dataRequirements.optional && (
                                    <div>
                                        <h4 className="text-sm font-semibold text-brand-text-primary mb-2">Optional (Improves Performance)</h4>
                                        <ul className="space-y-1">
                                            {specs.dataRequirements.optional.map((item: string, idx: number) => (
                                                <li key={idx} className="flex gap-2 text-sm">
                                                    <span className="text-yellow-500">⚡</span>
                                                    <span className="text-brand-text-secondary">{item}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                <div className="text-xs text-brand-text-secondary bg-brand-bg rounded p-2">
                                    <span className="font-semibold">Frequency:</span> {specs.dataRequirements.frequency}
                                </div>
                            </div>
                        </section>
                        
                        {/* Performance Metrics */}
                        <section>
                            <h3 className="text-lg font-semibold text-brand-text-primary mb-3">Performance & Best Use Cases</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-brand-bg rounded p-3">
                                    <div className="text-xs text-brand-text-secondary mb-1">Effectiveness</div>
                                    <div className="text-lg font-bold text-brand-primary">{specs.performance.effectiveness}</div>
                                    {specs.performance.improvementWithL2 && (
                                        <div className="text-xs text-green-500 mt-1">{specs.performance.improvementWithL2}</div>
                                    )}
                                    {specs.performance.improvementWithTrades && (
                                        <div className="text-xs text-green-500">{specs.performance.improvementWithTrades}</div>
                                    )}
                                </div>
                                <div className="bg-brand-bg rounded p-3">
                                    <div className="text-xs text-brand-text-secondary mb-1">Best Timeframes</div>
                                    <div className="flex gap-2 flex-wrap mt-1">
                                        {specs.performance.bestTimeframes.map((tf: string) => (
                                            <span key={tf} className="bg-brand-primary/20 text-brand-primary px-2 py-1 rounded text-xs font-semibold">
                                                {tf}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div className="bg-brand-bg rounded p-3">
                                    <div className="text-xs text-brand-text-secondary mb-1">Best Markets</div>
                                    <div className="text-sm text-brand-text-primary">
                                        {specs.performance.bestMarkets.join(', ')}
                                    </div>
                                </div>
                                <div className="bg-brand-bg rounded p-3">
                                    <div className="text-xs text-brand-text-secondary mb-1">Best Assets</div>
                                    <div className="text-sm text-brand-text-primary">
                                        {specs.performance.bestAssets.join(', ')}
                                    </div>
                                </div>
                            </div>
                        </section>
                        
                        {/* Important Notes */}
                        <section>
                            <h3 className="text-lg font-semibold text-brand-text-primary mb-3">Important Notes</h3>
                            <ul className="space-y-2">
                                {specs.notes.map((note: string, idx: number) => (
                                    <li key={idx} className="flex gap-3 text-sm">
                                        <span className="text-yellow-500 shrink-0">⚠️</span>
                                        <span className="text-brand-text-secondary">{note}</span>
                                    </li>
                                ))}
                            </ul>
                        </section>
                    </div>
                    
                    {/* Modal Footer */}
                    <div className="sticky bottom-0 bg-brand-surface border-t border-brand-border p-4 flex justify-end">
                        <button
                            onClick={() => setStrategyDetailsModal(null)}
                            className="px-4 py-2 bg-brand-primary text-white rounded hover:bg-brand-primary/90 transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        );
    };
    
    return (
        <div className="h-full flex flex-col">
            {/* Resource Monitor Header */}
            <ResourceMonitor />
            
            <main className="flex-1 grid grid-cols-[280px_320px_280px_1fr] gap-4 p-4 overflow-hidden">
                {/* Column 1: Strategy Selection */}
                <div className="bg-brand-surface rounded-lg overflow-y-auto">
                    {renderStrategySidebar()}
                </div>
                
                {/* Column 2: Config Panel */}
                <div className="bg-brand-surface rounded-lg overflow-y-auto">
                    {renderConfigPanel()}
                </div>
                
                {/* Column 3: Training Queue */}
                <TrainingQueue />
                
                {/* Column 4: Animated Progress */}
                <div className="overflow-y-auto">
                    <AnimatedProgress logs={allTrainingLogs} currentProgress={currentProgress} />
                </div>
            </main>
            
            {/* Strategy Details Modal */}
            {renderStrategyDetailsModal()}
        </div>
    );
};