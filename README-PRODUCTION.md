# FlushBot - Advanced Telegram Security System 🛡️

**Professional-grade Telegram bot for automated content moderation and security management**

[![Azure](https://img.shields.io/badge/Azure-Ready-blue.svg)](https://azure.microsoft.com/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![Security](https://img.shields.io/badge/Security-TOS%20Compliant-red.svg)](#security-features)

## 🎯 Overview

FlushBot is an enterprise-grade Telegram security bot designed to automatically detect and remove inappropriate content, spam, and Terms of Service violations. Built with advanced AI integration, multi-language support, and comprehensive logging.

### Key Features

- **🤖 AI-Powered Detection** - OpenRouter Grok-4 & Gemini 2.0 integration
- **⚡ Real-time Moderation** - Instant violation detection and removal
- **🔒 Multi-Level Security** - LOW/MEDIUM/EXTREME security modes
- **🌍 Multi-Language Support** - Detects violations in multiple languages
- **📊 Comprehensive Logging** - Detailed audit trails and analytics
- **☁️ Azure-Ready** - Production deployment on Azure Container Instances

---

## 🚀 Quick Deploy to Azure

### One-Click Azure Deployment

```bash
git clone https://github.com/AnuragKumarpy/flushbot.git
cd flushbot
./azure-deploy-aci.ps1 -ResourceGroupName "flushbot-rg" -ContainerName "flushbot-app"
```

📖 **[Complete Azure Deployment Guide](AZURE_DEPLOYMENT.md)**

---

## 📋 Prerequisites

### Required Services
- **Telegram Bot** (from @BotFather)
- **OpenRouter API Keys** (Grok-4 & Gemini 2.0)
- **Azure PostgreSQL** (or any PostgreSQL database)
- **Azure Redis Cache** (or any Redis instance)

### System Requirements
- Python 3.12+
- Docker (for containerized deployment)
- 1GB+ RAM for production use

---

## ⚡ Security Features

### Content Detection
- **Child Exploitation** - Zero tolerance, immediate deletion
- **Drug/Weapon Selling** - Advanced pattern recognition
- **Spam & Scams** - Sophisticated fraud detection
- **Harassment & Hate Speech** - Multi-language detection
- **Bypass Detection** - Advanced evasion pattern recognition

### Security Modes
- **LOW** - Basic spam and critical violations
- **MEDIUM** - Comprehensive moderation (recommended)
- **EXTREME** - Maximum security, strict enforcement

### Admin Protection
- **Sudo User Exemption** - Bot owner always exempt
- **Admin Deletion** - Can delete admin messages for critical TOS violations
- **Granular Permissions** - Fine-tuned access control

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram API  │───▶│   FlushBot      │───▶│  Azure Services │
│                 │    │                 │    │                 │
│ • Messages      │    │ • AI Analysis   │    │ • PostgreSQL    │
│ • Updates       │    │ • Rule Engine   │    │ • Redis Cache   │
│ • Commands      │    │ • Security      │    │ • Container ACI │
└─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     FlushBot Core Engine                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Instant Detection│ Delayed Sweep   │ Security Enforcement        │
│ • Rule-based    │ • 30-min batch  │ • Message deletion          │
│ • AI analysis   │ • AI validation │ • User restrictions         │
│ • Cache lookup  │ • Pattern match │ • Violation logging         │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

---

## 📊 Configuration

### Environment Variables

```bash
# Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
SUDO_USER_ID=your_telegram_user_id

# AI APIs
OPENROUTER_GROK_KEY=your_grok_api_key
OPENROUTER_GEMINI_KEY=your_gemini_api_key

# Database & Cache
DATABASE_URL=postgresql://user:pass@host:5432/flushbot
REDIS_URL=redis://host:6379/0

# Security Settings
ENABLE_BATCH_PROCESSING=false
DEBUG=false
LOG_LEVEL=INFO
```

### Security Modes

```python
# Set per-group security mode
/set_security_mode medium    # Recommended for most groups
/set_security_mode low       # Basic protection
/set_security_mode extreme   # Maximum security
```

---

## 🔧 Local Development

### Setup
```bash
git clone https://github.com/AnuragKumarpy/flushbot.git
cd flushbot
pip install -r requirements-production.txt
cp .env.production .env
# Edit .env with your configuration
python main.py
```

### Docker Development
```bash
docker-compose -f docker-compose.production.yml up --build
```

---

## 📈 Monitoring & Analytics

### Built-in Health Checks
- Database connectivity monitoring
- Redis cache status
- Telegram API health
- AI service availability

### Logging & Metrics
- Comprehensive violation logging
- Performance metrics
- User activity analytics
- Security event tracking

### Azure Integration
- Container health monitoring
- Auto-scaling capabilities
- Automated backup systems
- Security compliance reporting

---

## 🛡️ Security & Compliance

### Data Protection
- No sensitive data logging
- GDPR-compliant data handling
- Encrypted API communications
- Secure credential management

### Telegram TOS Compliance
- Automatic content moderation
- Terms of Service enforcement
- Spam prevention mechanisms
- User privacy protection

---

## 📞 Support & Documentation

### Documentation
- [Azure Deployment Guide](AZURE_DEPLOYMENT.md)
- [Configuration Reference](DOCUMENTATION.md)
- [Security Best Practices](#security-features)

### Community
- **Issues**: GitHub Issues for bug reports
- **Features**: Feature requests welcome
- **Security**: Responsible disclosure for security issues

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Azure Documentation**: [Microsoft Azure Docs](https://docs.microsoft.com/azure/)
- **Telegram Bot API**: [Core Bot API](https://core.telegram.org/bots/api)
- **OpenRouter**: [AI API Platform](https://openrouter.ai/)
- **Docker Hub**: Container Registry (if applicable)

---

**Built with ❤️ for Telegram community security**

*FlushBot - Professional Telegram Security at Scale*