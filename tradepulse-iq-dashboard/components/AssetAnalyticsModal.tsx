import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Modal } from './Modal';
import * as api from '../services/realApi';
import type { TrainedAssetDetails, Trade, RegimePerformance, ExchangePerformance, StrategyParameters } from '../types';
import { StrategyStatus } from '../types';
import { Skeleton } from './Skeleton';
import { PlayIcon, PauseIcon, ChevronDownIcon, ChevronUpIcon, ClipboardCopyIcon, SparklesIcon, ReceiptIcon, TimerIcon, ShuffleIcon } from './icons';
import { DataTable } from './DataTable';

interface AssetAnalyticsModalProps {
    isOpen: boolean;
    onClose: () => void;
    assetSymbol: string;
    userId: string;
    onStatusChange: () => void; // Callback to refresh sidebar
}

const formatCurrency = (value: number | undefined) => {
    if (value === undefined) return '...';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

const formatPercent = (value: number, decimals = 1) => `${(value * 100).toFixed(decimals)}%`;

const ParameterDisplay: React.FC<{ params: StrategyParameters }> = ({ params }) => {
    const renderParam = (label: string, value: any) => (
        <div>
            <span className="text-brand-text-secondary mr-2 capitalize">{label.replace(/([A-Z])/g, ' $1')}:</span>
            <span className="font-semibold text-brand-text-primary bg-brand-border/50 px-2 py-1 rounded">{String(value)}</span>
        </div>
    );
    
    return (
         <div className="grid md:grid-cols-3 gap-6 text-sm">
            <div className="bg-brand-bg/30 p-3 rounded-md border border-brand-border/50">
                 <h6 className="font-semibold text-brand-text-primary mb-2">Primary Signal ({params.primaryTimeframe})</h6>
                 <div className="space-y-1.5">
                    {Object.entries(params.primarySignal).map(([key, value]) => renderParam(key, value))}
                 </div>
            </div>
             <div className="bg-brand-bg/30 p-3 rounded-md border border-brand-border/50">
                 <h6 className="font-semibold text-brand-text-primary mb-2">Macro Confirmation ({params.macroTimeframe})</h6>
                 <div className="space-y-1.5">
                     {renderParam('Trend Filter', params.macroConfirmation.trendFilter)}
                     {renderParam('Required State', params.macroConfirmation.requiredState)}
                 </div>
            </div>
             <div className="bg-brand-bg/30 p-3 rounded-md border border-brand-border/50">
                <h6 className="font-semibold text-brand-text-primary mb-2">Risk Management</h6>
                 <div className="space-y-1.5">
                    {Object.entries(params.riskManagement).map(([key, value]) => renderParam(key, value))}
                </div>
            </div>
        </div>
    );
};

const ExchangeDisplay: React.FC<{ ex: ExchangePerformance; onToggle: () => void }> = ({ ex, onToggle }) => (
     <div className="flex items-center gap-4 text-xs p-2 bg-brand-bg/50 rounded-md border border-brand-border/50">
        <p className="font-semibold text-brand-text-primary w-20 shrink-0">{ex.exchange}</p>
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-x-4 gap-y-2">
            <div title="Win Rate">
                <p className={`font-mono font-semibold text-sm ${ex.winRate >= 0.55 ? 'text-brand-positive' : 'text-brand-negative'}`}>{formatPercent(ex.winRate)}</p>
            </div>
            <div title="Average Profit">
                <p className="font-mono text-brand-positive text-sm">{formatCurrency(ex.avgProfit)}</p>
            </div>
             <div title="Average Loss">
                <p className="font-mono text-brand-negative text-sm">{formatCurrency(ex.avgLoss)}</p>
            </div>
             <div title="Total P/L">
                <p className={`font-mono font-semibold text-sm ${ex.totalPL >= 0 ? 'text-brand-positive' : 'text-brand-negative'}`}>{formatCurrency(ex.totalPL)}</p>
            </div>
            <div className="flex items-center gap-1.5" title="Average Slippage">
                <ShuffleIcon className="w-3.5 h-3.5 text-brand-text-secondary" />
                <p className="font-mono text-brand-text-secondary">{formatPercent(ex.avgSlippage, 2)}</p>
            </div>
             <div className="flex items-center gap-1.5" title="Average Fees">
                <ReceiptIcon className="w-3.5 h-3.5 text-brand-text-secondary" />
                <p className="font-mono text-brand-text-secondary">{formatPercent(ex.avgFees, 2)}</p>
            </div>
            <div className="flex items-center gap-1.5" title="Average Latency">
                <TimerIcon className="w-3.5 h-3.5 text-brand-text-secondary" />
                <p className="font-mono text-brand-text-secondary">{ex.avgLatencyMs}ms</p>
            </div>
        </div>
         <button
            onClick={(e) => { e.stopPropagation(); onToggle(); }}
            className="ml-4 p-2 rounded-full text-brand-text-secondary hover:bg-brand-border hover:text-brand-primary transition-colors"
            aria-label={ex.status === StrategyStatus.ACTIVE ? `Pause on ${ex.exchange}` : `Activate on ${ex.exchange}`}
        >
            {ex.status === StrategyStatus.ACTIVE ? <PauseIcon className="w-4 h-4" /> : <PlayIcon className="w-4 h-4" />}
        </button>
    </div>
);


const RegimeDisplay: React.FC<{ 
    regime: RegimePerformance;
    onToggle: () => void;
    onToggleExchange: (exchangeName: string) => void;
}> = ({ regime, onToggle, onToggleExchange }) => (
    <div className="space-y-2">
        <div className="flex items-center gap-4 text-sm p-2 bg-brand-surface/50 rounded-md">
            <p className="font-bold text-brand-text-primary w-28 shrink-0">{regime.regime}</p>
            <p className="flex-1 text-xs text-brand-text-secondary">Toggle all exchanges for this regime</p>
            <button
                onClick={(e) => { e.stopPropagation(); onToggle(); }}
                className="ml-4 p-2 rounded-full text-brand-text-secondary hover:bg-brand-border hover:text-brand-primary transition-colors"
                aria-label={regime.status === StrategyStatus.ACTIVE ? `Pause ${regime.regime}` : `Activate ${regime.regime}`}
            >
                {regime.status === StrategyStatus.ACTIVE ? <PauseIcon className="w-4 h-4" /> : <PlayIcon className="w-4 h-4" />}
            </button>
        </div>
        <div className="pl-6 space-y-1.5">
            {regime.exchangePerformance.map(ex => <ExchangeDisplay key={ex.exchange} ex={ex} onToggle={() => onToggleExchange(ex.exchange)} />)}
        </div>
    </div>
);

const PatternAccordion: React.FC<{
    pattern: TrainedAssetDetails['patterns'][0];
    onToggle: () => void;
    onToggleRegime: (regimeName: string) => void;
    onToggleExchange: (regimeName: string, exchangeName: string) => void;
    isOpen: boolean;
    onHeaderClick: () => void;
}> = ({ pattern, onToggle, onToggleRegime, onToggleExchange, isOpen, onHeaderClick }) => {
    const isOverallProfit = pattern.analytics.avgProfit > Math.abs(pattern.analytics.avgLoss);

    return (
        <div className="bg-brand-surface/50 border border-brand-border rounded-lg overflow-hidden transition-all duration-300">
            <header
                className="flex items-center p-4 cursor-pointer hover:bg-brand-border/30"
                onClick={onHeaderClick}
                aria-expanded={isOpen}
                aria-controls={`pattern-content-${pattern.id}`}
            >
                <div className="flex-1 grid grid-cols-4 gap-4 items-center">
                    <h4 className="text-md font-bold text-brand-text-primary col-span-1 flex items-center gap-2">
                        {isOpen ? <ChevronUpIcon className="w-4 h-4" /> : <ChevronDownIcon className="w-4 h-4" />}
                        {pattern.name}
                    </h4>
                    <div>
                        <p className="text-xs text-brand-text-secondary">Win Rate</p>
                        <p className={`font-semibold ${isOverallProfit ? 'text-brand-positive' : 'text-brand-negative'}`}>{formatPercent(pattern.analytics.winRate)}</p>
                    </div>
                    <div>
                        <p className="text-xs text-brand-text-secondary">Avg. Profit</p>
                        <p className="font-semibold text-brand-positive">{formatCurrency(pattern.analytics.avgProfit)}</p>
                    </div>
                    <div>
                        <p className="text-xs text-brand-text-secondary">Avg. Loss</p>
                        <p className="font-semibold text-brand-negative">{formatCurrency(pattern.analytics.avgLoss)}</p>
                    </div>
                </div>
                <button
                    onClick={(e) => { e.stopPropagation(); onToggle(); }}
                    className="ml-4 p-2 rounded-full text-brand-text-secondary hover:bg-brand-border hover:text-brand-primary transition-colors"
                    aria-label={pattern.status === StrategyStatus.ACTIVE ? `Pause ${pattern.name}` : `Activate ${pattern.name}`}
                >
                    {pattern.status === StrategyStatus.ACTIVE ? <PauseIcon /> : <PlayIcon />}
                </button>
            </header>
            {isOpen && (
                <div id={`pattern-content-${pattern.id}`} className="p-4 border-t border-brand-border bg-black/20 animate-fadeIn space-y-6">
                    <div>
                        <h5 className="text-sm font-semibold text-brand-text-secondary mb-3">Performance by Market Regime & Exchange</h5>
                        <div className="space-y-4">
                            {pattern.regimePerformance.map(regime => (
                                <RegimeDisplay
                                    key={regime.regime}
                                    regime={regime}
                                    onToggle={() => onToggleRegime(regime.regime)}
                                    onToggleExchange={(exchangeName) => onToggleExchange(regime.regime, exchangeName)}
                                />
                            ))}
                        </div>
                    </div>
                    <div>
                        <h5 className="text-sm font-semibold text-brand-text-secondary mb-3">Multi-Timeframe Parameters</h5>
                        <ParameterDisplay params={pattern.parameters} />
                    </div>
                    <div>
                        <h5 className="text-sm font-semibold text-brand-text-secondary mb-3">Recent Live Trades</h5>
                        {pattern.recentTrades.length > 0 ? (
                            <div className="max-h-48 overflow-y-auto border border-brand-border rounded-md">
                                <DataTable
                                    headers={['Time', 'Side', 'P/L', 'Quantity']}
                                    data={pattern.recentTrades.map(t => [
                                        new Date(t.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' }),
                                        <span key={`${t.id}-dir`} className={`font-semibold ${t.direction === 'BUY' ? 'text-brand-positive' : 'text-brand-negative'}`}>{t.direction}</span>,
                                        <span key={`${t.id}-pnl`} className={`font-semibold ${t.pnl === undefined ? '' : t.pnl >= 0 ? 'text-brand-positive' : 'text-brand-negative'}`}>
                                            {formatCurrency(t.pnl)}
                                        </span>,
                                        t.quantity.toFixed(4)
                                    ])}
                                />
                            </div>
                        ) : <p className="text-sm text-brand-text-secondary text-center py-4">No recent trades for this pattern.</p>}
                    </div>
                </div>
            )}
        </div>
    );
};

export const AssetAnalyticsModal: React.FC<AssetAnalyticsModalProps> = ({ isOpen, onClose, assetSymbol, userId, onStatusChange }) => {
    const [details, setDetails] = useState<TrainedAssetDetails | null>(null);
    const [loading, setLoading] = useState(true);
    const [expandedPatternId, setExpandedPatternId] = useState<string | null>(null);
    const [aiFeedback, setAiFeedback] = useState('');
    const [isRetraining, setIsRetraining] = useState(false);
    const [copySuccess, setCopySuccess] = useState('');

    const fetchData = useCallback(async () => {
        if (!assetSymbol || !userId) return;
        setLoading(true);
        try {
            const data = await api.getAssetDetails(userId, assetSymbol);
            setDetails(data);
        } catch (error) {
            console.error(`Failed to fetch details for ${assetSymbol}`, error);
            setDetails(null);
        } finally {
            setLoading(false);
        }
    }, [assetSymbol, userId]);

    useEffect(() => {
        if (isOpen) {
            fetchData();
        } else {
            // Reset state when modal closes
            setExpandedPatternId(null);
            setAiFeedback('');
            setIsRetraining(false);
        }
    }, [isOpen, fetchData]);

    const handleToggleStatus = async (strategyId: string) => {
        await api.toggleStrategyStatusForAsset(userId, assetSymbol, strategyId);
        await fetchData();
        onStatusChange();
    };
    
    const handleToggleRegimeStatus = async (strategyId: string, regimeName: string) => {
        await api.togglePatternRegimeStatus(userId, assetSymbol, strategyId, regimeName);
        await fetchData();
    };
    
    const handleToggleExchangeStatus = async (strategyId: string, regimeName: string, exchangeName: string) => {
        await api.togglePatternRegimeExchangeStatus(userId, assetSymbol, strategyId, regimeName, exchangeName);
        await fetchData();
    };

    const handleToggleAccordion = (strategyId: string) => {
        setExpandedPatternId(currentId => currentId === strategyId ? null : strategyId);
    };
    
    const analysisPrompt = useMemo(() => {
        if (!details) return '';
        
        const formatParams = (params: StrategyParameters) => {
            let pString = `Primary TF: ${params.primaryTimeframe}, Macro TF: ${params.macroTimeframe}\n`;
            pString += `    Primary Signal: ${JSON.stringify(params.primarySignal)}\n`;
            pString += `    Macro Confirmation: ${JSON.stringify(params.macroConfirmation)}\n`;
            pString += `    Risk Management: ${JSON.stringify(params.riskManagement)}`;
            return pString;
        }

        let prompt = `Analyze the following trading performance data for asset ${details.symbol} and provide specific, actionable recommendations to improve overall profitability. Suggest modifications to parameters, or rules for enabling/disabling patterns in specific regimes or on specific exchanges. Consider exchange-specific factors like fees, slippage and latency. Format your response as a JSON object with a single key "recommendations" containing your analysis as a string.\n\n`;

        details.patterns.forEach(p => {
            prompt += `---
Pattern: "${p.name}"
Master Status: ${p.status}
Parameters:\n  ${formatParams(p.parameters).replace(/\n/g, '\n  ')}
Overall Win Rate: ${formatPercent(p.analytics.winRate)}, Avg Profit: ${formatCurrency(p.analytics.avgProfit)}, Avg Loss: ${formatCurrency(p.analytics.avgLoss)}

${p.regimePerformance.map(r => 
`\n  Regime: ${r.regime}
  Master Status for Regime: ${r.status}
${r.exchangePerformance.map(ex =>
`    Exchange: ${ex.exchange}
    - Status: ${ex.status}
    - Win Rate: ${formatPercent(ex.winRate)}
    - Total P/L: ${formatCurrency(ex.totalPL)}
    - Avg Profit: ${formatCurrency(ex.avgProfit)}
    - Avg Loss: ${formatCurrency(ex.avgLoss)}
    - Avg Slippage: ${formatPercent(ex.avgSlippage, 3)}
    - Avg Fees: ${formatPercent(ex.avgFees, 3)}
    - Avg Latency: ${ex.avgLatencyMs}ms`
).join('\n')}`
).join('')}

Recent Trades for "${p.name}":
${p.recentTrades.length > 0 ? p.recentTrades.map(t => 
`  - ${new Date(t.timestamp).toISOString()}: ${t.direction} ${t.quantity.toFixed(4)} ${p.name}, P/L: ${formatCurrency(t.pnl)}`
).join('\n') : '  - No recent trades.'}
\n`;
        });
        return prompt;
    }, [details]);

    const handleCopyPrompt = () => {
        navigator.clipboard.writeText(analysisPrompt).then(() => {
            setCopySuccess('Copied!');
            setTimeout(() => setCopySuccess(''), 2000);
        }, () => {
            setCopySuccess('Failed to copy');
            setTimeout(() => setCopySuccess(''), 2000);
        });
    };
    
    const handleRetrain = async () => {
        if (!aiFeedback.trim()) return;
        setIsRetraining(true);
        try {
            await api.retrainAssetWithFeedback(userId, assetSymbol, aiFeedback);
            setAiFeedback('');
            await fetchData();
        } catch (error) {
            console.error("Retraining failed", error);
        } finally {
            setIsRetraining(false);
        }
    };


    const renderContent = () => {
        if (loading) {
            return (
                <div className="space-y-4">
                    {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
                </div>
            );
        }
        if (!details || !details.patterns.length) {
            return (
                <div className="text-center text-brand-text-secondary">
                    Could not load analytics data for {assetSymbol}.
                </div>
            );
        }
        
        return (
            <div className="space-y-8">
                <div className="space-y-2">
                    {details.patterns.map(pattern => (
                        <PatternAccordion
                            key={pattern.id}
                            pattern={pattern}
                            onToggle={() => handleToggleStatus(pattern.id)}
                            onToggleRegime={(regimeName) => handleToggleRegimeStatus(pattern.id, regimeName)}
                            onToggleExchange={(regimeName, exchangeName) => handleToggleExchangeStatus(pattern.id, regimeName, exchangeName)}
                            isOpen={expandedPatternId === pattern.id}
                            onHeaderClick={() => handleToggleAccordion(pattern.id)}
                        />
                    ))}
                </div>

                <div className="bg-brand-surface/50 border border-brand-border rounded-lg p-6 space-y-6">
                     <div>
                        <h3 className="text-lg font-bold text-brand-text-primary mb-2">AI Analysis & Refinement</h3>
                        <p className="text-sm text-brand-text-secondary">Use an external AI to analyze this asset's performance. Copy the prompt below, paste it into your AI of choice, then paste the AI's response to retrain and refine the model.</p>
                    </div>
                    
                    <div>
                        <label className="block text-sm font-semibold text-brand-text-primary mb-2">Step 1: Generate & Copy Analysis Prompt</label>
                        <div className="relative">
                            <pre className="text-xs whitespace-pre-wrap font-mono text-brand-text-secondary bg-brand-bg/50 p-4 rounded-md max-h-48 overflow-y-auto">
                                {analysisPrompt}
                            </pre>
                            <button
                                onClick={handleCopyPrompt}
                                className="absolute top-2 right-2 flex items-center gap-1.5 bg-brand-border text-brand-text-secondary text-xs font-semibold px-2 py-1 rounded hover:bg-brand-primary hover:text-white transition-colors"
                            >
                                <ClipboardCopyIcon className="w-3 h-3" />
                                {copySuccess || 'Copy'}
                            </button>
                        </div>
                    </div>
                    
                    <div>
                        <label htmlFor="ai-feedback" className="block text-sm font-semibold text-brand-text-primary mb-2">Step 2: Submit AI Feedback to Retrain</label>
                        <textarea
                            id="ai-feedback"
                            value={aiFeedback}
                            onChange={(e) => setAiFeedback(e.target.value)}
                            disabled={isRetraining}
                            placeholder="Paste the JSON response from your AI here to begin retraining..."
                            className="w-full h-28 p-2 bg-brand-bg/50 border border-brand-border rounded-md text-sm text-brand-text-primary focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition"
                        />
                        <button
                            onClick={handleRetrain}
                            disabled={isRetraining || !aiFeedback.trim()}
                            className="mt-2 flex items-center justify-center gap-2 w-full bg-brand-primary text-white font-semibold px-4 py-2 rounded-lg hover:bg-brand-primary/80 transition-colors disabled:bg-brand-border disabled:text-brand-text-secondary disabled:cursor-not-allowed"
                        >
                            {isRetraining ? (
                                <>
                                    <SparklesIcon className="w-4 h-4 animate-pulse" />
                                    <span>Retraining in progress...</span>
                                </>
                            ) : (
                                <>
                                    <SparklesIcon className="w-4 h-4" />
                                    <span>Retrain with AI Feedback</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`Analytics for ${assetSymbol}`}>
            {renderContent()}
        </Modal>
    );
};