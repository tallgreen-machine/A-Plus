import React, { useEffect, useState } from 'react';

interface TrainingJob {
  id: string;
  config_id: string | null;
  rq_job_id: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  strategy_name: string;
  exchange: string;
  pair: string;
  timeframe: string;
  regime: string;
  current_episode: number | null;
  total_episodes: number | null;
  current_reward: number | null;
  current_loss: number | null;
  current_stage: string | null;
  submitted_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

const TrainingQueue: React.FC = () => {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchQueue = async () => {
      try {
        const response = await fetch('/api/training/queue');
        const data = await response.json();
        setJobs(data);
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to fetch training queue:', error);
        setIsLoading(false);
      }
    };

    // Fetch immediately
    fetchQueue();

    // Poll every 3 seconds
    const interval = setInterval(fetchQueue, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleCancel = async (jobId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent job selection
    
    if (!confirm('Are you sure you want to cancel this training job?')) {
      return;
    }

    try {
      const response = await fetch(`/api/training/${jobId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Remove from local state immediately
        setJobs(jobs.filter(j => j.id !== jobId));
      } else {
        const error = await response.json();
        alert(`Failed to cancel job: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to cancel job:', error);
      alert('Failed to cancel job. Please try again.');
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'bg-gray-500';
      case 'running':
        return 'bg-blue-500';
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'cancelled':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const formatTime = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  if (isLoading) {
    return (
      <div className="bg-gray-950 rounded-lg p-4 h-full overflow-y-auto">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">Training Queue</h3>
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-gray-900 rounded p-3 animate-pulse">
              <div className="h-4 bg-gray-800 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-800 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-950 rounded-lg p-4 h-full overflow-y-auto">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">
        Training Queue ({jobs.length})
      </h3>

      {jobs.length === 0 ? (
        <div className="text-center py-12">
          <svg
            className="w-12 h-12 text-gray-600 mx-auto mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <p className="text-sm text-gray-500">No training jobs in queue</p>
          <p className="text-xs text-gray-600 mt-1">Start a training to see it here</p>
        </div>
      ) : (
        <div className="space-y-2">
          {jobs.map(job => (
            <div
              key={job.id}
              className="bg-gray-900 rounded p-3 transition-all hover:bg-gray-800"
            >
              {/* Status Badge */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(job.status)}`} />
                  <span className="text-xs font-medium text-gray-400 uppercase">
                    {job.status}
                  </span>
                </div>
                <button
                  onClick={(e) => handleCancel(job.id, e)}
                  className="text-xs text-gray-500 hover:text-red-400 transition-colors"
                  title={job.status === 'pending' ? 'Remove from queue' : 'Cancel training'}
                >
                  {job.status === 'pending' ? 'Remove' : 'Cancel'}
                </button>
              </div>

              {/* Job Info */}
              <div className="text-sm text-gray-200 font-medium mb-1">
                {job.strategy_name.replace('_', ' ')}
              </div>
              <div className="text-xs text-gray-400 space-y-0.5">
                <div>{job.exchange} • {job.pair} • {job.timeframe}</div>
                <div className="flex items-center gap-2">
                  <span className="capitalize">{job.regime}</span>
                  <span>•</span>
                  <span>Submitted {formatTime(job.submitted_at)}</span>
                  {job.status === 'running' && (
                    <>
                      <span>•</span>
                      <span className="text-blue-400">Training...</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TrainingQueue;
