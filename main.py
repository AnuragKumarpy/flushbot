"""
FlushBot - Advanced Telegram Security Bot
Main application entry point
"""

import asyncio
import signal
import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from loguru import logger

from config.settings import settings, get_log_config
from core.database import db_manager
from core.cache import cache_manager, message_cache
from core.ai_analyzer import ai_analyzer
from core.security import initialize_security_enforcer, security_enforcer
from bot.utils.admin_utils import initialize_admin_utils
from bot.handlers.commands import (
    start, help_cmd, status, security, ban_user, unban_user, stats, sudo, export_data
)
from bot.handlers.messages import handle_text_message, handle_media_message


class FlushBot:
    """FlushBot main application class"""
    
    def __init__(self):
        self.application = None
        self.bot = None
        self.running = False
        self.startup_time = None
    
    async def initialize(self):
        """Initialize bot components"""
        
        logger.info("Initializing FlushBot...")
        
        try:
            # Setup logging
            self._setup_logging()
            
            # Initialize database
            logger.info("Connecting to database...")
            db_manager.create_tables()  # Ensure tables exist
            
            # Initialize Redis cache
            logger.info("Connecting to Redis...")
            try:
                await cache_manager.connect()
                if cache_manager.connected:
                    logger.info("✅ Redis connection established")
                else:
                    logger.warning("⚠️ Redis connection failed. Caching will be disabled.")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}. Caching will be disabled.")
            
            # Create Telegram bot application
            logger.info("Creating Telegram bot application...")
            self.application = Application.builder().token(settings.telegram_bot_token).build()
            self.bot = self.application.bot
            
            # Initialize security enforcer with bot instance
            initialize_security_enforcer(self.bot)
            
            # Initialize admin utilities
            initialize_admin_utils(self.bot)
            
            # Initialize delayed sweep system
            from core.delayed_sweep import initialize_delayed_sweep
            initialize_delayed_sweep(self.bot)
            
            # Setup handlers
            self._setup_handlers()
            
            # Test bot connection
            logger.info("Testing bot connection...")
            bot_info = await self.bot.get_me()
            logger.info(f"✅ Connected as @{bot_info.username} ({bot_info.first_name})")
            
            self.startup_time = datetime.now()
            logger.info("✅ FlushBot initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise
    
    def _setup_logging(self):
        """Setup logging configuration"""
        
        # Remove default logger
        logger.remove()
        
        # Add console logger
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
        
        # Add file logger if specified
        if settings.log_file:
            os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
            logger.add(
                settings.log_file,
                level=settings.log_level,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
                rotation=settings.log_max_size,
                retention=settings.log_backup_count,
                compression="zip"
            )
    
    def _setup_handlers(self):
        """Setup Telegram bot handlers"""
        
        logger.info("Setting up message handlers...")
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", start))
        self.application.add_handler(CommandHandler("help", help_cmd))
        self.application.add_handler(CommandHandler("status", status))
        self.application.add_handler(CommandHandler("security", security))
        self.application.add_handler(CommandHandler("ban", ban_user))
        self.application.add_handler(CommandHandler("unban", unban_user))
        self.application.add_handler(CommandHandler("stats", stats))
        self.application.add_handler(CommandHandler("export", export_data))
        self.application.add_handler(CommandHandler("sudo", sudo))
        
        # Message handlers
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
        )
        
        # Media message handlers
        self.application.add_handler(MessageHandler(filters.PHOTO, handle_media_message))
        self.application.add_handler(MessageHandler(filters.VIDEO, handle_media_message))
        self.application.add_handler(MessageHandler(filters.AUDIO, handle_media_message))
        self.application.add_handler(MessageHandler(filters.VOICE, handle_media_message))
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("✅ Handlers configured")
    
    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle bot errors"""
        
        logger.error(f"Bot error: {context.error}", exc_info=context.error)
        
        # Send error notification to sudo user
        if settings.sudo_user_id and update:
            try:
                error_text = (
                    f"🚨 **Bot Error Alert**\n\n"
                    f"**Error:** {str(context.error)[:200]}...\n"
                    f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**Update:** {str(update)[:100]}..."
                )
                
                await self.bot.send_message(
                    chat_id=settings.sudo_user_id,
                    text=error_text,
                    parse_mode='Markdown'
                )
            except Exception:
                pass  # Don't let error handler errors crash the bot
    
    async def start(self):
        """Start the bot"""
        
        logger.info("Starting FlushBot...")
        self.running = True
        
        try:
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=['message', 'callback_query', 'chat_member'],
                drop_pending_updates=True
            )
            
            # Start delayed sweep system
            from core.delayed_sweep import start_delayed_sweep
            await start_delayed_sweep()
            logger.info("🕒 Delayed sweep system started")
            
            # Send startup notification to sudo user
            if settings.sudo_user_id:
                try:
                    startup_text = (
                        f"🤖 **FlushBot Started**\n\n"
                        f"**Version:** Advanced Security System\n"
                        f"**Started:** {self.startup_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"**Security Level:** {settings.default_security_level.upper()}\n"
                        f"**AI System:** Grok-4 + Gemini 2.0 Fallback\n\n"
                        f"🛡️ Bot is now monitoring chats for security violations."
                    )
                    
                    await self.bot.send_message(
                        chat_id=settings.sudo_user_id,
                        text=startup_text,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Could not send startup notification: {e}")
            
            logger.info("🚀 FlushBot is running and ready!")
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Bot startup failed: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot gracefully"""
        
        logger.info("Stopping FlushBot...")
        self.running = False
        
        try:
            # Stop delayed sweep system
            from core.delayed_sweep import stop_delayed_sweep
            await stop_delayed_sweep()
            logger.info("🛑 Delayed sweep system stopped")
            # Send shutdown notification
            if settings.sudo_user_id and self.bot:
                try:
                    shutdown_text = (
                        f"🛑 **FlushBot Shutdown**\n\n"
                        f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"**Uptime:** {datetime.now() - self.startup_time if self.startup_time else 'Unknown'}\n\n"
                        f"Bot has been stopped gracefully."
                    )
                    
                    await self.bot.send_message(
                        chat_id=settings.sudo_user_id,
                        text=shutdown_text,
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass
            
            # Stop bot components
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            # Close AI analyzer
            await ai_analyzer.close()
            
            # Close cache connections
            await cache_manager.disconnect()
            
            logger.info("✅ FlushBot stopped gracefully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main application entry point"""
    
    print("FlushBot - Advanced Telegram Security System")
    print("=" * 50)
    print(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file based on .env.example")
        print("Run: cp .env.example .env")
        print("Then configure your API keys and settings.")
        sys.exit(1)
    
    # Initialize and start bot
    bot = FlushBot()
    bot.setup_signal_handlers()
    
    try:
        await bot.initialize()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await bot.stop()


if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 FlushBot shutdown complete.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)