#!/usr/bin/env python3
"""
Robust database migration runner for CheckGuard
This script provides better error handling and logging for Alembic migrations
"""

import sys
import os
import logging
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import time

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def wait_for_database(database_url: str, max_retries: int = 30, retry_interval: int = 2):
    """Wait for database to be available"""
    logger.info("Waiting for database connection...")
    
    # Convert async URL to sync for connection test
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(sync_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection successful!")
            engine.dispose()
            return True
        except OperationalError as e:
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                logger.error("Maximum database connection retries exceeded")
                return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            return False
    
    return False

def run_alembic_migration():
    """Run Alembic migrations with proper error handling"""
    try:
        logger.info("Starting Alembic migration...")
        
        # Import after path setup
        from alembic.config import Config
        from alembic import command
        from app.core.config import settings
        
        # Verify environment variables
        logger.info("Verifying environment configuration...")
        required_vars = ['DATABASE_URL']
        missing_vars = []
        
        for var in required_vars:
            if not hasattr(settings, var) or not getattr(settings, var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        logger.info(f"Database URL configured (host: {settings.DATABASE_URL.split('@')[1].split('/')[0] if '@' in settings.DATABASE_URL else 'unknown'})")
        
        # Wait for database to be available
        if not wait_for_database(settings.DATABASE_URL):
            logger.error("Database is not available")
            return False
        
        # Configure Alembic
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        # Run upgrade
        logger.info("Running Alembic upgrade to head...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Migration completed successfully!")
        return True
        
    except ImportError as e:
        logger.error(f"Import error (check dependencies): {e}")
        return False
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main execution function"""
    logger.info("=== CheckGuard Database Migration Runner ===")
    
    # Log environment info
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Python path: {sys.path[:3]}...")  # Show first 3 entries
    
    success = run_alembic_migration()
    
    if success:
        logger.info("=== Migration completed successfully ===")
        sys.exit(0)
    else:
        logger.error("=== Migration failed ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
