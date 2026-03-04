from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    external_id = Column(String(100), unique=True, nullable=True, index=True)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(String(30), nullable=False, index=True)

    property_name = Column(String(255), nullable=True)
    timezone = Column(String(100), nullable=False, default="America/New_York")

    rent_due_date = Column(Date, nullable=True)
    days_late = Column(Integer, nullable=False, default=0, server_default="0")

    consent_status = Column(Boolean, nullable=False, default=False, server_default="false")
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    consent_source = Column(String(255), nullable=True)
    consent_document_version = Column(String(100), nullable=True)

    opt_out_flag = Column(Boolean, nullable=False, default=False, server_default="false")
    opt_out_timestamp = Column(DateTime(timezone=True), nullable=True)
    eviction_status = Column(Boolean, nullable=False, default=False, server_default="false")
    is_suppressed = Column(Boolean, nullable=False, default=False, server_default="false")
    is_archived = Column(Boolean, nullable=False, default=False, server_default="false")
    archived_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization = relationship("Organization", back_populates="tenants")
    property = relationship("Property", back_populates="tenants")

    call_logs = relationship(
        "CallLog",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
