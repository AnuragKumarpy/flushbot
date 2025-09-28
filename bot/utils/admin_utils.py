"""
Admin Utilities for FlushBot
Helper functions for admin operations and permission management
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from telegram import Chat, ChatMember, User as TelegramUser
from telegram.error import TelegramError
from loguru import logger

from config.settings import settings
from core.database import db_manager


class AdminManager:
    """Manages admin permissions and operations"""
    
    def __init__(self, bot):
        self.bot = bot
        self._admin_cache = {}  # chat_id -> {user_id: (is_admin, cached_at)}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    async def is_admin(self, user_id: int, chat_id: int) -> bool:
        """
        Check if user is admin in the specific chat (not requiring global admin chat)
        """
        
        # Sudo user is always admin
        if user_id == settings.sudo_user_id:
            return True
        
        # Check cache first
        cache_key = (chat_id, user_id)
        if cache_key in self._admin_cache:
            is_admin, cached_at = self._admin_cache[cache_key]
            if (datetime.now() - cached_at).seconds < self._cache_ttl:
                return is_admin
        
        # Check with Telegram API
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in ['administrator', 'creator']
            
            # Cache result
            self._admin_cache[cache_key] = (is_admin, datetime.now())
            
            return is_admin
            
        except TelegramError as e:
            logger.error(f"Failed to check admin status for user {user_id} in chat {chat_id}: {e}")
            return False
    
    async def get_chat_admins(self, chat_id: int) -> List[Dict]:
        """Get list of chat administrators"""
        
        try:
            administrators = await self.bot.get_chat_administrators(chat_id)
            
            admin_list = []
            for admin in administrators:
                user = admin.user
                admin_info = {
                    "user_id": user.id,
                    "username": getattr(user, 'username', None),
                    "first_name": getattr(user, 'first_name', ''),
                    "last_name": getattr(user, 'last_name', ''),
                    "status": admin.status,
                    "is_anonymous": getattr(admin, 'is_anonymous', False),
                    "can_be_edited": getattr(admin, 'can_be_edited', False),
                    "can_manage_chat": getattr(admin, 'can_manage_chat', False),
                    "can_delete_messages": getattr(admin, 'can_delete_messages', False),
                    "can_manage_video_chats": getattr(admin, 'can_manage_video_chats', False),
                    "can_restrict_members": getattr(admin, 'can_restrict_members', False),
                    "can_promote_members": getattr(admin, 'can_promote_members', False),
                    "can_change_info": getattr(admin, 'can_change_info', False),
                    "can_invite_users": getattr(admin, 'can_invite_users', False),
                    "can_pin_messages": getattr(admin, 'can_pin_messages', False)
                }
                admin_list.append(admin_info)
            
            return admin_list
            
        except TelegramError as e:
            logger.error(f"Failed to get chat admins for {chat_id}: {e}")
            return []
    
    async def has_required_permissions(self, chat_id: int) -> Tuple[bool, List[str]]:
        """Check if bot has required permissions in chat"""
        
        required_permissions = [
            'can_delete_messages',
            'can_restrict_members'
        ]
        
        try:
            bot_member = await self.bot.get_chat_member(chat_id, self.bot.id)
            
            missing_permissions = []
            for perm in required_permissions:
                if not getattr(bot_member, perm, False):
                    missing_permissions.append(perm)
            
            return len(missing_permissions) == 0, missing_permissions
            
        except TelegramError as e:
            logger.error(f"Failed to check bot permissions in chat {chat_id}: {e}")
            return False, required_permissions
    
    async def get_chat_info(self, chat_id: int) -> Optional[Dict]:
        """Get comprehensive chat information"""
        
        try:
            chat = await self.bot.get_chat(chat_id)
            
            chat_info = {
                "chat_id": chat.id,
                "title": getattr(chat, 'title', ''),
                "type": chat.type,
                "description": getattr(chat, 'description', ''),
                "invite_link": getattr(chat, 'invite_link', ''),
                "pinned_message_id": chat.pinned_message.message_id if chat.pinned_message else None,
                "permissions": {
                    "can_send_messages": getattr(chat.permissions, 'can_send_messages', True) if chat.permissions else True,
                    "can_send_media_messages": getattr(chat.permissions, 'can_send_media_messages', True) if chat.permissions else True,
                    "can_send_polls": getattr(chat.permissions, 'can_send_polls', True) if chat.permissions else True,
                    "can_send_other_messages": getattr(chat.permissions, 'can_send_other_messages', True) if chat.permissions else True,
                    "can_add_web_page_previews": getattr(chat.permissions, 'can_add_web_page_previews', True) if chat.permissions else True,
                    "can_change_info": getattr(chat.permissions, 'can_change_info', False) if chat.permissions else False,
                    "can_invite_users": getattr(chat.permissions, 'can_invite_users', True) if chat.permissions else True,
                    "can_pin_messages": getattr(chat.permissions, 'can_pin_messages', False) if chat.permissions else False
                } if chat.permissions else {}
            }
            
            # Get member count for groups
            if chat.type in ['group', 'supergroup']:
                try:
                    member_count = await self.bot.get_chat_member_count(chat_id)
                    chat_info["member_count"] = member_count
                except TelegramError:
                    chat_info["member_count"] = None
            
            return chat_info
            
        except TelegramError as e:
            logger.error(f"Failed to get chat info for {chat_id}: {e}")
            return None
    
    async def notify_chat_admins(
        self, 
        chat_id: int, 
        message: str, 
        exclude_user_id: Optional[int] = None
    ):
        """Send notification to all chat administrators"""
        
        admins = await self.get_chat_admins(chat_id)
        
        notification_count = 0
        for admin in admins:
            # Skip bots and excluded user
            if admin.get('user_id') == self.bot.id:
                continue
            if exclude_user_id and admin.get('user_id') == exclude_user_id:
                continue
            
            try:
                await self.bot.send_message(
                    chat_id=admin['user_id'],
                    text=f"🔔 **Admin Notification**\n\nChat: {chat_id}\n{message}",
                    parse_mode='Markdown'
                )
                notification_count += 1
                
            except TelegramError:
                # Admin may have blocked bot or disabled PMs
                continue
        
        logger.info(f"Sent admin notifications to {notification_count} admins in chat {chat_id}")
        return notification_count
    
    def clear_admin_cache(self, chat_id: Optional[int] = None, user_id: Optional[int] = None):
        """Clear admin cache for specific chat/user or all"""
        
        if chat_id and user_id:
            # Clear specific cache entry
            cache_key = (chat_id, user_id)
            if cache_key in self._admin_cache:
                del self._admin_cache[cache_key]
        elif chat_id:
            # Clear all cache entries for chat
            keys_to_remove = [key for key in self._admin_cache.keys() if key[0] == chat_id]
            for key in keys_to_remove:
                del self._admin_cache[key]
        else:
            # Clear entire cache
            self._admin_cache.clear()
    
    async def validate_chat_setup(self, chat_id: int) -> Dict:
        """Validate chat setup and permissions"""
        
        validation_result = {
            "chat_id": chat_id,
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        # Check if chat exists and bot is member
        chat_info = await self.get_chat_info(chat_id)
        if not chat_info:
            validation_result["valid"] = False
            validation_result["issues"].append("Cannot access chat information")
            return validation_result
        
        # Check bot permissions
        has_perms, missing_perms = await self.has_required_permissions(chat_id)
        if not has_perms:
            validation_result["valid"] = False
            validation_result["issues"].extend([
                f"Missing permission: {perm}" for perm in missing_perms
            ])
        
        # Check if there are any admins
        admins = await self.get_chat_admins(chat_id)
        human_admins = [a for a in admins if a["user_id"] != self.bot.id]
        
        if not human_admins:
            validation_result["warnings"].append("No human administrators found")
        
        # Check chat settings in database
        chat_settings = await db_manager.get_chat_settings(chat_id)
        if not chat_settings:
            validation_result["warnings"].append("Chat not initialized in database")
        
        return validation_result


class PermissionManager:
    """Manages user permissions and restrictions"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def can_delete_messages(self, chat_id: int) -> bool:
        """Check if bot can delete messages in chat"""
        
        try:
            bot_member = await self.bot.get_chat_member(chat_id, self.bot.id)
            return getattr(bot_member, 'can_delete_messages', False)
        except TelegramError:
            return False
    
    async def can_restrict_members(self, chat_id: int) -> bool:
        """Check if bot can restrict members in chat"""
        
        try:
            bot_member = await self.bot.get_chat_member(chat_id, self.bot.id)
            return getattr(bot_member, 'can_restrict_members', False)
        except TelegramError:
            return False
    
    async def can_ban_members(self, chat_id: int) -> bool:
        """Check if bot can ban members in chat"""
        
        try:
            bot_member = await self.bot.get_chat_member(chat_id, self.bot.id)
            return getattr(bot_member, 'can_restrict_members', False)
        except TelegramError:
            return False
    
    async def get_user_permissions(self, chat_id: int, user_id: int) -> Dict:
        """Get user's permissions in chat"""
        
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            
            permissions = {
                "status": member.status,
                "is_member": member.status not in ['left', 'kicked'],
                "can_send_messages": True,
                "can_send_media": True,
                "until_date": None
            }
            
            # Handle restricted members
            if member.status == 'restricted':
                permissions.update({
                    "can_send_messages": getattr(member, 'can_send_messages', False),
                    "can_send_media": getattr(member, 'can_send_media_messages', False),
                    "can_send_polls": getattr(member, 'can_send_polls', False),
                    "can_send_other_messages": getattr(member, 'can_send_other_messages', False),
                    "can_add_web_page_previews": getattr(member, 'can_add_web_page_previews', False),
                    "until_date": getattr(member, 'until_date', None)
                })
            
            # Handle kicked members
            elif member.status == 'kicked':
                permissions.update({
                    "can_send_messages": False,
                    "can_send_media": False,
                    "until_date": getattr(member, 'until_date', None)
                })
            
            return permissions
            
        except TelegramError as e:
            logger.error(f"Failed to get user permissions for {user_id} in {chat_id}: {e}")
            return {
                "status": "unknown",
                "is_member": False,
                "can_send_messages": False,
                "can_send_media": False,
                "until_date": None
            }


# Global instances will be initialized with bot instance
admin_manager: Optional[AdminManager] = None
permission_manager: Optional[PermissionManager] = None


def initialize_admin_utils(bot):
    """Initialize admin utilities with bot instance"""
    global admin_manager, permission_manager
    admin_manager = AdminManager(bot)
    permission_manager = PermissionManager(bot)