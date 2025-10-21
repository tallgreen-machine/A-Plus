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

    const tabTextSize = isSubTabs ? 'text-sm' : 'text-lg';
    const tabPadding = isSubTabs ? 'py-2 px-1' : 'py-3 px-1';

    const handleTabClick = (index: number) => {
        setActiveTab(index);
        onTabClick?.(index);
    };

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
};