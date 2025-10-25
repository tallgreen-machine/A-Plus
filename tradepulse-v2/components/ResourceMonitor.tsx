import React, { useEffect, useState } from 'react';

interface SystemResources {
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  error?: string;
}

const ResourceMonitor: React.FC = () => {
  const [resources, setResources] = useState<SystemResources | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchResources = async () => {
      try {
        const response = await fetch('/api/system/resources');
        const data = await response.json();
        setResources(data);
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to fetch system resources:', error);
        setIsLoading(false);
      }
    };

    // Fetch immediately
    fetchResources();

    // Then poll every 5 seconds
    const interval = setInterval(fetchResources, 5000);

    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center gap-6 px-6 py-3 bg-gray-900 border-b border-gray-800">
        <div className="h-5 w-32 bg-gray-800 rounded animate-pulse" />
        <div className="h-5 w-32 bg-gray-800 rounded animate-pulse" />
        <div className="h-5 w-32 bg-gray-800 rounded animate-pulse" />
      </div>
    );
  }

  if (!resources || resources.error) {
    return null;
  }

  const getColorClass = (percent: number): string => {
    if (percent >= 90) return 'text-red-400';
    if (percent >= 75) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getBarColorClass = (percent: number): string => {
    if (percent >= 90) return 'bg-red-500';
    if (percent >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="flex items-center gap-6 px-6 py-3 bg-gray-900 border-b border-gray-800">
      {/* CPU Usage */}
      <div className="flex items-center gap-2">
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
        <span className="text-sm text-gray-400">CPU</span>
        <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getBarColorClass(resources.cpu_percent)}`}
            style={{ width: `${Math.min(resources.cpu_percent, 100)}%` }}
          />
        </div>
        <span className={`text-sm font-mono ${getColorClass(resources.cpu_percent)}`}>
          {resources.cpu_percent.toFixed(1)}%
        </span>
      </div>

      {/* RAM Usage */}
      <div className="flex items-center gap-2">
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <span className="text-sm text-gray-400">RAM</span>
        <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getBarColorClass(resources.ram_percent)}`}
            style={{ width: `${Math.min(resources.ram_percent, 100)}%` }}
          />
        </div>
        <span className={`text-sm font-mono ${getColorClass(resources.ram_percent)}`}>
          {resources.ram_used_gb.toFixed(1)}/{resources.ram_total_gb.toFixed(1)} GB
        </span>
      </div>

      {/* Disk Usage */}
      <div className="flex items-center gap-2">
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
        <span className="text-sm text-gray-400">Disk</span>
        <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getBarColorClass(resources.disk_percent)}`}
            style={{ width: `${Math.min(resources.disk_percent, 100)}%` }}
          />
        </div>
        <span className={`text-sm font-mono ${getColorClass(resources.disk_percent)}`}>
          {resources.disk_used_gb.toFixed(1)}/{resources.disk_total_gb.toFixed(1)} GB
        </span>
      </div>
    </div>
  );
};

export default ResourceMonitor;
