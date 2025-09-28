"""
Database Setup Script for FlushBot
Initializes database tables and creates default data
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from core.database import db_manager, Base
from sqlalchemy import text
from loguru import logger


async def setup_database():
    """Setup database with all required tables and initial data"""
    
    logger.info("Starting database setup...")
    
    try:
        # Create all tables
        db_manager.create_tables()
        logger.info("✅ Database tables created successfully")
        
        # Test database connection
        with db_manager.get_session() as session:
            # Try a simple query
            result = session.execute(text("SELECT 1")).fetchone()
            if result:
                logger.info("✅ Database connection test passed")
            else:
                raise Exception("Database connection test failed")
        
        # Create initial admin chat if sudo user is configured
        if settings.sudo_user_id:
            logger.info(f"Creating initial data for sudo user: {settings.sudo_user_id}")
            
            # This would typically be done when the bot first starts
            # but we can prepare the database structure
            pass
        
        logger.info("✅ Database setup completed successfully")
        
        # Print configuration summary
        print("\n" + "="*50)
        print("DATABASE SETUP COMPLETE")
        print("="*50)
        print(f"Database URL: {settings.database_url}")
        print(f"Tables created: ✅")
        print(f"Connection test: ✅")
        
        if settings.sudo_user_id:
            print(f"Sudo User ID: {settings.sudo_user_id}")
        
        print("\nNext steps:")
        print("1. Set up your .env file with proper credentials")
        print("2. Start Redis server if using Redis caching")
        print("3. Run 'python main.py' to start the bot")
        print("="*50)
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        print("\n" + "="*50)
        print("DATABASE SETUP FAILED")
        print("="*50)
        print(f"Error: {e}")
        print("\nPlease check:")
        print("1. Database connection string in .env file")
        print("2. Database server is running")
        print("3. Required permissions for database operations")
        print("="*50)
        sys.exit(1)


def check_environment():
    """Check if environment is properly configured"""
    
    logger.info("Checking environment configuration...")
    
    issues = []
    
    # Check required environment variables
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "SUDO_USER_ID", 
        "OPENROUTER_GROK_KEY",
        "OPENROUTER_GEMINI_KEY"
    ]
    
    for var in required_vars:
        value = getattr(settings, var.lower(), None)
        if not value:
            issues.append(f"Missing required environment variable: {var}")
    
    # Check database URL
    if not settings.database_url:
        issues.append("Missing DATABASE_URL configuration")
    
    # Check Redis URL (optional but recommended)
    if not settings.redis_url:
        logger.warning("Redis URL not configured - caching will be disabled")
    
    if issues:
        print("\n" + "="*50)
        print("ENVIRONMENT CONFIGURATION ISSUES")
        print("="*50)
        for issue in issues:
            print(f"❌ {issue}")
        print("\nPlease create a .env file based on .env.example and configure all required variables.")
        print("="*50)
        return False
    
    logger.info("✅ Environment configuration looks good")
    return True


async def test_apis():
    """Test API connections"""
    
    logger.info("Testing API connections...")
    
    try:
        from core.ai_analyzer import ai_analyzer
        
        # Test with a simple message
        test_result = await ai_analyzer.analyze_content("Hello world", {"test": True})
        
        if test_result:
            logger.info("✅ AI API connection test passed")
        else:
            logger.warning("⚠️ AI API test returned empty result")
            
    except Exception as e:
        logger.error(f"❌ AI API test failed: {e}")
        print(f"\nAPI Test Failed: {e}")
        print("This might be due to:")
        print("1. Invalid API keys")
        print("2. Network connectivity issues") 
        print("3. API service unavailability")
        print("\nThe bot will still work with rule-based analysis only.")


async def test_redis():
    """Test Redis connection"""
    
    logger.info("Testing Redis connection...")
    
    try:
        from core.cache import cache_manager
        
        await cache_manager.connect()
        
        # Test basic operations
        await cache_manager.set("test_key", "test_value", ttl=60)
        value = await cache_manager.get("test_key")
        
        if value == "test_value":
            logger.info("✅ Redis connection test passed")
            await cache_manager.delete("test_key")
        else:
            raise Exception("Redis test value mismatch")
            
        await cache_manager.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Redis test failed: {e}")
        print(f"\nRedis Test Failed: {e}")
        print("This will disable caching but the bot will still work.")
        print("To enable caching:")
        print("1. Install and start Redis server")
        print("2. Configure REDIS_URL in .env file")


if __name__ == "__main__":
    print("FlushBot Database Setup")
    print("=" * 50)
    
    # Check environment first
    if not check_environment():
        sys.exit(1)
    
    # Setup database
    asyncio.run(setup_database())
    
    # Test APIs (optional)
    print("\nTesting external services...")
    asyncio.run(test_apis())
    asyncio.run(test_redis())
    
    print("\n🎉 Setup complete! You can now start the bot with 'python main.py'")