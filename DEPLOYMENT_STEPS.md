# 🚀 FlushBot Azure Deployment - Step-by-Step Instructions

## 📋 Complete Production Deployment Checklist

### Phase 1: Prerequisites Setup ✅

#### 1.1 Azure Account Preparation
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Set your subscription (if you have multiple)
az account set --subscription "Your-Subscription-Name"
```

#### 1.2 Clone Production Repository
```bash
git clone https://github.com/AnuragKumarpy/flushbot.git
cd flushbot
```

#### 1.3 Get Required API Keys
- **Telegram Bot Token**: Message @BotFather on Telegram
- **OpenRouter Grok Key**: Register at https://openrouter.ai/
- **OpenRouter Gemini Key**: Get from OpenRouter dashboard
- **Your Telegram User ID**: Message @userinfobot

---

### Phase 2: Azure Infrastructure Setup 🏗️

#### 2.1 Create Resource Group
```bash
az group create --name flushbot-rg --location "East US"
```

#### 2.2 Create PostgreSQL Database
```bash
# Create PostgreSQL server
az postgres flexible-server create \
  --resource-group flushbot-rg \
  --name flushbot-db-$(date +%s) \
  --location "East US" \
  --admin-user flushbot \
  --admin-password "SecurePass123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --public-access 0.0.0.0 \
  --storage-size 32 \
  --version 15

# Create database
az postgres flexible-server db create \
  --resource-group flushbot-rg \
  --server-name flushbot-db-$(date +%s) \
  --database-name flushbot
```

#### 2.3 Create Redis Cache
```bash
az redis create \
  --resource-group flushbot-rg \
  --name flushbot-redis-$(date +%s) \
  --location "East US" \
  --sku Basic \
  --vm-size C0 \
  --enable-non-ssl-port
```

#### 2.4 Get Connection Strings
```bash
# Get PostgreSQL connection string
az postgres flexible-server show-connection-string \
  --server-name flushbot-db-$(date +%s) \
  --database-name flushbot \
  --admin-user flushbot

# Get Redis connection details
az redis show --resource-group flushbot-rg --name flushbot-redis-$(date +%s)
az redis list-keys --resource-group flushbot-rg --name flushbot-redis-$(date +%s)
```

---

### Phase 3: Environment Configuration 🔧

#### 3.1 Create Production Environment File
```bash
cp .env.production .env
```

#### 3.2 Edit Environment File
```bash
nano .env
```

**Fill in these values:**
```bash
# Bot Configuration
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
BOT_USERNAME=your_bot_username
SUDO_USER_ID=YOUR_TELEGRAM_USER_ID

# AI API Keys
OPENROUTER_GROK_KEY=sk-or-v1-your-grok-key-here
OPENROUTER_GEMINI_KEY=sk-or-v1-your-gemini-key-here

# Database (replace with your actual values)
DATABASE_URL=postgresql://flushbot:SecurePass123!@flushbot-db-XXXXX.postgres.database.azure.com:5432/flushbot

# Redis (replace with your actual values)
REDIS_URL=redis://flushbot-redis-XXXXX.redis.cache.windows.net:6380
REDIS_PASSWORD=your_redis_primary_access_key
```

---

### Phase 4: Container Deployment 🐳

#### Option A: Automated PowerShell Deployment (Recommended)
```powershell
./azure-deploy-aci.ps1 -ResourceGroupName "flushbot-rg" `
                       -ContainerName "flushbot-app" `
                       -Location "East US" `
                       -TelegramBotToken "YOUR_BOT_TOKEN" `
                       -SudoUserId "YOUR_USER_ID" `
                       -DatabaseUrl "postgresql://..." `
                       -RedisUrl "redis://..." `
                       -GroKApiKey "YOUR_GROK_KEY" `
                       -GeminiApiKey "YOUR_GEMINI_KEY"
```

#### Option B: Manual Azure Container Instance
```bash
# Create Container Registry
az acr create --resource-group flushbot-rg --name flushbotacr$(date +%s) --sku Basic --admin-enabled true

# Build and push image
az acr build --registry flushbotacr$(date +%s) --image flushbot:latest --file Dockerfile.production .

# Deploy container
az container create \
  --resource-group flushbot-rg \
  --name flushbot-app \
  --image flushbotacr$(date +%s).azurecr.io/flushbot:latest \
  --registry-login-server flushbotacr$(date +%s).azurecr.io \
  --cpu 1 \
  --memory 2 \
  --restart-policy Always \
  --environment-variables \
    TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
    SUDO_USER_ID="$SUDO_USER_ID" \
    DATABASE_URL="$DATABASE_URL" \
    REDIS_URL="$REDIS_URL" \
    OPENROUTER_GROK_KEY="$OPENROUTER_GROK_KEY" \
    OPENROUTER_GEMINI_KEY="$OPENROUTER_GEMINI_KEY" \
    ENVIRONMENT=production \
    DEBUG=false \
  --location "East US"
