from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Table, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

# Association table mapping Roles to granular Permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(50), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(50), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
)

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(50), primary_key=True)  # e.g. "job:prepare", "job:check", "job:file", "job:cancel", "job:reopen"
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Role(Base):
    __tablename__ = "roles"

    id = Column(String(50), primary_key=True)  # "MAKER", "CHECKER", "FILER", "SUPERVISOR", "ADMIN", "CLIENT_VIEWER", "PARSER"
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    permissions = relationship("Permission", secondary=role_permissions, backref="roles")
