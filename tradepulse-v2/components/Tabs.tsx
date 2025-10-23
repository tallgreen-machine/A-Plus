import React, { useState } from 'react';

interface Tab {
    label: string;
    content: React.ReactNode;
}

interface TabsProps {
    tabs: Tab[];
    isSubTabs?: boolean;
    isCollapsed?: boolean;
    onTabClick?: (index: number) => void;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, isSubTabs = false, isCollapsed = false, onTabClick }) => {
    const [activeTab, setActiveTab] = useState(0);

    const handleTabClick = (index: number) => {
        setActiveTab(index);
        onTabClick?.(index);
    };

    // Style for simple, underlined sub-tabs (e.g., in AI Trainer)
    if (isSubTabs) {
        const tabTextSize = 'text-sm';
        const tabPadding = 'py-2 px-1';
        return (
            <div className="flex flex-col h-full">
                <div className="border-b border-brand-border">
                    <nav className="-mb-px flex space-x-4" aria-label="Tabs">
                        {tabs.map((tab, index) => (
                            <button
                                key={tab.label}
                                onClick={() => handleTabClick(index)}
                                className={`${
                                    activeTab === index
                                        ? 'border-brand-primary text-brand-primary font-semibold'
                                        : 'border-transparent text-brand-text-secondary hover:text-brand-text-primary hover:border-gray-300'
                                } whitespace-nowrap ${tabPadding} border-b-2 font-medium ${tabTextSize} transition-all duration-200 ease-in-out focus:outline-none`}
                                aria-current={activeTab === index ? 'page' : undefined}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </nav>
                </div>
                <div className={`mt-4 flex-grow transition-opacity duration-300 h-full ${isCollapsed ? 'opacity-0 h-0 overflow-hidden invisible' : 'opacity-100 visible'}`}>
                    {tabs[activeTab] && tabs[activeTab].content}
                </div>
            </div>
        );
    }

    // Style for main, physical-looking tabs (e.g., in the bottom panel)
    return (
        <div className="flex flex-col h-full">
            {/* Tab Buttons */}
            <div className="shrink-0 py-2">
                <nav className="flex space-x-2" aria-label="Tabs">
                    {tabs.map((tab, index) => (
                        <button
                            key={tab.label}
                            onClick={() => handleTabClick(index)}
                            className={`px-4 py-2 text-lg font-semibold rounded-t-lg transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-inset focus:ring-brand-primary ${
                                activeTab === index
                                    ? 'bg-brand-surface text-brand-text-primary'
                                    : 'bg-transparent text-brand-text-secondary hover:bg-brand-surface/50 hover:text-brand-text-primary'
                            }`}
                            aria-current={activeTab === index ? 'page' : undefined}
                        >
                            {tab.label}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Content Panel */}
            <div className={`
                flex-grow bg-brand-surface rounded-b-lg rounded-tr-lg
                transition-all duration-300
                ${isCollapsed ? 'opacity-0 h-0 overflow-hidden invisible p-0' : 'opacity-100 visible p-4'}
            `}>
                <div className="h-full">
                    {tabs[activeTab] && tabs[activeTab].content}
                </div>
            </div>
        </div>
    );
};