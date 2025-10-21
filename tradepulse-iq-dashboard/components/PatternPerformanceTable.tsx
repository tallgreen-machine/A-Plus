
import React, { useState } from 'react';
import type { PatternPerformance } from '../types';
import { PatternStatus } from '../types';
import { ChevronDownIcon, ChevronUpIcon } from './icons';

interface PatternPerformanceTableProps {
    patterns: PatternPerformance[];
}

const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

export const PatternPerformanceTable: React.FC<PatternPerformanceTableProps> = ({ patterns }) => {
    const [expandedRowId, setExpandedRowId] = useState<string | null>(null);

    if (!patterns || patterns.length === 0) {
        return <div className="text-brand-text-secondary text-center py-4">No pattern data available.</div>;
    }

    const handleRowClick = (patternId: string) => {
        setExpandedRowId(currentId => (currentId === patternId ? null : patternId));
    };

    return (
        <div className="overflow-x-auto">
             <table className="min-w-full text-sm text-left">
                <thead className="bg-brand-surface border-b border-brand-border">
                    <tr>
                        <th scope="col" className="px-4 py-3 font-medium text-brand-text-secondary uppercase">Pattern Name</th>
                        <th scope="col" className="px-4 py-3 font-medium text-brand-text-secondary uppercase">Status</th>
                        <th scope="col" className="px-4 py-3 font-medium text-brand-text-secondary uppercase">Total P/L</th>
                        <th scope="col" className="px-4 py-3 font-medium text-brand-text-secondary uppercase">Win/Loss Ratio</th>
                        <th scope="col" className="px-4 py-3 font-medium text-brand-text-secondary uppercase">Total Trades</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-brand-border">
                    {patterns.map((pattern) => (
                        <React.Fragment key={pattern.id}>
                            <tr
                                className="hover:bg-white/5 cursor-pointer transition-colors duration-200"
                                onClick={() => handleRowClick(pattern.id)}
                            >
                                <td className="px-4 py-3 whitespace-nowrap font-semibold text-brand-text-primary">
                                    <div className="flex items-center gap-2">
                                        <span className="text-brand-text-secondary">
                                            {expandedRowId === pattern.id ? <ChevronUpIcon /> : <ChevronDownIcon />}
                                        </span>
                                        <span>{pattern.name}</span>
                                    </div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">
                                    <span className={`px-2 py-1 text-xs font-bold rounded-full ${
                                        pattern.status === PatternStatus.ACTIVE ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'
                                    }`}>
                                        {pattern.status}
                                    </span>
                                </td>
                                <td className={`px-4 py-3 whitespace-nowrap font-semibold ${pattern.totalPL >= 0 ? 'text-brand-positive' : 'text-brand-negative'}`}>
                                    {formatCurrency(pattern.totalPL)}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">{pattern.winLossRatio.toFixed(2)}</td>
                                <td className="px-4 py-3 whitespace-nowrap">{pattern.totalTrades}</td>
                            </tr>
                            {expandedRowId === pattern.id && (
                                <tr className="bg-black/20">
                                    <td colSpan={5} className="p-0">
                                        <div className="p-4 border-l-4 border-brand-primary animate-fade-in-slow">
                                            <h4 className="text-md font-semibold text-brand-text-primary mb-3">Parameters</h4>
                                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-x-8 gap-y-3 text-sm">
                                                {Object.entries(pattern.parameters).map(([key, value]) => (
                                                    <div key={key} className="flex flex-col">
                                                        <span className="text-brand-text-secondary">{key}</span>
                                                        <span className="font-semibold text-brand-text-primary">{String(value)}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </React.Fragment>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
