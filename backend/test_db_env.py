#!/usr/bin/env python3
"""
Database connection test for CheckGuard
Run this to test database connectivity and environment setup
"""

import sys
import os
import logging

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment():
    """Test environment variables"""
    logger.info("=== Environment Variables Test ===")
    
    required_vars = [
        'DATABASE_URL',
        'AWS_ACCESS_KEY_ID', 
        'AWS_SECRET_ACCESS_KEY',
        'S3_BUCKET_NAME',
        'CLERK_SECRET_KEY',
        'GEMINI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var, '')
        if not value:
            missing_vars.append(var)
            logger.error(f"❌ {var}: NOT SET")
        else:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var or 'TOKEN' in var:
                display_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            else:
                display_value = value
            logger.info(f"✅ {var}: {display_value}")
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("All required environment variables are set")
    return True

def test_database_connection():
    """Test database connection"""
    logger.info("=== Database Connection Test ===")
    
    try:
        from app.core.config import settings
        database_url = settings.DATABASE_URL
        
        # Parse database URL for logging
        if '@' in database_url:
            parts = database_url.split('@')
            if len(parts) >= 2:
                host_part = parts[1].split('/')[0]
                logger.info(f"Database host: {host_part}")
        
        # Test sync connection
        from sqlalchemy import create_engine, text
        
        # Convert async URL to sync for connection test
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        logger.info("Creating database engine...")
        engine = create_engine(sync_url, echo=False)
        
        logger.info("Testing connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ Database connection successful!")
            logger.info(f"PostgreSQL version: {version}")
        
        engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def test_imports():
    """Test critical imports"""
    logger.info("=== Import Test ===")
    
    critical_imports = [
        ('app.core.config', 'settings'),
        ('alembic.config', 'Config'),
        ('alembic', 'command'),
        ('sqlalchemy', 'create_engine'),
        ('app.database', 'Base'),
    ]
    
    success = True
    for module_name, attr_name in critical_imports:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            getattr(module, attr_name)
            logger.info(f"✅ {module_name}.{attr_name}")
        except Exception as e:
            logger.error(f"❌ {module_name}.{attr_name}: {e}")
            success = False
    
    return success

def main():
    """Main test function"""
    logger.info("=== CheckGuard Database Environment Test ===")
    
    # Test environment
    env_ok = test_environment()
    
    # Test imports
    import_ok = test_imports()
    
    # Test database connection
    db_ok = test_database_connection()
    
    # Summary
    logger.info("=== Test Summary ===")
    logger.info(f"Environment: {'✅ PASS' if env_ok else '❌ FAIL'}")
    logger.info(f"Imports: {'✅ PASS' if import_ok else '❌ FAIL'}")
    logger.info(f"Database: {'✅ PASS' if db_ok else '❌ FAIL'}")
    
    if env_ok and import_ok and db_ok:
        logger.info("🎉 All tests passed! Ready for migration.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
