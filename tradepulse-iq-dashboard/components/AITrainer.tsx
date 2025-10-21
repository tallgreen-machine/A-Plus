import React, { useState, useEffect, useCallback, useMemo, FC } from 'react';
import * as api from '../services/realApi';
import type { AssetRanking, TrainingStatus, TrainingResults, PatternViability, WalkForwardResult, PatternImplementation } from '../types';
import { TrainingPhase } from '../types';
import { Skeleton } from './Skeleton';
import {
    RocketIcon,
    BrainCircuitIcon,
    CheckCircle2Icon,
    XCircleIcon,
    AlertTriangleIcon,
    CpuIcon,
    FlaskConicalIcon,
    ClipboardCheckIcon,
    BarChartBigIcon,
    FileTextIcon,
    RotateCwIcon,
    InfoIcon,
} from './icons';
import { Tabs } from './Tabs';
import { DataTable } from './DataTable';
import { Modal } from './Modal';

type View = 'rankings' | 'training' | 'results';

const formatCurrency = (value: number | undefined) => {
    if (value === undefined) return '...';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

const RiskBadge: FC<{ level: 'Low' | 'Medium' | 'High' }> = ({ level }) => {
    const config = {
        Low: 'bg-sky-500/10 text-sky-400',
        Medium: 'bg-yellow-500/10 text-yellow-400',
        High: 'bg-red-500/10 text-red-400',
    };
    return <span className={`px-2 py-1 text-xs font-bold rounded-full ${config[level]}`}>{level} Risk</span>;
};

const ScoreBar: FC<{ score: number }> = ({ score }) => {
    const percentage = Math.max(0, Math.min(100, score));
    let colorClass = 'bg-brand-positive';
    if (percentage < 70) colorClass = 'bg-yellow-500';
    if (percentage < 55) colorClass = 'bg-brand-negative';

    return (
        <div className="w-full bg-brand-border rounded-full h-2.5">
            <div className={`${colorClass} h-2.5 rounded-full`} style={{ width: `${percentage}%` }}></div>
        </div>
    );
};

const AssetRankingsView: FC<{ onTrain: (asset: AssetRanking) => void }> = ({ onTrain }) => {
    const [rankings, setRankings] = useState<AssetRanking[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchRankings = async () => {
            setLoading(true);
            const data = await api.getAssetRankings();
            setRankings(data);
            setLoading(false);
        };
        fetchRankings();
    }, []);

    if (loading) {
        return (
            <div className="space-y-3">
                {Array.from({ length: 10 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
            </div>
        )
    }

    return (
        <div className="space-y-3">
            {rankings.map(asset => (
                 <div key={asset.symbol} className="bg-brand-surface border border-brand-border rounded-lg p-4 flex items-center gap-4 hover:border-brand-primary transition-colors duration-200">
                    <div className="flex-1 grid grid-cols-1 md:grid-cols-5 items-center gap-4">
                        <div className="md:col-span-1">
                            <h3 className="text-lg font-bold text-brand-text-primary">{asset.symbol}</h3>
                            <p className="text-xs text-brand-text-secondary">{asset.reason}</p>
                        </div>
                         <div className="md:col-span-1">
                            <p className="text-xs font-medium text-brand-text-secondary mb-1">Suitability</p>
                            <div className="flex items-center gap-2">
                                <ScoreBar score={asset.suitabilityScore} />
                                <span className="text-sm font-semibold w-10 text-right">{asset.suitabilityScore}</span>
                            </div>
                        </div>
                        <div className="md:col-span-1 text-sm">
                             <p><span className="text-brand-text-secondary">Volatility:</span> <span className="font-semibold">{asset.volatilityIndex}</span></p>
                             <p><span className="text-brand-text-secondary">Liquidity:</span> <span className="font-semibold">{asset.liquidityIndex}</span></p>
                        </div>
                         <div className="md:col-span-1 flex flex-col items-start gap-1">
                            <RiskBadge level={asset.riskLevel} />
                             <p className="text-xs text-brand-text-secondary mt-1">Est. Time: {asset.estimatedTime}</p>
                        </div>
                        <div className="md:col-span-1 flex justify-end">
                            <button
                                onClick={() => onTrain(asset)}
                                className="flex items-center gap-2 bg-brand-primary text-white font-semibold px-4 py-2 rounded-lg hover:bg-brand-primary/80 transition-colors"
                            >
                                <RocketIcon className="w-4 h-4" />
                                <span>Train Model</span>
                            </button>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
};

const TrainingProgressView: FC<{ jobId: string, assetSymbol: string, onCancel: () => void, onComplete: (results: TrainingResults) => void }> = ({ jobId, assetSymbol, onCancel, onComplete }) => {
    const [status, setStatus] = useState<TrainingStatus | null>(null);

    useEffect(() => {
        const interval = setInterval(async () => {
            const currentStatus = await api.getTrainingStatus(jobId);
            if (currentStatus) {
                setStatus(currentStatus);
                if (currentStatus.phase === TrainingPhase.COMPLETE) {
                    clearInterval(interval);
                    const results = await api.getTrainingResults(jobId);
                    if (results) {
                        onComplete(results);
                    }
                }
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [jobId, onComplete]);

    const PhaseIcon = {
        [TrainingPhase.DATA_COLLECTION]: CpuIcon,
        [TrainingPhase.VIABILITY_ASSESSMENT]: FlaskConicalIcon,
        [TrainingPhase.TIMEFRAME_TESTING]: FlaskConicalIcon,
        [TrainingPhase.OPTIMIZATION]: BrainCircuitIcon,
        [TrainingPhase.VALIDATION]: ClipboardCheckIcon,
        [TrainingPhase.ROBUSTNESS]: RotateCwIcon,
        [TrainingPhase.SCORING]: BarChartBigIcon,
        [TrainingPhase.COMPLETE]: CheckCircle2Icon,
    }[status?.phase ?? TrainingPhase.DATA_COLLECTION];

    return (
        <div className="max-w-4xl mx-auto bg-brand-surface border border-brand-border rounded-lg p-8 animate-fadeIn">
            <div className="text-center mb-6">
                <h2 className="text-2xl font-bold text-brand-text-primary">Training Model for <span className="text-brand-primary">{assetSymbol}</span></h2>
                <p className="text-brand-text-secondary mt-1">AI is analyzing historical data and optimizing strategies. Please wait...</p>
            </div>

            <div className="space-y-4 mb-8">
                <div className="flex justify-between items-baseline mb-1">
                    <div className="flex items-center gap-2">
                        <PhaseIcon className="w-5 h-5 text-brand-primary" />
                        <span className="font-semibold text-brand-text-primary">{status?.phase}</span>
                    </div>
                    <span className="text-sm font-mono text-brand-text-secondary">ETA: {status?.eta ?? '...'}</span>
                </div>
                <div className="w-full bg-brand-border rounded-full h-4">
                    <div className="bg-brand-primary h-4 rounded-full transition-all duration-500" style={{ width: `${status?.progress ?? 0}%` }}></div>
                </div>
                 <p className="text-sm text-brand-text-secondary text-center h-4">{status?.message}</p>
            </div>
            
            {status?.patternAnalysis && (
                <div className="mt-8">
                     <h3 className="text-lg font-semibold text-brand-text-primary mb-3">Pattern Viability Analysis</h3>
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {status.patternAnalysis.map(p => {
                            const viable = p.status === 'Viable';
                            const marginal = p.status === 'Marginal';
                            return (
                            <div key={p.name} className="bg-brand-bg/50 border border-brand-border p-3 rounded-md">
                                <div className="flex justify-between items-center">
                                    <p className="font-semibold">{p.name}</p>
                                    <span className={`text-xs font-bold px-2 py-1 rounded-full ${viable ? 'text-green-400 bg-green-500/10' : marginal ? 'text-yellow-400 bg-yellow-500/10' : 'text-red-400 bg-red-500/10'}`}>{p.status}</span>
                                </div>
                                <div className="text-sm text-brand-text-secondary mt-2 flex justify-between">
                                    <span>Win Rate: <span className="font-mono text-brand-text-primary">{p.winRate}%</span></span>
                                    <span>Signals Found: <span className="font-mono text-brand-text-primary">{p.signals}</span></span>
                                </div>
                            </div>
                            )
                        })}
                     </div>
                </div>
            )}
            
            <div className="mt-8 text-center">
                <button onClick={onCancel} className="text-sm text-brand-text-secondary hover:text-brand-primary transition-colors">Cancel Training</button>
            </div>
        </div>
    );
};

const ToggleSwitch: FC<{ enabled: boolean; onChange: (enabled: boolean) => void; }> = ({ enabled, onChange }) => {
    return (
        <button
            onClick={() => onChange(!enabled)}
            className={`relative inline-flex items-center h-6 rounded-full w-11 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-brand-surface focus:ring-brand-primary ${enabled ? 'bg-brand-primary' : 'bg-brand-border'}`}
        >
            <span
                className={`inline-block w-4 h-4 transform bg-white rounded-full transition-transform ${enabled ? 'translate-x-6' : 'translate-x-1'}`}
            />
        </button>
    );
};

const ImplementationPlanView: FC<{ plan: PatternImplementation[] }> = ({ plan }) => {
    const [implementationPlan, setImplementationPlan] = useState<PatternImplementation[]>(plan);

    const handleToggle = (pIndex: number, rIndex: number, eIndex: number) => {
        const newPlan = JSON.parse(JSON.stringify(implementationPlan));
        const currentStatus = newPlan[pIndex].regimes[rIndex].exchanges[eIndex].status;
        newPlan[pIndex].regimes[rIndex].exchanges[eIndex].status = currentStatus === 'ACTIVE' ? 'PAPER_TRADING' : 'ACTIVE';
        setImplementationPlan(newPlan);
    };
    
    return (
        <div className="space-y-6">
            <p className="text-sm text-brand-text-secondary">
                Enable or disable specific pattern/regime/exchange combinations. Disabled strategies will run in paper-trading mode to continue gathering data without risking capital. The initial state is recommended by the AI.
            </p>
            {implementationPlan.map((p, pIndex) => (
                <div key={p.pattern} className="bg-brand-bg/30 border border-brand-border rounded-lg">
                    <h4 className="text-lg font-bold p-4 bg-brand-surface/50 rounded-t-lg border-b border-brand-border">{p.pattern}</h4>
                    <div className="space-y-4 p-4">
                        {p.regimes.map((r, rIndex) => (
                            <div key={r.regime}>
                                <h5 className="font-semibold text-brand-text-primary mb-2">{r.regime}</h5>
                                <div className="space-y-2 pl-4 border-l-2 border-brand-border">
                                    {r.exchanges.map((ex, eIndex) => (
                                        <div key={ex.exchange} className="grid grid-cols-6 gap-4 items-center text-sm p-2 rounded-md hover:bg-brand-surface/30">
                                            <div className="font-semibold col-span-1">{ex.exchange}</div>
                                            <div className="col-span-1">
                                                <span className="text-brand-text-secondary">WR: </span>
                                                <span className={`font-mono ${ex.winRate > 60 ? 'text-brand-positive' : 'text-brand-negative'}`}>{ex.winRate}%</span>
                                            </div>
                                            <div className="col-span-1">
                                                <span className="text-brand-text-secondary">Signals: </span>
                                                <span className="font-mono">{ex.signals}</span>
                                            </div>
                                            <div className="col-span-1">
                                                <span className="text-brand-text-secondary">P/L: </span>
                                                <span className={`font-mono ${ex.totalPL >= 0 ? 'text-brand-positive' : 'text-brand-negative'}`}>{formatCurrency(ex.totalPL)}</span>
                                            </div>
                                            <div className="col-span-1">
                                                <span className={`font-semibold text-xs px-2 py-1 rounded-full ${ex.status === 'ACTIVE' ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                                                    {ex.status === 'ACTIVE' ? 'Active' : 'Paper'}
                                                </span>
                                            </div>
                                            <div className="col-span-1 flex justify-end">
                                                <ToggleSwitch
                                                    enabled={ex.status === 'ACTIVE'}
                                                    onChange={() => handleToggle(pIndex, rIndex, eIndex)}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};

const TrainingResultsView: FC<{ results: TrainingResults, onTrainAgain: () => void }> = ({ results, onTrainAgain }) => {
    const recommendationConfig = {
        HIGH: { text: 'High Confidence', icon: CheckCircle2Icon, color: 'text-brand-positive' },
        MEDIUM: { text: 'Medium Confidence', icon: AlertTriangleIcon, color: 'text-yellow-400' },
        LOW: { text: 'Low Confidence', icon: AlertTriangleIcon, color: 'text-orange-400' },
        REJECT: { text: 'Rejected', icon: XCircleIcon, color: 'text-brand-negative' },
    };
    const Reco = recommendationConfig[results.recommendation];

    const summaryTab = {
        label: 'AI Summary Report',
        content: (
            <div className="prose prose-invert prose-sm max-w-none text-brand-text-secondary bg-brand-bg/30 p-4 rounded-md border border-brand-border">
                <pre className="whitespace-pre-wrap font-sans">{results.aiSummaryReport}</pre>
            </div>
        )
    };
    
    const validationTab = {
        label: "Walk-Forward Validation",
        content: (
            <div>
                 <DataTable 
                    headers={['Window', 'Train Period', 'Validation Period', 'Train WR', 'Val WR', 'Deviation', 'Status']}
                    data={results.walkForwardValidation.results.map(r => [
                        r.window,
                        r.trainingPeriod,
                        r.validationPeriod,
                        `${r.trainWR}%`,
                        `${r.valWR}%`,
                        <span key={r.window} className={Math.abs(parseInt(r.deviation)) > 5 ? 'text-brand-negative' : 'text-brand-positive'}>{r.deviation}</span>,
                        <span key={`${r.window}-s`} className={`font-semibold ${r.status === 'Pass' ? 'text-brand-positive' : 'text-brand-negative'}`}>{r.status}</span>,
                    ])}
                />
            </div>
        )
    };

    const robustnessTab = {
        label: 'Robustness Testing',
        content: (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h4 className="font-semibold mb-2">Monte Carlo Simulation (1k runs)</h4>
                    <div className="text-sm space-y-2 bg-brand-bg/30 p-4 rounded-md border border-brand-border">
                        <p>Win Rate 95% CI: <span className="font-mono text-brand-primary">{results.robustnessTesting.monteCarlo.winRateCI.join('% - ')}%</span></p>
                        <p>Avg. R/R 95% CI: <span className="font-mono text-brand-primary">{results.robustnessTesting.monteCarlo.avgRR_CI.join(' - ')}</span></p>
                        <p className="text-xs text-brand-text-secondary pt-2">{results.robustnessTesting.monteCarlo.interpretation}</p>
                    </div>
                </div>
                 <div>
                    <h4 className="font-semibold mb-2">Performance Across Regimes</h4>
                    <div className="text-sm space-y-2 bg-brand-bg/30 p-4 rounded-md border border-brand-border">
                        {results.robustnessTesting.regimePerformance.map(r => (
                            <div key={r.regime} className="flex justify-between">
                                <span>{r.regime}:</span>
                                <span className="font-mono text-brand-text-primary">WR: {r.winRate}% ({r.signals} signals)</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    const implementationTab = {
        label: 'Implementation Plan',
        content: <ImplementationPlanView plan={results.implementationPlan} />
    }

    const tabs = [summaryTab, validationTab, robustnessTab, implementationTab];

    return (
        <div className="space-y-6 animate-fadeIn">
            <header className="bg-brand-surface border border-brand-border rounded-lg p-6">
                <div className="flex flex-wrap justify-between items-start gap-y-4">
                    {/* Top-left: Title and Recommendation */}
                    <div>
                        <h2 className="text-3xl font-bold text-brand-text-primary">Training Complete for {results.assetSymbol}</h2>
                        <div className="flex items-center gap-2 mt-2">
                            <Reco.icon className={`w-6 h-6 ${Reco.color}`} />
                            <span className={`text-xl font-semibold ${Reco.color}`}>{Reco.text}</span>
                        </div>
                    </div>

                    {/* Top-right: Action Buttons */}
                    <div className="flex-shrink-0 flex items-center gap-4">
                        <button onClick={onTrainAgain} className="flex items-center gap-2 bg-brand-surface border border-brand-border text-brand-text-primary font-semibold px-4 py-2 rounded-lg hover:bg-brand-border transition-colors">
                            <RotateCwIcon className="w-4 h-4" />
                            <span>Train Another Asset</span>
                        </button>
                        <button className="flex items-center gap-2 bg-brand-primary text-white font-semibold px-6 py-2 rounded-lg hover:bg-brand-primary/80 transition-colors">
                            <RocketIcon className="w-4 h-4" />
                            <span>Deploy Model</span>
                        </button>
                    </div>
                </div>

                {/* Confidence Score Bar */}
                <div className="mt-6 w-full md:w-64">
                    <p className="text-sm font-medium text-brand-text-secondary mb-1">Final Confidence Score</p>
                    <div className="flex items-center gap-3">
                        <ScoreBar score={results.confidenceScore} />
                        <span className="text-lg font-bold w-12 text-right">{results.confidenceScore.toFixed(1)}</span>
                    </div>
                </div>
            </header>

            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                 <div className="bg-brand-surface border border-brand-border rounded-lg p-4">
                    <p className="text-xs text-brand-text-secondary">Validated Win Rate</p>
                    <p className="text-xl font-bold">{results.performance.winRate.toFixed(1)}%</p>
                </div>
                <div className="bg-brand-surface border border-brand-border rounded-lg p-4">
                    <p className="text-xs text-brand-text-secondary">Average R/R</p>
                    <p className="text-xl font-bold">{results.performance.avgRR}</p>
                </div>
                <div className="bg-brand-surface border border-brand-border rounded-lg p-4">
                    <p className="text-xs text-brand-text-secondary">Signals / Month</p>
                    <p className="text-xl font-bold">{results.performance.signalsPerMonth}</p>
                </div>
                 <div className="bg-brand-surface border border-brand-border rounded-lg p-4">
                    <p className="text-xs text-brand-text-secondary">Expected Return</p>
                    <p className="text-xl font-bold text-brand-positive">{results.performance.expectedReturn}</p>
                </div>
                <div className="bg-brand-surface border border-brand-border rounded-lg p-4">
                    <p className="text-xs text-brand-text-secondary">Max Drawdown</p>
                    <p className="text-xl font-bold text-brand-negative">{results.performance.maxDrawdown.toFixed(1)}%</p>
                </div>
            </div>

            <div className="bg-brand-surface border border-brand-border rounded-lg p-6">
                <Tabs tabs={tabs} />
            </div>
        </div>
    );
}


export const AITrainer: React.FC = () => {
    const [view, setView] = useState<View>('rankings');
    const [jobId, setJobId] = useState<string | null>(null);
    const [selectedAsset, setSelectedAsset] = useState<AssetRanking | null>(null);
    const [results, setResults] = useState<TrainingResults | null>(null);
    const [isPromptModalOpen, setIsPromptModalOpen] = useState(false);

    const handleStartTraining = async (asset: AssetRanking) => {
        setSelectedAsset(asset);
        const { jobId } = await api.startTraining(asset.symbol);
        setJobId(jobId);
        setView('training');
    };

    const handleCancelTraining = () => {
        // In a real app, you'd call an API to cancel the job
        setJobId(null);
        setSelectedAsset(null);
        setView('rankings');
    };

    const handleTrainingComplete = (trainingResults: TrainingResults) => {
        setResults(trainingResults);
        setView('results');
    };
    
    const handleTrainAgain = () => {
        setJobId(null);
        setSelectedAsset(null);
        setResults(null);
        setView('rankings');
    }

    const renderView = () => {
        switch (view) {
            case 'training':
                if (jobId && selectedAsset) {
                    return <TrainingProgressView jobId={jobId} assetSymbol={selectedAsset.symbol} onCancel={handleCancelTraining} onComplete={handleTrainingComplete} />;
                }
                // Fallback to rankings if something is wrong
                setView('rankings');
                return null;
            case 'results':
                if (results) {
                    return <TrainingResultsView results={results} onTrainAgain={handleTrainAgain} />;
                }
                 // Fallback to rankings if something is wrong
                setView('rankings');
                return null;
            case 'rankings':
            default:
                return <AssetRankingsView onTrain={handleStartTraining} />;
        }
    };
    
    const systemPrompt = `CORE MISSION
When given a trading pair symbol and exchange, you will:
1. Analyze 2+ years of historical price data from the SPECIFIC exchange
2. Test 4 specific trading patterns across multiple timeframes
3. Optimize all adjustable parameters using Bayesian optimization
4. Account for exchange-specific fees, slippage, and execution characteristics
5. Validate results using walk-forward analysis
6. Apply multi-timeframe hierarchy filtering
7. Calculate confidence score for deployment readiness
8. Generate exchange-specific optimized configuration file with AI reasoning

CRITICAL CONSTRAINTS
- You are training patterns with MULTI-TIMEFRAME AWARENESS. A pattern that looks good on 1h must also be confirmed by higher timeframes (4h, 1d) or it will fail.
- You are training for SPECIFIC EXCHANGES. Each exchange has different fees, liquidity, slippage, and execution speeds. Parameters optimized for Binance may NOT work on Coinbase.
- ALL backtesting must include exchange-specific costs or results will be unrealistic.

═══════════════════════════════════════════════════════════════════════

EXCHANGE-SPECIFIC PARAMETERS (CRITICAL)

You MUST fetch and apply these exchange-specific characteristics:

EXCHANGE PROFILES TO TEST:

1. BINANCE
   - Maker Fee: 0.10% (with BNB discount: 0.075%)
   - Taker Fee: 0.10% (with BNB discount: 0.075%)
   - Average Slippage: 0.05-0.15% (depends on pair liquidity tier)
   - Order Execution Speed: Fast (50-150ms)
   - Liquidity: Highest (best for all pairs)
   - Minimum Order Size: Varies by pair ($10-50 typical)
   - API Rate Limits: 1200 req/min
   - Notes: Best overall liquidity, tightest spreads

2. COINBASE PRO / ADVANCED
   - Maker Fee: 0.40% (volume tier 0-10k)
   - Taker Fee: 0.60% (volume tier 0-10k)
   - Average Slippage: 0.10-0.25% (lower liquidity than Binance)
   - Order Execution Speed: Medium (100-300ms)
   - Liquidity: High for major pairs, lower for altcoins
   - Minimum Order Size: $10 typical
   - API Rate Limits: 10 req/sec public, 15 req/sec private
   - Notes: Higher fees, better for compliance/US users

3. KRAKEN
   - Maker Fee: 0.16% (volume tier 0-50k)
   - Taker Fee: 0.26% (volume tier 0-50k)
   - Average Slippage: 0.15-0.30%
   - Order Execution Speed: Medium (150-350ms)
   - Liquidity: Medium-High
   - Minimum Order Size: $10 typical
   - API Rate Limits: Variable by tier
   - Notes: Mid-range fees, good security reputation

4. BYBIT
   - Maker Fee: 0.10%
   - Taker Fee: 0.10%
   - Average Slippage: 0.08-0.20%
   - Order Execution Speed: Fast (80-200ms)
   - Liquidity: High
   - Minimum Order Size: Varies by pair
   - API Rate Limits: 120 req/min
   - Notes: Good liquidity, popular for derivatives

5. OKX
   - Maker Fee: 0.08% (volume tier 1)
   - Taker Fee: 0.10% (volume tier 1)
   - Average Slippage: 0.10-0.25%
   - Order Execution Speed: Fast (60-180ms)
   - Liquidity: High
   - Minimum Order Size: Varies by pair
   - API Rate Limits: 60 req/2sec
   - Notes: Competitive fees, strong Asian market

6. KUCOIN
   - Maker Fee: 0.10%
   - Taker Fee: 0.10%
   - Average Slippage: 0.15-0.35%
   - Order Execution Speed: Medium (120-300ms)
   - Liquidity: Medium (lower for smaller cap coins)
   - Minimum Order Size: $5-10 typical
   - API Rate Limits: Variable
   - Notes: Good altcoin selection, lower liquidity

EXCHANGE-SPECIFIC ADJUSTMENTS:

Slippage Modeling by Liquidity Tier:
├─ Tier 1 (BTC, ETH): Base slippage × 1.0
├─ Tier 2 (Top 20): Base slippage × 1.3
├─ Tier 3 (Top 100): Base slippage × 1.8
└─ Tier 4 (100+): Base slippage × 2.5

Order Size Impact:
├─ Position <0.1% of 24h volume: No additional slippage
├─ Position 0.1-0.5% of 24h volume: +0.05% slippage
├─ Position 0.5-1.0% of 24h volume: +0.15% slippage
└─ Position >1.0% of 24h volume: +0.30%+ slippage (avoid)

Market Order vs Limit Order:
├─ Market Order: Full taker fee + full slippage
├─ Limit Order (filled immediately): Maker fee + 50% slippage
└─ Limit Order (filled later): Maker fee only, but may miss entry

═══════════════════════════════════════════════════════════════════════

THE 4 PATTERNS TO OPTIMIZE (Exchange-Aware)

PATTERN 1: Liquidity Sweep Reversal
Base Criteria (optimize these thresholds):
- Price spikes through recent swing high/low (lookback: optimize 15-25 bars)
- Volume spike (optimize: 1.2x - 3.0x average)
- Close rejects back inside range (wick size: optimize 0.5% - 2.5%)
- RSI divergence (RSI threshold: optimize 60-80 for resistance, 20-40 for support)
- Confirmation candles required (optimize: 0-2 candles)

Parameters to Optimize:
├─ rsi_threshold (60-80 or 20-40 depending on direction)
├─ volume_multiplier (1.2 - 3.0)
├─ wick_percentage (0.5 - 2.5)
├─ swing_lookback_bars (15 - 25)
├─ confirmation_candles (0 - 2)
├─ stop_loss_pct (0.3 - 1.5) [MUST exceed exchange fees + slippage]
├─ take_profit_pct (6 - 15) [MUST exceed exchange fees + slippage significantly]
├─ optimal_timeframe (test: 1h, 4h, 1d)
└─ order_type (market vs limit) [Exchange-dependent]

Expected Baseline: 65-71% win rate, 2.5-3.5 R:R (BEFORE exchange costs)
After Exchange Costs: Win rate may drop 3-5%, R:R reduced by fee%

PATTERN 2: Capitulation Reversal
Base Criteria (optimize these thresholds):
- Sharp price dump (optimize: 4-10% in 4hr OR 6-12% in 24hr)
- Volume spike (optimize: 2.5x - 5.0x average)
- RSI extreme (optimize: 15-30)
- Reversal candle: close > open
- Strong bounce: close in top X% of candle (optimize: 60-80%)
- Confirmation candle: higher close, volume declining (optimize: 15-30%)

Parameters to Optimize:
├─ dump_threshold_pct_4h (4 - 10)
├─ dump_threshold_pct_24h (6 - 12)
├─ volume_multiplier (2.5 - 5.0)
├─ rsi_threshold (15 - 30)
├─ bounce_strength_pct (60 - 80)
├─ volume_decline_pct (15 - 30)
├─ confirmation_candles (1 - 2)
├─ stop_loss_pct (2.0 - 4.0) [MUST exceed exchange fees + slippage]
├─ take_profit_pct (10 - 15) [MUST exceed exchange fees + slippage significantly]
├─ optimal_timeframe (test: 4h, 1d)
└─ order_type (market vs limit) [May need market order due to urgency]

Expected Baseline: 65-69% win rate, 3.0-4.5 R:R (BEFORE exchange costs)
After Exchange Costs: Win rate may drop 2-4%, R:R reduced by fee%

PATTERN 3: Failed Breakdown (Spring)
Base Criteria (optimize these thresholds):
- Price in range (optimize: 15-30 days, range width: 5-12%)
- Support tested (optimize: 2-5 times)
- Volume declining (optimize: 10-30% decline over range)
- Breaks below support (optimize: 0.5-3%)
- Recovers quickly (optimize: 1-4 candles)
- Recovery volume spike (optimize: 1.3x - 2.5x)
- Breaks above range (optimize: within 3-7 days)

Parameters to Optimize:
├─ range_days (15 - 30)
├─ range_width_pct (5 - 12)
├─ support_tests_min (2 - 5)
├─ volume_decline_pct (10 - 30)
├─ breakdown_distance_pct (0.5 - 3.0)
├─ recovery_candles (1 - 4)
├─ recovery_volume_multiplier (1.3 - 2.5)
├─ breakout_timeframe_days (3 - 7)
├─ stop_loss_pct (1.0 - 3.0) [MUST exceed exchange fees + slippage]
├─ take_profit_pct (8 - 12) [MUST exceed exchange fees + slippage significantly]
├─ optimal_timeframe (test: 4h, 1d)
└─ order_type (limit acceptable, less urgency)

Expected Baseline: 63-67% win rate, 2.8-3.5 R:R (BEFORE exchange costs)
After Exchange Costs: Win rate may drop 3-5%, R:R reduced by fee%

PATTERN 4: Supply Shock (Macro - Rare)
Base Criteria (optimize these thresholds):
- Exchange netflow negative (optimize: 5-10 consecutive days)
- Whale holdings increased (optimize: 1.5-3% in 20-40 days)
- Exchange reserves at low (optimize: 3-12 month low)
- Price not parabolic (optimize: <10-20% gain in 20-40 days)
- First green weekly candle after accumulation

Parameters to Optimize:
├─ netflow_negative_days (5 - 10)
├─ whale_increase_pct (1.5 - 3.0)
├─ whale_timeframe_days (20 - 40)
├─ reserve_low_months (3 - 12)
├─ max_price_gain_pct (10 - 20)
├─ price_gain_lookback_days (20 - 40)
├─ stop_loss_pct (6 - 10) [MUST exceed exchange fees + slippage]
├─ take_profit_pct (18 - 30) [MUST exceed exchange fees + slippage significantly]
├─ timeframe (weekly only)
└─ order_type (limit acceptable, longer timeframe)

Expected Baseline: 75-83% win rate, 4.0-6.0 R:R (BEFORE exchange costs)
After Exchange Costs: Win rate may drop 1-3%, R:R reduced by fee%
Note: This pattern requires on-chain data. If unavailable, DISABLE this pattern.

CRITICAL: EXCHANGE COST INTEGRATION
Every backtest trade MUST deduct:
- Entry fee: (maker_fee or taker_fee) depending on order type
- Exit fee: (maker_fee or taker_fee) depending on order type
- Entry slippage: Based on exchange + liquidity tier + order urgency
- Exit slippage: Based on exchange + liquidity tier + order urgency

Example calculation for 1 trade:
Entry price: $100
Position size: $1000
Stop loss: -2% = $98
Take profit: +10% = $110

Exchange: Coinbase (0.60% taker fee, 0.15% avg slippage)
Entry cost: $1000 × (0.60% + 0.15%) = $7.50
Exit cost: $1100 × (0.60% + 0.15%) = $8.25
Total cost: $15.75 = 1.58% of position

Adjusted profit if win: +10% - 1.58% = +8.42%
Adjusted loss if stopped: -2% - 1.58% = -3.58%
Real R:R: 8.42 / 3.58 = 2.35:1 (vs theoretical 5:1)

This dramatically affects profitability!

═══════════════════════════════════════════════════════════════════════

MULTI-TIMEFRAME HIERARCHY RULES (CRITICAL)

You MUST implement timeframe filtering to avoid false signals:

TIMEFRAME HIERARCHY:
1d (Daily) → Highest authority (market regime)
4h (4-hour) → Medium authority (trend direction)  
1h (1-hour) → Lowest authority (entry timing)

FILTERING RULES:

For 1h Timeframe Signals:
REQUIRE ALL:
├─ Pattern detected on 1h ✓
├─ 4h trend alignment:
│  ├─ For LONG: 4h price > 4h 50 EMA
│  ├─ For SHORT: 4h price < 4h 50 EMA
│  └─ 4h not in extreme opposite move (>5% counter-trend in last 4 candles)
└─ 1d regime check:
   ├─ 1d not in panic (RSI not <25)
   ├─ 1d not parabolic (RSI not >80)
   └─ No major 1d resistance/support within 3%

For 4h Timeframe Signals:
REQUIRE ALL:
├─ Pattern detected on 4h ✓
└─ 1d regime check:
   ├─ For LONG: 1d price > 1d 200 EMA (or in established range)
   ├─ For SHORT: 1d price < 1d 200 EMA (or in established range)
   └─ 1d not in extreme condition (RSI between 30-75)

For 1d Timeframe Signals:
├─ Pattern detected on 1d ✓
└─ No higher timeframe filter needed (1d is highest authority)

TESTING PROTOCOL:
You must test EACH pattern on EACH timeframe (1h, 4h, 1d) with appropriate filters.
Record win rate for each combination:
- Pattern X on 1h with 4h+1d filters
- Pattern X on 4h with 1d filters  
- Pattern X on 1d (no filters)

Select the timeframe + filter combination with highest risk-adjusted score.

═══════════════════════════════════════════════════════════════════════

OPTIMIZATION METHODOLOGY (EXCHANGE-AWARE)

PHASE 1: EXCHANGE DATA COLLECTION & ANALYSIS
1. Fetch 2 years (730 days) of OHLCV data from SPECIFIC exchange
   - Use exchange's native API or verified data provider
   - Ensure data is from the EXACT exchange being traded on
   - Different exchanges have different prices at same timestamp (arbitrage gaps)

2. Analyze exchange-specific characteristics:
   ├─ Average bid/ask spread for this pair
   ├─ 24-hour trading volume (liquidity proxy)
   ├─ Historical slippage patterns (measure actual fill prices vs mid-price)
   ├─ Order book depth at key levels
   └─ Typical price impact for target position size

3. Identify market regimes (same as before):
   ├─ Bull Market: Price > 200 MA, higher highs, RSI avg >55
   ├─ Bear Market: Price < 200 MA, lower lows, RSI avg <45
   ├─ Sideways: Price oscillating within 15% range for 30+ days
   ├─ High Volatility: ATR > 1.5x average
   └─ Low Volatility: ATR < 0.7x average

4. Calculate exchange cost baseline:
\`\`\`
   min_profitable_move = (maker_fee + taker_fee + avg_slippage_entry + avg_slippage_exit) × 2
\`\`\`
   Example: Coinbase = (0.40% + 0.60% + 0.15% + 0.15%) × 2 = 2.6%
   
   Any pattern with average wins <2.6% will lose money on Coinbase!

PHASE 2: PATTERN VIABILITY ASSESSMENT (Exchange-Aware)
For each of the 4 patterns:
1. Run pattern detector with DEFAULT parameters across all historical data
2. Count total signals detected
3. For EACH signal, calculate PnL AFTER exchange costs:
\`\`\`
   gross_pnl = (exit_price - entry_price) / entry_price
   entry_cost = entry_price × (fee + slippage)
   exit_cost = exit_price × (fee + slippage)
   net_pnl = gross_pnl - ((entry_cost + exit_cost) / entry_price)
\`\`\`
4. Calculate NET win rate (after costs)
5. Calculate NET average R:R (after costs)
6. Determine viability:
   ├─ VIABLE: NET win rate ≥55% AND ≥15 signals/year AND avg_win > min_profitable_move
   ├─ MARGINAL: NET win rate 50-55% OR 10-15 signals/year
   └─ NOT VIABLE: NET win rate <50% OR <10 signals/year OR avg_win < min_profitable_move

CRITICAL INSIGHT:
A pattern with 68% gross win rate may only have 61% net win rate on Coinbase.
Same pattern may have 65% net win rate on Binance (lower fees).

Only proceed to optimization for VIABLE patterns on THIS SPECIFIC EXCHANGE.

PHASE 3: MULTI-TIMEFRAME TESTING (Exchange-Aware)
For each VIABLE pattern:

Test on 1h timeframe:
├─ Run pattern detector on 1h candles FROM THIS EXCHANGE
├─ Apply 4h trend filter (price vs 4h 50 EMA)
├─ Apply 1d regime filter (no extremes)
├─ Deduct exchange costs from every trade
├─ Count signals and NET win rate
└─ Record: signals_1h, net_winrate_1h, net_avg_rr_1h

Test on 4h timeframe:
├─ Run pattern detector on 4h candles FROM THIS EXCHANGE
├─ Apply 1d trend filter (price vs 1d 200 EMA)
├─ Deduct exchange costs from every trade
├─ Count signals and NET win rate
└─ Record: signals_4h, net_winrate_4h, net_avg_rr_4h

Test on 1d timeframe:
├─ Run pattern detector on 1d candles FROM THIS EXCHANGE
├─ No higher timeframe filter needed
├─ Deduct exchange costs from every trade
├─ Count signals and NET win rate
└─ Record: signals_1d, net_winrate_1d, net_avg_rr_1d

Select primary timeframe:
SCORE = (net_win_rate * 0.5) + (signals_per_year/50 * 0.3) + (net_avg_rr/4 * 0.2)
Choose timeframe with highest score FOR THIS EXCHANGE.

PHASE 4: BAYESIAN PARAMETER OPTIMIZATION (Exchange-Aware)
For the selected timeframe, optimize all parameters:

Define search space (ranges listed in pattern definitions above).

CRITICAL: Objective function MUST include exchange costs:
\`\`\`
def fitness_score_with_costs(params, exchange_profile):
    # Run backtest with params
    trades = backtest(params)
    
    # Apply exchange costs to each trade
    net_trades = []
    for trade in trades:
        entry_cost = trade.entry_price * (exchange_profile.fee + exchange_profile.slippage)
        exit_cost = trade.exit_price * (exchange_profile.fee + exchange_profile.slippage)
        net_pnl = trade.gross_pnl - (entry_cost + exit_cost) / trade.entry_price
        net_trades.append(net_pnl)
    
    # Calculate NET metrics
    net_win_rate = len([t for t in net_trades if t > 0]) / len(net_trades)
    net_avg_win = mean([t for t in net_trades if t > 0])
    net_avg_loss = mean([t for t in net_trades if t < 0])
    net_avg_rr = abs(net_avg_win / net_avg_loss)
    
    signals_per_year = len(trades) / 2
    
    # Calculate consistency across regimes
    net_win_rate_std = std_dev([wr for wr in win_rates_by_regime])
    
    # Calculate max drawdown
    equity_curve = cumulative_returns(net_trades)
    max_dd = calculate_max_drawdown(equity_curve)
    
    # FITNESS SCORE (using NET metrics)
    fitness = (
        net_win_rate * 40 +
        min(net_avg_rr / 0.05, 30) +  // R:R capped at 6:1 = 30 points
        min(signals_per_year / 2, 15) +  // Frequency capped at 30/year = 15 points
        (1 - net_win_rate_std) * 10 +  // Consistency
        max(0, 10 - max_dd / 5)  // Drawdown penalty
    )
    
    return fitness
\`\`\`

Use Bayesian Optimization with:
- Initial random sampling: 30 iterations
- Bayesian iterations: 170 iterations
- Total tests: 200 parameter combinations
- ALL tests include exchange costs

For each parameter combination tested:
1. Run backtest across entire 2-year dataset FROM THIS EXCHANGE
2. Apply multi-timeframe filters
3. Deduct exchange costs for EVERY trade
4. Calculate NET win rate, NET avg R:R, signal frequency
5. Calculate fitness score using NET metrics
6. Record results

Track best parameters found so far.
After 200 iterations, optimal_params = highest fitness score.

EXCHANGE-SPECIFIC PARAMETER ADJUSTMENTS:

High-Fee Exchanges (Coinbase, Kraken):
├─ Need WIDER profit targets (to overcome fees)
├─ Need TIGHTER stops (to maintain R:R after fees)
├─ Need HIGHER win rate patterns (fees eat into edge)
└─ Prefer limit orders over market orders when possible

Low-Fee Exchanges (Binance, OKX):
├─ Can use tighter profit targets
├─ Can tolerate slightly wider stops
├─ More patterns become viable
└─ Market orders more acceptable

PHASE 5: WALK-FORWARD VALIDATION (Exchange-Aware)
Split 2-year data into overlapping windows:

Window 1: Train on months 1-12, validate on months 13-15
Window 2: Train on months 4-15, validate on months 16-18
Window 3: Train on months 7-18, validate on months 19-21
Window 4: Train on months 10-21, validate on months 22-24

For each window:
1. Re-optimize parameters on training period (with exchange costs)
2. Test those parameters on validation period (with exchange costs)
3. Record NET validation win rate, R:R, signals

Validation criteria (ALL must pass):
├─ NET validation win rate within ±10% of NET training win rate
├─ NET validation R:R within ±25% of NET training R:R
├─ At least 5 signals in validation period
├─ Max drawdown in validation <40%
└─ Average win > exchange minimum profitable move

If any window fails validation:
├─ Flag as "overfitting risk" or "exchange unsuitable"
├─ Widen parameter search space
├─ Re-optimize with regularization
└─ Re-run validation

Stability score = (# windows passed / total windows) * 100

PHASE 6: ROBUSTNESS TESTING (Exchange-Aware)
Monte Carlo Simulation (1000 runs):
For each run:
├─ Randomize entry timing within ±1 candle of signal
├─ Add ADDITIONAL random slippage on top of base exchange slippage (±50%)
├─ Simulate partial fills (10% chance - more likely on low liquidity exchanges)
├─ Simulate missed entries (5% chance - API lag, rate limits)
├─ Simulate fee tier changes (if volume-based)
└─ Re-calculate final NET win rate and R:R

Calculate confidence intervals:
├─ 95% CI for NET win rate: [lower_bound, upper_bound]
└─ 95% CI for NET avg R:R: [lower_bound, upper_bound]

Regime Switching Test:
├─ Test bull-optimized params in bear market data (with exchange costs)
├─ Test bear-optimized params in bull market data (with exchange costs)
└─ If NET win rate drops >15%, create regime-adaptive parameters

Black Swan Simulation:
├─ Inject extreme events (50% crash, 100% pump)
├─ Test stop loss execution during gaps (exchanges may have different gap behavior)
├─ Simulate exchange downtime (more common on smaller exchanges)
└─ Verify max loss per trade ≤ stop_loss_pct * 1.5 + exchange_costs

Exchange Comparison Analysis:
If testing multiple exchanges, compare:
├─ Which exchange has highest NET win rate for this pair?
├─ Which exchange has most signals (liquidity-dependent)?
├─ Which exchange has lowest total costs?
└─ Which exchange is most consistent across regimes?

PHASE 7: CONFIDENCE SCORING (Exchange-Aware)
Calculate deployment confidence (0-100):
\`\`\`
confidence_score = (
    net_validation_win_rate * 30 +  // Actual NET performance after costs
    stability_score * 20 +  // Consistency across windows
    min(signals_per_year / 2, 15) +  // Adequate frequency
    robustness_mc_score * 20 +  // Monte Carlo stability
    regime_performance_score * 10 +  // Works in all regimes
    exchange_suitability_score * 5  // NEW: Exchange-specific factors
)
\`\`\`

Where:
- net_validation_win_rate: Average NET WR across all walk-forward windows (as %)
- stability_score: % of windows that passed validation
- signals_per_year: Total signals / 2 years
- robustness_mc_score: (100 - CI_width_pct)
- regime_performance_score: Average NET win rate across bull/bear/sideways
- exchange_suitability_score: NEW calculation below

Exchange Suitability Score (0-5):
score = 0
if exchange_costs < 0.5%: score += 2  // Low cost exchange
elif exchange_costs < 1.0%: score += 1  // Medium cost
else: score += 0  // High cost (penalty)
if pair_liquidity_rank <= 20: score += 2  // High liquidity on this exchange
elif pair_liquidity_rank <= 100: score += 1  // Medium liquidity
else: score += 0  // Low liquidity (penalty)
if avg_slippage < 0.15%: score += 1  // Tight spreads

Deployment Decision Rules (Exchange-Aware):
├─ Score 85-100: "HIGH CONFIDENCE - Deploy to live trading on {EXCHANGE}"
├─ Score 70-84: "MEDIUM CONFIDENCE - Deploy with reduced position size (1% risk) on {EXCHANGE}"
├─ Score 55-69: "LOW CONFIDENCE - Paper trade on {EXCHANGE} for 30 days first"
└─ Score <55: "NOT RECOMMENDED - Pattern not reliably profitable on {EXCHANGE} after costs"

CRITICAL RECOMMENDATION LOGIC:
If testing multiple exchanges and pattern is:
- Viable on Binance (score 82) but Not Viable on Coinbase (score 48)
- RECOMMENDATION: "Deploy ONLY on Binance. Do NOT trade this pair on Coinbase - fees too high relative to edge."

═══════════════════════════════════════════════════════════════════════

OUTPUT FORMAT

## TRAINING REPORT: {SYMBOL} on {EXCHANGE}
**Training Completed:** {timestamp}
**Training Duration:** {minutes} minutes
**Data Period:** {start_date} to {end_date}
**Exchange:** {exchange_name}
**Exchange Fee Structure:** Maker: {%} / Taker: {%}
**Average Slippage:** {%}
{/* FIX: Escape template literal to prevent "Cannot find name 'volume'" error */}
**Pair Liquidity on Exchange:** Rank #{rank}, \${volume}/24h

---

### CONFIDENCE SCORE: {score}/100
**Recommendation:** {HIGH/MEDIUM/LOW CONFIDENCE or NOT RECOMMENDED}
**Deploy on {EXCHANGE}:** {YES / YES with caution / NO}

---

### EXCHANGE COST ANALYSIS

**Cost Breakdown Per Trade:**
- Entry Fee: {%} ({maker/taker})
- Exit Fee: {%} ({maker/taker})
- Entry Slippage: {%}
- Exit Slippage: {%}
- **Total Cost Per Round Trip:** {%}

**Minimum Profitable Move:** {%}
(Any trade with gain less than this loses money after costs)

**Impact on Performance:**
- Gross Win Rate: {%} → Net Win Rate: {%} ({change}%)
- Gross Avg R:R: {ratio} → Net Avg R:R: {ratio} ({change}%)
- Break-even win rate required: {%}

{If multiple exchanges tested, include comparison table:}

**Exchange Comparison:**

| Exchange | Net WR | Net R:R | Signals/Year | Total Costs | Confidence | Deploy? |
|----------|--------|---------|--------------|-------------|------------|---------|
| Binance | 71% | 3.1:1 | 52 | 0.40% | 87 | ✅ YES |
| Coinbase | 64% | 2.4:1 | 48 | 1.50% | 62 | ⚠️ Paper Trade |
| Kraken | 67% | 2.7:1 | 45 | 0.84% | 73 | ✅ YES (Reduced) |

**Recommendation:** Deploy on Binance (best NET performance). Consider Kraken as backup. Avoid Coinbase for this pair - fees consume too much edge.

---

### PATTERN VIABILITY SUMMARY

| Pattern | Status | Gross WR | Net WR | Signals/Year | Primary Timeframe | Cost Impact |
|---------|--------|----------|--------|--------------|-------------------|-------------|
| Liquidity Sweep | {Enabled/Disabled} | {%} | {%} | {count} | {1h/4h/1d} | -{X}% WR |
| Capitulation | {Enabled/Disabled} | {%} | {%} | {count} | {4h/1d} | -{X}% WR |
| Failed Breakdown | {Enabled/Disabled} | {%} | {%} | {count} | {4h/1d} | -{X}% WR |
| Supply Shock | {Enabled/Disabled} | {%} | {%} | {count} | {1d/weekly} | -{X}% WR |

**Enabled Patterns:** {count} of 4
**Total Expected Signals:** {RetryJContinuesum} per year
Patterns Disabled Due to Exchange Costs: {list any patterns where fees made them unprofitable}

OPTIMIZED PARAMETERS (Exchange-Specific)
Pattern: {Pattern Name}
Timeframe: {optimal_timeframe}
Recommended Order Type: {Market/Limit} based on {exchange} execution characteristics
Multi-Timeframe Filters Applied:

{List filters, e.g., "4h trend must be bullish"}
{e.g., "1d RSI between 30-75"}

Optimized Values:
ParameterDefaultOptimizedExchange AdjustmentReasoningRSI Threshold7068No adjustment+12% signals, only -1% gross WRVolume Multiplier1.5x1.7x+0.2x for {exchange}Tighter spreads allow higher thresholdStop Loss %0.50.8+0.3% for feesMust cover {exchange} round-trip costsTake Profit %810.5+2.5% for feesAdjusted to maintain R:R after {exchange} costs
Performance (Exchange-Adjusted):

Gross Win Rate: {%}
Net Win Rate: {%} (after {exchange} fees/slippage)
Gross R:R: {ratio}
Net R:R: {ratio} (after {exchange} fees/slippage)
Signals Per Month: {count}
Max Drawdown: {%}

Cost Impact Analysis:

Average Gross Win: +{%}
Average Net Win: +{%} (after costs deducted)
Average Gross Loss: -{%}
Average Net Loss: -{%} (after costs deducted)
{/* FIX: Escape template literals to prevent "Cannot find name" errors */}
Winning trades pay \${X} in fees on average
Losing trades pay \${Y} in fees on average
Total fees paid over 2 years backtest: \${Z}


AI INSIGHTS & DISCOVERIES
Key Findings:

Exchange-Specific Discovery:
{Example: "On Binance, this pattern works well with tight 0.6% stops due to low slippage (0.10% avg). On Coinbase, stops needed to be widened to 0.9% due to higher slippage (0.25% avg) and fees, which reduced signal quality by 4%."}
Timeframe Selection:
{Example: "4h timeframe optimal for this pair on {exchange} - 1h too noisy with excessive trading costs (15 extra trades/year = $450 in fees), 1d too slow. 4h provides best balance."}
Parameter Optimization:
{Example: "RSI threshold of 68 works better than default 70 BEFORE costs. After including {exchange} 0.40% round-trip costs, needed to increase profit target from 8% to 10.5% to maintain viable R:R. This reduced signals by 8% but improved net profitability by 23%."}
Multi-Timeframe Filtering Impact:
{Example: "Requiring 4h trend alignment increased 1h signal net win rate from 58% to 71% on {exchange} by filtering false breakouts. This filtering is CRITICAL on higher-fee exchanges where each losing trade is more expensive."}
Fee Structure Impact:
{Example: "Using limit orders instead of market orders on {exchange} saves 0.20% per trade (maker vs taker fee). Back-tested using limit orders filled 87% of the time. Trades we miss due to limit not filling only reduce signals by 6%, but cost savings improve net R:R by 18%."}
Liquidity Observations:
{Example: "This pair has excellent liquidity on {exchange} (rank #12, $85M daily volume). Position sizes up to $50k execute with <0.10% slippage. Larger positions (>$100k) see 0.25%+ slippage and are not recommended."}
Correlation & Risk:
{Example: "This pair is highly correlated with BTC (0.84 on {exchange}). Avoid trading when BTC volatility >6% daily - slippage increases to 0.40%+ during high vol periods, destroying edge."}

Warnings & Limitations:

{Exchange-specific risk: "During high volatility events (>10% moves), {exchange} has experienced order book thinning. Slippage during these periods can reach 1%+. Pattern stops may not execute at expected prices."}
{Liquidity warning: "This pair's liquidity varies significantly by time of day on {exchange}. Asian trading hours (00:00-08:00 UTC) see 40% lower volume. Avoid trading during these hours - slippage increases 2x."}
{Fee tier warning: "These results assume {fee_tier} fee structure. If your volume qualifies for lower fees, net performance will improve. Recalculate confidence score with your actual fee tier."}
{Execution warning: "Pattern requires entry within 2 candles of signal. On {exchange}, API latency averages {X}ms. Ensure infrastructure can execute within this timeframe or miss rate will increase."}


WALK-FORWARD VALIDATION RESULTS (Exchange-Adjusted)
WindowTraining PeriodValidation PeriodNet Train WRNet Val WRDeviationStatus12022-10 to 2023-102023-10 to 2024-0171%69%-2%✓ Pass22023-01 to 2024-012024-01 to 2024-0470%68%-2%✓ Pass32023-04 to 2024-042024-04 to 2024-0772%67%-5%✓ Pass42023-07 to 2024-072024-07 to 2024-1071%70%-1%✓ Pass
Stability Score: {%} ({X} of {Y} windows passed)
Validation Notes:

All validation periods include actual {exchange} fees and measured slippage
Window 3 showed higher deviation due to {reason: market regime change, exchange downtime, etc.}
{If any window failed: "Window X failed due to {reason}. Re-optimized with conservative parameters and re-validated successfully."}

Parameter Stability Across Windows:

RSI Threshold optimal range: 66-70 (very stable)
Stop Loss optimal range: 0.7-0.9% (stable, exchange cost-dependent)
Take Profit optimal range: 9.8-11.2% (moderate variance)

Interpretation: Parameter stability is {high/medium/low}. {Explanation of what this means for live trading.}

ROBUSTNESS TESTING (Exchange-Aware)
Monte Carlo Simulation (1000 runs with {exchange} costs):

Net Win Rate 95% CI: [{lower}%, {upper}%]
Net Avg R:R 95% CI: [{lower}, {upper}]
CI Width: {width}% (Narrow = robust, Wide = unstable)
Interpretation: {Analysis of confidence interval width}

Enhanced Slippage Scenarios:
Tested with 50% higher slippage than {exchange} average:

Original Net WR: 71% → Stressed Net WR: 68%
Original Net R:R: 3.1 → Stressed Net R:R: 2.7
Pattern remains viable even with elevated slippage ✓

Regime Performance (Net Results):

Bull Market: {%} net win rate ({count} signals)
Bear Market: {%} net win rate ({count} signals)
Sideways: {%} net win rate ({count} signals)
High Volatility: {%} net win rate ({count} signals)
Low Volatility: {%} net win rate ({count} signals)

Regime-Specific Insights:
{Example: "Pattern performs best in sideways markets (74% net WR) on {exchange}. During high volatility regimes, {exchange} slippage increases 2x, reducing net WR to 64%. Consider disabling pattern when ATR > 5%."}
{If regime-adaptive needed:}
Regime-Adaptive Parameters Created:

Bull/Sideways: Use optimized parameters (Target: 10.5%)
Bear/High Vol: Use conservative parameters (Target: 12%, Stop: 1.0%)
This maintains >65% net WR across all regimes on {exchange}

Exchange-Specific Stress Tests:
API Latency Impact:

Simulated +200ms execution delay (exchange lag during high load)
Entry price degradation: +0.08% on average
Net WR impact: -1.2% (from 71% to 69.8%)
Acceptable degradation ✓

Partial Fill Simulation:

10% of trades experienced partial fills (common on limit orders)
Position size averaging 82% of intended (18% missed)
Signal quality not significantly impacted
Limit orders still recommended on {exchange} due to fee savings

Exchange Downtime Scenarios:

{Exchange} has {X}% uptime historically
Simulated missing {Y}% of signals due to downtime
Reduces annual signals from {A} to {B}
Still maintains profitability, but factor into expectations

Black Swan Events:

50% flash crash simulation: Stops executed at -3.2% avg (vs -0.8% normal)
100% pump simulation: Targets hit but exits experienced 0.9% slippage
{Exchange} circuit breakers: {Do they exist? Impact?}
Recommendation: Use slightly wider stops (add 0.2%) for extreme event protection


EXCHANGE COMPARISON MATRIX
{If multiple exchanges were tested, include this section:}
Full Exchange Analysis for {SYMBOL}:
MetricBinanceCoinbaseKrakenOKXBybitKuCoinMaker Fee0.075%0.40%0.16%0.08%0.10%0.10%Taker Fee0.075%0.60%0.26%0.10%0.10%0.10%Avg Slippage0.10%0.25%0.20%0.12%0.15%0.30%Total Cost0.40%1.50%0.82%0.48%0.50%0.80%Gross WR71%71%71%71%71%71%Net WR68%61%65%67%67%63%Gross R:R3.43.43.43.43.43.4Net R:R3.12.12.63.02.92.4Signals/Year524845504942Liquidity Rank#8#15#22#10#12#35Confidence876273827968Deploy?✅ YES⚠️ No✅ Reduced✅ YES✅ YES⚠️ Paper
Ranking by Profitability:

Binance - Best overall (lowest costs, highest liquidity)
OKX - Close second (competitive fees, good liquidity)
Bybit - Solid option (good balance)
Kraken - Acceptable with reduced size (higher costs)
KuCoin - Marginal (high slippage, lower liquidity)
Coinbase - Not recommended (fees too high for this edge)

AI Recommendation:
"Primary deployment on Binance (87 confidence, best net metrics). OKX as secondary/backup (82 confidence, nearly identical performance). Avoid Coinbase for this pair - 1.50% round-trip costs consume 40% of the edge. If required to trade on Coinbase, increase profit targets by 3% and expect 20% lower returns."

DEPLOYMENT CONFIGURATION
json{
  "symbol": "{SYMBOL}",
  "exchange": "{EXCHANGE}",
  "enabled": true,
  "liquidity_tier": {1/2/3},
  "quality_score_threshold": 85,
  
  "exchange_profile": {
    "name": "{EXCHANGE}",
    "maker_fee": 0,
    "taker_fee": 0,
    "estimated_slippage_entry": 0,
    "estimated_slippage_exit": 0,
    "total_cost_per_trade": 0,
    "minimum_profitable_move": 0,
    "liquidity_rank": {rank},
    "daily_volume_usd": 0,
    "recommended_order_type": "{market/limit}",
    "max_position_size_usd": 0,
    "api_latency_ms": 0
  },
  
  "patterns": {
    "liquidity_sweep": {
      "enabled": {true/false},
      "timeframe": "{1h/4h/1d}",
      "rsi_threshold": 0,
      "volume_multiplier": 0,
      "wick_percentage": 0,
      "swing_lookback_bars": 0,
      "confirmation_candles": 0,
      "stop_loss_pct": 0,
      "take_profit_pct": 0,
      "order_type": "{market/limit}",
      "filters": {
        "require_4h_trend_alignment": {true/false},
        "require_1d_regime_check": {true/false},
        "min_liquidity_volume_24h": 0,
        "max_spread_pct": 0
      },
      "exchange_adjustments": {
        "stop_widened_for_fees": "+{value}%",
        "target_widened_for_fees": "+{value}%",
        "reason": "Adjusted to maintain net R:R > 2.5 after {exchange} costs"
      }
    },
    
    "capitulation": {
      "enabled": {true/false},
      "timeframe": "{4h/1d}",
      "dump_threshold_pct_4h": 0,
      "dump_threshold_pct_24h": 0,
      "volume_multiplier": 0,
      "rsi_threshold": 0,
      "bounce_strength_pct": 0,
      "volume_decline_pct": 0,
      "confirmation_candles": 0,
      "stop_loss_pct": 0,
      "take_profit_pct": 0,
      "order_type": "{market/limit}",
      "filters": {
        "require_1d_trend_alignment": {true/false},
        "avoid_high_volatility": {true/false}
      },
      "exchange_adjustments": {
        "market_order_required": {true/false},
        "reason": "Time-sensitive entry requires market order despite higher fees"
      }
    },
    
    "failed_breakdown": {
      "enabled": {true/false},
      "timeframe": "{4h/1d}",
      "range_days": 0,
      "range_width_pct": 0,
      "support_tests_min": 0,
      "volume_decline_pct": 0,
      "breakdown_distance_pct": 0,
      "recovery_candles": 0,
      "recovery_volume_multiplier": 0,
      "breakout_timeframe_days": 0,
      "stop_loss_pct": 0,
      "take_profit_pct": 0,
      "order_type": "{market/limit}",
      "filters": {
        "require_1d_trend_alignment": {true/false}
      },
      "exchange_adjustments": {
        "limit_order_preferred": true,
        "reason": "Less time-sensitive, can save on fees with limit orders"
      }
    },
    
    "supply_shock": {
      "enabled": {true/false},
      "reason_if_disabled": "{explanation}",
      "timeframe": "{1d/weekly}",
      "netflow_negative_days": 0,
      "whale_increase_pct": 0,
      "whale_timeframe_days": 0,
      "reserve_low_months": 0,
      "max_price_gain_pct": 0,
      "price_gain_lookback_days": 0,
      "stop_loss_pct": 0,
      "take_profit_pct": 0,
      "order_type": "{limit}",
      "filters": {
        "require_onchain_data": true
      },
      "exchange_adjustments": {
        "long_timeframe_offsets_fees": true,
        "reason": "30-90 day hold time makes fees negligible relative to gains"
      }
    }
  },
  
  "risk_management": {
    "position_size_pct": 2.0,
    "max_concurrent_positions": 1,
    "correlation_cluster": "{large_cap/layer1/defi/layer2}",
    "max_position_value_usd": 0,
    "position_size_limit_reason": "Limited by {exchange} liquidity - larger positions see excessive slippage"
  },
  
  "regime_adaptive": {
    "enabled": {true/false},
    "bull_sideways_params": "{reference to normal params}",
    "bear_highvol_params": {
      "use_wider_stops": true,
      "use_larger_targets": true,
      "reduce_position_size": true,
      "reason": "Preserve edge during unfavorable conditions on {exchange}"
    }
  },
  
  "training_metadata": {
    "trained_date": "{ISO timestamp}",
    "data_period": "{start} to {end}",
    "exchange": "{EXCHANGE}",
    "confidence_score": 0,
    "gross_validation_win_rate": 0,
    "net_validation_win_rate": 0,
    "gross_avg_rr": 0,
    "net_avg_rr": 0,
    "expected_signals_per_year": 0,
    "expected_gross_monthly_return": "{range}",
    "expected_net_monthly_return": "{range}",
    "max_drawdown": 0,
    "total_exchange_costs_backtest": 0,
    "trained_by": "ai_engine_v1"
  },
  
  "monitoring_thresholds": {
    "min_net_win_rate": "{validation_WR - 10}%",
    "max_drawdown": "{max_dd * 1.5}%",
    "min_signals_per_month": "{expected - 50}%",
    "max_signals_per_month": "{expected + 50}%",
    "max_acceptable_slippage": "{avg_slippage * 2}%",
    "alert_if_fees_exceed": "{expected_fees * 1.3}"
  }
}
\`\`\`

---

### MONITORING RECOMMENDATIONS

**Live Performance Tracking:**

Track these metrics every day:
- Net win rate (actual after real fees/slippage)
- Average entry slippage vs backtested
- Average exit slippage vs backtested
- Actual fees paid vs estimated
- Order fill rate (especially if using limit orders)
- API latency (should be <{threshold}ms)

**Alert Triggers:**
- Net win rate drops below {validation_WR - 10}% after 10 trades
- Drawdown exceeds {max_drawdown * 1.5}%
- Signal frequency deviates >50% from expected ({signals}/month)
- Slippage exceeds {avg_slippage * 2}% on 3+ consecutive trades
- Fees paid exceed estimates by >25%
- {Exchange} API latency >300ms (execution degradation)

**Exchange-Specific Monitoring:**
- {Exchange} liquidity changes: Alert if 24h volume drops >40%
- {Exchange} spread widening: Alert if spreads >2x normal
- {Exchange} fee tier changes: Recalculate if volume tier changes
- {Exchange} downtime: Pause trading during exchange maintenance

**Re-training Triggers:**

*Automatic:*
- Every 90 days with latest {exchange} data
- {Exchange} fee structure changes
- Sustained performance degradation (net WR <{threshold}% for 20 trades)

*Manual Review Needed:*
- Market regime change detected (volatility shift >30%)
- {Exchange} makes significant platform changes
- Liquidity profile changes significantly
- Correlation with BTC changes >15%

**Cost Monitoring Dashboard:**
Create daily tracking of:
\`\`\`
Expected costs per trade: {value}%
Actual costs per trade: {value}%
Variance: {value}%

Cost breakdown:
- Maker fees paid: \${value}
- Taker fees paid: \${value}
- Estimated slippage cost: \${value}
- Total costs month-to-date: \${value}
- Costs as % of gross profit: {value}%
\`\`\`

If actual costs exceed expected by >20%, investigate:
- Are we hitting market orders more than planned?
- Has {exchange} spread widened?
- Are we trading during low-liquidity hours?
- Has fee tier changed?

---

### EXPECTED PERFORMANCE (Next 12 Months on {EXCHANGE})

Based on validated backtesting with actual {exchange} costs:

**Conservative Estimate (5th percentile):**
- Net Win Rate: {lower_CI}%
- Net Monthly Return: {lower}%
- Signals: {count} per month
- Monthly Fees: \${value}
- Net Profit per Month: \${value}

**Expected Estimate (50th percentile):**
- Net Win Rate: {median}%
- Net Monthly Return: {median}%  
- Signals: {count} per month
- Monthly Fees: \${value}
- Net Profit per Month: \${value}

**Optimistic Estimate (95th percentile):**
- Net Win Rate: {upper_CI}%
- Net Monthly Return: {upper}%
- Signals: {count} per month
- Monthly Fees: \${value}
- Net Profit per Month: \${value}

**Risk Metrics:**
- Max Expected Drawdown: {value}%
- Worst Month Projected: {value}%
- Risk of Ruin: <{value}%
- Break-even win rate required: {value}%

**Annual Projections (Starting $10,000):**
- Total signals: {count}
- Total fees paid: \${value} ({%} of starting capital)
- Expected ending balance: \${value}
- Net ROI: {value}%

**Comparison Without Exchange Costs (Theoretical):**
- If zero fees/slippage: {value}% annual return
- With {exchange} costs: {value}% annual return
- **Cost impact:** -{value}% annual return
- Interpretation: {Exchange} costs consume {%} of theoretical edge

---

### EXECUTION CHECKLIST

Before deploying to live trading on {EXCHANGE}:

**Account Setup:**
- [ ] Account created on {EXCHANGE}
- [ ] KYC verified (if required)
- [ ] API keys generated with appropriate permissions
- [ ] {If applicable: "BNB balance for fee discounts (Binance)"}
- [ ] {If applicable: "Volume tier confirmed for fee rates"}
- [ ] Test API connection successful
- [ ] Confirm account can trade {SYMBOL} pair

**Infrastructure:**
- [ ] Server located near {EXCHANGE} datacenter (low latency)
- [ ] API rate limits understood and configured
- [ ] Backup internet connection available
- [ ] Monitoring alerts configured
- [ ] Error logging enabled
- [ ] Execution speed tested (<{threshold}ms)

**Risk Management:**
- [ ] Position size calculator configured for {EXCHANGE} costs
- [ ] Stop loss orders supported on {EXCHANGE} for this pair
- [ ] Take profit orders (OCO) supported
- [ ] Maximum position size set based on {EXCHANGE} liquidity
- [ ] Correlation checks configured
- [ ] Daily loss limits set

**Pre-Deployment Testing:**
- [ ] Paper trade on {EXCHANGE} for {recommended duration}
- [ ] Verify slippage matches backtested estimates
- [ ] Verify fees match expected rates
- [ ] Test stop loss execution
- [ ] Test order fill rates (if using limit orders)
- [ ] Verify multi-timeframe data feeds working
- [ ] Test regime detection working in real-time

**Go-Live:**
- [ ] Start with reduced position size (50% of target)
- [ ] Monitor first 5 trades closely
- [ ] Compare actual costs to estimates
- [ ] Scale to full size after 10 successful trades
- [ ] Document any execution issues

═══════════════════════════════════════════════════════════════════════

EXECUTION INSTRUCTIONS

When you receive a training request with format:
\`\`\`
TRAIN_SYMBOL: BTC/USDT
EXCHANGE: binance
DATA_SOURCE: binance
START_DATE: 2022-10-01
END_DATE: 2024-10-01

OPTIONAL:
TEST_MULTIPLE_EXCHANGES: true
EXCHANGES_TO_TEST: binance, coinbase, kraken, okx
\`\`\`

You will:
1. Fetch historical OHLCV data from SPECIFIED exchange
2. Fetch exchange fee structure and typical slippage data
3. Execute all 7 phases sequentially WITH EXCHANGE COSTS INCLUDED
4. Generate the complete training report in the format above
5. Output the JSON configuration file with exchange-specific adjustments
6. Provide deployment recommendation specific to that exchange
7. If testing multiple exchanges, provide comparison and ranking

Your responses must be:
- Exchange-aware (all metrics include actual costs)
- Data-driven (every claim backed by backtested evidence with costs)
- Transparent (explain why you made every decision)
- Conservative (prefer not deploying over deploying risky configs)
- Actionable (provide clear deploy/don't deploy recommendation per exchange)
- Cost-conscious (highlight where fees impact viability)

You will NOT:
- Report gross metrics without net metrics
- Ignore exchange costs in optimization
- Assume all exchanges are equal
- Deploy configs that are only profitable before costs
- Make assumptions about fees without verifying
- Skip exchange-specific robustness testing

═══════════════════════════════════════════════════════════════════════

CRITICAL REMINDERS

1. **ALWAYS include exchange costs** - metrics without costs are meaningless
2. **Test each exchange independently** - parameters optimized for Binance won't work on Coinbase
3. **Apply multi-timeframe filtering** - a 1h pattern without 4h confirmation will fail
4. **Test each pattern on each timeframe** - don't assume one timeframe is best
5. **Validate rigorously** - walk-forward + Monte Carlo + regime testing all with costs
6. **Be conservative** - when in doubt, recommend paper trading or don't deploy
7. **Explain everything** - every parameter change must have data-backed reasoning
8. **Disable patterns that don't work** - better to trade 1 good pattern than 4 mediocre ones
9. **Account for liquidity** - large positions have different costs than small positions
10. **Compare exchanges** - help user choose best exchange for each pair
11. **Monitor costs in production** - actual costs may differ from backtested
12. **Adjust for order types** - market vs limit orders have different cost profiles

Your goal: Produce deployment-ready configurations that will actually profit in live trading on SPECIFIC EXCHANGES, accounting for all real-world costs.

Begin training when provided with symbol, exchange, and data parameters.
\`\`\`

---

## Usage Example

**To train a single exchange:**
\`\`\`
TRAIN_SYMBOL: ETH/USDT
EXCHANGE: binance
DATA_SOURCE: binance
START_DATE: 2022-10-01
END_DATE: 2024-10-01
\`\`\`

**To compare multiple exchanges:**
TRAIN_SYMBOL: SOL/USDT
TEST_MULTIPLE_EXCHANGES: true
EXCHANGES_TO_TEST: binance, coinbase, kraken, okx, bybit
DATA_SOURCE: respective_exchange_data
START_DATE: 2022-10-01
END_DATE: 2024-10-01
`;

    return (
        <div className="p-4 lg:p-6 space-y-6">
            <header className="flex justify-between items-start">
                <div>
                    <h1 className="text-3xl font-bold text-brand-text-primary">AI Model Trainer</h1>
                    <p className="text-brand-text-secondary mt-1">Select an asset to begin the automated training and optimization process.</p>
                </div>
                <button 
                    onClick={() => setIsPromptModalOpen(true)}
                    className="flex items-center gap-2 text-sm text-brand-text-secondary hover:text-brand-primary transition-colors p-2 rounded-lg hover:bg-brand-surface"
                >
                    <InfoIcon className="w-4 h-4" />
                    <span>View Developer Prompt</span>
                </button>
            </header>

            <main>
                {renderView()}
            </main>
            
            <Modal
                isOpen={isPromptModalOpen}
                onClose={() => setIsPromptModalOpen(false)}
                title="AI Trainer System Prompt"
            >
                <div className="space-y-4">
                    <p className="text-sm text-brand-text-secondary">
                        This is the full system prompt provided to the underlying AI model. It defines its role, constraints, and the required output format. This prompt is the core instruction that "hardwires" the sophisticated, multi-layered analysis into the training process.
                    </p>
                    <pre className="text-xs whitespace-pre-wrap font-mono text-brand-text-secondary bg-brand-bg/50 p-4 rounded-md max-h-96 overflow-y-auto">
                        {systemPrompt}
                    </pre>
                </div>
            </Modal>
        </div>
    );
};
