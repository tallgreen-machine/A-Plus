
import React from 'react';
import { BotStatusState } from '../types';

interface StatusIndicatorProps {
    status: BotStatusState;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status }) => {
    const statusConfig = {
        [BotStatusState.RUNNING]: { text: 'Running', color: 'bg-brand-positive' },
        [BotStatusState.STOPPED]: { text: 'Stopped', color: 'bg-gray-500' },
        [BotStatusState.FAILED]: { text: 'Failed', color: 'bg-brand-negative' },
    };

    const { text, color } = statusConfig[status] || statusConfig[BotStatusState.STOPPED];

    return (
        <div className="flex items-center space-x-2 bg-brand-surface/70 border border-brand-border p-2 rounded-lg">
            <span className={`h-3 w-3 rounded-full ${color}`}></span>
            <span className="text-sm font-semibold text-brand-text-primary">{text}</span>
        </div>
    );
};