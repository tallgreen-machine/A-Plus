import React from 'react';
import type { TrainedConfiguration } from '../types';

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

interface ConfigurationCardProps {
    config: TrainedConfiguration;
    onClick: () => void;
    displayNetProfit: number;
    displayWinRate: number;
    metricType: 'live' | 'trained';
}

export const ConfigurationCard: React.FC<ConfigurationCardProps> = ({ config, onClick, displayNetProfit, displayWinRate, metricType }) => {
    const isProfitable = displayNetProfit > 0;
    const isUntraded = config.performance.sample_size === 0;

    const bgColor = isUntraded && metricType === 'trained' ? 'bg-brand-surface' : 'bg-brand-bg';
    const textColor = isUntraded && metricType === 'trained' ? 'text-brand-text-secondary' : 'text-brand-text-primary';

    return (
        <div 
            onClick={onClick}
            className={`w-72 flex-shrink-0 ${bgColor} p-3 rounded-lg border border-brand-border text-left space-y-2 cursor-pointer transition-all hover:-translate-y-1 hover:border-brand-primary`}
        >
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <span className={`font-bold text-sm ${textColor} block truncate`} title={config.pair}>{config.pair}</span>
                    <span className="text-xs text-brand-text-secondary">{config.exchange} &middot; {config.timeframe}</span>
                </div>
                <LifecycleBadge stage={config.lifecycle_stage} />
            </div>

            {/* Strategy Name */}
            <p className="text-xs text-brand-text-secondary truncate" title={config.strategy_name}>
                {config.strategy_name}
            </p>

            {/* Metrics */}
            <div className="pt-1 grid grid-cols-3 gap-2 text-center">
                 <div>
                    <p className="text-[10px] text-brand-text-secondary">Net Profit</p>
                    <p className={`text-sm font-bold font-mono ${isUntraded && metricType === 'trained' ? 'text-brand-text-secondary' : isProfitable ? 'text-brand-positive' : 'text-brand-negative'}`}>
                        {isUntraded && metricType === 'trained' ? 'N/A' : `${displayNetProfit.toFixed(2)}%`}
                    </p>
                </div>
                 <div>
                    <p className="text-[10px] text-brand-text-secondary">Win Rate</p>
                    <p className={`text-sm font-bold font-mono ${textColor}`}>
                         {isUntraded && metricType === 'trained' ? 'N/A' : `${displayWinRate.toFixed(1)}%`}
                    </p>
                </div>
                <div>
                    <p className="text-[10px] text-brand-text-secondary">Sharpe</p>
                    <p className={`text-sm font-bold font-mono ${textColor}`}>
                        {isUntraded ? 'N/A' : config.validation.sharpe_ratio.toFixed(2)}
                    </p>
                </div>
            </div>
        </div>
    );
};
