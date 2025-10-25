import React, { useMemo, useState, useRef, useEffect } from 'react';
import type { TrainedConfiguration } from '../types';
import { BrainCircuitIcon, LayoutGridIcon, ListOrderedIcon, RotateCcwIcon, ChevronDownIcon, ServerIcon, SearchIcon, ZapIcon } from './icons';

interface TrainedAssetsProps {
    assets: TrainedConfiguration[] | null;
    onClear: () => void;
    serverLatency: number;
    onActivateVisible: (visibleIds: string[]) => void;
    onSelectConfig: (config: TrainedConfiguration) => void;
}

// Utility function to format relative time
const formatRelativeTime = (isoTimestamp: string | undefined): string => {
    if (!isoTimestamp) return 'Unknown';
    
    const now = new Date();
    const past = new Date(isoTimestamp);
    const diffMs = now.getTime() - past.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHr / 24);
    
    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    
    return past.toLocaleDateString();
};

const LifecycleBadge: React.FC<{ stage: TrainedConfiguration['lifecycle_stage'] }> = ({ stage }) => {
    const config = {
        DISCOVERY: 'bg-purple-500/10 text-purple-400',
        VALIDATION: 'bg-sky-500/10 text-sky-400',
        MATURE: 'bg-green-500/10 text-green-400',
        DECAY: 'bg-yellow-500/10 text-yellow-400',
        PAPER: 'bg-gray-500/10 text-gray-400',
    };
    const color = config[stage] || config.PAPER;
    return <span className={`px-2 py-1 text-xs font-bold rounded-full ${color}`}>{stage}</span>;
}

const AssetCard: React.FC<{ asset: TrainedConfiguration; onClick: () => void }> = ({ asset, onClick }) => {
    const isProfitable = asset.performance.net_profit > 0;
    return (
        <div 
            onClick={onClick}
            className={`bg-brand-surface border rounded-lg p-4 flex flex-col gap-3 animate-fadeIn transition-all hover:-translate-y-1 cursor-pointer ${asset.isActive ? 'border-brand-primary ring-2 ring-brand-primary/50' : 'border-brand-border hover:border-brand-primary/50'}`}
        >
            <header className="flex justify-between items-start">
                <div>
                    <h3 className="font-bold text-brand-text-primary">{asset.pair}</h3>
                    <p className="text-xs text-brand-text-secondary">{asset.exchange} - {asset.timeframe}</p>
                    <p className="text-xs text-brand-text-secondary mt-0.5">
                        Trained {formatRelativeTime(asset.created_at)}
                        {asset.training_settings?.optimizer && (
                            <span className="ml-1">• {asset.training_settings.optimizer}</span>
                        )}
                    </p>
                </div>
                <LifecycleBadge stage={asset.lifecycle_stage} />
            </header>
            
            <div className="text-xs text-brand-text-secondary truncate" title={asset.strategy_name}>
                Strategy: <span className="font-semibold text-brand-text-primary">{asset.strategy_name}</span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-brand-bg/50 p-2 rounded-md">
                    <p className="text-xs text-brand-text-secondary">Gross WR</p>
                    <p className="text-lg font-bold font-mono text-brand-primary">{asset.performance.gross_win_rate.toFixed(1)}%</p>
                </div>
                <div className="bg-brand-bg/50 p-2 rounded-md">
                    <p className="text-xs text-brand-text-secondary">Net Profit %</p>
                    <p className={`text-lg font-bold font-mono ${isProfitable ? 'text-brand-positive' : 'text-brand-negative'}`}>{asset.performance.net_profit.toFixed(2)}%</p>
                </div>
                 <div className="bg-brand-bg/50 p-2 rounded-md">
                    <p className="text-xs text-brand-text-secondary">Sharpe</p>
                    <p className="text-lg font-bold font-mono text-brand-text-primary">{asset.validation.sharpe_ratio.toFixed(2)}</p>
                </div>
            </div>

            <footer className="text-xs text-brand-text-secondary text-center">
                Sample Size: {asset.performance.sample_size} trades
            </footer>
        </div>
    );
}

