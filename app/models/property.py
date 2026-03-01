from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Property(Base):
    __tablename__ = "properties"

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_properties_org_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    timezone = Column(String(100), nullable=False, default="America/New_York")
    address_line = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization = relationship("Organization", back_populates="properties")
    tenants = relationship("Tenant", back_populates="property")
    call_logs = relationship("CallLog", back_populates="property")
    csv_imports = relationship("CsvImport", back_populates="property")
    user_access = relationship(
        "PropertyUserAccess",
        back_populates="property",
        cascade="all, delete-orphan",
    )