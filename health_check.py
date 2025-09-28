#!/usr/bin/env python3
"""
Health Check Script for FlushBot Azure Deployment
"""
import sys
import os
import asyncio
import redis
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def check_database():
    """Check database connectivity"""
    try:
        from core.database import db_manager
        # Simple connection test
        with db_manager.get_session() as session:
            session.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database check failed: {e}")
        return False

def check_redis():
    """Check Redis connectivity"""
    try:
        from config.settings import settings
        r = redis.Redis.from_url(settings.redis_url, password=settings.redis_password)
        r.ping()
        return True
    except Exception as e:
        print(f"Redis check failed: {e}")
        return False

def check_bot_token():
    """Check if bot token is configured"""
    try:
        from config.settings import settings
        return bool(settings.telegram_bot_token and len(settings.telegram_bot_token) > 10)
    except Exception as e:
        print(f"Bot token check failed: {e}")
        return False

async def check_telegram_api():
    """Check Telegram API connectivity"""
    try:
        from telegram import Bot
        from config.settings import settings
        
        bot = Bot(token=settings.telegram_bot_token)
        me = await bot.get_me()
        return bool(me.username)
    except Exception as e:
        print(f"Telegram API check failed: {e}")
        return False

async def main():
    """Run all health checks"""
    print("🔍 FlushBot Health Check Starting...")
    
    checks = {
        "Database": check_database(),
        "Redis": check_redis(), 
        "Bot Token": check_bot_token(),
        "Telegram API": await check_telegram_api()
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("🎉 All health checks passed!")
        sys.exit(0)
    else:
        print("💥 Some health checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())