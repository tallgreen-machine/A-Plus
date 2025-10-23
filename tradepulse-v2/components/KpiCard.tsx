
import React from 'react';
import { ArrowUpIcon, ArrowDownIcon } from './icons';

interface KpiCardProps {
    title: string;
    value: string;
    icon: React.ReactNode;
    change?: string;
    changeType?: 'positive' | 'negative';
}

export const KpiCard: React.FC<KpiCardProps> = ({ title, value, icon, change, changeType }) => {
    const changeColor = changeType === 'positive' ? 'text-brand-positive' : 'text-brand-negative';
    const ChangeIcon = changeType === 'positive' ? ArrowUpIcon : ArrowDownIcon;

    return (
        <div className="bg-brand-surface p-4 rounded-lg border border-brand-border transition-all duration-300 ease-in-out hover:shadow-md hover:-translate-y-1">
            <div className="flex items-center justify-between mb-1">
                <p className="text-sm text-brand-text-secondary font-medium">{title}</p>
                 <div className="text-brand-text-secondary">{icon}</div>
            </div>
            <div className="flex items-baseline space-x-2">
                <p className="text-2xl font-semibold text-brand-text-primary">{value}</p>
                {change && (
                    <div className={`flex items-center text-sm font-semibold ${changeColor}`}>
                        <ChangeIcon />
                        <span>{change}</span>
                    </div>
                )}
            </div>
        </div>
    );
};
