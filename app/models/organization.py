from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    properties = relationship(
        "Property",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    memberships = relationship(
        "AdminUserMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    tenants = relationship("Tenant", back_populates="organization")
    call_logs = relationship("CallLog", back_populates="organization")
    csv_imports = relationship("CsvImport", back_populates="organization")
    call_policies = relationship("CallPolicy", back_populates="organization")