const AssetListItem: React.FC<{ asset: TrainedConfiguration; onClick: () => void }> = ({ asset, onClick }) => {
    const isProfitable = asset.performance.net_profit > 0;
    return (
        <div 
            onClick={onClick}
            className={`grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr_1fr_1fr] items-center gap-4 text-sm p-3 bg-brand-surface rounded-md border transition-colors cursor-pointer ${asset.isActive ? 'border-brand-primary' : 'border-transparent hover:border-brand-border/50'}`}
        >
            <div>
                <p className="font-semibold text-brand-text-primary">{asset.pair}</p>
                <p className="text-xs text-brand-text-secondary truncate">{asset.strategy_name}</p>
                <p className="text-xs text-brand-text-secondary">{formatRelativeTime(asset.created_at)}</p>
            </div>
            <p className="text-xs text-brand-text-secondary">{asset.exchange}</p>
            <p className="text-xs text-brand-text-secondary">{asset.timeframe}</p>
            <p className="font-mono font-semibold text-brand-primary">{asset.performance.gross_win_rate.toFixed(1)}%</p>
            <p className={`font-mono font-semibold ${isProfitable ? 'text-brand-positive' : 'text-brand-negative'}`}>{asset.performance.net_profit.toFixed(2)}%</p>
            <p className="font-mono text-brand-text-primary">{asset.validation.sharpe_ratio.toFixed(2)}</p>
            <p className="text-xs text-brand-text-secondary">{asset.performance.sample_size}</p>
            <p className="text-xs text-brand-text-secondary capitalize">{asset.training_settings?.optimizer || '-'}</p>
            <LifecycleBadge stage={asset.lifecycle_stage} />
        </div>
    );
}


