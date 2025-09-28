"""
Database Models and Operations for FlushBot
SQLAlchemy-based database layer for persistent storage
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import json

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, 
    DateTime, Float, ForeignKey, Index, JSON, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
from loguru import logger

from config.settings import settings

Base = declarative_base()


class SecurityLevel(str, Enum):
    """Security level enumeration"""
    LOW = "low"
    MEDIUM = "medium" 
    EXTREME = "extreme"


class ViolationType(str, Enum):
    """Violation type enumeration"""
    CHILD_EXPLOITATION = "child_exploitation"
    ILLEGAL_DRUGS = "illegal_drugs"
    WEAPONS_VIOLENCE = "weapons_violence"
    HATE_TERRORISM = "hate_terrorism"
    FRAUD_SCAMS = "fraud_scams"
    SPAM_ADVERTISING = "spam_advertising"
    BOT_BEHAVIOR = "bot_behavior"


class ActionType(str, Enum):
    """Moderation action enumeration"""
    ALLOW = "allow"
    WARN = "warn"
    MUTE = "mute"
    RESTRICT = "restrict"
    BAN = "ban"
    DELETE = "delete"


# Database Models

class Chat(Base):
    """Chat/Group configuration"""
    __tablename__ = "chats"
    
    chat_id = Column(Integer, primary_key=True)
    title = Column(String(255))
    chat_type = Column(String(50))  # group, supergroup, channel
    security_level = Column(String(20), default=SecurityLevel.MEDIUM.value)
    auto_delete_violations = Column(Boolean, default=True)
    log_all_messages = Column(Boolean, default=False)
    bot_detection_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Configuration JSON
    config = Column(JSON, default=lambda: {})
    
    # Relationships
    messages = relationship("Message", back_populates="chat")
    violations = relationship("Violation", back_populates="chat")
    actions = relationship("ModerationAction", back_populates="chat")
    
    def __repr__(self):
        return f"<Chat(chat_id={self.chat_id}, title='{self.title}', security_level='{self.security_level}')>"


class User(Base):
    """User information and statistics"""
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_bot = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    violation_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(Text)
    ban_until = Column(DateTime)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Trust score (0.0 to 1.0)
    trust_score = Column(Float, default=0.5)
    
    # Relationships
    messages = relationship("Message", back_populates="user")
    violations = relationship("Violation", back_populates="user")
    actions_received = relationship("ModerationAction", back_populates="user")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', violations={self.violation_count})>"


class Message(Base):
    """Message storage and metadata"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.chat_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    text = Column(Text)
    message_type = Column(String(50))  # text, photo, video, document, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Analysis results
    analyzed = Column(Boolean, default=False)
    analysis_confidence = Column(Float, default=0.0)
    violation_detected = Column(Boolean, default=False)
    
    # Message metadata
    message_metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")
    violations = relationship("Violation", back_populates="message")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_chat_timestamp', 'chat_id', 'timestamp'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_message_chat', 'message_id', 'chat_id'),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat_id={self.chat_id}, user_id={self.user_id}, analyzed={self.analyzed})>"


class Violation(Base):
    """Detected policy violations"""
    __tablename__ = "violations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.chat_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    violation_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    confidence = Column(Float, nullable=False)
    
    # Detection details
    detected_by = Column(String(50))  # ai, rules, manual
    ai_model = Column(String(100))
    rule_matches = Column(JSON, default=lambda: [])
    
    # Violation content
    description = Column(Text)
    keywords_matched = Column(JSON, default=lambda: [])
    patterns_matched = Column(JSON, default=lambda: [])
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="violations")
    chat = relationship("Chat", back_populates="violations")
    user = relationship("User", back_populates="violations")
    actions = relationship("ModerationAction", back_populates="violation")
    
    def __repr__(self):
        return f"<Violation(id={self.id}, type={self.violation_type}, severity={self.severity}, confidence={self.confidence})>"


