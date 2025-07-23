"""
ProcessPoolExecutor lifecycle management for forensics analysis.

This module provides a singleton executor manager that handles the lifecycle
of ProcessPoolExecutor instances used for CPU-intensive forensics operations.
"""

import multiprocessing
import platform
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutorManager:
    """
    Singleton ProcessPoolExecutor manager with lifecycle management.
    
    Provides a shared ProcessPoolExecutor instance for the application
    with proper resource management and platform compatibility.
    """
    
    _instance: Optional['ExecutorManager'] = None
    _executor: Optional[ProcessPoolExecutor] = None
    _lock = multiprocessing.Lock()
    
    def __new__(cls) -> 'ExecutorManager':
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the executor manager."""
        if self._executor is None:
            self._initialize_executor()
    
    def _initialize_executor(self):
        """Initialize the ProcessPoolExecutor with platform-specific settings."""
        try:
            # CRITICAL: macOS compatibility - set start method
            if platform.system() == 'Darwin':
                try:
                    multiprocessing.set_start_method('spawn', force=True)
                    logger.info("Set multiprocessing start method to 'spawn' for macOS compatibility")
                except RuntimeError:
                    # Start method already set, which is fine
                    logger.debug("Multiprocessing start method already set")
                    pass
            
            # OPTIMIZE: CPU count based on system and workload
            # Limit to 4 workers to prevent excessive memory usage with large images
            cpu_count = multiprocessing.cpu_count()
            max_workers = min(4, cpu_count)
            
            logger.info(f"Initializing ProcessPoolExecutor with {max_workers} workers (CPU count: {cpu_count})")
            
            self._executor = ProcessPoolExecutor(
                max_workers=max_workers,
                mp_context=multiprocessing.get_context()
            )
            
            logger.info("ProcessPoolExecutor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ProcessPoolExecutor: {str(e)}")
            raise
    
    @classmethod
    def get_executor(cls) -> ProcessPoolExecutor:
        """
        Get the shared ProcessPoolExecutor instance.
        
        Returns:
            ProcessPoolExecutor instance for CPU-bound operations
            
        Raises:
            RuntimeError: If executor initialization failed
        """
        if cls._instance is None:
            cls._instance = cls()
        
        if cls._instance._executor is None:
            raise RuntimeError("ProcessPoolExecutor not initialized")
        
        return cls._instance._executor
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the executor is initialized."""
        try:
            return (cls._instance is not None and 
                    cls._instance._executor is not None)
        except Exception:
            return False
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the ProcessPoolExecutor gracefully.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        if self._executor is not None:
            try:
                logger.info("Shutting down ProcessPoolExecutor...")
                self._executor.shutdown(wait=wait)
                logger.info("ProcessPoolExecutor shutdown completed")
            except Exception as e:
                logger.error(f"Error during ProcessPoolExecutor shutdown: {str(e)}")
            finally:
                self._executor = None
    
    @classmethod
    def shutdown_global(cls, wait: bool = True):
        """
        Shutdown the global executor instance.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        if cls._instance is not None:
            cls._instance.shutdown(wait=wait)
            cls._instance = None
    
    def __del__(self):
        """Ensure cleanup on garbage collection."""
        try:
            self.shutdown(wait=False)
        except Exception:
            # Ignore exceptions during cleanup
            pass


def get_forensics_executor() -> ProcessPoolExecutor:
    """
    Convenience function to get the forensics ProcessPoolExecutor.
    
    Returns:
        ProcessPoolExecutor instance for forensics operations
    """
    return ExecutorManager.get_executor()


def shutdown_forensics_executor(wait: bool = True):
    """
    Convenience function to shutdown the forensics ProcessPoolExecutor.
    
    Args:
        wait: Whether to wait for pending tasks to complete
    """
    ExecutorManager.shutdown_global(wait=wait)


def is_executor_available() -> bool:
    """
    Check if the forensics executor is available and ready.
    
    Returns:
        True if executor is initialized and ready, False otherwise
    """
    return ExecutorManager.is_initialized()