export const TrainedAssets: React.FC<TrainedAssetsProps> = ({ assets, onClear, serverLatency, onActivateVisible, onSelectConfig }) => {
    const [selectedStages, setSelectedStages] = useState<TrainedConfiguration['lifecycle_stage'][]>([]);
    const [isFilterOpen, setIsFilterOpen] = useState(false);
    const [view, setView] = useState<'grid' | 'list'>('grid');
    const [serverLoad, setServerLoad] = useState(100);
    const filterRef = useRef<HTMLDivElement>(null);
    const [searchQuery, setSearchQuery] = useState('');

    const allStages: TrainedConfiguration['lifecycle_stage'][] = ['DISCOVERY', 'VALIDATION', 'MATURE', 'DECAY', 'PAPER'];

    const getLatencyColor = () => {
        if (serverLatency > 150) return 'text-brand-negative';
        if (serverLatency > 100) return 'text-yellow-400';
        return 'text-brand-positive';
    };

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
                setIsFilterOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleStageToggle = (stage: TrainedConfiguration['lifecycle_stage']) => {
        setSelectedStages(prev => 
            prev.includes(stage) 
                ? prev.filter(s => s !== stage)
                : [...prev, stage]
        );
    };

    const filteredAndSortedAssets = useMemo(() => {
        if (!assets) return [];
        
        let processedAssets = [...assets];

        const query = searchQuery.toLowerCase();
        if (query) {
             processedAssets = processedAssets.filter(a => 
                a.pair.toLowerCase().includes(query) ||
                a.strategy_name.toLowerCase().includes(query) ||
                a.exchange.toLowerCase().includes(query)
            );
        }

        // Filter by lifecycle stage if any stages are selected
        if (selectedStages.length > 0) {
            processedAssets = processedAssets.filter(a => selectedStages.includes(a.lifecycle_stage));
        }

        // Always sort by net profit, highest to lowest
        processedAssets.sort((a, b) => b.performance.net_profit - a.performance.net_profit);
        
        const countToShow = Math.ceil(processedAssets.length * (serverLoad / 100));
        return processedAssets.slice(0, countToShow);

    }, [assets, selectedStages, serverLoad, searchQuery]);
    
    const handleActivateVisible = () => {
        const visibleIds = filteredAndSortedAssets.map(asset => asset.id);
        onActivateVisible(visibleIds);
    };


    // The total width of the slider track is 256px. The thumb is 20px wide.
    // The slidable range for the thumb's center is from 10px (half thumb width) to 246px (total width - half thumb width).
    // This gives a total travel distance of 236px.
    // We map the serverLoad value (1-100) to this pixel range to position the fill's end at the thumb's center.
    const sliderFillWidth = 10 + ((serverLoad - 1) / 99) * 236;

    return (
        <div className="p-4 lg:p-6 h-full flex flex-col">
            <header className="shrink-0 flex justify-between items-start">
                <div>
                    <h1 className="text-3xl font-bold text-brand-text-primary">Trained Assets</h1>
                    <p className="text-brand-text-secondary mt-1">Review training results and activate promising configurations for live trading.</p>
                </div>
                
                {/* Server Load & Latency Widget */}
                <div className="bg-brand-surface p-4 rounded-lg border border-brand-border grid grid-cols-[1fr_auto_1fr] items-center gap-6">
                    {/* Column 1: Config Load */}
                    <div className="space-y-2">
                        <div className="flex items-center gap-3">
                            <h3 className="text-sm font-semibold text-brand-text-primary">Active Configuration Load</h3>
                            <span className="text-xs text-brand-text-secondary font-mono">
                                {filteredAndSortedAssets.length} / {assets?.length || 0} Configs
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <ServerIcon className="w-5 h-5 text-brand-text-secondary" title="Adjust server load by changing number of displayed configurations."/>
                            <div className="slider-container">
                                <div className="slider-track-fill" style={{ width: `${sliderFillWidth}px` }}></div>
                                <input
                                    type="range"
                                    min="1"
                                    max="100"
                                    value={serverLoad}
                                    onChange={(e) => setServerLoad(Number(e.target.value))}
                                    className="server-load-slider"
                                    title={`Showing top ${serverLoad}% of configurations`}
                                />
                            </div>
                            <span className="text-sm font-mono font-semibold text-brand-text-primary w-10 text-right">{serverLoad}%</span>
                        </div>
                    </div>

                    {/* Column 2: Divider */}
                    <div className="h-12 w-px bg-brand-border"></div>

                    {/* Column 3: Server Latency */}
                    <div className="flex flex-col items-center justify-center">
                        <h3 className="text-sm font-semibold text-brand-text-primary mb-2">Server Latency</h3>
                        <div className="flex items-center justify-center gap-2">
                            <div className={`w-2.5 h-2.5 rounded-full animate-pulse ${getLatencyColor().replace('text-','bg-')}`}></div>
                            <span className={`text-2xl font-mono font-semibold ${getLatencyColor()}`}>{serverLatency}ms</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* Controls Bar */}
            <div className="shrink-0 flex justify-between items-center mt-6 py-2 border-y border-brand-border">
                <div className="flex items-center gap-4">
                    {/* Search Bar */}
                    <div className="relative flex items-center">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Filter configs..."
                            className="w-56 bg-brand-surface border border-brand-border rounded-md py-1.5 pl-4 pr-8 text-sm placeholder-brand-text-secondary focus:ring-1 focus:ring-brand-primary focus:border-brand-primary transition-all"
                        />
                        <SearchIcon className="absolute right-3 w-4 h-4 text-brand-text-secondary pointer-events-none" />
                    </div>

                    {/* Filter Controls */}
                     <div ref={filterRef} className="relative">
                        <button 
                            onClick={() => setIsFilterOpen(!isFilterOpen)}
                            className="flex items-center gap-2 text-sm bg-brand-surface border border-brand-border font-semibold px-3 py-1.5 rounded-md hover:bg-brand-border transition-colors"
                        >
                            <span>Filter by Stage</span>
                             {selectedStages.length > 0 && (
                                <span className="bg-brand-primary text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">{selectedStages.length}</span>
                            )}
                            <ChevronDownIcon className={`w-4 h-4 text-brand-text-secondary transition-transform ${isFilterOpen ? 'rotate-180' : ''}`} />
                        </button>
                        {isFilterOpen && (
                            <div className="absolute top-full mt-2 w-56 bg-brand-surface border border-brand-border rounded-lg shadow-lg z-10 p-2 animate-fadeIn">
                                {allStages.map(stage => (
                                    <label key={stage} className="flex items-center gap-2 p-2 rounded-md hover:bg-brand-border cursor-pointer">
                                        <input 
                                            type="checkbox"
                                            checked={selectedStages.includes(stage)}
                                            onChange={() => handleStageToggle(stage)}
                                            className="h-4 w-4 rounded bg-brand-bg border-brand-border text-brand-primary focus:ring-brand-primary"
                                        />
                                        <LifecycleBadge stage={stage} />
                                    </label>
                                ))}
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleActivateVisible}
                        className="flex items-center gap-2 text-sm bg-brand-primary/10 text-brand-primary border border-brand-primary/50 font-semibold px-3 py-1.5 rounded-md hover:bg-brand-primary/20 transition-colors"
                        title="Activate all visible configurations and deactivate all others"
                    >
                        <ZapIcon className="w-4 h-4"/>
                        <span>Activate Visible</span>
                    </button>
                   
                    {assets && assets.length > 0 && (
                         <button
                            onClick={onClear}
                            className="flex items-center gap-2 text-sm text-brand-text-secondary hover:text-brand-negative font-semibold transition-colors pl-4 border-l border-brand-border"
                            title="Clear all trained asset results"
                        >
                            <RotateCcwIcon className="w-4 h-4" />
                            <span>Clear All</span>
                        </button>
                    )}
                </div>

                <div className="flex items-center gap-4">
                    {/* View Toggles */}
                    <div className="flex items-center gap-1 bg-brand-surface p-1 rounded-md">
                        <button 
                            onClick={() => setView('grid')}
                            className={`p-2 rounded transition-colors ${view === 'grid' ? 'bg-brand-primary text-white' : 'text-brand-text-secondary hover:bg-brand-border'}`}
                            aria-label="Grid View"
                        >
                            <LayoutGridIcon className="w-4 h-4" />
                        </button>
                        <button 
                            onClick={() => setView('list')}
                            className={`p-2 rounded transition-colors ${view === 'list' ? 'bg-brand-primary text-white' : 'text-brand-text-secondary hover:bg-brand-border'}`}
                            aria-label="List View"
                        >
                            <ListOrderedIcon className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
            
            <main className="mt-4 flex-1 overflow-y-auto pr-2">
                {!assets ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="text-center text-brand-text-secondary">
                            <BrainCircuitIcon className="w-12 h-12 mx-auto mb-4" />
                            <h2 className="text-xl font-semibold text-brand-text-primary">No Models Trained Yet</h2>
                            <p className="mt-2">Go to the <span className="font-semibold text-brand-primary">Strategy Studio</span> to select a pair and train your models.</p>
                        </div>
                    </div>
                ) : filteredAndSortedAssets.length === 0 ? (
                     <div className="flex items-center justify-center h-full">
                        <div className="text-center text-brand-text-secondary">
                            <h2 className="text-xl font-semibold text-brand-text-primary">No Matching Assets</h2>
                            <p className="mt-2">No models found with the selected filters. Try adjusting your search or filters.</p>
                        </div>
                    </div>
                ) : view === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
                        {filteredAndSortedAssets.map(asset => (
                            <AssetCard key={asset.id} asset={asset} onClick={() => onSelectConfig(asset)} />
                        ))}
                    </div>
                ) : (
                    <div className="space-y-2">
                         <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr_1fr_1fr] items-center gap-4 text-xs p-3 text-brand-text-secondary font-semibold border-b border-brand-border">
                            <span>Pair / Strategy</span>
                            <span>Exchange</span>
                            <span>Timeframe</span>
                            <span>Gross WR</span>
                            <span>Net Profit</span>
                            <span>Sharpe</span>
                            <span>Trades</span>
                            <span>Optimizer</span>
                            <span>Stage</span>
                        </div>
                        {filteredAndSortedAssets.map(asset => (
                            <AssetListItem key={asset.id} asset={asset} onClick={() => onSelectConfig(asset)} />
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
};