class ModerationAction(Base):
    """Moderation actions taken"""
    __tablename__ = "moderation_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.chat_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    violation_id = Column(Integer, ForeignKey("violations.id"))
    
    action_type = Column(String(20), nullable=False)
    reason = Column(Text)
    duration = Column(Integer)  # Duration in seconds for temporary actions
    
    # Action metadata
    automated = Column(Boolean, default=True)
    admin_user_id = Column(Integer)  # Admin who performed manual action
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Relationships
    chat = relationship("Chat", back_populates="actions")
    user = relationship("User", back_populates="actions_received")
    violation = relationship("Violation", back_populates="actions")
    
    def __repr__(self):
        return f"<ModerationAction(id={self.id}, action={self.action_type}, user_id={self.user_id}, automated={self.automated})>"


class APIUsage(Base):
    """API usage tracking"""
    __tablename__ = "api_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    api_provider = Column(String(50), nullable=False)  # grok, gemini
    model = Column(String(100), nullable=False)
    
    requests_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    
    # Performance metrics
    avg_response_time = Column(Float, default=0.0)
    error_count = Column(Integer, default=0)
    success_rate = Column(Float, default=1.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<APIUsage(date={self.date}, provider={self.api_provider}, requests={self.requests_count})>"


# Database Manager Class

class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self):
        """Setup database connection and session factory"""
        # Create engine with appropriate settings
        if settings.database_url.startswith("sqlite"):
            # SQLite specific settings
            self.engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.debug
            )
        else:
            # PostgreSQL settings
            self.engine = create_engine(
                settings.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=settings.debug
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False, 
            bind=self.engine
        )
        
        logger.info(f"Database initialized: {settings.database_url}")
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    # Chat Operations
    
    async def get_or_create_chat(self, chat_id: int, title: str = None, chat_type: str = None) -> Chat:
        """Get existing chat or create new one"""
        with self.get_session() as session:
            chat = session.query(Chat).filter(Chat.chat_id == chat_id).first()
            
            if not chat:
                chat = Chat(
                    chat_id=chat_id,
                    title=title,
                    chat_type=chat_type,
                    security_level=settings.default_security_level
                )
                session.add(chat)
                session.commit()
                session.refresh(chat)
                logger.info(f"Created new chat: {chat_id}")
            else:
                # Update title if provided
                if title and chat.title != title:
                    chat.title = title
                    chat.updated_at = datetime.utcnow()
                    session.commit()
            
            return chat
    
    async def update_chat_security_level(self, chat_id: int, security_level: str) -> bool:
        """Update chat security level"""
        with self.get_session() as session:
            chat = session.query(Chat).filter(Chat.chat_id == chat_id).first()
            if chat:
                chat.security_level = security_level
                chat.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
    
    async def get_chat_settings(self, chat_id: int) -> Optional[Dict]:
        """Get chat settings"""
        with self.get_session() as session:
            chat = session.query(Chat).filter(Chat.chat_id == chat_id).first()
            if chat:
                return {
                    "chat_id": chat.chat_id,
                    "title": chat.title,
                    "security_level": chat.security_level,
                    "auto_delete_violations": chat.auto_delete_violations,
                    "log_all_messages": chat.log_all_messages,
                    "bot_detection_enabled": chat.bot_detection_enabled,
                    "config": chat.config
                }
            return None
    
    # User Operations
    
    async def get_or_create_user(self, user_data: Dict) -> User:
        """Get existing user or create new one"""
        with self.get_session() as session:
            user = session.query(User).filter(User.user_id == user_data["user_id"]).first()
            
            if not user:
                user = User(**user_data)
                session.add(user)
                session.commit()
                session.refresh(user)
            else:
                # Update user info
                for key, value in user_data.items():
                    if hasattr(user, key) and key != "user_id":
                        setattr(user, key, value)
                user.last_active = datetime.utcnow()
                session.commit()
            
            return user
    
    async def increment_user_violations(self, user_id: int) -> int:
        """Increment user violation count"""
        with self.get_session() as session:
            user = session.query(User).filter(User.user_id == user_id).first()
            if user:
                user.violation_count += 1
                session.commit()
                return user.violation_count
            return 0
    
    async def ban_user(self, user_id: int, reason: str, duration: Optional[int] = None) -> bool:
        """Ban user with optional duration"""
        with self.get_session() as session:
            user = session.query(User).filter(User.user_id == user_id).first()
            if user:
                user.is_banned = True
                user.ban_reason = reason
                if duration:
                    user.ban_until = datetime.utcnow() + timedelta(seconds=duration)
                session.commit()
                return True
            return False
    
    # Message Operations
    
    async def store_message(self, message_data: Dict) -> Message:
        """Store message in database"""
        with self.get_session() as session:
            message = Message(**message_data)
            session.add(message)
            session.commit()
            session.refresh(message)
            return message
    
    async def update_message_analysis(self, message_id: int, analysis_result: Dict) -> bool:
        """Update message with analysis results"""
        with self.get_session() as session:
            message = session.query(Message).filter(Message.id == message_id).first()
            if message:
                message.analyzed = True
                message.analysis_confidence = analysis_result.get("confidence", 0.0)
                message.violation_detected = len(analysis_result.get("violations", [])) > 0
                session.commit()
                return True
            return False
    
    # Violation Operations
    
    async def store_violation(self, violation_data: Dict) -> Violation:
        """Store violation record"""
        with self.get_session() as session:
            violation = Violation(**violation_data)
            session.add(violation)
            session.commit()
            session.refresh(violation)
            return violation
    
    async def get_user_violations(self, user_id: int, days: int = 30) -> List[Violation]:
        """Get user violations in the last N days"""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            return session.query(Violation)\
                .filter(Violation.user_id == user_id)\
                .filter(Violation.timestamp >= cutoff_date)\
                .order_by(Violation.timestamp.desc())\
                .all()
    
    # Moderation Action Operations
    
    async def store_moderation_action(self, action_data: Dict) -> ModerationAction:
        """Store moderation action"""
        with self.get_session() as session:
            action = ModerationAction(**action_data)
            session.add(action)
            session.commit()
            session.refresh(action)
            return action
    
    # Analytics and Statistics
    
    async def get_chat_statistics(self, chat_id: int, days: int = 30) -> Dict:
        """Get chat statistics"""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            total_messages = session.query(Message)\
                .filter(Message.chat_id == chat_id)\
                .filter(Message.timestamp >= cutoff_date)\
                .count()
            
            total_violations = session.query(Violation)\
                .filter(Violation.chat_id == chat_id)\
                .filter(Violation.timestamp >= cutoff_date)\
                .count()
            
            total_actions = session.query(ModerationAction)\
                .filter(ModerationAction.chat_id == chat_id)\
                .filter(ModerationAction.timestamp >= cutoff_date)\
                .count()
            
            return {
                "chat_id": chat_id,
                "period_days": days,
                "total_messages": total_messages,
                "total_violations": total_violations,
                "total_actions": total_actions,
                "violation_rate": total_violations / total_messages if total_messages > 0 else 0
            }
    
    async def get_api_usage_stats(self, days: int = 7) -> Dict:
        """Get API usage statistics"""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            usage_records = session.query(APIUsage)\
                .filter(APIUsage.date >= cutoff_date)\
                .all()
            
            total_requests = sum(r.requests_count for r in usage_records)
            total_cost = sum(r.cost for r in usage_records)
            avg_success_rate = sum(r.success_rate for r in usage_records) / len(usage_records) if usage_records else 0
            
            return {
                "period_days": days,
                "total_requests": total_requests,
                "total_cost": total_cost,
                "avg_success_rate": avg_success_rate,
                "records_count": len(usage_records)
            }
    
    async def get_active_chats(self) -> List[Chat]:
        """Get all active chats"""
        with self.get_session() as session:
            return session.query(Chat)\
                .filter(Chat.is_active == True)\
                .all()
    
    async def get_recent_messages(self, chat_id: int, since: datetime) -> List[Message]:
        """Get recent messages from a chat since a specific time"""
        with self.get_session() as session:
            return session.query(Message)\
                .filter(Message.chat_id == chat_id)\
                .filter(Message.timestamp >= since)\
                .order_by(Message.timestamp.desc())\
                .limit(1000)\
                .all()  # Limit to prevent memory issues
    
    async def update_message_analysis(self, message_db_id: int, analysis_result: Dict):
        """Update message with analysis results"""
        with self.get_session() as session:
            message = session.query(Message).filter(Message.id == message_db_id).first()
            if message:
                message.analyzed = True
                message.analysis_confidence = analysis_result.get("confidence", 0.0)
                message.violation_detected = len(analysis_result.get("violations", [])) > 0
                session.commit()


# Global database instance
db_manager = DatabaseManager()