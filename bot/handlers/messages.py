"""
Message Handler for FlushBot
Processes all incoming messages for security analysis
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional

from telegram import Update, Message, User as TelegramUser
from telegram.ext import ContextTypes
from loguru import logger

from config.settings import settings
from config.security_rules import security_rules
from core.ai_analyzer import ai_analyzer
from core.database import db_manager
from core.cache import message_cache
from bot.utils.admin_utils import admin_manager

def get_security_enforcer():
    """Get security enforcer instance safely"""
    try:
        from core.security import security_enforcer
        return security_enforcer
    except ImportError:
        return None

class MessageProcessor:
    """Processes incoming messages for security analysis"""
    
    def __init__(self):
        self.processing_queue = asyncio.Queue()
        self.batch_messages = []
        self.last_batch_time = datetime.now()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming message"""
        
        if not update.message or not update.message.text:
            return
        
        message = update.message
        
        # Extract message data
        message_data = self._extract_message_data(message)
        
        # Check admin status for logging
        is_admin = await self._is_user_admin(message_data["user_id"], message_data["chat_id"])
        admin_status = "👑 ADMIN" if is_admin else "👤 USER"
        
        # 📊 DETAILED MESSAGE LOGGING
        logger.info(f"📨 NEW MESSAGE | Chat: {message_data['chat_id']} | {admin_status}: {message_data['user_id']} ({message_data.get('user_username', 'N/A')}) | Text: '{message_data['text'][:100]}...' | Length: {len(message_data['text'])}")
        
        # Skip processing ONLY for sudo user (bot owner)
        if await self._is_user_exempt(message_data["user_id"], message_data["chat_id"]):
            logger.info(f"⚪ SUDO EXEMPT | User {message_data['user_id']} is the bot owner (sudo user)")
            return
        
        # Check if it's a bot message and handle accordingly
        if message_data["user_is_bot"]:
            await self._handle_bot_message(message_data, context)
            return
        
        # Add to processing queue for batch processing or immediate analysis
        if settings.enable_batch_processing:
            await self._add_to_batch(message_data)
        else:
            await self._process_single_message(message_data, context)
    
    def _extract_message_data(self, message: Message) -> Dict:
        """Extract relevant data from Telegram message"""
        
        user = message.from_user
        chat = message.chat
        
        return {
            "message_id": message.message_id,
            "chat_id": chat.id,
            "user_id": user.id,
            "text": message.text or "",
            "timestamp": message.date,
            "chat_title": getattr(chat, 'title', ''),
            "chat_type": chat.type,
            "user_username": getattr(user, 'username', ''),
            "user_first_name": getattr(user, 'first_name', ''),
            "user_last_name": getattr(user, 'last_name', ''),
            "user_is_bot": user.is_bot,
            "message_type": "text",
            "reply_to_message": message.reply_to_message.message_id if message.reply_to_message else None,
            "forward_from": getattr(message.forward_from, 'id', None) if hasattr(message, 'forward_from') and message.forward_from else None
        }
    
    async def _is_user_exempt(self, user_id: int, chat_id: int) -> bool:
        """Check if user should be exempt from ALL security processing"""
        
        # Only SUDO user (bot owner) is fully exempt from security checks
        if user_id == settings.sudo_user_id:
            return True
        
        # NO OTHER USERS ARE EXEMPT - admins can also violate TOS
        return False
    
    async def _is_user_admin(self, user_id: int, chat_id: int) -> bool:
        """Check if user is a chat admin (for context, not exemption)"""
        
        # Check if user is chat admin (cached check)
        cache_key = f"admin:{chat_id}:{user_id}"
        is_admin = await message_cache.cache.get(cache_key)
        
        if is_admin is None:
            try:
                # Check with Telegram API
                security_enforcer = get_security_enforcer()
                if security_enforcer and security_enforcer.bot:
                    member = await security_enforcer.bot.get_chat_member(chat_id, user_id)
                    is_admin = member.status in ['administrator', 'creator']
                    
                    # Cache result for 1 hour
                    await message_cache.cache.set(cache_key, is_admin, ttl=3600)
                else:
                    logger.warning("Security enforcer or bot not available for admin check")
                    is_admin = False
            except Exception as e:
                logger.error(f"Failed to check admin status for user {user_id}: {e}")
                is_admin = False
        
        return is_admin
    
    async def _handle_bot_message(self, message_data: Dict, context: ContextTypes.DEFAULT_TYPE):
        """Handle message from another bot"""
        
        chat_settings = await self._get_chat_settings(message_data["chat_id"])
        
        if not chat_settings.get("bot_detection_enabled", True):
            return
        
        # Check if bot is allowed
        allowed_bots = chat_settings.get("config", {}).get("allowed_bots", [])
        
        if message_data["user_id"] not in allowed_bots:
            # Delete bot message
            try:
                if context and context.bot:
                    await context.bot.delete_message(
                        chat_id=message_data["chat_id"],
                        message_id=message_data["message_id"]
                    )
                else:
                    security_enforcer = get_security_enforcer()
                    if security_enforcer and security_enforcer.bot:
                        await security_enforcer.bot.delete_message(
                            chat_id=message_data["chat_id"],
                            message_id=message_data["message_id"]
                        )
                
                logger.info(f"Deleted message from unauthorized bot {message_data['user_id']} in chat {message_data['chat_id']}")
                
            except Exception as e:
                logger.error(f"Failed to delete bot message: {e}")
    
    async def _add_to_batch(self, message_data: Dict):
        """Add message to batch processing queue"""
        
        self.batch_messages.append(message_data)
        
        # Process batch if it's full or enough time has passed
        time_since_last_batch = (datetime.now() - self.last_batch_time).total_seconds()
        
        if (len(self.batch_messages) >= settings.batch_processing_size or 
            time_since_last_batch >= settings.batch_interval_minutes * 60):
            
            await self._process_batch()
    
    async def _process_batch(self):
        """Process accumulated batch of messages"""
        
        if not self.batch_messages:
            return
        
        batch = self.batch_messages.copy()
        self.batch_messages.clear()
        self.last_batch_time = datetime.now()
        
        logger.info(f"Processing batch of {len(batch)} messages")
        
        try:
            # Prepare messages for AI analysis
            ai_messages = [
                {
                    "text": msg["text"],
                    "context": {
                        "user_id": msg["user_id"],
                        "chat_id": msg["chat_id"],
                        "timestamp": msg["timestamp"].isoformat()
                    }
                }
                for msg in batch
            ]
            
            # Batch analyze with AI
            analysis_results = await ai_analyzer.batch_analyze(ai_messages)
            
            # Process each result
            for message_data, analysis_result in zip(batch, analysis_results):
                await self._handle_analysis_result(message_data, analysis_result)
                
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            
            # Fallback to individual processing
            for message_data in batch:
                try:
                    await self._process_single_message(message_data, None)
                except Exception as inner_e:
                    logger.error(f"Fallback processing failed for message: {inner_e}")
    
    async def _process_single_message(self, message_data: Dict, context: Optional[ContextTypes.DEFAULT_TYPE]):
        """Process individual message"""
        
        try:
            # Store message in database
            db_message_data = {
                "message_id": message_data["message_id"],
                "chat_id": message_data["chat_id"],
                "user_id": message_data["user_id"],
                "text": message_data["text"],
                "message_type": message_data["message_type"],
                "timestamp": message_data["timestamp"],
                "message_metadata": {
                    "chat_title": message_data["chat_title"],
                    "user_username": message_data["user_username"],
                    "reply_to": message_data["reply_to_message"],
                    "forward_from": message_data["forward_from"]
                }
            }
            
            stored_message = await db_manager.store_message(db_message_data)
            
            # Get or create user
            user_data = {
                "user_id": message_data["user_id"],
                "username": message_data["user_username"],
                "first_name": message_data["user_first_name"],
                "last_name": message_data["user_last_name"],
                "is_bot": message_data["user_is_bot"]
            }
            
            await db_manager.get_or_create_user(user_data)
            
            # Check cache for identical message analysis
            cached_analysis = await message_cache.get_cached_analysis(message_data["text"])
            
            if cached_analysis and not settings.debug:  # Skip cache in debug mode
                analysis_result = cached_analysis
                logger.debug(f"Using cached analysis for message {message_data['message_id']}")
            else:
                # Analyze message with AI
                context_data = {
                    "user_id": message_data["user_id"],
                    "chat_id": message_data["chat_id"],
                    "chat_type": message_data["chat_type"],
                    "timestamp": message_data["timestamp"].isoformat(),  # Convert datetime to ISO string
                    "reply_to": message_data["reply_to_message"] is not None
                }
                
                analysis_result = await ai_analyzer.analyze_content(
                    message_data["text"], 
                    context_data
                )
                
                # Cache analysis result
                if analysis_result.get("ai_analysis"):
                    await message_cache.cache_analysis_result(
                        message_data["text"], 
                        analysis_result
                    )
            
            # Update message with analysis
            await db_manager.update_message_analysis(stored_message.id, analysis_result)
            
            # Handle analysis result
            await self._handle_analysis_result(message_data, analysis_result, context)
            
        except Exception as e:
            logger.error(f"Failed to process message {message_data['message_id']}: {e}")
    
    async def _handle_analysis_result(self, message_data: Dict, analysis_result: Dict, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
        """Handle the result of message analysis"""
        
        violations = analysis_result.get("violations", [])
        
        # Get chat settings
        chat_settings = await self._get_chat_settings(message_data["chat_id"])
        
        # Get current security mode from chat settings
        security_mode_str = chat_settings.get("security_mode", "medium")
        from config.security_rules import SecurityMode
        security_mode = SecurityMode(security_mode_str)
        
        # 🔍 DETAILED SECURITY ANALYSIS LOGGING
        logger.info(f"🛡️ SECURITY ANALYSIS | Chat: {message_data['chat_id']} | Mode: {security_mode.value.upper()} | Violations Found: {len(violations)}")
        
        if violations:
            for i, violation in enumerate(violations, 1):
                logger.info(f"⚠️ VIOLATION {i} | Category: {violation.get('category', 'unknown')} | Severity: {violation.get('severity', 'unknown')} | Confidence: {violation.get('confidence', 0):.2f}")
        else:
            logger.info(f"✅ CLEAN MESSAGE | No violations detected")
            return
        
        # Instant deletion check based on security mode
        from config.security_rules import should_delete_message
        
        # Check if message should be deleted instantly
        violation_categories = [v["category"] for v in violations]
        should_delete = should_delete_message(violation_categories, security_mode)
        
        logger.info(f"🎯 DELETION DECISION | Categories: {violation_categories} | Security Mode: {security_mode.value} | Should Delete: {should_delete}")
        
        if should_delete:
            # Delete message immediately and silently
            try:
                logger.warning(f"🎯 ATTEMPTING DELETION | Chat: {message_data['chat_id']} | TG Message ID: {message_data['message_id']} | User: {message_data['user_id']} | Categories: {violation_categories}")
                
                security_enforcer = get_security_enforcer()
                if security_enforcer and security_enforcer.bot:
                    await security_enforcer.bot.delete_message(
                        chat_id=message_data["chat_id"],
                        message_id=message_data["message_id"]
                    )
                    logger.warning(f"✅ DELETION SUCCESS | User: {message_data['user_id']} | Chat: {message_data['chat_id']} | Categories: {violation_categories} | Text: '{message_data['text'][:50]}...'")
                elif context and context.bot:
                    await context.bot.delete_message(
                        chat_id=message_data["chat_id"], 
                        message_id=message_data["message_id"]
                    )
                    logger.warning(f"✅ DELETION VIA CONTEXT | Categories: {violation_categories} | Text: '{message_data['text'][:50]}...'")
                else:
                    logger.error("❌ NO BOT AVAILABLE FOR DELETION")
            except Exception as e:
                logger.error(f"❌ DELETION FAILED | Chat: {message_data['chat_id']} | TG Message ID: {message_data['message_id']} | Error: {e} | Message: '{message_data['text'][:50]}...'")
        else:
            logger.info(f"📝 MESSAGE PRESERVED | Violations found but not deleted per security mode {security_mode.value}")
        
        # Store violations in database (whether deleted or not - for history tracking)
        for violation in violations:
            violation_data = {
                "message_id": message_data["message_id"],  # This should be the DB message ID
                "chat_id": message_data["chat_id"],
                "user_id": message_data["user_id"],
                "violation_type": violation["category"],
                "severity": violation["severity"],
                "confidence": violation.get("confidence", 0.0),
                "detected_by": "instant" if should_delete else "rules",
                "ai_model": "instant_detection" if should_delete else None,
                "description": f"{'DELETED: ' if should_delete else ''}{violation.get('description', '')}",
                "keywords_matched": violation.get("keyword_matches", []),
                "patterns_matched": violation.get("pattern_matches", [])
            }
            
            await db_manager.store_violation(violation_data)
        
        # Enforce security action
        security_enforcer = get_security_enforcer()
        if security_enforcer:
            enforcement_result = await security_enforcer.enforce_security_action(
                analysis_result, message_data, chat_settings
            )
            
            logger.info(
                f"Security action for user {message_data['user_id']} in chat {message_data['chat_id']}: "
                f"{enforcement_result.get('action_taken', 'none')}"
            )
    
    async def _get_chat_settings(self, chat_id: int) -> Dict:
        """Get chat settings from cache or database"""
        
        # Try cache first
        settings = await message_cache.get_chat_settings(chat_id)
        
        if not settings:
            # Get from database
            settings = await db_manager.get_chat_settings(chat_id)
            
            if not settings:
                # Create default settings
                await db_manager.get_or_create_chat(chat_id)
                settings = await db_manager.get_chat_settings(chat_id)
            
            # Cache settings
            if settings:
                await message_cache.cache_chat_settings(settings)
        
        return settings or {}


# Global message processor
message_processor = MessageProcessor()


# Handler function for telegram-python-bot
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler function for text messages"""
    await message_processor.handle_message(update, context)


async def handle_media_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler function for media messages (photos, videos, etc.)"""
    
    # For now, just log media messages - image analysis will be added later
    if update.message:
        # Determine message type based on available attributes
        msg_type = "unknown"
        if update.message.photo:
            msg_type = "photo"
        elif update.message.video:
            msg_type = "video"
        elif update.message.audio:
            msg_type = "audio"
        elif update.message.voice:
            msg_type = "voice"
        elif update.message.document:
            msg_type = "document"
        elif update.message.sticker:
            msg_type = "sticker"
            
        logger.info(
            f"Media message received in chat {update.message.chat.id} "
            f"from user {update.message.from_user.id}: {msg_type}"
        )
    
    # TODO: Implement image/video content analysis in Phase 2