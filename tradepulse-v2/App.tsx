
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { Portfolio, Trade, PerformanceMetrics, BotStatus, StrategyPerformance, ActiveTrade, TrainedAsset, TrainedConfiguration } from './types';
import { BotStatusState, TradeDirection } from './types';
import * as api from './services/realApi';
import { KpiCard } from './components/KpiCard';
import { DataTable } from './components/DataTable';
import { LogViewer } from './components/LogViewer';
import { StatusIndicator } from './components/StatusIndicator';
import { ArrowDownIcon, BarChartIcon, HashIcon, ActivityIcon, ZapIcon, ChevronDownIcon, ChevronUpIcon, ListIcon, ClockIcon, TrendingUpIcon, DollarSignIcon, BrandIcon, LayoutDashboardIcon, SettingsIcon, SearchIcon, BookOpenIcon, ClipboardCheckIcon } from './components/icons';
import { StrategyPerformanceTable } from './components/StrategyPerformanceTable';
import { Tabs } from './components/Tabs';
import { Skeleton } from './components/Skeleton';
import { UserSelector } from './components/UserSelector';
import { ConfigurationDetailModal } from './components/ConfigurationDetailModal';
import { ConfigurationCard } from './components/ConfigurationCard';
import { TrainedAssets } from './components/TrainedAssets';
import { ExchangeSettings } from './components/ExchangeSettings';
import { StrategyStudio } from './components/StrategyStudio';

type Timeframe = '24h' | '7d' | '30d' | 'lifetime';
type SortMetric = 'net_profit' | 'win_rate';
type SortDirection = 'top' | 'lowest';
type ActiveView = 'dashboard' | 'trainedAssets' | 'settings' | 'strategyStudio';
type MetricType = 'live' | 'trained';


