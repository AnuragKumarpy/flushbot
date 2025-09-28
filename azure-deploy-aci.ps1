# Azure Container Instances Deployment Script for FlushBot
# PowerShell Script for Azure deployment

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$ContainerName,
    
    [Parameter(Mandatory=$true)]
    [string]$Location = "East US",
    
    [Parameter(Mandatory=$true)]
    [string]$TelegramBotToken,
    
    [Parameter(Mandatory=$true)]
    [string]$SudoUserId,
    
    [Parameter(Mandatory=$true)]
    [string]$DatabaseUrl,
    
    [Parameter(Mandatory=$true)]
    [string]$RedisUrl,
    
    [string]$GroKApiKey = "",
    [string]$GeminiApiKey = ""
)

# Azure CLI Commands for FlushBot Deployment

Write-Host "🚀 Starting FlushBot Azure Deployment..." -ForegroundColor Green

# 1. Create Resource Group
Write-Host "📁 Creating Resource Group..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location

# 2. Create Azure Container Registry (optional - for private images)
$AcrName = $ResourceGroupName.ToLower() + "acr"
Write-Host "🏗️ Creating Container Registry..." -ForegroundColor Yellow
az acr create --resource-group $ResourceGroupName --name $AcrName --sku Basic --admin-enabled true

# 3. Build and push image to ACR
Write-Host "🔨 Building and pushing Docker image..." -ForegroundColor Yellow
az acr build --registry $AcrName --image flushbot:latest --file Dockerfile.production .

# 4. Get ACR credentials
$AcrServer = az acr show --name $AcrName --resource-group $ResourceGroupName --query "loginServer" --output tsv
$AcrUsername = az acr credential show --name $AcrName --resource-group $ResourceGroupName --query "username" --output tsv
$AcrPassword = az acr credential show --name $AcrName --resource-group $ResourceGroupName --query "passwords[0].value" --output tsv

# 5. Deploy Container Instance
Write-Host "🚀 Deploying Container Instance..." -ForegroundColor Yellow

$DeployCommand = @"
az container create \
  --resource-group $ResourceGroupName \
  --name $ContainerName \
  --image $AcrServer/flushbot:latest \
  --registry-login-server $AcrServer \
  --registry-username $AcrUsername \
  --registry-password $AcrPassword \
  --cpu 1 \
  --memory 2 \
  --restart-policy Always \
  --environment-variables \
    TELEGRAM_BOT_TOKEN=$TelegramBotToken \
    SUDO_USER_ID=$SudoUserId \
    DATABASE_URL="$DatabaseUrl" \
    REDIS_URL="$RedisUrl" \
    OPENROUTER_GROK_KEY="$GroKApiKey" \
    OPENROUTER_GEMINI_KEY="$GeminiApiKey" \
    ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO \
    ENABLE_BATCH_PROCESSING=false \
  --ports 8000 \
  --location $Location
"@

Invoke-Expression $DeployCommand

# 6. Show deployment status
Write-Host "📊 Checking deployment status..." -ForegroundColor Yellow
az container show --resource-group $ResourceGroupName --name $ContainerName --query "{Status:instanceView.state,IP:ipAddress.ip,Ports:ipAddress.ports}" --output table

# 7. Show logs
Write-Host "📋 Container Logs:" -ForegroundColor Green
az container logs --resource-group $ResourceGroupName --name $ContainerName

Write-Host "✅ FlushBot deployment completed!" -ForegroundColor Green
Write-Host "📍 Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host "🐳 Container: $ContainerName" -ForegroundColor Cyan
Write-Host "🌍 Location: $Location" -ForegroundColor Cyan

# Instructions for managing the deployment
Write-Host "`n📖 Management Commands:" -ForegroundColor Magenta
Write-Host "View logs: az container logs --resource-group $ResourceGroupName --name $ContainerName" -ForegroundColor Gray
Write-Host "Restart: az container restart --resource-group $ResourceGroupName --name $ContainerName" -ForegroundColor Gray
Write-Host "Delete: az container delete --resource-group $ResourceGroupName --name $ContainerName --yes" -ForegroundColor Gray
Write-Host "Status: az container show --resource-group $ResourceGroupName --name $ContainerName --query instanceView.state" -ForegroundColor Gray