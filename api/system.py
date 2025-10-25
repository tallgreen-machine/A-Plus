"""
System Resources API
Provides real-time system resource monitoring (CPU, RAM, Disk)
"""
from fastapi import APIRouter
import psutil
from typing import Dict

router = APIRouter()

@router.get("/resources")
async def get_system_resources() -> Dict[str, float]:
    """
    Get current system resource usage
    
    Returns:
        - cpu_percent: CPU usage percentage (0-100)
        - ram_percent: RAM usage percentage (0-100)
        - ram_used_gb: RAM used in GB
        - ram_total_gb: Total RAM in GB
        - disk_percent: Disk usage percentage (0-100)
        - disk_used_gb: Disk used in GB
        - disk_total_gb: Total disk in GB
    """
    try:
        # CPU usage (interval=1 gives more accurate reading than 0.1)
        # Using 1 second provides better accuracy while still being responsive
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        ram_percent = memory.percent
        ram_used_gb = memory.used / (1024**3)
        ram_total_gb = memory.total / (1024**3)
        
        # Disk usage (root partition)
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        
        return {
            "cpu_percent": round(cpu_percent, 1),
            "ram_percent": round(ram_percent, 1),
            "ram_used_gb": round(ram_used_gb, 2),
            "ram_total_gb": round(ram_total_gb, 2),
            "disk_percent": round(disk_percent, 1),
            "disk_used_gb": round(disk_used_gb, 2),
            "disk_total_gb": round(disk_total_gb, 2),
        }
    except Exception as e:
        # Return safe defaults if monitoring fails
        return {
            "cpu_percent": 0,
            "ram_percent": 0,
            "ram_used_gb": 0,
            "ram_total_gb": 0,
            "disk_percent": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
            "error": str(e)
        }