```

---

### Phase 5: Verification & Testing 🧪

#### 5.1 Check Deployment Status
```bash
# Container status
az container show --resource-group flushbot-rg --name flushbot-app \
  --query "{Status:instanceView.state,RestartCount:instanceView.restartCount}" --output table

# View logs
az container logs --resource-group flushbot-rg --name flushbot-app

# Follow logs in real-time
az container logs --resource-group flushbot-rg --name flushbot-app --follow
```

#### 5.2 Test Bot Functionality
1. **Add bot to your test group**
2. **Set bot as administrator with delete message permissions**
3. **Test commands:**
   ```
   /start
   /help
   /status
   /set_security_mode medium
   ```
4. **Test violation detection** (send test messages)

#### 5.3 Monitor Health
```bash
# Check health endpoint (if exposed)
curl http://$(az container show --resource-group flushbot-rg --name flushbot-app --query "ipAddress.ip" -o tsv):8000/health

# Azure Monitor integration
az monitor activity-log list --resource-group flushbot-rg
```

---

### Phase 6: Production Configuration 🎛️

#### 6.1 Set Security Groups
```bash
# In your Telegram group, send:
/set_security_mode medium    # Recommended for most groups
/admin_status               # Check admin configuration
```

#### 6.2 Configure Monitoring
```bash
# Set up log analytics workspace
az monitor log-analytics workspace create \
  --resource-group flushbot-rg \
  --workspace-name flushbot-logs

# Enable container monitoring
az container update \
  --resource-group flushbot-rg \
  --name flushbot-app \
  --log-analytics-workspace $(az monitor log-analytics workspace show --resource-group flushbot-rg --workspace-name flushbot-logs --query "customerId" -o tsv)
```

---

### Phase 7: Maintenance & Scaling 📈

#### 7.1 Update Deployment
```bash
# Update container with new environment variables
az container update \
  --resource-group flushbot-rg \
  --name flushbot-app \
  --environment-variables NEW_VAR=value

# Restart container
az container restart --resource-group flushbot-rg --name flushbot-app
```

#### 7.2 Scale Resources
```bash
# Vertical scaling
az container update \
  --resource-group flushbot-rg \
  --name flushbot-app \
  --cpu 2 \
  --memory 4

# Database scaling
az postgres flexible-server update \
  --resource-group flushbot-rg \
  --name flushbot-db-XXXXX \
  --sku-name Standard_B2s
```

---

## 🚨 Troubleshooting Guide

### Common Issues & Solutions

#### Container Won't Start
```bash
# Check detailed logs
az container logs --resource-group flushbot-rg --name flushbot-app

# Check events
az container show --resource-group flushbot-rg --name flushbot-app \
  --query "instanceView.events" --output table

# Restart container
az container restart --resource-group flushbot-rg --name flushbot-app
```

#### Database Connection Issues
```bash
# Test connectivity
az postgres flexible-server connect \
  --name flushbot-db-XXXXX \
  --admin-user flushbot \
  --database-name flushbot

# Check firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group flushbot-rg \
  --name flushbot-db-XXXXX
```

#### Bot Not Responding
1. Verify bot token in environment
2. Check bot permissions in Telegram group
3. Monitor API rate limits
4. Review violation logs

---

## 🔐 Security Checklist

- ✅ Environment variables secured
- ✅ Database firewall configured
- ✅ Redis access restrictions enabled
- ✅ Container running as non-root user
- ✅ SSL/TLS encryption enabled
- ✅ Backup strategy implemented
- ✅ Monitoring and alerting active

---

## 💰 Cost Optimization Tips

1. **Right-size resources** based on actual usage
2. **Use burstable database tiers** for variable workloads
3. **Enable auto-shutdown** for development environments
4. **Monitor costs** with Azure Cost Management
5. **Set up budget alerts** to avoid surprises

---

## 🎯 Success Criteria

Your FlushBot deployment is successful when:

- ✅ Container shows "Running" status
- ✅ Bot responds to /start command
- ✅ Database connectivity confirmed
- ✅ Redis cache operational
- ✅ Violation detection working
- ✅ Logs show normal operation
- ✅ Health checks passing

---

## 📞 Support & Next Steps

### Immediate Actions After Deployment
1. **Join bot to production groups**
2. **Configure security modes per group**
3. **Set up monitoring alerts**
4. **Document group-specific settings**
5. **Train moderators on bot commands**

### Ongoing Maintenance
- Monitor logs weekly
- Update API keys as needed
- Review violation patterns monthly
- Scale resources based on usage
- Keep security rules updated

**🎉 Congratulations! Your FlushBot is now running securely on Azure!**

For ongoing support, monitor the Azure portal and check logs regularly. The bot will now automatically protect your Telegram groups 24/7.

---

*FlushBot - Enterprise Telegram Security Made Easy* 🛡️