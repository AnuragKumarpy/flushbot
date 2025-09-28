# 🚀 FlushBot Quick Start Guide

## Prerequisites
- Python 3.9 or higher
- Telegram Bot Token (from @BotFather)
- Your Telegram User ID (sudo privileges)

## 📦 Installation

### Option 1: Automatic Installation (Recommended)
```bash
# Clone the repository
git clone <your-repo-url>
cd flushbot

# Run the installation script
./install.sh
```

### Option 2: Manual Installation
```bash
# Install dependencies
pip3 install -r requirements.txt

# Copy environment template
cp .env.example .env

# Create necessary directories
mkdir -p logs data/exports
```

## ⚙️ Configuration

1. **Edit the .env file** with your settings:
```bash
# Required settings
TELEGRAM_BOT_TOKEN=your_bot_token_here
SUDO_USER_ID=your_user_id_here

# AI API keys (already provided)
OPENROUTER_GROK_KEY=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
OPENROUTER_GEMINI_KEY=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

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379/0
```

2. **Get your Telegram User ID**:
   - Message @userinfobot on Telegram
   - Or use @RawDataBot and look for "from" -> "id"

3. **Create your Telegram bot**:
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Copy the token to your .env file

## 🗄️ Database Setup

```bash
# Initialize database tables
python3 setup_db.py
```

## 🚀 Running the Bot

```bash
# Start the bot
python3 main.py
```

## 📱 Bot Usage

### Adding to Groups
1. Add your bot to a Telegram group
2. Make the bot an administrator with these permissions:
   - Delete messages
   - Ban users
   - Restrict members

### Commands
- `/start` - Initialize bot in chat
- `/help` - Show available commands  
- `/status` - Check security status
- `/security <level>` - Set security level (admin)
- `/stats` - Show statistics (admin)
- `/export` - Export chat data (admin)

### Security Levels
- **Low**: Warning only mode
- **Medium**: Progressive restrictions (default)
- **Extreme**: Zero tolerance - immediate bans

## 🛡️ Features

### ✅ Active Features
- **Multi-level security** (Low/Medium/Extreme)
- **AI content analysis** (Grok-4 + Gemini 2.0 fallback)
- **Real-time moderation** with configurable actions
- **Privacy protection** (no usernames in public messages)
- **Bot detection** and management
- **Redis caching** for performance
- **Batch processing** for historical data
- **CSV/Parquet export** capabilities
- **Admin-per-chat** permissions (no global admin chat required)

### 🔄 Coming Soon
- Image content analysis
- Multi-language support
- Advanced machine learning models
- Mobile management app

## 🚨 Troubleshooting

### Common Issues

1. **"Redis connection failed"**
   - Install Redis: `sudo apt-get install redis-server` (Ubuntu)
   - Or disable Redis in .env: `REDIS_URL=`

2. **"Database initialization failed"** 
   - Check database permissions
   - For SQLite: ensure directory is writable
   - For PostgreSQL: check connection string

3. **"Bot permissions error"**
   - Make bot admin in the group
   - Grant "Delete messages" and "Ban users" permissions

4. **"API quota exceeded"**
   - Check your OpenRouter usage
   - Bot will fallback to rule-based analysis

### Getting Help

1. Check logs in `logs/flushbot.log`
2. Use `/debug` command (sudo only) for system status
3. Review the full documentation in `DOCUMENTATION.md`

## 📊 Monitoring

### Admin Commands
- `/stats` - View detailed statistics
- `/export csv 30` - Export 30 days of data as CSV
- `/security extreme` - Set to maximum security

### Sudo Commands  
- `/sudo debug` - System diagnostics
- `/sudo leave` - Leave current chat

## 🔒 Security Notes

- **Sudo user** bypasses all restrictions
- **Chat admins** can configure security settings per chat
- **No global admin chat** required - each group is independent
- **Privacy focused** - no usernames exposed in public messages
- **AI failover** - rule-based analysis if APIs fail

## 📈 Performance Tips

1. **Enable Redis** for better performance
2. **Batch processing** reduces API usage
3. **Appropriate security levels** prevent false positives
4. **Regular exports** help track trends

---

**Need help?** Check `DOCUMENTATION.md` for detailed information or create an issue on GitHub.