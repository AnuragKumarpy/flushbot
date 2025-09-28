#!/usr/bin/env python3
"""
Delayed Sweep System for FlushBot
Exports chat history every 30 minutes, analyzes with AI, and deletes inappropriate content
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from telegram import Bot
from telegram.error import TelegramError
from loguru import logger

from config.settings import settings
from config.security_rules import should_delete_message, SecurityMode, SECURITY_MODE_RULES
from core.database import db_manager
from core.cache import cache_manager
from core.ai_analyzer import ai_analyzer


class DelayedSweepSystem:
    """
    Secondary detection system that exports chat history and analyzes with AI
    Runs every 30 minutes to catch messages that bypassed instant detection
    """
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.sweep_interval = 1800  # 30 minutes
        self.export_path = Path("data/exports/delayed_sweeps")
        self.export_path.mkdir(parents=True, exist_ok=True)
        self.running = False
    
    async def start(self):
        """Start the delayed sweep background task"""
        if self.running:
            return
        
        self.running = True
        logger.info("🕒 Starting delayed sweep system (30-minute intervals)")
        
        # Start background task
        asyncio.create_task(self._sweep_loop())
    
    async def stop(self):
        """Stop the delayed sweep system"""
        self.running = False
        logger.info("⏹️ Stopped delayed sweep system")
    
    async def _sweep_loop(self):
        """Main sweep loop - runs every 30 minutes"""
        while self.running:
            try:
                await asyncio.sleep(self.sweep_interval)
                if self.running:  # Check again after sleep
                    await self._perform_sweep()
            except Exception as e:
                logger.error(f"Error in delayed sweep loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _perform_sweep(self):
        """Perform a complete sweep of all active chats"""
        logger.info("🔍 Starting delayed sweep analysis...")
        
        try:
            # Get all active chats from database
            active_chats = await db_manager.get_active_chats()
            
            sweep_stats = {
                "chats_processed": 0,
                "messages_analyzed": 0,
                "messages_deleted": 0,
                "violations_found": 0
            }
            
            for chat in active_chats:
                chat_id = chat.chat_id
                try:
                    # Process this chat
                    chat_stats = await self._sweep_chat(chat_id)
                    
                    # Update overall stats
                    sweep_stats["chats_processed"] += 1
                    sweep_stats["messages_analyzed"] += chat_stats["messages_analyzed"]
                    sweep_stats["messages_deleted"] += chat_stats["messages_deleted"]
                    sweep_stats["violations_found"] += chat_stats["violations_found"]
                    
                except Exception as e:
                    logger.error(f"Error sweeping chat {chat_id}: {e}")
            
            # Log sweep results
            logger.info(
                f"🧹 Sweep completed: {sweep_stats['chats_processed']} chats, "
                f"{sweep_stats['messages_analyzed']} messages analyzed, "
                f"{sweep_stats['messages_deleted']} deleted, "
                f"{sweep_stats['violations_found']} violations found"
            )
            
        except Exception as e:
            logger.error(f"Error in delayed sweep: {e}")
    
    async def _sweep_chat(self, chat_id: int) -> Dict:
        """Sweep a single chat for violations"""
        chat_stats = {
            "messages_analyzed": 0,
            "messages_deleted": 0,
            "violations_found": 0
        }
        
        try:
            # Get chat settings to determine security mode
            chat_settings = await db_manager.get_chat_settings(chat_id)
            security_mode_str = chat_settings.get("security_mode", "medium")
            security_mode = SecurityMode(security_mode_str)
            
            # Export recent chat history (last 30 minutes)
            cutoff_time = datetime.now() - timedelta(minutes=30)
            messages = await self._export_chat_history(chat_id, cutoff_time)
            
            if not messages:
                return chat_stats
            
            logger.info(f"Analyzing {len(messages)} messages from chat {chat_id}")
            
            # Analyze each message with AI
            for message in messages:
                try:
                    chat_stats["messages_analyzed"] += 1
                    
                    # Skip if already processed or deleted
                    if message.get("already_deleted", False):
                        continue
                    
                    # Analyze with AI
                    analysis_result = await ai_analyzer.analyze_content(
                        message["text"],
                        {
                            "chat_id": chat_id,
                            "user_id": message["user_id"],
                            "timestamp": message["timestamp"],
                            "delayed_analysis": True
                        }
                    )
                    
                    # Check for violations
                    violations = analysis_result.get("violations", [])
                    if violations:
                        chat_stats["violations_found"] += len(violations)
                        
                        # Check if message should be deleted based on security mode
                        violation_categories = [v["category"] for v in violations]
                        should_delete = should_delete_message(violation_categories, security_mode)
                        
                        if should_delete:
                            # Try to delete the message
                            deleted = await self._delete_message_by_id(
                                chat_id, 
                                message["message_id"],
                                violation_categories
                            )
                            
                            if deleted:
                                chat_stats["messages_deleted"] += 1
                                
                                # Log the violation in database
                                await self._log_delayed_violation(
                                    message, violations, "DELAYED_DELETE"
                                )
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error analyzing message {message.get('message_id')}: {e}")
            
        except Exception as e:
            logger.error(f"Error in chat sweep {chat_id}: {e}")
        
        return chat_stats
    
    async def _export_chat_history(self, chat_id: int, since: datetime) -> List[Dict]:
        """Export recent chat history for analysis"""
        try:
            # Get messages from database (messages stored by FlushBot)
            messages = await db_manager.get_recent_messages(chat_id, since)
            
            return [
                {
                    "message_id": msg.message_id,
                    "user_id": msg.user_id,
                    "text": msg.text or "",
                    "timestamp": msg.timestamp,
                    "already_deleted": msg.violation_detected,
                }
                for msg in messages
                if msg.text and len(msg.text.strip()) > 0
            ]
            
        except Exception as e:
            logger.error(f"Error exporting chat history for {chat_id}: {e}")
            return []
    
    async def _delete_message_by_id(self, chat_id: int, message_id: int, categories: List[str]) -> bool:
        """Attempt to delete a message by ID"""
        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(
                f"🗑️ [DELAYED] Deleted message {message_id} in chat {chat_id} "
                f"- Categories: {categories}"
            )
            return True
            
        except TelegramError as e:
            if "message to delete not found" in str(e).lower():
                logger.debug(f"Message {message_id} already deleted or not found")
            else:
                logger.warning(f"Failed to delete message {message_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")
            return False
    
    async def _log_delayed_violation(self, message: Dict, violations: List[Dict], action: str):
        """Log violation found during delayed sweep"""
        try:
            for violation in violations:
                violation_data = {
                    "message_id": message["message_id"],
                    "chat_id": message.get("chat_id"),
                    "user_id": message["user_id"],
                    "violation_type": violation["category"],
                    "severity": violation["severity"],
                    "confidence": violation.get("confidence", 0.0),
                    "detected_by": "delayed_ai_sweep",
                    "ai_model": "grok-4_delayed",
                    "description": f"{action}: {violation.get('description', '')}",
                    "keywords_matched": violation.get("keyword_matches", []),
                    "patterns_matched": violation.get("pattern_matches", [])
                }
                
                await db_manager.store_violation(violation_data)
                
        except Exception as e:
            logger.error(f"Error logging delayed violation: {e}")


# Global instance (will be initialized when bot starts)
delayed_sweep_system: Optional[DelayedSweepSystem] = None

def initialize_delayed_sweep(bot: Bot):
    """Initialize the delayed sweep system"""
    global delayed_sweep_system
    delayed_sweep_system = DelayedSweepSystem(bot)

async def start_delayed_sweep():
    """Start the delayed sweep system"""
    if delayed_sweep_system:
        await delayed_sweep_system.start()

async def stop_delayed_sweep():
    """Stop the delayed sweep system"""
    if delayed_sweep_system:
        await delayed_sweep_system.stop()