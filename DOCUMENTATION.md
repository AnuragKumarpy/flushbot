# FlushBot - Telegram Security Bot

## 🔒 Overview

FlushBot is an advanced Telegram security bot designed to monitor and moderate chat messages in real-time. It uses AI-powered content analysis to detect and prevent harmful content including drug sales, illegal activities, child abuse, and other violations of Telegram's policies.

## 🎯 Key Features

### Security Modes
- **Extreme Mode**: Zero tolerance - immediate ban for any detected violation
- **Medium Mode**: Warning system with escalation to temporary restrictions
- **Low Mode**: Warning only with logging for review

### Content Detection
- Drug sales and illegal substances
- Child abuse and exploitation (CP)
- Weapon sales and trafficking
- Hate speech and harassment
- Spam and scam messages
- Bot message detection and management

### AI Integration
- **Primary API**: Grok-4 via OpenRouter (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)
- **Fallback API**: Gemini 2.0 via OpenRouter (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)
- Quota optimization with Redis caching
- Batch processing for historical message analysis

### Data Storage & Caching
- **Database**: SQLite/PostgreSQL for persistent storage
- **Redis**: Message caching and rate limiting
- **CSV/Parquet**: Historical message batch processing
- **Message History**: Efficient retrieval and analysis

### Administrative Features
- **Sudo Override**: Admin bypass for all restrictions
- **Silent Operations**: Non-intrusive moderation
- **Privacy Protection**: No usernames/names in public messages
- **Cross-Bot Management**: Detection and removal of other bots

## 🏗️ Architecture

### Core Components

1. **Message Processor**
   - Real-time message analysis
   - Content classification
   - Action determination based on security level

2. **AI Content Analyzer**
   - OpenRouter API integration
   - Fallback mechanism
   - Quota management
   - Batch processing capabilities

3. **Database Layer**
   - User management
   - Message logging
   - Security level configuration
   - Historical data storage

4. **Redis Cache Manager**
   - Message caching
   - Rate limiting
   - Temporary data storage
   - Performance optimization

5. **Admin Panel**
   - Security level configuration
   - User management
   - Statistics and reporting
   - Manual override controls

## 📊 Security Levels

### Extreme Mode
- **Actions**: Immediate ban, message deletion
- **Triggers**: Any policy violation detected
- **Appeals**: Admin review required
- **Logging**: Full detailed logs

### Medium Mode
- **Actions**: Warning → Mute → Temporary ban → Permanent ban
- **Triggers**: Escalation based on violation count
- **Appeals**: Automatic after time period
- **Logging**: Moderate detail logs

### Low Mode
- **Actions**: Warning messages only
- **Triggers**: Notification to admins
- **Appeals**: No restrictions applied
- **Logging**: Basic violation logs

## 🔧 Configuration

### Environment Variables
```env
# Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
SUDO_USER_ID=your_admin_user_id

# AI API Keys
OPENROUTER_GROK_KEY=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
OPENROUTER_GEMINI_KEY=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

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/flushbot
REDIS_URL=redis://localhost:6379

# API Limits
DAILY_API_QUOTA=1000
BATCH_SIZE=50
CACHE_TTL=3600
```

### Security Policies

#### Violation Categories
1. **Illegal Substances**: Drug sales, distribution
2. **Child Exploitation**: CP, grooming, abuse
3. **Weapons**: Sales, trafficking
4. **Hate Speech**: Discrimination, harassment
5. **Fraud**: Scams, phishing
6. **Spam**: Excessive messaging, ads

#### Detection Methods
- **Keyword Analysis**: Pattern matching
- **Context Analysis**: AI-powered understanding
- **Behavioral Analysis**: User activity patterns
- **Image Analysis**: (Future implementation)

## 🚀 Installation & Setup

### Prerequisites
- Python 3.9+
- Redis Server
- PostgreSQL (optional)
- Telegram Bot Token
- OpenRouter API Keys

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd flushbot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python setup_db.py

# Run bot
python main.py
```

## 📱 Bot Commands

### User Commands
- `/start` - Initialize bot for chat
- `/help` - Show available commands
- `/status` - Check security level

### Admin Commands
- `/security <level>` - Set security mode (extreme/medium/low)
- `/ban <user_id>` - Ban user
- `/unban <user_id>` - Unban user
- `/mute <user_id> <duration>` - Mute user
- `/stats` - Show moderation statistics
- `/export` - Export chat data
- `/leave` - Leave current chat (sudo only)

### Sudo Commands
- `/sudo <command>` - Execute with admin privileges
- `/override <action>` - Bypass security restrictions
- `/debug` - Show debug information

## 🔍 Monitoring & Analytics

### Real-time Metrics
- Messages processed per minute
- Violations detected
- Actions taken
- API usage statistics

### Historical Analysis
- Violation trends
- User behavior patterns
- Security effectiveness
- Performance metrics

### Reporting
- Daily/Weekly/Monthly reports
- Violation summaries
- User activity reports
- API usage reports

## 🛡️ Privacy & Security

### Data Protection
- No storage of personal information
- Encrypted message logs
- Automatic data purging
- GDPR compliance

### Bot Permissions Required
- Read messages
- Delete messages
- Ban/restrict users
- Pin messages (optional)
- Manage chat (admin features)

## 🔄 Future Enhancements

### Phase 2 Features
- Image content analysis
- Video content detection
- Voice message analysis
- Multi-language support

### Phase 3 Features
- Machine learning model training
- Advanced behavioral analysis
- Integration with external threat feeds
- Mobile app for management

## 📞 Support & Maintenance

### Error Handling
- Graceful API fallback
- Automatic retry mechanisms
- Error logging and alerting
- Performance monitoring

### Updates & Patches
- Automatic security updates
- Policy rule updates
- API compatibility maintenance
- Performance optimizations

## 📄 License & Legal

### Compliance
- Telegram Terms of Service
- OpenRouter Usage Policy
- Data Protection Regulations
- Content Moderation Guidelines

### Disclaimer
This bot is designed for legitimate security purposes only. Users are responsible for ensuring compliance with local laws and regulations.