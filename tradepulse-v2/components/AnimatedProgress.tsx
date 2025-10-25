import React, { useEffect, useRef } from 'react';

interface LogEntry {
  timestamp: string;
  message: string;
  progress: number;
  jobId: number;
  job_metadata?: {
    strategy_name: string;
    pair: string;
    exchange: string;
  };
}

interface ProgressData {
  progress: number;
  current_episode?: number;
  total_episodes?: number;
  current_reward?: number;
  current_loss?: number;
  stage?: string;
  status?: string;
}

interface AnimatedProgressProps {
  logs: LogEntry[];
  currentProgress?: ProgressData;
}

const AnimatedProgress: React.FC<AnimatedProgressProps> = ({ logs, currentProgress }) => {
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Group logs by job_id to add headers
  const groupedLogs: { jobId: number; logs: LogEntry[] }[] = [];
  let currentJobId: number | null = null;
  
  logs.forEach(log => {
    if (log.jobId !== currentJobId) {
      currentJobId = log.jobId;
      groupedLogs.push({ jobId: log.jobId, logs: [log] });
    } else {
      groupedLogs[groupedLogs.length - 1].logs.push(log);
    }
  });

  if (logs.length === 0) {
    return (
      <div className="bg-gray-950 rounded-lg p-4 h-full flex items-center justify-center">
        <p className="text-sm text-gray-500 font-mono">No training logs yet...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-950 rounded-lg p-4 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 font-mono">Training Progress</h3>
        <span className="text-xs text-gray-500 font-mono">{logs.length} log entries</span>
      </div>

      {/* Current Progress Display */}
      {currentProgress && currentProgress.status === 'running' && (
        <div className="mb-4 p-3 bg-gray-900 rounded-lg border border-gray-800">
          {/* Progress Bar */}
          <div className="mb-3">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-gray-400 font-mono">
                {currentProgress.stage || 'Training...'}
              </span>
              <span className="text-xs text-blue-400 font-mono font-semibold">
                {currentProgress.progress.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-300 ease-out"
                style={{ width: `${currentProgress.progress}%` }}
              />
            </div>
          </div>

          {/* Training Details */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            {currentProgress.current_episode !== undefined && currentProgress.total_episodes && (
              <div className="flex justify-between">
                <span className="text-gray-500">Episode:</span>
                <span className="text-gray-300 font-mono">
                  {currentProgress.current_episode} / {currentProgress.total_episodes}
                </span>
              </div>
            )}
            {currentProgress.current_reward !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">Reward:</span>
                <span className={`font-mono ${currentProgress.current_reward >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {currentProgress.current_reward.toFixed(2)}
                </span>
              </div>
            )}
            {currentProgress.current_loss !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">Loss:</span>
                <span className="text-yellow-400 font-mono">
                  {currentProgress.current_loss.toFixed(4)}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Log content */}
      <div 
        ref={logContainerRef}
        className="flex-1 overflow-y-auto font-mono text-xs space-y-1"
      >
        {groupedLogs.map((group, groupIndex) => (
          <div key={`job-${group.jobId}-${groupIndex}`}>
            <div className="sticky top-0 bg-gray-900 border-l-4 border-blue-500 px-3 py-2 mb-2 mt-3 first:mt-0">
              <div className="text-blue-400 font-semibold">
                === Job #{group.jobId} {group.logs[0].job_metadata && (
                  <>
                    | {group.logs[0].job_metadata.strategy_name} | {group.logs[0].job_metadata.pair} | {group.logs[0].job_metadata.exchange}
                  </>
                )} | {group.logs[0].timestamp} ===
              </div>
            </div>
            
            {group.logs.map((entry, index) => (
              <div 
                key={`${group.jobId}-${index}`}
                className="px-2 py-1 hover:bg-gray-900/50"
              >
                <span className="text-gray-500">[{entry.timestamp}]</span>{' '}
                <span className="text-gray-300 whitespace-pre-wrap">{entry.message}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default AnimatedProgress;
