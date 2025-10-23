import React from 'react';

interface DataTableProps {
    headers: string[];
    data: (string | number | React.ReactNode)[][];
}

export const DataTable: React.FC<DataTableProps> = ({ headers, data }) => {
    return (
        <div className="overflow-x-auto h-full">
            <div className="h-full overflow-y-auto">
                <table className="min-w-full text-sm text-left">
                    <thead className="sticky top-0 bg-brand-surface border-b border-brand-border">
                        <tr>
                            {headers.map((header, index) => (
                                <th key={index} scope="col" className="px-4 py-3 font-medium text-brand-text-secondary uppercase tracking-wider">
                                    {header}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-brand-border">
                        {data.map((row, rowIndex) => (
                            <tr key={rowIndex} className="hover:bg-white/5 transition-colors duration-200">
                                {row.map((cell, cellIndex) => (
                                    <td key={cellIndex} className="px-4 py-3 whitespace-nowrap text-brand-text-primary">
                                        {cell}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};