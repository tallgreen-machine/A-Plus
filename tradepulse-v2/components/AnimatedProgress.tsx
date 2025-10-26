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

  // Build live CLI progress display from currentProgress
  const buildLiveProgress = () => {
    if (!currentProgress || currentProgress.status !== 'running') return null;
    
    const { 
      stage, current_episode, total_episodes, current_reward, current_loss, progress,
      jobId, strategy_name, pair, exchange, timeframe, regime
    } = currentProgress;
    
    // Build job header line
    const jobHeader = `=== Job #${jobId} | ${strategy_name} | ${pair} | ${exchange} | ${timeframe} | ${regime} ===`;
    
    // Build status line
    const parts = [stage || 'Training...'];
    if (current_episode !== undefined && total_episodes) {
      parts.push(`Episode ${current_episode}/${total_episodes}`);
    }
    if (current_reward != null) {
      parts.push(`Reward: ${current_reward.toFixed(2)}`);
    }
    if (current_loss != null) {
      parts.push(`Loss: ${current_loss.toFixed(4)}`);
    }
    const statusLine = parts.join(' | ');
    
    // Build ASCII progress bar
    const barWidth = 50;
    const filled = Math.floor(barWidth * (progress || 0) / 100);
    const empty = barWidth - filled;
    const bar = '█'.repeat(filled) + '░'.repeat(empty);
    const progressLine = `[${(progress || 0).toFixed(2)}%] ${bar}`;
    
    return `${jobHeader}\n${statusLine}\n${progressLine}`;
  };

  const liveProgress = buildLiveProgress();

  if (logs.length === 0 && !liveProgress) {
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
        <h3 className="text-sm font-semibold text-gray-400 font-mono">Training Logs</h3>
        <span className="text-xs text-gray-500 font-mono">{logs.length} entries</span>
      </div>

      {/* Log content - Simple list without job headers */}
      <div 
        ref={logContainerRef}
        className="flex-1 overflow-y-auto font-mono text-xs space-y-1 mb-3"
      >
        {logs.map((entry, index) => (
          <div 
            key={`${entry.jobId}-${index}`}
            className="px-2 py-1 hover:bg-gray-900/50"
          >
            <span className="text-gray-500">[{entry.timestamp}]</span>{' '}
            <span className="text-green-400 whitespace-pre-wrap">{entry.message}</span>
          </div>
        ))}
      </div>

      {/* Live Progress Zone - at bottom, updates in place like a real CLI */}
      {liveProgress && (
        <div className="mt-auto p-3 bg-black/50 rounded border border-green-500/30 sticky bottom-0">
          <pre className="text-green-400 font-mono text-xs whitespace-pre leading-relaxed">
            {liveProgress}
          </pre>
        </div>
      )}
    </div>
  );
};

export default AnimatedProgress;
