from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class Branch(Base):
    __tablename__ = "branches"

    id = Column(String(50), primary_key=True)  # e.g. "branch_mum", "branch_del"
    code = Column(String(10), unique=True, nullable=False)  # "BOM", "DEL"
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Client(Base):
    __tablename__ = "clients"

    id = Column(String(50), primary_key=True)  # e.g. "client_01"
    code = Column(String(50), unique=True, nullable=False)  # "TATA_MOTORS"
    name = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
