import React, { useEffect, useState, useRef } from 'react';

interface ProgressData {
  progress: number;
  current_episode: number | null;
  total_episodes: number | null;
  current_reward: number | null;
  current_loss: number | null;
  stage: string | null;
  status: string;
}

interface LogEntry {
  timestamp: string;
  message: string;
  progress: number;
  jobId: string;
}

interface AnimatedProgressProps {
  jobId: string | null;
}

const AnimatedProgress: React.FC<AnimatedProgressProps> = ({ jobId }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  useEffect(() => {
    if (!jobId) {
      setIsConnected(false);
      return;
    }

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Fetch historical logs before connecting to SSE stream
    const loadHistoricalLogs = async () => {
      try {
        const response = await fetch(`/api/training/${jobId}/logs?limit=1000`);
        if (response.ok) {
          const historicalLogs = await response.json();
          
          // Transform API logs to LogEntry format
          const formattedLogs: LogEntry[] = historicalLogs.map((log: any) => ({
            timestamp: new Date(log.timestamp).toLocaleTimeString('en-US', { 
              hour12: false, 
              hour: '2-digit', 
              minute: '2-digit', 
              second: '2-digit' 
            }),
            message: log.message,
            progress: log.progress || 0,
            jobId: log.job_id
          }));
          
          setLogs(formattedLogs);
        }
      } catch (err) {
        console.error('Failed to load historical logs:', err);
        // Don't block SSE connection if historical logs fail
      }
    };

    // Load historical logs first, then connect to SSE
    loadHistoricalLogs().then(() => {
      // Create new SSE connection
      const eventSource = new EventSource(`/api/training/${jobId}/stream`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        
        // Add connection log
        const timestamp = new Date().toLocaleTimeString('en-US', { 
          hour12: false, 
          hour: '2-digit', 
          minute: '2-digit', 
          second: '2-digit' 
        });
        setLogs(prev => [...prev, {
          timestamp,
          message: `Connected to training job ${jobId}`,
          progress: 0,
          jobId
        }]);
      };

      eventSource.addEventListener('progress', (event) => {
        try {
          const data: ProgressData = JSON.parse(event.data);
          const timestamp = new Date().toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
          });
          
          // Build classic CLI-style progress message
          let message = `Training...`;
          
          if (data.current_episode && data.total_episodes) {
            message += ` Episode ${data.current_episode}/${data.total_episodes}`;
          }
          
          if (data.current_reward !== null) {
            message += ` | Reward: ${data.current_reward.toFixed(4)}`;
          }
          
          if (data.current_loss !== null) {
            message += ` | Loss: ${data.current_loss.toFixed(4)}`;
          }
          
          if (data.stage) {
            message += ` | Stage: ${data.stage}`;
          }
          
          // Progress bar
          const progressPct = data.progress.toFixed(1);
          const barWidth = 50;
          const filledWidth = Math.floor((data.progress / 100) * barWidth);
          const progressBar = '█'.repeat(filledWidth) + '░'.repeat(barWidth - filledWidth);
          const progressLine = `[${progressPct}%] ${progressBar}`;
          
          // Update in place - find and replace the last "Training..." log entry
          setLogs(prev => {
            // Find the last log that starts with Training...
            const lastTrainingIndex = [...prev].reverse().findIndex(log => 
              log.message.startsWith('Training...')
            );
            
            if (lastTrainingIndex === -1) {
              // No training log yet, add new one
              return [...prev, {
                timestamp,
                message: `${message}\n${progressLine}`,
                progress: data.progress,
                jobId
              }];
            }
            
            // Update the last training log in place
            const actualIndex = prev.length - 1 - lastTrainingIndex;
            const newLogs = [...prev];
            newLogs[actualIndex] = {
              timestamp,
              message: `${message}\n${progressLine}`,
              progress: data.progress,
              jobId
            };
            return newLogs;
          });
          
        } catch (e) {
          console.error('Failed to parse progress data:', e);
        }
      });

      eventSource.addEventListener('complete', (event) => {
        try {
          const data = JSON.parse(event.data);
          const timestamp = new Date().toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
          });
          
          setLogs(prev => [...prev, {
            timestamp,
            message: `✓ Training completed: ${data.status}`,
            progress: 100,
            jobId
          }]);
          
          eventSource.close();
        } catch (e) {
          console.error('Failed to parse completion data:', e);
        }
      });

      eventSource.addEventListener('error', (event: any) => {
        try {
          const data = JSON.parse(event.data);
          setError(data.error);
          
          const timestamp = new Date().toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
          });
          
          setLogs(prev => [...prev, {
            timestamp,
            message: `✗ Error: ${data.error}`,
            progress: 0,
            jobId
          }]);
        } catch (e) {
          console.error('SSE error:', e);
        }
      });

      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource.close();
      };
    });

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [jobId]);

  if (!jobId) {
    return (
      <div className="bg-gray-950 rounded-lg p-4 h-full flex items-center justify-center">
        <p className="text-sm text-gray-500 font-mono">Waiting for training job...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-950 rounded-lg p-4 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 font-mono">Training Log</h3>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-600'}`} />
          <span className="text-xs text-gray-500 font-mono">
            {isConnected ? 'LIVE' : 'DISCONNECTED'}
          </span>
        </div>
      </div>

      {/* Log Terminal */}
      <div 
        ref={logContainerRef}
        className="flex-1 overflow-y-auto bg-black rounded p-3 font-mono text-sm space-y-1"
        style={{ 
          fontFamily: 'Consolas, Monaco, "Courier New", monospace',
          lineHeight: '1.4'
        }}
      >
        {logs.length === 0 ? (
          <div className="text-gray-600">No logs yet...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="text-green-400">
              <span className="text-gray-600">[{log.timestamp}]</span>{' '}
              <span className="whitespace-pre-wrap">{log.message}</span>
            </div>
          ))
        )}
      </div>

      {error && (
        <div className="mt-2 p-2 bg-red-900/20 border border-red-500/30 rounded text-xs text-red-400 font-mono">
          Error: {error}
        </div>
      )}
    </div>
  );
};

export default AnimatedProgress;
