
import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { Portfolio, Trade, EquityPoint, PerformanceMetrics, BotStatus, StrategyPerformance, ActiveTrade, TrainedAsset } from './types';
import { BotStatusState, TradeDirection } from './types';
import * as api from './services/realApi';
import { KpiCard } from './components/KpiCard';
import { DataTable } from './components/DataTable';
import { LogViewer } from './components/LogViewer';
import { StatusIndicator } from './components/StatusIndicator';
import { ArrowDownIcon, BarChartIcon, HashIcon, ActivityIcon, ZapIcon, ChevronDownIcon, ChevronUpIcon, ListIcon, ClockIcon, TrendingUpIcon, DollarSignIcon, BrandIcon, LayoutDashboardIcon, BrainCircuitIcon, SettingsIcon } from './components/icons';
import { StrategyPerformanceTable } from './components/StrategyPerformanceTable';
import { Tabs } from './components/Tabs';
import { Skeleton } from './components/Skeleton';
import { UserSelector } from './components/UserSelector';
import { AssetAnalyticsModal } from './components/AssetAnalyticsModal';
import { AITrainer } from './components/AITrainer';
import { ExchangeSettings } from './components/ExchangeSettings';

const App: React.FC = () => {
    const [activeView, setActiveView] = useState<'dashboard' | 'trainer' | 'settings'>('dashboard');
    const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
    const [trades, setTrades] = useState<Trade[]>([]);
    const [logs, setLogs] = useState<string[]>([]);
    const [history, setHistory] = useState<EquityPoint[]>([]);
    const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
    const [status, setStatus] = useState<BotStatus>({ status: BotStatusState.STOPPED });
    const [patterns, setStrategies] = useState<StrategyPerformance[]>([]);
    const [activeTrades, setActiveTrades] = useState<ActiveTrade[]>([]);
    const [trainedAssets, setTrainedAssets] = useState<TrainedAsset[]>([]);
    const [loading, setLoading] = useState(true);
    const [isBottomPanelCollapsed, setIsBottomPanelCollapsed] = useState(true);
    const [currentUser, setCurrentUser] = useState<string>('user1');
    const [selectedAsset, setSelectedAsset] = useState<TrainedAsset | null>(null);

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

            // Fetch portfolio data with error handling
            const portfolioData = await api.getPortfolio(currentUser);
            
            if (portfolioData && portfolioData.portfolio) {
                setPortfolio(portfolioData.portfolio);
            } else {
                console.warn('Invalid portfolio data received:', portfolioData);
            }

            // Fetch other data with individual error handling
            try {
                const tradesData = await api.getTrades(currentUser);
                setTrades(Array.isArray(tradesData) ? tradesData : []);
            } catch (error) {
                console.warn('Failed to fetch trades:', error);
                setTrades([]);
            }

            try {
                const logsData = await api.getLogs(currentUser);
                setLogs(Array.isArray(logsData) ? logsData : []);
            } catch (error) {
                console.warn('Failed to fetch logs:', error);
                setLogs([]);
            }

            try {
                const historyData = await api.getPortfolioHistory(currentUser);
                setHistory(Array.isArray(historyData) ? historyData : []);
            } catch (error) {
                console.warn('Failed to fetch history:', error);
                setHistory([]);
            }

            try {
                const performanceData = await api.getPerformance(currentUser);
                setPerformance(performanceData);
            } catch (error) {
                console.warn('Failed to fetch performance:', error);
                setPerformance(null);
            }

            try {
                const statusData = await api.getStatus();
                setStatus(statusData);
            } catch (error) {
                console.warn('Failed to fetch status:', error);
                setStatus({ status: 'STOPPED' });
            }

            try {
                const strategiesData = await api.getStrategiesPerformance(currentUser);
                setStrategies(Array.isArray(strategiesData) ? strategiesData : []);
            } catch (error) {
                console.warn('Failed to fetch strategies:', error);
                setStrategies([]);
            }

            try {
                const activeTradesData = await api.getActiveTrades(currentUser);
                setActiveTrades(Array.isArray(activeTradesData) ? activeTradesData : []);
            } catch (error) {
                console.warn('Failed to fetch active trades:', error);
                setActiveTrades([]);
            }

            try {
                const trainedAssetsData = await api.getTrainedAssets(currentUser);
                setTrainedAssets(Array.isArray(trainedAssetsData) ? trainedAssetsData : []);
            } catch (error) {
                console.warn('Failed to fetch trained assets:', error);
                setTrainedAssets([]);
            }

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
    
    const handleUserChange = (userId: string) => {
        if (userId !== currentUser) {
            setCurrentUser(userId);
        }
    };

    const handleBottomTabClick = () => {
        if (isBottomPanelCollapsed) {
            setIsBottomPanelCollapsed(false);
        }
    };
    
    const refreshTrainedAssets = useCallback(async () => {
        const trainedAssetsData = await api.getTrainedAssets(currentUser);
        setTrainedAssets(trainedAssetsData);
    }, [currentUser]);

    const formatCurrency = (value: number | undefined) => {
        if (value === undefined) return '...';
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
    }
    
    const formatPercentage = (value: number) => {
        return `${(value * 100).toFixed(2)}%`;
    }

    const bottomTabs = [
        {
            label: "Live Logs",
            content: (
                <div className="h-full">
                    <LogViewer logs={logs} />
                </div>
            )
        },
        {
            label: "Overall Strategy Performance",
            content: (
                <div className="h-full overflow-y-auto">
                    <StrategyPerformanceTable patterns={strategies} />
                </div>
            )
        }
    ];
    
    const renderDashboard = () => {
        if (loading) {
            return (
                 <div className="flex flex-col h-full bg-brand-bg text-brand-text-primary font-sans overflow-hidden">
                    <header className="flex flex-wrap justify-between items-center gap-4 p-4 lg:p-6 border-b border-brand-border shrink-0">
                        <div className="flex items-center gap-3">
                            <Skeleton className="h-8 w-8 rounded-full" />
                            <Skeleton className="h-9 w-56" />
                        </div>
                        <div className="flex items-center space-x-4">
                            <Skeleton className="h-10 w-28" />
                             <Skeleton className="h-10 w-40" />
                        </div>
                    </header>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 p-4 lg:p-6 shrink-0">
                        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[76px]" />)}
                    </div>
                    <main className="flex-1 flex overflow-hidden">
                        <aside className="w-[320px] p-4 border-r border-brand-border">
                            <Skeleton className="h-full" />
                        </aside>
                        <div className="flex-1 p-4 lg:p-6"><Skeleton className="h-full" /></div>
                        <aside className="w-[400px] p-4 border-l border-brand-border">
                            <Skeleton className="h-full" />
                        </aside>
                    </main>
                    <footer className="h-80 bg-brand-surface border-t border-brand-border shrink-0 p-4 lg:p-6">
                         <Skeleton className="h-full" />
                    </footer>
                </div>
            )
        }
        
        return (
            <div className="flex flex-col h-full overflow-hidden">
                {/* KPIs */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 p-4 lg:p-6 shrink-0">
                    <KpiCard title="Total Equity" value={portfolio ? formatCurrency(portfolio.equity) : '...'} icon={<DollarSignIcon />} />
                    <KpiCard title="Total P/L" value={performance ? formatCurrency(performance.totalPL.value) : '...'} change={performance ? formatPercentage(performance.totalPL.percentage) : undefined} changeType={performance && performance.totalPL.value >= 0 ? 'positive' : 'negative'} icon={<BarChartIcon />} />
                    <KpiCard title="Sharpe Ratio" value={performance ? performance.sharpeRatio.toFixed(2) : '...'} icon={<ZapIcon />} />
                    <KpiCard title="Max Drawdown" value={performance ? formatPercentage(performance.maxDrawdown) : '...'} changeType="negative" icon={<ArrowDownIcon />} />
                    <KpiCard title="Win/Loss Ratio" value={performance ? performance.winLossRatio.toFixed(2) : '...'} icon={<HashIcon />} />
                    <KpiCard title="Total Trades" value={performance ? performance.totalTrades.toString() : '...'} icon={<ActivityIcon />} />
                </div>
    
                <main className="flex-1 flex overflow-hidden">
                    {/* Left Sidebar */}
                    <aside className="w-[320px] flex flex-col bg-brand-surface border-r border-brand-border overflow-hidden">
                         <div className="flex-1 flex flex-col p-4 overflow-hidden">
                            <div className="flex items-center gap-2 mb-4 text-brand-text-primary shrink-0">
                                <ListIcon className="w-5 h-5 text-brand-text-secondary" />
                                <h3 className="text-lg font-semibold">Trained Assets</h3>
                            </div>
                            <div className="flex-1 overflow-y-auto pr-2">
                                 <div className="space-y-2">
                                    {trainedAssets.map(asset => (
                                        <button 
                                            key={asset.symbol} 
                                            onClick={() => setSelectedAsset(asset)}
                                            className="w-full flex items-center justify-between p-3 rounded-lg bg-brand-bg hover:bg-brand-border transition-colors text-left"
                                        >
                                            <span className="font-semibold text-brand-text-primary">{asset.symbol}</span>
                                            <div className="flex items-center gap-2">
                                                {asset.patterns.map(p => (
                                                    <div 
                                                        key={p.strategyId}
                                                        className={`w-5 h-5 rounded-md flex items-center justify-center text-xs font-bold transition-all
                                                            ${p.status === 'ACTIVE' ? 'opacity-100' : 'opacity-30'}
                                                            ${p.totalPL >= 0 ? 'bg-brand-positive text-green-900' : 'bg-brand-negative text-red-900'}`}
                                                        title={`${p.initials} P/L: ${formatCurrency(p.totalPL)}`}
                                                    >
                                                        {p.initials}
                                                    </div>
                                                ))}
                                            </div>
                                        </button>
                                    ))}
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
    
                                    const rangeMin = Math.min(trade.takeProfit, trade.stopLoss);
                                    const rangeMax = Math.max(trade.takeProfit, trade.stopLoss);
                                    const range = rangeMax - rangeMin;
    
                                    if (range <= 0) return null;
    
                                    const getPosition = (price: number) => {
                                        const value = price - rangeMin;
                                        return Math.max(0, Math.min(100, (value / range) * 100));
                                    };
    
                                    const currentPrice = trade.currentPrice ?? trade.entryPrice;
                                    const entryPosition = getPosition(trade.entryPrice);
                                    const currentPosition = getPosition(currentPrice);
    
                                    let fillStart, fillWidth;
                                    if (currentPosition > entryPosition) {
                                        fillStart = entryPosition;
                                        fillWidth = currentPosition - entryPosition;
                                    } else {
                                        fillStart = currentPosition;
                                        fillWidth = entryPosition - currentPosition;
                                    }
    
                                    return (
                                    <div key={trade.id} className="bg-brand-bg p-4 rounded-lg border border-brand-border animate-fadeIn shrink-0">
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <div>
                                                    <span className="font-bold text-md text-brand-text-primary">{trade.symbol}</span>
                                                    <span className={`ml-2 font-semibold text-xs px-2 py-1 rounded-full ${isBuy ? 'bg-brand-positive/10 text-brand-positive' : 'bg-brand-negative/10 text-brand-negative'}`}>
                                                        {trade.direction}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-brand-text-secondary mt-1">{trade.strategyName}</p>
                                                <p className="text-xs text-brand-text-secondary mt-1">
                                                    Size: <span className="font-medium text-brand-text-primary">{formatCurrency(trade.quantity * trade.entryPrice)}</span>
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                 <p className="text-xs text-brand-text-secondary">Current P/L</p>
                                                 <p className={`text-lg font-bold ${isProfit ? 'text-brand-positive' : 'text-brand-negative'}`}>
                                                    {formatCurrency(trade.currentPL)}
                                                 </p>
                                            </div>
                                        </div>
    
                                        <div className="relative h-12">
                                            <div className="absolute top-1/2 -translate-y-1/2 w-full h-1 bg-brand-border rounded-full">
                                                <div 
                                                    className={`absolute h-full rounded-full ${isProfit ? 'bg-brand-positive' : 'bg-brand-negative'}`}
                                                    style={{ left: `${fillStart}%`, width: `${fillWidth}%` }}
                                                />
                                            </div>
    
                                            <div className="absolute top-1/2 -translate-x-1/2" style={{ left: `${entryPosition}%`}}>
                                                <div className="h-4 w-px bg-brand-text-secondary" />
                                                <p className="absolute -top-4 left-1/2 -translate-x-1/2 text-xs text-brand-text-secondary whitespace-nowrap">Entry</p>
                                            </div>
                                            
                                            <div className="absolute top-1/2 -translate-x-1/2 transition-all duration-300 ease-out" style={{ left: `${currentPosition}%`}}>
                                                <div className="h-2 w-2 rounded-full bg-brand-primary ring-2 ring-brand-bg" />
                                                <p className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs font-bold text-brand-primary whitespace-nowrap">{formatCurrency(currentPrice)}</p>
                                            </div>
    
                                            <div className="absolute top-0 left-0 text-left">
                                                <p className={`text-xs ${isBuy ? 'text-brand-negative' : 'text-brand-positive'}`}>{isBuy ? 'SL' : 'TP'}</p>
                                                <p className="text-xs font-medium">{formatCurrency(isBuy ? trade.stopLoss : trade.takeProfit)}</p>
                                            </div>
                                            <div className="absolute top-0 right-0 text-right">
                                                <p className={`text-xs ${isBuy ? 'text-brand-positive' : 'text-brand-negative'}`}>{isBuy ? 'TP' : 'SL'}</p>
                                                <p className="text-xs font-medium">{formatCurrency(isBuy ? trade.takeProfit : trade.stopLoss)}</p>
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
                
                <footer className={`bg-brand-surface border-t border-brand-border shrink-0 transition-all duration-300 ease-in-out ${isBottomPanelCollapsed ? 'h-[68px]' : 'h-80'}`}>
                    <div className="relative h-full">
                        <button 
                            onClick={() => setIsBottomPanelCollapsed(!isBottomPanelCollapsed)}
                            className="absolute top-3 right-4 z-20 p-2 rounded-full text-brand-text-secondary hover:bg-brand-border hover:text-brand-primary transition-colors"
                            aria-label={isBottomPanelCollapsed ? 'Expand Panel' : 'Collapse Panel'}
                        >
                            {isBottomPanelCollapsed ? <ChevronUpIcon className="w-5 h-5" /> : <ChevronDownIcon className="w-5 h-5" />}
                        </button>
                        <div className="p-4 lg:p-6 h-full">
                             <Tabs tabs={bottomTabs} isCollapsed={isBottomPanelCollapsed} onTabClick={handleBottomTabClick} />
                        </div>
                    </div>
                </footer>
                
                {selectedAsset && (
                    <AssetAnalyticsModal 
                        isOpen={!!selectedAsset}
                        onClose={() => setSelectedAsset(null)}
                        assetSymbol={selectedAsset.symbol}
                        userId={currentUser}
                        onStatusChange={refreshTrainedAssets}
                    />
                )}
            </div>
        );
    }

    const renderActiveView = () => {
        switch (activeView) {
            case 'dashboard':
                return renderDashboard();
            case 'trainer':
                return <AITrainer />;
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
                
                 <nav className="flex items-center space-x-1 bg-brand-surface p-1 rounded-lg">
                    <button 
                        onClick={() => setActiveView('dashboard')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${
                            activeView === 'dashboard' 
                            ? 'bg-brand-border text-brand-text-primary' 
                            : 'text-brand-text-secondary hover:bg-brand-border hover:text-brand-text-primary'
                        }`}
                    >
                        <LayoutDashboardIcon className="w-4 h-4" />
                        <span>Dashboard</span>
                    </button>
                     <button 
                        onClick={() => setActiveView('trainer')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${
                            activeView === 'trainer' 
                            ? 'bg-brand-border text-brand-text-primary' 
                            : 'text-brand-text-secondary hover:bg-brand-border hover:text-brand-text-primary'
                        }`}
                    >
                        <BrainCircuitIcon className="w-4 h-4" />
                        <span>AI Trainer</span>
                    </button>
                     <button 
                        onClick={() => setActiveView('settings')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${
                            activeView === 'settings' 
                            ? 'bg-brand-border text-brand-text-primary' 
                            : 'text-brand-text-secondary hover:bg-brand-border hover:text-brand-text-primary'
                        }`}
                    >
                        <SettingsIcon className="w-4 h-4" />
                        <span>Settings</span>
                    </button>
                </nav>

                <div className="flex items-center space-x-4 justify-end">
                    {activeView === 'dashboard' && <StatusIndicator status={status.status} />}
                    <UserSelector users={users} selectedUser={currentUser} onSelectUser={handleUserChange} />
                </div>
            </header>
            
            <div className="flex-1 overflow-y-auto">
                {renderActiveView()}
            </div>
        </div>
    );
};

export default App;
