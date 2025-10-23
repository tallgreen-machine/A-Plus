
import React, { useEffect, useRef } from 'react';

interface LogViewerProps {
    logs: string[];
}

export const LogViewer: React.FC<LogViewerProps> = ({ logs }) => {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const formatLog = (log: string) => {
        if (log.startsWith("INFO:")) return <span className="text-blue-400">{log}</span>;
        if (log.startsWith("WARN:")) return <span className="text-yellow-400">{log}</span>;
        if (log.startsWith("ERROR:") || log.startsWith("CRITICAL:")) return <span className="text-red-400">{log}</span>;
        if (log.startsWith("DEBUG:")) return <span className="text-gray-500">{log}</span>;
        return <span>{log}</span>;
    }

    return (
        <div ref={scrollRef} className="h-full overflow-y-auto bg-black/20 p-2 rounded">
            <pre className="text-xs whitespace-pre-wrap font-mono">
                {logs.map((log, index) => (
                    <div key={index}>{formatLog(log)}</div>
                ))}
            </pre>
        </div>
    );
};