"""
Security Enforcement Engine for FlushBot
Handles security level enforcement, user restrictions, and moderation actions
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from telegram import Bot, ChatMember, ChatPermissions
from telegram.error import TelegramError, Forbidden, BadRequest
from loguru import logger

from config.settings import settings, SECURITY_LEVELS
from config.security_rules import SecurityMode, ViolationSeverity
from core.database import db_manager, ActionType, Chat, User, Violation, ModerationAction
from core.cache import message_cache, rate_limiter


class RestrictionLevel(Enum):
    """User restriction levels"""
    NONE = "none"
    LIMITED = "limited"
    RESTRICTED = "restricted"
    BANNED = "banned"


class SecurityEnforcer:
    """Security enforcement engine"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.active_restrictions = {}  # chat_id -> {user_id: restriction_info}
    
    async def enforce_security_action(
        self, 
        analysis_result: Dict, 
        message_data: Dict, 
        chat_settings: Dict
    ) -> Dict:
        """
        Enforce security action based on analysis result
        
        Args:
            analysis_result: AI/rule analysis result
            message_data: Message information 
            chat_settings: Chat configuration
            
        Returns:
            Enforcement result with action taken
        """
        chat_id = message_data["chat_id"]
        user_id = message_data["user_id"]
        message_id = message_data["message_id"]
        
        # Check if user is admin/sudo - they bypass restrictions
        if await self._is_user_exempt(user_id, chat_id):
            return {
                "action_taken": "exempt",
                "reason": "admin_or_sudo_user",
                "success": True
            }
        
        # Get security mode for chat
        security_mode = SecurityMode(chat_settings.get("security_level", "medium"))
        
        # Determine required action
        violations = analysis_result.get("violations", [])
        if not violations:
            return {
                "action_taken": "allow",
                "reason": "no_violations",
                "success": True
            }
        
        # Check rate limiting
        is_limited, current_count = await rate_limiter.is_rate_limited(
            f"action:{user_id}", limit=10, window=300  # 10 actions per 5 minutes
        )
        
        if is_limited:
            logger.warning(f"Rate limited enforcement for user {user_id}")
            return {
                "action_taken": "rate_limited",
                "reason": "too_many_actions",
                "success": False
            }
        
        # Execute enforcement based on security mode and violation severity
        result = await self._execute_enforcement(
            violations, security_mode, message_data, chat_settings
        )
        
        # Store moderation action in database
        await self._record_moderation_action(result, message_data, violations)
        
        return result
    
    async def _execute_enforcement(
        self, 
        violations: List[Dict], 
        security_mode: SecurityMode, 
        message_data: Dict, 
        chat_settings: Dict
    ) -> Dict:
        """Execute the appropriate enforcement action"""
        
        chat_id = message_data["chat_id"]
        user_id = message_data["user_id"]
        message_id = message_data["message_id"]
        
        # Determine action based on violation severity and security mode
        max_severity = max((self._get_severity_level(v["severity"]) for v in violations), default=0)
        has_critical = any(v["severity"] == "critical" for v in violations)
        
        # Critical violations always result in immediate ban
        if has_critical:
            return await self._execute_ban(
                chat_id, user_id, message_id, 
                "Critical policy violation detected", 
                violations, permanent=True
            )
        
        # Security mode specific enforcement
        if security_mode == SecurityMode.EXTREME:
            if max_severity >= 2:  # Medium or High severity
                return await self._execute_ban(
                    chat_id, user_id, message_id,
                    "Policy violation in extreme security mode",
                    violations, permanent=True
                )
            else:
                return await self._execute_warning(
                    chat_id, user_id, message_id, violations, delete_message=True
                )
        
        elif security_mode == SecurityMode.MEDIUM:
            if max_severity >= 3:  # High severity
                # Check violation history for progressive enforcement
                user_violations = await db_manager.get_user_violations(user_id, days=7)
                
                if len(user_violations) >= 3:
                    return await self._execute_ban(
                        chat_id, user_id, message_id,
                        "Repeated policy violations",
                        violations, duration=7*24*3600  # 7 days
                    )
                elif len(user_violations) >= 1:
                    return await self._execute_restriction(
                        chat_id, user_id, message_id,
                        "Multiple policy violations", 
                        violations, duration=24*3600  # 24 hours
                    )
                else:
                    return await self._execute_warning(
                        chat_id, user_id, message_id, violations, delete_message=True
                    )
            elif max_severity >= 2:  # Medium severity
                return await self._execute_warning(
                    chat_id, user_id, message_id, violations, delete_message=False
                )
            else:
                return await self._log_violation(chat_id, user_id, message_id, violations)
        
        else:  # LOW mode
            if max_severity >= 2:
                return await self._execute_warning(
                    chat_id, user_id, message_id, violations, delete_message=False
                )
            else:
                return await self._log_violation(chat_id, user_id, message_id, violations)
    
    def _get_severity_level(self, severity: str) -> int:
        """Convert severity string to numeric level"""
        return {
            "low": 1,
            "medium": 2, 
            "high": 3,
            "critical": 4
        }.get(severity, 1)
    
    async def _execute_ban(
        self, 
        chat_id: int, 
        user_id: int, 
        message_id: int, 
        reason: str, 
        violations: List[Dict],
        permanent: bool = False,
        duration: Optional[int] = None
    ) -> Dict:
        """Execute user ban"""
        
        try:
            # Delete the violation message first
            await self._delete_message(chat_id, message_id)
            
            # Calculate ban until time
            until_date = None if permanent else datetime.now() + timedelta(seconds=duration or 86400)
            
            # Ban user from chat
            await self.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                until_date=until_date
            )
            
            # Update database
            await db_manager.ban_user(
                user_id, reason, duration if not permanent else None
            )
            await db_manager.increment_user_violations(user_id)
            
            # Send notification to admins (not public)
            await self._notify_admins(
                chat_id, 
                f"🚫 User banned for policy violation\nReason: {reason}",
                violations
            )
            
            logger.info(f"Banned user {user_id} in chat {chat_id}: {reason}")
            
            return {
                "action_taken": "ban",
                "reason": reason,
                "duration": duration,
                "permanent": permanent,
                "success": True,
                "message_deleted": True
            }
            
        except TelegramError as e:
            logger.error(f"Failed to ban user {user_id} in chat {chat_id}: {e}")
            return {
                "action_taken": "ban",
                "reason": reason, 
                "success": False,
                "error": str(e)
            }
    
    async def _execute_restriction(
        self, 
        chat_id: int, 
        user_id: int, 
        message_id: int, 
        reason: str, 
        violations: List[Dict],
        duration: int = 3600
    ) -> Dict:
        """Execute user restriction (mute)"""
        
        try:
            # Delete the violation message
            await self._delete_message(chat_id, message_id)
            
            # Restrict user permissions
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
            
            until_date = datetime.now() + timedelta(seconds=duration)
            
            await self.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=permissions,
                until_date=until_date
            )
            
            # Update violation count
            await db_manager.increment_user_violations(user_id)
            
            # Store restriction info
            self.active_restrictions.setdefault(chat_id, {})[user_id] = {
                "type": "restriction",
                "until": until_date,
                "reason": reason
            }
            
            logger.info(f"Restricted user {user_id} in chat {chat_id} for {duration}s: {reason}")
            
            return {
                "action_taken": "restrict",
                "reason": reason,
                "duration": duration,
                "success": True,
                "message_deleted": True
            }
            
        except TelegramError as e:
            logger.error(f"Failed to restrict user {user_id} in chat {chat_id}: {e}")
            return {
                "action_taken": "restrict",
                "reason": reason,
                "success": False,
                "error": str(e)
            }
    
    async def _execute_warning(
        self, 
        chat_id: int, 
        user_id: int, 
        message_id: int, 
        violations: List[Dict],
        delete_message: bool = False
    ) -> Dict:
        """Execute warning action"""
        
        try:
            if delete_message:
                await self._delete_message(chat_id, message_id)
            
            # Send private warning to user (no public shaming)
            try:
                warning_text = (
                    "⚠️ **Policy Violation Warning**\n\n"
                    "Your recent message was flagged for potential policy violations. "
                    "Please review the community guidelines and adjust your behavior accordingly.\n\n"
                    "Repeated violations may result in restrictions or removal from the chat."
                )
                
                await self.bot.send_message(
                    chat_id=user_id,
                    text=warning_text,
                    parse_mode='Markdown'
                )
            except (Forbidden, BadRequest):
                # User has blocked bot or doesn't allow PMs
                logger.info(f"Could not send private warning to user {user_id}")
            
            # Update violation count  
            await db_manager.increment_user_violations(user_id)
            
            logger.info(f"Warned user {user_id} in chat {chat_id}")
            
            return {
                "action_taken": "warn",
                "reason": "policy_violation",
                "success": True,
                "message_deleted": delete_message,
                "warning_sent": True
            }
            
        except TelegramError as e:
            logger.error(f"Failed to warn user {user_id}: {e}")
            return {
                "action_taken": "warn",
                "reason": "policy_violation",
                "success": False,
                "error": str(e)
            }
    
    async def _log_violation(
        self, 
        chat_id: int, 
        user_id: int, 
        message_id: int, 
        violations: List[Dict]
    ) -> Dict:
        """Log violation without taking action"""
        
        # Just increment violation count and log
        await db_manager.increment_user_violations(user_id)
        
        logger.info(f"Logged violation for user {user_id} in chat {chat_id}")
        
        return {
            "action_taken": "log",
            "reason": "low_severity_violation",
            "success": True,
            "message_deleted": False
        }
    
    async def _delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a message"""
        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except TelegramError as e:
            logger.error(f"Failed to delete message {message_id} in chat {chat_id}: {e}")
            return False
    
    async def _notify_admins(
        self, 
        chat_id: int, 
        message: str, 
        violations: List[Dict]
    ):
        """Send notification to chat admins"""
        try:
            # Get chat administrators
            admins = await self.bot.get_chat_administrators(chat_id)
            
            notification_text = f"{message}\n\nViolations detected: {len(violations)}"
            
            for admin in admins:
                if not admin.user.is_bot and admin.user.id != settings.sudo_user_id:
                    try:
                        await self.bot.send_message(
                            chat_id=admin.user.id,
                            text=notification_text
                        )
                    except (Forbidden, BadRequest):
                        # Admin has blocked bot or doesn't allow PMs
                        continue
            
            # Also notify sudo user
            if settings.sudo_user_id:
                try:
                    await self.bot.send_message(
                        chat_id=settings.sudo_user_id,
                        text=f"🔒 **FlushBot Alert**\n\nChat: {chat_id}\n{notification_text}"
                    )
                except (Forbidden, BadRequest):
                    pass
                    
        except TelegramError as e:
            logger.error(f"Failed to notify admins for chat {chat_id}: {e}")
    
    async def _is_user_exempt(self, user_id: int, chat_id: int) -> bool:
        """Check if user is exempt from restrictions (admin/sudo)"""
        
        # Check if user is sudo
        if user_id == settings.sudo_user_id:
            return True
        
        # Check if user is chat admin
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            return member.status in ['administrator', 'creator']
        except TelegramError:
            return False
    
    async def _record_moderation_action(
        self, 
        result: Dict, 
        message_data: Dict, 
        violations: List[Dict]
    ):
        """Record moderation action in database"""
        
        try:
            # Find violation record if it exists
            violation_id = None
            if violations:
                # This would need to be implemented based on how violations are stored
                pass
            
            action_data = {
                "chat_id": message_data["chat_id"],
                "user_id": message_data["user_id"], 
                "violation_id": violation_id,
                "action_type": result["action_taken"],
                "reason": result.get("reason", ""),
                "duration": result.get("duration"),
                "automated": True,
                "success": result.get("success", False),
                "error_message": result.get("error")
            }
            
            await db_manager.store_moderation_action(action_data)
            
        except Exception as e:
            logger.error(f"Failed to record moderation action: {e}")
    
    # Admin Commands
    
    async def manual_ban_user(
        self, 
        chat_id: int, 
        user_id: int, 
        admin_id: int, 
        reason: str, 
        duration: Optional[int] = None
    ) -> Dict:
        """Manually ban a user (admin command)"""
        
        try:
            until_date = None if not duration else datetime.now() + timedelta(seconds=duration)
            
            await self.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=user_id, 
                until_date=until_date
            )
            
            # Record manual action
            action_data = {
                "chat_id": chat_id,
                "user_id": user_id,
                "action_type": "ban",
                "reason": f"Manual ban by admin: {reason}",
                "duration": duration,
                "automated": False,
                "admin_user_id": admin_id,
                "success": True
            }
            
            await db_manager.store_moderation_action(action_data)
            
            return {"success": True, "message": "User banned successfully"}
            
        except TelegramError as e:
            return {"success": False, "error": str(e)}
    
    async def manual_unban_user(self, chat_id: int, user_id: int, admin_id: int) -> Dict:
        """Manually unban a user (admin command)"""
        
        try:
            await self.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            
            # Update database
            await db_manager.ban_user(user_id, "", duration=0)  # Clear ban
            
            # Record action
            action_data = {
                "chat_id": chat_id,
                "user_id": user_id,
                "action_type": "unban",
                "reason": "Manual unban by admin",
                "automated": False,
                "admin_user_id": admin_id,
                "success": True
            }
            
            await db_manager.store_moderation_action(action_data)
            
            return {"success": True, "message": "User unbanned successfully"}
            
        except TelegramError as e:
            return {"success": False, "error": str(e)}
    
    async def leave_chat(self, chat_id: int) -> Dict:
        """Leave a chat (sudo command)"""
        
        try:
            await self.bot.leave_chat(chat_id)
            
            # Update chat status in database
            with db_manager.get_session() as session:
                chat = session.query(Chat).filter(Chat.chat_id == chat_id).first()
                if chat:
                    chat.is_active = False
                    session.commit()
            
            return {"success": True, "message": "Left chat successfully"}
            
        except TelegramError as e:
            return {"success": False, "error": str(e)}
    
    async def get_chat_statistics(self, chat_id: int) -> Dict:
        """Get enforcement statistics for a chat"""
        return await db_manager.get_chat_statistics(chat_id)


# Global enforcer instance (will be initialized with bot instance)
security_enforcer: Optional[SecurityEnforcer] = None


def initialize_security_enforcer(bot: Bot):
    """Initialize global security enforcer with bot instance"""
    global security_enforcer
    security_enforcer = SecurityEnforcer(bot)