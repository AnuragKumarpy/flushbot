"""
Command Handlers for FlushBot
Handles admin commands, user commands, and sudo commands
"""

from datetime import datetime, timedelta
from typing import Dict, List

from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from loguru import logger

from config.settings import settings, SECURITY_LEVELS
from core.database import db_manager
from core.cache import message_cache
from core.ai_analyzer import ai_analyzer
from bot.utils.admin_utils import admin_manager
from bot.utils.data_processing import data_exporter

def get_security_enforcer():
    """Get security enforcer instance safely"""
    try:
        from core.security import security_enforcer
        return security_enforcer
    except ImportError:
        return None

class CommandHandler:
    """Handles bot commands"""
    
    def __init__(self):
        pass
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        
        if not update.message:
            return
        
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id
        
        # Initialize chat and user in database
        await db_manager.get_or_create_chat(
            chat_id, 
            title=getattr(update.message.chat, 'title', ''),
            chat_type=update.message.chat.type
        )
        
        user_data = {
            "user_id": user_id,
            "username": getattr(update.message.from_user, 'username', ''),
            "first_name": getattr(update.message.from_user, 'first_name', ''),
            "last_name": getattr(update.message.from_user, 'last_name', ''),
            "is_bot": update.message.from_user.is_bot
        }
        
        await db_manager.get_or_create_user(user_data)
        
        # Send welcome message (no personal info)
        welcome_text = (
            "🛡️ **FlushBot Security System Activated**\n\n"
            "This chat is now protected by advanced AI-powered content moderation.\n\n"
            "**Features:**\n"
            "• Real-time message analysis\n"
            "• Multi-level security enforcement\n"
            "• Privacy-focused moderation\n"
            "• Intelligent threat detection\n\n"
            "Type /help for available commands."
        )
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        
        logger.info(f"Bot started in chat {chat_id} by user {user_id}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id
        
        # Check if user is admin or sudo
        is_admin = await self._is_admin(user_id, chat_id)
        is_sudo = user_id == settings.sudo_user_id
        
        help_text = "🔍 **FlushBot Commands**\n\n"
        
        # User commands
        help_text += "**User Commands:**\n"
        help_text += "`/start` - Initialize bot\n"
        help_text += "`/help` - Show this help\n"
        help_text += "`/status` - Check security status\n\n"
        
        # Admin commands
        if is_admin:
            help_text += "**Admin Commands:**\n"
            help_text += "`/security <level>` - Set security mode (low/medium/extreme)\n"
            help_text += "`/ban <reply>` - Ban user (reply to message)\n"
            help_text += "`/unban <user_id>` - Unban user\n"
            help_text += "`/mute <reply> <duration>` - Mute user (reply to message)\n"
            help_text += "`/stats` - Show moderation statistics\n"
            help_text += "`/export` - Export chat data\n\n"
        
        # Sudo commands
        if is_sudo:
            help_text += "**Sudo Commands:**\n"
            help_text += "`/sudo <command>` - Execute with elevated privileges\n"
            help_text += "`/override <action>` - Override security restrictions\n"
            help_text += "`/leave` - Leave current chat\n"
            help_text += "`/debug` - Show debug information\n"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        
        chat_id = update.message.chat.id
        
        # Get chat settings
        chat_settings = await db_manager.get_chat_settings(chat_id)
        
        if not chat_settings:
            await update.message.reply_text("❌ Chat not initialized. Use /start first.")
            return
        
        # Get statistics
        stats = await db_manager.get_chat_statistics(chat_id, days=7)
        
        # Get AI analyzer status
        ai_stats = ai_analyzer.get_statistics()
        
        # Get current security mode and deletion policy
        from config.security_rules import SECURITY_MODE_RULES, SecurityMode
        security_mode = SecurityMode(chat_settings.get('security_mode', 'medium'))
        mode_config = SECURITY_MODE_RULES[security_mode]
        
        status_text = f"📊 **Security Status**\n\n"
        status_text += f"**Security Mode:** {security_mode.value.upper()}\n"
        status_text += f"**Description:** {mode_config['description']}\n\n"
        
        status_text += f"**🗑️ Auto-Delete Categories:**\n"
        for category in mode_config['delete_categories']:
            status_text += f"• {category.replace('_', ' ').title()}\n"
        status_text += "\n"
        
        status_text += f"**⚙️ System Status:**\n"
        status_text += f"• Instant Detection: ✅\n"
        status_text += f"• Delayed Sweep (30min): ✅\n"
        status_text += f"• Bot Detection: {'✅' if chat_settings.get('bot_detection_enabled', True) else '❌'}\n\n"
        
        status_text += f"**7-Day Statistics:**\n"
        status_text += f"• Messages Processed: {stats['total_messages']}\n"
        status_text += f"• Violations Detected: {stats['total_violations']}\n"
        status_text += f"• Actions Taken: {stats['total_actions']}\n"
        status_text += f"• Violation Rate: {stats['violation_rate']:.2%}\n\n"
        
        status_text += f"**AI System:**\n"
        status_text += f"• Daily Quota: {ai_stats['quota_status']['daily_used']}/{ai_stats['quota_status']['daily_limit']}\n"
        status_text += f"• API Available: {'✅' if ai_stats['api_available'] else '❌'}\n"
        status_text += f"• Fallback Active: {'⚠️' if ai_stats['fallback_active'] else '✅'}\n"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def security_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /security command (admin only)"""
        
        if not await self._check_admin_permission(update):
            return
        
        if len(context.args) == 0:
            # Show current security configuration
            from config.security_rules import SECURITY_MODE_RULES
            
            help_text = "🛡️ **Security Mode Configuration**\n\n"
            
            for mode, config in SECURITY_MODE_RULES.items():
                help_text += f"**{mode.value.upper()}:**\n"
                help_text += f"{config['description']}\n"
                help_text += f"Deletes: {', '.join(config['delete_categories'][:3])}{'...' if len(config['delete_categories']) > 3 else ''}\n\n"
            
            help_text += "Usage: `/security <level>`\n"
            help_text += "Available levels: low, medium, extreme"
            
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        new_level = context.args[0].lower()
        
        if new_level not in SECURITY_LEVELS:
            await update.message.reply_text(
                f"❌ Invalid security level. Available: {', '.join(SECURITY_LEVELS.keys())}"
            )
            return
        
        chat_id = update.message.chat.id
        
        # Update security level
        success = await db_manager.update_chat_security_level(chat_id, new_level)
        
        if success:
            # Clear cache
            await message_cache.cache.delete(f"chat:{chat_id}")
            
            level_info = SECURITY_LEVELS[new_level]
            
            response_text = (
                f"🔒 **Security Level Updated**\n\n"
                f"**New Level:** {level_info['name']}\n"
                f"**Description:** {level_info['description']}\n"
                f"**Actions:** {', '.join(level_info['actions'])}"
            )
            
            await update.message.reply_text(response_text, parse_mode='Markdown')
            
            logger.info(f"Security level changed to {new_level} in chat {chat_id}")
        else:
            await update.message.reply_text("❌ Failed to update security level.")
    
    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ban command (admin only)"""
        
        if not await self._check_admin_permission(update):
            return
        
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Reply to a message to ban the user.")
            return
        
        target_user_id = update.message.reply_to_message.from_user.id
        admin_id = update.message.from_user.id
        chat_id = update.message.chat.id
        
        # Check if trying to ban admin or sudo
        if await self._is_admin(target_user_id, chat_id) or target_user_id == settings.sudo_user_id:
            await update.message.reply_text("❌ Cannot ban administrators or sudo users.")
            return
        
        reason = " ".join(context.args) if context.args else "Manual ban by admin"
        
        # Execute ban
        security_enforcer = get_security_enforcer()
        if not security_enforcer:
            await update.message.reply_text("❌ Security system not available.")
            return
            
        result = await security_enforcer.manual_ban_user(
            chat_id, target_user_id, admin_id, reason
        )
        
        if result["success"]:
            await update.message.reply_text("✅ User banned successfully.")
        else:
            await update.message.reply_text(f"❌ Ban failed: {result['error']}")
    
    async def unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unban command (admin only)"""
        
        if not await self._check_admin_permission(update):
            return
        
        if len(context.args) != 1:
            await update.message.reply_text("Usage: `/unban <user_id>`", parse_mode='Markdown')
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
            return
        
        admin_id = update.message.from_user.id
        chat_id = update.message.chat.id
        
        # Execute unban
        security_enforcer = get_security_enforcer()
        if not security_enforcer:
            await update.message.reply_text("❌ Security system not available.")
            return
            
        result = await security_enforcer.manual_unban_user(chat_id, target_user_id, admin_id)
        
        if result["success"]:
            await update.message.reply_text("✅ User unbanned successfully.")
        else:
            await update.message.reply_text(f"❌ Unban failed: {result['error']}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command (admin only)"""
        
        if not await self._check_admin_permission(update):
            return
        
        chat_id = update.message.chat.id
        
        # Get detailed statistics
        stats = await db_manager.get_chat_statistics(chat_id, days=30)
        
        stats_text = f"📈 **Detailed Statistics (30 days)**\n\n"
        stats_text += f"**Messages:** {stats['total_messages']}\n"
        stats_text += f"**Violations:** {stats['total_violations']}\n"
        stats_text += f"**Actions:** {stats['total_actions']}\n"
        stats_text += f"**Violation Rate:** {stats['violation_rate']:.2%}\n\n"
        
        # Get API usage stats
        api_stats = await db_manager.get_api_usage_stats()
        
        stats_text += f"**AI Usage (7 days):**\n"
        stats_text += f"• Total Requests: {api_stats['total_requests']}\n"
        stats_text += f"• Success Rate: {api_stats['avg_success_rate']:.1%}\n"
        stats_text += f"• Total Cost: ${api_stats['total_cost']:.4f}\n"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command (admin only)"""
        
        if not await self._check_admin_permission(update):
            return
        
        chat_id = update.message.chat.id
        
        # Parse arguments for export options
        export_format = "csv"
        days = 30
        
        if context.args:
            if len(context.args) >= 1:
                format_arg = context.args[0].lower()
                if format_arg in ["csv", "json", "parquet"]:
                    export_format = format_arg
            
            if len(context.args) >= 2:
                try:
                    days = int(context.args[1])
                    days = max(1, min(days, 365))  # Limit between 1-365 days
                except ValueError:
                    pass
        
        await update.message.reply_text(f"📁 Starting export... (Format: {export_format}, Days: {days})")
        
        try:
            # Export chat data
            filepath = await data_exporter.export_chat_messages(
                chat_id=chat_id,
                format=export_format
            )
            
            success_text = (
                f"✅ **Export Complete**\n\n"
                f"**Format:** {export_format.upper()}\n"
                f"**File:** `{filepath}`\n"
                f"**Period:** {days} days\n\n"
                f"The file has been saved on the server."
            )
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Export failed: {str(e)}")
            logger.error(f"Export failed for chat {chat_id}: {e}")
    
    async def sudo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sudo command (sudo only)"""
        
        if not await self._check_sudo_permission(update):
            return
        
        if not context.args:
            await update.message.reply_text("Usage: `/sudo <command>`", parse_mode='Markdown')
            return
        
        command = context.args[0].lower()
        
        if command == "leave":
            chat_id = update.message.chat.id
            security_enforcer = get_security_enforcer()
            if not security_enforcer:
                await update.message.reply_text("❌ Security system not available.")
                return
                
            result = await security_enforcer.leave_chat(chat_id)
            
            if result["success"]:
                await update.message.reply_text("👋 Leaving chat...")
            else:
                await update.message.reply_text(f"❌ Failed to leave: {result['error']}")
        
        elif command == "debug":
            await self._debug_info(update, context)
        
        else:
            await update.message.reply_text(f"❌ Unknown sudo command: {command}")
    
    async def _debug_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show debug information"""
        
        chat_id = update.message.chat.id
        
        # Get various system stats
        ai_stats = ai_analyzer.get_statistics()
        chat_settings = await db_manager.get_chat_settings(chat_id)
        
        debug_text = f"🔧 **Debug Information**\n\n"
        debug_text += f"**Chat ID:** {chat_id}\n"
        debug_text += f"**Security Level:** {chat_settings.get('security_level', 'unknown') if chat_settings else 'none'}\n\n"
        
        debug_text += f"**AI System:**\n"
        debug_text += f"• Grok-4 Available: {'✅' if not ai_stats['fallback_active'] else '❌'}\n"
        debug_text += f"• Gemini Fallback: {'✅' if ai_stats['fallback_active'] else '⏸️'}\n"
        debug_text += f"• Daily Quota: {ai_stats['quota_status']['daily_used']}/{ai_stats['quota_status']['daily_limit']}\n\n"
        
        debug_text += f"**Environment:**\n"
        debug_text += f"• Debug Mode: {'✅' if settings.debug else '❌'}\n"
        debug_text += f"• Batch Processing: {'✅' if settings.enable_batch_processing else '❌'}\n"
        debug_text += f"• Redis Connected: {'✅' if message_cache.cache.connected else '❌'}\n"
        
        await update.message.reply_text(debug_text, parse_mode='Markdown')
    
    async def _check_admin_permission(self, update: Update) -> bool:
        """Check if user has admin permission"""
        
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id
        
        # Sudo user always has permission
        if user_id == settings.sudo_user_id:
            return True
        
        # Check if user is chat admin
        if await self._is_admin(user_id, chat_id):
            return True
        
        await update.message.reply_text("❌ This command requires administrator privileges.")
        return False
    
    async def _check_sudo_permission(self, update: Update) -> bool:
        """Check if user has sudo permission"""
        
        user_id = update.message.from_user.id
        
        if user_id == settings.sudo_user_id:
            return True
        
        await update.message.reply_text("❌ This command requires sudo privileges.")
        return False
    
    async def _is_admin(self, user_id: int, chat_id: int) -> bool:
        """Check if user is chat administrator"""
        
        if admin_manager:
            return await admin_manager.is_admin(user_id, chat_id)
        
        # Fallback to direct API call
        try:
            security_enforcer = get_security_enforcer()
            if security_enforcer and security_enforcer.bot:
                member = await security_enforcer.bot.get_chat_member(chat_id, user_id)
                return member.status in ['administrator', 'creator']
            else:
                return False
        except TelegramError:
            return False


# Global command handler
command_handler = CommandHandler()


# Handler functions for telegram-python-bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.start_command(update, context)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.help_command(update, context)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.status_command(update, context)

async def security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.security_command(update, context)

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.ban_command(update, context)

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.unban_command(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.stats_command(update, context)

async def sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.sudo_command(update, context)

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await command_handler.export_command(update, context)