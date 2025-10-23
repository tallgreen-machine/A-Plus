import React from 'react';
import type { TrainedConfiguration } from '../types';
import { Modal } from './Modal';
import { SparklesIcon, BarChartIcon, BrainCircuitIcon, CheckCircle2Icon } from './icons';

// A small component for consistent metric display
const MetricDisplay: React.FC<{ label: string; value: string | number; className?: string }> = ({ label, value, className = '' }) => (
    <div className={`bg-brand-bg/50 p-3 rounded-md border border-brand-border/50 ${className}`}>
        <p className="text-xs text-brand-text-secondary">{label}</p>
        <p className="text-xl font-semibold font-mono text-brand-text-primary">{value}</p>
    </div>
);

const formatPercent = (val: number) => `${val.toFixed(2)}%`;
const formatNumber = (val: number, decimals = 2) => val.toFixed(decimals);

const LifecycleBadge: React.FC<{ stage: TrainedConfiguration['lifecycle_stage'] }> = ({ stage }) => {
    const config = {
        MATURE: 'bg-green-500/10 text-green-400',
        VALIDATION: 'bg-sky-500/10 text-sky-400',
        DISCOVERY: 'bg-purple-500/10 text-purple-400',
        DECAY: 'bg-yellow-500/10 text-yellow-400',
        PAPER: 'bg-gray-500/10 text-gray-400',
    };
    const color = config[stage] || config.PAPER;
    return <span className={`px-2 py-1 text-xs font-bold rounded-full ${color}`}>{stage}</span>;
}

export const ConfigurationDetailModal: React.FC<{
    isOpen: boolean;
    onClose: () => void;
    config: TrainedConfiguration | null;
}> = ({ isOpen, onClose, config }) => {
    if (!config) return null;
    
    const isProfitable = config.performance.net_profit > 0;

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`Configuration Details: ${config.pair}`}>
            <div className="space-y-6">
                {/* Header Section */}
                <div className="p-4 bg-brand-bg rounded-lg border border-brand-border flex justify-between items-center">
                    <div>
                        <h2 className="text-xl font-bold text-brand-text-primary">{config.strategy_name}</h2>
                        <p className="text-sm text-brand-text-secondary">{config.exchange} &middot; {config.timeframe}</p>
                    </div>
                    <LifecycleBadge stage={config.lifecycle_stage} />
                </div>

                {/* Performance Overview */}
                <section>
                    <h3 className="text-base font-semibold text-brand-text-primary mb-3 flex items-center gap-2">
                        <BarChartIcon className="w-4 h-4 text-brand-text-secondary" />
                        Performance Snapshot
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <MetricDisplay label="Net Profit" value={formatPercent(config.performance.net_profit)} className={isProfitable ? 'text-brand-positive' : 'text-brand-negative'}/>
                        <MetricDisplay label="Gross Win Rate" value={formatPercent(config.performance.gross_win_rate)} />
                        <MetricDisplay label="Sharpe Ratio" value={formatNumber(config.validation.sharpe_ratio)} />
                        <MetricDisplay label="Sample Size" value={config.performance.sample_size} />
                    </div>
                </section>

                {/* Parameters Section */}
                <section>
                    <h3 className="text-base font-semibold text-brand-text-primary mb-3 flex items-center gap-2">
                        <SparklesIcon className="w-4 h-4 text-brand-text-secondary" />
                        Strategy Parameters
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm bg-brand-bg/50 p-4 rounded-md border border-brand-border/50">
                        {Object.entries(config.parameters).map(([key, value]) => (
                             <div key={key}>
                                <p className="capitalize text-brand-text-secondary">{key.replace(/_/g, ' ')}</p>
                                <p className="font-mono font-semibold text-brand-text-primary">{String(value)}</p>
                            </div>
                        ))}
                    </div>
                </section>
                
                {/* Validation Section */}
                <section>
                    <h3 className="text-base font-semibold text-brand-text-primary mb-3 flex items-center gap-2">
                        <CheckCircle2Icon className="w-4 h-4 text-brand-text-secondary" />
                        Statistical Validation
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm bg-brand-bg/50 p-4 rounded-md border border-brand-border/50">
                         {Object.entries(config.validation).map(([key, value]) => (
                             <div key={key}>
                                <p className="capitalize text-brand-text-secondary">{key.replace(/_/g, ' ')}</p>
                                <p className="font-mono font-semibold text-brand-text-primary">{formatNumber(value as number, 3)}</p>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Regime Section */}
                <section>
                    <h3 className="text-base font-semibold text-brand-text-primary mb-3 flex items-center gap-2">
                        <BrainCircuitIcon className="w-4 h-4 text-brand-text-secondary" />
                        Market Regime Probabilities
                    </h3>
                     <div className="grid grid-cols-3 gap-3 text-sm bg-brand-bg/50 p-4 rounded-md border border-brand-border/50">
                        {Object.entries(config.regime.regime_probabilities).map(([key, value]) => (
                             <div key={key} className="text-center">
                                <p className="capitalize text-brand-text-secondary">{key}</p>
                                <p className="font-mono font-semibold text-brand-text-primary text-lg">{formatPercent(value as number)}</p>
                            </div>
                        ))}
                    </div>
                </section>
            </div>
        </Modal>
    );
};