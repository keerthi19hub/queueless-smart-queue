from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    prefix = Column(String(10), nullable=False)  # e.g., ADM, FEE, SUP, GEN
    counter_number = Column(String(50), nullable=False, default="Counter 1")
    description = Column(Text, nullable=True)
    icon = Column(String(50), default="building")
    avg_service_time_mins = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow)
    
    tokens = relationship("Token", back_populates="service", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "prefix": self.prefix,
            "counter_number": self.counter_number,
            "description": self.description,
            "icon": self.icon,
            "avg_service_time_mins": self.avg_service_time_mins,
            "is_active": self.is_active,
        }

class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    token_number = Column(String(20), nullable=False, index=True)  # e.g., ADM-101
    sequence_number = Column(Integer, nullable=False)             # 101, 102...
    reference_code = Column(String(20), unique=True, nullable=False, index=True) # e.g., QL-9X4K2M
    
    visitor_name = Column(String(100), nullable=True)
    student_id = Column(String(50), nullable=True)
    phone_or_email = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Statuses: WAITING, SERVING, COMPLETED, SKIPPED, CANCELLED
    status = Column(String(20), nullable=False, default="WAITING", index=True)
    
    idempotency_key = Column(String(64), nullable=True, unique=True, index=True)
    
    created_at = Column(DateTime, default=utcnow, index=True)
    called_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    service_duration_seconds = Column(Integer, nullable=True)
    
    service = relationship("Service", back_populates="tokens")
    events = relationship("QueueEvent", back_populates="token", cascade="all, delete-orphan", order_by="QueueEvent.created_at.desc()")
    
    __table_args__ = (
        Index("idx_service_status_created", "service_id", "status", "created_at"),
    )
    
    def to_dict(self, include_events=False):
        data = {
            "id": self.id,
            "service_id": self.service_id,
            "service_name": self.service.name if self.service else None,
            "service_prefix": self.service.prefix if self.service else None,
            "counter_number": self.service.counter_number if self.service else None,
            "token_number": self.token_number,
            "sequence_number": self.sequence_number,
            "reference_code": self.reference_code,
            "visitor_name": self.visitor_name,
            "student_id": self.student_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "called_at": self.called_at.isoformat() if self.called_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "service_duration_seconds": self.service_duration_seconds,
        }
        if include_events:
            data["events"] = [e.to_dict() for e in self.events]
        return data

class QueueEvent(Base):
    __tablename__ = "queue_events"
    
    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False) # CREATED, CALLED, RECALLED, COMPLETED, SKIPPED, CANCELLED
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, index=True)
    
    token = relationship("Token", back_populates="events")
    
    def to_dict(self):
        return {
            "id": self.id,
            "token_id": self.token_id,
            "event_type": self.event_type,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), default="admin")
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    key = Column(String(60), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
