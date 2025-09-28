"""
FlushBot Configuration Management
Handles all application settings and environment variables
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Bot Configuration
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    bot_username: str = Field("", env="BOT_USERNAME")
    
    # Admin Configuration
    sudo_user_id: int = Field(..., env="SUDO_USER_ID")
    
    # AI API Configuration
    openrouter_grok_key: str = Field(..., env="OPENROUTER_GROK_KEY")
    openrouter_gemini_key: str = Field(..., env="OPENROUTER_GEMINI_KEY")
    openrouter_base_url: str = Field("https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL")
    grok_model: str = Field("x-ai/grok-beta", env="GROK_MODEL")
    gemini_model: str = Field("google/gemini-2.0-flash-exp", env="GEMINI_MODEL")
    
    # Database Configuration
    database_url: str = Field("sqlite:///flushbot.db", env="DATABASE_URL")
    
    # Redis Configuration
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_password: str = Field("", env="REDIS_PASSWORD")
    redis_db: int = Field(0, env="REDIS_DB")
    
    # Cache Configuration
    cache_ttl: int = Field(3600, env="CACHE_TTL")
    message_cache_size: int = Field(1000, env="MESSAGE_CACHE_SIZE")
    batch_processing_size: int = Field(50, env="BATCH_PROCESSING_SIZE")
    
    # API Quota Management
    daily_api_quota: int = Field(1000, env="DAILY_API_QUOTA")
    hourly_api_quota: int = Field(100, env="HOURLY_API_QUOTA")
    api_rate_limit: int = Field(10, env="API_RATE_LIMIT")
    quota_reset_hour: int = Field(0, env="QUOTA_RESET_HOUR")
    
    # Security Configuration
    default_security_level: str = Field("medium", env="DEFAULT_SECURITY_LEVEL")
    extreme_mode_enabled: bool = Field(True, env="EXTREME_MODE_ENABLED")
    auto_delete_violations: bool = Field(True, env="AUTO_DELETE_VIOLATIONS")
    log_all_messages: bool = Field(False, env="LOG_ALL_MESSAGES")
    
    # Batch Processing
    enable_batch_processing: bool = Field(True, env="ENABLE_BATCH_PROCESSING")
    batch_interval_minutes: int = Field(30, env="BATCH_INTERVAL_MINUTES")
    csv_export_path: str = Field("./data/exports/", env="CSV_EXPORT_PATH")
    parquet_support: bool = Field(True, env="PARQUET_SUPPORT")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("./logs/flushbot.log", env="LOG_FILE")
    log_max_size: str = Field("10MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(5, env="LOG_BACKUP_COUNT")
    
    # Performance Settings
    max_concurrent_requests: int = Field(10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")
    retry_attempts: int = Field(3, env="RETRY_ATTEMPTS")
    backoff_factor: float = Field(2.0, env="BACKOFF_FACTOR")
    
    # Feature Flags
    enable_bot_detection: bool = Field(True, env="ENABLE_BOT_DETECTION")
    enable_historical_analysis: bool = Field(True, env="ENABLE_HISTORICAL_ANALYSIS")
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    enable_webhooks: bool = Field(False, env="ENABLE_WEBHOOKS")
    
    # Development Settings
    debug: bool = Field(False, env="DEBUG")
    testing: bool = Field(False, env="TESTING")
    mock_ai_responses: bool = Field(False, env="MOCK_AI_RESPONSES")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    def get_ai_headers(self, use_fallback: bool = False) -> dict:
        """Get headers for AI API requests"""
        key = self.openrouter_gemini_key if use_fallback else self.openrouter_grok_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/AnuragKumarpy/flushbot",
            "X-Title": "FlushBot Security System"
        }
    
    def get_ai_model(self, use_fallback: bool = False) -> str:
        """Get AI model name"""
        return self.gemini_model if use_fallback else self.grok_model
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return not self.debug and not self.testing

# Global settings instance
settings = Settings()

# Security level mappings
SECURITY_LEVELS = {
    "low": {
        "name": "Low Security",
        "description": "Warning only mode",
        "actions": ["warn", "log"],
        "threshold": 0.3
    },
    "medium": {
        "name": "Medium Security", 
        "description": "Progressive restrictions",
        "actions": ["warn", "mute", "restrict"],
        "threshold": 0.6
    },
    "extreme": {
        "name": "Extreme Security",
        "description": "Zero tolerance - immediate ban",
        "actions": ["ban", "delete", "log"],
        "threshold": 0.8
    }
}

# Violation categories
VIOLATION_CATEGORIES = {
    "drugs": {
        "name": "Illegal Substances",
        "keywords": ["drug", "weed", "cocaine", "heroin", "mdma", "lsd"],
        "severity": "high"
    },
    "child_abuse": {
        "name": "Child Exploitation", 
        "keywords": ["cp", "child", "minor", "underage"],
        "severity": "critical"
    },
    "weapons": {
        "name": "Weapons & Violence",
        "keywords": ["gun", "weapon", "bomb", "explosive"],
        "severity": "high"
    },
    "hate_speech": {
        "name": "Hate Speech",
        "keywords": ["nazi", "terrorist", "kill"],
        "severity": "medium"
    },
    "fraud": {
        "name": "Fraud & Scams",
        "keywords": ["scam", "fraud", "phishing", "fake"],
        "severity": "medium"
    },
    "spam": {
        "name": "Spam",
        "keywords": ["spam", "advertisement", "promotion"],
        "severity": "low"
    }
}

def get_log_config() -> dict:
    """Get logging configuration"""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[{time:YYYY-MM-DD HH:mm:ss}] {level} | {name}:{line} - {message}",
                "style": "{"
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "loguru._logger.Logger",
                "level": settings.log_level,
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["default"],
        },
    }