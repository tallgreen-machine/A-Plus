import React, { useState, useEffect, useCallback, FormEvent, useRef } from 'react';
import * as api from '../services/realApi';
import type { Strategy, TrainedConfiguration } from '../types';
import { Skeleton } from './Skeleton';
import { PlusIcon, TrashIcon, SparklesIcon, RocketIcon } from './icons';

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
        name: 'Liquidity Sweep',
        description: 'Identifies and trades liquidity sweeps with volume confirmation'
    }
];

const AVAILABLE_SYMBOLS = [
    'BTC/USDT',
    'ETH/USDT',
    'SOL/USDT',
    'ADA/USDT',
    'AVAX/USDT',
    'DOT/USDT',
    'MATIC/USDT'
];

const AVAILABLE_EXCHANGES = ['binanceus'];
const AVAILABLE_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d'];
const AVAILABLE_REGIMES = ['bull', 'bear', 'sideways'];

const API_BASE = 'http://138.68.245.159:8000';

export const StrategyStudio: React.FC<StrategyStudioProps> = ({ currentUser, onTrainingComplete }) => {
    // Strategy selection
    const [selectedStrategies, setSelectedStrategies] = useState<string[]>(['LIQUIDITY_SWEEP']);
    
    // Training config
    const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC/USDT');
    const [selectedExchange] = useState<string>('binanceus');
    const [selectedTimeframe, setSelectedTimeframe] = useState<string>('5m');
    const [selectedRegime, setSelectedRegime] = useState<string>('sideways');
    const [optimizer, setOptimizer] = useState<string>('bayesian');
    const [lookbackDays, setLookbackDays] = useState<number>(30);
    const [nIterations, setNIterations] = useState<number>(20);
    
    // Training state
    const [isTraining, setIsTraining] = useState(false);
    const [currentJob, setCurrentJob] = useState<TrainingJob | null>(null);
    const [trainingLog, setTrainingLog] = useState<LogEntry[]>([]);
    const logContainerRef = useRef<HTMLDivElement>(null);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
            addLog(`Starting training for ${selectedSymbol} on ${selectedExchange} (${selectedTimeframe})`, 'info');
            
            // Start training job with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch(`${API_BASE}/api/v2/training/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy: selectedStrategies[0], // First selected strategy
                    symbol: selectedSymbol,
                    exchange: selectedExchange,
                    timeframe: selectedTimeframe,
                    regime: selectedRegime,
                    optimizer: optimizer,
                    lookback_days: lookbackDays,
                    n_iterations: nIterations,
                    run_validation: false
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to start training');
            }

            const job: TrainingJob = await response.json();
            setCurrentJob(job);
            addLog(`✓ Training job started: ${job.job_id}`, 'success');
            addLog(`Monitoring progress...`, 'info');

            // Poll progress every 2 seconds
            pollIntervalRef.current = setInterval(async () => {
                try {
                    const progressResponse = await fetch(`${API_BASE}/api/v2/training/jobs/${job.job_id}/progress`);
                    if (!progressResponse.ok) return;

                    const progress: TrainingProgress = await progressResponse.json();

                    // Build progress log message
                    const pct = progress.percentage.toFixed(1);
                    let progressLine = `[${pct}%] Step ${progress.step_number}/4: ${progress.current_step}`;
                    
                    if (progress.current_iteration && progress.total_iterations) {
                        progressLine += ` | Iteration ${progress.current_iteration}/${progress.total_iterations}`;
                    }
                    
                    if (progress.best_score !== undefined && progress.best_score !== null) {
                        progressLine += ` | Best Score: ${progress.best_score.toFixed(4)}`;
                    }

                    addLog(progressLine, 'progress');

                    // Check completion
                    if (progress.is_complete) {
                        if (pollIntervalRef.current) {
                            clearInterval(pollIntervalRef.current);
                            pollIntervalRef.current = null;
                        }
                        
                        if (progress.error_message) {
                            addLog(`✗ Training failed: ${progress.error_message}`, 'error');
                        } else {
                            addLog(`✓ Training complete! Best score: ${progress.best_score?.toFixed(4)}`, 'success');
                            
                            // Fetch results
                            const resultsResponse = await fetch(`${API_BASE}/api/v2/training/jobs/${job.job_id}/results`);
                            if (resultsResponse.ok) {
                                const results = await resultsResponse.json();
                                addLog(`Configuration saved with ID: ${results.config_id}`, 'success');
                                addLog(`View trained asset on the Trained Assets page`, 'info');
                            }
                        }
                        
                        setIsTraining(false);
                    }
                } catch (error) {
                    console.error('Error polling progress:', error);
                }
            }, 2000);

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

    const toggleStrategy = (strategyId: string) => {
        setSelectedStrategies(prev =>
            prev.includes(strategyId)
                ? prev.filter(id => id !== strategyId)
                : [...prev, strategyId]
        );
    };
    
    const renderStrategySidebar = () => {
        return (
            <div className="flex flex-col h-full">
                <div className="p-4 border-b border-brand-border shrink-0">
                    <h3 className="text-lg font-bold text-brand-text-primary mb-1">Available Strategies</h3>
                    <p className="text-xs text-brand-text-secondary">Select strategies to train</p>
                </div>
                <nav className="flex-1 overflow-y-auto p-2 space-y-2">
                    {AVAILABLE_STRATEGIES.map(strategy => {
                        const isSelected = selectedStrategies.includes(strategy.id);
                        return (
                            <button
                                key={strategy.id}
                                onClick={() => toggleStrategy(strategy.id)}
                                className={`w-full text-left px-3 py-3 rounded-md text-sm transition-colors border-2 ${
                                    isSelected
                                        ? 'bg-brand-primary/20 border-brand-primary text-brand-primary'
                                        : 'border-brand-border text-brand-text-primary hover:bg-brand-surface'
                                }`}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="font-semibold">{strategy.name}</div>
                                        <div className="text-xs text-brand-text-secondary mt-1">{strategy.description}</div>
                                    </div>
                                    {isSelected && (
                                        <div className="ml-2 text-brand-primary">✓</div>
                                    )}
                                </div>
                            </button>
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
                            disabled
                            className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm opacity-60 cursor-not-allowed"
                        >
                            {AVAILABLE_EXCHANGES.map(exchange => (
                                <option key={exchange} value={exchange}>{exchange}</option>
                            ))}
                        </select>
                        <p className="text-xs text-brand-text-secondary mt-1">Currently only binanceus is supported</p>
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
                            <option value="grid">Grid Search</option>
                        </select>
                        <p className="text-xs text-brand-text-secondary mt-1">
                            {optimizer === 'bayesian' && 'Smart search using probability models - fastest convergence'}
                            {optimizer === 'random' && 'Random parameter exploration - good for broad search'}
                            {optimizer === 'grid' && 'Exhaustive search - most thorough but slowest'}
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-brand-text-secondary mb-1.5">
                                Lookback Days
                            </label>
                            <input
                                type="number"
                                value={lookbackDays}
                                onChange={(e) => setLookbackDays(Number(e.target.value))}
                                min="7"
                                max="365"
                                className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                            />
                            <p className="text-xs text-brand-text-secondary mt-1">Historical data window</p>
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
    
    return (
        <div className="h-full flex flex-col">
            <header className="p-4 lg:p-6 border-b border-brand-border shrink-0">
                <div>
                    <h1 className="text-3xl font-bold text-brand-text-primary">Strategy Studio</h1>
                    <p className="text-brand-text-secondary mt-1">
                        Train strategies with machine learning optimization
                    </p>
                </div>
            </header>
            <main className="flex-1 grid grid-cols-[280px_1fr_380px] overflow-hidden">
                <aside className="bg-brand-surface/50 border-r border-brand-border overflow-hidden">
                    {renderStrategySidebar()}
                </aside>
                <div className="bg-brand-surface overflow-y-auto">
                    {renderConfigPanel()}
                </div>
                <aside className="border-l border-brand-border overflow-hidden">
                    {renderTrainingSidebar()}
                </aside>
            </main>
        </div>
    );
};