const App: React.FC = () => {
    const [activeView, setActiveView] = useState<ActiveView>('dashboard');
    const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
    const [trades, setTrades] = useState<Trade[]>([]);
    const [logs, setLogs] = useState<string[]>([]);
    const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
    const [status, setStatus] = useState<BotStatus>({ status: BotStatusState.STOPPED });
    const [strategies, setStrategies] = useState<StrategyPerformance[]>([]);
    const [activeTrades, setActiveTrades] = useState<ActiveTrade[]>([]);
    const [loading, setLoading] = useState(true);
    const [isBottomPanelCollapsed, setIsBottomPanelCollapsed] = useState(true);
    const [currentUser, setCurrentUser] = useState<string>('user1');
    const [assetSearchQuery, setAssetSearchQuery] = useState('');
    const [sortConfig, setSortConfig] = useState<{ metric: SortMetric, direction: SortDirection }>({ metric: 'net_profit', direction: 'top' });
    const [trainedConfigurations, setTrainedConfigurations] = useState<TrainedConfiguration[] | null>(null);
    const [serverLatency, setServerLatency] = useState<number>(0);
    const [selectedConfig, setSelectedConfig] = useState<TrainedConfiguration | null>(null);
    const [metricType, setMetricType] = useState<MetricType>('live');


    // FIX: Use `ReturnType<typeof setInterval>` instead of `NodeJS.Timeout` for browser compatibility.
    const dataFetchInterval = useRef<ReturnType<typeof setInterval> | null>(null);


    const users = [
        { id: 'user1', name: 'User Alpha' },
        { id: 'user2', name: 'User Bravo' },
    ];

    const fetchData = useCallback(async (isInitial = false) => {
        if (activeView !== 'dashboard') return;
        try {
            if (isInitial) setLoading(true);

            // FIX: Fetch only non-auth endpoints for now
            // Auth endpoints (portfolio, trades, logs, performance, strategies, activeTrades) 
            // will be enabled once authentication is properly set up
            const statusData = await api.getStatus();
            setStatus(statusData);

        } catch (error) {
            console.error("Failed to fetch data:", error);
        } finally {
            if (isInitial) setLoading(false);
        }
    }, [currentUser, activeView]);

    useEffect(() => {
        if (dataFetchInterval.current) {
            clearInterval(dataFetchInterval.current);
        }
        if (activeView === 'dashboard') {
            fetchData(true); // Initial load
            dataFetchInterval.current = setInterval(() => fetchData(false), 2000);
        }
        return () => {
             if (dataFetchInterval.current) {
                clearInterval(dataFetchInterval.current);
            }
        };
    }, [currentUser, fetchData, activeView]);

    // NEW useEffect for latency
    useEffect(() => {
        const fetchLatency = async () => {
            try {
                const latencyData = await api.getServerLatency();
                setServerLatency(latencyData);
            } catch (error) {
                console.error("Failed to fetch server latency:", error);
            }
        };
        
        fetchLatency();
        const interval = setInterval(fetchLatency, 2500);
        return () => clearInterval(interval);
    }, []); // Run only once on mount
    
    // NEW useEffect for training configurations (no auth required)
    useEffect(() => {
        const fetchTrainingConfigurations = async () => {
            try {
                const configs = await api.getTrainedConfigurations(currentUser);
                setTrainedConfigurations(prev => {
                    // Preserve isActive state during updates
                    const activeStateMap = new Map(prev?.map(c => [c.id, c.isActive]));
                    return configs.map(c => ({
                        ...c,
                        isActive: activeStateMap.get(c.id) || false
                    }));
                });
            } catch (error) {
                console.error("Failed to fetch training configurations:", error);
            }
        };

        // Fetch immediately
        fetchTrainingConfigurations();

        // Set up interval to refresh every 5 seconds
        const interval = setInterval(fetchTrainingConfigurations, 5000);
        return () => clearInterval(interval);
    }, [currentUser]);

    const handleUserChange = (userId: string) => {
        if (userId !== currentUser) {
            setCurrentUser(userId);
        }
    };
    
    const handleTrainingComplete = (results: TrainedConfiguration[]) => {
        const newConfigsWithState = results.map(r => ({...r, isActive: false}));
        setTrainedConfigurations(prev => [...(prev || []), ...newConfigsWithState]);
        setActiveView('trainedAssets');
    }

    const handleClearTrainedAssets = () => {
        // This is now less relevant as data is not pre-seeded, but can be a reset function.
        // For now, we'll just clear the state. A real implementation might call an API.
        setTrainedConfigurations([]);
    }
    
    const handleActivateVisibleConfigs = (visibleIds: string[]) => {
        // Update local state for immediate UI feedback
        setTrainedConfigurations(prev => {
            if (!prev) return null;
            const visibleIdSet = new Set(visibleIds);
            return prev.map(config => ({
                ...config,
                isActive: visibleIdSet.has(config.id)
            }));
        });
        // Update the backend/mock service so the simulation knows which configs are active
        api.updateActiveConfigs(visibleIds);
    };

    const formatCurrency = (value: number | undefined) => {
        if (value === undefined) return '...';
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
    }
    
    const formatPercentage = (value: number) => {
        return `${(value * 100).toFixed(2)}%`;
    }
    
    const liveMetricsByConfig = useMemo(() => {
        const metrics = new Map<string, { wins: number; losses: number; totalPL: number; totalCost: number }>();

        // Process closed trades
        trades.forEach(trade => {
            if (!trade.configId) return;
            const stats = metrics.get(trade.configId) || { wins: 0, losses: 0, totalPL: 0, totalCost: 0 };
            stats.totalPL += trade.pnl || 0;
            stats.totalCost += trade.fill_cost || 0;
            if ((trade.pnl || 0) >= 0) {
                stats.wins++;
            } else {
                stats.losses++;
            }
            metrics.set(trade.configId, stats);
        });

        // Process active trades
        activeTrades.forEach(trade => {
            if (!trade.configId) return;
            const stats = metrics.get(trade.configId) || { wins: 0, losses: 0, totalPL: 0, totalCost: 0 };
            stats.totalPL += trade.currentPL;
            // FIX: Include the cost of active trades in the total cost basis for an accurate Net Profit %
            stats.totalCost += trade.quantity * trade.entryPrice;
            metrics.set(trade.configId, stats);
        });

        return metrics;
    }, [trades, activeTrades]);

    const filteredAndSortedConfigurations = useMemo(() => {
        if (!trainedConfigurations) return [];
    
        const query = assetSearchQuery.toLowerCase();
    
        // The user wants to see *only* active configurations on the dashboard carousel.
        // So, we first filter by `isActive`, then apply the search query and sorting on that subset.
        const filtered = trainedConfigurations
            .filter(config => config.isActive)
            .filter(config => 
                config.pair.toLowerCase().includes(query) ||
                config.strategy_name.toLowerCase().includes(query) ||
                config.exchange.toLowerCase().includes(query)
            );
    
        const { metric, direction } = sortConfig;
        filtered.sort((a, b) => {
            const valA = metric === 'net_profit' ? a.performance.net_profit : a.performance.gross_win_rate;
            const valB = metric === 'net_profit' ? b.performance.net_profit : b.performance.gross_win_rate;
            return direction === 'top' ? valB - valA : valA - valB;
        });
        
        return filtered;
    }, [trainedConfigurations, assetSearchQuery, sortConfig]);
    
    const renderDashboard = () => {
        if (loading) {
            return (
                <div className="flex flex-col h-full overflow-hidden">
                    <div className="shrink-0 bg-brand-surface/50 border-b border-brand-border p-4 space-y-3">
                        <Skeleton className="h-6 w-48 mb-3" />
                        <div className="flex gap-4 overflow-hidden">
                            {Array.from({ length: 8 }).map((_, i) => (
                                <Skeleton key={i} className="h-36 w-72 flex-shrink-0" />
                            ))}
                        </div>
                    </div>
                    <main className="flex-1 flex overflow-hidden">
                        <aside className="w-[320px] p-4 lg:p-6 border-r border-brand-border flex flex-col gap-6 bg-brand-surface">
                            <div>
                                <Skeleton className="h-6 w-48 mb-4" />
                                <div className="space-y-3">
                                    {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[76px]" />)}
                                </div>
                            </div>
                        </aside>
                        <div className="flex-1 p-4 lg:p-6 bg-brand-surface">
                            <Skeleton className="h-full" />
                        </div>
                        <aside className="w-[400px] p-4 border-l border-brand-border bg-brand-surface">
                            <Skeleton className="h-full" />
                        </aside>
                    </main>
                </div>
            )
        }
        
        return (
            <div className="flex flex-col h-full overflow-hidden">
                 {/* Trained Configurations Carousel */}
                 <section className="shrink-0 bg-brand-surface/50 border-b border-brand-border p-4 space-y-3">
                    <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-2 text-brand-text-primary">
                            <ListIcon className="w-5 h-5 text-brand-text-secondary" />
                            <h3 className="text-lg font-semibold">Active Configurations</h3>
                        </div>
                        <div className="flex items-center gap-4">
                             <div className="flex items-center gap-1 bg-brand-bg p-1 rounded-md border border-brand-border">
                                <button
                                    onClick={() => setMetricType('live')}
                                    className={`px-2 py-1 text-xs font-semibold rounded transition-colors ${metricType === 'live' ? 'bg-brand-primary text-white' : 'text-brand-text-secondary hover:bg-brand-border'}`}
                                >
                                    Live %
                                </button>
                                <button
                                    onClick={() => setMetricType('trained')}
                                    className={`px-2 py-1 text-xs font-semibold rounded transition-colors ${metricType === 'trained' ? 'bg-brand-primary text-white' : 'text-brand-text-secondary hover:bg-brand-border'}`}
                                >
                                    Trained %
                                </button>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="flex items-center gap-1 bg-brand-bg p-1 rounded-md border border-brand-border">
                                    <button 
                                        onClick={() => setSortConfig({ metric: 'net_profit', direction: 'top'})}
                                        className={`px-2 py-1 text-xs font-semibold rounded transition-colors ${sortConfig.metric === 'net_profit' && sortConfig.direction === 'top' ? 'bg-brand-primary text-white' : 'text-brand-text-secondary hover:bg-brand-border'}`}
                                    >
                                        Top Net Profit %
                                    </button>
                                    <button 
                                        onClick={() => setSortConfig({ metric: 'net_profit', direction: 'lowest'})}
                                        className={`px-2 py-1 text-xs font-semibold rounded transition-colors ${sortConfig.metric === 'net_profit' && sortConfig.direction === 'lowest' ? 'bg-brand-primary text-white' : 'text-brand-text-secondary hover:bg-brand-border'}`}
                                    >
                                        Lowest Net Profit %
                                    </button>
                                </div>
                                <div className="flex items-center gap-1 bg-brand-bg p-1 rounded-md border border-brand-border">
                                    <button 
                                        onClick={() => setSortConfig({ metric: 'win_rate', direction: 'top'})}
                                        className={`px-2 py-1 text-xs font-semibold rounded transition-colors ${sortConfig.metric === 'win_rate' && sortConfig.direction === 'top' ? 'bg-brand-primary text-white' : 'text-brand-text-secondary hover:bg-brand-border'}`}
                                    >
                                        Top WR
                                    </button>
                                    <button 
                                        onClick={() => setSortConfig({ metric: 'win_rate', direction: 'lowest'})}
                                        className={`px-2 py-1 text-xs font-semibold rounded transition-colors ${sortConfig.metric === 'win_rate' && sortConfig.direction === 'lowest' ? 'bg-brand-primary text-white' : 'text-brand-text-secondary hover:bg-brand-border'}`}
                                    >
                                        Lowest WR
                                    </button>
                                </div>
                            </div>
                            <div className="relative flex items-center">
                                <input
                                    type="text"
                                    value={assetSearchQuery}
                                    onChange={(e) => setAssetSearchQuery(e.target.value)}
                                    placeholder="Search active configs..."
                                    className="w-56 bg-brand-bg border border-brand-border rounded-full py-1.5 pl-4 pr-8 text-sm placeholder-brand-text-secondary focus:ring-1 focus:ring-brand-primary focus:border-brand-primary transition-all"
                                />
                                <SearchIcon className="absolute right-3 w-4 h-4 text-brand-text-secondary pointer-events-none" />
                            </div>
                        </div>
                    </div>

                    <div className="flex gap-4 overflow-x-auto pb-2 -mb-2">
                        {trainedConfigurations === null ? (
                            Array.from({ length: 8 }).map((_, i) => (
                                <Skeleton key={i} className="h-36 w-72 flex-shrink-0" />
                            ))
                        ) : filteredAndSortedConfigurations.length > 0 ? (
                            filteredAndSortedConfigurations.map(config => {
                                const isUntraded = config.performance.sample_size === 0;
                                let displayNetProfit = isUntraded ? 0 : config.performance.net_profit * 100;
                                let displayWinRate = isUntraded ? 0 : config.performance.gross_win_rate;

                                if (metricType === 'live') {
                                    const liveData = liveMetricsByConfig.get(config.id);
                                    const wins = liveData?.wins || 0;
                                    const losses = liveData?.losses || 0;
                                    const totalClosedTrades = wins + losses;
                                    displayWinRate = totalClosedTrades > 0 ? (wins / totalClosedTrades) * 100 : 0;
                                    
                                    const totalCost = liveData?.totalCost || 0;
                                    const totalPL = liveData?.totalPL || 0;
                                    displayNetProfit = totalCost > 0 ? (totalPL / totalCost) * 100 : 0;
                                }

                                return (
                                    <ConfigurationCard 
                                        key={config.id}
                                        config={config}
                                        onClick={() => setSelectedConfig(config)}
                                        displayNetProfit={displayNetProfit}
                                        displayWinRate={displayWinRate}
                                        metricType={metricType}
                                    />
                                );
                            })
                        ) : (
                             <div className="w-full text-center py-8 text-sm text-brand-text-secondary">
                                {trainedConfigurations.length === 0 
                                    ? "No configurations trained yet. Go to the Strategy Studio to begin." 
                                    : !trainedConfigurations.some(c => c.isActive)
                                        ? "No configurations are active. Go to the Trained Assets page to activate them."
                                        : `No active configurations found matching "${assetSearchQuery}".`
                                }
                            </div>
                        )}
                    </div>
                </section>

                <main className="flex-1 flex overflow-hidden">
                    {/* Left Sidebar */}
                    <aside className="w-[320px] flex flex-col bg-brand-surface border-r border-brand-border overflow-hidden">
                         <div className="flex-1 flex flex-col p-4 lg:p-6 space-y-6 overflow-hidden">
                            {/* KPIs Section */}
                            <div className="shrink-0">
                                <div className="flex items-center gap-2 mb-4 text-brand-text-primary">
                                    <BarChartIcon className="w-5 h-5 text-brand-text-secondary" />
                                    <h3 className="text-lg font-semibold">Portfolio Snapshot</h3>
                                </div>
                                <div className="flex flex-col gap-3">
                                    <KpiCard title="Total Equity" value={portfolio ? formatCurrency(portfolio.equity) : '...'} icon={<DollarSignIcon />} />
                                    <KpiCard title="Total P/L" value={performance ? formatCurrency(performance.totalPL.value) : '...'} change={performance ? formatPercentage(performance.totalPL.percentage) : undefined} changeType={performance && performance.totalPL.value >= 0 ? 'positive' : 'negative'} icon={<BarChartIcon />} />
                                    <KpiCard title="Sharpe Ratio" value={performance ? performance.sharpeRatio.toFixed(2) : '...'} icon={<ZapIcon />} />
                                    <KpiCard title="Max Drawdown" value={performance ? formatPercentage(performance.maxDrawdown) : '...'} changeType="negative" icon={<ArrowDownIcon />} />
                                    <KpiCard title="Win/Loss Ratio" value={performance ? performance.winLossRatio.toFixed(2) : '...'} icon={<HashIcon />} />
                                    <KpiCard title="Total Trades" value={performance ? performance.totalTrades.toString() : '...'} icon={<ActivityIcon />} />
                                </div>
                            </div>
                        </div>
                    </aside>
    
                    {/* Main Content: Active Trades */}
                    <div className="flex-1 bg-brand-surface flex flex-col p-4 lg:p-6 overflow-hidden">
                        <div className="flex items-center gap-2 mb-4 text-brand-text-primary shrink-0">
                            <TrendingUpIcon className="w-5 h-5 text-brand-text-secondary" />
                            <h3 className="text-lg font-semibold">Active Trades</h3>
                        </div>
                        <div className="flex-1 overflow-y-auto flex flex-col gap-4 pr-2">
                             {activeTrades.length > 0 ? (
                                activeTrades.map(trade => {
                                    const isBuy = trade.direction === TradeDirection.BUY;
                                    const isProfit = trade.currentPL >= 0;
                                    const pnlPercentage = (trade.quantity * trade.entryPrice) !== 0
                                        ? trade.currentPL / (trade.quantity * trade.entryPrice)
                                        : 0;
    
                                    // The gauge's scale is now fixed: SL on the left (0%), TP on the right (100%).
                                    const rangeMin = trade.stopLoss;
                                    const rangeMax = trade.takeProfit;
                                    const range = rangeMax - rangeMin;
    
                                    if (range === 0) return null;
    
                                    const getPosition = (price: number) => {
                                        const value = price - rangeMin;
                                        const position = (value / range) * 100;
                                        return Math.max(0, Math.min(100, position));
                                    };
    
                                    const currentPrice = trade.currentPrice ?? trade.entryPrice;
                                    const entryPosition = getPosition(trade.entryPrice);
                                    const currentPosition = getPosition(currentPrice);
                                    const slPosition = getPosition(trade.stopLoss);
                                    const tpPosition = getPosition(trade.takeProfit);

                                    const daysTraded = Math.floor((new Date().getTime() - new Date(trade.startTimestamp).getTime()) / (1000 * 60 * 60 * 24));
    
                                    let fillStart, fillWidth;
                                    if (currentPosition > entryPosition) {
                                        fillStart = entryPosition;
                                        fillWidth = currentPosition - entryPosition;
                                    } else {
                                        fillStart = currentPosition;
                                        fillWidth = entryPosition - currentPosition;
                                    }
    
                                    return (
                                        <div key={trade.id} className="bg-brand-bg p-4 rounded-lg border border-brand-border animate-fadeIn shrink-0 transition-all duration-300 hover:-translate-y-1">
                                            {/* Header */}
                                            <div className="grid grid-cols-12 gap-4 items-center mb-4">
                                                {/* Col 1: Config Info */}
                                                <div className="col-span-5">
                                                    <div className="flex items-center justify-between">
                                                        <div>
                                                            <div className="flex items-baseline gap-2">
                                                                <span className="font-bold text-lg text-brand-text-primary">{trade.pair}</span>
                                                                <span className="text-xs text-brand-text-secondary font-semibold">{trade.exchange} &middot; {trade.timeframe}</span>
                                                            </div>
                                                            <p className="text-xs text-brand-text-secondary mt-1 truncate" title={trade.strategyName}>{trade.strategyName}</p>
                                                        </div>
                                                         <span className={`font-semibold text-xs px-2 py-1 rounded-full ${isBuy ? 'bg-brand-positive/10 text-brand-positive' : 'bg-brand-negative/10 text-brand-negative'}`}>
                                                            {trade.direction}
                                                        </span>
                                                    </div>
                                                </div>

                                                {/* Col 2: P/L */}
                                                <div className="pl-4 border-l border-brand-border col-span-3 text-center">
                                                    <span className="text-xs text-brand-text-secondary">Total P/L</span>
                                                    <p className={`text-xl font-bold font-mono ${isProfit ? 'text-brand-positive' : 'text-brand-negative'}`}>
                                                        {formatCurrency(trade.currentPL)}
                                                    </p>
                                                </div>

                                                {/* Col 3: Size */}
                                                <div className="pl-4 border-l border-brand-border col-span-2 text-center">
                                                    <span className="text-xs text-brand-text-secondary">Position Size</span>
                                                    <p className="font-mono text-base font-semibold text-brand-text-primary">
                                                        {formatCurrency(trade.quantity * trade.entryPrice)}
                                                    </p>
                                                </div>

                                                {/* Col 4: Duration */}
                                                <div className="pl-4 border-l border-brand-border col-span-2 text-center">
                                                    <span className="text-xs text-brand-text-secondary">Duration</span>
                                                    <p className="font-mono text-base font-semibold text-brand-text-primary">
                                                        {daysTraded} Day{daysTraded !== 1 ? 's' : ''}
                                                    </p>
                                                </div>
                                            </div>
                                            
                                            {/* Trade Gauge */}
                                            <div className="relative h-20">
                                                <div className="relative w-[95%] mx-auto h-full">
                                                    {/* P/L % Indicator */}
                                                    <div 
                                                        className="absolute top-0 text-center -translate-x-1/2 transition-all duration-500 ease-in-out" 
                                                        style={{ left: `${currentPosition}%` }}
                                                    >
                                                        <p className={`text-xs font-semibold ${isProfit ? 'text-brand-positive' : 'text-brand-negative'}`}>
                                                            ({isProfit ? '+' : ''}{formatPercentage(pnlPercentage)})
                                                        </p>
                                                    </div>

                                                    {/* Background Bar */}
                                                    <div className="absolute top-6 h-3 w-full rounded-full bg-brand-border" />
                                                    
                                                    {/* The P/L Bar */}
                                                     <div 
                                                        className={`absolute top-6 h-3 transition-all duration-500 ease-in-out ${isProfit ? 'bg-brand-positive' : 'bg-brand-negative'}`}
                                                        style={{ 
                                                            left: `${fillStart}%`, 
                                                            width: `${fillWidth}%`,
                                                        } as React.CSSProperties}
                                                    />

                                                    {/* Markers */}
                                                    <div className="absolute top-12" style={{ left: `${slPosition}%`}}>
                                                        <div className="text-left">
                                                            <p className="text-xs font-semibold text-brand-negative">SL</p>
                                                            <p className="text-xs font-mono text-brand-text-secondary whitespace-nowrap">{formatCurrency(trade.stopLoss)}</p>
                                                        </div>
                                                    </div>
                                                    
                                                    <div className="absolute top-12" style={{ left: `${tpPosition}%`}}>
                                                        <div className="text-right -translate-x-full">
                                                            <p className="text-xs font-semibold text-brand-positive">TP</p>
                                                            <p className="text-xs font-mono text-brand-text-secondary whitespace-nowrap">{formatCurrency(trade.takeProfit)}</p>
                                                        </div>
                                                    </div>

                                                    <div className="absolute top-12" style={{ left: `${entryPosition}%`}}>
                                                        <div className="text-center -translate-x-1/2">
                                                            <p className="text-xs font-semibold text-brand-text-secondary">Entry</p>
                                                            <p className="text-xs font-mono text-brand-text-secondary whitespace-nowrap">{formatCurrency(trade.entryPrice)}</p>
                                                        </div>
                                                    </div>
                                                    
                                                    {/* Current Price Orb */}
                                                    <div className="absolute top-6 -translate-x-1/2 transition-all duration-500 ease-in-out" style={{ left: `${currentPosition}%`}}>
                                                        <div className="h-3 w-3 rounded-full bg-brand-text-primary ring-4 ring-brand-bg animate-pulse-indicator" />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })
                            ) : (
                                <div className="flex items-center justify-center h-full">
                                    <p className="text-center text-brand-text-secondary">
                                        No active trades.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
    
                    {/* Right Sidebar: Recent Trades */}
                    <aside className="w-[400px] flex flex-col bg-brand-surface border-l border-brand-border overflow-hidden">
                        <div className="flex-1 flex flex-col p-4 overflow-hidden">
                            <div className="flex items-center gap-2 mb-2 text-brand-text-primary shrink-0">
                                <ClockIcon className="w-5 h-5 text-brand-text-secondary" />
                                <h3 className="text-lg font-semibold">Recent Trades</h3>
                            </div>
                            <div className="flex-1 relative">
                                <div className="absolute inset-0">
                                    <DataTable 
                                        headers={['Time', 'Symbol', 'Side', 'P/L']}
                                        data={trades.slice(0, 50).map(t => [
                                            new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                                            t.symbol,
                                            <span key={`${t.id}-dir`} className={`font-semibold ${t.direction === 'BUY' ? 'text-brand-positive' : 'text-brand-negative'}`}>{t.direction}</span>,
                                            <span key={`${t.id}-pnl`} className={`font-semibold ${t.pnl === undefined ? '' : t.pnl >= 0 ? 'text-brand-positive' : 'text-brand-negative'}`}>
                                                {formatCurrency(t.pnl)}
                                            </span>
                                        ])}
                                    />
                                </div>
                            </div>
                        </div>
                    </aside>
                </main>
            </div>
        );
    }

    const renderActiveView = () => {
        switch (activeView) {
            case 'dashboard':
                return renderDashboard();
            case 'trainedAssets':
                return <TrainedAssets 
                    assets={trainedConfigurations} 
                    onClear={handleClearTrainedAssets} 
                    serverLatency={serverLatency} 
                    onActivateVisible={handleActivateVisibleConfigs}
                />;
            case 'strategyStudio':
                return <StrategyStudio currentUser={currentUser} onTrainingComplete={handleTrainingComplete} />;
            case 'settings':
                return <ExchangeSettings currentUser={currentUser} />;
            default:
                return renderDashboard();
        }
    }

    return (
        <div className="flex flex-col h-screen bg-brand-bg text-brand-text-primary font-sans overflow-hidden">
            <header className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] items-center gap-4 p-4 lg:p-6 border-b border-brand-border shrink-0">
                <div className="flex items-center gap-3">
                    <BrandIcon className="w-8 h-8 text-brand-primary animate-pulse-glow" />
                    <div>
                        <h1 className="text-3xl font-bold text-brand-text-primary">TradePulse IQ</h1>
                        <p className="text-sm text-brand-text-secondary -mt-1">Deep Learning AI-Trading Agent</p>
                    </div>
                </div>
                
                 <nav className="flex items-center space-x-1 bg-brand-surface p-1 rounded-full">
                    <button 
                        onClick={() => setActiveView('dashboard')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-colors ${
                            activeView === 'dashboard' 
                            ? 'bg-brand-primary text-white shadow-md' 
                            : 'text-brand-text-secondary hover:bg-brand-border hover:text-brand-text-primary'
                        }`}
                    >
                        <LayoutDashboardIcon className="w-4 h-4" />
                        <span>Dashboard</span>
                    </button>
                    <button 
                        onClick={() => setActiveView('strategyStudio')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-colors ${
                            activeView === 'strategyStudio' 
                            ? 'bg-brand-primary text-white shadow-md' 
                            : 'text-brand-text-secondary hover:bg-brand-border hover:text-brand-text-primary'
                        }`}
                    >
                        <BookOpenIcon className="w-4 h-4" />
                        <span>Strategy Studio</span>
                    </button>
                     <button 
                        onClick={() => setActiveView('trainedAssets')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-colors ${
                            activeView === 'trainedAssets' 
                             ? 'bg-brand-primary text-white shadow-md' 
                            : 'text-brand-text-secondary hover:bg-brand-border hover:text-brand-text-primary'
                        }`}
                    >
                        <ClipboardCheckIcon className="w-4 h-4" />
                        <span>Trained Assets</span>
                    </button>
                     <button 
                        onClick={() => setActiveView('settings')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-colors ${
                            activeView === 'settings' 
                             ? 'bg-brand-primary text-white shadow-md' 
                            : 'text-brand-text-secondary hover:bg-brand-border hover:text-brand-text-primary'
                        }`}
                    >
                        <SettingsIcon className="w-4 h-4" />
                        <span>Settings</span>
                    </button>
                </nav>

                <div className="flex justify-end items-center space-x-4">
                    <StatusIndicator status={status.status} />
                    <UserSelector users={users} selectedUser={currentUser} onSelectUser={handleUserChange} />
                </div>
            </header>
            <div className="flex-1 flex flex-col overflow-hidden">
                {renderActiveView()}
            </div>
            <ConfigurationDetailModal
                isOpen={!!selectedConfig}
                onClose={() => setSelectedConfig(null)}
                config={selectedConfig}
            />
        </div>
    );
};

export default App;
