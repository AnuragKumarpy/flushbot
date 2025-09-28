# FlushBot Azure Deployment Guide 🚀

Complete step-by-step guide for deploying FlushBot to Azure Container Instances with PostgreSQL and Redis.

## 📋 Prerequisites

### 1. Azure Account & CLI
- Azure subscription with sufficient credits
- [Azure CLI installed](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- Login: `az login`

### 2. Required Services
- **Telegram Bot Token** (from @BotFather)
- **OpenRouter API Keys** (for AI analysis)
- **Azure PostgreSQL Database**
- **Azure Redis Cache**

---

## 🏗️ Step 1: Create Azure Resources

### Create Resource Group
```bash
az group create --name flushbot-rg --location "East US"
```

### Create PostgreSQL Database
```bash
# Create PostgreSQL server
az postgres flexible-server create \
  --resource-group flushbot-rg \
  --name flushbot-db \
  --location "East US" \
  --admin-user flushbot \
  --admin-password "YourSecurePassword123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --public-access 0.0.0.0 \
  --storage-size 32 \
  --version 15

# Create database
az postgres flexible-server db create \
  --resource-group flushbot-rg \
  --server-name flushbot-db \
  --database-name flushbot
```

### Create Redis Cache
```bash
az redis create \
  --resource-group flushbot-rg \
  --name flushbot-redis \
  --location "East US" \
  --sku Basic \
  --vm-size C0 \
  --enable-non-ssl-port
```

---

## 🔧 Step 2: Configure Environment

### Create Production Environment File
```bash
cp .env.production .env
```

### Edit `.env` with your values:
```bash
# Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:YOUR_BOT_TOKEN_HERE
BOT_USERNAME=your_bot_username  
SUDO_USER_ID=123456789

# AI API Keys
OPENROUTER_GROK_KEY=sk-or-v1-your-grok-key
OPENROUTER_GEMINI_KEY=sk-or-v1-your-gemini-key

# Database (get from Azure PostgreSQL)
DATABASE_URL=postgresql://flushbot:YourSecurePassword123!@flushbot-db.postgres.database.azure.com:5432/flushbot

# Redis (get from Azure Redis)
REDIS_URL=redis://flushbot-redis.redis.cache.windows.net:6380
REDIS_PASSWORD=your_redis_access_key
```

---

## 🐳 Step 3: Docker Deployment Options

### Option A: Azure Container Instances (Recommended)

#### Using PowerShell Script:
```powershell
./azure-deploy-aci.ps1 -ResourceGroupName "flushbot-rg" `
                       -ContainerName "flushbot-app" `
                       -Location "East US" `
                       -TelegramBotToken "YOUR_TOKEN" `
                       -SudoUserId "YOUR_USER_ID" `
                       -DatabaseUrl "YOUR_DB_URL" `
                       -RedisUrl "YOUR_REDIS_URL" `
                       -GroKApiKey "YOUR_GROK_KEY" `
                       -GeminiApiKey "YOUR_GEMINI_KEY"
```

#### Manual Azure CLI:
```bash
# Build and deploy container
az container create \
  --resource-group flushbot-rg \
  --name flushbot-app \
  --image your-registry/flushbot:latest \
  --cpu 1 \
  --memory 2 \
  --restart-policy Always \
  --environment-variables \
    TELEGRAM_BOT_TOKEN="YOUR_TOKEN" \
    DATABASE_URL="YOUR_DB_URL" \
    REDIS_URL="YOUR_REDIS_URL" \
  --location "East US"
```

### Option B: Azure Container Apps (Advanced)
```bash
# Create Container Apps environment
az containerapp env create \
  --name flushbot-env \
  --resource-group flushbot-rg \
  --location "East US"

# Deploy container app
az containerapp create \
  --name flushbot-app \
  --resource-group flushbot-rg \
  --environment flushbot-env \
  --image your-registry/flushbot:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    TELEGRAM_BOT_TOKEN="YOUR_TOKEN" \
    DATABASE_URL="YOUR_DB_URL" \
    REDIS_URL="YOUR_REDIS_URL"
```

---

## 📊 Step 4: Monitoring & Management

### Check Deployment Status
```bash
# Container status
az container show --resource-group flushbot-rg --name flushbot-app \
  --query "{Status:instanceView.state,IP:ipAddress.ip}" --output table

# View logs  
az container logs --resource-group flushbot-rg --name flushbot-app

# Follow logs in real-time
az container logs --resource-group flushbot-rg --name flushbot-app --follow
```

### Health Monitoring
- Health check endpoint: `http://container-ip:8000/health`
- Built-in Docker health checks
- Azure Monitor integration available

---

## 🔒 Step 5: Security & Best Practices

### Environment Security
- Store sensitive values in Azure Key Vault
- Use managed identities for Azure services
- Enable Azure Defender for Containers

### Database Security
- Enable SSL connections
- Configure firewall rules
- Regular backups enabled

### Redis Security
- SSL/TLS encryption enabled
- Access keys rotated regularly
- Network access restrictions

---

## 🎛️ Step 6: Scaling & Performance

### Vertical Scaling
```bash
# Increase container resources
az container update \
  --resource-group flushbot-rg \
  --name flushbot-app \
  --cpu 2 \
  --memory 4
```

### Database Scaling
```bash
# Scale PostgreSQL
az postgres flexible-server update \
  --resource-group flushbot-rg \
  --name flushbot-db \
  --sku-name Standard_B2s
```

---

## 🚨 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check logs
az container logs --resource-group flushbot-rg --name flushbot-app

# Check events  
az container show --resource-group flushbot-rg --name flushbot-app \
  --query "instanceView.events" --output table
```

#### Database Connection Issues
- Verify firewall rules allow Azure services
- Check connection string format
- Test connectivity from container

#### Bot Not Responding
- Verify Telegram bot token
- Check webhook settings
- Monitor API rate limits

---

## 💰 Cost Optimization

### Container Instances
- Use minimum required CPU/memory
- Consider Azure Container Apps for auto-scaling
- Monitor usage with Azure Cost Management

### Database & Redis
- Right-size based on usage
- Use burstable tiers for development
- Enable auto-pause for dev environments

---

## 📋 Management Commands

```bash
# Restart container
az container restart --resource-group flushbot-rg --name flushbot-app

# Update container
az container update --resource-group flushbot-rg --name flushbot-app \
  --environment-variables NEW_VAR=value

# Delete deployment
az container delete --resource-group flushbot-rg --name flushbot-app --yes

# Clean up all resources
az group delete --name flushbot-rg --yes --no-wait
```

---

## 📞 Support

For issues and questions:
- Check Azure logs and metrics
- Review FlushBot documentation
- Monitor Telegram API status
- Use Azure Support for infrastructure issues

---

## 🎯 Next Steps

1. **Monitoring**: Set up Azure Monitor alerts
2. **Backup**: Configure automated database backups  
3. **Scaling**: Implement auto-scaling based on load
4. **CI/CD**: Set up GitHub Actions for automated deployment
5. **Security**: Integrate with Azure Security Center

**Your FlushBot is now running securely on Azure! 🎉**