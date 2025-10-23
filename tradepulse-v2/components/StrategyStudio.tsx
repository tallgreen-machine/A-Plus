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
    result?: TrainedConfiguration | null;
}

export const StrategyStudio: React.FC<StrategyStudioProps> = ({ currentUser, onTrainingComplete }) => {
    const [strategies, setStrategies] = useState<Strategy[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
    const [formData, setFormData] = useState({ name: '', prompt: '' });
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState('');
    const [isTraining, setIsTraining] = useState(false);
    const [selectedPair, setSelectedPair] = useState<string>('');
    const [tradingPairs] = useState(api.mockTrainedAssetsList);
    const [trainingLog, setTrainingLog] = useState<LogEntry[]>([]);
    const logContainerRef = useRef<HTMLDivElement>(null);


    const fetchStrategies = useCallback(async () => {
        setLoading(true);
        const data = await api.getStrategies(currentUser);
        setStrategies(data);
        if (data.length > 0 && !selectedStrategyId) {
            // setSelectedStrategyId(data[0].id);
        }
        setLoading(false);
    }, [currentUser, selectedStrategyId]);

    useEffect(() => {
        fetchStrategies();
    }, [fetchStrategies]);
    
    useEffect(() => {
        if (selectedStrategyId) {
            const selected = strategies.find(s => s.id === selectedStrategyId);
            if (selected) {
                setFormData({ name: selected.name, prompt: selected.prompt });
            }
        } else {
            setFormData({ name: '', prompt: '' });
        }
        setError('');
    }, [selectedStrategyId, strategies]);

    useEffect(() => {
        if (logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [trainingLog]);

    const handleSelectStrategy = (id: string) => {
        setSelectedStrategyId(id);
    };

    const handleCreateNew = () => {
        setSelectedStrategyId(null);
    };

    const handleDelete = async () => {
        if (selectedStrategyId && window.confirm('Are you sure you want to delete this strategy? This cannot be undone.')) {
            await api.deleteStrategy(currentUser, selectedStrategyId);
            setSelectedStrategyId(null);
            await fetchStrategies();
        }
    };
    
    const handleSave = async (e: FormEvent) => {
        e.preventDefault();
        setError('');
        if (!formData.name || !formData.prompt) {
            setError('Both name and prompt are required.');
            return;
        }

        setIsSaving(true);
        try {
            const savedStrategy = await api.saveStrategy(currentUser, { ...formData, id: selectedStrategyId ?? undefined });
            await fetchStrategies();
            setSelectedStrategyId(savedStrategy.id);
        } catch (err) {
            setError('Failed to save strategy. Please try again.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleTrain = async () => {
        if (!selectedPair) return;

        const addLog = (content: string, result: TrainedConfiguration | null = null) => {
            const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            setTrainingLog(prev => [...prev, { timestamp, content, result }]);
        };
        
        setTrainingLog([]);
        setIsTraining(true);
        
        try {
            addLog(`Initiating training for ${selectedPair}...`);
            await new Promise(res => setTimeout(res, 500));
            addLog(`Analyzing ${strategies.length} selected strategies.`);
            await new Promise(res => setTimeout(res, 800));
            addLog(`Backtesting against multiple exchanges and timeframes...`);
            addLog(`-------------------------------------------------------------------------------------`);
            addLog(`STATUS     | EXCHANGE | TF   | GROSS WR | NET PROFIT | TRADES`);
            addLog(`-------------------------------------------------------------------------------------`);
            
            const handleTrainingProgress = (result: TrainedConfiguration) => {
                const isProfitable = result.performance.net_profit > 0;
                const status = isProfitable ? '✔ VIABLE' : '❌ REJECTED';
                const logLine = `${status.padEnd(10)} | ${result.exchange.padEnd(8)} | ${result.timeframe.padEnd(4)} | ${result.performance.gross_win_rate.toFixed(1).padStart(7)}% | ${result.performance.net_profit.toFixed(2).padStart(9)}% | ${result.performance.sample_size}`;
                addLog(logLine, result);
            };
            
            const results = await api.runTrainingSimulation(selectedPair, strategies, handleTrainingProgress);
            
            addLog(`-------------------------------------------------------------------------------------`);
            await new Promise(res => setTimeout(res, 500));
            
            addLog(`✔ Simulation complete. Passing all ${results.length} configurations to results page.`);

            await new Promise(res => setTimeout(res, 1000));
            addLog(`Navigating to results page...`);
            onTrainingComplete(results);

        } catch(err) {
            console.error("Training simulation failed", err);
            addLog(`❌ Error during training simulation.`);
        // FIX: Ensure isTraining state is reset regardless of success or failure.
        } finally {
            setIsTraining(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };
    
    const renderSidebar = () => {
        if (loading) {
            return (
                <div className="space-y-2 p-4">
                    {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-10" />)}
                </div>
            )
        }
        
        return (
             <div className="flex flex-col h-full">
                <div className="p-4 border-b border-brand-border shrink-0">
                    <button
                        onClick={handleCreateNew}
                        className="w-full flex items-center justify-center gap-2 bg-brand-surface border border-brand-border text-brand-text-primary font-semibold px-3 py-2 rounded-lg hover:bg-brand-border transition-colors"
                    >
                        <PlusIcon className="w-4 h-4" />
                        <span>New Strategy</span>
                    </button>
                </div>
                <nav className="flex-1 overflow-y-auto p-2">
                    {strategies.map(strat => (
                        <button
                            key={strat.id}
                            onClick={() => handleSelectStrategy(strat.id)}
                            className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                                selectedStrategyId === strat.id
                                    ? 'bg-brand-primary/20 text-brand-primary'
                                    : 'text-brand-text-primary hover:bg-brand-surface'
                            }`}
                        >
                            {strat.name}
                        </button>
                    ))}
                </nav>
            </div>
        )
    };

    const renderViewport = () => {
        if (!selectedStrategyId && strategies.length > 0) {
             return (
                <div className="flex items-center justify-center h-full">
                    <div className="text-center text-brand-text-secondary">
                        <p className="font-semibold">Select a strategy to view or edit</p>
                        <p className="text-sm mt-1">Or create a new one to get started.</p>
                    </div>
                </div>
            );
        }
        
        return (
             <form onSubmit={handleSave} className="flex flex-col h-full p-6 space-y-4">
                 <h2 className="text-2xl font-bold text-brand-text-primary">
                    {selectedStrategyId ? 'Edit Strategy' : 'Create New Strategy'}
                </h2>
                <div>
                    <label htmlFor="name" className="block text-sm font-medium text-brand-text-secondary mb-1">
                        Strategy Name
                    </label>
                    <input
                        type="text"
                        id="name"
                        name="name"
                        value={formData.name}
                        onChange={handleChange}
                        placeholder="e.g., Conservative Trend Follower"
                        className="block w-full bg-brand-bg border border-brand-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand-primary focus:border-brand-primary sm:text-sm"
                    />
                </div>
                <div className="flex-1 flex flex-col">
                    <label htmlFor="prompt" className="block text-sm font-medium text-brand-text-secondary mb-1">
                        Strategy Prompt
                    </label>
                    <textarea
                        id="prompt"
                        name="prompt"
                        value={formData.prompt}
                        onChange={handleChange}
                        placeholder="Enter the detailed instructions for the AI trainer..."
                        className="flex-1 block w-full bg-brand-bg border border-brand-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand-primary focus:border-brand-primary sm:text-sm font-mono resize-none"
                    />
                </div>
                
                 {error && <p className="text-sm text-brand-negative">{error}</p>}

                <div className="pt-2 flex justify-between items-center">
                     <div>
                        {selectedStrategyId && (
                            <button
                                type="button"
                                onClick={handleDelete}
                                disabled={isSaving}
                                className="flex items-center justify-center gap-2 text-sm bg-brand-negative/10 text-brand-negative font-semibold px-4 py-2 rounded-md hover:bg-brand-negative/20 transition-colors disabled:opacity-50"
                            >
                                <TrashIcon className="w-4 h-4" />
                                <span>Delete</span>
                            </button>
                        )}
                    </div>
                    <button
                        type="submit"
                        disabled={isSaving}
                        className="flex items-center justify-center gap-2 bg-brand-primary text-white font-semibold px-6 py-2 rounded-lg hover:bg-brand-primary/80 transition-colors disabled:bg-brand-border disabled:text-brand-text-secondary disabled:cursor-not-allowed"
                    >
                        {isSaving ? (
                            <>
                                <SparklesIcon className="w-4 h-4 animate-pulse" />
                                <span>Saving...</span>
                            </>
                        ) : (
                            <span>Save Changes</span>
                        )}
                    </button>
                </div>
             </form>
        )
    };

     const renderTrainingSidebar = () => {
        return (
            <div className="flex flex-col h-full bg-brand-surface/50">
                <div className="p-4 border-b border-brand-border shrink-0 space-y-4">
                     <h3 className="text-lg font-bold text-brand-text-primary">Simulation & Training</h3>
                     <div className="space-y-2">
                         <label htmlFor="trading-pair" className="block text-sm font-medium text-brand-text-secondary">
                            1. Select Trading Pair
                         </label>
                         <select
                            id="trading-pair"
                            value={selectedPair}
                            onChange={(e) => setSelectedPair(e.target.value)}
                            className="w-full bg-brand-bg border border-brand-border rounded-md py-2 px-3 text-sm placeholder-brand-text-secondary focus:ring-1 focus:ring-brand-primary focus:border-brand-primary transition-all"
                        >
                            <option value="">Select Trading Pair...</option>
                            {tradingPairs.map(pair => (
                                <option key={pair} value={pair}>{pair}</option>
                            ))}
                        </select>
                     </div>
                     <button
                        onClick={handleTrain}
                        disabled={!selectedPair || isTraining || strategies.length === 0}
                        className="w-full flex items-center justify-center gap-2 bg-brand-primary text-white font-semibold px-4 py-2 rounded-lg hover:bg-brand-primary/80 transition-colors disabled:bg-brand-border disabled:text-brand-text-secondary disabled:cursor-not-allowed"
                    >
                        {isTraining ? (
                            <>
                                <SparklesIcon className="w-4 h-4 animate-spin" />
                                <span>Training...</span>
                            </>
                        ) : (
                            <>
                                <RocketIcon className="w-4 h-4" />
                                <span>Train with all {strategies.length} Strategies</span>
                            </>
                        )}
                    </button>
                </div>
                <div className="flex-1 flex flex-col p-4 min-h-0">
                     <h4 className="text-md font-semibold text-brand-text-primary mb-2 shrink-0">Training Log</h4>
                     <div ref={logContainerRef} className="flex-1 overflow-y-auto bg-black/20 p-2 rounded-md">
                        {trainingLog.length > 0 ? (
                            <pre className="text-xs whitespace-pre-wrap font-mono space-y-1.5">
                                {trainingLog.map((log, index) => {
                                    let colorClass = 'text-brand-text-secondary';
                                    if (log.result) {
                                        colorClass = log.result.performance.net_profit > 0 ? 'text-green-400' : 'text-red-400';
                                    } else if (log.content.includes('✔')) {
                                        colorClass = 'text-green-400';
                                    } else if (log.content.includes('❌')) {
                                        colorClass = 'text-red-400';
                                    }

                                    return (
                                        <div key={index}>
                                            <span className="text-gray-500">{`[${log.timestamp}] `}</span>
                                            <span className={colorClass}>{log.content}</span>
                                        </div>
                                    )
                                })}
                            </pre>
                        ) : (
                            <div className="flex items-center justify-center h-full text-center text-sm text-brand-text-secondary/50 p-4">
                                Logs will appear here when training starts.
                            </div>
                        )}
                     </div>
                </div>
            </div>
        );
    }
    
    return (
        <div className="h-full flex flex-col">
            <header className="p-4 lg:p-6 border-b border-brand-border shrink-0">
                <div>
                    <h1 className="text-3xl font-bold text-brand-text-primary">Strategy Studio</h1>
                    <p className="text-brand-text-secondary mt-1">Create and manage custom prompts to guide the AI Trainer.</p>
                </div>
            </header>
            <main className="flex-1 grid grid-cols-[320px_1fr_400px] overflow-hidden">
                <aside className="bg-brand-surface/50 border-r border-brand-border overflow-hidden">
                    {renderSidebar()}
                </aside>
                <div className="bg-brand-surface overflow-y-auto">
                    {renderViewport()}
                </div>
                 <aside className="border-l border-brand-border overflow-hidden">
                    {renderTrainingSidebar()}
                </aside>
            </main>
        </div>
    );
};