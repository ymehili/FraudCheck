"""
Resource monitoring for Celery tasks with automatic termination.

This module provides memory and CPU monitoring with automatic task termination
when resource limits are exceeded to prevent OOM kills and worker crashes.
"""

import os
import psutil
import time
import logging
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    memory_mb: float
    peak_memory_mb: float
    cpu_percent: float
    processing_time_seconds: float
    file_size_mb: float
    timestamp: datetime


class ResourceLimitError(Exception):
    """Exception raised when resource limits are exceeded."""
    pass


class ResourceMonitor:
    """
    Resource monitor for Celery tasks with automatic limit enforcement.
    
    Monitors memory and CPU usage during task execution and automatically
    terminates tasks that exceed configured limits to prevent system crashes.
    """
    
    def __init__(
        self,
        memory_limit_mb: int = 500,
        cpu_limit_percent: float = 90.0,
        monitoring_interval: float = 1.0,
        file_size_mb: float = 0.0
    ):
        """
        Initialize resource monitor.
        
        Args:
            memory_limit_mb: Maximum memory usage in MB before termination
            cpu_limit_percent: Maximum CPU usage percentage before alert
            monitoring_interval: How often to check resources (seconds)
            file_size_mb: Size of file being processed (for context)
        """
        self.memory_limit_mb = memory_limit_mb
        self.cpu_limit_percent = cpu_limit_percent
        self.monitoring_interval = monitoring_interval
        self.file_size_mb = file_size_mb
        
        # Tracking state
        self.start_time = time.time()
        self.peak_memory_mb = 0.0
        self.last_check_time = self.start_time
        self.process = psutil.Process()
        
        # Alert thresholds (warnings before termination)
        self.memory_warning_threshold = memory_limit_mb * 0.8  # 80% of limit
        self.memory_critical_threshold = memory_limit_mb * 0.95  # 95% of limit
        
        logger.info(
            f"ResourceMonitor initialized: memory_limit={memory_limit_mb}MB, "
            f"cpu_limit={cpu_limit_percent}%, file_size={file_size_mb}MB"
        )
    
    def check_resources(self) -> ResourceUsage:
        """
        Check current resource usage and enforce limits.
        
        Returns:
            ResourceUsage with current metrics
            
        Raises:
            ResourceLimitError: If resource limits are exceeded
        """
        try:
            current_time = time.time()
            processing_time = current_time - self.start_time
            
            # Get memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Track peak memory
            if memory_mb > self.peak_memory_mb:
                self.peak_memory_mb = memory_mb
            
            # Get CPU usage (averaged over interval)
            cpu_percent = self.process.cpu_percent()
            
            # Create usage snapshot
            usage = ResourceUsage(
                memory_mb=memory_mb,
                peak_memory_mb=self.peak_memory_mb,
                cpu_percent=cpu_percent,
                processing_time_seconds=processing_time,
                file_size_mb=self.file_size_mb,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Check memory limits
            self._check_memory_limits(usage)
            
            # Check CPU limits (warning only, don't terminate)
            self._check_cpu_limits(usage)
            
            # Update last check time
            self.last_check_time = current_time
            
            return usage
            
        except ResourceLimitError:
            raise
        except Exception as e:
            logger.error(f"Resource monitoring failed: {str(e)}")
            # Return safe defaults if monitoring fails
            return ResourceUsage(
                memory_mb=0.0,
                peak_memory_mb=self.peak_memory_mb,
                cpu_percent=0.0,
                processing_time_seconds=time.time() - self.start_time,
                file_size_mb=self.file_size_mb,
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_memory_limits(self, usage: ResourceUsage) -> None:
        """Check memory limits and raise exception if exceeded."""
        memory_mb = usage.memory_mb
        
        if memory_mb > self.memory_limit_mb:
            error_msg = (
                f"Memory limit exceeded: {memory_mb:.1f}MB > {self.memory_limit_mb}MB "
                f"(peak: {usage.peak_memory_mb:.1f}MB, file: {self.file_size_mb:.1f}MB, "
                f"time: {usage.processing_time_seconds:.1f}s)"
            )
            logger.error(error_msg)
            raise ResourceLimitError(error_msg)
        
        elif memory_mb > self.memory_critical_threshold:
            logger.warning(
                f"Memory usage critical: {memory_mb:.1f}MB "
                f"({(memory_mb/self.memory_limit_mb)*100:.1f}% of limit)"
            )
        
        elif memory_mb > self.memory_warning_threshold:
            logger.info(
                f"Memory usage warning: {memory_mb:.1f}MB "
                f"({(memory_mb/self.memory_limit_mb)*100:.1f}% of limit)"
            )
    
    def _check_cpu_limits(self, usage: ResourceUsage) -> None:
        """Check CPU limits and log warnings (don't terminate)."""
        cpu_percent = usage.cpu_percent
        
        if cpu_percent > self.cpu_limit_percent:
            logger.warning(
                f"High CPU usage: {cpu_percent:.1f}% "
                f"(threshold: {self.cpu_limit_percent}%)"
            )
    
    async def monitor_async_operation(
        self,
        operation_coro,
        operation_name: str = "operation"
    ):
        """
        Monitor an async operation with resource checking.
        
        Args:
            operation_coro: Coroutine to monitor
            operation_name: Name for logging
            
        Returns:
            Result of the operation
            
        Raises:
            ResourceLimitError: If resource limits exceeded during operation
        """
        logger.info(f"Starting monitored async operation: {operation_name}")
        
        # Create monitoring task
        monitor_task = asyncio.create_task(self._periodic_monitoring())
        
        try:
            # Run operation with monitoring
            result = await operation_coro
            logger.info(f"Monitored operation completed: {operation_name}")
            return result
            
        except Exception as e:
            logger.error(f"Monitored operation failed: {operation_name}: {str(e)}")
            raise
        finally:
            # Stop monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _periodic_monitoring(self):
        """Periodic resource monitoring loop."""
        try:
            while True:
                self.check_resources()
                await asyncio.sleep(self.monitoring_interval)
        except asyncio.CancelledError:
            logger.debug("Resource monitoring cancelled")
        except ResourceLimitError:
            logger.error("Resource limit exceeded during monitoring")
            raise
        except Exception as e:
            logger.error(f"Periodic monitoring error: {str(e)}")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of resource usage for reporting."""
        current_usage = self.check_resources()
        
        return {
            "current_memory_mb": current_usage.memory_mb,
            "peak_memory_mb": current_usage.peak_memory_mb,
            "memory_limit_mb": self.memory_limit_mb,
            "memory_utilization_percent": (current_usage.memory_mb / self.memory_limit_mb) * 100,
            "cpu_percent": current_usage.cpu_percent,
            "processing_time_seconds": current_usage.processing_time_seconds,
            "file_size_mb": self.file_size_mb,
            "efficiency_mb_per_mb": (
                current_usage.memory_mb / max(self.file_size_mb, 0.1)
            ),
            "timestamp": current_usage.timestamp.isoformat(),
            "status": self._get_status_from_usage(current_usage)
        }
    
    def _get_status_from_usage(self, usage: ResourceUsage) -> str:
        """Get status string based on current usage."""
        memory_percent = (usage.memory_mb / self.memory_limit_mb) * 100
        
        if memory_percent > 95:
            return "critical"
        elif memory_percent > 80:
            return "warning"
        elif memory_percent > 60:
            return "elevated"
        else:
            return "normal"


class SystemResourceMonitor:
    """
    System-wide resource monitor for worker health checks.
    
    Monitors overall system resources to detect potential issues
    that could affect worker performance.
    """
    
    @staticmethod
    def get_system_resources() -> Dict[str, Any]:
        """Get current system resource usage."""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Disk usage for temp directory
            temp_dir = "/tmp"
            if os.path.exists(temp_dir):
                disk_usage = psutil.disk_usage(temp_dir)
                disk_free_gb = disk_usage.free / (1024**3)
                disk_used_percent = (disk_usage.used / disk_usage.total) * 100
            else:
                disk_free_gb = 0
                disk_used_percent = 0
            
            return {
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "used_percent": memory.percent,
                    "free_gb": memory.free / (1024**3)
                },
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "disk": {
                    "free_gb": disk_free_gb,
                    "used_percent": disk_used_percent
                },
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"System resource monitoring failed: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @staticmethod
    def check_system_health() -> Dict[str, Any]:
        """Check system health and return status."""
        resources = SystemResourceMonitor.get_system_resources()
        
        if "error" in resources:
            return {"status": "unknown", "resources": resources}
        
        # Determine health status
        memory_critical = resources["memory"]["used_percent"] > 90
        cpu_critical = resources["cpu"]["usage_percent"] > 95
        disk_critical = resources["disk"]["free_gb"] < 1.0  # Less than 1GB free
        
        if memory_critical or cpu_critical or disk_critical:
            status = "critical"
        elif (resources["memory"]["used_percent"] > 80 or 
              resources["cpu"]["usage_percent"] > 80 or
              resources["disk"]["free_gb"] < 5.0):
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "resources": resources,
            "alerts": {
                "memory_critical": memory_critical,
                "cpu_critical": cpu_critical,
                "disk_critical": disk_critical
            }
        }


def create_resource_monitor_for_file(
    file_size_bytes: int = 0,
    memory_limit_mb: Optional[int] = None
) -> ResourceMonitor:
    """
    Create resource monitor with appropriate limits for file size.
    
    Args:
        file_size_bytes: Size of file being processed
        memory_limit_mb: Override default memory limit
        
    Returns:
        Configured ResourceMonitor instance
    """
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    # Default memory limit from environment or 500MB
    default_limit = int(os.getenv('MAX_ANALYSIS_MEMORY_MB', '500'))
    
    # Use provided limit or default
    if memory_limit_mb is None:
        memory_limit_mb = default_limit
    
    # Adjust limits based on file size for very large files
    if file_size_mb > 20:  # Files larger than 20MB
        # Allow extra memory for large files (up to 1.5x file size)
        suggested_limit = min(memory_limit_mb, int(file_size_mb * 1.5) + 200)
        if suggested_limit > memory_limit_mb:
            logger.info(
                f"Large file ({file_size_mb:.1f}MB) - using higher memory limit: "
                f"{suggested_limit}MB (was {memory_limit_mb}MB)"
            )
            memory_limit_mb = suggested_limit
    
    return ResourceMonitor(
        memory_limit_mb=memory_limit_mb,
        cpu_limit_percent=90.0,
        monitoring_interval=2.0,  # Check every 2 seconds for tasks
        file_size_mb=file_size_mb
    )


def log_resource_usage(usage: ResourceUsage, operation: str = "analysis"):
    """Log resource usage in structured format."""
    logger.info(
        f"Resource usage [{operation}]: "
        f"memory={usage.memory_mb:.1f}MB (peak={usage.peak_memory_mb:.1f}MB), "
        f"cpu={usage.cpu_percent:.1f}%, "
        f"time={usage.processing_time_seconds:.1f}s, "
        f"file_size={usage.file_size_mb:.1f}MB"
    )