"""
CPU Configuration for Training Jobs

Provides dynamic CPU core detection and safe allocation limits.
Ensures system remains responsive by reserving cores for other operations.
"""

import os
import logging
import multiprocessing

log = logging.getLogger(__name__)


def get_available_cores() -> int:
    """
    Get the number of CPU cores available on the system.
    
    Returns:
        int: Number of CPU cores detected
    """
    try:
        return multiprocessing.cpu_count()
    except Exception as e:
        log.warning(f"Could not detect CPU cores: {e}, defaulting to 1")
        return 1


def get_training_workers(reserve_cores: int = 1) -> int:
    """
    Calculate optimal number of worker processes for training.
    
    Reserves cores for system operations (UI, database, OS tasks) to prevent
    the system from becoming unresponsive during training.
    
    Args:
        reserve_cores: Number of cores to reserve for system (default: 1)
        
    Returns:
        int: Number of workers to use for parallel processing (minimum 1)
        
    Examples:
        2 cores total  -> 1 training worker  (reserve 1 for system)
        4 cores total  -> 3 training workers (reserve 1 for system)
        8 cores total  -> 7 training workers (reserve 1 for system)
        16 cores total -> 14 training workers (reserve 2 for system)
    """
    total_cores = get_available_cores()
    
    # For systems with many cores, reserve more for system operations
    if total_cores >= 16:
        reserve_cores = 2
    elif total_cores >= 8:
        reserve_cores = 1
    else:
        reserve_cores = 1
    
    # Always use at least 1 worker
    training_workers = max(1, total_cores - reserve_cores)
    
    log.info(f"CPU Config: {total_cores} cores detected, using {training_workers} for training, reserving {reserve_cores} for system")
    
    return training_workers


def get_cpu_usage_limit() -> float:
    """
    Get the CPU usage limit as a percentage (0.0 to 1.0).
    
    This is used for CPU-bound operations to prevent maxing out the system.
    
    Returns:
        float: CPU usage limit (e.g., 0.85 = 85% max CPU usage)
    """
    total_cores = get_available_cores()
    
    # Leave more headroom on smaller systems
    if total_cores <= 2:
        return 0.75  # Use 75% max on 2-core systems
    elif total_cores <= 4:
        return 0.85  # Use 85% max on 4-core systems
    else:
        return 0.90  # Use 90% max on 8+ core systems


def get_training_config() -> dict:
    """
    Get complete training configuration with CPU settings.
    
    Returns:
        dict: Configuration dictionary with:
            - total_cores: Total CPU cores available
            - training_workers: Workers to use for parallel processing
            - reserved_cores: Cores reserved for system
            - cpu_limit: Maximum CPU usage percentage
    """
    total_cores = get_available_cores()
    training_workers = get_training_workers()
    reserved_cores = total_cores - training_workers
    cpu_limit = get_cpu_usage_limit()
    
    config = {
        'total_cores': total_cores,
        'training_workers': training_workers,
        'reserved_cores': reserved_cores,
        'cpu_limit': cpu_limit
    }
    
    log.info(f"Training Config: {config}")
    return config


# Module-level cache to avoid repeated detection
_cpu_config_cache = None

def get_cached_training_workers() -> int:
    """
    Get training workers with caching to avoid repeated CPU detection.
    
    Returns:
        int: Number of training workers
    """
    global _cpu_config_cache
    
    if _cpu_config_cache is None:
        _cpu_config_cache = get_training_workers()
    
    return _cpu_config_cache


if __name__ == '__main__':
    # Test CPU configuration
    logging.basicConfig(level=logging.INFO)
    
    print("=== CPU Configuration Test ===")
    config = get_training_config()
    print(f"\nTotal Cores: {config['total_cores']}")
    print(f"Training Workers: {config['training_workers']}")
    print(f"Reserved for System: {config['reserved_cores']}")
    print(f"CPU Limit: {config['cpu_limit']:.0%}")
    print(f"\nThis will use ~{(config['training_workers'] / config['total_cores']) * 100:.0f}% of available CPU")
